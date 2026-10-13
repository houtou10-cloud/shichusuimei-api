"""Independent boundary and behavioral regressions for the reviewed B model."""
import json
import math
import os
import subprocess
import sys

import pytest

from scripts.symbol_judgment_b_model import DEFAULT_CONFIG, _relations, _symbol, evaluate

CHART = {"pillars": {"year": "甲辰", "month": "癸酉", "day": "丁亥", "hour": "乙巳"},
         "element_roles": {"useful": ["木"], "favorable": ["火", "水"], "unfavorable": ["土", "金"]}}


def row(result, kind, target=None):
    return next(r for r in result["evaluations"] if r["target_type"] == kind and (target is None or r["target"] == target))


@pytest.mark.parametrize("config", [[], {"weights": None}, {"weights": {"unknown": 1}},
    {"season_weight": True}, {"hidden_stem_weight": -1}, {"season_weight": math.nan},
    {"season_weight": math.inf}, {"season_weight": 1e308}, {"unknown": 1},
    {"thresholds": {"excellent": 0}}, {"period_branch_share": .9}, {"seasonal_strength_weight": 1}])
def test_invalid_configuration_returns_hold_without_exception(config):
    assert evaluate(CHART, config)["status"] == "hold"


@pytest.mark.parametrize("role", [None, "木", ["木", {}], [["木"]], 2])
def test_malformed_role_lists_return_hold(role):
    assert evaluate(dict(CHART, element_roles={"useful": role}))["status"] == "hold"


def test_unclassified_element_is_not_silently_unfavorable():
    result = evaluate(dict(CHART, element_roles={"useful": ["木"]}))
    metal = row(result, "five_element", "金")
    assert metal["status"] == "hold" and metal["symbol"] is None
    assert row(result, "five_element", "木")["status"] == "provisional"


def test_invalid_sexagenary_pair_is_rejected():
    assert evaluate(dict(CHART, annual="甲丑"))["status"] == "hold"


def test_same_period_stem_with_different_branch_changes_component_score():
    a = row(evaluate(dict(CHART, great_luck="甲寅")), "great_luck")
    b = row(evaluate(dict(CHART, great_luck="甲申")), "great_luck")
    assert sum(p["contribution"] for p in a["components"]) != sum(p["contribution"] for p in b["components"])
    assert sum(p["share"] for p in a["components"]) == pytest.approx(1)
    assert len(a["components"]) > 2


def test_hidden_stems_affect_branch_grade_and_are_traceable():
    result = evaluate(CHART)
    tiger = row(result, "branch", "寅")
    assert [p["element"] for p in tiger["components"]] == ["木", "火", "土"]
    assert [p["share"] for p in tiger["components"]] == [.6, .3, .1]
    assert "B.HIDDEN.001" in tiger["applied_rule_ids"]


def test_seasonal_weight_changes_distribution_and_inference_is_conservative():
    a = evaluate(CHART)
    b = evaluate(CHART, {"seasonal_strength_weight": 0})
    assert a["analysis"]["five_element_distribution"] != b["analysis"]["five_element_distribution"]
    assert a["analysis"]["seasonal_states"]["金"] == "旺"
    assert evaluate({"pillars": CHART["pillars"]})["status"] == "hold"


def test_deficient_unfavorable_element_does_not_receive_positive_balance_bonus():
    metal = row(evaluate(CHART), "five_element", "土")
    assert metal["components"][0]["balance"] <= 0


def test_clash_effect_depends_on_affected_element_instead_of_always_negative():
    useful = {"useful": ["火"], "favorable": [], "unfavorable": []}
    unfavorable = {"useful": [], "favorable": [], "unfavorable": ["火"]}
    a, _ = _relations(("甲", "子"), [("庚", "午")], DEFAULT_CONFIG["weights"], useful)
    b, _ = _relations(("甲", "子"), [("庚", "午")], DEFAULT_CONFIG["weights"], unfavorable)
    assert a < 0 < b


def test_identical_relationships_saturate_and_self_punishment_is_detected():
    score, relations = _relations(("甲", "辰"), [("甲", "辰"), ("甲", "辰")], DEFAULT_CONFIG["weights"], CHART["element_roles"])
    assert len(relations) == 1 and relations[0]["type"] == "自刑"
    assert score == relations[0]["effect"]


def test_standalone_stems_and_branches_receive_natal_interactions():
    result = evaluate(CHART)
    assert any(r["type"] == "干合" for r in row(result, "stem", "壬")["interactions"])
    assert any(r["type"] == "冲" for r in row(result, "branch", "卯")["interactions"])


def test_combined_period_score_does_not_add_individual_scores_and_duplicate_mutual_relation():
    result = evaluate(dict(CHART, great_luck="甲子", annual="庚午"))
    a, b, combined = row(result, "great_luck"), row(result, "annual"), row(result, "great_luck_annual")
    natal = list(result["normalized_input"]["pillars"].values())
    great = result["normalized_input"]["periods"]["great_luck"]
    annual = result["normalized_input"]["periods"]["annual"]
    isolated = sum(_relations(p, natal, DEFAULT_CONFIG["weights"], CHART["element_roles"])[0] for p in [great, annual]) / 2
    base = sum(sum(p["contribution"] for p in r["components"]) for r in [a, b]) / 2
    mutual = sum(r["effect"] for r in combined["interactions"])
    assert combined["score"] == pytest.approx(base + isolated + mutual)
    assert len([r for r in combined["interactions"] if r["type"] == "冲"]) == 1


@pytest.mark.parametrize("score,expected", [(3,"◎"),(2.999,"○"),(1,"○"),(.999,"△"),(-1.999,"△"),(-2,"×")])
def test_exact_symbol_thresholds(score, expected):
    assert _symbol(score, DEFAULT_CONFIG["thresholds"]) == expected


def test_all_applied_rule_ids_resolve_and_original_observations_remain_hold():
    result = evaluate(dict(CHART, great_luck="甲子", annual="庚午"))
    catalog = {r["rule_id"] for r in result["rule_catalog"]}
    assert all(set(r["applied_rule_ids"]) <= catalog for r in result["evaluations"])
    assert result["original_observations"]["comparison"] == "hold"


def test_cli_malformed_json_returns_machine_readable_hold():
    run = subprocess.run([sys.executable, "-m", "scripts.symbol_judgment_b_model", "-"], input="{", text=True, capture_output=True, encoding="utf-8")
    assert run.returncode == 2
    assert json.loads(run.stdout)["status"] == "hold"


def test_cli_accepts_windows_utf8_bom_file(tmp_path):
    path = tmp_path / "input.json"
    path.write_text(json.dumps(CHART, ensure_ascii=False), encoding="utf-8-sig")
    run = subprocess.run([sys.executable, "-m", "scripts.symbol_judgment_b_model", str(path)], text=True, capture_output=True, encoding="utf-8")
    assert run.returncode == 0
    assert json.loads(run.stdout)["revision"] == "b-review-2"


def test_cli_accepts_utf8_json_from_cp932_standard_streams():
    payload = "\ufeff" + json.dumps(CHART, ensure_ascii=False)
    env = {**os.environ, "PYTHONIOENCODING": "cp932"}
    run = subprocess.run(
        [sys.executable, "-m", "scripts.symbol_judgment_b_model", "-"],
        input=payload,
        text=True,
        capture_output=True,
        encoding="utf-8",
        env=env,
    )
    assert run.returncode == 0
    assert json.loads(run.stdout)["revision"] == "b-review-2"
