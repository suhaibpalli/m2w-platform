import requests
import json
import uuid
import logging
from decimal import Decimal
from datetime import timedelta

from django.shortcuts import render, redirect
from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.conf import settings
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.urls import reverse_lazy

from accounts.models import Company
from core.models import SiteSettings
from .models import Payment

logger = logging.getLogger('payments')

# ==============================================================================
# UTILITY FUNCTIONS
# ==============================================================================

def get_access_token():
    """Step 1: Authenticate and retrieve the Access Token."""
    token_url = f"{settings.NGENIUS_BASE_URL}/identity/auth/access-token"

    token_headers = {
        'Authorization': f"Basic {settings.NGENIUS_SERVICE_ACCOUNT_API_KEY}",
        'Content-Type': 'application/vnd.ni-identity.v1+json',
        'Accept': 'application/vnd.ni-identity.v1+json'
    }

    # ✅ FIX: Use correct realm name based on environment
    # Sandbox uses "ni", Production uses "NetworkInternational"
    is_sandbox = 'sandbox' in settings.NGENIUS_BASE_URL.lower()
    realm_name = "ni" if is_sandbox else "NetworkInternational"

    try:
        logger.info(f"[TOKEN] Requesting from: {token_url}")
        logger.info(f"[TOKEN] Using realm: {realm_name}")
        token_response = requests.post(
            token_url,
            headers=token_headers,
            data=json.dumps({"realmName": realm_name}),
            timeout=30
        )
        logger.info(f"[TOKEN] Response status: {token_response.status_code}")
        if token_response.status_code != 200:
            logger.error(f"[TOKEN] Failed. Status: {token_response.status_code}")
            logger.error(f"[TOKEN] Response: {token_response.text}")
            return None
        access_token = token_response.json().get('access_token')
        if access_token:
            logger.info("[TOKEN] Access token obtained successfully")
            return access_token
        else:
            logger.error("[TOKEN] No access_token in response")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"[TOKEN] API Error: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"[TOKEN] Response body: {e.response.text}")
        return None

def create_ngenius_order(request, payment):
    """
    Create N-Genius order with complete billing address for 3DS2 validation.
    """
    access_token = get_access_token()
    if not access_token:
        logger.error("ORDER: Failed to get access token")
        return None

    transactions_url = f"{settings.NGENIUS_BASE_URL}/transactions/outlets/{settings.NGENIUS_OUTLET_REF}/orders"
    
    return_url = request.build_absolute_uri(reverse_lazy('payments:callback'))
    notify_url = request.build_absolute_uri(reverse_lazy('payments:webhook'))
    
    order_headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/vnd.ni-payment.v2+json",
        "Accept": "application/vnd.ni-payment.v2+json"
    }
    
    # Get company data
    company = payment.company
    email = company.contact_email or getattr(getattr(company, "user", None), "email", None) or "noemail@example.com"
    
    # Parse first/last name from contact_person_name
    contact_name = company.contact_person_name or "Customer User"
    name_parts = contact_name.strip().split()
    first_name = name_parts[0] if name_parts else "Customer"
    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else "User"
    
    # Build order payload
    order_payload = {
        "action": "PURCHASE",
        "amount": {
            "currencyCode": payment.currency,
            "value": payment.amount_in_cents
        },
        "merchantOrderReference": payment.order_id,
        "emailAddress": email,
        
        # Complete billing address for 3DS2
        "billingAddress": {
            "firstName": first_name,
            "lastName": last_name,
            "address1": (company.company_address or "Address Line 1")[:100],
            "city": company.billing_city or "Dubai",
            "state": company.billing_state or "Dubai",
            "country": company.billing_country or "United Arab Emirates",
            "countryCode": (company.billing_country_code or "AE").upper(),
            "postalCode": company.billing_postal_code or "00000",
            "phone": company.contact_phone or ""
        },
        
        "merchantAttributes": {
            "redirectUrl": return_url,
            "notificationUrl": notify_url,
            "skipConfirmationPage": True,
            "maskPaymentInfo": True,
            "showPayerName": True,
            "slim": "true"
        }
    }

    try:
        logger.info(f"ORDER: Creating for {company.company_name}")
        logger.info(f"ORDER: billingAddress = {order_payload['billingAddress']}")
        
        order_response = requests.post(
            transactions_url,
            json=order_payload,
            headers=order_headers,
            timeout=30
        )
        
        logger.info(f"ORDER: Response status = {order_response.status_code}")
        
        if order_response.status_code not in [200, 201]:
            logger.error(f"ORDER: Failed - {order_response.text}")
            return None
        
        order_data = order_response.json()
        payment_link = order_data.get("_links", {}).get("payment", {}).get("href")
        order_reference = order_data.get("reference")
        
        if payment_link and order_reference:
            payment.transaction_reference = order_reference
            payment.save()
            logger.info(f"ORDER: Created {order_reference}")
            return payment_link
        
        logger.error(f"ORDER: No payment link in response")
        return None
        
    except requests.exceptions.RequestException as e:
        logger.error(f"ERROR: Order API failed - {str(e)}", exc_info=True)
        return None

