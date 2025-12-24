from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'user_type', 'first_name', 'last_name', 'is_active', 'date_joined']
    list_filter = ['user_type', 'is_active', 'is_staff','is_default_password', 'date_joined']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'phone_number']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Information', {
            'fields': ('user_type','phone_number', 'date_of_birth', 'address', 'is_default_password')
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Additional Information', {
            'fields': ('user_type','phone_number', 'date_of_birth', 'address', 'is_default_password')
        }),
    )
