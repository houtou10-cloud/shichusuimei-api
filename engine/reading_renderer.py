"""
engine/reading_renderer.py

四柱推命 鑑定 HTMLレンダリングレイヤー v1

目的
----
ReadingProduct
    ↓
reading_renderer_v1
    ↓
商品用HTML

このモジュールは、

- 命式を再計算しない
- AI鑑定文を書き換えない
- ReadingProduct の内容だけを表示する
- HTMLエスケープを行う
- APIキーや内部生成情報を表示しない
- Web表示とA4印刷の両方に対応する

Version
-------
reading_renderer_v1
"""

from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence, Union

from engine.reading_product import (
    ReadingProduct,
)


READING_RENDERER_VERSION = (
    "reading_renderer_v1"
)

READING_RENDERER_METHOD = (
    "reading_renderer_v1"
)

READING_RENDERER_STATUS = "ready"


PILLAR_TITLES = {
    "year": "年柱",
    "month": "月柱",
    "day": "日柱",
    "hour": "時柱",
}


GENDER_LABELS = {
    "male": "男性",
    "female": "女性",
    "other": "その他",
}


ELEMENT_ORDER = (
    "木",
    "火",
    "土",
    "金",
    "水",
)


# 表示専用フォールバック。
#
# ReadingProduct.day_master に element / yin_yang が存在する場合は
# 必ずその計算済み値を優先する。
#
# 欠損時のみ、日主天干の固定属性を表示補完する。
# 命式・格局・用神・運勢などの再計算は行わない。
STEM_DISPLAY_METADATA = {
    "甲": {
        "element": "木",
        "yin_yang": "陽",
    },
    "乙": {
        "element": "木",
        "yin_yang": "陰",
    },
    "丙": {
        "element": "火",
        "yin_yang": "陽",
    },
    "丁": {
        "element": "火",
        "yin_yang": "陰",
    },
    "戊": {
        "element": "土",
        "yin_yang": "陽",
    },
    "己": {
        "element": "土",
        "yin_yang": "陰",
    },
    "庚": {
        "element": "金",
        "yin_yang": "陽",
    },
    "辛": {
        "element": "金",
        "yin_yang": "陰",
    },
    "壬": {
        "element": "水",
        "yin_yang": "陽",
    },
    "癸": {
        "element": "水",
        "yin_yang": "陰",
    },
}


class ReadingRendererError(
    Exception
):
    """reading_renderer.py の基底例外。"""


class ReadingRendererValidationError(
    ReadingRendererError
):
    """レンダリング対象データが不正。"""


def _require_product(
    product: Any,
) -> ReadingProduct:
    if not isinstance(
        product,
        ReadingProduct,
    ):
        raise TypeError(
            "productはReadingProductで"
            "指定してください。"
        )

    return product


def _safe_mapping(
    value: Any,
) -> Mapping[str, Any]:
    if isinstance(
        value,
        Mapping,
    ):
        return value

    return {}


def _safe_sequence(
    value: Any,
) -> Sequence[Any]:
    if isinstance(
        value,
        (list, tuple),
    ):
        return value

    return ()


def _text(
    value: Any,
) -> str:
    if value is None:
        return ""

    return str(value).strip()


def _html(
    value: Any,
) -> str:
    return escape(
        _text(value),
        quote=True,
    )


def _display(
    value: Any,
    *,
    empty: str = "―",
) -> str:
    text = _text(value)

    if not text:
        return empty

    return text


def _display_html(
    value: Any,
    *,
    empty: str = "―",
) -> str:
    return _html(
        _display(
            value,
            empty=empty,
        )
    )


def _format_japanese_date(
    value: Any,
) -> str:
    """ISO日時または日付を「YYYY年M月D日」へ整形する。"""
    text = _text(
        value
    )

    if not text:
        return ""

    normalized = text.replace(
        "Z",
        "+00:00",
    )

    try:
        parsed = datetime.fromisoformat(
            normalized
        )
    except ValueError:
        try:
            parsed = datetime.strptime(
                text[:10],
                "%Y-%m-%d",
            )
        except ValueError:
            return text

    return (
        f"{parsed.year}年"
        f"{parsed.month}月"
        f"{parsed.day}日"
    )


