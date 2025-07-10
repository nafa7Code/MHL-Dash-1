"""
Admin configuration for core models.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse

from .models import Company, Profile, Seller, VendorBill, Order


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    """Admin interface for Company model."""
    list_display = ['name', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name']
    ordering = ['name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('name',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


class ProfileInline(admin.StackedInline):
    """Inline admin for Profile."""
    model = Profile
    can_delete = False
    verbose_name_plural = _('Profile')
    
    fieldsets = (
        (None, {
            'fields': ('company', 'phone', 'department', 'preferred_language')
        }),
    )


class UserAdmin(BaseUserAdmin):
    """Extended User admin with profile inline."""
    inlines = (ProfileInline,)
    
    list_display = ['username', 'email', 'first_name', 'last_name', 'get_company', 'is_staff', 'is_active']
    list_filter = ['is_staff', 'is_active', 'profile__company']
    
    def get_company(self, obj):
        """Get user's company."""
        try:
            return obj.profile.company.name
        except:
            return '-'
    get_company.short_description = _('Company')


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


# @admin.register(Seller)
# class SellerAdmin(admin.ModelAdmin):
#     """Admin interface for Seller model."""
#     list_display = ['guid', 'name', 'code', 'email', 'phone', 'is_active', 'created_at']
#     list_filter = ['is_active', 'created_at']
#     search_fields = ['name', 'code', 'email', 'guid']
#     readonly_fields = ['guid', 'created_at', 'updated_at']
#     ordering = ['name']
    
#     fieldsets = (
#         (None, {
#             'fields': ('guid', 'name', 'code', 'email', 'phone', 'is_active')
#         }),
#         (_('Address'), {
#             'fields': ('address',),
#             'classes': ('collapse',)
#         }),
#         (_('Timestamps'), {
#             'fields': ('created_at', 'updated_at'),
#             'classes': ('collapse',)
#         }),
#     )


@admin.register(Seller)
class SellerAdmin(admin.ModelAdmin):
    # What fields to display in the list view of the admin
    list_display = (
        'name',
        'guid',
        'email',
        'phone',
        # Corrected field names:
        'created_at_local', # Use your local creation timestamp
        'updated_at_local', # Use your local update timestamp
        # 'is_active', # Remove this line if you don't add the field to the model
    )

    # Fields to make clickable links to the detail page
    list_display_links = (
        'name',
        'guid',
    )

    # Fields to allow searching on
    search_fields = (
        'name',
        'guid',
        'email',
        'phone',
        'code',
    )

    # Fields to filter by in the right sidebar of the admin list view
    list_filter = (
        # Corrected field names:
        'created_at_local', # Use your local creation timestamp for filtering
        # 'is_active', # Remove this line if you don't add the field to the model
    )

    # Fields that cannot be edited directly in the admin form (they are displayed as text)
    readonly_fields = (
        'guid', # GUID should generally not be editable after creation
        'created_at_api', # These are from Omniful, so usually read-only
        'updated_at_api', #
        'created_at_local', # These are auto-managed by Django
        'updated_at_local', #
    )

    # Optional: How many items to display per page in the admin list view
    list_per_page = 25


from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _ # Import for translation of fieldset titles

from .models import VendorBill, Seller # Ensure Seller is also imported if you have SellerAdmin

