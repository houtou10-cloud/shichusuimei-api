import pytest

from engine.pattern_special_rules import (
    SPECIAL_RULE_METHOD,
    SPECIAL_RULE_STATUS,
    collect_ten_god_occurrences,
    count_ten_gods,
    detect_food_god_controls_killing,
    detect_hurting_officer_meets_officer,
    detect_indirect_resource_robs_food,
    detect_mixed_officer_killing,
    detect_wealth_breaks_resource,
    detect_wealth_many_body_weak,
    evaluate_pattern_special_rules,
)


def make_occurrence(
    ten_god,
    position="year",
    source="heavenly_stem",
    stem=None,
):
    return {
        "ten_god": ten_god,
        "position": position,
        "source": source,
        "stem": stem,
    }


def make_pillar(
    *,
    stem="甲",
    stem_ten_god=None,
    hidden=None,
):
    if hidden is None:
        hidden = []

    return {
        "stem": stem,
        "stem_ten_god": stem_ten_god,
        "hidden_stem_ten_gods": [
            {
                "stem": item[
                    "stem"
                ],
                "ten_god": item[
                    "ten_god"
                ],
            }
            for item in hidden
        ],
    }


def make_chart(
    *,
    year_stem_ten_god=None,
    month_stem_ten_god=None,
    hour_stem_ten_god=None,
    year_hidden=None,
    month_hidden=None,
    day_hidden=None,
    hour_hidden=None,
):
    return {
        "year": make_pillar(
            stem="甲",
            stem_ten_god=year_stem_ten_god,
            hidden=(
                year_hidden
                or []
            ),
        ),
        "month": make_pillar(
            stem="乙",
            stem_ten_god=month_stem_ten_god,
            hidden=(
                month_hidden
                or []
            ),
        ),
        "day": make_pillar(
            stem="丙",
            stem_ten_god=None,
            hidden=(
                day_hidden
                or []
            ),
        ),
        "hour": make_pillar(
            stem="丁",
            stem_ten_god=hour_stem_ten_god,
            hidden=(
                hour_hidden
                or []
            ),
        ),
    }


def make_strength(
    technical_label="balanced",
    final_score=50.0,
):
    return {
        "technical_label": technical_label,
        "final_score": final_score,
    }


# =========================================================
# collect_ten_god_occurrences
# =========================================================


def test_collect_ten_god_occurrences_heavenly_stems():
    chart = make_chart(
        year_stem_ten_god="正官",
        month_stem_ten_god="偏官",
        hour_stem_ten_god="食神",
    )

    result = (
        collect_ten_god_occurrences(
            chart
        )
    )

    assert (
        len(
            result
        )
        == 3
    )

    assert (
        result[0]["ten_god"]
        == "正官"
    )

    assert (
        result[1]["ten_god"]
        == "偏官"
    )

    assert (
        result[2]["ten_god"]
        == "食神"
    )


def test_collect_ten_god_occurrences_hidden_stems():
    chart = make_chart(
        month_hidden=[
            {
                "stem": "戊",
                "ten_god": "偏財",
            },
            {
                "stem": "己",
                "ten_god": "正財",
            },
        ],
    )

    result = (
        collect_ten_god_occurrences(
            chart
        )
    )

    hidden = [
        item
        for item in result
        if (
            item["source"]
            == "hidden_stem"
        )
    ]

    assert (
        len(
            hidden
        )
        == 2
    )

    assert {
        item["ten_god"]
        for item in hidden
    } == {
        "偏財",
        "正財",
    }


def test_collect_ten_god_occurrences_excludes_day_stem_by_default():
    chart = make_chart()

    chart["day"][
        "stem_ten_god"
    ] = "比肩"

    result = (
        collect_ten_god_occurrences(
            chart
        )
    )

    assert (
        not any(
            item[
                "position"
            ]
            == "day"
            and item[
                "source"
            ]
            == "heavenly_stem"
            for item in result
        )
    )


