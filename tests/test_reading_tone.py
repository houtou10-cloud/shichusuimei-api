"""八雲式 四柱推命鑑定：AIの鑑定文に、不安をあおらない文体の指示を必ず渡す。"""

from api import fast_reading
from api.customer_routes import _render_fast_result_raw
from api.fast_reading import DETAIL_TYPES, FAST_SECTIONS, READING_TONE_INSTRUCTIONS


def test_tone_instructions_cover_the_red_lines():
    for text in ("不安をあおる表現", "霊・因縁・先祖・前世・波動", "結果を言い切らない", "たとえとして控えめに", "転職や独立に限らず"):
        assert text in READING_TONE_INSTRUCTIONS


def test_all_provider_calls_receive_tone_instructions(monkeypatch):
    source = fast_reading.__loader__.get_source(fast_reading.__name__)
    assert source.count("+ READING_TONE_INSTRUCTIONS") == 3


def test_career_label_is_role_not_career():
    assert dict(FAST_SECTIONS)["career"] == "仕事と役割"
    assert DETAIL_TYPES["career"] == "仕事と役割"
    html = _render_fast_result_raw({"session_id": "s", "chart": {}, "sections": {}})
    assert "<h2>仕事と役割</h2>" in html and "仕事・適職" not in html
