"""
scripts/patch_reading_renderer_decade_luck_v1_1.py

v1.1
reading_renderer.py に
「10年ごとの大運」一覧表示を追加するための
一回限りの安全なパッチスクリプト。

追加内容
--------
1. _render_decade_luck() を追加
2. 大運専用CSSを追加
3. スマホ用CSSを追加
4. 印刷用CSSを追加
5. 完全HTMLへ大運を追加
6. fragmentへ大運を追加
7. 免責事項は最後のまま維持
8. 元ファイルをバックアップ
9. Python構文チェック
"""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

TARGET = (
    ROOT
    / "engine"
    / "reading_renderer.py"
)

BACKUP = (
    ROOT
    / "engine"
    / "reading_renderer.py.bak_v1_1_decade_luck"
)


# ============================================================
# Renderer function
# ============================================================

DECADE_LUCK_FUNCTION = r'''

def _render_decade_luck(
    product: ReadingProduct,
) -> str:
    """
    v1.1
    10年ごとの大運一覧を表示する。

    占術計算は行わず、
    ReadingProduct.chart_summary に保持された
    luck_pillars をそのまま表示する。
    """

    chart = _safe_mapping(
        product.chart_summary
    )

    luck_pillars = _safe_mapping(
        chart.get(
            "luck_pillars"
        )
    )

    pillars = [
        pillar
        for pillar
        in _safe_sequence(
            luck_pillars.get(
                "pillars"
            )
        )
        if isinstance(
            pillar,
            Mapping,
        )
    ]

    if not pillars:
        return ""

    current_luck = _safe_mapping(
        chart.get(
            "current_luck"
        )
    )

    current_ganzhi = _text(
        current_luck.get(
            "ganzhi"
        )
    )

    direction = (
        _text(
            luck_pillars.get(
                "direction_japanese"
            )
        )
        or _text(
            luck_pillars.get(
                "direction"
            )
        )
    )

    start_age = _display_age_html(
        luck_pillars.get(
            "start_age"
        )
    )

    rows = []

    for pillar in pillars:
        ganzhi = _text(
            pillar.get(
                "ganzhi"
            )
        )

        is_current = (
            bool(
                current_ganzhi
            )
            and ganzhi
            == current_ganzhi
        )

        row_class = (
            ' class="decade-luck-current"'
            if is_current
            else ""
        )

        current_badge = (
            '<span class="decade-current-badge">'
            "現在"
            "</span>"
            if is_current
            else ""
        )

        start_age_value = (
            _display_age_html(
                pillar.get(
                    "start_age"
                )
            )
        )

        end_age_value = (
            _display_age_html(
                pillar.get(
                    "end_age"
                )
            )
        )

        age_range = (
            f"{start_age_value}"
            "〜"
            f"{end_age_value}"
        )

        stem_element = _display_html(
            pillar.get(
                "stem_element"
            )
        )

        branch_element = _display_html(
            pillar.get(
                "branch_element"
            )
        )

        element_text = (
            f"{stem_element}"
            "・"
            f"{branch_element}"
        )

        rows.append(
            f"""
            <tr{row_class}>
                <td class="decade-luck-index">
                    {_display_html(
                        pillar.get(
                            "index"
                        )
                    )}
                </td>

                <td class="decade-luck-age">
                    {age_range}
                </td>

                <td class="decade-luck-ganzhi">
                    {_display_html(
                        ganzhi
                    )}
                    {current_badge}
                </td>

                <td>
                    {_display_html(
                        pillar.get(
                            "stem_ten_god"
                        )
                    )}
                </td>

                <td>
                    {element_text}
                </td>
            </tr>
            """
        )

    return f"""
<section
    class="reading-card decade-luck-card"
    aria-labelledby="decade-luck-heading"
>
    <div
        class="section-number decade-section-number"
        aria-hidden="true"
    >
        09
    </div>

    <h2 id="decade-luck-heading">
        10年ごとの大運
    </h2>

    <p class="decade-luck-intro">
        大運は、人生を約10年単位で捉えた
        長期的な運気の流れです。
        年ごとの歳運よりも大きな時間軸から、
        人生の変化やテーマを見ていきます。
    </p>

    <div class="decade-luck-meta">

        <div>
            <span class="decade-luck-meta-label">
                大運開始
            </span>

            <strong>
                {start_age}
            </strong>
        </div>

        <div>
            <span class="decade-luck-meta-label">
                運行
            </span>

            <strong>
                {_display_html(
                    direction
                )}
            </strong>
        </div>

        <div>
            <span class="decade-luck-meta-label">
                大運数
            </span>

            <strong>
                {_display_html(
                    len(
                        pillars
                    )
                )}
            </strong>
        </div>

    </div>

    <div class="decade-luck-table-wrap">

        <table class="decade-luck-table">

            <thead>
                <tr>
                    <th>第</th>
                    <th>年齢</th>
                    <th>大運</th>
                    <th>通変星</th>
                    <th>五行</th>
                </tr>
            </thead>

            <tbody>
                {''.join(rows)}
            </tbody>

        </table>

    </div>

    <p class="decade-luck-note">
        「現在」と表示された大運が、
        現在進行している約10年間の
        大きな流れです。
    </p>

</section>
"""
'''


