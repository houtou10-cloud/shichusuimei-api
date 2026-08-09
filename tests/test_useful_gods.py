"""
tests/test_useful_gods.py

engine/useful_gods.py の単体テスト。

検証対象:
- 日主五行
- 五行生剋関係
- 身強・身弱・中和
- 扶抑法による用神候補
- 喜神候補
- 忌神候補
- weighted_five_elements による順位
- confidence
- pattern_judgment_v2 evidence
- validation
"""

import pytest

from engine.useful_gods import (
    USEFUL_GODS_METHOD,
    USEFUL_GODS_STATUS,
    ELEMENTS,
    get_day_master_element,
    get_element_relations,
    validate_weighted_five_elements,
    extract_element_scores,
    extract_strength_evidence,
    classify_strength_for_useful_gods,
    rank_elements_by_score,
    build_fuyoku_candidates,
    calculate_element_role,
    build_candidate_details,
    determine_confidence,
    build_pattern_evidence,
    evaluate_useful_gods,
)


# =========================================================
# Test helpers
# =========================================================


def make_weighted_five_elements(
    *,
    wood=2.4,
    fire=1.9,
    earth=1.5,
    metal=0.2,
    water=2.0,
):
    return {
        "method": (
            "weighted_hidden_stems_v1"
        ),
        "scores": {
            "木": wood,
            "火": fire,
            "土": earth,
            "金": metal,
            "水": water,
        },
        "percentages": {},
        "total": (
            wood
            + fire
            + earth
            + metal
            + water
        ),
        "pillar_details": {},
        "status": (
            "provisional_weights"
        ),
        "notes": [],
    }


def make_final_strength(
    *,
    technical_label="balanced",
    final_score=50.0,
    confidence="high",
):
    return {
        "technical_label": (
            technical_label
        ),
        "final_score": (
            final_score
        ),
        "label": "中和",
        "confidence": (
            confidence
        ),
        "method": (
            "final_strength_judgment_v1"
        ),
        "status": (
            "provisional_final_strength"
        ),
    }


def make_pattern_judgment(
    *,
    primary_pattern="偏財格",
    technical_pattern=(
        "indirect_wealth"
    ),
    overall_judgment="possible",
    confidence="medium",
):
    return {
        "has_pattern_candidate": True,
        "has_pattern": True,
        "judgment_count": 1,
        "primary_pattern": (
            primary_pattern
        ),
        "technical_pattern": (
            technical_pattern
        ),
        "primary_judgment": {},
        "judgments": [],
        "strong_count": 0,
        "possible_count": 1,
        "weakened_count": 0,
        "school_rule_count": 0,
        "overall_judgment": (
            overall_judgment
        ),
        "confidence": (
            confidence
        ),
        "evidence": {},
        "method": (
            "pattern_judgment_v2"
        ),
        "status": (
            "provisional_pattern_judgment_v2"
        ),
        "notes": [],
    }


# =========================================================
# Constants
# =========================================================


def test_useful_gods_constants():
    assert (
        USEFUL_GODS_METHOD
        == "useful_gods_v1"
    )

    assert (
        USEFUL_GODS_STATUS
        == "provisional_useful_gods"
    )


def test_elements_constant():
    assert ELEMENTS == (
        "木",
        "火",
        "土",
        "金",
        "水",
    )


# =========================================================
# Day master element
# =========================================================


@pytest.mark.parametrize(
    (
        "stem",
        "expected",
    ),
    [
        ("甲", "木"),
        ("乙", "木"),
        ("丙", "火"),
        ("丁", "火"),
        ("戊", "土"),
        ("己", "土"),
        ("庚", "金"),
        ("辛", "金"),
        ("壬", "水"),
        ("癸", "水"),
    ],
)
def test_get_day_master_element(
    stem,
    expected,
):
    assert (
        get_day_master_element(
            stem
        )
        == expected
    )


def test_get_day_master_element_invalid():
    with pytest.raises(
        ValueError
    ):
        get_day_master_element(
            "A"
        )


def test_get_day_master_element_type_error():
    with pytest.raises(
        TypeError
    ):
        get_day_master_element(
            123
        )


# =========================================================
# Five element relations
# =========================================================


