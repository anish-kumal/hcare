from django.urls import path

from .views import AppointmentPaymentView, PaymentListView, PaymentDetailView, PaymentUpdateView

app_name = 'payments'

urlpatterns = [
    path('appointment/<int:appointment_id>/', AppointmentPaymentView.as_view(), name='appointment_payment'),
    path('manage/', PaymentListView.as_view(), name='payment_list'),
    path('manage/<int:pk>/', PaymentDetailView.as_view(), name='payment_detail'),
    path('manage/<int:pk>/edit/', PaymentUpdateView.as_view(), name='payment_edit'),
]
