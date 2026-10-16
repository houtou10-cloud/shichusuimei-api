"""『四柱推命 基礎』の手順どおりに時柱と蔵干を求める規則（本どおりモード）。

engine/pillars.py の rule_set="book_kiso" から使う。既定（rule_set="engine_v1"）
の計算には影響しない。節入日時は既存の天文計算（engine.solar_terms）を使う。

原典の根拠
----------
時柱      : 基礎編p.48〜49（干支時刻表、区切りの扱い、サマータイム）
蔵干      : 基礎編p.50〜52（節入からの日数の数え方、月律分野蔵干表）

本の記述から一意に決められない点は status="hold" と理由を返す。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from engine.constants import BRANCHES, STEMS
from engine.solar_terms import get_current_solar_term


# 基礎編p.49 干支時刻表：日干の組ごとの「午前0時〜1時」の子の干。
# 甲・己日=甲子、乙・庚日=丙子、丙・辛日=戊子、丁・壬日=庚子、戊・癸日=壬子
_ZI_STEM_INDEX = {"甲": 0, "己": 0, "乙": 2, "庚": 2, "丙": 4, "辛": 4, "丁": 6, "壬": 6, "戊": 8, "癸": 8}

# 基礎編p.49 サマータイムの実施期間（期間中は生時を1時間繰り下げる）。
SUMMER_TIME_PERIODS = (
    (date(1948, 5, 2), date(1948, 9, 11)),
    (date(1949, 4, 3), date(1949, 9, 10)),
    (date(1950, 5, 7), date(1950, 9, 9)),
    (date(1951, 5, 6), date(1951, 9, 8)),
)

# 基礎編p.52 月律分野蔵干表（阿部泰山式）。
# 各地支について (この日数まで, 蔵干, 区分) を順に並べる。最後は21日以後を含む。
_PHASE_TABLE = {
    "子": ((10, "壬", "初期"), (99, "癸", "正期")),
    "丑": ((9, "癸", "初期"), (12, "辛", "中期"), (99, "己", "正期")),
    "寅": ((7, "戊", "初期"), (14, "丙", "中期"), (99, "甲", "正期")),
    "卯": ((10, "甲", "初期"), (99, "乙", "正期")),
    "辰": ((9, "乙", "初期"), (12, "癸", "中期"), (99, "戊", "正期")),
    "巳": ((7, "戊", "初期"), (14, "庚", "中期"), (99, "丙", "正期")),
    "午": ((10, "丙", "初期"), (20, "己", "中期"), (99, "丁", "正期")),
    "未": ((9, "丁", "初期"), (12, "乙", "中期"), (99, "己", "正期")),
    "申": ((7, "戊", "初期"), (14, "壬", "中期"), (99, "庚", "正期")),
    "酉": ((10, "庚", "初期"), (99, "辛", "正期")),
    "戌": ((9, "辛", "初期"), (12, "丁", "中期"), (99, "戊", "正期")),
    "亥": ((7, "戊", "初期"), (14, "甲", "中期"), (99, "壬", "正期")),
}


@dataclass(frozen=True)
class BookResult:
    value: str | None
    status: str  # "ok" | "hold"
    note: str = ""


def in_summer_time(birth: datetime) -> bool:
    d = birth.date()
    return any(start <= d <= end for start, end in SUMMER_TIME_PERIODS)


def book_hour_pillar(day_stem: str, birth: datetime, *, apply_summer_time: bool = True) -> BookResult:
    """基礎編p.49の干支時刻表で時柱を求める。

    区切りちょうどの時刻は前の時間帯に入れる（1時ちょうど→0時〜1時）。
    午後11時〜0時は、表の「午後11時〜0時」の欄（翌日の日干の子）を使う。
    サマータイム期間は生時を1時間繰り下げる。
    """
    if day_stem not in _ZI_STEM_INDEX:
        raise ValueError(f"不正な日干です: {day_stem}")
    note = ""
    t = birth
    if apply_summer_time and in_summer_time(birth):
        t = birth - timedelta(hours=1)
        note = "サマータイム期間のため生時を1時間繰り下げ"
        if t.date() != birth.date():
            return BookResult(None, "hold", "繰り下げで日付が変わるため、日柱の扱いが本の記述から決められない")
    minutes = t.hour * 60 + t.minute + (1 if (t.second or t.microsecond) else 0)
    if minutes == 0:
        return BookResult(None, "hold", "午前0時ちょうどは、前日の『午後11時〜0時』か当日の『午前0時〜1時』か本から決められない")
    base = _ZI_STEM_INDEX[day_stem]
    if minutes <= 60:  # 午前0時〜1時（1時ちょうどを含む）
        return BookResult(STEMS[base] + "子", "ok", note)
    if minutes > 23 * 60:  # 午後11時〜0時：表では次の子（干が2つ進む）
        return BookResult(STEMS[(base + 12) % 10] + "子", "ok", (note + "・" if note else "") + "午後11時〜0時の欄")
    # 丑(1-3時]、寅(3-5時] … 亥(21-23時]
    branch_index = (minutes - 61) // 120 + 1
    return BookResult(STEMS[(base + branch_index) % 10] + BRANCHES[branch_index], "ok", note)


def days_since_setsuiri(birth: datetime) -> int:
    """基礎編p.50：節入前は前月の節入日から、節入後はその月の節入日から数える。

    本の例題（10月5日、前月の節入9月7日 → 30−7＋5＝28）に合わせ、
    節入日からの日付の差で数える（節入日当日は0日目）。
    """
    term = get_current_solar_term(birth)
    return (birth.date() - term.datetime.date()).days


def book_hidden_stem(branch: str, days: int) -> BookResult:
    """基礎編p.52の月律分野蔵干表で、節入後の日数に対応する蔵干を返す。"""
    if branch not in _PHASE_TABLE:
        raise ValueError(f"不正な地支です: {branch}")
    if days < 0:
        return BookResult(None, "hold", "節入後の日数が負")
    for limit, stem, phase in _PHASE_TABLE[branch]:
        if days <= limit:
            return BookResult(stem, "ok", phase)
    raise AssertionError("unreachable")


def book_hidden_stems_for_chart(birth: datetime, branches: dict[str, str]) -> dict[str, BookResult]:
    """同じ日数を四つの地支すべてに当てはめる（基礎編p.51の例題の方法）。"""
    days = days_since_setsuiri(birth)
    return {position: book_hidden_stem(branch, days) for position, branch in branches.items()}


def month_branch_phases(branch: str) -> tuple[tuple[str, str], ...]:
    """月律分野蔵干表で、その地支に入る干と区分（初期・中期・正期）を順に返す。"""
    if branch not in _PHASE_TABLE:
        raise ValueError(f"不正な地支です: {branch}")
    return tuple((stem, phase) for _, stem, phase in _PHASE_TABLE[branch])
