"""基礎編p.61〜64・p.114〜117の例題で、本どおりの立運を確かめる。"""

from datetime import datetime

from api.models import ChartRequest
from engine.chart import calculate_chart
from engine.luck_pillars import calculate_book_start_age


def test_book_start_age_examples_p61():
    base = datetime(2001, 3, 1, 12, 0)
    assert calculate_book_start_age(base, datetime(2001, 3, 13, 5, 0)) == 4.0
    assert round(calculate_book_start_age(base, datetime(2001, 3, 8, 5, 0)) * 12) == 28  # 2歳4ヵ月
    assert round(calculate_book_start_age(base, datetime(2001, 3, 3, 5, 0)) * 12) == 8   # 8ヵ月


def _luck(date, time, gender):
    req = ChartRequest(birth_date=date, birth_time=time, birth_place="東京都", gender=gender)
    return calculate_chart(req, target_datetime=datetime(2026, 1, 1))["luck_pillars"]


def test_book_examples_start_age_match_book():
    assert _luck("1964-10-05", "10:00", "female")["start_age_detail"] == {"years": 9, "months": 4, "days": 0}
    assert _luck("1964-10-06", "11:30", "male")["start_age_detail"] == {"years": 0, "months": 8, "days": 0}
    assert _luck("1938-01-04", "18:00", "female")["start_age_detail"] == {"years": 0, "months": 8, "days": 0}


def test_engine_v1_start_age_is_kept():
    req = ChartRequest(birth_date="1964-10-05", birth_time="10:00", birth_place="東京都", gender="female")
    lp = calculate_chart(req, target_datetime=datetime(2026, 1, 1), rule_set="engine_v1")["luck_pillars"]
    assert lp["calculation_rules"]["start_age_rule"] == "三日一年法"
