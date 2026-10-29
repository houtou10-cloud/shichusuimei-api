"""Academy login (Google) and monthly / yearly course subscriptions (Stripe).

No local database: the subscription record lives at Stripe (subscription
metadata), and the browser keeps only a signed cookie.  The gate is off
unless ACADEMY_LOGIN_REQUIRED is set, so existing deployments are unchanged.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
import hmac
import json
import os
import re
import time
from urllib.parse import quote, urlencode
from uuid import uuid4

import httpx

from api.stripe_checkout import checkout_mode


PRODUCT_CODE = "yakumo-academy"
LOGIN_SECONDS = 30 * 24 * 60 * 60
STATE_SECONDS = 10 * 60
FREE_CHAPTERS = frozenset({1})
ACCESS_COOKIE = "yakumo_academy_login"
STATE_COOKIE = "yakumo_academy_oauth"
_GOOGLE_AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN = "https://oauth2.googleapis.com/token"
_GOOGLE_ISSUERS = {"https://accounts.google.com", "accounts.google.com"}
_EMAIL = re.compile(r"^[^@\s'\"\\]+@[^@\s'\"\\]+$")


class AcademyAccessError(RuntimeError):
    """A safe, classified failure in login or purchase handling."""


@dataclass(frozen=True)
class Login:
    email: str
    access_until: int

    def active(self, now: int | None = None) -> bool:
        return self.access_until > (int(time.time()) if now is None else now)


def login_required() -> bool:
    return os.getenv("ACADEMY_LOGIN_REQUIRED", "").strip().lower() in {"1", "true", "yes", "on"}


def chapter_is_free(chapter: int) -> bool:
    return chapter in FREE_CHAPTERS


def _secret() -> bytes:
    secret = os.getenv("CUSTOMER_ENTITLEMENT_SECRET", "")
    if len(secret) < 32:
        raise AcademyAccessError("entitlement_secret_missing")
    return b"academy-v1:" + secret.encode("utf-8")


def _base_url() -> str:
    base = os.getenv("CUSTOMER_PUBLIC_BASE_URL", "").rstrip("/")
    if not base.startswith("https://"):
        raise AcademyAccessError("public_base_url_invalid")
    return base


def _sign(payload: dict[str, object]) -> str:
    encoded = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).decode("ascii").rstrip("=")
    signature = hmac.new(_secret(), encoded.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{encoded}.{signature}"


def _unsign(token: str, now: int | None = None) -> dict[str, object] | None:
    try:
        encoded, signature = token.split(".", 1)
        expected = hmac.new(_secret(), encoded.encode("ascii"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            return None
        payload = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)).decode("utf-8"))
    except (AcademyAccessError, ValueError, TypeError, UnicodeDecodeError):
        return None
    current = int(time.time()) if now is None else now
    if not isinstance(payload, dict) or not isinstance(payload.get("exp"), int) or payload["exp"] < current:
        return None
    return payload


def normalize_email(email: str) -> str:
    email = email.strip().lower()
    if not _EMAIL.fullmatch(email) or len(email) > 254:
        raise AcademyAccessError("email_invalid")
    return email


def issue_login(login: Login, *, now: int | None = None) -> str:
    current = int(time.time()) if now is None else now
    return _sign({"email": login.email, "until": login.access_until, "mode": checkout_mode(), "exp": current + LOGIN_SECONDS})


def read_login(token: str, *, now: int | None = None) -> Login | None:
    payload = _unsign(token, now)
    if payload is None or payload.get("mode") != checkout_mode():
        return None
    email, until = payload.get("email"), payload.get("until")
    if not isinstance(email, str) or not isinstance(until, int):
        return None
    return Login(email, until)


def issue_state(next_path: str, *, now: int | None = None) -> tuple[str, str]:
    state = uuid4().hex
    current = int(time.time()) if now is None else now
    return state, _sign({"state": state, "next": safe_next(next_path), "exp": current + STATE_SECONDS})


def read_state(token: str, state: str, *, now: int | None = None) -> str | None:
    payload = _unsign(token, now)
    if payload is None or not state or not hmac.compare_digest(str(payload.get("state", "")), state):
        return None
    return safe_next(str(payload.get("next", "")))


def safe_next(path: str) -> str:
    return path if re.fullmatch(r"/academy(?:/[A-Za-z0-9_/-]*)?", path or "") else "/academy/courses"


# --- Google -----------------------------------------------------------------

def _google_client() -> tuple[str, str]:
    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "").strip()
    client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "").strip()
    if not client_id.endswith(".apps.googleusercontent.com") or not client_secret:
        raise AcademyAccessError("google_oauth_missing")
    return client_id, client_secret


def _redirect_uri() -> str:
    return f"{_base_url()}/academy/auth/callback"


def google_auth_url(state: str) -> str:
    client_id, _ = _google_client()
    query = urlencode({
        "client_id": client_id,
        "redirect_uri": _redirect_uri(),
        "response_type": "code",
        "scope": "openid email",
        "state": state,
        "prompt": "select_account",
    })
    return f"{_GOOGLE_AUTH}?{query}"


def google_email(code: str, *, now: int | None = None) -> str:
    """Exchange the code directly with Google (TLS) and return the verified email."""
    client_id, client_secret = _google_client()
    try:
        response = httpx.post(
            _GOOGLE_TOKEN,
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": _redirect_uri(),
                "grant_type": "authorization_code",
            },
            timeout=10.0,
        )
        response.raise_for_status()
        id_token = response.json()["id_token"]
        body = id_token.split(".")[1]
        claims = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
    except (httpx.HTTPError, KeyError, IndexError, ValueError, TypeError) as exc:
        raise AcademyAccessError("google_token_failed") from exc
    current = int(time.time()) if now is None else now
    valid = (
        isinstance(claims, dict)
        and claims.get("aud") == client_id
        and claims.get("iss") in _GOOGLE_ISSUERS
        and isinstance(claims.get("exp"), int) and claims["exp"] >= current
        and claims.get("email_verified") is True
        and isinstance(claims.get("email"), str)
    )
    if not valid:
        raise AcademyAccessError("google_token_invalid")
    return normalize_email(claims["email"])


# --- Stripe -----------------------------------------------------------------

PLANS = {
    "monthly": {"label": "月額プラン", "price_text": "月額2,980円（税込）", "env": "ACADEMY_MONTHLY_PRICE_ID", "cycle": "1か月"},
    "yearly": {"label": "年額プラン", "price_text": "年額19,800円（税込）", "env": "ACADEMY_YEARLY_PRICE_ID", "cycle": "1年"},
}
# past_due は Stripe が再請求を続けている間の猶予として視聴を認める。
_ACTIVE_STATUSES = {"active", "trialing", "past_due"}


def _secret_key() -> str:
    mode = checkout_mode()
    if mode == "disabled":
        raise AcademyAccessError("stripe_checkout_disabled")
    prefix = "STRIPE_TEST" if mode == "test" else "STRIPE_LIVE"
    secret_key = os.getenv(f"{prefix}_SECRET_KEY", "").strip()
    if not secret_key.startswith("sk_test_" if mode == "test" else "sk_live_"):
        raise AcademyAccessError(f"stripe_{mode}_key_missing")
    return secret_key


def _price_id(plan: str) -> str:
    if plan not in PLANS:
        raise AcademyAccessError("plan_invalid")
    prefix = "STRIPE_TEST" if checkout_mode() == "test" else "STRIPE_LIVE"
    price_id = os.getenv(f"{prefix}_{PLANS[plan]['env']}", "").strip()
    if not price_id.startswith("price_"):
        raise AcademyAccessError(f"academy_{plan}_price_missing")
    return price_id


def purchase_ready() -> bool:
    try:
        _secret_key()
        for plan in PLANS:
            _price_id(plan)
        _google_client()
        _base_url()
        _secret()
    except AcademyAccessError:
        return False
    return True


def _period_end(subscription: dict[str, object]) -> int:
    """Paid-through time; newer API versions keep it on the subscription items."""
    ends = [subscription.get("current_period_end")]
    items = subscription.get("items")
    if isinstance(items, dict) and isinstance(items.get("data"), list):
        ends += [item.get("current_period_end") for item in items["data"] if isinstance(item, dict)]
    return max((end for end in ends if isinstance(end, int)), default=0)


def _until(subscription: dict[str, object]) -> int:
    if subscription.get("status") not in _ACTIVE_STATUSES:
        return 0
    return _period_end(subscription)


def _stripe_get(path: str, params: dict[str, str]) -> dict[str, object]:
    try:
        response = httpx.get(
            f"https://api.stripe.com/v1/{path}",
            params=params,
            headers={"Authorization": f"Bearer {_secret_key()}"},
            timeout=10.0,
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise AcademyAccessError("stripe_request_failed") from exc
    if not isinstance(payload, dict):
        raise AcademyAccessError("stripe_request_failed")
    return payload


def _subscriptions(email: str) -> list[dict[str, object]]:
    email = normalize_email(email)
    query = f"metadata['yakumo_product']:'{PRODUCT_CODE}' AND metadata['academy_email']:'{email}'"
    data = _stripe_get("subscriptions/search", {"query": query, "limit": "20"}).get("data", [])
    return [item for item in data if isinstance(item, dict)] if isinstance(data, list) else []


def find_access_until(email: str) -> int:
    """Paid-through time of this email's live academy subscription (0 if none)."""
    return max((_until(item) for item in _subscriptions(email)), default=0)


