"""
scripts/patch_reading_renderer_decade_ai_v1_1.py

四柱推命鑑定書 v1.1

engine/reading_renderer.py に
大運AI詳細鑑定を追加する安全版パッチ。

描画順
------
通常8セクション
    ↓
10年ごとの大運一覧
    ↓
大運から見る人生の流れ
    ↓
免責事項

方針
----
- 既存CSSを変更しない
- インラインstyleで表示する
- 既存の大運一覧は変更しない
- ReadingProduct.decade_luckを読むだけ
- 占術再計算をしない
- AI文章を書き換えない
- decade_luckが空なら何も表示しない
- HTML document / fragment の両方へ追加
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
    / "reading_renderer.py.bak_v1_1_decade_ai_v2"
)


# ============================================================
# Renderer
# ============================================================


RENDER_FUNCTION = r'''

# ============================================================
# v1.1
# 大運AI詳細鑑定
# ============================================================


def _render_decade_luck_reading(
    product: ReadingProduct,
) -> str:
    """
    ReadingProduct.decade_luck に格納された
    大運AI鑑定を顧客向けHTMLへ描画する。

    この関数では、

    - 大運を再計算しない
    - 干支を変更しない
    - 年齢を変更しない
    - AI文章を書き換えない

    表示だけを担当する。
    """

    product = _require_product(
        product
    )

    decade_luck = _safe_mapping(
        getattr(
            product,
            "decade_luck",
            {},
        )
    )

    if not decade_luck:
        return ""

    overview = _text(
        decade_luck.get(
            "overview"
        )
    )

    raw_periods = _safe_sequence(
        decade_luck.get(
            "periods"
        )
    )

    periods = [
        _safe_mapping(
            period
        )
        for period
        in raw_periods
        if isinstance(
            period,
            Mapping,
        )
    ]

    if (
        not overview
        and not periods
    ):
        return ""

    # --------------------------------------------------------
    # Overview
    # --------------------------------------------------------

    overview_html = ""

    if overview:
        overview_html = f"""
        <div
            style="
                margin: 20px 0 28px;
                padding: 22px 24px;
                border: 1px solid #ded7ca;
                border-radius: 12px;
                background: #faf8f4;
            "
        >
            <h3
                style="
                    margin: 0 0 10px;
                    font-size: 18px;
                    line-height: 1.5;
                "
            >
                これからの大きな流れ
            </h3>

            <div
                style="
                    line-height: 1.9;
                "
            >
                {_paragraphs(overview)}
            </div>
        </div>
        """

    # --------------------------------------------------------
    # Period cards
    # --------------------------------------------------------

    period_html_parts = []

    for position, period in enumerate(
        periods,
        start=1,
    ):
        index = period.get(
            "index"
        )

        ganzhi = _text(
            period.get(
                "ganzhi"
            )
        )

        start_age = period.get(
            "start_age"
        )

        end_age = period.get(
            "end_age"
        )

        title = _text(
            period.get(
                "title"
            )
        )

        theme = _text(
            period.get(
                "theme"
            )
        )

        career = _text(
            period.get(
                "career"
            )
        )

        wealth = _text(
            period.get(
                "wealth"
            )
        )

        relationships = _text(
            period.get(
                "relationships"
            )
        )

        caution = _text(
            period.get(
                "caution"
            )
        )

        advice = [
            _text(
                item
            )
            for item
            in _safe_sequence(
                period.get(
                    "advice"
                )
            )
            if _text(
                item
            )
        ]

        # ----------------------------------------------------
        # Age display
        # ----------------------------------------------------

        age_label = ""

        if (
            start_age is not None
            and end_age is not None
        ):
            age_label = (
                f"{_display(start_age)}歳〜"
                f"{_display(end_age)}歳"
            )

        elif start_age is not None:
            age_label = (
                f"{_display(start_age)}歳〜"
            )

        # ----------------------------------------------------
        # Meta
        # ----------------------------------------------------

        meta_parts = []

        if ganzhi:
            meta_parts.append(
                ganzhi
            )

        if age_label:
            meta_parts.append(
                age_label
            )

        meta_html = ""

        if meta_parts:
            meta_html = f"""
            <div
                style="
                    margin-bottom: 4px;
                    font-size: 13px;
                    line-height: 1.5;
                    opacity: 0.72;
                "
            >
                {_html(
                    " / ".join(
                        meta_parts
                    )
                )}
            </div>
            """

        # ----------------------------------------------------
        # Title
        # ----------------------------------------------------

        display_title = (
            title
            or (
                f"大運 {index}"
                if index is not None
                else f"大運 {position}"
            )
        )

        # ----------------------------------------------------
        # Theme
        # ----------------------------------------------------

        theme_html = ""

        if theme:
            theme_html = f"""
            <div
                style="
                    margin: 18px 0;
                    padding: 17px 20px;
                    border-left: 3px solid #b8aa92;
                    background: #faf8f4;
                    page-break-inside: avoid;
                "
            >
                <div
                    style="
                        margin-bottom: 7px;
                        font-size: 13px;
                        font-weight: 700;
                    "
                >
                    この10年のテーマ
                </div>

                <div
                    style="
                        line-height: 1.85;
                    "
                >
                    {_paragraphs(theme)}
                </div>
            </div>
            """

        # ----------------------------------------------------
        # Detail blocks
        # ----------------------------------------------------

        detail_definitions = (
            (
                "仕事・社会的役割",
                career,
            ),
            (
                "金運・お金との向き合い方",
                wealth,
            ),
            (
                "人間関係",
                relationships,
            ),
            (
                "注意したいこと",
                caution,
            ),
        )

        detail_html_parts = []

        for (
            label,
            body,
        ) in detail_definitions:
            if not body:
                continue

            detail_html_parts.append(
                f"""
                <div
                    style="
                        margin: 12px 0;
                        padding: 16px 18px;
                        border: 1px solid #e5e0d7;
                        border-radius: 10px;
                        page-break-inside: avoid;
                    "
                >
                    <h4
                        style="
                            margin: 0 0 8px;
                            font-size: 14px;
                            line-height: 1.5;
                        "
                    >
                        {_html(label)}
                    </h4>

                    <div
                        style="
                            line-height: 1.8;
                        "
                    >
                        {_paragraphs(body)}
                    </div>
                </div>
                """
            )

        details_html = "".join(
            detail_html_parts
        )

        # ----------------------------------------------------
        # Advice
        # ----------------------------------------------------

        advice_html = ""

        if advice:
            advice_items = "".join(
                f"""
                <li
                    style="
                        margin: 6px 0;
                        line-height: 1.75;
                    "
                >
                    {_html(item)}
                </li>
                """
                for item
                in advice
            )

            advice_html = f"""
            <div
                style="
                    margin-top: 18px;
                    padding: 18px 20px;
                    border-radius: 10px;
                    background: #f7f5f0;
                    page-break-inside: avoid;
                "
            >
                <div
                    style="
                        font-size: 13px;
                        font-weight: 700;
                    "
                >
                    この時期を活かすポイント
                </div>

                <ul
                    style="
                        margin: 10px 0 0;
                        padding-left: 1.4em;
                    "
                >
                    {advice_items}
                </ul>
            </div>
            """

        # ----------------------------------------------------
        # Card
        # ----------------------------------------------------

        period_html_parts.append(
            f"""
            <article
                style="
                    margin: 0 0 24px;
                    padding: 24px;
                    border: 1px solid #ddd7cc;
                    border-radius: 14px;
                    background: #ffffff;
                    page-break-inside: avoid;
                "
            >
                <div
                    style="
                        display: flex;
                        align-items: flex-start;
                        gap: 14px;
                        margin-bottom: 16px;
                    "
                >
                    <div
                        style="
                            flex: 0 0 auto;
                            width: 34px;
                            height: 34px;
                            border: 1px solid #b8aa92;
                            border-radius: 50%;
                            text-align: center;
                            line-height: 34px;
                            font-size: 14px;
                            font-weight: 700;
                        "
                    >
                        {_html(position)}
                    </div>

                    <div>
                        {meta_html}

                        <h3
                            style="
                                margin: 3px 0 0;
                                font-size: 20px;
                                line-height: 1.5;
                            "
                        >
                            {_html(display_title)}
                        </h3>
                    </div>
                </div>

                {theme_html}

                {details_html}

                {advice_html}

            </article>
            """
        )

    periods_html = "".join(
        period_html_parts
    )

    # --------------------------------------------------------
    # Entire section
    # --------------------------------------------------------

    return f"""
