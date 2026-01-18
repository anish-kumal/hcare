from django.db import models
from django.conf import settings
from django.utils.crypto import get_random_string
from apps.base.models import BaseModel
from apps.doctors.models import Doctor
from apps.hospitals.models import Hospital


def generate_booking_code(prefix='BK'):
    return f"{prefix}{get_random_string(10, allowed_chars='ABCDEFGHJKLMNPQRSTUVWXYZ23456789')}"


class Patient(BaseModel):
    """
    Patient profile model
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='patient_profile',
        limit_choices_to={'user_type': 'PATIENT'},
        help_text="User account for this patient"
    )

    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.SET_NULL,
        related_name='patients',
        blank=True,
        null=True,
        help_text="Hospital associated with this patient"
    )

    booking_uuid = models.CharField(
        max_length=20,
        unique=True,
        default=generate_booking_code,
        editable=False,
        help_text="Unique booking code for booking flow"
    )
    
    date_of_birth = models.DateField(
        help_text="Date of birth"
    )
    
    gender = models.CharField(
        max_length=10,
        choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')],
        help_text="Gender"
    )
    
    blood_group = models.CharField(
        max_length=5,
        choices=[
            ('O+', 'O+'),
            ('O-', 'O-'),
            ('A+', 'A+'),
            ('A-', 'A-'),
            ('B+', 'B+'),
            ('B-', 'B-'),
            ('AB+', 'AB+'),
            ('AB-', 'AB-'),
        ],
        blank=True,
        null=True,
        help_text="Blood group"
    )
    
    contact_number = models.CharField(
        max_length=15,
        help_text="Contact number"
    )
    
    emergency_contact = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        help_text="Emergency contact number"
    )
    
    emergency_contact_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Emergency contact person name"
    )
    
    address = models.TextField(
        help_text="Residential address"
    )
    
    city = models.CharField(
        max_length=100,
        help_text="City"
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
    
    medical_history = models.TextField(
        blank=True,
        null=True,
        help_text="Medical history and allergies"
    )
    
    insurance_provider = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Insurance provider name"
    )
    
    insurance_policy_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Insurance policy number"
    )
    
    profile_picture = models.ImageField(
        upload_to='patients/profiles/',
        blank=True,
        null=True,
        help_text="Profile picture"
    )
    
    is_verified = models.BooleanField(
        default=False,
        help_text="Email verified"
    )
    
    verified_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Verification timestamp"
    )
    
    class Meta:
        verbose_name = 'Patient'
        verbose_name_plural = 'Patients'
        ordering = ['user__first_name']
        indexes = [
            models.Index(fields=['is_verified']),
        ]
    
    def __str__(self):
        return f"{self.user.get_full_name()}"

    def save(self, *args, **kwargs):
        if not self.booking_uuid:
            # Retry to avoid extremely rare unique collisions.
            for _ in range(10):
                candidate = generate_booking_code()
                if not self.__class__.objects.filter(booking_uuid=candidate).exists():
                    self.booking_uuid = candidate
                    break
            if not self.booking_uuid:
                raise ValueError("Could not generate a unique booking code")
        super().save(*args, **kwargs)


class PatientAppointment(BaseModel):
    """
    Patient appointment with doctor
    """
    STATUS_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('RESCHEDULED', 'Rescheduled'),
        ('CONFIRMED', 'Confirmed'),
    ]
    
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='appointments',
        help_text="Patient"
    )
    
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name='patient_appointments',
        help_text="Doctor"
    )
    
    appointment_date = models.DateField(
        help_text="Appointment date"
    )
    
    appointment_time = models.TimeField(
        help_text="Appointment time"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='SCHEDULED',
        help_text="Appointment status"
    )
    
    reason = models.TextField(
        blank=True,
        null=True,
        help_text="Reason for appointment"
    )
    
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Doctor notes"
    )
    
    cancelled_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Cancellation timestamp"
    )
    
    cancelled_reason = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Cancellation reason"
    )
    
    class Meta:
        verbose_name = 'Patient Appointment'
        verbose_name_plural = 'Patient Appointments'
        ordering = ['-appointment_date', '-appointment_time']
        indexes = [
            models.Index(fields=['patient', 'doctor', 'appointment_date']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.patient} - {self.doctor} - {self.appointment_date}"
