"""
tests/test_verified_hour_boundaries.py

四柱推命 時柱・時刻境界
ゴールデン回帰テスト v1

目的
----
engine/hour.py と engine/pillars.py について、

・2時間ごとの時支境界
・23:00〜00:59 = 子刻
・01:00〜02:59 = 丑刻
・03:00〜04:59 = 寅刻
・...
・21:00〜22:59 = 亥刻
・23:00で亥→子へ切り替わること
・00:00では時支は子のままで、日柱だけが切り替わること
・01:00で子→丑へ切り替わること
・時柱が日干と時支から正しく計算されること
・既知の時柱
  1984-07-22 丁日 04:15 = 壬寅
  1984-07-22 丁日 13:40 = 丁未
  1985-07-17 丁日 21:50 = 辛亥
  1984-07-21 丙日 12:00 = 甲午
  を固定すること

を検証する。

重要
----
現行プロジェクトの仕様:

子刻:
    23:00〜00:59

丑刻:
    01:00〜02:59

寅刻:
    03:00〜04:59

...

亥刻:
    21:00〜22:59

また、日柱の日界は00:00。
したがって、

22:59:59
    日柱 = 当日
    時支 = 亥

23:00:00
    日柱 = 当日
    時支 = 子

23:59:59
    日柱 = 当日
    時支 = 子

00:00:00
    日柱 = 翌日
    時支 = 子

00:59:59
    日柱 = 翌日
    時支 = 子

01:00:00
    日柱 = 翌日
    時支 = 丑

となる。

Version
-------
verified_hour_boundaries_v1
"""

from __future__ import annotations

from datetime import (
    datetime,
    timedelta,
)
from zoneinfo import ZoneInfo

import pytest

