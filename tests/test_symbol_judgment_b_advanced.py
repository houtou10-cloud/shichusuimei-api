"""Research regressions for B-model transformation, climate and special structures."""

import pytest

from scripts.symbol_judgment_b_model import evaluate, evaluate_special_structure


BASE = {
    "pillars": {"year": "甲辰", "month": "癸酉", "day": "丁亥", "hour": "乙巳"},
    "element_roles": {"useful": ["木"], "favorable": ["火", "水"], "unfavorable": ["土", "金"]},
}


def row(result, kind, target):
    return next(item for item in result["evaluations"]
                if item["target_type"] == kind and item["target"] == target)


def test_natal_transformation_requires_month_root_exposure_and_no_competition():
    chart = {
        "pillars": {"year": "甲辰", "month": "己未", "day": "戊戌", "hour": "丙辰"},
        "element_roles": {"useful": ["土"], "favorable": ["火"], "unfavorable": ["木", "金", "水"]},
    }
    result = evaluate(chart)
    candidate = result["transformations"]["candidates"][0]
    assert candidate["status"] == "established"
    assert candidate["result_element"] == "土"
    assert candidate["root_positions"]
    assert candidate["external_exposure_positions"] == ["day"]
    assert result["analysis"]["transformation_adjustments"] == [
        {"positions": ["year", "month"], "result_element": "土"}
    ]


def test_competing_stem_combinations_are_held_and_not_applied():
    chart = {
        "pillars": {"year": "甲辰", "month": "己未", "day": "甲子", "hour": "戊辰"},
        "element_roles": {"useful": ["土"], "favorable": ["火"], "unfavorable": ["木", "金", "水"]},
    }
    result = evaluate(chart)
    candidates = result["transformations"]["candidates"]
    assert result["status"] == "hold"
    assert result["symbol"] is None
    assert result["reasons"] == ["unresolved_competing_stem_combination"]
    assert len(candidates) == 2
    assert all(item["status"] == "hold" for item in candidates)
    assert all("competing_stem_combination" in item["reasons"] for item in candidates)
    assert result["analysis"]["transformation_adjustments"] == []


def test_climate_reuses_month_branch_candidate_and_adds_bounded_score():
    with_climate = evaluate(BASE)
    without_climate = evaluate(BASE, {"climate_weight": 0})
    assert with_climate["climate"]["method"] == "climate_useful_gods_v1"
    assert with_climate["climate"]["primary_climate_element"] == "水"
    assert row(with_climate, "five_element", "水")["score"] == (
        row(without_climate, "five_element", "水")["score"] + 0.5
    )
    assert "B.CLIMATE.001" in row(with_climate, "five_element", "水")["applied_rule_ids"]


def test_explicit_follow_output_structure_overrides_conflicting_normal_roles():
    chart = {
        "pillars": {"year": "丙午", "month": "丁巳", "day": "甲午", "hour": "丙午"},
        "special_structure": {"type": "従児格"},
        "element_roles": {"useful": ["水"], "favorable": ["木"], "unfavorable": ["火", "土", "金"]},
    }
    result = evaluate(chart)
    assert result["special_structure"]["status"] == "established"
    assert result["special_structure"]["type"] == "follow_output"
    assert result["element_roles"]["method"] == "explicit_special_structure_hypothesis"
    assert result["element_roles"]["useful"] == ["火"]
    assert result["element_roles"]["overrides_element_roles"] is True


def test_special_structure_failure_and_unknown_type_are_reasoned_holds():
    unmet = evaluate({**BASE, "special_structure": {"type": "従旺格"}})
    unknown = evaluate({**BASE, "special_structure": {"type": "unknown"}})
    assert unmet["status"] == "hold"
    assert unmet["symbol"] is None
    assert unmet["reasons"] == ["follow_strong_requires_support_0.80_and_day_element_0.40"]
    assert unknown["status"] == "hold"
    assert unknown["reasons"] == ["unsupported_special_structure_type"]


def test_scope_and_priority_are_machine_readable():
    result = evaluate(BASE)
    catalog = {item["rule_id"]: item for item in result["rule_catalog"]}
    assert catalog["B.SPECIAL.001"]["priority"] > catalog["B.TRANSFORM.001"]["priority"]
    assert catalog["B.TRANSFORM.001"]["priority"] > catalog["B.CLIMATE.001"]["priority"]
    assert "期間干" in catalog["B.TRANSFORM.001"]["constraints"]
    assert "日干別調候表" in catalog["B.CLIMATE.001"]["constraints"]


def test_transformation_accounting_removes_old_elements_before_adding_result():
    chart = {
        "pillars": {"year": "甲辰", "month": "己未", "day": "戊戌", "hour": "丙辰"},
        "element_roles": {"useful": ["土"], "favorable": ["火"], "unfavorable": ["木", "金", "水"]},
    }
    analysis = evaluate(chart)["analysis"]
    pre = analysis["pre_transformation_distribution"]
    post = analysis["five_element_distribution"]
    accounting = analysis["transformation_accounting"][0]
    expected = dict(pre)
    for item in accounting["removed"]:
        expected[item["element"]] -= item["amount"]
    expected[accounting["added"]["element"]] += accounting["added"]["amount"]
    assert post == pytest.approx(expected)
    assert accounting["double_count_prevention"].startswith("remove_participant_stems")


