"""Stripe test-mode Checkout boundary for the isolated customer web service."""

from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
import hmac
import json
import os
import time
from urllib.parse import quote
from uuid import uuid4

import httpx


PRODUCT_CODE = "yakumo-career-reading"
EXPECTED_AMOUNT_JPY = 1980
ENTITLEMENT_COOKIE = "yakumo_reading_entitlement"


class StripeCheckoutError(RuntimeError):
    """A safe, classified failure at the Stripe connection boundary."""


@dataclass(frozen=True)
class StripeTestConfig:
    secret_key: str
    price_id: str
    webhook_secret: str
    entitlement_secret: str
    public_base_url: str


def test_checkout_enabled() -> bool:
    return os.getenv("STRIPE_TEST_CHECKOUT_ENABLED", "").strip().lower() in {
        "1", "true", "yes", "on",
    }


def _config() -> StripeTestConfig:
    values = {
        "secret_key": os.getenv("STRIPE_TEST_SECRET_KEY", ""),
        "price_id": os.getenv("STRIPE_TEST_PRICE_ID", ""),
        "webhook_secret": os.getenv("STRIPE_TEST_WEBHOOK_SECRET", "").strip(),
        "entitlement_secret": os.getenv("CUSTOMER_ENTITLEMENT_SECRET", ""),
        "public_base_url": os.getenv("CUSTOMER_PUBLIC_BASE_URL", "").rstrip("/"),
    }
    if not values["secret_key"].startswith("sk_test_"):
        raise StripeCheckoutError("stripe_test_key_missing")
    if not values["price_id"].startswith("price_"):
        raise StripeCheckoutError("stripe_test_price_missing")
    if not values["webhook_secret"].startswith("whsec_"):
        raise StripeCheckoutError("stripe_test_webhook_missing")
    if len(values["entitlement_secret"]) < 32:
        raise StripeCheckoutError("entitlement_secret_missing")
    if not values["public_base_url"].startswith("https://"):
        raise StripeCheckoutError("public_base_url_invalid")
    return StripeTestConfig(**values)


def create_checkout_session() -> str:
    config = _config()
    data = {
        "mode": "payment",
        "line_items[0][price]": config.price_id,
        "line_items[0][quantity]": "1",
        "success_url": f"{config.public_base_url}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}",
        "cancel_url": f"{config.public_base_url}/checkout/cancel",
        "metadata[product_code]": PRODUCT_CODE,
    }
    try:
        response = httpx.post(
            "https://api.stripe.com/v1/checkout/sessions",
            data=data,
            headers={
                "Authorization": f"Bearer {config.secret_key}",
                "Idempotency-Key": uuid4().hex,
            },
            timeout=10.0,
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise StripeCheckoutError("checkout_session_create_failed") from exc
    url = payload.get("url") if isinstance(payload, dict) else None
    if not isinstance(url, str) or not url.startswith("https://checkout.stripe.com/"):
        raise StripeCheckoutError("checkout_session_url_invalid")
    return url


def verify_paid_session(session_id: str) -> dict[str, object]:
    config = _config()
    if not session_id.startswith("cs_test_") or len(session_id) > 200:
        raise StripeCheckoutError("checkout_session_id_invalid")
    try:
        response = httpx.get(
            f"https://api.stripe.com/v1/checkout/sessions/{quote(session_id, safe='')}",
            headers={"Authorization": f"Bearer {config.secret_key}"},
            timeout=10.0,
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise StripeCheckoutError("checkout_session_verify_failed") from exc
    metadata = payload.get("metadata") if isinstance(payload, dict) else None
    valid = (
        isinstance(payload, dict)
        and payload.get("id") == session_id
        and payload.get("mode") == "payment"
        and payload.get("payment_status") == "paid"
        and payload.get("currency") == "jpy"
        and payload.get("amount_total") == EXPECTED_AMOUNT_JPY
        and isinstance(metadata, dict)
        and metadata.get("product_code") == PRODUCT_CODE
    )
    if not valid:
        raise StripeCheckoutError("checkout_session_not_paid")
    return payload


def verify_webhook(payload: bytes, signature_header: str, *, now: int | None = None) -> dict[str, object]:
    config = _config()
    parts: dict[str, list[str]] = {}
    for item in signature_header.split(","):
        key, separator, value = item.partition("=")
        if separator:
            parts.setdefault(key, []).append(value)
    timestamp_text = (parts.get("t") or [""])[0]
    try:
        timestamp = int(timestamp_text)
    except ValueError as exc:
        raise StripeCheckoutError("webhook_signature_invalid") from exc
    current = int(time.time()) if now is None else now
    if abs(current - timestamp) > 300:
        raise StripeCheckoutError("webhook_signature_expired")
    signed = timestamp_text.encode("ascii") + b"." + payload
    expected = hmac.new(config.webhook_secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
    if not any(hmac.compare_digest(expected, candidate) for candidate in parts.get("v1", [])):
        raise StripeCheckoutError("webhook_signature_invalid")
    try:
        event = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StripeCheckoutError("webhook_payload_invalid") from exc
    if not isinstance(event, dict):
        raise StripeCheckoutError("webhook_payload_invalid")
    return event


def issue_entitlement(session_id: str, *, now: int | None = None, lifetime_seconds: int = 1800) -> str:
    config = _config()
    current = int(time.time()) if now is None else now
    payload = {"sid": session_id, "exp": current + lifetime_seconds, "nonce": uuid4().hex}
    encoded = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).decode("ascii").rstrip("=")
    signature = hmac.new(config.entitlement_secret.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{encoded}.{signature}"


def read_entitlement(token: str, *, now: int | None = None) -> str | None:
    try:
        config = _config()
        encoded, signature = token.split(".", 1)
        expected = hmac.new(config.entitlement_secret.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            return None
        padded = encoded + "=" * (-len(encoded) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
        current = int(time.time()) if now is None else now
        session_id = payload.get("sid") if isinstance(payload, dict) else None
        expires = payload.get("exp") if isinstance(payload, dict) else None
        if not isinstance(session_id, str) or not session_id.startswith("cs_test_"):
            return None
        if not isinstance(expires, int) or expires < current:
            return None
        return session_id
    except (StripeCheckoutError, ValueError, TypeError, json.JSONDecodeError, UnicodeDecodeError):
        return None
