"""
scripts/patch_reading_product_decade_luck_v1_1.py

四柱推命鑑定書 v1.1

engine/reading_product.py に
大運AI鑑定を正式統合するための
一回限りの安全なパッチ。

変更内容
--------
1. dataclasses.field を追加
2. ReadingProduct.decade_luck を追加
3. to_dict() で大運AI鑑定を出力
4. build_product_decade_luck() を追加
5. build_reading_product() に decade_luck 引数を追加
6. ReadingProductへ大運AI結果を格納
7. __all__ を更新
8. v1.0との後方互換を維持
9. 元ファイルをバックアップ
10. Python構文チェック
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
    / "engine"
    / "reading_product.py"
)


BACKUP = (
    ROOT
    / "engine"
    / "reading_product.py.bak_v1_1_decade_luck"
)


# ============================================================
# Patch fragments
# ============================================================


IMPORT_OLD = (
    "from dataclasses import dataclass\n"
)


IMPORT_NEW = """from dataclasses import (
    dataclass,
    field,
)
"""


# ------------------------------------------------------------
# ReadingProduct field
# ------------------------------------------------------------


DATACLASS_ANCHOR = """    metadata: Dict[str, Any]
    schema_version: str = (
"""


DATACLASS_REPLACEMENT = """    metadata: Dict[str, Any]

    # --------------------------------------------------------
    # v1.1
    # 大運AI鑑定
    #
    # default_factory=dict にすることで、
    # v1.0形式でReadingProductを直接生成している
    # 既存コード・既存テストとの後方互換を維持する。
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
# ReadingProduct.to_dict()
#
# decade_luck が空ならキーそのものを出さない。
# これによりv1.0のserialized contractを極力維持する。
# ------------------------------------------------------------


TO_DICT_ANCHOR = """            "metadata": deepcopy(
                self.metadata
            ),
            "method": self.method,
"""


TO_DICT_REPLACEMENT = """            "metadata": deepcopy(
                self.metadata
            ),

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
# build_product_decade_luck()
# ------------------------------------------------------------


BUILD_PRODUCT_DECADE_LUCK = r'''

def build_product_decade_luck(
    decade_luck: Optional[
        Mapping[str, Any]
    ] = None,
) -> Dict[str, Any]:
    """
    v1.1

    大運AI鑑定をReadingProduct向けに
    安全にコピーする。

    この関数では、

    - 大運を再計算しない
    - 干支を変更しない
    - 年齢を変更しない
    - 通変星を変更しない
    - 五行を変更しない
    - AI文章を書き換えない

    decade_luck=None または空dictは、
    v1.0互換として空dictを返す。
    """

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

    # --------------------------------------------------------
    # overview
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # periods
    # --------------------------------------------------------

    periods = data.get(
        "periods"
    )

    if not isinstance(
        periods,
        list,
    ):
        raise ReadingProductValidationError(
            "decade_luck.periodsは"
            "配列である必要があります。"
        )

    if not periods:
        raise ReadingProductValidationError(
            "decade_luck.periodsが"
            "空です。"
        )

    normalized_periods: List[
        Dict[str, Any]
    ] = []

    # --------------------------------------------------------
    # AIではなくengine側が管理する事実
    # --------------------------------------------------------

    required_fact_fields = (
        "index",
        "ganzhi",
        "start_age",
        "end_age",
    )

    # --------------------------------------------------------
    # AI鑑定文章
    # --------------------------------------------------------

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
                "objectである必要があります。"
            )

        item = deepcopy(
            dict(
                period
            )
        )

        # ----------------------------------------------------
        # Protected facts existence
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
                "不正です。"
            )

        # ----------------------------------------------------
        # Ages
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

        start_age = item.get(
            "start_age"
        )

        end_age = item.get(
            "end_age"
        )

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
        # Interpretation text
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
        # Advice
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
                "配列である必要があります。"
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

        normalized_periods.append(
            item
        )

    # --------------------------------------------------------
    # index uniqueness
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # index order
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Result
    # --------------------------------------------------------

    result = deepcopy(
        data
    )

    result[
        "overview"
    ] = overview

    result[
        "periods"
    ] = normalized_periods

    return result
'''


BUILD_FUNCTION_ANCHOR = (
    "\ndef build_reading_product(\n"
)


# ------------------------------------------------------------
# build_reading_product signature
# ------------------------------------------------------------


SIGNATURE_ANCHOR = """    reading_datetime: Any = None,
    brand_name: Optional[str] = None,
) -> ReadingProduct:
"""


SIGNATURE_REPLACEMENT = """    reading_datetime: Any = None,
    brand_name: Optional[str] = None,
    decade_luck: Optional[
        Mapping[str, Any]
    ] = None,
) -> ReadingProduct:
"""


# ------------------------------------------------------------
# ReadingProduct construction
# ------------------------------------------------------------


RETURN_METADATA_ANCHOR = """        metadata=build_product_metadata(
            reading_context,
            created_at=(
                reading_datetime
            ),
            brand_name=brand_name,
        ),
    )
