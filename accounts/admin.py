from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from django.db import connection

from .models import User

try:
    from django_tenants.utils import get_public_schema_name
    is_public_schema = connection.schema_name == get_public_schema_name()
except Exception:
    is_public_schema = False

if not is_public_schema:
    @admin.register(User)
    class CustomUserAdmin(UserAdmin):
        list_display = ['phone_number', 'email', 'first_name', 'last_name', 'user_type', 'is_active', 'date_joined']
        list_filter = ['user_type', 'is_active', 'is_staff', 'date_joined']
        search_fields = ['phone_number', 'email', 'first_name', 'last_name']
        ordering = ['-date_joined']
        fieldsets = (
            (None, {'fields': ('phone_number', 'password')}),
            (_('Personal info'), {'fields': ('first_name', 'last_name', 'email', 'national_id')}),
            (_('Permissions'), {
                'fields': ('user_type', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            }),
            (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
            (_('Vendor info'), {'fields': ('vendor',)}),
        )
        add_fieldsets = (
            (None, {
                'classes': ('wide',),
                'fields': ('phone_number', 'password1', 'password2', 'first_name', 'last_name', 'email', 'user_type', 'vendor'),
            }),
        )
        def get_form(self, request, obj=None, **kwargs):
            form = super().get_form(request, obj, **kwargs)
            form.base_fields['phone_number'].required = True
            return form