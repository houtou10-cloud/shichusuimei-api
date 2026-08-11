"""
tests/test_verified_day_boundary.py

四柱推命 日柱・日界
ゴールデン回帰テスト v1

目的
----
engine/day.py と engine/pillars.py について、

・日柱が1日ごとに六十干支を1つ進むこと
・現行仕様の日界が00:00であること
・23:59:59では前日柱
・00:00:00ちょうどから新日柱
・00:00:01も新日柱
・日柱の天干と日主が一致すること
・既知の検証日
  1984-07-10 = 乙巳
  1984-07-21 = 丙辰
  1984-07-22 = 丁巳
  1985-07-17 = 丁巳
  を固定すること

を検証する。

重要
----
現行プロジェクトでは、
日柱の日界は00:00とする。

23:00で日柱を切り替える流派も存在するが、
その流派差はこのテストでは採用しない。

時柱の子刻は23:00〜00:59だが、
「時支の子刻」と「日柱の日界」は別契約として扱う。

Version
-------
verified_day_boundary_v1
"""

from __future__ import annotations

from datetime import (
    date,
    datetime,
    timedelta,
)
from zoneinfo import ZoneInfo

import pytest

from engine.day import (
    calculate_day_pillar,
)
from engine.ganzhi import (
    next_ganzhi,
    split_ganzhi,
)
from engine.pillars import (
    calculate_four_pillars,
)


# ============================================================
# Constants
# ============================================================


JST = ZoneInfo(
    "Asia/Tokyo"
)

VERIFIED_DAY_BOUNDARY_METHOD = (
    "verified_midnight_day_boundary_v1"
)

VERIFIED_DAY_BOUNDARY_STATUS = (
    "golden_regression"
)


# ============================================================
# Golden dates
# ============================================================


GOLDEN_DAYS = (
    {
        "target": date(
            1984,
            7,
            10,
        ),
        "pillar": "乙巳",
        "day_master": "乙",
    },
    {
        "target": date(
            1984,
            7,
            21,
        ),
        "pillar": "丙辰",
        "day_master": "丙",
    },
    {
        "target": date(
            1984,
            7,
            22,
        ),
        "pillar": "丁巳",
        "day_master": "丁",
    },
    {
        "target": date(
            1984,
            7,
            23,
        ),
        "pillar": "戊午",
        "day_master": "戊",
    },
    {
        "target": date(
            1985,
            7,
            17,
        ),
        "pillar": "丁巳",
        "day_master": "丁",
    },
)


GOLDEN_IDS = tuple(
    item[
        "target"
    ].isoformat()
    for item in GOLDEN_DAYS
)


# ============================================================
# Helpers
# ============================================================


def _calculate_four(
    value: datetime,
) -> dict:
    """
    datetimeから四柱を計算する。
    """

    result = calculate_four_pillars(
        value
    )

    assert isinstance(
        result,
        dict,
    )

    assert (
        "day"
        in result
    )

    assert (
        "day_master"
        in result
    )

    return result


def _day_pillar_from_datetime(
    value: datetime,
) -> str:
    """
    calculate_four_pillars()経由で
    日柱を取得する。
    """

    result = _calculate_four(
        value
    )

    day_data = result[
        "day"
    ]

    assert isinstance(
        day_data,
        dict,
    )

    pillar = day_data[
        "pillar"
    ]

    assert isinstance(
        pillar,
        str,
    )

    return pillar


def _day_master_from_datetime(
    value: datetime,
) -> str:
    """
    calculate_four_pillars()経由で
    日主を取得する。
    """

    result = _calculate_four(
        value
    )

    day_master = result[
        "day_master"
    ]

    assert isinstance(
        day_master,
        dict,
    )

    stem = day_master[
        "stem"
    ]

    assert isinstance(
        stem,
        str,
    )

    return stem


def _midnight(
    year: int,
    month: int,
    day: int,
) -> datetime:
    return datetime(
        year,
        month,
        day,
        0,
        0,
        0,
        tzinfo=JST,
    )


# ============================================================
# 1. Golden-data integrity
# ============================================================


def test_golden_day_ids_are_unique():
    assert (
        len(
            GOLDEN_IDS
        )
        == len(
            set(
                GOLDEN_IDS
            )
        )
    )


def test_golden_day_count():
    assert (
        len(
            GOLDEN_DAYS
        )
        == 5
    )


