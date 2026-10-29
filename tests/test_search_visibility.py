"""販売ページを本番決済（live）のときだけ検索エンジンに公開する。"""

from fastapi.testclient import TestClient

from main import app


def _live(monkeypatch):
    monkeypatch.setenv("STRIPE_CHECKOUT_MODE", "live")
    monkeypatch.setenv("STRIPE_LIVE_CHECKOUT_ENABLED", "1")
    monkeypatch.setenv("CUSTOMER_PUBLIC_BASE_URL", "https://app.yakumoshiki.jp")


def test_live_sales_and_legal_pages_are_indexable(monkeypatch):
    _live(monkeypatch)
    client = TestClient(app)
    sales = client.get("/career-reading").text
    assert '<meta name="robots" content="index,follow">' in sales
    assert '<link rel="canonical" href="https://app.yakumoshiki.jp/career-reading">' in sales
    assert '<meta name="description"' in sales
    for path in ("/terms", "/privacy", "/legal"):
        assert "index,follow" in client.get(path).text


def test_customer_input_and_results_stay_hidden(monkeypatch):
    _live(monkeypatch)
    robots = TestClient(app).get("/robots.txt").text
    assert "Allow: /career-reading" in robots
    assert "Disallow: /app" in robots and "Disallow: /academy" in robots
    assert "Sitemap: https://app.yakumoshiki.jp/sitemap.xml" in robots
    sitemap = TestClient(app).get("/sitemap.xml").text
    assert "<loc>https://app.yakumoshiki.jp/career-reading</loc>" in sitemap
    assert "yakumoshiki.jp/app<" not in sitemap and "yakumoshiki.jp/app/" not in sitemap


def test_not_live_stays_noindex(monkeypatch):
    monkeypatch.delenv("STRIPE_CHECKOUT_MODE", raising=False)
    monkeypatch.delenv("STRIPE_LIVE_CHECKOUT_ENABLED", raising=False)
    monkeypatch.delenv("STRIPE_TEST_CHECKOUT_ENABLED", raising=False)
    client = TestClient(app)
    assert "noindex,nofollow" in client.get("/career-reading").text
    assert "Disallow: /" in client.get("/robots.txt").text
    assert "<url>" not in client.get("/sitemap.xml").text
