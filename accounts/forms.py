from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from .models import User
from vendors.models import Vendor

class EndUserRegistrationForm(UserCreationForm):
    """Registration form for end users - only phone + password"""
    
    class Meta:
        model = User
        fields = ['phone_number', 'password1', 'password2']
        widgets = {
            'phone_number': forms.TextInput(attrs={
                'placeholder': '0721630939 or 254721630939',
                'class': 'form-control'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove unnecessary fields
        self.fields.pop('first_name', None)
        self.fields.pop('last_name', None)
        self.fields.pop('email', None)
        self.fields.pop('national_id', None)
        
        # Set user_type to end_user automatically
        self.instance.user_type = 'end_user'
    
    def clean_phone_number(self):
        """Accept multiple phone formats"""
        phone_number = self.cleaned_data.get('phone_number')
        return phone_number  # Validation handled by model

class VendorStaffRegistrationForm(UserCreationForm):
    """Registration form for vendor staff - requires email and national ID"""
    
    class Meta:
        model = User
        fields = ['phone_number', 'email', 'first_name', 'last_name', 'national_id', 'user_type', 'vendor', 'password1', 'password2']
        widgets = {
            'phone_number': forms.TextInput(attrs={'placeholder': '0721630939 or 254721630939'}),
            'email': forms.EmailInput(attrs={'placeholder': 'admin@company.com'}),
            'national_id': forms.TextInput(attrs={'placeholder': '12345678'})
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make email and national_id required for vendor staff
        self.fields['email'].required = True
        self.fields['national_id'].required = True
        
        # Limit user_type choices to vendor staff only
        self.fields['user_type'].choices = [
            ('vendor_admin', 'Vendor Admin'),
            ('vendor_staff', 'Vendor Staff'),
        ]
    
    def clean(self):
        """Ensure vendor, email, and national ID are provided for vendor staff"""
        cleaned_data = super().clean()
        user_type = cleaned_data.get('user_type')
        vendor = cleaned_data.get('vendor')
        email = cleaned_data.get('email')
        national_id = cleaned_data.get('national_id')
        
        if user_type in ['vendor_admin', 'vendor_staff']:
            if not vendor:
                raise ValidationError('Vendor is required for vendor staff accounts.')
            if not email:
                raise ValidationError('Email address is required for vendor staff accounts.')
            if not national_id:
                raise ValidationError('National ID number is required for vendor staff accounts.')
        
        return cleaned_data
    
    def clean_national_id(self):
        """Validate national ID format"""
        national_id = self.cleaned_data.get('national_id')
        if national_id:
            # Remove any spaces or dashes
            national_id = ''.join(filter(str.isdigit, national_id))
            if len(national_id) < 6 or len(national_id) > 12:
                raise ValidationError('National ID must be between 6 and 12 digits')
        return national_id
    
    def save(self, commit=True):
        user = super().save(commit=False)
        vendor_data = self.cleaned_data.get('vendor')
        # If vendor_data is a dict or form, create Vendor instance
        if isinstance(vendor_data, dict):
            vendor = Vendor.objects.create(**vendor_data)
            user.vendor = vendor
        elif vendor_data:
            user.vendor = vendor_data  # If already a Vendor instance
        if commit:
            user.save()
        return user
    
    # ...existing code...

class LoginForm(forms.Form):
    """Login form using phone number and password"""
    phone_number = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={
            'placeholder': '0721630939 or 254721630939',
            'class': 'form-control'
        }),
        label='Phone Number'
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Password',
            'class': 'form-control'
        }),
        label='Password'
    )

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        # You can add normalization here if needed
        return phone_number
