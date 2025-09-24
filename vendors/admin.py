from django.contrib import admin
from django.utils import timezone
from .models import Vendor, Domain

@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = [
        'business_name', 
        'business_type', 
        'license_status', 
        'is_trial',
        'schema_name',
        'created_at'
    ]
    list_filter = [
        'license_status', 
        'business_type', 
        'is_trial',
        'created_at'
    ]
    search_fields = [
        'business_name', 
        'business_email', 
        'contact_person',
        'schema_name'
    ]
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Business Information', {
            'fields': (
                'business_name', 'business_type', 'business_email', 
                'business_phone', 'address', 'website'
            )
        }),
        ('Contact Person', {
            'fields': ('contact_person', 'contact_email', 'contact_phone')
        }),
        ('License Management', {
            'fields': (
                'license_status', 'license_start_date', 'license_end_date',
                'license_duration_days'
            )
        }),
        ('Trial Management', {
            'fields': (
                'is_trial', 'trial_start_date', 'trial_end_date',
                'trial_duration_days'
            )
        }),
        ('Business Limits', {
            'fields': ('max_users', 'max_active_sessions')
        }),
        ('Revenue Sharing', {
            'fields': ('platform_fee_percentage',)
        }),
        ('System Information', {
            'fields': ('schema_name', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['activate_license', 'suspend_license', 'extend_trial']
    
    def activate_license(self, request, queryset):
        for vendor in queryset:
            vendor.license_status = 'active'
            vendor.license_start_date = timezone.now().date()
            vendor.license_end_date = vendor.license_start_date + timezone.timedelta(days=vendor.license_duration_days)
            vendor.save()
        self.message_user(request, f"Activated license for {queryset.count()} vendors.")
    activate_license.short_description = "Activate license for selected vendors"
    
    def suspend_license(self, request, queryset):
        updated = queryset.update(license_status='suspended')
        self.message_user(request, f"Suspended license for {updated} vendors.")
    suspend_license.short_description = "Suspend license for selected vendors"
    
    def extend_trial(self, request, queryset):
        for vendor in queryset:
            if vendor.is_trial and vendor.trial_end_date:
                vendor.trial_end_date += timezone.timedelta(days=7)
                vendor.save()
        self.message_user(request, f"Extended trial for {queryset.count()} vendors.")
    extend_trial.short_description = "Extend trial by 7 days"

@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ['domain', 'tenant', 'is_primary']
    list_filter = ['is_primary']
    search_fields = ['domain', 'tenant__business_name']
    list_select_related = ['tenant']