def test_get_element_relations_wood():
    result = (
        get_element_relations(
            "木"
        )
    )

    assert (
        result["self"]
        == "木"
    )

    assert (
        result["resource"]
        == "水"
    )

    assert (
        result["output"]
        == "火"
    )

    assert (
        result["wealth"]
        == "土"
    )

    assert (
        result["officer"]
        == "金"
    )


def test_get_element_relations_fire():
    result = (
        get_element_relations(
            "火"
        )
    )

    assert (
        result["self"]
        == "火"
    )

    assert (
        result["resource"]
        == "木"
    )

    assert (
        result["output"]
        == "土"
    )

    assert (
        result["wealth"]
        == "金"
    )

    assert (
        result["officer"]
        == "水"
    )


def test_get_element_relations_earth():
    result = (
        get_element_relations(
            "土"
        )
    )

    assert (
        result["self"]
        == "土"
    )

    assert (
        result["resource"]
        == "火"
    )

    assert (
        result["output"]
        == "金"
    )

    assert (
        result["wealth"]
        == "水"
    )

    assert (
        result["officer"]
        == "木"
    )


def test_get_element_relations_metal():
    result = (
        get_element_relations(
            "金"
        )
    )

    assert (
        result["self"]
        == "金"
    )

    assert (
        result["resource"]
        == "土"
    )

    assert (
        result["output"]
        == "水"
    )

    assert (
        result["wealth"]
        == "木"
    )

    assert (
        result["officer"]
        == "火"
    )


def test_get_element_relations_water():
    result = (
        get_element_relations(
            "水"
        )
    )

    assert (
        result["self"]
        == "水"
    )

    assert (
        result["resource"]
        == "金"
    )

    assert (
        result["output"]
        == "木"
    )

    assert (
        result["wealth"]
        == "火"
    )

    assert (
        result["officer"]
        == "土"
    )


def test_get_element_relations_invalid():
    with pytest.raises(
        ValueError
    ):
        get_element_relations(
            "風"
        )


# =========================================================
# weighted_five_elements validation
# =========================================================


def test_validate_weighted_five_elements():
    weighted = (
        make_weighted_five_elements()
    )

    validate_weighted_five_elements(
        weighted
    )


def test_validate_weighted_five_elements_type():
    with pytest.raises(
        TypeError
    ):
        validate_weighted_five_elements(
            []
        )


def test_validate_weighted_five_elements_missing_scores():
    with pytest.raises(
        ValueError
    ):
        validate_weighted_five_elements(
            {}
        )


def test_validate_weighted_five_elements_missing_element():
    weighted = (
        make_weighted_five_elements()
    )

    del weighted[
        "scores"
    ][
        "金"
    ]

    with pytest.raises(
        ValueError
    ):
        validate_weighted_five_elements(
            weighted
        )


def test_validate_weighted_five_elements_invalid_score():
    weighted = (
        make_weighted_five_elements()
    )

    weighted[
        "scores"
    ][
        "木"
    ] = "2.4"

    with pytest.raises(
        ValueError
    ):
        validate_weighted_five_elements(
            weighted
        )


def test_validate_weighted_five_elements_bool_is_invalid():
    weighted = (
        make_weighted_five_elements()
    )

    weighted[
        "scores"
    ][
        "木"
    ] = True

    with pytest.raises(
        ValueError
    ):
        validate_weighted_five_elements(
            weighted
        )


# =========================================================
# Element score extraction
# =========================================================


def test_extract_element_scores():
    result = (
        extract_element_scores(
            make_weighted_five_elements()
        )
    )

    assert result == {
        "木": 2.4,
        "火": 1.9,
        "土": 1.5,
        "金": 0.2,
        "水": 2.0,
    }


def test_extract_element_scores_returns_float():
    weighted = (
        make_weighted_five_elements(
            wood=2,
            fire=2,
            earth=2,
            metal=1,
            water=1,
        )
    )

    result = (
        extract_element_scores(
            weighted
        )
    )

    assert all(
        isinstance(
            value,
            float,
        )
        for value
        in result.values()
    )


# =========================================================
# Strength evidence
# =========================================================


