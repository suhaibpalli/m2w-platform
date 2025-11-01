from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    # Payment checkout - Triggers the API call and redirect
    path('checkout/', views.PaymentCheckoutView.as_view(), name='checkout'),

    # Callbacks - Browser redirects here after payment completion
    path('callback/', views.PaymentCallbackView.as_view(), name='callback'),
    # Webhook - Secure, server-to-server confirmation
    path('webhook/', views.payment_webhook, name='webhook'), 

    # Results
    path('success/<str:order_reference>/', views.PaymentSuccessView.as_view(), name='success'),
    path('failure/', views.PaymentFailureView.as_view(), name='failure'),
]