def test_collect_ten_god_occurrences_can_include_day_stem():
    chart = make_chart()

    chart["day"][
        "stem_ten_god"
    ] = "比肩"

    result = (
        collect_ten_god_occurrences(
            chart,
            include_day_stem=True,
        )
    )

    assert (
        any(
            item[
                "position"
            ]
            == "day"
            and item[
                "ten_god"
            ]
            == "比肩"
            for item in result
        )
    )


def test_collect_ten_god_occurrences_can_exclude_hidden():
    chart = make_chart(
        year_stem_ten_god="正官",
        year_hidden=[
            {
                "stem": "庚",
                "ten_god": "偏官",
            },
        ],
    )

    result = (
        collect_ten_god_occurrences(
            chart,
            include_hidden_stems=False,
        )
    )

    assert (
        len(
            result
        )
        == 1
    )

    assert (
        result[0][
            "ten_god"
        ]
        == "正官"
    )


def test_collect_ten_god_occurrences_nested_chart_supported():
    chart = {
        "chart": make_chart(
            year_stem_ten_god="正官",
        )
    }

    result = (
        collect_ten_god_occurrences(
            chart
        )
    )

    assert (
        len(
            result
        )
        == 1
    )

    assert (
        result[0][
            "ten_god"
        ]
        == "正官"
    )


def test_collect_ten_god_occurrences_invalid_chart_type():
    with pytest.raises(
        TypeError,
        match=(
            "chart_dataはdict型"
        ),
    ):
        collect_ten_god_occurrences(
            []
        )


def test_collect_ten_god_occurrences_ignores_invalid_ten_god():
    chart = make_chart(
        year_stem_ten_god="不明",
    )

    result = (
        collect_ten_god_occurrences(
            chart
        )
    )

    assert (
        result
        == []
    )


# =========================================================
# count_ten_gods
# =========================================================


def test_count_ten_gods():
    occurrences = [
        make_occurrence(
            "正官"
        ),
        make_occurrence(
            "正官",
            position="month",
        ),
        make_occurrence(
            "偏官",
            position="hour",
        ),
    ]

    result = count_ten_gods(
        occurrences
    )

    assert (
        result["正官"]
        == 2
    )

    assert (
        result["偏官"]
        == 1
    )

    assert (
        result["食神"]
        == 0
    )


def test_count_ten_gods_invalid_type():
    with pytest.raises(
        TypeError,
        match=(
            "occurrencesはlist型"
        ),
    ):
        count_ten_gods(
            {}
        )


def test_count_ten_gods_invalid_item():
    with pytest.raises(
        TypeError,
        match=(
            "occurrenceはdict型"
        ),
    ):
        count_ten_gods(
            [
                [],
            ]
        )


# =========================================================
# 官殺混雑
# =========================================================


def test_mixed_officer_killing_not_detected():
    occurrences = [
        make_occurrence(
            "正官"
        ),
    ]

    result = (
        detect_mixed_officer_killing(
            occurrences
        )
    )

    assert (
        result["detected"]
        is False
    )

    assert (
        result["effect"]
        == "neutral"
    )

    assert (
        result[
            "score_adjustment"
        ]
        == 0.0
    )


def test_mixed_officer_killing_both_visible():
    occurrences = [
        make_occurrence(
            "正官",
            source="heavenly_stem",
        ),
        make_occurrence(
            "偏官",
            position="month",
            source="heavenly_stem",
        ),
    ]

    result = (
        detect_mixed_officer_killing(
            occurrences
        )
    )

    assert (
        result["detected"]
        is True
    )

    assert (
        result["confidence"]
        == "high"
    )

    assert (
        result["severity"]
        == "high"
    )

    assert (
        result[
            "score_adjustment"
        ]
        == -10.0
    )


def test_mixed_officer_killing_one_visible():
    occurrences = [
        make_occurrence(
            "正官",
            source="heavenly_stem",
        ),
        make_occurrence(
            "偏官",
            position="month",
            source="hidden_stem",
        ),
    ]

    result = (
        detect_mixed_officer_killing(
            occurrences
        )
    )

    assert (
        result["confidence"]
        == "medium"
    )

    assert (
        result["severity"]
        == "medium"
    )

    assert (
        result[
            "score_adjustment"
        ]
        == -7.0
    )


