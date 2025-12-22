from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages

from apps.users.models import User
from .services import OTPService


class OTPRequestView(View):
    """
    Class-based view for requesting OTP.
    Sends OTP via email to the user.
    """
    
    template_name = 'otp/request_otp.html'
    
    def get(self, request):
        """Display OTP request form"""
        return render(request, self.template_name)
    
    def post(self, request):
        """Handle OTP request"""
        email = request.POST.get('email', '').strip()
        
        if not email:
            messages.error(request, "Please enter a valid email address.")
            return render(request, self.template_name)
        
        try:
            user = User.objects.get(email=email)
            otp = OTPService.create_and_send(user)
            
            if otp:
                messages.success(
                    request,
                    f"OTP sent to {email}. Please check your inbox."
                )
                return redirect('otp:verify', user_id=user.id)
            else:
                messages.error(
                    request,
                    "Failed to send OTP. Please try again."
                )
                
        except User.DoesNotExist:
            messages.error(request, "Email not found in our system.")
        
        return render(request, self.template_name)


class OTPVerifyView(View):
    """
    Class-based view for verifying OTP.
    Validates the OTP code entered by the user.
    """
    
    template_name = 'otp/verify_otp.html'
    
    def get(self, request, user_id=None):
        """Display OTP verification form"""
        context = {'user_id': user_id}
        return render(request, self.template_name, context)
    
    def post(self, request, user_id=None):
        """Handle OTP verification"""
        otp_code = request.POST.get('otp_code', '').strip()
        
        if not user_id or not otp_code:
            messages.error(request, "OTP code is required.")
            return render(request, self.template_name, {'user_id': user_id})
        
        try:
            user = User.objects.get(id=user_id)
            success, message = OTPService.verify_code(user, otp_code)
            
            if success:
                messages.success(request, "OTP verified successfully!")
                return redirect('users:password_reset', user_id=user_id)
            else:
                messages.error(request, message)
                
        except User.DoesNotExist:
            messages.error(request, "User not found.")
        
        context = {'user_id': user_id}
        return render(request, self.template_name, context)


class OTPResendView(View):
    """
    Class-based view for resending OTP.
    """
    
    def post(self, request, user_id=None):
        """Handle OTP resend"""
        if not user_id:
            messages.error(request, "Invalid request.")
            return redirect('otp:request')
        
        try:
            user = User.objects.get(id=user_id)
            otp = OTPService.resend_otp(user)
            
            if otp:
                messages.success(request, "New OTP sent to your email.")
            else:
                messages.error(request, "Failed to send OTP.")
                
        except User.DoesNotExist:
            messages.error(request, "User not found.")
        
        return redirect('otp:verify', user_id=user_id)