# ==============================================================================
# VIEWS
# ==============================================================================

class PaymentCheckoutView(LoginRequiredMixin, View):
    """Initializes payment and redirects user to N-Genius HPP."""

    def get(self, request, *args, **kwargs):
        # Prerequisite checks
        site_settings = SiteSettings.objects.first()
        if not site_settings:
            messages.error(request, 'Payment configuration not found. Please contact support.')
            return redirect('core:home')

        if not hasattr(request.user, 'company'):
            messages.error(request, 'Company profile not found. Please complete registration.')
            return redirect('accounts:register')

        company = request.user.company
        if company.subscription_status == 'active':
            messages.info(request, 'Your subscription is already active.')
            return redirect('dashboard:home')

        # Create local Payment record
        order_id = f"ORD-{uuid.uuid4().hex[:12].upper()}"
        try:
            payment = Payment.objects.create(
                company=company,
                amount=site_settings.annual_fee,
                currency=site_settings.currency,
                order_id=order_id,
                payment_type='registration'
            )
            logger.info(f"[CHECKOUT] Payment record created: {order_id}")
        except Exception as e:
            logger.error(f"[CHECKOUT] Error creating payment record: {str(e)}", exc_info=True)
            messages.error(request, 'An error occurred. Please try again.')
            return redirect('core:pricing')

        # Create N-Genius order and get payment URL
        payment_url = create_ngenius_order(request, payment)
        if payment_url:
            logger.info(f"[CHECKOUT] Redirecting to N-Genius HPP")
            return redirect(payment_url)
        else:
            payment.status = 'failed'
            payment.error_message = 'Failed to create N-Genius order.'
            payment.save()
            messages.error(request, 'Payment initialization failed. Please try again.')
            return redirect('core:pricing')


from django.urls import reverse_lazy

