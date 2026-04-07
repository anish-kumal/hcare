from django.urls import path

from .views import (
    AppointmentPaymentView,
    PaymentListView,
    PaymentDetailView,
    PaymentUpdateView,
    PatientPaymentListView,
    PatientPaymentStatusView,
    PatientPaymentProcessView,
)

app_name = 'payments'

urlpatterns = [
    path('appointment/<int:appointment_id>/', AppointmentPaymentView.as_view(), name='appointment_payment'),
    path('patient', PatientPaymentListView.as_view(), name='patient_payment_list_no_slash'),
    path('patient/', PatientPaymentListView.as_view(), name='patient_payment_list'),
    path('patient/status/<int:pk>/', PatientPaymentStatusView.as_view(), name='patient_payment_status'),
    path('patient/process/', PatientPaymentProcessView.as_view(), name='patient_payment_process'),
    path('manage/', PaymentListView.as_view(), name='payment_list'),
    path('manage/<int:pk>/', PaymentDetailView.as_view(), name='payment_detail'),
    path('manage/<int:pk>/edit/', PaymentUpdateView.as_view(), name='payment_edit'),
]
