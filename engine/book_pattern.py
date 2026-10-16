"""『四柱推命 基礎』p.104〜106の格（タイプ）の決め方（本どおりモード）。

内格の取り方の基本（p.104）
  ① 原則として元命（月支の蔵干）の通変星で格とする。
  ② 地支が三合・方合する場合は、その気の四旺（子・午・卯・酉）で格を定める。
  ③ 月支中の初気のみが天干に透っている場合は、それを格にとる。
  ④ 月支中の正気・中気・初気がすべて天干に透っている場合は、生日により定める。
  ⑤ 月支中の気が二種天干に透っている場合は、いずれの作用が大きいかを調べて定める。
破格（p.105〜106）：吉星の格が、それを剋す星に破られる場合。
外格（特殊な格）は「一定の条件」とあるのみで、条件は本のこの範囲にない。

本から一意に決められない点は status を "hold" にし、notes に書く。
"""

from __future__ import annotations

from typing import Any

from engine.book_rules import month_branch_phases
from engine.ten_gods import calculate_ten_god

# 本の格名と、既存の格局用神の規則で使う技術名。
# 比肩・劫財の格（本では「比肩タイプ」「劫財タイプ」）は、既存の規則の
# jianlu（建禄格）・yangren（羊刃格）に対応づける（八雲式の対応づけ）。
PATTERN_BY_TEN_GOD = {
    "正官": ("正官格", "direct_officer"),
    "偏官": ("偏官格", "seven_killings"),
    "正財": ("正財格", "direct_wealth"),
    "偏財": ("偏財格", "indirect_wealth"),
    "印綬": ("印綬格", "direct_resource"),
    "偏印": ("偏印格", "indirect_resource"),
    "食神": ("食神格", "eating_god"),
    "傷官": ("傷官格", "hurting_officer"),
    "比肩": ("比肩格", "jianlu"),
    "劫財": ("劫財格", "yangren"),
}

# 基礎編p.23「吉星は剋を嫌い」：吉星の格と、それを剋す星
_BREAKER_OF_AUSPICIOUS = {"偏財": "比肩", "正財": "劫財", "印綬": "正財", "正官": "傷官", "食神": "偏印"}

_TRINES = ((frozenset("申子辰"), "子"), (frozenset("亥卯未"), "卯"), (frozenset("寅午戌"), "午"), (frozenset("巳酉丑"), "酉"))
_DIRECTIONALS = ((frozenset("寅卯辰"), "卯"), (frozenset("巳午未"), "午"), (frozenset("申酉戌"), "酉"), (frozenset("亥子丑"), "子"))
# 四旺の支の正気（月律分野蔵干表の正期）
_PEAK_MAIN_STEM = {"子": "癸", "卯": "乙", "午": "丁", "酉": "辛"}


_ELEMENT = {"甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土", "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水"}


def _initial(phases):
    return next(s for s, phase in phases if phase == "初期")


def determine_book_pattern(pillars: dict[str, Any]) -> dict[str, Any]:
    """pillars は rule_set="book_kiso" の calculate_four_pillars の戻り値。"""
    day_stem = pillars["day_master"]["stem"]
    month = pillars["month"]
    month_branch = month["branch"]
    gen_ming_stem = month["main_hidden_stem"]  # 本どおりモードでは月律分野蔵干表で選んだ干
    positions = [p for p in ("year", "month", "day", "hour") if pillars.get(p)]
    branches = {pillars[p]["branch"] for p in positions}
    exposed_stems = {pillars[p]["stem"] for p in positions if p != "day"}
    notes: list[str] = []
    status = "ok"
    rule = "1_gen_ming"
    stem = gen_ming_stem

    combination = next(
        ((group, peak) for group, peak in _TRINES + _DIRECTIONALS if group <= branches),
        None,
    )
    phases = month_branch_phases(month_branch)
    exposed_phases = [phase for s, phase in phases if s in exposed_stems]

    if combination is not None:
        group, peak = combination
        stem = _PEAK_MAIN_STEM[peak]
        rule = "2_trine_or_directional_peak"
        notes.append(f"地支が{''.join(sorted(group))}で三合・方合するため、四旺の{peak}の気（{stem}）で格を定めた")
    elif exposed_phases == ["初期"] and _ELEMENT[_initial(phases)] != _ELEMENT[gen_ming_stem]:
        # 初気が元命と同じ五行のとき（例：子月の壬と癸）は元命のまま。
        # 基礎編p.116〜118の例3（丙日・子月、元命癸、月干壬が透干）は正官格。
        stem = _initial(phases)
        rule = "3_initial_qi_exposed"
        notes.append(f"月支中の初気（{stem}）のみが天干に透っている")
    elif len(phases) >= 3 and len(exposed_phases) == len(phases):
        rule = "4_all_qi_exposed_by_birth_day"
        notes.append("月支中の気がすべて天干に透っているため、生日（元命）で定めた")
    elif len(exposed_phases) == 2:
        status = "hold"
        rule = "5_two_qi_exposed_hold"
        notes.append("月支中の気が二種天干に透っている。いずれの作用が大きいかの判定方法が本に示されていないため、元命で仮に定めた")

    ten_god = calculate_ten_god(day_stem, stem)
    pattern, technical = PATTERN_BY_TEN_GOD[ten_god]

    stem_ten_gods = {calculate_ten_god(day_stem, s) for s in exposed_stems}
    breaker = _BREAKER_OF_AUSPICIOUS.get(ten_god)
    is_broken = breaker is not None and breaker in stem_ten_gods
    if is_broken:
        notes.append(f"吉星の{ten_god}を剋す{breaker}が天干にあるため破格（p.105〜106の例による）")

    return {
        "method": "book_kiso_p104_106",
        "pattern": pattern,
        "technical_pattern": technical,
        "ten_god": ten_god,
        "pattern_stem": stem,
        "gen_ming_stem": gen_ming_stem,
        "rule_applied": rule,
        "exposed_month_qi": exposed_phases,
        "is_broken": is_broken,
        "status": status,
        "notes": notes,
        "outer_pattern_checked": False,
    }


def apply_to_pattern_judgment(pattern_judgment: dict[str, Any], book: dict[str, Any]) -> dict[str, Any]:
    """既存の pattern_judgment の主要キーを、本の格で置き換えた辞書を返す。"""
    result = dict(pattern_judgment)
    primary = dict(result.get("primary_judgment") or {})
    primary.update(
        {
            "pattern": book["pattern"],
            "technical_pattern": book["technical_pattern"],
            "pattern_group": "standard_pattern",
            "source": book["method"],
            "is_broken": book["is_broken"],
        }
    )
    result.update(
        {
            "has_pattern_candidate": True,
            "has_pattern": True,
            "primary_pattern": book["pattern"],
            "technical_pattern": book["technical_pattern"],
            "primary_judgment": primary,
            "confidence": "medium" if book["status"] == "hold" else result.get("confidence", "high"),
            "book_pattern": book,
        }
    )
    return result