@admin.register(VendorBill)
class VendorBillAdmin(admin.ModelAdmin):
    """Admin interface for VendorBill model."""

    # Fields to display in the list view of the admin
    list_display = [
        'name',
        'seller',
        'status',
        'grand_total',
        'currency',
        'period_start_date', # Added new date field
        'period_end_date',   # Added new date field
        'due_date',          # Added new date field
        'created_at_api',    # Show the API's creation timestamp
        'created_at_local',  # Show the local database creation timestamp
        'refresh_action'
    ]

    # Fields to use for filtering in the sidebar
    list_filter = [
        'status',
        'currency',
        'period_start_date', # Added new date field
        'period_end_date',   # Added new date field
        'due_date',          # Added new date field
        'created_at_api',    # Filter by API creation date
        'created_at_local',  # Filter by local creation date
        'seller'
    ]

    # Fields to use for searching
    search_fields = ['name', 'seller__name', 'contract_name']

    # Fields that should not be editable after creation
    # 'name' is the primary key, so it's good to keep it readonly.
    # 'created_at_api' and 'created_at_local' are also generally readonly.
    readonly_fields = [
        'name',
        'created_at_api',
        'created_at_local',
        'updated_at_local' # Also good to have this as readonly
    ]

    # Default ordering for the list view
    ordering = ['-created_at_api'] # Order by API creation date, or choose created_at_local

    # Grouping and ordering fields in the detail view
    fieldsets = (
        (None, {
            'fields': ('name', 'seller', 'status', 'contract_name', 'pdf') # Added 'pdf' here
        }),
        (_('Financial Details'), {
            'fields': ('currency', 'grand_total', 'discount', 'grand_total_after_discount', 'fees', 'hub_bills') # Added JSON fields here
        }),
        (_('Dates'), {
            'fields': ('period_start_date', 'period_end_date', 'due_date', 'created_at_api', 'finalised_on') # Added new date fields and finalised_on
        }),
        (_('Audit Timestamps'), { # New fieldset for local and API timestamps
            'fields': ('created_at_local', 'updated_at_local'),
            'classes': ('collapse',)
        }),
        (_('Additional Info'), {
            'fields': ('finalised_by', 'remark', 'hubs'), # Moved hubs here as it's often more general info
            'classes': ('collapse',) # Collapse this section by default
        }),
    )
    
    # Custom method for the refresh button
    def refresh_action(self, obj):
        """Add refresh button for each bill."""
        # Assuming you have a URL pattern named 'admin:core_vendorbill_refresh'
        # or similar in your app's urls.py that handles refreshing a single bill.
        # This will depend on how your refresh logic is implemented.
        # If 'core:refresh_bill' is a custom view, ensure it's correctly mapped.
        # For admin actions, often you'd create a custom admin action or a custom view.
        # If 'core:refresh_bill' is defined in your main urls.py, it needs to be accessible.
        url = reverse('core:refresh_bill', args=[obj.name]) 
        return format_html(
            '<a class="button" href="{}" onclick="return confirm(\'Refresh bill data for this entry?\')">Refresh</a>',
            url
        )
    refresh_action.short_description = _('Actions')
    refresh_action.allow_tags = True

    # You can also add custom actions for bulk operations if needed
    # actions = ['refresh_selected_bills']

    # def refresh_selected_bills(self, request, queryset):
    #     """Custom admin action to refresh selected bills."""
    #     updated_count = 0
    #     for bill in queryset:
    #         # Call your sync logic for a single bill here
    #         # This would likely involve calling a function that performs
    #         # a similar API call as your management command but for a single bill
    #         # using bill.name or a bill ID.
    #         # Example: refresh_single_bill_from_api(bill.name)
    #         # For simplicity, we'll just mark them as updated in this example.
    #         bill.status = 'refreshed' # Placeholder action
    #         bill.save()
    #         updated_count += 1
    #     self.message_user(request, f"{updated_count} bills successfully refreshed.")
    # refresh_selected_bills.short_description = _("Refresh selected bills from API")

# You might also have a SellerAdmin
# @admin.register(Seller)
# class SellerAdmin(admin.ModelAdmin):
#    list_display = ['name', 'code', 'email', 'is_active', 'created_at_api', 'updated_at_api']
#    search_fields = ['name', 'code', 'email']
#    list_filter = ['is_active']
#    readonly_fields = ['created_at_api', 'updated_at_api', 'created_at_local', 'updated_at_local']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Admin interface for Order model."""
    list_display = ['order_id', 'seller', 'order_type', 'status_code', 'payment_mode', 'total', 'order_created_at', 'days_to_deliver']
    list_filter = ['order_type', 'status_code', 'payment_mode', 'is_delayed', 'delay_category', 'seller']
    search_fields = ['order_id', 'seller__name', 'customer_first_name', 'customer_last_name', 'customer_email']
    readonly_fields = ['order_id', 'omniful_id', 'created_at', 'updated_at', 'days_to_deliver', 'is_delayed', 'delay_category']
    ordering = ['-order_created_at']
    
    fieldsets = (
        (None, {
            'fields': ('order_id', 'omniful_id', 'seller', 'store_name', 'status_code', 'order_type', 'delivery_type')
        }),
        (_('Dates'), {
            'fields': ('order_created_at', 'delivery_date', 'days_to_deliver', 'delay_category', 'is_delayed')
        }),
        (_('Payment'), {
            'fields': ('payment_mode', 'payment_method', 'total')
        }),
        (_('Customer'), {
            'fields': ('customer_first_name', 'customer_last_name', 'customer_email', 'customer_phone')
        }),
        (_('Shipping'), {
            'fields': ('shipping_city', 'shipping_region', 'shipping_country', 'delivery_status')
        }),
        (_('Raw Data'), {
            'fields': ('raw_data',),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )