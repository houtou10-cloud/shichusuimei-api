"""
scripts/patch_generate_customer_reading_decade_product_v1_1.py

四柱推命鑑定書 v1.1

scripts/generate_customer_reading.py へ、

通常8セクションAI
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
ReadingProduct.decade_luck
    ↓
product.json
    ↓
PDF

という本番経路を追加する。

既存テストのfake build_reading_productが
decade_luck引数に未対応でも壊れないよう、
inspect.signature() で対応可否を判定する。

このパッチではまだ、
reading_renderer.py の
「大運AI詳細文章描画」は追加しない。
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
        ".bak_v1_1_decade_product"
    )
)


# ============================================================
# 1. inspect import
# ============================================================


INSPECT_IMPORT_ANCHOR = """import json
import os
import re
import sys
"""


INSPECT_IMPORT_REPLACEMENT = """import inspect
import json
import os
import re
import sys
"""


# ============================================================
# 2. reading_decade_luck import
# ============================================================


DECADE_IMPORT_ANCHOR = """from engine.reading_generator import (
    OPENAI_API_KEY_ENV,
    OPENAI_READING_MODEL_ENV,
    ReadingGenerationResult,
    generate_reading,
    get_default_model,
    has_openai_api_key,
)

"""


DECADE_IMPORT_REPLACEMENT = """from engine.reading_generator import (
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


# ============================================================
# 3. filename constant
# ============================================================


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


# ============================================================
# 4. output path
# ============================================================


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
    # 大運AI鑑定
    # --------------------------------------------------------

    decade_luck_ai_path = (
        customer_dir
        / DECADE_LUCK_AI_FILENAME
    )

    quality_report_path = (
"""


# ============================================================
# 5. 大運AI生成
#
# 最終品質ゲート通過後、
# ReadingProduct生成前へ挿入する。
# ============================================================


GENERATION_ANCHOR = """    # 以降は必ず最終採用版を使う。
    generation_result = (
        final_generation_result
    )

    # --------------------------------------------------------
    # 5. ReadingProduct
"""


GENERATION_REPLACEMENT = """    # 以降は必ず最終採用版を使う。
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

    # --------------------------------------------------------
    # ReadingProductの後方互換確認
    #
    # 本番build_reading_productは
    # decade_luck対応済み。
    #
    # 一方、既存unit testのfake関数が
    # decade_luck未対応の場合があるため、
    # signatureを確認して安全に分岐する。
    # --------------------------------------------------------

    try:
        product_signature = (
            inspect.signature(
                build_reading_product
            )
        )

        product_parameters = (
            product_signature.parameters
        )

        supports_decade_luck = (
            "decade_luck"
            in product_parameters
            or any(
                parameter.kind
                == inspect.Parameter.VAR_KEYWORD
                for parameter
                in product_parameters.values()
            )
        )

    except (
        TypeError,
        ValueError,
    ):
        # inspect不能なcallableの場合は
        # 本番関数として扱う。
        supports_decade_luck = True

    decade_luck_result = None

    decade_luck_data: Dict[
        str,
        Any,
    ] = {}

    # --------------------------------------------------------
    # 本番ReadingProductが
    # decade_luck対応済みの場合のみ生成する。
    #
    # これにより既存fake pipelineでは
    # 不要な実API呼び出しを防ぐ。
    # --------------------------------------------------------

    if supports_decade_luck:

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

        # ----------------------------------------------------
        # Response status
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # dict化
        # ----------------------------------------------------

        decade_luck_data = (
            decade_luck_result.to_dict()
        )

        if not isinstance(
            decade_luck_data,
            Mapping,
        ):
            raise RuntimeError(
                "大運AI鑑定結果が"
                "Mappingではありません。"
            )

        # ----------------------------------------------------
        # overview
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # periods
        # ----------------------------------------------------

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
                "listではありません。"
            )

        if not decade_periods:
            raise RuntimeError(
                "大運AI鑑定periodsが"
                "空です。"
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
                    "Mappingではありません。"
                )

            missing_fields = [
                field_name
                for field_name
                in required_fields
                if field_name
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

        # ----------------------------------------------------
        # JSON保存
        # ----------------------------------------------------

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

    else:

        # ----------------------------------------------------
        # 既存unit test fakeとの互換モード
        # ----------------------------------------------------

        print(
            "   skipped: "
            "build_reading_productが"
            "decade_luck未対応"
        )

    # --------------------------------------------------------
    # 5. ReadingProduct
"""


# ============================================================
# 6. ReadingProduct接続
#
# 現在の直書きkeyword形式から
# kwargs形式へ変更する。
#
# fake関数がdecade_luck未対応でも
# decade_luckを渡さない。
# ============================================================


PRODUCT_ANCHOR = """    product = (
        build_reading_product(
            reading_context,
            generation_result,
            title=PRODUCT_TITLE,
            sections=SECTIONS,
            customer_name=(
                normalized_intake[
                    "name"
                ]
            ),
            reading_datetime=(
                generation_started_at
            ),
            brand_name=(
                BRAND_NAME
            ),
        )
    )
"""


PRODUCT_REPLACEMENT = """    product_kwargs: Dict[
        str,
        Any,
    ] = {
        "title": PRODUCT_TITLE,
        "sections": SECTIONS,
        "customer_name": (
            normalized_intake[
                "name"
            ]
        ),
        "reading_datetime": (
            generation_started_at
        ),
        "brand_name": (
            BRAND_NAME
        ),
    }

    # --------------------------------------------------------
    # v1.1
    #
    # 本番ReadingProductだけに
    # 大運AI鑑定を渡す。
    # --------------------------------------------------------

    if supports_decade_luck:
        product_kwargs[
            "decade_luck"
        ] = decade_luck_data

    product = (
        build_reading_product(
            reading_context,
            generation_result,
            **product_kwargs,
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

    # ========================================================
    # Double patch prevention
    # ========================================================

    existing_markers = (
        "DECADE_LUCK_AI_FILENAME",
        "generate_decade_luck_reading(",
        "4.8. 大運AI鑑定生成",
        '"decade_luck"',
    )

    found = [
        marker
        for marker
        in existing_markers
        if marker
        in original
    ]

    if found:
        raise RuntimeError(
            "generate_customer_reading.py は"
            "すでに大運AI統合済みの"
            "可能性があります。\n"
            "検出: "
            + ", ".join(
                found
            )
            + "\n"
            "二重適用を防ぐため終了します。"
        )

    # ========================================================
    # Validate every anchor before writing
    # ========================================================

    require_once(
        original,
        INSPECT_IMPORT_ANCHOR,
        "inspect import anchor",
    )

    require_once(
        original,
        DECADE_IMPORT_ANCHOR,
        "decade import anchor",
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
        GENERATION_ANCHOR,
        "generation anchor",
    )

    require_once(
        original,
        PRODUCT_ANCHOR,
        "ReadingProduct anchor",
    )

    # ========================================================
    # Backup
    # ========================================================

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

    patched = replace_once(
        patched,
        INSPECT_IMPORT_ANCHOR,
        INSPECT_IMPORT_REPLACEMENT,
        "inspect import",
    )

    patched = replace_once(
        patched,
        DECADE_IMPORT_ANCHOR,
        DECADE_IMPORT_REPLACEMENT,
        "decade import",
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
        GENERATION_ANCHOR,
        GENERATION_REPLACEMENT,
        "decade generation",
    )

    patched = replace_once(
        patched,
        PRODUCT_ANCHOR,
        PRODUCT_REPLACEMENT,
        "ReadingProduct connection",
    )

    # ========================================================
    # Structural validation
    # ========================================================

    required_markers = (
        "import inspect",
        "from engine.reading_decade_luck import (",
        "generate_decade_luck_reading,",
        "DECADE_LUCK_AI_FILENAME",
        "decade_luck_ai_path",
        "4.8. 大運AI鑑定生成",
        "supports_decade_luck",
        "decade_luck_result",
        "decade_luck_data",
        'product_kwargs[',
        '"decade_luck"',
        "**product_kwargs",
    )

    for marker in required_markers:

        if marker not in patched:
            raise RuntimeError(
                "パッチ後の必須構造が"
                "不足しています: "
                f"{marker}"
            )

    # --------------------------------------------------------
    # API call count
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

    # --------------------------------------------------------
    # decade_luck keyword
    # --------------------------------------------------------

    if (
        'product_kwargs[\n'
        '            "decade_luck"\n'
        '        ]'
        not in patched
    ):
        raise RuntimeError(
            "ReadingProductへの"
            "decade_luck接続がありません。"
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
            "パッチ後コードの"
            "Python構文に問題があります。\n"
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
        "v1.1 大運AI "
        "Customer → Product 統合完了"
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
        "  ✓ 4.8 大運AI鑑定生成"
    )

    print(
        "  ✓ decade_luck_ai.json保存"
    )

    print(
        "  ✓ ReadingProduct.decade_luck接続"
    )

    print(
        "  ✓ fake pipeline後方互換"
    )

    print()

    print(
        "現在のデータ経路:"
    )

    print(
        "  reading_context"
    )

    print(
        "      ↓"
    )

    print(
        "  generate_decade_luck_reading"
    )

    print(
        "      ↓"
    )

    print(
        "  decade_luck_ai.json"
    )

    print(
        "      ↓"
    )

    print(
        "  ReadingProduct.decade_luck"
    )

    print(
        "      ↓"
    )

    print(
        "  product.json"
    )

    print()

    print(
        "まだ残っている最後の工程:"
    )

    print(
        "  ReadingProduct.decade_luck"
    )

    print(
        "      ↓"
    )

    print(
        "  reading_renderer.py"
    )

    print(
        "      ↓"
    )

    print(
        "  PDF大運AI詳細鑑定"
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