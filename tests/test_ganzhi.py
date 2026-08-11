from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from engine.calendar import (
    add_days,
    days_between,
    parse_date,
)
from engine.day import calculate_day_pillar
from engine.ganzhi import (
    ganzhi_from_index,
    generate_sixty_ganzhi,
    index_from_ganzhi,
    next_ganzhi,
    normalize_index,
    split_ganzhi,
)
from engine.hour import (
    calculate_hour_branch,
    calculate_hour_branch_index,
    calculate_hour_pillar,
)
from engine.month import (
    calculate_month_branch,
    calculate_month_pillar,
    calculate_month_stem,
)
from engine.pillars import calculate_four_pillars
from engine.year import (
    calculate_effective_year,
    calculate_year_pillar,
    is_near_provisional_lichun,
)


JST = ZoneInfo("Asia/Tokyo")


# ============================================================
# 六十干支 基本テスト
# ============================================================


def test_normalize_index():
    assert normalize_index(0) == 0
    assert normalize_index(59) == 59
    assert normalize_index(60) == 0
    assert normalize_index(61) == 1
    assert normalize_index(-1) == 59


def test_ganzhi_from_index():
    assert ganzhi_from_index(0) == "甲子"
    assert ganzhi_from_index(1) == "乙丑"
    assert ganzhi_from_index(40) == "甲辰"
    assert ganzhi_from_index(41) == "乙巳"
    assert ganzhi_from_index(52) == "丙辰"
    assert ganzhi_from_index(53) == "丁巳"
    assert ganzhi_from_index(59) == "癸亥"
    assert ganzhi_from_index(60) == "甲子"


def test_index_from_ganzhi():
    assert index_from_ganzhi("甲子") == 0
    assert index_from_ganzhi("甲辰") == 40
    assert index_from_ganzhi("乙巳") == 41
    assert index_from_ganzhi("丙辰") == 52
    assert index_from_ganzhi("丁巳") == 53
    assert index_from_ganzhi("癸亥") == 59


def test_split_ganzhi():
    result = split_ganzhi("甲辰")

    assert result["stem"] == "甲"
    assert result["branch"] == "辰"


def test_next_ganzhi():
    assert next_ganzhi("甲辰") == "乙巳"
    assert next_ganzhi("丙辰") == "丁巳"
    assert next_ganzhi("癸亥") == "甲子"
    assert next_ganzhi("甲子", -1) == "癸亥"


def test_generate_sixty_ganzhi():
    cycle = generate_sixty_ganzhi()

    assert len(cycle) == 60
    assert cycle[0] == "甲子"
    assert cycle[40] == "甲辰"
    assert cycle[52] == "丙辰"
    assert cycle[53] == "丁巳"
    assert cycle[59] == "癸亥"
    assert len(set(cycle)) == 60


# ============================================================
# Calendar
# ============================================================


def test_parse_date():
    result = parse_date("1984-07-21")

    assert result == date(1984, 7, 21)


def test_days_between():
    start = date(1984, 7, 21)
    end = date(1984, 7, 22)

    assert days_between(start, end) == 1
    assert days_between(end, start) == -1


def test_add_days():
    target = date(1984, 7, 21)

    assert add_days(target, 1) == date(1984, 7, 22)
    assert add_days(target, -1) == date(1984, 7, 20)


# ============================================================
# 日柱
# ============================================================


def test_verified_day_pillars():
    """
    engine/day.py の正式回帰基準。

    1984-07-10 = 乙巳 を最優先基準とするため、
    11日後の1984-07-21は丙辰、
    12日後の1984-07-22は丁巳となる。

    1985-07-17は1984-07-21から361日後で、
    60日周期では+1なので丁巳。
    """
    assert (
        calculate_day_pillar(
            date(1984, 7, 10)
        )
        == "乙巳"
    )

    assert (
        calculate_day_pillar(
            date(1984, 7, 21)
        )
        == "丙辰"
    )

    assert (
        calculate_day_pillar(
            date(1984, 7, 22)
        )
        == "丁巳"
    )

    assert (
        calculate_day_pillar(
            date(1985, 7, 17)
        )
        == "丁巳"
    )


