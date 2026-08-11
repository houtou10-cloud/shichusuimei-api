"""
tests/test_day.py

日柱計算の回帰テスト。

検証対象:
- 基準日
- 既知の検証済み日柱
- 前日・翌日
- 年末年始
- うるう年
- 六十干支60日周期
- 過去日付
- 未来日付
- 不正な入力

採用ルール:
- 日柱の切り替えは午前0時
- 日本標準時（JST）の日付を前提とする
- 1984年7月21日 = 丙辰を基準とする
"""

from datetime import date, datetime

import pytest

from engine.day import (
    BASE_DATE,
    BASE_GANZHI_INDEX,
    calculate_day_pillar,
)


# =========================================================
# Base configuration
# =========================================================


def test_day_base_date():
    assert BASE_DATE == date(
        1984,
        7,
        21,
    )


def test_day_base_ganzhi_index():
    assert BASE_GANZHI_INDEX == 52


def test_day_base_pillar():
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


# =========================================================
# Verified regression cases
# =========================================================


@pytest.mark.parametrize(
    "target_date,expected",
    [
        (
            date(
                1984,
                7,
                10,
            ),
            "乙巳",
        ),
        (
            date(
                1984,
                7,
                21,
            ),
            "丙辰",
        ),
        (
            date(
                1984,
                7,
                22,
            ),
            "丁巳",
        ),
        (
            date(
                1985,
                7,
                17,
            ),
            "丁巳",
        ),
    ],
)
def test_day_verified_regression_cases(
    target_date,
    expected,
):
    assert (
        calculate_day_pillar(
            target_date
        )
        == expected
    )


# =========================================================
# Days around verified anchor
# =========================================================


@pytest.mark.parametrize(
    "target_date,expected",
    [
        (
            date(
                1984,
                7,
                9,
            ),
            "甲辰",
        ),
        (
            date(
                1984,
                7,
                10,
            ),
            "乙巳",
        ),
        (
            date(
                1984,
                7,
                11,
            ),
            "丙午",
        ),
        (
            date(
                1984,
                7,
                20,
            ),
            "乙卯",
        ),
        (
            date(
                1984,
                7,
                21,
            ),
            "丙辰",
        ),
        (
            date(
                1984,
                7,
                22,
            ),
            "丁巳",
        ),
    ],
)
def test_day_sequence_around_anchor(
    target_date,
    expected,
):
    assert (
        calculate_day_pillar(
            target_date
        )
        == expected
    )


# =========================================================
# Year boundary
# =========================================================


@pytest.mark.parametrize(
    "target_date,expected",
    [
        (
            date(
                1984,
                12,
                31,
            ),
            "己亥",
        ),
        (
            date(
                1985,
                1,
                1,
            ),
            "庚子",
        ),
    ],
)
def test_day_year_boundary(
    target_date,
    expected,
):
    assert (
        calculate_day_pillar(
            target_date
        )
        == expected
    )


# =========================================================
# Leap year boundary
# =========================================================


@pytest.mark.parametrize(
    "target_date,expected",
    [
        (
            date(
                1984,
                2,
                28,
            ),
            "壬辰",
        ),
        (
            date(
                1984,
                2,
                29,
            ),
            "癸巳",
        ),
        (
            date(
                1984,
                3,
                1,
            ),
            "甲午",
        ),
    ],
)
def test_day_leap_year_1984(
    target_date,
    expected,
):
    assert (
        calculate_day_pillar(
            target_date
        )
        == expected
    )


@pytest.mark.parametrize(
    "target_date,expected",
    [
        (
            date(
                2000,
                2,
                28,
            ),
            "丙辰",
        ),
        (
            date(
                2000,
                2,
                29,
            ),
            "丁巳",
        ),
        (
            date(
                2000,
                3,
                1,
            ),
            "戊午",
        ),
    ],
)
def test_day_leap_year_2000(
    target_date,
    expected,
):
    assert (
        calculate_day_pillar(
            target_date
        )
        == expected
    )


# =========================================================
# 60-day cycle
# =========================================================


def test_day_pillar_repeats_after_60_days():
    start = date(
        1984,
        7,
        21,
    )

    after_60_days = date(
        1984,
        9,
        19,
    )

    assert (
        calculate_day_pillar(start)
        == calculate_day_pillar(
            after_60_days
        )
    )


def test_day_pillar_base_repeats_after_60_days():
    assert (
        calculate_day_pillar(
            date(
                1984,
                9,
                19,
            )
        )
        == "丙辰"
    )


# =========================================================
# Previous 60-day cycle
# =========================================================


def test_day_pillar_repeats_60_days_before():
    before_60_days = date(
        1984,
        5,
        22,
    )

    assert (
        calculate_day_pillar(
            before_60_days
        )
        == "丙辰"
    )


# =========================================================
# Deterministic behavior
# =========================================================


def test_day_pillar_same_date_same_result():
    target = date(
        1985,
        7,
        17,
    )

    first = calculate_day_pillar(
        target
    )

    second = calculate_day_pillar(
        target
    )

    assert first == second
    assert first == "丁巳"


# =========================================================
# Return type
# =========================================================


def test_day_pillar_returns_string():
    result = calculate_day_pillar(
        date(
            1984,
            7,
            21,
        )
    )

    assert isinstance(
        result,
        str,
    )


def test_day_pillar_returns_two_characters():
    result = calculate_day_pillar(
        date(
            1984,
            7,
            21,
        )
    )

    assert len(result) == 2


# =========================================================
# Invalid input
# =========================================================


@pytest.mark.parametrize(
    "invalid_value",
    [
        "1984-07-21",
        "1984/07/21",
        19840721,
        0,
        21.0,
        None,
        [],
        {},
    ],
)
def test_day_pillar_rejects_non_date(
    invalid_value,
):
    with pytest.raises(TypeError):
        calculate_day_pillar(
            invalid_value
        )


# =========================================================
# datetime handling
# =========================================================


def test_day_pillar_rejects_datetime():
    """
    datetime は date のサブクラスなので、
    現在の isinstance(target_date, date)
    だけでは通過する可能性がある。

    v1.0では calculate_day_pillar は
    date型専用であることを期待する。
    """

    with pytest.raises(TypeError):
        calculate_day_pillar(
            datetime(
                1984,
                7,
                21,
                12,
                0,
            )
        )