def test_mixed_officer_killing_hidden_only():
    occurrences = [
        make_occurrence(
            "正官",
            source="hidden_stem",
        ),
        make_occurrence(
            "偏官",
            position="month",
            source="hidden_stem",
        ),
    ]

    result = (
        detect_mixed_officer_killing(
            occurrences
        )
    )

    assert (
        result["confidence"]
        == "low"
    )

    assert (
        result["severity"]
        == "low"
    )

    assert (
        result[
            "score_adjustment"
        ]
        == -4.0
    )


# =========================================================
# 食神制殺
# =========================================================


def test_food_god_controls_killing_not_detected():
    result = (
        detect_food_god_controls_killing(
            [
                make_occurrence(
                    "偏官"
                ),
            ]
        )
    )

    assert (
        result["detected"]
        is False
    )

    assert (
        result[
            "score_adjustment"
        ]
        == 0.0
    )


def test_food_god_controls_killing_both_visible():
    occurrences = [
        make_occurrence(
            "偏官"
        ),
        make_occurrence(
            "食神",
            position="month",
        ),
    ]

    result = (
        detect_food_god_controls_killing(
            occurrences
        )
    )

    assert (
        result["detected"]
        is True
    )

    assert (
        result["effect"]
        == "rescue"
    )

    assert (
        result["confidence"]
        == "high"
    )

    assert (
        result[
            "score_adjustment"
        ]
        == 10.0
    )


def test_food_god_controls_killing_one_visible():
    occurrences = [
        make_occurrence(
            "偏官"
        ),
        make_occurrence(
            "食神",
            source="hidden_stem",
        ),
    ]

    result = (
        detect_food_god_controls_killing(
            occurrences
        )
    )

    assert (
        result["confidence"]
        == "medium"
    )

    assert (
        result[
            "score_adjustment"
        ]
        == 7.0
    )


def test_food_god_controls_killing_hidden_only():
    occurrences = [
        make_occurrence(
            "偏官",
            source="hidden_stem",
        ),
        make_occurrence(
            "食神",
            source="hidden_stem",
        ),
    ]

    result = (
        detect_food_god_controls_killing(
            occurrences
        )
    )

    assert (
        result["confidence"]
        == "low"
    )

    assert (
        result[
            "score_adjustment"
        ]
        == 4.0
    )


# =========================================================
# 傷官見官
# =========================================================


def test_hurting_officer_meets_officer_not_detected():
    result = (
        detect_hurting_officer_meets_officer(
            [
                make_occurrence(
                    "傷官"
                ),
            ]
        )
    )

    assert (
        result["detected"]
        is False
    )


def test_hurting_officer_meets_officer_both_visible():
    occurrences = [
        make_occurrence(
            "傷官"
        ),
        make_occurrence(
            "正官",
            position="month",
        ),
    ]

    result = (
        detect_hurting_officer_meets_officer(
            occurrences
        )
    )

    assert (
        result["detected"]
        is True
    )

    assert (
        result["effect"]
        == "breaking"
    )

    assert (
        result["confidence"]
        == "high"
    )

    assert (
        result[
            "score_adjustment"
        ]
        == -10.0
    )


def test_hurting_officer_meets_officer_one_visible():
    occurrences = [
        make_occurrence(
            "傷官"
        ),
        make_occurrence(
            "正官",
            source="hidden_stem",
        ),
    ]

    result = (
        detect_hurting_officer_meets_officer(
            occurrences
        )
    )

    assert (
        result["confidence"]
        == "medium"
    )

    assert (
        result[
            "score_adjustment"
        ]
        == -7.0
    )


def test_hurting_officer_meets_officer_hidden_only():
    occurrences = [
        make_occurrence(
            "傷官",
            source="hidden_stem",
        ),
        make_occurrence(
            "正官",
            source="hidden_stem",
        ),
    ]

    result = (
        detect_hurting_officer_meets_officer(
            occurrences
        )
    )

    assert (
        result["confidence"]
        == "low"
    )

    assert (
        result[
            "score_adjustment"
        ]
        == -4.0
    )


# =========================================================
# 財多身弱
# =========================================================


