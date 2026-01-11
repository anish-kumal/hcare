from django.db import models
from django.conf import settings
from apps.base.models import BaseModel
from apps.doctors.models import Doctor, DoctorSchedule
from apps.patients.models import Patient


# Using PatientAppointment from apps.patients.models
# This module re-exports it for convenience
from apps.patients.models import PatientAppointment

__all__ = ['PatientAppointment']

