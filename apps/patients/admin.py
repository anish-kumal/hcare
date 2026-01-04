from django.contrib import admin

from .models import Patient, PatientAppointment


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
	list_display = ('user', 'booking_uuid', 'gender', 'blood_group')
	list_filter = ('gender', 'blood_group')
	search_fields = ('booking_uuid', 'user__username', 'user__email', 'user__first_name', 'user__last_name', 'contact_number')
	exclude = ('is_verified', 'verified_at')


@admin.register(PatientAppointment)
class PatientAppointmentAdmin(admin.ModelAdmin):
	list_display = ('patient', 'doctor', 'appointment_date', 'appointment_time', 'status')
	list_filter = ('status', 'appointment_date')
	search_fields = ('patient__user__username', 'patient__user__email', 'doctor__user__username')
