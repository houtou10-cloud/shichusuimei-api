import pytest

from engine.stem_transformation_judgment import (
    apply_judgment_adjustment_steps,
    classify_judgment,
    evaluate_single_transformation_judgment,
    evaluate_stem_transformation_judgment,
    find_result_by_combination,
    get_conflicted_positions,
    get_exposure_strength_score,
    get_max_conflict_severity,
    get_month_support_score,
    get_related_typed_conflicts,
    get_root_strength_score,
    get_severity_adjustment_steps,
    get_transformation_conflict_info,
)


def make_transformation(
    combination_name="甲己",
    result_element="土",
    support_level="strong",
    position_a="year",
    position_b="month",
):
    return {
        "position_a": position_a,
        "stem_a": "甲",
        "position_b": position_b,
        "stem_b": "己",
        "combination_name": combination_name,
        "result_element": result_element,
        "transformation_status": "possible",
        "confidence": "high",
        "month_support": {
            "month_branch": "未",
            "month_element": "土",
            "result_element": result_element,
            "support_level": support_level,
            "support_score": 2.0,
        },
    }


def make_root_result(
    combination_name="甲己",
    result_element="土",
    root_strength="strong",
    has_root=True,
    has_month_root=True,
):
    return {
        "combination_name": combination_name,
        "result_element": result_element,
        "transformation_status": "possible",
        "confidence": "high",
        "root_evaluation": {
            "result_element": result_element,
            "has_root": has_root,
            "has_month_root": has_month_root,
            "root_count": (
                1 if has_root else 0
            ),
            "root_positions": (
                ["month"]
                if has_root
                else []
            ),
            "total_root_score": (
                1.5 if has_root else 0.0
            ),
            "month_root_score": (
                1.5
                if has_month_root
                else 0.0
            ),
            "root_strength": root_strength,
            "roots": [],
        },
    }


def make_exposure_result(
    combination_name="甲己",
    result_element="土",
    exposure_strength="strong",
    has_exposure=True,
    has_external_exposure=True,
):
    return {
        "combination_name": combination_name,
        "result_element": result_element,
        "transformation_status": "possible",
        "confidence": "high",
        "exposure_evaluation": {
            "combination_name": (
                combination_name
            ),
            "result_element": result_element,
            "has_exposure": has_exposure,
            "exposure_count": (
                1 if has_exposure else 0
            ),
            "has_external_exposure": (
                has_external_exposure
            ),
            "external_exposure_count": (
                1
                if has_external_exposure
                else 0
            ),
            "exposure_strength": (
                exposure_strength
            ),
        },
    }


def make_conflicts(
    positions=None,
):
    if positions is None:
        positions = []

    position_conflicts = [
        {
            "position": position,
            "stem": None,
            "combination_count": 2,
            "combination_names": [
                "甲己",
                "甲己",
            ],
            "partner_positions": [],
            "conflict_type": (
                "competing_combination"
            ),
        }
        for position in positions
    ]

    return {
        "has_stem_combination": True,
        "combination_count": 2,
        "has_conflict": bool(
            position_conflicts
        ),
        "conflict_count": len(
            position_conflicts
        ),
        "position_conflict_count": len(
            position_conflicts
        ),
        "duplicate_combination_count": 0,
        "position_conflicts": (
            position_conflicts
        ),
        "duplicate_combinations": [],
        "overall_status": (
            "conflicted"
            if position_conflicts
            else "clear"
        ),
    }


def make_typed_conflicts(
    conflicts=None,
):
    if conflicts is None:
        conflicts = []

    severity_counts = {
        "high": 0,
        "medium": 0,
        "low": 0,
    }

    for conflict in conflicts:
        severity = conflict.get(
            "severity"
        )

        if severity in severity_counts:
            severity_counts[
                severity
            ] += 1

    if severity_counts["high"] > 0:
        overall_severity = "high"
    elif severity_counts["medium"] > 0:
        overall_severity = "medium"
    elif severity_counts["low"] > 0:
        overall_severity = "low"
    else:
        overall_severity = "none"

    return {
        "has_typed_conflict": bool(
            conflicts
        ),
        "typed_conflict_count": len(
            conflicts
        ),
        "severity_counts": (
            severity_counts
        ),
        "overall_severity": (
            overall_severity
        ),
        "conflicts": conflicts,
    }


def make_position_typed_conflict(
    position="year",
    severity="medium",
    technical_type="competing_same_combination",
):
    return {
        "source_type": (
            "position_conflict"
        ),
        "position": position,
        "stem": "甲",
        "combination_count": 2,
        "combination_names": [
            "甲己",
            "甲己",
        ],
        "partner_positions": [
            "month",
            "day",
        ],
        "conflict_type": (
            "争合候補"
        ),
        "technical_type": (
            technical_type
        ),
        "severity": severity,
        "reason": "test",
        "is_provisional": True,
    }


