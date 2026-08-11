"""
engine/annual_luck.py

四柱推命 歳運（流年）計算エンジン v1

担当範囲
--------
1. 指定年の歳運干支を算出
2. 天干・地支へ分解
3. 天干の五行・陰陽
4. 地支の五行
5. 日主に対する通変星
6. 十二運
7. 蔵干
8. 蔵干通変星
9. 本気蔵干
10. useful_gods_v3 との関係
11. current_luck_v1 との関係
12. 将来の「大運 × 歳運」統合判定用データ生成

重要
----
歳運干支は既存の engine.ganzhi と
engine.year の計算基準に合わせる。

1984年 = 甲子 = index 0

そのため、

    2024年 = 甲辰
    2025年 = 乙巳
    2026年 = 丙午
    2027年 = 丁未

となる。

本モジュールでは
「対象年そのものの歳運」を扱う。

年初の立春境界を含めて
特定日時の歳運を求めたい場合は、
calculate_annual_luck_for_datetime()
を使用する。

Version:
    annual_luck_v1
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from engine.ganzhi import (
    ganzhi_from_index,
    split_ganzhi,
)
from engine.hidden_stems import (
    get_hidden_stems,
    get_main_hidden_stem,
)
from engine.ten_gods import (
    calculate_ten_god,
    get_element,
    get_yin_yang,
)
from engine.twelve_stages import (
    calculate_twelve_stage,
)
from engine.year import (
    BASE_YEAR,
    BASE_YEAR_GANZHI_INDEX,
    calculate_effective_year,
)


# =========================================================
# Constants
# =========================================================


ANNUAL_LUCK_METHOD = (
    "annual_luck_v1"
)


ANNUAL_LUCK_STATUS = (
    "provisional_annual_luck_v1"
)


FIVE_ELEMENTS = {
    "木",
    "火",
    "土",
    "金",
    "水",
}


BRANCH_ELEMENTS = {
    "子": "水",
    "丑": "土",
    "寅": "木",
    "卯": "木",
    "辰": "土",
    "巳": "火",
    "午": "火",
    "未": "土",
    "申": "金",
    "酉": "金",
    "戌": "土",
    "亥": "水",
}


GENERATES = {
    "木": "火",
    "火": "土",
    "土": "金",
    "金": "水",
    "水": "木",
}


CONTROLS = {
    "木": "土",
    "火": "金",
    "土": "水",
    "金": "木",
    "水": "火",
}


# =========================================================
# Validation
# =========================================================


def _validate_year(
    year: int,
) -> None:
    """
    西暦年を検証する。
    """

    if not isinstance(
        year,
        int,
    ):
        raise TypeError(
            "yearは整数で指定してください。"
        )

    if isinstance(
        year,
        bool,
    ):
        raise TypeError(
            "yearは整数で指定してください。"
        )

    if year < 1:
        raise ValueError(
            "yearは1以上で指定してください。"
        )


def _validate_datetime(
    value: datetime,
    name: str,
) -> None:
    """
    datetime 型を検証する。
    """

    if not isinstance(
        value,
        datetime,
    ):
        raise TypeError(
            f"{name}はdatetime型で指定してください。"
        )


def _validate_element(
    element: str,
) -> None:
    """
    五行を検証する。
    """

    if element not in FIVE_ELEMENTS:
        raise ValueError(
            f"不正な五行です: {element}"
        )


# =========================================================
# Annual Ganzhi
# =========================================================


def calculate_annual_ganzhi(
    year: int,
) -> str:
    """
    指定西暦年の歳運干支を返す。

    1984年 = 甲子 = index 0
    を基準に六十干支を循環させる。

    Examples
    --------
    1984 -> 甲子
    2024 -> 甲辰
    2025 -> 乙巳
    2026 -> 丙午
    """

    _validate_year(
        year
    )

    elapsed_years = (
        year
        - BASE_YEAR
    )

    ganzhi_index = (
        BASE_YEAR_GANZHI_INDEX
        + elapsed_years
    )

    return ganzhi_from_index(
        ganzhi_index
    )


def calculate_annual_ganzhi_for_datetime(
    target_datetime: datetime,
) -> Dict[str, Any]:
    """
    指定日時の立春境界を考慮して
    有効な歳運年・干支を返す。

    現在の year.py に合わせ、
    天文学的に計算された実際の立春時刻を使用する。

    例:
        2026-01-20
            -> effective_year = 2025
            -> 乙巳

        2026-02-10
            -> effective_year = 2026
            -> 丙午
    """

    _validate_datetime(
        target_datetime,
        "target_datetime",
    )

    effective_year = (
        calculate_effective_year(
            target_datetime
        )
    )

    ganzhi = calculate_annual_ganzhi(
        effective_year
    )

    return {
        "calendar_year": (
            target_datetime.year
        ),
        "effective_year": (
            effective_year
        ),
        "ganzhi": ganzhi,
    }


# =========================================================
# Branch helpers
# =========================================================


def get_branch_element(
    branch: str,
) -> str:
    """
    地支の五行を返す。
    """

    if branch not in BRANCH_ELEMENTS:
        raise ValueError(
            f"不正な地支です: {branch}"
        )

    return BRANCH_ELEMENTS[
        branch
    ]


# =========================================================
# Five-element relationship
# =========================================================


def get_element_relationship(
    source_element: str,
    target_element: str,
) -> str:
    """
    2つの五行関係を返す。

    Returns
    -------
    same
    generates
    generated_by
    controls
    controlled_by
    """

    _validate_element(
        source_element
    )

    _validate_element(
        target_element
    )

    if (
        source_element
        == target_element
    ):
        return "same"

    if (
        GENERATES[
            source_element
        ]
        == target_element
    ):
        return "generates"

    if (
        GENERATES[
            target_element
        ]
        == source_element
    ):
        return "generated_by"

    if (
        CONTROLS[
            source_element
        ]
        == target_element
    ):
        return "controls"

    if (
        CONTROLS[
            target_element
        ]
        == source_element
    ):
        return "controlled_by"

    raise ValueError(
        "五行関係を判定できません。"
    )


# =========================================================
# Useful gods
# =========================================================


def evaluate_element_against_useful_gods(
    element: str,
    useful_gods: Optional[
        Dict[str, Any]
    ],
) -> Dict[str, Any]:
    """
    五行と useful_gods_v3 の関係を評価する。

    luck_pillars_v2 と同様の意味構造を持たせる。

    useful_gods が未指定の場合でも
    歳運計算そのものは可能。
    """

    _validate_element(
        element
    )

    if not useful_gods:
        return {
            "is_useful": None,
            "is_primary_useful": None,
            "is_unfavorable": None,
            "priority": None,
            "relationship": "unknown",
        }

    primary = useful_gods.get(
        "primary_useful_element"
    )

    final_elements = useful_gods.get(
        "final_useful_elements",
        [],
    )

    if not isinstance(
        final_elements,
        list,
    ):
        final_elements = []

    if element == primary:
        return {
            "is_useful": True,
            "is_primary_useful": True,
            "is_unfavorable": False,
            "priority": 1,
            "relationship": (
                "primary_useful"
            ),
        }

    if element in final_elements:
        return {
            "is_useful": True,
            "is_primary_useful": False,
            "is_unfavorable": False,
            "priority": (
                final_elements.index(
                    element
                )
                + 1
            ),
            "relationship": (
                "secondary_useful"
            ),
        }

    support_balance = useful_gods.get(
        "support_balance",
        {},
    )

    if not isinstance(
        support_balance,
        dict,
    ):
        support_balance = {}

    unfavorable_elements = (
        support_balance.get(
            "unfavorable_elements",
            [],
        )
    )

    if not isinstance(
        unfavorable_elements,
        list,
    ):
        unfavorable_elements = []

    if element in unfavorable_elements:
        return {
            "is_useful": False,
            "is_primary_useful": False,
            "is_unfavorable": True,
            "priority": None,
            "relationship": (
                "support_unfavorable"
            ),
        }

    neutral_elements = (
        support_balance.get(
            "neutral_elements",
            [],
        )
    )

    if not isinstance(
        neutral_elements,
        list,
    ):
        neutral_elements = []

    if element in neutral_elements:
        return {
            "is_useful": False,
            "is_primary_useful": False,
            "is_unfavorable": False,
            "priority": None,
            "relationship": "neutral",
        }

    return {
        "is_useful": False,
        "is_primary_useful": False,
        "is_unfavorable": False,
        "priority": None,
        "relationship": "neutral",
    }


# =========================================================
# Current luck relation
# =========================================================


def evaluate_against_current_luck(
    *,
    annual_stem_element: str,
    annual_branch_element: str,
    current_luck: Optional[
        Dict[str, Any]
    ],
) -> Dict[str, Any]:
    """
    歳運と現在大運の五行関係を返す。

    current_luck_v1 が未指定の場合は
    unknown とする。

    注意
    ----
    ここでは吉凶を断定しない。

    大運天干・地支と歳運天干・地支の
    五行関係を構造化して返すだけ。

    将来の integrated_luck で
    合・冲・刑・害などを加味する。
    """

    _validate_element(
        annual_stem_element
    )

    _validate_element(
        annual_branch_element
    )

    if not current_luck:
        return {
            "has_current_luck": None,
            "current_luck_ganzhi": None,
            "current_luck_stem_element": None,
            "current_luck_branch_element": None,
            "stem_element_relation": (
                "unknown"
            ),
            "branch_element_relation": (
                "unknown"
            ),
            "status": "unknown",
        }

    has_current = current_luck.get(
        "has_current_luck"
    )

    current_pillar = current_luck.get(
        "current_luck_pillar"
    )

    if (
        not has_current
        or not isinstance(
            current_pillar,
            dict,
        )
    ):
        return {
            "has_current_luck": False,
            "current_luck_ganzhi": None,
            "current_luck_stem_element": None,
            "current_luck_branch_element": None,
            "stem_element_relation": (
                "unknown"
            ),
            "branch_element_relation": (
                "unknown"
            ),
            "status": (
                "no_current_luck"
            ),
        }

    current_stem_element = (
        current_pillar.get(
            "stem_element"
        )
    )

    current_branch_element = (
        current_pillar.get(
            "branch_element"
        )
    )

    # 簡易fixture等で五行がない場合は、
    # stem / branch から補完できる範囲だけ補完する。
    if current_stem_element is None:
        current_stem = (
            current_pillar.get(
                "stem"
            )
        )

        if current_stem:
            current_stem_element = (
                get_element(
                    current_stem
                )
            )

    if current_branch_element is None:
        current_branch = (
            current_pillar.get(
                "branch"
            )
        )

        if current_branch:
            current_branch_element = (
                get_branch_element(
                    current_branch
                )
            )

    if (
        current_stem_element
        not in FIVE_ELEMENTS
    ):
        stem_relation = "unknown"
    else:
        stem_relation = (
            get_element_relationship(
                current_stem_element,
                annual_stem_element,
            )
        )

    if (
        current_branch_element
        not in FIVE_ELEMENTS
    ):
        branch_relation = "unknown"
    else:
        branch_relation = (
            get_element_relationship(
                current_branch_element,
                annual_branch_element,
            )
        )

    return {
        "has_current_luck": True,
        "current_luck_ganzhi": (
            current_pillar.get(
                "ganzhi"
            )
        ),
        "current_luck_index": (
            current_pillar.get(
                "index"
            )
        ),
        "current_luck_stem_element": (
            current_stem_element
        ),
        "current_luck_branch_element": (
            current_branch_element
        ),
        "stem_element_relation": (
            stem_relation
        ),
        "branch_element_relation": (
            branch_relation
        ),
        "status": "evaluated",
    }


# =========================================================
# Hidden stems
# =========================================================


def build_hidden_stem_data(
    *,
    day_master_stem: str,
    branch: str,
) -> Dict[str, Any]:
    """
    歳運地支の蔵干情報を構築する。
    """

    hidden_stems = get_hidden_stems(
        branch
    )

    main_hidden_stem = (
        get_main_hidden_stem(
            branch
        )
    )

    hidden_stem_ten_gods = [
        {
            "stem": hidden_stem,
            "ten_god": calculate_ten_god(
                day_master_stem,
                hidden_stem,
            ),
            "element": get_element(
                hidden_stem
            ),
            "yin_yang": get_yin_yang(
                hidden_stem
            ),
        }
        for hidden_stem
        in hidden_stems
    ]

    return {
        "hidden_stems": (
            hidden_stems
        ),
        "main_hidden_stem": (
            main_hidden_stem
        ),
        "main_hidden_stem_ten_god": (
            calculate_ten_god(
                day_master_stem,
                main_hidden_stem,
            )
        ),
        "main_hidden_stem_element": (
            get_element(
                main_hidden_stem
            )
        ),
        "hidden_stem_ten_gods": (
            hidden_stem_ten_gods
        ),
    }


# =========================================================
# Evidence / reasoning
# =========================================================


def build_annual_luck_reasoning(
    *,
    year: int,
    ganzhi: str,
    stem_ten_god: str,
    twelve_stage: str,
    stem_useful_relation: Dict[
        str,
        Any,
    ],
    branch_useful_relation: Dict[
        str,
        Any,
    ],
) -> List[str]:
    """
    AI鑑定前段階で利用できる
    技術的な reasoning を生成する。

    吉凶断定は行わない。
    """

    reasoning: List[str] = []

    reasoning.append(
        (
            f"{year}年の歳運干支は"
            f"{ganzhi}です。"
        )
    )

    reasoning.append(
        (
            "歳運天干の日主に対する"
            f"通変星は{stem_ten_god}です。"
        )
    )

    reasoning.append(
        (
            "歳運地支の日主に対する"
            f"十二運は{twelve_stage}です。"
        )
    )

    stem_relationship = (
        stem_useful_relation.get(
            "relationship"
        )
    )

    branch_relationship = (
        branch_useful_relation.get(
            "relationship"
        )
    )

    reasoning.append(
        (
            "歳運天干五行の用神関係は"
            f"{stem_relationship}です。"
        )
    )

    reasoning.append(
        (
            "歳運地支五行の用神関係は"
            f"{branch_relationship}です。"
        )
    )

    return reasoning


# =========================================================
# Core builder
# =========================================================


def build_annual_luck(
    *,
    year: int,
    day_master_stem: str,
    useful_gods: Optional[
        Dict[str, Any]
    ] = None,
    current_luck: Optional[
        Dict[str, Any]
    ] = None,
) -> Dict[str, Any]:
    """
    指定年の歳運データを構築する。

    Parameters
    ----------
    year:
        歳運として評価する西暦年。

    day_master_stem:
        日主天干。

    useful_gods:
        useful_gods_v3。
        任意。

    current_luck:
        current_luck_v1。
        任意。
    """

    _validate_year(
        year
    )

    # get_element 内で天干チェックも行われる。
    day_master_element = (
        get_element(
            day_master_stem
        )
    )

    ganzhi = (
        calculate_annual_ganzhi(
            year
        )
    )

    parts = split_ganzhi(
        ganzhi
    )

    stem = parts[
        "stem"
    ]

    branch = parts[
        "branch"
    ]

    stem_element = (
        get_element(
            stem
        )
    )

    stem_yin_yang = (
        get_yin_yang(
            stem
        )
    )

    branch_element = (
        get_branch_element(
            branch
        )
    )

    stem_ten_god = (
        calculate_ten_god(
            day_master_stem,
            stem,
        )
    )

    twelve_stage = (
        calculate_twelve_stage(
            day_master_stem,
            branch,
        )
    )

    hidden_stem_data = (
        build_hidden_stem_data(
            day_master_stem=(
                day_master_stem
            ),
            branch=branch,
        )
    )

    stem_useful_relation = (
        evaluate_element_against_useful_gods(
            stem_element,
            useful_gods,
        )
    )

    branch_useful_relation = (
        evaluate_element_against_useful_gods(
            branch_element,
            useful_gods,
        )
    )

    current_luck_relation = (
        evaluate_against_current_luck(
            annual_stem_element=(
                stem_element
            ),
            annual_branch_element=(
                branch_element
            ),
            current_luck=current_luck,
        )
    )

    reasoning = (
        build_annual_luck_reasoning(
            year=year,
            ganzhi=ganzhi,
            stem_ten_god=(
                stem_ten_god
            ),
            twelve_stage=(
                twelve_stage
            ),
            stem_useful_relation=(
                stem_useful_relation
            ),
            branch_useful_relation=(
                branch_useful_relation
            ),
        )
    )

    evidence = {
        "year": year,
        "ganzhi": ganzhi,
        "day_master_stem": (
            day_master_stem
        ),
        "day_master_element": (
            day_master_element
        ),
        "stem_ten_god": (
            stem_ten_god
        ),
        "twelve_stage": (
            twelve_stage
        ),
        "stem_useful_relation": (
            stem_useful_relation
        ),
        "branch_useful_relation": (
            branch_useful_relation
        ),
        "current_luck_relation": (
            current_luck_relation
        ),
    }

    return {
        "year": year,
        "ganzhi": ganzhi,
        "stem": stem,
        "branch": branch,
        "stem_element": (
            stem_element
        ),
        "stem_yin_yang": (
            stem_yin_yang
        ),
        "branch_element": (
            branch_element
        ),
        "day_master_stem": (
            day_master_stem
        ),
        "day_master_element": (
            day_master_element
        ),
        "stem_ten_god": (
            stem_ten_god
        ),
        "twelve_stage": (
            twelve_stage
        ),
        "hidden_stems": (
            hidden_stem_data[
                "hidden_stems"
            ]
        ),
        "main_hidden_stem": (
            hidden_stem_data[
                "main_hidden_stem"
            ]
        ),
        "main_hidden_stem_ten_god": (
            hidden_stem_data[
                "main_hidden_stem_ten_god"
            ]
        ),
        "main_hidden_stem_element": (
            hidden_stem_data[
                "main_hidden_stem_element"
            ]
        ),
        "hidden_stem_ten_gods": (
            hidden_stem_data[
                "hidden_stem_ten_gods"
            ]
        ),
        "stem_useful_relation": (
            stem_useful_relation
        ),
        "branch_useful_relation": (
            branch_useful_relation
        ),
        "current_luck_relation": (
            current_luck_relation
        ),
        "reasoning": reasoning,
        "evidence": evidence,
        "method": (
            ANNUAL_LUCK_METHOD
        ),
        "status": (
            ANNUAL_LUCK_STATUS
        ),
        "notes": [
            (
                "歳運干支は1984年甲子を"
                "基準に六十干支を循環させています。"
            ),
            (
                "年単位の calculate_annual_luck() は"
                "対象年そのものの干支を返します。"
            ),
            (
                "立春前後を含む特定日時の判定には"
                "calculate_annual_luck_for_datetime() "
                "を使用します。"
            ),
            (
                "立春境界は現在の year.py に合わせて"
                "天文学的に計算された実際の立春時刻です。"
            ),
            (
                "current_luck_relation は現段階では"
                "五行関係のみを扱い、"
                "吉凶を断定しません。"
            ),
            (
                "干合・支合・冲・刑・害などとの"
                "統合判定は後続モジュールで実装します。"
            ),
        ],
    }


# =========================================================
# Main API
# =========================================================


def calculate_annual_luck(
    *,
    year: int,
    day_master_stem: str,
    useful_gods: Optional[
        Dict[str, Any]
    ] = None,
    current_luck: Optional[
        Dict[str, Any]
    ] = None,
) -> Dict[str, Any]:
    """
    指定年の歳運を計算する。

    Example
    -------
    result = calculate_annual_luck(
        year=2026,
        day_master_stem="乙",
        useful_gods=useful_gods,
        current_luck=current_luck,
    )

    2026年:
        丙午
    """

    return build_annual_luck(
        year=year,
        day_master_stem=(
            day_master_stem
        ),
        useful_gods=useful_gods,
        current_luck=current_luck,
    )


# =========================================================
# Datetime API
# =========================================================


def calculate_annual_luck_for_datetime(
    *,
    target_datetime: datetime,
    day_master_stem: str,
    useful_gods: Optional[
        Dict[str, Any]
    ] = None,
    current_luck: Optional[
        Dict[str, Any]
    ] = None,
) -> Dict[str, Any]:
    """
    指定日時時点の歳運を計算する。

    year.py の天文学的な立春境界を利用する。

    例
    ----
    2026-01-20
        effective_year = 2025
        乙巳

    2026-02-10
        effective_year = 2026
        丙午
    """

    _validate_datetime(
        target_datetime,
        "target_datetime",
    )

    year_info = (
        calculate_annual_ganzhi_for_datetime(
            target_datetime
        )
    )

    result = build_annual_luck(
        year=year_info[
            "effective_year"
        ],
        day_master_stem=(
            day_master_stem
        ),
        useful_gods=useful_gods,
        current_luck=current_luck,
    )

    result[
        "target_datetime"
    ] = target_datetime.isoformat()

    result[
        "calendar_year"
    ] = year_info[
        "calendar_year"
    ]

    result[
        "effective_year"
    ] = year_info[
        "effective_year"
    ]

    result[
        "year_boundary_applied"
    ] = (
        year_info["effective_year"]
        != year_info["calendar_year"]
    )

    result[
        "year_boundary_rule"
    ] = (
        "astronomical_lichun"
    )

    return result


# =========================================================
# Range API
# =========================================================


def calculate_annual_luck_range(
    *,
    start_year: int,
    end_year: int,
    day_master_stem: str,
    useful_gods: Optional[
        Dict[str, Any]
    ] = None,
    current_luck: Optional[
        Dict[str, Any]
    ] = None,
) -> List[
    Dict[str, Any]
]:
    """
    複数年の歳運を一括計算する。

    start_year / end_year は両端を含む。

    Example
    -------
    2025～2027:
        乙巳
        丙午
        丁未
    """

    _validate_year(
        start_year
    )

    _validate_year(
        end_year
    )

    if end_year < start_year:
        raise ValueError(
            "end_yearはstart_year以上で"
            "指定してください。"
        )

    return [
        calculate_annual_luck(
            year=year,
            day_master_stem=(
                day_master_stem
            ),
            useful_gods=(
                useful_gods
            ),
            current_luck=(
                current_luck
            ),
        )
        for year in range(
            start_year,
            end_year + 1,
        )
    ]


# =========================================================
# Compatibility aliases
# =========================================================


def evaluate_annual_luck(
    *,
    year: int,
    day_master_stem: str,
    useful_gods: Optional[
        Dict[str, Any]
    ] = None,
    current_luck: Optional[
        Dict[str, Any]
    ] = None,
) -> Dict[str, Any]:
    """
    calculate_annual_luck() の別名。
    """

    return calculate_annual_luck(
        year=year,
        day_master_stem=(
            day_master_stem
        ),
        useful_gods=useful_gods,
        current_luck=current_luck,
    )


# =========================================================
# Public API
# =========================================================


__all__ = [
    "ANNUAL_LUCK_METHOD",
    "ANNUAL_LUCK_STATUS",
    "FIVE_ELEMENTS",
    "BRANCH_ELEMENTS",
    "GENERATES",
    "CONTROLS",
    "calculate_annual_ganzhi",
    "calculate_annual_ganzhi_for_datetime",
    "get_branch_element",
    "get_element_relationship",
    "evaluate_element_against_useful_gods",
    "evaluate_against_current_luck",
    "build_hidden_stem_data",
    "build_annual_luck_reasoning",
    "build_annual_luck",
    "calculate_annual_luck",
    "calculate_annual_luck_for_datetime",
    "calculate_annual_luck_range",
    "evaluate_annual_luck",
]