def test_extract_strength_evidence():
    result = (
        extract_strength_evidence(
            make_final_strength(
                technical_label=(
                    "balanced"
                ),
                final_score=50.0,
                confidence="high",
            )
        )
    )

    assert (
        result[
            "technical_label"
        ]
        == "balanced"
    )

    assert (
        result[
            "final_score"
        ]
        == 50.0
    )

    assert (
        result[
            "confidence"
        ]
        == "high"
    )


def test_extract_strength_evidence_type():
    with pytest.raises(
        TypeError
    ):
        extract_strength_evidence(
            []
        )


def test_extract_strength_evidence_invalid_label():
    strength = (
        make_final_strength()
    )

    strength[
        "technical_label"
    ] = 123

    with pytest.raises(
        TypeError
    ):
        extract_strength_evidence(
            strength
        )


def test_extract_strength_evidence_invalid_score():
    strength = (
        make_final_strength()
    )

    strength[
        "final_score"
    ] = "50"

    with pytest.raises(
        TypeError
    ):
        extract_strength_evidence(
            strength
        )


# =========================================================
# Strength classification
# =========================================================


@pytest.mark.parametrize(
    "technical_label",
    [
        "strong",
        "very_strong",
        "extremely_strong",
    ],
)
def test_classify_strength_strong_labels(
    technical_label,
):
    result = (
        classify_strength_for_useful_gods(
            make_final_strength(
                technical_label=(
                    technical_label
                )
            )
        )
    )

    assert result == "strong"


@pytest.mark.parametrize(
    "technical_label",
    [
        "weak",
        "very_weak",
        "extremely_weak",
    ],
)
def test_classify_strength_weak_labels(
    technical_label,
):
    result = (
        classify_strength_for_useful_gods(
            make_final_strength(
                technical_label=(
                    technical_label
                )
            )
        )
    )

    assert result == "weak"


@pytest.mark.parametrize(
    "technical_label",
    [
        "balanced",
        "neutral",
    ],
)
def test_classify_strength_balanced_labels(
    technical_label,
):
    result = (
        classify_strength_for_useful_gods(
            make_final_strength(
                technical_label=(
                    technical_label
                )
            )
        )
    )

    assert result == "balanced"


def test_classify_strength_fallback_strong():
    strength = (
        make_final_strength(
            technical_label=(
                "unknown"
            ),
            final_score=60.0,
        )
    )

    assert (
        classify_strength_for_useful_gods(
            strength
        )
        == "strong"
    )


def test_classify_strength_fallback_weak():
    strength = (
        make_final_strength(
            technical_label=(
                "unknown"
            ),
            final_score=40.0,
        )
    )

    assert (
        classify_strength_for_useful_gods(
            strength
        )
        == "weak"
    )


def test_classify_strength_fallback_balanced():
    strength = (
        make_final_strength(
            technical_label=(
                "unknown"
            ),
            final_score=50.0,
        )
    )

    assert (
        classify_strength_for_useful_gods(
            strength
        )
        == "balanced"
    )


def test_classify_strength_without_score():
    strength = (
        make_final_strength(
            technical_label=(
                "unknown"
            ),
        )
    )

    strength[
        "final_score"
    ] = None

    assert (
        classify_strength_for_useful_gods(
            strength
        )
        == "balanced"
    )


# =========================================================
# Element ranking
# =========================================================


def test_rank_elements_by_score_ascending():
    scores = {
        "木": 2.4,
        "火": 1.9,
        "土": 1.5,
        "金": 0.2,
        "水": 2.0,
    }

    result = (
        rank_elements_by_score(
            [
                "木",
                "水",
                "金",
            ],
            scores,
        )
    )

    assert result == [
        "金",
        "水",
        "木",
    ]


def test_rank_elements_by_score_descending():
    scores = {
        "木": 2.4,
        "火": 1.9,
        "土": 1.5,
        "金": 0.2,
        "水": 2.0,
    }

    result = (
        rank_elements_by_score(
            [
                "木",
                "水",
                "金",
            ],
            scores,
            ascending=False,
        )
    )

    assert result == [
        "木",
        "水",
        "金",
    ]


def test_rank_elements_invalid_type():
    with pytest.raises(
        TypeError
    ):
        rank_elements_by_score(
            "木",
            {
                "木": 1.0,
            },
        )


def test_rank_elements_invalid_element():
    with pytest.raises(
        ValueError
    ):
        rank_elements_by_score(
            [
                "風",
            ],
            {
                "風": 1.0,
            },
        )


