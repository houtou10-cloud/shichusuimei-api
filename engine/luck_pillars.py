"""
engine/luck_pillars.py

四柱推命 大運計算エンジン v2

担当範囲
--------
1. 大運の順行・逆行判定
2. 月柱を基準とした大運干支生成
3. solar_terms_v2 から対象節入りを自動取得
4. 外部指定 target_term_datetime との後方互換
5. 大運開始年齢の計算
6. 大運開始日時の概算
7. 各大運の年齢範囲
8. 各大運の十神
9. 各大運の五行
10. useful_gods との簡易関係判定

重要
----
大運開始年齢は節入り日時に依存する。

v2 では通常、
target_term_datetime を指定する必要はない。

年干・性別から順行／逆行を判定し、
engine.solar_terms の
get_luck_pillar_target_term()
を利用して対象節入りを自動取得する。

ただし既存コードとの互換性を維持するため、
target_term_datetime を明示的に指定した場合は
その値を優先する。

これにより、

    target_term_datetime 指定あり
        -> external_input

    target_term_datetime 指定なし
        -> solar_terms_v2

という2つの経路を利用できる。

Version:
    luck_pillars_v2
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from engine.solar_terms import (
    get_luck_pillar_target_term,
)


# =========================================================
# Constants
# =========================================================


HEAVENLY_STEMS = [
    "甲",
    "乙",
    "丙",
    "丁",
    "戊",
    "己",
    "庚",
    "辛",
    "壬",
    "癸",
]


EARTHLY_BRANCHES = [
    "子",
    "丑",
    "寅",
    "卯",
    "辰",
    "巳",
    "午",
    "未",
    "申",
    "酉",
    "戌",
    "亥",
]


ELEMENTS = [
    "木",
    "火",
    "土",
    "金",
    "水",
]


STEM_TO_ELEMENT = {
    "甲": "木",
    "乙": "木",
    "丙": "火",
    "丁": "火",
    "戊": "土",
    "己": "土",
    "庚": "金",
    "辛": "金",
    "壬": "水",
    "癸": "水",
}


STEM_TO_YIN_YANG = {
    "甲": "陽",
    "乙": "陰",
    "丙": "陽",
    "丁": "陰",
    "戊": "陽",
    "己": "陰",
    "庚": "陽",
    "辛": "陰",
    "壬": "陽",
    "癸": "陰",
}


BRANCH_TO_ELEMENT = {
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


# 六十干支
SEXAGENARY_CYCLE = [
    (
        HEAVENLY_STEMS[index % 10]
        + EARTHLY_BRANCHES[index % 12]
    )
    for index in range(60)
]


# =========================================================
# Five-element relations
# =========================================================


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


GENERATED_BY = {
    generated: generator
    for generator, generated
    in GENERATES.items()
}


CONTROLLED_BY = {
    controlled: controller
    for controller, controlled
    in CONTROLS.items()
}


# =========================================================
# Data class
# =========================================================


@dataclass(frozen=True)
class LuckPillar:
    """
    1本の大運を表す内部データ。
    """

    index: int
    stem: str
    branch: str
    ganzhi: str
    start_age: float
    end_age: float
    start_datetime: Optional[datetime]
    end_datetime: Optional[datetime]


# =========================================================
# Validation
# =========================================================


def _validate_stem(
    stem: str,
) -> None:
    if stem not in HEAVENLY_STEMS:
        raise ValueError(
            f"不正な天干です: {stem}"
        )


def _validate_branch(
    branch: str,
) -> None:
    if branch not in EARTHLY_BRANCHES:
        raise ValueError(
            f"不正な地支です: {branch}"
        )


def _validate_gender(
    gender: str,
) -> None:
    if gender not in {
        "male",
        "female",
        "男",
        "女",
    }:
        raise ValueError(
            f"不正な性別です: {gender}"
        )


def _validate_datetime(
    value: datetime,
    name: str,
) -> None:
    if not isinstance(
        value,
        datetime,
    ):
        raise TypeError(
            f"{name} は datetime が必要です"
        )


def _normalize_gender(
    gender: str,
) -> str:
    _validate_gender(
        gender
    )

    if gender in {
        "male",
        "男",
    }:
        return "male"

    return "female"


# =========================================================
# Ganzhi helpers
# =========================================================


def split_ganzhi(
    ganzhi: str,
) -> tuple[str, str]:
    """
    干支文字列を天干・地支へ分割する。

    Example
    -------
    >>> split_ganzhi("辛未")
    ("辛", "未")
    """

    if not isinstance(
        ganzhi,
        str,
    ):
        raise ValueError(
            f"干支は文字列で指定してください: {ganzhi}"
        )

    if len(
        ganzhi
    ) != 2:
        raise ValueError(
            f"不正な干支です: {ganzhi}"
        )

    stem = ganzhi[0]
    branch = ganzhi[1]

    _validate_stem(
        stem
    )

    _validate_branch(
        branch
    )

    return (
        stem,
        branch,
    )


def get_sexagenary_index(
    ganzhi: str,
) -> int:
    """
    六十干支中の位置を返す。
    """

    if ganzhi not in SEXAGENARY_CYCLE:
        raise ValueError(
            f"六十干支に存在しない干支です: {ganzhi}"
        )

    return SEXAGENARY_CYCLE.index(
        ganzhi
    )


def shift_ganzhi(
    ganzhi: str,
    steps: int,
) -> str:
    """
    干支を六十干支上で移動する。

    正数:
        順行

    負数:
        逆行
    """

    index = get_sexagenary_index(
        ganzhi
    )

    new_index = (
        index + steps
    ) % 60

    return SEXAGENARY_CYCLE[
        new_index
    ]


# =========================================================
# Direction
# =========================================================


def determine_luck_direction(
    year_stem: str,
    gender: str,
) -> str:
    """
    大運の順行・逆行を判定する。

    基本ルール
    ----------
    陽年生まれ男性 -> 順行
    陰年生まれ女性 -> 順行

    陰年生まれ男性 -> 逆行
    陽年生まれ女性 -> 逆行

    Returns
    -------
    "forward"
    または
    "backward"
    """

    _validate_stem(
        year_stem
    )

    normalized_gender = (
        _normalize_gender(
            gender
        )
    )

    yin_yang = STEM_TO_YIN_YANG[
        year_stem
    ]

    if (
        yin_yang == "陽"
        and normalized_gender == "male"
    ):
        return "forward"

    if (
        yin_yang == "陰"
        and normalized_gender == "female"
    ):
        return "forward"

    return "backward"


# =========================================================
# Solar-term integration
# =========================================================


def resolve_target_term(
    *,
    birth_datetime: datetime,
    direction: str,
    target_term_datetime: Optional[
        datetime
    ] = None,
) -> Dict[str, Any]:
    """
    大運開始年齢計算に使う対象節入りを決定する。

    target_term_datetime が指定された場合:
        外部指定値を優先する。

    target_term_datetime が None の場合:
        solar_terms_v2 から自動取得する。
    """

    _validate_datetime(
        birth_datetime,
        "birth_datetime",
    )

    if direction not in {
        "forward",
        "backward",
    }:
        raise ValueError(
            f"不正な大運方向です: {direction}"
        )

    if target_term_datetime is not None:
        _validate_datetime(
            target_term_datetime,
            "target_term_datetime",
        )

        return {
            "target_term_datetime": target_term_datetime,
            "target_term_name": None,
            "target_term_month": None,
            "target_term_branch": None,
            "target_term_source": "external_input",
        }

    target_term = get_luck_pillar_target_term(
        birth_datetime,
        direction,
    )

    return {
        "target_term_datetime": target_term.datetime,
        "target_term_name": target_term.name,
        "target_term_month": target_term.datetime.month,
        "target_term_branch": target_term.month_branch,
        "target_term_source": "solar_terms_v2",
    }


# =========================================================
# Start-age calculation
# =========================================================


def calculate_term_distance_days(
    birth_datetime: datetime,
    target_term_datetime: datetime,
) -> float:
    """
    出生日時から対象節入り日時までの
    日数差の絶対値を返す。
    """

    _validate_datetime(
        birth_datetime,
        "birth_datetime",
    )

    _validate_datetime(
        target_term_datetime,
        "target_term_datetime",
    )

    delta = (
        target_term_datetime
        - birth_datetime
    )

    return abs(
        delta.total_seconds()
    ) / 86400.0


def calculate_start_age(
    birth_datetime: datetime,
    target_term_datetime: datetime,
) -> float:
    """
    大運開始年齢を計算する。

    三日一年法
    --------
    節入りまで3日 = 1年
    1日 = 4か月
    2時間 = 約10日

    内部ではまず、
        日数差 / 3
    により年単位へ変換する。

    Returns
    -------
    float
        大運開始年齢。
    """

    distance_days = (
        calculate_term_distance_days(
            birth_datetime,
            target_term_datetime,
        )
    )

    start_age = (
        distance_days / 3.0
    )

    return round(
        start_age,
        6,
    )


def age_to_year_month_day(
    age: float,
) -> Dict[str, int]:
    """
    小数年齢を、
    年・月・日の概算へ変換する。

    大運表示用であり、
    天文暦の厳密な年月日変換ではない。
    """

    if age < 0:
        raise ValueError(
            "年齢は0以上である必要があります"
        )

    years = int(
        age
    )

    remaining_year = (
        age - years
    )

    months_float = (
        remaining_year * 12.0
    )

    months = int(
        months_float
    )

    days = round(
        (
            months_float
            - months
        )
        * 30.0
    )

    if days >= 30:
        days = 0
        months += 1

    if months >= 12:
        months = 0
        years += 1

    return {
        "years": years,
        "months": months,
        "days": days,
    }


def estimate_start_datetime(
    birth_datetime: datetime,
    start_age: float,
) -> datetime:
    """
    開始年齢から大運開始日時を概算する。

    1年 = 365.2425日として換算。

    正確な暦日というより、
    API表示・範囲管理用の概算値。
    """

    _validate_datetime(
        birth_datetime,
        "birth_datetime",
    )

    if start_age < 0:
        raise ValueError(
            "start_age は0以上である必要があります"
        )

    days = (
        start_age
        * 365.2425
    )

    return (
        birth_datetime
        + timedelta(
            days=days
        )
    )


# =========================================================
# Ten gods
# =========================================================


def get_element_relation(
    day_master_element: str,
    target_element: str,
) -> str:
    """
    日主五行と対象五行の関係を返す。
    """

    if day_master_element not in ELEMENTS:
        raise ValueError(
            f"不正な五行です: {day_master_element}"
        )

    if target_element not in ELEMENTS:
        raise ValueError(
            f"不正な五行です: {target_element}"
        )

    if (
        target_element
        == day_master_element
    ):
        return "same"

    if (
        GENERATED_BY[
            day_master_element
        ]
        == target_element
    ):
        return "resource"

    if (
        GENERATES[
            day_master_element
        ]
        == target_element
    ):
        return "output"

    if (
        CONTROLS[
            day_master_element
        ]
        == target_element
    ):
        return "wealth"

    if (
        CONTROLLED_BY[
            day_master_element
        ]
        == target_element
    ):
        return "officer"

    raise ValueError(
        "五行関係を判定できません"
    )


def get_ten_god_for_stem(
    day_master_stem: str,
    target_stem: str,
) -> str:
    """
    日主天干から対象天干の通変星を返す。

    陰陽の同異も考慮する。
    """

    _validate_stem(
        day_master_stem
    )

    _validate_stem(
        target_stem
    )

    day_element = STEM_TO_ELEMENT[
        day_master_stem
    ]

    target_element = STEM_TO_ELEMENT[
        target_stem
    ]

    day_yin_yang = STEM_TO_YIN_YANG[
        day_master_stem
    ]

    target_yin_yang = STEM_TO_YIN_YANG[
        target_stem
    ]

    same_polarity = (
        day_yin_yang
        == target_yin_yang
    )

    relation = get_element_relation(
        day_element,
        target_element,
    )

    if relation == "same":
        return (
            "比肩"
            if same_polarity
            else "劫財"
        )

    if relation == "resource":
        return (
            "偏印"
            if same_polarity
            else "印綬"
        )

    if relation == "output":
        return (
            "食神"
            if same_polarity
            else "傷官"
        )

    if relation == "wealth":
        return (
            "偏財"
            if same_polarity
            else "正財"
        )

    if relation == "officer":
        return (
            "偏官"
            if same_polarity
            else "正官"
        )

    raise ValueError(
        "通変星を判定できません"
    )


# =========================================================
# Useful-god relationship
# =========================================================


def evaluate_element_against_useful_gods(
    element: str,
    useful_gods: Optional[
        Dict[str, Any]
    ],
) -> Dict[str, Any]:
    """
    五行が useful_gods_v3 の
    最終用神候補に含まれるかを判定する。

    useful_gods が未指定でも
    大運計算そのものは可能。
    """

    if element not in ELEMENTS:
        raise ValueError(
            f"不正な五行です: {element}"
        )

    if not useful_gods:
        return {
            "is_useful": None,
            "is_primary_useful": None,
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

    if primary == element:
        priority = 1

        return {
            "is_useful": True,
            "is_primary_useful": True,
            "priority": priority,
            "relationship": "primary_useful",
        }

    if element in final_elements:
        priority = (
            final_elements.index(
                element
            )
            + 1
        )

        return {
            "is_useful": True,
            "is_primary_useful": False,
            "priority": priority,
            "relationship": "secondary_useful",
        }

    support = useful_gods.get(
        "support_balance",
        {},
    )

    unfavorable = support.get(
        "unfavorable_elements",
        [],
    )

    if element in unfavorable:
        return {
            "is_useful": False,
            "is_primary_useful": False,
            "priority": None,
            "relationship": "support_unfavorable",
        }

    return {
        "is_useful": False,
        "is_primary_useful": False,
        "priority": None,
        "relationship": "neutral",
    }


# =========================================================
# Pillar generation
# =========================================================


def generate_luck_ganzhi(
    month_ganzhi: str,
    direction: str,
    count: int = 10,
) -> List[str]:
    """
    月柱を基準に大運干支列を生成する。

    月柱そのものは第1大運に含めない。

    Example
    -------
    辛未・順行:
        壬申
        癸酉
        甲戌
        ...

    辛未・逆行:
        庚午
        己巳
        戊辰
        ...
    """

    if direction not in {
        "forward",
        "backward",
    }:
        raise ValueError(
            f"不正な大運方向です: {direction}"
        )

    if not isinstance(
        count,
        int,
    ):
        raise TypeError(
            "count は整数で指定してください"
        )

    if count <= 0:
        raise ValueError(
            "count は1以上である必要があります"
        )

    get_sexagenary_index(
        month_ganzhi
    )

    sign = (
        1
        if direction == "forward"
        else -1
    )

    return [
        shift_ganzhi(
            month_ganzhi,
            sign * index,
        )
        for index in range(
            1,
            count + 1,
        )
    ]


# =========================================================
# Single pillar evaluation
# =========================================================


def build_luck_pillar_data(
    *,
    index: int,
    ganzhi: str,
    day_master_stem: str,
    start_age: float,
    birth_datetime: Optional[
        datetime
    ] = None,
    useful_gods: Optional[
        Dict[str, Any]
    ] = None,
) -> Dict[str, Any]:
    """
    1本の大運データを構築する。
    """

    stem, branch = split_ganzhi(
        ganzhi
    )

    _validate_stem(
        day_master_stem
    )

    stem_element = STEM_TO_ELEMENT[
        stem
    ]

    branch_element = BRANCH_TO_ELEMENT[
        branch
    ]

    stem_ten_god = (
        get_ten_god_for_stem(
            day_master_stem,
            stem,
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

    pillar_start_age = (
        start_age
        + (
            (index - 1)
            * 10.0
        )
    )

    pillar_end_age = (
        pillar_start_age
        + 10.0
    )

    start_datetime = None
    end_datetime = None

    if birth_datetime is not None:
        start_datetime = (
            estimate_start_datetime(
                birth_datetime,
                pillar_start_age,
            )
        )

        end_datetime = (
            estimate_start_datetime(
                birth_datetime,
                pillar_end_age,
            )
        )

    return {
        "index": index,
        "ganzhi": ganzhi,
        "stem": stem,
        "branch": branch,
        "stem_element": stem_element,
        "branch_element": branch_element,
        "stem_yin_yang": STEM_TO_YIN_YANG[
            stem
        ],
        "stem_ten_god": stem_ten_god,
        "start_age": round(
            pillar_start_age,
            6,
        ),
        "end_age": round(
            pillar_end_age,
            6,
        ),
        "start_age_detail": (
            age_to_year_month_day(
                pillar_start_age
            )
        ),
        "end_age_detail": (
            age_to_year_month_day(
                pillar_end_age
            )
        ),
        "start_datetime": (
            start_datetime.isoformat()
            if start_datetime
            else None
        ),
        "end_datetime": (
            end_datetime.isoformat()
            if end_datetime
            else None
        ),
        "stem_useful_relation": (
            stem_useful_relation
        ),
        "branch_useful_relation": (
            branch_useful_relation
        ),
    }


# =========================================================
# Main API
# =========================================================


def calculate_luck_pillars(
    *,
    year_stem: str,
    month_ganzhi: str,
    day_master_stem: str,
    gender: str,
    birth_datetime: datetime,
    target_term_datetime: Optional[
        datetime
    ] = None,
    count: int = 10,
    useful_gods: Optional[
        Dict[str, Any]
    ] = None,
) -> Dict[str, Any]:
    """
    大運を一括計算する。

    target_term_datetime を省略した場合は、
    順行・逆行を判定したうえで solar_terms_v2 から
    対象節入りを自動取得する。

    明示指定された場合は、その日時を優先する。
    """

    _validate_stem(year_stem)
    _validate_stem(day_master_stem)
    split_ganzhi(month_ganzhi)
    _validate_datetime(
        birth_datetime,
        "birth_datetime",
    )

    if not isinstance(count, int):
        raise TypeError(
            "count は整数で指定してください"
        )

    if count <= 0:
        raise ValueError(
            "count は1以上である必要があります"
        )

    normalized_gender = _normalize_gender(
        gender
    )

    direction = determine_luck_direction(
        year_stem,
        normalized_gender,
    )

    target_term_info = resolve_target_term(
        birth_datetime=birth_datetime,
        direction=direction,
        target_term_datetime=target_term_datetime,
    )

    resolved_target_datetime = target_term_info[
        "target_term_datetime"
    ]

    start_age = calculate_start_age(
        birth_datetime,
        resolved_target_datetime,
    )

    term_distance_days = calculate_term_distance_days(
        birth_datetime,
        resolved_target_datetime,
    )

    luck_ganzhi_list = generate_luck_ganzhi(
        month_ganzhi,
        direction,
        count=count,
    )

    pillars = [
        build_luck_pillar_data(
            index=index,
            ganzhi=ganzhi,
            day_master_stem=day_master_stem,
            start_age=start_age,
            birth_datetime=birth_datetime,
            useful_gods=useful_gods,
        )
        for index, ganzhi
        in enumerate(
            luck_ganzhi_list,
            start=1,
        )
    ]

    return {
        "direction": direction,
        "direction_japanese": (
            "順行"
            if direction == "forward"
            else "逆行"
        ),
        "year_stem": year_stem,
        "year_stem_yin_yang": STEM_TO_YIN_YANG[
            year_stem
        ],
        "gender": normalized_gender,
        "month_ganzhi": month_ganzhi,
        "day_master_stem": day_master_stem,
        "day_master_element": STEM_TO_ELEMENT[
            day_master_stem
        ],
        "birth_datetime": birth_datetime.isoformat(),
        "target_term_datetime": (
            resolved_target_datetime.isoformat()
        ),
        "target_term_name": target_term_info[
            "target_term_name"
        ],
        "target_term_month": target_term_info[
            "target_term_month"
        ],
        "target_term_branch": target_term_info[
            "target_term_branch"
        ],
        "target_term_source": target_term_info[
            "target_term_source"
        ],
        "term_distance_days": round(
            term_distance_days,
            6,
        ),
        "start_age": start_age,
        "start_age_detail": age_to_year_month_day(
            start_age
        ),
        "pillars": pillars,
        "pillar_count": len(pillars),
        "calculation_rules": {
            "direction_rule": (
                "陽男陰女順行・陰男陽女逆行"
            ),
            "start_age_rule": "三日一年法",
            "month_pillar_rule": (
                "月柱の次干支から第1大運"
            ),
            "pillar_duration_years": 10,
            "term_datetime_source": target_term_info[
                "target_term_source"
            ],
            "automatic_term_rule": (
                "順行は出生後の次節、"
                "逆行は出生前の前節"
            ),
            "term_boundary_rule": (
                "節入り同時刻はその節を含めず、"
                "順行は次節・逆行は前節を使用"
            ),
        },
        "method": "luck_pillars_v2",
        "status": "provisional_luck_pillars_v2",
        "notes": [
            (
                "大運開始年齢は対象節入り日時に"
                "依存します。"
            ),
            (
                "target_term_datetime を省略した場合は"
                "solar_terms_v2 から対象節入りを"
                "自動取得します。"
            ),
            (
                "target_term_datetime を指定した場合は"
                "後方互換のため指定値を優先します。"
            ),
            (
                "開始日時は365.2425日/年による"
                "概算表示です。"
            ),
            (
                "現在の solar_terms_v2 の節入り日時は"
                "固定月日・固定時刻による暫定値です。"
            ),
        ],
    }


# =========================================================
# Compatibility alias
# =========================================================


def evaluate_luck_pillars(
    *,
    year_stem: str,
    month_ganzhi: str,
    day_master_stem: str,
    gender: str,
    birth_datetime: datetime,
    target_term_datetime: Optional[
        datetime
    ] = None,
    count: int = 10,
    useful_gods: Optional[
        Dict[str, Any]
    ] = None,
) -> Dict[str, Any]:
    """
    calculate_luck_pillars の別名。
    """

    return calculate_luck_pillars(
        year_stem=year_stem,
        month_ganzhi=month_ganzhi,
        day_master_stem=day_master_stem,
        gender=gender,
        birth_datetime=birth_datetime,
        target_term_datetime=target_term_datetime,
        count=count,
        useful_gods=useful_gods,
    )


__all__ = [
    "HEAVENLY_STEMS",
    "EARTHLY_BRANCHES",
    "ELEMENTS",
    "STEM_TO_ELEMENT",
    "STEM_TO_YIN_YANG",
    "BRANCH_TO_ELEMENT",
    "SEXAGENARY_CYCLE",
    "GENERATES",
    "GENERATED_BY",
    "CONTROLS",
    "CONTROLLED_BY",
    "LuckPillar",
    "split_ganzhi",
    "get_sexagenary_index",
    "shift_ganzhi",
    "determine_luck_direction",
    "resolve_target_term",
    "calculate_term_distance_days",
    "calculate_start_age",
    "age_to_year_month_day",
    "estimate_start_datetime",
    "get_element_relation",
    "get_ten_god_for_stem",
    "evaluate_element_against_useful_gods",
    "generate_luck_ganzhi",
    "build_luck_pillar_data",
    "calculate_luck_pillars",
    "evaluate_luck_pillars",
]