def make_duplicate_typed_conflict(
    combination_name="甲己",
    severity="low",
):
    return {
        "source_type": (
            "duplicate_combination"
        ),
        "combination_name": (
            combination_name
        ),
        "combination_count": 2,
        "pairs": [],
        "conflict_type": (
            "重複干合候補"
        ),
        "technical_type": (
            "duplicated_combination"
        ),
        "severity": severity,
        "reason": "test",
        "is_provisional": True,
    }


# =========================================================
# Score conversion
# =========================================================


def test_get_month_support_score():
    assert (
        get_month_support_score(
            "strong"
        )
        == 4.0
    )

    assert (
        get_month_support_score(
            "supportive"
        )
        == 2.0
    )

    assert (
        get_month_support_score(
            "weak"
        )
        == 0.0
    )


def test_invalid_month_support_score():
    with pytest.raises(
        ValueError,
        match=(
            "不正なmonth support level"
        ),
    ):
        get_month_support_score(
            "invalid"
        )


def test_get_root_strength_score():
    assert (
        get_root_strength_score(
            "strong"
        )
        == 3.0
    )

    assert (
        get_root_strength_score(
            "present"
        )
        == 1.5
    )

    assert (
        get_root_strength_score(
            "none"
        )
        == 0.0
    )


def test_invalid_root_strength_score():
    with pytest.raises(
        ValueError,
        match="不正なroot strength",
    ):
        get_root_strength_score(
            "invalid"
        )


def test_get_exposure_strength_score():
    assert (
        get_exposure_strength_score(
            "strong"
        )
        == 2.0
    )

    assert (
        get_exposure_strength_score(
            "participant_only"
        )
        == 0.5
    )

    assert (
        get_exposure_strength_score(
            "none"
        )
        == 0.0
    )


def test_invalid_exposure_strength_score():
    with pytest.raises(
        ValueError,
        match=(
            "不正なexposure strength"
        ),
    ):
        get_exposure_strength_score(
            "invalid"
        )


# =========================================================
# find_result_by_combination
# =========================================================


def test_find_result_by_combination():
    results = [
        {
            "combination_name": "甲己",
            "value": 1,
        },
        {
            "combination_name": "乙庚",
            "value": 2,
        },
    ]

    result = find_result_by_combination(
        results,
        "乙庚",
    )

    assert result == {
        "combination_name": "乙庚",
        "value": 2,
    }


def test_find_result_by_combination_none():
    results = [
        {
            "combination_name": "甲己",
        },
    ]

    result = find_result_by_combination(
        results,
        "丙辛",
    )

    assert result is None


# =========================================================
# classify_judgment
# =========================================================


def test_classify_strong_candidate():
    result = classify_judgment(
        total_score=9.0,
        month_support_level="strong",
        has_root=True,
        has_external_exposure=True,
    )

    assert result == "strong_candidate"


def test_classify_possible_with_strong_month():
    result = classify_judgment(
        total_score=7.5,
        month_support_level="strong",
        has_root=True,
        has_external_exposure=False,
    )

    assert result == "possible"


def test_classify_possible_with_supportive_month():
    result = classify_judgment(
        total_score=5.5,
        month_support_level="supportive",
        has_root=True,
        has_external_exposure=True,
    )

    assert result == "possible"


def test_classify_weak():
    result = classify_judgment(
        total_score=4.0,
        month_support_level="strong",
        has_root=False,
        has_external_exposure=False,
    )

    assert result == "weak"


def test_classify_unsupported():
    result = classify_judgment(
        total_score=4.5,
        month_support_level="weak",
        has_root=True,
        has_external_exposure=False,
    )

    assert result == "unsupported"


# =========================================================
# Conflict helpers
# =========================================================


def test_get_conflicted_positions_none():
    assert (
        get_conflicted_positions(
            None
        )
        == set()
    )


def test_get_conflicted_positions():
    result = get_conflicted_positions(
        make_conflicts(
            [
                "year",
                "month",
            ]
        )
    )

    assert result == {
        "year",
        "month",
    }


def test_invalid_conflicts_type():
    with pytest.raises(
        TypeError,
        match=(
            "stem_combination_conflictsは"
            "dict型またはNone"
        ),
    ):
        get_conflicted_positions(
            []
        )


def test_invalid_position_conflicts_type():
    with pytest.raises(
        TypeError,
        match="position_conflictsはlist型",
    ):
        get_conflicted_positions(
            {
                "position_conflicts": {},
            }
        )


def test_invalid_position_conflict_item():
    with pytest.raises(
        TypeError,
        match="position_conflictはdict型",
    ):
        get_conflicted_positions(
            {
                "position_conflicts": [
                    [],
                ],
            }
        )


def test_get_transformation_conflict_info_conflicted():
    transformation = (
        make_transformation()
    )

    result = (
        get_transformation_conflict_info(
            transformation,
            make_conflicts(
                ["year"]
            ),
        )
    )

    assert result == {
        "has_conflict": True,
        "conflicted_positions": [
            "year",
        ],
        "adjustment_steps": -1,
        "reason": (
            "competing_combination"
        ),
    }


