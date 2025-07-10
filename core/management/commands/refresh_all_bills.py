"""
Management command to refresh all vendor bills with detailed data from Omniful API.
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command
from core.models import VendorBill


class Command(BaseCommand):
    help = 'Refresh all vendor bills with detailed data from Omniful API'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=10,
            help='Limit number of bills to refresh (default: 10)',
        )
    
    def handle(self, *args, **options):
        limit = options['limit']
        
        # Get bills that need refreshing (those without detailed data)
        bills_to_refresh = VendorBill.objects.filter(
            grand_total=0
        ).order_by('created_at')[:limit]
        
        if not bills_to_refresh:
            self.stdout.write('No bills need refreshing')
            return
        
        self.stdout.write(f'Refreshing {len(bills_to_refresh)} bills...')
        
        success_count = 0
        error_count = 0
        
        for bill in bills_to_refresh:
            try:
                self.stdout.write(f'Refreshing {bill.name}...')
                call_command('refresh_bill', bill.name)
                success_count += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error refreshing {bill.name}: {str(e)}'))
                error_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Completed: {success_count} successful, {error_count} errors'
            )
        )