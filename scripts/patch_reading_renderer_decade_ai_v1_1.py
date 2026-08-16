"""
scripts/patch_reading_renderer_decade_ai_v1_1.py

四柱推命鑑定書 v1.1

engine/reading_renderer.py に
「大運AI詳細鑑定」のHTML描画を追加する。

完成する描画順:

通常8セクション
    ↓
10年ごとの大運一覧
    ↓
大運から見る人生の流れ
    ↓
免責事項

設計原則
--------
- 既存の大運一覧は変更しない
- ReadingProduct.decade_luck を読むだけ
- 占術計算は行わない
- AI文章を書き換えない
- decade_luck が無い旧productでも安全
- periods が空でも安全
- HTML document / fragment 両対応
- モバイル対応
- A4印刷対応
"""

from __future__ import annotations

import ast
from pathlib import Path


# ============================================================
# Paths
# ============================================================


ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)


TARGET = (
    ROOT
    / "engine"
    / "reading_renderer.py"
)


BACKUP = (
    ROOT
    / "engine"
    / (
        "reading_renderer.py"
        ".bak_v1_1_decade_ai"
    )
)


# ============================================================
# Renderer function
# ============================================================


RENDER_FUNCTION = r'''

# ============================================================
# v1.1
# 大運AI詳細鑑定
# ============================================================


def _render_decade_luck_reading(
    product: Mapping[
        str,
        Any,
    ],
) -> str:
    """
    ReadingProduct.decade_luck を
    顧客向けHTMLへ描画する。

    注意:
    この関数では占術計算を行わない。
    AI文章の再生成・要約・改変も行わない。
    """

    if not isinstance(
        product,
        Mapping,
    ):
        return ""

    decade_luck = product.get(
        "decade_luck"
    )

    if not isinstance(
        decade_luck,
        Mapping,
    ):
        return ""

    overview = decade_luck.get(
        "overview"
    )

    if not isinstance(
        overview,
        str,
    ):
        overview = ""

    overview = overview.strip()

    raw_periods = decade_luck.get(
        "periods"
    )

    if not isinstance(
        raw_periods,
        (list, tuple),
    ):
        raw_periods = []

    periods = [
        period
        for period
        in raw_periods
        if isinstance(
            period,
            Mapping,
        )
    ]

    # --------------------------------------------------------
    # データが実質空ならセクション自体を出さない。
    # --------------------------------------------------------

    if (
        not overview
        and not periods
    ):
        return ""

    parts = []

    parts.append(
        '<section class="decade-reading-section">'
    )

    parts.append(
        '<div class="section-heading">'
        '<div class="section-number">10</div>'
        '<div>'
        '<h2>大運から見る人生の流れ</h2>'
        '<p class="section-subtitle">'
        '10年単位で変化する運勢のテーマ'
        '</p>'
        '</div>'
        '</div>'
    )

    # --------------------------------------------------------
    # Overview
    # --------------------------------------------------------

    if overview:

        parts.append(
            '<div class="decade-reading-overview">'
        )

        parts.append(
            '<h3>これからの大きな流れ</h3>'
        )

        parts.append(
            '<p>'
            + _escape(
                overview
            )
            + '</p>'
        )

        parts.append(
            '</div>'
        )

    # --------------------------------------------------------
    # Periods
    # --------------------------------------------------------

    if periods:

        parts.append(
            '<div class="decade-reading-periods">'
        )

        for position, period in enumerate(
            periods
        ):

            index = period.get(
                "index"
            )

            ganzhi = period.get(
                "ganzhi"
            )

            start_age = period.get(
                "start_age"
            )

            end_age = period.get(
                "end_age"
            )

            title = period.get(
                "title"
            )

            theme = period.get(
                "theme"
            )

            career = period.get(
                "career"
            )

            wealth = period.get(
                "wealth"
            )

            relationships = period.get(
                "relationships"
            )

            caution = period.get(
                "caution"
            )

            advice = period.get(
                "advice"
            )

            # ------------------------------------------------
            # Text normalization
            # ------------------------------------------------

            def text_or_empty(
                value: Any,
            ) -> str:

                if value is None:
                    return ""

                return str(
                    value
                ).strip()

            ganzhi_text = text_or_empty(
                ganzhi
            )

            title_text = text_or_empty(
                title
            )

            theme_text = text_or_empty(
                theme
            )

            career_text = text_or_empty(
                career
            )

            wealth_text = text_or_empty(
                wealth
            )

            relationships_text = (
                text_or_empty(
                    relationships
                )
            )

            caution_text = text_or_empty(
                caution
            )

            # ------------------------------------------------
            # Age label
            # ------------------------------------------------

            age_parts = []

            if start_age is not None:
                age_parts.append(
                    text_or_empty(
                        start_age
                    )
                )

            if end_age is not None:
                age_parts.append(
                    text_or_empty(
                        end_age
                    )
                )

            if len(
                age_parts
            ) == 2:

                age_label = (
                    age_parts[0]
                    + "歳〜"
                    + age_parts[1]
                    + "歳"
                )

            elif len(
                age_parts
            ) == 1:

                age_label = (
                    age_parts[0]
                    + "歳〜"
                )

            else:

                age_label = ""

            # ------------------------------------------------
            # Header label
            # ------------------------------------------------

            period_meta = []

            if ganzhi_text:
                period_meta.append(
                    ganzhi_text
                )

            if age_label:
                period_meta.append(
                    age_label
                )

            # ------------------------------------------------
            # Card
            # ------------------------------------------------

            parts.append(
                '<article class="decade-reading-card">'
            )

            parts.append(
                '<div class="decade-reading-card-header">'
            )

            parts.append(
                '<div class="decade-reading-order">'
                + _escape(
                    str(
                        position + 1
                    )
                )
                + '</div>'
            )

            parts.append(
                '<div class="decade-reading-card-title">'
            )

            if period_meta:

                parts.append(
                    '<div class="decade-reading-meta">'
                    + _escape(
                        " / ".join(
                            period_meta
                        )
                    )
                    + '</div>'
                )

            if title_text:

                parts.append(
                    '<h3>'
                    + _escape(
                        title_text
                    )
                    + '</h3>'
                )

            else:

                parts.append(
                    '<h3>'
                    '大運'
                    + _escape(
                        str(
                            index
                            if index
                            is not None
                            else position + 1
                        )
                    )
                    + '</h3>'
                )

            parts.append(
                '</div>'
            )

            parts.append(
                '</div>'
            )

            # ------------------------------------------------
            # Theme
            # ------------------------------------------------

            if theme_text:

                parts.append(
                    '<div class="decade-reading-theme">'
                )

                parts.append(
                    '<div class="decade-reading-label">'
                    'この10年のテーマ'
                    '</div>'
                )

                parts.append(
                    '<p>'
                    + _escape(
                        theme_text
                    )
                    + '</p>'
                )

                parts.append(
                    '</div>'
                )

            # ------------------------------------------------
            # Detail grid
            # ------------------------------------------------

            detail_items = (
                (
                    "仕事・社会的役割",
                    career_text,
                ),
                (
                    "金運・お金との向き合い方",
                    wealth_text,
                ),
                (
                    "人間関係",
                    relationships_text,
                ),
                (
                    "注意したいこと",
                    caution_text,
                ),
            )

            visible_detail_items = [
                item
                for item
                in detail_items
                if item[1]
            ]

            if visible_detail_items:

                parts.append(
                    '<div class="decade-reading-grid">'
                )

                for (
                    label,
                    body,
                ) in visible_detail_items:

                    parts.append(
                        '<div class="decade-reading-detail">'
                    )

                    parts.append(
                        '<h4>'
                        + _escape(
                            label
                        )
                        + '</h4>'
                    )

                    parts.append(
                        '<p>'
                        + _escape(
                            body
                        )
                        + '</p>'
                    )

                    parts.append(
                        '</div>'
                    )

                parts.append(
                    '</div>'
                )

            # ------------------------------------------------
            # Advice
            # ------------------------------------------------

            if isinstance(
                advice,
                (list, tuple),
            ):

                clean_advice = [
                    text_or_empty(
                        item
                    )
                    for item
                    in advice
                    if text_or_empty(
                        item
                    )
                ]

            else:

                clean_advice = []

            if clean_advice:

                parts.append(
                    '<div class="decade-reading-advice">'
                )

                parts.append(
                    '<div class="decade-reading-label">'
                    'この時期を活かすポイント'
                    '</div>'
                )

                parts.append(
                    '<ul>'
                )

                for item in clean_advice:

                    parts.append(
                        '<li>'
                        + _escape(
                            item
                        )
                        + '</li>'
                    )

                parts.append(
                    '</ul>'
                )

                parts.append(
                    '</div>'
                )

            parts.append(
                '</article>'
            )

        parts.append(
            '</div>'
        )

    parts.append(
        '</section>'
    )

    return "\n".join(
        parts
    )
'''


