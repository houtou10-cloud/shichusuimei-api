"""
tests/test_final_strength_judgment.py

身強身弱の最終統合判定モジュール v2 の回帰テスト。

検証対象:
- clamp_score
- safe_number
- extract_base_score
- 通根 evidence
- 月令 evidence
- 地支関係補正
- 干合化候補補正
- 最終身強身弱分類
- confidence
- 二重計上防止
- evaluate_final_strength_judgment
- 不正入力

重要な設計:
- weighted_strength_judgment["final_score"] には
  五行・通根・月令が既に反映済み
- 通根と月令は最終スコアへ再加算しない
- branch_relations は日主強弱への方向が
  明示された補正だけを使用
- stem transformation は限定補正
"""

import pytest

from engine.final_strength_judgment_v2 import (
    MAX_SCORE,
    MIN_SCORE,
    STRENGTH_THRESHOLDS,
    TRANSFORMATION_ADJUSTMENTS,
    VALID_CONFLICT_SEVERITIES,
    calculate_branch_adjustment,
    calculate_confidence,
    calculate_month_adjustment,
    calculate_root_adjustment,
    calculate_transformation_adjustment,
    clamp_score,
    classify_final_strength,
    evaluate_final_strength_judgment,
    extract_base_score,
    extract_branch_evidence,
    extract_month_evidence,
    extract_root_evidence,
    safe_number,
)


# =========================================================
# Constants
# =========================================================


def test_min_score():
    assert MIN_SCORE == 0.0


def test_max_score():
    assert MAX_SCORE == 100.0


def test_strength_thresholds():
    assert STRENGTH_THRESHOLDS == (
        (70.0, "very_strong", "極身強"),
        (58.0, "strong", "身強"),
        (43.0, "balanced", "中和"),
        (30.0, "weak", "身弱"),
        (0.0, "very_weak", "極身弱"),
    )


def test_transformation_adjustments():
    assert TRANSFORMATION_ADJUSTMENTS == {
        "strong_candidate": 3.0,
        "possible": 1.5,
        "weak": 0.5,
        "unsupported": 0.0,
    }


def test_valid_conflict_severities():
    assert VALID_CONFLICT_SEVERITIES == {
        "none",
        "low",
        "medium",
        "high",
    }


# =========================================================
# clamp_score
# =========================================================


@pytest.mark.parametrize(
    "value,expected",
    [
        (-10, 0.0),
        (0, 0.0),
        (12.345, 12.35),
        (50, 50.0),
        (99.999, 100.0),
        (100, 100.0),
        (120, 100.0),
    ],
)
def test_clamp_score(value, expected):
    assert clamp_score(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "50",
        None,
        [],
        {},
    ],
)
def test_clamp_score_invalid_type(value):
    with pytest.raises(TypeError):
        clamp_score(value)


# =========================================================
# safe_number
# =========================================================


@pytest.mark.parametrize(
    "value,default,expected",
    [
        (10, 0.0, 10.0),
        (10.5, 0.0, 10.5),
        (None, 0.0, 0.0),
        (None, 3.5, 3.5),
    ],
)
def test_safe_number(value, default, expected):
    assert safe_number(value, default) == expected


@pytest.mark.parametrize(
    "value",
    [
        "10",
        [],
        {},
    ],
)
def test_safe_number_invalid(value):
    with pytest.raises(TypeError):
        safe_number(value)


# =========================================================
# Base score
# =========================================================


@pytest.mark.parametrize(
    "payload,expected",
    [
        ({"final_score": 55.5}, 55.5),
        ({"score": 44.4}, 44.4),
        ({"strength_score": 33.3}, 33.3),
        ({"support_score": 22.2}, 22.2),
        ({"support_ratio": 11.1}, 11.1),
    ],
)
def test_extract_base_score(payload, expected):
    assert extract_base_score(payload) == expected


