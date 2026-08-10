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
    extract_branch_evidence,
    extract_month_evidence,
    extract_root_evidence,
    safe_number,
)


def make_weighted_strength_judgment(
    final_score=50.0,
    score=None,
):
    result = {
        "final_score": final_score,
        "label": "中和",
        "method": (
            "weighted_provisional_strength_v3"
        ),
    }

    if score is not None:
        result["score"] = score

    return result


def make_weighted_root_strength(
    adjustment=None,
    has_root=True,
):
    result = {
        "has_root": has_root,
        "root_count": (
            1 if has_root else 0
        ),
    }

    if adjustment is not None:
        result["adjustment"] = adjustment

    return result


def make_integrated_month_strength(
    adjustment=None,
    strength="neutral",
):
    result = {
        "strength": strength,
    }

    if adjustment is not None:
        result["adjustment"] = adjustment

    return result


def make_branch_relations(
    strength_adjustment=None,
    day_master_adjustment=None,
    adjustment=None,
    total_score=None,
):
    result = {}

    if strength_adjustment is not None:
        result[
            "strength_adjustment"
        ] = strength_adjustment

    if day_master_adjustment is not None:
        result[
            "day_master_adjustment"
        ] = day_master_adjustment

    if adjustment is not None:
        result["adjustment"] = adjustment

    if total_score is not None:
        result["total_score"] = total_score

    return result


def make_transformation_judgment(
    judgment="strong_candidate",
    conflict_severity="none",
):
    return {
        "judgments": [
            {
                "judgment": judgment,
                "conflict_severity": (
                    conflict_severity
                ),
            },
        ],
    }


# =========================================================
# clamp_score
# =========================================================


def test_clamp_score_normal():
    assert (
        clamp_score(
            55.123
        )
        == 55.12
    )


def test_clamp_score_upper_limit():
    assert (
        clamp_score(
            120
        )
        == 100.0
    )


def test_clamp_score_lower_limit():
    assert (
        clamp_score(
            -20
        )
        == 0.0
    )


def test_clamp_score_invalid_type():
    with pytest.raises(
        TypeError,
        match="scoreは数値",
    ):
        clamp_score(
            "50"
        )


# =========================================================
# safe_number
# =========================================================


def test_safe_number_int():
    assert (
        safe_number(
            10
        )
        == 10.0
    )


def test_safe_number_float():
    assert (
        safe_number(
            10.5
        )
        == 10.5
    )


def test_safe_number_none():
    assert (
        safe_number(
            None,
            default=3.5,
        )
        == 3.5
    )


def test_safe_number_invalid_type():
    with pytest.raises(
        TypeError,
        match=(
            "数値項目はintまたは"
        ),
    ):
        safe_number(
            "10"
        )


# =========================================================
# extract_base_score
# =========================================================


def test_extract_base_score_from_final_score():
    result = extract_base_score(
        {
            "final_score": 50.3,
        }
    )

    assert result == 50.3


def test_extract_base_score_from_score_fallback():
    result = extract_base_score(
        {
            "score": 44.0,
        }
    )

    assert result == 44.0


def test_extract_base_score_final_score_priority():
    result = extract_base_score(
        {
            "score": 45.0,
            "final_score": 60.0,
        }
    )

    assert result == 60.0


def test_extract_base_score_clamps_value():
    result = extract_base_score(
        {
            "final_score": 120.0,
        }
    )

    assert result == 100.0


def test_extract_base_score_invalid_type():
    with pytest.raises(
        TypeError,
        match=(
            "weighted_strength_judgmentは"
            "dict型"
        ),
    ):
        extract_base_score(
            []
        )


def test_extract_base_score_missing():
    with pytest.raises(
        ValueError,
        match=(
            "基礎スコアを取得できません"
        ),
    ):
        extract_base_score(
            {}
        )


# =========================================================
# root evidence / no double counting
# =========================================================


def test_extract_root_evidence_none():
    result = extract_root_evidence(
        None
    )

    assert (
        result["available"]
        is False
    )

    assert (
        result[
            "applied_to_final_score"
        ]
        is False
    )

    assert (
        result["reason"]
        == "not_available"
    )

    assert (
        result["data"]
        is None
    )


