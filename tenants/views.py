from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils import timezone
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json

from .models import DataPackage, UserSubscription, ActiveSession, PausedSession
from .forms import SessionPauseForm

# -----------------------------
# Data Package Views
# -----------------------------
class PackageListView(ListView):
    """List all available data packages - public access"""
    model = DataPackage
    template_name = 'tenants/package_list.html'
    context_object_name = 'packages'
    
    def get_queryset(self):
        return DataPackage.objects.filter(is_active=True).order_by('price')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            context['active_subscription'] = UserSubscription.objects.filter(
                user=self.request.user,
                status='active',
                expiry_date__gte=timezone.now()
            ).first()
        return context

# -----------------------------
# Subscription Views
# -----------------------------
class SubscriptionListView(LoginRequiredMixin, ListView):
    """List all subscriptions for the current user"""
    model = UserSubscription
    template_name = 'tenants/subscription_list.html'
    context_object_name = 'subscriptions'
    
    def get_queryset(self):
        return UserSubscription.objects.filter(user=self.request.user).order_by('-purchase_date')

class SubscriptionDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """Detail view for a user's subscription"""
    model = UserSubscription
    template_name = 'tenants/subscription_detail.html'
    context_object_name = 'subscription'
    
    def test_func(self):
        subscription = self.get_object()
        return subscription.user == self.request.user
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_sessions'] = ActiveSession.objects.filter(
            subscription=self.object,
            session_status='active'
        )
        context['pause_history'] = PausedSession.objects.filter(session__subscription=self.object)
        return context

class SubscriptionPauseView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Pause a subscription"""
    def test_func(self):
        subscription = get_object_or_404(UserSubscription, pk=self.kwargs['pk'])
        return subscription.user == self.request.user and subscription.is_active
    
    def get(self, request, *args, **kwargs):
        subscription = get_object_or_404(UserSubscription, pk=self.kwargs['pk'])
        return render(request, 'tenants/subscription_pause_confirm.html', {'subscription': subscription})
    
    def post(self, request, *args, **kwargs):
        subscription = get_object_or_404(UserSubscription, pk=self.kwargs['pk'])
        subscription.pause()
        messages.success(request, 'Subscription paused successfully!')
        return redirect('tenants:subscription_detail', pk=subscription.pk)

class SubscriptionResumeView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Resume a paused subscription"""
    def test_func(self):
        subscription = get_object_or_404(UserSubscription, pk=self.kwargs['pk'])
        return subscription.user == self.request.user and subscription.is_paused
    
    def get(self, request, *args, **kwargs):
        subscription = get_object_or_404(UserSubscription, pk=self.kwargs['pk'])
        return render(request, 'tenants/subscription_resume_confirm.html', {'subscription': subscription})
    
    def post(self, request, *args, **kwargs):
        subscription = get_object_or_404(UserSubscription, pk=self.kwargs['pk'])
        subscription.unpause()
        messages.success(request, 'Subscription resumed successfully!')
        return redirect('tenants:subscription_detail', pk=subscription.pk)

# -----------------------------
# Session Management Views
# -----------------------------
class ActiveSessionListView(LoginRequiredMixin, ListView):
    """List active sessions for the current user"""
    model = ActiveSession
    template_name = 'tenants/session_list.html'
    context_object_name = 'sessions'
    
    def get_queryset(self):
        return ActiveSession.objects.filter(
            user=self.request.user,
            session_status='active'
        ).order_by('-start_time')

class SessionPauseView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Pause an active session"""
    def test_func(self):
        session = get_object_or_404(ActiveSession, pk=self.kwargs['pk'])
        return session.user == self.request.user and session.is_active
    
    def get(self, request, *args, **kwargs):
        session = get_object_or_404(ActiveSession, pk=self.kwargs['pk'])
        form = SessionPauseForm()
        return render(request, 'tenants/session_pause.html', {
            'session': session,
            'form': form
        })
    
    def post(self, request, *args, **kwargs):
        session = get_object_or_404(ActiveSession, pk=self.kwargs['pk'])
        form = SessionPauseForm(request.POST)
        
        if form.is_valid():
            session.pause_session()
            
            # Create pause record
            PausedSession.objects.create(
                session=session,
                pause_reason=form.cleaned_data['pause_reason'],
                pause_description=form.cleaned_data['pause_description'],
                paused_by=self.request.user
            )
            
            messages.success(request, 'Session paused successfully!')
            return redirect('tenants:session_list')
        
        return render(request, 'tenants/session_pause.html', {
            'session': session,
            'form': form
        })

class SessionResumeView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Resume a paused session"""
    def test_func(self):
        session = get_object_or_404(ActiveSession, pk=self.kwargs['pk'])
        return session.user == self.request.user and session.is_paused
    
    def get(self, request, *args, **kwargs):
        session = get_object_or_404(ActiveSession, pk=self.kwargs['pk'])
        return render(request, 'tenants/session_resume_confirm.html', {'session': session})
    
    def post(self, request, *args, **kwargs):
        session = get_object_or_404(ActiveSession, pk=self.kwargs['pk'])
        session.resume_session()
        
        # Update the latest pause record
        latest_pause = PausedSession.objects.filter(
            session=session,
            resumed_at__isnull=True
        ).last()
        
        if latest_pause:
            latest_pause.resume()
        
        messages.success(request, 'Session resumed successfully!')
        return redirect('tenants:session_list')

