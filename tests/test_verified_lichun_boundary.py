"""
tests/test_verified_lichun_boundary.py

立春境界の年柱計算を検証する
ゴールデン回帰テスト。

目的
----
四柱推命の年柱は1月1日ではなく、
立春の実際の節入り日時を境界として切り替える。

このテストでは次の2層を分けて検証する。

1. 天文計算層
   engine.solar_terms / engine.year が返す立春日時が、
   国立天文台 暦計算室の公表時刻と整合すること。

2. 四柱推命ロジック層
   実際に計算された立春日時の
   1秒前 / ちょうど / 1秒後で、
   effective_year と年柱が正しく切り替わること。

重要
----
国立天文台の公開値は「分」単位である。
Skyfieldによる内部計算値は秒以下を含むため、
公表時刻との比較には90秒の許容差を設ける。

このテストでは固定2月4日00:00を正解としない。
2025年の立春は2月3日23:10であり、
年によって日付・時刻が変動すること自体を検証する。

参照
----
国立天文台 暦計算室
「二十四節気および雑節」

検証値:
1985-02-04 06:12 JST
2024-02-04 17:27 JST
2025-02-03 23:10 JST
2026-02-04 05:02 JST
"""

from __future__ import annotations

from datetime import (
    datetime,
    timedelta,
    timezone,
)

import pytest

from engine.year import (
    BASE_YEAR,
    BASE_YEAR_GANZHI_INDEX,
    YEAR_METHOD,
    YEAR_STATUS,
    calculate_effective_year,
    calculate_year_pillar,
    get_lichun_datetime,
    get_year_pillar_metadata,
    is_near_lichun,
    is_near_provisional_lichun,
)


# ============================================================
# Constants
# ============================================================


VERIFIED_LICHUN_BOUNDARY_METHOD = (
    "naoj_verified_lichun_boundary_v1"
)

VERIFIED_LICHUN_BOUNDARY_STATUS = (
    "golden_regression"
)

# 国立天文台の公表値は分単位。
#
# Skyfield内部値との秒差・丸め差を吸収するため、
# ±90秒以内を合格とする。
OFFICIAL_TIME_TOLERANCE_SECONDS = 90


# ============================================================
# Golden data
# ============================================================


LICHUN_GOLDEN_CASES = (
    {
        "year": 1985,
        "official": datetime(
            1985,
            2,
            4,
            6,
            12,
        ),
        "previous_effective_year": 1984,
        "current_effective_year": 1985,
        "previous_pillar": "甲子",
        "current_pillar": "乙丑",
        "source": (
            "国立天文台 暦計算室 "
            "1985年 二十四節気・雑節"
        ),
    },
    {
        "year": 2024,
        "official": datetime(
            2024,
            2,
            4,
            17,
            27,
        ),
        "previous_effective_year": 2023,
        "current_effective_year": 2024,
        "previous_pillar": "癸卯",
        "current_pillar": "甲辰",
        "source": (
            "国立天文台 暦計算室 "
            "2024年 暦要項"
        ),
    },
    {
        "year": 2025,
        "official": datetime(
            2025,
            2,
            3,
            23,
            10,
        ),
        "previous_effective_year": 2024,
        "current_effective_year": 2025,
        "previous_pillar": "甲辰",
        "current_pillar": "乙巳",
        "source": (
            "国立天文台 暦計算室 "
            "2025年 暦要項"
        ),
    },
    {
        "year": 2026,
        "official": datetime(
            2026,
            2,
            4,
            5,
            2,
        ),
        "previous_effective_year": 2025,
        "current_effective_year": 2026,
        "previous_pillar": "乙巳",
        "current_pillar": "丙午",
        "source": (
            "国立天文台 暦計算室 "
            "2026年 暦要項"
        ),
    },
)


LICHUN_CASE_IDS = tuple(
    f"lichun_{item['year']}"
    for item in LICHUN_GOLDEN_CASES
)


# ============================================================
# Helpers
# ============================================================


def _calculated_lichun(
    case: dict,
) -> datetime:
    """
    engine.year経由で立春日時を取得する。
    """

    value = get_lichun_datetime(
        case[
            "year"
        ]
    )

    assert isinstance(
        value,
        datetime,
    )

    return value


