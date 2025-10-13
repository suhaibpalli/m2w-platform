# payments/views.py
import json
import logging
from decimal import Decimal, ROUND_HALF_UP
from datetime import timedelta

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.conf import settings
from django.utils import timezone
from core.models import SiteSettings
from accounts.models import Company
from .models import Payment
import requests

logger = logging.getLogger(__name__)

@login_required
def checkout_view(request):
    """Display checkout page with N-Genius SDK"""
    company = request.user.company
    if company.subscription_status == 'active':
        return redirect('dashboard:home')
    
    site_settings = SiteSettings.objects.first()
    
    context = {
        'company': company,
        'site_settings': site_settings,
        'ngenius_hosted_session_key': settings.NGENIUS_HOSTED_SESSION_API_KEY,
        'ngenius_outlet_ref': settings.NGENIUS_OUTLET_REF,
    }
    return render(request, 'payments/checkout.html', context)

@login_required
def process_payment(request):
    """Process payment with N-Genius backend API"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    
    try:
        # Parse request data
        data = json.loads(request.body)
        session_id = data.get('session_id')
        amount = data.get('amount')
        
        if not session_id:
            return JsonResponse({'error': 'Missing session ID'}, status=400)
        
        logger.info(f"Processing payment for user: {request.user.email}, session: {session_id}, amount: {amount}")
        
        # Get site settings
        site_settings = SiteSettings.objects.first()
        company = request.user.company
        
        # Step 1: Get N-Genius access token
        access_token = get_ngenius_access_token()
        logger.info("✅ Got access token")
        
        # Step 2: Create payment record
        payment = Payment.objects.create(
            company=company,
            payment_type='subscription',
            amount=site_settings.annual_fee,
            currency=site_settings.currency,
            ngenius_session_id=session_id,
            status='pending'
        )
        logger.info(f"✅ Created payment record: {payment.id}")
        
        # Step 3: Call N-Genius payment API
        payment_response = complete_ngenius_payment(
            access_token=access_token,
            session_id=session_id,
            amount=float(site_settings.annual_fee),
            currency=site_settings.currency,
            outlet_ref=settings.NGENIUS_OUTLET_REF,
            merchant_ref=f"SUB-{company.id}-{payment.id}"
        )
        
        # Step 4: Store N-Genius response
        payment.ngenius_order_ref = payment_response.get('reference', '')
        payment.transaction_details = payment_response
        payment.save()
        
        logger.info(f"✅ Payment processed: {payment.ngenius_order_ref}")
        
        # Return full response to frontend for 3DS handling
        return JsonResponse(payment_response)
        
    except requests.exceptions.HTTPError as http_err:
        # Extract error details from N-Genius response
        try:
            error_detail = http_err.response.json()
        except:
            error_detail = http_err.response.text
        
        logger.error(f"❌ N-Genius HTTP Error {http_err.response.status_code}: {error_detail}")
        
        return JsonResponse({
            'error': 'Payment gateway error',
            'details': error_detail,
            'status_code': http_err.response.status_code
        }, status=http_err.response.status_code)
        
    except Exception as e:
        logger.error(f"❌ Payment processing error: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)

def get_ngenius_access_token():
    """
    Get access token from N-Genius Identity API
    According to N-Genius docs, this endpoint doesn't need form data
    """
    url = f"{settings.NGENIUS_BASE_URL}/identity/auth/access-token"
    
    # CORRECT headers - no Content-Type, just Authorization
    headers = {
        'Authorization': f'Basic {settings.NGENIUS_SERVICE_ACCOUNT_API_KEY}',
        'Accept': 'application/vnd.ni-identity.v1+json'
    }
    
    logger.info(f"🔄 Requesting access token from: {url}")
    
    # POST with NO data parameter - the API key in Authorization header is enough
    response = requests.post(url, headers=headers, timeout=10)
    
    # Log response for debugging
    logger.info(f"Identity API response status: {response.status_code}")
    
    response.raise_for_status()
    
    token_data = response.json()
    access_token = token_data.get('access_token')
    
    if not access_token:
        logger.error(f"No access token in response: {token_data}")
        raise ValueError("No access token received from N-Genius")
    
    logger.info("✅ Successfully obtained N-Genius access token")
    return access_token

def complete_ngenius_payment(access_token, session_id, amount, currency, outlet_ref, merchant_ref):
    """Complete payment using N-Genius Hosted Session API"""
    url = f"{settings.NGENIUS_BASE_URL}/transactions/outlets/{outlet_ref}/payment/hosted-session/{session_id}"
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/vnd.ni-payment.v2+json',
        'Accept': 'application/vnd.ni-payment.v2+json'
    }
    
    # Convert amount to minor units (cents)
    amount_cents = int(amount * 100)
    
    payload = {
        "action": "PURCHASE",  # Use PURCHASE for single-stage payment
        "amount": {
            "currencyCode": currency,
            "value": amount_cents
        },
        "merchantOrderReference": merchant_ref
    }
    
    logger.info(f"🔄 Sending payment request: {merchant_ref}, amount: {amount_cents} cents")
    logger.info(f"Payment URL: {url}")
    
    response = requests.post(url, headers=headers, json=payload, timeout=15)
    
    logger.info(f"Payment API response status: {response.status_code}")
    logger.info(f"Payment API response: {response.text[:500]}")  # Log first 500 chars
    
    response.raise_for_status()
    
    return response.json()

@login_required
def payment_success(request):
    """Payment success page - activate subscription"""
    company = request.user.company
    
    # Get the latest payment for this company
    latest_payment = Payment.objects.filter(
        company=company,
        payment_type='subscription'
    ).order_by('-created_at').first()
    
    if latest_payment and latest_payment.status == 'pending':
        # Update payment status to completed
        latest_payment.status = 'completed'
        latest_payment.save()
        
        # Activate subscription
        company.subscription_status = 'active'
        company.subscription_start_date = timezone.now()
        company.subscription_end_date = timezone.now() + timedelta(days=365)
        company.save()
        
        logger.info(f"✅ Activated subscription for company: {company.company_name}")
    
    context = {
        'company': company,
        'payment': latest_payment
    }
    return render(request, 'payments/success.html', context)

@login_required
def payment_failed(request):
    """Payment failed page"""
    return render(request, 'payments/failed.html')
