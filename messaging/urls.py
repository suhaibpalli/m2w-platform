from django.urls import path
from . import views

app_name = 'messaging'

urlpatterns = [
    # Quote requests
    path('quote/<int:product_id>/', views.QuoteRequestCreateView.as_view(), name='request_quote'),
    
    # Messages and conversations
    path('', views.MessagesListView.as_view(), name='messages'),
    path('conversation/<int:pk>/', views.ConversationDetailView.as_view(), name='conversation'),
    
    # Quote management
    path('quotes/received/', views.QuotesReceivedView.as_view(), name='quotes_received'),
    path('quotes/sent/', views.QuotesSentView.as_view(), name='quotes_sent'),
    
    # Notifications
    path('notifications/', views.NotificationsView.as_view(), name='notifications'),
    
    # AJAX endpoints
    path('api/unread-count/', views.get_unread_count, name='unread_count'),
]