def test_day_pillar_moves_one_step_per_day():
    first = calculate_day_pillar(
        date(1984, 7, 21)
    )
    second = calculate_day_pillar(
        date(1984, 7, 22)
    )

    assert next_ganzhi(first) == second


# ============================================================
# 時支・時柱
# ============================================================


def test_hour_branch_boundaries():
    assert calculate_hour_branch(23) == "子"
    assert calculate_hour_branch(0) == "子"

    assert calculate_hour_branch(1) == "丑"
    assert calculate_hour_branch(2) == "丑"

    assert calculate_hour_branch(3) == "寅"
    assert calculate_hour_branch(4) == "寅"

    assert calculate_hour_branch(11) == "午"
    assert calculate_hour_branch(12) == "午"

    assert calculate_hour_branch(13) == "未"
    assert calculate_hour_branch(14) == "未"

    assert calculate_hour_branch(21) == "亥"
    assert calculate_hour_branch(22) == "亥"


def test_hour_branch_index():
    assert calculate_hour_branch_index(23) == 0
    assert calculate_hour_branch_index(0) == 0
    assert calculate_hour_branch_index(4) == 2
    assert calculate_hour_branch_index(12) == 6
    assert calculate_hour_branch_index(22) == 11


def test_verified_hour_pillars():
    # 1984-07-22・丁日・04:15
    assert (
        calculate_hour_pillar(
            "丁",
            4,
        )
        == "壬寅"
    )

    # 1984-07-22・丁日・13:40
    assert (
        calculate_hour_pillar(
            "丁",
            13,
        )
        == "丁未"
    )

    # 1985-07-17・丁日・21:50
    assert (
        calculate_hour_pillar(
            "丁",
            21,
        )
        == "辛亥"
    )

    # 1984-07-21・丙日・12:00
    assert (
        calculate_hour_pillar(
            "丙",
            12,
        )
        == "甲午"
    )


def test_invalid_hour():
    with pytest.raises(ValueError):
        calculate_hour_pillar("丁", -1)

    with pytest.raises(ValueError):
        calculate_hour_pillar("丁", 24)

    with pytest.raises(ValueError):
        calculate_hour_pillar("無", 12)


# ============================================================
# 年柱
# ============================================================


def test_year_pillar_after_provisional_lichun():
    birth_datetime = datetime(
        1984,
        7,
        22,
        4,
        15,
        tzinfo=JST,
    )

    assert (
        calculate_effective_year(
            birth_datetime
        )
        == 1984
    )

    assert (
        calculate_year_pillar(
            birth_datetime
        )
        == "甲子"
    )


def test_year_pillar_for_1985():
    birth_datetime = datetime(
        1985,
        7,
        17,
        21,
        50,
        tzinfo=JST,
    )

    assert (
        calculate_year_pillar(
            birth_datetime
        )
        == "乙丑"
    )


def test_year_before_provisional_lichun():
    birth_datetime = datetime(
        1984,
        2,
        3,
        12,
        0,
        tzinfo=JST,
    )

    assert (
        calculate_effective_year(
            birth_datetime
        )
        == 1983
    )

    assert (
        calculate_year_pillar(
            birth_datetime
        )
        == "癸亥"
    )


def test_year_after_provisional_lichun():
    birth_datetime = datetime(
        1984,
        2,
        5,
        12,
        0,
        tzinfo=JST,
    )

    assert (
        calculate_effective_year(
            birth_datetime
        )
        == 1984
    )

    assert (
        calculate_year_pillar(
            birth_datetime
        )
        == "甲子"
    )


