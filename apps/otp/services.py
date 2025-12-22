import secrets
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string

from .models import OTP


class OTPService:
    """
    Service class for OTP operations.
    Handles OTP generation, sending, and verification.
    """
    
    OTP_LENGTH = 6
    OTP_VALIDITY_MINUTES = 5
    MAX_ATTEMPTS = 5
    
    @staticmethod
    def generate_code():
        """
        Generate a secure 6-digit OTP code.
        
        Returns:
            str: 6-digit OTP code
        """
        return ''.join(secrets.choice('0123456789') for _ in range(OTPService.OTP_LENGTH))
    
    @staticmethod
    def calculate_expiry():
        """
        Calculate OTP expiration time.
        
        Returns:
            datetime: Expiration datetime (5 minutes from now)
        """
        return timezone.now() + timedelta(minutes=OTPService.OTP_VALIDITY_MINUTES)
    
    @classmethod
    def create_or_update(cls, user):
        """
        Generate a new OTP or update existing one for a user.
        
        Args:
            user: User instance
            
        Returns:
            OTP: OTP instance
        """
        code = cls.generate_code()
        expires_at = cls.calculate_expiry()
        
        otp, created = OTP.objects.update_or_create(
            user=user,
            defaults={
                'code': code,
                'expires_at': expires_at,
                'verified': False,
                'verified_at': None,
                'attempts': 0
            }
        )
        
        return otp
    
    @staticmethod
    def verify_code(user, code):
        """
        Verify OTP code for a user.
        
        Args:
            user: User instance
            code (str): OTP code to verify
            
        Returns:
            tuple: (bool, str) - Success status and message
        """
        try:
            otp = OTP.objects.get(user=user)
        except OTP.DoesNotExist:
            return False, "No OTP found for this user."
        
        # Check if already verified
        if otp.verified:
            return False, "OTP already verified."
        
        # Check if expired
        if otp.is_expired:
            return False, "OTP has expired."
        
        # Check attempts
        if otp.attempts >= OTPService.MAX_ATTEMPTS:
            return False, "Maximum attempts exceeded. Please request a new OTP."
        
        # Verify code
        if otp.code == code:
            otp.verify()
            return True, "OTP verified successfully."
        
        otp.increment_attempts()
        remaining = OTPService.MAX_ATTEMPTS - otp.attempts
        return False, f"Invalid OTP. {remaining} attempts remaining."
    
    @staticmethod
    def send_otp_email(user, otp_code):
        """
        Send OTP via email to the user.
        
        Args:
            user: User instance
            otp_code (str): OTP code to send
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            subject = "Your OTP for Healthcare System Verification"
            
            context = {
                'user_name': user.get_full_name() or user.username,
                'otp_code': otp_code,
                'validity_minutes': OTPService.OTP_VALIDITY_MINUTES,
                'support_email': settings.DEFAULT_FROM_EMAIL,
            }
            
            # Try to use HTML email template
            try:
                html_message = render_to_string(
                    'otp/otp_email.html',
                    context
                )
            except Exception:
                # Fallback to plain text if template not found
                html_message = None
            
            message = f"""
            Hello {context['user_name']},
            
            Your OTP code is: {otp_code}
            
            This code will expire in {context['validity_minutes']} minutes.
            Do not share this code with anyone.
            
            If you did not request this code, please ignore this email.
            
            Best regards,
            Healthcare System Team
            """
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            return True
            
        except Exception as e:
            print(f"Error sending OTP email: {str(e)}")
            return False
    
    @classmethod
    def create_and_send(cls, user):
        """
        Create OTP and send it via email to the user.
        
        Args:
            user: User instance
            
        Returns:
            tuple: (OTP instance, bool) - OTP object and email sent status
        """
        otp = cls.create_or_update(user)
        email_sent = cls.send_otp_email(user, otp.code)
        return otp, email_sent
    
    @staticmethod
    def resend_otp(user):
        """
        Resend OTP to user (creates new OTP and sends it).
        
        Args:
            user: User instance
            
        Returns:
            tuple: (OTP instance, bool) - OTP object and email sent status
        """
        return OTPService.create_and_send(user)
    
    @staticmethod
    def delete_verified_otp(user):
        """
        Delete verified OTP for a user.
        
        Args:
            user: User instance
            
        Returns:
            bool: True if deleted, False otherwise
        """
        try:
            otp = OTP.objects.get(user=user, verified=True)
            otp.delete()
            return True
        except OTP.DoesNotExist:
            return False
