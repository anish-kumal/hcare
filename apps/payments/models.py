from django.db import models
from django.utils import timezone

from apps.base.models import BaseModel
from apps.patients.models import PatientAppointment
from auditlog.registry import auditlog


class AppointmentPayment(BaseModel):
    class PaymentStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PAID = 'PAID', 'Paid'
        FAILED = 'FAILED', 'Failed'
        REFUNDED = 'REFUNDED', 'Refunded'

    class PaymentMethod(models.TextChoices):
        CASH = 'CASH', 'Cash'
        CARD = 'CARD', 'Card'
        ONLINE = 'ONLINE', 'Online'

    appointment = models.OneToOneField(
        PatientAppointment,
        on_delete=models.PROTECT,
        related_name='payment',
        help_text='Appointment linked to this payment',
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text='Amount to collect')
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        help_text='Payment status',
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH,
        help_text='Payment mode used by patient',
    )
    transaction_reference = models.CharField(max_length=100, blank=True, null=True)
    paid_at = models.DateTimeField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = 'Appointment Payment'
        verbose_name_plural = 'Appointment Payments'
        ordering = ['-created']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['payment_method']),
        ]

    def mark_paid(self, payment_method=None, transaction_reference=None):
        self.status = self.PaymentStatus.PAID
        if payment_method:
            self.payment_method = payment_method
        if transaction_reference:
            self.transaction_reference = transaction_reference
        self.paid_at = timezone.now()
        self.save(update_fields=['status', 'payment_method', 'transaction_reference', 'paid_at', 'modified'])

    def __str__(self):
        return f'Payment for Appointment #{self.appointment_id} - {self.status}'


# Register model for audit logging
auditlog.register(AppointmentPayment)
