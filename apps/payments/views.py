from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.views.generic import UpdateView, ListView, DetailView

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