from engine.hour import (
    calculate_hour_branch,
    calculate_hour_branch_index,
    calculate_hour_pillar,
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

VERIFIED_HOUR_BOUNDARY_METHOD = (
    "verified_two_hour_boundary_v1"
)

VERIFIED_HOUR_BOUNDARY_STATUS = (
    "golden_regression"
)


# ============================================================
# Hour-branch table
# ============================================================


HOUR_BRANCH_CASES = (
    {
        "branch": "子",
        "start_hour": 23,
        "end_hour": 0,
    },
    {
        "branch": "丑",
        "start_hour": 1,
        "end_hour": 2,
    },
    {
        "branch": "寅",
        "start_hour": 3,
        "end_hour": 4,
    },
    {
        "branch": "卯",
        "start_hour": 5,
        "end_hour": 6,
    },
    {
        "branch": "辰",
        "start_hour": 7,
        "end_hour": 8,
    },
    {
        "branch": "巳",
        "start_hour": 9,
        "end_hour": 10,
    },
    {
        "branch": "午",
        "start_hour": 11,
        "end_hour": 12,
    },
    {
        "branch": "未",
        "start_hour": 13,
        "end_hour": 14,
    },
    {
        "branch": "申",
        "start_hour": 15,
        "end_hour": 16,
    },
    {
        "branch": "酉",
        "start_hour": 17,
        "end_hour": 18,
    },
    {
        "branch": "戌",
        "start_hour": 19,
        "end_hour": 20,
    },
    {
        "branch": "亥",
        "start_hour": 21,
        "end_hour": 22,
    },
)


HOUR_BRANCH_IDS = tuple(
    item[
        "branch"
    ]
    for item in HOUR_BRANCH_CASES
)


# ============================================================
# Boundary table
# ============================================================


HOUR_BOUNDARIES = (
    {
        "boundary_hour": 1,
        "before_branch": "子",
        "after_branch": "丑",
    },
    {
        "boundary_hour": 3,
        "before_branch": "丑",
        "after_branch": "寅",
    },
    {
        "boundary_hour": 5,
        "before_branch": "寅",
        "after_branch": "卯",
    },
    {
        "boundary_hour": 7,
        "before_branch": "卯",
        "after_branch": "辰",
    },
    {
        "boundary_hour": 9,
        "before_branch": "辰",
        "after_branch": "巳",
    },
    {
        "boundary_hour": 11,
        "before_branch": "巳",
        "after_branch": "午",
    },
    {
        "boundary_hour": 13,
        "before_branch": "午",
        "after_branch": "未",
    },
    {
        "boundary_hour": 15,
        "before_branch": "未",
        "after_branch": "申",
    },
    {
        "boundary_hour": 17,
        "before_branch": "申",
        "after_branch": "酉",
    },
    {
        "boundary_hour": 19,
        "before_branch": "酉",
        "after_branch": "戌",
    },
    {
        "boundary_hour": 21,
        "before_branch": "戌",
        "after_branch": "亥",
    },
    {
        "boundary_hour": 23,
        "before_branch": "亥",
        "after_branch": "子",
    },
)


HOUR_BOUNDARY_IDS = tuple(
    f"{item['boundary_hour']:02d}:00"
    for item in HOUR_BOUNDARIES
)


# ============================================================
# Helpers
# ============================================================


def _four(
    value: datetime,
) -> dict:
    result = calculate_four_pillars(
        value
    )

    assert isinstance(
        result,
        dict,
    )

    return result


def _hour_data(
    value: datetime,
) -> dict:
    result = _four(
        value
    )

    hour = result[
        "hour"
    ]

    assert isinstance(
        hour,
        dict,
    )

    return hour


def _day_data(
    value: datetime,
) -> dict:
    result = _four(
        value
    )

    day = result[
        "day"
    ]

    assert isinstance(
        day,
        dict,
    )

    return day


def _hour_pillar(
    value: datetime,
) -> str:
    return _hour_data(
        value
    )[
        "pillar"
    ]


def _hour_branch_from_four(
    value: datetime,
) -> str:
    return _hour_data(
        value
    )[
        "branch"
    ]


def _day_pillar(
    value: datetime,
) -> str:
    return _day_data(
        value
    )[
        "pillar"
    ]


def _day_stem(
    value: datetime,
) -> str:
    return _day_data(
        value
    )[
        "stem"
    ]


# ============================================================
# 1. Basic branch mapping
# ============================================================


@pytest.mark.parametrize(
    "case",
    HOUR_BRANCH_CASES,
    ids=HOUR_BRANCH_IDS,
)
def test_hour_branch_start_hour(
    case,
):
    result = calculate_hour_branch(
        case[
            "start_hour"
        ]
    )

    assert (
        result
        == case[
            "branch"
        ]
    )


@pytest.mark.parametrize(
    "case",
    HOUR_BRANCH_CASES,
    ids=HOUR_BRANCH_IDS,
)
def test_hour_branch_end_hour(
    case,
):
    result = calculate_hour_branch(
        case[
            "end_hour"
        ]
    )

    assert (
        result
        == case[
            "branch"
        ]
    )


# ============================================================
# 2. Known branch examples
# ============================================================


def test_23_is_rat():
    assert (
        calculate_hour_branch(
            23
        )
        == "子"
    )


def test_0_is_rat():
    assert (
        calculate_hour_branch(
            0
        )
        == "子"
    )


def test_1_is_ox():
    assert (
        calculate_hour_branch(
            1
        )
        == "丑"
    )


def test_2_is_ox():
    assert (
        calculate_hour_branch(
            2
        )
        == "丑"
    )


def test_21_is_pig():
    assert (
        calculate_hour_branch(
            21
        )
        == "亥"
    )


def test_22_is_pig():
    assert (
        calculate_hour_branch(
            22
        )
        == "亥"
    )


# ============================================================
# 3. Branch indexes
# ============================================================


@pytest.mark.parametrize(
    (
        "hour",
        "expected_index",
    ),
    (
        (23, 0),
        (0, 0),
        (1, 1),
        (2, 1),
        (3, 2),
        (4, 2),
        (5, 3),
        (6, 3),
        (7, 4),
        (8, 4),
        (9, 5),
        (10, 5),
        (11, 6),
        (12, 6),
        (13, 7),
        (14, 7),
        (15, 8),
        (16, 8),
        (17, 9),
        (18, 9),
        (19, 10),
        (20, 10),
        (21, 11),
        (22, 11),
    ),
)
def test_hour_branch_index(
    hour,
    expected_index,
):
    assert (
        calculate_hour_branch_index(
            hour
        )
        == expected_index
    )


# ============================================================
# 4. 2-hour exact boundaries
# ============================================================


@pytest.mark.parametrize(
    "case",
    HOUR_BOUNDARIES,
    ids=HOUR_BOUNDARY_IDS,
)
def test_hour_boundary_one_second_before(
    case,
):
    """
    各境界の1秒前は旧時支。
    """

    boundary = datetime(
        1984,
        7,
        22,
        case[
            "boundary_hour"
        ],
        0,
        0,
        tzinfo=JST,
    )

    before = (
        boundary
        - timedelta(
            seconds=1
        )
    )

    assert (
        calculate_hour_branch(
            before.hour
        )
        == case[
            "before_branch"
        ]
    )


@pytest.mark.parametrize(
    "case",
    HOUR_BOUNDARIES,
    ids=HOUR_BOUNDARY_IDS,
)
def test_hour_boundary_exact(
    case,
):
    """
    境界時刻ちょうどから新時支。
    """

    boundary = datetime(
        1984,
        7,
        22,
        case[
            "boundary_hour"
        ],
        0,
        0,
        tzinfo=JST,
    )

    assert (
        calculate_hour_branch(
            boundary.hour
        )
        == case[
            "after_branch"
        ]
    )


@pytest.mark.parametrize(
    "case",
    HOUR_BOUNDARIES,
    ids=HOUR_BOUNDARY_IDS,
)
def test_hour_boundary_one_second_after(
    case,
):
    boundary = datetime(
        1984,
        7,
        22,
        case[
            "boundary_hour"
        ],
        0,
        0,
        tzinfo=JST,
    )

    after = (
        boundary
        + timedelta(
            seconds=1
        )
    )

    assert (
        calculate_hour_branch(
            after.hour
        )
        == case[
            "after_branch"
        ]
    )


# ============================================================
# 5. 23:00 transition
# ============================================================


def test_225959_is_pig_hour():
    target = datetime(
        1984,
        7,
        21,
        22,
        59,
        59,
        tzinfo=JST,
    )

    assert (
        _hour_branch_from_four(
            target
        )
        == "亥"
    )


def test_230000_is_rat_hour():
    target = datetime(
        1984,
        7,
        21,
        23,
        0,
        0,
        tzinfo=JST,
    )

    assert (
        _hour_branch_from_four(
            target
        )
        == "子"
    )


def test_230001_is_rat_hour():
    target = datetime(
        1984,
        7,
        21,
        23,
        0,
        1,
        tzinfo=JST,
    )

    assert (
        _hour_branch_from_four(
            target
        )
        == "子"
    )


def test_235959_is_rat_hour():
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
        _hour_branch_from_four(
            target
        )
        == "子"
    )


