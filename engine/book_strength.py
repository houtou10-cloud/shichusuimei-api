"""『四柱推命 基礎』p.95〜103の身旺・身弱の計算法（本どおりモード）。

月令点＋五行点＋十二運星点の合計で判定する。
  +3以上 身旺 / 0〜+2 中和 / −1以下 身弱（p.101の判定法）

本から一意に決められない点は notes に書き、confidence を下げる。
engine/chart.py の rule_set="book_kiso" から使う。既定の計算には影響しない。
"""

from __future__ import annotations

from typing import Any

from engine.constants import BRANCHES, STEMS
from engine.twelve_stages import calculate_twelve_stage


STEM_ELEMENT = {"甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土", "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水"}
BRANCH_ELEMENT = {
    "子": "水", "丑": "土", "寅": "木", "卯": "木", "辰": "土", "巳": "火",
    "午": "火", "未": "土", "申": "金", "酉": "金", "戌": "土", "亥": "水",
}
GENERATES = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}

# 基礎編p.96 月令点（日干の五行 × 月支）
_MONTH_COMMAND_POINTS = {
    "木": {"寅": 3, "卯": 3, "辰": 2, "巳": 1, "午": 1, "未": 1, "申": 0, "酉": 0, "戌": 0, "亥": 1, "子": 1, "丑": 1},
    "火": {"寅": 1, "卯": 1, "辰": 1, "巳": 3, "午": 3, "未": 2, "申": 0, "酉": 0, "戌": 1, "亥": 0, "子": 0, "丑": 0},
    "土": {"寅": 0, "卯": 0, "辰": 2, "巳": 3, "午": 3, "未": 2, "申": 0, "酉": 0, "戌": 2, "亥": 0, "子": 0, "丑": 2},
    "金": {"寅": 0, "卯": 0, "辰": 0, "巳": 0, "午": 0, "未": 1, "申": 3, "酉": 3, "戌": 2, "亥": 1, "子": 1, "丑": 1},
    "水": {"寅": 1, "卯": 1, "辰": 1, "巳": 0, "午": 0, "未": 0, "申": 1, "酉": 1, "戌": 1, "亥": 3, "子": 3, "丑": 2},
}

# 基礎編p.100 十二運星点
_STAGE_POINTS = {"帝旺": 2, "建禄": 2, "長生": 1, "冠帯": 1}

# 基礎編p.103 三合・方合（その五行に+1、月支が旺支なら+2）
_TRINES = ((frozenset("申子辰"), "水"), (frozenset("亥卯未"), "木"), (frozenset("寅午戌"), "火"), (frozenset("巳酉丑"), "金"))
_DIRECTIONALS = ((frozenset("寅卯辰"), "木"), (frozenset("巳午未"), "火"), (frozenset("申酉戌"), "金"), (frozenset("亥子丑"), "水"))
_PEAK_BRANCHES = frozenset("子卯午酉")

# 空亡を解く関係（p.102）：支合・三合・方合・冲
_SIX_COMBINATIONS = (frozenset("子丑"), frozenset("寅亥"), frozenset("卯戌"), frozenset("辰酉"), frozenset("巳申"), frozenset("午未"))
_CLASHES = (frozenset("子午"), frozenset("丑未"), frozenset("寅申"), frozenset("卯酉"), frozenset("辰戌"), frozenset("巳亥"))

LABELS = {"strong": "身旺", "balanced": "中和", "weak": "身弱"}
_POSITION_JA = {"year": "年支", "month": "月支", "day": "日支", "hour": "時支"}

# 既存の下流処理は 0〜100 の点数を補助的に読むため、区分の代表値を入れる。
# 本の点数そのものは book_total_score に入れる。
REPRESENTATIVE_SCORE = {"strong": 64.0, "balanced": 50.0, "weak": 36.0}


def void_branches(day_stem: str, day_branch: str) -> tuple[str, str]:
    """日柱の旬から空亡の二支を求める（六十甲子表と空亡表、p.46・p.48）。"""
    s = STEMS.index(day_stem)
    b = BRANCHES.index(day_branch)
    head = (b - s) % 12
    return BRANCHES[(head + 10) % 12], BRANCHES[(head + 11) % 12]


def _forms_relation(branch: str, others: list[str]) -> bool:
    pool = set(others)
    for pair in _SIX_COMBINATIONS + _CLASHES:
        if branch in pair and (pair - {branch}) <= pool:
            return True
    for group, _ in _TRINES + _DIRECTIONALS:
        if branch in group and (group - {branch}) <= pool:
            return True
    return False


