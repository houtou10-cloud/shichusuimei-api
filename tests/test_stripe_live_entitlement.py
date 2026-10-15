"""Live-mode payment gate and Stripe-side consumption record. No real request is made."""

from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient

from api import customer_routes, stripe_checkout
from api.fast_reading import FAST_SECTIONS
from api.stripe_checkout import CONSUMED_METADATA_KEY, ENTITLEMENT_COOKIE, StripeCheckoutError
from main import app


# Captured at import, before the autouse conftest stub replaces them per test.
REAL_ENSURE_SESSION_UNUSED = stripe_checkout.ensure_session_unused
REAL_RECORD_READING_CONSUMED = stripe_checkout.record_reading_consumed


VALUES = {
    "birth_date": "1984-07-22",
    "birth_place": "東京都",
    "birth_time_unknown": "1",
    "gender": "female",
    "consultation": "",
}
FORM_HEADERS = {"content-type": "application/x-www-form-urlencoded"}
COOKIE = {"cookie": f"{ENTITLEMENT_COOKIE}=signed-entitlement"}


def _enable(monkeypatch, mode):
    prefix = "STRIPE_TEST" if mode == "test" else "STRIPE_LIVE"
    monkeypatch.setenv("STRIPE_CHECKOUT_MODE", mode)
    monkeypatch.setenv(f"{prefix}_CHECKOUT_ENABLED", "1")
    monkeypatch.setenv(f"{prefix}_SECRET_KEY", f"sk_{mode}_synthetic")
    monkeypatch.setenv(f"{prefix}_PRICE_ID", "price_synthetic")
    monkeypatch.setenv(f"{prefix}_WEBHOOK_SECRET", "whsec_synthetic")
    monkeypatch.setenv("CUSTOMER_ENTITLEMENT_SECRET", "synthetic-entitlement-secret-at-least-32-bytes")
    monkeypatch.setenv("CUSTOMER_PUBLIC_BASE_URL", "https://app.example.test")
    monkeypatch.delenv("CUSTOMER_ACCESS_CODE", raising=False)
    customer_routes._reset_entitlements()


@pytest.fixture
def reading(monkeypatch):
    calls = []
    result = {"session_id": "d" * 32, "chart": {}, "sections": {key: "合成応答" for key, _ in FAST_SECTIONS}}
    monkeypatch.setattr(customer_routes, "run_fast_reading", lambda *_a, **_k: calls.append(1) or result)
    return calls


def _post(client, headers=None):
    return client.post("/app/reading", content=urlencode(VALUES), headers={**FORM_HEADERS, **(headers or {})})


def test_live_mode_blocks_form_and_reading_without_payment(monkeypatch, reading):
    _enable(monkeypatch, "live")
    client = TestClient(app)
    assert client.get("/app").status_code == 402
    assert client.get("/app/reading").status_code == 402
    assert _post(client).status_code == 402
    assert client.post("/app/reading/full", content=urlencode(VALUES), headers=FORM_HEADERS).status_code == 402
    assert reading == []
    assert "テスト決済" not in client.get("/app").text


def test_live_mode_rejects_test_mode_entitlement(monkeypatch, reading):
    _enable(monkeypatch, "test")
    token = stripe_checkout.issue_entitlement("cs_test_paid")
    _enable(monkeypatch, "live")
    response = _post(TestClient(app), {"cookie": f"{ENTITLEMENT_COOKIE}={token}"})
    assert response.status_code == 402
    assert reading == []


def test_live_paid_entitlement_allows_one_reading_and_records_consumption(monkeypatch, reading):
    _enable(monkeypatch, "live")
    monkeypatch.setattr(customer_routes, "read_entitlement", lambda t: "cs_live_paid" if t == "signed-entitlement" else None)
    recorded = []
    monkeypatch.setattr(stripe_checkout, "record_reading_consumed", recorded.append)
    client = TestClient(app)
    assert client.get("/app", headers=COOKIE).status_code == 200
    assert _post(client, COOKIE).status_code == 200
    assert recorded == ["cs_live_paid"]
    assert _post(client, COOKIE).status_code == 402
    assert reading == [1]


def test_consumption_recorded_at_stripe_blocks_reuse_after_restart(monkeypatch, reading):
    _enable(monkeypatch, "live")
    monkeypatch.setattr(customer_routes, "read_entitlement", lambda t: "cs_live_paid" if t == "signed-entitlement" else None)

    def consumed(_session_id):
        raise StripeCheckoutError("checkout_session_consumed")

    monkeypatch.setattr(stripe_checkout, "ensure_session_unused", consumed)
    response = _post(TestClient(app), COOKIE)
    assert response.status_code == 402
    assert reading == []


def test_stripe_unreachable_fails_closed_without_consuming(monkeypatch, reading):
    _enable(monkeypatch, "live")
    monkeypatch.setattr(customer_routes, "read_entitlement", lambda t: "cs_live_paid" if t == "signed-entitlement" else None)

    def unreachable(_session_id):
        raise StripeCheckoutError("checkout_session_verify_failed")

    monkeypatch.setattr(stripe_checkout, "ensure_session_unused", unreachable)
    client = TestClient(app)
    assert _post(client, COOKIE).status_code == 503
    assert reading == []
    monkeypatch.setattr(stripe_checkout, "ensure_session_unused", lambda _s: None)
    assert _post(client, COOKIE).status_code == 200


def test_consumed_session_cannot_reissue_entitlement_on_success_page(monkeypatch):
    _enable(monkeypatch, "live")

    def consumed(_session_id):
        raise StripeCheckoutError("checkout_session_consumed")

    monkeypatch.setattr(customer_routes, "verify_paid_session", consumed)
    response = TestClient(app).get("/checkout/success?session_id=cs_live_paid", follow_redirects=False)
    assert response.status_code == 409
    assert "set-cookie" not in response.headers


class _Response:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _session(metadata=None):
    return {
        "id": "cs_live_paid",
        "mode": "payment",
        "payment_status": "paid",
        "currency": "jpy",
        "amount_total": 1980,
        "metadata": {"product_code": stripe_checkout.PRODUCT_CODE},
        "payment_intent": {"id": "pi_live_1", "metadata": metadata or {}},
    }


def test_real_check_and_record_use_payment_intent_metadata(monkeypatch):
    _enable(monkeypatch, "live")
    gets, posts = [], []
    state = {"metadata": {}}

    def get(url, *, params, headers, timeout):
        gets.append((url, params, headers))
        return _Response(_session(state["metadata"]))

    def post(url, *, data, headers, timeout):
        posts.append((url, data, headers))
        state["metadata"].update({CONSUMED_METADATA_KEY: "1"})
        return _Response({"id": "pi_live_1"})

    monkeypatch.setattr(stripe_checkout.httpx, "get", get)
    monkeypatch.setattr(stripe_checkout.httpx, "post", post)

    REAL_ENSURE_SESSION_UNUSED("cs_live_paid")
    assert gets[0][1] == {"expand[]": "payment_intent"}
    assert gets[0][2]["Authorization"] == "Bearer sk_live_synthetic"

    REAL_RECORD_READING_CONSUMED("cs_live_paid")
    assert posts[0][0] == "https://api.stripe.com/v1/payment_intents/pi_live_1"
    assert f"metadata[{CONSUMED_METADATA_KEY}]" in posts[0][1]

    with pytest.raises(StripeCheckoutError, match="checkout_session_consumed"):
        REAL_ENSURE_SESSION_UNUSED("cs_live_paid")
    with pytest.raises(StripeCheckoutError, match="checkout_session_consumed"):
        stripe_checkout.verify_paid_session("cs_live_paid")
