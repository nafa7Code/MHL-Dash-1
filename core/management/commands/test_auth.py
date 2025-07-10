"""
Test different authentication methods with Omniful API.
"""

import requests
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Test different auth methods with Omniful API'
    
    def handle(self, *args, **options):
        token = settings.OMNIFUL_ACCESS_TOKEN
        self.stdout.write(f'Token length: {len(token)}')
        
        # Test different header combinations
        test_cases = [
            {
                'name': 'Bearer with Content-Type',
                'headers': {
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json'
                }
            },
            {
                'name': 'Bearer only',
                'headers': {
                    'Authorization': f'Bearer {token}'
                }
            },
            {
                'name': 'Bearer with Accept',
                'headers': {
                    'Authorization': f'Bearer {token}',
                    'Accept': 'application/json'
                }
            }
        ]
        
        url = 'https://prodapi.omniful.com/sales-channel/public/v1/tenants/sellers?page=1&per_page=1'
        
        for test in test_cases:
            self.stdout.write(f'\nTesting: {test["name"]}')
            try:
                response = requests.get(url, headers=test['headers'], timeout=10)
                self.stdout.write(f'Status: {response.status_code}')
                if response.status_code == 200:
                    self.stdout.write('SUCCESS!')
                    break
                else:
                    self.stdout.write(f'Response: {response.text[:100]}')
            except Exception as e:
                self.stdout.write(f'Error: {str(e)}')