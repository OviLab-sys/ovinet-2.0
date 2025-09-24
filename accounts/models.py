from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from core.models import BaseModel


class UserManager(BaseUserManager):  # ← Change to BaseUserManager
    """Custom manager for User model with phone number authentication"""
    
    def create_user(self, phone_number, password=None, **extra_fields):
        """Create and save a regular user with the given phone number and password"""
        if not phone_number:
            raise ValueError('The Phone Number must be set')
        
        # Normalize phone number format
        phone_number = self.normalize_phone_number(phone_number)
        
        # Set default user_type to 'end_user' if not specified
        extra_fields.setdefault('user_type', 'end_user')
        
        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def normalize_phone_number(self, phone_number):
        """Convert any phone format to standard 254 format"""
        # Remove any non-digit characters except +
        phone_number = ''.join(filter(str.isdigit, phone_number))
        
        # Handle different formats
        if phone_number.startswith('0') and len(phone_number) == 10:
            # Convert 0721630939 to 254721630939
            return '254' + phone_number[1:]
        elif phone_number.startswith('254') and len(phone_number) == 12:
            # Already in 254 format
            return phone_number
        elif len(phone_number) == 9:
            # 721630939 to 254721630939
            return '254' + phone_number
        else:
            # Return as-is (will be validated by model)
            return phone_number

    def create_superuser(self, phone_number, password=None, **extra_fields):
        """Create superuser with vendor_admin as default type"""
        # Set superuser flags
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('user_type', 'vendor_admin')

        # Validate superuser flags
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        # Create the user using create_user method
        return self.create_user(phone_number, password, **extra_fields)

class User(AbstractUser, BaseModel):
    """Custom User model that exists in each tenant's schema"""
    
    USER_TYPE_CHOICES = (
        ('vendor_admin', 'Vendor Admin'),
        ('vendor_staff', 'Vendor Staff'),
        ('end_user', 'End User'),
    )
    
    # Remove username field, use phone number instead
    username = None
    
    # Primary identifier - phone number (multiple formats accepted)
    phone_number = models.CharField(
        max_length=15,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^(\+?254|0)?[17]\d{8}$',
                message="Enter a valid Kenyan phone number (e.g., 0721630939, +254721630939, 254721630939)"
            )
        ],
        verbose_name=_('Phone Number'),
        help_text=_('Your phone number for login and MPesa payments')
    )
    
    # Email - required for vendors, optional for end users
    email = models.EmailField(
        unique=True,
        blank=True,
        null=True,
        verbose_name=_('Email Address'),
        help_text=_('Required for vendor accounts')
    )
    
    # National ID - required for vendors
    national_id = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name=_('National ID Number'),
        help_text=_('National ID number (required for vendor accounts)'),
        validators=[
            RegexValidator(
                regex=r'^[0-9]{6,12}$',
                message="Enter a valid National ID number"
            )
        ]
    )
    
    # User type
    user_type = models.CharField(
        max_length=20,
        choices=USER_TYPE_CHOICES,
        default='end_user'
    )
    
    # Vendor relationship
    vendor = models.ForeignKey(
        'vendors.Vendor',
        on_delete=models.CASCADE,
        related_name='users',
        null=True,
        blank=True
    )

    objects = UserManager()
    
    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
    
    def __str__(self):
        return f"{self.phone_number} ({self.get_user_type_display()})"
    
    def clean(self):
        """Validate that vendors have email and national ID"""
        if self.user_type in ['vendor_admin', 'vendor_staff']:
            if not self.email:
                raise ValidationError('Email address is required for vendor accounts.')
            if not self.national_id:
                raise ValidationError('National ID number is required for vendor accounts.')
    
    def save(self, *args, **kwargs):
        """Auto-set vendor to None for end users and normalize phone number"""
        if self.user_type == 'end_user':
            self.vendor = None
            self.national_id = None  # Clear national ID for end users
        
        # Normalize phone number before saving
        self.phone_number = User.objects.normalize_phone_number(self.phone_number)
        
        super().save(*args, **kwargs)
    
    @property
    def is_end_user(self):
        return self.user_type == 'end_user'
    
    @property
    def is_vendor_staff(self):
        return self.user_type in ['vendor_admin', 'vendor_staff']
    
    @property
    def formatted_phone(self):
        """Return phone number in human-readable format"""
        if self.phone_number.startswith('254') and len(self.phone_number) == 12:
            return f"+{self.phone_number}"
        return self.phone_number