def test_extract_base_score_prefers_final_score():
    payload = {
        "final_score": 61.0,
        "score": 20.0,
        "strength_score": 30.0,
    }

    assert extract_base_score(payload) == 61.0


def test_extract_base_score_clamps():
    assert (
        extract_base_score(
            {
                "final_score": 120,
            }
        )
        == 100.0
    )


def test_extract_base_score_invalid_type():
    with pytest.raises(TypeError):
        extract_base_score(None)


def test_extract_base_score_missing():
    with pytest.raises(ValueError):
        extract_base_score({})


# =========================================================
# Root evidence
# =========================================================


def test_extract_root_evidence_none():
    result = extract_root_evidence(None)

    assert result == {
        "available": False,
        "applied_to_final_score": False,
        "reason": "not_available",
        "data": None,
    }


def test_extract_root_evidence_available():
    payload = {
        "root_score": 12.0,
    }

    result = extract_root_evidence(payload)

    assert result[
        "available"
    ] is True

    assert result[
        "applied_to_final_score"
    ] is False

    assert result[
        "reason"
    ] == (
        "already_reflected_in_"
        "weighted_strength_judgment"
    )

    assert result[
        "data"
    ] is payload


def test_extract_root_evidence_invalid():
    with pytest.raises(TypeError):
        extract_root_evidence([])


def test_calculate_root_adjustment_always_zero():
    assert (
        calculate_root_adjustment(
            {
                "root_score": 99,
            }
        )
        == 0.0
    )


# =========================================================
# Month evidence
# =========================================================


def test_extract_month_evidence_none():
    result = extract_month_evidence(None)

    assert result == {
        "available": False,
        "applied_to_final_score": False,
        "reason": "not_available",
        "data": None,
    }


def test_extract_month_evidence_available():
    payload = {
        "month_score": 20.0,
    }

    result = extract_month_evidence(payload)

    assert result[
        "available"
    ] is True

    assert result[
        "applied_to_final_score"
    ] is False

    assert result[
        "reason"
    ] == (
        "already_reflected_in_"
        "weighted_strength_judgment"
    )

    assert result[
        "data"
    ] is payload


def test_extract_month_evidence_invalid():
    with pytest.raises(TypeError):
        extract_month_evidence([])


def test_calculate_month_adjustment_always_zero():
    assert (
        calculate_month_adjustment(
            {
                "month_score": 99,
            }
        )
        == 0.0
    )


# =========================================================
# Branch adjustment
# =========================================================


def test_branch_adjustment_none():
    assert calculate_branch_adjustment(None) == 0.0


@pytest.mark.parametrize(
    "payload,expected",
    [
        (
            {
                "strength_adjustment": 4.0,
            },
            4.0,
        ),
        (
            {
                "day_master_adjustment": -3.0,
            },
            -3.0,
        ),
        (
            {
                "adjustment": 2.5,
            },
            2.5,
        ),
    ],
)
def test_branch_adjustment_explicit(
    payload,
    expected,
):
    assert (
        calculate_branch_adjustment(
            payload
        )
        == expected
    )


def test_branch_adjustment_priority():
    result = calculate_branch_adjustment(
        {
            "strength_adjustment": 1.0,
            "day_master_adjustment": 2.0,
            "adjustment": 3.0,
        }
    )

    assert result == 1.0


@pytest.mark.parametrize(
    "value,expected",
    [
        (10.0, 6.0),
        (-10.0, -6.0),
    ],
)
def test_branch_adjustment_clamped(
    value,
    expected,
):
    result = calculate_branch_adjustment(
        {
            "strength_adjustment": value,
        }
    )

    assert result == expected


def test_branch_total_score_not_automatically_applied():
    result = calculate_branch_adjustment(
        {
            "total_score": 99.0,
        }
    )

    assert result == 0.0


def test_branch_adjustment_invalid_type():
    with pytest.raises(TypeError):
        calculate_branch_adjustment([])


# =========================================================
# Branch evidence
# =========================================================


