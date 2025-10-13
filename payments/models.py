# payments/models.py
from django.db import models
from accounts.models import Company
from django.utils import timezone

class Payment(models.Model):
    """Payment records for subscription fees"""
    
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    PAYMENT_TYPE = [
        ('subscription', 'Annual Subscription'),
        ('product', 'Product Order'),
    ]
    
    # Core fields
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='payments')
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE, default='subscription')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    
    # N-Genius specific fields
    ngenius_order_ref = models.CharField(max_length=100, blank=True)
    ngenius_payment_ref = models.CharField(max_length=100, blank=True)
    ngenius_session_id = models.CharField(max_length=255, blank=True)
    
    # Status tracking
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Additional metadata
    payment_method = models.CharField(max_length=50, blank=True)  # VISA, Mastercard, etc.
    transaction_details = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.company.company_name} - {self.amount} {self.currency} ({self.status})"
