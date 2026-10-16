"""基礎編p.104〜106の例題で、本どおりの格の決め方を確かめる。"""

from datetime import datetime

from engine.book_pattern import determine_book_pattern
from engine.pillars import RULE_SET_BOOK, calculate_four_pillars


def test_kiso_example_indirect_wealth_from_gen_ming():
    # p.105：昭和39年10月5日午前10時生まれ。月支酉の元命は辛（偏財）、透出なし → 偏財格
    pillars = calculate_four_pillars(datetime(1964, 10, 5, 10, 0), rule_set=RULE_SET_BOOK)
    book = determine_book_pattern(pillars)
    assert book["pattern"] == "偏財格"
    assert book["rule_applied"] == "1_gen_ming"
    assert book["is_broken"] is False


def test_kiso_example_broken_direct_wealth():
    # p.105〜106：昭和6年3月26日午前12時、男命。辛未・辛卯・庚辰・壬午。
    # 月支卯の元命乙は正財。年上・月上の劫財（辛）に剋されるため破格の正財タイプ。
    pillars = calculate_four_pillars(datetime(1931, 3, 26, 12, 0), rule_set=RULE_SET_BOOK)
    assert [pillars[p]["pillar"] for p in ("year", "month", "day", "hour")] == ["辛未", "辛卯", "庚辰", "壬午"]
    book = determine_book_pattern(pillars)
    assert book["pattern"] == "正財格"
    assert book["is_broken"] is True


def _fake(day, month_branch, month_main, stems, branches):
    pillars = {"day_master": {"stem": day}}
    for p, s, b in zip(("year", "month", "day", "hour"), stems, branches):
        pillars[p] = {"stem": s, "branch": b, "main_hidden_stem": month_main if p == "month" else None}
    return pillars


def test_trine_uses_peak_branch():
    # 申子辰の三合水局 → 四旺の子の気（癸）。日干庚から癸は傷官。
    pillars = _fake("庚", "申", "庚", ("甲", "壬", "庚", "辛"), ("子", "申", "辰", "巳"))
    book = determine_book_pattern(pillars)
    assert book["rule_applied"] == "2_trine_or_directional_peak"
    assert book["pattern_stem"] == "癸" and book["pattern"] == "傷官格"


def test_only_initial_qi_exposed():
    # 寅月（初気戊・中気丙・正気甲）、元命は甲だが天干には戊だけが透る → 戊を格に
    pillars = _fake("甲", "寅", "甲", ("戊", "壬", "甲", "庚"), ("子", "寅", "午", "申"))
    book = determine_book_pattern(pillars)
    assert book["rule_applied"] == "3_initial_qi_exposed"
    assert book["pattern_stem"] == "戊" and book["pattern"] == "偏財格"


def test_two_qi_exposed_is_hold():
    pillars = _fake("甲", "寅", "甲", ("戊", "丙", "甲", "庚"), ("子", "寅", "午", "申"))
    book = determine_book_pattern(pillars)
    assert book["status"] == "hold"
    assert book["pattern_stem"] == "甲"


def test_kiso_example3_direct_officer_when_initial_qi_shares_element():
    # p.116〜118 例3：昭和13年1月4日午後6時、女命。丁丑・壬子・丙申・丁酉。
    # 元命癸（正官）、月干壬に透干 → 正官格（初気壬と元命癸は同じ水）。
    pillars = calculate_four_pillars(datetime(1938, 1, 4, 18, 0), rule_set=RULE_SET_BOOK)
    assert [pillars[p]["pillar"] for p in ("year", "month", "day", "hour")] == ["丁丑", "壬子", "丙申", "丁酉"]
    book = determine_book_pattern(pillars)
    assert book["pattern"] == "正官格"
    assert book["rule_applied"] == "1_gen_ming"