def test_branch_evidence_none():
    result = extract_branch_evidence(
        None
    )

    assert result[
        "available"
    ] is False

    assert result[
        "applied_to_final_score"
    ] is False

    assert result[
        "adjustment"
    ] == 0.0

    assert result[
        "total_score"
    ] is None


def test_branch_evidence_total_score_only():
    payload = {
        "total_score": 8.0,
    }

    result = extract_branch_evidence(
        payload
    )

    assert result[
        "available"
    ] is True

    assert result[
        "applied_to_final_score"
    ] is False

    assert result[
        "adjustment"
    ] == 0.0

    assert result[
        "total_score"
    ] == 8.0

    assert result[
        "reason"
    ] == (
        "no_explicit_day_master_adjustment"
    )


def test_branch_evidence_explicit_adjustment():
    payload = {
        "strength_adjustment": 4.0,
        "total_score": 20.0,
    }

    result = extract_branch_evidence(
        payload
    )

    assert result[
        "available"
    ] is True

    assert result[
        "applied_to_final_score"
    ] is True

    assert result[
        "adjustment"
    ] == 4.0

    assert result[
        "total_score"
    ] == 20.0

    assert result[
        "reason"
    ] == (
        "explicit_day_master_adjustment"
    )


# =========================================================
# Transformation adjustment
# =========================================================


def test_transformation_adjustment_none():
    assert (
        calculate_transformation_adjustment(
            None
        )
        == 0.0
    )


@pytest.mark.parametrize(
    "judgment,expected",
    [
        ("strong_candidate", 3.0),
        ("possible", 1.5),
        ("weak", 0.5),
        ("unsupported", 0.0),
        ("unknown", 0.0),
    ],
)
def test_transformation_adjustment_single(
    judgment,
    expected,
):
    result = (
        calculate_transformation_adjustment(
            {
                "judgments": [
                    {
                        "judgment": judgment,
                        "conflict_severity": (
                            "none"
                        ),
                    }
                ]
            }
        )
    )

    assert result == expected


@pytest.mark.parametrize(
    "severity,expected",
    [
        ("none", 3.0),
        ("low", 2.4),
        ("medium", 1.5),
        ("high", 0.75),
    ],
)
def test_transformation_conflict_multiplier(
    severity,
    expected,
):
    result = (
        calculate_transformation_adjustment(
            {
                "judgments": [
                    {
                        "judgment": (
                            "strong_candidate"
                        ),
                        "conflict_severity": (
                            severity
                        ),
                    }
                ]
            }
        )
    )

    assert result == expected


def test_transformation_adjustment_multiple_clamped_to_five():
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
                ]
            }
        )
    )

    assert result == 5.0


def test_transformation_invalid_container():
    with pytest.raises(TypeError):
        calculate_transformation_adjustment(
            []
        )


def test_transformation_invalid_judgments_type():
    with pytest.raises(TypeError):
        calculate_transformation_adjustment(
            {
                "judgments": {},
            }
        )


def test_transformation_invalid_judgment_item():
    with pytest.raises(TypeError):
        calculate_transformation_adjustment(
            {
                "judgments": [
                    "invalid",
                ],
            }
        )


def test_transformation_invalid_conflict_severity():
    with pytest.raises(ValueError):
        calculate_transformation_adjustment(
            {
                "judgments": [
                    {
                        "judgment": (
                            "strong_candidate"
                        ),
                        "conflict_severity": (
                            "extreme"
                        ),
                    }
                ]
            }
        )


# =========================================================
# Classification
# =========================================================