# ============================================================
# CSS
# ============================================================


CSS_BLOCK = r'''

/* ==========================================================
   v1.1
   大運AI詳細鑑定
   ========================================================== */

.decade-reading-section {
    margin-top: 42px;
}

.decade-reading-overview {
    margin: 22px 0 28px;
    padding: 22px 24px;
    border: 1px solid #ded7ca;
    border-radius: 12px;
    background: #faf8f4;
}

.decade-reading-overview h3 {
    margin: 0 0 10px;
    font-size: 18px;
    line-height: 1.5;
}

.decade-reading-overview p {
    margin: 0;
    line-height: 1.9;
}

.decade-reading-periods {
    display: flex;
    flex-direction: column;
    gap: 24px;
}

.decade-reading-card {
    border: 1px solid #ddd7cc;
    border-radius: 14px;
    padding: 24px;
    background: #fff;
    break-inside: avoid;
    page-break-inside: avoid;
}

.decade-reading-card-header {
    display: flex;
    align-items: flex-start;
    gap: 14px;
    margin-bottom: 18px;
}

.decade-reading-order {
    flex: 0 0 auto;
    width: 34px;
    height: 34px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 1px solid #b8aa92;
    font-size: 14px;
    font-weight: 700;
}

.decade-reading-card-title {
    min-width: 0;
}

.decade-reading-card-title h3 {
    margin: 3px 0 0;
    font-size: 20px;
    line-height: 1.5;
}

.decade-reading-meta {
    font-size: 13px;
    line-height: 1.5;
    opacity: 0.72;
}

.decade-reading-theme {
    margin-bottom: 18px;
    padding: 18px 20px;
    border-left: 3px solid #b8aa92;
    background: #faf8f4;
}

.decade-reading-theme p {
    margin: 7px 0 0;
    line-height: 1.85;
}

.decade-reading-label {
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.04em;
}

.decade-reading-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 14px;
    margin-top: 16px;
}

.decade-reading-detail {
    padding: 17px 18px;
    border: 1px solid #e5e0d7;
    border-radius: 10px;
}

.decade-reading-detail h4 {
    margin: 0 0 8px;
    font-size: 14px;
    line-height: 1.5;
}

.decade-reading-detail p {
    margin: 0;
    line-height: 1.8;
}

.decade-reading-advice {
    margin-top: 18px;
    padding: 18px 20px;
    border-radius: 10px;
    background: #f7f5f0;
}

.decade-reading-advice ul {
    margin: 10px 0 0;
    padding-left: 1.4em;
}

.decade-reading-advice li {
    margin: 6px 0;
    line-height: 1.75;
}


/* ----------------------------------------------------------
   Mobile
   ---------------------------------------------------------- */

@media (max-width: 720px) {

    .decade-reading-section {
        margin-top: 32px;
    }

    .decade-reading-overview {
        padding: 18px;
    }

    .decade-reading-card {
        padding: 18px;
    }

    .decade-reading-grid {
        grid-template-columns: 1fr;
    }

    .decade-reading-card-title h3 {
        font-size: 18px;
    }
}


/* ----------------------------------------------------------
   A4 / Print
   ---------------------------------------------------------- */

@media print {

    .decade-reading-section {
        margin-top: 8mm;
    }

    .decade-reading-overview {
        break-inside: avoid;
        page-break-inside: avoid;
    }

    .decade-reading-card {
        break-inside: avoid;
        page-break-inside: avoid;
        margin-bottom: 5mm;
    }

    .decade-reading-grid {
        gap: 3mm;
    }

    .decade-reading-detail {
        break-inside: avoid;
        page-break-inside: avoid;
    }

    .decade-reading-advice {
        break-inside: avoid;
        page-break-inside: avoid;
    }
}
'''


