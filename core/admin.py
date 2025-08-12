from django.contrib import admin
from django import forms
from django.utils.safestring import mark_safe
from .models import Industry, ContactInquiry, SiteSettings, HeroCarouselImage, TestimonialCarousel

@admin.register(Industry)
class IndustryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(ContactInquiry)
class ContactInquiryAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'subject', 'created_at', 'is_responded']
    list_filter = ['is_responded', 'created_at']
    search_fields = ['name', 'email', 'subject']
    readonly_fields = ['created_at']

@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ['site_name', 'annual_fee', 'currency']
    
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
        fields = ['title', 'is_active', 'order']
    
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
    search_fields = ['title']
    list_editable = ['is_active', 'order']
    readonly_fields = ['created_at', 'image_preview']
    
    def get_fieldsets(self, request, obj=None):
        if obj:  # editing an existing object
            return (
                ('Image Information', {
                    'fields': ('title', 'image_upload', 'image_preview', 'is_active', 'order')
                }),
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
