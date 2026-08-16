"""
scripts/patch_generate_customer_reading_decade_luck_v1_1.py

四柱推命鑑定書 v1.1

scripts/generate_customer_reading.py へ
大運AI鑑定を正式接続する一回限りのパッチ。

変更内容
--------
1. reading_decade_luck import追加
2. decade_luck_ai.json ファイル名定数追加
3. 顧客ディレクトリ内の保存パス追加
4. 最終品質ゲート後に大運AI鑑定を生成
5. decade_luck_ai.json 保存
6. ReadingProductへ decade_luck を渡す
7. Python構文チェック
8. 元ファイルをバックアップ
"""

from __future__ import annotations

import ast
from pathlib import Path


# ============================================================
# Paths
# ============================================================


ROOT = Path(
    __file__
).resolve().parents[1]


TARGET = (
    ROOT
    / "scripts"
    / "generate_customer_reading.py"
)


BACKUP = (
    ROOT
    / "scripts"
    / "generate_customer_reading.py.bak_decade_luck_v1_1"
)


# ============================================================
# Patch fragments
# ============================================================


# ------------------------------------------------------------
# 1. Import
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
# 2. Filename constant
# ------------------------------------------------------------


FILENAME_ANCHOR = """AI_READING_FILENAME = (
    "ai_reading.json"
)

QUALITY_REPORT_FILENAME = (
"""


FILENAME_REPLACEMENT = """AI_READING_FILENAME = (
    "ai_reading.json"
)

DECADE_LUCK_AI_FILENAME = (
    "decade_luck_ai.json"
)

QUALITY_REPORT_FILENAME = (
"""


# ------------------------------------------------------------
# 3. Output path
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

    decade_luck_ai_path = (
        customer_dir
        / DECADE_LUCK_AI_FILENAME
    )

    quality_report_path = (
"""


# ------------------------------------------------------------
# 4. Decade luck generation
#
# 最終品質ゲート通過後、
# ReadingProduct生成直前へ入れる。
# ------------------------------------------------------------


DECADE_LUCK_BLOCK_ANCHOR = """    # 以降は必ず最終採用版を使う。
    generation_result = (
        final_generation_result
    )

    # --------------------------------------------------------
    # 5. ReadingProduct
"""


DECADE_LUCK_BLOCK_REPLACEMENT = """    # 以降は必ず最終採用版を使う。
    generation_result = (
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

    if (
        decade_luck_result.status
        != "completed"
    ):
        raise RuntimeError(
            "大運AI鑑定が"
            "completedではありません: "
            f"{decade_luck_result.status}"
        )

    decade_luck_data = (
        decade_luck_result.to_dict()
    )

    decade_luck_periods = (
        decade_luck_data.get(
            "periods",
            [],
        )
    )

    if not isinstance(
        decade_luck_periods,
        list,
    ):
        raise RuntimeError(
            "大運AI鑑定periodsが"
            "配列ではありません。"
        )

    if not decade_luck_periods:
        raise RuntimeError(
            "大運AI鑑定periodsが"
            "空です。"
        )

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
        f"{len(decade_luck_periods)}"
    )

    # --------------------------------------------------------
    # 5. ReadingProduct
"""


# ------------------------------------------------------------
# 5. build_reading_product()
# ------------------------------------------------------------


PRODUCT_CALL_ANCHOR = """            brand_name=(
                BRAND_NAME
            ),
        )
    )
"""


PRODUCT_CALL_REPLACEMENT = """            brand_name=(
                BRAND_NAME
            ),
            decade_luck=(
                decade_luck_data
            ),
        )
    )
