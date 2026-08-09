"""
tests/test_useful_gods.py

engine/useful_gods.py の単体テスト。

現在の engine/useful_gods.py の公開APIに準拠する。

検証対象
--------
v1:
- 五行定数
- 日主五行
- 生剋関係
- weighted_five_elements 検証
- 身強身弱の正規化
- 扶抑候補
- 候補順位
- confidence
- pattern evidence
- evaluate_useful_gods()

v2:
- climate_useful_gods_v1 入力検証
- 扶抑スコア
- 調候統合スコア
- strong_agreement
- partial_agreement
- conflict
- independent
- support_balance_only
- 統合スコア
- 最終候補順位
- confidence
- evidence
- evaluate_useful_gods_v2()
"""

import pytest

from engine.useful_gods import (
    AGREEMENT_BONUS,
    BALANCED_LABELS,
    CLIMATE_WEIGHTS,
    CONTROLLED_BY,
    CONTROLS,
    ELEMENTS,
    GENERATED_BY,
    GENERATES,
    STEM_TO_ELEMENT,
    STRONG_LABELS,
    SUPPORT_FAVORABLE_WEIGHTS,
    SUPPORT_UNFAVORABLE_WEIGHTS,
    USEFUL_GODS_METHOD,
    USEFUL_GODS_STATUS,
    USEFUL_GODS_V2_METHOD,
    USEFUL_GODS_V2_STATUS,
    WEAK_LABELS,
    build_candidate_details,
    build_climate_integration_scores,
    build_fuyoku_candidates,
    build_integrated_candidate_details,
    build_integrated_element_scores,
    build_pattern_evidence,
    build_support_balance_scores,
    build_useful_gods_v2_reasoning,
    calculate_element_role,
    classify_strength_for_useful_gods,
    determine_confidence,
    determine_useful_gods_v2_confidence,
    evaluate_useful_gods,
    evaluate_useful_gods_agreement,
    evaluate_useful_gods_v2,
    extract_element_scores,
    extract_strength_evidence,
    get_day_master_element,
    get_element_relations,
    rank_elements_by_score,
    rank_integrated_useful_elements,
    validate_climate_useful_gods_result,
    validate_weighted_five_elements,
)


# =========================================================
# Helpers
# =========================================================


def make_weighted(
    *,
    wood=30.0,
    fire=20.0,
    earth=10.0,
    metal=15.0,
    water=25.0,
):
    return {
        "scores": {
            "木": wood,
            "火": fire,
            "土": earth,
            "金": metal,
            "水": water,
        },
        "method": (
            "weighted_five_elements_v1"
        ),
    }


def make_strength(
    *,
    label="balanced",
    score=None,
    confidence="medium",
):
    if score is None:
        if label in {
            "strong",
            "very_strong",
            "extremely_strong",
        }:
            score = 65.0
        elif label in {
            "weak",
            "very_weak",
            "extremely_weak",
        }:
            score = 35.0
        else:
            score = 50.0

    return {
        "technical_label": label,
        "final_score": score,
        "confidence": confidence,
        "method": (
            "final_strength_judgment_v2"
        ),
    }


def make_pattern(
    *,
    confidence="medium",
):
    return {
        "primary_pattern": "偏財格",
        "technical_pattern": (
            "indirect_wealth"
        ),
        "overall_judgment": (
            "provisional_possible"
        ),
        "confidence": confidence,
        "method": "pattern_judgment_v2",
        "status": (
            "provisional_pattern_judgment_v2"
        ),
    }


def make_climate(
    elements,
    *,
    day_master_stem="乙",
    confidence="medium",
):
    elements = list(
        elements
    )

    primary = (
        elements[0]
        if elements
        else None
    )

    return {
        "has_climate_candidate": (
            primary is not None
        ),
        "primary_climate_element": (
            primary
        ),
        "secondary_climate_elements": (
            elements[1:]
        ),
        "climate_elements": elements,
        "climate_candidates": [],
        "day_master_stem": (
            day_master_stem
        ),
        "day_master_element": "木",
        "month_branch": "未",
        "season": "summer",
        "season_japanese": "夏",
        "temperature_label": "hot",
        "moisture_label": (
            "slightly_dry"
        ),
        "heat_score": 1.15,
        "moisture_score": -0.4,
        "climate_needs": (
            ["cooling"]
            if elements
            else []
        ),
        "climate_element_scores": {
            element: 0.0
            for element in ELEMENTS
        },
        "confidence": confidence,
        "reasoning": [
            "test climate reasoning",
        ],
        "evidence": {
            "season_source": (
                "month_branch"
            ),
        },
        "method": (
            "climate_useful_gods_v1"
        ),
        "status": (
            "provisional_climate_useful_gods"
        ),
        "notes": [
            "test climate note",
        ],
    }