def test_wealth_many_body_weak_detected():
    occurrences = [
        make_occurrence(
            "正財"
        ),
        make_occurrence(
            "偏財",
            position="month",
        ),
    ]

    result = (
        detect_wealth_many_body_weak(
            occurrences,
            make_strength(
                technical_label="weak",
                final_score=35.0,
            ),
        )
    )

    assert (
        result["detected"]
        is True
    )

    assert (
        result[
            "requires_school_rule"
        ]
        is True
    )

    assert (
        result[
            "score_adjustment"
        ]
        == -8.0
    )


def test_wealth_many_but_not_weak():
    occurrences = [
        make_occurrence(
            "正財"
        ),
        make_occurrence(
            "偏財",
            position="month",
        ),
    ]

    result = (
        detect_wealth_many_body_weak(
            occurrences,
            make_strength(
                technical_label="strong",
                final_score=65.0,
            ),
        )
    )

    assert (
        result["detected"]
        is False
    )


def test_wealth_one_only_not_detected():
    result = (
        detect_wealth_many_body_weak(
            [
                make_occurrence(
                    "正財"
                ),
            ],
            make_strength(
                technical_label="weak",
                final_score=35.0,
            ),
        )
    )

    assert (
        result["detected"]
        is False
    )


def test_wealth_many_body_weak_score_fallback():
    occurrences = [
        make_occurrence(
            "正財"
        ),
        make_occurrence(
            "偏財",
        ),
    ]

    result = (
        detect_wealth_many_body_weak(
            occurrences,
            make_strength(
                technical_label="unknown",
                final_score=40.0,
            ),
        )
    )

    assert (
        result["detected"]
        is True
    )


# =========================================================
# 印綬の財破
# =========================================================


def test_wealth_breaks_resource_not_detected():
    result = (
        detect_wealth_breaks_resource(
            [
                make_occurrence(
                    "印綬"
                ),
            ]
        )
    )

    assert (
        result["detected"]
        is False
    )


def test_wealth_breaks_resource_both_visible():
    occurrences = [
        make_occurrence(
            "印綬"
        ),
        make_occurrence(
            "偏財",
            position="month",
        ),
    ]

    result = (
        detect_wealth_breaks_resource(
            occurrences
        )
    )

    assert (
        result["detected"]
        is True
    )

    assert (
        result["confidence"]
        == "high"
    )

    assert (
        result[
            "score_adjustment"
        ]
        == -9.0
    )


def test_wealth_breaks_resource_one_visible():
    occurrences = [
        make_occurrence(
            "印綬"
        ),
        make_occurrence(
            "正財",
            source="hidden_stem",
        ),
    ]

    result = (
        detect_wealth_breaks_resource(
            occurrences
        )
    )

    assert (
        result["confidence"]
        == "medium"
    )

    assert (
        result[
            "score_adjustment"
        ]
        == -6.0
    )


def test_wealth_breaks_resource_hidden_only():
    occurrences = [
        make_occurrence(
            "印綬",
            source="hidden_stem",
        ),
        make_occurrence(
            "偏財",
            source="hidden_stem",
        ),
    ]

    result = (
        detect_wealth_breaks_resource(
            occurrences
        )
    )

    assert (
        result["confidence"]
        == "low"
    )

    assert (
        result[
            "score_adjustment"
        ]
        == -3.0
    )


# =========================================================
# 偏印奪食
# =========================================================


def test_indirect_resource_robs_food_not_detected():
    result = (
        detect_indirect_resource_robs_food(
            [
                make_occurrence(
                    "偏印"
                ),
            ]
        )
    )

    assert (
        result["detected"]
        is False
    )


def test_indirect_resource_robs_food_both_visible():
    occurrences = [
        make_occurrence(
            "偏印"
        ),
        make_occurrence(
            "食神",
            position="month",
        ),
    ]

    result = (
        detect_indirect_resource_robs_food(
            occurrences
        )
    )

    assert (
        result["detected"]
        is True
    )

    assert (
        result["confidence"]
        == "high"
    )

    assert (
        result[
            "score_adjustment"
        ]
        == -9.0
    )


