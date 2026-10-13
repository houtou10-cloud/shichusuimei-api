import json
import subprocess
import sys

from scripts.symbol_judgment_b_model import DEFAULT_CONFIG, evaluate, normalize_input


CHART = {"pillars": {"year": "甲辰", "month": "癸酉", "day": "丁亥", "hour": "乙巳"},
         "element_roles": {"useful": ["木"], "favorable": ["火", "水"], "unfavorable": ["土", "金"]}}


def rows(result, kind):
    return [r for r in result["evaluations"] if r["target_type"] == kind]


def test_invalid_missing_and_ganzhi_is_not_a_stem():
    assert normalize_input({})["status"] == "hold"
    bad = {"pillars": {"year": "己卯", "month": "癸酉", "day": "丁亥", "hour": "乙巳"}, "day_master": "己卯"}
    assert "invalid_day_master" in normalize_input(bad)["reasons"]


def test_all_four_boundaries_and_hold_outside_scale():
    result = evaluate(CHART, {"thresholds": {"excellent": 2, "favorable": 1, "unfavorable": -2}})
    assert {r["symbol"] for r in result["evaluations"]} == {"◎", "○", "△", "×"}
    hold = evaluate({"pillars": CHART["pillars"]})
    assert hold["status"] == "hold" and hold["symbol"] is None


def test_explicit_and_inferred_roles_are_distinct_and_strength_changes():
    explicit = evaluate(CHART)
    assert explicit["element_roles"]["method"] == "explicit"
    weak_chart = {"pillars": {"year": "庚申", "month": "辛酉", "day": "甲戌", "hour": "戊辰"}}
    inferred = evaluate(weak_chart)
    assert inferred["element_roles"]["method"] == "inferred_fuyoku_hypothesis"
    assert inferred["analysis"]["day_master_strength"] == "weak"


def test_combine_does_not_transform_and_relations_are_not_double_counted():
    data = dict(CHART, great_luck="甲子")
    result = evaluate(data)
    luck = rows(result, "great_luck")[0]
    assert all(x["transformation成立"] is False for x in luck["interactions"] if x["type"] in {"干合", "支合"})
    keys = [(x["type"], tuple(sorted(x["pair"]))) for x in luck["interactions"]]
    assert len(keys) == len(set(keys))


def test_conflicting_relations_and_great_luck_annual_combination():
    result = evaluate(dict(CHART, great_luck="甲子", annual="庚午"))
    luck, annual = rows(result, "great_luck")[0], rows(result, "annual")[0]
    assert any(x["type"] == "冲" for x in luck["interactions"])
    assert annual["interactions"] and luck["interactions"]


def test_order_determinism_and_weight_sensitivity():
    reversed_pillars = dict(reversed(list(CHART["pillars"].items())))
    a = evaluate(CHART)
    b = evaluate({"pillars": reversed_pillars, "element_roles": CHART["element_roles"]})
    assert a["evaluations"] == b["evaluations"]
    changed = evaluate(CHART, {"weights": {"useful": 5.0}})
    assert rows(changed, "five_element")[0]["score"] != rows(a, "five_element")[0]["score"]


def test_original_55_observations_remain_separate():
    result = evaluate(CHART)
    assert result["original_observations"] == {"count": 55, "comparison": "hold", "separated_from_model": True}


def test_cli_json_from_stdin():
    payload = json.dumps(dict(CHART, great_luck="甲子", annual="庚午"), ensure_ascii=False)
    run = subprocess.run(
        [sys.executable, "-m", "scripts.symbol_judgment_b_model", "-"],
        input=payload, capture_output=True, text=True, encoding="utf-8", check=True,
    )
    assert json.loads(run.stdout)["model_version"] == "yakumo-b-research-v1"