def test_extract_root_evidence_available():
    data = (
        make_weighted_root_strength(
            adjustment=4.5,
        )
    )

    result = extract_root_evidence(
        data
    )

    assert (
        result["available"]
        is True
    )

    assert (
        result[
            "applied_to_final_score"
        ]
        is False
    )

    assert (
        result["reason"]
        == (
            "already_reflected_in_"
            "weighted_strength_judgment"
        )
    )

    assert (
        result["data"]
        == data
    )


def test_extract_root_evidence_invalid_type():
    with pytest.raises(
        TypeError,
        match=(
            "weighted_root_strengthは"
            "dict型またはNone"
        ),
    ):
        extract_root_evidence(
            []
        )


def test_root_adjustment_is_zero_even_when_explicit():
    assert (
        calculate_root_adjustment(
            make_weighted_root_strength(
                adjustment=4.5,
            )
        )
        == 0.0
    )


def test_root_adjustment_is_zero_when_strong():
    assert (
        calculate_root_adjustment(
            {
                "root_strength": "strong",
                "has_root": True,
            }
        )
        == 0.0
    )


def test_root_adjustment_is_zero_when_no_root():
    assert (
        calculate_root_adjustment(
            {
                "has_root": False,
            }
        )
        == 0.0
    )


def test_root_adjustment_none():
    assert (
        calculate_root_adjustment(
            None
        )
        == 0.0
    )


def test_root_adjustment_invalid_type():
    with pytest.raises(
        TypeError,
        match=(
            "weighted_root_strengthは"
            "dict型またはNone"
        ),
    ):
        calculate_root_adjustment(
            []
        )


# =========================================================
# month evidence / no double counting
# =========================================================


def test_extract_month_evidence_none():
    result = extract_month_evidence(
        None
    )

    assert (
        result["available"]
        is False
    )

    assert (
        result[
            "applied_to_final_score"
        ]
        is False
    )

    assert (
        result["reason"]
        == "not_available"
    )

    assert (
        result["data"]
        is None
    )


def test_extract_month_evidence_available():
    data = (
        make_integrated_month_strength(
            adjustment=-9.2,
        )
    )

    result = extract_month_evidence(
        data
    )

    assert (
        result["available"]
        is True
    )

    assert (
        result[
            "applied_to_final_score"
        ]
        is False
    )

    assert (
        result["reason"]
        == (
            "already_reflected_in_"
            "weighted_strength_judgment"
        )
    )

    assert (
        result["data"]
        == data
    )


def test_extract_month_evidence_invalid_type():
    with pytest.raises(
        TypeError,
        match=(
            "integrated_month_strengthは"
            "dict型またはNone"
        ),
    ):
        extract_month_evidence(
            []
        )


def test_month_adjustment_is_zero_even_when_explicit():
    assert (
        calculate_month_adjustment(
            make_integrated_month_strength(
                adjustment=-9.2,
            )
        )
        == 0.0
    )


def test_month_adjustment_is_zero_when_supportive():
    assert (
        calculate_month_adjustment(
            make_integrated_month_strength(
                strength="supportive",
            )
        )
        == 0.0
    )


def test_month_adjustment_is_zero_when_very_weak():
    assert (
        calculate_month_adjustment(
            make_integrated_month_strength(
                strength="very_weak",
            )
        )
        == 0.0
    )


def test_month_adjustment_none():
    assert (
        calculate_month_adjustment(
            None
        )
        == 0.0
    )


def test_month_adjustment_invalid_type():
    with pytest.raises(
        TypeError,
        match=(
            "integrated_month_strengthは"
            "dict型またはNone"
        ),
    ):
        calculate_month_adjustment(
            []
        )


# =========================================================
# branch adjustment
# =========================================================


def test_branch_adjustment_none():
    assert (
        calculate_branch_adjustment(
            None
        )
        == 0.0
    )


def test_branch_adjustment_strength_adjustment():
    result = (
        calculate_branch_adjustment(
            make_branch_relations(
                strength_adjustment=-1.6,
            )
        )
    )

    assert result == -1.6


def test_branch_adjustment_day_master_adjustment():
    result = (
        calculate_branch_adjustment(
            make_branch_relations(
                day_master_adjustment=2.5,
            )
        )
    )

    assert result == 2.5