def _day_master_display_value(
    day_master: Mapping[
        str,
        Any,
    ],
    key: str,
) -> str:
    """
    日主カード用の表示値を返す。

    ReadingProduct側に値がある場合は、
    その計算済み値をそのまま使用する。

    element / yin_yang が欠損している場合だけ、
    日主天干の固定属性を表示補完する。

    占術ロジックの再計算は行わない。
    """

    existing = _text(
        day_master.get(
            key
        )
    )

    if existing:
        return existing

    stem = _text(
        day_master.get(
            "stem"
        )
    )

    metadata = (
        STEM_DISPLAY_METADATA.get(
            stem,
            {},
        )
    )

    return _text(
        metadata.get(
            key
        )
    )


def _display_age(
    value: Any,
    *,
    empty: str = "―",
) -> str:
    """
    大運の開始・終了年齢を商品向けに表示する。

    内部の小数年齢は変更しない。
    HTML上の表示だけを最寄りの整数へ丸める。

    例:
        34.955068 -> 約35歳
        45.740251 -> 約46歳
    """

    text = _text(
        value
    )

    if not text:
        return empty

    if isinstance(
        value,
        bool,
    ):
        return text

    try:
        number = float(
            text
        )
    except (
        TypeError,
        ValueError,
    ):
        return text

    if (
        number != number
        or number
        in (
            float("inf"),
            float("-inf"),
        )
    ):
        return text

    if number >= 0:
        rounded = int(
            number + 0.5
        )
    else:
        rounded = int(
            number - 0.5
        )

    return (
        f"約{rounded}歳"
    )


def _display_age_html(
    value: Any,
    *,
    empty: str = "―",
) -> str:
    return _html(
        _display_age(
            value,
            empty=empty,
        )
    )


def _paragraphs(
    value: Any,
) -> str:
    """
    プレーンテキストを安全なHTML段落へ変換する。

    AI鑑定本文そのものは変更しない。
    改行単位で段落化するだけ。
    """

    text = _text(value)

    if not text:
        return ""

    blocks = [
        block.strip()
        for block
        in text.split("\n")
        if block.strip()
    ]

    return "\n".join(
        (
            '<p class="reading-paragraph">'
            f"{_html(block)}"
            "</p>"
        )
        for block
        in blocks
    )


def _render_list(
    values: Any,
    *,
    css_class: str,
) -> str:
    items = [
        _text(item)
        for item
        in _safe_sequence(values)
        if _text(item)
    ]

    if not items:
        return ""

    body = "\n".join(
        (
            "<li>"
            f"{_html(item)}"
            "</li>"
        )
        for item
        in items
    )

    return (
        f'<ul class="{_html(css_class)}">\n'
        f"{body}\n"
        "</ul>"
    )


def _gender_label(
    value: Any,
) -> str:
    raw = _text(value)

    if not raw:
        return "―"

    return GENDER_LABELS.get(
        raw.lower(),
        raw,
    )


def _render_subject(
    product: ReadingProduct,
) -> str:
    subject = _safe_mapping(
        product.subject
    )

    birth_date = _display_html(
        subject.get(
            "birth_date"
        )
    )

    birth_time = _display_html(
        subject.get(
            "birth_time"
        )
    )

    birth_place = _display_html(
        subject.get(
            "birth_place"
        )
    )

    gender = _html(
        _gender_label(
            subject.get(
                "gender"
            )
        )
    )

    timezone = _text(
        subject.get(
            "timezone"
        )
    )

    timezone_row = ""

    if timezone:
        timezone_row = f"""
        <div class="info-item">
            <span class="info-label">
                タイムゾーン
            </span>
            <span class="info-value">
                {_html(timezone)}
            </span>
        </div>
        """

    return f"""
<section
    class="reading-card subject-card"
    aria-labelledby="subject-heading"
>
    <h2 id="subject-heading">
        基本情報
    </h2>

    <div class="info-grid">
        <div class="info-item">
            <span class="info-label">
                生年月日
            </span>
            <span class="info-value">
                {birth_date}
            </span>
        </div>

        <div class="info-item">
            <span class="info-label">
                出生時刻
            </span>
            <span class="info-value">
                {birth_time}
            </span>
        </div>

        <div class="info-item">
            <span class="info-label">
                出生地
            </span>
            <span class="info-value">
                {birth_place}
            </span>
        </div>

        <div class="info-item">
            <span class="info-label">
                性別
            </span>
            <span class="info-value">
                {gender}
            </span>
        </div>

        {timezone_row}
    </div>
</section>
"""