# ============================================================
# Main CSS
# ============================================================

DECADE_LUCK_CSS = r'''
/* =========================================================
   v1.1
   10年ごとの大運
   ========================================================= */

.decade-luck-card {
    position: relative;
    padding-top: 44px;
}

.decade-section-number {
    pointer-events: none;
}

.decade-luck-intro {
    max-width: 760px;
    margin: 0 0 26px;
    color: var(--muted);
    font-size: 0.95rem;
    line-height: 1.9;
}

.decade-luck-meta {
    display: grid;
    grid-template-columns:
        repeat(
            3,
            minmax(0, 1fr)
        );
    gap: 1px;
    margin-bottom: 26px;
    background: var(--line);
    border: 1px solid var(--line);
}

.decade-luck-meta > div {
    padding: 16px 18px;
    background: #fcfaf6;
}

.decade-luck-meta-label {
    display: block;
    margin-bottom: 5px;
    color: var(--muted);
    font-size: 0.76rem;
    letter-spacing: 0.08em;
}

.decade-luck-meta strong {
    color: var(--deep);
    font-size: 1rem;
    font-weight: 600;
}

.decade-luck-table-wrap {
    width: 100%;
    overflow-x: auto;
}

.decade-luck-table {
    width: 100%;
    border-collapse: collapse;
    border-top: 1px solid var(--line);
    border-bottom: 1px solid var(--line);
}

.decade-luck-table th {
    padding: 11px 10px;
    color: var(--muted);
    background: #fcfaf6;
    border-bottom: 1px solid var(--line);
    text-align: left;
    font-size: 0.78rem;
    font-weight: 500;
    letter-spacing: 0.05em;
}

.decade-luck-table td {
    padding: 13px 10px;
    border-bottom: 1px solid var(--line);
    vertical-align: middle;
    font-size: 0.88rem;
}

.decade-luck-table tbody tr:last-child td {
    border-bottom: 0;
}

.decade-luck-index {
    width: 46px;
    color: var(--muted);
    text-align: center;
}

.decade-luck-age {
    white-space: nowrap;
}

.decade-luck-ganzhi {
    color: var(--deep);
    font-size: 1.05rem !important;
    font-weight: 600;
    white-space: nowrap;
}

.decade-luck-current td {
    background: var(--accent-soft);
}

.decade-luck-current
.decade-luck-ganzhi {
    color: var(--accent);
}

.decade-current-badge {
    display: inline-block;
    margin-left: 8px;
    padding: 2px 7px;
    color: #ffffff;
    background: var(--accent);
    border-radius: 999px;
    font-size: 0.67rem;
    line-height: 1.5;
    vertical-align: middle;
    letter-spacing: 0.04em;
}

.decade-luck-note {
    margin: 22px 0 0;
    padding-top: 16px;
    color: var(--muted);
    border-top: 1px dotted var(--line);
    font-size: 0.82rem;
    line-height: 1.8;
}

'''


# ============================================================
# Mobile CSS
# ============================================================

DECADE_LUCK_MOBILE_CSS = r'''
    .decade-luck-meta {
        grid-template-columns: 1fr;
    }

    .decade-luck-table {
        min-width: 580px;
    }

'''


# ============================================================
# Print CSS
# ============================================================

DECADE_LUCK_PRINT_CSS = r'''
    /*
     * v1.1
     * 大運一覧だけは複数ページへの分割を許可する。
     */
    .decade-luck-card {
        break-inside: auto;
        page-break-inside: auto;
    }

    .decade-luck-meta {
        break-inside: avoid;
        page-break-inside: avoid;
    }

    .decade-luck-table {
        break-inside: auto;
        page-break-inside: auto;
    }

    .decade-luck-table tr {
        break-inside: avoid;
        page-break-inside: avoid;
    }

    .decade-luck-table thead {
        display: table-header-group;
    }

    .decade-luck-table-wrap {
        overflow: visible;
    }

'''


# ============================================================
# Anchors
# ============================================================

FUNCTION_ANCHOR = """
def _render_overall_summary(
"""

CSS_ANCHOR = """
.overall-card {
"""

MOBILE_ANCHOR = """
    .info-grid,
    .chart-summary-grid,
    .luck-grid {
"""

PRINT_CARD_ANCHOR = """    .reading-card {
        margin-bottom: 8mm;
        padding: 8mm;
        border-radius: 0;
        break-inside: avoid;
        page-break-inside: avoid;
    }
"""

RENDER_ORDER_OLD = """{_render_sections(product)}

{_render_disclaimer(product)}"""

