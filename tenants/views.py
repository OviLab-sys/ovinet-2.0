from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum

from .models import DataPackage, UserSubscription, ActiveSession, PausedSession

def package_list(request):
    """List all available data packages - public access"""
    packages = DataPackage.objects.filter(is_active=True).order_by('price')
    
    active_subscription = None
    if request.user.is_authenticated:
        active_subscription = UserSubscription.objects.filter(
            user=request.user,
            status='active',
            expiry_date__gte=timezone.now()
        ).first()
    
    return render(request, 'tenants/package_list.html', {
        'packages': packages,
        'active_subscription': active_subscription
    })

@login_required
def purchase_package(request, package_id):
    """Handle package purchase - redirect to billing app"""
    package = get_object_or_404(DataPackage, pk=package_id, is_active=True)
    
    # Check if user already has active subscription
    active_sub = UserSubscription.objects.filter(
        user=request.user,
        status='active',
        expiry_date__gte=timezone.now()
    ).first()
    
    if active_sub:
        messages.warning(request, 'You already have an active subscription!')
        return redirect('tenants:subscription_detail', pk=active_sub.pk)
    
    # Redirect to billing app for payment processing
    return redirect('billing:initiate_payment', package_id=package.id)

@login_required
def subscription_list(request):
    """List all subscriptions for the current user"""
    subscriptions = UserSubscription.objects.filter(user=request.user).order_by('-purchase_date')
    return render(request, 'tenants/subscription_list.html', {
        'subscriptions': subscriptions
    })

# FIX: Add the missing pause_subscription function
@login_required
def pause_subscription(request, pk):
    """Pause a subscription - THIS WAS MISSING"""
    subscription = get_object_or_404(UserSubscription, pk=pk, user=request.user)
    
    if not subscription.is_active:
        messages.warning(request, 'Subscription is not active!')
        return redirect('tenants:subscription_detail', pk=subscription.pk)
    
    if request.method == 'POST':
        subscription.pause()
        messages.success(request, 'Subscription paused successfully!')
        return redirect('tenants:subscription_detail', pk=subscription.pk)
    
    return render(request, 'tenants/subscription_pause_confirm.html', {
        'subscription': subscription
    })

# FIX: Add the missing subscription_detail function
@login_required
def subscription_detail(request, pk):
    """Detail view for a user's subscription"""
    subscription = get_object_or_404(UserSubscription, pk=pk, user=request.user)
    
    active_sessions = ActiveSession.objects.filter(
        subscription=subscription,
        session_status='active'
    )
    
    pause_history = PausedSession.objects.filter(session__subscription=subscription)
    
    return render(request, 'tenants/subscription_detail.html', {
        'subscription': subscription,
        'active_sessions': active_sessions,
        'pause_history': pause_history
    })

# FIX: Add other missing view functions
@login_required
def resume_subscription(request, pk):
    """Resume a paused subscription"""
    subscription = get_object_or_404(UserSubscription, pk=pk, user=request.user)
    
    if not subscription.is_paused:
        messages.warning(request, 'Subscription is not paused!')
        return redirect('tenants:subscription_detail', pk=subscription.pk)
    
    if request.method == 'POST':
        subscription.unpause()
        messages.success(request, 'Subscription resumed successfully!')
        return redirect('tenants:subscription_detail', pk=subscription.pk)
    
    return render(request, 'tenants/subscription_resume_confirm.html', {
        'subscription': subscription
    })

@login_required
def active_session_list(request):
    """List active sessions for the current user"""
    sessions = ActiveSession.objects.filter(
        user=request.user,
        session_status='active'
    ).order_by('-start_time')
    
    return render(request, 'tenants/session_list.html', {
        'sessions': sessions
    })

@login_required
def pause_session(request, pk):
    """Pause an active session"""
    session = get_object_or_404(ActiveSession, pk=pk, user=request.user)
    
    if not session.is_active:
        messages.warning(request, 'Session is not active!')
        return redirect('tenants:session_list')
    
    if request.method == 'POST':
        session.pause_session()
        messages.success(request, 'Session paused successfully!')
        return redirect('tenants:session_list')
    
    return render(request, 'tenants/session_pause.html', {
        'session': session
    })

@login_required
def resume_session(request, pk):
    """Resume a paused session"""
    session = get_object_or_404(ActiveSession, pk=pk, user=request.user)
    
    if not session.is_paused:
        messages.warning(request, 'Session is not paused!')
        return redirect('tenants:session_list')
    
    if request.method == 'POST':
        session.resume_session()
        messages.success(request, 'Session resumed successfully!')
        return redirect('tenants:session_list')
    
    return render(request, 'tenants/session_resume_confirm.html', {
        'session': session
    })

@login_required
def terminate_session(request, pk):
    """Terminate a session"""
    session = get_object_or_404(ActiveSession, pk=pk, user=request.user)
    
    if not session.is_active:
        messages.warning(request, 'Session is not active!')
        return redirect('tenants:session_list')
    
    if request.method == 'POST':
        session.terminate_session()
        messages.success(request, 'Session terminated successfully!')
        return redirect('tenants:session_list')
    
    return render(request, 'tenants/session_terminate_confirm.html', {
        'session': session
    })

@login_required
def tenant_dashboard(request):
    """Main dashboard for tenant users"""
    user = request.user
    
    active_subscription = UserSubscription.objects.filter(
        user=user,
        status='active',
        expiry_date__gte=timezone.now()
    ).first()
    
    active_sessions = ActiveSession.objects.filter(
        user=user,
        session_status='active'
    )
    
    total_data_used = ActiveSession.objects.filter(
        user=user,
        start_time__date=timezone.now().date()
    ).aggregate(total=Sum('data_used_mb'))['total'] or 0
    
    return render(request, 'tenants/dashboard.html', {
        'active_subscription': active_subscription,
        'active_sessions': active_sessions,
        'total_data_used_today': total_data_used,
        'session_count': active_sessions.count(),
    })

@login_required
def usage_history(request):
    """Usage history page"""
    sessions = ActiveSession.objects.filter(user=request.user).order_by('-start_time')
    return render(request, 'tenants/usage_history.html', {'sessions': sessions})

@login_required
def session_stats(request):
    """Session statistics page"""
    today = timezone.now().date()
    
    today_sessions = ActiveSession.objects.filter(
        user=request.user,
        start_time__date=today
    )
    
    total_data_today = today_sessions.aggregate(total=Sum('data_used_mb'))['total'] or 0
    session_count_today = today_sessions.count()
    
    return render(request, 'tenants/session_stats.html', {
        'total_data_today': total_data_today,
        'session_count_today': session_count_today,
        'today_sessions': today_sessions,
    })

def subscription_success(request, pk):
    """Subscription purchase success page"""
    subscription = get_object_or_404(UserSubscription, pk=pk, user=request.user)
    return render(request, 'tenants/subscription_success.html', {'subscription': subscription})

def subscription_failed(request):
    """Subscription purchase failure page"""
    return render(request, 'tenants/subscription_failed.html')