def test_get_transformation_conflict_info_clear():
    transformation = (
        make_transformation()
    )

    result = (
        get_transformation_conflict_info(
            transformation,
            make_conflicts(
                ["day"]
            ),
        )
    )

    assert result == {
        "has_conflict": False,
        "conflicted_positions": [],
        "adjustment_steps": 0,
        "reason": None,
    }


def test_get_related_typed_conflicts_by_position():
    transformation = (
        make_transformation(
            position_a="year",
            position_b="month",
        )
    )

    related_conflict = (
        make_position_typed_conflict(
            position="year",
            severity="medium",
        )
    )

    unrelated_conflict = (
        make_position_typed_conflict(
            position="day",
            severity="high",
        )
    )

    result = get_related_typed_conflicts(
        transformation,
        make_typed_conflicts(
            [
                related_conflict,
                unrelated_conflict,
            ]
        ),
    )

    assert result == [
        related_conflict,
    ]


def test_get_related_typed_conflicts_by_combination_name():
    transformation = (
        make_transformation(
            combination_name="甲己"
        )
    )

    related_conflict = (
        make_duplicate_typed_conflict(
            combination_name="甲己",
            severity="low",
        )
    )

    unrelated_conflict = (
        make_duplicate_typed_conflict(
            combination_name="丙辛",
            severity="high",
        )
    )

    result = get_related_typed_conflicts(
        transformation,
        make_typed_conflicts(
            [
                related_conflict,
                unrelated_conflict,
            ]
        ),
    )

    assert result == [
        related_conflict,
    ]


def test_get_related_typed_conflicts_none():
    result = get_related_typed_conflicts(
        make_transformation(),
        None,
    )

    assert result == []


def test_get_max_conflict_severity_none():
    assert (
        get_max_conflict_severity(
            []
        )
        == "none"
    )


def test_get_max_conflict_severity_high():
    result = get_max_conflict_severity(
        [
            {
                "severity": "low",
            },
            {
                "severity": "high",
            },
            {
                "severity": "medium",
            },
        ]
    )

    assert result == "high"


def test_get_max_conflict_severity_invalid():
    with pytest.raises(
        ValueError,
        match=(
            "不正なconflict severity"
        ),
    ):
        get_max_conflict_severity(
            [
                {
                    "severity": "invalid",
                },
            ]
        )


def test_get_severity_adjustment_steps():
    assert (
        get_severity_adjustment_steps(
            "none"
        )
        == 0
    )

    assert (
        get_severity_adjustment_steps(
            "low"
        )
        == 0
    )

    assert (
        get_severity_adjustment_steps(
            "medium"
        )
        == -1
    )

    assert (
        get_severity_adjustment_steps(
            "high"
        )
        == -2
    )


def test_get_severity_adjustment_steps_invalid():
    with pytest.raises(
        ValueError,
        match=(
            "不正なconflict severity"
        ),
    ):
        get_severity_adjustment_steps(
            "invalid"
        )


def test_apply_judgment_adjustment_steps_zero():
    assert (
        apply_judgment_adjustment_steps(
            "strong_candidate",
            0,
        )
        == "strong_candidate"
    )


def test_apply_judgment_adjustment_steps_minus_one():
    assert (
        apply_judgment_adjustment_steps(
            "strong_candidate",
            -1,
        )
        == "possible"
    )


def test_apply_judgment_adjustment_steps_minus_two():
    assert (
        apply_judgment_adjustment_steps(
            "strong_candidate",
            -2,
        )
        == "weak"
    )


def test_apply_judgment_adjustment_steps_lower_bound():
    assert (
        apply_judgment_adjustment_steps(
            "weak",
            -10,
        )
        == "unsupported"
    )


def test_apply_judgment_adjustment_steps_invalid_judgment():
    with pytest.raises(
        ValueError,
        match="不正なjudgmentです",
    ):
        apply_judgment_adjustment_steps(
            "invalid",
            -1,
        )


def test_apply_judgment_adjustment_steps_invalid_steps_type():
    with pytest.raises(
        TypeError,
        match=(
            "adjustment_stepsはint型"
        ),
    ):
        apply_judgment_adjustment_steps(
            "possible",
            -1.0,
        )


# =========================================================
# Single judgment
# =========================================================


