import base64
import hashlib
import hmac
import json
from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.views.generic import UpdateView, ListView, DetailView, View, TemplateView

from apps.base.mixin import AdminHospitalScopedQuerysetMixin, AdminStaffOnlyMixin
from apps.hospitals.crypto import decrypt_khalti_key
from apps.patients.models import PatientAppointment

from .forms import AppointmentPaymentForm
from .models import AppointmentPayment


def _build_esewa_signature(secret_key, message):
    return base64.b64encode(
        hmac.new(secret_key.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).digest()
    ).decode('utf-8')


def _sign_esewa_message(secret_key, total_amount, transaction_uuid, product_code):
    signed_fields = "total_amount,transaction_uuid,product_code"
    message = (
        f"total_amount={total_amount},"
        f"transaction_uuid={transaction_uuid},"
        f"product_code={product_code}"
    )
    return signed_fields, _build_esewa_signature(secret_key=secret_key, message=message)


def _decode_esewa_data(data):
    padded = f"{data}{'=' * (-len(data) % 4)}"
    decoded = base64.b64decode(padded.encode('utf-8')).decode('utf-8')
    return json.loads(decoded)


class AppointmentPaymentView(LoginRequiredMixin, UpdateView):
    model = AppointmentPayment
    form_class = AppointmentPaymentForm
    template_name = 'payments/appointment_payment.html'
    context_object_name = 'payment'

    def get_appointment(self):
        return get_object_or_404(
            PatientAppointment.objects.select_related('patient__user', 'doctor__user', 'doctor'),
            pk=self.kwargs.get('appointment_id'),
        )

    def _has_permission(self, appointment):
        user = self.request.user
        if user.is_super_admin:
            return True
        if user.is_admin:
            hospital_id = getattr(self.request, 'admin_hospital_id', None)
            if not hospital_id:
                return False
            return appointment.doctor and appointment.doctor.hospital_id == hospital_id
        if user.is_patient:
            return appointment.patient.user_id == user.id
        return False

    def get_object(self, queryset=None):
        appointment = self.get_appointment()
        if not self._has_permission(appointment):
            raise PermissionDenied("You don't have permission to access this payment.")

        payment, _ = AppointmentPayment.objects.get_or_create(
            appointment=appointment,
            defaults={
                'amount': appointment.doctor.consultation_fee,
                'status': AppointmentPayment.PaymentStatus.PENDING,
                'payment_method': AppointmentPayment.PaymentMethod.CASH,
            },
        )
        return payment

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['appointment'] = self.object.appointment
        return context

    def form_valid(self, form):
        payment = form.save(commit=False)
        payment.status = AppointmentPayment.PaymentStatus.PAID
        payment.paid_at = timezone.now()
        payment.save()

        messages.success(self.request, 'Payment saved successfully.')

        appointment = payment.appointment
        if self.request.user.is_super_admin or self.request.user.is_admin:
            return redirect(reverse_lazy('appointments:appointment_doctor_schedule', kwargs={'pk': appointment.doctor_id}))

        return redirect(reverse_lazy('appointments:booking_confirmation'))


class PaymentListView(AdminHospitalScopedQuerysetMixin, AdminStaffOnlyMixin, ListView):
    """List payments for admin/super-admin."""
    model = AppointmentPayment
    template_name = 'payments/payment_list.html'
    context_object_name = 'payments'
    paginate_by = 10
    admin_hospital_field = 'appointment__hospital_id'

    def get_queryset(self):
        queryset = AppointmentPayment.objects.select_related(
            'appointment__patient__user',
            'appointment__doctor__user',
            'appointment__doctor__hospital',
        ).order_by('-created')
        queryset = self.scope_queryset_for_admin(queryset, hospital_field=self.admin_hospital_field)

        status = self.request.GET.get('status', '').strip()
        if status:
            queryset = queryset.filter(status=status)

        payment_method = self.request.GET.get('payment_method', '').strip()
        if payment_method:
            queryset = queryset.filter(payment_method=payment_method)

        search = self.request.GET.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(appointment__patient__user__first_name__icontains=search)
                | Q(appointment__patient__user__last_name__icontains=search)
                | Q(appointment__patient__booking_uuid__icontains=search)
                | Q(appointment__doctor__user__first_name__icontains=search)
                | Q(appointment__doctor__user__last_name__icontains=search)
                | Q(transaction_reference__icontains=search)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        payments = self.scope_queryset_for_admin(
            AppointmentPayment.objects.all(),
            hospital_field=self.admin_hospital_field,
        )
        context['selected_status'] = self.request.GET.get('status', '').strip()
        context['selected_payment_method'] = self.request.GET.get('payment_method', '').strip()
        context['search_query'] = self.request.GET.get('search', '').strip()
        context['status_choices'] = AppointmentPayment.PaymentStatus.choices
        context['payment_method_choices'] = AppointmentPayment.PaymentMethod.choices
        context['analytics_cards'] = [
            {'label': 'Total Payments', 'value': payments.count(), 'value_class': 'text-gray-900', 'icon': 'payments'},
            {
                'label': 'Cash Payments',
                'value': payments.filter(status=AppointmentPayment.PaymentMethod.CASH).count(),
                'icon': 'account_balance_wallet',
            },
            {
                'label': 'Online Payments',
                'value': payments.filter(status=AppointmentPayment.PaymentMethod.ONLINE).count(),
                'icon': 'language',
            },
            {
                'label': 'Card Payments',
                'value': payments.filter(status=AppointmentPayment.PaymentMethod.CARD).count(),
                'icon': 'credit_card',

            }
        ]
        return context


