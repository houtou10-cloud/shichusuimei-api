import pytest

from engine.final_strength_judgment import (
    calculate_branch_adjustment,
    calculate_confidence,
    calculate_month_adjustment,
    calculate_root_adjustment,
    calculate_transformation_adjustment,
    clamp_score,
    classify_final_strength,
    evaluate_final_strength_judgment,
    extract_base_score,
    safe_number,
)


def make_weighted_strength_judgment(
    final_score=55.0,
):
    return {
        "label": "やや身強寄り",
        "final_score": final_score,
        "base_supporting_ratio": 55.0,
        "method": (
            "weighted_provisional_strength_v3"
        ),
        "status": (
            "provisional_weighted_judgment"
        ),
    }


def make_weighted_root_strength(
    root_strength="strong",
    has_root=True,
):
    return {
        "day_stem": "乙",
        "day_element": "木",
        "has_root": has_root,
        "root_count": (
            2 if has_root else 0
        ),
        "root_strength": root_strength,
        "total_root_score": (
            0.45 if has_root else 0.0
        ),
    }


def make_integrated_month_strength(
    adjustment=None,
    strength=None,
):
    result = {
        "seasonal_state": "囚",
        "seasonal_score": -6.0,
        "supporting_ratio": 10.0,
        "draining_ratio": 90.0,
        "hidden_stem_balance": -0.8,
        "hidden_stem_adjustment": -3.2,
        "integrated_score": -9.2,
    }

    if adjustment is not None:
        result["adjustment"] = adjustment

    if strength is not None:
        result["strength"] = strength

    return result


def make_branch_relations(
    adjustment=None,
):
    result = {
        "total_relation_count": 2,
        "positive_score": 0.0,
        "negative_score": 4.0,
        "total_score": -4.0,
        "balance": "negative",
    }

    if adjustment is not None:
        result[
            "strength_adjustment"
        ] = adjustment

    return result


def make_transformation_judgment(
    judgment="strong_candidate",
    conflict_severity="none",
):
    return {
        "judgments": [
            {
                "combination_name": "甲己",
                "result_element": "土",
                "judgment": judgment,
                "conflict_severity": (
                    conflict_severity
                ),
            },
        ],
        "method": (
            "stem_transformation_judgment_v3"
        ),
    }


# =========================================================
# clamp_score
# =========================================================


def test_clamp_score_inside_range():
    assert clamp_score(55.678) == 55.68


def test_clamp_score_lower_bound():
    assert clamp_score(-10) == 0.0


def test_clamp_score_upper_bound():
    assert clamp_score(120) == 100.0


def test_clamp_score_invalid_type():
    with pytest.raises(
        TypeError,
        match="scoreは数値",
    ):
        clamp_score("55")


# =========================================================
# safe_number
# =========================================================


def test_safe_number_int():
    assert safe_number(5) == 5.0


def test_safe_number_float():
    assert safe_number(5.5) == 5.5


def test_safe_number_none():
    assert safe_number(
        None,
        default=3.0,
    ) == 3.0


def test_safe_number_invalid_type():
    with pytest.raises(
        TypeError,
        match="数値項目はintまたはfloat型",
    ):
        safe_number(
            "5"
        )


# =========================================================
# extract_base_score
# =========================================================


def test_extract_base_score_from_final_score():
    result = extract_base_score(
        make_weighted_strength_judgment(
            final_score=50.3
        )
    )

    assert result == 50.3


def test_extract_base_score_from_score():
    result = extract_base_score(
        {
            "score": 61.2,
        }
    )

    assert result == 61.2