def test_single_strong_candidate():
    transformation = (
        make_transformation(
            support_level="strong"
        )
    )

    root_result = make_root_result(
        root_strength="strong",
        has_root=True,
        has_month_root=True,
    )

    exposure_result = (
        make_exposure_result(
            exposure_strength="strong",
            has_exposure=True,
            has_external_exposure=True,
        )
    )

    result = (
        evaluate_single_transformation_judgment(
            transformation,
            root_result,
            exposure_result,
        )
    )

    assert (
        result["combination_name"]
        == "甲己"
    )

    assert (
        result["result_element"]
        == "土"
    )

    assert (
        result["position_a"]
        == "year"
    )

    assert (
        result["position_b"]
        == "month"
    )

    assert (
        result["month_support_level"]
        == "strong"
    )

    assert (
        result["month_support_score"]
        == 4.0
    )

    assert (
        result["root_strength"]
        == "strong"
    )

    assert (
        result["root_score"]
        == 3.0
    )

    assert result["has_root"] is True

    assert (
        result["has_month_root"]
        is True
    )

    assert (
        result["exposure_strength"]
        == "strong"
    )

    assert (
        result["exposure_score"]
        == 2.0
    )

    assert (
        result["has_exposure"]
        is True
    )

    assert (
        result[
            "has_external_exposure"
        ]
        is True
    )

    assert (
        result["total_score"]
        == 9.0
    )

    assert (
        result["base_judgment"]
        == "strong_candidate"
    )

    assert (
        result["has_conflict"]
        is False
    )

    assert (
        result["judgment"]
        == "strong_candidate"
    )

    assert (
        result["confidence"]
        == "high"
    )

    assert (
        "strong_month_support"
        in result["supporting_factors"]
    )

    assert (
        "has_transformation_root"
        in result["supporting_factors"]
    )

    assert (
        "has_month_root"
        in result["supporting_factors"]
    )

    assert (
        "has_external_exposure"
        in result["supporting_factors"]
    )

    assert (
        result["limiting_factors"]
        == []
    )


def test_single_strong_candidate_downgraded_by_conflict():
    transformation = (
        make_transformation(
            support_level="strong"
        )
    )

    result = (
        evaluate_single_transformation_judgment(
            transformation,
            make_root_result(
                root_strength="strong",
                has_root=True,
                has_month_root=True,
            ),
            make_exposure_result(
                exposure_strength="strong",
                has_exposure=True,
                has_external_exposure=True,
            ),
            {
                "has_conflict": True,
                "conflicted_positions": [
                    "year",
                ],
                "adjustment_steps": -1,
                "reason": (
                    "competing_combination"
                ),
            },
        )
    )

    assert (
        result["base_judgment"]
        == "strong_candidate"
    )

    assert (
        result["judgment"]
        == "possible"
    )

    assert (
        result["confidence"]
        == "medium"
    )

    assert (
        result["has_conflict"]
        is True
    )

    assert (
        "medium_conflict"
        in result["limiting_factors"]
    )


def test_single_possible():
    transformation = (
        make_transformation(
            support_level="supportive"
        )
    )

    root_result = make_root_result(
        root_strength="strong",
        has_root=True,
        has_month_root=False,
    )

    exposure_result = (
        make_exposure_result(
            exposure_strength="participant_only",
            has_exposure=True,
            has_external_exposure=False,
        )
    )

    result = (
        evaluate_single_transformation_judgment(
            transformation,
            root_result,
            exposure_result,
        )
    )

    assert (
        result["total_score"]
        == 5.5
    )

    assert (
        result["base_judgment"]
        == "possible"
    )

    assert (
        result["judgment"]
        == "possible"
    )

    assert (
        result["confidence"]
        == "medium"
    )


def test_single_possible_downgraded_to_weak():
    transformation = (
        make_transformation(
            support_level="supportive"
        )
    )

    result = (
        evaluate_single_transformation_judgment(
            transformation,
            make_root_result(
                root_strength="strong",
                has_root=True,
                has_month_root=False,
            ),
            make_exposure_result(
                exposure_strength="participant_only",
                has_exposure=True,
                has_external_exposure=False,
            ),
            {
                "has_conflict": True,
                "conflicted_positions": [
                    "year",
                ],
                "adjustment_steps": -1,
                "reason": (
                    "competing_combination"
                ),
            },
        )
    )

    assert (
        result["base_judgment"]
        == "possible"
    )

    assert (
        result["judgment"]
        == "weak"
    )

    assert (
        result["confidence"]
        == "low"
    )


def test_single_weak():
    transformation = (
        make_transformation(
            support_level="strong"
        )
    )

    result = (
        evaluate_single_transformation_judgment(
            transformation,
            make_root_result(
                root_strength="none",
                has_root=False,
                has_month_root=False,
            ),
            make_exposure_result(
                exposure_strength="none",
                has_exposure=False,
                has_external_exposure=False,
            ),
        )
    )

    assert (
        result["base_judgment"]
        == "weak"
    )

    assert (
        result["judgment"]
        == "weak"
    )

    assert (
        result["confidence"]
        == "low"
    )


