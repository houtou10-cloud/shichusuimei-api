"""八雲式B範囲の独立研究モデル。

原典の記号再現ではなく、明示した仮定を決定的に適用する研究専用実装。
本番engine/APIからは呼び出さない。
"""
from __future__ import annotations

import argparse
import json
import math
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from engine.climate_useful_gods import evaluate_climate_useful_gods
from engine.constants import BRANCHES, HIDDEN_STEMS, STEMS
from engine.five_elements import get_branch_element, get_stem_element
from engine.seasonal_strength import SEASONAL_STATES
from engine.stem_transformation import evaluate_month_support

MODEL_VERSION = "yakumo-b-research-v1"
ELEMENTS = ("木", "火", "土", "金", "水")
GENERATES = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
CONTROLS = {"木": "土", "火": "金", "土": "水", "金": "木", "水": "火"}
STEM_COMBINES = {frozenset(x) for x in (("甲", "己"), ("乙", "庚"), ("丙", "辛"), ("丁", "壬"), ("戊", "癸"))}
STEM_TRANSFORMATION_ELEMENTS = {
    frozenset(("甲", "己")): "土", frozenset(("乙", "庚")): "金",
    frozenset(("丙", "辛")): "水", frozenset(("丁", "壬")): "木",
    frozenset(("戊", "癸")): "火",
}
BRANCH_COMBINES = {frozenset(x) for x in (("子", "丑"), ("寅", "亥"), ("卯", "戌"), ("辰", "酉"), ("巳", "申"), ("午", "未"))}
BRANCH_CLASHES = {frozenset(x) for x in (("子", "午"), ("丑", "未"), ("寅", "申"), ("卯", "酉"), ("辰", "戌"), ("巳", "亥"))}
BRANCH_PUNISHMENTS = {frozenset(x) for x in (("寅", "巳"), ("巳", "申"), ("申", "寅"), ("丑", "戌"), ("戌", "未"), ("未", "丑"), ("子", "卯"))}

DEFAULT_CONFIG = {
    "weights": {"useful": 2.0, "favorable": 1.0, "unfavorable": -2.0, "deficient": 0.75, "excess": -0.75,
                "stem_combine": 0.5, "branch_combine": 0.5, "clash": -1.0, "punishment": -0.75},
    "thresholds": {"excellent": 3.0, "favorable": 1.0, "unfavorable": -2.0},
    "season_weight": 1.5,
    "hidden_stem_weight": 0.5,
    "period_stem_share": 0.4,
    "period_branch_share": 0.6,
    "seasonal_strength_weight": 0.2,
    "climate_weight": 0.5,
}