@pytest.mark.parametrize(
    "item",
    GOLDEN_DAYS,
    ids=GOLDEN_IDS,
)
def test_golden_pillar_is_two_characters(
    item,
):
    assert isinstance(
        item[
            "pillar"
        ],
        str,
    )

    assert (
        len(
            item[
                "pillar"
            ]
        )
        == 2
    )


# ============================================================
# 2. Direct engine/day.py regression
# ============================================================


@pytest.mark.parametrize(
    "item",
    GOLDEN_DAYS,
    ids=GOLDEN_IDS,
)
def test_verified_day_pillar_direct(
    item,
):
    """
    engine/day.py の直接回帰。
    """

    result = calculate_day_pillar(
        item[
            "target"
        ]
    )

    assert (
        result
        == item[
            "pillar"
        ]
    )


def test_verified_1984_07_10_is_otsushi():
    assert (
        calculate_day_pillar(
            date(
                1984,
                7,
                10,
            )
        )
        == "乙巳"
    )


def test_verified_1984_07_21_is_heishin():
    assert (
        calculate_day_pillar(
            date(
                1984,
                7,
                21,
            )
        )
        == "丙辰"
    )


def test_verified_1984_07_22_is_teishi():
    assert (
        calculate_day_pillar(
            date(
                1984,
                7,
                22,
            )
        )
        == "丁巳"
    )


def test_verified_1984_07_23_is_bogo():
    assert (
        calculate_day_pillar(
            date(
                1984,
                7,
                23,
            )
        )
        == "戊午"
    )


def test_verified_1985_07_17_is_teishi():
    assert (
        calculate_day_pillar(
            date(
                1985,
                7,
                17,
            )
        )
        == "丁巳"
    )


# ============================================================
# 3. Consecutive-day progression
# ============================================================


@pytest.mark.parametrize(
    (
        "first_date",
        "second_date",
    ),
    (
        (
            date(
                1984,
                7,
                20,
            ),
            date(
                1984,
                7,
                21,
            ),
        ),
        (
            date(
                1984,
                7,
                21,
            ),
            date(
                1984,
                7,
                22,
            ),
        ),
        (
            date(
                1984,
                7,
                22,
            ),
            date(
                1984,
                7,
                23,
            ),
        ),
        (
            date(
                1984,
                7,
                23,
            ),
            date(
                1984,
                7,
                24,
            ),
        ),
    ),
)
def test_day_pillar_moves_one_ganzhi_per_day(
    first_date,
    second_date,
):
    first = calculate_day_pillar(
        first_date
    )

    second = calculate_day_pillar(
        second_date
    )

    assert (
        next_ganzhi(
            first
        )
        == second
    )


def test_known_three_day_sequence():
    actual = [
        calculate_day_pillar(
            date(
                1984,
                7,
                day,
            )
        )
        for day in (
            21,
            22,
            23,
        )
    ]

    assert actual == [
        "丙辰",
        "丁巳",
        "戊午",
    ]


# ============================================================
# 4. 00:00 exact boundary
# ============================================================


def test_day_boundary_one_second_before_midnight():
    """
    1984-07-21 23:59:59 は丙辰日。
    """

    boundary = _midnight(
        1984,
        7,
        22,
    )

    target = (
        boundary
        - timedelta(
            seconds=1
        )
    )

    assert (
        target
        == datetime(
            1984,
            7,
            21,
            23,
            59,
            59,
            tzinfo=JST,
        )
    )

    assert (
        _day_pillar_from_datetime(
            target
        )
        == "丙辰"
    )


def test_day_boundary_exact_midnight():
    """
    1984-07-22 00:00:00 から丁巳日。
    """

    boundary = _midnight(
        1984,
        7,
        22,
    )

    assert (
        _day_pillar_from_datetime(
            boundary
        )
        == "丁巳"
    )


def test_day_boundary_one_second_after_midnight():
    """
    1984-07-22 00:00:01 も丁巳日。
    """

    boundary = _midnight(
        1984,
        7,
        22,
    )

    target = (
        boundary
        + timedelta(
            seconds=1
        )
    )

    assert (
        _day_pillar_from_datetime(
            target
        )
        == "丁巳"
    )


