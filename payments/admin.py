from django.contrib import admin
from .models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'order_id', 'company', 'amount', 'currency', 'status', 
        'payment_type', 'created_at'
    ]
    list_filter = ['status', 'payment_type', 'currency', 'created_at']
    search_fields = ['order_id', 'company__company_name', 'transaction_reference']
    readonly_fields = [
        'order_id', 'session_id', 'transaction_reference', 
        'created_at', 'updated_at', 'completed_at', 'webhook_data'
    ]
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_id', 'company', 'payment_type', 'created_at')
        }),
        ('Payment Details', {
            'fields': ('amount', 'currency', 'status')
        }),
        ('N-Genius References', {
            'fields': ('session_id', 'transaction_reference', 'authorization_code'),
            'classes': ('collapse',)
        }),
        ('Additional Data', {
            'fields': ('error_message', 'webhook_data'),
            'classes': ('collapse',)
        }),
        ('Timeline', {
            'fields': ('updated_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        return False  # Payments created only through checkout
    
    def has_delete_permission(self, request, obj=None):
        return False  # Never delete payment records
