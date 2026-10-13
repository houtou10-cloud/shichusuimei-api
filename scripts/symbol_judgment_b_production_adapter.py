"""本番計算結果をB研究モデルへ接続する、未組み込みの読み取り専用境界。

本番engine/API/Webからは呼び出さない。入力をdeepcopyして保持し、変換不能・
評価例外・機能無効を正常な評価記号へ変換しない。
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, Mapping

from engine.constants import BRANCHES, STEMS
from scripts.symbol_judgment_b_model import ELEMENTS, MODEL_VERSION, RULE_CATALOG, evaluate

ADAPTER_VERSION = "b_production_readonly_adapter_v1"
DISPLAY_NAME = "八雲式・参考評価"

REASON_JA = {
    "adapter_input_not_mapping": "本番計算結果が辞書形式ではありません。",
    "missing_chart": "命式データがありません。",
    "missing_useful_gods": "通常の喜忌分類がありません。",
    "invalid_useful_gods": "通常の喜忌分類の形式が不正です。",
    "missing_current_luck": "現在大運データがありません。",
    "missing_annual_luck": "流年データがありません。",
    "unclassified_element": "本番データに対象五行の喜忌分類がないため判定を保留しました。",
    "period_component_hold": "大運または流年に未分類要素があるため統合判定を保留しました。",
    "unresolved_competing_stem_combination": "争合により合化後の五行分布を一意に決められません。",
    "feature_disabled": "研究機能が無効です。Bモデルは実行していません。",
}


def _hold(*reasons: str, evidence: Any = None) -> dict[str, Any]:
    return {"status": "hold", "symbol": None, "reasons": list(reasons),
            "adapter": ADAPTER_VERSION, "evidence": evidence}


def _unwrap_engine_result(value: Mapping[str, Any]) -> Mapping[str, Any]:
    if isinstance(value.get("chart"), Mapping):
        return value
    wrapped = value.get("result")
    if isinstance(wrapped, Mapping) and isinstance(wrapped.get("chart"), Mapping):
        return wrapped
    return value


def _ganzhi_from_parts(value: Any, path: str) -> tuple[str | None, str | None]:
    if not isinstance(value, Mapping):
        return None, f"{path}_not_mapping"
    stem, branch = value.get("stem"), value.get("branch")
    if stem not in STEMS:
        return None, f"{path}_invalid_or_missing_stem"
    if branch not in BRANCHES:
        return None, f"{path}_invalid_or_missing_branch"
    combined = stem + branch
    for key in ("ganzhi", "pillar"):
        declared = value.get(key)
        if declared is not None and declared != combined:
            return None, f"{path}_{key}_mismatch"
    return combined, None


def _extract_roles(engine_result: Mapping[str, Any]) -> tuple[dict[str, list[str]] | None, str | None]:
    useful = engine_result.get("useful_gods")
    if not isinstance(useful, Mapping):
        return None, "missing_useful_gods"
    primary = useful.get("primary_useful_element")
    secondaries = useful.get("secondary_useful_elements")
    support_balance = useful.get("support_balance")
    unfavorable = support_balance.get("unfavorable_elements") if isinstance(support_balance, Mapping) else None
    if primary not in ELEMENTS or not isinstance(secondaries, list) or not isinstance(unfavorable, list):
        return None, "invalid_useful_gods"
    if any(item not in ELEMENTS for item in secondaries + unfavorable):
        return None, "invalid_useful_gods"
    roles = {"useful": [primary], "favorable": list(dict.fromkeys(secondaries)),
             "unfavorable": list(dict.fromkeys(unfavorable))}
    sets = [set(roles[key]) for key in ("useful", "favorable", "unfavorable")]
    if sets[0] & sets[1] or sets[0] & sets[2] or sets[1] & sets[2]:
        return None, "conflicting_production_element_roles"
    return roles, None


def adapt_production_result(
    production_result: Mapping[str, Any], *, include_periods: bool = True,
    explicit_special_structure: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """本番計算結果を変更せずBモデル入力へ変換する。"""
    if not isinstance(production_result, Mapping):
        return _hold("adapter_input_not_mapping")
    source = _unwrap_engine_result(production_result)
    chart = source.get("chart")
    if not isinstance(chart, Mapping):
        return _hold("missing_chart")
    pillars: dict[str, str] = {}
    for position in ("year", "month", "day", "hour"):
        ganzhi, error = _ganzhi_from_parts(chart.get(position), f"chart_{position}")
        if error:
            return _hold(error, evidence={"path": f"chart.{position}"})
        pillars[position] = ganzhi
    day_master = source.get("day_master")
    if day_master is not None:
        if not isinstance(day_master, Mapping) or day_master.get("stem") not in STEMS:
            return _hold("invalid_day_master", evidence={"path": "day_master.stem"})
        if day_master["stem"] != pillars["day"][0]:
            return _hold("day_master_mismatch", evidence={"path": "day_master.stem"})
    roles, error = _extract_roles(source)
    if error:
        return _hold(error, evidence={"path": "useful_gods"})
    b_input: dict[str, Any] = {"pillars": pillars, "element_roles": roles}
    if explicit_special_structure is not None:
        if not isinstance(explicit_special_structure, Mapping):
            return _hold("invalid_explicit_special_structure")
        b_input["special_structure"] = deepcopy(dict(explicit_special_structure))
    if include_periods:
        current = source.get("current_luck")
        if not isinstance(current, Mapping):
            return _hold("missing_current_luck", evidence={"path": "current_luck"})
        has_current = current.get("has_current_luck")
        if has_current is True:
            ganzhi, error = _ganzhi_from_parts(current.get("current_luck_pillar"), "current_luck_pillar")
            if error:
                return _hold(error, evidence={"path": "current_luck.current_luck_pillar"})
            b_input["great_luck"] = ganzhi
        elif has_current is not False:
            return _hold("invalid_has_current_luck", evidence={"path": "current_luck.has_current_luck"})
        annual = source.get("annual_luck")
        if not isinstance(annual, Mapping):
            return _hold("missing_annual_luck", evidence={"path": "annual_luck"})
        ganzhi, error = _ganzhi_from_parts(annual, "annual_luck")
        if error:
            return _hold(error, evidence={"path": "annual_luck"})
        b_input["annual"] = ganzhi
    return {"status": "ok", "adapter": ADAPTER_VERSION, "input": b_input,
            "source_contract": "calculate_chart_result", "source_mutated": False,
            "special_structure_source": "explicit_caller_input" if explicit_special_structure is not None else "not_supplied"}


def _reason_text(reasons: Any) -> str:
    if not isinstance(reasons, list) or not reasons:
        return "理由を確定できないため判定を保留しました。"
    rendered = []
    for reason in reasons:
        value = str(reason)
        if value.startswith("b_research_boundary_exception:"):
            rendered.append("B研究モデルの評価処理で例外が発生しました（" + value.split(":", 1)[1] + "）。")
        else:
            rendered.append(REASON_JA.get(value, value))
    return " / ".join(rendered)


def build_reference_display(model_result: Mapping[str, Any]) -> dict[str, Any]:
    """Bモデル結果を顧客助言ではない研究用表示データへ変換する。"""
    status = model_result.get("status")
    if status in {"disabled", "error"} or status == "hold" and "evaluations" not in model_result:
        reasons = model_result.get("reasons", ["feature_disabled"] if status == "disabled" else [])
        global_catalog = {item["rule_id"]: item for item in RULE_CATALOG}
        rules = ["B.TRANSFORM.001"] if "unresolved_competing_stem_combination" in reasons else []
        assumptions = [{"rule_id": rule, "basis": global_catalog[rule].get("basis")} for rule in rules]
        return {"display_name": DISPLAY_NAME, "status": status, "items": [{
            "symbol": None, "display_symbol": "判定保留", "target": "全体",
            "reason": _reason_text(reasons), "applied_rules": rules, "assumptions": assumptions,
        }], "model_version": model_result.get("model_version", MODEL_VERSION),
            "uncertainties": list(model_result.get("uncertainties", [])),
            "notice": "研究用の参考評価です。記号だけで転職・投資その他の意思決定を勧めません。"}
    catalog = {item["rule_id"]: item for item in model_result.get("rule_catalog", []) if isinstance(item, Mapping)}
    items = []
    for row in model_result.get("evaluations", []):
        if not isinstance(row, Mapping):
            continue
        rules = list(row.get("applied_rule_ids", []))
        assumptions = [{"rule_id": rule, "basis": catalog[rule].get("basis")}
                       for rule in rules if rule in catalog]
        symbol = row.get("symbol") if row.get("status") != "hold" else None
        items.append({"symbol": symbol, "display_symbol": symbol or "判定保留",
                      "target": row.get("target"), "target_type": row.get("target_type"),
                      "reason": _reason_text(row.get("reasons")), "applied_rules": rules,
                      "assumptions": assumptions})
    return {"display_name": DISPLAY_NAME, "status": status, "items": items,
            "model_version": model_result.get("model_version", MODEL_VERSION),
            "uncertainties": list(model_result.get("uncertainties", [])),
            "notice": "研究用の参考評価です。記号だけで転職・投資その他の意思決定を勧めません。"}


def run_reference_evaluation(
    production_result: Any, *, enabled: bool = False, include_periods: bool = True,
    explicit_special_structure: Mapping[str, Any] | None = None,
    evaluator: Callable[[Mapping[str, Any]], Mapping[str, Any]] = evaluate,
) -> dict[str, Any]:
    """feature flag、変換、評価、表示を一つの研究用境界で安全に実行する。"""
    original = deepcopy(production_result)
    if not enabled:
        disabled = {"status": "disabled", "symbol": None, "reasons": ["feature_disabled"],
                    "model_version": MODEL_VERSION}
        return {"status": "disabled", "enabled": False, "adapter": ADAPTER_VERSION,
                "original_data": original, "adapter_result": None, "model_result": disabled,
                "display": build_reference_display(disabled)}
    try:
        adapted = adapt_production_result(production_result, include_periods=include_periods,
                                          explicit_special_structure=explicit_special_structure)
        if adapted["status"] == "hold":
            return {"status": "hold", "enabled": True, "adapter": ADAPTER_VERSION,
                    "original_data": original, "adapter_result": adapted, "model_result": None,
                    "display": build_reference_display(adapted)}
        model_result = dict(evaluator(deepcopy(adapted["input"])))
        boundary_status = "success" if model_result.get("status") != "hold" else "hold"
        return {"status": boundary_status, "enabled": True, "adapter": ADAPTER_VERSION,
                "original_data": original, "adapter_result": adapted, "model_result": model_result,
                "display": build_reference_display(model_result)}
    except Exception as exc:  # 研究境界で本番データを保護し、記号で隠さない。
        failure = {"status": "error", "symbol": None,
                   "reasons": [f"b_research_boundary_exception:{type(exc).__name__}"],
                   "model_version": MODEL_VERSION, "uncertainties": ["Bモデル評価処理に失敗"]}
        return {"status": "error", "enabled": True, "adapter": ADAPTER_VERSION,
                "original_data": original, "adapter_result": None, "model_result": failure,
                "error": {"type": type(exc).__name__, "message": str(exc)},
                "display": build_reference_display(failure)}


__all__ = ["ADAPTER_VERSION", "DISPLAY_NAME", "adapt_production_result",
           "build_reference_display", "run_reference_evaluation"]