# ============================================================
# 6. 00:00 transition: day changes, branch does not
# ============================================================


def test_235959_day_and_hour():
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
        _day_pillar(
            target
        )
        == "丙辰"
    )

    assert (
        _hour_branch_from_four(
            target
        )
        == "子"
    )


def test_000000_day_changes_but_hour_branch_stays_rat():
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
        _day_pillar(
            target
        )
        == "丁巳"
    )

    assert (
        _hour_branch_from_four(
            target
        )
        == "子"
    )


def test_000001_day_new_and_rat_hour():
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
        _day_pillar(
            target
        )
        == "丁巳"
    )

    assert (
        _hour_branch_from_four(
            target
        )
        == "子"
    )


def test_005959_is_still_rat_hour():
    target = datetime(
        1984,
        7,
        22,
        0,
        59,
        59,
        tzinfo=JST,
    )

    assert (
        _hour_branch_from_four(
            target
        )
        == "子"
    )


# ============================================================
# 7. 01:00 transition
# ============================================================


def test_005959_before_ox_boundary():
    target = datetime(
        1984,
        7,
        22,
        0,
        59,
        59,
        tzinfo=JST,
    )

    assert (
        _hour_branch_from_four(
            target
        )
        == "子"
    )


def test_010000_is_ox_hour():
    target = datetime(
        1984,
        7,
        22,
        1,
        0,
        0,
        tzinfo=JST,
    )

    assert (
        _hour_branch_from_four(
            target
        )
        == "丑"
    )


