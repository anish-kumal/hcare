from django.contrib import admin
from .models import Prescription, Medicine

# The PatientAppointment model is already registered in the patients app
# This module is kept for organizational purposes


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
	list_display = ('id', 'appointment', 'created_by', 'created')
	search_fields = (
		'appointment__patient__user__first_name',
		'appointment__patient__user__last_name',
		'appointment__doctor__user__first_name',
		'appointment__doctor__user__last_name',
		'diagnosis',
	)
	list_filter = ('created',)
	autocomplete_fields = ('appointment', 'created_by')


@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
	list_display = ('id', 'name', 'prescription', 'dosage', 'frequency', 'duration', 'created_by', 'created')
	search_fields = ('name', 'dosage', 'frequency', 'duration', 'prescription__appointment__patient__user__username')
	list_filter = ('created',)
	autocomplete_fields = ('prescription', 'created_by')

