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
    logger.info(f"Checkout page accessed by user: {request.user.email}")
    
    company = request.user.company
    if company.subscription_status == 'active':
        logger.info(f"User {request.user.email} already has active subscription, redirecting to dashboard")
        return redirect('dashboard:home')
    
    site_settings = SiteSettings.objects.first()

    # MCP Configuration
    is_mcp_enabled = getattr(settings, 'NGENIUS_MCP_ENABLED', False)  # Add this to your settings

    context = {
        'company': company,
        'site_settings': site_settings,
        'ngenius_hosted_session_key': settings.NGENIUS_HOSTED_SESSION_API_KEY,
        'ngenius_outlet_ref': settings.NGENIUS_OUTLET_REF,
        'is_mcp_enabled': is_mcp_enabled,
        'merchant_currency': site_settings.currency,
        'order_amount': float(site_settings.annual_fee),
    }

    logger.info(
        f"Checkout context prepared - Amount: {site_settings.annual_fee} {site_settings.currency}, MCP: {is_mcp_enabled}"
    )
    return render(request, 'payments/checkout.html', context)


@login_required
def process_payment(request):
    """Process payment with N-Genius backend API"""
    if request.method != 'POST':
        logger.warning(f"Invalid method attempt: {request.method}")
        return JsonResponse({'error': 'Invalid method'}, status=405)
    
    try:
        # Parse request data
        data = json.loads(request.body)
        session_id = data.get('session_id')
        amount = data.get('amount')
        target_currency = data.get('target_currency')  # MCP support
        
        if not session_id:
            logger.error("Missing session_id in request")
            return JsonResponse({'error': 'Missing session ID'}, status=400)
        
        logger.info(f"=== PAYMENT PROCESS STARTED ===")
        logger.info(f"User: {request.user.email}")
        logger.info(f"Company: {request.user.company.company_name}")
        logger.info(f"Session ID: {session_id}")
        logger.info(f"Amount: {amount}")
        logger.info(f"Target Currency: {target_currency or 'None (merchant currency)'}")
        
        # Get site settings
        site_settings = SiteSettings.objects.first()
        company = request.user.company

        logger.info(f"Site Settings - Currency: {site_settings.currency}, Fee: {site_settings.annual_fee}")
        
        # Step 1: Get N-Genius access token
        logger.info("Step 1/4: Requesting N-Genius access token...")
        access_token = get_ngenius_access_token()
        logger.info(f"Step 1/4: Access token obtained (length: {len(access_token)} chars)")

        # Step 2: Create payment record
        logger.info("Step 2/4: Creating payment record in database...")
        payment = Payment.objects.create(
            company=company,
            payment_type='subscription',
            amount=site_settings.annual_fee,
            currency=target_currency or site_settings.currency,  # Use target currency if provided
            ngenius_session_id=session_id,
            status='pending'
        )
        logger.info(f"Step 2/4: Payment record created - ID: {payment.id}, Status: {payment.status}")

        # Step 3: Call N-Genius payment API
        merchant_ref = f"SUB-{company.id}-{payment.id}"
        logger.info(f"Step 3/4: Calling N-Genius payment API...")
        logger.info(f"Merchant Reference: {merchant_ref}")
        logger.info(f"Outlet Reference: {settings.NGENIUS_OUTLET_REF}")

        payment_response = complete_ngenius_payment(
            access_token=access_token,
            session_id=session_id,
            amount=float(site_settings.annual_fee),
            currency=site_settings.currency,
            outlet_ref=settings.NGENIUS_OUTLET_REF,
            merchant_ref=merchant_ref,
            target_currency=target_currency  # MCP parameter
        )

        # Step 4: Store N-Genius response
        logger.info("Step 4/4: Storing payment response...")
        payment.ngenius_order_ref = payment_response.get('reference', '')
        payment.transaction_details = payment_response
        payment.save()

        response_state = payment_response.get('state', 'UNKNOWN')
        logger.info(f"Step 4/4: Payment response stored")
        logger.info(f"Payment State: {response_state}")
        logger.info(f"Order Reference: {payment.ngenius_order_ref}")
        logger.info(f"=== PAYMENT PROCESS COMPLETED ===")
        
        # Return full response to frontend for 3DS handling
        return JsonResponse(payment_response)
        
    except requests.exceptions.HTTPError as http_err:
        # Extract error details from N-Genius response
        try:
            error_detail = http_err.response.json()
            error_message = error_detail.get('message', 'Unknown error')
            error_code = error_detail.get('code', http_err.response.status_code)
            errors_list = error_detail.get('errors', [])
        except:
            error_detail = http_err.response.text
            error_message = error_detail
            error_code = http_err.response.status_code
            errors_list = []
        
        logger.error(f"========================")
        logger.error(f"N-GENIUS HTTP ERROR")
        logger.error(f"Status Code: {http_err.response.status_code}")
        logger.error(f"Error Message: {error_message}")
        logger.error(f"Error Code: {error_code}")
        if errors_list:
            logger.error(f"Detailed Errors:")
            for err in errors_list:
                logger.error(f"   - {err.get('errorCode', 'N/A')}: {err.get('message', 'N/A')}")
        logger.error(f"Request URL: {http_err.request.url}")
        logger.error(f"Full Response: {error_detail}")
        logger.error(f"========================")
        
        return JsonResponse({
            'error': 'Payment gateway error',
            'message': error_message,
            'details': error_detail,
            'status_code': http_err.response.status_code
        }, status=http_err.response.status_code)
        
    except Exception as e:
        logger.error(f"========================")
        logger.error(f"PAYMENT PROCESSING ERROR")
        logger.error(f"Error Type: {type(e).__name__}")
        logger.error(f"Error Message: {str(e)}")
        logger.error(f"========================", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)