def test_midnight_boundary_changes_exactly_once():
    """
    23:59:59 → 00:00:00 でだけ
    日柱が切り替わることを確認する。
    """

    boundary = _midnight(
        1984,
        7,
        22,
    )

    before = _day_pillar_from_datetime(
        boundary
        - timedelta(
            seconds=1
        )
    )

    exact = _day_pillar_from_datetime(
        boundary
    )

    after = _day_pillar_from_datetime(
        boundary
        + timedelta(
            seconds=1
        )
    )

    assert before == "丙辰"
    assert exact == "丁巳"
    assert after == "丁巳"

    assert (
        before
        != exact
    )

    assert (
        exact
        == after
    )


# ============================================================
# 5. 23:00 is NOT the day boundary
# ============================================================


def test_2300_does_not_change_day_pillar():
    """
    現行仕様では23:00は子刻開始だが、
    日柱はまだ当日のまま。

    1984-07-21 22:59:59
    1984-07-21 23:00:00
    の両方とも丙辰。
    """

    before = datetime(
        1984,
        7,
        21,
        22,
        59,
        59,
        tzinfo=JST,
    )

    exact = datetime(
        1984,
        7,
        21,
        23,
        0,
        0,
        tzinfo=JST,
    )

    assert (
        _day_pillar_from_datetime(
            before
        )
        == "丙辰"
    )

    assert (
        _day_pillar_from_datetime(
            exact
        )
        == "丙辰"
    )


def test_235959_is_still_previous_day_pillar():
    target = datetime(
        1984,
        7,
        21,
        23,
        59,
        59,
        tzinfo=JST,
    )

    assert (
        _day_pillar_from_datetime(
            target
        )
        == "丙辰"
    )


def test_000000_is_new_day_pillar():
    target = datetime(
        1984,
        7,
        22,
        0,
        0,
        0,
        tzinfo=JST,
    )

    assert (
        _day_pillar_from_datetime(
            target
        )
        == "丁巳"
    )


# ============================================================
# 6. Same-date invariant
# ============================================================


@pytest.mark.parametrize(
    "hour",
    (
        0,
        1,
        6,
        12,
        18,
        22,
        23,
    ),
)
def test_same_calendar_date_has_same_day_pillar(
    hour,
):
    """
    1984-07-22内では時刻に関係なく丁巳。
    """

    target = datetime(
        1984,
        7,
        22,
        hour,
        30,
        0,
        tzinfo=JST,
    )

    assert (
        _day_pillar_from_datetime(
            target
        )
        == "丁巳"
    )


@pytest.mark.parametrize(
    (
        "hour",
        "minute",
        "second",
    ),
    (
        (0, 0, 0),
        (0, 0, 1),
        (0, 59, 59),
        (12, 0, 0),
        (22, 59, 59),
        (23, 0, 0),
        (23, 59, 59),
    ),
)
def test_entire_1984_07_22_is_teishi(
    hour,
    minute,
    second,
):
    target = datetime(
        1984,
        7,
        22,
        hour,
        minute,
        second,
        tzinfo=JST,
    )

    assert (
        _day_pillar_from_datetime(
            target
        )
        == "丁巳"
    )


# ============================================================
# 7. Day master
# ============================================================


def test_day_master_before_midnight():
    target = datetime(
        1984,
        7,
        21,
        23,
        59,
        59,
        tzinfo=JST,
    )

    assert (
        _day_master_from_datetime(
            target
        )
        == "丙"
    )


def test_day_master_exact_midnight():
    target = datetime(
        1984,
        7,
        22,
        0,
        0,
        0,
        tzinfo=JST,
    )

    assert (
        _day_master_from_datetime(
            target
        )
        == "丁"
    )


def test_day_master_one_second_after_midnight():
    target = datetime(
        1984,
        7,
        22,
        0,
        0,
        1,
        tzinfo=JST,
    )

    assert (
        _day_master_from_datetime(
            target
        )
        == "丁"
    )


@pytest.mark.parametrize(
    "item",
    GOLDEN_DAYS,
    ids=GOLDEN_IDS,
)
def test_day_master_matches_golden_day_stem(
    item,
):
    target = datetime(
        item[
            "target"
        ].year,
        item[
            "target"
        ].month,
        item[
            "target"
        ].day,
        12,
        0,
        0,
        tzinfo=JST,
    )

    assert (
        _day_master_from_datetime(
            target
        )
        == item[
            "day_master"
        ]
    )