def test_extract_base_score_clamps():
    result = extract_base_score(
        {
            "final_score": 150,
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
        match="基礎スコアを取得できません",
    ):
        extract_base_score(
            {}
        )


# =========================================================
# root adjustment
# =========================================================


def test_root_adjustment_none():
    assert (
        calculate_root_adjustment(
            None
        )
        == 0.0
    )


def test_root_adjustment_direct_value():
    assert (
        calculate_root_adjustment(
            {
                "adjustment": 4.5,
            }
        )
        == 4.5
    )


def test_root_adjustment_direct_value_clamped_high():
    assert (
        calculate_root_adjustment(
            {
                "adjustment": 20.0,
            }
        )
        == 8.0
    )


def test_root_adjustment_direct_value_clamped_low():
    assert (
        calculate_root_adjustment(
            {
                "adjustment": -20.0,
            }
        )
        == -8.0
    )


@pytest.mark.parametrize(
    (
        "root_strength",
        "expected",
    ),
    [
        (
            "very_strong",
            8.0,
        ),
        (
            "strong",
            6.0,
        ),
        (
            "medium",
            3.0,
        ),
        (
            "moderate",
            3.0,
        ),
        (
            "weak",
            1.0,
        ),
        (
            "none",
            -3.0,
        ),
    ],
)
def test_root_adjustment_mapping(
    root_strength,
    expected,
):
    result = (
        calculate_root_adjustment(
            {
                "root_strength": (
                    root_strength
                ),
            }
        )
    )

    assert result == expected


def test_root_adjustment_fallback_has_root_true():
    assert (
        calculate_root_adjustment(
            {
                "has_root": True,
            }
        )
        == 3.0
    )


def test_root_adjustment_fallback_has_root_false():
    assert (
        calculate_root_adjustment(
            {
                "has_root": False,
            }
        )
        == -3.0
    )


def test_root_adjustment_unknown_returns_zero():
    assert (
        calculate_root_adjustment(
            {
                "root_strength": (
                    "unknown"
                ),
            }
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
# month adjustment
# =========================================================


def test_month_adjustment_none():
    assert (
        calculate_month_adjustment(
            None
        )
        == 0.0
    )


def test_month_adjustment_direct_value():
    assert (
        calculate_month_adjustment(
            {
                "adjustment": -9.2,
            }
        )
        == -9.2
    )


def test_month_adjustment_clamped_high():
    assert (
        calculate_month_adjustment(
            {
                "adjustment": 30.0,
            }
        )
        == 15.0
    )


def test_month_adjustment_clamped_low():
    assert (
        calculate_month_adjustment(
            {
                "adjustment": -30.0,
            }
        )
        == -15.0
    )


@pytest.mark.parametrize(
    (
        "level",
        "expected",
    ),
    [
        (
            "very_strong",
            12.0,
        ),
        (
            "strong",
            9.0,
        ),
        (
            "supportive",
            5.0,
        ),
        (
            "neutral",
            0.0,
        ),
        (
            "weak",
            -6.0,
        ),
        (
            "very_weak",
            -10.0,
        ),
    ],
)
def test_month_adjustment_mapping(
    level,
    expected,
):
    assert (
        calculate_month_adjustment(
            {
                "strength": level,
            }
        )
        == expected
    )


def test_month_adjustment_unknown_returns_zero():
    assert (
        calculate_month_adjustment(
            {
                "strength": "unknown",
            }
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


def test_branch_adjustment_direct_value():
    assert (
        calculate_branch_adjustment(
            {
                "strength_adjustment": -1.6,
            }
        )
        == -1.6
    )


def test_branch_adjustment_clamped_high():
    assert (
        calculate_branch_adjustment(
            {
                "adjustment": 20.0,
            }
        )
        == 6.0
    )


def test_branch_adjustment_clamped_low():
    assert (
        calculate_branch_adjustment(
            {
                "adjustment": -20.0,
            }
        )
        == -6.0
    )


def test_branch_adjustment_missing_returns_zero():
    assert (
        calculate_branch_adjustment(
            {
                "total_score": -4.0,
            }
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
        match="judgmentsはlist型",
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
# integrated final judgment
# =========================================================


def test_final_strength_judgment_balanced():
    result = (
        evaluate_final_strength_judgment(
            make_weighted_strength_judgment(
                final_score=50.0
            ),
            {
                "adjustment": 2.0,
            },
            {
                "adjustment": -5.0,
            },
            {
                "strength_adjustment": -1.0,
            },
            {
                "judgments": [],
            },
        )
    )

    assert (
        result["base_score"]
        == 50.0
    )

    assert (
        result["root_adjustment"]
        == 2.0
    )

    assert (
        result["month_adjustment"]
        == -5.0
    )

    assert (
        result["branch_adjustment"]
        == -1.0
    )

    assert (
        result[
            "transformation_adjustment"
        ]
        == 0.0
    )

    assert (
        result["adjustment_total"]
        == -4.0
    )

    assert (
        result["raw_final_score"]
        == 46.0
    )

    assert (
        result["final_score"]
        == 46.0
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
        == "high"
    )


def test_final_strength_judgment_very_strong():
    result = (
        evaluate_final_strength_judgment(
            make_weighted_strength_judgment(
                final_score=65.0
            ),
            {
                "adjustment": 6.0,
            },
            {
                "adjustment": 5.0,
            },
            None,
            None,
        )
    )

    assert (
        result["final_score"]
        == 76.0
    )

    assert (
        result["technical_label"]
        == "very_strong"
    )

    assert (
        result["label"]
        == "極身強"
    )


def test_final_strength_judgment_strong():
    result = (
        evaluate_final_strength_judgment(
            make_weighted_strength_judgment(
                final_score=55.0
            ),
            {
                "adjustment": 3.0,
            },
            None,
            None,
            None,
        )
    )

    assert (
        result["final_score"]
        == 58.0
    )

    assert (
        result["technical_label"]
        == "strong"
    )

    assert (
        result["label"]
        == "身強"
    )


def test_final_strength_judgment_weak():
    result = (
        evaluate_final_strength_judgment(
            make_weighted_strength_judgment(
                final_score=45.0
            ),
            None,
            {
                "adjustment": -5.0,
            },
            None,
            None,
        )
    )

    assert (
        result["final_score"]
        == 40.0
    )

    assert (
        result["technical_label"]
        == "weak"
    )

    assert (
        result["label"]
        == "身弱"
    )


def test_final_strength_judgment_very_weak():
    result = (
        evaluate_final_strength_judgment(
            make_weighted_strength_judgment(
                final_score=30.0
            ),
            None,
            {
                "adjustment": -6.0,
            },
            None,
            None,
        )
    )

    assert (
        result["final_score"]
        == 24.0
    )

    assert (
        result["technical_label"]
        == "very_weak"
    )

    assert (
        result["label"]
        == "極身弱"
    )


def test_final_strength_judgment_upper_clamp():
    result = (
        evaluate_final_strength_judgment(
            make_weighted_strength_judgment(
                final_score=99.0
            ),
            {
                "adjustment": 8.0,
            },
            {
                "adjustment": 15.0,
            },
            {
                "strength_adjustment": 6.0,
            },
            make_transformation_judgment(
                judgment="strong_candidate",
                conflict_severity="none",
            ),
        )
    )

    assert (
        result["raw_final_score"]
        > 100.0
    )

    assert (
        result["final_score"]
        == 100.0
    )


def test_final_strength_judgment_lower_clamp():
    result = (
        evaluate_final_strength_judgment(
            make_weighted_strength_judgment(
                final_score=5.0
            ),
            {
                "adjustment": -8.0,
            },
            {
                "adjustment": -15.0,
            },
            {
                "strength_adjustment": -6.0,
            },
            None,
        )
    )

    assert (
        result["raw_final_score"]
        < 0.0
    )

    assert (
        result["final_score"]
        == 0.0
    )


def test_final_strength_judgment_components():
    result = (
        evaluate_final_strength_judgment(
            make_weighted_strength_judgment(
                final_score=50.0
            ),
            {
                "adjustment": 2.0,
            },
            {
                "adjustment": -5.0,
            },
            {
                "strength_adjustment": -1.0,
            },
            make_transformation_judgment(
                judgment="possible",
                conflict_severity="medium",
            ),
        )
    )

    assert (
        result["components"]["base"]
        == {
            "score": 50.0,
        }
    )

    assert (
        result["components"]["root"]
        == {
            "adjustment": 2.0,
            "available": True,
        }
    )

    assert (
        result["components"]["month"]
        == {
            "adjustment": -5.0,
            "available": True,
        }
    )

    assert (
        result[
            "components"
        ][
            "branch_relations"
        ] == {
            "adjustment": -1.0,
            "available": True,
        }
    )

    assert (
        result[
            "components"
        ][
            "stem_transformation"
        ][
            "available"
        ]
        is True
    )


def test_final_strength_judgment_metadata():
    result = (
        evaluate_final_strength_judgment(
            make_weighted_strength_judgment()
        )
    )

    assert (
        result["method"]
        == "final_strength_judgment_v1"
    )

    assert (
        result["status"]
        == "provisional_final_strength_judgment"
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
