from django.db import models
from django_tenants.models import TenantMixin, DomainMixin
from core.models import BaseModel
from django.core.validators import MinValueValidator
from django.utils import timezone

class Vendor(TenantMixin, BaseModel):
    """Tenant model - each vendor gets their own schema"""
    BUSINESS_TYPES = (
        ('isp', 'Internet Service Provider'),
        ('hotel', 'Hotel'),
        ('restaurant', 'Restaurant'),
        ('campus', 'Campus/University'),
        ('residential', 'Residential Complex'),
        ('other', 'Other'),
    )
    
    LICENSE_STATUS = (
        ('active', 'Active'),
        ('pending', 'Pending'),
        ('suspended', 'Suspended'),
        ('expired', 'Expired'),
    )
    
    # Business Information
    business_name = models.CharField(max_length=255, unique=True)
    business_type = models.CharField(max_length=20, choices=BUSINESS_TYPES, default='isp')
    business_email = models.EmailField(unique=True)
    business_phone = models.CharField(max_length=15)
    address = models.TextField()
    website = models.URLField(blank=True, null=True)
    
    # Contact Person
    contact_person = models.CharField(max_length=100)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=15)
    
    # License Management
    license_status = models.CharField(max_length=20, choices=LICENSE_STATUS, default='pending')
    license_start_date = models.DateField(null=True, blank=True)
    license_end_date = models.DateField(null=True, blank=True)
    license_duration_days = models.PositiveIntegerField(default=365, validators=[MinValueValidator(1)])
    
    # Business Limits
    max_users = models.PositiveIntegerField(default=100, validators=[MinValueValidator(1)])
    max_active_sessions = models.PositiveIntegerField(default=200, validators=[MinValueValidator(1)])
    
    # Trial Management
    is_trial = models.BooleanField(default=True)
    trial_start_date = models.DateField(null=True, blank=True)
    trial_end_date = models.DateField(null=True, blank=True)
    trial_duration_days = models.PositiveIntegerField(default=14, validators=[MinValueValidator(1)])
    
    # Revenue Sharing
    platform_fee_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=15.00,
        validators=[MinValueValidator(0)]
    )
    
    # django-tenants required fields
    auto_create_schema = True
    auto_drop_schema = True
    
    class Meta:
        verbose_name = 'Vendor'
        verbose_name_plural = 'Vendors'
        ordering = ['business_name']

    def __str__(self):
        return self.business_name
    
    def save(self, *args, **kwargs):
        # Set trial dates if this is a new vendor
        if self._state.adding and self.is_trial:
            self.trial_start_date = timezone.now().date()
            self.trial_end_date = self.trial_start_date + timezone.timedelta(days=self.trial_duration_days)
        
        # Set license dates when activating
        if self.license_status == 'active' and not self.license_start_date:
            self.license_start_date = timezone.now().date()
            self.license_end_date = self.license_start_date + timezone.timedelta(days=self.license_duration_days)
        
        super().save(*args, **kwargs)
    
    @property
    def is_license_active(self):
        """Check if license is currently active"""
        if self.license_status == 'active' and self.license_end_date:
            return self.license_end_date >= timezone.now().date()
        return False
    
    @property
    def is_trial_active(self):
        """Check if trial period is active"""
        return self.is_trial and self.trial_end_date and self.trial_end_date >= timezone.now().date()
    
    @property
    def days_until_license_expiry(self):
        """Days remaining until license expiry"""
        if self.license_end_date and self.is_license_active:
            return (self.license_end_date - timezone.now().date()).days
        return 0
    
    @property
    def days_until_trial_end(self):
        """Days remaining until trial ends"""
        if self.trial_end_date and self.is_trial_active:
            return (self.trial_end_date - timezone.now().date()).days
        return 0
    
    @property
    def should_display_warning(self):
        """Check if warning should be displayed for upcoming expiry"""
        if self.is_license_active and self.days_until_license_expiry <= 30:
            return True
        if self.is_trial_active and self.days_until_trial_end <= 7:
            return True
        return False

class Domain(DomainMixin):
    """Domain model for tenant URLs"""
    class Meta:
        verbose_name = 'Domain'
        verbose_name_plural = 'Domains'
    
    def __str__(self):
        return self.domain