class PaymentDetailView(AdminHospitalScopedQuerysetMixin, AdminStaffOnlyMixin, DetailView):
    """Show payment detail for admin/super-admin."""
    model = AppointmentPayment
    template_name = 'payments/payment_detail.html'
    context_object_name = 'payment'
    admin_hospital_field = 'appointment__hospital_id'

    def get_queryset(self):
        queryset = AppointmentPayment.objects.select_related(
            'appointment__patient__user',
            'appointment__doctor__user',
            'appointment__doctor__hospital',
        )
        return self.scope_queryset_for_admin(queryset, hospital_field=self.admin_hospital_field)


class PaymentUpdateView(AdminHospitalScopedQuerysetMixin, AdminStaffOnlyMixin, UpdateView):
    """Edit payment for admin/super-admin."""
    model = AppointmentPayment
    form_class = AppointmentPaymentForm
    template_name = 'payments/payment_form.html'
    context_object_name = 'payment'
    admin_hospital_field = 'appointment__hospital_id'

    def get_queryset(self):
        queryset = AppointmentPayment.objects.select_related(
            'appointment__patient__user',
            'appointment__doctor__user',
            'appointment__doctor__hospital',
        )
        return self.scope_queryset_for_admin(queryset, hospital_field=self.admin_hospital_field)

    def get_success_url(self):
        return reverse('payments:payment_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        payment = form.save(commit=False)
        if payment.status == AppointmentPayment.PaymentStatus.PAID and not payment.paid_at:
            payment.paid_at = timezone.now()
        elif payment.status != AppointmentPayment.PaymentStatus.PAID:
            payment.paid_at = None
        payment.save()
        messages.success(self.request, 'Payment updated successfully.')
        return redirect(self.get_success_url())


class PatientPaymentIndexView(LoginRequiredMixin, ListView):
    """Short list of payments; open one appointment to pay on PatientPaymentView."""
    model = AppointmentPayment
    template_name = 'payments/patient_payment_index.html'
    context_object_name = 'payments'
    paginate_by = 10

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_patient:
            raise PermissionDenied("Only patients can access this page.")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return AppointmentPayment.objects.select_related(
            'appointment__patient__user',
            'appointment__doctor__user',
            'appointment__doctor__hospital',
        ).filter(
            appointment__patient__user=self.request.user,
        ).order_by('-created')


class PatientPaymentView(LoginRequiredMixin, TemplateView):
    """Single appointment payment screen (cash / Khalti)."""
    template_name = 'payments/patient_payment.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_patient:
            raise PermissionDenied("Only patients can access this page.")
        return super().dispatch(request, *args, **kwargs)

    def get_payment(self):
        appointment_id = self.kwargs['appointment_id']
        return get_object_or_404(
            AppointmentPayment.objects.select_related(
                'appointment__patient__user',
                'appointment__doctor__user',
                'appointment__doctor__hospital',
            ),
            appointment_id=appointment_id,
            appointment__patient__user=self.request.user,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['payment'] = self.get_payment()
        return context

    def get(self, request, *args, **kwargs):
        pidx = (
            request.GET.get('pidx', '')
            or request.GET.get('transaction_id', '')
            or request.GET.get('tidx', '')
            or request.GET.get('txnId', '')
        ).strip()
        khalti_status = request.GET.get('status', '').strip().upper()

        if pidx:
            payment = AppointmentPayment.objects.filter(
                transaction_reference=pidx,
                appointment__patient__user=request.user,
            ).first()

            if not payment:
                messages.error(request, 'Payment reference not found for this account.')
                return redirect(reverse('payments:patient_payment_list'))

            if khalti_status == 'COMPLETED':
                if payment.status != AppointmentPayment.PaymentStatus.PAID:
                    payment.status = AppointmentPayment.PaymentStatus.PAID
                    payment.payment_method = AppointmentPayment.PaymentMethod.ONLINE
                    payment.paid_at = timezone.now()
                    payment.save(update_fields=['status', 'payment_method', 'paid_at', 'modified'])
                messages.success(request, 'Khalti payment completed successfully.')
                return redirect(reverse('payments:patient_payment_status', kwargs={'pk': payment.pk}))

            if khalti_status in {'FAILED', 'EXPIRED', 'CANCELED', 'USER_CANCELED'}:
                if payment.status != AppointmentPayment.PaymentStatus.PAID:
                    payment.status = AppointmentPayment.PaymentStatus.FAILED
                    payment.save(update_fields=['status', 'modified'])
                messages.error(request, 'Khalti payment was not completed.')
                return redirect(reverse('payments:patient_payment_status', kwargs={'pk': payment.pk}))

            messages.info(request, 'Khalti payment is still pending. Please check again.')
            return redirect(reverse('payments:patient_payment_status', kwargs={'pk': payment.pk}))

        return super().get(request, *args, **kwargs)


class PatientPaymentStatusView(LoginRequiredMixin, DetailView):
    """Show payment result/status page for patient."""
    model = AppointmentPayment
    template_name = 'payments/patient_payment_status.html'
    context_object_name = 'payment'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_patient:
            raise PermissionDenied("Only patients can access this page.")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return AppointmentPayment.objects.select_related(
            'appointment__patient__user',
            'appointment__doctor__user',
            'appointment__doctor__hospital',
        ).filter(appointment__patient__user=self.request.user)


class PatientPaymentProcessView(LoginRequiredMixin, View):
    """Handle cash or Khalti payment selection for patient appointments."""

    @staticmethod
    def _get_khalti_secret_key(appointment):
        """Read and validate hospital Khalti key only at payment initiation time."""
        hospital = appointment.doctor.hospital
        return decrypt_khalti_key(hospital.khalti_secret_key)

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_patient:
            raise PermissionDenied("Only patients can access this page.")
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        appointment_id = request.POST.get('appointment_id')
        selected_method = request.POST.get('payment_method', '').strip().upper()

        if not appointment_id:
            messages.error(request, 'Please choose an appointment to pay for.')
            return redirect(reverse('payments:patient_payment_list'))

        # Fetch appointment with required relations
        appointment = get_object_or_404(
            PatientAppointment.objects.select_related('patient__user', 'doctor__user', 'doctor', 'doctor__hospital'),
            pk=appointment_id,
            patient__user=request.user,
        )

        # Get or create payment record
        payment, _ = AppointmentPayment.objects.get_or_create(
            appointment=appointment,
            defaults={
                'amount': appointment.doctor.consultation_fee,
                'status': AppointmentPayment.PaymentStatus.PENDING,
                'payment_method': AppointmentPayment.PaymentMethod.CASH,
            },
        )

        if selected_method == AppointmentPayment.PaymentMethod.CASH:
            payment.payment_method = AppointmentPayment.PaymentMethod.CASH
            if payment.status != AppointmentPayment.PaymentStatus.PAID:
                payment.status = AppointmentPayment.PaymentStatus.PENDING
            payment.save(update_fields=['payment_method', 'status', 'modified'])
            messages.success(request, 'Cash at hospital selected. Please pay at the hospital counter.')
            return redirect(reverse('payments:patient_payment_status', kwargs={'pk': payment.pk}))

        if selected_method == 'KHALTI':
            payment.payment_method = AppointmentPayment.PaymentMethod.ONLINE
            if payment.status != AppointmentPayment.PaymentStatus.PAID:
                payment.status = AppointmentPayment.PaymentStatus.PENDING

            try:
                secret_key = self._get_khalti_secret_key(appointment)
            except ValueError:
                messages.error(request, 'Stored Khalti key is invalid. Please contact admin to reconfigure keys.')
                return redirect(reverse('payments:patient_payment_list'))

            if not secret_key:
                messages.error(request, 'Khalti secret key is not configured for this hospital.')
                return redirect(reverse('payments:patient_payment_list'))

            # Return to patient list scoped to this appointment; Khalti appends pidx/status query params.
            return_url = request.build_absolute_uri(
                reverse(
                    'payments:patient_payment_list_for_appointment',
                    kwargs={'appointment_id': appointment.id},
                )
            )
            website_url = request.build_absolute_uri('/')

            amount_paisa = int(payment.amount * 100)
            patient_user = appointment.patient.user
            purchase_order_id = f'APPT-{appointment.id}-{payment.id}'
            purchase_order_name = f'Appointment #{appointment.id}'

            initiate_khalti_payload = {
                'return_url': return_url,
                'website_url': website_url,
                'amount': amount_paisa,
                'purchase_order_id': purchase_order_id,
                'purchase_order_name': purchase_order_name,
                'customer_info': {
                    'name': patient_user.get_full_name() or patient_user.username,
                    'email': patient_user.email or 'no-email@example.com',
                    'phone': getattr(appointment.patient, 'contact_number', '') or '9800000000',
                },
            }

            headers = {
                'Authorization': f'Key {secret_key}',
                'Content-Type': 'application/json',
            }

            try:
                response = requests.post(
                    settings.PAYMENT_INITIATE_URL,
                    json=initiate_khalti_payload,
                    headers=headers,
                    timeout=15,
                )
            except requests.RequestException as exc:
                messages.error(request, f'Failed to connect to Khalti: {exc}')
                return redirect(reverse('payments:patient_payment_list'))

            try:
                response_data = response.json()
            except ValueError:
                response_data = {'detail': response.text}

            if response.ok:
                payment_url = response_data.get('payment_url')
                if not payment_url:
                    messages.error(request, 'Khalti payment URL not found in response.')
                    return redirect(reverse('payments:patient_payment_list'))

                payment.transaction_reference = response_data.get('pidx')
                payment.save(update_fields=['payment_method', 'status', 'transaction_reference', 'modified'])
                return redirect(payment_url)

            messages.error(request, f'Failed to initiate Khalti payment. {response_data}')
            return redirect(reverse('payments:patient_payment_list'))

        if selected_method == 'ESEWA':
            payment.payment_method = AppointmentPayment.PaymentMethod.ONLINE
            if payment.status != AppointmentPayment.PaymentStatus.PAID:
                payment.status = AppointmentPayment.PaymentStatus.PENDING

            total_amount = str(Decimal(payment.amount).quantize(Decimal('0.01')))
            transaction_uuid = f"ESEWA-APPT-{appointment.id}-{payment.id}-{int(timezone.now().timestamp())}"
            payment.transaction_reference = transaction_uuid

            # eSewa uses product_code to identify the merchant account.
            # It must be the configured merchant/product code, not a per-order value.
            product_code = getattr(settings, 'ESEWA_EPAY_V2_PRODUCT_CODE', '').strip()
            if not product_code:
                messages.error(
                    request,
                    'eSewa merchant product code is not configured. Please contact support.',
                )
                return redirect(reverse('payments:patient_payment_list'))
            secret_key = settings.ESEWA_EPAY_V2_SECRET_KEY
            signed_field_names, signature = _sign_esewa_message(
                secret_key=secret_key,
                total_amount=total_amount,
                transaction_uuid=transaction_uuid,
                product_code=product_code,
            )

            success_url = request.build_absolute_uri(reverse('payments:esewa_payment_callback'))
            failure_url = request.build_absolute_uri(reverse('payments:esewa_payment_callback'))

            form_payload = {
                'amount': total_amount,
                'tax_amount': '0',
                'total_amount': total_amount,
                'transaction_uuid': transaction_uuid,
                'product_code': product_code,
                'product_service_charge': '0',
                'product_delivery_charge': '0',
                'success_url': success_url,
                'failure_url': failure_url,
                'signed_field_names': signed_field_names,
                'signature': signature,
            }

            payment.save(update_fields=['payment_method', 'status', 'transaction_reference', 'modified'])

            return render(
                request,
                'payments/esewa_redirect.html',
                {
                    'esewa_action_url': settings.ESEWA_EPAY_V2_INITIATE_URL,
                    'esewa_payload': form_payload,
                    'payment': payment,
                },
            )

        messages.error(request, 'Please choose a valid payment method.')
        return redirect(reverse('payments:patient_payment_list'))


class EsewaPaymentCallbackView(LoginRequiredMixin, View):
    """Handle eSewa return callback for success/failure."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_patient:
            raise PermissionDenied("Only patients can access this page.")
        return super().dispatch(request, *args, **kwargs)

    def _verify_esewa_payload(self, payload):
        signed_field_names = payload.get('signed_field_names', '').strip()
        response_signature = payload.get('signature', '').strip()

        if not (signed_field_names and response_signature):
            return False

        fields_to_sign = [name.strip() for name in signed_field_names.split(',') if name.strip()]
        if not fields_to_sign:
            return False

        sign_parts = []
        for field_name in fields_to_sign:
            field_value = payload.get(field_name)
            if field_value is None:
                return False
            sign_parts.append(f"{field_name}={field_value}")

        expected_signature = _build_esewa_signature(
            secret_key=settings.ESEWA_EPAY_V2_SECRET_KEY,
            message=",".join(sign_parts),
        )
        return hmac.compare_digest(expected_signature, response_signature)

    def _get_payment(self, transaction_reference):
        return AppointmentPayment.objects.select_related(
            'appointment__patient__user',
        ).filter(
            transaction_reference=transaction_reference,
            appointment__patient__user=self.request.user,
        ).first()

    def get(self, request, *args, **kwargs):
        encoded_data = request.GET.get('data', '').strip()

        if encoded_data:
            try:
                payload = _decode_esewa_data(encoded_data)
            except (ValueError, TypeError, json.JSONDecodeError):
                messages.error(request, 'Invalid eSewa callback payload.')
                return redirect(reverse('payments:patient_payment_list'))

            transaction_uuid = payload.get('transaction_uuid', '').strip()
            payment = self._get_payment(transaction_uuid)
            if not payment:
                messages.error(request, 'eSewa transaction reference not found for this account.')
                return redirect(reverse('payments:patient_payment_list'))

            status = payload.get('status', '').strip().upper()
            signature_ok = self._verify_esewa_payload(payload)
            callback_product_code = payload.get('product_code', '').strip()
            expected_product_code = f'APPT-{payment.appointment_id}-{payment.id}'
            configured_product_code = getattr(settings, 'ESEWA_EPAY_V2_PRODUCT_CODE', '').strip()
            product_code_ok = (
                callback_product_code == expected_product_code
                or (configured_product_code and callback_product_code == configured_product_code)
            )

            try:
                callback_amount = Decimal(payload.get('total_amount', '0')).quantize(Decimal('0.01'))
            except (InvalidOperation, TypeError):
                callback_amount = Decimal('0.00')

            if (
                status in {'COMPLETE', 'SUCCESS'}
                and signature_ok
                and product_code_ok
                and callback_amount == Decimal(payment.amount).quantize(Decimal('0.01'))
            ):
                if payment.status != AppointmentPayment.PaymentStatus.PAID:
                    payment.status = AppointmentPayment.PaymentStatus.PAID
                    payment.payment_method = AppointmentPayment.PaymentMethod.ONLINE
                    payment.paid_at = timezone.now()
                    payment.save(update_fields=['status', 'payment_method', 'paid_at', 'modified'])
                messages.success(request, 'eSewa payment completed successfully.')
                return redirect(reverse('payments:patient_payment_status', kwargs={'pk': payment.pk}))

            if payment.status != AppointmentPayment.PaymentStatus.PAID:
                payment.status = AppointmentPayment.PaymentStatus.FAILED
                payment.save(update_fields=['status', 'modified'])
            messages.error(request, 'eSewa payment verification failed or payment was not completed.')
            return redirect(reverse('payments:patient_payment_status', kwargs={'pk': payment.pk}))

        fallback_reference = (
            request.GET.get('transaction_uuid', '')
            or request.GET.get('transaction_code', '')
            or request.GET.get('oid', '')
        ).strip()
        if fallback_reference:
            payment = self._get_payment(fallback_reference)
            if payment and payment.status != AppointmentPayment.PaymentStatus.PAID:
                payment.status = AppointmentPayment.PaymentStatus.FAILED
                payment.save(update_fields=['status', 'modified'])
                messages.error(request, 'eSewa payment was cancelled or failed.')
                return redirect(reverse('payments:patient_payment_status', kwargs={'pk': payment.pk}))

        messages.error(request, 'Unable to resolve eSewa payment result.')
        return redirect(reverse('payments:patient_payment_list'))
