import pytest

from engine.final_strength_judgment import (
    calculate_branch_adjustment,
    calculate_confidence,
    calculate_month_adjustment,
    calculate_root_adjustment,
    calculate_transformation_adjustment,
    classify_final_strength,
    clamp_score,
    evaluate_final_strength_judgment,
    extract_base_score,
    safe_number,
)


def make_weighted_strength_judgment(
    final_score=50.0,
):
    return {
        "final_score": final_score,
        "label": "中和",
        "method": (
            "weighted_provisional_strength_v3"
        ),
    }


def make_weighted_root_strength(
    has_root=True,
    root_strength=None,
    adjustment=None,
):
    result = {
        "has_root": has_root,
    }

    if root_strength is not None:
        result["root_strength"] = root_strength

    if adjustment is not None:
        result["adjustment"] = adjustment

    return result


def make_integrated_month_strength(
    level=None,
    adjustment=None,
):
    result = {}

    if level is not None:
        result["strength"] = level

    if adjustment is not None:
        result["adjustment"] = adjustment

    return result


def make_branch_relations(
    adjustment=None,
):
    result = {}

    if adjustment is not None:
        result["strength_adjustment"] = adjustment

    return result


def make_transformation_judgment(
    judgment="strong_candidate",
    conflict_severity="none",
):
    return {
        "judgments": [
            {
                "judgment": judgment,
                "conflict_severity": conflict_severity,
            },
        ],
    }


def test_clamp_score_normal():
    assert clamp_score(55.123) == 55.12


def test_clamp_score_upper_limit():
    assert clamp_score(120) == 100.0


def test_clamp_score_lower_limit():
    assert clamp_score(-20) == 0.0


def test_clamp_score_invalid_type():
    with pytest.raises(
        TypeError,
        match="scoreは数値",
    ):
        clamp_score("50")


def test_safe_number_int():
    assert safe_number(10) == 10.0


def test_safe_number_float():
    assert safe_number(10.5) == 10.5


def test_safe_number_none():
    assert safe_number(None, default=3.5) == 3.5


def test_safe_number_invalid_type():
    with pytest.raises(
        TypeError,
        match="数値項目はintまたは",
    ):
        safe_number("10")


def test_extract_base_score_from_final_score():
    result = extract_base_score(
        {
            "final_score": 50.3,
        }
    )
    assert result == 50.3


def test_extract_base_score_from_score():
    result = extract_base_score(
        {
            "score": 44.0,
        }
    )
    assert result == 44.0


def test_extract_base_score_priority():
    result = extract_base_score(
        {
            "score": 45.0,
            "final_score": 60.0,
        }
    )
    assert result == 45.0


def test_extract_base_score_invalid_type():
    with pytest.raises(
        TypeError,
        match=(
            "weighted_strength_judgmentは"
            "dict型"
        ),
    ):
        extract_base_score([])


def test_extract_base_score_missing():
    with pytest.raises(
        ValueError,
        match="基礎スコアを取得できません",
    ):
        extract_base_score({})


def test_root_adjustment_none():
    assert calculate_root_adjustment(None) == 0.0


def test_root_adjustment_explicit():
    result = calculate_root_adjustment(
        make_weighted_root_strength(
            adjustment=4.5,
        )
    )
    assert result == 4.5


def test_root_adjustment_clamped_high():
    result = calculate_root_adjustment(
        make_weighted_root_strength(
            adjustment=20,
        )
    )
    assert result == 8.0


def test_root_adjustment_clamped_low():
    result = calculate_root_adjustment(
        make_weighted_root_strength(
            adjustment=-20,
        )
    )
    assert result == -8.0


def test_root_adjustment_strong():
    result = calculate_root_adjustment(
        make_weighted_root_strength(
            root_strength="strong",
        )
    )
    assert result == 6.0


def test_root_adjustment_has_root():
    result = calculate_root_adjustment(
        {
            "has_root": True,
        }
    )
    assert result == 3.0


def test_root_adjustment_no_root():
    result = calculate_root_adjustment(
        {
            "has_root": False,
        }
    )
    assert result == -3.0


def test_root_adjustment_invalid_type():
    with pytest.raises(
        TypeError,
        match=(
            "weighted_root_strengthは"
            "dict型またはNone"
        ),
    ):
        calculate_root_adjustment([])


def test_month_adjustment_none():
    assert calculate_month_adjustment(None) == 0.0


def test_month_adjustment_explicit():
    result = calculate_month_adjustment(
        make_integrated_month_strength(
            adjustment=-9.2,
        )
    )
    assert result == -9.2


def test_month_adjustment_clamped_high():
    result = calculate_month_adjustment(
        make_integrated_month_strength(
            adjustment=30,
        )
    )
    assert result == 15.0