# =========================================================
# Fuyoku candidates
# =========================================================


def test_build_fuyoku_candidates_weak_wood():
    scores = (
        extract_element_scores(
            make_weighted_five_elements()
        )
    )

    result = (
        build_fuyoku_candidates(
            "木",
            "weak",
            scores,
        )
    )

    # 木日主:
    # 印星 = 水
    # 比劫 = 木
    #
    # score:
    # 水 = 2.0
    # 木 = 2.4
    #
    # 少ない水を優先
    assert (
        result[
            "favorable_elements"
        ]
        == [
            "水",
            "木",
        ]
    )

    assert set(
        result[
            "unfavorable_elements"
        ]
    ) == {
        "火",
        "土",
        "金",
    }

    assert (
        result[
            "selection_basis"
        ]
        == "weak_day_master_support"
    )


def test_build_fuyoku_candidates_strong_wood():
    scores = (
        extract_element_scores(
            make_weighted_five_elements()
        )
    )

    result = (
        build_fuyoku_candidates(
            "木",
            "strong",
            scores,
        )
    )

    # 木日主:
    #
    # 食傷 = 火 1.9
    # 財   = 土 1.5
    # 官殺 = 金 0.2
    #
    # 少ない順
    assert (
        result[
            "favorable_elements"
        ]
        == [
            "金",
            "土",
            "火",
        ]
    )

    # 印 = 水 2.0
    # 比劫 = 木 2.4
    #
    # 忌神側は多い順
    assert (
        result[
            "unfavorable_elements"
        ]
        == [
            "木",
            "水",
        ]
    )

    assert (
        result[
            "selection_basis"
        ]
        == "strong_day_master_drain"
    )


def test_build_fuyoku_candidates_balanced():
    scores = (
        extract_element_scores(
            make_weighted_five_elements()
        )
    )

    result = (
        build_fuyoku_candidates(
            "木",
            "balanced",
            scores,
        )
    )

    # 五行量の少ない順:
    #
    # 金 0.2
    # 土 1.5
    # 火 1.9
    # 水 2.0
    # 木 2.4
    assert (
        result[
            "favorable_elements"
        ]
        == [
            "金",
            "土",
        ]
    )

    assert (
        result[
            "unfavorable_elements"
        ]
        == []
    )

    assert (
        result[
            "neutral_elements"
        ]
        == [
            "火",
            "水",
            "木",
        ]
    )

    assert (
        result[
            "selection_basis"
        ]
        == "balanced_day_master_scarcity"
    )


def test_build_fuyoku_candidates_invalid_strength():
    scores = (
        extract_element_scores(
            make_weighted_five_elements()
        )
    )

    with pytest.raises(
        ValueError
    ):
        build_fuyoku_candidates(
            "木",
            "super_strong",
            scores,
        )


# =========================================================
# Element role
# =========================================================


def test_calculate_element_role():
    relations = (
        get_element_relations(
            "木"
        )
    )

    assert (
        calculate_element_role(
            "木",
            relations,
        )
        == "self"
    )

    assert (
        calculate_element_role(
            "水",
            relations,
        )
        == "resource"
    )

    assert (
        calculate_element_role(
            "火",
            relations,
        )
        == "output"
    )

    assert (
        calculate_element_role(
            "土",
            relations,
        )
        == "wealth"
    )

    assert (
        calculate_element_role(
            "金",
            relations,
        )
        == "officer"
    )


# =========================================================
# Candidate details
# =========================================================


def test_build_candidate_details():
    scores = (
        extract_element_scores(
            make_weighted_five_elements()
        )
    )

    relations = (
        get_element_relations(
            "木"
        )
    )

    result = (
        build_candidate_details(
            [
                "水",
                "木",
            ],
            category="favorable",
            element_scores=scores,
            relations=relations,
        )
    )

    assert len(
        result
    ) == 2

    assert result[0] == {
        "element": "水",
        "priority": 1,
        "category": "favorable",
        "day_master_relation": (
            "resource"
        ),
        "weighted_score": 2.0,
    }

    assert result[1] == {
        "element": "木",
        "priority": 2,
        "category": "favorable",
        "day_master_relation": (
            "self"
        ),
        "weighted_score": 2.4,
    }


