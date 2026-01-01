from django.db import models
from django.conf import settings
from apps.base.models import BaseModel
from apps.hospitals.models import Hospital, HospitalDepartment


class Doctor(BaseModel):
    """
    Doctor profile model
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='doctor_profile',
        limit_choices_to={'user_type': 'DOCTOR'},
        help_text="User account for this doctor"
    )
    
    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.CASCADE,
        related_name='doctors',
        help_text="Primary hospital"
    )
    
    department = models.ForeignKey(
        HospitalDepartment,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='doctors',
        help_text="Department"
    )
    
    specialization = models.CharField(
        max_length=100,
        help_text="Primary specialization (e.g., Cardiology, Pediatrics)"
    )
    
    license_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Medical license number"
    )
    
    employee_id = models.CharField(
        max_length=50,
        unique=True,
        help_text="Employee ID"
    )
    
    qualification = models.CharField(
        max_length=200,
        help_text="Medical qualifications (e.g., MBBS, MD)"
    )
    
    experience_years = models.PositiveIntegerField(
        default=0,
        help_text="Years of experience"
    )
    
    bio = models.TextField(
        blank=True,
        null=True,
        help_text="Doctor's biography"
    )
    
    consultation_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Consultation fee"
    )
    
    profile_picture = models.ImageField(
        upload_to='doctors/profiles/',
        blank=True,
        null=True,
        help_text="Profile picture"
    )
    
    is_available = models.BooleanField(
        default=True,
        help_text="Currently accepting appointments"
    )
    
    joining_date = models.DateField(
        help_text="Date joined hospital"
    )
    
    class Meta:
        verbose_name = 'Doctor'
        verbose_name_plural = 'Doctors'
        ordering = ['user__first_name']
        indexes = [
            models.Index(fields=['hospital', 'specialization']),
            models.Index(fields=['is_available']),
        ]
    
    def __str__(self):
        return f"Dr. {self.user.get_full_name()} - {self.specialization}"


class DoctorSchedule(BaseModel):
    """
    Doctor's availability schedule
    """
    WEEKDAY_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name='schedules',
        help_text="Doctor"
    )
    
    weekday = models.IntegerField(
        choices=WEEKDAY_CHOICES,
        help_text="Day of week"
    )
    
    start_time = models.TimeField(
        help_text="Start time"
    )
    
    end_time = models.TimeField(
        help_text="End time"
    )
    
    slot_duration = models.IntegerField(
        default=30,
        help_text="Appointment slot duration in minutes"
    )
    
    max_patients = models.IntegerField(
        default=20,
        help_text="Maximum patients per session"
    )
    
    is_available = models.BooleanField(
        default=True,
        help_text="Is schedule active"
    )
    
    class Meta:
        verbose_name = 'Doctor Schedule'
        verbose_name_plural = 'Doctor Schedules'
        ordering = ['weekday', 'start_time']
        unique_together = ['doctor', 'weekday', 'start_time']
    
    def __str__(self):
        return f"{self.doctor} - {self.get_weekday_display()} {self.start_time}-{self.end_time}"
