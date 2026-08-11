"""
tests/test_time_correction_boundaries.py

四柱推命 出生時刻補正
境界回帰テスト v1

対象
----
engine/time_correction.py
engine/year.py
engine/month.py
engine/day.py
engine/hour.py

目的
----
出生時刻へ経度補正を適用した結果、
四柱推命上の重要境界を跨ぐケースを固定する。

本テストではまだ
engine/pillars.py 自体へ補正機能を統合しない。

代わりに、

1. apply_time_correction()
2. corrected_datetime
3. year / month / day / hour 各エンジン

の順で計算し、

「補正後日時を四柱すべての入力に使う」

という将来統合仕様を先にテストとして固定する。

検証する境界
------------
・22:59 → 23:00
    亥刻 → 子刻

・23:59 → 00:00
    日柱切替

・00:59 → 01:00
    子刻 → 丑刻

・立春
    年柱 + 月柱切替

・月の節入り
    月柱切替

・日付跨ぎ
・月跨ぎ
・年跨ぎ

重要
----
現行仕様では、

日柱の日界:
    00:00

子刻:
    23:00〜00:59

である。

Version
-------
test_time_correction_boundaries_v1
"""

from __future__ import annotations

from datetime import (
    datetime,
    timedelta,
)
from zoneinfo import ZoneInfo

import pytest

from engine.day import (
    calculate_day_pillar,
)
from engine.hour import (
    calculate_hour_pillar,
)
from engine.month import (
    calculate_month_pillar,
)
from engine.solar_terms import (
    get_solar_term_datetime,
)
from engine.time_correction import (
    MODE_LONGITUDE,
    MODE_STANDARD,
    apply_time_correction,
)
from engine.year import (
    calculate_year_pillar,
    get_lichun_datetime,
)


# ============================================================
# Constants
# ============================================================


JST = ZoneInfo(
    "Asia/Tokyo"
)


TEST_METHOD = (
    "time_correction_boundary_v1"
)

TEST_STATUS = (
    "golden_regression"
)


# ============================================================
# Helpers
# ============================================================


def _calculate_four_from_datetime(
    target: datetime,
) -> dict[str, str]:
    """
    補正後datetimeから、
    各独立エンジンを使って四柱を計算する。

    pillars.pyへ補正機能を統合する前の
    期待仕様を表現する。
    """

    year = calculate_year_pillar(
        target
    )

    year_stem = year[
        0
    ]

    month = calculate_month_pillar(
        target,
        year_stem,
    )

    day = calculate_day_pillar(
        target.date()
    )

    day_stem = day[
        0
    ]

    hour = calculate_hour_pillar(
        day_stem,
        target.hour,
    )

    return {
        "year": year,
        "month": month,
        "day": day,
        "hour": hour,
        "day_master": day_stem,
    }


def _correct_and_calculate(
    target: datetime,
    *,
    longitude: float,
) -> dict[str, object]:
    correction = apply_time_correction(
        target,
        longitude=longitude,
        mode=MODE_LONGITUDE,
    )

    corrected = (
        correction.corrected_datetime
    )

    return {
        "correction": correction,
        "chart": (
            _calculate_four_from_datetime(
                corrected
            )
        ),
    }


# ============================================================
# 1. Standard mode baseline
# ============================================================


def test_standard_mode_does_not_cross_boundary():
    target = datetime(
        1984,
        7,
        21,
        22,
        58,
        tzinfo=JST,
    )

    result = apply_time_correction(
        target,
        mode=MODE_STANDARD,
    )

    assert (
        result.corrected_datetime
        == target
    )


def test_standard_mode_chart_uses_original_time():
    target = datetime(
        1984,
        7,
        21,
        22,
        58,
        tzinfo=JST,
    )

    chart = (
        _calculate_four_from_datetime(
            target
        )
    )

    assert chart[
        "day"
    ] == "丙辰"

    assert chart[
        "hour"
    ] == "己亥"


# ============================================================
# 2. 22:58 +4m => 23:02
# ============================================================


