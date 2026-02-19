from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.views import View
from django.views.generic import UpdateView, ListView, DetailView
import requests

from apps.base.mixin import SuperAdminAndAdminOnlyMixin
from apps.patients.models import PatientAppointment

from .forms import AppointmentPaymentForm
from .models import AppointmentPayment


class AppointmentPaymentView(LoginRequiredMixin, View):
    template_name = 'payments/appointment_payment.html'

    def get_appointment(self):
        return get_object_or_404(
            PatientAppointment.objects.select_related('patient__user', 'doctor__user', 'doctor'),
            pk=self.kwargs.get('appointment_id'),
        )

    def _has_permission(self, appointment):
        user = self.request.user
        if user.is_patient:
            return appointment.patient.user_id == user.id
        return False

    def get_payment(self, appointment):
        """Return existing payment or create a pending cash default."""
        payment, _ = AppointmentPayment.objects.get_or_create(
            appointment=appointment,
            defaults={
                'amount': appointment.doctor.consultation_fee,
                'status': AppointmentPayment.PaymentStatus.PENDING,
                'payment_method': AppointmentPayment.PaymentMethod.CASH,
            },
        )
        return payment

    def get_object(self, queryset=None):
        appointment = self.get_appointment()
        if not self._has_permission(appointment):
            raise PermissionDenied("You don't have permission to access this payment.")
        return self.get_payment(appointment)

    def get(self, request, *args, **kwargs):
        appointment = self.get_appointment()
        if not self._has_permission(appointment):
            raise PermissionDenied("You don't have permission to access this payment.")
        payment = self.get_payment(appointment)
        context = {
            'appointment': appointment,
            'payment': payment,
            'khalti_enabled': bool(getattr(settings, 'KHALTI_SECRET_KEY', '').strip()),
        }
        return render(request, self.template_name, context)

    def _initiate_khalti(self, request, appointment, payment):
        secret_key = getattr(settings, 'KHALTI_SECRET_KEY', '').strip()
        if not secret_key:
            messages.error(request, 'Khalti is not configured. Please choose Cash at Hospital.')
            return redirect('payments:appointment_payment', appointment_id=appointment.id)

        return_url = request.build_absolute_uri(reverse('payments:khalti_return'))
        website_url = request.build_absolute_uri(reverse('index'))
        initiate_khalti_payload = {
            'return_url': return_url,
            'website_url': website_url,
            # Khalti expects amount in paisa.
            'amount': int(payment.amount * 100),
            'purchase_order_id': f'APPT-{appointment.id}-PAY-{payment.id}',
            'purchase_order_name': f'Appointment #{appointment.id} with Dr. {appointment.doctor.user.get_full_name() or appointment.doctor.user.username}',
            'customer_info': {
                'name': appointment.patient.user.get_full_name() or appointment.patient.user.username,
                'email': appointment.patient.user.email or '',
                'phone': appointment.patient.contact_number or '',
            },
        }

        headers = {
            'Authorization': f'key {secret_key}',
            'Content-Type': 'application/json',
        }

        try:
            response = requests.post(
                settings.PAYMENT_INITIATE_URL,
                json=initiate_khalti_payload,
                headers=headers,
                timeout=20,
            )
            response_data = response.json()
        except requests.RequestException:
            messages.error(request, 'Could not connect to Khalti. Please try again.')
            return redirect('payments:appointment_payment', appointment_id=appointment.id)
        except ValueError:
            messages.error(request, 'Invalid response from Khalti. Please try again.')
            return redirect('payments:appointment_payment', appointment_id=appointment.id)

        if not response.ok:
            messages.error(request, f'Failed to initiate Khalti payment: {response_data}')
            return redirect('payments:appointment_payment', appointment_id=appointment.id)

        payment_url = response_data.get('payment_url')
        pidx = response_data.get('pidx')
        if not payment_url:
            messages.error(request, 'Payment URL not found in Khalti response.')
            return redirect('payments:appointment_payment', appointment_id=appointment.id)

        payment.payment_method = AppointmentPayment.PaymentMethod.ONLINE
        payment.status = AppointmentPayment.PaymentStatus.PENDING
        payment.transaction_reference = pidx
        payment.save(update_fields=['payment_method', 'status', 'transaction_reference', 'modified'])
        return redirect(payment_url)

    def post(self, request, *args, **kwargs):
        appointment = self.get_appointment()
        if not self._has_permission(appointment):
            raise PermissionDenied("You don't have permission to access this payment.")

        payment = self.get_payment(appointment)
        selected_method = (request.POST.get('payment_option') or '').strip().lower()

        if selected_method == 'cash':
            payment.payment_method = AppointmentPayment.PaymentMethod.CASH
            if payment.status != AppointmentPayment.PaymentStatus.PAID:
                payment.status = AppointmentPayment.PaymentStatus.PENDING
            payment.transaction_reference = ''
            payment.save(update_fields=['payment_method', 'status', 'transaction_reference', 'modified'])
            messages.success(request, 'Cash at Hospital selected. Please pay at hospital during your visit.')
            return redirect('appointments:booking_confirmation')

        if selected_method == 'khalti':
            return self._initiate_khalti(request, appointment, payment)

        messages.error(request, 'Please choose a payment option.')
        return redirect('payments:appointment_payment', appointment_id=appointment.id)


class KhaltiReturnView(LoginRequiredMixin, View):
    """Handle Khalti return callback and verify payment status."""

    def get(self, request, *args, **kwargs):
        pidx = (request.GET.get('pidx') or '').strip()
        if not pidx:
            messages.error(request, 'Missing Khalti payment identifier.')
            return redirect('appointments:booking_confirmation')

        payment = AppointmentPayment.objects.select_related('appointment__patient__user').filter(
            transaction_reference=pidx,
            payment_method=AppointmentPayment.PaymentMethod.ONLINE,
        ).first()

        if not payment:
            messages.error(request, 'Payment record not found for this Khalti transaction.')
            return redirect('appointments:booking_confirmation')

        if not request.user.is_patient or payment.appointment.patient.user_id != request.user.id:
            raise PermissionDenied("You don't have permission to access this payment.")

        secret_key = getattr(settings, 'KHALTI_SECRET_KEY', '').strip()
        lookup_url = f"{settings.SANDBOX_KHALTI_URL}epayment/lookup/"
        headers = {
            'Authorization': f'key {secret_key}',
            'Content-Type': 'application/json',
        }

        try:
            verify_response = requests.post(
                lookup_url,
                json={'pidx': pidx},
                headers=headers,
                timeout=20,
            )
            verify_data = verify_response.json()
        except requests.RequestException:
            messages.error(request, 'Could not verify Khalti payment. Please try again.')
            return redirect('payments:appointment_payment', appointment_id=payment.appointment_id)
        except ValueError:
            messages.error(request, 'Invalid Khalti verification response.')
            return redirect('payments:appointment_payment', appointment_id=payment.appointment_id)

        if verify_response.ok and verify_data.get('status') == 'Completed':
            transaction_id = verify_data.get('transaction_id') or verify_data.get('idx') or pidx
            payment.mark_paid(
                payment_method=AppointmentPayment.PaymentMethod.ONLINE,
                transaction_reference=transaction_id,
            )
            messages.success(request, 'Khalti payment successful. Your appointment is now paid.')
            return redirect('appointments:booking_confirmation')

        payment.status = AppointmentPayment.PaymentStatus.FAILED
        payment.save(update_fields=['status', 'modified'])
        messages.error(request, 'Khalti payment was not completed. Please try again or choose Cash at Hospital.')
        return redirect('payments:appointment_payment', appointment_id=payment.appointment_id)

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
