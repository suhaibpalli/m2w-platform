from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Company

class CompanyInline(admin.StackedInline):
    model = Company
    can_delete = False
    verbose_name_plural = 'Company Profile'
    fields = (
        'role', 'company_name', 'description', 'industries', 'other_industry',
        'contact_email', 'contact_phone', 'subscription_status',
        'subscription_start_date', 'subscription_end_date', 'is_verified'
    )

class CustomUserAdmin(UserAdmin):
    inlines = (CompanyInline,)
    list_display = (
        'username', 'email', 'get_company_name',
        'get_company_role', 'get_subscription_status',
        'is_staff', 'date_joined'
    )
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'company__subscription_status')
    
    def get_company_name(self, obj):
        return obj.company.company_name if hasattr(obj, 'company') else 'No Company'
    get_company_name.short_description = 'Company'
    
    def get_company_role(self, obj):
        return obj.company.role if hasattr(obj, 'company') else ''
    get_company_role.short_description = 'Role'
    
    def get_subscription_status(self, obj):
        return obj.company.subscription_status if hasattr(obj, 'company') else 'No Status'
    get_subscription_status.short_description = 'Subscription'

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = [
        'company_name', 'user', 'role',
        'subscription_status', 'is_verified', 'created_at'
    ]
    list_filter = ['subscription_status', 'is_verified', 'created_at']
    search_fields = ['company_name', 'user__email', 'user__username']
    filter_horizontal = ['industries']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'company_name', 'description')
        }),
        ('Contact Information', {
            'fields': ('contact_email', 'contact_phone')
        }),
        ('Business Registration', {
            'fields': ('registration_number', 'country_of_registration')
        }),
        ('Industries', {
            'fields': ('industries', 'other_industry')
        }),
        ('Subscription', {
            'fields': ('subscription_status', 'subscription_start_date', 'subscription_end_date', 'is_verified')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
