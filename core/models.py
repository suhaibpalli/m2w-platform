from django.db import models
from django.utils.text import slugify

class Industry(models.Model):
    """Industries supported by the platform"""
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)  # CSS class for icon
    image = models.TextField(blank=True, help_text="Base64 encoded industry image")  # Add this line
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0, help_text="Order for display (lower numbers first)")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Industries"
        ordering = ['display_order', 'name']  # ← Updated to use display_order first
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name
    
    def add_image_from_file(self, image_file):
        """Convert uploaded file to base64"""
        import base64
        
        # Reset file pointer to beginning
        image_file.seek(0)
        
        encoded = base64.b64encode(image_file.read()).decode('utf-8')
        mime_type = image_file.content_type
        self.image = f"data:{mime_type};base64,{encoded}"


class ContactInquiry(models.Model):
    """Contact form submissions"""
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_responded = models.BooleanField(default=False)
    
    class Meta:
        verbose_name_plural = "Contact Inquiries"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.subject}"

class SiteSettings(models.Model):
    """Site-wide settings"""
    site_name = models.CharField(max_length=100, default="MWPUAE Platform")
    annual_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="USD")
    contact_email = models.EmailField(default="info@mwpuaeplatform.com")
    contact_phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    # Add this new field
    site_logo = models.TextField(blank=True, help_text="Base64 encoded site logo")
    
    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"
    
    def __str__(self):
        return self.site_name
    
    # Add this method
    def add_logo_from_file(self, logo_file):
        """Convert uploaded file to base64"""
        import base64
        
        # Reset file pointer to beginning
        logo_file.seek(0)
        
        encoded = base64.b64encode(logo_file.read()).decode('utf-8')
        mime_type = logo_file.content_type
        self.site_logo = f"data:{mime_type};base64,{encoded}"


class HeroCarouselImage(models.Model):
    """Hero carousel background images"""
    title = models.CharField(max_length=200)
    # ADD THESE NEW FIELDS:
    hero_title = models.CharField(
        max_length=300, 
        default="Connect in Metal, Wood, Plastic, Machineries, Technology",
        help_text="Main hero title text"
    )
    hero_subtitle = models.TextField(
        default="Streamline your B2B trading with our multi-vendor platform. Find verified suppliers, secure payments, and industry-focused solutions.",
        help_text="Hero subtitle/description text"
    )
    # END NEW FIELDS
    image = models.TextField(help_text="Base64 encoded image data")
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0, help_text="Display order (lower numbers first)")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', '-created_at']
        verbose_name = "Hero Carousel Image"
        verbose_name_plural = "Hero Carousel Images"
    
    def __str__(self):
        return self.title
    
    def add_image_from_file(self, image_file):
        """Convert uploaded file to base64"""
        import base64

        # Reset file pointer to beginning
        image_file.seek(0)

        encoded = base64.b64encode(image_file.read()).decode('utf-8')
        mime_type = image_file.content_type
        self.image = f"data:{mime_type};base64,{encoded}"


class TestimonialCarousel(models.Model):
    """Client testimonials carousel"""
    client_name = models.CharField(max_length=200)
    client_title = models.CharField(max_length=200, help_text="e.g., CEO, Manager, Founder")
    company_name = models.CharField(max_length=200)
    testimonial_text = models.TextField(help_text="The testimonial content")
    rating = models.PositiveIntegerField(
        default=5,
        choices=[(i, f"{i} Star{'s' if i != 1 else ''}") for i in range(1, 6)],
        help_text="Rating out of 5 stars"
    )
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0, help_text="Display order (lower numbers first)")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', '-created_at']
        verbose_name = "Client Testimonial"
        verbose_name_plural = "Client Testimonials"
    
    def __str__(self):
        return f"{self.client_name} - {self.company_name}"
    
    def get_star_display(self):
        """Return star emojis for rating"""
        return "⭐" * self.rating
