from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Seller, VendorBill, SyncStatus, SyncLog
from decouple import config
from datetime import datetime
import requests
import traceback


class Command(BaseCommand):
    help = 'Sync vendor bills from Omniful API for sellers returned by API'

    API_DATE_FORMAT = "%b %d, %Y %I:%M:%S %p"

    def handle(self, *args, **options):
        log_lines = []
        stdout = options.get('stdout', self.stdout)

        def log(msg):
            log_lines.append(msg)
            stdout.write(msg + '\n')
            stdout.flush()

        def parse_date_str(date_str):
            if not date_str or date_str.strip() == "":
                return None
            try:
                dt_obj = datetime.strptime(date_str, self.API_DATE_FORMAT)
                return timezone.make_aware(dt_obj)
            except ValueError:
                log(f"⚠️ Could not parse date '{date_str}'")
                return None

        token = config('OMNIFUL_ACCESS_TOKEN', default='')
        if not token:
            log('❌ OMNIFUL_ACCESS_TOKEN not configured.')
            return

        headers = {'Authorization': f'Bearer {token}'}

        total_created = total_updated = total_synced = 0

        # Step 1: Fetch all sellers from API
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
                    break

                for s in seller_data_list:
                    if not s.get('name'):
                        continue
                    try:
                        seller = Seller.objects.get(name=s['name'])
                        sellers.append(seller)
                    except Seller.DoesNotExist:
                        log(f"❌ Seller '{s['name']}' not found in DB. Skipping.")
                        continue

                if current_page >= last_page:
                    break
                page += 1

            except requests.RequestException as e:
                log(f"❌ Failed to fetch sellers: {str(e)}")
                return

        # Step 2: Sync bills for each seller
        total_synced = 0
        for seller in sellers:
            page = 1
            while True:
                bills_url = f'https://prodapi.omniful.com/sales-channel/public/v1/tenants/bills?page={page}&per_page=100'
                try:
                    log(f"🌐 Fetching bills page {page} for seller {seller.name}")
                    response = requests.get(
                        bills_url, headers=headers, timeout=30)
                    response.raise_for_status()
                    data = response.json()

                    bills = data.get('data', [])
                    meta = data.get('meta', {})
                    current_page = meta.get('current_page', page)
                    last_page = meta.get('last_page', 1)

                    if not bills:
                        log("✅ No bills found")
                        break

                    for bill_data in bills:
                        seller_data = bill_data.get('seller', {})
                        if seller_data.get('name') != seller.name:
                            continue

                        bill_name = bill_data.get('name')
                        if not bill_name:
                            continue

                        detail_url = f"https://prodapi.omniful.com/sales-channel/public/v1/tenants/bills/{bill_name}"
                        detail_response = requests.get(
                            detail_url, headers=headers, timeout=20)
                        if detail_response.status_code != 200:
                            log(
                                f"❌ Failed to fetch details for bill {bill_name}")
                            continue

                        bill_detail = detail_response.json().get('data', {})

                        bill, created = VendorBill.objects.update_or_create(
                            name=bill_name,
                            defaults={
                                'seller': seller,
                                'hubs': bill_data.get('hubs', []),
                                'status': bill_data.get('status', ''),
                                'pdf': bill_data.get('pdf', ''),
                                'contract_name': bill_data.get('contract_name', ''),
                                'period_start_date': parse_date_str(bill_data.get('period_start_date')),
                                'period_end_date': parse_date_str(bill_data.get('period_end_date')),
                                'due_date': parse_date_str(bill_data.get('due_date')),
                                'created_at_api': parse_date_str(bill_data.get('created_at')),
                                'currency': bill_data.get('currency', 'SAR'),
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
                            total_created += 1
                            log(f'🧾 Created Bill: {bill.name}')
                        else:
                            total_updated += 1
                            log(f'🔁 Updated Bill: {bill.name}')

                        total_synced += 1

                    if current_page >= last_page:
                        break
                    page += 1

                except requests.RequestException as e:
                    log(f"❌ API request failed: {str(e)}")
                    break
                except Exception as e:
                    log(f"🔥 Unexpected error: {str(e)}")
                    log(traceback.format_exc())
                    break

        log(f"\n✅ Successfully synced {total_synced} bills")

        # Save sync timestamp
        SyncStatus.objects.update_or_create(
            key='vendor_bills',
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
            key='vendor_bills',
            defaults={'content': '\n'.join(log_lines)}
        )