def test_single_weak_downgraded_to_unsupported():
    transformation = (
        make_transformation(
            support_level="strong"
        )
    )

    result = (
        evaluate_single_transformation_judgment(
            transformation,
            make_root_result(
                root_strength="none",
                has_root=False,
                has_month_root=False,
            ),
            make_exposure_result(
                exposure_strength="none",
                has_exposure=False,
                has_external_exposure=False,
            ),
            {
                "has_conflict": True,
                "conflicted_positions": [
                    "month",
                ],
                "adjustment_steps": -1,
                "reason": (
                    "competing_combination"
                ),
            },
        )
    )

    assert (
        result["base_judgment"]
        == "weak"
    )

    assert (
        result["judgment"]
        == "unsupported"
    )

    assert (
        result["confidence"]
        == "very_low"
    )


def test_single_unsupported():
    transformation = (
        make_transformation(
            support_level="weak"
        )
    )

    result = (
        evaluate_single_transformation_judgment(
            transformation,
            make_root_result(
                root_strength="none",
                has_root=False,
                has_month_root=False,
            ),
            make_exposure_result(
                exposure_strength="none",
                has_exposure=False,
                has_external_exposure=False,
            ),
        )
    )

    assert (
        result["base_judgment"]
        == "unsupported"
    )

    assert (
        result["judgment"]
        == "unsupported"
    )

    assert (
        result["confidence"]
        == "very_low"
    )


def test_single_low_conflict_keeps_strong_candidate():
    result = (
        evaluate_single_transformation_judgment(
            make_transformation(
                support_level="strong"
            ),
            make_root_result(
                root_strength="strong",
                has_root=True,
                has_month_root=True,
            ),
            make_exposure_result(
                exposure_strength="strong",
                has_exposure=True,
                has_external_exposure=True,
            ),
            {
                "has_conflict": True,
                "conflicted_positions": [
                    "year",
                ],
                "adjustment_steps": -1,
                "reason": (
                    "competing_combination"
                ),
            },
            [
                make_duplicate_typed_conflict(
                    combination_name="甲己",
                    severity="low",
                ),
            ],
        )
    )

    assert (
        result["base_judgment"]
        == "strong_candidate"
    )

    assert (
        result["conflict_severity"]
        == "low"
    )

    assert (
        result[
            "conflict_adjustment_steps"
        ]
        == 0
    )

    assert (
        result["judgment"]
        == "strong_candidate"
    )

    assert (
        "low_conflict"
        in result["limiting_factors"]
    )


def test_single_medium_conflict_downgrades_one_step():
    result = (
        evaluate_single_transformation_judgment(
            make_transformation(),
            make_root_result(),
            make_exposure_result(),
            {
                "has_conflict": True,
                "conflicted_positions": [
                    "year",
                ],
                "adjustment_steps": -1,
                "reason": (
                    "competing_combination"
                ),
            },
            [
                make_position_typed_conflict(
                    position="year",
                    severity="medium",
                ),
            ],
        )
    )

    assert (
        result["base_judgment"]
        == "strong_candidate"
    )

    assert (
        result["conflict_severity"]
        == "medium"
    )

    assert (
        result[
            "conflict_adjustment_steps"
        ]
        == -1
    )

    assert (
        result["judgment"]
        == "possible"
    )


def test_single_high_conflict_downgrades_two_steps():
    result = (
        evaluate_single_transformation_judgment(
            make_transformation(),
            make_root_result(),
            make_exposure_result(),
            {
                "has_conflict": True,
                "conflicted_positions": [
                    "year",
                ],
                "adjustment_steps": -1,
                "reason": (
                    "competing_combination"
                ),
            },
            [
                make_position_typed_conflict(
                    position="year",
                    severity="high",
                    technical_type=(
                        "competing_multiple_combinations"
                    ),
                ),
            ],
        )
    )

    assert (
        result["base_judgment"]
        == "strong_candidate"
    )

    assert (
        result["conflict_severity"]
        == "high"
    )

    assert (
        result[
            "conflict_adjustment_steps"
        ]
        == -2
    )

    assert (
        result["judgment"]
        == "weak"
    )

    assert (
        result["confidence"]
        == "low"
    )

    assert (
        "high_conflict"
        in result["limiting_factors"]
    )


# =========================================================
# Invalid single inputs
# =========================================================


def test_invalid_transformation_type():
    with pytest.raises(
        TypeError,
        match="transformationはdict型",
    ):
        evaluate_single_transformation_judgment(
            [],
            {},
            {},
        )


def test_invalid_root_result_type():
    with pytest.raises(
        TypeError,
        match="root_resultはdict型",
    ):
        evaluate_single_transformation_judgment(
            make_transformation(),
            [],
            {},
        )


def test_invalid_exposure_result_type():
    with pytest.raises(
        TypeError,
        match="exposure_resultはdict型",
    ):
        evaluate_single_transformation_judgment(
            make_transformation(),
            make_root_result(),
            [],
        )


def test_invalid_conflict_info_type():
    with pytest.raises(
        TypeError,
        match=(
            "conflict_infoはdict型またはNone"
        ),
    ):
        evaluate_single_transformation_judgment(
            make_transformation(),
            make_root_result(),
            make_exposure_result(),
            [],
        )



