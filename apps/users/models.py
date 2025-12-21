from django.db import models
from django.contrib.auth.models import AbstractUser
from apps.base.models import BaseModel


class User(AbstractUser, BaseModel):
    """
    Custom User model with different user types for healthcare system
    """
    class UserType(models.TextChoices):
        SUPER_ADMIN = 'SUPER_ADMIN', 'Super Admin'
        DOCTOR = 'DOCTOR', 'Doctor'
        PATIENT = 'PATIENT', 'Patient'
        STAFF = 'STAFF', 'Staff'
        LAB_ASSISTANT = 'LAB_TECHNICIAN', 'Lab Technician'
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
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"
    
    @property
    def is_super_admin(self):
        return self.user_type == self.UserType.SUPER_ADMIN
    
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
        return self.user_type == self.UserType.LAB_TECHNICIAN
    
    @property
    def is_pharmacist(self):
        return self.user_type == self.UserType.PHARMACIST
