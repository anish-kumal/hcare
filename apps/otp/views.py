from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.urls import reverse
from urllib.parse import urlencode

from apps.users.models import User
from .services import OTPService


class OTPRequestView(View):
    """
    Class-based view for requesting OTP.
    Sends OTP via email to the user.
    """
    
    template_name = 'otp/request_otp.html'

    @staticmethod
    def get_login_url_name(source):
        return 'users:administer_login' if source == 'administer' else 'users:login'

    def get_source(self, request):
        source = request.POST.get('source') or request.GET.get('source')
        return 'administer' if source == 'administer' else 'patient'

    def build_url_with_source(self, url_name, source, **kwargs):
        url = reverse(url_name, kwargs=kwargs or None)
        return f"{url}?{urlencode({'source': source})}"
    
    def get(self, request):
        """Display OTP request form"""
        source = self.get_source(request)
        context = {
            'source': source,
            'login_back_url': reverse(self.get_login_url_name(source)),
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        """Handle OTP request"""
        source = self.get_source(request)
        email = request.POST.get('email', '').strip()

        context = {
            'source': source,
            'login_back_url': reverse(self.get_login_url_name(source)),
        }
        
        if not email:
            messages.error(request, "Please enter a valid email address.")
            return render(request, self.template_name, context)
        
        try:
            user = User.objects.get(email=email)
            otp = OTPService.create_and_send(user)
            
            if otp:
                messages.success(
                    request,
                    f"OTP sent to {email}. Please check your inbox."
                )
                return redirect(self.build_url_with_source('otp:verify', source, user_id=user.id))
            else:
                messages.error(
                    request,
                    "Failed to send OTP. Please try again."
                )
                
        except User.DoesNotExist:
            messages.success(request, f"OTP sent to {email}. Please check your inbox.")
            return redirect(self.build_url_with_source('otp:verify_generic', source))
        
        return render(request, self.template_name, context)


class OTPVerifyView(View):
    """
    Class-based view for verifying OTP.
    Validates the OTP code entered by the user.
    """
    
    template_name = 'otp/verify_otp.html'

    @staticmethod
    def get_login_url_name(source):
        return 'users:administer_login' if source == 'administer' else 'users:login'

    def get_source(self, request):
        source = request.POST.get('source') or request.GET.get('source')
        return 'administer' if source == 'administer' else 'patient'

    def build_url_with_source(self, url_name, source, **kwargs):
        url = reverse(url_name, kwargs=kwargs or None)
        return f"{url}?{urlencode({'source': source})}"
    
    def get(self, request, user_id=None):
        """Display OTP verification form"""
        source = self.get_source(request)
        context = {
            'user_id': user_id,
            'source': source,
            'login_back_url': reverse(self.get_login_url_name(source)),
        }
        return render(request, self.template_name, context)
    
    def post(self, request, user_id=None):
        """Handle OTP verification"""
        source = self.get_source(request)
        otp_code = request.POST.get('otp_code', '').strip()

        context = {
            'user_id': user_id,
            'source': source,
            'login_back_url': reverse(self.get_login_url_name(source)),
        }
        
        if not user_id or not otp_code:
            messages.error(request, "OTP code is required.")
            return render(request, self.template_name, context)
        
        try:
            user = User.objects.get(id=user_id)
            success, message = OTPService.verify_code(user, otp_code)
            
            if success:
                messages.success(request, "OTP verified successfully!")
                return redirect(self.build_url_with_source('otp:password_reset', source, user_id=user_id))
            else:
                messages.error(request, message)
                
        except User.DoesNotExist:
            messages.error(request, "User not found.")
        
        return render(request, self.template_name, context)


class OTPResendView(View):
    """
    Class-based view for resending OTP.
    """

    def post(self, request, user_id=None):
        """Handle OTP resend"""
        source = request.POST.get('source') or request.GET.get('source')
        source = 'administer' if source == 'administer' else 'patient'

        def build_url_with_source(url_name, **kwargs):
            url = reverse(url_name, kwargs=kwargs or None)
            return f"{url}?{urlencode({'source': source})}"

        if not user_id:
            messages.success(request, "New OTP sent to your email.")
            return redirect(build_url_with_source('otp:verify_generic'))

        try:
            user = User.objects.get(id=user_id)
            otp = OTPService.resend_otp(user)

            if otp:
                messages.success(request, "New OTP sent to your email.")
            else:
                messages.error(request, "Failed to send OTP.")

        except User.DoesNotExist:
            messages.success(request, "New OTP sent to your email.")
            return redirect(build_url_with_source('otp:verify_generic'))

        return redirect(build_url_with_source('otp:verify', user_id=user_id))


class PasswordResetView(View):
    """
    Class-based view for password reset after OTP verification
    """
    template_name = 'otp/password_reset.html'

    @staticmethod
    def get_login_url_name(source):
        return 'users:administer_login' if source == 'administer' else 'users:login'

    def get_source(self, request):
        source = request.POST.get('source') or request.GET.get('source')
        return 'administer' if source == 'administer' else 'patient'
    
    def get(self, request, user_id=None):
        """Display password reset form"""
        source = self.get_source(request)
        context = {
            'user_id': user_id,
            'source': source,
            'login_back_url': reverse(self.get_login_url_name(source)),
        }
        return render(request, self.template_name, context)
    
    def post(self, request, user_id=None):
        """Handle password reset"""
        source = self.get_source(request)
        password1 = request.POST.get('password1', '').strip()
        password2 = request.POST.get('password2', '').strip()

        context = {
            'user_id': user_id,
            'source': source,
            'login_back_url': reverse(self.get_login_url_name(source)),
        }
        
        if not password1 or not password2:
            messages.error(request, "Both password fields are required.")
            return render(request, self.template_name, context)
        
        if password1 != password2:
            messages.error(request, "Passwords do not match.")
            return render(request, self.template_name, context)
        
        if len(password1) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
            return render(request, self.template_name, context)
        
        try:
            user = User.objects.get(id=user_id)
            user.set_password(password1)
            user.save()
            messages.success(request, "Password reset successfully! Please log in with your new password.")
            return redirect(self.get_login_url_name(source))
        except User.DoesNotExist:
            messages.error(request, "User not found.")
            return redirect(self.get_login_url_name(source))

