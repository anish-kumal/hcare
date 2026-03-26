from datetime import datetime, timedelta

from django.apps import apps
from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.base.models import BaseModel
from apps.hospitals.models import Hospital, HospitalDepartment


class Doctor(BaseModel):
    """
    Doctor profile model
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='doctor_profile',
        limit_choices_to={'user_type': 'DOCTOR'},
        help_text="User account for this doctor"
    )
    
    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.PROTECT,
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

    def get_available_slots_by_date(self, days=7, now=None, active_statuses=None):
        """Return available appointment slots grouped by date for next N days."""
        if days <= 0:
            return []

        now = timezone.localtime(now or timezone.now())
        today = now.date()

        schedules = self.schedules.filter(
            is_available=True,
        ).order_by('weekday', 'start_time')

        schedules_by_weekday = {}
        for schedule in schedules:
            schedules_by_weekday.setdefault(schedule.weekday, []).append(schedule)

        available_slots = []
        for offset in range(days):
            appointment_date = today + timedelta(days=offset)
            day_schedules = schedules_by_weekday.get(appointment_date.weekday(), [])
            if not day_schedules:
                continue

            day_slots = []
            for schedule in day_schedules:
                day_slots.extend(
                    schedule.get_available_slots(
                        appointment_date=appointment_date,
                        now=now,
                        active_statuses=active_statuses,
                    )
                )

            if day_slots:
                available_slots.append({
                    'date': appointment_date,
                    'weekday': appointment_date.strftime('%A'),
                    'slots': sorted(day_slots, key=lambda slot: slot['time']),
                })

        return available_slots


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

    time_slots = models.JSONField(
        default=list,
        blank=True,
        help_text="Auto-calculated appointment time slots"
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

    def _calculate_time_slots(self):
        if not self.start_time or not self.end_time or self.slot_duration <= 0:
            return []

        # Only same-day slots are supported; invalid ranges produce no slots.
        start_dt = datetime.combine(datetime.today(), self.start_time)
        end_dt = datetime.combine(datetime.today(), self.end_time)
        if end_dt <= start_dt:
            return []

        slots = []
        current_dt = start_dt
        step = timedelta(minutes=self.slot_duration)

        while current_dt < end_dt:
            hour_24 = current_dt.hour
            hour_12 = hour_24 % 12 or 12
            meridiem = 'AM' if hour_24 < 12 else 'PM'
            slots.append(f"{hour_12}:{current_dt.minute:02d} {meridiem}")
            current_dt += step

        return slots

    def get_slot_times(self):
        """Return schedule slots as list of time objects."""
        slot_labels = self.time_slots or self._calculate_time_slots()
        return [datetime.strptime(slot_label, '%I:%M %p').time() for slot_label in slot_labels]

    def get_available_slots(self, appointment_date, now=None, active_statuses=None):
        """Return future slots that are not already booked for a specific date."""
        if not self.is_available:
            return []

        now = timezone.localtime(now or timezone.now())
        active_statuses = active_statuses or ['SCHEDULED', 'FOLLOW_UP']
        patient_appointment_model = apps.get_model('patients', 'PatientAppointment')
        current_tz = timezone.get_current_timezone()

        available_slots = []
        for slot_time in self.get_slot_times():
            if appointment_date == now.date() and slot_time <= now.time():
                continue

            slot_dt = timezone.make_aware(datetime.combine(appointment_date, slot_time), current_tz)
            if slot_dt <= now:
                continue

            existing_appointments = patient_appointment_model.objects.filter(
                doctor=self.doctor,
                appointment_date=appointment_date,
                appointment_time=slot_time,
                status__in=active_statuses,
            ).count()

            # If the slot already has a booking, hide it from availability.
            if existing_appointments > 0:
                continue

            if existing_appointments < self.max_patients:
                available_slots.append({
                    'time': slot_time,
                    'datetime': slot_dt,
                })

        return available_slots

    def save(self, *args, **kwargs):
        self.time_slots = self._calculate_time_slots()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.doctor} - {self.get_weekday_display()} {self.start_time}-{self.end_time}"