def test_invalid_related_typed_conflicts_type():
    with pytest.raises(
        TypeError,
        match=(
            "related_typed_conflictsは"
            "list型またはNone"
        ),
    ):
        evaluate_single_transformation_judgment(
            make_transformation(),
            make_root_result(),
            make_exposure_result(),
            None,
            {},
        )


def test_missing_combination_name():
    transformation = (
        make_transformation()
    )

    del transformation[
        "combination_name"
    ]

    with pytest.raises(
        ValueError,
        match=(
            "combination_nameが必要です"
        ),
    ):
        evaluate_single_transformation_judgment(
            transformation,
            make_root_result(),
            make_exposure_result(),
        )


def test_missing_result_element():
    transformation = (
        make_transformation()
    )

    del transformation[
        "result_element"
    ]

    with pytest.raises(
        ValueError,
        match=(
            "result_elementが必要です"
        ),
    ):
        evaluate_single_transformation_judgment(
            transformation,
            make_root_result(),
            make_exposure_result(),
        )


def test_missing_month_support():
    transformation = (
        make_transformation()
    )

    del transformation[
        "month_support"
    ]

    with pytest.raises(
        ValueError,
        match="month_supportが必要です",
    ):
        evaluate_single_transformation_judgment(
            transformation,
            make_root_result(),
            make_exposure_result(),
        )


def test_missing_month_support_level():
    transformation = (
        make_transformation()
    )

    transformation[
        "month_support"
    ] = {}

    with pytest.raises(
        ValueError,
        match=(
            "support_levelが必要です"
        ),
    ):
        evaluate_single_transformation_judgment(
            transformation,
            make_root_result(),
            make_exposure_result(),
        )


def test_missing_root_evaluation():
    with pytest.raises(
        ValueError,
        match=(
            "root_evaluationが必要です"
        ),
    ):
        evaluate_single_transformation_judgment(
            make_transformation(),
            {},
            make_exposure_result(),
        )


def test_missing_root_strength():
    root_result = make_root_result()

    root_result[
        "root_evaluation"
    ].pop(
        "root_strength"
    )

    with pytest.raises(
        ValueError,
        match="root_strengthが必要です",
    ):
        evaluate_single_transformation_judgment(
            make_transformation(),
            root_result,
            make_exposure_result(),
        )


def test_missing_exposure_evaluation():
    with pytest.raises(
        ValueError,
        match=(
            "exposure_evaluationが必要です"
        ),
    ):
        evaluate_single_transformation_judgment(
            make_transformation(),
            make_root_result(),
            {},
        )


def test_missing_exposure_strength():
    exposure_result = (
        make_exposure_result()
    )

    exposure_result[
        "exposure_evaluation"
    ].pop(
        "exposure_strength"
    )

    with pytest.raises(
        ValueError,
        match=(
            "exposure_strengthが必要です"
        ),
    ):
        evaluate_single_transformation_judgment(
            make_transformation(),
            make_root_result(),
            exposure_result,
        )


# =========================================================
# Collection judgment
# =========================================================


def test_judgment_not_applicable():
    result = (
        evaluate_stem_transformation_judgment(
            {
                "transformations": [],
            },
            {
                "results": [],
            },
            {
                "results": [],
            },
        )
    )

    assert (
        result[
            "has_transformation_candidate"
        ]
        is False
    )

    assert (
        result["judgment_count"]
        == 0
    )

    assert (
        result[
            "strong_candidate_count"
        ]
        == 0
    )

    assert (
        result["possible_count"]
        == 0
    )

    assert (
        result["weak_count"]
        == 0
    )

    assert (
        result["unsupported_count"]
        == 0
    )

    assert (
        result[
            "conflicted_judgment_count"
        ]
        == 0
    )


    assert (
        result["high_conflict_count"]
        == 0
    )

    assert (
        result["medium_conflict_count"]
        == 0
    )

    assert (
        result["low_conflict_count"]
        == 0
    )

    assert (
        result["overall_judgment"]
        == "not_applicable"
    )

    assert (
        result["judgments"]
        == []
    )

    assert (
        result["method"]
        == (
            "stem_transformation_"
            "judgment_v3"
        )
    )

    assert (
        result["status"]
        == (
            "provisional_stem_"
            "transformation_judgment"
        )
    )


def test_all_strong_candidates_without_conflict():
    transformations = {
        "transformations": [
            make_transformation(),
        ],
    }

    roots = {
        "results": [
            make_root_result(),
        ],
    }

    exposures = {
        "results": [
            make_exposure_result(),
        ],
    }

    result = (
        evaluate_stem_transformation_judgment(
            transformations,
            roots,
            exposures,
            make_conflicts([]),
        )
    )

    assert (
        result[
            "strong_candidate_count"
        ]
        == 1
    )

    assert (
        result[
            "conflicted_judgment_count"
        ]
        == 0
    )

    assert (
        result["overall_judgment"]
        == "strong_candidate"
    )