class SessionTerminateView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Terminate a session"""
    def test_func(self):
        session = get_object_or_404(ActiveSession, pk=self.kwargs['pk'])
        return session.user == self.request.user and session.is_active
    
    def get(self, request, *args, **kwargs):
        session = get_object_or_404(ActiveSession, pk=self.kwargs['pk'])
        return render(request, 'tenants/session_terminate_confirm.html', {'session': session})
    
    def post(self, request, *args, **kwargs):
        session = get_object_or_404(ActiveSession, pk=self.kwargs['pk'])
        session.terminate_session()
        messages.success(request, 'Session terminated successfully!')
        return redirect('tenants:session_list')

# -----------------------------
# Dashboard & Analytics Views
# -----------------------------
class TenantDashboardView(LoginRequiredMixin, TemplateView):
    """Main dashboard for tenant users"""
    template_name = 'tenants/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get active subscription
        active_subscription = UserSubscription.objects.filter(
            user=user,
            status='active',
            expiry_date__gte=timezone.now()
        ).first()
        
        # Get active sessions
        active_sessions = ActiveSession.objects.filter(
            user=user,
            session_status='active'
        )
        
        # Get usage statistics
        total_data_used = ActiveSession.objects.filter(
            user=user,
            start_time__date=timezone.now().date()
        ).aggregate(total=Sum('data_used_mb'))['total'] or 0
        
        context.update({
            'active_subscription': active_subscription,
            'active_sessions': active_sessions,
            'total_data_used_today': total_data_used,
            'session_count': active_sessions.count(),
        })
        
        return context

# -----------------------------
# API Views for JavaScript Integration
# -----------------------------
@method_decorator(csrf_exempt, name='dispatch')
class CreateSubscriptionAPIView(LoginRequiredMixin, View):
    """API endpoint for JavaScript to create subscriptions"""
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            package_id = data.get('package_id')
            payment_method = data.get('payment_method')
            
            package = get_object_or_404(DataPackage, pk=package_id, is_active=True)
            
            # Check if user already has active subscription
            active_sub = UserSubscription.objects.filter(
                user=request.user,
                status='active',
                expiry_date__gte=timezone.now()
            ).first()
            
            if active_sub:
                return JsonResponse({
                    'status': 'error',
                    'message': 'You already have an active subscription'
                }, status=400)
            
            # Create subscription (payment processing would happen here)
            subscription = UserSubscription.objects.create(
                user=request.user,
                package=package,
                expiry_date=timezone.now() + timezone.timedelta(days=package.duration_days),
                status='active'
            )
            
            # Here you would integrate with your payment gateway
            # For now, we'll simulate successful payment
            
            return JsonResponse({
                'status': 'success',
                'message': 'Subscription created successfully',
                'subscription_id': str(subscription.id),
                'redirect_url': reverse_lazy('tenants:subscription_success', kwargs={'pk': subscription.id})
            })
            
        except DataPackage.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Package not found'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)

@method_decorator(csrf_exempt, name='dispatch')
class SessionWebhookView(View):
    """Webhook endpoint for MikroTik session updates"""
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            session_id = data.get('session_id')
            action = data.get('action')
            data_used = data.get('data_used', 0)
            
            # Update session based on webhook data
            session = ActiveSession.objects.get(mikrotik_session_id=session_id)
            
            if action == 'update':
                session.data_used_mb = data_used
                session.save()
            elif action == 'terminate':
                session.terminate_session()
            
            return JsonResponse({'status': 'success'})
            
        except ActiveSession.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Session not found'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

# -----------------------------
# Utility Views
# -----------------------------
def subscription_success(request, pk):
    """Subscription purchase success page"""
    subscription = get_object_or_404(UserSubscription, pk=pk, user=request.user)
    return render(request, 'tenants/subscription_success.html', {'subscription': subscription})

def subscription_failed(request):
    """Subscription purchase failure page"""
    return render(request, 'tenants/subscription_failed.html')

def usage_history(request):
    """Usage history page"""
    sessions = ActiveSession.objects.filter(user=request.user).order_by('-start_time')
    return render(request, 'tenants/usage_history.html', {'sessions': sessions})

def session_stats(request):
    """Session statistics page"""
    user = request.user
    today = timezone.now().date()
    
    today_sessions = ActiveSession.objects.filter(
        user=user,
        start_time__date=today
    )
    
    total_data_today = today_sessions.aggregate(total=Sum('data_used_mb'))['total'] or 0
    session_count_today = today_sessions.count()
    
    return render(request, 'tenants/session_stats.html', {
        'total_data_today': total_data_today,
        'session_count_today': session_count_today,
        'today_sessions': today_sessions,
    })