def test_positive_correction_crosses_2300():
    """
    東経136度:
        +4分

    22:58
        ↓
    23:02

    時支:
        亥 → 子

    日柱:
        同日なので丙辰のまま
    """

    target = datetime(
        1984,
        7,
        21,
        22,
        58,
        tzinfo=JST,
    )

    result = _correct_and_calculate(
        target,
        longitude=136.0,
    )

    correction = result[
        "correction"
    ]

    chart = result[
        "chart"
    ]

    assert (
        correction.corrected_datetime
        == datetime(
            1984,
            7,
            21,
            23,
            2,
            tzinfo=JST,
        )
    )

    assert (
        chart[
            "day"
        ]
        == "丙辰"
    )

    assert (
        chart[
            "hour"
        ]
        == "戊子"
    )


def test_2300_crossing_changes_hour_not_day():
    target = datetime(
        1984,
        7,
        21,
        22,
        58,
        tzinfo=JST,
    )

    before = (
        _calculate_four_from_datetime(
            target
        )
    )

    after = (
        _correct_and_calculate(
            target,
            longitude=136.0,
        )[
            "chart"
        ]
    )

    assert before[
        "year"
    ] == after[
        "year"
    ]

    assert before[
        "month"
    ] == after[
        "month"
    ]

    assert before[
        "day"
    ] == after[
        "day"
    ]

    assert before[
        "day_master"
    ] == after[
        "day_master"
    ]

    assert before[
        "hour"
    ] == "己亥"

    assert after[
        "hour"
    ] == "戊子"


# ============================================================
# 3. 00:02 -4m => previous day 23:58
# ============================================================


def test_negative_correction_crosses_previous_day():
    """
    東経134度:
        -4分

    1984-07-22 00:02
        ↓
    1984-07-21 23:58

    日柱:
        丁巳 → 丙辰

    時支:
        子のまま

    時干:
        日干変更に伴い再計算
    """

    target = datetime(
        1984,
        7,
        22,
        0,
        2,
        tzinfo=JST,
    )

    result = _correct_and_calculate(
        target,
        longitude=134.0,
    )

    correction = result[
        "correction"
    ]

    chart = result[
        "chart"
    ]

    assert (
        correction.corrected_datetime
        == datetime(
            1984,
            7,
            21,
            23,
            58,
            tzinfo=JST,
        )
    )

    assert (
        correction.date_changed
        is True
    )

    assert (
        chart[
            "day"
        ]
        == "丙辰"
    )

    assert (
        chart[
            "day_master"
        ]
        == "丙"
    )

    assert (
        chart[
            "hour"
        ]
        == "戊子"
    )


def test_midnight_crossing_changes_day_master():
    target = datetime(
        1984,
        7,
        22,
        0,
        2,
        tzinfo=JST,
    )

    standard_chart = (
        _calculate_four_from_datetime(
            target
        )
    )

    corrected_chart = (
        _correct_and_calculate(
            target,
            longitude=134.0,
        )[
            "chart"
        ]
    )

    assert standard_chart[
        "day"
    ] == "丁巳"

    assert corrected_chart[
        "day"
    ] == "丙辰"

    assert standard_chart[
        "day_master"
    ] == "丁"

    assert corrected_chart[
        "day_master"
    ] == "丙"

    assert standard_chart[
        "hour"
    ] == "庚子"

    assert corrected_chart[
        "hour"
    ] == "戊子"


# ============================================================
# 4. 00:58 +4m => 01:02
# ============================================================


def test_positive_correction_crosses_0100():
    """
    00:58
        ↓ +4分
    01:02

    子刻 → 丑刻
    """

    target = datetime(
        1984,
        7,
        22,
        0,
        58,
        tzinfo=JST,
    )

    result = _correct_and_calculate(
        target,
        longitude=136.0,
    )

    correction = result[
        "correction"
    ]

    chart = result[
        "chart"
    ]

    assert (
        correction.corrected_datetime
        == datetime(
            1984,
            7,
            22,
            1,
            2,
            tzinfo=JST,
        )
    )

    assert (
        chart[
            "day"
        ]
        == "丁巳"
    )

    assert (
        chart[
            "hour"
        ]
        == "辛丑"
    )


