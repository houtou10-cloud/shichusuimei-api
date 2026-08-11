"""
tests/test_hour.py

時柱計算のテスト。

検証対象:
- 時支インデックス
- 時支
- 時柱
- 24時間すべての時支
- 10日干すべての亥時
- 不正な時刻
- 不正な日干

採用ルール:
- 子：23:00～00:59
- 丑：01:00～02:59
- 寅：03:00～04:59
- 卯：05:00～06:59
- 辰：07:00～08:59
- 巳：09:00～10:59
- 午：11:00～12:59
- 未：13:00～14:59
- 申：15:00～16:59
- 酉：17:00～18:59
- 戌：19:00～20:59
- 亥：21:00～22:59

時干は五鼠遁に基づく。
"""

import pytest

from engine.hour import (
    calculate_hour_branch,
    calculate_hour_branch_index,
    calculate_hour_pillar,
)


# =========================================================
# Hour branch index
# =========================================================


@pytest.mark.parametrize(
    "hour,expected",
    [
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
    ],
)
def test_hour_branch_index_all_24_hours(
    hour,
    expected,
):
    assert (
        calculate_hour_branch_index(hour)
        == expected
    )


# =========================================================
# Hour branch
# =========================================================


@pytest.mark.parametrize(
    "hour,expected",
    [
        (0, "子"),
        (1, "丑"),
        (2, "丑"),
        (3, "寅"),
        (4, "寅"),
        (5, "卯"),
        (6, "卯"),
        (7, "辰"),
        (8, "辰"),
        (9, "巳"),
        (10, "巳"),
        (11, "午"),
        (12, "午"),
        (13, "未"),
        (14, "未"),
        (15, "申"),
        (16, "申"),
        (17, "酉"),
        (18, "酉"),
        (19, "戌"),
        (20, "戌"),
        (21, "亥"),
        (22, "亥"),
        (23, "子"),
    ],
)
def test_hour_branch_all_24_hours(
    hour,
    expected,
):
    assert (
        calculate_hour_branch(hour)
        == expected
    )


# =========================================================
# Known hour pillar cases
# =========================================================


@pytest.mark.parametrize(
    "day_stem,hour,expected",
    [
        ("甲", 23, "甲子"),
        ("己", 23, "甲子"),
        ("乙", 23, "丙子"),
        ("庚", 23, "丙子"),
        ("丙", 23, "戊子"),
        ("辛", 23, "戊子"),
        ("丁", 23, "庚子"),
        ("壬", 23, "庚子"),
        ("戊", 23, "壬子"),
        ("癸", 23, "壬子"),
    ],
)
def test_hour_pillar_rat_hour_start(
    day_stem,
    hour,
    expected,
):
    assert (
        calculate_hour_pillar(
            day_stem=day_stem,
            hour=hour,
        )
        == expected
    )


# =========================================================
# Hai hour for all ten day stems
# =========================================================


@pytest.mark.parametrize(
    "day_stem,expected",
    [
        ("甲", "乙亥"),
        ("乙", "丁亥"),
        ("丙", "己亥"),
        ("丁", "辛亥"),
        ("戊", "癸亥"),
        ("己", "乙亥"),
        ("庚", "丁亥"),
        ("辛", "己亥"),
        ("壬", "辛亥"),
        ("癸", "癸亥"),
    ],
)
def test_hour_pillar_hai_for_all_day_stems(
    day_stem,
    expected,
):
    result = calculate_hour_pillar(
        day_stem=day_stem,
        hour=21,
    )

    assert result == expected


# =========================================================
# Same branch across two-hour block
# =========================================================


@pytest.mark.parametrize(
    "first_hour,second_hour,expected",
    [
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
    ],
)
def test_two_hour_block_has_same_branch(
    first_hour,
    second_hour,
    expected,
):
    assert (
        calculate_hour_branch(first_hour)
        == expected
    )

    assert (
        calculate_hour_branch(second_hour)
        == expected
    )


# =========================================================
# Rat hour boundary
# =========================================================


def test_rat_hour_wraps_across_midnight():
    assert calculate_hour_branch(23) == "子"
    assert calculate_hour_branch(0) == "子"


def test_rat_hour_same_pillar_across_midnight():
    before_midnight = calculate_hour_pillar(
        day_stem="丁",
        hour=23,
    )

    after_midnight = calculate_hour_pillar(
        day_stem="丁",
        hour=0,
    )

    assert before_midnight == "庚子"
    assert after_midnight == "庚子"


# =========================================================
# Invalid hour
# =========================================================


@pytest.mark.parametrize(
    "hour",
    [
        -100,
        -1,
        24,
        25,
        100,
    ],
)
def test_hour_branch_index_rejects_out_of_range(
    hour,
):
    with pytest.raises(ValueError):
        calculate_hour_branch_index(hour)


@pytest.mark.parametrize(
    "hour",
    [
        -1,
        24,
        100,
    ],
)
def test_hour_branch_rejects_out_of_range(
    hour,
):
    with pytest.raises(ValueError):
        calculate_hour_branch(hour)


@pytest.mark.parametrize(
    "hour",
    [
        -1,
        24,
        100,
    ],
)
def test_hour_pillar_rejects_out_of_range(
    hour,
):
    with pytest.raises(ValueError):
        calculate_hour_pillar(
            day_stem="丁",
            hour=hour,
        )


# =========================================================
# Invalid hour type
# =========================================================


@pytest.mark.parametrize(
    "hour",
    [
        "21",
        21.5,
        None,
    ],
)
def test_hour_branch_index_rejects_non_integer(
    hour,
):
    with pytest.raises(TypeError):
        calculate_hour_branch_index(hour)


@pytest.mark.parametrize(
    "hour",
    [
        "21",
        21.5,
        None,
    ],
)
def test_hour_branch_rejects_non_integer(
    hour,
):
    with pytest.raises(TypeError):
        calculate_hour_branch(hour)


@pytest.mark.parametrize(
    "hour",
    [
        "21",
        21.5,
        None,
    ],
)
def test_hour_pillar_rejects_non_integer(
    hour,
):
    with pytest.raises(TypeError):
        calculate_hour_pillar(
            day_stem="丁",
            hour=hour,
        )


# =========================================================
# Invalid day stem
# =========================================================


@pytest.mark.parametrize(
    "day_stem",
    [
        "",
        "子",
        "A",
        "甲子",
        None,
    ],
)
def test_hour_pillar_rejects_invalid_day_stem(
    day_stem,
):
    with pytest.raises(ValueError):
        calculate_hour_pillar(
            day_stem=day_stem,
            hour=21,
        )