def test_branch_adjustment_generic_adjustment():
    result = (
        calculate_branch_adjustment(
            make_branch_relations(
                adjustment=-2.0,
            )
        )
    )

    assert result == -2.0


def test_branch_adjustment_priority():
    result = (
        calculate_branch_adjustment(
            make_branch_relations(
                strength_adjustment=1.0,
                day_master_adjustment=2.0,
                adjustment=3.0,
            )
        )
    )

    assert result == 1.0


def test_branch_adjustment_clamped_high():
    result = (
        calculate_branch_adjustment(
            make_branch_relations(
                strength_adjustment=20.0,
            )
        )
    )

    assert result == 6.0


def test_branch_adjustment_clamped_low():
    result = (
        calculate_branch_adjustment(
            make_branch_relations(
                strength_adjustment=-20.0,
            )
        )
    )

    assert result == -6.0


def test_branch_total_score_only_is_not_applied():
    result = (
        calculate_branch_adjustment(
            make_branch_relations(
                total_score=-4.0,
            )
        )
    )

    assert result == 0.0


def test_branch_adjustment_missing():
    assert (
        calculate_branch_adjustment(
            {}
        )
        == 0.0
    )


def test_branch_adjustment_invalid_type():
    with pytest.raises(
        TypeError,
        match=(
            "branch_relationsは"
            "dict型またはNone"
        ),
    ):
        calculate_branch_adjustment(
            []
        )


# =========================================================
# branch evidence
# =========================================================


def test_branch_evidence_none():
    result = extract_branch_evidence(
        None
    )

    assert (
        result["available"]
        is False
    )

    assert (
        result[
            "applied_to_final_score"
        ]
        is False
    )

    assert (
        result["adjustment"]
        == 0.0
    )

    assert (
        result["total_score"]
        is None
    )

    assert (
        result["reason"]
        == "not_available"
    )


def test_branch_evidence_total_score_only():
    data = (
        make_branch_relations(
            total_score=-4.0,
        )
    )

    result = extract_branch_evidence(
        data
    )

    assert (
        result["available"]
        is True
    )

    assert (
        result[
            "applied_to_final_score"
        ]
        is False
    )

    assert (
        result["adjustment"]
        == 0.0
    )

    assert (
        result["total_score"]
        == -4.0
    )

    assert (
        result["reason"]
        == (
            "no_explicit_day_master_"
            "adjustment"
        )
    )

    assert (
        result["data"]
        == data
    )


def test_branch_evidence_explicit_adjustment():
    data = (
        make_branch_relations(
            strength_adjustment=-1.6,
            total_score=-4.0,
        )
    )

    result = extract_branch_evidence(
        data
    )

    assert (
        result["available"]
        is True
    )

    assert (
        result[
            "applied_to_final_score"
        ]
        is True
    )

    assert (
        result["adjustment"]
        == -1.6
    )

    assert (
        result["total_score"]
        == -4.0
    )

    assert (
        result["reason"]
        == (
            "explicit_day_master_"
            "adjustment"
        )
    )


def test_branch_evidence_invalid_type():
    with pytest.raises(
        TypeError,
        match=(
            "branch_relationsは"
            "dict型またはNone"
        ),
    ):
        extract_branch_evidence(
            []
        )


# =========================================================
# transformation adjustment
# =========================================================


def test_transformation_adjustment_none():
    assert (
        calculate_transformation_adjustment(
            None
        )
        == 0.0
    )


@pytest.mark.parametrize(
    (
        "judgment",
        "expected",
    ),
    [
        (
            "strong_candidate",
            3.0,
        ),
        (
            "possible",
            1.5,
        ),
        (
            "weak",
            0.5,
        ),
        (
            "unsupported",
            0.0,
        ),
    ],
)
def test_transformation_adjustment_base(
    judgment,
    expected,
):
    result = (
        calculate_transformation_adjustment(
            make_transformation_judgment(
                judgment=judgment,
                conflict_severity="none",
            )
        )
    )

    assert result == expected


def test_transformation_adjustment_low_conflict():
    result = (
        calculate_transformation_adjustment(
            make_transformation_judgment(
                judgment="strong_candidate",
                conflict_severity="low",
            )
        )
    )

    assert result == 2.4