def test_collection_strong_candidate_downgraded():
    transformations = {
        "transformations": [
            make_transformation(),
        ],
    }

    result = (
        evaluate_stem_transformation_judgment(
            transformations,
            {
                "results": [
                    make_root_result(),
                ],
            },
            {
                "results": [
                    make_exposure_result(),
                ],
            },
            make_conflicts(
                ["year"]
            ),
        )
    )

    assert (
        result[
            "strong_candidate_count"
        ]
        == 0
    )

    assert (
        result["possible_count"]
        == 1
    )

    assert (
        result[
            "conflicted_judgment_count"
        ]
        == 1
    )

    assert (
        result["overall_judgment"]
        == "possible"
    )


def test_unrelated_conflict_does_not_change_judgment():
    transformations = {
        "transformations": [
            make_transformation(
                position_a="year",
                position_b="month",
            ),
        ],
    }

    result = (
        evaluate_stem_transformation_judgment(
            transformations,
            {
                "results": [
                    make_root_result(),
                ],
            },
            {
                "results": [
                    make_exposure_result(),
                ],
            },
            make_conflicts(
                ["day"]
            ),
        )
    )

    assert (
        result[
            "strong_candidate_count"
        ]
        == 1
    )

    assert (
        result[
            "conflicted_judgment_count"
        ]
        == 0
    )

    assert (
        result["overall_judgment"]
        == "strong_candidate"
    )


def test_mixed_judgments_with_only_one_conflicted():
    transformation_a = (
        make_transformation(
            combination_name="甲己",
            result_element="土",
            support_level="strong",
            position_a="year",
            position_b="month",
        )
    )

    transformation_b = (
        make_transformation(
            combination_name="丙辛",
            result_element="水",
            support_level="strong",
            position_a="day",
            position_b="hour",
        )
    )

    roots = {
        "results": [
            make_root_result(
                combination_name="甲己",
                result_element="土",
            ),
            make_root_result(
                combination_name="丙辛",
                result_element="水",
            ),
        ],
    }

    exposures = {
        "results": [
            make_exposure_result(
                combination_name="甲己",
                result_element="土",
            ),
            make_exposure_result(
                combination_name="丙辛",
                result_element="水",
            ),
        ],
    }

    result = (
        evaluate_stem_transformation_judgment(
            {
                "transformations": [
                    transformation_a,
                    transformation_b,
                ],
            },
            roots,
            exposures,
            make_conflicts(
                ["year"]
            ),
        )
    )

    assert (
        result["judgment_count"]
        == 2
    )

    assert (
        result[
            "strong_candidate_count"
        ]
        == 1
    )

    assert (
        result["possible_count"]
        == 1
    )

    assert (
        result[
            "conflicted_judgment_count"
        ]
        == 1
    )

    assert (
        result["overall_judgment"]
        == "mixed"
    )


def test_collection_low_conflict_keeps_judgment():
    result = (
        evaluate_stem_transformation_judgment(
            {
                "transformations": [
                    make_transformation(),
                ],
            },
            {
                "results": [
                    make_root_result(),
                ],
            },
            {
                "results": [
                    make_exposure_result(),
                ],
            },
            make_conflicts(
                ["year"]
            ),
            make_typed_conflicts(
                [
                    make_duplicate_typed_conflict(
                        combination_name="甲己",
                        severity="low",
                    ),
                ]
            ),
        )
    )

    assert (
        result[
            "strong_candidate_count"
        ]
        == 1
    )

    assert (
        result["low_conflict_count"]
        == 1
    )

    assert (
        result[
            "conflicted_judgment_count"
        ]
        == 1
    )


def test_collection_medium_conflict_downgrades_one_step():
    result = (
        evaluate_stem_transformation_judgment(
            {
                "transformations": [
                    make_transformation(),
                ],
            },
            {
                "results": [
                    make_root_result(),
                ],
            },
            {
                "results": [
                    make_exposure_result(),
                ],
            },
            make_conflicts(
                ["year"]
            ),
            make_typed_conflicts(
                [
                    make_position_typed_conflict(
                        position="year",
                        severity="medium",
                    ),
                ]
            ),
        )
    )

    assert (
        result["possible_count"]
        == 1
    )

    assert (
        result[
            "medium_conflict_count"
        ]
        == 1
    )

    assert (
        result["overall_judgment"]
        == "possible"
    )


def test_collection_high_conflict_downgrades_two_steps():
    result = (
        evaluate_stem_transformation_judgment(
            {
                "transformations": [
                    make_transformation(),
                ],
            },
            {
                "results": [
                    make_root_result(),
                ],
            },
            {
                "results": [
                    make_exposure_result(),
                ],
            },
            make_conflicts(
                ["year"]
            ),
            make_typed_conflicts(
                [
                    make_position_typed_conflict(
                        position="year",
                        severity="high",
                        technical_type=(
                            "competing_multiple_combinations"
                        ),
                    ),
                ]
            ),
        )
    )

    assert (
        result["weak_count"]
        == 1
    )

    assert (
        result["high_conflict_count"]
        == 1
    )

    assert (
        result["overall_judgment"]
        == "weak"
    )


