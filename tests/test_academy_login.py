from __future__ import annotations

import time

import httpx
import pytest
from fastapi.testclient import TestClient

from api import academy_access
from api.academy_access import AcademyAccessError, Login
from main import app

CLIENT = TestClient(app)
NOW = int(time.time())


@pytest.fixture
def gate(monkeypatch):
    for key, value in {
        "ACADEMY_LOGIN_REQUIRED": "1",
        "CUSTOMER_ENTITLEMENT_SECRET": "x" * 40,
        "CUSTOMER_PUBLIC_BASE_URL": "https://academy.example.test",
        "STRIPE_CHECKOUT_MODE": "test",
        "STRIPE_TEST_CHECKOUT_ENABLED": "1",
        "STRIPE_TEST_SECRET_KEY": "sk_test_dummy",
        "STRIPE_TEST_ACADEMY_MONTHLY_PRICE_ID": "price_monthly",
        "STRIPE_TEST_ACADEMY_YEARLY_PRICE_ID": "price_yearly",
        "GOOGLE_OAUTH_CLIENT_ID": "dummy.apps.googleusercontent.com",
        "GOOGLE_OAUTH_CLIENT_SECRET": "dummy-secret",
    }.items():
        monkeypatch.setenv(key, value)


def _cookie(login: Login) -> dict[str, str]:
    return {"cookie": f"{academy_access.ACCESS_COOKIE}={academy_access.issue_login(login)}"}


def test_gate_is_off_unless_enabled(monkeypatch):
    monkeypatch.delenv("ACADEMY_LOGIN_REQUIRED", raising=False)
    assert CLIENT.get("/academy/course/6/4").status_code == 200
    assert "受講登録・ログイン" not in CLIENT.get("/academy/courses").text


def test_first_chapter_is_free_and_later_chapters_need_purchase(gate):
    assert CLIENT.get("/academy/course/1/7").status_code == 200
    locked = CLIENT.get("/academy/course/2/1")
    assert locked.status_code == 403
    assert "受講登録が必要です" in locked.text
    assert "youtube" not in locked.text
    assert "Googleでログイン" in locked.text
    assert CLIENT.post("/academy/course/2/1/check", data={}).status_code == 403
    assert "第2章以降と実践トレーニングは" in CLIENT.get("/academy/courses").text


def test_active_login_opens_paid_lessons(gate):
    active = _cookie(Login("buyer@example.com", NOW + 3600))
    assert CLIENT.get("/academy/course/12/7", headers=active).status_code == 200
    expired = CLIENT.get("/academy/course/12/7", headers=_cookie(Login("buyer@example.com", NOW - 1)))
    assert expired.status_code == 403
    assert "有効な受講登録がありません" in expired.text


def test_practice_needs_purchase(gate, monkeypatch):
    monkeypatch.setattr(academy_access, "find_access_until", lambda email: 0)
    locked = CLIENT.get("/academy/practice")
    assert locked.status_code == 403
    assert "実践トレーニングは、受講登録をした方が使える機能です" in locked.text
    assert "Googleでログイン" in locked.text
    assert CLIENT.post("/academy/start", data={}).status_code == 403
    assert CLIENT.post("/academy/check", data={}).status_code == 403
    assert CLIENT.get("/academy/practice", headers=_cookie(Login("new@example.com", NOW - 1))).status_code == 403
    assert CLIENT.get("/academy/practice", headers=_cookie(Login("buyer@example.com", NOW + 3600))).status_code == 200
    assert "第2章以降と実践トレーニングは" in CLIENT.get("/academy/courses").text


def test_tampered_or_other_mode_cookie_is_rejected(gate, monkeypatch):
    token = academy_access.issue_login(Login("buyer@example.com", NOW + 3600))
    head, signature = token.split(".")
    forged = f"{head}.{'0' * len(signature)}"
    assert CLIENT.get("/academy/course/2/1", headers={"cookie": f"{academy_access.ACCESS_COOKIE}={forged}"}).status_code == 403
    monkeypatch.setenv("STRIPE_CHECKOUT_MODE", "live")
    monkeypatch.setenv("STRIPE_LIVE_CHECKOUT_ENABLED", "1")
    assert academy_access.read_login(token) is None