class PaymentCallbackView(TemplateView):
    """Handle N-Genius payment callback - Browser redirect after payment"""
    template_name = 'payments/callback.html'

    def get(self, request, *args, **kwargs):
        """Process callback from N-Genius"""

        transaction_ref = request.GET.get('ref') or request.GET.get('reference')
        merchant_order_ref = request.GET.get('orderReference') or request.GET.get('order_id')

        logger.info(f"[CALLBACK] Received callback")
        logger.info(f"[CALLBACK] Transaction ref: {transaction_ref}")
        logger.info(f"[CALLBACK] Merchant order ref: {merchant_order_ref}")

        try:
            payment = None

            if transaction_ref:
                try:
                    payment = Payment.objects.get(transaction_reference=transaction_ref)
                    logger.info(f"[CALLBACK] Found by transaction_ref: {payment.order_id}")
                except Payment.DoesNotExist:
                    logger.warning(f"[CALLBACK] Not found by transaction_ref: {transaction_ref}")

            if not payment and merchant_order_ref:
                try:
                    payment = Payment.objects.get(order_id=merchant_order_ref)
                    logger.info(f"[CALLBACK] Found by order_id: {payment.order_id}")
                except Payment.DoesNotExist:
                    logger.warning(f"[CALLBACK] Not found by order_id: {merchant_order_ref}")

            if not payment:
                logger.error(f"[CALLBACK] Payment not found. Params: {dict(request.GET)}")
                messages.error(request, 'Payment record not found.')
                return redirect('core:home')

            # If already successful
            if payment.is_successful:
                logger.info(f"[CALLBACK] Payment already successful")
                messages.success(request, 'Payment successful! Your account is now active.')
                return redirect('payments:success', order_reference=payment.order_id)

            # If still pending - query API once
            if payment.status == 'pending':
                logger.info(f"[CALLBACK] Status pending, querying API...")
                if self.verify_payment_with_api(payment):
                    # API confirmed it's captured
                    logger.info(f"[CALLBACK] API confirmed payment captured")
                    messages.success(request, 'Payment successful! Your account is now active.')
                    return redirect('payments:success', order_reference=payment.order_id)
                else:
                    # API didn't confirm yet (webhook will arrive soon)
                    # ✅ FIX: Don't redirect - render a waiting page
                    logger.info(f"[CALLBACK] Payment pending - rendering waiting page")
                    messages.info(request, 'Your payment is being processed. Please wait...')
                    return render(request, 'payments/callback_waiting.html', {
                        'order_id': payment.order_id,
                        'transaction_ref': payment.transaction_reference,
                        'amount': payment.amount,
                        'currency': payment.currency,
                    })

            # If failed
            if payment.status == 'failed':
                logger.warning(f"[CALLBACK] Payment failed")
                messages.error(request, f'Payment failed: {payment.error_message}')
                return redirect('payments:failure')

        except Exception as e:
            logger.error(f"[CALLBACK] Unexpected error: {str(e)}", exc_info=True)
            messages.error(request, 'An unexpected error occurred.')
            return redirect('core:home')

    def verify_payment_with_api(self, payment):
        """Query N-Genius API to verify payment status"""
        try:
            token_url = f"{settings.NGENIUS_BASE_URL}/identity/auth/access-token"
            token_headers = {
                'Authorization': f"Basic {settings.NGENIUS_SERVICE_ACCOUNT_API_KEY}",
                'Content-Type': 'application/vnd.ni-identity.v1+json',
                'Accept': 'application/vnd.ni-identity.v1+json'
            }

            # ✅ FIX: Use correct realm name
            is_sandbox = 'sandbox' in settings.NGENIUS_BASE_URL.lower()
            realm_name = "ni" if is_sandbox else "NetworkInternational"

            token_response = requests.post(
                token_url,
                headers=token_headers,
                data=json.dumps({"realmName": realm_name}),
                timeout=30
            )

            if token_response.status_code != 200:
                logger.error(f"[CALLBACK-API] Token failed: {token_response.status_code}")
                return False

            access_token = token_response.json().get('access_token')
            if not access_token:
                logger.error("[CALLBACK-API] No access_token in response")
                return False

            order_url = f"{settings.NGENIUS_BASE_URL}/transactions/outlets/{settings.NGENIUS_OUTLET_REF}/orders/{payment.transaction_reference}"
            order_headers = {
                'Authorization': f"Bearer {access_token}",
                'Accept': 'application/vnd.ni-payment.v2+json'
            }

            order_response = requests.get(order_url, headers=order_headers, timeout=30)
            if order_response.status_code != 200:
                logger.error(f"[CALLBACK-API] Query failed: {order_response.status_code}")
                return False

            order_data = order_response.json()
            payments = order_data.get('_embedded', {}).get('payment', [])

            if not payments:
                logger.warning("[CALLBACK-API] No payment data in response")
                return False

            state = payments[0].get('state', '')
            logger.info(f"[CALLBACK-API] Payment state: {state}")

            # ✅ FIX: Include PURCHASED state
            if state in ['PURCHASED', 'CAPTURED', 'AUTHORISED']:
                logger.info(f"[CALLBACK-API] Payment successful (state: {state})")
                payment.status = 'captured'
                payment.completed_at = timezone.now()
                payment.webhook_data = order_data
                payment.authorization_code = payments[0].get('authResponse', {}).get('authorizationCode', '')
                payment.save()

                company = payment.company
                if company.subscription_status != 'active':
                    logger.info(f"[CALLBACK-API] Activating subscription for {company.company_name}")
                    company.subscription_status = 'active'
                    company.subscription_start_date = timezone.now()
                    company.subscription_end_date = timezone.now() + timedelta(days=365)
                    company.is_verified = True
                    company.save()
                    logger.info(f"[CALLBACK-API] Subscription activated")

                return True

            elif state in ['FAILED', 'DECLINED']:
                logger.warning(f"[CALLBACK-API] Payment failed: {state}")
                payment.status = 'failed'
                payment.error_message = payments[0].get('failureReason', 'Payment declined')
                payment.save()
                return False

            logger.warning(f"[CALLBACK-API] Unknown state: {state}")
            return False

        except Exception as e:
            logger.error(f"[CALLBACK-API] Error: {str(e)}", exc_info=True)
            return False


