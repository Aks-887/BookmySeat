"""Small Razorpay adapter. All gateway trust decisions stay on the server."""

import base64
import hashlib
import hmac
import json
from decimal import Decimal, ROUND_HALF_UP
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings


class PaymentGatewayError(Exception):
    """A safe, user-facing gateway failure."""


def _credentials():
    key_id = getattr(settings, 'RAZORPAY_KEY_ID', '')
    key_secret = getattr(settings, 'RAZORPAY_KEY_SECRET', '')
    if not key_id or not key_secret:
        raise PaymentGatewayError('Online payments are not configured.')
    return key_id, key_secret


def _api_request(path, method='GET', payload=None):
    key_id, key_secret = _credentials()
    data = json.dumps(payload).encode('utf-8') if payload is not None else None
    auth = base64.b64encode(f'{key_id}:{key_secret}'.encode('utf-8')).decode('ascii')
    request = Request(
        f'https://api.razorpay.com/v1/{path.lstrip("/")}',
        data=data,
        method=method,
        headers={
            'Authorization': f'Basic {auth}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        },
    )
    try:
        with urlopen(request, timeout=getattr(settings, 'PAYMENT_GATEWAY_TIMEOUT', 10)) as response:
            return json.loads(response.read().decode('utf-8'))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        # Provider responses can include payment/customer data; never expose it.
        raise PaymentGatewayError('The payment provider is temporarily unavailable.') from exc


def amount_to_subunits(amount):
    return int((Decimal(amount) * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def create_order(booking_reference, amount, currency):
    amount_subunits = amount_to_subunits(amount)
    if amount_subunits <= 0:
        raise PaymentGatewayError('The booking total must be greater than zero.')
    return _api_request('orders', method='POST', payload={
        'amount': amount_subunits,
        'currency': currency,
        'receipt': f'bms_{booking_reference.replace("-", "")[:32]}',
        'notes': {'booking_reference': booking_reference},
    })


def get_payment(gateway_payment_id):
    return _api_request(f'payments/{gateway_payment_id}')


def verify_checkout_signature(order_id, payment_id, signature):
    """Verify the signature returned by Checkout before querying Razorpay."""
    _, key_secret = _credentials()
    expected = hmac.new(
        key_secret.encode('utf-8'),
        f'{order_id}|{payment_id}'.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()
    return bool(signature) and hmac.compare_digest(expected, signature)


def verify_webhook_signature(raw_body, signature):
    _, key_secret = _credentials()
    expected = hmac.new(key_secret.encode('utf-8'), raw_body, hashlib.sha256).hexdigest()
    return bool(signature) and hmac.compare_digest(expected, signature)
