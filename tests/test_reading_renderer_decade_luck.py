"""
tests/test_reading_renderer_decade_luck.py

reading_renderer v1.1
10年ごとの大運（luck_pillars）表示テスト。

目的
----
ReadingProduct.chart_summary に保持された luck_pillars を、
占術計算をやり直さず、そのまま顧客向けHTMLへ表示する。

確認項目
--------
1. 「10年ごとの大運」見出しが表示される。
2. 全大運が表示される。
3. 大運の順序を維持する。
4. 開始年齢・終了年齢を表示する。
5. 通変星を表示する。
6. 天干五行・地支五行を表示する。
7. 順行/逆行と大運開始年齢を表示する。
8. 現在の大運を自動的に強調表示する。
9. 現在大運以外には「現在」バッジを付けない。
10. luck_pillars が無い旧商品でも壊れない。
11. pillars が空なら大運セクションを表示しない。
12. 不正なpillar要素を安全に無視する。
13. 顧客向け文字列をHTMLエスケープする。
14. HTML fragmentにも大運を表示する。
15. 完全HTMLに大運用CSSを含める。
16. 印刷時のページ分割保護CSSを含める。
17. 既存8セクションを壊さない。
18. 大運セクションは8セクションの後に表示する。
19. 免責事項は大運より後、最後に維持する。
20. rendererがReadingProductを変更しない。

このテストでは占術計算を行わない。
Rendererの責務は、ReadingProductに存在する
計算済み商品データを安全に表示することだけである。
"""

from __future__ import annotations

from copy import deepcopy

from engine.reading_product import (
    DEFAULT_SECTION_ORDER,
    ReadingProduct,
)
from engine.reading_renderer import (
    render_reading_product_fragment,
    render_reading_product_html,
)


SECTION_TITLES = {
    "core_personality": "本質・性格",
    "career": "仕事・適職",
    "wealth": "金運",
    "relationships": "恋愛・人間関係",
    "health": "健康傾向",
    "current_luck": "現在の運勢",
    "future_flow": "これから5年間の運勢",
    "advice": "開運アドバイス",
}


EXPECTED_LUCK_SEQUENCE = [
    "甲申",
    "乙酉",
    "丙戌",
    "丁亥",
    "戊子",
    "己丑",
    "庚寅",
    "辛卯",
]


def make_sections():
    return tuple(
        {
            "key": key,
            "title": SECTION_TITLES[key],
            "summary": (
                f"{SECTION_TITLES[key]}の要約"
            ),
            "detail": (
                f"{SECTION_TITLES[key]}の詳細本文"
            ),
            "evidence": [
                f"{SECTION_TITLES[key]}の根拠A",
            ],
            "advice": [
                f"{SECTION_TITLES[key]}の助言A",
            ],
        }
        for key in DEFAULT_SECTION_ORDER
    )


