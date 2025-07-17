"""
Core views for the logistics application.
Contains dashboard and common functionality.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext as _
from django.db.models import Count, Sum, Q, Avg, Max, Min, F, ExpressionWrapper, DurationField, FloatField, Case, When, Value
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.management import call_command
from datetime import datetime, timedelta
import requests
import json
from decimal import Decimal
from django.conf import settings


from .models import Seller, VendorBill, Order
from django.shortcuts import redirect
import io
import re
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.shortcuts import redirect, render


@login_required
def dashboard(request):
    """Main dashboard view with key metrics and recent activity."""
    # Get counts for dashboard cards
    total_sellers = Seller.objects.count()
    total_bills = VendorBill.objects.count()
    total_orders = Order.objects.count()

    # Recent activity
    recent_sellers = Seller.objects.order_by('-created_at_api')[:5]
    recent_bills = VendorBill.objects.select_related(
        'seller').order_by('-created_at_api')[:5]
    recent_orders = Order.objects.select_related(
        'seller').order_by('-order_created_at')[:5]

    context = {
        'total_sellers': total_sellers,
        'total_bills': total_bills,
        'total_orders': total_orders,
        'recent_sellers': recent_sellers,
        'recent_bills': recent_bills,
        'recent_orders': recent_orders,
    }

    return render(request, 'core/dashboard.html', context)


def set_language(request):
    """Handle language switching."""
    from django.conf import settings
    from django.http import HttpResponseRedirect
    from django.utils import translation

    language = request.GET.get('language')
    next_url = request.GET.get('next', '/')

    if language and language in [lang[0] for lang in settings.LANGUAGES]:
        translation.activate(language)
        response = HttpResponseRedirect(next_url)
        response.set_cookie(settings.LANGUAGE_COOKIE_NAME, language)
        return response

    return HttpResponseRedirect(next_url)


@login_required
def profile(request):
    """User profile view."""
    if request.method == 'POST':
        # Handle profile updates
        user = request.user
        profile = user.profile

        # Update user fields
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        user.save()

        # Update profile fields
        profile.phone = request.POST.get('phone', '')
        profile.department = request.POST.get('department', '')
        profile.preferred_language = request.POST.get(
            'preferred_language', 'en')
        profile.save()

        messages.success(request, _('Profile updated successfully.'))
        return redirect('core:profile')

    return render(request, 'core/profile.html')


def handler404(request, exception):
    """Custom 404 error handler."""
    return render(request, 'errors/404.html', status=404)


def handler500(request):
    """Custom 500 error handler."""
    return render(request, 'errors/500.html', status=500)


@login_required
def omniful_sync(request):
    """Omniful sync dashboard."""
    sellers_count = Seller.objects.count()
    bills_count = VendorBill.objects.count()
    orders_count = Order.objects.count()
    recent_sellers = Seller.objects.order_by('-created_at_api')[:5]
    recent_bills = VendorBill.objects.select_related(
        'seller').order_by('-created_at_api')[:10]

    # Add recent orders
    recent_orders = Order.objects.select_related(
        'seller').order_by('-order_created_at')[:5]

    context = {
        'sellers_count': sellers_count,
        'bills_count': bills_count,
        'orders_count': orders_count,
        'recent_sellers': recent_sellers,
        'recent_bills': recent_bills,
        'recent_orders': recent_orders,
    }

    return render(request, 'core/omniful_sync.html', context)


# @login_required
# @require_POST
# def sync_sellers(request):
#     """Sync sellers from Omniful API."""
#     try:
#         call_command('sync_sellers')
#         messages.success(request, _('Sellers synced successfully.'))
#     except Exception as e:
#         messages.error(request, _('Error syncing sellers: {}').format(str(e)))

#     return redirect('core:sellers_list')


@login_required
@require_POST
def sync_sellers(request):
    """Sync sellers from Omniful API and capture logs."""
    stdout = io.StringIO()
    stderr = io.StringIO()

    try:
        call_command('sync_sellers', stdout=stdout, stderr=stderr)
        output = stdout.getvalue()
        messages.success(request, _('Sellers synced successfully.'))

        # Pass the output log to the next request via session
        request.session['sync_logs'] = output

    except Exception as e:
        error_output = stderr.getvalue() + "\n" + str(e)
        messages.error(request, _('Error syncing sellers: {}').format(str(e)))
        request.session['sync_logs'] = error_output

    return redirect('core:sellers_list')


@login_required
@require_POST
def sync_bills(request):
    """Sync Bills from Omniful API and capture logs."""
    stdout = io.StringIO()
    stderr = io.StringIO()

    try:
        # Call the management command with custom stdout and stderr
        call_command('sync_bills', stdout=stdout, stderr=stderr)
        output = stdout.getvalue()

        messages.success(request, _('Bills synced successfully.'))

        # Store the output log in session for display
        request.session['sync_logs'] = output

    except Exception as e:
        error_output = stderr.getvalue() + "\n" + str(e)
        messages.error(request, _('Error syncing bills: {}').format(str(e)))
        request.session['sync_logs'] = error_output

    return redirect('core:bills_list')


@login_required
def refresh_bill(request, bill_name):
    """Refresh specific bill data."""
    try:
        call_command('refresh_bill', bill_name)
        messages.success(request, _(
            'Bill {} refreshed successfully.').format(bill_name))
    except Exception as e:
        messages.error(request, _('Error refreshing bill: {}').format(str(e)))

    return redirect('core:omniful_sync')


@login_required
def sellers_list(request):
    """List all sellers and optionally display sync logs."""
    sellers = Seller.objects.all().order_by('name')
    total_sellers = sellers.count()

    # Get logs from session (set after sync), then clear so they show only once
    sync_logs = request.session.pop('sync_logs', None)

    return render(request, 'core/sellers_list.html', {
        'sellers': sellers,
        'total_sellers': total_sellers,
        'sync_logs': sync_logs,
    })


@login_required
def seller_detail(request, guid):
    """Seller detail page with related bills."""
    seller = get_object_or_404(Seller, guid=guid)
    bills = VendorBill.objects.filter(
        seller=seller).order_by('-created_at_api')

    context = {
        'seller': seller,
        'bills': bills,
        'bills_count': bills.count(),
    }
    return render(request, 'core/seller_detail.html', context)


@login_required
def bills_list(request):
    """List all vendor bills."""
    bills = VendorBill.objects.select_related(
        'seller').order_by('-created_at_api')

    # Extract and remove sync_logs from session (if available)
    sync_logs = request.session.pop('sync_logs', None)

    context = {
        'bills': bills,
        'total_bills': bills.count(),
        'sync_logs': sync_logs,
    }

    return render(request, 'core/bills_list.html', context)


@login_required
def bill_detail(request, name):
    """Bill detail page with full JSON data."""
    bill = get_object_or_404(VendorBill, name=name)
    context = {
        'bill': bill,
    }
    return render(request, 'core/bill_detail.html', context)


@login_required
@require_POST
def refresh_bill_ajax(request, name):
    """Refresh bill data via AJAX."""
    try:
        call_command('refresh_bill', name)
        return JsonResponse({'success': True, 'message': _('Bill refreshed successfully')})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
@require_POST
def update_bill_dates(request):
    """Update bill dates from Omniful API."""
    try:
        limit = int(request.POST.get('limit', 50))
        call_command('fix_bill_dates', limit=limit)
        messages.success(request, _('Bill dates updated successfully.'))
    except Exception as e:
        messages.error(request, _(
            'Error updating bill dates: {}').format(str(e)))

    return redirect('core:bills_list')


@login_required
def fix_all_dates(request):
    """Fix all bill dates with progress tracking."""
    if request.method == 'POST':
        # Start the process in the background
        import subprocess
        import os
        import sys

        python_executable = sys.executable
        manage_py = os.path.join(os.getcwd(), 'manage.py')

        # Run the command in the background
        subprocess.Popen(
            [python_executable, manage_py, 'fix_all_dates'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        messages.success(request, _(
            'Date fix process started. Please check the progress below.'))
        return redirect('core:fix_dates_progress')

    return render(request, 'core/fix_all_dates.html')


@login_required
def fix_dates_progress(request):
    """Show progress of date fixing process."""
    import json
    import os

    progress = {
        'total': 0,
        'processed': 0,
        'success': 0,
        'errors': 0,
        'percentage': 0
    }

    # Try to read progress file
    try:
        if os.path.exists('date_fix_progress.json'):
            with open('date_fix_progress.json', 'r') as f:
                progress = json.load(f)
    except:
        pass

    context = {
        'progress': progress
    }

    return render(request, 'core/fix_dates_progress.html', context)


@login_required
def get_fix_progress(request):
    """AJAX endpoint to get progress data."""
    import json
    import os

    progress = {
        'total': 0,
        'processed': 0,
        'success': 0,
        'errors': 0,
        'percentage': 0,
        'is_complete': False
    }

    # Try to read progress file
    try:
        if os.path.exists('date_fix_progress.json'):
            with open('date_fix_progress.json', 'r') as f:
                data = json.load(f)
                progress.update(data)

                # Check if process is complete
                if data.get('processed', 0) >= data.get('total', 0) and data.get('total', 0) > 0:
                    progress['is_complete'] = True
    except:
        pass

    return JsonResponse(progress)


@login_required
@require_POST
def sync_orders(request):
    """Sync orders from Omniful API and capture logs."""
    stdout = io.StringIO()
    stderr = io.StringIO()

    try:
        call_command('sync_orders', stdout=stdout, stderr=stderr)
        output = stdout.getvalue()
        messages.success(request, _(
            'Orders synced successfully for all sellers.'))

        # Save logs to session for display
        request.session['sync_logs'] = output

    except Exception as e:
        error_output = stderr.getvalue() + "\n" + str(e)
        messages.error(request, _('Error syncing orders: {}').format(str(e)))
        request.session['sync_logs'] = error_output

    return redirect('core:orders_dashboard')


@login_required
@require_POST
def sync_all_orders(request):
    """Sync all orders from Omniful API with progress tracking."""
    seller_code = request.POST.get('seller_code')

    try:
        # Start the process in the background
        import subprocess
        import os
        import sys

        python_executable = sys.executable
        manage_py = os.path.join(os.getcwd(), 'manage.py')

        # Build command arguments
        cmd = [python_executable, manage_py, 'sync_all_orders']
        if seller_code:
            cmd.extend(['--seller_code', seller_code])

        # Run the command in the background
        subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        if seller_code:
            messages.success(request, _(
                'Full order sync started for seller {}. This may take some time.').format(seller_code))
        else:
            messages.success(request, _(
                'Full order sync started for all sellers. This may take some time.'))

        return redirect('core:orders_sync_progress')
    except Exception as e:
        messages.error(request, _(
            'Error starting order sync: {}').format(str(e)))
        return redirect('core:orders_dashboard')


@login_required
def orders_sync_progress(request):
    """Show progress of order syncing process."""
    import json
    import os

    progress = {
        'total_sellers': 0,
        'processed_sellers': 0,
        'total_orders': 0,
        'processed_orders': 0,
        'current_seller': '',
        'current_page': 0,
        'total_pages': 0,
        'percentage': 0,
        'is_complete': False
    }

    # Try to read progress file
    try:
        if os.path.exists('orders_sync_progress.json'):
            with open('orders_sync_progress.json', 'r') as f:
                progress = json.load(f)
    except:
        pass

    context = {
        'progress': progress
    }

    return render(request, 'core/orders_sync_progress.html', context)


@login_required
def get_orders_sync_progress(request):
    """AJAX endpoint to get order sync progress data."""
    import json
    import os

    progress = {
        'total_sellers': 0,
        'processed_sellers': 0,
        'total_orders': 0,
        'processed_orders': 0,
        'current_seller': '',
        'current_page': 0,
        'total_pages': 0,
        'percentage': 0,
        'is_complete': False
    }

    # Try to read progress file
    try:
        if os.path.exists('orders_sync_progress.json'):
            with open('orders_sync_progress.json', 'r') as f:
                progress = json.load(f)
    except:
        pass

    return JsonResponse(progress)


@login_required
def orders_dashboard(request):
    """Main orders KPI dashboard."""
    sync_logs = request.session.pop('sync_logs', None)
    # Get filters
    seller_code = request.GET.get('seller')
    order_type = request.GET.get('type')  # B2B or B2C
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    status = request.GET.get('status')
    payment_mode = request.GET.get('payment_mode')

    # Base queryset
    orders = Order.objects.all()

    # Apply filters
    if seller_code:
        orders = orders.filter(seller__code=seller_code)

    if order_type:
        orders = orders.filter(order_type=order_type)

    if date_from:
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d')
            orders = orders.filter(order_created_at__gte=date_from)
        except:
            pass

    if date_to:
        try:
            date_to = datetime.strptime(date_to, '%Y-%m-%d')
            date_to = date_to.replace(hour=23, minute=59, second=59)
            orders = orders.filter(order_created_at__lte=date_to)
        except:
            pass

    if status:
        orders = orders.filter(status_code=status)

    if payment_mode:
        orders = orders.filter(payment_mode=payment_mode)

    # Calculate KPIs
    total_orders = orders.count()
    b2b_orders = orders.filter(order_type='B2B').count()
    b2c_orders = orders.filter(order_type='B2C').count()

    # Status breakdown
    status_counts = orders.values('status_code').annotate(count=Count('id'))

    # Payment mode breakdown
    payment_counts = orders.values('payment_mode').annotate(count=Count('id'))

    # Delivery time metrics
    avg_delivery_time = orders.exclude(days_to_deliver__isnull=True).aggregate(
        avg=Avg('days_to_deliver'))['avg'] or 0

    # Delay metrics
    delayed_orders = orders.filter(is_delayed=True).count()
    on_time_rate = (total_orders - delayed_orders) / \
        total_orders * 100 if total_orders > 0 else 0

    # Delay categories
    green_orders = orders.filter(delay_category='green').count()
    yellow_orders = orders.filter(delay_category='yellow').count()
    red_orders = orders.filter(delay_category='red').count()

    # New orders delayed (>2 days)
    new_orders_delayed = orders.filter(
        status_code='new_order',
        order_created_at__lt=timezone.now() - timedelta(days=2)
    ).count()

    # Top regions
    top_regions = orders.values('shipping_city').annotate(
        count=Count('id')
    ).order_by('-count')[:5]

    # Recent orders
    recent_orders = orders.order_by('-order_created_at')[:10]

    # Get all sellers for filter dropdown
    sellers = Seller.objects.filter(is_active=True).order_by('name')

    context = {
        'total_orders': total_orders,
        'b2b_orders': b2b_orders,
        'b2c_orders': b2c_orders,
        'status_counts': status_counts,
        'payment_counts': payment_counts,
        'avg_delivery_time': round(avg_delivery_time, 1),
        'delayed_orders': delayed_orders,
        'on_time_rate': round(on_time_rate, 1),
        'green_orders': green_orders,
        'yellow_orders': yellow_orders,
        'red_orders': red_orders,
        'new_orders_delayed': new_orders_delayed,
        'top_regions': top_regions,
        'recent_orders': recent_orders,
        'sellers': sellers,
        'selected_seller': seller_code,
        'selected_type': order_type,
        'selected_status': status,
        'selected_payment': payment_mode,
        'date_from': date_from,
        'date_to': date_to,
        'sync_logs': sync_logs,
    }

    return render(request, 'core/orders_dashboard.html', context)


@login_required
def seller_orders(request, code):
    """Orders dashboard for a specific seller."""
    seller = get_object_or_404(Seller, code=code)

    # Get filters
    order_type = request.GET.get('type')  # B2B or B2C
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    status = request.GET.get('status')
    payment_mode = request.GET.get('payment_mode')

    # Base queryset
    orders = Order.objects.filter(seller=seller)

    # Apply filters
    if order_type:
        orders = orders.filter(order_type=order_type)

    if date_from:
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d')
            orders = orders.filter(order_created_at__gte=date_from)
        except:
            pass

    if date_to:
        try:
            date_to = datetime.strptime(date_to, '%Y-%m-%d')
            date_to = date_to.replace(hour=23, minute=59, second=59)
            orders = orders.filter(order_created_at__lte=date_to)
        except:
            pass

    if status:
        orders = orders.filter(status_code=status)

    if payment_mode:
        orders = orders.filter(payment_mode=payment_mode)

    # Calculate KPIs
    total_orders = orders.count()
    b2b_orders = orders.filter(order_type='B2B').count()
    b2c_orders = orders.filter(order_type='B2C').count()

    # Status breakdown
    status_counts = orders.values('status_code').annotate(count=Count('id'))

    # Payment mode breakdown
    payment_counts = orders.values('payment_mode').annotate(count=Count('id'))

    # Delivery time metrics
    avg_delivery_time = orders.exclude(days_to_deliver__isnull=True).aggregate(
        avg=Avg('days_to_deliver'))['avg'] or 0

    # Delay metrics
    delayed_orders = orders.filter(is_delayed=True).count()
    on_time_rate = (total_orders - delayed_orders) / \
        total_orders * 100 if total_orders > 0 else 0

    # Delay categories
    green_orders = orders.filter(delay_category='green').count()
    yellow_orders = orders.filter(delay_category='yellow').count()
    red_orders = orders.filter(delay_category='red').count()

    # New orders delayed (>2 days)
    new_orders_delayed = orders.filter(
        status_code='new_order',
        order_created_at__lt=timezone.now() - timedelta(days=2)
    ).count()

    # Top regions
    top_regions = orders.values('shipping_city').annotate(
        count=Count('id')
    ).order_by('-count')[:5]

    # Recent orders
    recent_orders = orders.order_by('-order_created_at')[:20]

    context = {
        'seller': seller,
        'total_orders': total_orders,
        'b2b_orders': b2b_orders,
        'b2c_orders': b2c_orders,
        'status_counts': status_counts,
        'payment_counts': payment_counts,
        'avg_delivery_time': round(avg_delivery_time, 1),
        'delayed_orders': delayed_orders,
        'on_time_rate': round(on_time_rate, 1),
        'green_orders': green_orders,
        'yellow_orders': yellow_orders,
        'red_orders': red_orders,
        'new_orders_delayed': new_orders_delayed,
        'top_regions': top_regions,
        'recent_orders': recent_orders,
        'selected_type': order_type,
        'selected_status': status,
        'selected_payment': payment_mode,
        'date_from': date_from,
        'date_to': date_to,
    }

    return render(request, 'core/seller_orders.html', context)


@login_required
def order_detail(request, order_id):
    """Order detail view."""
    order = get_object_or_404(Order, order_id=order_id)

    context = {
        'order': order,
        'raw_data': json.dumps(order.raw_data, indent=2),
    }

    return render(request, 'core/order_detail.html', context)


@login_required
def customer_orders(request):
    """Customer orders analytics."""
    # Get filters
    seller_code = request.GET.get('seller')
    order_type = request.GET.get('type')  # B2B or B2C
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    # Base queryset
    orders = Order.objects.all()

    # Apply filters
    if seller_code:
        orders = orders.filter(seller__code=seller_code)

    if order_type:
        orders = orders.filter(order_type=order_type)

    if date_from:
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d')
            orders = orders.filter(order_created_at__gte=date_from)
        except:
            pass

    if date_to:
        try:
            date_to = datetime.strptime(date_to, '%Y-%m-%d')
            date_to = date_to.replace(hour=23, minute=59, second=59)
            orders = orders.filter(order_created_at__lte=date_to)
        except:
            pass

    # Customer metrics
    customer_metrics = orders.values(
        'customer_first_name', 'customer_last_name', 'customer_email'
    ).annotate(
        order_count=Count('id'),
        avg_delivery_time=Avg('days_to_deliver'),
        delayed_orders=Count(Case(When(is_delayed=True, then=1))),
        total_spent=Sum('total')
    ).order_by('-order_count')[:50]

    # Get all sellers for filter dropdown
    sellers = Seller.objects.filter(is_active=True).order_by('name')

    context = {
        'customer_metrics': customer_metrics,
        'sellers': sellers,
        'selected_seller': seller_code,
        'selected_type': order_type,
        'date_from': date_from,
        'date_to': date_to,
    }

    return render(request, 'core/customer_orders.html', context)


@login_required
def sellers_kpi_dashboard(request):
    """Sellers KPI Dashboard with key metrics."""
    # Basic counts
    total_sellers = Seller.objects.count()
    total_bills = VendorBill.objects.count()

    # Seller aggregations
    seller_totals = VendorBill.objects.values('seller__name', 'seller__guid').annotate(
        total_amount=Sum('grand_total'),
        bill_count=Count('name')
    ).order_by('-total_amount')

    # Top and lowest sellers
    top_seller = seller_totals.first() if seller_totals else None
    lowest_seller = seller_totals.last() if seller_totals else None

    # Last bill paid
    last_paid_bill = VendorBill.objects.filter(
        status__in=['paid', 'approved']
    ).order_by('-created_at_api').first()

    # Unpaid sellers count
    unpaid_sellers = VendorBill.objects.filter(
        status__in=['draft', 'pending']
    ).values('seller').distinct().count()

    # Average bill per seller
    avg_bill_amount = VendorBill.objects.filter(
        grand_total__gt=0
    ).aggregate(avg=Avg('grand_total'))['avg'] or 0

    # Most active seller
    most_active_seller = seller_totals.order_by(
        '-bill_count').first() if seller_totals else None

    # Oldest unpaid bill
    oldest_bill = VendorBill.objects.filter(
        status__in=['draft', 'pending']
    ).order_by('created_at_api').first()

    # Bills with detailed data
    bills_with_data = VendorBill.objects.filter(grand_total__gt=0).count()

    context = {
        'total_sellers': total_sellers,
        'total_bills': total_bills,
        'top_seller': top_seller,
        'lowest_seller': lowest_seller,
        'last_paid_bill': last_paid_bill,
        'unpaid_sellers': unpaid_sellers,
        'avg_bill_amount': avg_bill_amount,
        'most_active_seller': most_active_seller,
        'oldest_bill': oldest_bill,
        'bills_with_data': bills_with_data,
        'seller_totals': seller_totals[:10],
    }

    return render(request, 'core/sellers_kpi_dashboard.html', context)
