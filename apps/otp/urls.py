from django.urls import path
from .views import (
    OTPRequestView,
    OTPVerifyView,
    OTPResendView,
)

app_name = 'otp'

urlpatterns = [
    path('request/', OTPRequestView.as_view(), name='request'),
    path('verify/<int:user_id>/', OTPVerifyView.as_view(), name='verify'),
    path('resend/<int:user_id>/', OTPResendView.as_view(), name='resend'),
]