def test_collection_unrelated_high_conflict_does_not_affect():
    result = (
        evaluate_stem_transformation_judgment(
            {
                "transformations": [
                    make_transformation(
                        position_a="year",
                        position_b="month",
                    ),
                ],
            },
            {
                "results": [
                    make_root_result(),
                ],
            },
            {
                "results": [
                    make_exposure_result(),
                ],
            },
            make_conflicts(
                ["day"]
            ),
            make_typed_conflicts(
                [
                    make_position_typed_conflict(
                        position="day",
                        severity="high",
                        technical_type=(
                            "competing_multiple_combinations"
                        ),
                    ),
                ]
            ),
        )
    )

    assert (
        result[
            "strong_candidate_count"
        ]
        == 1
    )

    assert (
        result["high_conflict_count"]
        == 0
    )

    assert (
        result[
            "conflicted_judgment_count"
        ]
        == 0
    )


# =========================================================
# Collection validation
# =========================================================


def test_invalid_stem_transformations_type():
    with pytest.raises(
        TypeError,
        match=(
            "stem_transformationsはdict型"
        ),
    ):
        evaluate_stem_transformation_judgment(
            [],
            {},
            {},
        )


def test_invalid_transformation_roots_type():
    with pytest.raises(
        TypeError,
        match=(
            "transformation_rootsはdict型"
        ),
    ):
        evaluate_stem_transformation_judgment(
            {
                "transformations": [],
            },
            [],
            {},
        )


def test_invalid_transformation_exposures_type():
    with pytest.raises(
        TypeError,
        match=(
            "transformation_exposuresはdict型"
        ),
    ):
        evaluate_stem_transformation_judgment(
            {
                "transformations": [],
            },
            {
                "results": [],
            },
            [],
        )


def test_invalid_stem_combination_conflicts_type():
    with pytest.raises(
        TypeError,
        match=(
            "stem_combination_conflictsは"
            "dict型またはNone"
        ),
    ):
        evaluate_stem_transformation_judgment(
            {
                "transformations": [],
            },
            {
                "results": [],
            },
            {
                "results": [],
            },
            [],
        )



def test_invalid_stem_combination_conflict_types_type():
    with pytest.raises(
        TypeError,
        match=(
            "stem_combination_conflict_typesは"
            "dict型またはNone"
        ),
    ):
        evaluate_stem_transformation_judgment(
            {
                "transformations": [],
            },
            {
                "results": [],
            },
            {
                "results": [],
            },
            None,
            [],
        )


def test_invalid_transformations_list():
    with pytest.raises(
        TypeError,
        match="transformationsはlist型",
    ):
        evaluate_stem_transformation_judgment(
            {
                "transformations": {},
            },
            {
                "results": [],
            },
            {
                "results": [],
            },
        )


def test_invalid_root_results_list():
    with pytest.raises(
        TypeError,
        match=(
            "transformation_rootsの"
            "resultsはlist型"
        ),
    ):
        evaluate_stem_transformation_judgment(
            {
                "transformations": [],
            },
            {
                "results": {},
            },
            {
                "results": [],
            },
        )


def test_invalid_exposure_results_list():
    with pytest.raises(
        TypeError,
        match=(
            "transformation_exposuresの"
            "resultsはlist型"
        ),
    ):
        evaluate_stem_transformation_judgment(
            {
                "transformations": [],
            },
            {
                "results": [],
            },
            {
                "results": {},
            },
        )


def test_missing_root_result():
    transformations = {
        "transformations": [
            make_transformation(),
        ],
    }

    with pytest.raises(
        ValueError,
        match=(
            "対応する通根評価が"
            "見つかりません"
        ),
    ):
        evaluate_stem_transformation_judgment(
            transformations,
            {
                "results": [],
            },
            {
                "results": [
                    make_exposure_result(),
                ],
            },
        )


def test_missing_exposure_result():
    transformations = {
        "transformations": [
            make_transformation(),
        ],
    }

    with pytest.raises(
        ValueError,
        match=(
            "対応する透干評価が"
            "見つかりません"
        ),
    ):
        evaluate_stem_transformation_judgment(
            transformations,
            {
                "results": [
                    make_root_result(),
                ],
            },
            {
                "results": [],
            },
        )


def test_result_contains_notes():
    result = (
        evaluate_stem_transformation_judgment(
            {
                "transformations": [],
            },
            {
                "results": [],
            },
            {
                "results": [],
            },
        )
    )

    assert isinstance(
        result["notes"],
        list,
    )

    assert len(
        result["notes"]
    ) >= 1
