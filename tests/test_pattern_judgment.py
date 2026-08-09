import pytest

from engine.pattern_judgment import (
    base_candidate_score,
    branch_adjustment,
    classify_establishment,
    clamp_score,
    collect_breaking_factors,
    collect_rescue_factors,
    confidence_from_score,
    determine_primary_judgment,
    evaluate_pattern_judgment,
    exposure_adjustment,
    extract_branch_evidence,
    extract_final_strength_evidence,
    extract_transformation_evidence,
    judge_pattern_candidate,
    judgment_priority,
    school_rule_adjustment,
    transformation_adjustment,
    validate_pattern_candidates,
)


def make_candidate(
    pattern="偏財格",
    technical_pattern="indirect_wealth",
    pattern_group="standard_pattern",
    confidence="medium",
    is_exposed=False,
    exposure_positions=None,
    requires_school_rule=False,
    candidate_status="provisional_candidate",
):
    if exposure_positions is None:
        exposure_positions = []

    return {
        "pattern": pattern,
        "technical_pattern": (
            technical_pattern
        ),
        "pattern_group": (
            pattern_group
        ),
        "confidence": confidence,
        "candidate_status": (
            candidate_status
        ),
        "is_exposed": is_exposed,
        "exposure_positions": (
            exposure_positions
        ),
        "requires_school_rule": (
            requires_school_rule
        ),
        "source": (
            "month_main_hidden_stem"
        ),
        "month_branch": "未",
        "month_main_hidden_stem": "己",
        "ten_god": "偏財",
        "is_provisional": True,
    }


def make_pattern_candidates(
    candidates=None,
    primary_candidate=None,
):
    if candidates is None:
        candidates = []

    if primary_candidate is None:
        primary_candidate = (
            candidates[0]
            if candidates
            else None
        )

    return {
        "has_candidate": bool(
            candidates
        ),
        "candidate_count": len(
            candidates
        ),
        "primary_candidate": (
            primary_candidate
        ),
        "candidates": candidates,
        "method": (
            "pattern_candidates_v1"
        ),
        "status": (
            "provisional_pattern_candidates"
        ),
    }


def make_final_strength(
    final_score=50.0,
    technical_label="balanced",
    label="中和",
    confidence="high",
):
    return {
        "final_score": final_score,
        "technical_label": (
            technical_label
        ),
        "label": label,
        "confidence": confidence,
        "method": (
            "final_strength_judgment_v2"
        ),
    }


def make_transformation_judgment(
    has_candidate=False,
    conflicted_count=0,
    overall_judgment="not_applicable",
):
    return {
        "has_transformation_candidate": (
            has_candidate
        ),
        "conflicted_judgment_count": (
            conflicted_count
        ),
        "overall_judgment": (
            overall_judgment
        ),
    }