def make_luck_pillars():
    return {
        "direction": "forward",
        "direction_japanese": "順行",
        "start_age": 7.0,
        "start_age_detail": {
            "years": 7,
            "months": 0,
            "days": 0,
        },
        "pillar_count": 8,
        "pillars": [
            {
                "index": 1,
                "ganzhi": "甲申",
                "stem": "甲",
                "branch": "申",
                "stem_element": "木",
                "branch_element": "金",
                "stem_ten_god": "正印",
                "start_age": 7.0,
                "end_age": 17.0,
                "stem_useful_relation": {
                    "relation": "supportive",
                },
                "branch_useful_relation": {
                    "relation": "primary_useful",
                },
            },
            {
                "index": 2,
                "ganzhi": "乙酉",
                "stem": "乙",
                "branch": "酉",
                "stem_element": "木",
                "branch_element": "金",
                "stem_ten_god": "偏印",
                "start_age": 17.0,
                "end_age": 27.0,
                "stem_useful_relation": {
                    "relation": "supportive",
                },
                "branch_useful_relation": {
                    "relation": "primary_useful",
                },
            },
            {
                "index": 3,
                "ganzhi": "丙戌",
                "stem": "丙",
                "branch": "戌",
                "stem_element": "火",
                "branch_element": "土",
                "stem_ten_god": "劫財",
                "start_age": 27.0,
                "end_age": 37.0,
                "stem_useful_relation": {
                    "relation": "unfavorable",
                },
                "branch_useful_relation": {
                    "relation": "supportive",
                },
            },
            {
                "index": 4,
                "ganzhi": "丁亥",
                "stem": "丁",
                "branch": "亥",
                "stem_element": "火",
                "branch_element": "水",
                "stem_ten_god": "比肩",
                "start_age": 37.0,
                "end_age": 47.0,
                "stem_useful_relation": {
                    "relation": "unfavorable",
                },
                "branch_useful_relation": {
                    "relation": "supportive",
                },
            },
            {
                "index": 5,
                "ganzhi": "戊子",
                "stem": "戊",
                "branch": "子",
                "stem_element": "土",
                "branch_element": "水",
                "stem_ten_god": "傷官",
                "start_age": 47.0,
                "end_age": 57.0,
                "stem_useful_relation": {
                    "relation": "supportive",
                },
                "branch_useful_relation": {
                    "relation": "supportive",
                },
            },
            {
                "index": 6,
                "ganzhi": "己丑",
                "stem": "己",
                "branch": "丑",
                "stem_element": "土",
                "branch_element": "土",
                "stem_ten_god": "食神",
                "start_age": 57.0,
                "end_age": 67.0,
                "stem_useful_relation": {
                    "relation": "supportive",
                },
                "branch_useful_relation": {
                    "relation": "supportive",
                },
            },
            {
                "index": 7,
                "ganzhi": "庚寅",
                "stem": "庚",
                "branch": "寅",
                "stem_element": "金",
                "branch_element": "木",
                "stem_ten_god": "正財",
                "start_age": 67.0,
                "end_age": 77.0,
                "stem_useful_relation": {
                    "relation": "primary_useful",
                },
                "branch_useful_relation": {
                    "relation": "supportive",
                },
            },
            {
                "index": 8,
                "ganzhi": "辛卯",
                "stem": "辛",
                "branch": "卯",
                "stem_element": "金",
                "branch_element": "木",
                "stem_ten_god": "偏財",
                "start_age": 77.0,
                "end_age": 87.0,
                "stem_useful_relation": {
                    "relation": "primary_useful",
                },
                "branch_useful_relation": {
                    "relation": "supportive",
                },
            },
        ],
    }