# =========================================================
# Constants
# =========================================================


def test_v1_metadata_constants():
    assert (
        USEFUL_GODS_METHOD
        == "useful_gods_v1"
    )

    assert (
        USEFUL_GODS_STATUS
        == "provisional_useful_gods"
    )


def test_v2_metadata_constants():
    assert (
        USEFUL_GODS_V2_METHOD
        == "useful_gods_v2"
    )

    assert (
        USEFUL_GODS_V2_STATUS
        == "provisional_useful_gods_v2"
    )


def test_elements_constant():
    assert ELEMENTS == (
        "木",
        "火",
        "土",
        "金",
        "水",
    )


def test_stem_to_element_mapping():
    assert STEM_TO_ELEMENT == {
        "甲": "木",
        "乙": "木",
        "丙": "火",
        "丁": "火",
        "戊": "土",
        "己": "土",
        "庚": "金",
        "辛": "金",
        "壬": "水",
        "癸": "水",
    }


def test_generates_mapping():
    assert GENERATES == {
        "木": "火",
        "火": "土",
        "土": "金",
        "金": "水",
        "水": "木",
    }


def test_generated_by_mapping():
    assert GENERATED_BY == {
        "火": "木",
        "土": "火",
        "金": "土",
        "水": "金",
        "木": "水",
    }


def test_controls_mapping():
    assert CONTROLS == {
        "木": "土",
        "火": "金",
        "土": "水",
        "金": "木",
        "水": "火",
    }


def test_controlled_by_mapping():
    assert CONTROLLED_BY == {
        "土": "木",
        "金": "火",
        "水": "土",
        "木": "金",
        "火": "水",
    }


def test_strength_label_sets():
    assert STRONG_LABELS == {
        "strong",
        "very_strong",
        "extremely_strong",
    }

    assert WEAK_LABELS == {
        "weak",
        "very_weak",
        "extremely_weak",
    }

    assert BALANCED_LABELS == {
        "balanced",
        "neutral",
    }


def test_v2_weight_constants():
    assert (
        SUPPORT_FAVORABLE_WEIGHTS
        == (
            3.0,
            2.0,
            1.0,
        )
    )

    assert (
        SUPPORT_UNFAVORABLE_WEIGHTS
        == (
            -2.5,
            -1.5,
            -1.0,
        )
    )

    assert (
        CLIMATE_WEIGHTS
        == (
            3.0,
            1.5,
            1.0,
        )
    )

    assert (
        AGREEMENT_BONUS
        == 2.0
    )


# =========================================================
# Day master / relations
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


def test_get_day_master_element_type_error():
    with pytest.raises(
        TypeError
    ):
        get_day_master_element(
            123
        )


def test_get_day_master_element_value_error():
    with pytest.raises(
        ValueError
    ):
        get_day_master_element(
            "A"
        )


def test_get_element_relations_wood():
    result = (
        get_element_relations(
            "木"
        )
    )

    assert result == {
        "self": "木",
        "resource": "水",
        "output": "火",
        "wealth": "土",
        "officer": "金",
    }


@pytest.mark.parametrize(
    "element",
    ELEMENTS,
)
def test_get_element_relations_all_elements(
    element,
):
    result = (
        get_element_relations(
            element
        )
    )

    assert set(
        result.keys()
    ) == {
        "self",
        "resource",
        "output",
        "wealth",
        "officer",
    }

    assert set(
        result.values()
    ) == set(
        ELEMENTS
    )


def test_get_element_relations_invalid():
    with pytest.raises(
        ValueError
    ):
        get_element_relations(
            "風"
        )


# =========================================================
# Weighted five elements
# =========================================================


def test_validate_weighted_five_elements():
    validate_weighted_five_elements(
        make_weighted()
    )


def test_validate_weighted_five_elements_type_error():
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
    weighted = make_weighted()

    del weighted[
        "scores"
    ][
        "水"
    ]

    with pytest.raises(
        ValueError
    ):
        validate_weighted_five_elements(
            weighted
        )


def test_validate_weighted_five_elements_bool_invalid():
    weighted = make_weighted()

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


def test_extract_element_scores():
    assert (
        extract_element_scores(
            make_weighted()
        )
        == {
            "木": 30.0,
            "火": 20.0,
            "土": 10.0,
            "金": 15.0,
            "水": 25.0,
        }
    )


def test_extract_element_scores_returns_float():
    result = (
        extract_element_scores(
            make_weighted(
                wood=3,
                fire=2,
                earth=1,
                metal=4,
                water=5,
            )
        )
    )

    assert all(
        isinstance(
            value,
            float,
        )
        for value in result.values()
    )