def calculate_book_strength(pillars: dict[str, Any]) -> dict[str, Any]:
    """pillars は engine.pillars.calculate_four_pillars の戻り値（時刻不明なら hour=None）。"""
    day_stem = pillars["day_master"]["stem"]
    day_element = STEM_ELEMENT[day_stem]
    positions = [p for p in ("year", "month", "day", "hour") if pillars.get(p)]
    stems = {p: pillars[p]["stem"] for p in positions}
    branches = {p: pillars[p]["branch"] for p in positions}
    notes: list[str] = []
    confidence = "high"
    if "hour" not in positions:
        notes.append("出生時刻不明のため、時柱を除く三柱で計算")
        confidence = "medium"

    # 空亡（年支・時支のみ。月支は空亡として扱わない。合・冲があれば解空）
    voids = void_branches(day_stem, branches["day"])
    void_positions = []
    for position in ("year", "hour"):
        branch = branches.get(position)
        if branch in voids:
            others = [branches[p] for p in positions if p != position]
            if _forms_relation(branch, others):
                notes.append(f"{_POSITION_JA[position]}の{branch}は空亡だが、合・冲があるため解空")
            else:
                void_positions.append(position)

    # 月令点
    month_command = _MONTH_COMMAND_POINTS[day_element][branches["month"]]

    # 五行点
    counts = {e: 0 for e in GENERATES}
    for p in positions:
        counts[STEM_ELEMENT[stems[p]]] += 1
        if p not in void_positions:
            counts[BRANCH_ELEMENT[branches[p]]] += 1
    combination_bonus = []
    present = {branches[p] for p in positions if p not in void_positions}
    for group, element in _TRINES + _DIRECTIONALS:
        if group <= present:
            bonus = 2 if branches["month"] in group and branches["month"] in _PEAK_BRANCHES else 1
            counts[element] += bonus
            combination_bonus.append({"branches": "".join(b for b in BRANCHES if b in group), "element": element, "bonus": bonus})
    resource = next(e for e, g in GENERATES.items() if g == day_element)
    output = GENERATES[day_element]
    wealth = GENERATES[output]
    officer = GENERATES[wealth]
    plus = counts[day_element] + counts[resource]
    minus = counts[output] + counts[wealth] + counts[officer]
    five_element = plus - minus

    # 十二運星点（月柱・日柱・時柱。年柱は数えない。空亡の支は数えない）
    stages = {}
    for p in ("month", "day", "hour"):
        if p in positions and p not in void_positions:
            stages[p] = calculate_twelve_stage(day_stem, branches[p])
    peak_count = sum(1 for s in stages.values() if s in ("帝旺", "建禄"))
    stage_points = 3 if peak_count >= 2 else max((_STAGE_POINTS.get(s, 0) for s in stages.values()), default=0)

    # 丑・辰は壬・癸の日干の根になる（p.95）。加味の方法は本に示されていない。
    if day_stem in ("壬", "癸") and any(branches[p] in ("丑", "辰") for p in positions):
        notes.append("p.95：丑・辰は壬・癸の根となるが、加味の方法が本に示されていないため点数に反映していない")
        confidence = "medium"

    total = month_command + five_element + stage_points
    technical = "strong" if total >= 3 else "balanced" if total >= 0 else "weak"
    return {
        "method": "book_kiso_p95_103",
        "month_command_points": month_command,
        "five_element_points": five_element,
        "five_element_counts": counts,
        "combination_bonus": combination_bonus,
        "twelve_stage_points": stage_points,
        "twelve_stages_counted": stages,
        "void_branches": list(voids),
        "void_positions": void_positions,
        "book_total_score": total,
        "technical_label": technical,
        "label": LABELS[technical],
        "confidence": confidence,
        "notes": notes,
    }


def to_final_strength_judgment(book: dict[str, Any], engine_judgment: dict[str, Any] | None = None) -> dict[str, Any]:
    """既存の final_strength_judgment の構造（components・uncertainty など）を保ち、
    判定（label・technical_label・final_score・confidence）を本の結果で置き換える。"""
    technical = book["technical_label"]
    score = REPRESENTATIVE_SCORE[technical]
    result = dict(engine_judgment or {})
    if engine_judgment:
        result["engine_v1_judgment"] = {
            k: engine_judgment.get(k) for k in ("final_score", "technical_label", "label", "confidence")
        }
    result.update({
        "final_score": score,
        "raw_final_score": score,
        "score_scale": "book_kiso_label_representative",
        "book_total_score": book["book_total_score"],
        "technical_label": technical,
        "label": book["label"],
        "confidence": book["confidence"],
        "book_method": book["method"],
        "book_strength": book,
    })
    return result