"""


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
            "ファイルを変更せず終了します。"
        )


# ============================================================
# Main
# ============================================================


def main() -> None:
    if not TARGET.exists():
        raise FileNotFoundError(
            "対象ファイルがありません: "
            f"{TARGET}"
        )

    original = TARGET.read_text(
        encoding="utf-8"
    )

    # --------------------------------------------------------
    # 二重適用防止
    # --------------------------------------------------------

    if (
        "generate_decade_luck_reading"
        in original
    ):
        raise RuntimeError(
            "generate_customer_reading.py は"
            "すでに大運AI対応済みの"
            "可能性があります。"
            "二重適用を防ぐため終了します。"
        )

    if (
        "DECADE_LUCK_AI_FILENAME"
        in original
    ):
        raise RuntimeError(
            "DECADE_LUCK_AI_FILENAME が"
            "すでに存在します。"
        )

    # --------------------------------------------------------
    # Anchor validation
    # --------------------------------------------------------

    require_once(
        original,
        IMPORT_ANCHOR,
        "reading_generator import",
    )

    require_once(
        original,
        FILENAME_ANCHOR,
        "filename anchor",
    )

    require_once(
        original,
        PATH_ANCHOR,
        "output path anchor",
    )

    require_once(
        original,
        DECADE_LUCK_BLOCK_ANCHOR,
        "final quality gate anchor",
    )

    require_once(
        original,
        PRODUCT_CALL_ANCHOR,
        "build_reading_product anchor",
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
    # 1. import
    # --------------------------------------------------------

    patched = patched.replace(
        IMPORT_ANCHOR,
        IMPORT_REPLACEMENT,
        1,
    )

    # --------------------------------------------------------
    # 2. filename
    # --------------------------------------------------------

    patched = patched.replace(
        FILENAME_ANCHOR,
        FILENAME_REPLACEMENT,
        1,
    )

    # --------------------------------------------------------
    # 3. output path
    # --------------------------------------------------------

    patched = patched.replace(
        PATH_ANCHOR,
        PATH_REPLACEMENT,
        1,
    )

    # --------------------------------------------------------
    # 4. decade luck generation
    # --------------------------------------------------------

    patched = patched.replace(
        DECADE_LUCK_BLOCK_ANCHOR,
        DECADE_LUCK_BLOCK_REPLACEMENT,
        1,
    )

    # --------------------------------------------------------
    # 5. ReadingProduct integration
    # --------------------------------------------------------

    patched = patched.replace(
        PRODUCT_CALL_ANCHOR,
        PRODUCT_CALL_REPLACEMENT,
        1,
    )

    # ========================================================
    # Structural validation
    # ========================================================

    if (
        patched.count(
            "generate_decade_luck_reading("
        )
        != 1
    ):
        raise RuntimeError(
            "generate_decade_luck_reading() の"
            "呼び出し数が不正です。"
        )

    if (
        patched.count(
            "DECADE_LUCK_AI_FILENAME"
        )
        != 2
    ):
        raise RuntimeError(
            "DECADE_LUCK_AI_FILENAME の"
            "出現数が不正です。"
        )

    if (
        patched.count(
            "decade_luck_ai_path"
        )
        < 2
    ):
        raise RuntimeError(
            "decade_luck_ai_path が"
            "正しく追加されていません。"
        )

    if (
        "decade_luck=("
        not in patched
    ):
        raise RuntimeError(
            "ReadingProductへの"
            "decade_luck接続がありません。"
        )

    if (
        '"4.8. 大運AI鑑定生成"'
        not in patched
    ):
        raise RuntimeError(
            "4.8 大運AI鑑定ブロックが"
            "追加されていません。"
        )

    # --------------------------------------------------------
    # Syntax validation
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Completion
    # --------------------------------------------------------

    print()
    print("=" * 72)
    print(
        "v1.1 customer pipeline "
        "大運AI統合 patch 完了"
    )
    print("=" * 72)

    print()
    print("target:")
    print(TARGET)

    print()
    print("追加:")
    print(
        "  ✓ generate_decade_luck_reading import"
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
        "  ✓ ReadingProduct decade_luck接続"
    )

    print()
    print(
        "Python syntax: OK"
    )

    print()
    print("次に実行:")

    print(
        "python -m pytest "
        "tests/test_generate_customer_reading.py -q"
    )


if __name__ == "__main__":
    main()