def make_branch_relation_strength(
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
        result[
            "adjustment"
        ] = adjustment

    if total_score is not None:
        result[
            "total_score"
        ] = total_score

    return result


# =========================================================
# clamp / confidence
# =========================================================


def test_clamp_score_normal():
    assert (
        clamp_score(
            65.4321
        )
        == 65.43
    )


def test_clamp_score_upper():
    assert (
        clamp_score(
            150
        )
        == 100.0
    )


def test_clamp_score_lower():
    assert (
        clamp_score(
            -10
        )
        == 0.0
    )


def test_clamp_score_invalid_type():
    with pytest.raises(
        TypeError,
        match="valueは数値",
    ):
        clamp_score(
            "60"
        )


@pytest.mark.parametrize(
    (
        "score",
        "expected",
    ),
    [
        (80.0, "high"),
        (75.0, "high"),
        (74.99, "medium"),
        (50.0, "medium"),
        (49.99, "low"),
        (10.0, "low"),
    ],
)
def test_confidence_from_score(
    score,
    expected,
):
    assert (
        confidence_from_score(
            score
        )
        == expected
    )


def test_confidence_from_score_invalid_type():
    with pytest.raises(
        TypeError,
        match="scoreは数値",
    ):
        confidence_from_score(
            "75"
        )


# =========================================================
# validate_pattern_candidates
# =========================================================


def test_validate_pattern_candidates():
    validate_pattern_candidates(
        make_pattern_candidates(
            [
                make_candidate(),
            ]
        )
    )


def test_validate_pattern_candidates_invalid_type():
    with pytest.raises(
        TypeError,
        match=(
            "pattern_candidatesは"
            "dict型"
        ),
    ):
        validate_pattern_candidates(
            []
        )


def test_validate_pattern_candidates_missing_key():
    data = make_pattern_candidates(
        [
            make_candidate(),
        ]
    )

    data.pop(
        "candidate_count"
    )

    with pytest.raises(
        ValueError,
        match=(
            "必要なキーがありません"
        ),
    ):
        validate_pattern_candidates(
            data
        )


def test_validate_pattern_candidates_invalid_has_candidate():
    data = make_pattern_candidates()

    data[
        "has_candidate"
    ] = 1

    with pytest.raises(
        TypeError,
        match=(
            "has_candidateはbool型"
        ),
    ):
        validate_pattern_candidates(
            data
        )


def test_validate_pattern_candidates_invalid_candidate_count():
    data = make_pattern_candidates()

    data[
        "candidate_count"
    ] = "0"

    with pytest.raises(
        TypeError,
        match=(
            "candidate_countはint型"
        ),
    ):
        validate_pattern_candidates(
            data
        )


def test_validate_pattern_candidates_invalid_candidates():
    data = make_pattern_candidates()

    data[
        "candidates"
    ] = {}

    with pytest.raises(
        TypeError,
        match=(
            "candidatesはlist型"
        ),
    ):
        validate_pattern_candidates(
            data
        )


def test_validate_pattern_candidates_invalid_primary():
    data = make_pattern_candidates()

    data[
        "primary_candidate"
    ] = []

    with pytest.raises(
        TypeError,
        match=(
            "primary_candidateは"
            "dict型またはNone"
        ),
    ):
        validate_pattern_candidates(
            data
        )


# =========================================================
# evidence extraction
# =========================================================


def test_extract_final_strength_evidence_none():
    result = (
        extract_final_strength_evidence(
            None
        )
    )

    assert result == {
        "available": False,
        "final_score": None,
        "technical_label": None,
        "label": None,
        "confidence": None,
    }


def test_extract_final_strength_evidence_available():
    data = make_final_strength(
        final_score=61.2,
        technical_label="strong",
        label="身強",
        confidence="high",
    )

    result = (
        extract_final_strength_evidence(
            data
        )
    )

    assert result == {
        "available": True,
        "final_score": 61.2,
        "technical_label": "strong",
        "label": "身強",
        "confidence": "high",
    }


def test_extract_final_strength_evidence_invalid_type():
    with pytest.raises(
        TypeError,
        match=(
            "final_strength_judgmentは"
            "dict型またはNone"
        ),
    ):
        extract_final_strength_evidence(
            []
        )


def test_extract_transformation_evidence_none():
    result = (
        extract_transformation_evidence(
            None
        )
    )

    assert result == {
        "available": False,
        "has_candidate": False,
        "conflicted_count": 0,
        "overall_judgment": None,
    }


def test_extract_transformation_evidence_available():
    data = (
        make_transformation_judgment(
            has_candidate=True,
            conflicted_count=2,
            overall_judgment="mixed",
        )
    )

    result = (
        extract_transformation_evidence(
            data
        )
    )

    assert result == {
        "available": True,
        "has_candidate": True,
        "conflicted_count": 2,
        "overall_judgment": "mixed",
    }


def test_extract_transformation_evidence_invalid_count_defaults_zero():
    result = (
        extract_transformation_evidence(
            {
                "has_transformation_candidate": True,
                "conflicted_judgment_count": (
                    "invalid"
                ),
                "overall_judgment": "mixed",
            }
        )
    )

    assert (
        result[
            "conflicted_count"
        ]
        == 0
    )


def test_extract_transformation_evidence_invalid_type():
    with pytest.raises(
        TypeError,
        match=(
            "stem_transformation_judgmentは"
            "dict型またはNone"
        ),
    ):
        extract_transformation_evidence(
            []
        )


def test_extract_branch_evidence_none():
    result = (
        extract_branch_evidence(
            None
        )
    )

    assert result == {
        "available": False,
        "adjustment": 0.0,
        "total_score": None,
    }


def test_extract_branch_evidence_explicit_adjustment():
    result = (
        extract_branch_evidence(
            make_branch_relation_strength(
                strength_adjustment=-2.5,
                total_score=-4.0,
            )
        )
    )

    assert result == {
        "available": True,
        "adjustment": -2.5,
        "total_score": -4.0,
    }


def test_extract_branch_evidence_total_score_only():
    result = (
        extract_branch_evidence(
            make_branch_relation_strength(
                total_score=-4.0,
            )
        )
    )

    assert result == {
        "available": True,
        "adjustment": 0.0,
        "total_score": -4.0,
    }


def test_extract_branch_evidence_priority():
    result = (
        extract_branch_evidence(
            make_branch_relation_strength(
                strength_adjustment=1.0,
                day_master_adjustment=2.0,
                adjustment=3.0,
            )
        )
    )

    assert (
        result["adjustment"]
        == 1.0
    )


def test_extract_branch_evidence_invalid_type():
    with pytest.raises(
        TypeError,
        match=(
            "branch_relation_strengthは"
            "dict型またはNone"
        ),
    ):
        extract_branch_evidence(
            []
        )


# =========================================================
# candidate score helpers
# =========================================================


@pytest.mark.parametrize(
    (
        "confidence",
        "expected",
    ),
    [
        ("high", 70.0),
        ("medium", 60.0),
        ("low", 50.0),
        (None, 55.0),
        ("unknown", 55.0),
    ],
)
def test_base_candidate_score(
    confidence,
    expected,
):
    candidate = make_candidate(
        confidence=confidence
    )

    assert (
        base_candidate_score(
            candidate
        )
        == expected
    )


def test_base_candidate_score_invalid_type():
    with pytest.raises(
        TypeError,
        match=(
            "candidateはdict型"
        ),
    ):
        base_candidate_score(
            []
        )


def test_exposure_adjustment_standard_exposed():
    candidate = make_candidate(
        technical_pattern="indirect_wealth",
        is_exposed=True,
    )

    assert (
        exposure_adjustment(
            candidate
        )
        == 10.0
    )


def test_exposure_adjustment_standard_not_exposed():
    candidate = make_candidate(
        technical_pattern="indirect_wealth",
        is_exposed=False,
    )

    assert (
        exposure_adjustment(
            candidate
        )
        == 0.0
    )


def test_exposure_adjustment_special_pattern():
    candidate = make_candidate(
        pattern="建禄格",
        technical_pattern="jianlu",
        pattern_group="special_month_pattern",
        is_exposed=True,
    )

    assert (
        exposure_adjustment(
            candidate
        )
        == 0.0
    )


def test_exposure_adjustment_invalid_type():
    with pytest.raises(
        TypeError,
        match=(
            "candidateはdict型"
        ),
    ):
        exposure_adjustment(
            []
        )


def test_school_rule_adjustment_true():
    candidate = make_candidate(
        requires_school_rule=True
    )

    assert (
        school_rule_adjustment(
            candidate
        )
        == -15.0
    )


def test_school_rule_adjustment_false():
    candidate = make_candidate(
        requires_school_rule=False
    )

    assert (
        school_rule_adjustment(
            candidate
        )
        == 0.0
    )


def test_school_rule_adjustment_invalid_type():
    with pytest.raises(
        TypeError,
        match=(
            "candidateはdict型"
        ),
    ):
        school_rule_adjustment(
            []
        )


def test_transformation_adjustment_no_conflict():
    candidate = make_candidate()

    result = (
        transformation_adjustment(
            candidate,
            make_transformation_judgment(
                has_candidate=True,
                conflicted_count=0,
            ),
        )
    )

    assert result == 0.0


def test_transformation_adjustment_with_conflict():
    candidate = make_candidate()

    result = (
        transformation_adjustment(
            candidate,
            make_transformation_judgment(
                has_candidate=True,
                conflicted_count=1,
            ),
        )
    )

    assert result == -5.0


def test_transformation_adjustment_none():
    assert (
        transformation_adjustment(
            make_candidate(),
            None,
        )
        == 0.0
    )


def test_transformation_adjustment_invalid_candidate():
    with pytest.raises(
        TypeError,
        match=(
            "candidateはdict型"
        ),
    ):
        transformation_adjustment(
            [],
            None,
        )


def test_branch_adjustment_positive():
    result = branch_adjustment(
        make_branch_relation_strength(
            strength_adjustment=3.0,
        )
    )

    assert result == 3.0


def test_branch_adjustment_negative():
    result = branch_adjustment(
        make_branch_relation_strength(
            strength_adjustment=-2.0,
        )
    )

    assert result == -2.0


def test_branch_adjustment_clamped_high():
    result = branch_adjustment(
        make_branch_relation_strength(
            strength_adjustment=20.0,
        )
    )

    assert result == 5.0


def test_branch_adjustment_clamped_low():
    result = branch_adjustment(
        make_branch_relation_strength(
            strength_adjustment=-20.0,
        )
    )

    assert result == -5.0


def test_branch_adjustment_total_score_only():
    result = branch_adjustment(
        make_branch_relation_strength(
            total_score=-4.0,
        )
    )

    assert result == 0.0


# =========================================================
# breaking factors
# =========================================================


def test_breaking_factor_not_exposed_standard():
    candidate = make_candidate(
        is_exposed=False
    )

    factors = (
        collect_breaking_factors(
            candidate
        )
    )

    types = {
        factor["type"]
        for factor in factors
    }

    assert (
        "main_hidden_stem_not_exposed"
        in types
    )


def test_breaking_factor_exposed_standard_no_not_exposed_factor():
    candidate = make_candidate(
        is_exposed=True
    )

    factors = (
        collect_breaking_factors(
            candidate
        )
    )

    types = {
        factor["type"]
        for factor in factors
    }

    assert (
        "main_hidden_stem_not_exposed"
        not in types
    )


def test_breaking_factor_transformation_conflict():
    factors = (
        collect_breaking_factors(
            make_candidate(),
            make_transformation_judgment(
                has_candidate=True,
                conflicted_count=1,
            ),
        )
    )

    types = {
        factor["type"]
        for factor in factors
    }

    assert (
        "stem_transformation_conflict"
        in types
    )


def test_breaking_factor_negative_branch():
    factors = (
        collect_breaking_factors(
            make_candidate(),
            None,
            make_branch_relation_strength(
                strength_adjustment=-2.0,
            ),
        )
    )

    factor = next(
        item
        for item in factors
        if (
            item["type"]
            == "negative_branch_adjustment"
        )
    )

    assert (
        factor["severity"]
        == "low"
    )

    assert (
        factor["value"]
        == -2.0
    )


def test_breaking_factor_negative_branch_medium():
    factors = (
        collect_breaking_factors(
            make_candidate(),
            None,
            make_branch_relation_strength(
                strength_adjustment=-3.0,
            ),
        )
    )

    factor = next(
        item
        for item in factors
        if (
            item["type"]
            == "negative_branch_adjustment"
        )
    )

    assert (
        factor["severity"]
        == "medium"
    )


def test_breaking_factor_school_rule():
    candidate = make_candidate(
        requires_school_rule=True
    )

    factors = (
        collect_breaking_factors(
            candidate
        )
    )

    types = {
        factor["type"]
        for factor in factors
    }

    assert (
        "school_rule_dependency"
        in types
    )


def test_breaking_factor_invalid_candidate():
    with pytest.raises(
        TypeError,
        match=(
            "candidateはdict型"
        ),
    ):
        collect_breaking_factors(
            []
        )


# =========================================================
# rescue factors
# =========================================================


def test_rescue_factor_exposed():
    factors = (
        collect_rescue_factors(
            make_candidate(
                is_exposed=True
            )
        )
    )

    types = {
        factor["type"]
        for factor in factors
    }

    assert (
        "main_hidden_stem_exposed"
        in types
    )


def test_rescue_factor_balanced_day_master():
    factors = (
        collect_rescue_factors(
            make_candidate(),
            make_final_strength(
                technical_label="balanced",
                label="中和",
            ),
        )
    )

    types = {
        factor["type"]
        for factor in factors
    }

    assert (
        "balanced_day_master"
        in types
    )


def test_rescue_factor_positive_branch():
    factors = (
        collect_rescue_factors(
            make_candidate(),
            None,
            make_branch_relation_strength(
                strength_adjustment=2.0,
            ),
        )
    )

    factor = next(
        item
        for item in factors
        if (
            item["type"]
            == "positive_branch_adjustment"
        )
    )

    assert (
        factor["strength"]
        == "low"
    )

    assert (
        factor["value"]
        == 2.0
    )


def test_rescue_factor_positive_branch_medium():
    factors = (
        collect_rescue_factors(
            make_candidate(),
            None,
            make_branch_relation_strength(
                strength_adjustment=3.0,
            ),
        )
    )

    factor = next(
        item
        for item in factors
        if (
            item["type"]
            == "positive_branch_adjustment"
        )
    )

    assert (
        factor["strength"]
        == "medium"
    )


def test_rescue_factor_invalid_candidate():
    with pytest.raises(
        TypeError,
        match=(
            "candidateはdict型"
        ),
    ):
        collect_rescue_factors(
            []
        )


# =========================================================
# classify_establishment
# =========================================================


def test_classify_establishment_strong():
    result = (
        classify_establishment(
            make_candidate(),
            75.0,
        )
    )

    assert result == {
        "establishment_status": "strong",
        "final_judgment": (
            "provisional_established"
        ),
    }


def test_classify_establishment_possible():
    result = (
        classify_establishment(
            make_candidate(),
            60.0,
        )
    )

    assert result == {
        "establishment_status": "possible",
        "final_judgment": (
            "provisional_possible"
        ),
    }


def test_classify_establishment_weakened():
    result = (
        classify_establishment(
            make_candidate(),
            50.0,
        )
    )

    assert result == {
        "establishment_status": "weakened",
        "final_judgment": (
            "provisional_weakened"
        ),
    }


def test_classify_establishment_school_rule():
    result = (
        classify_establishment(
            make_candidate(
                requires_school_rule=True
            ),
            100.0,
        )
    )

    assert result == {
        "establishment_status": (
            "requires_school_rule"
        ),
        "final_judgment": (
            "requires_school_rule"
        ),
    }


def test_classify_establishment_invalid_candidate():
    with pytest.raises(
        TypeError,
        match=(
            "candidateはdict型"
        ),
    ):
        classify_establishment(
            [],
            60.0,
        )


def test_classify_establishment_invalid_score():
    with pytest.raises(
        TypeError,
        match=(
            "scoreは数値"
        ),
    ):
        classify_establishment(
            make_candidate(),
            "60",
        )


# =========================================================
# judge_pattern_candidate
# =========================================================


def test_judge_standard_unexposed_possible():
    candidate = make_candidate(
        confidence="medium",
        is_exposed=False,
    )

    result = (
        judge_pattern_candidate(
            candidate,
            make_final_strength(),
            make_transformation_judgment(),
            make_branch_relation_strength(
                total_score=-4.0,
            ),
        )
    )

    assert (
        result["base_score"]
        == 60.0
    )

    assert (
        result["exposure_adjustment"]
        == 0.0
    )

    assert (
        result[
            "transformation_adjustment"
        ]
        == 0.0
    )

    assert (
        result["branch_adjustment"]
        == 0.0
    )

    assert (
        result["establishment_score"]
        == 60.0
    )

    assert (
        result["establishment_status"]
        == "possible"
    )

    assert (
        result["final_judgment"]
        == "provisional_possible"
    )

    assert (
        result["confidence"]
        == "medium"
    )


def test_judge_standard_exposed_strong():
    candidate = make_candidate(
        confidence="high",
        is_exposed=True,
        exposure_positions=[
            "month",
        ],
    )

    result = (
        judge_pattern_candidate(
            candidate
        )
    )

    assert (
        result["base_score"]
        == 70.0
    )

    assert (
        result["exposure_adjustment"]
        == 10.0
    )

    assert (
        result["establishment_score"]
        == 80.0
    )

    assert (
        result["establishment_status"]
        == "strong"
    )

    assert (
        result["final_judgment"]
        == "provisional_established"
    )

    assert (
        result["confidence"]
        == "high"
    )


def test_judge_transformation_conflict_reduces_score():
    candidate = make_candidate(
        confidence="medium",
        is_exposed=False,
    )

    result = (
        judge_pattern_candidate(
            candidate,
            None,
            make_transformation_judgment(
                has_candidate=True,
                conflicted_count=1,
            ),
            None,
        )
    )

    assert (
        result[
            "transformation_adjustment"
        ]
        == -5.0
    )

    assert (
        result["establishment_score"]
        == 55.0
    )

    assert (
        result["establishment_status"]
        == "possible"
    )


def test_judge_negative_branch_can_weaken():
    candidate = make_candidate(
        confidence="medium",
        is_exposed=False,
    )

    result = (
        judge_pattern_candidate(
            candidate,
            None,
            None,
            make_branch_relation_strength(
                strength_adjustment=-5.0,
            ),
        )
    )

    assert (
        result["branch_adjustment"]
        == -5.0
    )

    assert (
        result["establishment_score"]
        == 55.0
    )


def test_judge_school_rule_candidate():
    candidate = make_candidate(
        pattern="羊刃格",
        technical_pattern="yangren",
        pattern_group="special_month_pattern",
        confidence="medium",
        requires_school_rule=True,
        candidate_status=(
            "requires_school_rule"
        ),
    )

    result = (
        judge_pattern_candidate(
            candidate
        )
    )

    assert (
        result[
            "school_rule_adjustment"
        ]
        == -15.0
    )

    assert (
        result["establishment_status"]
        == "requires_school_rule"
    )

    assert (
        result["final_judgment"]
        == "requires_school_rule"
    )


def test_judge_pattern_candidate_invalid_type():
    with pytest.raises(
        TypeError,
        match=(
            "candidateはdict型"
        ),
    ):
        judge_pattern_candidate(
            []
        )


# =========================================================
# judgment priority / primary
# =========================================================


def make_judgment(
    technical_pattern="indirect_wealth",
    status="possible",
    score=60.0,
):
    return {
        "technical_pattern": (
            technical_pattern
        ),
        "establishment_status": status,
        "establishment_score": score,
    }


def test_judgment_priority_strong():
    result = judgment_priority(
        make_judgment(
            status="strong",
            score=80.0,
        )
    )

    assert result == (
        4,
        80.0,
    )


def test_judgment_priority_invalid_type():
    with pytest.raises(
        TypeError,
        match=(
            "judgmentはdict型"
        ),
    ):
        judgment_priority(
            []
        )


def test_determine_primary_judgment_empty():
    assert (
        determine_primary_judgment(
            []
        )
        is None
    )


def test_determine_primary_judgment_prefers_candidate():
    a = make_judgment(
        technical_pattern="direct_officer",
        status="strong",
        score=90.0,
    )

    b = make_judgment(
        technical_pattern="indirect_wealth",
        status="possible",
        score=60.0,
    )

    preferred = make_candidate(
        technical_pattern="indirect_wealth"
    )

    result = (
        determine_primary_judgment(
            [
                a,
                b,
            ],
            preferred_candidate=preferred,
        )
    )

    assert result is b


def test_determine_primary_judgment_fallback_highest():
    a = make_judgment(
        technical_pattern="direct_officer",
        status="strong",
        score=80.0,
    )

    b = make_judgment(
        technical_pattern="indirect_wealth",
        status="possible",
        score=70.0,
    )

    result = (
        determine_primary_judgment(
            [
                a,
                b,
            ]
        )
    )

    assert result is a


def test_determine_primary_judgment_invalid_type():
    with pytest.raises(
        TypeError,
        match=(
            "judgmentsはlist型"
        ),
    ):
        determine_primary_judgment(
            {}
        )


def test_determine_primary_judgment_invalid_item():
    with pytest.raises(
        TypeError,
        match=(
            "judgmentはdict型"
        ),
    ):
        determine_primary_judgment(
            [
                [],
            ]
        )


# =========================================================
# evaluate_pattern_judgment
# =========================================================


def test_evaluate_pattern_judgment_no_candidate():
    pattern_candidates = (
        make_pattern_candidates()
    )

    result = (
        evaluate_pattern_judgment(
            pattern_candidates
        )
    )

    assert (
        result[
            "has_pattern_candidate"
        ]
        is False
    )

    assert (
        result["has_pattern"]
        is False
    )

    assert (
        result["judgment_count"]
        == 0
    )

    assert (
        result["primary_pattern"]
        is None
    )

    assert (
        result["technical_pattern"]
        is None
    )

    assert (
        result["primary_judgment"]
        is None
    )

    assert (
        result["judgments"]
        == []
    )

    assert (
        result["overall_judgment"]
        == "not_applicable"
    )

    assert (
        result["method"]
        == "pattern_judgment_v1"
    )

    assert (
        result["status"]
        == "provisional_pattern_judgment"
    )


def test_evaluate_pattern_judgment_single_standard():
    candidate = make_candidate(
        pattern="偏財格",
        technical_pattern="indirect_wealth",
        confidence="medium",
        is_exposed=False,
    )

    pattern_candidates = (
        make_pattern_candidates(
            [
                candidate,
            ],
            primary_candidate=candidate,
        )
    )

    result = (
        evaluate_pattern_judgment(
            pattern_candidates,
            make_final_strength(),
            make_transformation_judgment(),
            make_branch_relation_strength(
                total_score=-4.0,
            ),
        )
    )

    assert (
        result[
            "has_pattern_candidate"
        ]
        is True
    )

    assert (
        result["has_pattern"]
        is True
    )

    assert (
        result["judgment_count"]
        == 1
    )

    assert (
        result["primary_pattern"]
        == "偏財格"
    )

    assert (
        result["technical_pattern"]
        == "indirect_wealth"
    )

    assert (
        result["strong_count"]
        == 0
    )

    assert (
        result["possible_count"]
        == 1
    )

    assert (
        result["weakened_count"]
        == 0
    )

    assert (
        result["school_rule_count"]
        == 0
    )

    assert (
        result["overall_judgment"]
        == "provisional_possible"
    )

    assert (
        result["confidence"]
        == "medium"
    )


def test_evaluate_pattern_judgment_strong_exposed():
    candidate = make_candidate(
        pattern="正官格",
        technical_pattern="direct_officer",
        confidence="high",
        is_exposed=True,
        exposure_positions=[
            "month",
        ],
    )

    result = (
        evaluate_pattern_judgment(
            make_pattern_candidates(
                [
                    candidate,
                ]
            )
        )
    )

    assert (
        result["strong_count"]
        == 1
    )

    assert (
        result["overall_judgment"]
        == "provisional_established"
    )

    assert (
        result["confidence"]
        == "high"
    )


def test_evaluate_pattern_judgment_school_rule():
    candidate = make_candidate(
        pattern="羊刃格",
        technical_pattern="yangren",
        pattern_group="special_month_pattern",
        confidence="medium",
        requires_school_rule=True,
        candidate_status=(
            "requires_school_rule"
        ),
    )

    result = (
        evaluate_pattern_judgment(
            make_pattern_candidates(
                [
                    candidate,
                ]
            )
        )
    )

    assert (
        result["school_rule_count"]
        == 1
    )

    assert (
        result["overall_judgment"]
        == "requires_school_rule"
    )


def test_evaluate_pattern_judgment_evidence_preserved():
    candidate = make_candidate()

    pattern_candidates = (
        make_pattern_candidates(
            [
                candidate,
            ]
        )
    )

    final_strength = (
        make_final_strength()
    )

    transformation = (
        make_transformation_judgment()
    )

    branches = (
        make_branch_relation_strength(
            total_score=-4.0
        )
    )

    result = (
        evaluate_pattern_judgment(
            pattern_candidates,
            final_strength,
            transformation,
            branches,
        )
    )

    assert (
        result["evidence"][
            "pattern_candidates"
        ]
        == pattern_candidates
    )

    assert (
        result["evidence"][
            "final_strength_judgment"
        ]
        == final_strength
    )

    assert (
        result["evidence"][
            "stem_transformation_judgment"
        ]
        == transformation
    )

    assert (
        result["evidence"][
            "branch_relation_strength"
        ]
        == branches
    )


def test_evaluate_pattern_judgment_notes():
    candidate = make_candidate()

    result = (
        evaluate_pattern_judgment(
            make_pattern_candidates(
                [
                    candidate,
                ]
            )
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


# =========================================================
# verified 1985-style case
# 乙丑 / 癸未 / 乙巳 / 丁亥
# pattern candidate: 偏財格, not exposed
# =========================================================


def test_verified_1985_style_pattern_judgment():
    candidate = make_candidate(
        pattern="偏財格",
        technical_pattern="indirect_wealth",
        pattern_group="standard_pattern",
        confidence="medium",
        is_exposed=False,
        exposure_positions=[],
        requires_school_rule=False,
    )

    pattern_candidates = (
        make_pattern_candidates(
            [
                candidate,
            ],
            primary_candidate=candidate,
        )
    )

    result = (
        evaluate_pattern_judgment(
            pattern_candidates,
            make_final_strength(
                final_score=50.0,
                technical_label="balanced",
                label="中和",
                confidence="high",
            ),
            make_transformation_judgment(
                has_candidate=False,
                conflicted_count=0,
                overall_judgment=(
                    "not_applicable"
                ),
            ),
            make_branch_relation_strength(
                total_score=-4.0,
            ),
        )
    )

    assert (
        result["primary_pattern"]
        == "偏財格"
    )

    assert (
        result["technical_pattern"]
        == "indirect_wealth"
    )

    assert (
        result["primary_judgment"][
            "is_exposed"
        ]
        is False
    )

    assert (
        result["primary_judgment"][
            "establishment_score"
        ]
        == 60.0
    )

    assert (
        result["primary_judgment"][
            "establishment_status"
        ]
        == "possible"
    )

    assert (
        result["primary_judgment"][
            "final_judgment"
        ]
        == "provisional_possible"
    )

    breaking_types = {
        factor["type"]
        for factor
        in result[
            "primary_judgment"
        ][
            "breaking_factors"
        ]
    }

    assert (
        "main_hidden_stem_not_exposed"
        in breaking_types
    )

    rescue_types = {
        factor["type"]
        for factor
        in result[
            "primary_judgment"
        ][
            "rescue_factors"
        ]
    }

    assert (
        "balanced_day_master"
        in rescue_types
    )
