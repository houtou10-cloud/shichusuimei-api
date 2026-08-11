"""
tests/test_verified_four_pillar_boundaries.py

四柱推命 四柱総合境界
ゴールデン回帰テスト v1

目的
----
これまで個別に検証した、

・年柱の立春境界
・月柱の節入り境界
・日柱の00:00境界
・時柱の2時間境界
・23:00 / 00:00 / 01:00 の複合境界

を、calculate_four_pillars() を入口として
四柱全体で統合検証する。

このテストでは、
単一モジュールだけが正しい状態ではなく、

出生日時
    ↓
年柱
    ↓
月柱
    ↓
日柱
    ↓
時柱
    ↓
日主

まで一貫して正しいことを固定する。

重要
----
現行プロジェクト仕様:

年柱:
    実際の立春日時で切替

月柱:
    12節の実際の節入り日時で切替

日柱:
    00:00で切替

時柱:
    子 = 23:00〜00:59
    丑 = 01:00〜02:59
    寅 = 03:00〜04:59
    ...
    亥 = 21:00〜22:59

23:00では、
日柱は切り替わらず、
時支だけが亥→子へ変化する。

00:00では、
時支は子のままだが、
日柱が翌日へ変化するため
時干も再計算される。

Version
-------
verified_four_pillar_boundaries_v1
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
from engine.pillars import (
    calculate_four_pillars,
)
from engine.solar_terms import (
    get_solar_term_datetime,
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

VERIFIED_FOUR_PILLAR_BOUNDARY_METHOD = (
    "verified_four_pillar_boundary_v1"
)

VERIFIED_FOUR_PILLAR_BOUNDARY_STATUS = (
    "golden_regression"
)


# ============================================================
# Helpers
# ============================================================


def _calculate(
    target: datetime,
) -> dict:
    result = calculate_four_pillars(
        target
    )

    assert isinstance(
        result,
        dict,
    )

    for key in (
        "year",
        "month",
        "day",
        "hour",
        "day_master",
    ):
        assert (
            key
            in result
        )

    return result


def _pillar(
    result: dict,
    position: str,
) -> str:
    data = result[
        position
    ]

    assert isinstance(
        data,
        dict,
    )

    value = data[
        "pillar"
    ]

    assert isinstance(
        value,
        str,
    )

    return value


def _stem(
    result: dict,
    position: str,
) -> str:
    data = result[
        position
    ]

    assert isinstance(
        data,
        dict,
    )

    return data[
        "stem"
    ]


def _branch(
    result: dict,
    position: str,
) -> str:
    data = result[
        position
    ]

    assert isinstance(
        data,
        dict,
    )

    return data[
        "branch"
    ]


def _day_master(
    result: dict,
) -> str:
    value = result[
        "day_master"
    ]

    assert isinstance(
        value,
        dict,
    )

    stem = value[
        "stem"
    ]

    assert isinstance(
        stem,
        str,
    )

    return stem


def _summary(
    target: datetime,
) -> dict[str, str]:
    result = _calculate(
        target
    )

    return {
        "year": _pillar(
            result,
            "year",
        ),
        "month": _pillar(
            result,
            "month",
        ),
        "day": _pillar(
            result,
            "day",
        ),
        "hour": _pillar(
            result,
            "hour",
        ),
        "day_master": (
            _day_master(
                result
            )
        ),
    }


# ============================================================
# 1. Known complete charts
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
            {
                "year": "甲子",
                "month": "辛未",
                "day": "丁巳",
                "hour": "壬寅",
                "day_master": "丁",
            },
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
            {
                "year": "甲子",
                "month": "辛未",
                "day": "丁巳",
                "hour": "丁未",
                "day_master": "丁",
            },
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
            {
                "year": "乙丑",
                "month": "癸未",
                "day": "丁巳",
                "hour": "辛亥",
                "day_master": "丁",
            },
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
            {
                "year": "甲子",
                "month": "辛未",
                "day": "丙辰",
                "hour": "甲午",
                "day_master": "丙",
            },
        ),
    ),
)
def test_known_complete_four_pillars(
    target,
    expected,
):
    assert (
        _summary(
            target
        )
        == expected
    )


# ============================================================
# 2. Lichun integrated boundary
# ============================================================


def test_2026_lichun_one_second_before():
    """
    2026年立春1秒前:

    年柱 = 乙巳
    月柱 = 己丑

    日柱・時柱は同じ暦日のため
    己酉 / 丁卯。
    """

    lichun = get_lichun_datetime(
        2026
    )

    target = (
        lichun
        - timedelta(
            seconds=1
        )
    )

    result = _summary(
        target
    )

    assert result == {
        "year": "乙巳",
        "month": "己丑",
        "day": "己酉",
        "hour": "丁卯",
        "day_master": "己",
    }


def test_2026_lichun_exact():
    """
    立春ちょうどから、

    乙巳年 → 丙午年
    己丑月 → 庚寅月

    へ同時切替する。
    """

    lichun = get_lichun_datetime(
        2026
    )

    result = _summary(
        lichun
    )

    assert result == {
        "year": "丙午",
        "month": "庚寅",
        "day": "己酉",
        "hour": "丁卯",
        "day_master": "己",
    }


def test_2026_lichun_one_second_after():
    lichun = get_lichun_datetime(
        2026
    )

    target = (
        lichun
        + timedelta(
            seconds=1
        )
    )

    result = _summary(
        target
    )

    assert result == {
        "year": "丙午",
        "month": "庚寅",
        "day": "己酉",
        "hour": "丁卯",
        "day_master": "己",
    }


def test_lichun_changes_only_year_and_month():
    """
    同じ秒近傍なので、
    立春境界では年柱・月柱だけが変化し、
    日柱・時柱・日主は変わらない。
    """

    lichun = get_lichun_datetime(
        2026
    )

    before = _summary(
        lichun
        - timedelta(
            seconds=1
        )
    )

    exact = _summary(
        lichun
    )

    assert (
        before[
            "year"
        ]
        != exact[
            "year"
        ]
    )

    assert (
        before[
            "month"
        ]
        != exact[
            "month"
        ]
    )

    assert (
        before[
            "day"
        ]
        == exact[
            "day"
        ]
    )

    assert (
        before[
            "hour"
        ]
        == exact[
            "hour"
        ]
    )

    assert (
        before[
            "day_master"
        ]
        == exact[
            "day_master"
        ]
    )


# ============================================================
# 3. Non-Lichun month boundary
# ============================================================


def test_2026_keichitsu_one_second_before():
    """
    啓蟄では年柱は変わらず、
    月柱だけが切り替わる。
    """

    boundary = get_solar_term_datetime(
        2026,
        "啓蟄",
    )

    before = (
        boundary
        - timedelta(
            seconds=1
        )
    )

    result = _calculate(
        before
    )

    assert (
        _pillar(
            result,
            "year",
        )
        == "丙午"
    )

    assert (
        _pillar(
            result,
            "month",
        )
        == "庚寅"
    )


def test_2026_keichitsu_exact():
    boundary = get_solar_term_datetime(
        2026,
        "啓蟄",
    )

    result = _calculate(
        boundary
    )

    assert (
        _pillar(
            result,
            "year",
        )
        == "丙午"
    )

    assert (
        _pillar(
            result,
            "month",
        )
        == "辛卯"
    )


def test_2026_keichitsu_changes_month_not_year():
    boundary = get_solar_term_datetime(
        2026,
        "啓蟄",
    )

    before = _calculate(
        boundary
        - timedelta(
            seconds=1
        )
    )

    exact = _calculate(
        boundary
    )

    assert (
        _pillar(
            before,
            "year",
        )
        == _pillar(
            exact,
            "year",
        )
        == "丙午"
    )

    assert (
        _pillar(
            before,
            "month",
        )
        == "庚寅"
    )

    assert (
        _pillar(
            exact,
            "month",
        )
        == "辛卯"
    )


# ============================================================
# 4. 22:59:59 -> 23:00:00
# ============================================================


def test_225959_complete_chart():
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
        _summary(
            target
        )
        == {
            "year": "甲子",
            "month": "辛未",
            "day": "丙辰",
            "hour": "己亥",
            "day_master": "丙",
        }
    )


def test_230000_complete_chart():
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
        _summary(
            target
        )
        == {
            "year": "甲子",
            "month": "辛未",
            "day": "丙辰",
            "hour": "戊子",
            "day_master": "丙",
        }
    )


def test_2300_changes_hour_only():
    before = _summary(
        datetime(
            1984,
            7,
            21,
            22,
            59,
            59,
            tzinfo=JST,
        )
    )

    exact = _summary(
        datetime(
            1984,
            7,
            21,
            23,
            0,
            0,
            tzinfo=JST,
        )
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
            == exact[
                key
            ]
        )

    assert (
        before[
            "hour"
        ]
        == "己亥"
    )

    assert (
        exact[
            "hour"
        ]
        == "戊子"
    )


# ============================================================
# 5. 23:59:59 -> 00:00:00
# ============================================================


def test_235959_complete_chart():
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
        _summary(
            target
        )
        == {
            "year": "甲子",
            "month": "辛未",
            "day": "丙辰",
            "hour": "戊子",
            "day_master": "丙",
        }
    )


def test_000000_complete_chart():
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
        _summary(
            target
        )
        == {
            "year": "甲子",
            "month": "辛未",
            "day": "丁巳",
            "hour": "庚子",
            "day_master": "丁",
        }
    )


def test_midnight_changes_day_and_hour_stem_but_not_hour_branch():
    before_target = datetime(
        1984,
        7,
        21,
        23,
        59,
        59,
        tzinfo=JST,
    )

    exact_target = datetime(
        1984,
        7,
        22,
        0,
        0,
        0,
        tzinfo=JST,
    )

    before = _calculate(
        before_target
    )

    exact = _calculate(
        exact_target
    )

    assert (
        _pillar(
            before,
            "year",
        )
        == _pillar(
            exact,
            "year",
        )
        == "甲子"
    )

    assert (
        _pillar(
            before,
            "month",
        )
        == _pillar(
            exact,
            "month",
        )
        == "辛未"
    )

    assert (
        _pillar(
            before,
            "day",
        )
        == "丙辰"
    )

    assert (
        _pillar(
            exact,
            "day",
        )
        == "丁巳"
    )

    assert (
        _branch(
            before,
            "hour",
        )
        == "子"
    )

    assert (
        _branch(
            exact,
            "hour",
        )
        == "子"
    )

    assert (
        _pillar(
            before,
            "hour",
        )
        == "戊子"
    )

    assert (
        _pillar(
            exact,
            "hour",
        )
        == "庚子"
    )

    assert (
        _day_master(
            before
        )
        == "丙"
    )

    assert (
        _day_master(
            exact
        )
        == "丁"
    )


# ============================================================
# 6. 00:59:59 -> 01:00:00
# ============================================================


def test_005959_complete_chart():
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
        _summary(
            target
        )
        == {
            "year": "甲子",
            "month": "辛未",
            "day": "丁巳",
            "hour": "庚子",
            "day_master": "丁",
        }
    )


def test_010000_complete_chart():
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
        _summary(
            target
        )
        == {
            "year": "甲子",
            "month": "辛未",
            "day": "丁巳",
            "hour": "辛丑",
            "day_master": "丁",
        }
    )


def test_0100_changes_only_hour_pillar():
    before = _summary(
        datetime(
            1984,
            7,
            22,
            0,
            59,
            59,
            tzinfo=JST,
        )
    )

    exact = _summary(
        datetime(
            1984,
            7,
            22,
            1,
            0,
            0,
            tzinfo=JST,
        )
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
            == exact[
                key
            ]
        )

    assert (
        before[
            "hour"
        ]
        == "庚子"
    )

    assert (
        exact[
            "hour"
        ]
        == "辛丑"
    )


# ============================================================
# 7. Complete night sequence
# ============================================================


def test_complete_night_boundary_sequence():
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
            {
                "year": "甲子",
                "month": "辛未",
                "day": "丙辰",
                "hour": "己亥",
                "day_master": "丙",
            },
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
            {
                "year": "甲子",
                "month": "辛未",
                "day": "丙辰",
                "hour": "戊子",
                "day_master": "丙",
            },
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
            {
                "year": "甲子",
                "month": "辛未",
                "day": "丙辰",
                "hour": "戊子",
                "day_master": "丙",
            },
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
            {
                "year": "甲子",
                "month": "辛未",
                "day": "丁巳",
                "hour": "庚子",
                "day_master": "丁",
            },
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
            {
                "year": "甲子",
                "month": "辛未",
                "day": "丁巳",
                "hour": "庚子",
                "day_master": "丁",
            },
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
            {
                "year": "甲子",
                "month": "辛未",
                "day": "丁巳",
                "hour": "辛丑",
                "day_master": "丁",
            },
        ),
    )

    for (
        target,
        expected,
    ) in samples:
        assert (
            _summary(
                target
            )
            == expected
        )


# ============================================================
# 8. Cross-module consistency
# ============================================================


@pytest.mark.parametrize(
    "target",
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
            1,
            0,
            0,
            tzinfo=JST,
        ),
        datetime(
            1985,
            7,
            17,
            21,
            50,
            tzinfo=JST,
        ),
    ),
)
def test_four_pillar_engine_matches_individual_engines(
    target,
):
    result = _calculate(
        target
    )

    expected_year = (
        calculate_year_pillar(
            target
        )
    )

    year_stem = (
        expected_year[
            0
        ]
    )

    expected_month = (
        calculate_month_pillar(
            target,
            year_stem,
        )
    )

    expected_day = (
        calculate_day_pillar(
            target.date()
        )
    )

    expected_hour = (
        calculate_hour_pillar(
            expected_day[
                0
            ],
            target.hour,
        )
    )

    assert (
        _pillar(
            result,
            "year",
        )
        == expected_year
    )

    assert (
        _pillar(
            result,
            "month",
        )
        == expected_month
    )

    assert (
        _pillar(
            result,
            "day",
        )
        == expected_day
    )

    assert (
        _pillar(
            result,
            "hour",
        )
        == expected_hour
    )

    assert (
        _day_master(
            result
        )
        == expected_day[
            0
        ]
    )


# ============================================================
# 9. Pillar internal consistency
# ============================================================


@pytest.mark.parametrize(
    "target",
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
            2026,
            2,
            4,
            12,
            0,
            0,
            tzinfo=JST,
        ),
    ),
)
def test_each_pillar_equals_stem_plus_branch(
    target,
):
    result = _calculate(
        target
    )

    for position in (
        "year",
        "month",
        "day",
        "hour",
    ):
        assert (
            _pillar(
                result,
                position,
            )
            == (
                _stem(
                    result,
                    position,
                )
                + _branch(
                    result,
                    position,
                )
            )
        )


def test_day_master_always_matches_day_stem():
    samples = (
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
            1985,
            7,
            17,
            21,
            50,
            tzinfo=JST,
        ),
    )

    for target in samples:
        result = _calculate(
            target
        )

        assert (
            _day_master(
                result
            )
            == _stem(
                result,
                "day",
            )
        )


# ============================================================
# 10. Lichun direct-engine agreement
# ============================================================


def test_2026_lichun_four_pillar_agrees_with_individual_engines():
    lichun = get_lichun_datetime(
        2026
    )

    for target in (
        lichun
        - timedelta(
            seconds=1
        ),
        lichun,
        lichun
        + timedelta(
            seconds=1
        ),
    ):
        result = _calculate(
            target
        )

        year = calculate_year_pillar(
            target
        )

        month = calculate_month_pillar(
            target,
            year[
                0
            ],
        )

        day = calculate_day_pillar(
            target.date()
        )

        hour = calculate_hour_pillar(
            day[
                0
            ],
            target.hour,
        )

        assert (
            _pillar(
                result,
                "year",
            )
            == year
        )

        assert (
            _pillar(
                result,
                "month",
            )
            == month
        )

        assert (
            _pillar(
                result,
                "day",
            )
            == day
        )

        assert (
            _pillar(
                result,
                "hour",
            )
            == hour
        )


# ============================================================
# 11. Reproducibility
# ============================================================


@pytest.mark.parametrize(
    "target",
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
            1,
            0,
            0,
            tzinfo=JST,
        ),
        datetime(
            1985,
            7,
            17,
            21,
            50,
            tzinfo=JST,
        ),
    ),
)
def test_four_pillar_boundary_reproducible(
    target,
):
    first = _summary(
        target
    )

    second = _summary(
        target
    )

    assert (
        first
        == second
    )


# ============================================================
# 12. Final smoke
# ============================================================


def test_verified_four_pillar_boundaries_final_smoke():
    """
    最終スモーク。

    主要な四柱境界をまとめて確認する。
    """

    actual = {
        "225959": _summary(
            datetime(
                1984,
                7,
                21,
                22,
                59,
                59,
                tzinfo=JST,
            )
        ),
        "230000": _summary(
            datetime(
                1984,
                7,
                21,
                23,
                0,
                0,
                tzinfo=JST,
            )
        ),
        "235959": _summary(
            datetime(
                1984,
                7,
                21,
                23,
                59,
                59,
                tzinfo=JST,
            )
        ),
        "000000": _summary(
            datetime(
                1984,
                7,
                22,
                0,
                0,
                0,
                tzinfo=JST,
            )
        ),
        "005959": _summary(
            datetime(
                1984,
                7,
                22,
                0,
                59,
                59,
                tzinfo=JST,
            )
        ),
        "010000": _summary(
            datetime(
                1984,
                7,
                22,
                1,
                0,
                0,
                tzinfo=JST,
            )
        ),
    }

    assert actual == {
        "225959": {
            "year": "甲子",
            "month": "辛未",
            "day": "丙辰",
            "hour": "己亥",
            "day_master": "丙",
        },
        "230000": {
            "year": "甲子",
            "month": "辛未",
            "day": "丙辰",
            "hour": "戊子",
            "day_master": "丙",
        },
        "235959": {
            "year": "甲子",
            "month": "辛未",
            "day": "丙辰",
            "hour": "戊子",
            "day_master": "丙",
        },
        "000000": {
            "year": "甲子",
            "month": "辛未",
            "day": "丁巳",
            "hour": "庚子",
            "day_master": "丁",
        },
        "005959": {
            "year": "甲子",
            "month": "辛未",
            "day": "丁巳",
            "hour": "庚子",
            "day_master": "丁",
        },
        "010000": {
            "year": "甲子",
            "month": "辛未",
            "day": "丁巳",
            "hour": "辛丑",
            "day_master": "丁",
        },
    }


# ============================================================
# 13. Metadata
# ============================================================


def test_verified_four_pillar_boundary_metadata():
    assert (
        VERIFIED_FOUR_PILLAR_BOUNDARY_METHOD
        == "verified_four_pillar_boundary_v1"
    )

    assert (
        VERIFIED_FOUR_PILLAR_BOUNDARY_STATUS
        == "golden_regression"
    )
