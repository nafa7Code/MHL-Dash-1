"""
Management command to fix bill dates directly in the database.
"""

import requests
import time
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import connection
from core.models import VendorBill
from decouple import config


class Command(BaseCommand):
    help = 'Fix bill dates directly in the database'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Limit number of bills to update (default: 50)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update all bills even if they already have dates',
        )
    
    def handle(self, *args, **options):
        token = config('OMNIFUL_ACCESS_TOKEN', default='')
        
        if not token:
            self.stdout.write(self.style.ERROR('OMNIFUL_ACCESS_TOKEN not configured'))
            return
        
        headers = {
            'Authorization': f'Bearer {token}'
        }
        
        limit = options['limit']
        force = options['force']
        
        # Get bills to update
        if force:
            bills = VendorBill.objects.all()[:limit]
            self.stdout.write(f'Forcing update for {len(bills)} bills...')
        else:
            # Get bills with default dates (likely from today)
            bills = VendorBill.objects.filter(created_at__year=2025, created_at__month=7)[:limit]
            self.stdout.write(f'Found {len(bills)} bills with incorrect dates...')
        
        success_count = 0
        error_count = 0
        
        for i, bill in enumerate(bills):
            try:
                self.stdout.write(f'[{i+1}/{len(bills)}] Updating {bill.name}...')
                url = f'https://prodapi.omniful.com/sales-channel/public/v1/tenants/bills/{bill.name}'
                
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                bill_data = data.get('data', {})
                
                # Parse created_at date
                created_at_str = bill_data.get('created_at')
                if created_at_str:
                    try:
                        created_at = datetime.strptime(created_at_str, '%B %d, %Y %I:%M %p')
                        created_at_aware = timezone.make_aware(created_at)
                        
                        # Update directly in the database for reliability
                        with connection.cursor() as cursor:
                            cursor.execute(
                                "UPDATE core_vendorbill SET created_at = %s WHERE name = %s",
                                [created_at_aware, bill.name]
                            )
                        
                        self.stdout.write(f'  Updated created_at: {created_at_aware} (was: {bill.created_at})')
                        success_count += 1
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'  Error parsing date: {str(e)}'))
                        error_count += 1
                else:
                    self.stdout.write('  No created_at date in API response')
                    error_count += 1
                
                # Add a small delay to avoid overwhelming the API
                time.sleep(0.5)
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error updating {bill.name}: {str(e)}'))
                error_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Completed: {success_count} successful, {error_count} errors'
            )
        )