def test_month_adjustment_clamped_low():
    result = calculate_month_adjustment(
        make_integrated_month_strength(
            adjustment=-30,
        )
    )
    assert result == -15.0


def test_month_adjustment_supportive():
    result = calculate_month_adjustment(
        make_integrated_month_strength(
            level="supportive",
        )
    )
    assert result == 5.0


def test_month_adjustment_very_weak():
    result = calculate_month_adjustment(
        make_integrated_month_strength(
            level="very_weak",
        )
    )
    assert result == -10.0


def test_month_adjustment_invalid_type():
    with pytest.raises(
        TypeError,
        match=(
            "integrated_month_strengthは"
            "dict型またはNone"
        ),
    ):
        calculate_month_adjustment([])


def test_branch_adjustment_none():
    assert calculate_branch_adjustment(None) == 0.0


def test_branch_adjustment_explicit():
    result = calculate_branch_adjustment(
        make_branch_relations(
            adjustment=-1.6,
        )
    )
    assert result == -1.6


def test_branch_adjustment_clamped_high():
    result = calculate_branch_adjustment(
        make_branch_relations(
            adjustment=20,
        )
    )
    assert result == 6.0


def test_branch_adjustment_clamped_low():
    result = calculate_branch_adjustment(
        make_branch_relations(
            adjustment=-20,
        )
    )
    assert result == -6.0


def test_branch_adjustment_missing():
    assert calculate_branch_adjustment({}) == 0.0


def test_branch_adjustment_invalid_type():
    with pytest.raises(
        TypeError,
        match=(
            "branch_relationsは"
            "dict型またはNone"
        ),
    ):
        calculate_branch_adjustment([])


def test_transformation_adjustment_none():
    assert calculate_transformation_adjustment(None) == 0.0


def test_transformation_strong_candidate():
    result = calculate_transformation_adjustment(
        make_transformation_judgment(
            judgment="strong_candidate",
            conflict_severity="none",
        )
    )
    assert result == 3.0


def test_transformation_possible():
    result = calculate_transformation_adjustment(
        make_transformation_judgment(
            judgment="possible",
            conflict_severity="none",
        )
    )
    assert result == 1.5


def test_transformation_weak():
    result = calculate_transformation_adjustment(
        make_transformation_judgment(
            judgment="weak",
            conflict_severity="none",
        )
    )
    assert result == 0.5


def test_transformation_unsupported():
    result = calculate_transformation_adjustment(
        make_transformation_judgment(
            judgment="unsupported",
            conflict_severity="none",
        )
    )
    assert result == 0.0


def test_transformation_low_conflict():
    result = calculate_transformation_adjustment(
        make_transformation_judgment(
            judgment="strong_candidate",
            conflict_severity="low",
        )
    )
    assert result == 2.4


def test_transformation_medium_conflict():
    result = calculate_transformation_adjustment(
        make_transformation_judgment(
            judgment="strong_candidate",
            conflict_severity="medium",
        )
    )
    assert result == 1.5


def test_transformation_high_conflict():
    result = calculate_transformation_adjustment(
        make_transformation_judgment(
            judgment="strong_candidate",
            conflict_severity="high",
        )
    )
    assert result == 0.75


def test_transformation_multiple_clamped():
    data = {
        "judgments": [
            {
                "judgment": "strong_candidate",
                "conflict_severity": "none",
            },
            {
                "judgment": "strong_candidate",
                "conflict_severity": "none",
            },
        ],
    }
    result = calculate_transformation_adjustment(data)
    assert result == 5.0


def test_transformation_invalid_type():
    with pytest.raises(
        TypeError,
        match=(
            "stem_transformation_judgmentは"
            "dict型またはNone"
        ),
    ):
        calculate_transformation_adjustment([])


def test_transformation_invalid_judgments_type():
    with pytest.raises(
        TypeError,
        match="judgmentsはlist型",
    ):
        calculate_transformation_adjustment(
            {
                "judgments": {},
            }
        )


def test_transformation_invalid_judgment_item():
    with pytest.raises(
        TypeError,
        match=(
            "transformation judgmentは"
            "dict型"
        ),
    ):
        calculate_transformation_adjustment(
            {
                "judgments": [
                    [],
                ],
            }
        )


@pytest.mark.parametrize(
    (
        "score",
        "technical_label",
        "label",
    ),
    [
        (75.0, "very_strong", "極身強"),
        (60.0, "strong", "身強"),
        (50.0, "balanced", "中和"),
        (35.0, "weak", "身弱"),
        (20.0, "very_weak", "極身弱"),
    ],
)
def test_classify_final_strength(
    score,
    technical_label,
    label,
):
    result = classify_final_strength(score)

    assert (
        result["technical_label"]
        == technical_label
    )
    assert result["label"] == label


def test_classify_threshold_70():
    assert (
        classify_final_strength(
            70.0
        )["technical_label"]
        == "very_strong"
    )


