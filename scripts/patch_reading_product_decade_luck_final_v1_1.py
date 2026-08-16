"""
scripts/patch_reading_product_decade_luck_final_v1_1.py

四柱推命鑑定書 v1.1

engine/reading_product.py に
大運AI鑑定を正式統合する最終パッチ。

目的
----
計算済み大運:
    ReadingProduct.chart_summary["luck_pillars"]

AIによる大運解釈:
    ReadingProduct.decade_luck

として責務を分離する。

今回の変更
----------
1. dataclasses.field を追加
2. ReadingProduct.decade_luck を追加
3. ReadingProduct.to_dict() に decade_luck を追加
4. build_product_decade_luck() を追加
5. build_reading_product() に decade_luck 引数を追加
6. ReadingProduct(...) に decade_luck を格納
7. __all__ に build_product_decade_luck を追加
8. 元ファイルをバックアップ
9. AST構文チェック

後方互換
--------
decade_luck=None または空dictの場合は、
従来のv1.0と同じく大運AIなしで動作する。

このレイヤーでは占術再計算を行わない。
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
    / "reading_product.py"
)


BACKUP = (
    ROOT
    / "engine"
    / "reading_product.py.bak_v1_1_decade_luck_final"
)


# ============================================================
# Patch fragments
# ============================================================


# ------------------------------------------------------------
# 1. dataclasses import
# ------------------------------------------------------------


IMPORT_OLD = (
    "from dataclasses import dataclass\n"
)


IMPORT_NEW = """from dataclasses import (
    dataclass,
    field,
)
"""


# ------------------------------------------------------------
# 2. ReadingProduct field
# ------------------------------------------------------------


DATACLASS_ANCHOR = """    generation: Dict[str, Any]
    metadata: Dict[str, Any]
    schema_version: str = (
"""


DATACLASS_REPLACEMENT = """    generation: Dict[str, Any]
    metadata: Dict[str, Any]

    # --------------------------------------------------------
    # v1.1
    # 大運AI鑑定
    #
    # chart_summary["luck_pillars"] は計算済み事実。
    # decade_luck はAIによる解釈。
    #
    # default_factory=dict により
    # 既存v1.0呼び出しとの後方互換を維持する。
    # --------------------------------------------------------

    decade_luck: Dict[
        str,
        Any,
    ] = field(
        default_factory=dict
    )

    schema_version: str = (
"""


# ------------------------------------------------------------
# 3. to_dict()
# ------------------------------------------------------------


TO_DICT_ANCHOR = """            "metadata": deepcopy(
                self.metadata
            ),
            "method": self.method,
"""


TO_DICT_REPLACEMENT = """            "metadata": deepcopy(
                self.metadata
            ),

            # ------------------------------------------------
            # v1.1
            # 大運AI鑑定
            #
            # 空の場合は既存JSON互換のため
            # キー自体を出力しない。
            # ------------------------------------------------

            **(
                {
                    "decade_luck": deepcopy(
                        self.decade_luck
                    )
                }
                if self.decade_luck
                else {}
            ),

            "method": self.method,
"""


# ------------------------------------------------------------
# 4. build_product_decade_luck()
# ------------------------------------------------------------


BUILD_DECADE_FUNCTION = r'''

def build_product_decade_luck(
    decade_luck: Optional[
        Mapping[str, Any]
    ] = None,
) -> Dict[str, Any]:
    """
    v1.1

    reading_decade_luck.py が生成した
    大運AI鑑定結果をReadingProduct向けに
    検証・コピーする。

    この関数では占術再計算を行わない。

    Parameters
    ----------
    decade_luck:
        ReadingDecadeLuckResult.to_dict()
        相当のMapping。

        Noneまたは空Mappingの場合は
        空dictを返す。

    Returns
    -------
    Dict[str, Any]
        商品格納用の大運AI鑑定。
    """

    # --------------------------------------------------------
    # Backward compatibility
    # --------------------------------------------------------

    if decade_luck is None:
        return {}

    if not isinstance(
        decade_luck,
        Mapping,
    ):
        raise TypeError(
            "decade_luckは"
            "MappingまたはNoneで"
            "指定してください。"
        )

    data = deepcopy(
        dict(
            decade_luck
        )
    )

    if not data:
        return {}

    # ========================================================
    # overview
    # ========================================================

    overview = data.get(
        "overview"
    )

    if not isinstance(
        overview,
        str,
    ):
        raise ReadingProductValidationError(
            "decade_luck.overviewは"
            "文字列である必要があります。"
        )

    overview = (
        overview.strip()
    )

    if not overview:
        raise ReadingProductValidationError(
            "decade_luck.overviewが"
            "空です。"
        )

    # ========================================================
    # periods
    # ========================================================

    periods = data.get(
        "periods"
    )

    if not isinstance(
        periods,
        list,
    ):
        raise ReadingProductValidationError(
            "decade_luck.periodsは"
            "listである必要があります。"
        )

    if not periods:
        raise ReadingProductValidationError(
            "decade_luck.periodsが"
            "空です。"
        )

    normalized_periods: List[
        Dict[str, Any]
    ] = []

    required_fact_fields = (
        "index",
        "ganzhi",
        "start_age",
        "end_age",
    )

    required_text_fields = (
        "title",
        "theme",
        "career",
        "wealth",
        "relationships",
        "caution",
    )

    for position, period in enumerate(
        periods
    ):

        if not isinstance(
            period,
            Mapping,
        ):
            raise ReadingProductValidationError(
                "decade_luck.periods"
                f"[{position}]は"
                "Mappingである必要があります。"
            )

        item = deepcopy(
            dict(
                period
            )
        )

        # ----------------------------------------------------
        # Required engine facts
        # ----------------------------------------------------

        for field_name in (
            required_fact_fields
        ):

            if (
                field_name
                not in item
            ):
                raise ReadingProductValidationError(
                    "decade_luck.periods"
                    f"[{position}]."
                    f"{field_name}"
                    "がありません。"
                )

        # ----------------------------------------------------
        # index
        # ----------------------------------------------------

        index_value = item.get(
            "index"
        )

        if (
            isinstance(
                index_value,
                bool,
            )
            or not isinstance(
                index_value,
                int,
            )
        ):
            raise ReadingProductValidationError(
                "decade_luck.periods"
                f"[{position}].indexは"
                "整数である必要があります。"
            )

        if index_value <= 0:
            raise ReadingProductValidationError(
                "decade_luck.periods"
                f"[{position}].indexは"
                "1以上である必要があります。"
            )

        # ----------------------------------------------------
        # ganzhi
        # ----------------------------------------------------

        ganzhi = item.get(
            "ganzhi"
        )

        if (
            not isinstance(
                ganzhi,
                str,
            )
            or not ganzhi.strip()
        ):
            raise ReadingProductValidationError(
                "decade_luck.periods"
                f"[{position}].ganzhiが"
                "空または不正です。"
            )

        # ----------------------------------------------------
        # ages
        # ----------------------------------------------------

        for age_field in (
            "start_age",
            "end_age",
        ):

            age_value = item.get(
                age_field
            )

            if (
                isinstance(
                    age_value,
                    bool,
                )
                or not isinstance(
                    age_value,
                    (int, float),
                )
            ):
                raise ReadingProductValidationError(
                    "decade_luck.periods"
                    f"[{position}]."
                    f"{age_field}は"
                    "数値である必要があります。"
                )

        start_age = item[
            "start_age"
        ]

        end_age = item[
            "end_age"
        ]

        if (
            start_age
            >= end_age
        ):
            raise ReadingProductValidationError(
                "decade_luck.periods"
                f"[{position}]の"
                "start_age / end_ageが"
                "不正です。"
            )

        # ----------------------------------------------------
        # AI text fields
        # ----------------------------------------------------

        for field_name in (
            required_text_fields
        ):

            value = item.get(
                field_name
            )

            if (
                not isinstance(
                    value,
                    str,
                )
                or not value.strip()
            ):
                raise ReadingProductValidationError(
                    "decade_luck.periods"
                    f"[{position}]."
                    f"{field_name}が"
                    "空または不正です。"
                )

        # ----------------------------------------------------
        # advice
        # ----------------------------------------------------

        advice = item.get(
            "advice"
        )

        if not isinstance(
            advice,
            list,
        ):
            raise ReadingProductValidationError(
                "decade_luck.periods"
                f"[{position}].adviceは"
                "listである必要があります。"
            )

        if not (
            2
            <= len(
                advice
            )
            <= 3
        ):
            raise ReadingProductValidationError(
                "decade_luck.periods"
                f"[{position}].adviceは"
                "2〜3件必要です。"
            )

        normalized_advice: List[
            str
        ] = []

        for (
            advice_position,
            advice_item,
        ) in enumerate(
            advice
        ):

            if (
                not isinstance(
                    advice_item,
                    str,
                )
                or not advice_item.strip()
            ):
                raise ReadingProductValidationError(
                    "decade_luck.periods"
                    f"[{position}].advice"
                    f"[{advice_position}]が"
                    "空または不正です。"
                )

            normalized_advice.append(
                advice_item.strip()
            )

        # ----------------------------------------------------
        # Normalize whitespace only
        # ----------------------------------------------------

        item[
            "ganzhi"
        ] = ganzhi.strip()

        for field_name in (
            required_text_fields
        ):

            item[
                field_name
            ] = (
                item[
                    field_name
                ].strip()
            )

        item[
            "advice"
        ] = normalized_advice

        normalized_periods.append(
            item
        )

    # ========================================================
    # index duplicate / order validation
    # ========================================================

    indexes = [
        item[
            "index"
        ]
        for item
        in normalized_periods
    ]

    if (
        len(
            indexes
        )
        != len(
            set(
                indexes
            )
        )
    ):
        raise ReadingProductValidationError(
            "decade_luck.periodsの"
            "indexが重複しています。"
        )

    if (
        indexes
        != sorted(
            indexes
        )
    ):
        raise ReadingProductValidationError(
            "decade_luck.periodsの"
            "index順序が不正です。"
        )

    # ========================================================
    # generation metadata
    # ========================================================

    generation = data.get(
        "generation"
    )

    if (
        generation is not None
        and not isinstance(
            generation,
            Mapping,
        )
    ):
        raise ReadingProductValidationError(
            "decade_luck.generationは"
            "Mappingである必要があります。"
        )

    # ========================================================
    # optional metadata strings
    # ========================================================

    for optional_text_field in (
        "version",
        "method",
        "status",
    ):

        value = data.get(
            optional_text_field
        )

        if (
            value is not None
            and not isinstance(
                value,
                str,
            )
        ):
            raise ReadingProductValidationError(
                "decade_luck."
                f"{optional_text_field}は"
                "文字列である必要があります。"
            )

    # ========================================================
    # result
    # ========================================================

    result = deepcopy(
        data
    )

    result[
        "overview"
    ] = overview

    result[
        "periods"
    ] = normalized_periods

    if isinstance(
        generation,
        Mapping,
    ):
        result[
            "generation"
        ] = deepcopy(
            dict(
                generation
            )
        )

    return result
'''


BUILD_FUNCTION_ANCHOR = (
    "\ndef build_reading_product(\n"
)


# ------------------------------------------------------------
# 5. build_reading_product signature
# ------------------------------------------------------------


SIGNATURE_ANCHOR = """    customer_name: Optional[str] = None,
    reading_datetime: Any = None,
    brand_name: Optional[str] = None,
) -> ReadingProduct:
"""


SIGNATURE_REPLACEMENT = """    customer_name: Optional[str] = None,
    reading_datetime: Any = None,
    brand_name: Optional[str] = None,
    decade_luck: Optional[
        Mapping[str, Any]
    ] = None,
) -> ReadingProduct:
"""


# ------------------------------------------------------------
# 6. ReadingProduct construction
# ------------------------------------------------------------


PRODUCT_CONSTRUCTION_ANCHOR = """        metadata=build_product_metadata(
            reading_context,
            created_at=(
                reading_datetime
            ),
            brand_name=brand_name,
        ),
    )