def make_product(
    *,
    include_luck_pillars=True,
):
    chart_summary = {
        "pillars": {
            "year": {
                "position": "year",
                "pillar": "乙丑",
                "stem": "乙",
                "branch": "丑",
                "stem_ten_god": "偏印",
                "twelve_stage": "墓",
                "main_hidden_stem": "己",
                "main_hidden_stem_ten_god": "食神",
            },
            "month": {
                "position": "month",
                "pillar": "癸未",
                "stem": "癸",
                "branch": "未",
                "stem_ten_god": "偏官",
                "twelve_stage": "冠帯",
                "main_hidden_stem": "己",
                "main_hidden_stem_ten_god": "食神",
            },
            "day": {
                "position": "day",
                "pillar": "丁巳",
                "stem": "丁",
                "branch": "巳",
                "stem_ten_god": None,
                "twelve_stage": "帝旺",
                "main_hidden_stem": "丙",
                "main_hidden_stem_ten_god": "劫財",
            },
            "hour": {
                "position": "hour",
                "pillar": "辛亥",
                "stem": "辛",
                "branch": "亥",
                "stem_ten_god": "偏財",
                "twelve_stage": "胎",
                "main_hidden_stem": "壬",
                "main_hidden_stem_ten_god": "正官",
            },
        },
        "pillar_sequence": [
            "乙丑",
            "癸未",
            "丁巳",
            "辛亥",
        ],
        "day_master": {
            "stem": "丁",
            "element": "火",
            "yin_yang": "陰",
            "day_pillar": "丁巳",
        },
        "five_elements": {
            "weighted_scores": {
                "木": 18.5,
                "火": 24.0,
                "土": 22.5,
                "金": 12.0,
                "水": 31.0,
            },
            "strongest_element": "水",
            "weakest_element": "金",
        },
        "strength": {
            "technical_label": "balanced",
            "label": "中和",
            "final_score": 50.0,
            "confidence": "high",
        },
        "pattern": {
            "primary_pattern": "食神格",
            "technical_pattern": "shokujin",
            "overall_judgment": "established",
            "confidence": "medium",
        },
        "useful_gods": {
            "primary_useful_element": "金",
            "secondary_useful_elements": [
                "水",
                "木",
                "土",
            ],
            "final_useful_elements": [
                "金",
                "水",
                "木",
                "土",
            ],
            "unfavorable_elements": [
                "火",
            ],
            "confidence": "medium",
        },
        "current_luck": {
            "ganzhi": "丁亥",
            "stem_ten_god": "比肩",
            "start_age": 37.0,
            "end_age": 47.0,
        },
        "annual_luck": {
            "year": 2026,
            "ganzhi": "丙午",
            "stem_ten_god": "劫財",
            "twelve_stage": "建禄",
        },
    }

    if include_luck_pillars:
        chart_summary[
            "luck_pillars"
        ] = make_luck_pillars()

    return ReadingProduct(
        title="四柱推命鑑定書",
        subject={
            "name": "テスト太郎",
            "birth_date": "1985-07-17",
            "birth_time": "21:50",
            "birth_place": "石川県",
            "gender": "female",
            "timezone": "Asia/Tokyo",
        },
        chart_summary=chart_summary,
        sections=make_sections(),
        summary=(
            "命式全体を踏まえた"
            "総合鑑定です。"
        ),
        disclaimer=(
            "本鑑定は将来を断定または"
            "保証するものではありません。"
        ),
        generation={
            "model": "test-model",
            "response_id": "resp_test",
            "response_status": "completed",
            "usage": {},
            "sections": list(
                DEFAULT_SECTION_ORDER
            ),
            "method": (
                "openai_responses_api_v1"
            ),
            "status": "completed",
        },
        metadata={
            "created_at": (
                "2026-08-16T08:00:00+09:00"
            ),
            "product_version": (
                "reading_product_v1"
            ),
            "recalculates_astrology": False,
            "rewrites_ai_reading": False,
            "brand_name": "四柱推命 八雲",
        },
    )


# ============================================================
# 1. Basic rendering
# ============================================================


def test_renderer_has_decade_luck_heading():
    product = make_product()

    html = render_reading_product_html(
        product
    )

    assert (
        "10年ごとの大運"
        in html
    )


def test_renderer_has_decade_luck_container():
    product = make_product()

    html = render_reading_product_html(
        product
    )

    assert (
        'class="reading-card decade-luck-card"'
        in html
    )

    assert (
        'id="decade-luck-heading"'
        in html
    )


def test_renderer_renders_all_luck_pillars():
    product = make_product()

    html = render_reading_product_html(
        product
    )

    for ganzhi in EXPECTED_LUCK_SEQUENCE:
        assert ganzhi in html


def test_renderer_preserves_luck_pillar_order():
    product = make_product()

    html = render_reading_product_html(
        product
    )

    decade_start = html.index(
        '<section\n'
        '    class="reading-card decade-luck-card"'
    )

    decade_end = html.index(
        "</section>",
        decade_start,
    )

    decade_html = html[
        decade_start:
        decade_end
    ]

    positions = [
        decade_html.index(
            ganzhi
        )
        for ganzhi
        in EXPECTED_LUCK_SEQUENCE
    ]

    assert (
        positions
        == sorted(
            positions
        )
    )


# ============================================================
# 2. Displayed values
# ============================================================


def test_renderer_renders_age_ranges():
    product = make_product()

    html = render_reading_product_html(
        product
    )

    for start_age, end_age in (
        (7, 17),
        (17, 27),
        (27, 37),
        (37, 47),
        (47, 57),
        (57, 67),
        (67, 77),
        (77, 87),
    ):
        assert (
            f"約{start_age}歳"
            "〜"
            f"約{end_age}歳"
            in html
        )


def test_renderer_renders_ten_gods():
    product = make_product()

    html = render_reading_product_html(
        product
    )

    for ten_god in (
        "正印",
        "偏印",
        "劫財",
        "比肩",
        "傷官",
        "食神",
        "正財",
        "偏財",
    ):
        assert ten_god in html


