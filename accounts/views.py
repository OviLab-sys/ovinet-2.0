from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect

from .forms import EndUserRegistrationForm, VendorStaffRegistrationForm

def login_view(request):
    """Login view for all users - phone number + password"""
    if request.method == 'POST':
        phone_number = request.POST.get('phone_number')
        password = request.POST.get('password')
        
        # Normalize phone number (remove + and ensure 254 format)
        if phone_number:
            phone_number = ''.join(filter(str.isdigit, phone_number))
            if phone_number.startswith('0') and len(phone_number) == 10:
                phone_number = '254' + phone_number[1:]
        
        user = authenticate(request, phone_number=phone_number, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.get_full_name()}!')
            
            # Redirect based on user type
            if user.is_vendor_staff:
                return redirect('vendors:dashboard')
            else:
                return redirect('tenants:dashboard')
        else:
            messages.error(request, 'Invalid phone number or password.')
    
    return render(request, 'accounts/login.html')

def end_user_register(request):
    """Registration for end users - phone + password only"""
    if request.method == 'POST':
        form = EndUserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Set default names from phone number
            user.first_name = "User"
            user.last_name = form.cleaned_data['phone_number'][-4:]  # Last 4 digits
            user.save()
            
            login(request, user)
            messages.success(request, 'Registration successful! Welcome to OviLink.')
            return redirect('tenants:dashboard')
    else:
        form = EndUserRegistrationForm()
    
    return render(request, 'accounts/end_user_register.html', {'form': form})

@login_required
def vendor_staff_register(request):
    """Registration for vendor staff - requires email, national ID, and vendor"""
    # Only allow vendor admins to access this view
    if not request.user.is_vendor_staff:
        messages.error(request, 'You must be a vendor administrator to create staff accounts.')
        return redirect('accounts:login')
    
    if request.method == 'POST':
        form = VendorStaffRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Vendor staff account created successfully!')
            return redirect('vendors:dashboard')
    else:
        form = VendorStaffRegistrationForm()
    
    return render(request, 'accounts/vendor_staff_register.html', {'form': form})

@login_required
def profile(request):
    """User profile page"""
    return render(request, 'accounts/profile.html', {'user': request.user})

def logout_view(request):
    """Logout view"""
    from django.contrib.auth import logout
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('accounts:login')