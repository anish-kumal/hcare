from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import UpdateView

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
