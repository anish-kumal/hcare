from django.db import models
from django.conf import settings
from apps.base.models import BaseModel

class Hospital(BaseModel):
    """
    Hospital model representing healthcare facilities in the system
    """
    name = models.CharField(
        max_length=200,
        help_text="Hospital name"
    )
    
    registration_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Hospital registration/license number"
    )
    
    email = models.EmailField(
        unique=True,
        help_text="Hospital contact email"
    )
    
    phone_number = models.CharField(
        max_length=15,
        help_text="Hospital contact phone"
    )
    
    address = models.TextField(
        help_text="Hospital physical address"
    )
    
    city = models.CharField(
        max_length=100,
        help_text="City where hospital is located"
    )
    
    state = models.CharField(
        max_length=100,
        help_text="State/Province"
    )
    
    country = models.CharField(
        max_length=100,
        default="Nepal",
        help_text="Country"
    )
    
    postal_code = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text="Postal/ZIP code"
    )
    
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Hospital description and facilities"
    )
    
    logo = models.ImageField(
        upload_to='hospitals/logos/',
        blank=True,
        null=True,
        help_text="Hospital logo"
    )
    
    website = models.URLField(
        blank=True,
        null=True,
        help_text="Hospital website URL"
    )
    
    established_date = models.DateField(
        blank=True,
        null=True,
        help_text="Date when hospital was established"
    )
    
    total_beds = models.PositiveIntegerField(
        default=0,
        help_text="Total number of beds"
    )
    
    emergency_contact = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        help_text="Emergency contact number"
    )
    
    is_verified = models.BooleanField(
        default=False,
        help_text="Whether hospital is verified by super admin"
    )
    
    verified_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Date and time when hospital was verified"
    )
    
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='verified_hospitals',
        help_text="Super admin who verified this hospital"
    )
    
    class Meta:
        verbose_name = 'Hospital'
        verbose_name_plural = 'Hospitals'
        ordering = ['name']
        indexes = [
            models.Index(fields=['city', 'state']),
            models.Index(fields=['is_verified', 'is_active']),
        ]
    
    def __str__(self):
        return self.name


class HospitalDepartment(BaseModel):
    """
    Hospital Department model - represents departments within a hospital
    """
    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.CASCADE,
        related_name='departments',
        help_text="Hospital this department belongs to"
    )
    
    name = models.CharField(
        max_length=100,
        help_text="Department name (e.g., Cardiology, Orthopedics)"
    )
    
    code = models.CharField(
        max_length=20,
        help_text="Department code"
    )
    
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Department description"
    )
    
    head_doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='headed_departments',
        help_text="Head doctor of this department"
    )
    
    total_beds = models.PositiveIntegerField(
        default=0,
        help_text="Total beds in this department"
    )
    
    available_beds = models.PositiveIntegerField(
        default=0,
        help_text="Currently available beds"
    )
    
    class Meta:
        verbose_name = 'Hospital Department'
        verbose_name_plural = 'Hospital Departments'
        ordering = ['hospital', 'name']
        unique_together = [['hospital', 'code']]
    
    def __str__(self):
        return f"{self.name} - {self.hospital.name}"


class HospitalAdmin(BaseModel):
    """
    Hospital Admin model - manages a specific hospital
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='hospital_admin_profile',
        limit_choices_to={'user_type': 'ADMIN'},
        help_text="User account for this admin"
    )
    
    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.CASCADE,
        related_name='admins',
        help_text="Hospital managed by this admin"
    )
    
    class Meta:
        verbose_name = 'Hospital Admin'
        verbose_name_plural = 'Hospital Admins'
        ordering = ['-created']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.hospital.name}"
    

class HospitalStaff(BaseModel):
    """
    Hospital Staff model - represents staff members working in a hospital
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='hospital_staff_profile',
        limit_choices_to={
            'user_type__in': ['STAFF', 'LAB_ASSISTANT', 'PHARMACIST']
        },
        help_text="User account for this staff member"
    )
    
    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.CASCADE,
        related_name='staff',
        help_text="Hospital where this staff member works"
    )
    
    class Meta:
        verbose_name = 'Hospital Staff'
        verbose_name_plural = 'Hospital Staff'
        ordering = ['-created']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.hospital.name}"
