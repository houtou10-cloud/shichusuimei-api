"""自分史鑑定の申込ページ（/jibunshi）。"""

from fastapi.testclient import TestClient

from api import jibunshi
from main import app

CLIENT = TestClient(app)
BANNED = ("霊視します", "因縁", "先祖", "不幸", "必ず", "治る", "運気が上がる", "収入が増える", "本によると", "本では", "基礎編", "応用編", "八雲が読みます")


def _clear(monkeypatch):
    for name in (jibunshi.PAYMENT_ENV, jibunshi.FORM_ENV):
        monkeypatch.delenv(name, raising=False)


def test_page_is_pending_without_payment_links(monkeypatch):
    _clear(monkeypatch)
    page = CLIENT.get("/jibunshi").text
    assert "八雲式 自分史鑑定" in page and "19,800円（税込）" in page
    assert "受付の準備中" in page and "buy.stripe.com" not in page
    assert "noindex,nofollow" in page


def test_support_comes_before_purchase(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv(jibunshi.PAYMENT_ENV, "https://buy.stripe.com/test_abc")
    page = CLIENT.get("/jibunshi").text
    assert 'href="tel:0120279338"' in page
    assert page.index("お申し込みの前に") < page.index("https://buy.stripe.com/test_abc")


def test_single_regular_price_button(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv(jibunshi.PAYMENT_ENV, "https://buy.stripe.com/regular")
    page = CLIENT.get("/jibunshi").text
    assert "申し込む（19,800円）" in page
    assert "受付の準備中" not in page and "モニター" not in page and "9,800円" not in page.replace("19,800円", "")


def test_untrusted_urls_are_ignored(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv(jibunshi.PAYMENT_ENV, "https://evil.example/pay")
    assert "evil.example" not in CLIENT.get("/jibunshi").text
    monkeypatch.setenv(jibunshi.PAYMENT_ENV, 'https://buy.stripe.com/x"><script>')
    page = CLIENT.get("/jibunshi").text
    assert "<script>" not in page and "受付の準備中" in page


def test_page_states_reading_rules_without_banned_words(monkeypatch):
    _clear(monkeypatch)
    page = CLIENT.get("/jibunshi").text
    assert "命式と結びつけて読みません" in page
    assert "名前は、動画とPDFに入れません" in page
    assert "30日後" in page and "Claude" in page
    assert not any(word in page for word in BANNED)


def test_thanks_page_shows_form_link_only_when_valid(monkeypatch):
    _clear(monkeypatch)
    assert "フォームの準備中" in CLIENT.get("/jibunshi/thanks").text
    monkeypatch.setenv(jibunshi.FORM_ENV, "https://forms.gle/abc123")
    page = CLIENT.get("/jibunshi/thanks").text
    assert 'href="https://forms.gle/abc123"' in page and "noindex,nofollow" in page
    monkeypatch.setenv(jibunshi.FORM_ENV, "https://example.com/form")
    assert "example.com" not in CLIENT.get("/jibunshi/thanks").text


def test_legal_pages_cover_jibunshi():
    assert "10. 自分史鑑定" in CLIENT.get("/terms").text
    privacy = CLIENT.get("/privacy").text
    assert "Anthropic PBCのClaude" in privacy and "お届けしてから30日後に削除" in privacy
    legal = CLIENT.get("/legal").text
    assert "<h2>自分史鑑定</h2>" in legal and "1件19,800円（税込）" in legal and "モニター" not in legal


def test_jibunshi_is_listed_for_search_when_live(monkeypatch):
    monkeypatch.setattr("api.customer_routes.checkout_mode", lambda: "live")
    monkeypatch.setenv("CUSTOMER_PUBLIC_BASE_URL", "https://app.yakumoshiki.jp")
    assert "Allow: /jibunshi" in CLIENT.get("/robots.txt").text
    assert "index,follow" in CLIENT.get("/jibunshi").text
