from django.urls import path
from .views import (
    OTPRequestView,
    OTPVerifyView,
    OTPResendView,
    PasswordResetView
)

app_name = 'otp'

urlpatterns = [
    path('request/', OTPRequestView.as_view(), name='request'),
    path('verify/', OTPVerifyView.as_view(), name='verify_generic'),
    path('verify/<int:user_id>/', OTPVerifyView.as_view(), name='verify'),
    path('resend/', OTPResendView.as_view(), name='resend_generic'),
    path('resend/<int:user_id>/', OTPResendView.as_view(), name='resend'),
    path('password-reset/<int:user_id>/', PasswordResetView.as_view(), name='password_reset'),
]