def test_0100_crossing_changes_hour_only():
    target = datetime(
        1984,
        7,
        22,
        0,
        58,
        tzinfo=JST,
    )

    before = (
        _calculate_four_from_datetime(
            target
        )
    )

    after = (
        _correct_and_calculate(
            target,
            longitude=136.0,
        )[
            "chart"
        ]
    )

    for key in (
        "year",
        "month",
        "day",
        "day_master",
    ):
        assert (
            before[
                key
            ]
            == after[
                key
            ]
        )

    assert before[
        "hour"
    ] == "庚子"

    assert after[
        "hour"
    ] == "辛丑"


# ============================================================
# 5. 23:58 +4m => next day 00:02
# ============================================================


def test_positive_correction_crosses_next_day():
    target = datetime(
        1984,
        7,
        21,
        23,
        58,
        tzinfo=JST,
    )

    result = _correct_and_calculate(
        target,
        longitude=136.0,
    )

    correction = result[
        "correction"
    ]

    chart = result[
        "chart"
    ]

    assert (
        correction.corrected_datetime
        == datetime(
            1984,
            7,
            22,
            0,
            2,
            tzinfo=JST,
        )
    )

    assert (
        correction.date_changed
        is True
    )

    assert (
        chart[
            "day"
        ]
        == "丁巳"
    )

    assert (
        chart[
            "hour"
        ]
        == "庚子"
    )


# ============================================================
# 6. Lichun crossing
# ============================================================


def test_positive_correction_crosses_2026_lichun():
    """
    立春2分前を入力し、
    +4分補正すると
    立春2分後になる。

    年柱:
        乙巳 → 丙午

    月柱:
        己丑 → 庚寅
    """

    lichun = get_lichun_datetime(
        2026
    )

    target = (
        lichun
        - timedelta(
            minutes=2
        )
    )

    before_chart = (
        _calculate_four_from_datetime(
            target
        )
    )

    result = _correct_and_calculate(
        target,
        longitude=136.0,
    )

    correction = result[
        "correction"
    ]

    after_chart = result[
        "chart"
    ]

    assert (
        correction.corrected_datetime
        == (
            lichun
            + timedelta(
                minutes=2
            )
        )
    )

    assert before_chart[
        "year"
    ] == "乙巳"

    assert before_chart[
        "month"
    ] == "己丑"

    assert after_chart[
        "year"
    ] == "丙午"

    assert after_chart[
        "month"
    ] == "庚寅"


def test_negative_correction_moves_back_before_2026_lichun():
    """
    立春2分後を入力し、
    -4分補正すると
    立春2分前になる。
    """

    lichun = get_lichun_datetime(
        2026
    )

    target = (
        lichun
        + timedelta(
            minutes=2
        )
    )

    before_chart = (
        _calculate_four_from_datetime(
            target
        )
    )

    result = _correct_and_calculate(
        target,
        longitude=134.0,
    )

    correction = result[
        "correction"
    ]

    after_chart = result[
        "chart"
    ]

    assert (
        correction.corrected_datetime
        == (
            lichun
            - timedelta(
                minutes=2
            )
        )
    )

    assert before_chart[
        "year"
    ] == "丙午"

    assert before_chart[
        "month"
    ] == "庚寅"

    assert after_chart[
        "year"
    ] == "乙巳"

    assert after_chart[
        "month"
    ] == "己丑"


def test_lichun_crossing_changes_year_and_month_together():
    lichun = get_lichun_datetime(
        2026
    )

    target = (
        lichun
        - timedelta(
            minutes=2
        )
    )

    before = (
        _calculate_four_from_datetime(
            target
        )
    )

    after = (
        _correct_and_calculate(
            target,
            longitude=136.0,
        )[
            "chart"
        ]
    )

    assert (
        before[
            "year"
        ]
        != after[
            "year"
        ]
    )

    assert (
        before[
            "month"
        ]
        != after[
            "month"
        ]
    )