def test_renderer_renders_elements():
    product = make_product()

    html = render_reading_product_html(
        product
    )

    for element_pair in (
        "木・金",
        "火・土",
        "火・水",
        "土・水",
        "土・土",
        "金・木",
    ):
        assert element_pair in html


def test_renderer_renders_direction_and_start_age():
    product = make_product()

    html = render_reading_product_html(
        product
    )

    assert "順行" in html

    assert "大運開始" in html

    assert "約7歳" in html


# ============================================================
# 3. Current luck highlighting
# ============================================================


def test_renderer_marks_current_luck():
    product = make_product()

    html = render_reading_product_html(
        product
    )

    assert (
        'class="decade-luck-current"'
        in html
    )

    assert (
        'class="decade-current-badge"'
        in html
    )

    assert "現在" in html


def test_renderer_marks_only_one_current_luck():
    product = make_product()

    html = render_reading_product_html(
        product
    )

    assert (
        html.count(
            'class="decade-luck-current"'
        )
        == 1
    )

    assert (
        html.count(
            'class="decade-current-badge"'
        )
        == 1
    )


def test_current_badge_is_attached_to_current_ganzhi():
    product = make_product()

    html = render_reading_product_html(
        product
    )

    current_position = html.index(
        "丁亥",
        html.index(
            "10年ごとの大運"
        ),
    )

    badge_position = html.index(
        'class="decade-current-badge"',
        current_position,
    )

    next_position = html.index(
        "戊子",
        current_position,
    )

    assert (
        current_position
        < badge_position
        < next_position
    )


# ============================================================
# 4. Missing / invalid data compatibility
# ============================================================


def test_missing_luck_pillars_is_safe():
    product = make_product(
        include_luck_pillars=False
    )

    html = render_reading_product_html(
        product
    )

    assert (
        'id="decade-luck-heading"'
        not in html
    )

    assert (
        'class="reading-card decade-luck-card"'
        not in html
    )

    assert (
        "本質・性格"
        in html
    )

    assert (
        "免責・注意事項"
        in html
    )


def test_empty_luck_pillars_is_safe():
    product = make_product()

    product.chart_summary[
        "luck_pillars"
    ][
        "pillars"
    ] = []

    html = render_reading_product_html(
        product
    )

    assert (
        'id="decade-luck-heading"'
        not in html
    )

    assert (
        'class="reading-card decade-luck-card"'
        not in html
    )


def test_invalid_luck_pillar_items_are_ignored():
    product = make_product()

    product.chart_summary[
        "luck_pillars"
    ][
        "pillars"
    ] = [
        None,
        "invalid",
        123,
        {
            "index": 1,
            "ganzhi": "有効な大運",
            "stem_element": "木",
            "branch_element": "金",
            "stem_ten_god": "正印",
            "start_age": 7,
            "end_age": 17,
        },
    ]

    html = render_reading_product_html(
        product
    )

    assert (
        "有効な大運"
        in html
    )

    assert (
        "10年ごとの大運"
        in html
    )


# ============================================================
# 5. HTML escaping
# ============================================================


def test_decade_luck_content_is_html_escaped():
    product = make_product()

    first = product.chart_summary[
        "luck_pillars"
    ][
        "pillars"
    ][0]

    first[
        "ganzhi"
    ] = (
        '<script>alert("luck")</script>'
    )

    first[
        "stem_ten_god"
    ] = "<b>正印</b>"

    first[
        "stem_element"
    ] = "<i>木</i>"

    html = render_reading_product_html(
        product
    )

    assert (
        '<script>alert("luck")</script>'
        not in html
    )

    assert (
        "<b>正印</b>"
        not in html
    )

    assert (
        "<i>木</i>"
        not in html
    )

    assert "&lt;script&gt;" in html

    assert (
        "&lt;b&gt;正印&lt;/b&gt;"
        in html
    )

    assert (
        "&lt;i&gt;木&lt;/i&gt;"
        in html
    )


# ============================================================
# 6. Fragment / CSS
# ============================================================


def test_fragment_contains_decade_luck():
    product = make_product()

    fragment = (
        render_reading_product_fragment(
            product
        )
    )

    assert (
        "10年ごとの大運"
        in fragment
    )

    assert "丁亥" in fragment

    assert (
        'class="decade-current-badge"'
        in fragment
    )


