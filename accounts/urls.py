from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Registration
    path('register/end-user/', views.end_user_register, name='end_user_register'),
    path('register/vendor-staff/', views.vendor_staff_register, name='vendor_staff_register'),
    
    # Profile
    path('profile/', views.profile, name='profile'),
]