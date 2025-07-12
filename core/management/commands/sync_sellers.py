"""
Management command to sync sellers from Omniful API.
"""

import requests
import os
from django.core.management.base import BaseCommand
from django.conf import settings
# Ensure this import path is correct for your Seller model
# If your Seller model is in 'core/models.py', use:
from core.models import Seller
# If your Seller model is in 'core/models.py', keep:
# from core.models import Seller

from decouple import config
from dateutil import parser  # pip install python-dateutil for robust date parsing


class Command(BaseCommand):
    help = 'Sync sellers from Omniful API'

    def handle(self, *args, **options):
        token = config('OMNIFUL_ACCESS_TOKEN', default='')

        if not token:
            self.stdout.write(self.style.ERROR(
                'OMNIFUL_ACCESS_TOKEN not configured in .env file'))
            return

        token_length = len(token)
        token_preview = token[:20] + '...' if token_length > 20 else token
        self.stdout.write(f'Token length: {token_length}')
        self.stdout.write(f'Token preview: {token_preview}')

        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'  # Good practice to include this
        }

        self.stdout.write(f'Starting sync of sellers from Omniful API...')

        page = 1
        total_synced = 0
        total_created = 0
        total_updated = 0

        while True:
            url = f'https://prodapi.omniful.com/sales-channel/public/v1/tenants/sellers?page={page}&per_page=100'

            try:
                self.stdout.write(f'Fetching page {page} from {url}')
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)
                data = response.json()

                sellers_data = data.get('data', [])
                meta = data.get('meta', {})

                if not sellers_data:
                    self.stdout.write(
                        f'No more sellers found on page {page}. Ending sync.')
                    break

                current_page = meta.get('current_page', page)
                last_page = meta.get('last_page', 1)
                total_items = meta.get('total', 'N/A')

                self.stdout.write(
                    f'Processing page {current_page} of {last_page} ({len(sellers_data)} sellers on this page, Total: {total_items})')

                for seller_item in sellers_data:
                    # --- Date Parsing ---
                    created_at_api_dt = None
                    if 'created_at' in seller_item and seller_item['created_at']:
                        try:
                            created_at_api_dt = parser.parse(
                                seller_item['created_at'])
                        except ValueError:
                            self.stdout.write(self.style.WARNING(
                                f"Could not parse created_at for seller {seller_item.get('guid', 'N/A')}: {seller_item['created_at']}"))

                    updated_at_api_dt = None
                    if 'updated_at' in seller_item and seller_item['updated_at']:
                        try:
                            updated_at_api_dt = parser.parse(
                                seller_item['updated_at'])
                        except ValueError:
                            self.stdout.write(self.style.WARNING(
                                f"Could not parse updated_at for seller {seller_item.get('guid', 'N/A')}: {seller_item['updated_at']}"))

                    # --- Prepare address data---
                    api_address = seller_item.get('address', {})

                    # Extract specific parts from the address
                    country_name = api_address.get(
                        'country', {}).get('name', '')
                    state_name = api_address.get('state', {}).get('name', '')
                    state_code = api_address.get('state', {}).get('code', '')
                    city_name = api_address.get('city', {}).get('name', '')
                    address_line1 = api_address.get('address_line1', '')
                    address_line2 = api_address.get('address_line2', '')

                    # Construct the address dictionary
                    address_data = {
                        'country_name': country_name,
                        'state_name': state_name,
                        'state_code': state_code,
                        'city_name': city_name,
                        'address_line1': address_line1,
                        'address_line2': address_line2,
                    }

                    address_str = address_data

                    # --- Save/Update Seller ---
                    # Using update_or_create is efficient for syncing
                    seller, created = Seller.objects.update_or_create(
                        code=seller_item.get('code'),  # Lookup by guid
                        defaults={
                            'guid': seller_item.get('guid'),
                            'name': seller_item.get('name', ''),
                            'phone': seller_item.get('phone', ''),
                            'email': seller_item.get('email', ''),
                            'code': seller_item.get('code', ''),
                            'address': address_str,  # Use the prepared address string
                            # Only if you added is_active to model
                            'is_active': seller_item.get('is_active', True),
                            'created_at_api': created_at_api_dt,
                            'updated_at_api': updated_at_api_dt,
                        }
                    )

                    if created:
                        total_created += 1
                        self.stdout.write(
                            f'Created seller: {seller.name} (GUID: {seller.guid})')
                    else:
                        total_updated += 1
                        self.stdout.write(
                            f'Updated seller: {seller.name} (GUID: {seller.guid})')

                    total_synced += 1

                # Pagination logic
                if current_page >= last_page:
                    self.stdout.write(
                        f'Finished processing all pages. Last page was {last_page}.')
                    break  # Exit the while loop

                page += 1

                # Safety check to prevent infinite loops for APIs that don't correctly return last_page
                # Check a few pages beyond last_page
                if page > (last_page + 10) and last_page != 0:
                    self.stdout.write(self.style.WARNING(
                        f'Reached a safety page limit (current page {page}, last page {last_page}), stopping to prevent infinite loop.'))
                    break
                elif page > 1000 and last_page == 0:  # If last_page is not provided or 0, cap at 1000 pages
                    self.stdout.write(self.style.WARNING(
                        'Reached hard page limit (1000), stopping to prevent infinite loop.'))
                    break

            except requests.exceptions.HTTPError as http_err:
                self.stdout.write(self.style.ERROR(
                    f'HTTP error occurred: {http_err}'))
                if http_err.response is not None:
                    self.stdout.write(
                        f'Response status: {http_err.response.status_code}')
                    # Print more of the error
                    self.stdout.write(
                        f'Response text: {http_err.response.text[:500]}')
                break
            except requests.exceptions.ConnectionError as conn_err:
                self.stdout.write(self.style.ERROR(
                    f'Connection error occurred: {conn_err}. Check network or API availability.'))
                break
            except requests.exceptions.Timeout as timeout_err:
                self.stdout.write(self.style.ERROR(
                    f'Timeout error occurred: {timeout_err}. API did not respond in time.'))
                break
            except requests.exceptions.RequestException as req_err:
                self.stdout.write(self.style.ERROR(
                    f'An unexpected request error occurred: {req_err}'))
                break
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f'An unexpected error occurred during processing: {str(e)}'))
                import traceback
                # Print full traceback for debugging
                self.stdout.write(self.style.ERROR(traceback.format_exc()))
                break

        self.stdout.write(
            self.style.SUCCESS(
                f'Sync process completed: Created {total_created} sellers, Updated {total_updated} sellers. Total synced: {total_synced}')
        )