def _seconds_difference(
    left: datetime,
    right: datetime,
) -> float:
    return abs(
        (
            left
            - right
        ).total_seconds()
    )


def _before(
    lichun: datetime,
) -> datetime:
    return (
        lichun
        - timedelta(
            seconds=1
        )
    )


def _after(
    lichun: datetime,
) -> datetime:
    return (
        lichun
        + timedelta(
            seconds=1
        )
    )


# ============================================================
# 1. Golden data integrity
# ============================================================


def test_lichun_golden_case_count():
    assert (
        len(
            LICHUN_GOLDEN_CASES
        )
        == 4
    )


def test_lichun_golden_years_are_unique():
    years = [
        item[
            "year"
        ]
        for item in LICHUN_GOLDEN_CASES
    ]

    assert (
        len(
            years
        )
        == len(
            set(
                years
            )
        )
    )


@pytest.mark.parametrize(
    "case",
    LICHUN_GOLDEN_CASES,
    ids=LICHUN_CASE_IDS,
)
def test_lichun_golden_case_has_source(
    case,
):
    assert isinstance(
        case[
            "source"
        ],
        str,
    )

    assert (
        case[
            "source"
        ].strip()
    )


# ============================================================
# 2. Astronomical Lichun vs NAOJ
# ============================================================


@pytest.mark.parametrize(
    "case",
    LICHUN_GOLDEN_CASES,
    ids=LICHUN_CASE_IDS,
)
def test_calculated_lichun_matches_naoj_official_minute(
    case,
):
    """
    Skyfield計算値が国立天文台の分単位公表値と
    ±90秒以内で一致することを確認する。
    """

    calculated = (
        _calculated_lichun(
            case
        )
    )

    official = case[
        "official"
    ]

    difference = (
        _seconds_difference(
            calculated,
            official,
        )
    )

    assert (
        difference
        <= OFFICIAL_TIME_TOLERANCE_SECONDS
    ), (
        f"{case['year']}年立春が"
        "国立天文台公表時刻から外れています。 "
        f"calculated={calculated!r}, "
        f"official={official!r}, "
        f"difference_seconds={difference}"
    )


@pytest.mark.parametrize(
    "case",
    LICHUN_GOLDEN_CASES,
    ids=LICHUN_CASE_IDS,
)
def test_calculated_lichun_is_timezone_naive(
    case,
):
    """
    year.pyの公開契約どおり、
    JST相当のtimezone-naive datetimeであること。
    """

    calculated = (
        _calculated_lichun(
            case
        )
    )

    assert (
        calculated.tzinfo
        is None
    )


@pytest.mark.parametrize(
    "case",
    LICHUN_GOLDEN_CASES,
    ids=LICHUN_CASE_IDS,
)
def test_calculated_lichun_calendar_year_matches_requested_year(
    case,
):
    calculated = (
        _calculated_lichun(
            case
        )
    )

    assert (
        calculated.year
        == case[
            "year"
        ]
    )


# ============================================================
# 3. Important date variation
# ============================================================


def test_2025_lichun_is_february_3_not_fixed_february_4():
    """
    固定2月4日実装への退行を防止する。

    2025年の立春は
    2月3日23:10 JST（国立天文台）。
    """

    calculated = (
        get_lichun_datetime(
            2025
        )
    )

    assert (
        calculated.month,
        calculated.day,
    ) == (
        2,
        3,
    )


def test_2026_lichun_is_february_4():
    calculated = (
        get_lichun_datetime(
            2026
        )
    )

    assert (
        calculated.month,
        calculated.day,
    ) == (
        2,
        4,
    )


def test_lichun_time_is_not_hardcoded_midnight():
    """
    旧暫定実装の00:00固定へ戻っていないこと。
    """

    for case in (
        LICHUN_GOLDEN_CASES
    ):
        calculated = (
            _calculated_lichun(
                case
            )
        )

        assert (
            calculated.hour,
            calculated.minute,
        ) != (
            0,
            0,
        )


# ============================================================
# 4. Effective year exact boundary
# ============================================================


@pytest.mark.parametrize(
    "case",
    LICHUN_GOLDEN_CASES,
    ids=LICHUN_CASE_IDS,
)
def test_effective_year_one_second_before_lichun(
    case,
):
    lichun = (
        _calculated_lichun(
            case
        )
    )

    assert (
        calculate_effective_year(
            _before(
                lichun
            )
        )
        == case[
            "previous_effective_year"
        ]
    )