def test_010001_is_ox_hour():
    target = datetime(
        1984,
        7,
        22,
        1,
        0,
        1,
        tzinfo=JST,
    )

    assert (
        _hour_branch_from_four(
            target
        )
        == "丑"
    )


# ============================================================
# 8. Full 23:00 -> 01:00 integrated sequence
# ============================================================


def test_2300_midnight_0100_integrated_sequence():
    """
    一番事故りやすい複合境界を一括固定する。
    """

    samples = (
        (
            datetime(
                1984,
                7,
                21,
                22,
                59,
                59,
                tzinfo=JST,
            ),
            "丙辰",
            "亥",
        ),
        (
            datetime(
                1984,
                7,
                21,
                23,
                0,
                0,
                tzinfo=JST,
            ),
            "丙辰",
            "子",
        ),
        (
            datetime(
                1984,
                7,
                21,
                23,
                59,
                59,
                tzinfo=JST,
            ),
            "丙辰",
            "子",
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
            "丁巳",
            "子",
        ),
        (
            datetime(
                1984,
                7,
                22,
                0,
                59,
                59,
                tzinfo=JST,
            ),
            "丁巳",
            "子",
        ),
        (
            datetime(
                1984,
                7,
                22,
                1,
                0,
                0,
                tzinfo=JST,
            ),
            "丁巳",
            "丑",
        ),
    )

    actual = []

    for (
        target,
        expected_day,
        expected_branch,
    ) in samples:
        actual.append(
            (
                _day_pillar(
                    target
                ),
                _hour_branch_from_four(
                    target
                ),
            )
        )

    assert actual == [
        ("丙辰", "亥"),
        ("丙辰", "子"),
        ("丙辰", "子"),
        ("丁巳", "子"),
        ("丁巳", "子"),
        ("丁巳", "丑"),
    ]


# ============================================================
# 9. Known hour pillars
# ============================================================


def test_verified_1984_07_22_0415_hour_pillar():
    """
    丁日・04:15 = 壬寅。
    """

    assert (
        calculate_hour_pillar(
            "丁",
            4,
        )
        == "壬寅"
    )


def test_verified_1984_07_22_1340_hour_pillar():
    """
    丁日・13:40 = 丁未。
    """

    assert (
        calculate_hour_pillar(
            "丁",
            13,
        )
        == "丁未"
    )


def test_verified_1985_07_17_2150_hour_pillar():
    """
    丁日・21:50 = 辛亥。
    """

    assert (
        calculate_hour_pillar(
            "丁",
            21,
        )
        == "辛亥"
    )


def test_verified_1984_07_21_1200_hour_pillar():
    """
    丙日・12:00 = 甲午。
    """

    assert (
        calculate_hour_pillar(
            "丙",
            12,
        )
        == "甲午"
    )


# ============================================================
# 10. calculate_hour_pillar vs calculate_four_pillars
# ============================================================


