from django import forms
from .models import Vendor

class VendorSignupForm(forms.ModelForm):
    class Meta:
        model = Vendor
        fields = [
            'business_name',
            'business_type',
            'business_email',
            'business_phone',
            'address',
        ]
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'business_name': 'Business Name',
            'business_type': 'Type of Business',
            'business_email': 'Business Email',
            'business_phone': 'Business Phone',
            'address': 'Business Address',
        }


class VendorSettingsForm(forms.ModelForm):
    class Meta:
        model = Vendor
        fields = [
            'business_name',
            'business_type',
            'business_email',
            'business_phone',
            'address',
        ]
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'business_name': 'Business Name',
            'business_type': 'Type of Business',
            'business_email': 'Business Email',
            'business_phone': 'Business Phone',
            'address': 'Business Address',
        }