@pytest.mark.parametrize(
    "case",
    LICHUN_GOLDEN_CASES,
    ids=LICHUN_CASE_IDS,
)
def test_effective_year_exactly_at_lichun(
    case,
):
    """
    立春ちょうどから新しい干支年。
    """

    lichun = (
        _calculated_lichun(
            case
        )
    )

    assert (
        calculate_effective_year(
            lichun
        )
        == case[
            "current_effective_year"
        ]
    )


@pytest.mark.parametrize(
    "case",
    LICHUN_GOLDEN_CASES,
    ids=LICHUN_CASE_IDS,
)
def test_effective_year_one_second_after_lichun(
    case,
):
    lichun = (
        _calculated_lichun(
            case
        )
    )

    assert (
        calculate_effective_year(
            _after(
                lichun
            )
        )
        == case[
            "current_effective_year"
        ]
    )


# ============================================================
# 5. Year pillar exact boundary
# ============================================================


@pytest.mark.parametrize(
    "case",
    LICHUN_GOLDEN_CASES,
    ids=LICHUN_CASE_IDS,
)
def test_year_pillar_one_second_before_lichun(
    case,
):
    lichun = (
        _calculated_lichun(
            case
        )
    )

    assert (
        calculate_year_pillar(
            _before(
                lichun
            )
        )
        == case[
            "previous_pillar"
        ]
    )


@pytest.mark.parametrize(
    "case",
    LICHUN_GOLDEN_CASES,
    ids=LICHUN_CASE_IDS,
)
def test_year_pillar_exactly_at_lichun(
    case,
):
    lichun = (
        _calculated_lichun(
            case
        )
    )

    assert (
        calculate_year_pillar(
            lichun
        )
        == case[
            "current_pillar"
        ]
    )


@pytest.mark.parametrize(
    "case",
    LICHUN_GOLDEN_CASES,
    ids=LICHUN_CASE_IDS,
)
def test_year_pillar_one_second_after_lichun(
    case,
):
    lichun = (
        _calculated_lichun(
            case
        )
    )

    assert (
        calculate_year_pillar(
            _after(
                lichun
            )
        )
        == case[
            "current_pillar"
        ]
    )


# ============================================================
# 6. Explicit verified transitions
# ============================================================


def test_1985_lichun_transition():
    lichun = (
        get_lichun_datetime(
            1985
        )
    )

    assert (
        calculate_year_pillar(
            lichun
            - timedelta(
                seconds=1
            )
        )
        == "甲子"
    )

    assert (
        calculate_year_pillar(
            lichun
        )
        == "乙丑"
    )


def test_2024_lichun_transition():
    lichun = (
        get_lichun_datetime(
            2024
        )
    )

    assert (
        calculate_year_pillar(
            lichun
            - timedelta(
                seconds=1
            )
        )
        == "癸卯"
    )

    assert (
        calculate_year_pillar(
            lichun
        )
        == "甲辰"
    )


def test_2025_lichun_transition():
    lichun = (
        get_lichun_datetime(
            2025
        )
    )

    assert (
        calculate_year_pillar(
            lichun
            - timedelta(
                seconds=1
            )
        )
        == "甲辰"
    )

    assert (
        calculate_year_pillar(
            lichun
        )
        == "乙巳"
    )


def test_2026_lichun_transition():
    lichun = (
        get_lichun_datetime(
            2026
        )
    )

    assert (
        calculate_year_pillar(
            lichun
            - timedelta(
                seconds=1
            )
        )
        == "乙巳"
    )

    assert (
        calculate_year_pillar(
            lichun
        )
        == "丙午"
    )


# ============================================================
# 7. Regression against Jan 1 boundary
# ============================================================


@pytest.mark.parametrize(
    (
        "birth_datetime",
        "expected_pillar",
    ),
    (
        (
            datetime(
                2024,
                1,
                1,
                12,
                0,
            ),
            "癸卯",
        ),
        (
            datetime(
                2025,
                1,
                1,
                12,
                0,
            ),
            "甲辰",
        ),
        (
            datetime(
                2026,
                1,
                1,
                12,
                0,
            ),
            "乙巳",
        ),
    ),
)
def test_january_1_still_uses_previous_ganzhi_year(
    birth_datetime,
    expected_pillar,
):
    """
    西暦1月1日で年柱を切り替えないことを固定する。
    """

    assert (
        calculate_year_pillar(
            birth_datetime
        )
        == expected_pillar
    )


