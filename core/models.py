from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
import json


class TimeStampedModel(models.Model):
    """Base model with created and updated timestamps."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, blank=True)
    department = models.CharField(max_length=100, blank=True)
    company = models.ForeignKey(
        'Company', on_delete=models.SET_NULL, null=True, blank=True)
    preferred_language = models.CharField(
        max_length=10, choices=[('en', 'English'), ('ar', 'Arabic')], default='en')

    def __str__(self):
        return f"{self.user.username}'s profile"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()


class Company(models.Model):
    name = models.CharField(max_length=100)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    logo = models.ImageField(upload_to='company_logos/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Companies"


class Seller(models.Model):
    guid = models.CharField(max_length=255, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField(max_length=255, blank=True, null=True)
    code = models.CharField(max_length=100, blank=True, null=True)
    address = models.JSONField(blank=True, null=True)
    # <-- ADD THIS FIELD for is_active
    is_active = models.BooleanField(default=True, db_index=True)

    created_at_api = models.DateTimeField(null=True, blank=True)
    updated_at_api = models.DateTimeField(null=True, blank=True)

    created_at_local = models.DateTimeField(auto_now_add=True)
    updated_at_local = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Seller"
        verbose_name_plural = "Sellers"

    def __str__(self):
        return self.name


class VendorBill(models.Model):
    # RECOMMENDATION: Let Django create its default 'id' PK
    # If you remove primary_key=True, Django will automatically add 'id' as the PK.
    # This is generally preferred unless 'name' is truly a stable, immutable, and unique identifier for *all* bills.
    # REMOVED: primary_key=True
    name = models.CharField(max_length=255, unique=True)

    seller = models.ForeignKey(
        Seller, on_delete=models.PROTECT, related_name='vendor_bills')

    # JSON fields should allow null if default=list, to be consistent with DB TEXT NULLable
    hubs = models.JSONField(default=list, blank=True,
                            null=True)  # Added null=True
    status = models.CharField(max_length=50, default='draft')

    # URLField allows blank and null by default
    pdf = models.URLField(max_length=500, blank=True, null=True)

    contract_name = models.CharField(
        max_length=255, blank=True, null=True)  # Added blank=True, null=True

    # Date and Time Fields - Ensure these are DateTimeField as per sync script
    period_start_date = models.DateTimeField(null=True, blank=True)
    period_end_date = models.DateTimeField(null=True, blank=True)
    due_date = models.DateTimeField(null=True, blank=True)

    currency = models.CharField(max_length=10, default='USD')
    grand_total = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00)
    discount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00)
    grand_total_after_discount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00)

    # These should be nullable
    finalised_on = models.DateTimeField(null=True, blank=True)
    # finalised_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True) # If linking to User
    # Changed to allow null/blank
    finalised_by = models.CharField(max_length=255, blank=True, null=True)
    # Added blank=True, null=True
    remark = models.TextField(blank=True, null=True)

    # JSON fields should allow null if default=list, to be consistent with DB TEXT NULLable
    fees = models.JSONField(default=list, blank=True,
                            null=True)  # Added null=True
    hub_bills = models.JSONField(
        default=list, blank=True, null=True)  # Added null=True

    # New timestamp fields (from API and local)
    created_at_api = models.DateTimeField(
        null=True, blank=True)  # Timestamp from Omniful API
    created_at_local = models.DateTimeField(
        auto_now_add=True)   # Timestamp when saved to your DB
    # Timestamp when last updated in your DB
    updated_at_local = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Vendor Bill"
        verbose_name_plural = "Vendor Bills"
        ordering = ['-created_at_api']


class Order(models.Model):
    ORDER_STATUS_CHOICES = [
        ('new_order', 'New Order'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('returned', 'Returned'),
        ('failed', 'Failed'),
    ]

    ORDER_TYPE_CHOICES = [
        ('B2B', 'B2B'),
        ('B2C', 'B2C'),
    ]

    PAYMENT_MODE_CHOICES = [
        ('Cash On Delivery', 'Cash On Delivery'),
        ('Prepaid', 'Prepaid'),
    ]

    # Basic order info
    order_id = models.CharField(max_length=100, unique=True)
    omniful_id = models.CharField(max_length=100, unique=True)
    order_alias = models.CharField(max_length=100, blank=True, null=True)
    seller = models.ForeignKey(
        Seller, on_delete=models.CASCADE, related_name='orders')
    seller_code = models.CharField(max_length=50, blank=True, null=True)
    store_name = models.CharField(max_length=255)
    status_code = models.CharField(max_length=50, choices=ORDER_STATUS_CHOICES)
    source = models.CharField(max_length=100, blank=True, null=True)
    order_type = models.CharField(max_length=10, choices=ORDER_TYPE_CHOICES)
    delivery_type = models.CharField(max_length=50, blank=True)

    # Dates
    order_created_at = models.DateTimeField()
    created_at_api = models.DateTimeField(blank=True, null=True)
    last_updated_at = models.DateTimeField(auto_now=True)
    delivery_date = models.DateTimeField(null=True, blank=True)

    # Payment info
    payment_mode = models.CharField(
        max_length=50, choices=PAYMENT_MODE_CHOICES)
    payment_method = models.CharField(max_length=50, blank=True)
    total = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    # Address info
    billing_address = models.JSONField(default=dict, blank=True, null=True)
    shipping_address = models.JSONField(default=dict, blank=True, null=True)
    shipping_city = models.CharField(max_length=100, blank=True)
    shipping_region = models.CharField(max_length=100, blank=True)
    shipping_country = models.CharField(max_length=100, blank=True)

    # Customer info
    customer = models.JSONField(default=dict, blank=True, null=True)
    customer_first_name = models.CharField(max_length=100)
    customer_last_name = models.CharField(max_length=100)
    customer_email = models.EmailField(blank=True, null=True)
    customer_phone = models.CharField(max_length=50, blank=True, null=True)

    # Shipment info
    shipment = models.JSONField(default=dict, blank=True, null=True)
    delivery_status = models.CharField(max_length=50, blank=True)
    tracking_url = models.URLField(blank=True, null=True)
    shipment_type = models.CharField(max_length=50, blank=True, null=True)
    require_shipping = models.BooleanField(default=True)
    cancel_order_after_seconds = models.IntegerField(default=0)
    expected_delivery_epoch = models.BigIntegerField(default=0)

    # Invoice details
    invoice = models.JSONField(default=dict, blank=True, null=True)

    # Calculated fields
    days_to_deliver = models.IntegerField(null=True, blank=True)
    is_delayed = models.BooleanField(default=False)
    delay_category = models.CharField(
        max_length=20, blank=True)  # 'green', 'yellow', 'red'

    # Raw data
    raw_data = models.JSONField(default=dict)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.order_id} - {self.seller.name}"

    def save(self, *args, **kwargs):
        # Calculate delivery metrics
        if self.delivery_date and self.order_created_at:
            delta = self.delivery_date - self.order_created_at
            self.days_to_deliver = delta.days

            if self.days_to_deliver <= 5:
                self.delay_category = 'green'
            elif self.days_to_deliver <= 10:
                self.delay_category = 'yellow'
            else:
                self.delay_category = 'red'
                self.is_delayed = True

        # Check if new order is delayed (>2 days old)
        if self.status_code == 'new_order' and self.order_created_at:
            delta = timezone.now() - self.order_created_at
            if delta.days > 2:
                self.is_delayed = True

        super().save(*args, **kwargs)


class SyncLog(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    log = models.TextField(blank=True)
    completed = models.BooleanField(default=False)
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True)
