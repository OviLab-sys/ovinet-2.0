from django.urls import path
from . import views

app_name = 'tenants'

urlpatterns = [
    # Package routes
    path('packages/', views.package_list, name='package_list'),
    path('packages/<uuid:package_id>/purchase/', views.purchase_package, name='purchase_package'),
    
    # Subscription routes
    path('subscriptions/', views.subscription_list, name='subscription_list'),
    path('subscriptions/<uuid:pk>/', views.subscription_detail, name='subscription_detail'),
    path('subscriptions/<uuid:pk>/pause/', views.pause_subscription, name='pause_subscription'),
    path('subscriptions/<uuid:pk>/resume/', views.resume_subscription, name='resume_subscription'),
    
    # Session routes
    path('sessions/', views.active_session_list, name='session_list'),
    path('sessions/<uuid:pk>/pause/', views.pause_session, name='pause_session'),
    path('sessions/<uuid:pk>/resume/', views.resume_session, name='resume_session'),
    path('sessions/<uuid:pk>/terminate/', views.terminate_session, name='terminate_session'),
    
    # Dashboard and analytics routes
    path('dashboard/', views.tenant_dashboard, name='dashboard'),
    path('usage-history/', views.usage_history, name='usage_history'),
    path('session-stats/', views.session_stats, name='session_stats'),
    
    # Purchase result routes
    path('subscription-success/<uuid:pk>/', views.subscription_success, name='subscription_success'),
    path('subscription-failed/', views.subscription_failed, name='subscription_failed'),
]