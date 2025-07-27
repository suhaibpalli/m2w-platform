from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from core.models import Industry

class Company(models.Model):
    """Company profile linked to User"""
    ROLE_CHOICES = [
        ('vendor', 'Vendor'),
        ('business_buyer', 'Business Buyer'),
        ('consumer_buyer', 'Consumer Buyer'),
    ]
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='vendor',
        help_text="Are you registering as a vendor or buyer?"
    )
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
    
    # Contact Information
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    
    # Business Registration
    registration_number = models.CharField(max_length=100, blank=True)
    country_of_registration = models.CharField(max_length=100, blank=True)
    
    # Industries
    industries = models.ManyToManyField(Industry, blank=True)
    other_industry = models.CharField(max_length=200, blank=True)
    
    # Subscription
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

# Signal to create Company when User is created
@receiver(post_save, sender=User)
def create_user_company(sender, instance, created, **kwargs):
    if created:
        Company.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_company(sender, instance, **kwargs):
    if hasattr(instance, 'company'):
        instance.company.save()
