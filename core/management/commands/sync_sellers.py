from django.core.management.base import BaseCommand
from core.models import Seller, SyncStatus, SyncLog
from decouple import config
from dateutil import parser
from django.utils.timezone import now
import requests


class Command(BaseCommand):
    help = 'Sync sellers from Omniful API'

    def handle(self, *args, **options):
        log_lines = []

        # Use passed-in stdout (for call_command) or default to self.stdout
        stdout = options.get('stdout', self.stdout)

        def log(msg):
            log_lines.append(msg)
            stdout.write(msg + "\n")  # Ensure newline
            stdout.flush()

        token = config('OMNIFUL_ACCESS_TOKEN', default='')
        if not token:
            log("❌ OMNIFUL_ACCESS_TOKEN not set in .env file")
            return

        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

        page = 1
        total_created = total_updated = total_synced = 0

        while True:
            url = f'https://prodapi.omniful.com/sales-channel/public/v1/tenants/sellers?page={page}&per_page=100'

            try:
                log(f'🌐 Fetching page {page} from {url}')
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                data = response.json()

                sellers_data = data.get('data', [])
                current_page = data.get('current_page', page)
                last_page = data.get('last_page', page)

                if not sellers_data:
                    break

                log(
                    f'🔄 Processing page {current_page} of {last_page} '
                    f'({len(sellers_data)} sellers)'
                )

                for seller_data in sellers_data:
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
                    if created:
                        total_created += 1
                        log(f'✅ Created: {seller.name} (GUID: {seller.guid})')
                    else:
                        total_updated += 1
                        log(f'♻️ Updated: {seller.name} (GUID: {seller.guid})')

                    total_synced += 1

                page += 1

            except requests.exceptions.RequestException as e:
                log(f'❌ Request error: {str(e)}')
                break
            except Exception as e:
                import traceback
                log(f'🔥 Unexpected error: {str(e)}')
                log(traceback.format_exc())
                break

        # Save last synced time
        SyncStatus.objects.update_or_create(
            key='sellers',
            defaults={'last_synced_at': now()}
        )

        summary = (
            f"\n✅ Sync Complete!\n"
            f"Created: {total_created}\n"
            f"Updated: {total_updated}\n"
            f"Total Synced: {total_synced}"
        )
        log(summary)

        # Save logs to database
        SyncLog.objects.update_or_create(
            key='sellers',
            defaults={'content': '\n'.join(log_lines)}
        )