# ============================================================
# 8. Before/after same calendar date
# ============================================================


def test_2026_same_date_changes_year_pillar_at_actual_lichun_time():
    """
    2026-02-04は同じ日付内で
    立春前後に年柱が切り替わる。

    「日付だけ」で年柱を決める実装への退行を防ぐ。
    """

    lichun = (
        get_lichun_datetime(
            2026
        )
    )

    before = (
        lichun
        - timedelta(
            minutes=1
        )
    )

    after = (
        lichun
        + timedelta(
            minutes=1
        )
    )

    assert (
        before.date()
        == after.date()
    )

    assert (
        calculate_year_pillar(
            before
        )
        == "乙巳"
    )

    assert (
        calculate_year_pillar(
            after
        )
        == "丙午"
    )


def test_2025_february_3_changes_year_pillar_late_at_night():
    """
    2025年は2月3日の夜に立春がある。
    固定2月4日境界では誤判定になるケース。
    """

    lichun = (
        get_lichun_datetime(
            2025
        )
    )

    assert (
        lichun.date()
        == datetime(
            2025,
            2,
            3,
        ).date()
    )

    before = (
        lichun
        - timedelta(
            seconds=1
        )
    )

    after = (
        lichun
        + timedelta(
            seconds=1
        )
    )

    assert (
        calculate_year_pillar(
            before
        )
        == "甲辰"
    )

    assert (
        calculate_year_pillar(
            after
        )
        == "乙巳"
    )


# ============================================================
# 9. Near-Lichun
# ============================================================


@pytest.mark.parametrize(
    "case",
    LICHUN_GOLDEN_CASES,
    ids=LICHUN_CASE_IDS,
)
def test_is_near_lichun_exact_boundary(
    case,
):
    lichun = (
        _calculated_lichun(
            case
        )
    )

    assert (
        is_near_lichun(
            lichun
        )
        is True
    )


@pytest.mark.parametrize(
    "case",
    LICHUN_GOLDEN_CASES,
    ids=LICHUN_CASE_IDS,
)
def test_is_near_lichun_within_two_days(
    case,
):
    lichun = (
        _calculated_lichun(
            case
        )
    )

    assert (
        is_near_lichun(
            lichun
            - timedelta(
                days=1,
                hours=23,
                minutes=59,
            )
        )
        is True
    )

    assert (
        is_near_lichun(
            lichun
            + timedelta(
                days=1,
                hours=23,
                minutes=59,
            )
        )
        is True
    )


@pytest.mark.parametrize(
    "case",
    LICHUN_GOLDEN_CASES,
    ids=LICHUN_CASE_IDS,
)
def test_is_near_lichun_outside_two_days(
    case,
):
    lichun = (
        _calculated_lichun(
            case
        )
    )

    assert (
        is_near_lichun(
            lichun
            - timedelta(
                days=2,
                seconds=1,
            )
        )
        is False
    )

    assert (
        is_near_lichun(
            lichun
            + timedelta(
                days=2,
                seconds=1,
            )
        )
        is False
    )


def test_is_near_lichun_zero_margin():
    lichun = (
        get_lichun_datetime(
            2026
        )
    )

    assert (
        is_near_lichun(
            lichun,
            margin_days=0,
        )
        is True
    )

    assert (
        is_near_lichun(
            lichun
            + timedelta(
                seconds=1
            ),
            margin_days=0,
        )
        is False
    )


# ============================================================
# 10. Backward compatibility alias
# ============================================================


@pytest.mark.parametrize(
    "case",
    LICHUN_GOLDEN_CASES,
    ids=LICHUN_CASE_IDS,
)
def test_provisional_lichun_alias_matches_new_function(
    case,
):
    lichun = (
        _calculated_lichun(
            case
        )
    )

    samples = (
        lichun
        - timedelta(
            days=3
        ),
        lichun
        - timedelta(
            seconds=1
        ),
        lichun,
        lichun
        + timedelta(
            seconds=1
        ),
        lichun
        + timedelta(
            days=3
        ),
    )

    for sample in samples:
        assert (
            is_near_provisional_lichun(
                sample
            )
            == is_near_lichun(
                sample
            )
        )