def test_near_provisional_lichun_warning():
    near_datetime = datetime(
        1984,
        2,
        4,
        12,
        0,
        tzinfo=JST,
    )

    normal_datetime = datetime(
        1984,
        7,
        22,
        12,
        0,
        tzinfo=JST,
    )

    assert (
        is_near_provisional_lichun(
            near_datetime
        )
        is True
    )

    assert (
        is_near_provisional_lichun(
            normal_datetime
        )
        is False
    )


# ============================================================
# 月柱
# ============================================================


def test_month_branch():
    assert (
        calculate_month_branch(
            datetime(
                1984,
                7,
                22,
            )
        )
        == "未"
    )

    assert (
        calculate_month_branch(
            datetime(
                1984,
                8,
                10,
            )
        )
        == "申"
    )

    assert (
        calculate_month_branch(
            datetime(
                1984,
                2,
                10,
            )
        )
        == "寅"
    )

    assert (
        calculate_month_branch(
            datetime(
                1984,
                12,
                20,
            )
        )
        == "子"
    )


def test_month_stem_by_five_tigers():
    assert (
        calculate_month_stem(
            "甲",
            "寅",
        )
        == "丙"
    )

    assert (
        calculate_month_stem(
            "甲",
            "未",
        )
        == "辛"
    )

    assert (
        calculate_month_stem(
            "乙",
            "未",
        )
        == "癸"
    )

    assert (
        calculate_month_stem(
            "丙",
            "未",
        )
        == "乙"
    )


def test_verified_month_pillars():
    assert (
        calculate_month_pillar(
            datetime(
                1984,
                7,
                22,
                4,
                15,
            ),
            "甲",
        )
        == "辛未"
    )

    assert (
        calculate_month_pillar(
            datetime(
                1985,
                7,
                17,
                21,
                50,
            ),
            "乙",
        )
        == "癸未"
    )


# ============================================================
# 四柱
# ============================================================


def test_verified_four_pillars_1984_early_hour():
    birth_datetime = datetime(
        1984,
        7,
        22,
        4,
        15,
        tzinfo=JST,
    )

    result = calculate_four_pillars(
        birth_datetime
    )

    assert result["year"]["pillar"] == "甲子"
    assert result["month"]["pillar"] == "辛未"
    assert result["day"]["pillar"] == "丁巳"
    assert result["hour"]["pillar"] == "壬寅"
    assert result["day_master"]["stem"] == "丁"


def test_verified_four_pillars_1984_afternoon():
    birth_datetime = datetime(
        1984,
        7,
        22,
        13,
        40,
        tzinfo=JST,
    )

    result = calculate_four_pillars(
        birth_datetime
    )

    assert result["year"]["pillar"] == "甲子"
    assert result["month"]["pillar"] == "辛未"
    assert result["day"]["pillar"] == "丁巳"
    assert result["hour"]["pillar"] == "丁未"
    assert result["day_master"]["stem"] == "丁"


def test_verified_four_pillars_1985():
    birth_datetime = datetime(
        1985,
        7,
        17,
        21,
        50,
        tzinfo=JST,
    )

    result = calculate_four_pillars(
        birth_datetime
    )

    assert result["year"]["pillar"] == "乙丑"
    assert result["month"]["pillar"] == "癸未"
    assert result["day"]["pillar"] == "丁巳"
    assert result["hour"]["pillar"] == "辛亥"
    assert result["day_master"]["stem"] == "丁"


def test_verified_four_pillars_1984_previous_day():
    birth_datetime = datetime(
        1984,
        7,
        21,
        12,
        0,
        tzinfo=JST,
    )

    result = calculate_four_pillars(
        birth_datetime
    )

    assert result["year"]["pillar"] == "甲子"
    assert result["month"]["pillar"] == "辛未"
    assert result["day"]["pillar"] == "丙辰"
    assert result["hour"]["pillar"] == "甲午"
    assert result["day_master"]["stem"] == "丙"
