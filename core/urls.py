"""
URL configuration for core app.
"""

from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('profile/', views.profile, name='profile'),
    path('omniful/', views.omniful_sync, name='omniful_sync'),
    path('sync-sellers/', views.sync_sellers, name='sync_sellers'),
    path('sync-bills/', views.sync_bills, name='sync_bills'),
    path('refresh-bill/<str:bill_name>/', views.refresh_bill, name='refresh_bill'),
    path('sellers/', views.sellers_list, name='sellers_list'),
    path('sellers-dashboard/', views.sellers_kpi_dashboard, name='sellers_kpi_dashboard'),
    path('sellers/<str:guid>/', views.seller_detail, name='seller_detail'),
    path('bills/', views.bills_list, name='bills_list'),
    path('bills/<str:name>/', views.bill_detail, name='bill_detail'),
    path('api/refresh-bill/<str:name>/', views.refresh_bill_ajax, name='refresh_bill_ajax'),
    path('update-bill-dates/', views.update_bill_dates, name='update_bill_dates'),
    path('fix-all-dates/', views.fix_all_dates, name='fix_all_dates'),
    path('fix-dates-progress/', views.fix_dates_progress, name='fix_dates_progress'),
    path('api/fix-progress/', views.get_fix_progress, name='get_fix_progress'),
    path('sync-orders/', views.sync_orders, name='sync_orders'),
    path('sync-all-orders/', views.sync_all_orders, name='sync_all_orders'),

    path('orders-dashboard/', views.orders_dashboard, name='orders_dashboard'),
    path('orders-sync-progress/', views.orders_sync_progress, name='orders_sync_progress'),
    path('api/orders-sync-progress/', views.get_orders_sync_progress, name='get_orders_sync_progress'),
    path('seller-orders/<str:code>/', views.seller_orders, name='seller_orders'),
    path('order-detail/<str:order_id>/', views.order_detail, name='order_detail'),
    path('customer-orders/', views.customer_orders, name='customer_orders'),
]