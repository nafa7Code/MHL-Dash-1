"""
Management command to set up initial data for the logistics application.
Creates default company, admin user, and sample data.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction
from decimal import Decimal
from datetime import date, timedelta

from core.models import Company, Profile
from invoices.models import Invoice, InvoiceItem


class Command(BaseCommand):
    help = 'Set up initial data for the logistics application'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--with-sample-data',
            action='store_true',
            help='Create sample invoices and data',
        )
        parser.add_argument(
            '--admin-username',
            type=str,
            default='admin',
            help='Admin username (default: admin)',
        )
        parser.add_argument(
            '--admin-password',
            type=str,
            default='admin123',
            help='Admin password (default: admin123)',
        )
        parser.add_argument(
            '--company-name',
            type=str,
            default='MHL Logistics',
            help='Company name (default: MHL Logistics)',
        )
    
    def handle(self, *args, **options):
        with transaction.atomic():
            # Create default company
            company = self.create_company(options['company_name'])
            
            # Create admin user
            admin_user = self.create_admin_user(
                options['admin_username'],
                options['admin_password'],
                company
            )
            
            # Create sample data if requested
            if options['with_sample_data']:
                self.create_sample_data(company)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully set up initial data!\n'
                    f'Company: {company.name}\n'
                    f'Admin user: {admin_user.username}\n'
                    f'Admin password: {options["admin_password"]}\n'
                    f'Login URL: http://localhost:8000/accounts/login/'
                )
            )
    
    def create_company(self, company_name):
        """Create default company."""
        company, created = Company.objects.get_or_create(
            code='MHL001',
            defaults={
                'name': company_name,
                'name_ar': 'شركة إم إتش إل للخدمات اللوجستية',
                'is_active': True,
            }
        )
        
        if created:
            self.stdout.write(f'Created company: {company.name}')
        else:
            self.stdout.write(f'Company already exists: {company.name}')
        
        return company
    
    def create_admin_user(self, username, password, company):
        """Create admin user with profile."""
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': 'admin@mhllogistics.com',
                'first_name': 'System',
                'last_name': 'Administrator',
                'is_staff': True,
                'is_superuser': True,
                'is_active': True,
            }
        )
        
        if created:
            user.set_password(password)
            user.save()
            self.stdout.write(f'Created admin user: {username}')
        else:
            self.stdout.write(f'Admin user already exists: {username}')
        
        # Create or update user profile
        profile, profile_created = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                'company': company,
                'department': 'Administration',
                'is_admin': True,
                'preferred_language': 'en',
            }
        )
        
        if profile_created:
            self.stdout.write('Created admin user profile')
        
        return user
    
    def create_sample_data(self, company):
        """Create sample invoices and data."""
        self.stdout.write('Creating sample data...')
        
        # Sample customers
        customers = [
            {'name': 'ABC Trading Company', 'code': 'ABC001'},
            {'name': 'XYZ Logistics Ltd', 'code': 'XYZ002'},
            {'name': 'Global Shipping Inc', 'code': 'GSI003'},
            {'name': 'Fast Delivery Services', 'code': 'FDS004'},
            {'name': 'International Freight Co', 'code': 'IFC005'},
        ]
        
        # Create sample invoices
        base_date = date.today() - timedelta(days=90)
        
        for i, customer in enumerate(customers):
            # Create 2-3 invoices per customer
            for j in range(2, 4):
                invoice_date = base_date + timedelta(days=i*10 + j*5)
                due_date = invoice_date + timedelta(days=30)
                
                invoice = Invoice.objects.create(
                    company=company,
                    invoice_number=f'INV-{2024}-{(i*3+j):04d}',
                    customer_name=customer['name'],
                    customer_code=customer['code'],
                    invoice_date=invoice_date,
                    due_date=due_date,
                    total_amount=Decimal(str(1000 + i*500 + j*250)),
                    currency='SAR',
                    status=['draft', 'pending', 'paid'][j % 3],
                    notes=f'Sample invoice for {customer["name"]}',
                )
                
                # Create invoice items
                items = [
                    {'desc': 'Freight Transportation', 'qty': 1, 'price': 800},
                    {'desc': 'Handling Charges', 'qty': 2, 'price': 150},
                    {'desc': 'Documentation Fee', 'qty': 1, 'price': 50},
                ]
                
                for item_data in items:
                    InvoiceItem.objects.create(
                        invoice=invoice,
                        description=item_data['desc'],
                        quantity=Decimal(str(item_data['qty'])),
                        unit_price=Decimal(str(item_data['price'])),
                    )
        
        invoice_count = Invoice.objects.filter(company=company).count()
        self.stdout.write(f'Created {invoice_count} sample invoices')
        
        # Create a regular user
        regular_user, created = User.objects.get_or_create(
            username='user1',
            defaults={
                'email': 'user@mhllogistics.com',
                'first_name': 'John',
                'last_name': 'Doe',
                'is_active': True,
            }
        )
        
        if created:
            regular_user.set_password('user123')
            regular_user.save()
            
            UserProfile.objects.create(
                user=regular_user,
                company=company,
                department='Operations',
                is_admin=False,
                preferred_language='en',
            )
            
            self.stdout.write('Created regular user: user1 (password: user123)')
        
        self.stdout.write(self.style.SUCCESS('Sample data created successfully!'))