# ============================================================
# 8. Day pillar stem consistency
# ============================================================


@pytest.mark.parametrize(
    "item",
    GOLDEN_DAYS,
    ids=GOLDEN_IDS,
)
def test_day_pillar_first_character_matches_day_master(
    item,
):
    pillar = item[
        "pillar"
    ]

    assert (
        pillar[
            0
        ]
        == item[
            "day_master"
        ]
    )


@pytest.mark.parametrize(
    "item",
    GOLDEN_DAYS,
    ids=GOLDEN_IDS,
)
def test_split_ganzhi_stem_matches_day_master(
    item,
):
    split = split_ganzhi(
        item[
            "pillar"
        ]
    )

    assert (
        split[
            "stem"
        ]
        == item[
            "day_master"
        ]
    )


# ============================================================
# 9. calculate_day_pillar vs calculate_four_pillars
# ============================================================


@pytest.mark.parametrize(
    "item",
    GOLDEN_DAYS,
    ids=GOLDEN_IDS,
)
def test_direct_day_engine_and_four_pillar_engine_agree(
    item,
):
    direct = calculate_day_pillar(
        item[
            "target"
        ]
    )

    target_datetime = datetime(
        item[
            "target"
        ].year,
        item[
            "target"
        ].month,
        item[
            "target"
        ].day,
        12,
        0,
        0,
        tzinfo=JST,
    )

    integrated = (
        _day_pillar_from_datetime(
            target_datetime
        )
    )

    assert (
        direct
        == integrated
        == item[
            "pillar"
        ]
    )


# ============================================================
# 10. Midnight boundary across multiple dates
# ============================================================


@pytest.mark.parametrize(
    (
        "boundary",
        "before_pillar",
        "after_pillar",
    ),
    (
        (
            datetime(
                1984,
                7,
                21,
                0,
                0,
                0,
                tzinfo=JST,
            ),
            "乙卯",
            "丙辰",
        ),
        (
            datetime(
                1984,
                7,
                22,
                0,
                0,
                0,
                tzinfo=JST,
            ),
            "丙辰",
            "丁巳",
        ),
        (
            datetime(
                1984,
                7,
                23,
                0,
                0,
                0,
                tzinfo=JST,
            ),
            "丁巳",
            "戊午",
        ),
    ),
)
def test_multiple_midnight_boundaries(
    boundary,
    before_pillar,
    after_pillar,
):
    assert (
        _day_pillar_from_datetime(
            boundary
            - timedelta(
                seconds=1
            )
        )
        == before_pillar
    )

    assert (
        _day_pillar_from_datetime(
            boundary
        )
        == after_pillar
    )

    assert (
        _day_pillar_from_datetime(
            boundary
            + timedelta(
                seconds=1
            )
        )
        == after_pillar
    )


# ============================================================
# 11. Month/year transition does not break daily cycle
# ============================================================


def test_end_of_month_daily_progression():
    """
    月末でも日柱は1日だけ進む。
    """

    first_date = date(
        1984,
        7,
        31,
    )

    second_date = date(
        1984,
        8,
        1,
    )

    first = calculate_day_pillar(
        first_date
    )

    second = calculate_day_pillar(
        second_date
    )

    assert (
        next_ganzhi(
            first
        )
        == second
    )


def test_end_of_year_daily_progression():
    """
    年末でも日柱は1日だけ進む。
    """

    first_date = date(
        1984,
        12,
        31,
    )

    second_date = date(
        1985,
        1,
        1,
    )

    first = calculate_day_pillar(
        first_date
    )

    second = calculate_day_pillar(
        second_date
    )

    assert (
        next_ganzhi(
            first
        )
        == second
    )


def test_leap_day_daily_progression():
    """
    うるう日をまたいでも
    日柱は1日ずつ進む。
    """

    feb28 = calculate_day_pillar(
        date(
            1984,
            2,
            28,
        )
    )

    feb29 = calculate_day_pillar(
        date(
            1984,
            2,
            29,
        )
    )

    mar1 = calculate_day_pillar(
        date(
            1984,
            3,
            1,
        )
    )

    assert (
        next_ganzhi(
            feb28
        )
        == feb29
    )

    assert (
        next_ganzhi(
            feb29
        )
        == mar1
    )


# ============================================================
# 12. 60-day cycle
# ============================================================


