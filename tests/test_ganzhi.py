from datetime import date

from engine.calendar import add_days, days_between, parse_date
from engine.day import calculate_day_pillar
from engine.ganzhi import (
    ganzhi_from_index,
    generate_sixty_ganzhi,
    index_from_ganzhi,
    next_ganzhi,
    normalize_index,
    split_ganzhi,
)


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
    assert ganzhi_from_index(59) == "癸亥"
    assert ganzhi_from_index(60) == "甲子"


def test_index_from_ganzhi():
    assert index_from_ganzhi("甲子") == 0
    assert index_from_ganzhi("甲辰") == 40
    assert index_from_ganzhi("乙巳") == 41
    assert index_from_ganzhi("癸亥") == 59


def test_split_ganzhi():
    result = split_ganzhi("甲辰")

    assert result["stem"] == "甲"
    assert result["branch"] == "辰"


def test_next_ganzhi():
    assert next_ganzhi("甲辰") == "乙巳"
    assert next_ganzhi("癸亥") == "甲子"
    assert next_ganzhi("甲子", -1) == "癸亥"


def test_generate_sixty_ganzhi():
    cycle = generate_sixty_ganzhi()

    assert len(cycle) == 60
    assert cycle[0] == "甲子"
    assert cycle[40] == "甲辰"
    assert cycle[59] == "癸亥"
    assert len(set(cycle)) == 60


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


def test_verified_day_pillars():
    assert calculate_day_pillar(date(1984, 7, 21)) == "甲辰"
    assert calculate_day_pillar(date(1984, 7, 22)) == "乙巳"
    assert calculate_day_pillar(date(1985, 7, 17)) == "乙巳"


def test_day_pillar_moves_one_step_per_day():
    first = calculate_day_pillar(date(1984, 7, 21))
    second = calculate_day_pillar(date(1984, 7, 22))

    assert next_ganzhi(first) == second