def test_login_redirects_to_google_with_state_cookie(gate):
    response = CLIENT.get("/academy/login?next=/academy/course/3/2", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"].startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert "redirect_uri=https%3A%2F%2Facademy.example.test%2Facademy%2Fauth%2Fcallback" in response.headers["location"]
    assert academy_access.STATE_COOKIE in response.headers["set-cookie"]


def test_callback_requires_matching_state(gate, monkeypatch):
    monkeypatch.setattr(academy_access, "google_email", lambda code: "buyer@example.com")
    monkeypatch.setattr(academy_access, "find_access_until", lambda email: NOW + 3600)
    state, token = academy_access.issue_state("/academy/course/3/2")
    headers = {"cookie": f"{academy_access.STATE_COOKIE}={token}"}
    bad = CLIENT.get("/academy/auth/callback?code=c&state=wrong", headers=headers, follow_redirects=False)
    assert bad.status_code == 400
    good = CLIENT.get(f"/academy/auth/callback?code=c&state={state}", headers=headers, follow_redirects=False)
    assert good.status_code == 303
    assert good.headers["location"] == "/academy/course/3/2"
    assert academy_access.ACCESS_COOKIE in good.headers["set-cookie"]


def test_callback_without_purchase_goes_to_purchase_page(gate, monkeypatch):
    monkeypatch.setattr(academy_access, "google_email", lambda code: "new@example.com")
    monkeypatch.setattr(academy_access, "find_access_until", lambda email: 0)
    state, token = academy_access.issue_state("/academy/course/3/2")
    response = CLIENT.get(f"/academy/auth/callback?code=c&state={state}", headers={"cookie": f"{academy_access.STATE_COOKIE}={token}"}, follow_redirects=False)
    assert response.headers["location"] == "/academy/purchase"


def test_purchase_page_shows_both_plans_and_subscription_terms(gate, monkeypatch):
    monkeypatch.setattr(academy_access, "find_access_until", lambda email: 0)
    anonymous = CLIENT.get("/academy/purchase").text
    assert "Googleでログイン" in anonymous and "最低契約期間はありません" in anonymous
    page = CLIENT.get("/academy/purchase", headers=_cookie(Login("new@example.com", 0))).text
    assert "new@example.com" in page
    for text in ("月額プランで申し込む（月額2,980円（税込））", "年額プランで申し込む（年額19,800円（税込））", "自動で請求", "次回の請求日の前日までに解約", "18歳以上", "/academy/terms", "契約の確認・解約"):
        assert text in page


def test_checkout_uses_selected_plan(gate, monkeypatch):
    chosen = []
    monkeypatch.setattr(academy_access, "create_academy_checkout", lambda email, plan: chosen.append((email, plan)) or "https://checkout.stripe.com/c/pay/test")
    login = _cookie(Login("new@example.com", 0))
    response = CLIENT.post("/academy/checkout", headers=login, data={"plan": "yearly"}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "https://checkout.stripe.com/c/pay/test"
    assert chosen == [("new@example.com", "yearly")]
    assert CLIENT.post("/academy/checkout", headers=login, data={"plan": "lifetime"}, follow_redirects=False).headers["location"] == "/academy/purchase"
    assert CLIENT.post("/academy/checkout", data={"plan": "monthly"}, follow_redirects=False).headers["location"] == "/academy/purchase"


def test_checkout_session_is_a_subscription_with_metadata(gate, monkeypatch):
    sent = {}

    def fake_post(url, data=None, headers=None, timeout=None):
        sent.update(data)
        return httpx.Response(200, json={"url": "https://checkout.stripe.com/c/pay/x"}, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", fake_post)
    academy_access.create_academy_checkout("Buyer@Example.com", "monthly")
    assert sent["mode"] == "subscription"
    assert sent["line_items[0][price]"] == "price_monthly"
    assert sent["subscription_data[metadata][academy_email]"] == "buyer@example.com"
    assert sent["subscription_data[metadata][yakumo_product]"] == "yakumo-academy"


def test_expired_cookie_is_renewed_from_stripe(gate, monkeypatch):
    monkeypatch.setattr(academy_access, "find_access_until", lambda email: NOW + 3600)
    response = CLIENT.get("/academy/course/2/1", headers=_cookie(Login("buyer@example.com", NOW - 10)))
    assert response.status_code == 200
    assert academy_access.ACCESS_COOKIE in response.headers["set-cookie"]


def test_billing_portal_redirect(gate, monkeypatch):
    monkeypatch.setattr(academy_access, "billing_portal_url", lambda email: "https://billing.stripe.com/p/session/x")
    response = CLIENT.post("/academy/billing", headers=_cookie(Login("buyer@example.com", NOW + 10)), follow_redirects=False)
    assert response.headers["location"] == "https://billing.stripe.com/p/session/x"
    assert CLIENT.post("/academy/billing", follow_redirects=False).headers["location"] == "/academy/purchase"


def test_academy_terms_page():
    page = CLIENT.get("/academy/terms").text
    for text in ("月額プランが2,980円", "年額プランが19,800円", "最低契約期間はありません", "18歳以上の方が利用できます", "日割りを含む"):
        assert text in page


def test_checkout_success_grants_access(gate, monkeypatch):
    monkeypatch.setattr(academy_access, "verify_academy_checkout", lambda session_id, email: NOW + 30 * 86400)
    response = CLIENT.get("/academy/checkout/success?session_id=cs_test_1", headers=_cookie(Login("new@example.com", 0)))
    assert response.status_code == 200
    assert "受講登録が完了しました" in response.text
    assert academy_access.ACCESS_COOKIE in response.headers["set-cookie"]
    assert CLIENT.get("/academy/checkout/success?session_id=cs_test_1").status_code == 401


def test_safe_next_only_allows_academy_paths():
    assert academy_access.safe_next("/academy/course/2/1") == "/academy/course/2/1"
    for value in ("https://evil.example", "//evil.example", "/app/reading", "/academy/../app", ""):
        assert academy_access.safe_next(value) == "/academy/courses"


def test_only_live_subscriptions_give_access():
    assert academy_access._until({"status": "canceled", "current_period_end": NOW + 99}) == 0
    assert academy_access._until({"status": "incomplete", "current_period_end": NOW + 99}) == 0
    assert academy_access._until({"status": "active", "current_period_end": NOW + 99}) == NOW + 99
    assert academy_access._until({"status": "past_due", "items": {"data": [{"current_period_end": NOW + 50}]}}) == NOW + 50


def test_checkout_must_belong_to_logged_in_email(gate, monkeypatch):
    session = {
        "id": "cs_test_1", "mode": "subscription", "status": "complete",
        "metadata": {"yakumo_product": "yakumo-academy", "academy_email": "other@example.com"},
        "subscription": {"status": "active", "current_period_end": NOW + 99},
    }
    monkeypatch.setattr(httpx, "get", lambda *a, **k: httpx.Response(200, json=session, request=httpx.Request("GET", "https://api.stripe.com")))
    with pytest.raises(AcademyAccessError):
        academy_access.verify_academy_checkout("cs_test_1", "buyer@example.com")
    session["metadata"]["academy_email"] = "buyer@example.com"
    assert academy_access.verify_academy_checkout("cs_test_1", "Buyer@Example.com") == NOW + 99


def test_search_query_rejects_unsafe_email(gate):
    with pytest.raises(AcademyAccessError):
        academy_access.find_access_until("a'b@example.com")


def test_portal_and_lessons_link_to_career_reading():
    assert 'href="/career-reading"' in CLIENT.get("/academy").text
    assert 'href="/career-reading"' in CLIENT.get("/academy/course/1/2").text


def test_menu_links_to_career_reading():
    nav = CLIENT.get("/academy/courses").text.split('<nav class="nav">')[1].split("</nav>")[0]
    assert '<a href="/career-reading">四柱推命鑑定</a>' in nav
