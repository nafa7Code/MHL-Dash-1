"""
Account views for user authentication and management.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils.translation import gettext as _
from django.core.paginator import Paginator
from django.db.models import Q

from core.models import Profile, Company


def login_view(request):
    """User login view."""
    if request.user.is_authenticated:
        return redirect('core:dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if username and password:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                next_url = request.GET.get('next', 'core:dashboard')
                messages.success(request, _('Welcome back, {}!').format(user.get_full_name() or user.username))
                return redirect(next_url)
            else:
                messages.error(request, _('Invalid username or password.'))
        else:
            messages.error(request, _('Please enter both username and password.'))
    
    return render(request, 'accounts/login.html')


@login_required
def logout_view(request):
    """User logout view."""
    logout(request)
    messages.info(request, _('You have been logged out successfully.'))
    return redirect('accounts:login')


@login_required
def profile(request):
    """User profile management."""
    if request.method == 'POST':
        user = request.user
        profile = user.profile
        
        # Update user fields
        user.first_name = request.POST.get('first_name', '').strip()
        user.last_name = request.POST.get('last_name', '').strip()
        user.email = request.POST.get('email', '').strip()
        
        # Validate email uniqueness
        if user.email and User.objects.filter(email=user.email).exclude(id=user.id).exists():
            messages.error(request, _('This email address is already in use.'))
        else:
            user.save()
            
            # Update profile fields
            profile.phone = request.POST.get('phone', '').strip()
            profile.department = request.POST.get('department', '').strip()
            profile.preferred_language = request.POST.get('preferred_language', 'en')
            profile.save()
            
            messages.success(request, _('Profile updated successfully.'))
            return redirect('accounts:profile')
    
    return render(request, 'accounts/profile.html')


def is_admin(user):
    """Check if user is admin."""
    return user.is_authenticated and user.is_staff


@user_passes_test(is_admin)
def users_list(request):
    """List all users (admin only)."""
    search_query = request.GET.get('search', '').strip()
    company_filter = request.GET.get('company', '')
    status_filter = request.GET.get('status', '')
    
    users = User.objects.select_related('profile', 'profile__company').all()
    
    # Apply filters
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    if company_filter:
        users = users.filter(profile__company_id=company_filter)
    
    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)
    
    # Pagination
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get companies for filter dropdown
    companies = Company.objects.filter(is_active=True).order_by('name')
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'company_filter': company_filter,
        'status_filter': status_filter,
        'companies': companies,
    }
    
    return render(request, 'accounts/users_list.html', context)


@user_passes_test(is_admin)
def user_detail(request, user_id):
    """User detail view (admin only)."""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'toggle_status':
            user.is_active = not user.is_active
            user.save()
            status = _('activated') if user.is_active else _('deactivated')
            messages.success(request, _('User {} successfully.').format(status))
        
        elif action == 'toggle_admin':
            user.is_staff = not user.is_staff
            user.save()
            status = _('granted') if user.is_staff else _('revoked')
            messages.success(request, _('Admin privileges {} successfully.').format(status))
        
        elif action == 'reset_password':
            # In a real application, you would send a password reset email
            messages.info(request, _('Password reset email would be sent to the user.'))
        
        return redirect('accounts:user_detail', user_id=user.id)
    
    context = {
        'user_obj': user,  # Using user_obj to avoid conflict with request.user
    }
    
    return render(request, 'accounts/user_detail.html', context)