def test_classify_threshold_58():
    assert (
        classify_final_strength(
            58.0
        )["technical_label"]
        == "strong"
    )


def test_classify_threshold_43():
    assert (
        classify_final_strength(
            43.0
        )["technical_label"]
        == "balanced"
    )


def test_classify_threshold_30():
    assert (
        classify_final_strength(
            30.0
        )["technical_label"]
        == "weak"
    )


def test_confidence_high():
    result = calculate_confidence(
        {},
        {},
        {},
        {},
    )
    assert result == "high"


def test_confidence_medium():
    result = calculate_confidence(
        {},
        {},
        None,
        None,
    )
    assert result == "medium"


def test_confidence_low():
    result = calculate_confidence(
        {},
        None,
        None,
        None,
    )
    assert result == "low"


def test_evaluate_final_strength_basic():
    result = evaluate_final_strength_judgment(
        make_weighted_strength_judgment(
            final_score=50.0,
        )
    )

    assert result["base_score"] == 50.0
    assert result["root_adjustment"] == 0.0
    assert result["month_adjustment"] == 0.0
    assert result["branch_adjustment"] == 0.0
    assert (
        result["transformation_adjustment"]
        == 0.0
    )
    assert result["adjustment_total"] == 0.0
    assert result["raw_final_score"] == 50.0
    assert result["final_score"] == 50.0
    assert (
        result["technical_label"]
        == "balanced"
    )
    assert result["label"] == "中和"
    assert result["confidence"] == "low"
    assert (
        result["method"]
        == "final_strength_judgment_v1"
    )
    assert (
        result["status"]
        == "provisional_final_strength_judgment"
    )


def test_evaluate_final_strength_all_components():
    result = evaluate_final_strength_judgment(
        make_weighted_strength_judgment(
            final_score=50.3,
        ),
        make_weighted_root_strength(
            adjustment=4.5,
        ),
        make_integrated_month_strength(
            adjustment=-9.2,
        ),
        make_branch_relations(
            adjustment=-1.6,
        ),
        make_transformation_judgment(
            judgment="possible",
            conflict_severity="none",
        ),
    )

    assert result["base_score"] == 50.3
    assert result["root_adjustment"] == 4.5
    assert result["month_adjustment"] == -9.2
    assert result["branch_adjustment"] == -1.6
    assert (
        result["transformation_adjustment"]
        == 1.5
    )
    assert result["adjustment_total"] == -4.8
    assert result["raw_final_score"] == 45.5
    assert result["final_score"] == 45.5
    assert (
        result["technical_label"]
        == "balanced"
    )
    assert result["label"] == "中和"
    assert result["confidence"] == "high"


def test_evaluate_final_strength_upper_clamp():
    result = evaluate_final_strength_judgment(
        make_weighted_strength_judgment(
            final_score=99.0,
        ),
        make_weighted_root_strength(
            adjustment=8.0,
        ),
        make_integrated_month_strength(
            adjustment=15.0,
        ),
        make_branch_relations(
            adjustment=6.0,
        ),
        make_transformation_judgment(
            judgment="strong_candidate",
            conflict_severity="none",
        ),
    )

    assert result["raw_final_score"] > 100.0
    assert result["final_score"] == 100.0
    assert (
        result["technical_label"]
        == "very_strong"
    )


def test_evaluate_final_strength_lower_clamp():
    result = evaluate_final_strength_judgment(
        make_weighted_strength_judgment(
            final_score=5.0,
        ),
        make_weighted_root_strength(
            adjustment=-8.0,
        ),
        make_integrated_month_strength(
            adjustment=-15.0,
        ),
        make_branch_relations(
            adjustment=-6.0,
        ),
        {
            "judgments": [],
        },
    )

    assert result["raw_final_score"] < 0.0
    assert result["final_score"] == 0.0
    assert (
        result["technical_label"]
        == "very_weak"
    )


def test_evaluate_components_structure():
    result = evaluate_final_strength_judgment(
        make_weighted_strength_judgment(
            final_score=50.0,
        ),
        {},
        {},
        {},
        {
            "judgments": [],
        },
    )

    assert (
        result["components"]["base"][
            "score"
        ]
        == 50.0
    )
    assert (
        result["components"]["root"][
            "available"
        ]
        is True
    )
    assert (
        result["components"]["month"][
            "available"
        ]
        is True
    )
    assert (
        result["components"][
            "branch_relations"
        ]["available"]
        is True
    )
    assert (
        result["components"][
            "stem_transformation"
        ]["available"]
        is True
    )


def test_result_contains_notes():
    result = evaluate_final_strength_judgment(
        make_weighted_strength_judgment(
            final_score=50.0,
        )
    )

    assert isinstance(
        result["notes"],
        list,
    )
    assert len(result["notes"]) >= 1