def create_academy_checkout(email: str, plan: str) -> str:
    secret_key, price_id = _secret_key(), _price_id(plan)
    email = normalize_email(email)
    base = _base_url()
    data = {
        "mode": "subscription",
        "line_items[0][price]": price_id,
        "line_items[0][quantity]": "1",
        "customer_email": email,
        "success_url": f"{base}/academy/checkout/success?session_id={{CHECKOUT_SESSION_ID}}",
        "cancel_url": f"{base}/academy/purchase",
        "metadata[yakumo_product]": PRODUCT_CODE,
        "metadata[academy_email]": email,
        "metadata[academy_plan]": plan,
        "subscription_data[metadata][yakumo_product]": PRODUCT_CODE,
        "subscription_data[metadata][academy_email]": email,
        "subscription_data[metadata][academy_plan]": plan,
    }
    try:
        response = httpx.post(
            "https://api.stripe.com/v1/checkout/sessions",
            data=data,
            headers={"Authorization": f"Bearer {secret_key}", "Idempotency-Key": uuid4().hex},
            timeout=10.0,
        )
        response.raise_for_status()
        url = response.json().get("url")
    except (httpx.HTTPError, ValueError, AttributeError) as exc:
        raise AcademyAccessError("checkout_session_create_failed") from exc
    if not isinstance(url, str) or not url.startswith("https://checkout.stripe.com/"):
        raise AcademyAccessError("checkout_session_url_invalid")
    return url


