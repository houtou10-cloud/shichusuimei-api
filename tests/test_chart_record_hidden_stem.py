"""鑑定カルテの蔵干・蔵干通変星は、本どおり（基礎編p.50〜52）の主蔵干を1つだけ出す。"""

from api import customer_routes


def _result():
    card = {
        "year": {"stem": "甲", "branch": "子", "hidden_stems": ["壬", "癸"], "hidden_stem_ten_gods": ["印綬", "偏印"]},
        "month": {"stem": "辛", "branch": "未", "hidden_stems": ["丁", "乙", "己"], "hidden_stem_ten_gods": ["食神", "比肩", "偏財"]},
        "day": {"stem": "乙", "branch": "巳", "hidden_stems": ["戊", "庚", "丙"], "hidden_stem_ten_gods": ["正財", "正官", "傷官"]},
        "hour": {"stem": "丁", "branch": "亥", "hidden_stems": [], "hidden_stem_ten_gods": None},
    }
    return {"chart": {}, "chart_card": card, "luck_pillars": [], "annual_luck_15": []}


def test_chart_record_shows_only_the_main_hidden_stem():
    html = customer_routes._render_fast_chart(_result())
    for main in ("<td>壬</td>", "<td>丁</td>", "<td>戊</td>", "<td>印綬</td>", "<td>食神</td>", "<td>正財</td>"):
        assert main in html
    assert " / " not in html.split("鑑定カルテ", 1)[1].split("</table>", 1)[0]
    assert "癸" not in html and "偏印" not in html


def test_empty_hidden_stems_show_dash():
    html = customer_routes._render_fast_chart(_result())
    assert html.count("<td>―</td>") >= 2
