"""Mobile/PWA connection regressions using synthetic customer input.

The provider result is replaced at the HTTP boundary; these are not source-text
cases and do not assert divination accuracy.
"""

import asyncio
from types import SimpleNamespace
from urllib.parse import urlencode

from fastapi.testclient import TestClient

import api.customer_routes as customer_routes
from api.fast_reading import FAST_SECTIONS
from main import app
from api.stripe_checkout import ENTITLEMENT_COOKIE, StripeCheckoutError


def _values(**changes):
    values = {
        "birth_date": "1984-07-22",
        "birth_hour": "13",
        "birth_minute": "40",
        "birth_place": "福岡県",
        "gender": "male",
        "consultation": "合成入力によるスマホ接続確認です。",
    }
    values.update(changes)
    return values


def _post(values):
    return TestClient(app).post(
        "/app/reading",
        content=urlencode(values),
        headers={"content-type": "application/x-www-form-urlencoded"},
    )


def _reset_guard():
    asyncio.run(customer_routes._CUSTOMER_REQUEST_GUARD.reset())
    customer_routes._reset_entitlements()


def _enable_test_checkout(monkeypatch):
    monkeypatch.delenv("STRIPE_CHECKOUT_MODE", raising=False)
    monkeypatch.setenv("STRIPE_TEST_CHECKOUT_ENABLED", "1")
    monkeypatch.setenv("STRIPE_TEST_SECRET_KEY", "sk_test_synthetic")
    monkeypatch.setenv("STRIPE_TEST_PRICE_ID", "price_synthetic")
    monkeypatch.setenv("STRIPE_TEST_WEBHOOK_SECRET", "whsec_synthetic")
    monkeypatch.setenv("CUSTOMER_ENTITLEMENT_SECRET", "synthetic-entitlement-secret-at-least-32-bytes")
    monkeypatch.setenv("CUSTOMER_PUBLIC_BASE_URL", "https://example.test")
    monkeypatch.delenv("CUSTOMER_ACCESS_CODE", raising=False)


def test_mobile_form_has_accessible_inputs_truthful_status_and_single_submit_handler():
    html = TestClient(app).get("/app").text
    assert 'name="viewport" content="width=device-width,initial-scale=1"' in html
    assert 'aria-describedby="birth-date-hint"' in html
    assert 'aria-describedby="birth-place-hint"' in html
    assert 'aria-describedby="gender-hint"' in html
    assert "大運の順逆計算に使用します" in html
    assert "命式を計算し、鑑定を生成しています" in html
    assert "AI鑑定" not in html
    assert "進捗率" not in html and "残り時間" not in html
    assert html.count("readingForm.addEventListener('submit'") == 1
    assert "dataset.submitting" in html and "pageshow" in html
    assert "font-size:16px" in html


def test_career_sales_page_is_mobile_ready_and_truthful_before_payment_connection():
    response = TestClient(app).get("/career-reading")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    html = response.text
    assert 'name="viewport" content="width=device-width,initial-scale=1"' in html
    assert "転職すべきか" in html and "独立へ進むべきか" in html
    assert "1鑑定 1,980円（税込）" in html
    assert "買い切り" in html and "継続課金はありません" in html
    assert "Stripe決済はまだ接続されておらず" in html
    assert 'href="/app"' in html
    assert "残り" not in html and "今だけ" not in html
    assert "@media(max-width:700px)" in html


def test_test_checkout_start_is_disabled_by_default_and_uses_redirect_only_when_enabled(monkeypatch):
    client = TestClient(app)
    disabled = client.post("/checkout/start")
    assert disabled.status_code == 404
    assert "決済は無効です" in disabled.text

    _enable_test_checkout(monkeypatch)
    monkeypatch.setattr(customer_routes, "create_checkout_session", lambda: "https://checkout.stripe.com/c/pay/synthetic")
    enabled_sales = client.get("/career-reading")
    assert 'action="/checkout/start"' in enabled_sales.text
    assert "Stripeテストモードです" in enabled_sales.text
    started = client.post("/checkout/start", follow_redirects=False)
    assert started.status_code == 303
    assert started.headers["location"] == "https://checkout.stripe.com/c/pay/synthetic"