def test_transformation_adjustment_medium_conflict():
    result = (
        calculate_transformation_adjustment(
            make_transformation_judgment(
                judgment="strong_candidate",
                conflict_severity="medium",
            )
        )
    )

    assert result == 1.5


def test_transformation_adjustment_high_conflict():
    result = (
        calculate_transformation_adjustment(
            make_transformation_judgment(
                judgment="strong_candidate",
                conflict_severity="high",
            )
        )
    )

    assert result == 0.75


def test_transformation_adjustment_multiple_clamped():
    result = (
        calculate_transformation_adjustment(
            {
                "judgments": [
                    {
                        "judgment": (
                            "strong_candidate"
                        ),
                        "conflict_severity": (
                            "none"
                        ),
                    },
                    {
                        "judgment": (
                            "strong_candidate"
                        ),
                        "conflict_severity": (
                            "none"
                        ),
                    },
                ],
            }
        )
    )

    assert result == 5.0


def test_transformation_adjustment_invalid_type():
    with pytest.raises(
        TypeError,
        match=(
            "stem_transformation_judgmentは"
            "dict型またはNone"
        ),
    ):
        calculate_transformation_adjustment(
            []
        )


def test_transformation_adjustment_invalid_judgments_type():
    with pytest.raises(
        TypeError,
        match=(
            "judgmentsはlist型"
        ),
    ):
        calculate_transformation_adjustment(
            {
                "judgments": {},
            }
        )


def test_transformation_adjustment_invalid_item():
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


def test_transformation_adjustment_invalid_severity():
    with pytest.raises(
        ValueError,
        match=(
            "不正なconflict_severity"
        ),
    ):
        calculate_transformation_adjustment(
            make_transformation_judgment(
                judgment="strong_candidate",
                conflict_severity="invalid",
            )
        )


# =========================================================
# classification
# =========================================================


@pytest.mark.parametrize(
    (
        "score",
        "technical_label",
        "label",
    ),
    [
        (
            70.0,
            "very_strong",
            "極身強",
        ),
        (
            69.99,
            "strong",
            "身強",
        ),
        (
            58.0,
            "strong",
            "身強",
        ),
        (
            57.99,
            "balanced",
            "中和",
        ),
        (
            43.0,
            "balanced",
            "中和",
        ),
        (
            42.99,
            "weak",
            "身弱",
        ),
        (
            30.0,
            "weak",
            "身弱",
        ),
        (
            29.99,
            "very_weak",
            "極身弱",
        ),
        (
            0.0,
            "very_weak",
            "極身弱",
        ),
    ],
)
def test_classify_final_strength(
    score,
    technical_label,
    label,
):
    result = (
        classify_final_strength(
            score
        )
    )

    assert (
        result["technical_label"]
        == technical_label
    )

    assert (
        result["label"]
        == label
    )


# =========================================================
# confidence
# =========================================================


def test_confidence_high():
    assert (
        calculate_confidence(
            {},
            {},
            {},
            {},
        )
        == "high"
    )


def test_confidence_medium():
    assert (
        calculate_confidence(
            {},
            {},
            None,
            None,
        )
        == "medium"
    )


def test_confidence_low():
    assert (
        calculate_confidence(
            {},
            None,
            None,
            None,
        )
        == "low"
    )


def test_confidence_low_with_no_optional_data():
    assert (
        calculate_confidence(
            None,
            None,
            None,
            None,
        )
        == "low"
    )


# =========================================================
# integrated final judgment v2
# =========================================================


def test_final_strength_judgment_no_optional_adjustments():
    result = (
        evaluate_final_strength_judgment(
            make_weighted_strength_judgment(
                final_score=50.0,
            )
        )
    )

    assert (
        result["base_score"]
        == 50.0
    )

    assert (
        result["root_adjustment"]
        == 0.0
    )

    assert (
        result["month_adjustment"]
        == 0.0
    )

    assert (
        result["branch_adjustment"]
        == 0.0
    )

    assert (
        result[
            "transformation_adjustment"
        ]
        == 0.0
    )

    assert (
        result["adjustment_total"]
        == 0.0
    )

    assert (
        result["raw_final_score"]
        == 50.0
    )

    assert (
        result["final_score"]
        == 50.0
    )

    assert (
        result["technical_label"]
        == "balanced"
    )

    assert (
        result["label"]
        == "中和"
    )

    assert (
        result["confidence"]
        == "low"
    )