def get_ngenius_access_token():
    """
    Get access token from N-Genius Identity API
    """
    url = f"{settings.NGENIUS_BASE_URL}/identity/auth/access-token"
    
    headers = {
        'Authorization': f'Basic {settings.NGENIUS_SERVICE_ACCOUNT_API_KEY}',
        'Accept': 'application/vnd.ni-identity.v1+json'
    }

    logger.info(f"Requesting access token from N-Genius Identity API")
    logger.info(f"URL: {url}")
    logger.debug(f"API Key (first 20 chars): {settings.NGENIUS_SERVICE_ACCOUNT_API_KEY[:20]}...")

    try:
        response = requests.post(url, headers=headers, timeout=10)
        
        logger.info(f"Identity API Response Status: {response.status_code}")
        
        response.raise_for_status()
        
        token_data = response.json()
        access_token = token_data.get('access_token')
        expires_in = token_data.get('expires_in', 'Unknown')

        if not access_token:
            logger.error(f"No access token in response: {token_data}")
            raise ValueError("No access token received from N-Genius")
        
        logger.info(f"Access token obtained successfully")
        logger.info(f"Token expires in: {expires_in} seconds")
        logger.debug(f"Token (first 30 chars): {access_token[:30]}...")

        return access_token

    except requests.exceptions.Timeout:
        logger.error("Request to N-Genius Identity API timed out after 10 seconds")
        raise
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error to N-Genius Identity API: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting access token: {str(e)}")
        raise

def complete_ngenius_payment(access_token, session_id, amount, currency, outlet_ref, merchant_ref, target_currency=None):
    """Complete payment using N-Genius Hosted Session API with MCP support"""
    url = f"{settings.NGENIUS_BASE_URL}/transactions/outlets/{outlet_ref}/payment/hosted-session/{session_id}"
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/vnd.ni-payment.v2+json',
        'Accept': 'application/vnd.ni-payment.v2+json'
    }
    
    # Convert amount to minor units (cents)
    amount_cents = int(amount * 100)
    
    # Base payload
    payload = {
        "action": "PURCHASE",
        "amount": {
            "currencyCode": currency,  # Original merchant currency
            "value": amount_cents
        },
        "merchantOrderReference": merchant_ref
    }
    
    # Add MCP payment block if target currency provided
    if target_currency and target_currency != currency:
        payload["payment"] = {
            "currency": target_currency
        }
        logger.info(f"MCP ENABLED - Original: {currency}, Target: {target_currency}")
    else:
        logger.info(f"Standard Payment - Currency: {currency}")
    
    logger.info(f"Sending payment request to N-Genius")
    logger.info(f"URL: {url}")
    logger.info(f"Merchant Order Reference: {merchant_ref}")
    logger.info(f"Amount: {amount_cents} minor units ({amount} {currency})")
    logger.info(f"Outlet: {outlet_ref}")
    logger.debug(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        
        logger.info(f"Payment API Response Status: {response.status_code}")
        
        # Log response regardless of status
        try:
            response_json = response.json()
            logger.info(f"Response State: {response_json.get('state', 'N/A')}")
            logger.info(f"Response Reference: {response_json.get('reference', 'N/A')}")
            logger.debug(f"Full Response: {json.dumps(response_json, indent=2)[:1000]}...")
        except:
            logger.warning(f"Response is not JSON: {response.text[:500]}")
        
        response.raise_for_status()
        
        logger.info(f"Payment request completed successfully")
        return response.json()
        
    except requests.exceptions.Timeout:
        logger.error("Payment request timed out after 15 seconds")
        raise
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP Error during payment: {e.response.status_code}")
        logger.error(f"Response: {e.response.text}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during payment: {str(e)}")
        raise

@login_required
def payment_success(request):
    """Payment success page - activate subscription"""
    logger.info(f"Payment success page accessed by user: {request.user.email}")
    
    company = request.user.company
    
    # Get the latest payment for this company
    latest_payment = Payment.objects.filter(
        company=company,
        payment_type='subscription'
    ).order_by('-created_at').first()
    
    if latest_payment and latest_payment.status == 'pending':
        logger.info(f"Activating subscription for company: {company.company_name}")
        logger.info(f"Payment ID: {latest_payment.id}")
        logger.info(f"Amount: {latest_payment.amount} {latest_payment.currency}")
        
        # Update payment status to completed
        latest_payment.status = 'completed'
        latest_payment.save()
        
        # Activate subscription
        subscription_start = timezone.now()
        subscription_end = subscription_start + timedelta(days=365)
        
        company.subscription_status = 'active'
        company.subscription_start_date = subscription_start
        company.subscription_end_date = subscription_end
        company.save()
        
        logger.info(f"Subscription activated successfully")
        logger.info(f"Start Date: {subscription_start}")
        logger.info(f"End Date: {subscription_end}")
    else:
        logger.warning(f"No pending payment found for company: {company.company_name}")
    
    context = {
        'company': company,
        'payment': latest_payment
    }
    return render(request, 'payments/success.html', context)

@login_required
def payment_failed(request):
    """Payment failed page"""
    logger.warning(f"Payment failed page accessed by user: {request.user.email}")
    return render(request, 'payments/failed.html')
