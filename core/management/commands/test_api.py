"""
Test command to check Omniful API connectivity and response format.
"""

import requests
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Test Omniful API connectivity'
    
    def handle(self, *args, **options):
        if not settings.OMNIFUL_ACCESS_TOKEN:
            self.stdout.write(self.style.ERROR('OMNIFUL_ACCESS_TOKEN not configured'))
            return
        
        headers = {
            'Authorization': f'Bearer {settings.OMNIFUL_ACCESS_TOKEN}',
            'Content-Type': 'application/json'
        }
        
        # Test sellers endpoint
        # self.stdout.write('Testing sellers endpoint...')
        # try:
        #     url = 'https://prodapi.omniful.com/sales-channel/public/v1/tenants/sellers?page=1&per_page=5'
        #     response = requests.get(url, headers=headers, timeout=10)
        #     self.stdout.write(f'Status Code: {response.status_code}')
            
        #     if response.status_code == 200:
        #         data = response.json()
        #         self.stdout.write(f'Response keys: {list(data.keys())}')
        #         sellers = data.get('data', [])
        #         self.stdout.write(f'Found {len(sellers)} sellers on page 1')
        #         if sellers:
        #             self.stdout.write(f'First seller keys: {list(sellers[0].keys())}')
        #     else:
        #         self.stdout.write(f'Error response: {response.text}')
                
        # except Exception as e:
        #     self.stdout.write(self.style.ERROR(f'Sellers API error: {str(e)}'))
        
        # Test bills endpoint
        # self.stdout.write('\nTesting bills endpoint...')
        # try:
        #     url = 'https://prodapi.omniful.com/sales-channel/public/v1/tenants/bills?page=1&per_page=5'
        #     response = requests.get(url, headers=headers, timeout=10)
        #     self.stdout.write(f'Status Code: {response.status_code}')
            
        #     if response.status_code == 200:
        #         data = response.json()
        #         self.stdout.write(f'Response keys: {list(data.keys())}')
        #         bills = data.get('data', [])
        #         self.stdout.write(f'Found {len(bills)} bills on page 1')
                
        #         if bills:
        #             first_bill = bills[0]
        #             self.stdout.write('\nInspecting First Bill:')
        #             for key, value in first_bill.items():
        #                 self.stdout.write(f'  {key} ({type(value).__name__}): {value}')
        #     else:
        #         self.stdout.write(f'Error response: {response.text}')
                
        # except Exception as e:
        #     self.stdout.write(self.style.ERROR(f'Bills API error: {str(e)}'))
            
            # Test Order endpoint
        self.stdout.write('\nTesting Order endpoint...')
        try:
            url = 'https://prodapi.omniful.com//sales-channel/public/v1/tenants/sellers/KE-270/orders?page=1&per_page=20'
            response = requests.get(url, headers=headers, timeout=10)
            self.stdout.write(f'Status Code: {response.status_code}')

            if response.status_code == 200:
                data = response.json()
                self.stdout.write(f'Response keys: {list(data.keys())}')
                bills = data.get('data', [])
                self.stdout.write(f'Found {len(bills)} Orders on page 1')

                if bills:
                    first_bill = bills[0]
                    self.stdout.write('\nInspecting First Bill:')
                    for key, value in first_bill.items():
                        self.stdout.write(
                            f'  {key} ({type(value).__name__}): {value}')
            else:
                self.stdout.write(f'Error response: {response.text}')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Bills API error: {str(e)}'))