def verify_academy_checkout(session_id: str, email: str) -> int:
    """Return the paid-through time for a completed academy subscription of this email."""
    email = normalize_email(email)
    prefix = "cs_test_" if checkout_mode() == "test" else "cs_live_"
    if not session_id.startswith(prefix) or len(session_id) > 200:
        raise AcademyAccessError("checkout_session_id_invalid")
    payload = _stripe_get(f"checkout/sessions/{quote(session_id, safe='')}", {"expand[]": "subscription"})
    metadata = payload.get("metadata")
    subscription = payload.get("subscription")
    valid = (
        isinstance(metadata, dict)
        and payload.get("id") == session_id
        and payload.get("mode") == "subscription"
        and payload.get("status") == "complete"
        and metadata.get("yakumo_product") == PRODUCT_CODE
        and metadata.get("academy_email") == email
        and isinstance(subscription, dict)
    )
    until = _until(subscription) if valid else 0
    if until <= 0:
        raise AcademyAccessError("checkout_session_not_paid")
    return until


def billing_portal_url(email: str) -> str:
    """Stripe customer portal (cancel, change card, receipts) for this email's subscription."""
    subscriptions = sorted(_subscriptions(email), key=lambda item: (_until(item) > 0, item.get("created") or 0), reverse=True)
    customers = [item.get("customer") for item in subscriptions]
    customers = [c for c in customers if isinstance(c, str) and c.startswith("cus_")]
    if not customers:
        raise AcademyAccessError("billing_customer_not_found")
    try:
        response = httpx.post(
            "https://api.stripe.com/v1/billing_portal/sessions",
            data={"customer": customers[0], "return_url": f"{_base_url()}/academy/purchase"},
            headers={"Authorization": f"Bearer {_secret_key()}"},
            timeout=10.0,
        )
        response.raise_for_status()
        url = response.json().get("url")
    except (httpx.HTTPError, ValueError, AttributeError) as exc:
        raise AcademyAccessError("billing_portal_failed") from exc
    if not isinstance(url, str) or not url.startswith("https://billing.stripe.com/"):
        raise AcademyAccessError("billing_portal_url_invalid")
    return url