@csrf_exempt
@require_POST
def payment_webhook(request):
    """Handle N-Genius webhook callback"""

    # 🛑 CRITICAL SECURITY WARNING 🛑
    # You MUST implement HMAC/Signature verification here before processing the payment.
    # Without signature verification, an attacker could send a fake 'CAPTURED' payload.
    # Refer to N-Genius documentation on Consuming web-hooks for HMAC verification details.

    try:
        payload = json.loads(request.body)
        logger.info(f"[WEBHOOK] Received webhook")

        # Ensure order_reference is extracted correctly (N-Genius uses 'reference' in webhook)
        order_reference = payload.get('reference')

        if not order_reference:
            logger.warning("[WEBHOOK] No order reference in payload")
            return JsonResponse({'error': 'No order reference'}, status=400)

        try:
            payment = Payment.objects.get(transaction_reference=order_reference)
        except Payment.DoesNotExist:
            logger.error(f"[WEBHOOK] Payment not found: {order_reference}")
            return JsonResponse({'error': 'Payment not found'}, status=404)

        # Extract payment state
        embedded = payload.get('_embedded', {})
        payment_data = embedded.get('payment', [{}])[0]
        state = payment_data.get('state', '')

        logger.info(f"[WEBHOOK] Payment state: {state}")

        # ✅ FIX: Include PURCHASED state
        if state in ['PURCHASED', 'CAPTURED', 'AUTHORISED']:
            logger.info(f"[WEBHOOK] Payment successful (state: {state})")
            payment.status = 'captured'
            payment.completed_at = timezone.now()
            payment.webhook_data = payload
            payment.authorization_code = payment_data.get('authResponse', {}).get('authorizationCode', '')
            payment.save()

            company = payment.company
            if company.subscription_status != 'active':
                logger.info(f"[WEBHOOK] Activating subscription for {company.company_name}")
                company.subscription_status = 'active'
                company.subscription_start_date = timezone.now()
                company.subscription_end_date = timezone.now() + timedelta(days=365)
                company.is_verified = True
                company.save()
                logger.info(f"[WEBHOOK] Subscription activated")

        elif state in ['FAILED', 'DECLINED']:
            logger.info(f"[WEBHOOK] Payment failed: {state}")
            payment.status = 'failed'
            payment.error_message = payment_data.get('failureReason', 'Payment declined')
            payment.webhook_data = payload
            payment.save()
            logger.warning(f"[WEBHOOK] Payment declined: {order_reference}")

        return JsonResponse({'status': 'received'}, status=200)

    except json.JSONDecodeError:
        logger.error("[WEBHOOK] Invalid JSON in webhook")
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"[WEBHOOK] Processing error: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


class PaymentSuccessView(LoginRequiredMixin, TemplateView):
    """Payment success page"""
    template_name = 'payments/success.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order_reference = self.kwargs.get('order_reference')

        try:
            payment = Payment.objects.get(order_id=order_reference)
            context['payment'] = payment
            context['company'] = payment.company
            context['is_active'] = payment.is_successful
            logger.info(f"[SUCCESS] Success page: {order_reference}")
        except Payment.DoesNotExist:
            context['is_active'] = False
            logger.error(f"[ERROR] Success page: Payment not found {order_reference}")

        return context

class PaymentFailureView(TemplateView):
    """Payment failure page"""
    template_name = 'payments/failure.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        logger.info("[FAILURE] Failure page accessed")
        return context
