from django.contrib import admin
from django import forms
from django.utils.safestring import mark_safe
from .models import Industry, ContactInquiry, SiteSettings, HeroCarouselImage, TestimonialCarousel

class IndustryImageForm(forms.ModelForm):
    image_upload = forms.ImageField(
        required=False,
        help_text="Upload industry image (JPG, PNG). Recommended size: 800x600px"
    )
    
    class Meta:
        model = Industry
        fields = ['name', 'slug', 'description', 'icon', 'is_active']
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.cleaned_data.get('image_upload'):
            instance.add_image_from_file(self.cleaned_data['image_upload'])
        if commit:
            instance.save()
        return instance

@admin.register(Industry)
class IndustryAdmin(admin.ModelAdmin):
    form = IndustryImageForm
    list_display = ['name', 'slug', 'display_order', 'is_active', 'has_image', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'image_preview']
    list_editable = ['display_order']  # Allow editing order directly in list view

    def get_fieldsets(self, request, obj=None):
        if obj:  # editing an existing object
            return (
                ('Basic Information', {
                    'fields': ('name', 'slug', 'description', 'icon', 'display_order')
                }),
                ('Image', {
                    'fields': ('image_upload', 'image_preview')
                }),
                ('Settings', {
                    'fields': ('is_active', 'created_at'),
                }),
            )
        else:  # adding a new object
            return (
                ('Basic Information', {
                    'fields': ('name', 'slug', 'description', 'icon', 'display_order')
                }),
                ('Image', {
                    'fields': ('image_upload',)
                }),
                ('Settings', {
                    'fields': ('is_active',)
                }),
            )

    def has_image(self, obj):
        return bool(obj.image)
    has_image.boolean = True
    has_image.short_description = "Has Image"

    def image_preview(self, obj):
        if obj and obj.image:
            return mark_safe(f'<img src="{obj.image}" style="max-height: 200px; max-width: 300px; border-radius: 8px;" />')
        return "No image uploaded"
    image_preview.short_description = "Current Image"

@admin.register(ContactInquiry)
class ContactInquiryAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'subject', 'created_at', 'is_responded']
    list_filter = ['is_responded', 'created_at']
    search_fields = ['name', 'email', 'subject']
    readonly_fields = ['created_at']

class SiteSettingsForm(forms.ModelForm):
    logo_upload = forms.ImageField(
        required=False,
        help_text="Upload site logo (SVG, PNG, JPG). Recommended size: 200x60px"
    )
    
    class Meta:
        model = SiteSettings
        fields = ['site_name', 'annual_fee', 'currency', 'contact_email', 'contact_phone', 'address']
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.cleaned_data.get('logo_upload'):
            instance.add_logo_from_file(self.cleaned_data['logo_upload'])
        if commit:
            instance.save()
        return instance

@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    form = SiteSettingsForm
    list_display = ['site_name', 'annual_fee', 'currency']
    readonly_fields = ['logo_preview']
    
    def get_fieldsets(self, request, obj=None):
        if obj:  # editing an existing object
            return (
                ('Site Information', {
                    'fields': ('site_name', 'logo_upload', 'logo_preview')
                }),
                ('Financial Settings', {
                    'fields': ('annual_fee', 'currency')
                }),
                ('Contact Information', {
                    'fields': ('contact_email', 'contact_phone', 'address')
                }),
            )
        else:  # adding a new object
            return (
                ('Site Information', {
                    'fields': ('site_name', 'logo_upload')
                }),
                ('Financial Settings', {
                    'fields': ('annual_fee', 'currency')
                }),
                ('Contact Information', {
                    'fields': ('contact_email', 'contact_phone', 'address')
                }),
            )
    
    def logo_preview(self, obj):
        if obj and obj.site_logo:
            return mark_safe(f'<img src="{obj.site_logo}" style="max-height: 60px; max-width: 200px;" />')
        return "No logo uploaded"
    logo_preview.short_description = "Current Logo"
    
    def has_add_permission(self, request):
        # Only allow one SiteSettings instance
        return not SiteSettings.objects.exists()

class HeroCarouselImageForm(forms.ModelForm):
    image_upload = forms.ImageField(
        required=False,
        help_text="Upload image (JPG, PNG). Recommended size: 1920x1080px"
    )
    
    class Meta:
        model = HeroCarouselImage
        fields = ['title', 'hero_title', 'hero_subtitle', 'is_active', 'order']  # ADD hero_title, hero_subtitle
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make image_upload required for new instances
        if not self.instance.pk:
            self.fields['image_upload'].required = True
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.cleaned_data.get('image_upload'):
            instance.add_image_from_file(self.cleaned_data['image_upload'])
        if commit:
            instance.save()
        return instance

@admin.register(HeroCarouselImage)
class HeroCarouselImageAdmin(admin.ModelAdmin):
    form = HeroCarouselImageForm
    list_display = ['title', 'is_active', 'order', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['title', 'hero_title']  # ADD hero_title to search
    list_editable = ['is_active', 'order']
    readonly_fields = ['created_at', 'image_preview']
    
    def get_fieldsets(self, request, obj=None):
        if obj:  # editing an existing object
            return (
                ('Image Information', {
                    'fields': ('title', 'image_upload', 'image_preview', 'is_active', 'order')
                }),
                # ADD THIS NEW FIELDSET:
                ('Hero Content', {
                    'fields': ('hero_title', 'hero_subtitle'),
                    'description': 'Text content that will be displayed over this hero image'
                }),
                # END NEW FIELDSET
                ('Metadata', {
                    'fields': ('created_at',),
                    'classes': ('collapse',)
                }),
            )
        else:  # adding a new object
            return (
                ('Image Information', {
                    'fields': ('title', 'image_upload', 'is_active', 'order')
                }),
                # ADD THIS NEW FIELDSET:
                ('Hero Content', {
                    'fields': ('hero_title', 'hero_subtitle'),
                    'description': 'Text content that will be displayed over this hero image'
                }),
                # END NEW FIELDSET
            )
    
    def image_preview(self, obj):
        if obj and obj.image:
            return mark_safe(f'<img src="{obj.image}" style="max-height: 200px; max-width: 300px; border-radius: 8px;" />')
        return "No image uploaded"
    image_preview.short_description = "Current Image"
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return ['created_at', 'image_preview']
        else:  # adding a new object
            return ['created_at']

@admin.register(TestimonialCarousel)
class TestimonialCarouselAdmin(admin.ModelAdmin):
    list_display = ['client_name', 'company_name', 'rating', 'is_active', 'order', 'created_at']
    list_filter = ['is_active', 'rating', 'created_at']
    search_fields = ['client_name', 'company_name', 'testimonial_text']
    list_editable = ['is_active', 'order', 'rating']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Client Information', {
            'fields': ('client_name', 'client_title', 'company_name')
        }),
        ('Testimonial Content', {
            'fields': ('testimonial_text', 'rating')
        }),
        ('Display Settings', {
            'fields': ('is_active', 'order')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).order_by('order', '-created_at')
