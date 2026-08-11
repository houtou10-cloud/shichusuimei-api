"""
engine/year.py

四柱推命 年柱計算エンジン v3

目的
----
出生日時から四柱推命上の年柱を計算する。

年境界には暦年の1月1日ではなく、
天文学的に計算された「立春」の
実際の節入り日時を使用する。

計算方針
--------
・1984年 = 甲子年を基準とする
・立春より前は前年の干支年
・立春ちょうどから新しい干支年
・立春日時は solar_terms_v3 から取得
・solar_terms_v3 は Skyfield / JPL DE421 を使用
・公開される節入り日時はJST相当の
  timezone-naive datetime

注意
----
出生地による真太陽時補正は、
このモジュールでは行わない。

Version
-------
year_v3
"""

from __future__ import annotations

from datetime import datetime, timedelta

from engine.ganzhi import ganzhi_from_index
from engine.solar_terms import (
    get_solar_term_datetime,
)


# =========================================================
# Constants
# =========================================================


YEAR_METHOD = "astronomical_lichun_v3"

YEAR_STATUS = "astronomical"


# 1984年は甲子年
BASE_YEAR = 1984

# 甲子 = 六十干支 index 0
BASE_YEAR_GANZHI_INDEX = 0


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
            "birth_datetimeはdatetime型で指定してください。"
        )


def _validate_margin_days(
    margin_days: int,
) -> None:
    """
    立春近傍判定の日数を検証する。
    """

    if not isinstance(
        margin_days,
        int,
    ):
        raise TypeError(
            "margin_daysは整数で指定してください。"
        )

    if margin_days < 0:
        raise ValueError(
            "margin_daysは0以上で指定してください。"
        )


# =========================================================
# Lichun
# =========================================================


def get_lichun_datetime(
    year: int,
) -> datetime:
    """
    指定年の実際の立春日時を返す。

    Parameters
    ----------
    year : int
        西暦年。

    Returns
    -------
    datetime
        solar_terms_v3 が計算した
        JST相当のtimezone-naive datetime。

    Notes
    -----
    solar_terms_v3 の
    get_solar_term_datetime() を使用する。
    """

    if not isinstance(
        year,
        int,
    ):
        raise TypeError(
            "yearは整数で指定してください。"
        )

    if year < 1:
        raise ValueError(
            "yearは1以上で指定してください。"
        )

    return get_solar_term_datetime(
        year,
        "立春",
    )


# =========================================================
# Effective year
# =========================================================


def calculate_effective_year(
    birth_datetime: datetime,
) -> int:
    """
    年柱計算に使用する干支年を返す。

    Rules
    -----
    ・立春より前
        -> 前年

    ・立春ちょうど
        -> 当年

    ・立春より後
        -> 当年

    Example
    -------
    1985年の立春より前:
        effective_year = 1984

    1985年の立春以後:
        effective_year = 1985
    """

    _validate_birth_datetime(
        birth_datetime
    )

    lichun = get_lichun_datetime(
        birth_datetime.year
    )

    # solar_terms_v3 の公開日時は
    # timezone-naive datetime。
    #
    # birth_datetime が timezone-aware の場合は
    # 比較できないため、
    # 同じローカル日時表現としてtzinfoを外す。
    comparison_datetime = birth_datetime

    if (
        comparison_datetime.tzinfo
        is not None
    ):
        comparison_datetime = (
            comparison_datetime.replace(
                tzinfo=None
            )
        )

    if comparison_datetime < lichun:
        return (
            birth_datetime.year
            - 1
        )

    return birth_datetime.year


# =========================================================
# Year pillar
# =========================================================


def calculate_year_pillar(
    birth_datetime: datetime,
) -> str:
    """
    出生日時から年柱を計算する。

    Parameters
    ----------
    birth_datetime : datetime
        出生日時。

    Returns
    -------
    str
        「甲子」「乙丑」などの年柱。

    Calculation
    -----------
    1984年 = 甲子を基準として、
    effective_yearとの差を
    六十干支へ反映する。

    年境界には実際の立春日時を使用する。
    """

    _validate_birth_datetime(
        birth_datetime
    )

    effective_year = (
        calculate_effective_year(
            birth_datetime
        )
    )

    elapsed_years = (
        effective_year
        - BASE_YEAR
    )

    ganzhi_index = (
        BASE_YEAR_GANZHI_INDEX
        + elapsed_years
    )

    return ganzhi_from_index(
        ganzhi_index
    )


# =========================================================
# Near Lichun
# =========================================================


def is_near_lichun(
    birth_datetime: datetime,
    margin_days: int = 2,
) -> bool:
    """
    出生日時が立春付近か判定する。

    Parameters
    ----------
    birth_datetime : datetime
        出生日時。

    margin_days : int
        立春前後何日までを
        「立春付近」とするか。
        デフォルトは2日。

    Returns
    -------
    bool
        立春との差が指定日数以内ならTrue。

    Notes
    -----
    旧実装の固定2月4日ではなく、
    solar_terms_v3 が計算した
    実際の立春日時を使用する。
    """

    _validate_birth_datetime(
        birth_datetime
    )

    _validate_margin_days(
        margin_days
    )

    lichun = get_lichun_datetime(
        birth_datetime.year
    )

    comparison_datetime = birth_datetime

    if (
        comparison_datetime.tzinfo
        is not None
    ):
        comparison_datetime = (
            comparison_datetime.replace(
                tzinfo=None
            )
        )

    difference = abs(
        comparison_datetime
        - lichun
    )

    return (
        difference
        <= timedelta(
            days=margin_days
        )
    )


# =========================================================
# Backward compatibility
# =========================================================


def is_near_provisional_lichun(
    birth_datetime: datetime,
    margin_days: int = 2,
) -> bool:
    """
    旧APIとの互換用。

    以前は固定の2月4日00:00を基準としていたが、
    v3では実際の立春日時を使用する。

    関数名は既存コードとの互換性のため残す。
    """

    return is_near_lichun(
        birth_datetime,
        margin_days=margin_days,
    )


# =========================================================
# Metadata
# =========================================================


def get_year_pillar_metadata() -> dict:
    """
    年柱エンジンの計算方式を返す。
    """

    return {
        "method": YEAR_METHOD,
        "status": YEAR_STATUS,
        "base_year": BASE_YEAR,
        "base_ganzhi": "甲子",
        "boundary": "astronomical_lichun",
        "timezone": (
            "JST_naive_solar_term"
        ),
        "solar_term_source": (
            "solar_terms_v3"
        ),
        "true_solar_time": False,
    }


# =========================================================
# Public API
# =========================================================


__all__ = [
    "YEAR_METHOD",
    "YEAR_STATUS",
    "BASE_YEAR",
    "BASE_YEAR_GANZHI_INDEX",
    "get_lichun_datetime",
    "calculate_effective_year",
    "calculate_year_pillar",
    "is_near_lichun",
    "is_near_provisional_lichun",
    "get_year_pillar_metadata",
]
