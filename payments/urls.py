# payments/urls.py
from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('checkout/', views.checkout_view, name='checkout'),
    path('process/', views.process_payment, name='process_payment'),
    path('success/', views.payment_success, name='success'),
    path('failed/', views.payment_failed, name='failed'),
]