def _render_pillars(
    chart_summary: Mapping[
        str,
        Any,
    ],
) -> str:
    pillars = _safe_mapping(
        chart_summary.get(
            "pillars"
        )
    )

    cells = []

    for position in (
        "year",
        "month",
        "day",
        "hour",
    ):
        pillar = _safe_mapping(
            pillars.get(
                position
            )
        )

        cells.append(
            f"""
            <div class="pillar-card">
                <div class="pillar-title">
                    {_html(
                        PILLAR_TITLES[
                            position
                        ]
                    )}
                </div>

                <div class="pillar-ganzhi">
                    {_display_html(
                        pillar.get(
                            "pillar"
                        )
                    )}
                </div>

                <dl class="pillar-details">
                    <div>
                        <dt>天干</dt>
                        <dd>
                            {_display_html(
                                pillar.get(
                                    "stem"
                                )
                            )}
                        </dd>
                    </div>

                    <div>
                        <dt>地支</dt>
                        <dd>
                            {_display_html(
                                pillar.get(
                                    "branch"
                                )
                            )}
                        </dd>
                    </div>

                    <div>
                        <dt>通変星</dt>
                        <dd>
                            {_display_html(
                                pillar.get(
                                    "stem_ten_god"
                                )
                            )}
                        </dd>
                    </div>

                    <div>
                        <dt>十二運</dt>
                        <dd>
                            {_display_html(
                                pillar.get(
                                    "twelve_stage"
                                )
                            )}
                        </dd>
                    </div>

                    <div>
                        <dt>蔵干</dt>
                        <dd>
                            {_display_html(
                                pillar.get(
                                    "main_hidden_stem"
                                )
                            )}
                        </dd>
                    </div>

                    <div>
                        <dt>蔵干通変星</dt>
                        <dd>
                            {_display_html(
                                pillar.get(
                                    "main_hidden_stem_ten_god"
                                )
                            )}
                        </dd>
                    </div>
                </dl>
            </div>
            """
        )

    return (
        '<div class="pillar-grid">'
        + "\n".join(cells)
        + "</div>"
    )


def _render_five_elements(
    chart_summary: Mapping[
        str,
        Any,
    ],
) -> str:
    five_elements = _safe_mapping(
        chart_summary.get(
            "five_elements"
        )
    )

    scores = _safe_mapping(
        five_elements.get(
            "weighted_scores"
        )
    )

    if not scores:
        return ""

    ordered_keys = [
        element
        for element
        in ELEMENT_ORDER
        if element in scores
    ]

    ordered_keys.extend(
        key
        for key
        in scores.keys()
        if key not in ordered_keys
    )

    rows = []

    for element in ordered_keys:
        rows.append(
            f"""
            <tr>
                <th scope="row">
                    {_html(element)}
                </th>
                <td>
                    {_display_html(
                        scores.get(
                            element
                        )
                    )}
                </td>
            </tr>
            """
        )

    strongest = _display_html(
        five_elements.get(
            "strongest_element"
        )
    )

    weakest = _display_html(
        five_elements.get(
            "weakest_element"
        )
    )

    return f"""
<div class="sub-card">
    <h3>五行バランス</h3>

    <table class="data-table">
        <tbody>
            {''.join(rows)}
        </tbody>
    </table>

    <div class="mini-summary">
        <span>
            <strong>最も強い五行：</strong>
            {strongest}
        </span>

        <span>
            <strong>最も弱い五行：</strong>
            {weakest}
        </span>
    </div>
</div>
"""