# =========================================================
# Pattern evidence
# =========================================================


def test_build_pattern_evidence_none():
    result = (
        build_pattern_evidence(
            None
        )
    )

    assert result == {
        "available": False,
        "primary_pattern": None,
        "technical_pattern": None,
        "overall_judgment": None,
        "confidence": None,
    }


def test_build_pattern_evidence():
    pattern = (
        make_pattern_judgment()
    )

    result = (
        build_pattern_evidence(
            pattern
        )
    )

    assert (
        result[
            "available"
        ]
        is True
    )

    assert (
        result[
            "primary_pattern"
        ]
        == "偏財格"
    )

    assert (
        result[
            "technical_pattern"
        ]
        == "indirect_wealth"
    )

    assert (
        result[
            "overall_judgment"
        ]
        == "possible"
    )

    assert (
        result[
            "confidence"
        ]
        == "medium"
    )


def test_build_pattern_evidence_invalid_type():
    with pytest.raises(
        TypeError
    ):
        build_pattern_evidence(
            []
        )


# =========================================================
# Confidence
# =========================================================


def test_determine_confidence_balanced():
    result = (
        determine_confidence(
            "balanced",
            make_final_strength(
                confidence="high"
            ),
            make_pattern_judgment(
                confidence="high"
            ),
        )
    )

    assert result == "medium"


def test_determine_confidence_balanced_low():
    result = (
        determine_confidence(
            "balanced",
            make_final_strength(
                confidence="low"
            ),
            make_pattern_judgment(
                confidence="high"
            ),
        )
    )

    assert result == "low"


def test_determine_confidence_strong_high():
    result = (
        determine_confidence(
            "strong",
            make_final_strength(
                technical_label="strong",
                confidence="high",
            ),
            make_pattern_judgment(
                confidence="high"
            ),
        )
    )

    assert result == "high"


def test_determine_confidence_weak_high():
    result = (
        determine_confidence(
            "weak",
            make_final_strength(
                technical_label="weak",
                confidence="high",
            ),
            make_pattern_judgment(
                confidence="medium"
            ),
        )
    )

    assert result == "high"


def test_determine_confidence_without_pattern():
    result = (
        determine_confidence(
            "weak",
            make_final_strength(
                technical_label="weak",
                confidence="high",
            ),
            None,
        )
    )

    assert result == "medium"


# =========================================================
# Main evaluator
# =========================================================


def test_evaluate_useful_gods_weak_wood():
    result = (
        evaluate_useful_gods(
            "乙",
            make_weighted_five_elements(),
            make_final_strength(
                technical_label="weak",
                final_score=40.0,
                confidence="high",
            ),
            make_pattern_judgment(),
        )
    )

    assert (
        result[
            "has_useful_candidate"
        ]
        is True
    )

    assert (
        result[
            "day_master_stem"
        ]
        == "乙"
    )

    assert (
        result[
            "day_master_element"
        ]
        == "木"
    )

    assert (
        result[
            "strength_class"
        ]
        == "weak"
    )

    assert (
        result[
            "primary_useful_element"
        ]
        == "水"
    )

    assert (
        result[
            "secondary_favorable_elements"
        ]
        == [
            "木",
        ]
    )

    assert (
        result[
            "favorable_elements"
        ]
        == [
            "水",
            "木",
        ]
    )

    assert set(
        result[
            "unfavorable_elements"
        ]
    ) == {
        "火",
        "土",
        "金",
    }


def test_evaluate_useful_gods_strong_wood():
    result = (
        evaluate_useful_gods(
            "乙",
            make_weighted_five_elements(),
            make_final_strength(
                technical_label="strong",
                final_score=65.0,
                confidence="high",
            ),
            make_pattern_judgment(),
        )
    )

    assert (
        result[
            "strength_class"
        ]
        == "strong"
    )

    assert (
        result[
            "primary_useful_element"
        ]
        == "金"
    )

    assert (
        result[
            "favorable_elements"
        ]
        == [
            "金",
            "土",
            "火",
        ]
    )

    assert (
        result[
            "unfavorable_elements"
        ]
        == [
            "木",
            "水",
        ]
    )