# ============================================================
# 11. Timezone-aware compatibility
# ============================================================


def test_timezone_aware_jst_datetime_is_accepted_at_boundary():
    """
    year.pyはaware datetimeの場合、
    現行仕様として同じローカル時刻表現へ
    tzinfoを外して比較する。

    ここではその既存契約を固定する。
    """

    lichun = (
        get_lichun_datetime(
            2026
        )
    )

    jst = timezone(
        timedelta(
            hours=9
        )
    )

    aware = lichun.replace(
        tzinfo=jst
    )

    assert (
        calculate_effective_year(
            aware
        )
        == 2026
    )

    assert (
        calculate_year_pillar(
            aware
        )
        == "丙午"
    )


def test_timezone_aware_jst_one_second_before_boundary():
    lichun = (
        get_lichun_datetime(
            2026
        )
    )

    jst = timezone(
        timedelta(
            hours=9
        )
    )

    aware_before = (
        lichun
        - timedelta(
            seconds=1
        )
    ).replace(
        tzinfo=jst
    )

    assert (
        calculate_effective_year(
            aware_before
        )
        == 2025
    )

    assert (
        calculate_year_pillar(
            aware_before
        )
        == "乙巳"
    )


# ============================================================
# 12. Validation
# ============================================================


@pytest.mark.parametrize(
    "bad_value",
    (
        None,
        "2026-02-04",
        20260204,
        {},
        [],
    ),
)
def test_calculate_effective_year_rejects_non_datetime(
    bad_value,
):
    with pytest.raises(
        TypeError
    ):
        calculate_effective_year(
            bad_value
        )


@pytest.mark.parametrize(
    "bad_value",
    (
        None,
        "2026-02-04",
        20260204,
        {},
        [],
    ),
)
def test_calculate_year_pillar_rejects_non_datetime(
    bad_value,
):
    with pytest.raises(
        TypeError
    ):
        calculate_year_pillar(
            bad_value
        )


@pytest.mark.parametrize(
    "bad_value",
    (
        None,
        "2026-02-04",
        20260204,
        {},
        [],
    ),
)
def test_is_near_lichun_rejects_non_datetime(
    bad_value,
):
    with pytest.raises(
        TypeError
    ):
        is_near_lichun(
            bad_value
        )


@pytest.mark.parametrize(
    "bad_margin",
    (
        -1,
        -10,
    ),
)
def test_is_near_lichun_rejects_negative_margin(
    bad_margin,
):
    with pytest.raises(
        ValueError
    ):
        is_near_lichun(
            datetime(
                2026,
                2,
                4,
                5,
                2,
            ),
            margin_days=bad_margin,
        )


@pytest.mark.parametrize(
    "bad_margin",
    (
        None,
        1.5,
        "2",
        [],
        {},
    ),
)
def test_is_near_lichun_rejects_non_integer_margin(
    bad_margin,
):
    with pytest.raises(
        TypeError
    ):
        is_near_lichun(
            datetime(
                2026,
                2,
                4,
                5,
                2,
            ),
            margin_days=bad_margin,
        )


def test_get_lichun_datetime_rejects_non_integer_year():
    with pytest.raises(
        TypeError
    ):
        get_lichun_datetime(
            "2026"
        )


def test_get_lichun_datetime_rejects_year_zero():
    with pytest.raises(
        ValueError
    ):
        get_lichun_datetime(
            0
        )


# ============================================================
# 13. Base year contract
# ============================================================


def test_base_year_is_1984():
    assert (
        BASE_YEAR
        == 1984
    )


def test_base_ganzhi_index_is_zero():
    assert (
        BASE_YEAR_GANZHI_INDEX
        == 0
    )


def test_1984_after_lichun_is_kinoene():
    lichun = (
        get_lichun_datetime(
            1984
        )
    )

    assert (
        calculate_year_pillar(
            lichun
        )
        == "甲子"
    )


def test_1984_before_lichun_is_previous_cycle_year():
    lichun = (
        get_lichun_datetime(
            1984
        )
    )

    assert (
        calculate_year_pillar(
            lichun
            - timedelta(
                seconds=1
            )
        )
        == "癸亥"
    )