RULE_CATALOG = [
    {"rule_id": "B.INPUT.001", "basis": "八雲式仮定", "condition": "四柱と対象の形式が妥当", "effect": "正規化", "priority": 100, "conflict": "不正ならhold", "constraints": "四柱欠落は非対応"},
    {"rule_id": "B.SPECIAL.001", "basis": "八雲式研究仮定", "condition": "特殊格局を明示し、類型別の純度条件を満たす", "effect": "特殊格局専用の喜忌を優先", "priority": 95, "priority_scope": "成立後の喜忌競合", "evaluation_phase": 30, "depends_on": ["B.TRANSFORM.001"], "conflict": "明示element_rolesより優先。日干合化と非化気格の併存、不成立・複数候補・未知類型は理由付きhold", "constraints": "従旺・従児・従財・従官殺・化気の限定実装。自動認定しない"},
    {"rule_id": "B.TRANSFORM.001", "basis": "既存合化候補規則＋八雲式研究仮定", "condition": "五合、化神が月令同気、通根、参加干以外への透干、争合なし", "effect": "参加二干の旧五行を除去後、化神五行へ置換", "priority": 90, "priority_scope": "五行分布確定", "evaluation_phase": 20, "depends_on": ["B.INPUT.001"], "conflict": "争合は全体hold。生月・透干不足は候補止まりで不適用", "constraints": "命式内天干のみ。支合化・期間干の合化は未対応"},
    {"rule_id": "B.CLIMATE.001", "basis": "既存climate_useful_gods_v1＋八雲式研究仮定", "condition": "月支から強い調候候補が得られる", "effect": "第一候補+0.5、第二候補+0.25を成分点へ加算", "priority": 85, "conflict": "特殊格局で忌神となる候補は特殊格局を優先し補正しない", "constraints": "日干別調候表ではなく月支中心の暫定判定"},
    {"rule_id": "B.BALANCE.001", "basis": "八雲式仮定", "condition": "天干・地支・蔵干・月令", "effect": "五行分布と日主強弱", "priority": 80, "conflict": "月令を加重", "constraints": "量的近似"},
    {"rule_id": "B.USEFUL.001", "basis": "八雲式仮定", "condition": "明示分類または扶抑法推定", "effect": "分類に基づく基礎点", "priority": 70, "conflict": "未分類要素・推定境界域はhold", "constraints": "特殊格局非対応"},
    {"rule_id": "B.RELATION.001", "basis": "八雲式仮定", "condition": "干合・支合・冲・刑・自刑", "effect": "相手の五行分類に応じ対象点を補正", "priority": 50, "conflict": "同一文字組・作用を一度だけ集計し、正負は加算", "constraints": "支合化は未判定。対象運干の合化は評価しない"},
    {"rule_id": "B.HIDDEN.001", "basis": "八雲式仮定", "condition": "地支・期間評価", "effect": "蔵干を1、7:3、6:3:1で配分", "priority": 60, "conflict": "総配分1。未分類が寄与する場合はhold", "constraints": "蔵干配分は独自仮定"},
    {"rule_id": "B.PERIOD.001", "basis": "八雲式仮定", "condition": "大運と流年が入力済み", "effect": "天干4割・地支蔵干6割。統合は期間基礎点と対命式作用の平均＋期間相互作用", "priority": 40, "conflict": "期間相互作用は流年から大運へ一度だけ", "constraints": "期間は同じ重み。期間算出・開始年齢は行わない"},
    {"rule_id": "B.SEASON.001", "basis": "八雲式仮定", "condition": "月支の旺相休囚死", "effect": "五行量に1.2/1.1/1/0.9/0.8を乗算", "priority": 80, "conflict": "未加重量を保持", "constraints": "季節係数は独自近似。土用は簡略化"},
    {"rule_id": "B.GRADE.001", "basis": "八雲式仮定", "condition": "解消不能競合なし", "effect": "点を◎○△×へ変換", "priority": 10, "conflict": "holdを記号で埋めない", "constraints": "鑑定精度を保証しない"},
]


def _hold(reasons: list[str], target: Any = None) -> dict[str, Any]:
    return {"status": "hold", "symbol": None, "target": target, "reasons": reasons, "model_version": MODEL_VERSION,
            "source_type": "yakumo_independent_hypothesis", "original_comparison": "hold"}


def _pillar(value: Any) -> tuple[str, str] | None:
    if isinstance(value, str) and len(value) == 2 and value[0] in STEMS and value[1] in BRANCHES:
        return (value[0], value[1]) if STEMS.index(value[0]) % 2 == BRANCHES.index(value[1]) % 2 else None
    if isinstance(value, Mapping) and value.get("stem") in STEMS and value.get("branch") in BRANCHES:
        return _pillar(value["stem"] + value["branch"])
    return None


