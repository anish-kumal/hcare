from django.contrib import admin

from .models import Hospital, HospitalAdmin, HospitalDepartment


@admin.register(Hospital)
class HospitalAdminConfig(admin.ModelAdmin):
	list_display = ('name', 'city', 'state', 'is_verified', 'has_khalti_keys', 'total_beds')
	list_filter = ('city', 'state', 'is_verified')
	search_fields = ('name', 'registration_number', 'email', 'phone_number')

	@admin.display(boolean=True, description='Khalti Configured')
	def has_khalti_keys(self, obj):
		return bool(obj.khalti_secret_key and obj.khalti_public_key)


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
