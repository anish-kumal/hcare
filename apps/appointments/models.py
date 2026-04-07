from django.db import models
from django.conf import settings
from apps.base.models import BaseModel
from apps.doctors.models import Doctor, DoctorSchedule
from apps.patients.models import Patient


# Using PatientAppointment from apps.patients.models
# This module re-exports it for convenience
from apps.patients.models import PatientAppointment


class Prescription(BaseModel):
	"""Doctor consultation log attached to one appointment."""

	appointment = models.OneToOneField(
		PatientAppointment,
		on_delete=models.CASCADE,
		related_name='prescription_record',
		help_text='Appointment linked to this prescription'
	)
	diagnosis = models.TextField(help_text='Diagnosis and clinical findings')
	notes = models.TextField(blank=True, null=True, help_text='Additional consultation notes')
	created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_prescriptions',
        help_text='User who created this prescription'
    )

	class Meta:
		ordering = ['-created']

	def __str__(self):
		return f"Prescription for appointment #{self.appointment_id}"


class Medicine(BaseModel):
	"""Medicine rows under a prescription."""

	prescription = models.ForeignKey(
		Prescription,
		on_delete=models.CASCADE,
		related_name='medicines',
		help_text='Prescription this medicine belongs to'
	)
	name = models.CharField(max_length=255)
	dosage = models.CharField(max_length=100, help_text='e.g. 500mg')
	frequency = models.CharField(max_length=100, help_text='e.g. 2 times a day')
	duration = models.CharField(max_length=100, help_text='e.g. 5 days')
	notes = models.TextField(blank=True, null=True, help_text='Additional notes for this medicine')
	created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_medicines',
        help_text='User who created this medicine entry'
    )

	class Meta:
		ordering = ['created']

	def __str__(self):
		return f"{self.name} ({self.dosage})"


__all__ = ['PatientAppointment', 'Prescription', 'Medicine']

