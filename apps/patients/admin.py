from django.contrib import admin

from .models import Patient, PatientAppointment


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
	list_display = ('user', 'gender', 'blood_group', 'is_verified')
	list_filter = ('gender', 'blood_group', 'is_verified')
	search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name', 'contact_number')


@admin.register(PatientAppointment)
class PatientAppointmentAdmin(admin.ModelAdmin):
	list_display = ('patient', 'doctor', 'appointment_date', 'appointment_time', 'status')
	list_filter = ('status', 'appointment_date')
	search_fields = ('patient__user__username', 'patient__user__email', 'doctor__user__username')
