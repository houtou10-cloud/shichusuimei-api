"""End-to-end CLI scenarios made only from synthetic research charts.

These cases are not observations or fixtures transcribed from a source text.
"""

import json
import subprocess
import sys

import pytest


NORMAL = {
    "pillars": {"year": "甲辰", "month": "癸酉", "day": "丁亥", "hour": "乙巳"},
    "element_roles": {"useful": ["木"], "favorable": ["火", "水"], "unfavorable": ["土", "金"]},
}

SYNTHETIC_CASES = {
    "normal": NORMAL,
    "strong": {"pillars": {"year": "甲寅", "month": "乙卯", "day": "甲寅", "hour": "癸亥"}},
    "weak": {"pillars": {"year": "庚申", "month": "辛酉", "day": "甲戌", "hour": "戊辰"}},
    "transformation_established": {
        "pillars": {"year": "甲辰", "month": "己未", "day": "戊戌", "hour": "丙辰"},
        "element_roles": {"useful": ["土"], "favorable": ["火"], "unfavorable": ["木", "金", "水"]},
    },
    "transformation_unsupported": {
        "pillars": {"year": "甲辰", "month": "癸酉", "day": "己丑", "hour": "丙寅"},
        "element_roles": {"useful": ["土"], "favorable": ["火"], "unfavorable": ["木", "金", "水"]},
    },
    "explicit_special": {
        "pillars": {"year": "丙午", "month": "丁巳", "day": "甲午", "hour": "丙午"},
        "special_structure": {"type": "従児格"},
    },
    "great_luck_and_annual": {**NORMAL, "great_luck": "壬子", "annual": "癸亥"},
    "competing_hold": {
        "pillars": {"year": "甲辰", "month": "己未", "day": "甲子", "hour": "戊辰"},
        "element_roles": {"useful": ["土"], "favorable": ["火"], "unfavorable": ["木", "金", "水"]},
    },
}


def run_cli(payload):
    run = subprocess.run(
        [sys.executable, "-m", "scripts.symbol_judgment_b_model", "-"],
        input=json.dumps(payload, ensure_ascii=False),
        text=True,
        capture_output=True,
        encoding="utf-8",
    )
    return run, json.loads(run.stdout)


def assert_complete_provisional_contract(result):
    catalog = {item["rule_id"] for item in result["rule_catalog"]}
    assert result["status"] == "provisional"
    assert result["source_type"] == "yakumo_independent_hypothesis"
    assert result["original_observations"]["comparison"] == "hold"
    assert result["evaluations"]
    for item in result["evaluations"]:
        assert item["status"] in {"provisional", "hold"}
        assert item.get("reasons")
        if item["status"] == "provisional":
            assert item["symbol"] in {"◎", "○", "△", "×"}
            assert item["applied_rule_ids"]
            assert set(item["applied_rule_ids"]) <= catalog
        else:
            assert item["symbol"] is None


@pytest.mark.parametrize("name", [
    "normal", "strong", "weak", "transformation_established",
    "transformation_unsupported", "explicit_special", "great_luck_and_annual",
])
def test_cli_synthetic_success_scenarios_have_consistent_contract(name):
    run, result = run_cli(SYNTHETIC_CASES[name])
    assert run.returncode == 0
    assert run.stderr == ""
    assert_complete_provisional_contract(result)


def test_cli_strong_and_weak_inference_are_distinct():
    _, strong = run_cli(SYNTHETIC_CASES["strong"])
    _, weak = run_cli(SYNTHETIC_CASES["weak"])
    assert strong["analysis"]["day_master_strength"] == "strong"
    assert weak["analysis"]["day_master_strength"] == "weak"
    assert strong["element_roles"]["method"] == weak["element_roles"]["method"] == "inferred_fuyoku_hypothesis"


def test_cli_transformation_established_and_unsupported_are_distinct():
    _, established = run_cli(SYNTHETIC_CASES["transformation_established"])
    _, unsupported = run_cli(SYNTHETIC_CASES["transformation_unsupported"])
    candidate = established["transformations"]["candidates"][0]
    rejected = unsupported["transformations"]["candidates"][0]
    assert candidate["status"] == "established"
    assert candidate["reasons"] == ["all_research_conditions_satisfied"]
    assert established["analysis"]["transformation_accounting"]
    assert all("B.TRANSFORM.001" in item["applied_rule_ids"] for item in established["evaluations"])
    assert rejected["status"] == "unsupported"
    assert rejected["reasons"] == ["month_command_not_same_as_transformation_element"]
    assert unsupported["analysis"]["transformation_adjustments"] == []
    assert all("B.TRANSFORM.001" not in item["applied_rule_ids"] for item in unsupported["evaluations"])


def test_cli_explicit_special_structure_reports_assumption_and_priority():
    _, result = run_cli(SYNTHETIC_CASES["explicit_special"])
    special = result["special_structure"]
    assert special["status"] == "established"
    assert special["type"] == "follow_output"
    assert special["source_type"] == "yakumo_explicit_research_assumption"
    assert result["element_roles"]["method"] == "explicit_special_structure_hypothesis"
    assert all("B.SPECIAL.001" in item["applied_rule_ids"] for item in result["evaluations"])


def test_cli_period_combination_has_one_traceable_combined_result():
    _, result = run_cli(SYNTHETIC_CASES["great_luck_and_annual"])
    combined = [item for item in result["evaluations"] if item["target_type"] == "great_luck_annual"]
    assert len(combined) == 1
    assert combined[0]["symbol"] in {"◎", "○", "△", "×"}
    assert combined[0]["reasons"] == [
        "大運・流年の成分点（調候を含む）と対命式作用を各1/2で平均し、期間同士の作用を一度だけ加算"
    ]
    assert combined[0]["applied_rule_ids"].count("B.PERIOD.001") == 1
    assert combined[0]["applied_rule_ids"].count("B.CLIMATE.001") == 1


def test_cli_competing_combination_is_machine_readable_global_hold():
    run, result = run_cli(SYNTHETIC_CASES["competing_hold"])
    assert run.returncode == 2
    assert run.stderr == ""
    assert result["status"] == "hold"
    assert result["symbol"] is None
    assert result["reasons"] == ["unresolved_competing_stem_combination"]
    assert result["hold_scope"] == "entire_model"
    assert "全対象" in result["hold_explanation"]
    assert "evaluations" not in result
