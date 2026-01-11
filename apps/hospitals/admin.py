from django.contrib import admin

from .models import Hospital, HospitalAdmin, HospitalDepartment


@admin.register(Hospital)
class HospitalAdminConfig(admin.ModelAdmin):
	list_display = ('name', 'city', 'state', 'is_verified', 'total_beds')
	list_filter = ('city', 'state', 'is_verified')
	search_fields = ('name', 'registration_number', 'email', 'phone_number')


@admin.register(HospitalDepartment)
class HospitalDepartmentAdmin(admin.ModelAdmin):
	list_display = ('hospital', 'name', 'code', 'head_doctor', 'total_beds', 'available_beds')
	list_filter = ('hospital',)
	search_fields = ('name', 'code', 'hospital__name')


@admin.register(HospitalAdmin)
class HospitalAdminAdmin(admin.ModelAdmin):
	list_display = ('user', 'hospital', 'designation', 'employee_id', 'joining_date')
	list_filter = ('hospital', 'joining_date')
	search_fields = ('user__username', 'user__email', 'employee_id')