"""


PRODUCT_CONSTRUCTION_REPLACEMENT = """        metadata=build_product_metadata(
            reading_context,
            created_at=(
                reading_datetime
            ),
            brand_name=brand_name,
        ),

        decade_luck=(
            build_product_decade_luck(
                decade_luck
            )
        ),
    )
"""


# ------------------------------------------------------------
# 7. __all__
# ------------------------------------------------------------


ALL_ANCHOR = """    "build_generation_metadata",
    "build_product_metadata",
    "build_reading_product",
"""


ALL_REPLACEMENT = """    "build_generation_metadata",
    "build_product_metadata",
    "build_product_decade_luck",
    "build_reading_product",
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
    # target
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
    # double patch prevention
    # ========================================================

    existing_markers = (
        "def build_product_decade_luck(",
        "decade_luck: Dict[",
        '"decade_luck": deepcopy(',
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
            "reading_product.py は"
            "すでに大運AI対応済みの"
            "可能性があります。\n"
            "検出: "
            + ", ".join(
                found
            )
            + "\n"
            "二重適用を防ぐため終了します。"
        )

    # ========================================================
    # validate anchors
    # ========================================================

    require_once(
        original,
        IMPORT_OLD,
        "dataclasses import",
    )

    require_once(
        original,
        DATACLASS_ANCHOR,
        "ReadingProduct field anchor",
    )

    require_once(
        original,
        TO_DICT_ANCHOR,
        "ReadingProduct.to_dict anchor",
    )

    require_once(
        original,
        BUILD_FUNCTION_ANCHOR,
        "build_reading_product anchor",
    )

    require_once(
        original,
        SIGNATURE_ANCHOR,
        "build_reading_product signature",
    )

    require_once(
        original,
        PRODUCT_CONSTRUCTION_ANCHOR,
        "ReadingProduct construction",
    )

    require_once(
        original,
        ALL_ANCHOR,
        "__all__ anchor",
    )

    # ========================================================
    # backup
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
    # apply patch in memory
    # ========================================================

    patched = original

    patched = replace_once(
        patched,
        IMPORT_OLD,
        IMPORT_NEW,
        "dataclasses import",
    )

    patched = replace_once(
        patched,
        DATACLASS_ANCHOR,
        DATACLASS_REPLACEMENT,
        "ReadingProduct.decade_luck",
    )

    patched = replace_once(
        patched,
        TO_DICT_ANCHOR,
        TO_DICT_REPLACEMENT,
        "ReadingProduct.to_dict",
    )

    patched = replace_once(
        patched,
        BUILD_FUNCTION_ANCHOR,
        (
            BUILD_DECADE_FUNCTION
            + "\n"
            + BUILD_FUNCTION_ANCHOR
        ),
        "build_product_decade_luck",
    )

    patched = replace_once(
        patched,
        SIGNATURE_ANCHOR,
        SIGNATURE_REPLACEMENT,
        "build_reading_product signature",
    )

    patched = replace_once(
        patched,
        PRODUCT_CONSTRUCTION_ANCHOR,
        PRODUCT_CONSTRUCTION_REPLACEMENT,
        "ReadingProduct construction",
    )

    patched = replace_once(
        patched,
        ALL_ANCHOR,
        ALL_REPLACEMENT,
        "__all__",
    )

    # ========================================================
    # structural validation
    # ========================================================

    required_markers = (
        "from dataclasses import (",
        "field,",
        "decade_luck: Dict[",
        '"decade_luck": deepcopy(',
        "def build_product_decade_luck(",
        "decade_luck: Optional[",
        "build_product_decade_luck(",
        '"build_product_decade_luck",',
    )

    for marker in (
        required_markers
    ):

        if marker not in patched:
            raise RuntimeError(
                "パッチ後の必須構造が"
                "不足しています: "
                f"{marker}"
            )

    # --------------------------------------------------------
    # counts
    # --------------------------------------------------------

    if (
        patched.count(
            "def build_product_decade_luck("
        )
        != 1
    ):
        raise RuntimeError(
            "build_product_decade_luck() の"
            "定義数が不正です。"
        )

    if (
        patched.count(
            "decade_luck: Dict["
        )
        != 1
    ):
        raise RuntimeError(
            "ReadingProduct.decade_luck の"
            "定義数が不正です。"
        )

    # ========================================================
    # AST validation
    # ========================================================

    try:

        ast.parse(
            patched
        )

    except SyntaxError as exc:

        raise RuntimeError(
            "パッチ後のreading_product.pyに"
            "Python構文エラーがあります。\n"
            f"{exc}"
        ) from exc

    # ========================================================
    # write
    # ========================================================

    TARGET.write_text(
        patched,
        encoding="utf-8",
    )

    # ========================================================
    # completion
    # ========================================================

    print()

    print(
        "=" * 72
    )

    print(
        "v1.1 ReadingProduct "
        "大運AI統合 final patch 完了"
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
        "  ✓ dataclasses.field"
    )

    print(
        "  ✓ ReadingProduct.decade_luck"
    )

    print(
        "  ✓ to_dict() decade_luck"
    )

    print(
        "  ✓ build_product_decade_luck()"
    )

    print(
        "  ✓ build_reading_product("
        "decade_luck=...)"
    )

    print(
        "  ✓ ReadingProduct(...)へ格納"
    )

    print(
        "  ✓ __all__"
    )

    print()

    print(
        "設計:"
    )

    print(
        "  ✓ luck_pillars = 計算事実"
    )

    print(
        "  ✓ decade_luck = AI解釈"
    )

    print(
        "  ✓ 占術再計算なし"
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
        "tests/test_reading_product.py -q"
    )


if __name__ == "__main__":
    main()