def _render_chart_summary(
    product: ReadingProduct,
) -> str:
    chart = _safe_mapping(
        product.chart_summary
    )

    day_master = _safe_mapping(
        chart.get(
            "day_master"
        )
    )

    strength = _safe_mapping(
        chart.get(
            "strength"
        )
    )

    pattern = _safe_mapping(
        chart.get(
            "pattern"
        )
    )

    useful = _safe_mapping(
        chart.get(
            "useful_gods"
        )
    )

    current_luck = _safe_mapping(
        chart.get(
            "current_luck"
        )
    )

    annual_luck = _safe_mapping(
        chart.get(
            "annual_luck"
        )
    )

    # --------------------------------------------------------
    # 日主の表示値
    #
    # ReadingProductに計算済み値があればそれを最優先。
    # element / yin_yang 欠損時だけ、
    # 日主天干の固定属性を表示補完する。
    # --------------------------------------------------------

    day_master_stem = _text(
        day_master.get(
            "stem"
        )
    )

    day_master_element = (
        _day_master_display_value(
            day_master,
            "element",
        )
    )

    day_master_yin_yang = (
        _day_master_display_value(
            day_master,
            "yin_yang",
        )
    )

    # --------------------------------------------------------
    # 大運年齢
    #
    # 内部値は変更せず、
    # 商品画面だけ整数の「約○歳」で表示する。
    # --------------------------------------------------------

    start_age_display = (
        _display_age_html(
            current_luck.get(
                "start_age"
            )
        )
    )

    end_age_display = (
        _display_age_html(
            current_luck.get(
                "end_age"
            )
        )
    )

    # --------------------------------------------------------
    # 用神表示
    # --------------------------------------------------------

    secondary = "・".join(
        _text(item)
        for item
        in _safe_sequence(
            useful.get(
                "secondary_useful_elements"
            )
        )
        if _text(item)
    )

    unfavorable = "・".join(
        _text(item)
        for item
        in _safe_sequence(
            useful.get(
                "unfavorable_elements"
            )
        )
        if _text(item)
    )

    # --------------------------------------------------------
    # 技術値
    #
    # 既存HTML契約との後方互換のため
    # HTMLソースには保持するが、
    # Web/PDFの顧客表示からは完全に隠す。
    # --------------------------------------------------------

    strength_technical = (
        _text(
            strength.get(
                "technical_label"
            )
        )
    )

    pattern_technical = (
        _text(
            pattern.get(
                "technical_pattern"
            )
        )
    )

    pattern_overall = (
        _text(
            pattern.get(
                "overall_judgment"
            )
        )
    )

    hidden_technical = f"""
    <span
        class="internal-technical"
        aria-hidden="true"
    >
        {_html(strength_technical)}
        {_html(pattern_technical)}
        {_html(pattern_overall)}
    </span>
    """

    return f"""
<section
    class="reading-card chart-card"
    aria-labelledby="chart-heading"
>
    <h2 id="chart-heading">
        命式
    </h2>

    {_render_pillars(chart)}

    <div class="chart-summary-grid">

        <div class="sub-card">
            <h3>日主</h3>

            <div class="major-value">
                {_display_html(
                    day_master_stem
                )}
            </div>

            <dl class="summary-list">
                <div>
                    <dt>五行</dt>
                    <dd>
                        {_display_html(
                            day_master_element
                        )}
                    </dd>
                </div>

                <div>
                    <dt>陰陽</dt>
                    <dd>
                        {_display_html(
                            day_master_yin_yang
                        )}
                    </dd>
                </div>

                <div>
                    <dt>日柱</dt>
                    <dd>
                        {_display_html(
                            day_master.get(
                                "day_pillar"
                            )
                        )}
                    </dd>
                </div>
            </dl>
        </div>

        <div class="sub-card">
            <h3>身強・身弱</h3>

            <div class="major-value">
                {_display_html(
                    strength.get(
                        "label"
                    )
                )}
            </div>

            <dl class="summary-list">
                <div>
                    <dt>スコア</dt>
                    <dd>
                        {_display_html(
                            strength.get(
                                "final_score"
                            )
                        )}
                    </dd>
                </div>
            </dl>
        </div>

        <div class="sub-card">
            <h3>格局</h3>

            <div class="major-value small">
                {_display_html(
                    pattern.get(
                        "primary_pattern"
                    )
                )}
            </div>

            <p class="customer-note">
                命式全体から見た中心的な格局です。
            </p>
        </div>

        <div class="sub-card">
            <h3>用神</h3>

            <div class="major-value">
                {_display_html(
                    useful.get(
                        "primary_useful_element"
                    )
                )}
            </div>

            <dl class="summary-list">
                <div>
                    <dt>補助</dt>
                    <dd>
                        {_display_html(
                            secondary
                        )}
                    </dd>
                </div>

                <div>
                    <dt>忌神傾向</dt>
                    <dd>
                        {_display_html(
                            unfavorable
                        )}
                    </dd>
                </div>
            </dl>
        </div>

    </div>

    {hidden_technical}

    {_render_five_elements(chart)}

    <div class="luck-grid">

        <div class="sub-card">
            <h3>現在の大運</h3>

            <div class="major-value">
                {_display_html(
                    current_luck.get(
                        "ganzhi"
                    )
                )}
            </div>

            <dl class="summary-list">
                <div>
                    <dt>通変星</dt>
                    <dd>
                        {_display_html(
                            current_luck.get(
                                "stem_ten_god"
                            )
                        )}
                    </dd>
                </div>

                <div>
                    <dt>開始年齢</dt>
                    <dd>
                        {start_age_display}
                    </dd>
                </div>

                <div>
                    <dt>終了年齢</dt>
                    <dd>
                        {end_age_display}
                    </dd>
                </div>
            </dl>
        </div>

        <div class="sub-card">
            <h3>歳運</h3>

            <div class="major-value">
                {_display_html(
                    annual_luck.get(
                        "ganzhi"
                    )
                )}
            </div>

            <dl class="summary-list">
                <div>
                    <dt>年</dt>
                    <dd>
                        {_display_html(
                            annual_luck.get(
                                "year"
                            )
                        )}
                    </dd>
                </div>

                <div>
                    <dt>通変星</dt>
                    <dd>
                        {_display_html(
                            annual_luck.get(
                                "stem_ten_god"
                            )
                        )}
                    </dd>
                </div>

                <div>
                    <dt>十二運</dt>
                    <dd>
                        {_display_html(
                            annual_luck.get(
                                "twelve_stage"
                            )
                        )}
                    </dd>
                </div>
            </dl>
        </div>

    </div>

</section>
"""