# ============================================================
# Helpers
# ============================================================


def require(
    condition: bool,
    message: str,
) -> None:

    if not condition:
        raise RuntimeError(
            message
        )


def insert_before(
    text: str,
    anchor: str,
    addition: str,
    name: str,
) -> str:

    count = text.count(
        anchor
    )

    if count != 1:
        raise RuntimeError(
            f"{name}: anchorが"
            f"{count}件です。"
            "想定は1件です。"
        )

    return text.replace(
        anchor,
        addition
        + "\n\n"
        + anchor,
        1,
    )


# ============================================================
# Main
# ============================================================


def main() -> None:

    # --------------------------------------------------------
    # Target
    # --------------------------------------------------------

    require(
        TARGET.exists(),
        (
            "対象ファイルがありません: "
            f"{TARGET}"
        ),
    )

    original = TARGET.read_text(
        encoding="utf-8"
    )

    # --------------------------------------------------------
    # Double patch prevention
    # --------------------------------------------------------

    if (
        "def _render_decade_luck_reading("
        in original
    ):
        raise RuntimeError(
            "reading_renderer.py は"
            "すでに大運AI詳細鑑定対応済みです。"
            "二重適用を防ぐため終了します。"
        )

    # --------------------------------------------------------
    # Existing renderer checks
    # --------------------------------------------------------

    require(
        "def _render_decade_luck("
        in original,
        (
            "既存の _render_decade_luck() "
            "が見つかりません。"
        ),
    )

    require(
        "def _render_disclaimer("
        in original,
        (
            "_render_disclaimer() "
            "が見つかりません。"
        ),
    )

    # --------------------------------------------------------
    # Backup
    # --------------------------------------------------------

    if not BACKUP.exists():

        BACKUP.write_text(
            original,
            encoding="utf-8",
        )

        print(
            "backup:"
        )

        print(
            BACKUP
        )

    else:

        print(
            "backup already exists:"
        )

        print(
            BACKUP
        )

    patched = original

    # ========================================================
    # 1. Renderer function
    #
    # disclaimer関数の直前へ追加。
    # ========================================================

    disclaimer_function_anchor = (
        "def _render_disclaimer("
    )

    patched = insert_before(
        patched,
        disclaimer_function_anchor,
        RENDER_FUNCTION.strip(),
        "renderer function",
    )

    # ========================================================
    # 2. CSS
    #
    # </style> の直前へ追加。
    #
    # reading_renderer.py 内には
    # CSS template中の </style> が
    # 原則1つあることを期待する。
    # ========================================================

    style_anchor = "</style>"

    style_count = patched.count(
        style_anchor
    )

    if style_count < 1:
        raise RuntimeError(
            "</style> が見つかりません。"
        )

    # 最初のstyle終了位置へ追加する。
    patched = patched.replace(
        style_anchor,
        CSS_BLOCK.strip()
        + "\n\n"
        + style_anchor,
        1,
    )

    # ========================================================
    # 3. HTML document
    #
    # _render_decade_luck(product)
    # の直後、
    # _render_disclaimer(product)
    # の直前へ追加。
    # ========================================================

    document_candidates = (
        """{_render_decade_luck(product)}
{_render_disclaimer(product)}""",
        """{_render_decade_luck(product)}

{_render_disclaimer(product)}""",
        """{_render_decade_luck(product)}
    
{_render_disclaimer(product)}""",
    )

    document_replaced = False

    for anchor in document_candidates:

        if anchor in patched:

            replacement = (
                anchor.replace(
                    "{_render_disclaimer(product)}",
                    "{_render_decade_luck_reading(product)}\n"
                    "{_render_disclaimer(product)}",
                )
            )

            patched = patched.replace(
                anchor,
                replacement,
                1,
            )

            document_replaced = True

            break

    # --------------------------------------------------------
    # f-stringではなくjoin/list形式の場合へのfallback
    # --------------------------------------------------------

    if not document_replaced:

        anchor = (
            "_render_decade_luck(product),"
        )

        count = patched.count(
            anchor
        )

        if count >= 1:

            patched = patched.replace(
                anchor,
                (
                    "_render_decade_luck(product),\n"
                    "        "
                    "_render_decade_luck_reading(product),"
                ),
                1,
            )

            document_replaced = True

    require(
        document_replaced,
        (
            "HTML document側の"
            "大運一覧→免責事項の接続位置を"
            "特定できませんでした。"
        ),
    )

    # ========================================================
    # 4. HTML fragment
    #
    # documentとは別に同じ並びがある場合、
    # もう一度追加する。
    # ========================================================

    fragment_replaced = False

    for anchor in document_candidates:

        if anchor in patched:

            replacement = (
                anchor.replace(
                    "{_render_disclaimer(product)}",
                    "{_render_decade_luck_reading(product)}\n"
                    "{_render_disclaimer(product)}",
                )
            )

            patched = patched.replace(
                anchor,
                replacement,
                1,
            )

            fragment_replaced = True

            break

    if not fragment_replaced:

        anchor = (
            "_render_decade_luck(product),"
        )

        if anchor in patched:

            patched = patched.replace(
                anchor,
                (
                    "_render_decade_luck(product),\n"
                    "        "
                    "_render_decade_luck_reading(product),"
                ),
                1,
            )

            fragment_replaced = True

    # --------------------------------------------------------
    # Rendererによってfragment実装が無い場合もある。
    #
    # ただし現在のv1.1ではdocument/fragmentの
    # 両方がある前提なので、ここでは必須とする。
    # --------------------------------------------------------

    require(
        fragment_replaced,
        (
            "HTML fragment側の"
            "大運一覧→免責事項の接続位置を"
            "特定できませんでした。"
        ),
    )

    # ========================================================
    # Structural validation
    # ========================================================

    require(
        (
            patched.count(
                "def _render_decade_luck_reading("
            )
            == 1
        ),
        (
            "_render_decade_luck_reading() "
            "の定義数が不正です。"
        ),
    )

    render_call_count = (
        patched.count(
            "_render_decade_luck_reading(product)"
        )
    )

    require(
        render_call_count >= 2,
        (
            "大運AI詳細鑑定の描画呼び出しが"
            "2箇所未満です。"
            f" actual={render_call_count}"
        ),
    )

    required_markers = (
        'product.get(\n        "decade_luck"',
        "大運から見る人生の流れ",
        "これからの大きな流れ",
        "この10年のテーマ",
        "仕事・社会的役割",
        "金運・お金との向き合い方",
        "人間関係",
        "注意したいこと",
        "この時期を活かすポイント",
        ".decade-reading-section",
        ".decade-reading-card",
        ".decade-reading-grid",
        "@media (max-width: 720px)",
        "@media print",
    )

    for marker in required_markers:

        require(
            marker in patched,
            (
                "パッチ後の必須構造が"
                "ありません: "
                f"{marker}"
            ),
        )

    # ========================================================
    # Ordering validation
    #
    # 呼び出し位置について
    # decade一覧 → decade AI → disclaimer
    # が成立することを確認。
    # ========================================================

    first_decade_list_call = (
        patched.find(
            "_render_decade_luck(product)"
        )
    )

    first_decade_ai_call = (
        patched.find(
            "_render_decade_luck_reading(product)"
        )
    )

    first_disclaimer_call = (
        patched.find(
            "_render_disclaimer(product)"
        )
    )

    require(
        first_decade_list_call
        != -1,
        "大運一覧呼び出しがありません。",
    )

    require(
        first_decade_ai_call
        != -1,
        "大運AI呼び出しがありません。",
    )

    require(
        first_disclaimer_call
        != -1,
        "免責事項呼び出しがありません。",
    )

    require(
        (
            first_decade_list_call
            < first_decade_ai_call
            < first_disclaimer_call
        ),
        (
            "描画順が不正です。\n"
            "期待:\n"
            "大運一覧\n"
            "↓\n"
            "大運AI詳細\n"
            "↓\n"
            "免責事項"
        ),
    )

    # ========================================================
    # Syntax validation
    # ========================================================

    try:

        ast.parse(
            patched
        )

    except SyntaxError as exc:

        raise RuntimeError(
            "パッチ後のreading_renderer.pyに"
            "Python構文エラーがあります。\n"
            f"{exc}"
        ) from exc

    # ========================================================
    # Write
    # ========================================================

    TARGET.write_text(
        patched,
        encoding="utf-8",
    )

    # ========================================================
    # Completion
    # ========================================================

    print()

    print(
        "=" * 72
    )

    print(
        "v1.1 大運AI詳細 renderer patch 完了"
    )

    print(
        "=" * 72
    )

    print()

    print(
        "target:"
    )

    print(
        TARGET
    )

    print()

    print(
        "追加:"
    )

    print(
        "  ✓ _render_decade_luck_reading()"
    )

    print(
        "  ✓ overview"
    )

    print(
        "  ✓ 大運period cards"
    )

    print(
        "  ✓ theme"
    )

    print(
        "  ✓ career"
    )

    print(
        "  ✓ wealth"
    )

    print(
        "  ✓ relationships"
    )

    print(
        "  ✓ caution"
    )

    print(
        "  ✓ advice"
    )

    print(
        "  ✓ HTML document"
    )

    print(
        "  ✓ HTML fragment"
    )

    print(
        "  ✓ モバイルCSS"
    )

    print(
        "  ✓ A4印刷CSS"
    )

    print(
        "  ✓ decade_luck無し旧product対応"
    )

    print()

    print(
        "描画順:"
    )

    print(
        "  8セクション"
    )

    print(
        "      ↓"
    )

    print(
        "  10年ごとの大運一覧"
    )

    print(
        "      ↓"
    )

    print(
        "  大運から見る人生の流れ"
    )

    print(
        "      ↓"
    )

    print(
        "  免責事項"
    )

    print()

    print(
        "Python syntax: OK"
    )

    print()

    print(
        "次に実行:"
    )

    print(
        "python -m pytest "
        "tests/test_reading_renderer.py "
        "tests/test_reading_renderer_five_year_luck.py "
        "tests/test_reading_renderer_decade_luck.py "
        "-q"
    )


if __name__ == "__main__":
    main()
