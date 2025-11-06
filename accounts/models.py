from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from core.models import Industry

class Company(models.Model):
    """Company profile linked to User"""

    COMPANY_TYPE_CHOICES = [
        ('manufacturer', 'Manufacturer'),
        ('trader', 'Trader'),
        ('buyer', 'Buyer'),
        ('seller', 'Seller'),
        ('distributor', 'Distributor'),
        ('service_provider', 'Service Provider'),
        ('other', 'Other'),
    ]

    SECTOR_CHOICES = [
        ('metal', 'Metal'),
        ('wood', 'Wood'),
        ('plastic', 'Plastic'),
        ('technology', 'Technology'),
        ('machinery', 'Machinery'),
        ('other', 'Other'),
    ]

    SUBSCRIPTION_STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('pending', 'Pending Payment'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='company')
    company_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    logo = models.TextField(blank=True)  # Base64 encoded logo

    # New fields for unified registration
    company_types = models.JSONField(default=list, blank=True, help_text="List of company types")
    sectors = models.JSONField(default=list, blank=True, help_text="List of business sectors")
    other_company_type = models.CharField(max_length=200, blank=True)
    other_sector = models.CharField(max_length=200, blank=True)

    # Contact Information (existing, non-duplicated fields)
    contact_person_name = models.CharField(max_length=200, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    company_address = models.TextField(blank=True)

    # Billing fields for payment gateway (N-Genius 3DS2 requirement)
    billing_city = models.CharField(max_length=100, blank=True, default="Dubai")
    billing_state = models.CharField(max_length=100, blank=True, default="Dubai")
    billing_country = models.CharField(max_length=100, blank=True, default="United Arab Emirates")
    billing_country_code = models.CharField(max_length=2, blank=True, default="AE")
    billing_postal_code = models.CharField(max_length=20, blank=True, default="00000")

    # Business Registration
    cr_number = models.CharField(max_length=100, blank=True, help_text="CR Number / VAT / Tax ID")
    country_of_registration = models.CharField(max_length=100, blank=True)

    # Industries (keep for backward compatibility)
    industries = models.ManyToManyField(Industry, blank=True)
    other_industry = models.CharField(max_length=200, blank=True)

    # Subscription - Now flat rate for everyone
    subscription_status = models.CharField(
        max_length=20,
        choices=SUBSCRIPTION_STATUS_CHOICES,
        default='pending'
    )
    subscription_start_date = models.DateTimeField(null=True, blank=True)
    subscription_end_date = models.DateTimeField(null=True, blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_verified = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "Companies"
        ordering = ['-created_at']

    def __str__(self):
        return self.company_name or f"Company of {self.user.email}"

    @property
    def is_subscription_active(self):
        return self.subscription_status == 'active'

    @property
    def primary_company_type(self):
        """Return the first company type for display purposes"""
        if self.company_types:
            return self.company_types[0]
        return 'Not specified'

    @property
    def primary_sector(self):
        """Return the first sector for display purposes"""
        if self.sectors:
            return self.sectors[0]
        return 'Not specified'

# Keep the existing signals
@receiver(post_save, sender=User)
def create_user_company(sender, instance, created, **kwargs):
    if created:
        Company.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_company(sender, instance, **kwargs):
    if hasattr(instance, 'company'):
        instance.company.save()
