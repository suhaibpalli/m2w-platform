from django.db import models
from accounts.models import Company
from decimal import Decimal
import json


class Payment(models.Model):
    """Track all payment transactions"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('authorized', 'Authorized'),
        ('captured', 'Captured'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    PAYMENT_TYPE_CHOICES = [
        ('registration', 'Registration Fee'),
        ('subscription_renewal', 'Subscription Renewal'),
        ('one_time', 'One-time Purchase'),
    ]
    
    # Relationships
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='payments')
    
    # Payment Details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='AED')  # FIX: Changed from USD to AED
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_type = models.CharField(max_length=30, choices=PAYMENT_TYPE_CHOICES, default='registration')
    
    # N-Genius References
    order_id = models.CharField(max_length=100, unique=True)
    session_id = models.CharField(max_length=255, blank=True)
    transaction_reference = models.CharField(max_length=255, blank=True)
    authorization_code = models.CharField(max_length=100, blank=True)
    
    # Additional Data
    webhook_data = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'
        indexes = [
            models.Index(fields=['company', '-created_at']),
            models.Index(fields=['order_id']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.company.company_name} - {self.amount} {self.currency} ({self.status})"
    
    @property
    def amount_in_cents(self):
        """Returns the amount as an integer in minor currency units (e.g., fils).
        10 AED = 1000 fils
        """
        return int(self.amount * 100)

    @property
    def is_successful(self):
        """Check if payment was successful"""
        return self.status in ['captured', 'authorized']
    
    @property
    def is_pending(self):
        """Check if payment is still pending"""
        return self.status == 'pending'
