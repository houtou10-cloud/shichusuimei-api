"""
scripts/patch_generate_customer_reading_decade_luck_v1_1.py

四柱推命鑑定書 v1.1
本番顧客鑑定パイプラインへの
大運AI鑑定正式接続パッチ。

対象
----
scripts/generate_customer_reading.py

今回追加する処理
----------------
通常8セクションAI鑑定
    ↓
品質ゲート
    ↓
Auto-Repair
    ↓
最終品質ゲート
    ↓
大運AI鑑定
    ↓
decade_luck_ai.json
    ↓
ReadingProduct

注意
----
このパッチではまだ
ReadingProduct / PDFへの
大運AI文章表示は行わない。

まず大運AI生成を
本番パイプラインへ安全に固定する。

次段階で、

decade_luck_ai
    ↓
ReadingProduct
    ↓
reading_renderer
    ↓
PDF

を接続する。
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
    / "scripts"
    / "generate_customer_reading.py"
)


BACKUP = (
    ROOT
    / "scripts"
    / (
        "generate_customer_reading.py"
        ".bak_v1_1_decade_ai"
    )
)


# ============================================================
# Patch fragments
# ============================================================


# ------------------------------------------------------------
# 1. import
# ------------------------------------------------------------


IMPORT_ANCHOR = """from engine.reading_generator import (
    OPENAI_API_KEY_ENV,
    OPENAI_READING_MODEL_ENV,
    ReadingGenerationResult,
    generate_reading,
    get_default_model,
    has_openai_api_key,
)

"""


IMPORT_REPLACEMENT = """from engine.reading_generator import (
    OPENAI_API_KEY_ENV,
    OPENAI_READING_MODEL_ENV,
    ReadingGenerationResult,
    generate_reading,
    get_default_model,
    has_openai_api_key,
)

from engine.reading_decade_luck import (
    generate_decade_luck_reading,
)

"""


# ------------------------------------------------------------
# 2. filename
# ------------------------------------------------------------


FILENAME_ANCHOR = """AI_READING_FILENAME = (
    "ai_reading.json"
)