def test_indirect_resource_robs_food_one_visible():
    occurrences = [
        make_occurrence(
            "偏印"
        ),
        make_occurrence(
            "食神",
            source="hidden_stem",
        ),
    ]

    result = (
        detect_indirect_resource_robs_food(
            occurrences
        )
    )

    assert (
        result["confidence"]
        == "medium"
    )

    assert (
        result[
            "score_adjustment"
        ]
        == -6.0
    )


def test_indirect_resource_robs_food_hidden_only():
    occurrences = [
        make_occurrence(
            "偏印",
            source="hidden_stem",
        ),
        make_occurrence(
            "食神",
            source="hidden_stem",
        ),
    ]

    result = (
        detect_indirect_resource_robs_food(
            occurrences
        )
    )

    assert (
        result["confidence"]
        == "low"
    )

    assert (
        result[
            "score_adjustment"
        ]
        == -3.0
    )


# =========================================================
# aggregate evaluation
# =========================================================


def test_evaluate_pattern_special_rules_no_rule():
    chart = make_chart()

    result = (
        evaluate_pattern_special_rules(
            chart,
            make_strength(),
        )
    )

    assert (
        result[
            "has_special_rule"
        ]
        is False
    )

    assert (
        result[
            "detected_rule_count"
        ]
        == 0
    )

    assert (
        result[
            "overall_status"
        ]
        == "no_special_rule_detected"
    )

    assert (
        result[
            "total_score_adjustment"
        ]
        == 0.0
    )

    assert (
        result["method"]
        == SPECIAL_RULE_METHOD
    )

    assert (
        result["status"]
        == SPECIAL_RULE_STATUS
    )


def test_evaluate_pattern_special_rules_breaking_only():
    chart = make_chart(
        year_stem_ten_god="傷官",
        month_stem_ten_god="正官",
    )

    result = (
        evaluate_pattern_special_rules(
            chart,
            make_strength(),
        )
    )

    assert (
        result[
            "has_special_rule"
        ]
        is True
    )

    assert (
        result[
            "breaking_rule_count"
        ]
        >= 1
    )

    assert (
        result[
            "overall_status"
        ]
        == "breaking_rules_detected"
    )


def test_evaluate_pattern_special_rules_rescue_only():
    chart = make_chart(
        year_stem_ten_god="偏官",
        month_stem_ten_god="食神",
    )

    result = (
        evaluate_pattern_special_rules(
            chart,
            make_strength(),
        )
    )

    assert (
        result[
            "rescue_rule_count"
        ]
        >= 1
    )

    assert (
        result[
            "breaking_rule_count"
        ]
        == 0
    )

    assert (
        result[
            "overall_status"
        ]
        == "rescue_rules_detected"
    )


def test_evaluate_pattern_special_rules_mixed():
    chart = make_chart(
        year_stem_ten_god="正官",
        month_stem_ten_god="偏官",
        hour_stem_ten_god="食神",
    )

    result = (
        evaluate_pattern_special_rules(
            chart,
            make_strength(),
        )
    )

    assert (
        result[
            "breaking_rule_count"
        ]
        >= 1
    )

    assert (
        result[
            "rescue_rule_count"
        ]
        >= 1
    )

    assert (
        result[
            "overall_status"
        ]
        == "mixed_special_rules"
    )


def test_evaluate_pattern_special_rules_total_adjustment_clamped_low():
    chart = make_chart(
        year_stem_ten_god="正官",
        month_stem_ten_god="偏官",
        hour_stem_ten_god="傷官",
        year_hidden=[
            {
                "stem": "戊",
                "ten_god": "偏財",
            },
            {
                "stem": "己",
                "ten_god": "正財",
            },
        ],
        month_hidden=[
            {
                "stem": "壬",
                "ten_god": "印綬",
            },
            {
                "stem": "癸",
                "ten_god": "偏印",
            },
            {
                "stem": "甲",
                "ten_god": "食神",
            },
        ],
    )

    result = (
        evaluate_pattern_special_rules(
            chart,
            make_strength(
                technical_label="weak",
                final_score=35.0,
            ),
        )
    )

    assert (
        result[
            "total_score_adjustment"
        ]
        >= -20.0
    )

    assert (
        result[
            "total_score_adjustment"
        ]
        <= 20.0
    )