def test_final_strength_does_not_reapply_root_or_month():
    result = (
        evaluate_final_strength_judgment(
            make_weighted_strength_judgment(
                final_score=50.3,
            ),
            make_weighted_root_strength(
                adjustment=4.5,
            ),
            make_integrated_month_strength(
                adjustment=-9.2,
            ),
            None,
            None,
        )
    )

    assert (
        result["base_score"]
        == 50.3
    )

    assert (
        result["root_adjustment"]
        == 0.0
    )

    assert (
        result["month_adjustment"]
        == 0.0
    )

    assert (
        result["adjustment_total"]
        == 0.0
    )

    assert (
        result["raw_final_score"]
        == 50.3
    )

    assert (
        result["final_score"]
        == 50.3
    )


def test_final_strength_total_score_only_branch_not_applied():
    result = (
        evaluate_final_strength_judgment(
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
                total_score=-4.0,
            ),
            {
                "judgments": [],
            },
        )
    )

    assert (
        result["branch_adjustment"]
        == 0.0
    )

    assert (
        result["adjustment_total"]
        == 0.0
    )

    assert (
        result["final_score"]
        == 50.3
    )

    assert (
        result["components"][
            "branch_relations"
        ][
            "total_score"
        ]
        == -4.0
    )

    assert (
        result["components"][
            "branch_relations"
        ][
            "applied_to_final_score"
        ]
        is False
    )


def test_final_strength_explicit_branch_adjustment_applied():
    result = (
        evaluate_final_strength_judgment(
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
                strength_adjustment=-1.6,
                total_score=-4.0,
            ),
            {
                "judgments": [],
            },
        )
    )

    assert (
        result["branch_adjustment"]
        == -1.6
    )

    assert (
        result["adjustment_total"]
        == -1.6
    )

    assert (
        result["raw_final_score"]
        == 48.7
    )

    assert (
        result["final_score"]
        == 48.7
    )


def test_final_strength_transformation_adjustment_applied():
    result = (
        evaluate_final_strength_judgment(
            make_weighted_strength_judgment(
                final_score=50.3,
            ),
            make_weighted_root_strength(
                adjustment=4.5,
            ),
            make_integrated_month_strength(
                adjustment=-9.2,
            ),
            None,
            make_transformation_judgment(
                judgment="possible",
                conflict_severity="none",
            ),
        )
    )

    assert (
        result[
            "transformation_adjustment"
        ]
        == 1.5
    )

    assert (
        result["adjustment_total"]
        == 1.5
    )

    assert (
        result["raw_final_score"]
        == 51.8
    )

    assert (
        result["final_score"]
        == 51.8
    )


def test_final_strength_branch_and_transformation():
    result = (
        evaluate_final_strength_judgment(
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
                strength_adjustment=-1.6,
            ),
            make_transformation_judgment(
                judgment="possible",
                conflict_severity="none",
            ),
        )
    )

    assert (
        result["root_adjustment"]
        == 0.0
    )

    assert (
        result["month_adjustment"]
        == 0.0
    )

    assert (
        result["branch_adjustment"]
        == -1.6
    )

    assert (
        result[
            "transformation_adjustment"
        ]
        == 1.5
    )

    assert (
        result["adjustment_total"]
        == -0.1
    )

    assert (
        result["raw_final_score"]
        == 50.2
    )

    assert (
        result["final_score"]
        == 50.2
    )

    assert (
        result["confidence"]
        == "high"
    )


def test_final_strength_upper_clamp():
    result = (
        evaluate_final_strength_judgment(
            make_weighted_strength_judgment(
                final_score=99.0,
            ),
            None,
            None,
            make_branch_relations(
                strength_adjustment=6.0,
            ),
            make_transformation_judgment(
                judgment="strong_candidate",
                conflict_severity="none",
            ),
        )
    )

    assert (
        result["raw_final_score"]
        == 108.0
    )

    assert (
        result["final_score"]
        == 100.0
    )

    assert (
        result["technical_label"]
        == "very_strong"
    )


