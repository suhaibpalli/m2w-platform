from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Company

class CompanyInline(admin.StackedInline):
    model = Company
    can_delete = False
    verbose_name_plural = 'Company Profile'
    fields = (
        'company_types', 'other_company_type', 'sectors', 'other_sector',
        'company_name', 'description', 'cr_number', 'contact_person_name',
        'contact_email', 'contact_phone', 'company_address',
        'subscription_status', 'subscription_start_date', 'subscription_end_date', 
        'is_verified'
    )
    
    # Add readonly_fields to show JSONField contents nicely
    readonly_fields = ('company_types_display', 'sectors_display')
    
    def company_types_display(self, obj):
        if obj and obj.company_types:
            return ', '.join(obj.company_types)
        return 'Not specified'
    company_types_display.short_description = 'Selected Company Types'
    
    def sectors_display(self, obj):
        if obj and obj.sectors:
            return ', '.join(obj.sectors)
        return 'Not specified'
    sectors_display.short_description = 'Selected Sectors'

class CustomUserAdmin(UserAdmin):
    inlines = (CompanyInline,)
    list_display = (
        'username', 'email', 'get_company_name',
        'get_company_types', 'get_sectors', 'get_subscription_status',
        'is_staff', 'date_joined'
    )
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'company__subscription_status')
    
    def get_company_name(self, obj):
        return obj.company.company_name if hasattr(obj, 'company') else 'No Company'
    get_company_name.short_description = 'Company'
    
    def get_company_types(self, obj):
        if hasattr(obj, 'company') and obj.company.company_types:
            return ', '.join(obj.company.company_types)
        return 'Not specified'
    get_company_types.short_description = 'Company Types'
    
    def get_sectors(self, obj):
        if hasattr(obj, 'company') and obj.company.sectors:
            return ', '.join(obj.company.sectors)
        return 'Not specified'
    get_sectors.short_description = 'Sectors'
    
    def get_subscription_status(self, obj):
        return obj.company.subscription_status if hasattr(obj, 'company') else 'No Status'
    get_subscription_status.short_description = 'Subscription'

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = [
        'company_name', 'user', 'get_company_types_display', 'get_sectors_display',
        'subscription_status', 'is_verified', 'created_at'
    ]
    list_filter = ['subscription_status', 'is_verified', 'created_at']
    search_fields = ['company_name', 'user__email', 'user__username']
    
    # Remove filter_horizontal for JSONFields
    # filter_horizontal = ['company_types', 'sectors']  # Remove this line
    
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'company_name', 'description')
        }),
        ('Company Type & Sectors', {
            'fields': ('company_types', 'other_company_type', 'sectors', 'other_sector')
        }),
        ('Contact Information', {
            'fields': ('contact_person_name', 'contact_email', 'contact_phone', 'company_address')
        }),
        ('Business Registration', {
            'fields': ('cr_number',)
        }),
        ('Subscription', {
            'fields': ('subscription_status', 'subscription_start_date', 'subscription_end_date', 'is_verified')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    # Add methods to display JSONField contents nicely
    def get_company_types_display(self, obj):
        if obj.company_types:
            return ', '.join(obj.company_types)
        return 'Not specified'
    get_company_types_display.short_description = 'Company Types'
    
    def get_sectors_display(self, obj):
        if obj.sectors:
            return ', '.join(obj.sectors)
        return 'Not specified'
    get_sectors_display.short_description = 'Sectors'

# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