@pytest.mark.parametrize(
    (
        "target",
        "expected",
    ),
    (
        (
            datetime(
                1984,
                7,
                22,
                4,
                15,
                tzinfo=JST,
            ),
            "壬寅",
        ),
        (
            datetime(
                1984,
                7,
                22,
                13,
                40,
                tzinfo=JST,
            ),
            "丁未",
        ),
        (
            datetime(
                1985,
                7,
                17,
                21,
                50,
                tzinfo=JST,
            ),
            "辛亥",
        ),
        (
            datetime(
                1984,
                7,
                21,
                12,
                0,
                tzinfo=JST,
            ),
            "甲午",
        ),
    ),
)
def test_direct_hour_engine_and_four_pillar_engine_agree(
    target,
    expected,
):
    day_stem = _day_stem(
        target
    )

    direct = calculate_hour_pillar(
        day_stem,
        target.hour,
    )

    integrated = _hour_pillar(
        target
    )

    assert (
        direct
        == integrated
        == expected
    )


# ============================================================
# 11. 子刻 hour pillar across midnight
# ============================================================


def test_rat_hour_pillar_uses_same_day_stem_before_midnight():
    """
    1984-07-21 23:00は
    日主丙の子刻。
    """

    target = datetime(
        1984,
        7,
        21,
        23,
        0,
        0,
        tzinfo=JST,
    )

    day_stem = _day_stem(
        target
    )

    assert (
        day_stem
        == "丙"
    )

    assert (
        _hour_branch_from_four(
            target
        )
        == "子"
    )

    assert (
        _hour_pillar(
            target
        )
        == calculate_hour_pillar(
            "丙",
            23,
        )
    )


def test_rat_hour_pillar_recalculates_after_midnight():
    """
    1984-07-22 00:00は
    日主丁の子刻。

    時支は子のままだが、
    日干が丙→丁へ変わるため
    時干は再計算される。
    """

    target = datetime(
        1984,
        7,
        22,
        0,
        0,
        0,
        tzinfo=JST,
    )

    day_stem = _day_stem(
        target
    )

    assert (
        day_stem
        == "丁"
    )

    assert (
        _hour_branch_from_four(
            target
        )
        == "子"
    )

    assert (
        _hour_pillar(
            target
        )
        == calculate_hour_pillar(
            "丁",
            0,
        )
    )


def test_rat_hour_pillar_can_change_at_midnight_even_branch_same():
    before = datetime(
        1984,
        7,
        21,
        23,
        59,
        59,
        tzinfo=JST,
    )

    after = datetime(
        1984,
        7,
        22,
        0,
        0,
        0,
        tzinfo=JST,
    )

    assert (
        _hour_branch_from_four(
            before
        )
        == "子"
    )

    assert (
        _hour_branch_from_four(
            after
        )
        == "子"
    )

    assert (
        _day_stem(
            before
        )
        == "丙"
    )

    assert (
        _day_stem(
            after
        )
        == "丁"
    )

    # 日干が変わるため、
    # 時柱全体は変わることを期待する。
    assert (
        _hour_pillar(
            before
        )
        != _hour_pillar(
            after
        )
    )


# ============================================================
# 12. Same 2-hour block invariant
# ============================================================


@pytest.mark.parametrize(
    (
        "first_hour",
        "second_hour",
        "expected_branch",
    ),
    (
        (1, 2, "丑"),
        (3, 4, "寅"),
        (5, 6, "卯"),
        (7, 8, "辰"),
        (9, 10, "巳"),
        (11, 12, "午"),
        (13, 14, "未"),
        (15, 16, "申"),
        (17, 18, "酉"),
        (19, 20, "戌"),
        (21, 22, "亥"),
    ),
)
def test_two_hours_share_same_branch(
    first_hour,
    second_hour,
    expected_branch,
):
    assert (
        calculate_hour_branch(
            first_hour
        )
        == expected_branch
    )

    assert (
        calculate_hour_branch(
            second_hour
        )
        == expected_branch
    )


def test_23_and_0_share_same_rat_branch():
    assert (
        calculate_hour_branch(
            23
        )
        == "子"
    )

    assert (
        calculate_hour_branch(
            0
        )
        == "子"
    )


# ============================================================
# 13. Invalid hour
# ============================================================