def test_final_strength_lower_clamp():
    result = (
        evaluate_final_strength_judgment(
            make_weighted_strength_judgment(
                final_score=3.0,
            ),
            None,
            None,
            make_branch_relations(
                strength_adjustment=-6.0,
            ),
            None,
        )
    )

    assert (
        result["raw_final_score"]
        == -3.0
    )

    assert (
        result["final_score"]
        == 0.0
    )

    assert (
        result["technical_label"]
        == "very_weak"
    )


# =========================================================
# components / evidence / double counting
# =========================================================


def test_final_strength_components():
    root = (
        make_weighted_root_strength(
            adjustment=4.5,
        )
    )

    month = (
        make_integrated_month_strength(
            adjustment=-9.2,
        )
    )

    branches = (
        make_branch_relations(
            total_score=-4.0,
        )
    )

    transformation = {
        "judgments": [],
    }

    result = (
        evaluate_final_strength_judgment(
            make_weighted_strength_judgment(
                final_score=50.3,
            ),
            root,
            month,
            branches,
            transformation,
        )
    )

    assert (
        result["components"]["base"][
            "score"
        ]
        == 50.3
    )

    assert (
        result["components"]["base"][
            "contains"
        ]
        == [
            "weighted_five_elements",
            "weighted_root_strength",
            "integrated_month_strength",
        ]
    )

    assert (
        result["components"]["root"][
            "adjustment"
        ]
        == 0.0
    )

    assert (
        result["components"]["root"][
            "available"
        ]
        is True
    )

    assert (
        result["components"]["root"][
            "applied_to_final_score"
        ]
        is False
    )

    assert (
        result["components"]["month"][
            "adjustment"
        ]
        == 0.0
    )

    assert (
        result["components"]["month"][
            "available"
        ]
        is True
    )

    assert (
        result["components"]["month"][
            "applied_to_final_score"
        ]
        is False
    )

    assert (
        result["components"][
            "branch_relations"
        ][
            "total_score"
        ]
        == -4.0
    )

    assert (
        result["components"][
            "stem_transformation"
        ][
            "available"
        ]
        is True
    )


def test_final_strength_evidence_preserved():
    weighted = (
        make_weighted_strength_judgment(
            final_score=50.3,
        )
    )

    root = (
        make_weighted_root_strength(
            adjustment=4.5,
        )
    )

    month = (
        make_integrated_month_strength(
            adjustment=-9.2,
        )
    )

    branches = (
        make_branch_relations(
            total_score=-4.0,
        )
    )

    transformation = {
        "judgments": [],
    }

    result = (
        evaluate_final_strength_judgment(
            weighted,
            root,
            month,
            branches,
            transformation,
        )
    )

    assert (
        result["evidence"][
            "weighted_strength_judgment"
        ]
        == weighted
    )

    assert (
        result["evidence"][
            "weighted_root_strength"
        ]
        == root
    )

    assert (
        result["evidence"][
            "integrated_month_strength"
        ]
        == month
    )

    assert (
        result["evidence"][
            "branch_relations"
        ]
        == branches
    )

    assert (
        result["evidence"][
            "stem_transformation_judgment"
        ]
        == transformation
    )


def test_double_count_prevention():
    result = (
        evaluate_final_strength_judgment(
            make_weighted_strength_judgment(
                final_score=50.3,
            ),
            make_weighted_root_strength(
                adjustment=4.5,
            ),
            make_integrated_month_strength(
                adjustment=-9.2,
            ),
        )
    )

    prevention = result[
        "double_count_prevention"
    ]

    assert (
        prevention["root_reapplied"]
        is False
    )

    assert (
        prevention["month_reapplied"]
        is False
    )

    assert (
        prevention["reason"]
        == (
            "root_and_month_are_already_"
            "included_in_weighted_"
            "strength_judgment"
        )
    )


# =========================================================
# metadata
# =========================================================


def test_final_strength_judgment_metadata():
    result = (
        evaluate_final_strength_judgment(
            make_weighted_strength_judgment()
        )
    )

    assert (
        result["method"]
        == "final_strength_judgment_v2"
    )

    assert (
        result["status"]
        == (
            "provisional_final_strength_"
            "judgment_v2"
        )
    )

    assert isinstance(
        result["notes"],
        list,
    )

    assert (
        len(
            result["notes"]
        )
        >= 1
    )