def test_evaluate_useful_gods_balanced_wood():
    result = (
        evaluate_useful_gods(
            "乙",
            make_weighted_five_elements(),
            make_final_strength(
                technical_label=(
                    "balanced"
                ),
                final_score=50.0,
                confidence="high",
            ),
            make_pattern_judgment(),
        )
    )

    assert (
        result[
            "strength_class"
        ]
        == "balanced"
    )

    assert (
        result[
            "primary_useful_element"
        ]
        == "金"
    )

    assert (
        result[
            "secondary_favorable_elements"
        ]
        == [
            "土",
        ]
    )

    assert (
        result[
            "unfavorable_elements"
        ]
        == []
    )

    assert (
        result[
            "confidence"
        ]
        == "medium"
    )


# =========================================================
# Main evaluator structure
# =========================================================


def test_evaluate_useful_gods_structure():
    result = (
        evaluate_useful_gods(
            "乙",
            make_weighted_five_elements(),
            make_final_strength(),
            make_pattern_judgment(),
        )
    )

    required_keys = {
        "has_useful_candidate",
        "primary_useful_element",
        "secondary_favorable_elements",
        "favorable_elements",
        "primary_unfavorable_element",
        "unfavorable_elements",
        "neutral_elements",
        "useful_candidates",
        "unfavorable_candidates",
        "neutral_candidates",
        "day_master_stem",
        "day_master_element",
        "strength_class",
        "selection_basis",
        "confidence",
        "relations",
        "element_scores",
        "reasoning",
        "evidence",
        "method",
        "status",
        "notes",
    }

    assert required_keys.issubset(
        result.keys()
    )


def test_evaluate_useful_gods_method():
    result = (
        evaluate_useful_gods(
            "乙",
            make_weighted_five_elements(),
            make_final_strength(),
        )
    )

    assert (
        result["method"]
        == "useful_gods_v1"
    )

    assert (
        result["status"]
        == "provisional_useful_gods"
    )


# =========================================================
# Evidence integrity
# =========================================================


def test_evaluate_useful_gods_evidence_preserved():
    weighted = (
        make_weighted_five_elements()
    )

    strength = (
        make_final_strength()
    )

    pattern = (
        make_pattern_judgment()
    )

    result = (
        evaluate_useful_gods(
            "乙",
            weighted,
            strength,
            pattern,
        )
    )

    evidence = result[
        "evidence"
    ]

    assert (
        evidence[
            "weighted_five_elements"
        ]
        == weighted
    )

    assert (
        evidence[
            "final_strength_judgment"
        ]
        == strength
    )

    assert (
        evidence[
            "pattern_judgment"
        ]
        == pattern
    )


def test_evaluate_useful_gods_pattern_summary():
    result = (
        evaluate_useful_gods(
            "乙",
            make_weighted_five_elements(),
            make_final_strength(),
            make_pattern_judgment(),
        )
    )

    summary = result[
        "evidence"
    ][
        "pattern_summary"
    ]

    assert (
        summary[
            "available"
        ]
        is True
    )

    assert (
        summary[
            "primary_pattern"
        ]
        == "偏財格"
    )

    assert (
        summary[
            "technical_pattern"
        ]
        == "indirect_wealth"
    )


# =========================================================
# Candidate consistency
# =========================================================


def test_primary_useful_matches_first_favorable():
    result = (
        evaluate_useful_gods(
            "乙",
            make_weighted_five_elements(),
            make_final_strength(
                technical_label="weak"
            ),
        )
    )

    assert (
        result[
            "primary_useful_element"
        ]
        == result[
            "favorable_elements"
        ][0]
    )


def test_primary_unfavorable_matches_first():
    result = (
        evaluate_useful_gods(
            "乙",
            make_weighted_five_elements(),
            make_final_strength(
                technical_label="strong"
            ),
        )
    )

    assert (
        result[
            "primary_unfavorable_element"
        ]
        == result[
            "unfavorable_elements"
        ][0]
    )


def test_useful_candidate_priority():
    result = (
        evaluate_useful_gods(
            "乙",
            make_weighted_five_elements(),
            make_final_strength(
                technical_label="weak"
            ),
        )
    )

    candidates = result[
        "useful_candidates"
    ]

    assert (
        candidates[0][
            "priority"
        ]
        == 1
    )

    assert (
        candidates[1][
            "priority"
        ]
        == 2
    )


