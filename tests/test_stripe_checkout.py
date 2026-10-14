"""Stripe test-mode boundary tests. No external request or real payment is made."""

import hashlib
import hmac
import json

import pytest

from api import stripe_checkout


def _config(monkeypatch):
    monkeypatch.setenv("STRIPE_TEST_SECRET_KEY", "sk_test_synthetic")
    monkeypatch.setenv("STRIPE_TEST_PRICE_ID", "price_synthetic")
    monkeypatch.setenv("STRIPE_TEST_WEBHOOK_SECRET", "whsec_synthetic")
    monkeypatch.setenv("CUSTOMER_ENTITLEMENT_SECRET", "synthetic-entitlement-secret-at-least-32-bytes")
    monkeypatch.setenv("CUSTOMER_PUBLIC_BASE_URL", "https://example.test")


def test_live_secret_key_is_rejected(monkeypatch):
    _config(monkeypatch)
    monkeypatch.setenv("STRIPE_TEST_SECRET_KEY", "sk_live_must_not_be_used")
    with pytest.raises(stripe_checkout.StripeCheckoutError, match="stripe_test_key_missing"):
        stripe_checkout.issue_entitlement("cs_test_123")


def test_entitlement_is_signed_tamper_evident_and_expires(monkeypatch):
    _config(monkeypatch)
    token = stripe_checkout.issue_entitlement("cs_test_123", now=1000, lifetime_seconds=60)
    assert stripe_checkout.read_entitlement(token, now=1059) == "cs_test_123"
    assert stripe_checkout.read_entitlement(token + "x", now=1059) is None
    assert stripe_checkout.read_entitlement(token, now=1061) is None


def test_webhook_signature_and_timestamp_are_verified(monkeypatch):
    _config(monkeypatch)
    payload = json.dumps({"id": "evt_test_1", "type": "checkout.session.completed"}).encode()
    signature = hmac.new(b"whsec_synthetic", b"1000." + payload, hashlib.sha256).hexdigest()
    event = stripe_checkout.verify_webhook(payload, f"t=1000,v1={signature}", now=1000)
    assert event["id"] == "evt_test_1"
    with pytest.raises(stripe_checkout.StripeCheckoutError, match="webhook_signature_expired"):
        stripe_checkout.verify_webhook(payload, f"t=1000,v1={signature}", now=1301)


def test_webhook_secret_ignores_surrounding_whitespace(monkeypatch):
    _config(monkeypatch)
    monkeypatch.setenv("STRIPE_TEST_WEBHOOK_SECRET", "  whsec_synthetic\r\n")
    payload = json.dumps({"id": "evt_test_whitespace", "type": "checkout.session.completed"}).encode()
    signature = hmac.new(b"whsec_synthetic", b"1000." + payload, hashlib.sha256).hexdigest()

    event = stripe_checkout.verify_webhook(payload, f"t=1000,v1={signature}", now=1000)

    assert event["id"] == "evt_test_whitespace"


def test_paid_session_requires_expected_amount_currency_and_product(monkeypatch):
    _config(monkeypatch)

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "id": "cs_test_paid",
                "mode": "payment",
                "payment_status": "paid",
                "currency": "jpy",
                "amount_total": 1980,
                "metadata": {"product_code": stripe_checkout.PRODUCT_CODE},
            }

    monkeypatch.setattr(stripe_checkout.httpx, "get", lambda *_args, **_kwargs: Response())
    assert stripe_checkout.verify_paid_session("cs_test_paid")["amount_total"] == 1980

    class WrongAmount(Response):
        def json(self):
            payload = super().json()
            payload["amount_total"] = 100
            return payload

    monkeypatch.setattr(stripe_checkout.httpx, "get", lambda *_args, **_kwargs: WrongAmount())
    with pytest.raises(stripe_checkout.StripeCheckoutError, match="checkout_session_not_paid"):
        stripe_checkout.verify_paid_session("cs_test_paid")
