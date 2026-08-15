"""
tests/test_reading_renderer_five_year_luck.py

reading_renderer の
future_flow.yearly / 5年運表示テスト。

目的
----
ReadingProduct に保持された future_flow.yearly を、
HTML / PDF変換前HTMLで顧客向けに読みやすく表示する。

確認項目
--------
1. future_flow.yearly の5年間がHTMLへ表示される
2. year と title を年別見出しとして表示する
3. summary / detail / advice を各年ごとに表示する
4. 2026～2030年の順序を維持する
5. yearly の顧客向け文字列をHTMLエスケープする
6. future_flow.yearly が無い旧ReadingProductも従来どおり描画できる
7. yearly が空でも壊れない
8. 不正なyearly要素を安全に無視できる
9. HTML fragmentにも5年運が表示される
10. 5年運用CSSが完全HTMLへ含まれる
11. 既存セクション表示を壊さない
12. renderer がReadingProductを変更しない

このテストでは占術計算を行わない。
Rendererの責務は、ReadingProductに存在する
計算・AI生成済みの商品データを安全に表示することだけである。
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


EXPECTED_SEQUENCE = [
    "乙丑",
    "癸未",
    "丁巳",
    "辛亥",
]


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


# ============================================================
# Helpers
# ============================================================


def _pillar(
    position,
    pillar,
    stem,
    branch,
    god,
    stage,
    hidden,
    hidden_god,
):
    return {
        "position": position,
        "pillar": pillar,
        "stem": stem,
        "branch": branch,
        "stem_ten_god": god,
        "twelve_stage": stage,
        "main_hidden_stem": hidden,
        "main_hidden_stem_ten_god": (
            hidden_god
        ),
    }


def make_yearly():
    return [
        {
            "year": 2026,
            "title": "ここから年末まで",
            "summary": (
                "足元を整えながら、"
                "次の流れへ備える期間です。"
            ),
            "detail": (
                "鑑定日時点から年末までは、"
                "優先順位を確認しながら"
                "進むことが大切です。"
            ),
            "advice": [
                (
                    "今年残りの期間は、"
                    "重要なことへ集中しましょう。"
                ),
            ],
        },
        {
            "year": 2027,
            "title": "基盤を整える年",
            "summary": (
                "今後につながる基盤を"
                "整えやすい一年です。"
            ),
            "detail": (
                "目先だけではなく、"
                "継続できる形を作る視点が"
                "役立ちます。"
            ),
            "advice": [
                (
                    "長く続けられる方法を"
                    "選んでください。"
                ),
            ],
        },
        {
            "year": 2028,
            "title": "動きが強まる年",
            "summary": (
                "整えてきたものを"
                "動かしやすい一年です。"
            ),
            "detail": (
                "状況を見極めながら、"
                "必要な場面では"
                "一歩前へ進みます。"
            ),
            "advice": [
                (
                    "機会を選びながら、"
                    "行動範囲を広げましょう。"
                ),
            ],
        },
        {
            "year": 2029,
            "title": "形にしていく年",
            "summary": (
                "積み重ねを成果へ"
                "つなげやすい一年です。"
            ),
            "detail": (
                "広げるだけではなく、"
                "重要なものを選び"
                "完成度を高めます。"
            ),
            "advice": [
                (
                    "成果として残したいものを"
                    "明確にしましょう。"
                ),
            ],
        },
        {
            "year": 2030,
            "title": "次の段階へ向かう年",
            "summary": (
                "5年間の経験を整理し、"
                "次へつなげる一年です。"
            ),
            "detail": (
                "残すものと変えるものを"
                "見極めながら、"
                "次の方向を選びます。"
            ),
            "advice": [
                (
                    "次の長期目標を"
                    "考えてみましょう。"
                ),
            ],
        },
    ]


def make_sections(
    *,
    include_yearly=True,
):
    sections = []

    for index, key in enumerate(
        DEFAULT_SECTION_ORDER,
        start=1,
    ):
        section = {
            "key": key,
            "title": SECTION_TITLES[
                key
            ],
            "summary": (
                f"{SECTION_TITLES[key]}"
                f"の要約{index}"
            ),
            "detail": (
                f"{SECTION_TITLES[key]}"
                f"の詳細本文{index}。"
                "計算済みデータを基にした"
                "鑑定です。"
            ),
            "evidence": [
                (
                    f"{SECTION_TITLES[key]}"
                    "の根拠A"
                ),
                (
                    f"{SECTION_TITLES[key]}"
                    "の根拠B"
                ),
            ],
            "advice": [
                (
                    f"{SECTION_TITLES[key]}"
                    "の助言A"
                ),
                (
                    f"{SECTION_TITLES[key]}"
                    "の助言B"
                ),
            ],
        }

        if (
            key == "future_flow"
            and include_yearly
        ):
            section[
                "yearly"
            ] = make_yearly()

        sections.append(
            section
        )

    return tuple(
        sections
    )


def make_product(
    *,
    include_yearly=True,
):
    return ReadingProduct(
        title="四柱推命鑑定書",
        subject={
            "birth_date": "1985-07-17",
            "birth_time": "21:50",
            "birth_place": "石川県",
            "gender": "female",
            "timezone": "Asia/Tokyo",
        },
        chart_summary={
            "pillar_sequence": list(
                EXPECTED_SEQUENCE
            ),
            "pillars": {
                "year": _pillar(
                    "year",
                    "乙丑",
                    "乙",
                    "丑",
                    "偏印",
                    "墓",
                    "己",
                    "食神",
                ),
                "month": _pillar(
                    "month",
                    "癸未",
                    "癸",
                    "未",
                    "偏官",
                    "冠帯",
                    "己",
                    "食神",
                ),
                "day": _pillar(
                    "day",
                    "丁巳",
                    "丁",
                    "巳",
                    "日主",
                    "帝旺",
                    "丙",
                    "劫財",
                ),
                "hour": _pillar(
                    "hour",
                    "辛亥",
                    "辛",
                    "亥",
                    "偏財",
                    "胎",
                    "壬",
                    "正官",
                ),
            },
            "day_master": {
                "stem": "丁",
                "element": "火",
                "yin_yang": "陰",
                "day_pillar": "丁巳",
            },
            "five_elements": {
                "weighted_scores": {
                    "木": 18.0,
                    "火": 23.0,
                    "土": 20.0,
                    "金": 14.0,
                    "水": 25.0,
                },
                "strongest_element": "水",
                "weakest_element": "金",
            },
            "strength": {
                "label": "中和",
                "technical_label": (
                    "balanced"
                ),
                "final_score": 50.0,
            },
            "pattern": {
                "primary_pattern": "食神格",
                "technical_pattern": (
                    "食神格"
                ),
                "overall_judgment": "成立",
            },
            "useful_gods": {
                "primary_useful_element": "金",
                "secondary_useful_elements": [
                    "水",
                    "木",
                    "土",
                ],
                "unfavorable_elements": [
                    "火",
                ],
            },
            "current_luck": {
                "ganzhi": "丁亥",
                "stem_ten_god": "比肩",
                "branch_element": "水",
                "start_age": 37,
                "end_age": 47,
            },
            "annual_luck": {
                "year": 2026,
                "ganzhi": "丙午",
                "stem_ten_god": "劫財",
                "twelve_stage": "建禄",
            },
        },
        sections=make_sections(
            include_yearly=include_yearly,
        ),
        summary=(
            "丁を中心に、"
            "自分の持ち味を活かしていく"
            "命です。"
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
                "2026-08-15T03:00:00+09:00"
            ),
            "product_version": (
                "reading_product_v1"
            ),
            "recalculates_astrology": False,
            "rewrites_ai_reading": False,
        },
    )


def future_flow_section(
    product,
):
    return next(
        section
        for section in product.sections
        if section.get(
            "key"
        )
        == "future_flow"
    )


# ============================================================
# 1. Five-year rendering
# ============================================================


def test_renderer_renders_all_five_years():
    product = make_product()

    html = render_reading_product_html(
        product
    )

    for year in (
        2026,
        2027,
        2028,
        2029,
        2030,
    ):
        assert str(
            year
        ) in html


def test_renderer_renders_all_yearly_titles():
    product = make_product()

    html = render_reading_product_html(
        product
    )

    for title in (
        "ここから年末まで",
        "基盤を整える年",
        "動きが強まる年",
        "形にしていく年",
        "次の段階へ向かう年",
    ):
        assert title in html


def test_renderer_renders_yearly_summary_detail_and_advice():
    product = make_product()

    html = render_reading_product_html(
        product
    )

    for text in (
        (
            "足元を整えながら、"
            "次の流れへ備える期間です。"
        ),
        (
            "鑑定日時点から年末までは、"
            "優先順位を確認しながら"
            "進むことが大切です。"
        ),
        (
            "今年残りの期間は、"
            "重要なことへ集中しましょう。"
        ),
        (
            "5年間の経験を整理し、"
            "次へつなげる一年です。"
        ),
        (
            "次の長期目標を"
            "考えてみましょう。"
        ),
    ):
        assert text in html


def test_renderer_preserves_year_order():
    product = make_product()

    html = render_reading_product_html(
        product
    )

    positions = [
        html.index(
            str(year)
        )
        for year in (
            2026,
            2027,
            2028,
            2029,
            2030,
        )
    ]

    assert positions == sorted(
        positions
    )


# ============================================================
# 2. Expected markup contract
# ============================================================


def test_renderer_has_yearly_flow_container():
    product = make_product()

    html = render_reading_product_html(
        product
    )

    assert (
        'class="yearly-flow"'
        in html
    )


def test_renderer_has_five_year_cards():
    product = make_product()

    html = render_reading_product_html(
        product
    )

    assert (
        html.count(
            'class="yearly-flow-item"'
        )
        == 5
    )


def test_renderer_has_year_labels():
    product = make_product()

    html = render_reading_product_html(
        product
    )

    assert (
        'class="yearly-flow-year"'
        in html
    )

    assert (
        'class="yearly-flow-title"'
        in html
    )


# ============================================================
# 3. HTML escaping
# ============================================================


def test_yearly_content_is_html_escaped():
    product = make_product()

    section = future_flow_section(
        product
    )

    section[
        "yearly"
    ][0][
        "title"
    ] = (
        '<script>alert("title")</script>'
    )

    section[
        "yearly"
    ][0][
        "detail"
    ] = (
        "<b>詳細</b>"
    )

    section[
        "yearly"
    ][0][
        "advice"
    ][0] = (
        "<i>助言</i>"
    )

    html = render_reading_product_html(
        product
    )

    assert (
        '<script>alert("title")</script>'
        not in html
    )

    assert (
        "<b>詳細</b>"
        not in html
    )

    assert (
        "<i>助言</i>"
        not in html
    )

    assert (
        "&lt;script&gt;"
        in html
    )

    assert (
        "&lt;b&gt;詳細&lt;/b&gt;"
        in html
    )

    assert (
        "&lt;i&gt;助言&lt;/i&gt;"
        in html
    )


# ============================================================
# 4. Backward compatibility
# ============================================================


def test_renderer_without_yearly_still_renders_future_flow():
    product = make_product(
        include_yearly=False
    )

    html = render_reading_product_html(
        product
    )

    assert (
        "これから5年間の運勢"
        in html
    )

    assert (
        "これから5年間の運勢の要約7"
        in html
    )

    assert (
        "これから5年間の運勢の詳細本文7"
        in html
    )


def test_empty_yearly_does_not_break_renderer():
    product = make_product()

    section = future_flow_section(
        product
    )

    section[
        "yearly"
    ] = []

    html = render_reading_product_html(
        product
    )

    assert (
        "これから5年間の運勢"
        in html
    )

    assert (
        'class="yearly-flow-item"'
        not in html
    )


def test_invalid_yearly_items_are_ignored_safely():
    product = make_product()

    section = future_flow_section(
        product
    )

    section[
        "yearly"
    ] = [
        None,
        "invalid",
        123,
        {
            "year": 2030,
            "title": (
                "有効な年別データ"
            ),
            "summary": (
                "有効な要約です。"
            ),
            "detail": (
                "有効な詳細です。"
            ),
            "advice": [
                "有効な助言です。",
            ],
        },
    ]

    html = render_reading_product_html(
        product
    )

    assert (
        "有効な年別データ"
        in html
    )

    assert (
        "有効な要約です。"
        in html
    )

    assert (
        "有効な詳細です。"
        in html
    )

    assert (
        "有効な助言です。"
        in html
    )


# ============================================================
# 5. Fragment
# ============================================================


def test_fragment_contains_five_year_flow():
    product = make_product()

    fragment = (
        render_reading_product_fragment(
            product
        )
    )

    assert (
        "2026"
        in fragment
    )

    assert (
        "2030"
        in fragment
    )

    assert (
        "ここから年末まで"
        in fragment
    )

    assert (
        "次の段階へ向かう年"
        in fragment
    )

    assert (
        'class="yearly-flow"'
        in fragment
    )


# ============================================================
# 6. CSS / print contract
# ============================================================


def test_full_html_contains_five_year_css():
    product = make_product()

    html = render_reading_product_html(
        product
    )

    for token in (
        ".yearly-flow",
        ".yearly-flow-item",
        ".yearly-flow-header",
        ".yearly-flow-year",
        ".yearly-flow-title",
        ".yearly-flow-summary",
        ".yearly-flow-detail",
        ".yearly-flow-advice",
    ):
        assert token in html


def test_five_year_css_has_print_break_protection():
    product = make_product()

    html = render_reading_product_html(
        product
    )

    assert (
        "@media print"
        in html
    )

    assert (
        ".yearly-flow-item"
        in html
    )

    assert (
        "break-inside"
        in html
    )


# ============================================================
# 7. Existing renderer compatibility
# ============================================================


def test_existing_sections_are_still_rendered():
    product = make_product()

    html = render_reading_product_html(
        product
    )

    for title in (
        "本質・性格",
        "仕事・適職",
        "金運",
        "恋愛・人間関係",
        "健康傾向",
        "現在の運勢",
        "開運アドバイス",
    ):
        assert title in html


def test_existing_evidence_and_advice_are_preserved():
    product = make_product()

    html = render_reading_product_html(
        product
    )

    assert (
        "仕事・適職の根拠A"
        in html
    )

    assert (
        "仕事・適職の助言A"
        in html
    )

    assert (
        "これから5年間の運勢の根拠A"
        in html
    )

    assert (
        "これから5年間の運勢の助言A"
        in html
    )


# ============================================================
# 8. Immutability
# ============================================================


def test_renderer_does_not_mutate_yearly():
    product = make_product()

    before = deepcopy(
        product.sections
    )

    render_reading_product_html(
        product
    )

    assert (
        product.sections
        == before
    )


def test_fragment_does_not_mutate_yearly():
    product = make_product()

    before = deepcopy(
        product.sections
    )

    render_reading_product_fragment(
        product
    )

    assert (
        product.sections
        == before
    )
