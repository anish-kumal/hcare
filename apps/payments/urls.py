from django.urls import path

from .views import (
    AppointmentPaymentView,
    PaymentListView,
    PaymentDetailView,
    PaymentUpdateView,
    PatientPaymentIndexView,
    PatientPaymentView,
    PatientPaymentStatusView,
    PatientPaymentProcessView,
)

app_name = 'payments'

urlpatterns = [
    path('appointment/<int:appointment_id>/', AppointmentPaymentView.as_view(), name='appointment_payment'),
    path('patient/status/<int:pk>/', PatientPaymentStatusView.as_view(), name='patient_payment_status'),
    path('patient/process/', PatientPaymentProcessView.as_view(), name='patient_payment_process'),
    path('patient/<int:appointment_id>/', PatientPaymentView.as_view(), name='patient_payment_list_for_appointment'),
    path('patient/<int:appointment_id>', PatientPaymentView.as_view(), name='patient_payment_list_for_appointment_no_slash'),
    path('patient/', PatientPaymentIndexView.as_view(), name='patient_payment_list'),
    path('patient', PatientPaymentIndexView.as_view(), name='patient_payment_list_no_slash'),
    path('manage/', PaymentListView.as_view(), name='payment_list'),
    path('manage/<int:pk>/', PaymentDetailView.as_view(), name='payment_detail'),
    path('manage/<int:pk>/edit/', PaymentUpdateView.as_view(), name='payment_edit'),
]
