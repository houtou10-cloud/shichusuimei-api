"""鑑定結果の「八雲式の読み物」：日干のイメージと五行の数から、固定の文章を出す。"""

from datetime import datetime

from api import customer_routes
from api.models import ChartRequest
from api.yakumo_reading_note import DAY_STEM_NOTES, FEW_ELEMENT_CARE, MANY_ELEMENT_NOTE, element_counts, render_yakumo_note
from engine.chart import calculate_chart

BANNED = ("霊", "因縁", "先祖", "不幸", "必ず", "治る", "病気", "運気が上がる", "収入が増える", "本の", "基礎編", "応用編")


def _chart(time):
    return calculate_chart(ChartRequest(birth_date="1984-10-10", birth_time=time, birth_place="東京都", gender="female"), target_datetime=datetime(2026, 1, 1))


def test_three_pillar_chart_counts_six_characters():
    chart = _chart(None)  # 甲子・甲戌・丁丑
    assert element_counts(chart) == {"木": 2, "火": 1, "土": 2, "金": 0, "水": 1}
    html = render_yakumo_note(chart)
    assert "日干は丁：灯火" in html
    assert "命式の6文字を五行で数えると、木2、火1、土2、金0、水1です。" in html
    assert "少ない五行は金、多い五行は木・土です。" in html
    assert FEW_ELEMENT_CARE["金"] in html
    assert "四柱推命の判定ではなく" in html


def test_known_time_counts_eight_characters():
    assert sum(element_counts(_chart("12:00")).values()) == 8


def test_all_stems_have_notes_and_no_banned_words():
    assert set(DAY_STEM_NOTES) == set("甲乙丙丁戊己庚辛壬癸")
    texts = [v for note in DAY_STEM_NOTES.values() for v in note.values()]
    texts += list(FEW_ELEMENT_CARE.values()) + list(MANY_ELEMENT_NOTE.values())
    for text in texts:
        assert not any(word in text for word in BANNED), text


def test_missing_chart_renders_nothing():
    assert render_yakumo_note({}) == ""
    assert render_yakumo_note(None) == ""


def test_fast_result_includes_note_after_reading_cards():
    result = {"session_id": "s1", "chart": _chart(None), "sections": {"advice": "今すべきこと"}}
    html = customer_routes._render_fast_result_raw(result)
    assert html.index("今すべきこと") < html.index("八雲式の読み物")


def test_concern_answer_comes_before_note():
    result = {"session_id": "s1", "chart": _chart(None), "sections": {}, "consultation": "仕事で悩んでいます"}
    html = customer_routes._render_fast_result(result)
    assert html.index("今すべきこと") < html.index("仕事で悩んでいます") < html.index("八雲式の読み物")