def test_full_html_contains_decade_luck_css():
    product = make_product()

    html = render_reading_product_html(
        product
    )

    for token in (
        ".decade-luck-card",
        ".decade-luck-meta",
        ".decade-luck-table",
        ".decade-luck-current",
        ".decade-current-badge",
        ".decade-luck-note",
    ):
        assert token in html


def test_decade_luck_css_has_print_protection():
    product = make_product()

    html = render_reading_product_html(
        product
    )

    assert "@media print" in html

    assert (
        ".decade-luck-card"
        in html
    )

    assert (
        "page-break-inside: auto"
        in html
    )

    assert (
        ".decade-luck-table tr"
        in html
    )

    assert (
        "page-break-inside: avoid"
        in html
    )

    assert (
        "display: table-header-group"
        in html
    )


# ============================================================
# 7. Existing renderer compatibility / order
# ============================================================


def test_existing_sections_are_still_rendered():
    product = make_product()

    html = render_reading_product_html(
        product
    )

    for title in SECTION_TITLES.values():
        assert title in html


def test_decade_luck_is_after_eight_sections():
    product = make_product()

    html = render_reading_product_html(
        product
    )

    advice_position = html.rindex(
        '<h2 id="section-8">'
    )

    decade_position = html.index(
        'id="decade-luck-heading"'
    )

    assert (
        advice_position
        < decade_position
    )


def test_disclaimer_remains_after_decade_luck():
    product = make_product()

    html = render_reading_product_html(
        product
    )

    decade_position = html.index(
        'id="decade-luck-heading"'
    )

    disclaimer_position = html.index(
        'id="disclaimer-heading"'
    )

    assert (
        decade_position
        < disclaimer_position
    )


def test_fragment_disclaimer_remains_after_decade_luck():
    product = make_product()

    fragment = (
        render_reading_product_fragment(
            product
        )
    )

    decade_position = fragment.index(
        'id="decade-luck-heading"'
    )

    disclaimer_position = fragment.index(
        'id="disclaimer-heading"'
    )

    assert (
        decade_position
        < disclaimer_position
    )


# ============================================================
# 8. Immutability
# ============================================================


def test_renderer_does_not_mutate_luck_pillars():
    product = make_product()

    before = deepcopy(
        product.chart_summary[
            "luck_pillars"
        ]
    )

    render_reading_product_html(
        product
    )

    assert (
        product.chart_summary[
            "luck_pillars"
        ]
        == before
    )


def test_fragment_does_not_mutate_luck_pillars():
    product = make_product()

    before = deepcopy(
        product.chart_summary[
            "luck_pillars"
        ]
    )

    render_reading_product_fragment(
        product
    )

    assert (
        product.chart_summary[
            "luck_pillars"
        ]
        == before
    )


# ============================================================
# 9. Final gate
# ============================================================


def test_reading_renderer_decade_luck_v1_1_final_gate():
    product = make_product()

    html = render_reading_product_html(
        product
    )

    fragment = (
        render_reading_product_fragment(
            product
        )
    )

    assert (
        "10年ごとの大運"
        in html
    )

    for ganzhi in EXPECTED_LUCK_SEQUENCE:
        assert ganzhi in html

    assert "順行" in html
    assert "約7歳" in html

    assert (
        html.count(
            'class="decade-luck-current"'
        )
        == 1
    )

    assert (
        html.count(
            'class="decade-current-badge"'
        )
        == 1
    )

    assert (
        "丁亥"
        in html
    )

    assert (
        "10年ごとの大運"
        in fragment
    )

    for title in SECTION_TITLES.values():
        assert title in html

    assert (
        html.rindex(
            '<h2 id="section-8">'
        )
        < html.index(
            'id="decade-luck-heading"'
        )
        < html.index(
            'id="disclaimer-heading"'
        )
    )

    assert (
        fragment.index(
            'id="decade-luck-heading"'
        )
        < fragment.index(
            'id="disclaimer-heading"'
        )
    )

    assert (
        ".decade-luck-card"
        in html
    )

    assert "@media print" in html

    assert (
        "display: table-header-group"
        in html
    )
