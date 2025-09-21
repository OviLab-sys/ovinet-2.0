from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.urls import reverse
from django_tenants.models import TenantModel
from core.models import BaseModel
from core.constants import DurationStatus, SessionStatus
from core.managers import SoftDeleteManager, AllObjectsManager

# -----------------------------
# Subscription Status (Tenant-specific)
# -----------------------------
class SubscriptionStatus(models.TextChoices):
    ACTIVE = 'active', 'Active'
    PAUSED = 'paused', 'Paused'
    EXPIRED = 'expired', 'Expired'
    CANCELLED = 'cancelled', 'Cancelled'

# -----------------------------
# Data Package Model
# -----------------------------
class DataPackage(BaseModel, TenantModel):
    """Data packages offered by the vendor (tenant-specific)"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    data_limit_mb = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Data limit in megabytes"
    )
    duration_status = models.CharField(
        max_length=10,
        choices=DurationStatus.choices,
        default=DurationStatus.DAILY,
        help_text="Billing duration period"
    )
    duration_days = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Number of days the package is valid"
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Price in local currency"
    )
    bandwidth_limit_mbps = models.PositiveIntegerField(
        default=5,
        validators=[MinValueValidator(1)],
        help_text="Maximum bandwidth speed in Mbps"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this package is available for purchase"
    )

    # Managers
    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        ordering = ["price"]
        verbose_name = "Data Package"
        verbose_name_plural = "Data Packages"
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['price']),
        ]

    def __str__(self):
        return f"{self.name} - {self.get_duration_status_display()}"

    def get_absolute_url(self):
        return reverse("tenants:package_detail", kwargs={"pk": self.pk})

    @property
    def formatted_price(self):
        return f"KES {self.price:.2f}"

    @property
    def formatted_data_limit(self):
        if self.data_limit_mb >= 1024:
            return f"{self.data_limit_mb / 1024:.1f} GB"
        return f"{self.data_limit_mb} MB"

# -----------------------------
# User Subscription Model
# -----------------------------
class UserSubscription(BaseModel, TenantModel):
    """User subscriptions to data packages (tenant-specific)"""
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='subscriptions',
        help_text="User who purchased this subscription"
    )
    package = models.ForeignKey(
        DataPackage,
        on_delete=models.CASCADE,
        related_name='subscriptions',
        help_text="The data package purchased"
    )
    purchase_date = models.DateTimeField(
        auto_now_add=True,
        help_text="When the subscription was purchased"
    )
    expiry_date = models.DateTimeField(
        help_text="When the subscription expires"
    )
    status = models.CharField(
        max_length=20,
        choices=SubscriptionStatus.choices,
        default='active',
        help_text="Current status of the subscription"
    )
    simultaneous_connections = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="Maximum number of simultaneous connections allowed"
    )
    current_connections = models.PositiveIntegerField(
        default=0,
        help_text="Current number of active connections"
    )
    data_used_mb = models.BigIntegerField(
        default=0,
        help_text="Total data used in megabytes"
    )

    # Managers
    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = 'User Subscription'
        verbose_name_plural = 'User Subscriptions'
        ordering = ['-purchase_date']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['expiry_date']),
            models.Index(fields=['user', 'status']),
        ]

    def __str__(self):
        return f"{self.user.phone_number} - {self.package.name}"

    def save(self, *args, **kwargs):
        """Auto-set expiry date if not provided"""
        if not self.expiry_date and self.package:
            self.expiry_date = timezone.now() + timezone.timedelta(
                days=self.package.duration_days
            )
        super().save(*args, **kwargs)

    @property
    def is_active(self):
        """Check if subscription is currently active"""
        return self.status == 'active' and self.expiry_date >= timezone.now()

    @property
    def is_paused(self):
        return self.status == 'paused'

    @property
    def has_reached_connection_limit(self):
        """Check if connection limit has been reached"""
        return self.current_connections >= self.simultaneous_connections

    @property
    def time_remaining(self):
        """Human-readable time remaining"""
        if not self.is_active:
            return "Not active"
        
        remaining = self.expiry_date - timezone.now()
        if remaining.total_seconds() <= 0:
            return "Expired"
        
        seconds = int(remaining.total_seconds())
        days, seconds = divmod(seconds, 86400)
        hours, seconds = divmod(seconds, 3600)
        minutes, seconds = divmod(seconds, 60)
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m {seconds}s"

    @property
    def data_usage_percentage(self):
        """Percentage of data used"""
        if self.package.data_limit_mb == 0:
            return 0
        return min(100, (self.data_used_mb / self.package.data_limit_mb) * 100)

    def pause(self):
        """Pause the subscription"""
        if self.status == 'active':
            self.status = 'paused'
            self.save(update_fields=['status'])

    def unpause(self):
        """Unpause the subscription"""
        if self.status == 'paused':
            self.status = 'active'
            self.save(update_fields=['status'])

# -----------------------------
# Active Session Model
# -----------------------------
class ActiveSession(BaseModel, TenantModel):
    """Active user sessions (tenant-specific)"""
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='active_sessions',
        help_text="User associated with this session"
    )
    subscription = models.ForeignKey(
        UserSubscription,
        on_delete=models.CASCADE,
        related_name='active_sessions',
        null=True,
        blank=True,
        help_text="Subscription used for this session"
    )
    session_status = models.CharField(
        max_length=20,
        choices=SessionStatus.choices,
        default=SessionStatus.ACTIVE,
        help_text="Current status of the session"
    )
    start_time = models.DateTimeField(
        default=timezone.now,
        help_text="When the session started"
    )
    end_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the session ended"
    )
    data_used_mb = models.BigIntegerField(
        default=0,
        help_text="Data used in this session (MB)"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="User's IP address"
    )
    mac_address = models.CharField(
        max_length=17,
        null=True,
        blank=True,
        help_text="User's MAC address"
    )
    mikrotik_session_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="MikroTik session ID for tracking"
    )

    # Managers
    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        ordering = ["-start_time"]
        verbose_name = "Active Session"
        verbose_name_plural = "Active Sessions"
        indexes = [
            models.Index(fields=['session_status']),
            models.Index(fields=['start_time']),
            models.Index(fields=['user', 'session_status']),
        ]

    def __str__(self):
        return f"Session {self.id} for {self.user.phone_number}"

    @property
    def is_active(self):
        return self.session_status == SessionStatus.ACTIVE

    @property
    def is_paused(self):
        return self.session_status == SessionStatus.PAUSED

    @property
    def duration(self):
        """Calculate session duration"""
        end_time = self.end_time or timezone.now()
        return end_time - self.start_time

    @property
    def duration_seconds(self):
        """Duration in seconds"""
        return int(self.duration.total_seconds())

    def pause_session(self):
        """Pause the session"""
        if self.session_status == SessionStatus.ACTIVE:
            self.session_status = SessionStatus.PAUSED
            self.save(update_fields=['session_status'])

    def resume_session(self):
        """Resume the session"""
        if self.session_status == SessionStatus.PAUSED:
            self.session_status = SessionStatus.ACTIVE
            self.save(update_fields=['session_status'])

    def terminate_session(self):
        """Terminate the session"""
        self.session_status = SessionStatus.TERMINATED
        self.end_time = timezone.now()
        self.save(update_fields=['session_status', 'end_time'])

# -----------------------------
# Paused Session Model
# -----------------------------
class PausedSession(BaseModel, TenantModel):
    """Track session pause history (tenant-specific)"""
    PAUSE_REASON_CHOICES = (
        ('user_request', 'User Request'),
        ('admin_action', 'Admin Action'),
        ('system_auto', 'System Auto-pause'),
        ('payment_issue', 'Payment Issue'),
        ('other', 'Other'),
    )
    
    session = models.ForeignKey(
        ActiveSession,
        on_delete=models.CASCADE,
        related_name='pause_history',
        help_text="The session that was paused"
    )
    paused_at = models.DateTimeField(
        default=timezone.now,
        help_text="When the session was paused"
    )
    resumed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the session was resumed"
    )
    pause_reason = models.CharField(
        max_length=20,
        choices=PAUSE_REASON_CHOICES,
        default='other',
        help_text="Reason for pausing the session"
    )
    pause_description = models.TextField(
        blank=True,
        null=True,
        help_text="Additional details about the pause"
    )
    paused_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='paused_sessions',
        help_text="User who paused the session"
    )

    # Managers
    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        ordering = ['-paused_at']
        verbose_name = "Paused Session"
        verbose_name_plural = "Paused Sessions"

    def __str__(self):
        return f"Paused Session {self.session.id}"

    @property
    def pause_duration(self):
        """Calculate total pause duration"""
        if self.resumed_at:
            return self.resumed_at - self.paused_at
        return timezone.now() - self.paused_at

    @property
    def is_active_pause(self):
        """Check if this pause is still active"""
        return self.resumed_at is None

    def resume(self):
        """Resume the paused session"""
        if self.resumed_at is None:
            self.resumed_at = timezone.now()
            self.save()
            # Also resume the main session
            self.session.resume_session()