def normalize_input(data: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(data, Mapping):
        return _hold(["input_not_object"])
    raw = data.get("chart", data.get("pillars"))
    if isinstance(raw, Mapping) and "pillars" in raw:
        raw = raw["pillars"]
    if not isinstance(raw, Mapping):
        return _hold(["missing_pillars"])
    pillars = {k: _pillar(raw.get(k)) for k in ("year", "month", "day", "hour")}
    bad = [k for k, value in pillars.items() if value is None]
    if bad:
        return _hold([f"invalid_or_missing_{k}_pillar" for k in bad])
    day_master = data.get("day_master", pillars["day"][0])
    if day_master not in STEMS:
        return _hold(["invalid_day_master"])
    if day_master != pillars["day"][0]:
        return _hold(["day_master_mismatch"])
    special_structure = data.get("special_structure")
    if special_structure is not None and not isinstance(special_structure, Mapping):
        return _hold(["invalid_special_structure"])
    periods: dict[str, tuple[str, str] | None] = {}
    for key in ("great_luck", "annual"):
        value = data.get(key)
        periods[key] = None if value is None else _pillar(value)
        if value is not None and periods[key] is None:
            return _hold([f"invalid_{key}_ganzhi"])
    return {"status": "ok", "pillars": pillars, "day_master": day_master, "periods": periods,
            "special_structure": dict(special_structure) if special_structure is not None else None}


def analyze_chart(normalized: Mapping[str, Any], config: Mapping[str, Any]) -> dict[str, Any]:
    counts = {e: 0.0 for e in ELEMENTS}
    for position, (stem, branch) in normalized["pillars"].items():
        counts[get_stem_element(stem)] += 1.0
        counts[get_branch_element(branch)] += config["season_weight"] if position == "month" else 1.0
        for hidden in HIDDEN_STEMS[branch]:
            counts[get_stem_element(hidden)] += config["hidden_stem_weight"]
    raw_counts = dict(counts)
    states = SEASONAL_STATES[normalized["pillars"]["month"][1]]
    scale = {"旺": 1, "相": 0.5, "休": 0, "囚": -0.5, "死": -1}
    factors = {e: 1 + config["seasonal_strength_weight"] * scale[states[e]] for e in ELEMENTS}
    counts = {e: counts[e] * factors[e] for e in ELEMENTS}
    dm = get_stem_element(normalized["day_master"])
    resource = next(e for e, generated in GENERATES.items() if generated == dm)
    support = counts[dm] + counts[resource]
    total = sum(counts.values())
    ratio = support / total
    raw_ratio = (raw_counts[dm] + raw_counts[resource]) / sum(raw_counts.values())
    def band(value: float) -> str:
        return "weak" if value < 0.38 else "strong" if value > 0.58 else "balanced"
    # 季節近似だけで境界を越える場合は推定を保留する。
    strength = band(ratio) if band(ratio) == band(raw_ratio) else "balanced"
    return {"five_element_distribution": counts, "unweighted_distribution": raw_counts,
            "seasonal_states": states, "seasonal_factors": factors, "day_master_element": dm, "resource_element": resource,
            "support_ratio": round(ratio, 6), "raw_support_ratio": round(raw_ratio, 6), "day_master_strength": strength,
            "directions": {e: _direction(dm, e) for e in ELEMENTS}}


def evaluate_natal_transformations(normalized: Mapping[str, Any]) -> dict[str, Any]:
    """命式内の天干五合を、成立・候補保留・不成立へ保守的に分ける。"""
    pillars = normalized["pillars"]
    positions = tuple(pillars)
    stems = {position: pillars[position][0] for position in positions}
    candidates: list[dict[str, Any]] = []
    participant_counts = {position: 0 for position in positions}
    for index, left in enumerate(positions):
        for right in positions[index + 1:]:
            pair = frozenset((stems[left], stems[right]))
            if pair in STEM_TRANSFORMATION_ELEMENTS:
                participant_counts[left] += 1
                participant_counts[right] += 1
                candidates.append({"positions": [left, right], "stems": [stems[left], stems[right]],
                                   "result_element": STEM_TRANSFORMATION_ELEMENTS[pair]})
    branches = {position: pillars[position][1] for position in positions}
    for candidate in candidates:
        left, right = candidate["positions"]
        result_element = candidate["result_element"]
        month_support = evaluate_month_support(result_element, branches["month"])
        roots = [position for position, branch in branches.items()
                 if any(get_stem_element(hidden) == result_element for hidden in HIDDEN_STEMS[branch])]
        exposures = [position for position, stem in stems.items()
                     if position not in {left, right} and get_stem_element(stem) == result_element]
        conflicts = [position for position in (left, right) if participant_counts[position] > 1]
        reasons: list[str] = []
        if conflicts:
            status = "hold"
            reasons.append("competing_stem_combination")
        elif month_support["support_level"] != "strong":
            status = "hold" if month_support["support_level"] == "supportive" else "unsupported"
            reasons.append("month_command_not_same_as_transformation_element")
        elif not roots:
            status = "hold"
            reasons.append("transformation_element_has_no_root")
        elif not exposures:
            status = "hold"
            reasons.append("transformation_element_not_exposed_outside_pair")
        else:
            status = "established"
            reasons.append("all_research_conditions_satisfied")
        candidate.update(status=status, reasons=reasons, month_support=month_support,
                         root_positions=roots, external_exposure_positions=exposures,
                         conflict_positions=conflicts, rule_id="B.TRANSFORM.001")
    return {"status": "evaluated", "candidates": candidates,
            "established_count": sum(item["status"] == "established" for item in candidates),
            "hold_count": sum(item["status"] == "hold" for item in candidates),
            "scope": "natal_heavenly_stems_only"}


def apply_established_transformations(analysis: dict[str, Any], transformations: Mapping[str, Any]) -> dict[str, Any]:
    """成立した合化だけを五行分布へ反映する。候補保留は動かさない。"""
    adjusted = deepcopy(analysis)
    counts = dict(adjusted["five_element_distribution"])
    applied: list[dict[str, Any]] = []
    accounting: list[dict[str, Any]] = []
    for candidate in transformations["candidates"]:
        if candidate["status"] != "established":
            continue
        removed = []
        for position, stem in zip(candidate["positions"], candidate["stems"]):
            original = get_stem_element(stem)
            amount = adjusted["seasonal_factors"][original]
            counts[original] = max(0.0, counts[original] - amount)
            removed.append({"position": position, "stem": stem, "element": original, "amount": amount})
        result = candidate["result_element"]
        added_amount = 2.0 * adjusted["seasonal_factors"][result]
        counts[result] += added_amount
        applied.append({"positions": candidate["positions"], "result_element": result})
        accounting.append({"positions": candidate["positions"], "removed": removed,
                           "added": {"element": result, "amount": added_amount},
                           "double_count_prevention": "remove_participant_stems_before_adding_transformation_element"})
    if not applied:
        adjusted["transformation_adjustments"] = []
        adjusted["transformation_accounting"] = []
        return adjusted
    adjusted["pre_transformation_distribution"] = adjusted["five_element_distribution"]
    adjusted["five_element_distribution"] = counts
    dm = adjusted["day_master_element"]
    resource = adjusted["resource_element"]
    ratio = (counts[dm] + counts[resource]) / sum(counts.values())
    adjusted["support_ratio"] = round(ratio, 6)
    adjusted["day_master_strength"] = "weak" if ratio < 0.38 else "strong" if ratio > 0.58 else "balanced"
    adjusted["transformation_adjustments"] = applied
    adjusted["transformation_accounting"] = accounting
    return adjusted


def evaluate_special_structure(normalized: Mapping[str, Any], analysis: Mapping[str, Any],
                               transformations: Mapping[str, Any]) -> dict[str, Any]:
    """明示された特殊格局だけを、公開した数値条件で判定する。"""
    raw = normalized.get("special_structure")
    if raw is None:
        return {"status": "not_requested", "type": None, "rule_id": "B.SPECIAL.001"}
    aliases = {"従旺格": "follow_strong", "従強格": "follow_strong", "従児格": "follow_output",
               "従財格": "follow_wealth", "従殺格": "follow_officer", "従官殺格": "follow_officer",
               "化気格": "transforming_qi"}
    kind = aliases.get(raw.get("type"), raw.get("type"))
    supported = {"follow_strong", "follow_output", "follow_wealth", "follow_officer", "transforming_qi"}
    if kind not in supported:
        return _hold(["unsupported_special_structure_type"], raw.get("type"))
    dm = analysis["day_master_element"]
    resource = analysis["resource_element"]
    output = GENERATES[dm]
    wealth = CONTROLS[dm]
    officer = next(element for element, controlled in CONTROLS.items() if controlled == dm)
    total = sum(analysis["five_element_distribution"].values())
    ratios = {element: analysis["five_element_distribution"][element] / total for element in ELEMENTS}
    expected = {"follow_strong": dm, "follow_output": output, "follow_wealth": wealth,
                "follow_officer": officer}.get(kind)
    evidence: dict[str, Any] = {"element_ratios": {k: round(v, 6) for k, v in ratios.items()},
                                "support_ratio": analysis["support_ratio"]}
    established_day_transformations = [item for item in transformations["candidates"]
                                       if item["status"] == "established" and "day" in item["positions"]]
    if kind != "transforming_qi" and established_day_transformations:
        return _hold(["non_transforming_special_structure_conflicts_with_day_stem_transformation"], kind)
    if kind == "transforming_qi":
        established = established_day_transformations
        if len(established) != 1:
            return _hold(["transforming_qi_requires_one_established_day_stem_transformation"], kind)
        expected = established[0]["result_element"]
        evidence["transformation"] = established[0]
        condition_met = ratios[expected] >= 0.50
        failure = "transforming_qi_element_below_0.50"
    elif kind == "follow_strong":
        condition_met = analysis["support_ratio"] >= 0.80 and ratios[dm] >= 0.40
        failure = "follow_strong_requires_support_0.80_and_day_element_0.40"
    else:
        condition_met = analysis["support_ratio"] <= 0.20 and ratios[expected] >= 0.50
        failure = f"{kind}_requires_support_at_most_0.20_and_dominant_element_0.50"
    declared = raw.get("element")
    if declared is not None and declared != expected:
        return _hold(["special_structure_element_mismatch"], kind)
    if not condition_met:
        return _hold([failure], kind)
    favorable = resource if kind == "follow_strong" else next(e for e, generated in GENERATES.items() if generated == expected)
    if kind in {"follow_output", "follow_wealth", "follow_officer"}:
        favorable = next((e for e in ELEMENTS if GENERATES[e] == expected), favorable)
    roles = {"useful": [expected], "favorable": [favorable],
             "unfavorable": [e for e in ELEMENTS if e not in {expected, favorable}]}
    return {"status": "established", "type": kind, "declared_type": raw.get("type"),
            "dominant_element": expected, "roles": roles, "evidence": evidence,
            "rule_id": "B.SPECIAL.001", "source_type": "yakumo_explicit_research_assumption"}


def _direction(dm: str, target: str) -> str:
    if target == dm: return "助"
    if GENERATES[target] == dm: return "生"
    if GENERATES[dm] == target: return "洩"
    if CONTROLS[dm] == target: return "耗"
    return "剋"


def classify_elements(data: Mapping[str, Any], analysis: Mapping[str, Any]) -> dict[str, Any]:
    explicit = data.get("element_roles")
    if explicit is not None:
        if not isinstance(explicit, Mapping): return _hold(["invalid_element_roles"])
        lists = [explicit.get(k, []) for k in ("useful", "favorable", "unfavorable")]
        if any(not isinstance(v, (list, tuple)) or any(not isinstance(x, str) for x in v) for v in lists):
            return _hold(["invalid_element_role_value"])
        useful, favorable, unfavorable = (set(v) for v in lists)
        if any(x not in ELEMENTS for x in useful | favorable | unfavorable): return _hold(["invalid_element_role_value"])
        if useful & favorable or useful & unfavorable or favorable & unfavorable: return _hold(["conflicting_element_roles"])
        return {"status": "ok", "method": "explicit", "useful": sorted(useful), "favorable": sorted(favorable), "unfavorable": sorted(unfavorable)}
    strength, dm, resource = analysis["day_master_strength"], analysis["day_master_element"], analysis["resource_element"]
    if strength == "balanced": return _hold(["unresolved_balanced_strength_useful_god"])
    output = GENERATES[dm]; wealth = CONTROLS[dm]; officer = next(e for e, controlled in CONTROLS.items() if controlled == dm)
    if strength == "weak": useful, favorable, unfavorable = {resource}, {dm}, {output, wealth, officer}
    else: useful, favorable, unfavorable = {officer}, {output, wealth}, {dm, resource}
    return {"status": "ok", "method": "inferred_fuyoku_hypothesis", "useful": sorted(useful), "favorable": sorted(favorable), "unfavorable": sorted(unfavorable)}


def _relations(target: tuple[str | None, str | None], others: list[tuple[str, str]], weights: Mapping[str, float], roles: Mapping[str, Any] | None = None) -> tuple[float, list[dict[str, Any]]]:
    score = 0.0; rows: list[dict[str, Any]] = []; seen: set[tuple[str, str, str]] = set()
    for stem, branch in others:
        candidates = []
        if frozenset((target[0], stem)) in STEM_COMBINES: candidates.append(("干合", weights["stem_combine"], target[0], stem))
        pair = frozenset((target[1], branch))
        if pair in BRANCH_COMBINES: candidates.append(("支合", weights["branch_combine"], target[1], branch))
        if pair in BRANCH_CLASHES: candidates.append(("冲", weights["clash"], target[1], branch))
        if pair in BRANCH_PUNISHMENTS: candidates.append(("刑", weights["punishment"], target[1], branch))
        if target[1] == branch and branch in {"辰", "午", "酉", "亥"}:
            candidates.append(("自刑", weights["punishment"], branch, branch))
        for kind, effect, left, right in candidates:
            key = (kind, *sorted((left, right)))
            if key in seen: continue
            seen.add(key)
            affected = get_stem_element(right) if kind == "干合" else get_branch_element(right)
            if roles:
                # 合は結び付き、冲・刑は揺らぎの仮説。相手の有利不利で方向を決める。
                direction = 1 if affected in roles["useful"] or affected in roles["favorable"] else -1 if affected in roles["unfavorable"] else 0
                effect *= direction
            score += effect
            rows.append({"type": kind, "pair": [left, right], "effect": effect, "affected_element": affected,
                         "transformation成立": False if kind in {"干合", "支合"} else None,
                         "transformation_status": "not_evaluated" if kind in {"干合", "支合"} else None,
                         "rule_id": "B.RELATION.001"})
    return score, rows


def _symbol(score: float, thresholds: Mapping[str, float]) -> str:
    if score >= thresholds["excellent"]: return "◎"
    if score >= thresholds["favorable"]: return "○"
    if score <= thresholds["unfavorable"]: return "×"
    return "△"


def evaluate(data: Mapping[str, Any], config: Mapping[str, Any] | None = None) -> dict[str, Any]:
    cfg = deepcopy(DEFAULT_CONFIG)
    if config is not None:
        if not isinstance(config, Mapping):
            return _hold(["invalid_config"])
        for section, values in config.items():
            if section in {"weights", "thresholds"}:
                if not isinstance(values, Mapping) or any(k not in cfg[section] for k in values):
                    return _hold(["invalid_config_section"])
                cfg[section].update(values)
            elif section in cfg: cfg[section] = values
            else: return _hold(["unknown_config_key"])
    numbers = list(cfg["weights"].values()) + list(cfg["thresholds"].values()) + [cfg[k] for k in ("season_weight", "hidden_stem_weight", "period_stem_share", "period_branch_share", "seasonal_strength_weight", "climate_weight")]
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in numbers):
        return _hold(["non_finite_or_non_numeric_config"])
    if any(abs(v) > 1_000_000 for v in numbers):
        return _hold(["config_magnitude_out_of_range"])
    if not cfg["thresholds"]["unfavorable"] < cfg["thresholds"]["favorable"] < cfg["thresholds"]["excellent"]:
        return _hold(["invalid_threshold_order"])
    if cfg["season_weight"] <= 0 or cfg["hidden_stem_weight"] < 0 or min(cfg["period_stem_share"], cfg["period_branch_share"]) < 0 or not math.isclose(cfg["period_stem_share"] + cfg["period_branch_share"], 1):
        return _hold(["invalid_weight_range"])
    if not 0 <= cfg["seasonal_strength_weight"] < 1:
        return _hold(["invalid_seasonal_strength_weight"])
    if cfg["climate_weight"] < 0:
        return _hold(["invalid_climate_weight"])
    normalized = normalize_input(data)
    if normalized["status"] == "hold": return normalized
    analysis = analyze_chart(normalized, cfg)
    transformations = evaluate_natal_transformations(normalized)
    analysis = apply_established_transformations(analysis, transformations)
    unresolved_transformation_conflicts = [
        item for item in transformations["candidates"]
        if "competing_stem_combination" in item["reasons"]
    ]
    if unresolved_transformation_conflicts:
        result = _hold(["unresolved_competing_stem_combination"])
        result.update({"analysis": analysis, "normalized_input": normalized,
                       "transformations": transformations, "hold_scope": "entire_model",
                       "hold_explanation": "争合で命式全体の合化後五行分布が一意に定まらず、全対象が同じ分布を共有するため"})
        return result
    climate = evaluate_climate_useful_gods(normalized["day_master"], normalized["pillars"]["month"][1])
    special_structure = evaluate_special_structure(normalized, analysis, transformations)
    if normalized.get("special_structure") is not None and special_structure["status"] != "established":
        special_structure.update({"analysis": analysis, "normalized_input": normalized,
                                  "transformations": transformations, "climate": climate})
        return special_structure
    if special_structure["status"] == "established":
        roles = {"status": "ok", "method": "explicit_special_structure_hypothesis",
                 **special_structure["roles"], "overrides_element_roles": "element_roles" in data}
    else:
        roles = classify_elements(data, analysis)
    if roles["status"] == "hold":
        roles.update({"analysis": analysis, "normalized_input": normalized}); return roles
    weights = cfg["weights"]; mean = sum(analysis["five_element_distribution"].values()) / 5
    natal = list(normalized["pillars"].values())
    targets: list[tuple[str, str, tuple[str, str] | None]] = []
    for e in ELEMENTS: targets.append(("five_element", e, None))
    for stem in STEMS: targets.append(("stem", stem, None))
    for branch in BRANCHES: targets.append(("branch", branch, None))
    for key in ("great_luck", "annual"):
        if normalized["periods"][key]: targets.append((key, "".join(normalized["periods"][key]), normalized["periods"][key]))
    def component(element: str, share: float) -> dict[str, Any]:
        if element in roles["useful"]: base, role = weights["useful"], "用神"
        elif element in roles["favorable"]: base, role = weights["favorable"], "喜神"
        elif element in roles["unfavorable"]: base, role = weights["unfavorable"], "忌神"
        else: return {"element": element, "share": share, "status": "hold", "reason": "unclassified_element", "base": 0.0, "balance": 0.0, "contribution": 0.0}
        # 不足は常に良いとは限らない。忌神の補充なら負方向へ補正する。
        delta = weights["deficient"] if analysis["five_element_distribution"][element] < mean - .5 else weights["excess"] if analysis["five_element_distribution"][element] > mean + .5 else 0.0
        balance = delta if base > 0 else -delta if base < 0 else 0.0
        climate_rank = climate["climate_elements"].index(element) if element in climate["climate_elements"] else None
        climate_adjustment = cfg["climate_weight"] if climate_rank == 0 else cfg["climate_weight"] / 2 if climate_rank == 1 else 0.0
        climate_conflict = special_structure["status"] == "established" and element in roles["unfavorable"] and climate_adjustment > 0
        if climate_conflict:
            climate_adjustment = 0.0
        return {"element": element, "share": share, "status": "provisional", "role": role,
                "base": base, "balance": balance, "climate_adjustment": climate_adjustment,
                "climate_conflict_suppressed": climate_conflict,
                "contribution": share * (base + balance + climate_adjustment)}
    def components(kind: str, value: str, pair: tuple[str, str] | None) -> list[dict[str, Any]]:
        if kind == "five_element": return [component(value, 1)]
        if kind == "stem": return [component(get_stem_element(value), 1)]
        branch = value if kind == "branch" else pair[1]
        hidden = HIDDEN_STEMS[branch]
        # 本気・中気・余気は位置に応じ6:3:1（2つなら7:3）、総量は1。
        shares = [1.0] if len(hidden) == 1 else [0.7, 0.3] if len(hidden) == 2 else [0.6, 0.3, 0.1]
        out = [] if kind == "branch" else [component(get_stem_element(pair[0]), cfg["period_stem_share"])]
        out.extend(component(get_stem_element(h), share * (1 if kind == "branch" else cfg["period_branch_share"])) for h, share in zip(hidden, shares))
        return out
    results = []
    for target_type, value, ganzhi in targets:
        element = value if target_type == "five_element" else get_stem_element(value) if target_type == "stem" else get_branch_element(value) if target_type == "branch" else get_stem_element(ganzhi[0])
        parts = components(target_type, value, ganzhi)
        if any(p["status"] == "hold" and p["share"] > 0 for p in parts):
            results.append(dict(_hold(["unclassified_element"], value), target_type=target_type, components=parts))
            continue
        role = "複合" if len(parts) > 1 else parts[0]["role"]
        base = sum(p["share"] * p.get("base", 0) for p in parts)
        balance = sum(p["share"] * p.get("balance", 0) for p in parts)
        relation_score, relations = (0.0, [])
        if ganzhi:
            others = natal + [p for k, p in normalized["periods"].items() if p and k != target_type]
            relation_score, relations = _relations(ganzhi, others, weights, roles)
        elif target_type in {"stem", "branch"}:
            relation_score, relations = _relations((value, None) if target_type == "stem" else (None, value), natal, weights, roles)
        climate_score = sum(p["share"] * p.get("climate_adjustment", 0) for p in parts)
        score = round(base + balance + climate_score + relation_score, 6)
        results.append({"target_type": target_type, "target": value, "symbol": _symbol(score, cfg["thresholds"]), "status": "provisional",
                        "score": score, "element": element, "role": role, "favorable_effects": [r for r in relations if r["effect"] > 0],
                        "components": parts,
                        "unfavorable_effects": [r for r in relations if r["effect"] < 0], "interactions": relations,
                        "reasons": [f"{role}:{base:+g}", f"balance:{balance:+g}", f"climate:{climate_score:+g}", f"relations:{relation_score:+g}"],
                        "applied_rule_ids": ["B.BALANCE.001", "B.SEASON.001", "B.USEFUL.001", "B.CLIMATE.001", "B.GRADE.001"] + (["B.SPECIAL.001"] if special_structure["status"] == "established" else []) + (["B.TRANSFORM.001"] if transformations["established_count"] else []) + (["B.RELATION.001"] if relations else []) + (["B.HIDDEN.001"] if target_type in {"branch", "great_luck", "annual"} else []) + (["B.PERIOD.001"] if ganzhi else [])})
    if all(normalized["periods"].values()):
        period_rows = [r for r in results if r["target_type"] in {"great_luck", "annual"}]
        combined = {"target_type": "great_luck_annual", "target": "大運＋流年", "components": period_rows,
                    "source_type": "yakumo_independent_hypothesis"}
        if any(r["status"] == "hold" for r in period_rows):
            combined.update(status="hold", symbol=None, reasons=["period_component_hold"])
        else:
            # 大運と流年の相互作用は一方向に一度。個別評価から取り除いて再集計。
            individual = [_relations(p, natal, weights, roles)[0] for p in normalized["periods"].values()]
            mutual_score, mutual = _relations(normalized["periods"]["annual"], [normalized["periods"]["great_luck"]], weights, roles)
            climate_score = sum(sum(p["share"] * p.get("climate_adjustment", 0) for p in r["components"])
                                for r in period_rows) / 2
            score = round(sum(sum(p["contribution"] for p in r["components"]) for r in period_rows) / 2 + sum(individual) / 2 + mutual_score, 6)
            combined.update(status="provisional", score=score, symbol=_symbol(score, cfg["thresholds"]),
                            interactions=mutual, climate_score=round(climate_score, 6),
                            reasons=["大運・流年の成分点（調候を含む）と対命式作用を各1/2で平均し、期間同士の作用を一度だけ加算"],
                            applied_rule_ids=["B.PERIOD.001", "B.CLIMATE.001", "B.RELATION.001", "B.GRADE.001"] + (["B.SPECIAL.001"] if special_structure["status"] == "established" else []) + (["B.TRANSFORM.001"] if transformations["established_count"] else []))
        results.append(combined)
    return {"status": "provisional", "model_version": MODEL_VERSION, "source_type": "yakumo_independent_hypothesis",
            "original_observations": {"count": 55, "comparison": "hold", "separated_from_model": True},
            "revision": "b-review-2", "normalized_input": normalized, "analysis": analysis, "element_roles": roles, "config": cfg,
            "transformations": transformations, "climate": climate, "special_structure": special_structure,
            "rule_catalog": RULE_CATALOG, "evaluations": results,
            "uncertainties": ["支合化・期間干合化は未対応", "日干別調候表は未対応", "特殊格局は明示入力された限定類型のみ", "科学的検証・鑑定精度保証なし"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="八雲式B範囲・研究用評価CLI")
    parser.add_argument("input", help="入力JSONファイル（- は標準入力）")
    parser.add_argument("--config", help="重み・閾値JSON")
    args = parser.parse_args(argv)
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8-sig")
    try:
        raw = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8-sig")
        data = json.loads(raw.lstrip("\ufeff"))
        config = json.loads(Path(args.config).read_text(encoding="utf-8-sig")) if args.config else None
        result = evaluate(data, config)
    except (OSError, UnicodeError, ValueError) as exc:
        result = _hold(["cli_input_error:" + type(exc).__name__])
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["status"] != "hold" else 2


if __name__ == "__main__":
    raise SystemExit(main())
