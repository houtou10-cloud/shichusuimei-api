"""無料の日干診断（/nikkan）。"""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from api import day_stem_check
from main import app

CLIENT = TestClient(app)


def test_form_page_is_free_and_noindex_before_live():
    page = CLIENT.get("/nikkan?src=yt_013").text
    assert "あなたの日干を、無料で調べる" in page
    assert 'name="src" value="yt_013"' in page
    assert "noindex,nofollow" in page
    assert "0120-279-338" in page


@pytest.mark.parametrize(("birth", "stem", "image"), [("1985-10-13", "乙", "草花"), ("1984-10-10", "丁", "灯火"), ("1977-06-10", "戊", "山")])
def test_result_shows_day_stem_note(birth, stem, image):
    page = CLIENT.post("/nikkan", data={"birth_date": birth}).text
    assert f"あなたの日干は「{stem}」<br>{image}のイメージ" in page
    assert day_stem_check.DAY_STEM_NOTES[stem]["question"] in page
    assert "四柱推命の判定ではありません" in page
    assert 'href="/career-reading"' in page


def test_src_is_carried_to_paid_links_and_sanitized():
    page = CLIENT.post("/nikkan", data={"birth_date": "1985-10-13", "src": "yt_013\"><script>"}).text
    assert 'href="/career-reading?src=yt_013script"' in page
    assert "<script>" not in page


@pytest.mark.parametrize("value", ["", "abc", "1899-12-31", "2999-01-01"])
def test_invalid_dates_are_rejected(value):
    response = CLIENT.post("/nikkan", data={"birth_date": value})
    assert response.status_code == 422
    assert 'class="error"' in response.text


def test_parse_birth_date_accepts_today():
    assert day_stem_check.parse_birth_date("2026-10-30", today=date(2026, 10, 30)) == date(2026, 10, 30)


BANNED = ("霊", "因縁", "先祖", "不幸", "必ず", "治る", "病気", "運気が上がる", "収入が増える", "死", "本の", "基礎編", "応用編")


def test_every_stem_has_a_note_for_each_concern_without_banned_words():
    assert set(day_stem_check.CONCERN_NOTES) == set("甲乙丙丁戊己庚辛壬癸")
    for notes in day_stem_check.CONCERN_NOTES.values():
        assert set(notes) == {"work", "relation", "love", "self"}
        for text in notes.values():
            assert not any(word in text for word in BANNED), text


def test_form_offers_optional_concern_choices():
    page = CLIENT.get("/nikkan").text
    for label in day_stem_check.CONCERNS.values():
        assert label in page
    assert "選ばなくても調べられます" in page


def test_concern_note_is_shown_with_paid_link():
    page = CLIENT.post("/nikkan", data={"birth_date": "1985-10-13", "concern": "relation"}).text
    assert "「人間関係」に悩むとき" in page
    assert day_stem_check.CONCERN_NOTES["乙"]["relation"] in page
    assert 'href="/career-reading"' in page


def test_hard_concern_shows_support_first_and_no_sales_links():
    page = CLIENT.post("/nikkan", data={"birth_date": "1985-10-13", "concern": "hard", "src": "yt_013"}).text
    assert page.index("ひとりで抱えないでください") < page.index("あなたの日干は")
    assert 'href="tel:0120279338"' in page
    assert "/career-reading" not in page and "/academy" not in page


def test_unknown_concern_is_ignored():
    page = CLIENT.post("/nikkan", data={"birth_date": "1985-10-13", "concern": "<x>"}).text
    assert "に悩むとき" not in page
    assert 'href="/career-reading"' in page


def test_only_the_concern_type_is_logged(caplog):
    caplog.set_level("INFO", logger="api.day_stem_check")
    CLIENT.post("/nikkan", data={"birth_date": "1985-10-13", "concern": "work"})
    CLIENT.post("/nikkan", data={"birth_date": "1985-10-13"})
    messages = [r.getMessage() for r in caplog.records if r.name == "api.day_stem_check"]
    assert messages == ["free_day_stem_check concern=work", "free_day_stem_check concern=none"]
    assert not any("1985" in m for m in messages)


def test_privacy_policy_mentions_free_check():
    page = CLIENT.get("/privacy").text
    assert "無料の日干診断では、入力した生年月日を日干の計算にだけ使い、保存しません。" in page


def test_nikkan_is_listed_for_search_when_live(monkeypatch):
    monkeypatch.setattr("api.customer_routes.checkout_mode", lambda: "live")
    monkeypatch.setenv("CUSTOMER_PUBLIC_BASE_URL", "https://app.yakumoshiki.jp")
    assert "Allow: /nikkan" in CLIENT.get("/robots.txt").text
    assert "<loc>https://app.yakumoshiki.jp/nikkan</loc>" in CLIENT.get("/sitemap.xml").text
    assert "index,follow" in CLIENT.get("/nikkan").text