def _analysis(distribution, support_ratio, day_master="木", resource="水"):
    return {"five_element_distribution": distribution, "support_ratio": support_ratio,
            "day_master_element": day_master, "resource_element": resource}


def _special(kind, analysis, transformations=None):
    normalized = {"special_structure": {"type": kind}}
    transformations = transformations or {"candidates": []}
    return evaluate_special_structure(normalized, analysis, transformations)


def test_follow_strong_accepts_exact_thresholds_and_rejects_each_lower_boundary():
    exact = _analysis({"木": .4, "火": .1, "土": .05, "金": .05, "水": .4}, .8)
    assert _special("follow_strong", exact)["status"] == "established"
    below_support = _analysis(exact["five_element_distribution"], .799999)
    below_day = _analysis({"木": .399999, "火": .100001, "土": .05, "金": .05, "水": .4}, .8)
    assert _special("follow_strong", below_support)["status"] == "hold"
    assert _special("follow_strong", below_day)["status"] == "hold"


@pytest.mark.parametrize("kind,target", [
    ("follow_output", "火"), ("follow_wealth", "土"), ("follow_officer", "金"),
])
def test_follow_types_accept_exact_thresholds_and_reject_both_sides(kind, target):
    distribution = {"木": .125, "火": .125, "土": .125, "金": .125, "水": .125}
    distribution[target] = .5
    exact = _analysis(distribution, .2)
    assert _special(kind, exact)["status"] == "established"
    assert _special(kind, _analysis(distribution, .200001))["status"] == "hold"
    below_target = dict(distribution)
    below_target[target] = .499999
    below_target["水" if target != "水" else "木"] += .000001
    assert _special(kind, _analysis(below_target, .2))["status"] == "hold"


def test_transforming_qi_uses_post_transformation_distribution_and_exact_ratio():
    chart = {"pillars": {"year": "丙申", "month": "乙卯", "day": "丁酉", "hour": "壬寅"},
             "special_structure": {"type": "化気格"}}
    result = evaluate(chart)
    analysis = result["analysis"]
    pre = analysis["pre_transformation_distribution"]
    post = analysis["five_element_distribution"]
    assert pre["木"] / sum(pre.values()) < .5
    assert post["木"] / sum(post.values()) >= .5
    assert result["special_structure"]["status"] == "established"
    assert result["special_structure"]["evidence"]["element_ratios"]["木"] == pytest.approx(
        post["木"] / sum(post.values()), abs=1e-6
    )


def test_transforming_qi_exact_half_passes_and_below_half_holds():
    transformation = {"status": "established", "positions": ["day", "hour"], "result_element": "木"}
    transformations = {"candidates": [transformation]}
    exact = _analysis({"木": .5, "火": .1, "土": .1, "金": .1, "水": .2}, .7)
    below = _analysis({"木": .499999, "火": .100001, "土": .1, "金": .1, "水": .2}, .7)
    assert _special("transforming_qi", exact, transformations)["status"] == "established"
    result = _special("transforming_qi", below, transformations)
    assert result["status"] == "hold"
    assert result["reasons"] == ["transforming_qi_element_below_0.50"]


def test_non_transforming_special_structure_cannot_ignore_day_stem_transformation():
    chart = {"pillars": {"year": "丙申", "month": "乙卯", "day": "丁酉", "hour": "壬寅"},
             "special_structure": {"type": "従旺格"}}
    result = evaluate(chart)
    assert result["status"] == "hold"
    assert result["reasons"] == ["non_transforming_special_structure_conflicts_with_day_stem_transformation"]


def test_climate_adjustment_is_once_per_target_and_once_in_period_average():
    periods = {**BASE, "great_luck": "壬子", "annual": "癸亥"}
    with_climate = evaluate(periods)
    without_climate = evaluate(periods, {"climate_weight": 0})
    expected = {("stem", "壬"): .5, ("branch", "子"): .5,
                ("great_luck", "壬子"): .5, ("annual", "癸亥"): .455}
    for (kind, target), adjustment in expected.items():
        actual = row(with_climate, kind, target)
        actual_zero = row(without_climate, kind, target)
        assert actual["score"] - actual_zero["score"] == pytest.approx(adjustment)
        assert sum(part["share"] * part["climate_adjustment"] for part in actual["components"]) == pytest.approx(adjustment)
    combined = row(with_climate, "great_luck_annual", "大運＋流年")
    combined_zero = row(without_climate, "great_luck_annual", "大運＋流年")
    assert combined["climate_score"] == pytest.approx((.5 + .455) / 2)
    assert combined["score"] - combined_zero["score"] == pytest.approx((.5 + .455) / 2)
    assert combined["applied_rule_ids"].count("B.CLIMATE.001") == 1


def test_global_competing_hold_explains_why_unrelated_targets_are_not_emitted():
    chart = {
        "pillars": {"year": "甲辰", "month": "己未", "day": "甲子", "hour": "戊辰"},
        "element_roles": {"useful": ["土"], "favorable": ["火"], "unfavorable": ["木", "金", "水"]},
    }
    result = evaluate(chart)
    assert result["hold_scope"] == "entire_model"
    assert "全対象" in result["hold_explanation"]
    assert "evaluations" not in result
