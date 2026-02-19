from django.contrib import admin

from .models import Doctor, DoctorSchedule



@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
	list_display = ('user', 'hospital', 'specialization', 'is_available', 'joining_date')
	list_filter = ('hospital', 'specialization', 'is_available', 'joining_date')
	search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name', 'license_number')


@admin.register(DoctorSchedule)
class DoctorScheduleAdmin(admin.ModelAdmin):
	list_display = ('doctor', 'weekday', 'start_time', 'end_time', 'slot_duration', 'is_available', 'time_slots')
	list_filter = ('weekday', 'is_available')
	search_fields = ('doctor__user__username', 'doctor__user__email')
	readonly_fields = ('time_slots',)