def test_useful_candidate_first_element():
    result = (
        evaluate_useful_gods(
            "乙",
            make_weighted_five_elements(),
            make_final_strength(
                technical_label="weak"
            ),
        )
    )

    assert (
        result[
            "useful_candidates"
        ][0][
            "element"
        ]
        == result[
            "primary_useful_element"
        ]
    )


# =========================================================
# 乙 day master regression
# Based on verified chart:
# 乙丑 / 癸未 / 乙巳 / 丁亥
#
# weighted elements:
# 木 2.4
# 火 1.9
# 土 1.5
# 金 0.2
# 水 2.0
# =========================================================


def test_verified_1985_style_balanced_case():
    result = (
        evaluate_useful_gods(
            "乙",
            make_weighted_five_elements(
                wood=2.4,
                fire=1.9,
                earth=1.5,
                metal=0.2,
                water=2.0,
            ),
            make_final_strength(
                technical_label=(
                    "balanced"
                ),
                final_score=50.0,
                confidence="high",
            ),
            make_pattern_judgment(
                primary_pattern="偏財格",
                technical_pattern=(
                    "indirect_wealth"
                ),
                overall_judgment=(
                    "possible"
                ),
                confidence="medium",
            ),
        )
    )

    assert (
        result[
            "day_master_stem"
        ]
        == "乙"
    )

    assert (
        result[
            "day_master_element"
        ]
        == "木"
    )

    assert (
        result[
            "strength_class"
        ]
        == "balanced"
    )

    # v1では中和時は
    # 五行量が少ないものから
    # 暫定候補にする。
    #
    # 金 0.2
    # 土 1.5
    assert (
        result[
            "primary_useful_element"
        ]
        == "金"
    )

    assert (
        result[
            "secondary_favorable_elements"
        ]
        == [
            "土",
        ]
    )

    assert (
        result[
            "confidence"
        ]
        == "medium"
    )

    assert (
        result[
            "evidence"
        ][
            "pattern_summary"
        ][
            "primary_pattern"
        ]
        == "偏財格"
    )


# =========================================================
# All day-master elements
# =========================================================


@pytest.mark.parametrize(
    (
        "stem",
        "expected_element",
    ),
    [
        ("甲", "木"),
        ("乙", "木"),
        ("丙", "火"),
        ("丁", "火"),
        ("戊", "土"),
        ("己", "土"),
        ("庚", "金"),
        ("辛", "金"),
        ("壬", "水"),
        ("癸", "水"),
    ],
)
def test_evaluate_useful_gods_all_day_masters(
    stem,
    expected_element,
):
    result = (
        evaluate_useful_gods(
            stem,
            make_weighted_five_elements(),
            make_final_strength(),
        )
    )

    assert (
        result[
            "day_master_element"
        ]
        == expected_element
    )

    assert (
        result[
            "has_useful_candidate"
        ]
        is True
    )


# =========================================================
# Reasoning / notes
# =========================================================


def test_reasoning_exists():
    result = (
        evaluate_useful_gods(
            "乙",
            make_weighted_five_elements(),
            make_final_strength(),
        )
    )

    assert isinstance(
        result[
            "reasoning"
        ],
        list,
    )

    assert (
        len(
            result[
                "reasoning"
            ]
        )
        >= 1
    )


def test_notes_exist():
    result = (
        evaluate_useful_gods(
            "乙",
            make_weighted_five_elements(),
            make_final_strength(),
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
# No mutation
# =========================================================


def test_evaluate_useful_gods_does_not_mutate_inputs():
    weighted = (
        make_weighted_five_elements()
    )

    strength = (
        make_final_strength()
    )

    pattern = (
        make_pattern_judgment()
    )

    weighted_before = {
        **weighted,
        "scores": {
            **weighted[
                "scores"
            ]
        },
    }

    strength_before = {
        **strength
    }

    pattern_before = {
        **pattern
    }

    evaluate_useful_gods(
        "乙",
        weighted,
        strength,
        pattern,
    )

    assert (
        weighted
        == weighted_before
    )

    assert (
        strength
        == strength_before
    )

    assert (
        pattern
        == pattern_before
    )