@pytest.mark.parametrize(
    "bad_hour",
    (
        -1,
        24,
        25,
        100,
    ),
)
def test_calculate_hour_branch_rejects_invalid_hour(
    bad_hour,
):
    with pytest.raises(
        ValueError
    ):
        calculate_hour_branch(
            bad_hour
        )


@pytest.mark.parametrize(
    "bad_hour",
    (
        -1,
        24,
        25,
        100,
    ),
)
def test_calculate_hour_branch_index_rejects_invalid_hour(
    bad_hour,
):
    with pytest.raises(
        ValueError
    ):
        calculate_hour_branch_index(
            bad_hour
        )


@pytest.mark.parametrize(
    "bad_hour",
    (
        -1,
        24,
        25,
    ),
)
def test_calculate_hour_pillar_rejects_invalid_hour(
    bad_hour,
):
    with pytest.raises(
        ValueError
    ):
        calculate_hour_pillar(
            "丁",
            bad_hour,
        )


def test_calculate_hour_pillar_rejects_invalid_day_stem():
    with pytest.raises(
        ValueError
    ):
        calculate_hour_pillar(
            "無",
            12,
        )


# ============================================================
# 14. Reproducibility
# ============================================================


@pytest.mark.parametrize(
    (
        "day_stem",
        "hour",
        "expected",
    ),
    (
        ("丁", 4, "壬寅"),
        ("丁", 13, "丁未"),
        ("丁", 21, "辛亥"),
        ("丙", 12, "甲午"),
    ),
)
def test_hour_pillar_is_reproducible(
    day_stem,
    hour,
    expected,
):
    first = calculate_hour_pillar(
        day_stem,
        hour,
    )

    second = calculate_hour_pillar(
        day_stem,
        hour,
    )

    assert (
        first
        == second
        == expected
    )


def test_integrated_hour_pillar_is_reproducible():
    target = datetime(
        1985,
        7,
        17,
        21,
        50,
        tzinfo=JST,
    )

    first = _hour_pillar(
        target
    )

    second = _hour_pillar(
        target
    )

    assert (
        first
        == second
        == "辛亥"
    )


# ============================================================
# 15. Final smoke
# ============================================================


def test_verified_hour_boundaries_final_smoke():
    """
    最終スモーク。

    22:59:59
        丙辰 / 亥

    23:00:00
        丙辰 / 子

    23:59:59
        丙辰 / 子

    00:00:00
        丁巳 / 子

    00:59:59
        丁巳 / 子

    01:00:00
        丁巳 / 丑
    """

    samples = (
        datetime(
            1984,
            7,
            21,
            22,
            59,
            59,
            tzinfo=JST,
        ),
        datetime(
            1984,
            7,
            21,
            23,
            0,
            0,
            tzinfo=JST,
        ),
        datetime(
            1984,
            7,
            21,
            23,
            59,
            59,
            tzinfo=JST,
        ),
        datetime(
            1984,
            7,
            22,
            0,
            0,
            0,
            tzinfo=JST,
        ),
        datetime(
            1984,
            7,
            22,
            0,
            59,
            59,
            tzinfo=JST,
        ),
        datetime(
            1984,
            7,
            22,
            1,
            0,
            0,
            tzinfo=JST,
        ),
    )

    actual = [
        (
            _day_pillar(
                target
            ),
            _hour_branch_from_four(
                target
            ),
        )
        for target in samples
    ]

    assert actual == [
        ("丙辰", "亥"),
        ("丙辰", "子"),
        ("丙辰", "子"),
        ("丁巳", "子"),
        ("丁巳", "子"),
        ("丁巳", "丑"),
    ]


# ============================================================
# 16. Metadata
# ============================================================


def test_verified_hour_boundary_metadata():
    assert (
        VERIFIED_HOUR_BOUNDARY_METHOD
        == "verified_two_hour_boundary_v1"
    )

    assert (
        VERIFIED_HOUR_BOUNDARY_STATUS
        == "golden_regression"
    )