# ============================================================
# 7. Non-Lichun month boundary
# ============================================================


@pytest.mark.parametrize(
    (
        "term_name",
        "before_month",
        "after_month",
    ),
    (
        (
            "啓蟄",
            "庚寅",
            "辛卯",
        ),
        (
            "清明",
            "辛卯",
            "壬辰",
        ),
        (
            "立夏",
            "壬辰",
            "癸巳",
        ),
        (
            "芒種",
            "癸巳",
            "甲午",
        ),
        (
            "小暑",
            "甲午",
            "乙未",
        ),
        (
            "立秋",
            "乙未",
            "丙申",
        ),
        (
            "白露",
            "丙申",
            "丁酉",
        ),
        (
            "寒露",
            "丁酉",
            "戊戌",
        ),
        (
            "立冬",
            "戊戌",
            "己亥",
        ),
        (
            "大雪",
            "己亥",
            "庚子",
        ),
    ),
)
def test_positive_correction_crosses_month_boundary(
    term_name,
    before_month,
    after_month,
):
    """
    節入り2分前
        ↓ +4分
    節入り2分後

    月柱だけが切り替わる。
    """

    boundary = (
        get_solar_term_datetime(
            2026,
            term_name,
        )
    )

    target = (
        boundary
        - timedelta(
            minutes=2
        )
    )

    before = (
        _calculate_four_from_datetime(
            target
        )
    )

    after = (
        _correct_and_calculate(
            target,
            longitude=136.0,
        )[
            "chart"
        ]
    )

    assert before[
        "year"
    ] == "丙午"

    assert after[
        "year"
    ] == "丙午"

    assert before[
        "month"
    ] == before_month

    assert after[
        "month"
    ] == after_month


@pytest.mark.parametrize(
    (
        "term_name",
        "before_month",
        "after_month",
    ),
    (
        (
            "啓蟄",
            "庚寅",
            "辛卯",
        ),
        (
            "小暑",
            "甲午",
            "乙未",
        ),
        (
            "立冬",
            "戊戌",
            "己亥",
        ),
    ),
)
def test_negative_correction_moves_back_across_month_boundary(
    term_name,
    before_month,
    after_month,
):
    boundary = (
        get_solar_term_datetime(
            2026,
            term_name,
        )
    )

    target = (
        boundary
        + timedelta(
            minutes=2
        )
    )

    before = (
        _calculate_four_from_datetime(
            target
        )
    )

    after = (
        _correct_and_calculate(
            target,
            longitude=134.0,
        )[
            "chart"
        ]
    )

    assert before[
        "month"
    ] == after_month

    assert after[
        "month"
    ] == before_month


# ============================================================
# 8. Xiaohan boundary
# ============================================================


def test_positive_correction_crosses_2026_xiaohan():
    """
    小寒は立春前なので
    年柱は乙巳のまま。

    月柱:
        戊子 → 己丑
    """

    boundary = (
        get_solar_term_datetime(
            2026,
            "小寒",
        )
    )

    target = (
        boundary
        - timedelta(
            minutes=2
        )
    )

    before = (
        _calculate_four_from_datetime(
            target
        )
    )

    after = (
        _correct_and_calculate(
            target,
            longitude=136.0,
        )[
            "chart"
        ]
    )

    assert before[
        "year"
    ] == "乙巳"

    assert after[
        "year"
    ] == "乙巳"

    assert before[
        "month"
    ] == "戊子"

    assert after[
        "month"
    ] == "己丑"


# ============================================================
# 9. Date / month / year flags
# ============================================================


def test_date_changed_flag_matches_corrected_datetime():
    target = datetime(
        2026,
        8,
        11,
        23,
        58,
        tzinfo=JST,
    )

    result = apply_time_correction(
        target,
        longitude=136.0,
        mode=MODE_LONGITUDE,
    )

    assert (
        result.date_changed
        is True
    )

    assert (
        result.day_changed
        is True
    )

    assert (
        result.month_changed
        is False
    )

    assert (
        result.year_changed
        is False
    )