def test_live_checkout_requires_two_flags_and_has_no_test_copy(monkeypatch):
    monkeypatch.setenv("STRIPE_CHECKOUT_MODE", "live")
    monkeypatch.delenv("STRIPE_LIVE_CHECKOUT_ENABLED", raising=False)
    disabled = TestClient(app).get("/career-reading").text
    assert "鑑定を購入する" not in disabled
    assert "Stripe決済はまだ接続されておらず" in disabled

    monkeypatch.setenv("STRIPE_LIVE_CHECKOUT_ENABLED", "1")
    enabled = TestClient(app).get("/career-reading").text
    assert "鑑定を購入する（1,980円）" in enabled
    assert "Stripeの安全な決済画面へ移動します" in enabled
    assert "テスト決済" not in enabled


def test_paid_test_session_issues_secure_entitlement_and_blocks_direct_access(monkeypatch):
    _reset_guard()
    _enable_test_checkout(monkeypatch)
    client = TestClient(app)
    denied = client.get("/app")
    assert denied.status_code == 402
    assert "お支払いの確認が必要です" in denied.text

    calls = []
    monkeypatch.setattr(customer_routes, "verify_paid_session", lambda session_id: calls.append(session_id) or {})
    monkeypatch.setattr(customer_routes, "issue_entitlement", lambda _session_id: "signed-entitlement")
    success = client.get("/checkout/success?session_id=cs_test_paid", follow_redirects=False)
    assert success.status_code == 303
    assert success.headers["location"] == "/app?payment=success"
    cookie = success.headers["set-cookie"]
    assert f"{ENTITLEMENT_COOKIE}=signed-entitlement" in cookie
    assert "HttpOnly" in cookie and "Secure" in cookie and "SameSite=lax" in cookie
    assert calls == ["cs_test_paid"]


def test_entitlement_is_consumed_only_after_successful_reading(monkeypatch):
    _reset_guard()
    _enable_test_checkout(monkeypatch)
    monkeypatch.setattr(customer_routes, "read_entitlement", lambda token: "cs_test_paid" if token == "signed-entitlement" else None)
    result = {
        "session_id": "b" * 32,
        "chart": {},
        "sections": {key: "合成応答" for key, _ in FAST_SECTIONS},
    }
    calls = []
    monkeypatch.setattr(customer_routes, "run_fast_reading", lambda *_args, **_kwargs: calls.append(1) or result)
    headers = {"cookie": f"{ENTITLEMENT_COOKIE}=signed-entitlement"}
    client = TestClient(app)
    form = client.get("/app", headers=headers)
    assert form.status_code == 200
    first = client.post(
        "/app/reading",
        content=urlencode(_values()),
        headers={"content-type": "application/x-www-form-urlencoded", **headers},
    )
    assert first.status_code == 200
    assert calls == [1]
    second = client.post(
        "/app/reading",
        content=urlencode(_values()),
        headers={"content-type": "application/x-www-form-urlencoded", **headers},
    )
    assert second.status_code == 402
    assert calls == [1]


def test_generation_failure_keeps_entitlement_available_for_retry(monkeypatch):
    _reset_guard()
    _enable_test_checkout(monkeypatch)
    monkeypatch.setattr(customer_routes, "read_entitlement", lambda token: "cs_test_retry" if token == "signed-entitlement" else None)
    attempts = []

    def reading(*_args, **_kwargs):
        attempts.append(1)
        if len(attempts) == 1:
            raise RuntimeError("synthetic provider failure")
        return {
            "session_id": "c" * 32,
            "chart": {},
            "sections": {key: "再試行成功" for key, _ in FAST_SECTIONS},
        }

    monkeypatch.setattr(customer_routes, "run_fast_reading", reading)
    headers = {
        "content-type": "application/x-www-form-urlencoded",
        "cookie": f"{ENTITLEMENT_COOKIE}=signed-entitlement",
    }
    client = TestClient(app)
    first = client.post("/app/reading", content=urlencode(_values()), headers=headers)
    assert first.status_code == 503
    assert "もう一度お試しください" in first.text
    second = client.post("/app/reading", content=urlencode(_values()), headers=headers)
    assert second.status_code == 200
    assert "再試行成功" in second.text
    assert attempts == [1, 1]