def test_evaluate_pattern_special_rules_ten_god_counts():
    chart = make_chart(
        year_stem_ten_god="正官",
        month_stem_ten_god="偏官",
        hour_stem_ten_god="食神",
    )

    result = (
        evaluate_pattern_special_rules(
            chart
        )
    )

    counts = result[
        "ten_god_counts"
    ]

    assert (
        counts["正官"]
        == 1
    )

    assert (
        counts["偏官"]
        == 1
    )

    assert (
        counts["食神"]
        == 1
    )


def test_evaluate_pattern_special_rules_strength_evidence():
    chart = make_chart(
        year_stem_ten_god="正財",
        month_stem_ten_god="偏財",
    )

    result = (
        evaluate_pattern_special_rules(
            chart,
            make_strength(
                technical_label="weak",
                final_score=35.0,
            ),
        )
    )

    evidence = result[
        "strength_evidence"
    ]

    assert (
        evidence[
            "technical_label"
        ]
        == "weak"
    )

    assert (
        evidence[
            "final_score"
        ]
        == 35.0
    )

    assert (
        evidence[
            "is_weak_day_master"
        ]
        is True
    )


def test_evaluate_pattern_special_rules_school_rule_count():
    chart = make_chart(
        year_stem_ten_god="正財",
        month_stem_ten_god="偏財",
    )

    result = (
        evaluate_pattern_special_rules(
            chart,
            make_strength(
                technical_label="weak",
                final_score=35.0,
            ),
        )
    )

    assert (
        result[
            "school_rule_count"
        ]
        >= 1
    )

    assert (
        any(
            rule[
                "technical_rule"
            ]
            == "wealth_many_body_weak"
            for rule in result[
                "school_rule_items"
            ]
        )
    )


def test_evaluate_pattern_special_rules_rule_count_is_six():
    result = (
        evaluate_pattern_special_rules(
            make_chart()
        )
    )

    assert (
        result[
            "rule_count"
        ]
        == 6
    )

    assert (
        len(
            result[
                "rules"
            ]
        )
        == 6
    )


def test_evaluate_pattern_special_rules_detected_lists_consistent():
    chart = make_chart(
        year_stem_ten_god="正官",
        month_stem_ten_god="偏官",
        hour_stem_ten_god="食神",
    )

    result = (
        evaluate_pattern_special_rules(
            chart
        )
    )

    assert (
        result[
            "detected_rule_count"
        ]
        == len(
            result[
                "detected_rules"
            ]
        )
    )

    assert (
        result[
            "breaking_rule_count"
        ]
        == len(
            result[
                "breaking_rules"
            ]
        )
    )

    assert (
        result[
            "rescue_rule_count"
        ]
        == len(
            result[
                "rescue_rules"
            ]
        )
    )

    assert (
        result[
            "school_rule_count"
        ]
        == len(
            result[
                "school_rule_items"
            ]
        )
    )


def test_evaluate_pattern_special_rules_invalid_chart_type():
    with pytest.raises(
        TypeError,
        match=(
            "chart_dataはdict型"
        ),
    ):
        evaluate_pattern_special_rules(
            []
        )


def test_evaluate_pattern_special_rules_invalid_strength_type():
    with pytest.raises(
        TypeError,
        match=(
            "final_strength_judgmentは"
            "dict型またはNone"
        ),
    ):
        evaluate_pattern_special_rules(
            make_chart(),
            [],
        )


def test_evaluate_pattern_special_rules_notes():
    result = (
        evaluate_pattern_special_rules(
            make_chart()
        )
    )

    assert isinstance(
        result[
            "notes"
        ],
        list,
    )

    assert (
        len(
            result[
                "notes"
            ]
        )
        >= 1
    )


# =========================================================
# metadata
# =========================================================


def test_special_rule_constants():
    assert (
        SPECIAL_RULE_METHOD
        == "pattern_special_rules_v1"
    )

    assert (
        SPECIAL_RULE_STATUS
        == "provisional_pattern_special_rules"
    )
