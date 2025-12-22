from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.base.models import BaseModel


class OTP(BaseModel):
    """
    OTP Model for email verification and authentication.
    Stores OTP code with expiration time linked to users.
    """
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='otp',
        help_text="User associated with this OTP"
    )
    
    code = models.CharField(
        max_length=6,
        help_text="6-digit OTP code"
    )
    
    expires_at = models.DateTimeField(
        help_text="Expiration time for the OTP"
    )
    
    verified = models.BooleanField(
        default=False,
        help_text="Whether the OTP has been verified"
    )
    
    verified_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Timestamp when OTP was verified"
    )
    
    attempts = models.IntegerField(
        default=0,
        help_text="Number of verification attempts"
    )
    
    class Meta:
        verbose_name = 'One Time Password'
        verbose_name_plural = 'One Time Passwords'
        ordering = ['-created']
    
    def __str__(self):
        return f"OTP for {self.user.username} (Verified: {self.verified})"
    
    @property
    def is_expired(self):
        """Check if OTP has expired"""
        return timezone.now() > self.expires_at
    
    @property
    def is_valid(self):
        """Check if OTP is valid (not expired and not verified)"""
        return not self.is_expired and not self.verified
    
    def verify(self):
        """Mark OTP as verified"""
        if not self.is_expired:
            self.verified = True
            self.verified_at = timezone.now()
            self.save()
            return True
        return False
    
    def increment_attempts(self):
        """Increment verification attempts"""
        self.attempts += 1
        self.save()
