"""
engine/solar_terms.py

四柱推命 節入り・節気エンジン v2

目的
----
1. 月柱判定に必要な12節を管理する
2. 出生日時より前の節入りを取得する
3. 出生日時より後の節入りを取得する
4. 大運の順行・逆行に応じた対象節入りを取得する
5. 将来の天文計算エンジンへの差し替え口を統一する

重要
----
現在は「固定月日・固定時刻」による暫定計算。

実際の節入り日時は年ごとに変動するため、
鑑定実用版では Skyfield 等による
太陽黄経計算へ置き換える必要がある。

ただし公開APIは維持し、
内部計算だけ差し替えられる設計とする。

Version:
    solar_terms_v2
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional


# =========================================================
# Constants
# =========================================================


SOLAR_TERM_METHOD = "fixed_solar_terms_v2"

SOLAR_TERM_STATUS = "provisional"


# ---------------------------------------------------------
# 四柱推命で月境界として使う「節」12個
#
# month_branch:
#   その節入り後に始まる月支
#
# month_number:
#   寅月を1として数えた四柱推命上の月番号
#
# 現在は固定日時。
# 将来は太陽黄経計算へ置換する。
# ---------------------------------------------------------


SOLAR_TERMS = [
    {
        "name": "小寒",
        "month": 1,
        "day": 6,
        "hour": 0,
        "minute": 0,
        "month_branch": "丑",
        "month_number": 12,
    },
    {
        "name": "立春",
        "month": 2,
        "day": 4,
        "hour": 0,
        "minute": 0,
        "month_branch": "寅",
        "month_number": 1,
    },
    {
        "name": "啓蟄",
        "month": 3,
        "day": 6,
        "hour": 0,
        "minute": 0,
        "month_branch": "卯",
        "month_number": 2,
    },
    {
        "name": "清明",
        "month": 4,
        "day": 5,
        "hour": 0,
        "minute": 0,
        "month_branch": "辰",
        "month_number": 3,
    },
    {
        "name": "立夏",
        "month": 5,
        "day": 6,
        "hour": 0,
        "minute": 0,
        "month_branch": "巳",
        "month_number": 4,
    },
    {
        "name": "芒種",
        "month": 6,
        "day": 6,
        "hour": 0,
        "minute": 0,
        "month_branch": "午",
        "month_number": 5,
    },
    {
        "name": "小暑",
        "month": 7,
        "day": 7,
        "hour": 0,
        "minute": 0,
        "month_branch": "未",
        "month_number": 6,
    },
    {
        "name": "立秋",
        "month": 8,
        "day": 8,
        "hour": 0,
        "minute": 0,
        "month_branch": "申",
        "month_number": 7,
    },
    {
        "name": "白露",
        "month": 9,
        "day": 8,
        "hour": 0,
        "minute": 0,
        "month_branch": "酉",
        "month_number": 8,
    },
    {
        "name": "寒露",
        "month": 10,
        "day": 8,
        "hour": 0,
        "minute": 0,
        "month_branch": "戌",
        "month_number": 9,
    },
    {
        "name": "立冬",
        "month": 11,
        "day": 7,
        "hour": 0,
        "minute": 0,
        "month_branch": "亥",
        "month_number": 10,
    },
    {
        "name": "大雪",
        "month": 12,
        "day": 7,
        "hour": 0,
        "minute": 0,
        "month_branch": "子",
        "month_number": 11,
    },
]


SOLAR_TERM_NAMES = [
    term["name"]
    for term in SOLAR_TERMS
]


MONTH_BRANCHES = [
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
    "子",
    "丑",
]


# =========================================================
# Data class
# =========================================================


@dataclass(frozen=True)
class SolarTerm:
    """
    節入り1件を表す内部データ。
    """

    name: str
    datetime: datetime
    month_branch: str
    month_number: int
    method: str = SOLAR_TERM_METHOD
    status: str = SOLAR_TERM_STATUS


# =========================================================
# Validation
# =========================================================


def _validate_datetime(
    value: datetime,
    field_name: str = "datetime",
) -> None:
    if not isinstance(
        value,
        datetime,
    ):
        raise TypeError(
            f"{field_name} は datetime で指定してください"
        )


def _validate_year(
    year: int,
) -> None:
    if not isinstance(
        year,
        int,
    ):
        raise TypeError(
            "year は整数で指定してください"
        )

    if year < 1:
        raise ValueError(
            "year は1以上である必要があります"
        )


def _validate_direction(
    direction: str,
) -> None:
    if direction not in {
        "forward",
        "backward",
    }:
        raise ValueError(
            f"不正な方向です: {direction}"
        )


# =========================================================
# Definition helpers
# =========================================================


def get_solar_term_definition(
    name: str,
) -> Dict:
    """
    節名から定義を取得する。
    """

    for term in SOLAR_TERMS:
        if term["name"] == name:
            return dict(
                term
            )

    raise ValueError(
        f"未定義の節です: {name}"
    )


def get_solar_term_by_month(
    month: int,
) -> Dict:
    """
    暦月から、その月の節を取得する。
    """

    if not isinstance(
        month,
        int,
    ):
        raise TypeError(
            "month は整数で指定してください"
        )

    if not 1 <= month <= 12:
        raise ValueError(
            f"不正な月です: {month}"
        )

    for term in SOLAR_TERMS:
        if term["month"] == month:
            return dict(
                term
            )

    raise ValueError(
        f"{month}月の節が見つかりません"
    )


# =========================================================
# Solar-term datetime
# =========================================================


def get_solar_term_datetime(
    year: int,
    name: str,
) -> datetime:
    """
    指定年・指定節の節入り日時を返す。

    現在は固定日時。

    Example
    -------
    >>> get_solar_term_datetime(
    ...     1984,
    ...     "小暑",
    ... )
    datetime(1984, 7, 7, 0, 0)
    """

    _validate_year(
        year
    )

    definition = (
        get_solar_term_definition(
            name
        )
    )

    return datetime(
        year,
        definition["month"],
        definition["day"],
        definition["hour"],
        definition["minute"],
    )


def build_solar_term(
    year: int,
    name: str,
) -> SolarTerm:
    """
    SolarTerm オブジェクトを生成する。
    """

    definition = (
        get_solar_term_definition(
            name
        )
    )

    term_datetime = (
        get_solar_term_datetime(
            year,
            name,
        )
    )

    return SolarTerm(
        name=name,
        datetime=term_datetime,
        month_branch=definition[
            "month_branch"
        ],
        month_number=definition[
            "month_number"
        ],
    )


# =========================================================
# Year terms
# =========================================================


def get_year_solar_terms(
    year: int,
) -> List[SolarTerm]:
    """
    指定年の12節を時系列で返す。
    """

    _validate_year(
        year
    )

    terms = [
        build_solar_term(
            year,
            definition["name"],
        )
        for definition
        in SOLAR_TERMS
    ]

    return sorted(
        terms,
        key=lambda item: item.datetime,
    )


def get_year_solar_terms_dict(
    year: int,
) -> List[Dict]:
    """
    API等で使いやすいdict形式で返す。
    """

    return [
        solar_term_to_dict(
            term
        )
        for term
        in get_year_solar_terms(
            year
        )
    ]


# =========================================================
# Serialization
# =========================================================


def solar_term_to_dict(
    term: SolarTerm,
) -> Dict:
    """
    SolarTerm をdictへ変換する。
    """

    if not isinstance(
        term,
        SolarTerm,
    ):
        raise TypeError(
            "term は SolarTerm で指定してください"
        )

    return {
        "name": term.name,
        "datetime": (
            term.datetime.isoformat()
        ),
        "month_branch": (
            term.month_branch
        ),
        "month_number": (
            term.month_number
        ),
        "method": term.method,
        "status": term.status,
    }


# =========================================================
# Search range
# =========================================================


def get_surrounding_solar_terms(
    target_datetime: datetime,
) -> List[SolarTerm]:
    """
    対象日時の前年・当年・翌年について
    12節をまとめて取得する。

    年境界での検索漏れを防ぐ。
    """

    _validate_datetime(
        target_datetime,
        "target_datetime",
    )

    years = [
        target_datetime.year - 1,
        target_datetime.year,
        target_datetime.year + 1,
    ]

    terms: List[SolarTerm] = []

    for year in years:
        if year < 1:
            continue

        terms.extend(
            get_year_solar_terms(
                year
            )
        )

    return sorted(
        terms,
        key=lambda item: item.datetime,
    )


# =========================================================
# Previous / next term
# =========================================================


def get_previous_solar_term(
    target_datetime: datetime,
    *,
    inclusive: bool = False,
) -> SolarTerm:
    """
    対象日時より前の直近節入りを返す。

    inclusive=False:
        target と同時刻の節は含めない。

    inclusive=True:
        target と同時刻の節を含める。
    """

    _validate_datetime(
        target_datetime,
        "target_datetime",
    )

    terms = (
        get_surrounding_solar_terms(
            target_datetime
        )
    )

    if inclusive:
        candidates = [
            term
            for term in terms
            if (
                term.datetime
                <= target_datetime
            )
        ]
    else:
        candidates = [
            term
            for term in terms
            if (
                term.datetime
                < target_datetime
            )
        ]

    if not candidates:
        raise ValueError(
            "直前の節入りを取得できません"
        )

    return max(
        candidates,
        key=lambda item: item.datetime,
    )


def get_next_solar_term(
    target_datetime: datetime,
    *,
    inclusive: bool = False,
) -> SolarTerm:
    """
    対象日時より後の直近節入りを返す。

    inclusive=False:
        target と同時刻の節は含めない。

    inclusive=True:
        target と同時刻の節を含める。
    """

    _validate_datetime(
        target_datetime,
        "target_datetime",
    )

    terms = (
        get_surrounding_solar_terms(
            target_datetime
        )
    )

    if inclusive:
        candidates = [
            term
            for term in terms
            if (
                term.datetime
                >= target_datetime
            )
        ]
    else:
        candidates = [
            term
            for term in terms
            if (
                term.datetime
                > target_datetime
            )
        ]

    if not candidates:
        raise ValueError(
            "直後の節入りを取得できません"
        )

    return min(
        candidates,
        key=lambda item: item.datetime,
    )


# =========================================================
# Luck-pillar target term
# =========================================================


def get_luck_pillar_target_term(
    birth_datetime: datetime,
    direction: str,
) -> SolarTerm:
    """
    大運開始年齢計算に使う節入りを取得する。

    Rules
    -----
    forward:
        出生後の次の節入り。

    backward:
        出生前の直前の節入り。

    節入りちょうどの出生では、
    現在はその節そのものではなく
    「次」または「前」を使う。

    この境界ルールは将来、
    流派設定として分離可能。
    """

    _validate_datetime(
        birth_datetime,
        "birth_datetime",
    )

    _validate_direction(
        direction
    )

    if direction == "forward":
        return get_next_solar_term(
            birth_datetime,
            inclusive=False,
        )

    return get_previous_solar_term(
        birth_datetime,
        inclusive=False,
    )


def get_luck_pillar_target_datetime(
    birth_datetime: datetime,
    direction: str,
) -> datetime:
    """
    大運用対象節入りの datetime だけを返す。

    luck_pillars.py との接続用。
    """

    term = (
        get_luck_pillar_target_term(
            birth_datetime,
            direction,
        )
    )

    return term.datetime


# =========================================================
# Current solar month
# =========================================================


def get_current_solar_term(
    target_datetime: datetime,
) -> SolarTerm:
    """
    対象日時が属する四柱推命上の節月を返す。

    節入り時刻そのものは新しい月として扱う。
    """

    return get_previous_solar_term(
        target_datetime,
        inclusive=True,
    )


def get_month_branch_by_datetime(
    target_datetime: datetime,
) -> str:
    """
    日時から月支を返す。
    """

    return (
        get_current_solar_term(
            target_datetime
        ).month_branch
    )


def get_month_number_by_datetime(
    target_datetime: datetime,
) -> int:
    """
    日時から四柱推命上の月番号を返す。

    寅月 = 1
    卯月 = 2
    ...
    子月 = 11
    丑月 = 12
    """

    return (
        get_current_solar_term(
            target_datetime
        ).month_number
    )


# =========================================================
# Distance helpers
# =========================================================


def get_distance_to_previous_term_days(
    target_datetime: datetime,
) -> float:
    """
    直前の節入りから対象日時までの日数。
    """

    previous_term = (
        get_previous_solar_term(
            target_datetime,
            inclusive=False,
        )
    )

    delta = (
        target_datetime
        - previous_term.datetime
    )

    return (
        delta.total_seconds()
        / 86400.0
    )


def get_distance_to_next_term_days(
    target_datetime: datetime,
) -> float:
    """
    対象日時から直後の節入りまでの日数。
    """

    next_term = (
        get_next_solar_term(
            target_datetime,
            inclusive=False,
        )
    )

    delta = (
        next_term.datetime
        - target_datetime
    )

    return (
        delta.total_seconds()
        / 86400.0
    )


# =========================================================
# Debug / metadata
# =========================================================


def get_solar_terms_metadata() -> Dict:
    """
    節入りエンジンのメタデータ。
    """

    return {
        "method": (
            SOLAR_TERM_METHOD
        ),
        "status": (
            SOLAR_TERM_STATUS
        ),
        "term_count": len(
            SOLAR_TERMS
        ),
        "term_type": (
            "12_month_boundary_terms"
        ),
        "precision": (
            "fixed_day_time"
        ),
        "timezone": (
            "naive_local_datetime"
        ),
        "supports": [
            "month_boundary",
            "previous_term",
            "next_term",
            "luck_pillar_target_term",
        ],
        "limitations": [
            (
                "節入り日時は固定月日・"
                "固定時刻による暫定値です。"
            ),
            (
                "実際の節入り日時は"
                "年ごとに変動します。"
            ),
            (
                "高精度鑑定では太陽黄経による"
                "天文計算への置換が必要です。"
            ),
            (
                "現在のdatetimeは"
                "timezone-naiveです。"
            ),
        ],
    }


# =========================================================
# Compatibility helpers
# =========================================================


def get_previous_term(
    target_datetime: datetime,
) -> SolarTerm:
    """
    get_previous_solar_term の互換alias。
    """

    return get_previous_solar_term(
        target_datetime
    )


def get_next_term(
    target_datetime: datetime,
) -> SolarTerm:
    """
    get_next_solar_term の互換alias。
    """

    return get_next_solar_term(
        target_datetime
    )


def get_target_term_for_luck_pillars(
    birth_datetime: datetime,
    direction: str,
) -> SolarTerm:
    """
    get_luck_pillar_target_term の互換alias。
    """

    return (
        get_luck_pillar_target_term(
            birth_datetime,
            direction,
        )
    )


# =========================================================
# Public API
# =========================================================


__all__ = [
    "SOLAR_TERM_METHOD",
    "SOLAR_TERM_STATUS",
    "SOLAR_TERMS",
    "SOLAR_TERM_NAMES",
    "MONTH_BRANCHES",
    "SolarTerm",
    "get_solar_term_definition",
    "get_solar_term_by_month",
    "get_solar_term_datetime",
    "build_solar_term",
    "get_year_solar_terms",
    "get_year_solar_terms_dict",
    "solar_term_to_dict",
    "get_surrounding_solar_terms",
    "get_previous_solar_term",
    "get_next_solar_term",
    "get_luck_pillar_target_term",
    "get_luck_pillar_target_datetime",
    "get_current_solar_term",
    "get_month_branch_by_datetime",
    "get_month_number_by_datetime",
    "get_distance_to_previous_term_days",
    "get_distance_to_next_term_days",
    "get_solar_terms_metadata",
    "get_previous_term",
    "get_next_term",
    "get_target_term_for_luck_pillars",
]
