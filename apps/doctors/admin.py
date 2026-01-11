from django.contrib import admin

from .models import Doctor, DoctorSchedule, Specialization


@admin.register(Specialization)
class SpecializationAdmin(admin.ModelAdmin):
	list_display = ('name', 'code', 'created', 'modified')
	search_fields = ('name', 'code')


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
	list_display = ('user', 'hospital', 'specialization', 'is_available', 'is_verified', 'joining_date')
	list_filter = ('hospital', 'specialization', 'is_available', 'is_verified', 'joining_date')
	search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name', 'license_number')


@admin.register(DoctorSchedule)
class DoctorScheduleAdmin(admin.ModelAdmin):
	list_display = ('doctor', 'weekday', 'start_time', 'end_time', 'slot_duration', 'is_available')
	list_filter = ('weekday', 'is_available')
	search_fields = ('doctor__user__username', 'doctor__user__email')
