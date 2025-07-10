"""
Management command to update bill dates from Omniful API.
"""

import requests
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import VendorBill
from decouple import config


class Command(BaseCommand):
    help = 'Update bill dates from Omniful API'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=10,
            help='Limit number of bills to update (default: 10)',
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
        bills = VendorBill.objects.all()[:limit]
        
        self.stdout.write(f'Updating dates for {len(bills)} bills...')
        
        success_count = 0
        error_count = 0
        
        for bill in bills:
            try:
                self.stdout.write(f'Updating {bill.name}...')
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
                        bill.created_at = timezone.make_aware(created_at)
                        bill.save(update_fields=['created_at'])
                        self.stdout.write(f'  Updated created_at: {bill.created_at}')
                        success_count += 1
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'  Error parsing date: {str(e)}'))
                        error_count += 1
                else:
                    self.stdout.write('  No created_at date in API response')
                    error_count += 1
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error updating {bill.name}: {str(e)}'))
                error_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Completed: {success_count} successful, {error_count} errors'
            )
        )