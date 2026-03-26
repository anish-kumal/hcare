from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
import re
from apps.base.models import BaseModel


class CustomUserManager(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        if '@' in username:
            raise ValueError('Username cannot contain @.')
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields['user_type'] = User.UserType.SUPER_ADMIN
        extra_fields['is_default_password'] = False
        return super().create_superuser(username, email, password, **extra_fields)

class User(AbstractUser, BaseModel):
    """
    Custom User model with different user types for healthcare system
    """
    class UserType(models.TextChoices):
        SUPER_ADMIN = 'SUPER_ADMIN', 'Super Admin'
        ADMIN = 'ADMIN', 'Admin'
        DOCTOR = 'DOCTOR', 'Doctor'
        PATIENT = 'PATIENT', 'Patient'
        STAFF = 'STAFF', 'Staff'
        LAB_ASSISTANT = 'LAB_ASSISTANT', 'Lab Technician'
        PHARMACIST = 'PHARMACIST', 'Pharmacist'
    
    email = models.EmailField(unique=True, blank=False)
    
    user_type = models.CharField(
        max_length=20,
        choices=UserType.choices,
        default=UserType.PATIENT,
        help_text="Type of user in the healthcare system"
    )
    
    phone_number = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        help_text="Contact phone number"
    )
    
    date_of_birth = models.DateField(
        blank=True,
        null=True,
        help_text="Date of birth"
    )
    
    address = models.TextField(
        blank=True,
        null=True,
        help_text="Residential address"
    )

    is_default_password = models.BooleanField(
        default=True,
        help_text="Indicates whether the user is still using the default password"
    )


    objects = CustomUserManager()
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created']
    
    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"
    
    @property
    def is_super_admin(self):
        return self.user_type == self.UserType.SUPER_ADMIN
    
    @property
    def is_admin(self):
        return self.user_type == self.UserType.ADMIN
    
    @property
    def is_doctor(self):
        return self.user_type == self.UserType.DOCTOR
    
    @property
    def is_patient(self):
        return self.user_type == self.UserType.PATIENT
    
    @property
    def is_staff_member(self):
        return self.user_type == self.UserType.STAFF
    
    @property
    def is_lab_assistant(self):
        return self.user_type == self.UserType.LAB_ASSISTANT
    
    @property
    def is_pharmacist(self):
        return self.user_type == self.UserType.PHARMACIST
    
    def validate_password_strength(self, password):
        """
        Validates that password meets strong security requirements:
        - Minimum 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character
        """
        if not password:
            raise ValidationError("Password cannot be empty.")
        
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long.")
        
        if not re.search(r'[A-Z]', password):
            raise ValidationError("Password must contain at least one uppercase letter.")
        
        if not re.search(r'[a-z]', password):
            raise ValidationError("Password must contain at least one lowercase letter.")
        
        if not re.search(r'[0-9]', password):
            raise ValidationError("Password must contain at least one digit.")
        
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'",.<>?/\\|`~]', password):
            raise ValidationError("Password must contain at least one special character (!@#$%^&*()_+-=[]{};:'\",.<>?/\\|`~).")
    
    def clean(self):
        """Validates the user instance before saving"""
        super().clean()
        # Validate password if it has been changed
        if self.pk is None and hasattr(self, '_password'):
            # New user with password
            self.validate_password_strength(self._password)
    
    def save(self, *args, **kwargs):
        """Saves the user instance with validation"""
        # Validate password strength before saving
        if self.pk is None and hasattr(self, '_password'):
            self.validate_password_strength(self._password)
        
        super().save(*args, **kwargs)