RENDER_ORDER_NEW = """{_render_sections(product)}

{_render_decade_luck(product)}

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
            f"{name} の挿入位置が"
            f"{count}件見つかりました。"
            "想定は1件です。"
            "ファイルを変更せず終了します。"
        )


def main() -> None:
    if not TARGET.exists():
        raise FileNotFoundError(
            f"対象ファイルがありません: {TARGET}"
        )

    original = TARGET.read_text(
        encoding="utf-8"
    )

    # --------------------------------------------------------
    # 二重適用防止
    # --------------------------------------------------------

    if (
        "def _render_decade_luck("
        in original
    ):
        raise RuntimeError(
            "すでに _render_decade_luck() が"
            "存在します。"
            "二重適用を防ぐため終了します。"
        )

    if (
        ".decade-luck-card"
        in original
    ):
        raise RuntimeError(
            "すでに大運用CSSが存在します。"
            "二重適用を防ぐため終了します。"
        )

    # --------------------------------------------------------
    # Anchor validation
    # --------------------------------------------------------

    require_once(
        original,
        FUNCTION_ANCHOR,
        "FUNCTION_ANCHOR",
    )

    require_once(
        original,
        CSS_ANCHOR,
        "CSS_ANCHOR",
    )

    require_once(
        original,
        MOBILE_ANCHOR,
        "MOBILE_ANCHOR",
    )

    require_once(
        original,
        PRINT_CARD_ANCHOR,
        "PRINT_CARD_ANCHOR",
    )

    render_order_count = (
        original.count(
            RENDER_ORDER_OLD
        )
    )

    if render_order_count != 2:
        raise RuntimeError(
            "HTML描画順の対象が"
            f"{render_order_count}件でした。"
            "完全HTML＋fragmentの"
            "2件を想定しています。"
            "ファイルを変更せず終了します。"
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
            "backup:",
            BACKUP,
        )
    else:
        print(
            "backup already exists:",
            BACKUP,
        )

    patched = original

    # --------------------------------------------------------
    # 1. Renderer function
    # --------------------------------------------------------

    patched = patched.replace(
        FUNCTION_ANCHOR,
        DECADE_LUCK_FUNCTION
        + "\n"
        + FUNCTION_ANCHOR,
        1,
    )

    # --------------------------------------------------------
    # 2. Main CSS
    # --------------------------------------------------------

    patched = patched.replace(
        CSS_ANCHOR,
        "\n"
        + DECADE_LUCK_CSS
        + CSS_ANCHOR,
        1,
    )

    # --------------------------------------------------------
    # 3. Mobile CSS
    # --------------------------------------------------------

    patched = patched.replace(
        MOBILE_ANCHOR,
        DECADE_LUCK_MOBILE_CSS
        + MOBILE_ANCHOR,
        1,
    )

    # --------------------------------------------------------
    # 4. Print CSS
    #    通常 .reading-card の print rule より後に
    #    decade override を置くことが重要。
    # --------------------------------------------------------

    patched = patched.replace(
        PRINT_CARD_ANCHOR,
        PRINT_CARD_ANCHOR
        + "\n"
        + DECADE_LUCK_PRINT_CSS,
        1,
    )

    # --------------------------------------------------------
    # 5. HTML document + fragment
    #
    # 8セクション
    # ↓
    # 大運
    # ↓
    # 免責
    #
    # 免責は最後のまま。
    # --------------------------------------------------------

    patched = patched.replace(
        RENDER_ORDER_OLD,
        RENDER_ORDER_NEW,
    )

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    if (
        patched.count(
            "{_render_decade_luck(product)}"
        )
        != 2
    ):
        raise RuntimeError(
            "大運rendererの呼び出し数が"
            "2件ではありません。"
        )

    if (
        patched.count(
            "def _render_decade_luck("
        )
        != 1
    ):
        raise RuntimeError(
            "_render_decade_luck() の"
            "定義数が不正です。"
        )

    if (
        patched.count(
            ".decade-luck-card"
        )
        < 2
    ):
        raise RuntimeError(
            "大運CSSが正しく"
            "追加されていません。"
        )

    # Python syntax validation
    ast.parse(
        patched
    )

    # --------------------------------------------------------
    # Write
    # --------------------------------------------------------

    TARGET.write_text(
        patched,
        encoding="utf-8",
    )

    print()
    print("=" * 72)
    print("v1.1 大運一覧 renderer patch 完了")
    print("=" * 72)
    print()
    print("target:")
    print(TARGET)
    print()
    print("追加:")
    print("  ✓ _render_decade_luck()")
    print("  ✓ 大運一覧CSS")
    print("  ✓ モバイルCSS")
    print("  ✓ A4印刷CSS")
    print("  ✓ HTML document")
    print("  ✓ HTML fragment")
    print("  ✓ 現在大運ハイライト")
    print("  ✓ 免責事項は最後のまま")
    print()
    print("Python syntax: OK")
    print()
    print("次に実行:")
    print(
        "python -m pytest "
        "tests/test_reading_renderer.py "
        "tests/test_reading_renderer_five_year_luck.py -q"
    )


if __name__ == "__main__":
    main()
  
