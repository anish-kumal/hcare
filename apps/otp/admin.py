from django.contrib import admin
from django.utils.html import format_html
from .models import OTP


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    """
    Admin interface for OTP model.
    Provides a user-friendly interface for managing OTPs.
    """
    
    list_display = (
        'user',
        'code_masked',
        'verified_badge',
        'expiry_status',
        'attempts',
        'created',
    )
    
    list_filter = (
        'verified',
        'created',
        'expires_at',
    )
    
    search_fields = (
        'user__username',
        'user__email',
        'code',
    )
    
    readonly_fields = (
        'user',
        'code',
        'created',
        'modified',
        'verified_at',
        'is_expired',
        'is_valid',
    )
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('OTP Details', {
            'fields': ('code', 'expires_at', 'attempts')
        }),
        ('Verification Status', {
            'fields': ('verified', 'verified_at', 'is_expired', 'is_valid')
        }),
        ('Timestamps', {
            'fields': ('created', 'modified'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_verified', 'reset_attempts']
    
    def code_masked(self, obj):
        """Display masked OTP code for security"""
        return f"***{obj.code[-2:]}"
    code_masked.short_description = 'Code'
    
    def verified_badge(self, obj):
        """Display verification status as colored badge"""
        if obj.verified:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Verified</span>'
            )
        return format_html(
            '<span style="color: orange; font-weight: bold;">⏳ Pending</span>'
        )
    verified_badge.short_description = 'Status'
    
    def expiry_status(self, obj):
        """Display OTP expiry status"""
        if obj.is_expired:
            return format_html(
                '<span style="color: red; font-weight: bold;">Expired</span>'
            )
        return format_html(
            '<span style="color: green;">Valid</span>'
        )
    expiry_status.short_description = 'Expiry'
    
    def mark_as_verified(self, request, queryset):
        """Admin action to mark OTPs as verified"""
        updated = queryset.update(verified=True)
        self.message_user(request, f"{updated} OTP(s) marked as verified.")
    mark_as_verified.short_description = "Mark selected OTPs as verified"
    
    def reset_attempts(self, request, queryset):
        """Admin action to reset verification attempts"""
        updated = queryset.update(attempts=0)
        self.message_user(request, f"{updated} OTP(s) attempts reset.")
    reset_attempts.short_description = "Reset attempts for selected OTPs"
    
    def has_add_permission(self, request):
        """Prevent manual OTP creation from admin"""
        return False