QUALITY_REPORT_FILENAME = (
"""


FILENAME_REPLACEMENT = """AI_READING_FILENAME = (
    "ai_reading.json"
)

# ============================================================
# v1.1
# 大運AI鑑定
# ============================================================

DECADE_LUCK_AI_FILENAME = (
    "decade_luck_ai.json"
)

QUALITY_REPORT_FILENAME = (
"""


# ------------------------------------------------------------
# 3. customer output path
# ------------------------------------------------------------


PATH_ANCHOR = """    ai_reading_path = (
        customer_dir
        / AI_READING_FILENAME
    )

    quality_report_path = (
"""


PATH_REPLACEMENT = """    ai_reading_path = (
        customer_dir
        / AI_READING_FILENAME
    )

    # --------------------------------------------------------
    # v1.1
    # 大運AI鑑定JSON
    # --------------------------------------------------------

    decade_luck_ai_path = (
        customer_dir
        / DECADE_LUCK_AI_FILENAME
    )

    quality_report_path = (
"""


# ------------------------------------------------------------
# 4. 大運AI生成
#
# 既存8セクションが
# Quality Gate / Auto-Repairを
# 完全に通過した後へ入れる。
# ------------------------------------------------------------


DECADE_GENERATION_ANCHOR = """    generation_result = (
        final_generation_result
    )

    # --------------------------------------------------------
    # 5. ReadingProduct
"""


DECADE_GENERATION_REPLACEMENT = """    generation_result = (
        final_generation_result
    )

    # --------------------------------------------------------
    # 4.8. 大運AI鑑定
    # --------------------------------------------------------

    print()

    print(
        "4.8. 大運AI鑑定生成"
    )

    decade_luck_result = (
        generate_decade_luck_reading(
            reading_context,
            consultation_context=(
                consultation_context
            ),
            model=model,
            reasoning_effort=(
                REASONING_EFFORT
            ),
            store=STORE,
        )
    )

    # --------------------------------------------------------
    # Result validation
    # --------------------------------------------------------

    if (
        decade_luck_result.status
        != "completed"
    ):
        raise RuntimeError(
            "大運AI鑑定が"
            "completedではありません: "
            f"{decade_luck_result.status}"
        )

    if (
        decade_luck_result.response_status
        not in (
            None,
            "completed",
        )
    ):
        raise RuntimeError(
            "大運AI鑑定の"
            "response_statusが"
            "正常ではありません: "
            f"{decade_luck_result.response_status}"
        )

    decade_luck_data = (
        decade_luck_result.to_dict()
    )

    # --------------------------------------------------------
    # overview
    # --------------------------------------------------------

    decade_overview = (
        decade_luck_data.get(
            "overview"
        )
    )

    if (
        not isinstance(
            decade_overview,
            str,
        )
        or not decade_overview.strip()
    ):
        raise RuntimeError(
            "大運AI鑑定overviewが"
            "空または不正です。"
        )

    # --------------------------------------------------------
    # periods
    # --------------------------------------------------------

    decade_periods = (
        decade_luck_data.get(
            "periods"
        )
    )

    if not isinstance(
        decade_periods,
        list,
    ):
        raise RuntimeError(
            "大運AI鑑定periodsが"
            "配列ではありません。"
        )

    if not decade_periods:
        raise RuntimeError(
            "大運AI鑑定periodsが"
            "空です。"
        )

    # 現在＋未来4大運を基本とする。
    #
    # 生年月日や大運末尾などで
    # 利用可能期間数が少ない場合に備え、
    # ここでは「5件固定」ではなく
    # 1件以上を成立条件とする。
    for position, period in enumerate(
        decade_periods
    ):
        if not isinstance(
            period,
            Mapping,
        ):
            raise RuntimeError(
                "大運AI鑑定periods"
                f"[{position}]が"
                "objectではありません。"
            )

        required_fields = (
            "index",
            "ganzhi",
            "start_age",
            "end_age",
            "title",
            "theme",
            "career",
            "wealth",
            "relationships",
            "caution",
            "advice",
        )

        missing_fields = [
            field
            for field
            in required_fields
            if field
            not in period
        ]

        if missing_fields:
            raise RuntimeError(
                "大運AI鑑定periods"
                f"[{position}]に"
                "必須フィールドがありません: "
                + ", ".join(
                    missing_fields
                )
            )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    save_json(
        decade_luck_ai_path,
        decade_luck_data,
    )

    print(
        "   OK"
    )

    print(
        "   response_status: "
        f"{decade_luck_result.response_status}"
    )

    print(
        "   response_id: "
        f"{decade_luck_result.response_id}"
    )

    print(
        "   period_count: "
        f"{len(decade_periods)}"
    )

    print(
        "   output: "
        f"{decade_luck_ai_path}"
    )

    # --------------------------------------------------------
    # 5. ReadingProduct
"""


# ------------------------------------------------------------
# 5. summary.jsonへ大運AI生成情報を追加
#
# build_summary()自体は変更しない。
# 生成後に安全に追加する。
# ------------------------------------------------------------


SUMMARY_ANCHOR = """    summary[
        "pdf_metadata"
    ] = _json_safe_copy(
        pdf_metadata
    )

    save_json(
"""


SUMMARY_REPLACEMENT = """    summary[
        "pdf_metadata"
    ] = _json_safe_copy(
        pdf_metadata
    )

    # --------------------------------------------------------
    # v1.1
    # 大運AI生成情報
    # --------------------------------------------------------

    summary[
        "decade_luck"
    ] = {
        "path": (
            str(
                decade_luck_ai_path
            )
        ),
        "period_count": (
            len(
                decade_periods
            )
        ),
        "response_status": (
            decade_luck_result
            .response_status
        ),
        "response_id": (
            decade_luck_result
            .response_id
        ),
        "model": (
            decade_luck_result
            .model
        ),
        "method": (
            decade_luck_result
            .method
        ),
        "status": (
            decade_luck_result
            .status
        ),
    }

    save_json(
"""


# ------------------------------------------------------------
# 6. generate_customer_reading() return
# ------------------------------------------------------------


RETURN_ANCHOR = """        "ai_reading_path": (
            ai_reading_path
        ),
        "quality_report_path": (
"""


RETURN_REPLACEMENT = """        "ai_reading_path": (
            ai_reading_path
        ),

        # ----------------------------------------------------
        # v1.1
        # 大運AI鑑定
        # ----------------------------------------------------

        "decade_luck_ai_path": (
            decade_luck_ai_path
        ),

        "decade_luck": (
            deepcopy(
                decade_luck_data
            )
        ),

        "decade_luck_response_status": (
            decade_luck_result
            .response_status
        ),

        "decade_luck_response_id": (
            decade_luck_result
            .response_id
        ),

        "quality_report_path": (
"""


# ------------------------------------------------------------
# 7. console output
# ------------------------------------------------------------


CONSOLE_ANCHOR = """    print(
        "AI Reading JSON:"
    )

    print(
        "  "
        f"{result['ai_reading_path'].resolve()}"
    )

    print()

    print(
        "Quality Report:"
"""


CONSOLE_REPLACEMENT = """    print(
        "AI Reading JSON:"
    )

    print(
        "  "
        f"{result['ai_reading_path'].resolve()}"
    )

    print()

    print(
        "Decade Luck AI JSON:"
    )

    print(
        "  "
        f"{result['decade_luck_ai_path'].resolve()}"
    )

    print(
        "  response_status: "
        f"{result['decade_luck_response_status']}"
    )

    print()

    print(
        "Quality Report:"
"""


# ============================================================
# Helpers
# ============================================================


def require_once(
    text: str,
    anchor: str,
    name: str,
) -> None:
    """
    anchorが必ず1件だけ存在することを確認する。

    0件:
        想定ファイルと違う。

    2件以上:
        誤置換の危険がある。

    どちらの場合も書き込み前に停止する。
    """

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


def replace_once(
    text: str,
    anchor: str,
    replacement: str,
    name: str,
) -> str:
    require_once(
        text,
        anchor,
        name,
    )

    return text.replace(
        anchor,
        replacement,
        1,
    )


# ============================================================
# Main
# ============================================================


def main() -> None:

    # --------------------------------------------------------
    # Target validation
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

    existing_markers = (
        "DECADE_LUCK_AI_FILENAME",
        "decade_luck_ai_path",
        "4.8. 大運AI鑑定生成",
    )

    found_existing = [
        marker
        for marker
        in existing_markers
        if marker
        in original
    ]

    if found_existing:
        raise RuntimeError(
            "generate_customer_reading.py は"
            "すでに大運AI統合済みの"
            "可能性があります。\n"
            "検出: "
            + ", ".join(
                found_existing
            )
            + "\n"
            "二重適用を防ぐため終了します。"
        )

    # --------------------------------------------------------
    # All anchors validation
    #
    # 1つでも不一致なら、
    # ファイルへ一切書き込まない。
    # --------------------------------------------------------

    require_once(
        original,
        IMPORT_ANCHOR,
        "import anchor",
    )

    require_once(
        original,
        FILENAME_ANCHOR,
        "filename anchor",
    )

    require_once(
        original,
        PATH_ANCHOR,
        "path anchor",
    )

    require_once(
        original,
        DECADE_GENERATION_ANCHOR,
        "generation anchor",
    )

    require_once(
        original,
        SUMMARY_ANCHOR,
        "summary anchor",
    )

    require_once(
        original,
        RETURN_ANCHOR,
        "return anchor",
    )

    require_once(
        original,
        CONSOLE_ANCHOR,
        "console anchor",
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

    # --------------------------------------------------------
    # Apply patch in memory
    # --------------------------------------------------------

    patched = original

    patched = replace_once(
        patched,
        IMPORT_ANCHOR,
        IMPORT_REPLACEMENT,
        "import",
    )

    patched = replace_once(
        patched,
        FILENAME_ANCHOR,
        FILENAME_REPLACEMENT,
        "filename",
    )

    patched = replace_once(
        patched,
        PATH_ANCHOR,
        PATH_REPLACEMENT,
        "path",
    )

    patched = replace_once(
        patched,
        DECADE_GENERATION_ANCHOR,
        DECADE_GENERATION_REPLACEMENT,
        "generation",
    )

    patched = replace_once(
        patched,
        SUMMARY_ANCHOR,
        SUMMARY_REPLACEMENT,
        "summary",
    )

    patched = replace_once(
        patched,
        RETURN_ANCHOR,
        RETURN_REPLACEMENT,
        "return",
    )

    patched = replace_once(
        patched,
        CONSOLE_ANCHOR,
        CONSOLE_REPLACEMENT,
        "console",
    )

    # ========================================================
    # Structural validation
    # ========================================================

    required_after_patch = (
        "from engine.reading_decade_luck import (",
        "generate_decade_luck_reading,",
        "DECADE_LUCK_AI_FILENAME",
        "decade_luck_ai_path",
        "decade_luck_result = (",
        "generate_decade_luck_reading(",
        "decade_luck_result.to_dict()",
        '"decade_luck"',
        '"decade_luck_ai_path"',
        '"4.8. 大運AI鑑定生成"',
    )

    for marker in (
        required_after_patch
    ):
        if marker not in patched:
            raise RuntimeError(
                "パッチ後の必須構造が"
                "不足しています: "
                f"{marker}"
            )

    # --------------------------------------------------------
    # Call count
    # --------------------------------------------------------

    if (
        patched.count(
            "generate_decade_luck_reading("
        )
        != 1
    ):
        raise RuntimeError(
            "generate_decade_luck_reading() "
            "の呼び出し数が不正です。"
        )

    # 定数定義＋利用箇所なので
    # 最低2回は存在する必要がある。
    if (
        patched.count(
            "DECADE_LUCK_AI_FILENAME"
        )
        < 2
    ):
        raise RuntimeError(
            "DECADE_LUCK_AI_FILENAME "
            "の利用箇所が不足しています。"
        )

    # --------------------------------------------------------
    # Python syntax
    # --------------------------------------------------------

    try:

        ast.parse(
            patched
        )

    except SyntaxError as exc:

        raise RuntimeError(
            "パッチ後コードの"
            "Python構文チェックに"
            "失敗しました。\n"
            f"{exc}"
        ) from exc

    # --------------------------------------------------------
    # Write
    # --------------------------------------------------------

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
        "v1.1 大運AI "
        "customer pipeline patch 完了"
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
        "  ✓ reading_decade_luck import"
    )

    print(
        "  ✓ DECADE_LUCK_AI_FILENAME"
    )

    print(
        "  ✓ decade_luck_ai_path"
    )

    print(
        "  ✓ 4.8 大運AI鑑定"
    )

    print(
        "  ✓ decade_luck_ai.json 保存"
    )

    print(
        "  ✓ summary.json 大運metadata"
    )

    print(
        "  ✓ return result 大運情報"
    )

    print(
        "  ✓ console output"
    )

    print()

    print(
        "まだ行っていない:"
    )

    print(
        "  - ReadingProductへの"
        "大運AI文章統合"
    )

    print(
        "  - PDFへの"
        "大運AI詳細文章表示"
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
        "tests/test_generate_customer_reading.py "
        "-q"
    )


if __name__ == "__main__":
    main()
