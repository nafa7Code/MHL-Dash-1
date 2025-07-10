"""
Test token loading in management command.
"""

from django.core.management.base import BaseCommand
from decouple import config
import os


class Command(BaseCommand):
    help = 'Test token loading'
    
    def handle(self, *args, **options):
        # Test different ways to get the token
        token1 = config('OMNIFUL_ACCESS_TOKEN', default='')
        token2 = os.getenv('OMNIFUL_ACCESS_TOKEN', '')
        
        self.stdout.write(f'Config token length: {len(token1)}')
        self.stdout.write(f'Config token preview: {token1[:20]}...')
        
        self.stdout.write(f'OS env token length: {len(token2)}')
        self.stdout.write(f'OS env token preview: {token2[:20]}...')
        
        # Check if .env file exists
        env_file = '.env'
        if os.path.exists(env_file):
            self.stdout.write(f'.env file exists: {os.path.abspath(env_file)}')
        else:
            self.stdout.write('.env file not found')
            
        # Show current working directory
        self.stdout.write(f'Current directory: {os.getcwd()}')