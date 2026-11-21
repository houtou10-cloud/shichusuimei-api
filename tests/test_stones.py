"""天然石＋プレミアム鑑定の見本ページ（/stones）。"""

from fastapi.testclient import TestClient

from main import app

CLIENT = TestClient(app)
BANNED = ("金運が上がる", "運気が上がる", "治る", "癒し", "波動", "浄化", "天中殺", "必ず", "あなたに必要", "鑑定士による")


def test_sample_page_is_hidden_and_cannot_take_orders():
    response = CLIENT.get("/stones")
    page = response.text
    assert response.status_code == 200
    assert "noindex,nofollow" in page and response.headers["x-robots-tag"] == "noindex, nofollow"
    assert "これは見本です。まだ販売していません" in page
    assert "<form" not in page and "buy.stripe.com" not in page and "/checkout" not in page


def test_sample_page_follows_the_wording_rules():
    page = CLIENT.get("/stones").text
    for word in BANNED:
        assert word not in page
    assert "VOICEVOX「麒ヶ島宗麟」" in page
    assert "1,980円の鑑定と同じ八雲式の規則" in page
    assert "日干が" not in page
    assert "お申し込みの前に" not in page and "自分史" not in page
    assert "0120-279-338" in page


def test_sample_page_is_not_linked_from_public_pages():
    for path in ("/career-reading", "/jibunshi", "/nikkan"):
        assert 'href="/stones' not in CLIENT.get(path).text