# =========================================================
# Strength evidence / classification
# =========================================================


def test_extract_strength_evidence():
    result = (
        extract_strength_evidence(
            make_strength(
                label="strong",
                score=62.5,
                confidence="high",
            )
        )
    )

    assert result == {
        "technical_label": "strong",
        "final_score": 62.5,
        "confidence": "high",
    }


def test_extract_strength_evidence_type_error():
    with pytest.raises(
        TypeError
    ):
        extract_strength_evidence(
            []
        )


def test_extract_strength_evidence_invalid_label():
    with pytest.raises(
        TypeError
    ):
        extract_strength_evidence(
            {
                "technical_label": 123,
                "final_score": 50.0,
            }
        )


def test_extract_strength_evidence_invalid_score():
    with pytest.raises(
        TypeError
    ):
        extract_strength_evidence(
            {
                "technical_label": (
                    "balanced"
                ),
                "final_score": "50",
            }
        )


@pytest.mark.parametrize(
    (
        "label",
        "expected",
    ),
    [
        ("strong", "strong"),
        ("very_strong", "strong"),
        ("extremely_strong", "strong"),
        ("weak", "weak"),
        ("very_weak", "weak"),
        ("extremely_weak", "weak"),
        ("balanced", "balanced"),
        ("neutral", "balanced"),
    ],
)
def test_classify_strength_by_label(
    label,
    expected,
):
    assert (
        classify_strength_for_useful_gods(
            make_strength(
                label=label
            )
        )
        == expected
    )


@pytest.mark.parametrize(
    (
        "score",
        "expected",
    ),
    [
        (55.0, "strong"),
        (70.0, "strong"),
        (44.9, "weak"),
        (20.0, "weak"),
        (45.0, "balanced"),
        (54.9, "balanced"),
    ],
)
def test_classify_strength_fallback_score(
    score,
    expected,
):
    result = (
        classify_strength_for_useful_gods(
            {
                "technical_label": (
                    "unknown"
                ),
                "final_score": score,
            }
        )
    )

    assert result == expected


def test_classify_strength_without_score():
    assert (
        classify_strength_for_useful_gods(
            {
                "technical_label": (
                    "unknown"
                ),
                "final_score": None,
            }
        )
        == "balanced"
    )


# =========================================================
# Ranking / fuyoku
# =========================================================


def test_rank_elements_by_score_ascending():
    scores = (
        extract_element_scores(
            make_weighted()
        )
    )

    assert (
        rank_elements_by_score(
            [
                "木",
                "水",
                "金",
            ],
            scores,
        )
        == [
            "金",
            "水",
            "木",
        ]
    )


def test_rank_elements_by_score_descending():
    scores = (
        extract_element_scores(
            make_weighted()
        )
    )

    assert (
        rank_elements_by_score(
            [
                "木",
                "水",
                "金",
            ],
            scores,
            ascending=False,
        )
        == [
            "木",
            "水",
            "金",
        ]
    )


def test_rank_elements_by_score_type_error():
    with pytest.raises(
        TypeError
    ):
        rank_elements_by_score(
            "木",
            {
                "木": 1.0,
            },
        )


def test_rank_elements_by_score_invalid_element():
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


