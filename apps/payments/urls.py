from django.urls import path

from .views import AppointmentPaymentView

app_name = 'payments'

urlpatterns = [
    path('appointment/<int:appointment_id>/', AppointmentPaymentView.as_view(), name='appointment_payment'),
]
