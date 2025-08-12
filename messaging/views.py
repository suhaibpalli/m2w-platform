from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q, Count
from .models import QuoteRequest, Conversation, Message, Notification
from .forms import QuoteRequestForm, MessageForm, QuoteResponseForm
from products.models import Product
from accounts.models import Company

class QuoteRequestCreateView(LoginRequiredMixin, CreateView):
    """Create a new quote request"""
    model = QuoteRequest
    form_class = QuoteRequestForm
    template_name = 'messaging/quote_request_form.html'
    
    def dispatch(self, request, *args, **kwargs):
        self.product = get_object_or_404(Product, pk=self.kwargs['product_id'])
        
        # Check if user's company is active
        if request.user.company.subscription_status != 'active':
            messages.error(request, 'You need an active subscription to request quotes.')
            return redirect('core:pricing')
        
        # Prevent vendors from requesting quotes on their own products
        if request.user.company == self.product.company:
            messages.error(request, 'You cannot request a quote for your own product.')
            return redirect('products:detail', pk=self.product.pk)
            
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['product'] = self.product
        return context
    
    def form_valid(self, form):
        form.instance.product = self.product
        form.instance.requester = self.request.user.company
        form.instance.supplier = self.product.company
        
        quote_request = form.save()
        
        # Create conversation
        conversation = Conversation.objects.create(quote_request=quote_request)
        conversation.participants.add(quote_request.requester, quote_request.supplier)
        
        # Send notification email to supplier
        self.send_quote_notification(quote_request)
        
        # Create in-app notification
        Notification.objects.create(
            recipient=quote_request.supplier,
            notification_type='quote_request',
            title=f'New Quote Request for {quote_request.product.name}',
            message=f'{quote_request.requester.company_name} has requested a quote for your product.',
            quote_request=quote_request
        )
        
        messages.success(self.request, 'Quote request sent successfully! The supplier will be notified.')
        return redirect('products:detail', pk=self.product.pk)
    
    def send_quote_notification(self, quote_request):
        """Send email notification to supplier"""
        try:
            subject = f'New Quote Request for {quote_request.product.name}'
            message = f"""
            Dear {quote_request.supplier.company_name},

            You have received a new quote request for your product: {quote_request.product.name}

            From: {quote_request.requester.company_name}
            Contact: {quote_request.contact_name} ({quote_request.contact_email})
            
            Quote Details:
            - Quantity: {quote_request.quantity}
            - Target Price: ${quote_request.target_price}
            - Delivery Location: {quote_request.delivery_location}
            - Expected Delivery: {quote_request.expected_delivery}
            
            Message:
            {quote_request.message}
            
            Please log in to your dashboard to respond: {self.request.build_absolute_uri(reverse('dashboard:home'))}
            
            Best regards,
            MWPUAE Platform Team
            """
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [quote_request.supplier.contact_email or quote_request.supplier.user.email],
                fail_silently=True,
            )
        except Exception as e:
            # Log error but don't break the flow
            print(f"Email sending failed: {e}")

class MessagesListView(LoginRequiredMixin, ListView):
    """List all conversations for the user"""
    model = Conversation
    template_name = 'messaging/messages_list.html'
    context_object_name = 'conversations'
    paginate_by = 20
    
    def get_queryset(self):
        return Conversation.objects.filter(
            participants=self.request.user.company
        ).select_related('quote_request__product', 'quote_request__requester', 'quote_request__supplier')