"""


RETURN_METADATA_REPLACEMENT = """        metadata=build_product_metadata(
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
# __all__
# ------------------------------------------------------------


ALL_ANCHOR = (
    '    "build_product_metadata",\n'
    '    "build_reading_product",\n'
)


ALL_REPLACEMENT = (
    '    "build_product_metadata",\n'
    '    "build_product_decade_luck",\n'
    '    "build_reading_product",\n'
)


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
        "def build_product_decade_luck("
        in original
    ):
        raise RuntimeError(
            "build_product_decade_luck() は"
            "すでに存在します。"
            "二重適用を防ぐため終了します。"
        )

    if (
        "decade_luck: Dict["
        in original
    ):
        raise RuntimeError(
            "ReadingProduct.decade_luck が"
            "すでに存在する可能性があります。"
            "二重適用を防ぐため終了します。"
        )

    # --------------------------------------------------------
    # Anchor validation
    # --------------------------------------------------------

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
        RETURN_METADATA_ANCHOR,
        "ReadingProduct return anchor",
    )

    require_once(
        original,
        ALL_ANCHOR,
        "__all__ anchor",
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
    # 1. dataclasses.field
    # --------------------------------------------------------

    patched = patched.replace(
        IMPORT_OLD,
        IMPORT_NEW,
        1,
    )

    # --------------------------------------------------------
    # 2. ReadingProduct.decade_luck
    # --------------------------------------------------------

    patched = patched.replace(
        DATACLASS_ANCHOR,
        DATACLASS_REPLACEMENT,
        1,
    )

    # --------------------------------------------------------
    # 3. to_dict()
    # --------------------------------------------------------

    patched = patched.replace(
        TO_DICT_ANCHOR,
        TO_DICT_REPLACEMENT,
        1,
    )

    # --------------------------------------------------------
    # 4. build_product_decade_luck()
    # --------------------------------------------------------

    patched = patched.replace(
        BUILD_FUNCTION_ANCHOR,
        (
            BUILD_PRODUCT_DECADE_LUCK
            + "\n"
            + BUILD_FUNCTION_ANCHOR
        ),
        1,
    )

    # --------------------------------------------------------
    # 5. build_reading_product signature
    # --------------------------------------------------------

    patched = patched.replace(
        SIGNATURE_ANCHOR,
        SIGNATURE_REPLACEMENT,
        1,
    )

    # --------------------------------------------------------
    # 6. ReadingProduct construction
    # --------------------------------------------------------

    patched = patched.replace(
        RETURN_METADATA_ANCHOR,
        RETURN_METADATA_REPLACEMENT,
        1,
    )

    # --------------------------------------------------------
    # 7. __all__
    # --------------------------------------------------------

    patched = patched.replace(
        ALL_ANCHOR,
        ALL_REPLACEMENT,
        1,
    )

    # ========================================================
    # Final structural validation
    # ========================================================

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

    if (
        patched.count(
            '"decade_luck": deepcopy('
        )
        != 1
    ):
        raise RuntimeError(
            "to_dict() のdecade_luckが"
            "正しく追加されていません。"
        )

    if (
        patched.count(
            "build_product_decade_luck("
        )
        < 2
    ):
        raise RuntimeError(
            "大運AIの商品統合が"
            "正しく追加されていません。"
        )

    if (
        '"build_product_decade_luck",'
        not in patched
    ):
        raise RuntimeError(
            "__all__ に"
            "build_product_decade_luckが"
            "ありません。"
        )

    # --------------------------------------------------------
    # Python syntax validation
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
        "v1.1 ReadingProduct "
        "大運AI統合 patch 完了"
    )
    print("=" * 72)

    print()
    print("target:")
    print(TARGET)

    print()
    print("追加:")
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
        "  ✓ ReadingProductへの"
        "大運AI格納"
    )
    print(
        "  ✓ __all__"
    )

    print()
    print("後方互換:")
    print(
        "  ✓ decade_luck未指定時は空dict"
    )
    print(
        "  ✓ 空の場合to_dict()へ"
        "decade_luckを出さない"
    )

    print()
    print(
        "Python syntax: OK"
    )

    print()
    print("次に実行:")

    print(
        "python -m pytest "
        "tests/test_reading_product.py -q"
    )


if __name__ == "__main__":
    main()
