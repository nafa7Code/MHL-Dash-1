"""
Debug command to check bill API response structure.
"""

import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from decouple import config
import json


class Command(BaseCommand):
    help = 'Debug bill API response'
    
    def add_arguments(self, parser):
        parser.add_argument('bill_name', type=str, help='Bill name to debug')
    
    def handle(self, *args, **options):
        bill_name = options['bill_name']
        token = config('OMNIFUL_ACCESS_TOKEN', default='')
        
        if not token:
            self.stdout.write(self.style.ERROR('OMNIFUL_ACCESS_TOKEN not configured'))
            return
        
        headers = {
            'Authorization': f'Bearer {token}'
        }
        
        url = f'https://prodapi.omniful.com/sales-channel/public/v1/tenants/bills/{bill_name}'
        
        try:
            self.stdout.write(f'Fetching: {url}')
            response = requests.get(url, headers=headers, timeout=30)
            self.stdout.write(f'Status: {response.status_code}')
            
            if response.status_code == 200:
                data = response.json()
                self.stdout.write('=== FULL API RESPONSE ===')
                self.stdout.write(json.dumps(data, indent=2, ensure_ascii=False))
                
                # Check specific fields
                bill_data = data.get('data', {})
                self.stdout.write('\n=== KEY FIELDS ===')
                self.stdout.write(f'grand_total: {bill_data.get("grand_total")} (type: {type(bill_data.get("grand_total"))})')
                self.stdout.write(f'status: {bill_data.get("status")}')
                self.stdout.write(f'currency: {bill_data.get("currency")}')
                self.stdout.write(f'contract_name: {bill_data.get("contract_name")}')
                self.stdout.write(f'period_start_date: {bill_data.get("period_start_date")}')
                self.stdout.write(f'discount: {bill_data.get("discount")} (type: {type(bill_data.get("discount"))})')
                
            else:
                self.stdout.write(f'Error: {response.text}')
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))