'''
Management command to sync orders from Omniful API.
'''

import requests
import time
import uuid
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Seller, Order
from decouple import config


class Command(BaseCommand):
    help = 'Sync orders from Omniful API for all sellers'

    def handle(self, *args, **options):
        token = config('OMNIFUL_ACCESS_TOKEN', default='')

        if not token:
            self.stdout.write(self.style.ERROR(
                'OMNIFUL_ACCESS_TOKEN not configured'))
            return

        headers = {
            'Authorization': f'Bearer {token}'
        }

        # Step 1: Sync Sellers
        sellers = []
        page = 1
        while True:
            seller_url = f'https://prodapi.omniful.com/sales-channel/public/v1/tenants/sellers?page={page}&per_page=100'
            try:
                response = requests.get(
                    seller_url, headers=headers, timeout=30)
                response.raise_for_status()
                data = response.json()

                seller_list = data.get('data', [])
                meta = data.get('meta', {})
                current_page = meta.get('current_page', page)
                last_page = meta.get('last_page', 1)

                if not seller_list:
                    self.stdout.write(f'No more sellers found on page {page}')
                    break

                self.stdout.write(
                    f'Syncing {len(seller_list)} sellers from page {page}')

                for seller_data in seller_list:
                    seller_code = seller_data.get('code')
                    seller_name = seller_data.get('name')
                    if not seller_code or not seller_name:
                        continue

                    seller, created = Seller.objects.update_or_create(
                        code=seller_code,
                        defaults={
                            'name': seller_name,
                            'guid': str(uuid.uuid4()),
                            'is_active': True,
                            'created_at_api': timezone.now(),
                            'updated_at_api': timezone.now(),
                        }
                    )
                    sellers.append(seller)
                    if created:
                        self.stdout.write(self.style.SUCCESS(
                            f'Created new seller: {seller.name}'))
                    else:
                        self.stdout.write(f'Updated seller: {seller.name}')

                if current_page >= last_page:
                    break

                page += 1

            except requests.RequestException as e:
                self.stdout.write(self.style.ERROR(
                    f'Failed to fetch sellers: {str(e)}'))
                break

        # Step 2: Sync Orders for each Seller
        total_orders = 0

        for seller in sellers:
            if not seller.code:
                self.stdout.write(f'Skipping seller {seller.name} - no code')
                continue

            self.stdout.write(
                f'Syncing orders for seller {seller.name} ({seller.code})')
            page = 1

            while True:
                orders_url = f'https://prodapi.omniful.com/sales-channel/public/v1/tenants/sellers/{seller.code}/orders?page={page}&per_page=100'
                try:
                    response = requests.get(
                        orders_url, headers=headers, timeout=30)
                    response.raise_for_status()
                    data = response.json()

                    orders = data.get('data', [])
                    meta = data.get('meta', {})
                    current_page = meta.get('current_page', page)
                    last_page = meta.get('last_page', 1)

                    if not orders:
                        self.stdout.write(
                            f'No orders found for {seller.name} on page {page}')
                        break

                    for order_data in orders:
                        order_id = order_data.get('order_id')
                        omniful_id = order_data.get('id')

                        if not order_id or not omniful_id:
                            continue

                        try:
                            order_created_at = datetime.fromisoformat(
                                order_data['order_created_at'].replace('Z', '+00:00'))
                        except:
                            order_created_at = timezone.now()

                        shipment = order_data.get('shipment', {})
                        delivery_status = shipment.get('delivery_status', '')

                        try:
                            delivery_date = datetime.fromisoformat(shipment.get('order_delivered_at', '').replace(
                                'Z', '+00:00')) if shipment.get('order_delivered_at') else None
                        except:
                            delivery_date = None

                        customer = order_data.get('customer', {})
                        billing = order_data.get('billing_address', {})
                        shipping = order_data.get('shipping_address', {})

                        order, created = Order.objects.update_or_create(
                            omniful_id=omniful_id,
                            defaults={
                                'order_id': order_id,
                                'order_alias': order_data.get('order_alias', ''),
                                'seller': seller,
                                'seller_code': order_data.get('seller_code', ''),
                                'store_name': order_data.get('store_name', ''),
                                'status_code': order_data.get('status_code', ''),
                                'source': order_data.get('source', ''),
                                'order_type': order_data.get('type', 'B2C'),
                                'delivery_type': order_data.get('delivery_type', ''),
                                'order_created_at': order_created_at,
                                'created_at_api': order_created_at,
                                'delivery_date': delivery_date,
                                'payment_mode': order_data.get('payment_mode', ''),
                                'payment_method': order_data.get('payment_method', ''),
                                'total': order_data.get('total', 0),
                                'billing_address': billing,
                                'shipping_address': shipping,
                                'shipping_city': shipping.get('city', ''),
                                'shipping_region': shipping.get('state', ''),
                                'shipping_country': shipping.get('country', ''),
                                'customer': customer,
                                'customer_first_name': customer.get('first_name', ''),
                                'customer_last_name': customer.get('last_name', ''),
                                'customer_email': customer.get('email', ''),
                                'customer_phone': customer.get('phone', ''),
                                'shipment': shipment,
                                'delivery_status': delivery_status,
                                'tracking_url': shipment.get('tracking_url', ''),
                                'shipment_type': order_data.get('shipment_type', ''),
                                'require_shipping': order_data.get('require_shipping', True),
                                'cancel_order_after_seconds': order_data.get('cancel_order_after_seconds', 0),
                                'expected_delivery_epoch': order_data.get('expected_delivery_epoch', 0),
                                'invoice': order_data.get('invoice', {}),
                                'raw_data': order_data
                            }
                        )

                        if created:
                            self.stdout.write(
                                f'  Created order: {order.order_id}')
                        else:
                            self.stdout.write(
                                f'  Updated order: {order.order_id}')

                        total_orders += 1

                    if current_page >= last_page:
                        break
                    page += 1

                except requests.RequestException as e:
                    self.stdout.write(self.style.ERROR(
                        f'Failed to fetch orders for {seller.name}: {str(e)}'))
                    break

        self.stdout.write(self.style.SUCCESS(
            f'Total synced orders: {total_orders}'))
