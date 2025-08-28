from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from core.models import Industry
from accounts.models import Company
import json

class Category(models.Model):
    """Product categories within industries"""
    name = models.CharField(max_length=100)
    industry = models.ForeignKey(Industry, on_delete=models.CASCADE, related_name='categories')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['industry', 'name']
    
    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return f"{self.industry.name} > {self.name}"

class Product(models.Model):
    """Product listings by companies"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('pending', 'Pending Approval'),
        ('sold', 'Sold'),
        ('expired', 'Expired'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    description = models.TextField()
    price = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    
    # Specifications
    minimum_order_quantity = models.CharField(max_length=100, blank=True)
    lead_time = models.CharField(max_length=100, blank=True)
    
    # Images stored as base64 JSON array
    images = models.JSONField(default=list, blank=True)
    
    # Tags and keywords
    tags = models.TextField(blank=True, help_text="Comma-separated tags")
    
    # Status and metadata
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    featured = models.BooleanField(default=False)
    views_count = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['category', 'status']),
            models.Index(fields=['company', 'status']),
        ]
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('products:detail', kwargs={'pk': self.pk})
    
    @property
    def main_image(self):
        """Get the first image or return None"""
        if self.images:
            return self.images[0]
        return None
    
    @property
    def tag_list(self):
        """Convert comma-separated tags to list"""
        if self.tags:
            return [tag.strip() for tag in self.tags.split(',') if tag.strip()]
        return []
    
    def add_image(self, image_file):
        """Add base64 encoded image to images list"""
        import base64
        encoded = base64.b64encode(image_file.read()).decode('utf-8')
        mime_type = image_file.content_type
        image_data = f"data:{mime_type};base64,{encoded}"
        
        if not self.images:
            self.images = []
        if len(self.images) < 5:  # Limit to 5 images total
            self.images.append(image_data)
    
    def add_images(self, image_files):
        """Add new images while keeping existing ones"""
        if not self.images:
            self.images = []
        for image_file in image_files:
            if len(self.images) >= 5:  # Limit to 5 images total
                break
            self.add_image(image_file)
    
    def remove_image(self, image_url):
        """Remove a specific image from the images list"""
        if self.images and image_url in self.images:
            self.images.remove(image_url)
    
    def increment_views(self):
        """Increment view count"""
        self.views_count += 1
        self.save(update_fields=['views_count'])