def test_build_fuyoku_candidates_weak_wood():
    result = (
        build_fuyoku_candidates(
            "木",
            "weak",
            extract_element_scores(
                make_weighted()
            ),
        )
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

    assert (
        result[
            "unfavorable_elements"
        ]
        == [
            "火",
            "金",
            "土",
        ]
    )

    assert (
        result[
            "neutral_elements"
        ]
        == []
    )

    assert (
        result[
            "selection_basis"
        ]
        == "weak_day_master_support"
    )


def test_build_fuyoku_candidates_strong_wood():
    result = (
        build_fuyoku_candidates(
            "木",
            "strong",
            extract_element_scores(
                make_weighted()
            ),
        )
    )

    assert (
        result[
            "favorable_elements"
        ]
        == [
            "土",
            "金",
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

    assert (
        result[
            "selection_basis"
        ]
        == "strong_day_master_drain"
    )


def test_build_fuyoku_candidates_balanced_wood():
    result = (
        build_fuyoku_candidates(
            "木",
            "balanced",
            extract_element_scores(
                make_weighted()
            ),
        )
    )

    assert (
        result[
            "favorable_elements"
        ]
        == [
            "土",
            "金",
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
    with pytest.raises(
        ValueError
    ):
        build_fuyoku_candidates(
            "木",
            "super_strong",
            extract_element_scores(
                make_weighted()
            ),
        )


# =========================================================
# Candidate details
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


def test_build_candidate_details():
    result = (
        build_candidate_details(
            [
                "水",
                "木",
            ],
            category="favorable",
            element_scores=(
                extract_element_scores(
                    make_weighted()
                )
            ),
            relations=(
                get_element_relations(
                    "木"
                )
            ),
        )
    )

    assert result == [
        {
            "element": "水",
            "priority": 1,
            "category": "favorable",
            "day_master_relation": (
                "resource"
            ),
            "weighted_score": 25.0,
        },
        {
            "element": "木",
            "priority": 2,
            "category": "favorable",
            "day_master_relation": (
                "self"
            ),
            "weighted_score": 30.0,
        },
    ]


# =========================================================
# Pattern evidence / v1 confidence
# =========================================================


def test_build_pattern_evidence_none():
    assert (
        build_pattern_evidence(
            None
        )
        == {
            "available": False,
            "primary_pattern": None,
            "technical_pattern": None,
            "overall_judgment": None,
            "confidence": None,
        }
    )


def test_build_pattern_evidence():
    result = (
        build_pattern_evidence(
            make_pattern(
                confidence="high"
            )
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
        == "provisional_possible"
    )

    assert (
        result[
            "confidence"
        ]
        == "high"
    )


def test_build_pattern_evidence_type_error():
    with pytest.raises(
        TypeError
    ):
        build_pattern_evidence(
            []
        )


def test_determine_confidence_balanced():
    assert (
        determine_confidence(
            "balanced",
            make_strength(
                label="balanced",
                confidence="high",
            ),
            make_pattern(
                confidence="high"
            ),
        )
        == "medium"
    )


def test_determine_confidence_balanced_low():
    assert (
        determine_confidence(
            "balanced",
            make_strength(
                label="balanced",
                confidence="low",
            ),
            make_pattern(),
        )
        == "low"
    )


def test_determine_confidence_strong_high():
    assert (
        determine_confidence(
            "strong",
            make_strength(
                label="strong",
                confidence="high",
            ),
            make_pattern(
                confidence="medium"
            ),
        )
        == "high"
    )


def test_determine_confidence_without_pattern():
    assert (
        determine_confidence(
            "weak",
            make_strength(
                label="weak",
                confidence="high",
            ),
            None,
        )
        == "medium"
    )


# =========================================================
# v1 main evaluator
# =========================================================


def test_evaluate_useful_gods_weak():
    result = evaluate_useful_gods(
        "乙",
        make_weighted(),
        make_strength(
            label="weak",
            confidence="high",
        ),
        make_pattern(),
    )

    assert (
        result[
            "method"
        ]
        == "useful_gods_v1"
    )

    assert (
        result[
            "status"
        ]
        == "provisional_useful_gods"
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


def test_evaluate_useful_gods_strong():
    result = evaluate_useful_gods(
        "乙",
        make_weighted(),
        make_strength(
            label="strong",
            confidence="high",
        ),
        make_pattern(),
    )

    assert (
        result[
            "primary_useful_element"
        ]
        == "土"
    )

    assert (
        result[
            "favorable_elements"
        ]
        == [
            "土",
            "金",
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


def test_evaluate_useful_gods_balanced():
    result = evaluate_useful_gods(
        "乙",
        make_weighted(),
        make_strength(
            label="balanced",
            confidence="high",
        ),
        make_pattern(),
    )

    assert (
        result[
            "primary_useful_element"
        ]
        == "土"
    )

    assert (
        result[
            "secondary_favorable_elements"
        ]
        == [
            "金",
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
            "confidence"
        ]
        == "medium"
    )


def test_evaluate_useful_gods_structure():
    result = evaluate_useful_gods(
        "乙",
        make_weighted(),
        make_strength(),
        make_pattern(),
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


def test_evaluate_useful_gods_evidence_integrity():
    weighted = make_weighted()
    strength = make_strength()
    pattern = make_pattern()

    result = evaluate_useful_gods(
        "乙",
        weighted,
        strength,
        pattern,
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


def test_evaluate_useful_gods_invalid_stem():
    with pytest.raises(
        ValueError
    ):
        evaluate_useful_gods(
            "A",
            make_weighted(),
            make_strength(),
            make_pattern(),
        )


# =========================================================
# v2 climate validation
# =========================================================


def test_validate_climate_result_valid():
    validate_climate_useful_gods_result(
        make_climate(
            [
                "水",
            ]
        )
    )


def test_validate_climate_result_type_error():
    with pytest.raises(
        TypeError
    ):
        validate_climate_useful_gods_result(
            []
        )


def test_validate_climate_result_missing_elements():
    climate = make_climate(
        [
            "水",
        ]
    )

    del climate[
        "climate_elements"
    ]

    with pytest.raises(
        ValueError
    ):
        validate_climate_useful_gods_result(
            climate
        )


def test_validate_climate_result_invalid_element():
    climate = make_climate(
        [
            "水",
        ]
    )

    climate[
        "climate_elements"
    ] = [
        "A",
    ]

    with pytest.raises(
        ValueError
    ):
        validate_climate_useful_gods_result(
            climate
        )


def test_validate_climate_result_invalid_primary():
    climate = make_climate(
        [
            "水",
        ]
    )

    climate[
        "primary_climate_element"
    ] = "A"

    with pytest.raises(
        ValueError
    ):
        validate_climate_useful_gods_result(
            climate
        )


# =========================================================
# v2 support / climate integration scores
# =========================================================


def test_build_support_balance_scores():
    support = {
        "favorable_elements": [
            "水",
            "木",
            "火",
        ],
        "unfavorable_elements": [
            "土",
            "金",
        ],
    }

    assert (
        build_support_balance_scores(
            support
        )
        == {
            "木": 2.0,
            "火": 1.0,
            "土": -2.5,
            "金": -1.5,
            "水": 3.0,
        }
    )


def test_build_support_balance_scores_weight_clamp():
    support = {
        "favorable_elements": [
            "木",
            "火",
            "土",
            "金",
        ],
        "unfavorable_elements": [
            "水",
        ],
    }

    result = (
        build_support_balance_scores(
            support
        )
    )

    assert (
        result[
            "木"
        ]
        == 3.0
    )

    assert (
        result[
            "火"
        ]
        == 2.0
    )

    assert (
        result[
            "土"
        ]
        == 1.0
    )

    assert (
        result[
            "金"
        ]
        == 1.0
    )

    assert (
        result[
            "水"
        ]
        == -2.5
    )


def test_build_support_balance_scores_type_error():
    with pytest.raises(
        TypeError
    ):
        build_support_balance_scores(
            []
        )


def test_build_climate_integration_scores():
    assert (
        build_climate_integration_scores(
            make_climate(
                [
                    "水",
                    "木",
                    "火",
                ]
            )
        )
        == {
            "木": 1.5,
            "火": 1.0,
            "土": 0.0,
            "金": 0.0,
            "水": 3.0,
        }
    )


def test_build_climate_integration_scores_empty():
    assert (
        build_climate_integration_scores(
            make_climate(
                []
            )
        )
        == {
            element: 0.0
            for element in ELEMENTS
        }
    )


# =========================================================
# v2 agreement states
# =========================================================


def test_agreement_strong():
    support = {
        "primary_useful_element": "水",
        "favorable_elements": [
            "水",
            "木",
        ],
        "unfavorable_elements": [
            "火",
            "土",
        ],
    }

    result = (
        evaluate_useful_gods_agreement(
            support,
            make_climate(
                [
                    "水",
                ]
            ),
        )
    )

    assert (
        result[
            "agreement_level"
        ]
        == "strong_agreement"
    )

    assert (
        result[
            "has_agreement"
        ]
        is True
    )

    assert (
        result[
            "has_conflict"
        ]
        is False
    )

    assert (
        result[
            "agreed_elements"
        ]
        == [
            "水",
        ]
    )


def test_agreement_partial():
    support = {
        "primary_useful_element": "木",
        "favorable_elements": [
            "木",
            "水",
        ],
        "unfavorable_elements": [
            "火",
            "土",
        ],
    }

    result = (
        evaluate_useful_gods_agreement(
            support,
            make_climate(
                [
                    "水",
                ]
            ),
        )
    )

    assert (
        result[
            "agreement_level"
        ]
        == "partial_agreement"
    )

    assert (
        result[
            "agreed_elements"
        ]
        == [
            "水",
        ]
    )


def test_agreement_conflict():
    support = {
        "primary_useful_element": "金",
        "favorable_elements": [
            "金",
            "土",
        ],
        "unfavorable_elements": [
            "水",
            "木",
        ],
    }

    result = (
        evaluate_useful_gods_agreement(
            support,
            make_climate(
                [
                    "水",
                ]
            ),
        )
    )

    assert (
        result[
            "agreement_level"
        ]
        == "conflict"
    )

    assert (
        result[
            "has_agreement"
        ]
        is False
    )

    assert (
        result[
            "has_conflict"
        ]
        is True
    )

    assert (
        result[
            "conflicted_elements"
        ]
        == [
            "水",
        ]
    )


def test_agreement_independent():
    support = {
        "primary_useful_element": "木",
        "favorable_elements": [
            "木",
        ],
        "unfavorable_elements": [
            "金",
        ],
    }

    result = (
        evaluate_useful_gods_agreement(
            support,
            make_climate(
                [
                    "水",
                ]
            ),
        )
    )

    assert (
        result[
            "agreement_level"
        ]
        == "independent"
    )

    assert (
        result[
            "has_agreement"
        ]
        is False
    )

    assert (
        result[
            "has_conflict"
        ]
        is False
    )


def test_agreement_support_balance_only():
    support = {
        "primary_useful_element": "木",
        "favorable_elements": [
            "木",
        ],
        "unfavorable_elements": [
            "金",
        ],
    }

    result = (
        evaluate_useful_gods_agreement(
            support,
            make_climate(
                []
            ),
        )
    )

    assert (
        result[
            "agreement_level"
        ]
        == "support_balance_only"
    )


# =========================================================
# v2 integrated scores / ranking
# =========================================================


def test_integrated_scores_strong_agreement():
    support = {
        "primary_useful_element": "水",
        "favorable_elements": [
            "水",
            "木",
        ],
        "unfavorable_elements": [
            "火",
            "土",
        ],
    }

    climate = make_climate(
        [
            "水",
        ]
    )

    agreement = (
        evaluate_useful_gods_agreement(
            support,
            climate,
        )
    )

    result = (
        build_integrated_element_scores(
            support,
            climate,
            agreement,
        )
    )

    assert (
        result[
            "水"
        ]
        == 8.0
    )

    assert (
        result[
            "木"
        ]
        == 2.0
    )

    assert (
        result[
            "火"
        ]
        == -2.5
    )

    assert (
        result[
            "土"
        ]
        == -1.5
    )

    assert (
        result[
            "金"
        ]
        == 0.0
    )


def test_integrated_scores_conflict():
    support = {
        "primary_useful_element": "金",
        "favorable_elements": [
            "金",
            "土",
        ],
        "unfavorable_elements": [
            "水",
            "木",
        ],
    }

    climate = make_climate(
        [
            "水",
        ]
    )

    agreement = (
        evaluate_useful_gods_agreement(
            support,
            climate,
        )
    )

    result = (
        build_integrated_element_scores(
            support,
            climate,
            agreement,
        )
    )

    assert (
        result[
            "水"
        ]
        == 0.5
    )

    assert (
        result[
            "金"
        ]
        == 3.0
    )

    assert (
        result[
            "土"
        ]
        == 2.0
    )


def test_rank_integrated_useful_elements():
    assert (
        rank_integrated_useful_elements(
            {
                "木": 2.0,
                "火": -1.0,
                "土": 0.0,
                "金": 3.0,
                "水": 8.0,
            }
        )
        == [
            "水",
            "金",
            "木",
        ]
    )


def test_rank_integrated_ignores_zero_negative():
    assert (
        rank_integrated_useful_elements(
            {
                "木": 0.0,
                "火": -1.0,
                "土": 0.0,
                "金": 1.0,
                "水": -2.0,
            }
        )
        == [
            "金",
        ]
    )


def test_rank_integrated_stable_tie():
    assert (
        rank_integrated_useful_elements(
            {
                "木": 2.0,
                "火": 2.0,
                "土": 0.0,
                "金": 0.0,
                "水": 0.0,
            }
        )
        == [
            "木",
            "火",
        ]
    )


def test_rank_integrated_invalid_score():
    with pytest.raises(
        ValueError
    ):
        rank_integrated_useful_elements(
            {
                "木": True,
                "火": 2.0,
                "土": 0.0,
                "金": 0.0,
                "水": 0.0,
            }
        )


# =========================================================
# v2 integrated candidate details
# =========================================================


def test_build_integrated_candidate_details():
    support = {
        "primary_useful_element": "水",
        "favorable_elements": [
            "水",
            "木",
        ],
        "unfavorable_elements": [
            "火",
            "土",
        ],
    }

    climate = make_climate(
        [
            "水",
        ]
    )

    agreement = (
        evaluate_useful_gods_agreement(
            support,
            climate,
        )
    )

    scores = (
        build_integrated_element_scores(
            support,
            climate,
            agreement,
        )
    )

    ranked = (
        rank_integrated_useful_elements(
            scores
        )
    )

    result = (
        build_integrated_candidate_details(
            ranked,
            scores,
            support,
            climate,
            agreement,
        )
    )

    assert (
        result[
            0
        ][
            "element"
        ]
        == "水"
    )

    assert (
        result[
            0
        ][
            "priority"
        ]
        == 1
    )

    assert (
        result[
            0
        ][
            "integrated_score"
        ]
        == 8.0
    )

    assert (
        result[
            0
        ][
            "support_balance_score"
        ]
        == 3.0
    )

    assert (
        result[
            0
        ][
            "climate_score"
        ]
        == 3.0
    )

    assert (
        result[
            0
        ][
            "agreement_bonus"
        ]
        == 2.0
    )

    assert (
        result[
            0
        ][
            "is_agreed"
        ]
        is True
    )

    assert (
        result[
            0
        ][
            "is_conflicted"
        ]
        is False
    )


# =========================================================
# v2 confidence / reasoning
# =========================================================


def test_v2_confidence_strong_agreement_high():
    assert (
        determine_useful_gods_v2_confidence(
            {
                "confidence": "high",
            },
            {
                "confidence": "high",
            },
            {
                "agreement_level": (
                    "strong_agreement"
                ),
            },
        )
        == "high"
    )


def test_v2_confidence_strong_agreement_medium():
    assert (
        determine_useful_gods_v2_confidence(
            {
                "confidence": "low",
            },
            {
                "confidence": "high",
            },
            {
                "agreement_level": (
                    "strong_agreement"
                ),
            },
        )
        == "medium"
    )


def test_v2_confidence_partial():
    assert (
        determine_useful_gods_v2_confidence(
            {
                "confidence": "high",
            },
            {
                "confidence": "high",
            },
            {
                "agreement_level": (
                    "partial_agreement"
                ),
            },
        )
        == "medium"
    )


def test_v2_confidence_conflict():
    assert (
        determine_useful_gods_v2_confidence(
            {
                "confidence": "high",
            },
            {
                "confidence": "high",
            },
            {
                "agreement_level": (
                    "conflict"
                ),
            },
        )
        == "low"
    )


def test_v2_confidence_independent_high_high():
    assert (
        determine_useful_gods_v2_confidence(
            {
                "confidence": "high",
            },
            {
                "confidence": "high",
            },
            {
                "agreement_level": (
                    "independent"
                ),
            },
        )
        == "medium"
    )


def test_v2_confidence_support_only():
    assert (
        determine_useful_gods_v2_confidence(
            {
                "confidence": "high",
            },
            {
                "confidence": "low",
            },
            {
                "agreement_level": (
                    "support_balance_only"
                ),
            },
        )
        == "medium"
    )


def test_v2_reasoning_strong_agreement():
    result = (
        build_useful_gods_v2_reasoning(
            {
                "primary_useful_element": (
                    "水"
                ),
            },
            {
                "primary_climate_element": (
                    "水"
                ),
            },
            {
                "agreement_level": (
                    "strong_agreement"
                ),
            },
            [
                "水",
            ],
        )
    )

    assert any(
        "強い一致"
        in item
        for item in result
    )

    assert any(
        "水"
        in item
        for item in result
    )


def test_v2_reasoning_conflict():
    result = (
        build_useful_gods_v2_reasoning(
            {
                "primary_useful_element": (
                    "金"
                ),
            },
            {
                "primary_climate_element": (
                    "水"
                ),
            },
            {
                "agreement_level": (
                    "conflict"
                ),
            },
            [
                "金",
                "水",
            ],
        )
    )

    assert any(
        "競合"
        in item
        for item in result
    )


# =========================================================
# v2 main evaluator
# =========================================================


def test_evaluate_useful_gods_v2_structure():
    result = (
        evaluate_useful_gods_v2(
            "乙",
            make_weighted(),
            make_strength(
                label="weak",
                confidence="high",
            ),
            make_pattern(
                confidence="medium"
            ),
            make_climate(
                [
                    "水",
                ],
                confidence="high",
            ),
        )
    )

    required_keys = {
        "has_useful_candidate",
        "primary_useful_element",
        "secondary_useful_elements",
        "final_useful_elements",
        "final_candidates",
        "integrated_element_scores",
        "support_balance",
        "climate",
        "agreement",
        "day_master_stem",
        "day_master_element",
        "strength_class",
        "confidence",
        "reasoning",
        "evidence",
        "method",
        "status",
        "notes",
    }

    assert required_keys.issubset(
        result.keys()
    )


def test_evaluate_useful_gods_v2_strong_agreement():
    result = (
        evaluate_useful_gods_v2(
            "乙",
            make_weighted(),
            make_strength(
                label="weak",
                confidence="high",
            ),
            make_pattern(
                confidence="medium"
            ),
            make_climate(
                [
                    "水",
                ],
                confidence="high",
            ),
        )
    )

    assert (
        result[
            "method"
        ]
        == "useful_gods_v2"
    )

    assert (
        result[
            "status"
        ]
        == "provisional_useful_gods_v2"
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
            "support_balance"
        ][
            "primary_useful_element"
        ]
        == "水"
    )

    assert (
        result[
            "climate"
        ][
            "primary_climate_element"
        ]
        == "水"
    )

    assert (
        result[
            "agreement"
        ][
            "agreement_level"
        ]
        == "strong_agreement"
    )

    assert (
        result[
            "primary_useful_element"
        ]
        == "水"
    )

    assert (
        result[
            "final_useful_elements"
        ][0]
        == "水"
    )

    assert (
        result[
            "confidence"
        ]
        == "high"
    )


def test_evaluate_useful_gods_v2_primary_consistency():
    result = (
        evaluate_useful_gods_v2(
            "乙",
            make_weighted(),
            make_strength(
                label="weak",
                confidence="high",
            ),
            make_pattern(),
            make_climate(
                [
                    "水",
                ]
            ),
        )
    )

    final_elements = result[
        "final_useful_elements"
    ]

    assert (
        result[
            "primary_useful_element"
        ]
        == final_elements[0]
    )

    assert (
        result[
            "secondary_useful_elements"
        ]
        == final_elements[1:]
    )

    assert (
        result[
            "has_useful_candidate"
        ]
        is True
    )


def test_evaluate_useful_gods_v2_candidate_priorities():
    result = (
        evaluate_useful_gods_v2(
            "乙",
            make_weighted(),
            make_strength(
                label="weak"
            ),
            make_pattern(),
            make_climate(
                [
                    "水",
                ]
            ),
        )
    )

    candidates = result[
        "final_candidates"
    ]

    assert (
        len(
            candidates
        )
        == len(
            result[
                "final_useful_elements"
            ]
        )
    )

    for index, candidate in enumerate(
        candidates,
        start=1,
    ):
        assert (
            candidate[
                "priority"
            ]
            == index
        )

        assert (
            candidate[
                "element"
            ]
            == result[
                "final_useful_elements"
            ][
                index - 1
            ]
        )


def test_evaluate_useful_gods_v2_evidence_integrity():
    weighted = make_weighted()
    strength = make_strength(
        label="weak"
    )
    pattern = make_pattern()
    climate = make_climate(
        [
            "水",
        ]
    )

    result = (
        evaluate_useful_gods_v2(
            "乙",
            weighted,
            strength,
            pattern,
            climate,
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

    assert (
        evidence[
            "climate_useful_gods"
        ]
        == climate
    )

    assert (
        evidence[
            "support_balance"
        ]
        == result[
            "support_balance"
        ]
    )


def test_evaluate_useful_gods_v2_preserves_v1_support():
    weighted = make_weighted()
    strength = make_strength(
        label="weak"
    )
    pattern = make_pattern()

    expected = (
        evaluate_useful_gods(
            "乙",
            weighted,
            strength,
            pattern,
        )
    )

    result = (
        evaluate_useful_gods_v2(
            "乙",
            weighted,
            strength,
            pattern,
            make_climate(
                [
                    "水",
                ]
            ),
        )
    )

    assert (
        result[
            "support_balance"
        ]
        == expected
    )


def test_evaluate_useful_gods_v2_day_master_mismatch():
    with pytest.raises(
        ValueError
    ):
        evaluate_useful_gods_v2(
            "乙",
            make_weighted(),
            make_strength(
                label="weak"
            ),
            make_pattern(),
            make_climate(
                [
                    "水",
                ],
                day_master_stem="甲",
            ),
        )


def test_evaluate_useful_gods_v2_integrated_scores_numeric():
    result = (
        evaluate_useful_gods_v2(
            "乙",
            make_weighted(),
            make_strength(
                label="weak"
            ),
            make_pattern(),
            make_climate(
                [
                    "水",
                ]
            ),
        )
    )

    scores = result[
        "integrated_element_scores"
    ]

    assert set(
        scores.keys()
    ) == set(
        ELEMENTS
    )

    assert all(
        isinstance(
            value,
            (int, float),
        )
        and not isinstance(
            value,
            bool,
        )
        for value in scores.values()
    )


def test_evaluate_useful_gods_v2_reasoning_notes():
    result = (
        evaluate_useful_gods_v2(
            "乙",
            make_weighted(),
            make_strength(
                label="weak"
            ),
            make_pattern(),
            make_climate(
                [
                    "水",
                ]
            ),
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


def test_evaluate_useful_gods_v2_confidence_valid():
    result = (
        evaluate_useful_gods_v2(
            "乙",
            make_weighted(),
            make_strength(
                label="weak"
            ),
            make_pattern(),
            make_climate(
                [
                    "水",
                ]
            ),
        )
    )

    assert (
        result[
            "confidence"
        ]
        in {
            "high",
            "medium",
            "low",
        }
    )
