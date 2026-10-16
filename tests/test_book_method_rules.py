from datetime import datetime

from scripts.book_method_rules import (
    book_hidden_stem,
    book_hidden_stems_for_chart,
    book_hour_pillar,
    days_since_setsuiri,
    in_summer_time,
)


def test_book_hour_example_ding_day_10am():
    # 基礎編p.48：日干丁・午前10時 → 乙巳
    assert book_hour_pillar("丁", datetime(1964, 10, 5, 10, 0)).value == "乙巳"


def test_book_hour_late_night_zi_uses_next_column():
    # 基礎編p.49：甲・己日の午後11時〜0時は丙子、午前0時〜1時は甲子
    assert book_hour_pillar("甲", datetime(2001, 3, 3, 23, 30)).value == "丙子"
    assert book_hour_pillar("己", datetime(2001, 3, 3, 0, 30)).value == "甲子"


def test_book_hour_exact_boundary_goes_to_previous_slot():
    # 基礎編p.49：1時ちょうどは0時〜1時、3時ちょうどは1時〜3時
    assert book_hour_pillar("甲", datetime(2001, 3, 3, 1, 0)).value == "甲子"
    assert book_hour_pillar("甲", datetime(2001, 3, 3, 1, 1)).value == "乙丑"
    assert book_hour_pillar("甲", datetime(2001, 3, 3, 3, 0)).value == "乙丑"
    assert book_hour_pillar("甲", datetime(2001, 3, 3, 23, 0)).value == "乙亥"


def test_book_hour_midnight_exact_is_hold():
    result = book_hour_pillar("甲", datetime(2001, 3, 3, 0, 0))
    assert result.status == "hold" and result.value is None


def test_summer_time_shifts_birth_time_one_hour():
    birth = datetime(1950, 7, 1, 8, 30)
    assert in_summer_time(birth)
    # 8:30 → 7:30（辰 7〜9時の範囲内）。甲日の辰は戊辰。
    result = book_hour_pillar("甲", birth)
    assert result.value == "戊辰"
    assert "サマータイム" in result.note
    # 9:30 → 8:30 は辰、補正しなければ巳
    assert book_hour_pillar("甲", datetime(1950, 7, 1, 9, 30)).value == "戊辰"
    assert book_hour_pillar("甲", datetime(1950, 7, 1, 9, 30), apply_summer_time=False).value == "己巳"
    assert not in_summer_time(datetime(1952, 7, 1, 9, 30))


def test_book_hidden_stem_table_ranges():
    # 基礎編p.52：寅は7日まで戊、8〜14日丙、15日以後甲
    assert book_hidden_stem("寅", 5).value == "戊"
    assert book_hidden_stem("寅", 10).value == "丙"
    assert book_hidden_stem("寅", 20).value == "甲"
    assert book_hidden_stem("辰", 11).value == "癸"
    assert book_hidden_stem("巳", 10).value == "庚"
    assert book_hidden_stem("午", 20).value == "己"
    assert book_hidden_stem("午", 21).value == "丁"
    assert book_hidden_stem("卯", 10).note == "初期"


def test_book_example_1964_10_05_days_and_hidden_stems():
    # 基礎編p.50〜51：10月5日生まれ、前月の節入9月7日から28日目。辰=戊、酉=辛、亥=壬、巳=丙
    birth = datetime(1964, 10, 5, 10, 0)
    assert days_since_setsuiri(birth) == 28
    result = book_hidden_stems_for_chart(birth, {"year": "辰", "month": "酉", "day": "亥", "hour": "巳"})
    assert {k: v.value for k, v in result.items()} == {"year": "戊", "month": "辛", "day": "壬", "hour": "丙"}
