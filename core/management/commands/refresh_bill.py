"""
Management command to refresh a specific vendor bill from Omniful API.
"""

import requests
from datetime import datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from core.models import VendorBill
from decouple import config


class Command(BaseCommand):
    help = 'Refresh specific vendor bill details from Omniful API'
    
    def add_arguments(self, parser):
        parser.add_argument('bill_name', type=str, help='Bill name to refresh')
    
    def handle(self, *args, **options):
        bill_name = options['bill_name']
        
        token = config('OMNIFUL_ACCESS_TOKEN', default='')
        
        if not token:
            self.stdout.write(self.style.ERROR('OMNIFUL_ACCESS_TOKEN not configured'))
            return
        
        try:
            bill = VendorBill.objects.get(name=bill_name)
        except VendorBill.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Bill not found: {bill_name}'))
            return
        
        headers = {
            'Authorization': f'Bearer {token}'
        }
        
        url = f'https://prodapi.omniful.com/sales-channel/public/v1/tenants/bills/{bill_name}'
        
        try:
            self.stdout.write(f'Fetching bill details for: {bill_name}')
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            self.stdout.write('Successfully fetched bill data from API')
            
            # Extract the actual bill data from the nested response
            bill_data = data.get('data', {})
            
            # Update bill with detailed data
            bill.hubs = bill_data.get('hubs', [])
            bill.grand_total = Decimal(str(bill_data.get('grand_total', 0)))
            
            # Handle discount field (can be object or number)
            discount_data = bill_data.get('discount', 0)
            if isinstance(discount_data, dict):
                bill.discount = Decimal(str(discount_data.get('value', 0)))
            else:
                bill.discount = Decimal(str(discount_data))
            
            bill.grand_total_after_discount = Decimal(str(bill_data.get('grand_total_after_discount', 0)))
            bill.contract_name = bill_data.get('contract_name', '')
            bill.fees = bill_data.get('fees', [])
            bill.hub_bills = bill_data.get('hub_bills', [])
            bill.status = bill_data.get('status', '')
            bill.currency = bill_data.get('currency', 'SAR')
            
            # Parse dates (Omniful format: "November 01, 2024")
            if bill_data.get('period_start_date'):
                try:
                    bill.period_start_date = datetime.strptime(bill_data['period_start_date'], '%B %d, %Y').date()
                except:
                    pass
            
            if bill_data.get('period_end_date'):
                try:
                    bill.period_end_date = datetime.strptime(bill_data['period_end_date'], '%B %d, %Y').date()
                except:
                    pass
            
            if bill_data.get('due_date'):
                try:
                    bill.due_date = datetime.strptime(bill_data['due_date'], '%B %d, %Y').date()
                except:
                    pass
            
            bill.finalised_on = bill_data.get('finalised_on', '')
            bill.finalised_by = bill_data.get('finalised_by', '')
            bill.remark = bill_data.get('remark', '')
            bill.pdf = bill_data.get('pdf', '')
            
            # Parse created_at date from API
            if bill_data.get('created_at'):
                try:
                    api_created_at = datetime.strptime(bill_data['created_at'], '%B %d, %Y %I:%M %p')
                    bill.created_at = timezone.make_aware(api_created_at)
                except:
                    pass
            
            bill.save()
            
            self.stdout.write(
                self.style.SUCCESS(f'Successfully refreshed bill: {bill_name}')
            )
            
        except requests.Timeout:
            self.stdout.write(self.style.ERROR('Request timed out after 30 seconds'))
        except requests.RequestException as e:
            self.stdout.write(self.style.ERROR(f'API request failed: {str(e)}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error processing data: {str(e)}'))