from django.contrib import admin
from .models import Product, Category

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'industry', 'parent', 'is_active', 'created_at']
    list_filter = ['industry', 'is_active', 'created_at']
    search_fields = ['name', 'industry__name']
    list_editable = ['is_active']
    raw_id_fields = ['parent']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'company', 'category', 'price', 'currency', 'status', 'featured', 'views_count', 'created_at']
    list_filter = ['status', 'category__industry', 'created_at', 'featured']
    search_fields = ['name', 'company__company_name', 'tags']
    list_editable = ['status', 'featured']
    readonly_fields = ['views_count', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('company', 'name', 'category', 'description')
        }),
        ('Pricing & Specifications', {
            'fields': ('price', 'currency', 'minimum_order_quantity', 'lead_time')
        }),
        ('Images & Tags', {
            'fields': ('images', 'tags')
        }),
        ('Status & Visibility', {
            'fields': ('status', 'featured')
        }),
        ('Metadata', {
            'fields': ('views_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