def test_month_changed_flag():
    target = datetime(
        2026,
        8,
        31,
        23,
        58,
        tzinfo=JST,
    )

    result = apply_time_correction(
        target,
        longitude=136.0,
        mode=MODE_LONGITUDE,
    )

    assert (
        result.corrected_datetime
        == datetime(
            2026,
            9,
            1,
            0,
            2,
            tzinfo=JST,
        )
    )

    assert (
        result.month_changed
        is True
    )

    assert (
        result.year_changed
        is False
    )


def test_year_changed_flag():
    target = datetime(
        2026,
        12,
        31,
        23,
        58,
        tzinfo=JST,
    )

    result = apply_time_correction(
        target,
        longitude=136.0,
        mode=MODE_LONGITUDE,
    )

    assert (
        result.corrected_datetime
        == datetime(
            2027,
            1,
            1,
            0,
            2,
            tzinfo=JST,
        )
    )

    assert (
        result.year_changed
        is True
    )

    assert (
        result.month_changed
        is True
    )

    assert (
        result.day_changed
        is True
    )


# ============================================================
# 10. Same side of boundary does not change chart
# ============================================================


def test_small_positive_correction_without_boundary_keeps_day_hour():
    """
    12:00 → 12:04なら、
    午刻の中に留まる。
    """

    target = datetime(
        1984,
        7,
        22,
        12,
        0,
        tzinfo=JST,
    )

    before = (
        _calculate_four_from_datetime(
            target
        )
    )

    after = (
        _correct_and_calculate(
            target,
            longitude=136.0,
        )[
            "chart"
        ]
    )

    assert before == after


def test_small_negative_correction_without_boundary_keeps_chart():
    """
    12:00 → 11:56も
    午刻内なので四柱は同じ。
    """

    target = datetime(
        1984,
        7,
        22,
        12,
        0,
        tzinfo=JST,
    )

    before = (
        _calculate_four_from_datetime(
            target
        )
    )

    after = (
        _correct_and_calculate(
            target,
            longitude=134.0,
        )[
            "chart"
        ]
    )

    assert before == after


# ============================================================
# 11. Real-prefecture longitude examples
# ============================================================


def test_tokyo_can_push_time_forward():
    target = datetime(
        1984,
        7,
        21,
        22,
        50,
        tzinfo=JST,
    )

    result = apply_time_correction(
        target,
        birth_place="東京都",
        mode=MODE_LONGITUDE,
    )

    assert (
        result.corrected_datetime
        > datetime(
            1984,
            7,
            21,
            23,
            0,
            tzinfo=JST,
        )
    )


def test_fukuoka_can_push_time_backward():
    target = datetime(
        1984,
        7,
        22,
        0,
        10,
        tzinfo=JST,
    )

    result = apply_time_correction(
        target,
        birth_place="福岡県",
        mode=MODE_LONGITUDE,
    )

    assert (
        result.corrected_datetime.date()
        == datetime(
            1984,
            7,
            21,
            tzinfo=JST,
        ).date()
    )


def test_aichi_1984_07_10_2245_does_not_cross_2300():
    """
    愛知県代表経度では約+7分38秒。

    22:45
        ↓
    約22:52:38

    23:00は跨がない。
    """

    target = datetime(
        1984,
        7,
        10,
        22,
        45,
        tzinfo=JST,
    )

    result = apply_time_correction(
        target,
        birth_place="愛知県",
        mode=MODE_LONGITUDE,
    )

    assert (
        result.corrected_datetime.hour
        == 22
    )


# ============================================================
# 12. Reproducibility
# ============================================================


