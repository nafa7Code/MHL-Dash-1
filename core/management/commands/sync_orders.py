from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Seller, Order, SyncStatus, SyncLog
from decouple import config
from datetime import datetime
import requests
import traceback


class Command(BaseCommand):
    help = 'Sync orders from Omniful API for all sellers'

    def handle(self, *args, **options):
        log_lines = []
        stdout = options.get('stdout', self.stdout)

        def log(msg):
            log_lines.append(msg)
            stdout.write(msg + "\n")
            stdout.flush()

        token = config('OMNIFUL_ACCESS_TOKEN', default='')
        if not token:
            log("❌ OMNIFUL_ACCESS_TOKEN not set in .env file")
            return

        total_created = total_updated = total_synced = 0
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

        # Step 1: Fetch all sellers
        sellers = []
        page = 1
        while True:
            url = f'https://prodapi.omniful.com/sales-channel/public/v1/tenants/sellers?page={page}&per_page=100'
            try:
                log(f"🌐 Fetching sellers from page {page}")
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                data = response.json()

                seller_data_list = data.get('data', [])
                meta = data.get('meta', {})
                current_page = meta.get('current_page', page)
                last_page = meta.get('last_page', page)

                if not seller_data_list:
                    log("✅ No more sellers found.")
                    break

                for s in seller_data_list:
                    if not s.get('code') or not s.get('name'):
                        continue
                    seller, _ = Seller.objects.get_or_create(
                        code=s['code'], defaults={'name': s['name']})
                    sellers.append(seller)

                if current_page >= last_page:
                    break
                page += 1

            except requests.RequestException as e:
                log(f"❌ Failed to fetch sellers: {str(e)}")
                return

        # Step 2: Fetch orders for each seller
<< << << < HEAD
       total_created = total_updated = total_synced = 0
== == == =
>>>>>> > 8da4d44(update Ui/Ux, remove unnecessary buttons, update orders logic, accurate dummy data)

       for seller in sellers:
            if not seller.code:
                log(f"⚠️ Skipping seller with missing code: {seller.name}")
                continue

            page = 1
            log(f"📦 Syncing orders for seller: {seller.name} ({seller.code})")

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
                        log(f"✅ No orders for {seller.name} on page {page}")
                        break

                    for order_data in orders:
                        omniful_id = order_data.get('id')
                        order_id = order_data.get('order_id')

                        if not order_id or not omniful_id:
                            continue

                        try:
                            order_created_at = datetime.fromisoformat(
                                order_data.get('order_created_at', '').replace('Z', '+00:00'))
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
                                'raw_data': order_data,
                            }
                        )

                        if created:
                            total_created += 1
                            log(
                                f'🆕 Created Order: {order.order_id} (Omniful ID: {order.omniful_id})')
                        else:
                            total_updated += 1
                            log(
                                f'♻️ Updated Order: {order.order_id} (Omniful ID: {order.omniful_id})')

                        total_synced += 1

                    if current_page >= last_page:
                        break
                    page += 1

                except requests.RequestException as e:
                    log(f"❌ Failed to fetch orders for {seller.name}: {str(e)}")
                    break
                except Exception as e:
                    log(f"🔥 Error syncing order: {str(e)}")
                    log(traceback.format_exc())
                    break

        log(f"\n✅ Orders sync completed. Total orders synced: {total_synced}")

        # Save sync status timestamp
        SyncStatus.objects.update_or_create(
            key='orders',
            defaults={'last_synced_at': timezone.now()}
        )

        summary = (
            f"\n✅ Sync Complete!\n"
            f"Created: {total_created}\n"
            f"Updated: {total_updated}\n"
            f"Total Synced: {total_synced}"
        )
        log(summary)

        # Save logs to DB
        SyncLog.objects.update_or_create(
            key='orders',
            defaults={'content': '\n'.join(log_lines)}
        )
