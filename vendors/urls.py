# vendors/urls.py
from django.urls import path
from . import views

app_name = 'vendors'

urlpatterns = [
    path('signup/', views.vendor_signup, name='signup'),
    path('dashboard/', views.vendor_dashboard, name='dashboard'),
    path('settings/', views.vendor_settings, name='settings'),
    path('analytics/', views.vendor_analytics, name='analytics'),
]