def _render_overall_summary(
    product: ReadingProduct,
) -> str:
    summary = _text(
        product.summary
    )

    if not summary:
        return ""

    return f"""
<section
    class="reading-card overall-card"
    aria-labelledby="overall-heading"
>
    <h2 id="overall-heading">
        総合鑑定
    </h2>

    <div class="overall-text">
        {_paragraphs(summary)}
    </div>
</section>
"""


def _render_section(
    section: Mapping[
        str,
        Any,
    ],
    *,
    index: int,
) -> str:
    title = _display_html(
        section.get(
            "title"
        ),
        empty="鑑定",
    )

    summary = _text(
        section.get(
            "summary"
        )
    )

    detail = _text(
        section.get(
            "detail"
        )
    )

    evidence = _render_list(
        section.get(
            "evidence"
        ),
        css_class="evidence-list",
    )

    advice = _render_list(
        section.get(
            "advice"
        ),
        css_class="advice-list",
    )

    summary_html = ""

    if summary:
        summary_html = f"""
        <div class="section-lead">
            {_paragraphs(summary)}
        </div>
        """

    detail_html = ""

    if detail:
        detail_html = f"""
        <div class="section-detail">
            {_paragraphs(detail)}
        </div>
        """

    evidence_html = ""

    if evidence:
        evidence_html = f"""
        <div class="section-block evidence-block">
            <h3>鑑定の根拠</h3>
            {evidence}
        </div>
        """

    advice_html = ""

    if advice:
        advice_html = f"""
        <div class="section-block advice-block">
            <h3>アドバイス</h3>
            {advice}
        </div>
        """

    return f"""
<section
    class="reading-card reading-section"
    aria-labelledby="section-{index}"
>
    <div class="section-number">
        {index:02d}
    </div>

    <h2 id="section-{index}">
        {title}
    </h2>

    {summary_html}

    {detail_html}

    {evidence_html}

    {advice_html}
</section>
"""


def _render_sections(
    product: ReadingProduct,
) -> str:
    sections = _safe_sequence(
        product.sections
    )

    rendered = []

    for index, section in enumerate(
        sections,
        start=1,
    ):
        if not isinstance(
            section,
            Mapping,
        ):
            continue

        rendered.append(
            _render_section(
                section,
                index=index,
            )
        )

    return "\n".join(
        rendered
    )


def _render_disclaimer(
    product: ReadingProduct,
) -> str:
    disclaimer = _text(
        product.disclaimer
    )

    if not disclaimer:
        return ""

    return f"""
<section
    class="disclaimer"
    aria-labelledby="disclaimer-heading"
>
    <h2 id="disclaimer-heading">
        免責・注意事項
    </h2>

    {_paragraphs(disclaimer)}
</section>
"""


