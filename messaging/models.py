from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from accounts.models import Company
from products.models import Product
from django.utils import timezone

class QuoteRequest(models.Model):
    """Quote requests from buyers to suppliers"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('responded', 'Responded'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('closed', 'Closed'),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='quote_requests')
    requester = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='sent_quotes')
    supplier = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='received_quotes')
    
    # Quote details
    message = models.TextField()
    quantity = models.CharField(max_length=100, blank=True)
    target_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    delivery_location = models.CharField(max_length=200, blank=True)
    expected_delivery = models.CharField(max_length=100, blank=True)
    
    # Contact details
    contact_name = models.CharField(max_length=100)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['supplier', '-created_at']),
            models.Index(fields=['requester', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]
    
    def __str__(self):
        return f"Quote for {self.product.name} from {self.requester.company_name}"
    
    def get_absolute_url(self):
        return reverse('messaging:quote_detail', kwargs={'pk': self.pk})

class Conversation(models.Model):
    """Conversation thread between two companies"""
    quote_request = models.OneToOneField(QuoteRequest, on_delete=models.CASCADE, related_name='conversation')
    participants = models.ManyToManyField(Company, related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"Conversation about {self.quote_request.product.name}"
    
    def get_other_participant(self, company):
        """Get the other participant in the conversation"""
        return self.participants.exclude(pk=company.pk).first()

class Message(models.Model):
    """Individual messages within a conversation"""
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    
    # Attachments (if needed)
    attachment = models.TextField(blank=True)  # Base64 encoded file if needed
    
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Message from {self.sender.company_name} at {self.created_at}"

class Notification(models.Model):
    """Notifications for quote requests and messages"""
    TYPES = [
        ('quote_request', 'Quote Request'),
        ('quote_response', 'Quote Response'),
        ('new_message', 'New Message'),
        ('quote_status_change', 'Quote Status Change'),
    ]
    
    recipient = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Related objects
    quote_request = models.ForeignKey(QuoteRequest, on_delete=models.CASCADE, null=True, blank=True)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, null=True, blank=True)
    
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Notification for {self.recipient.company_name}: {self.title}"
