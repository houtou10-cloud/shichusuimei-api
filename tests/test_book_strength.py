"""基礎編p.98〜103の例題で、本どおりの身旺・身弱の計算を確かめる。"""

from engine.book_strength import calculate_book_strength, void_branches
from engine.twelve_stages import calculate_twelve_stage


def _pillars(year, month, day, hour):
    day_stem = day[0]
    result = {"day_master": {"stem": day_stem}}
    for name, gz in (("year", year), ("month", month), ("day", day), ("hour", hour)):
        result[name] = None if gz is None else {"stem": gz[0], "branch": gz[1], "twelve_stage": calculate_twelve_stage(day_stem, gz[1])}
    return result


def test_kiso_example_balanced_plus2():
    # p.98・p.100：甲辰・癸酉・丁亥・乙巳 → 月令0、五行0、十二運+2、合計+2 中和
    r = calculate_book_strength(_pillars("甲辰", "癸酉", "丁亥", "乙巳"))
    assert (r["month_command_points"], r["five_element_points"], r["twelve_stage_points"]) == (0, 0, 2)
    assert r["book_total_score"] == 2 and r["label"] == "中和"


def test_kiso_example_plus5():
    # p.99・p.100：丙戌・甲午・丁丑・庚子 → 月令+3、五行0、十二運+2、合計+5 身旺
    r = calculate_book_strength(_pillars("丙戌", "甲午", "丁丑", "庚子"))
    assert (r["month_command_points"], r["five_element_points"], r["twelve_stage_points"]) == (3, 0, 2)
    assert r["book_total_score"] == 5 and r["label"] == "身旺"


def test_kiso_example_void_hour_branch():
    # p.101〜102：辛卯・乙未・庚辰・甲申、時支申が空亡 → +1、+1、+1、合計+3 身旺
    r = calculate_book_strength(_pillars("辛卯", "乙未", "庚辰", "甲申"))
    assert set(void_branches("庚", "辰")) == {"申", "酉"}
    assert r["void_positions"] == ["hour"]
    assert (r["month_command_points"], r["five_element_points"], r["twelve_stage_points"]) == (1, 1, 1)
    assert r["book_total_score"] == 3 and r["label"] == "身旺"


def test_kiso_example_month_void_is_not_void():
    # p.102：庚午・戊子・辛酉・丙申、月支子は空亡でも計算上空亡としない → +1、+2、+3、合計+6
    r = calculate_book_strength(_pillars("庚午", "戊子", "辛酉", "丙申"))
    assert r["void_positions"] == []
    assert (r["month_command_points"], r["five_element_points"], r["twelve_stage_points"]) == (1, 2, 3)
    assert r["book_total_score"] == 6


def test_kiso_example_trine_water():
    # p.103 例1：甲子・壬申・庚辰・辛巳、三合水局 → 月令+3、五行−1、十二運+2、合計+4 身旺
    r = calculate_book_strength(_pillars("甲子", "壬申", "庚辰", "辛巳"))
    assert r["combination_bonus"] == [{"branches": "子辰申", "element": "水", "bonus": 1}]
    assert (r["month_command_points"], r["five_element_points"], r["twelve_stage_points"]) == (3, -1, 2)
    assert r["book_total_score"] == 4


def test_kiso_example_directional_fire_and_void_released_by_clash():
    # p.103 例2：丁丑・丁未・丁巳・丙午、火方合、年支丑は空亡だが冲で解空 → +2、+5、+3、合計+10
    r = calculate_book_strength(_pillars("丁丑", "丁未", "丁巳", "丙午"))
    assert r["void_positions"] == []
    assert (r["month_command_points"], r["five_element_points"], r["twelve_stage_points"]) == (2, 5, 3)
    assert r["book_total_score"] == 10 and r["label"] == "身旺"


def test_unknown_birth_time_uses_three_pillars():
    r = calculate_book_strength(_pillars("甲辰", "癸酉", "丁亥", None))
    assert r["confidence"] == "medium"
    assert "hour" not in r["twelve_stages_counted"]