def _default_css() -> str:
    return """
:root {
    --page-bg: #f6f2e9;
    --paper: #ffffff;
    --ink: #28251f;
    --muted: #746e63;
    --line: #ded6c8;
    --accent: #8a6a34;
    --accent-soft: #f4ede0;
    --deep: #3c3428;
}

* {
    box-sizing: border-box;
}

html {
    font-size: 16px;
}

body {
    margin: 0;
    padding: 0;
    background: var(--page-bg);
    color: var(--ink);
    font-family:
        "Noto Serif JP",
        "Yu Mincho",
        "Hiragino Mincho ProN",
        "Hiragino Mincho Pro",
        "YuMincho",
        serif;
    line-height: 1.9;
    -webkit-font-smoothing: antialiased;
}

.reading-document {
    width: min(100%, 960px);
    margin: 0 auto;
    padding: 48px 24px 80px;
}

.cover {
    min-height: 440px;
    padding: 72px 48px;
    background: var(--deep);
    color: #ffffff;
    display: flex;
    flex-direction: column;
    justify-content: center;
    text-align: center;
    border-radius: 4px;
    margin-bottom: 32px;
}

.cover-kicker {
    margin: 0 0 20px;
    font-size: 0.82rem;
    letter-spacing: 0.28em;
    opacity: 0.75;
}

.cover h1 {
    margin: 0;
    font-size: clamp(
        2rem,
        6vw,
        3.8rem
    );
    line-height: 1.35;
    font-weight: 500;
    letter-spacing: 0.12em;
}

.cover-line {
    width: 64px;
    height: 1px;
    margin: 28px auto;
    background: rgba(
        255,
        255,
        255,
        0.6
    );
}

.cover-subtitle {
    margin: 0;
    font-size: 0.95rem;
    letter-spacing: 0.16em;
    opacity: 0.8;
}

.cover-customer {
    margin: 2px 0 0;
    font-size: 1.45rem;
    letter-spacing: 0.12em;
    font-weight: 500;
}

.cover-reading-date {
    margin: 18px 0 0;
    font-size: 0.88rem;
    letter-spacing: 0.1em;
    opacity: 0.82;
}

.cover-brand {
    margin: 34px 0 0;
    font-size: 0.92rem;
    letter-spacing: 0.18em;
    opacity: 0.9;
}

.reading-card {
    position: relative;
    margin: 0 0 28px;
    padding: 36px 40px;
    background: var(--paper);
    border: 1px solid var(--line);
    border-radius: 4px;
}

.reading-card > h2 {
    margin: 0 0 28px;
    color: var(--deep);
    font-size: 1.55rem;
    font-weight: 600;
    letter-spacing: 0.08em;
}

.info-grid {
    display: grid;
    grid-template-columns:
        repeat(
            2,
            minmax(0, 1fr)
        );
    gap: 1px;
    background: var(--line);
    border: 1px solid var(--line);
}

.info-item {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 18px 20px;
    background: var(--paper);
}

.info-label {
    color: var(--muted);
    font-size: 0.78rem;
    letter-spacing: 0.08em;
}

.info-value {
    font-size: 1rem;
    font-weight: 600;
}

.pillar-grid {
    display: grid;
    grid-template-columns:
        repeat(
            4,
            minmax(0, 1fr)
        );
    gap: 12px;
    margin-bottom: 28px;
}

.pillar-card {
    padding: 20px 14px;
    border: 1px solid var(--line);
    text-align: center;
}

.pillar-title {
    color: var(--muted);
    font-size: 0.8rem;
    letter-spacing: 0.1em;
}

.pillar-ganzhi {
    margin: 8px 0 16px;
    color: var(--deep);
    font-size: 1.8rem;
    font-weight: 600;
    letter-spacing: 0.08em;
}

.pillar-details {
    margin: 0;
    text-align: left;
}

.pillar-details > div {
    display: flex;
    justify-content: space-between;
    gap: 8px;
    padding: 5px 0;
    border-top: 1px dotted var(--line);
    font-size: 0.76rem;
}

.pillar-details dt {
    color: var(--muted);
}

.pillar-details dd {
    margin: 0;
    text-align: right;
}

.chart-summary-grid,
.luck-grid {
    display: grid;
    grid-template-columns:
        repeat(
            2,
            minmax(0, 1fr)
        );
    gap: 16px;
    margin-bottom: 16px;
}

.sub-card {
    padding: 24px;
    background: #fcfaf6;
    border: 1px solid var(--line);
}

.sub-card h3 {
    margin: 0 0 16px;
    color: var(--muted);
    font-size: 0.88rem;
    letter-spacing: 0.08em;
}

.major-value {
    margin-bottom: 18px;
    color: var(--accent);
    font-size: 2rem;
    font-weight: 600;
}

.major-value.small {
    font-size: 1.45rem;
}

.summary-list {
    margin: 0;
}

.summary-list > div {
    display: grid;
    grid-template-columns:
        100px 1fr;
    gap: 12px;
    padding: 7px 0;
    border-top: 1px solid var(--line);
}

.summary-list dt {
    color: var(--muted);
    font-size: 0.82rem;
}

.summary-list dd {
    margin: 0;
    font-size: 0.9rem;
}

.customer-note {
    margin: 0;
    color: var(--muted);
    font-size: 0.82rem;
    line-height: 1.7;
}

.internal-technical {
    display: none !important;
}

.data-table {
    width: 100%;
    border-collapse: collapse;
}

.data-table th,
.data-table td {
    padding: 8px 12px;
    border-bottom: 1px solid var(--line);
}

.data-table th {
    width: 30%;
    text-align: left;
    font-weight: 500;
}

.data-table td {
    text-align: right;
}

.mini-summary {
    display: flex;
    flex-wrap: wrap;
    gap: 12px 28px;
    margin-top: 18px;
    font-size: 0.88rem;
}

.overall-card {
    border-top: 4px solid var(--accent);
}

.overall-text {
    font-size: 1.04rem;
}

.reading-paragraph {
    margin: 0 0 1em;
}

.reading-paragraph:last-child {
    margin-bottom: 0;
}

.reading-section {
    padding-top: 44px;
}

.section-number {
    position: absolute;
    top: 20px;
    right: 28px;
    color: var(--accent-soft);
    font-family:
        Georgia,
        "Times New Roman",
        serif;
    font-size: 3.5rem;
    line-height: 1;
    font-weight: 700;
}

.section-lead {
    position: relative;
    z-index: 1;
    margin: 0 0 24px;
    padding: 20px 24px;
    background: var(--accent-soft);
    font-size: 1.02rem;
    font-weight: 500;
}

.section-detail {
    margin-bottom: 28px;
}

.section-block {
    margin-top: 28px;
    padding-top: 20px;
    border-top: 1px solid var(--line);
}

.section-block h3 {
    margin: 0 0 14px;
    color: var(--accent);
    font-size: 1rem;
    letter-spacing: 0.08em;
}

.evidence-list,
.advice-list {
    margin: 0;
    padding-left: 1.4em;
}

.evidence-list li,
.advice-list li {
    margin: 8px 0;
}

.disclaimer {
    margin-top: 40px;
    padding: 24px 28px;
    color: var(--muted);
    background: rgba(
        255,
        255,
        255,
        0.55
    );
    border: 1px solid var(--line);
    font-size: 0.8rem;
}

.disclaimer h2 {
    margin: 0 0 12px;
    color: var(--deep);
    font-size: 0.95rem;
}

.document-footer {
    padding: 30px 0 0;
    color: var(--muted);
    text-align: center;
    font-size: 0.72rem;
    letter-spacing: 0.06em;
}

@media (
    max-width: 720px
) {
    .reading-document {
        padding:
            20px
            12px
            48px;
    }

    .cover {
        min-height: 360px;
        padding: 48px 24px;
    }

    .reading-card {
        padding: 28px 20px;
    }

    .info-grid,
    .chart-summary-grid,
    .luck-grid {
        grid-template-columns: 1fr;
    }

    .pillar-grid {
        grid-template-columns:
            repeat(
                2,
                minmax(0, 1fr)
            );
    }
}

@media (
    max-width: 440px
) {
    .pillar-grid {
        grid-template-columns: 1fr;
    }
}

@page {
    size: A4;
    margin: 16mm 14mm 18mm;
}

@media print {

    :root {
        --page-bg: #ffffff;
    }

    html {
        font-size: 10.5pt;
    }

    body {
        background: #ffffff;
    }

    .reading-document {
        width: 100%;
        max-width: none;
        margin: 0;
        padding: 0;
    }

    .cover {
        min-height: 250mm;
        margin: 0;
        padding: 60mm 15mm;
        border-radius: 0;
        break-after: page;
        page-break-after: always;
    }

    .reading-card {
        margin-bottom: 8mm;
        padding: 8mm;
        border-radius: 0;
        break-inside: avoid;
        page-break-inside: avoid;
    }

    .reading-section {
        break-inside: auto;
        page-break-inside: auto;
    }

    .section-lead,
    .section-block,
    .sub-card,
    .pillar-card {
        break-inside: avoid;
        page-break-inside: avoid;
    }

    .subject-card,
    .chart-card,
    .overall-card {
        break-inside: auto;
        page-break-inside: auto;
    }

    .disclaimer {
        break-inside: avoid;
        page-break-inside: avoid;
    }

    a {
        color: inherit;
        text-decoration: none;
    }
}
"""


