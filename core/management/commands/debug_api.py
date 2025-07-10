"""
Debug API endpoints and authentication.
"""

import requests
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Debug API endpoints'
    
    def handle(self, *args, **options):
        token = settings.OMNIFUL_ACCESS_TOKEN
        
        # Try the exact same request that worked in test_api
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        # Test the working endpoint from test_api
        url = 'https://prodapi.omniful.com/sales-channel/public/v1/tenants/sellers?page=1&per_page=5'
        
        try:
            self.stdout.write(f'Testing URL: {url}')
            response = requests.get(url, headers=headers, timeout=10)
            self.stdout.write(f'Status: {response.status_code}')
            
            if response.status_code == 200:
                data = response.json()
                self.stdout.write('SUCCESS! API is working')
                self.stdout.write(f'Found {len(data.get("data", []))} sellers')
            else:
                self.stdout.write(f'Error: {response.text}')
                
        except Exception as e:
            self.stdout.write(f'Exception: {str(e)}')