def test_test_checkout_failure_and_webhook_duplicates_are_explicit(monkeypatch):
    _reset_guard()
    _enable_test_checkout(monkeypatch)
    monkeypatch.setattr(customer_routes, "create_checkout_session", lambda: (_ for _ in ()).throw(StripeCheckoutError("synthetic_failure")))
    failed = TestClient(app).post("/checkout/start")
    assert failed.status_code == 503
    assert "決済を開始できませんでした" in failed.text

    monkeypatch.setattr(customer_routes, "verify_webhook", lambda *_args: {"id": "evt_test_1", "type": "checkout.session.completed"})
    client = TestClient(app)
    first = client.post("/stripe/webhook", content=b"{}")
    second = client.post("/stripe/webhook", content=b"{}")
    assert first.json() == {"received": True, "duplicate": False}
    assert second.json() == {"received": True, "duplicate": True}


def test_legal_pages_are_linked_mobile_ready_and_disclosure_image_is_served():
    client = TestClient(app)
    sales = client.get("/career-reading").text
    for path, label in (("/terms", "利用規約"), ("/privacy", "プライバシーポリシー"), ("/legal", "特定商取引法に基づく表記")):
        assert f'href="{path}"' in sales
        response = client.get(path)
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert 'name="viewport" content="width=device-width,initial-scale=1"' in response.text
        assert label in response.text
        if path != "/legal":
            assert "公開前案" not in response.text
            assert "2026年10月15日" in response.text
    assert "決済へ進むことで、利用規約とプライバシーポリシーを確認し、同意したものとします。" in sales
    terms = client.get("/terms").text
    assert "特定商取引法に基づく表記" in terms
    assert "自動更新・継続課金はありません" in terms
    privacy = client.get("/privacy").text
    assert "OpenAI API" in privacy
    assert "Render" in privacy
    assert "Stripe" in privacy
    assert 'href="https://form.os7.biz/f/be4d264a/"' in privacy
    legal = client.get("/legal").text
    assert 'src="/legal/disclosure.png"' in legal
    assert 'href="https://form.os7.biz/f/be4d264a/"' in legal
    assert 'rel="noopener noreferrer"' in legal
    image = client.get("/legal/disclosure.png")
    assert image.status_code == 200
    assert image.headers["content-type"] == "image/png"
    assert image.content.startswith(b"\x89PNG\r\n\x1a\n")


def test_access_code_is_optional_until_configured(monkeypatch):
    monkeypatch.delenv("CUSTOMER_ACCESS_CODE", raising=False)
    html = TestClient(app).get("/app").text
    assert 'name="access_code"' not in html


def test_access_code_rejects_before_provider_and_never_echoes_secret(monkeypatch):
    _reset_guard()
    monkeypatch.setenv("CUSTOMER_ACCESS_CODE", "synthetic-secret-code")
    calls = []
    monkeypatch.setattr(customer_routes, "run_fast_reading", lambda *_args, **_kwargs: calls.append(1))

    form = TestClient(app).get("/app")
    assert form.status_code == 200
    assert 'name="access_code" type="password"' in form.text
    assert "synthetic-secret-code" not in form.text

    denied = _post(_values(access_code="wrong-code", consultation="保持対象の相談"))
    assert denied.status_code == 403
    assert denied.headers["cache-control"] == "no-store"
    assert "アクセスコードを確認してください" in denied.text
    assert "保持対象の相談" in denied.text
    assert "wrong-code" not in denied.text
    assert "synthetic-secret-code" not in denied.text
    assert calls == []