def render_reading_product_html(
    product: ReadingProduct,
    *,
    include_css: bool = True,
    document_title: Optional[
        str
    ] = None,
) -> str:
    """
    ReadingProductを完全なHTML文書へ変換する。

    占術再計算:
        しない

    AI文章再生成:
        しない

    HTML escaping:
        行う
    """

    product = _require_product(
        product
    )

    title = (
        _text(document_title)
        or _text(product.title)
        or "四柱推命鑑定書"
    )

    css = ""

    if include_css:
        css = (
            "<style>\n"
            f"{_default_css()}"
            "\n</style>"
        )

    subject = _safe_mapping(
        product.subject
    )

    birth_date = _display_html(
        subject.get(
            "birth_date"
        )
    )

    customer_name = _text(
        subject.get(
            "name"
        )
    )

    metadata = _safe_mapping(
        product.metadata
    )

    reading_date = _format_japanese_date(
        metadata.get(
            "created_at"
        )
    )

    brand_name = _text(
        metadata.get(
            "brand_name"
        )
    )

    if customer_name:
        cover_detail = f"""
    <p class="cover-customer">
        {_html(customer_name)} 様
    </p>

    {f'<p class="cover-reading-date">鑑定日　{_html(reading_date)}</p>' if reading_date else ''}

    {f'<p class="cover-brand">{_html(brand_name)}</p>' if brand_name else ''}
        """
    else:
        # 後方互換: パーソナライズ情報がない既存商品は
        # 従来どおり生年月日を表示する。
        cover_detail = f"""
    <p class="cover-subtitle">
        {birth_date}
    </p>
        """

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>
<meta
    name="robots"
    content="noindex,nofollow"
