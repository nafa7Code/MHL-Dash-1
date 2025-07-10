"""
Management command to sync all orders from Omniful API with progress tracking.
"""

import requests
import time
import json
import os
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Seller, Order
from decouple import config


class Command(BaseCommand):
    help = 'Sync all orders from Omniful API with progress tracking'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--seller_code',
            type=str,
            help='Sync orders for a specific seller code',
        )
        parser.add_argument(
            '--per_page',
            type=int,
            default=100,
            help='Number of orders per page (default: 100)',
        )
        parser.add_argument(
            '--sleep',
            type=float,
            default=0.5,
            help='Sleep time between API calls in seconds (default: 0.5)',
        )
        parser.add_argument(
            '--progress_file',
            type=str,
            default='orders_sync_progress.json',
            help='File to store progress information',
        )
    
    def handle(self, *args, **options):
        token = config('OMNIFUL_ACCESS_TOKEN', default='')
        
        if not token:
            self.stdout.write(self.style.ERROR('OMNIFUL_ACCESS_TOKEN not configured'))
            return
        
        headers = {
            'Authorization': f'Bearer {token}'
        }
        
        # Get sellers to process
        if options['seller_code']:
            try:
                sellers = [Seller.objects.get(code=options['seller_code'])]
                self.stdout.write(f'Processing single seller: {sellers[0].name}')
            except Seller.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Seller with code {options["seller_code"]} not found'))
                return
        else:
            sellers = Seller.objects.filter(is_active=True)
            self.stdout.write(f'Processing {len(sellers)} active sellers')
        
        total_orders = 0
        per_page = options['per_page']
        sleep_time = options['sleep']
        progress_file = options['progress_file']
        
        # Initialize progress tracking
        progress = {
            'total_sellers': len(sellers),
            'processed_sellers': 0,
            'total_orders': 0,
            'processed_orders': 0,
            'current_seller': '',
            'current_page': 0,
            'total_pages': 0,
            'percentage': 0,
            'is_complete': False
        }
        
        # Save initial progress
        self._save_progress(progress, progress_file)
        
        for seller in sellers:
            if not seller.code:
                self.stdout.write(f'Skipping seller {seller.name} - no code available')
                continue
                
            self.stdout.write(f'Fetching orders for seller: {seller.name} (code: {seller.code})')
            
            # Update progress
            progress['current_seller'] = seller.name
            progress['current_page'] = 0
            self._save_progress(progress, progress_file)
            
            # First, get the total number of orders for this seller
            url = f'https://prodapi.omniful.com/sales-channel/public/v1/tenants/sellers/{seller.code}/orders?page=1&per_page={per_page}'
            
            try:
                response = requests.get(url, headers=headers, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    meta = data.get('meta', {})
                    seller_total_orders = meta.get('total', 0)
                    last_page = meta.get('last_page', 1)
                    
                    self.stdout.write(f'  Total orders for {seller.name}: {seller_total_orders} (Pages: {last_page})')
                    
                    # Update progress
                    progress['total_orders'] += seller_total_orders
                    progress['total_pages'] = last_page
                    self._save_progress(progress, progress_file)
                else:
                    self.stdout.write(self.style.ERROR(f'  Failed to get total orders for {seller.name}'))
                    continue
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  Error getting total orders: {str(e)}'))
                continue
            
            page = 1
            seller_orders = 0
            
            while True:
                url = f'https://prodapi.omniful.com/sales-channel/public/v1/tenants/sellers/{seller.code}/orders?page={page}&per_page={per_page}'
                
                try:
                    self.stdout.write(f'  Requesting page {page} of {last_page}...')
                    
                    # Update progress
                    progress['current_page'] = page
                    self._save_progress(progress, progress_file)
                    
                    response = requests.get(url, headers=headers, timeout=30)
                    
                    if response.status_code != 200:
                        self.stdout.write(self.style.ERROR(f'  API request failed with status code: {response.status_code}'))
                        self.stdout.write(f'  Response: {response.text[:200]}')
                        break
                    
                    data = response.json()
                    
                    orders = data.get('data', [])
                    meta = data.get('meta', {})
                    
                    if not orders:
                        self.stdout.write(f'  No orders found for {seller.name} on page {page}')
                        break
                    
                    self.stdout.write(f'  Processing {len(orders)} orders from page {page}')
                    
                    # Process orders in batches for better performance
                    batch_size = 20
                    for i in range(0, len(orders), batch_size):
                        batch = orders[i:i+batch_size]
                        self.stdout.write(f'  Processing batch {i//batch_size + 1} of {(len(orders) + batch_size - 1) // batch_size}')
                        
                        for order_data in batch:
                            # Extract order details
                            order_id = order_data.get('order_id')
                            omniful_id = order_data.get('id')
                            
                            if not order_id or not omniful_id:
                                continue
                            
                            # Parse dates
                            order_created_at = None
                            if order_data.get('order_created_at'):
                                try:
                                    # Fix common ISO format issues
                                    date_str = order_data['order_created_at']
                                    if 'Z' in date_str:
                                        date_str = date_str.replace('Z', '+00:00')
                                    # Fix milliseconds format if needed
                                    if '+00:00' in date_str and '.' in date_str:
                                        parts = date_str.split('.')
                                        if len(parts) == 2:
                                            ms_part = parts[1].split('+')[0]
                                            if len(ms_part) < 6:
                                                # Pad with zeros to get microseconds
                                                ms_part = ms_part.ljust(6, '0')
                                            date_str = f"{parts[0]}.{ms_part}+00:00"
                                    
                                    order_created_at = datetime.fromisoformat(date_str)
                                except Exception as e:
                                    order_created_at = timezone.now()
                            
                            # Get delivery date if available
                            delivery_date = None
                            delivery_status = None
                            shipment = order_data.get('shipment', {})
                            if shipment:
                                delivery_status = shipment.get('delivery_status')
                                # If there's a delivery timestamp, use it
                                if shipment.get('delivery_timestamp'):
                                    try:
                                        # Fix common ISO format issues
                                        date_str = shipment['delivery_timestamp']
                                        if 'Z' in date_str:
                                            date_str = date_str.replace('Z', '+00:00')
                                        # Fix milliseconds format if needed
                                        if '+00:00' in date_str and '.' in date_str:
                                            parts = date_str.split('.')
                                            if len(parts) == 2:
                                                ms_part = parts[1].split('+')[0]
                                                if len(ms_part) < 6:
                                                    # Pad with zeros to get microseconds
                                                    ms_part = ms_part.ljust(6, '0')
                                                date_str = f"{parts[0]}.{ms_part}+00:00"
                                        
                                        delivery_date = datetime.fromisoformat(date_str)
                                    except Exception as e:
                                        pass
                            
                            # Extract customer info
                            customer = order_data.get('customer', {})
                            customer_first_name = customer.get('first_name', '')
                            customer_last_name = customer.get('last_name', '')
                            customer_email = customer.get('email')
                            customer_phone = customer.get('phone')
                            
                            # Extract shipping address
                            shipping_address = order_data.get('shipping_address', {})
                            shipping_city = shipping_address.get('city', '')
                            shipping_region = shipping_address.get('region', '')
                            shipping_country = shipping_address.get('country', '')
                            
                            # Create or update order
                            try:
                                order, created = Order.objects.update_or_create(
                                    omniful_id=omniful_id,
                                    defaults={
                                        'order_id': order_id,
                                        'seller': seller,
                                        'store_name': order_data.get('store_name', ''),
                                        'status_code': order_data.get('status_code', ''),
                                        'order_type': order_data.get('type', 'B2C'),
                                        'delivery_type': order_data.get('delivery_type', ''),
                                        'order_created_at': order_created_at or timezone.now(),
                                        'delivery_date': delivery_date,
                                        'payment_mode': order_data.get('payment_mode', ''),
                                        'payment_method': order_data.get('payment_method', ''),
                                        'total': order_data.get('total', 0),
                                        'customer_first_name': customer_first_name,
                                        'customer_last_name': customer_last_name,
                                        'customer_email': customer_email,
                                        'customer_phone': customer_phone,
                                        'shipping_city': shipping_city,
                                        'shipping_region': shipping_region,
                                        'shipping_country': shipping_country,
                                        'delivery_status': delivery_status,
                                        'raw_data': order_data,
                                    }
                                )
                                
                                seller_orders += 1
                                progress['processed_orders'] += 1
                                
                                # Update progress percentage
                                if progress['total_orders'] > 0:
                                    progress['percentage'] = round((progress['processed_orders'] / progress['total_orders']) * 100, 1)
                                
                                # Save progress periodically
                                if seller_orders % 50 == 0:
                                    self._save_progress(progress, progress_file)
                                    
                            except Exception as e:
                                self.stdout.write(self.style.ERROR(f'    Error saving order {order_id}: {str(e)}'))
                    
                    # Check if this is the last page
                    current_page = meta.get('current_page', page)
                    last_page = meta.get('last_page', 1)
                    
                    if current_page >= last_page:
                        self.stdout.write(f'  Reached last page ({last_page}) for {seller.name}')
                        break
                    
                    page += 1
                    
                    # Sleep to avoid overwhelming the API
                    if sleep_time > 0:
                        time.sleep(sleep_time)
                    
                except requests.RequestException as e:
                    self.stdout.write(self.style.ERROR(f'  API request failed: {str(e)}'))
                    if hasattr(e, 'response') and e.response is not None:
                        self.stdout.write(f'  Response status: {e.response.status_code}')
                        self.stdout.write(f'  Response text: {e.response.text[:200]}')
                    break
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  Error processing data: {str(e)}'))
                    break
            
            self.stdout.write(f'Synced {seller_orders} orders for {seller.name}')
            total_orders += seller_orders
            
            # Update progress for completed seller
            progress['processed_sellers'] += 1
            self._save_progress(progress, progress_file)
        
        # Mark as complete
        progress['is_complete'] = True
        self._save_progress(progress, progress_file)
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully synced {total_orders} orders for {len(sellers)} sellers')
        )
    
    def _save_progress(self, progress, filename):
        """Save progress information to a file."""
        try:
            with open(filename, 'w') as f:
                json.dump(progress, f)
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Error saving progress: {str(e)}'))