from django.shortcuts import render
from .forms import VendorSignupForm, VendorSettingsForm
from .models import Domain
from tenants.models import UserSubscription, Transaction
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from django.shortcuts import redirect
from django.db.models import Sum

# vendors/views.py
def vendor_signup(request):
    """Allow businesses to sign up as vendors through a public form"""
    if request.method == 'POST':
        form = VendorSignupForm(request.POST)
        if form.is_valid():
            vendor = form.save(commit=False)
            vendor.license_status = 'pending'  # Needs admin approval
            vendor.save()
            # Create default domain
            Domain.objects.create(domain=f"{vendor.schema_name}.ovinet.com", tenant=vendor)
            messages.success(request, 'Application submitted! We will review it soon.')
            return redirect('home')
    else:
        form = VendorSignupForm()
    return render(request, 'vendors/signup.html', {'form': form})


@login_required
def vendor_dashboard(request):
    """Dashboard for vendors to manage their business"""
    if not request.user.is_vendor_staff:
        return redirect('accounts:login')
    
    vendor = request.user.vendor
    stats = {
        'total_users': vendor.users.count(),
        'active_subscriptions': UserSubscription.objects.filter(
            user__vendor=vendor, status='active'
        ).count(),
        'revenue_today': Transaction.objects.filter(
            package__vendor=vendor, created_at__date=timezone.now().date()
        ).aggregate(total=Sum('amount'))['total'] or 0
    }
    
    return render(request, 'vendors/dashboard.html', {
        'vendor': vendor,
        'stats': stats
    })
    
@login_required
@user_passes_test(lambda u: u.is_vendor_admin)
def vendor_settings(request):
    """Vendor admin can update their business info"""
    vendor = request.user.vendor
    
    if request.method == 'POST':
        form = VendorSettingsForm(request.POST, instance=vendor)
        if form.is_valid():
            form.save()
            messages.success(request, 'Settings updated successfully!')
            return redirect('vendors:dashboard')
    else:
        form = VendorSettingsForm(instance=vendor)
    
    return render(request, 'vendors/settings.html', {'form': form})