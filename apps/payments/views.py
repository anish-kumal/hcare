import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.views.generic import UpdateView, ListView, DetailView, View

from apps.base.mixin import SuperAdminAndAdminOnlyMixin
from apps.patients.models import PatientAppointment

from .forms import AppointmentPaymentForm
from .models import AppointmentPayment


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
        if user.is_super_admin or user.is_admin:
            return True
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


class PaymentListView(SuperAdminAndAdminOnlyMixin, ListView):
    """List payments for admin/super-admin."""
    model = AppointmentPayment
    template_name = 'payments/payment_list.html'
    context_object_name = 'payments'
    paginate_by = 20

    def get_queryset(self):
        queryset = AppointmentPayment.objects.select_related(
            'appointment__patient__user',
            'appointment__doctor__user',
            'appointment__doctor__hospital',
        ).order_by('-created')

        status = self.request.GET.get('status', '').strip()
        if status:
            queryset = queryset.filter(status=status)

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
        context['selected_status'] = self.request.GET.get('status', '').strip()
        context['search_query'] = self.request.GET.get('search', '').strip()
        context['status_choices'] = AppointmentPayment.PaymentStatus.choices
        return context


class PaymentDetailView(SuperAdminAndAdminOnlyMixin, DetailView):
    """Show payment detail for admin/super-admin."""
    model = AppointmentPayment
    template_name = 'payments/payment_detail.html'
    context_object_name = 'payment'

    def get_queryset(self):
        return AppointmentPayment.objects.select_related(
            'appointment__patient__user',
            'appointment__doctor__user',
            'appointment__doctor__hospital',
        )


class PaymentUpdateView(SuperAdminAndAdminOnlyMixin, UpdateView):
    """Edit payment for admin/super-admin."""
    model = AppointmentPayment
    form_class = AppointmentPaymentForm
    template_name = 'payments/payment_form.html'
    context_object_name = 'payment'

    def get_queryset(self):
        return AppointmentPayment.objects.select_related(
            'appointment__patient__user',
            'appointment__doctor__user',
            'appointment__doctor__hospital',
        )

    def get_success_url(self):
        return reverse('payments:payment_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        payment = form.save(commit=False)
        if payment.status == AppointmentPayment.PaymentStatus.PAID and not payment.paid_at:
            payment.paid_at = timezone.now()
        payment.save()
        messages.success(self.request, 'Payment updated successfully.')
        return redirect(self.get_success_url())


class PatientPaymentListView(LoginRequiredMixin, ListView):
    """List patient payments available for payment."""
    model = AppointmentPayment
    template_name = 'payments/patient_payment_list.html'
    context_object_name = 'payments'

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

    def get(self, request, *args, **kwargs):
        # Khalti may return the payment identifier in different query keys.
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

            # Keep callback URL canonical and explicit to avoid provider slash normalization issues.
            return_url = request.build_absolute_uri('/payments/patient/')
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
                'Authorization': f'Key {getattr(appointment.doctor.hospital, "khalti_secret_key", None)}',
                'Content-Type': 'application/json',
            }

            if not headers['Authorization'].replace('Key ', '').strip():
                messages.error(request, 'Khalti secret key is not configured for this hospital.')
                return redirect(reverse('payments:patient_payment_list'))

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

        messages.error(request, 'Please choose a valid payment method.')
        return redirect(reverse('payments:patient_payment_list'))
