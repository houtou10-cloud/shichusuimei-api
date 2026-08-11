"""
engine/month.py

四柱推命 月柱計算エンジン v3

目的
----
出生日時から月柱を計算する。

月支の境界には、
固定された節入り日ではなく、
solar_terms_v3 が天文学的に計算した
実際の節入り日時を使用する。

月干は五虎遁によって計算する。

計算方針
--------
・月支は節入り基準
・節入り時刻ちょうどから新しい月
・月支判定は solar_terms_v3 に一本化
・月干は年干と月支から五虎遁で算出
・出生地による真太陽時補正は行わない

Version
-------
month_v3
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict

from engine.constants import STEMS
from engine.solar_terms import (
    get_month_branch_by_datetime,
)


# =========================================================
# Metadata
# =========================================================


MONTH_METHOD = (
    "astronomical_solar_terms_v3"
)

MONTH_STATUS = (
    "astronomical"
)


# =========================================================
# Five Tiger Escape
# =========================================================

# 年干ごとの寅月の開始天干
#
# 甲・己年：丙寅
# 乙・庚年：戊寅
# 丙・辛年：庚寅
# 丁・壬年：壬寅
# 戊・癸年：甲寅

TIGER_MONTH_STEM_START = {
    "甲": 2,
    "己": 2,
    "乙": 4,
    "庚": 4,
    "丙": 6,
    "辛": 6,
    "丁": 8,
    "壬": 8,
    "戊": 0,
    "癸": 0,
}


# 節月の順序
#
# 寅月から始まり、
# 丑月で終了する。

MONTH_BRANCH_ORDER = [
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
# Validation
# =========================================================


def _validate_birth_datetime(
    birth_datetime: datetime,
) -> None:
    """
    出生日時を検証する。
    """

    if not isinstance(
        birth_datetime,
        datetime,
    ):
        raise TypeError(
            "birth_datetimeはdatetime型で"
            "指定してください。"
        )


def _validate_year_stem(
    year_stem: str,
) -> None:
    """
    年干を検証する。
    """

    if year_stem not in STEMS:
        raise ValueError(
            f"不正な年干です: {year_stem}"
        )


def _validate_month_branch(
    month_branch: str,
) -> None:
    """
    月支を検証する。
    """

    if (
        month_branch
        not in MONTH_BRANCH_ORDER
    ):
        raise ValueError(
            f"不正な月支です: {month_branch}"
        )


# =========================================================
# Month branch
# =========================================================


def calculate_month_branch(
    birth_datetime: datetime,
) -> str:
    """
    出生日時から月支を計算する。

    Parameters
    ----------
    birth_datetime : datetime
        出生日時。

    Returns
    -------
    str
        寅・卯・辰・巳・午・未・
        申・酉・戌・亥・子・丑
        のいずれか。

    Rules
    -----
    solar_terms_v3 が計算した
    実際の節入り日時を使用する。

    節入り時刻より前:
        前の月支

    節入り時刻ちょうど:
        新しい月支

    節入り時刻より後:
        新しい月支

    Notes
    -----
    固定節入り日は使用しない。
    """

    _validate_birth_datetime(
        birth_datetime
    )

    return get_month_branch_by_datetime(
        birth_datetime
    )


# =========================================================
# Month stem
# =========================================================


def calculate_month_stem(
    year_stem: str,
    month_branch: str,
) -> str:
    """
    年干と月支から月干を計算する。

    五虎遁を使用する。

    Rules
    -----
    甲・己年:
        丙寅から開始

    乙・庚年:
        戊寅から開始

    丙・辛年:
        庚寅から開始

    丁・壬年:
        壬寅から開始

    戊・癸年:
        甲寅から開始
    """

    _validate_year_stem(
        year_stem
    )

    _validate_month_branch(
        month_branch
    )

    branch_index = (
        MONTH_BRANCH_ORDER.index(
            month_branch
        )
    )

    starting_stem_index = (
        TIGER_MONTH_STEM_START[
            year_stem
        ]
    )

    stem_index = (
        starting_stem_index
        + branch_index
    ) % 10

    return STEMS[
        stem_index
    ]


# =========================================================
# Month pillar
# =========================================================


def calculate_month_pillar(
    birth_datetime: datetime,
    year_stem: str,
) -> str:
    """
    出生日時と年干から月柱を計算する。

    Parameters
    ----------
    birth_datetime : datetime
        出生日時。

    year_stem : str
        年柱の天干。

    Returns
    -------
    str
        「丙寅」「辛未」などの月柱。

    Calculation
    -----------
    1. solar_terms_v3 で月支を決定
    2. 五虎遁で月干を決定
    3. 月干 + 月支を返す
    """

    _validate_birth_datetime(
        birth_datetime
    )

    _validate_year_stem(
        year_stem
    )

    month_branch = (
        calculate_month_branch(
            birth_datetime
        )
    )

    month_stem = (
        calculate_month_stem(
            year_stem,
            month_branch,
        )
    )

    return (
        month_stem
        + month_branch
    )


# =========================================================
# Detailed result
# =========================================================


def calculate_month_pillar_data(
    birth_datetime: datetime,
    year_stem: str,
) -> Dict[str, object]:
    """
    月柱の詳細データを返す。

    AI鑑定・API・デバッグ用途を想定する。
    """

    _validate_birth_datetime(
        birth_datetime
    )

    _validate_year_stem(
        year_stem
    )

    month_branch = (
        calculate_month_branch(
            birth_datetime
        )
    )

    month_stem = (
        calculate_month_stem(
            year_stem,
            month_branch,
        )
    )

    ganzhi = (
        month_stem
        + month_branch
    )

    return {
        "ganzhi": ganzhi,
        "stem": month_stem,
        "branch": month_branch,
        "year_stem": year_stem,
        "method": MONTH_METHOD,
        "status": MONTH_STATUS,
        "boundary": (
            "astronomical_solar_term"
        ),
        "solar_term_source": (
            "solar_terms_v3"
        ),
        "true_solar_time": False,
    }


# =========================================================
# Metadata
# =========================================================


def get_month_pillar_metadata() -> Dict[
    str,
    object,
]:
    """
    月柱エンジンの計算方式を返す。
    """

    return {
        "method": MONTH_METHOD,
        "status": MONTH_STATUS,
        "boundary": (
            "astronomical_solar_term"
        ),
        "solar_term_source": (
            "solar_terms_v3"
        ),
        "month_branch_order": (
            MONTH_BRANCH_ORDER.copy()
        ),
        "true_solar_time": False,
    }


# =========================================================
# Public API
# =========================================================


__all__ = [
    "MONTH_METHOD",
    "MONTH_STATUS",
    "TIGER_MONTH_STEM_START",
    "MONTH_BRANCH_ORDER",
    "calculate_month_branch",
    "calculate_month_stem",
    "calculate_month_pillar",
    "calculate_month_pillar_data",
    "get_month_pillar_metadata",
]