<section
    class="reading-card decade-reading-card-section"
    aria-labelledby="decade-reading-heading"
    style="
        margin-top: 42px;
    "
>
    <h2
        id="decade-reading-heading"
    >
        大運から見る人生の流れ
    </h2>

    <p
        style="
            margin: -4px 0 20px;
            line-height: 1.8;
            opacity: 0.76;
        "
    >
        現在から先の10年単位の運勢を読み解きます。
    </p>

    {overview_html}

    {periods_html}

</section>
"""
'''


# ============================================================
# Anchors
# ============================================================


FUNCTION_ANCHOR = (
    "def _render_disclaimer("
)


CALL_ANCHOR = """{_render_decade_luck(product)}

{_render_disclaimer(product)}"""


CALL_REPLACEMENT = """{_render_decade_luck(product)}

{_render_decade_luck_reading(product)}

{_render_disclaimer(product)}"""


# ============================================================
# Helpers
# ============================================================


def require_once(
    text: str,
    anchor: str,
    name: str,
) -> None:

    count = text.count(
        anchor
    )

    if count != 1:
        raise RuntimeError(
            f"{name} が"
            f"{count}件見つかりました。"
            "想定は1件です。"
            "ファイルは変更しません。"
        )


# ============================================================
# Main
# ============================================================


def main() -> None:

    # --------------------------------------------------------
    # Target
    # --------------------------------------------------------

    if not TARGET.exists():
        raise FileNotFoundError(
            "対象ファイルがありません: "
            f"{TARGET}"
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
    # Existing v1.1 list renderer
    # --------------------------------------------------------

    if (
        "def _render_decade_luck("
        not in original
    ):
        raise RuntimeError(
            "既存の"
            "_render_decade_luck()"
            "が見つかりません。"
        )

    # --------------------------------------------------------
    # Anchors
    # --------------------------------------------------------

    require_once(
        original,
        FUNCTION_ANCHOR,
        "_render_disclaimer definition",
    )

    # HTML document + fragment の
    # 2箇所を想定。
    call_count = original.count(
        CALL_ANCHOR
    )

    if call_count != 2:
        raise RuntimeError(
            "大運一覧→免責事項の"
            "描画箇所が"
            f"{call_count}件でした。"
            "想定は2件です。"
            "ファイルは変更しません。"
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

    # ========================================================
    # Apply in memory
    # ========================================================

    patched = original

    # --------------------------------------------------------
    # Function
    # --------------------------------------------------------

    patched = patched.replace(
        FUNCTION_ANCHOR,
        (
            RENDER_FUNCTION.strip()
            + "\n\n\n"
            + FUNCTION_ANCHOR
        ),
        1,
    )

    # --------------------------------------------------------
    # HTML document + fragment
    # --------------------------------------------------------

    patched = patched.replace(
        CALL_ANCHOR,
        CALL_REPLACEMENT,
    )

    # ========================================================
    # Structural checks
    # ========================================================

    if (
        patched.count(
            "def _render_decade_luck_reading("
        )
        != 1
    ):
        raise RuntimeError(
            "_render_decade_luck_reading() "
            "の定義数が不正です。"
        )

    call_count_after = (
        patched.count(
            "_render_decade_luck_reading(product)"
        )
    )

    if call_count_after != 2:
        raise RuntimeError(
            "大運AI詳細描画の"
            "呼び出し数が不正です。"
            f" actual={call_count_after}"
        )

    required_markers = (
        'getattr(\n            product,\n            "decade_luck"',
        "大運から見る人生の流れ",
        "これからの大きな流れ",
        "この10年のテーマ",
        "仕事・社会的役割",
        "金運・お金との向き合い方",
        "人間関係",
        "注意したいこと",
        "この時期を活かすポイント",
        "_paragraphs(overview)",
        "_html(display_title)",
    )

    for marker in required_markers:

        if marker not in patched:
            raise RuntimeError(
                "パッチ後の必須構造が"
                "不足しています: "
                f"{marker}"
            )

    # --------------------------------------------------------
    # Ordering check
    #
    # 実際のHTML生成部分だけを確認する。
    # --------------------------------------------------------

    expected_sequence = """{_render_decade_luck(product)}

{_render_decade_luck_reading(product)}

{_render_disclaimer(product)}"""

    sequence_count = (
        patched.count(
            expected_sequence
        )
    )

    if sequence_count != 2:
        raise RuntimeError(
            "描画順が不正です。"
            "期待:"
            "大運一覧 → 大運AI → 免責"
            f" actual={sequence_count}"
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
        "v1.1 大運AI詳細 "
        "renderer patch 完了"
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
        "  ✓ 期間別タイトル"
    )

    print(
        "  ✓ 干支"
    )

    print(
        "  ✓ 年齢"
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
        "  ✓ 旧product安全対応"
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
        "  10年ごとの大運"
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