@pytest.mark.parametrize(
    (
        "target",
        "longitude",
    ),
    (
        (
            datetime(
                1984,
                7,
                21,
                22,
                58,
                tzinfo=JST,
            ),
            136.0,
        ),
        (
            datetime(
                1984,
                7,
                22,
                0,
                2,
                tzinfo=JST,
            ),
            134.0,
        ),
        (
            datetime(
                1984,
                7,
                22,
                0,
                58,
                tzinfo=JST,
            ),
            136.0,
        ),
    ),
)
def test_boundary_correction_is_reproducible(
    target,
    longitude,
):
    first = (
        _correct_and_calculate(
            target,
            longitude=longitude,
        )
    )

    second = (
        _correct_and_calculate(
            target,
            longitude=longitude,
        )
    )

    assert (
        first[
            "correction"
        ]
        == second[
            "correction"
        ]
    )

    assert (
        first[
            "chart"
        ]
        == second[
            "chart"
        ]
    )


# ============================================================
# 13. Final night-boundary smoke
# ============================================================


def test_time_correction_night_boundary_final_smoke():
    """
    経度補正によって、
    23時・0時・1時境界を跨ぐ3例を一括確認。
    """

    case_2300 = (
        _correct_and_calculate(
            datetime(
                1984,
                7,
                21,
                22,
                58,
                tzinfo=JST,
            ),
            longitude=136.0,
        )
    )

    case_midnight = (
        _correct_and_calculate(
            datetime(
                1984,
                7,
                22,
                0,
                2,
                tzinfo=JST,
            ),
            longitude=134.0,
        )
    )

    case_0100 = (
        _correct_and_calculate(
            datetime(
                1984,
                7,
                22,
                0,
                58,
                tzinfo=JST,
            ),
            longitude=136.0,
        )
    )

    assert (
        case_2300[
            "chart"
        ][
            "day"
        ]
        == "丙辰"
    )

    assert (
        case_2300[
            "chart"
        ][
            "hour"
        ]
        == "戊子"
    )

    assert (
        case_midnight[
            "chart"
        ][
            "day"
        ]
        == "丙辰"
    )

    assert (
        case_midnight[
            "chart"
        ][
            "hour"
        ]
        == "戊子"
    )

    assert (
        case_0100[
            "chart"
        ][
            "day"
        ]
        == "丁巳"
    )

    assert (
        case_0100[
            "chart"
        ][
            "hour"
        ]
        == "辛丑"
    )


# ============================================================
# 14. Final seasonal-boundary smoke
# ============================================================


def test_time_correction_seasonal_boundary_final_smoke():
    """
    立春と啓蟄を補正で跨ぐケースを一括確認する。
    """

    lichun = get_lichun_datetime(
        2026
    )

    lichun_target = (
        lichun
        - timedelta(
            minutes=2
        )
    )

    lichun_before = (
        _calculate_four_from_datetime(
            lichun_target
        )
    )

    lichun_after = (
        _correct_and_calculate(
            lichun_target,
            longitude=136.0,
        )[
            "chart"
        ]
    )

    assert (
        lichun_before[
            "year"
        ],
        lichun_before[
            "month"
        ],
    ) == (
        "乙巳",
        "己丑",
    )

    assert (
        lichun_after[
            "year"
        ],
        lichun_after[
            "month"
        ],
    ) == (
        "丙午",
        "庚寅",
    )

    keichitsu = (
        get_solar_term_datetime(
            2026,
            "啓蟄",
        )
    )

    keichitsu_target = (
        keichitsu
        - timedelta(
            minutes=2
        )
    )

    keichitsu_before = (
        _calculate_four_from_datetime(
            keichitsu_target
        )
    )

    keichitsu_after = (
        _correct_and_calculate(
            keichitsu_target,
            longitude=136.0,
        )[
            "chart"
        ]
    )

    assert (
        keichitsu_before[
            "year"
        ]
        == keichitsu_after[
            "year"
        ]
        == "丙午"
    )

    assert (
        keichitsu_before[
            "month"
        ]
        == "庚寅"
    )

    assert (
        keichitsu_after[
            "month"
        ]
        == "辛卯"
    )


# ============================================================
# 15. Metadata
# ============================================================


def test_time_correction_boundary_metadata():
    assert (
        TEST_METHOD
        == "time_correction_boundary_v1"
    )

    assert (
        TEST_STATUS
        == "golden_regression"
    )
