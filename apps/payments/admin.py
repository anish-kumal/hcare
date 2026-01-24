from django.contrib import admin

from .models import AppointmentPayment


@admin.register(AppointmentPayment)
class AppointmentPaymentAdmin(admin.ModelAdmin):
    list_display = (
        'appointment',
        'amount',
        'status',
        'payment_method',
        'transaction_reference',
        'paid_at',
    )
    list_filter = ('status', 'payment_method', 'created')
    search_fields = (
        'appointment__patient__user__username',
        'appointment__patient__user__email',
        'appointment__doctor__user__username',
        'transaction_reference',
    )
