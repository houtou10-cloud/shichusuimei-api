"""
engine/solar_terms.py

四柱推命 節入り・節気エンジン v3

目的
----
1. 四柱推命の月境界として使用する12節を管理する
2. Skyfield により太陽黄経から節入り日時を計算する
3. 出生日時より前の直近節入りを取得する
4. 出生日時より後の直近節入りを取得する
5. 大運の順行・逆行に応じた対象節入りを取得する
6. 月支・四柱推命上の月番号を取得する
7. 節入りからの経過日数を取得する
8. 既存 solar_terms_v2 API との互換性を維持する

計算方針
--------
四柱推命で月境界として使用する12の「節」は、
太陽の視黄経ではなく、地球から見た太陽の
黄道座標上の黄経を基準として求める。

各節の黄経:
    小寒   285°
    立春   315°
    啓蟄   345°
    清明    15°
    立夏    45°
    芒種    75°
    小暑   105°
    立秋   135°
    白露   165°
    寒露   195°
    立冬   225°
    大雪   255°

Skyfield内部ではUTCで計算し、
公開APIでは日本標準時相当の
timezone-naive datetime を返す。

これは既存エンジンとの互換性を維持するためである。

Version:
    solar_terms_v3
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Dict, List

from skyfield.api import load
from skyfield.framelib import ecliptic_frame


# =========================================================
# Constants
# =========================================================


SOLAR_TERM_METHOD = "skyfield_solar_longitude_v3"

SOLAR_TERM_STATUS = "astronomical"


JST = timezone(
    timedelta(
        hours=9
    )
)


# ---------------------------------------------------------
# 四柱推命で月境界として使用する12節
#
# longitude:
#   太陽黄経
#
# month_branch:
#   その節入り後に始まる月支
#
# month_number:
#   寅月を1として数える
#
# approximate_month/day:
#   天文探索範囲を作るためだけの概算日。
#   実際の節入り日時には使用しない。
# ---------------------------------------------------------


SOLAR_TERMS = [
    {
        "name": "小寒",
        "month": 1,
        "day": 6,
        "hour": 0,
        "minute": 0,
        "longitude": 285.0,
        "month_branch": "丑",
        "month_number": 12,
    },
    {
        "name": "立春",
        "month": 2,
        "day": 4,
        "hour": 0,
        "minute": 0,
        "longitude": 315.0,
        "month_branch": "寅",
        "month_number": 1,
    },
    {
        "name": "啓蟄",
        "month": 3,
        "day": 6,
        "hour": 0,
        "minute": 0,
        "longitude": 345.0,
        "month_branch": "卯",
        "month_number": 2,
    },
    {
        "name": "清明",
        "month": 4,
        "day": 5,
        "hour": 0,
        "minute": 0,
        "longitude": 15.0,
        "month_branch": "辰",
        "month_number": 3,
    },
    {
        "name": "立夏",
        "month": 5,
        "day": 6,
        "hour": 0,
        "minute": 0,
        "longitude": 45.0,
        "month_branch": "巳",
        "month_number": 4,
    },
    {
        "name": "芒種",
        "month": 6,
        "day": 6,
        "hour": 0,
        "minute": 0,
        "longitude": 75.0,
        "month_branch": "午",
        "month_number": 5,
    },
    {
        "name": "小暑",
        "month": 7,
        "day": 7,
        "hour": 0,
        "minute": 0,
        "longitude": 105.0,
        "month_branch": "未",
        "month_number": 6,
    },
    {
        "name": "立秋",
        "month": 8,
        "day": 8,
        "hour": 0,
        "minute": 0,
        "longitude": 135.0,
        "month_branch": "申",
        "month_number": 7,
    },
    {
        "name": "白露",
        "month": 9,
        "day": 8,
        "hour": 0,
        "minute": 0,
        "longitude": 165.0,
        "month_branch": "酉",
        "month_number": 8,
    },
    {
        "name": "寒露",
        "month": 10,
        "day": 8,
        "hour": 0,
        "minute": 0,
        "longitude": 195.0,
        "month_branch": "戌",
        "month_number": 9,
    },
    {
        "name": "立冬",
        "month": 11,
        "day": 7,
        "hour": 0,
        "minute": 0,
        "longitude": 225.0,
        "month_branch": "亥",
        "month_number": 10,
    },
    {
        "name": "大雪",
        "month": 12,
        "day": 7,
        "hour": 0,
        "minute": 0,
        "longitude": 255.0,
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
    longitude: float
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


def _normalize_to_jst_naive(
    value: datetime,
    field_name: str = "datetime",
) -> datetime:
    """
    datetimeをJST相当のtimezone-naiveへ正規化する。

    Rules
    -----
    ・naive datetime:
        既存エンジン互換のため、
        JSTローカル時刻としてそのまま扱う。

    ・aware datetime:
        同じ瞬間を保ったままJSTへ変換し、
        最後にtzinfoを外す。

    Returns
    -------
    datetime
        JST相当のtimezone-naive datetime。
    """

    _validate_datetime(
        value,
        field_name,
    )

    if value.tzinfo is None:
        return value

    return (
        value.astimezone(
            JST
        ).replace(
            tzinfo=None
        )
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
# Skyfield resources
# =========================================================


@lru_cache(
    maxsize=1
)
def _get_timescale():
    """
    Skyfield Timescale をキャッシュする。
    """

    return load.timescale()


@lru_cache(
    maxsize=1
)
def _get_ephemeris():
    """
    JPL DE421 暦を取得する。

    Skyfield標準キャッシュを使用するため、
    初回のみファイル取得が必要になる場合がある。

    2回目以降はキャッシュを使用する。
    """

    return load(
        "de421.bsp"
    )


# =========================================================
# Longitude helpers
# =========================================================


def _normalize_longitude(
    longitude: float,
) -> float:
    """
    黄経を0以上360未満へ正規化する。
    """

    return (
        longitude
        % 360.0
    )


def _angular_difference(
    current: float,
    target: float,
) -> float:
    """
    target に対する current の符号付き角度差。

    戻り値:
        -180 <= value < 180
    """

    return (
        (
            current
            - target
            + 180.0
        )
        % 360.0
    ) - 180.0


def _sun_ecliptic_longitude(
    utc_datetime: datetime,
) -> float:
    """
    指定UTC日時における地心視太陽黄経を返す。
    """

    if utc_datetime.tzinfo is None:
        utc_datetime = (
            utc_datetime.replace(
                tzinfo=timezone.utc
            )
        )
    else:
        utc_datetime = (
            utc_datetime.astimezone(
                timezone.utc
            )
        )

    ts = _get_timescale()
    eph = _get_ephemeris()

    earth = eph["earth"]
    sun = eph["sun"]

    t = ts.from_datetime(
        utc_datetime
    )

    apparent = (
        earth.at(
            t
        )
        .observe(
            sun
        )
        .apparent()
    )

    _, longitude, _ = (
        apparent.frame_latlon(
            ecliptic_frame
        )
    )

    return _normalize_longitude(
        longitude.degrees
    )


# =========================================================
# Astronomical search
# =========================================================


def _find_longitude_crossing(
    *,
    target_longitude: float,
    start_utc: datetime,
    end_utc: datetime,
) -> datetime:
    """
    指定範囲内で太陽黄経が target_longitude に
    到達する時刻を二分探索で求める。

    太陽は通常1日約1度進むため、
    節入り付近の短い探索区間では
    単調増加として扱える。
    """

    if start_utc.tzinfo is None:
        start_utc = start_utc.replace(
            tzinfo=timezone.utc
        )

    if end_utc.tzinfo is None:
        end_utc = end_utc.replace(
            tzinfo=timezone.utc
        )

    if start_utc >= end_utc:
        raise ValueError(
            "探索開始日時は終了日時より前である必要があります"
        )

    target_longitude = (
        _normalize_longitude(
            target_longitude
        )
    )

    # -----------------------------------------------------
    # まず粗探索。
    #
    # 6時間刻みで符号反転区間を探す。
    # -----------------------------------------------------

    step = timedelta(
        hours=6
    )

    previous_time = start_utc
    previous_diff = (
        _angular_difference(
            _sun_ecliptic_longitude(
                previous_time
            ),
            target_longitude,
        )
    )

    current_time = (
        previous_time
        + step
    )

    bracket_start = None
    bracket_end = None

    while current_time <= end_utc:
        current_diff = (
            _angular_difference(
                _sun_ecliptic_longitude(
                    current_time
                ),
                target_longitude,
            )
        )

        if previous_diff == 0:
            return previous_time

        if current_diff == 0:
            return current_time

        # ±180°のラップを跨いだだけの
        # 偽の符号反転を除外する。
        normal_crossing = (
            previous_diff < 0
            and current_diff > 0
            and abs(
                current_diff
                - previous_diff
            ) < 180.0
        )

        if normal_crossing:
            bracket_start = (
                previous_time
            )
            bracket_end = (
                current_time
            )
            break

        previous_time = (
            current_time
        )

        previous_diff = (
            current_diff
        )

        current_time = (
            current_time
            + step
        )

    if (
        bracket_start is None
        or bracket_end is None
    ):
        raise ValueError(
            "指定範囲内で太陽黄経の到達時刻を"
            "検出できませんでした"
        )

    # -----------------------------------------------------
    # 二分探索。
    #
    # 1秒程度まで絞り込む。
    # -----------------------------------------------------

    left = bracket_start
    right = bracket_end

    while (
        right - left
    ).total_seconds() > 1.0:
        middle = (
            left
            + (
                right - left
            )
            / 2
        )

        middle_diff = (
            _angular_difference(
                _sun_ecliptic_longitude(
                    middle
                ),
                target_longitude,
            )
        )

        if middle_diff < 0:
            left = middle
        else:
            right = middle

    return (
        left
        + (
            right - left
        )
        / 2
    )


# =========================================================
# Solar-term datetime
# =========================================================


@lru_cache(
    maxsize=512
)
def get_solar_term_datetime(
    year: int,
    name: str,
) -> datetime:
    """
    指定年・指定節の実際の節入り日時を返す。

    内部:
        Skyfield / JPL DE421
        太陽黄経

    出力:
        日本標準時相当の
        timezone-naive datetime

    timezone-naive として返すのは、
    既存の四柱推命エンジンとの互換性を
    維持するため。
    """

    _validate_year(
        year
    )

    definition = (
        get_solar_term_definition(
            name
        )
    )

    target_longitude = (
        float(
            definition[
                "longitude"
            ]
        )
    )

    # 概算日の前後5日を探索する。
    #
    # JSTの概算日をUTCへ変換して
    # 探索範囲を作る。

    approximate_jst = datetime(
        year,
        definition["month"],
        definition["day"],
        12,
        0,
        tzinfo=JST,
    )

    approximate_utc = (
        approximate_jst.astimezone(
            timezone.utc
        )
    )

    start_utc = (
        approximate_utc
        - timedelta(
            days=5
        )
    )

    end_utc = (
        approximate_utc
        + timedelta(
            days=5
        )
    )

    crossing_utc = (
        _find_longitude_crossing(
            target_longitude=target_longitude,
            start_utc=start_utc,
            end_utc=end_utc,
        )
    )

    crossing_jst = (
        crossing_utc.astimezone(
            JST
        )
    )

    # 既存API互換のためtzinfoを外す。
    return crossing_jst.replace(
        tzinfo=None
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
        longitude=float(
            definition[
                "longitude"
            ]
        ),
    )


# =========================================================
# Year terms
# =========================================================


@lru_cache(
    maxsize=128
)
def _get_year_solar_terms_cached(
    year: int,
) -> tuple[SolarTerm, ...]:
    """
    内部キャッシュ版。
    """

    _validate_year(
        year
    )

    terms = [
        build_solar_term(
            year,
            definition[
                "name"
            ],
        )
        for definition
        in SOLAR_TERMS
    ]

    return tuple(
        sorted(
            terms,
            key=lambda item: (
                item.datetime
            ),
        )
    )


def get_year_solar_terms(
    year: int,
) -> List[SolarTerm]:
    """
    指定年の12節を時系列で返す。
    """

    return list(
        _get_year_solar_terms_cached(
            year
        )
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
        "longitude": (
            term.longitude
        ),
        "method": (
            term.method
        ),
        "status": (
            term.status
        ),
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

    target_datetime = (
        _normalize_to_jst_naive(
            target_datetime,
            "target_datetime",
        )
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
        key=lambda item: (
            item.datetime
        ),
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

    target_datetime = (
        _normalize_to_jst_naive(
            target_datetime,
            "target_datetime",
        )
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
        key=lambda item: (
            item.datetime
        ),
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

    target_datetime = (
        _normalize_to_jst_naive(
            target_datetime,
            "target_datetime",
        )
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
        key=lambda item: (
            item.datetime
        ),
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
    その節そのものではなく
    次節または前節を使用する。

    将来的には流派設定として
    分離可能。
    """

    _validate_datetime(
        birth_datetime,
        "birth_datetime",
    )

    birth_datetime = (
        _normalize_to_jst_naive(
            birth_datetime,
            "birth_datetime",
        )
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
    大運用対象節入りのdatetimeだけを返す。
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

    節入り時刻そのものは
    新しい月として扱う。
    """

    target_datetime = (
        _normalize_to_jst_naive(
            target_datetime,
            "target_datetime",
        )
    )


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

    target_datetime = (
        _normalize_to_jst_naive(
            target_datetime,
            "target_datetime",
        )
    )


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

    target_datetime = (
        _normalize_to_jst_naive(
            target_datetime,
            "target_datetime",
        )
    )


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

    target_datetime = (
        _normalize_to_jst_naive(
            target_datetime,
            "target_datetime",
        )
    )


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

    target_datetime = (
        _normalize_to_jst_naive(
            target_datetime,
            "target_datetime",
        )
    )


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


def get_solar_term_position(
    target_datetime: datetime,
) -> Dict:
    """
    現在の節月内での位置を返す。

    月令精密化で使用するための
    補助情報。

    Returns
    -------
    {
        current_term,
        next_term,
        days_from_current_term,
        days_to_next_term,
        term_span_days,
        progress_ratio,
        is_just_after_term,
    }
    """

    _validate_datetime(
        target_datetime,
        "target_datetime",
    )

    target_datetime = (
        _normalize_to_jst_naive(
            target_datetime,
            "target_datetime",
        )
    )

    current_term = (
        get_current_solar_term(
            target_datetime
        )
    )

    next_term = (
        get_next_solar_term(
            target_datetime,
            inclusive=False,
        )
    )

    elapsed = (
        target_datetime
        - current_term.datetime
    )

    remaining = (
        next_term.datetime
        - target_datetime
    )

    span = (
        next_term.datetime
        - current_term.datetime
    )

    elapsed_days = (
        elapsed.total_seconds()
        / 86400.0
    )

    remaining_days = (
        remaining.total_seconds()
        / 86400.0
    )

    span_days = (
        span.total_seconds()
        / 86400.0
    )

    if span_days <= 0:
        progress_ratio = 0.0
    else:
        progress_ratio = (
            elapsed_days
            / span_days
        )

    progress_ratio = max(
        0.0,
        min(
            1.0,
            progress_ratio,
        ),
    )

    return {
        "current_term": (
            solar_term_to_dict(
                current_term
            )
        ),
        "next_term": (
            solar_term_to_dict(
                next_term
            )
        ),
        "days_from_current_term": round(
            elapsed_days,
            8,
        ),
        "days_to_next_term": round(
            remaining_days,
            8,
        ),
        "term_span_days": round(
            span_days,
            8,
        ),
        "progress_ratio": round(
            progress_ratio,
            8,
        ),
        "is_just_after_term": (
            elapsed_days
            < 3.0
        ),
        "method": SOLAR_TERM_METHOD,
        "status": SOLAR_TERM_STATUS,
    }


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
            "astronomical_solar_longitude"
        ),
        "timezone": (
            "JST_naive_public_api"
        ),
        "ephemeris": (
            "JPL DE421"
        ),
        "supports": [
            "month_boundary",
            "previous_term",
            "next_term",
            "luck_pillar_target_term",
            "solar_term_position",
            "astronomical_longitude",
            "timezone_aware_input",
            "timezone_naive_input",
        ],
        "limitations": [
            (
                "公開APIでは既存コードとの互換性のため"
                "JST相当のtimezone-naive datetimeを返します。"
            ),
            (
                "出生地による真太陽時補正は"
                "このモジュールでは行いません。"
            ),
            (
                "大運開始年齢の流派差は"
                "luck_pillars側で扱います。"
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
    "get_solar_term_position",
    "get_solar_terms_metadata",
    "get_previous_term",
    "get_next_term",
    "get_target_term_for_luck_pillars",
]
