# sync_sellers.py
from core.models import Seller, SyncLog  # Ensure SyncLog is imported
from django.core.management.base import BaseCommand
from decouple import config
from dateutil import parser
import requests


class Command(BaseCommand):
    help = 'Sync sellers from Omniful API'

    def add_arguments(self, parser):
        parser.add_argument('--log_id', type=int, help='SyncLog ID')

    def handle(self, *args, **options):
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

        headers = {'Authorization': f'Bearer {token}',
                   'Content-Type': 'application/json'}
        page = 1
        total_created = total_updated = 0

        while True:
            url = f'https://prodapi.omniful.com/sales-channel/public/v1/tenants/sellers?page={page}&per_page=100'
            try:
                log_line(f"📦 Fetching sellers page {page}...")
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                data = response.json()

                sellers = data.get('data', [])
                if not sellers:
                    log_line("✅ No more sellers. Sync complete.")
                    break

                for seller_data in sellers:
                    seller, created = Seller.objects.update_or_create(
                        code=seller_data.get('code'),
                        defaults={
                            'guid': seller_data.get('guid'),
                            'name': seller_data.get('name', ''),
                            'phone': seller_data.get('phone', ''),
                            'email': seller_data.get('email', ''),
                            'is_active': seller_data.get('is_active', True),
                            'created_at_api': parser.parse(seller_data['created_at']) if seller_data.get('created_at') else None,
                            'updated_at_api': parser.parse(seller_data['updated_at']) if seller_data.get('updated_at') else None,
                            'address': seller_data.get('address', {}),
                        }
                    )
                    log_line(
                        f"{'✅ Created' if created else '🔄 Updated'} seller: {seller.name}")
                    if created:
                        total_created += 1
                    else:
                        total_updated += 1

                page += 1
            except Exception as e:
                log_line(f"❌ Error: {str(e)}")
                break

        if log_obj:
            log_obj.completed = True
            log_obj.save(update_fields=["completed", "log"])
        log_line(
            f"🎉 Sync complete: {total_created} created, {total_updated} updated.")

        # if log_obj:
        #     log_obj.completed = True
        #     log_obj.save(update_fields=["completed"])
        #     time.sleep(3)
        #     log_obj.delete()