def test_access_code_allows_provider_without_leaking_code(monkeypatch):
    _reset_guard()
    monkeypatch.setenv("CUSTOMER_ACCESS_CODE", "synthetic-secret-code")
    result = {
        "session_id": "a" * 32,
        "chart": {},
        "sections": {key: "合成応答" for key, _ in FAST_SECTIONS},
    }
    calls = []

    def reading(*_args, **_kwargs):
        calls.append(1)
        return result

    monkeypatch.setattr(customer_routes, "run_fast_reading", reading)
    response = _post(_values(access_code="synthetic-secret-code"))
    assert response.status_code == 200
    assert "あなたの鑑定結果" in response.text
    assert "synthetic-secret-code" not in response.text
    assert calls == [1]


def test_pwa_assets_are_installable_but_never_cache_customer_data():
    client = TestClient(app)
    form = client.get("/app")
    assert 'rel="manifest" href="/app/manifest.webmanifest"' in form.text
    assert 'rel="apple-touch-icon" sizes="180x180" href="/app/apple-touch-icon.png"' in form.text
    assert "この鑑定には通信が必要です" in form.text
    assert form.text.count("鑑定には通信が必要です") == 1
    assert "端末へ保存することはありません" in form.text
    assert "beforeinstallprompt" in form.text
    assert "iPhone／iPadでは共有メニュー" in form.text

    manifest = client.get("/app/manifest.webmanifest")
    assert manifest.status_code == 200
    payload = manifest.json()
    assert payload["start_url"] == "/app"
    assert payload["scope"] == "/app"
    assert payload["display"] == "standalone"
    assert [(icon["sizes"], icon["type"]) for icon in payload["icons"][:2]] == [
        ("192x192", "image/png"), ("512x512", "image/png")
    ]
    assert all(icon["purpose"] == "any maskable" for icon in payload["icons"][:2])

    for path, size in (
        ("/app/apple-touch-icon.png", 180),
        ("/app/icon-192.png", 192),
        ("/app/icon-512.png", 512),
    ):
        icon = client.get(path)
        assert icon.status_code == 200
        assert icon.headers["content-type"].startswith("image/png")
        # PNG signature plus IHDR width/height fields.
        assert icon.content.startswith(b"\x89PNG\r\n\x1a\n")
        assert int.from_bytes(icon.content[16:20], "big") == size
        assert int.from_bytes(icon.content[20:24], "big") == size

    worker = client.get("/app/sw.js")
    assert worker.status_code == 200
    assert worker.headers["cache-control"] == "no-store"
    assert worker.headers["service-worker-allowed"] == "/app"
    assert "fetch" not in worker.text
    assert "caches.delete" in worker.text
    for forbidden in ("localStorage", "sessionStorage", "indexedDB"):
        assert forbidden not in form.text + worker.text


def test_input_error_retains_values_and_marks_the_specific_field():
    response = _post(_values(birth_date="not-a-date"))
    assert response.status_code == 422
    assert 'value="not-a-date"' in response.text
    assert "入力内容をご確認ください" in response.text
    assert "合成入力によるスマホ接続確認です" in response.text


def test_timeout_and_ai_failure_are_distinct_and_retain_input(monkeypatch):
    def timeout(*_args, **_kwargs):
        raise TimeoutError("synthetic timeout")

    monkeypatch.setattr(customer_routes, "run_fast_reading", timeout)
    timed_out = _post(_values())
    assert timed_out.status_code == 503
    assert "時間内に完了しませんでした" in timed_out.text
    assert 'value="1984-07-22"' in timed_out.text
    assert "合成入力によるスマホ接続確認です" in timed_out.text

    def failed(*_args, **_kwargs):
        raise RuntimeError("synthetic provider failure")

    monkeypatch.setattr(customer_routes, "run_fast_reading", failed)
    failed_response = _post(_values())
    assert failed_response.status_code == 503
    assert "鑑定の生成中に確認が必要な状態" in failed_response.text
    assert "AI鑑定" not in failed_response.text
    assert "時間内に完了しませんでした" not in failed_response.text