class ConversationDetailView(LoginRequiredMixin, DetailView):
    """View conversation thread"""
    model = Conversation
    template_name = 'messaging/conversation_detail.html'
    context_object_name = 'conversation'
    
    def dispatch(self, request, *args, **kwargs):
        conversation = self.get_object()
        if request.user.company not in conversation.participants.all():
            messages.error(request, 'You do not have access to this conversation.')
            return redirect('messaging:messages')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        conversation = self.get_object()
        
        # Mark messages as read
        Message.objects.filter(
            conversation=conversation
        ).exclude(sender=self.request.user.company).update(is_read=True)
        
        context['messages'] = conversation.messages.all().select_related('sender')
        context['message_form'] = MessageForm()
        context['quote_response_form'] = QuoteResponseForm(instance=conversation.quote_request)
        context['other_participant'] = conversation.get_other_participant(self.request.user.company)
        
        return context
    
    def post(self, request, *args, **kwargs):
        conversation = self.get_object()
        
        if 'send_message' in request.POST:
            form = MessageForm(request.POST)
            if form.is_valid():
                message = form.save(commit=False)
                message.conversation = conversation
                message.sender = request.user.company
                message.save()
                
                # Update conversation timestamp
                conversation.save()  # This updates updated_at
                
                # Create notification for other participant
                other_participant = conversation.get_other_participant(request.user.company)
                if other_participant:
                    Notification.objects.create(
                        recipient=other_participant,
                        notification_type='new_message',
                        title=f'New message from {request.user.company.company_name}',
                        message=message.content[:100] + '...' if len(message.content) > 100 else message.content,
                        conversation=conversation
                    )
                
                messages.success(request, 'Message sent successfully.')
                return redirect('messaging:conversation', pk=conversation.pk)
        
        elif 'respond_quote' in request.POST:
            form = QuoteResponseForm(request.POST, instance=conversation.quote_request)
            if form.is_valid():
                quote_request = form.save()
                
                # Send response message
                response_message = request.POST.get('response_message', '')
                if response_message:
                    Message.objects.create(
                        conversation=conversation,
                        sender=request.user.company,
                        content=response_message
                    )
                
                # Update conversation timestamp
                conversation.save()
                
                messages.success(request, 'Quote response sent successfully.')
                return redirect('messaging:conversation', pk=conversation.pk)
        
        return self.get(request, *args, **kwargs)

class QuotesReceivedView(LoginRequiredMixin, ListView):
    """List quotes received by vendors"""
    model = QuoteRequest
    template_name = 'messaging/quotes_received.html'
    context_object_name = 'quotes'
    paginate_by = 20
    
    def get_queryset(self):
        return QuoteRequest.objects.filter(
            supplier=self.request.user.company
        ).select_related('product', 'requester').order_by('-created_at')

class QuotesSentView(LoginRequiredMixin, ListView):
    """List quotes sent by buyers"""
    model = QuoteRequest
    template_name = 'messaging/quotes_sent.html'
    context_object_name = 'quotes'
    paginate_by = 20
    
    def get_queryset(self):
        return QuoteRequest.objects.filter(
            requester=self.request.user.company
        ).select_related('product', 'supplier').order_by('-created_at')

class NotificationsView(LoginRequiredMixin, ListView):
    """List notifications for user"""
    model = Notification
    template_name = 'messaging/notifications.html'
    context_object_name = 'notifications'
    paginate_by = 20
    
    def get_queryset(self):
        return Notification.objects.filter(
            recipient=self.request.user.company
        ).order_by('-created_at')
    
    def get(self, request, *args, **kwargs):
        # Mark all notifications as read when viewed
        Notification.objects.filter(
            recipient=request.user.company,
            is_read=False
        ).update(is_read=True)
        
        return super().get(request, *args, **kwargs)

def get_unread_count(request):
    """AJAX endpoint to get unread message count"""
    if not request.user.is_authenticated:
        return JsonResponse({'count': 0})
    
    # Count unread messages
    unread_messages = Message.objects.filter(
        conversation__participants=request.user.company
    ).exclude(sender=request.user.company).filter(is_read=False).count()
    
    # Count unread notifications
    unread_notifications = Notification.objects.filter(
        recipient=request.user.company,
        is_read=False
    ).count()
    
    return JsonResponse({
        'messages': unread_messages,
        'notifications': unread_notifications,
        'total': unread_messages + unread_notifications
    })