@pytest.mark.parametrize(
    "score,technical,label",
    [
        (
            100.0,
            "very_strong",
            "極身強",
        ),
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
    technical,
    label,
):
    result = classify_final_strength(
        score
    )

    assert result[
        "technical_label"
    ] == technical

    assert result[
        "label"
    ] == label


# =========================================================
# Confidence
# =========================================================


def test_confidence_low_no_optional_evidence():
    result = calculate_confidence(
        None,
        None,
        None,
        None,
    )

    assert result == "low"


def test_confidence_low_one_source():
    result = calculate_confidence(
        {},
        None,
        None,
        None,
    )

    assert result == "low"


def test_confidence_medium_two_sources():
    result = calculate_confidence(
        {},
        {},
        None,
        None,
    )

    assert result == "medium"


def test_confidence_medium_three_sources():
    result = calculate_confidence(
        {},
        {},
        {},
        None,
    )

    assert result == "medium"


def test_confidence_high_four_sources():
    result = calculate_confidence(
        {},
        {},
        {},
        {},
    )

    assert result == "high"


# =========================================================
# Final evaluation - base only
# =========================================================


def test_final_evaluation_base_only():
    result = (
        evaluate_final_strength_judgment(
            {
                "final_score": 50.0,
            }
        )
    )

    assert result[
        "base_score"
    ] == 50.0

    assert result[
        "root_adjustment"
    ] == 0.0

    assert result[
        "month_adjustment"
    ] == 0.0

    assert result[
        "branch_adjustment"
    ] == 0.0

    assert result[
        "transformation_adjustment"
    ] == 0.0

    assert result[
        "adjustment_total"
    ] == 0.0

    assert result[
        "raw_final_score"
    ] == 50.0

    assert result[
        "final_score"
    ] == 50.0

    assert result[
        "technical_label"
    ] == "balanced"

    assert result[
        "label"
    ] == "中和"

    assert result[
        "confidence"
    ] == "low"


# =========================================================
# Double counting prevention
# =========================================================


def test_root_and_month_are_not_reapplied():
    result = (
        evaluate_final_strength_judgment(
            weighted_strength_judgment={
                "final_score": 50.0,
            },
            weighted_root_strength={
                "score": 30.0,
            },
            integrated_month_strength={
                "score": 25.0,
            },
        )
    )

    assert result[
        "base_score"
    ] == 50.0

    assert result[
        "root_adjustment"
    ] == 0.0

    assert result[
        "month_adjustment"
    ] == 0.0

    assert result[
        "final_score"
    ] == 50.0

    assert result[
        "double_count_prevention"
    ][
        "root_reapplied"
    ] is False

    assert result[
        "double_count_prevention"
    ][
        "month_reapplied"
    ] is False


def test_components_mark_root_not_applied():
    result = (
        evaluate_final_strength_judgment(
            {
                "final_score": 50.0,
            },
            weighted_root_strength={
                "score": 12.0,
            },
        )
    )

    root = result[
        "components"
    ][
        "root"
    ]

    assert root[
        "available"
    ] is True

    assert root[
        "applied_to_final_score"
    ] is False

    assert root[
        "adjustment"
    ] == 0.0


def test_components_mark_month_not_applied():
    result = (
        evaluate_final_strength_judgment(
            {
                "final_score": 50.0,
            },
            integrated_month_strength={
                "score": 12.0,
            },
        )
    )

    month = result[
        "components"
    ][
        "month"
    ]

    assert month[
        "available"
    ] is True

    assert month[
        "applied_to_final_score"
    ] is False

    assert month[
        "adjustment"
    ] == 0.0


# =========================================================
# Final evaluation - branch adjustment
# =========================================================


def test_final_evaluation_branch_positive():
    result = (
        evaluate_final_strength_judgment(
            weighted_strength_judgment={
                "final_score": 55.0,
            },
            branch_relations={
                "strength_adjustment": 4.0,
            },
        )
    )

    assert result[
        "branch_adjustment"
    ] == 4.0

    assert result[
        "adjustment_total"
    ] == 4.0

    assert result[
        "final_score"
    ] == 59.0

    assert result[
        "technical_label"
    ] == "strong"

    assert result[
        "label"
    ] == "身強"


def test_final_evaluation_branch_negative():
    result = (
        evaluate_final_strength_judgment(
            weighted_strength_judgment={
                "final_score": 45.0,
            },
            branch_relations={
                "strength_adjustment": -4.0,
            },
        )
    )

    assert result[
        "final_score"
    ] == 41.0

    assert result[
        "technical_label"
    ] == "weak"

    assert result[
        "label"
    ] == "身弱"


def test_final_evaluation_total_score_only_not_applied():
    result = (
        evaluate_final_strength_judgment(
            weighted_strength_judgment={
                "final_score": 50.0,
            },
            branch_relations={
                "total_score": 100.0,
            },
        )
    )

    assert result[
        "branch_adjustment"
    ] == 0.0

    assert result[
        "final_score"
    ] == 50.0


# =========================================================
# Final evaluation - transformation
# =========================================================


def test_final_evaluation_transformation():
    result = (
        evaluate_final_strength_judgment(
            weighted_strength_judgment={
                "final_score": 56.0,
            },
            stem_transformation_judgment={
                "judgments": [
                    {
                        "judgment": (
                            "possible"
                        ),
                        "conflict_severity": (
                            "none"
                        ),
                    }
                ]
            },
        )
    )

    assert result[
        "transformation_adjustment"
    ] == 1.5

    assert result[
        "final_score"
    ] == 57.5

    assert result[
        "technical_label"
    ] == "balanced"


def test_final_evaluation_branch_and_transformation():
    result = (
        evaluate_final_strength_judgment(
            weighted_strength_judgment={
                "final_score": 55.0,
            },
            branch_relations={
                "strength_adjustment": 2.0,
            },
            stem_transformation_judgment={
                "judgments": [
                    {
                        "judgment": (
                            "possible"
                        ),
                        "conflict_severity": (
                            "none"
                        ),
                    }
                ]
            },
        )
    )

    assert result[
        "branch_adjustment"
    ] == 2.0

    assert result[
        "transformation_adjustment"
    ] == 1.5

    assert result[
        "adjustment_total"
    ] == 3.5

    assert result[
        "final_score"
    ] == 58.5

    assert result[
        "technical_label"
    ] == "strong"


# =========================================================
# Score clamping
# =========================================================


def test_final_score_clamped_to_100():
    result = (
        evaluate_final_strength_judgment(
            weighted_strength_judgment={
                "final_score": 99.0,
            },
            branch_relations={
                "strength_adjustment": 6.0,
            },
            stem_transformation_judgment={
                "judgments": [
                    {
                        "judgment": (
                            "strong_candidate"
                        ),
                        "conflict_severity": (
                            "none"
                        ),
                    }
                ]
            },
        )
    )

    assert result[
        "raw_final_score"
    ] == 108.0

    assert result[
        "final_score"
    ] == 100.0


def test_final_score_clamped_to_zero():
    result = (
        evaluate_final_strength_judgment(
            weighted_strength_judgment={
                "final_score": 3.0,
            },
            branch_relations={
                "strength_adjustment": -6.0,
            },
        )
    )

    assert result[
        "raw_final_score"
    ] == -3.0

    assert result[
        "final_score"
    ] == 0.0


# =========================================================
# Evidence
# =========================================================


def test_final_evaluation_preserves_evidence():
    weighted = {
        "final_score": 50.0,
    }

    root = {
        "root_score": 10,
    }

    month = {
        "month_score": 20,
    }

    branch = {
        "strength_adjustment": 1,
    }

    transformation = {
        "judgments": [],
    }

    result = (
        evaluate_final_strength_judgment(
            weighted_strength_judgment=(
                weighted
            ),
            weighted_root_strength=root,
            integrated_month_strength=(
                month
            ),
            branch_relations=branch,
            stem_transformation_judgment=(
                transformation
            ),
        )
    )

    evidence = result[
        "evidence"
    ]

    assert evidence[
        "weighted_strength_judgment"
    ] is weighted

    assert evidence[
        "weighted_root_strength"
    ] is root

    assert evidence[
        "integrated_month_strength"
    ] is month

    assert evidence[
        "branch_relations"
    ] is branch

    assert evidence[
        "stem_transformation_judgment"
    ] is transformation


# =========================================================
# Metadata
# =========================================================


def test_final_evaluation_metadata():
    result = (
        evaluate_final_strength_judgment(
            {
                "final_score": 50.0,
            }
        )
    )

    assert result[
        "method"
    ] == (
        "final_strength_judgment_v2"
    )

    assert result[
        "status"
    ] == (
        "provisional_final_strength_"
        "judgment_v2"
    )

    assert isinstance(
        result[
            "notes"
        ],
        list,
    )

    assert len(
        result[
            "notes"
        ]
    ) >= 1


# =========================================================
# Components
# =========================================================


def test_final_evaluation_components_exist():
    result = (
        evaluate_final_strength_judgment(
            {
                "final_score": 50.0,
            }
        )
    )

    components = result[
        "components"
    ]

    assert {
        "base",
        "root",
        "month",
        "branch_relations",
        "stem_transformation",
    }.issubset(
        components.keys()
    )


def test_base_component_contains_expected_sources():
    result = (
        evaluate_final_strength_judgment(
            {
                "final_score": 50.0,
            }
        )
    )

    assert result[
        "components"
    ][
        "base"
    ][
        "contains"
    ] == [
        "weighted_five_elements",
        "weighted_root_strength",
        "integrated_month_strength",
    ]


# =========================================================
# Confidence integration
# =========================================================


def test_final_evaluation_confidence_medium():
    result = (
        evaluate_final_strength_judgment(
            weighted_strength_judgment={
                "final_score": 50.0,
            },
            weighted_root_strength={},
            integrated_month_strength={},
        )
    )

    assert result[
        "confidence"
    ] == "medium"


def test_final_evaluation_confidence_high():
    result = (
        evaluate_final_strength_judgment(
            weighted_strength_judgment={
                "final_score": 50.0,
            },
            weighted_root_strength={},
            integrated_month_strength={},
            branch_relations={},
            stem_transformation_judgment={
                "judgments": [],
            },
        )
    )

    assert result[
        "confidence"
    ] == "high"


# =========================================================
# Threshold regression
# =========================================================


@pytest.mark.parametrize(
    "score,technical",
    [
        (70.0, "very_strong"),
        (69.99, "strong"),
        (58.0, "strong"),
        (57.99, "balanced"),
        (43.0, "balanced"),
        (42.99, "weak"),
        (30.0, "weak"),
        (29.99, "very_weak"),
    ],
)
def test_final_strength_threshold_regression(
    score,
    technical,
):
    result = (
        evaluate_final_strength_judgment(
            {
                "final_score": score,
            }
        )
    )

    assert result[
        "technical_label"
    ] == technical


# =========================================================
# Input immutability
# =========================================================


def test_inputs_are_not_mutated():
    weighted = {
        "final_score": 50.0,
    }

    root = {
        "root_score": 10.0,
    }

    month = {
        "month_score": 20.0,
    }

    branch = {
        "strength_adjustment": 2.0,
        "total_score": 5.0,
    }

    transformation = {
        "judgments": [
            {
                "judgment": "possible",
                "conflict_severity": "low",
            }
        ]
    }

    weighted_before = dict(
        weighted
    )

    root_before = dict(
        root
    )

    month_before = dict(
        month
    )

    branch_before = dict(
        branch
    )

    transformation_before = {
        "judgments": [
            dict(
                transformation[
                    "judgments"
                ][0]
            )
        ]
    }

    evaluate_final_strength_judgment(
        weighted_strength_judgment=(
            weighted
        ),
        weighted_root_strength=root,
        integrated_month_strength=month,
        branch_relations=branch,
        stem_transformation_judgment=(
            transformation
        ),
    )

    assert weighted == weighted_before
    assert root == root_before
    assert month == month_before
    assert branch == branch_before

    assert (
        transformation
        == transformation_before
    )
