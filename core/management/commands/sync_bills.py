"""
Management command to sync vendor bills from Omniful API.
"""

import requests
import uuid
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from core.models import Seller, VendorBill
from decouple import config


class Command(BaseCommand):
    help = 'Sync vendor bills from Omniful API'

    API_DATE_FORMAT = "%b %d, %Y %I:%M:%S %p"

    def add_arguments(self, parser):
        parser.add_argument('--log_id', type=int, help='SyncLog ID')

    def handle(self, *args, **options):
        from core.models import SyncLog
        import time

        log_id = options.get('log_id')
        log_obj = SyncLog.objects.filter(id=log_id).first()

        def log_line(text):
            self.stdout.write(text)
            if log_obj:
                log_obj.log += text + "\n"
                log_obj.save(update_fields=["log"])

        token = config('OMNIFUL_ACCESS_TOKEN', default='')
        if not token:
            log_line('❌ OMNIFUL_ACCESS_TOKEN not configured.')
            log_obj.completed = True
            log_obj.save(update_fields=["completed", "log"])
            return

        headers = {
            'Authorization': f'Bearer {token}'
        }

        page = 1
        total_synced = 0

        def parse_date_str(date_str):
            if not date_str or date_str.strip() == "":
                return None
            try:
                dt_obj = datetime.strptime(date_str, self.API_DATE_FORMAT)
                return timezone.make_aware(dt_obj)
            except ValueError:
                log_line(f"⚠️ Could not parse date '{date_str}'")
                return None

        while True:
            url = f'https://prodapi.omniful.com/sales-channel/public/v1/tenants/bills?page={page}&per_page=100'

            try:
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                data = response.json()

                bills = data.get('data', [])
                meta = data.get('meta', {})

                if not bills:
                    log_line(f'🚫 No more bills found on page {page}')
                    break

                log_line(f'📦 Processing page {page} with {len(bills)} bills')

                current_page = meta.get('current_page', page)
                last_page = meta.get('last_page', 1)

                for bill_data in bills:
                    bill_name = bill_data.get('name')
                    if not bill_name:
                        log_line("🚫 Skipping bill with no 'name'")
                        continue

                    detail_url = f'https://prodapi.omniful.com/sales-channel/public/v1/tenants/bills/{bill_name}?page=1&per_page=30'
                    detail_response = requests.get(
                        detail_url, headers=headers, timeout=20)
                    if detail_response.status_code != 200:
                        log_line(
                            f"❌ Failed to fetch details for bill '{bill_name}'")
                        continue

                    bill_detail = detail_response.json().get('data', {})

                    seller_api_data = bill_data.get('seller')
                    seller_instance = None
                    if seller_api_data and 'name' in seller_api_data:
                        seller_name = seller_api_data['name']
                        try:
                            seller_instance = Seller.objects.get(
                                name=seller_name)
                        except Seller.DoesNotExist:
                            log_line(
                                f"🆕 Seller '{seller_name}' not found for bill '{bill_name}', Creating new seller...")
                            try:
                                seller_instance = Seller.objects.create(
                                    name=seller_name,
                                    guid=str(uuid.uuid4()),
                                    created_at_api=timezone.now(),
                                    updated_at_api=timezone.now(),
                                )
                                log_line(
                                    f"✅ Created new Seller: {seller_name}")
                            except Exception as e:
                                log_line(
                                    f"❌ Failed to create seller '{seller_name}': {str(e)}")
                                continue

                    if not seller_instance:
                        log_line(
                            f"❌ Skipping bill '{bill_name}' due to missing seller")
                        continue

                    period_start_date = parse_date_str(
                        bill_data.get('period_start_date'))
                    period_end_date = parse_date_str(
                        bill_data.get('period_end_date'))
                    due_date = parse_date_str(bill_data.get('due_date'))
                    created_at_api = parse_date_str(
                        bill_data.get('created_at'))

                    bill, created = VendorBill.objects.update_or_create(
                        name=bill_name,
                        defaults={
                            'seller': seller_instance,
                            'hubs': bill_data.get('hubs', []),
                            'status': bill_data.get('status', ''),
                            'pdf': bill_data.get('pdf', ''),
                            'contract_name': bill_data.get('contract_name', ''),
                            'period_start_date': period_start_date,
                            'period_end_date': period_end_date,
                            'due_date': due_date,
                            'created_at_api': created_at_api,
                            'currency': bill_data.get('currency', 'USD'),
                            'grand_total': bill_detail.get('grand_total', 0),
                            'discount': bill_data.get('discount', 0),
                            'grand_total_after_discount': bill_data.get('grand_total_after_discount', 0),
                            'finalised_on': parse_date_str(bill_data.get('finalised_on')),
                            'finalised_by': bill_data.get('finalised_by', ''),
                            'remark': bill_data.get('remark', ''),
                            'fees': bill_data.get('fees', []),
                            'hub_bills': bill_data.get('hub_bills', []),
                            'created_at_local': timezone.now(),
                            'updated_at_local': timezone.now(),
                        }
                    )

                    if created:
                        log_line(f'🧾 Created bill: {bill.name}')
                    else:
                        log_line(f'🔄 Updated bill: {bill.name}')

                    total_synced += 1

                if current_page >= last_page:
                    log_line(f'✅ Completed processing last page ({last_page})')
                    break

                page += 1

                if page > 1000:
                    log_line('⚠️ Reached page limit (1000), stopping')
                    break

            except requests.RequestException as e:
                log_line(f'❌ API request failed: {str(e)}')
                break
            except Exception as e:
                log_line(f'❌ Error processing data: {str(e)}')
                break

        log_line(f'✅ Successfully synced {total_synced} bills')
        if log_obj:
            log_obj.completed = True
            log_obj.save(update_fields=["completed"])

            # if log_obj:
            #     log_obj.completed = True
            #     log_obj.save(update_fields=["completed"])
            #     time.sleep(3)  # Allow frontend polling to finish
            #     log_obj.delete()