def test_day_pillar_repeats_after_60_days():
    start = date(
        1984,
        7,
        22,
    )

    later = (
        start
        + timedelta(
            days=60
        )
    )

    assert (
        calculate_day_pillar(
            start
        )
        == calculate_day_pillar(
            later
        )
    )


@pytest.mark.parametrize(
    "offset",
    (
        1,
        2,
        10,
        30,
        59,
    ),
)
def test_day_pillar_before_sixty_days_not_same(
    offset,
):
    start = date(
        1984,
        7,
        22,
    )

    later = (
        start
        + timedelta(
            days=offset
        )
    )

    assert (
        calculate_day_pillar(
            start
        )
        != calculate_day_pillar(
            later
        )
    )


# ============================================================
# 13. Timezone-aware JST
# ============================================================


def test_jst_aware_datetime_before_midnight():
    target = datetime(
        1984,
        7,
        21,
        23,
        59,
        59,
        tzinfo=JST,
    )

    assert (
        _day_pillar_from_datetime(
            target
        )
        == "丙辰"
    )


def test_jst_aware_datetime_at_midnight():
    target = datetime(
        1984,
        7,
        22,
        0,
        0,
        0,
        tzinfo=JST,
    )

    assert (
        _day_pillar_from_datetime(
            target
        )
        == "丁巳"
    )


# ============================================================
# 14. Naive datetime compatibility
# ============================================================


def test_naive_datetime_boundary_before_midnight():
    """
    calculate_four_pillarsがnaive datetimeを
    現行契約として受け付ける場合の回帰。
    """

    target = datetime(
        1984,
        7,
        21,
        23,
        59,
        59,
    )

    assert (
        _day_pillar_from_datetime(
            target
        )
        == "丙辰"
    )


def test_naive_datetime_boundary_at_midnight():
    target = datetime(
        1984,
        7,
        22,
        0,
        0,
        0,
    )

    assert (
        _day_pillar_from_datetime(
            target
        )
        == "丁巳"
    )


# ============================================================
# 15. Reproducibility
# ============================================================


@pytest.mark.parametrize(
    "item",
    GOLDEN_DAYS,
    ids=GOLDEN_IDS,
)
def test_day_pillar_is_reproducible(
    item,
):
    first = calculate_day_pillar(
        item[
            "target"
        ]
    )

    second = calculate_day_pillar(
        item[
            "target"
        ]
    )

    assert (
        first
        == second
        == item[
            "pillar"
        ]
    )


def test_midnight_boundary_is_reproducible():
    boundary = _midnight(
        1984,
        7,
        22,
    )

    first = (
        _day_pillar_from_datetime(
            boundary
        )
    )

    second = (
        _day_pillar_from_datetime(
            boundary
        )
    )

    assert (
        first
        == second
        == "丁巳"
    )


# ============================================================
# 16. Final golden smoke
# ============================================================


def test_verified_day_boundary_final_smoke():
    """
    最終スモーク。

    1984-07-22 00:00を境に、

    23:59:59 = 丙辰
    00:00:00 = 丁巳
    00:00:01 = 丁巳

    となることを固定する。
    """

    boundary = _midnight(
        1984,
        7,
        22,
    )

    actual = {
        "before": (
            _day_pillar_from_datetime(
                boundary
                - timedelta(
                    seconds=1
                )
            )
        ),
        "exact": (
            _day_pillar_from_datetime(
                boundary
            )
        ),
        "after": (
            _day_pillar_from_datetime(
                boundary
                + timedelta(
                    seconds=1
                )
            )
        ),
        "day_master_before": (
            _day_master_from_datetime(
                boundary
                - timedelta(
                    seconds=1
                )
            )
        ),
        "day_master_exact": (
            _day_master_from_datetime(
                boundary
            )
        ),
    }

    assert actual == {
        "before": "丙辰",
        "exact": "丁巳",
        "after": "丁巳",
        "day_master_before": "丙",
        "day_master_exact": "丁",
    }


# ============================================================
# 17. Metadata
# ============================================================


def test_verified_day_boundary_metadata():
    assert (
        VERIFIED_DAY_BOUNDARY_METHOD
        == "verified_midnight_day_boundary_v1"
    )

    assert (
        VERIFIED_DAY_BOUNDARY_STATUS
        == "golden_regression"
    )
