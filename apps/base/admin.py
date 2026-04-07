from django.contrib import admin
from .models import ContactMessage


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
	list_display = ("full_name", "email", "phone_number", "subject", "created", "is_active")
	list_filter = ("is_active", "created")
	search_fields = ("full_name", "email", "phone_number", "subject", "message")
