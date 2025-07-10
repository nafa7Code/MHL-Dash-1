"""
Management command to clear test data and replace with real Omniful data.
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command
from invoices.models import Invoice, ImportBatch
from reports.models import ProfitReport
from core.models import Seller, VendorBill


class Command(BaseCommand):
    help = 'Clear test data and sync real data from Omniful'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm deletion of test data',
        )
    
    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(
                self.style.WARNING(
                    'This will delete ALL existing invoices, reports, and import batches.\n'
                    'Omniful sellers and bills will be kept and refreshed.\n'
                    'Run with --confirm to proceed.'
                )
            )
            return
        
        self.stdout.write('Clearing test data...')
        
        # Clear test invoices and related data
        invoice_count = Invoice.objects.count()
        batch_count = ImportBatch.objects.count()
        report_count = ProfitReport.objects.count()
        
        Invoice.objects.all().delete()
        ImportBatch.objects.all().delete()
        ProfitReport.objects.all().delete()
        
        self.stdout.write(f'Deleted {invoice_count} invoices')
        self.stdout.write(f'Deleted {batch_count} import batches')
        self.stdout.write(f'Deleted {report_count} reports')
        
        # Sync fresh data from Omniful
        self.stdout.write('\nSyncing fresh data from Omniful...')
        
        try:
            call_command('sync_sellers')
            call_command('sync_bills')
            self.stdout.write(
                self.style.SUCCESS(
                    '\nSuccessfully replaced test data with real Omniful data!'
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error syncing Omniful data: {str(e)}')
            )