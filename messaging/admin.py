from django.contrib import admin
from .models import QuoteRequest, Conversation, Message, Notification

@admin.register(QuoteRequest)
class QuoteRequestAdmin(admin.ModelAdmin):
    list_display = ['product', 'requester', 'supplier', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['product__name', 'requester__company_name', 'supplier__company_name']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['quote_request', 'created_at', 'updated_at']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['conversation', 'sender', 'created_at', 'is_read']
    list_filter = ['is_read', 'created_at']
    search_fields = ['content', 'sender__company_name']

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['recipient', 'notification_type', 'title', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['title', 'recipient__company_name']
