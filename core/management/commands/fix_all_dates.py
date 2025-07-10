"""
Management command to fix all bill dates with progress feedback.
"""

import requests
import time
import json
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import connection
from core.models import VendorBill
from decouple import config


class Command(BaseCommand):
    help = 'Fix all bill dates with progress feedback'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--batch',
            type=int,
            default=20,
            help='Number of bills to process in each batch (default: 20)',
        )
    
    def handle(self, *args, **options):
        token = config('OMNIFUL_ACCESS_TOKEN', default='')
        
        if not token:
            self.stdout.write(self.style.ERROR('OMNIFUL_ACCESS_TOKEN not configured'))
            return
        
        headers = {
            'Authorization': f'Bearer {token}'
        }
        
        batch_size = options['batch']
        
        # Count total bills
        total_bills = VendorBill.objects.count()
        self.stdout.write(f'Total bills to process: {total_bills}')
        
        # Process in batches
        processed = 0
        success_count = 0
        error_count = 0
        
        while processed < total_bills:
            # Get next batch
            bills = VendorBill.objects.all()[processed:processed+batch_size]
            if not bills:
                break
                
            self.stdout.write(f'Processing batch {processed//batch_size + 1} ({len(bills)} bills)...')
            
            for i, bill in enumerate(bills):
                try:
                    self.stdout.write(f'  [{processed+i+1}/{total_bills}] Updating {bill.name}...')
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
                            
                            # Update directly in the database
                            with connection.cursor() as cursor:
                                cursor.execute(
                                    "UPDATE core_vendorbill SET created_at = %s WHERE name = %s",
                                    [created_at_aware, bill.name]
                                )
                            
                            # Also update other fields
                            if bill_data.get('status'):
                                bill.status = bill_data.get('status')
                            
                            if bill_data.get('currency'):
                                bill.currency = bill_data.get('currency')
                                
                            if bill_data.get('grand_total'):
                                bill.grand_total = bill_data.get('grand_total')
                                
                            if bill_data.get('contract_name'):
                                bill.contract_name = bill_data.get('contract_name')
                                
                            # Parse period dates
                            if bill_data.get('period_start_date'):
                                try:
                                    bill.period_start_date = datetime.strptime(
                                        bill_data['period_start_date'], '%B %d, %Y'
                                    ).date()
                                except:
                                    pass
                                    
                            if bill_data.get('period_end_date'):
                                try:
                                    bill.period_end_date = datetime.strptime(
                                        bill_data['period_end_date'], '%B %d, %Y'
                                    ).date()
                                except:
                                    pass
                                    
                            if bill_data.get('due_date'):
                                try:
                                    bill.due_date = datetime.strptime(
                                        bill_data['due_date'], '%B %d, %Y'
                                    ).date()
                                except:
                                    pass
                            
                            # Save the model to update other fields
                            bill.save()
                            
                            self.stdout.write(f'    Updated: {created_at_aware}')
                            success_count += 1
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f'    Error parsing date: {str(e)}'))
                            error_count += 1
                    else:
                        self.stdout.write('    No created_at date in API response')
                        error_count += 1
                        
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'    Error updating {bill.name}: {str(e)}'))
                    error_count += 1
                
                # Add a small delay to avoid overwhelming the API
                time.sleep(0.2)
            
            # Update processed count
            processed += len(bills)
            self.stdout.write(f'Completed batch: {processed}/{total_bills} bills processed')
            
            # Write progress to a file for the web UI to read
            progress = {
                'total': total_bills,
                'processed': processed,
                'success': success_count,
                'errors': error_count,
                'percentage': round((processed / total_bills) * 100, 1)
            }
            
            try:
                with open('date_fix_progress.json', 'w') as f:
                    json.dump(progress, f)
            except:
                pass
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Completed: {success_count} successful, {error_count} errors'
            )
        )