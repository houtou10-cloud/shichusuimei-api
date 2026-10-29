"""鑑定の販売ページを「八雲式 四柱推命鑑定」として、キャリアに限らない内容で案内する。"""

from fastapi.testclient import TestClient

from main import app

CLIENT = TestClient(app)


def test_sales_page_is_general_reading_without_fear_appeals():
    html = CLIENT.get("/career-reading").text
    assert "<title>八雲式 四柱推命鑑定</title>" in html
    assert "キャリア" not in html and "転職すべきか" not in html
    assert "あなたの本質" in html and "五行のバランス" in html
    assert "不安をあおったりする鑑定ではありません" in html
    assert "霊視や霊的な力による鑑定ではなく" in html
    assert "1鑑定 1,980円（税込）" in html


def test_terms_cover_general_themes():
    terms = CLIENT.get("/terms").text
    assert "自己理解、人間関係、仕事、これからの運気の流れ" in terms
    assert "転職、独立およびキャリア形成を主なテーマ" not in terms
    assert "改定日：</strong>2026年10月29日" in terms
    assert "← 八雲式 四柱推命鑑定" in terms