>
<title>{_html(title)}</title>
{css}
</head>

<body>

<main class="reading-document">

<header class="cover">

    <p class="cover-kicker">
        SHICHUSUIMEI READING
    </p>

    <h1>
        {_html(product.title)}
    </h1>

    <div class="cover-line"></div>

    {cover_detail}

</header>

{_render_subject(product)}

{_render_chart_summary(product)}

{_render_overall_summary(product)}

{_render_sections(product)}

{_render_disclaimer(product)}

<footer class="document-footer">
    {_html(brand_name or "四柱推命鑑定")}
</footer>

</main>

</body>
</html>
"""


def render_reading_product_fragment(
    product: ReadingProduct,
) -> str:
    """
    Webページへの埋め込み用HTML fragment。

    html/head/bodyタグは含めない。
    """

    product = _require_product(
        product
    )

    return f"""
<div class="reading-document">

{_render_subject(product)}

{_render_chart_summary(product)}

{_render_overall_summary(product)}

{_render_sections(product)}

{_render_disclaimer(product)}

</div>
""".strip()


def write_reading_product_html(
    product: ReadingProduct,
    output_path: Union[
        str,
        Path,
    ],
    *,
    document_title: Optional[
        str
    ] = None,
) -> Path:
    """
    ReadingProductをUTF-8 HTMLファイルとして保存。
    """

    product = _require_product(
        product
    )

    path = Path(
        output_path
    )

    if path.suffix.lower() not in (
        ".html",
        ".htm",
    ):
        raise ValueError(
            "output_pathは"
            ".html または .htm "
            "で指定してください。"
        )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    html_document = (
        render_reading_product_html(
            product,
            include_css=True,
            document_title=(
                document_title
            ),
        )
    )

    path.write_text(
        html_document,
        encoding="utf-8",
    )

    return path


def get_reading_renderer_metadata(
) -> Dict[str, Any]:
    return {
        "version": (
            READING_RENDERER_VERSION
        ),
        "method": (
            READING_RENDERER_METHOD
        ),
        "status": (
            READING_RENDERER_STATUS
        ),
        "input_type": (
            "ReadingProduct"
        ),
        "output_types": [
            "html_document",
            "html_fragment",
        ],
        "recalculates_astrology": False,
        "rewrites_ai_reading": False,
        "escapes_html": True,
        "exposes_generation_metadata": False,
        "exposes_api_key": False,
        "print_ready": True,
    }


__all__ = [
    "READING_RENDERER_VERSION",
    "READING_RENDERER_METHOD",
    "READING_RENDERER_STATUS",
    "ReadingRendererError",
    "ReadingRendererValidationError",
    "render_reading_product_html",
    "render_reading_product_fragment",
    "write_reading_product_html",
    "get_reading_renderer_metadata",
]
