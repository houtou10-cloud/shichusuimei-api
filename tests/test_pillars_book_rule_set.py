from datetime import datetime

import pytest

from engine.pillars import RULE_SET_BOOK, calculate_four_pillars


def test_default_rule_set_is_book_and_engine_v1_is_kept():
    default = calculate_four_pillars(datetime(1964, 10, 5, 10, 0))
    book = calculate_four_pillars(datetime(1964, 10, 5, 10, 0), rule_set=RULE_SET_BOOK)
    engine = calculate_four_pillars(datetime(1964, 10, 5, 10, 0), rule_set="engine_v1")
    assert default == book
    assert default["calculation_rules"]["rule_set"] == RULE_SET_BOOK
    assert "rule_set" not in engine["calculation_rules"]
    assert engine["day"]["hidden_stems"] == ["壬", "甲"]


def test_book_rule_set_reproduces_kiso_p50_51_example():
    result = calculate_four_pillars(datetime(1964, 10, 5, 10, 0), rule_set=RULE_SET_BOOK)
    assert [result[p]["pillar"] for p in ("year", "month", "day", "hour")] == ["甲辰", "癸酉", "丁亥", "乙巳"]
    assert [result[p]["main_hidden_stem"] for p in ("year", "month", "day", "hour")] == ["戊", "辛", "壬", "丙"]
    assert [result[p]["hidden_stems"][0] for p in ("year", "month", "day", "hour")] == ["戊", "辛", "壬", "丙"]
    assert result["calculation_rules"]["days_since_setsuiri"] == 28
    assert result["calculation_rules"]["rule_set"] == RULE_SET_BOOK
    assert result["day"]["stem_ten_god"] is None


def test_book_rule_set_late_zi_and_early_hidden_stem():
    birth = datetime(2001, 3, 3, 23, 30)
    engine = calculate_four_pillars(birth, rule_set="engine_v1")
    book = calculate_four_pillars(birth, rule_set=RULE_SET_BOOK)
    assert engine["day"]["pillar"] == book["day"]["pillar"] == "乙丑"
    assert engine["hour"]["pillar"] == "丙子"
    assert book["hour"]["pillar"] == "戊子"
    # 寅月の節入から27日目 → 正期の甲
    assert book["month"]["hidden_stems"][0] == "甲"
    assert book["hour"]["stem_ten_god"] == "正財"


def test_book_rule_set_hold_keeps_engine_hour_with_warning():
    birth = datetime(2001, 3, 3, 0, 0)
    engine = calculate_four_pillars(birth, rule_set="engine_v1")
    book = calculate_four_pillars(birth, rule_set=RULE_SET_BOOK)
    assert book["hour"]["pillar"] == engine["hour"]["pillar"]
    assert book["calculation_rules"]["hour_rule_applied"] == "hold_engine_v1_kept"
    assert any("本どおりの時柱を決められない" in w for w in book["warnings"])


def test_unknown_rule_set_is_rejected():
    with pytest.raises(ValueError):
        calculate_four_pillars(datetime(2001, 3, 3, 12, 0), rule_set="other")
