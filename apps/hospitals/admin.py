from django.contrib import admin

from .models import Hospital, HospitalAdmin, HospitalDepartment


@admin.register(Hospital)
class HospitalAdminConfig(admin.ModelAdmin):
	list_display = ('name', 'city', 'state', 'is_verified', 'total_beds')
	list_filter = ('city', 'state', 'is_verified')
	search_fields = ('name', 'registration_number', 'email', 'phone_number')


@admin.register(HospitalDepartment)
class HospitalDepartmentAdmin(admin.ModelAdmin):
	list_display = ('hospital', 'name', 'code')
	list_filter = ('hospital',)
	search_fields = ('name', 'code', 'hospital__name')


@admin.register(HospitalAdmin)
class HospitalAdminAdmin(admin.ModelAdmin):
	list_display = ('user', 'hospital', 'created')
	list_filter = ('hospital', 'created')
	search_fields = ('user__username', 'user__email', 'hospital__name')
