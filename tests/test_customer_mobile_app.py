"""Mobile/PWA connection regressions using synthetic customer input.

The provider result is replaced at the HTTP boundary; these are not source-text
cases and do not assert divination accuracy.
"""

from urllib.parse import urlencode

from fastapi.testclient import TestClient

import api.customer_routes as customer_routes
from api.fast_reading import FAST_SECTIONS
from main import app


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


def test_mobile_form_has_accessible_inputs_truthful_status_and_single_submit_handler():
    html = TestClient(app).get("/app").text
    assert 'name="viewport" content="width=device-width,initial-scale=1"' in html
    assert 'aria-describedby="birth-date-hint"' in html
    assert 'aria-describedby="birth-place-hint"' in html
    assert 'aria-describedby="gender-hint"' in html
    assert "大運の順逆計算に使用します" in html
    assert "命式を計算し、AI鑑定を生成しています" in html
    assert "進捗率" not in html and "残り時間" not in html
    assert html.count("readingForm.addEventListener('submit'") == 1
    assert "dataset.submitting" in html and "pageshow" in html
    assert "font-size:16px" in html


def test_pwa_assets_are_installable_but_never_cache_customer_data():
    client = TestClient(app)
    form = client.get("/app")
    assert 'rel="manifest" href="/app/manifest.webmanifest"' in form.text
    assert 'rel="apple-touch-icon" sizes="180x180" href="/app/apple-touch-icon.png"' in form.text
    assert "この鑑定には通信が必要です" in form.text
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
    assert "AI鑑定の生成中に確認が必要な状態" in failed_response.text
    assert "時間内に完了しませんでした" not in failed_response.text


def test_synthetic_input_reaches_mobile_result_without_page_wide_overflow(monkeypatch):
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