# ============================================================
# 14. Metadata
# ============================================================


def test_year_method_is_astronomical_lichun():
    assert (
        YEAR_METHOD
        == "astronomical_lichun_v3"
    )


def test_year_status_is_astronomical():
    assert (
        YEAR_STATUS
        == "astronomical"
    )


def test_year_metadata_contract():
    metadata = (
        get_year_pillar_metadata()
    )

    assert isinstance(
        metadata,
        dict,
    )

    assert (
        metadata[
            "method"
        ]
        == YEAR_METHOD
    )

    assert (
        metadata[
            "status"
        ]
        == YEAR_STATUS
    )

    assert (
        metadata[
            "base_year"
        ]
        == 1984
    )

    assert (
        metadata[
            "base_ganzhi"
        ]
        == "甲子"
    )

    assert (
        metadata[
            "boundary"
        ]
        == "astronomical_lichun"
    )

    assert (
        metadata[
            "timezone"
        ]
        == "JST_naive_solar_term"
    )

    assert (
        metadata[
            "solar_term_source"
        ]
        == "solar_terms_v3"
    )

    assert (
        metadata[
            "true_solar_time"
        ]
        is False
    )


# ============================================================
# 15. Reproducibility
# ============================================================


@pytest.mark.parametrize(
    "case",
    LICHUN_GOLDEN_CASES,
    ids=LICHUN_CASE_IDS,
)
def test_lichun_datetime_is_reproducible(
    case,
):
    first = (
        _calculated_lichun(
            case
        )
    )

    second = (
        _calculated_lichun(
            case
        )
    )

    assert (
        first
        == second
    )


@pytest.mark.parametrize(
    "case",
    LICHUN_GOLDEN_CASES,
    ids=LICHUN_CASE_IDS,
)
def test_boundary_year_pillar_is_reproducible(
    case,
):
    lichun = (
        _calculated_lichun(
            case
        )
    )

    samples = (
        lichun
        - timedelta(
            seconds=1
        ),
        lichun,
        lichun
        + timedelta(
            seconds=1
        ),
    )

    first = [
        calculate_year_pillar(
            value
        )
        for value in samples
    ]

    second = [
        calculate_year_pillar(
            value
        )
        for value in samples
    ]

    assert (
        first
        == second
    )


# ============================================================
# 16. Final smoke
# ============================================================


def test_verified_lichun_boundary_final_smoke():
    """
    最終スモーク。

    4年分について、
    ・国立天文台公表時刻との整合
    ・1秒前は前年柱
    ・立春ちょうどから当年柱
    を一括確認する。
    """

    actual = {}

    for case in (
        LICHUN_GOLDEN_CASES
    ):
        lichun = (
            _calculated_lichun(
                case
            )
        )

        official_difference = (
            _seconds_difference(
                lichun,
                case[
                    "official"
                ],
            )
        )

        actual[
            case[
                "year"
            ]
        ] = {
            "official_match": (
                official_difference
                <= (
                    OFFICIAL_TIME_TOLERANCE_SECONDS
                )
            ),
            "before": (
                calculate_year_pillar(
                    lichun
                    - timedelta(
                        seconds=1
                    )
                )
            ),
            "at": (
                calculate_year_pillar(
                    lichun
                )
            ),
            "after": (
                calculate_year_pillar(
                    lichun
                    + timedelta(
                        seconds=1
                    )
                )
            ),
        }

    assert actual == {
        1985: {
            "official_match": True,
            "before": "甲子",
            "at": "乙丑",
            "after": "乙丑",
        },
        2024: {
            "official_match": True,
            "before": "癸卯",
            "at": "甲辰",
            "after": "甲辰",
        },
        2025: {
            "official_match": True,
            "before": "甲辰",
            "at": "乙巳",
            "after": "乙巳",
        },
        2026: {
            "official_match": True,
            "before": "乙巳",
            "at": "丙午",
            "after": "丙午",
        },
    }


# ============================================================
# 17. Test metadata
# ============================================================


def test_verified_lichun_boundary_metadata():
    assert (
        VERIFIED_LICHUN_BOUNDARY_METHOD
        == "naoj_verified_lichun_boundary_v1"
    )

    assert (
        VERIFIED_LICHUN_BOUNDARY_STATUS
        == "golden_regression"
    )