def test_synthetic_input_reaches_mobile_result_without_page_wide_overflow(monkeypatch):
    _reset_guard()
    result = {
        "session_id": "a" * 32,
        "chart": {},
        "sections": {key: "合成したAI応答です。" for key, _ in FAST_SECTIONS},
    }
    monkeypatch.setattr(customer_routes, "run_fast_reading", lambda *_args, **_kwargs: result)
    response = _post(_values())
    assert response.status_code == 200
    assert "あなたの鑑定結果" in response.text
    assert response.text.count('class="fast-card"') == 7
    assert ".table-wrap{overflow-x:hidden;" in response.text
    assert ".chart-table,.luck-table{min-width:0" in response.text
    assert ".annual-grid{min-width:0;grid-template-columns:repeat(2" in response.text
    assert 'rel="manifest" href="/app/manifest.webmanifest"' in response.text


def test_rate_limit_returns_429_retains_input_and_skips_provider(monkeypatch):
    _reset_guard()
    monkeypatch.setenv("CUSTOMER_RATE_LIMIT_ENABLED", "1")
    monkeypatch.setenv("CUSTOMER_RATE_LIMIT_MAX_REQUESTS", "1")
    calls = []

    def reading(*_args, **_kwargs):
        calls.append(1)
        return {
            "session_id": "a" * 32,
            "chart": {},
            "sections": {key: "合成応答" for key, _ in FAST_SECTIONS},
        }

    monkeypatch.setattr(customer_routes, "run_fast_reading", reading)
    assert _post(_values()).status_code == 200
    limited = _post(_values(consultation="保持される相談内容"))
    assert limited.status_code == 429
    assert limited.headers["retry-after"]
    assert limited.headers["cache-control"] == "no-store"
    assert "短時間に鑑定が集中しています" in limited.text
    assert "保持される相談内容" in limited.text
    assert len(calls) == 1


def test_invalid_input_does_not_consume_rate_limit(monkeypatch):
    _reset_guard()
    monkeypatch.setenv("CUSTOMER_RATE_LIMIT_ENABLED", "1")
    monkeypatch.setenv("CUSTOMER_RATE_LIMIT_MAX_REQUESTS", "1")
    result = {
        "session_id": "a" * 32,
        "chart": {},
        "sections": {key: "合成応答" for key, _ in FAST_SECTIONS},
    }
    monkeypatch.setattr(customer_routes, "run_fast_reading", lambda *_args, **_kwargs: result)
    assert _post(_values(birth_date="invalid")).status_code == 422
    assert _post(_values()).status_code == 200


def test_rate_limit_can_be_disabled_for_controlled_recovery(monkeypatch):
    _reset_guard()
    monkeypatch.setenv("CUSTOMER_RATE_LIMIT_ENABLED", "0")
    monkeypatch.setenv("CUSTOMER_RATE_LIMIT_MAX_REQUESTS", "1")
    result = {
        "session_id": "a" * 32,
        "chart": {},
        "sections": {key: "合成応答" for key, _ in FAST_SECTIONS},
    }
    monkeypatch.setattr(customer_routes, "run_fast_reading", lambda *_args, **_kwargs: result)
    assert _post(_values()).status_code == 200
    assert _post(_values()).status_code == 200


def test_concurrent_guard_rejects_extra_request(monkeypatch):
    monkeypatch.setenv("CUSTOMER_RATE_LIMIT_ENABLED", "1")
    monkeypatch.setenv("CUSTOMER_RATE_LIMIT_MAX_CONCURRENT", "1")

    async def scenario():
        await customer_routes._CUSTOMER_REQUEST_GUARD.reset()
        request = SimpleNamespace(client=SimpleNamespace(host="synthetic-client"))
        async with customer_routes._CUSTOMER_REQUEST_GUARD.limit(request):
            try:
                async with customer_routes._CUSTOMER_REQUEST_GUARD.limit(request):
                    raise AssertionError("second request should not enter")
            except customer_routes._CustomerRateLimitExceeded as exc:
                assert exc.retry_after == 5

    asyncio.run(scenario())
