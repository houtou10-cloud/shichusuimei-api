"""
tests/test_useful_gods.py

engine/useful_gods.py の単体テスト。

v1:
- 扶抑用神候補判定の基本動作
- 五行関係
- 身強身弱の抽出
- 喜神・忌神・中立候補
- evidence / metadata

v2:
- 扶抑用神 v1 と調候用神 v1 の統合
- strong_agreement
- partial_agreement
- conflict
- independent
- support_balance_only
- 統合スコア
- 最終候補順位
- confidence
- evidence / metadata

重要:
evaluate_useful_gods() は後方互換のため v1 のまま検証し、
evaluate_useful_gods_v2() を別テストで固定する。
"""

import pytest

from engine.useful_gods import (
    AGREEMENT_BONUS,
    CLIMATE_WEIGHTS,
    ELEMENTS,
    ELEMENT_CONTROLS,
    ELEMENT_GENERATES,
    ELEMENT_ORDER,
    STEM_TO_ELEMENT,
    SUPPORT_FAVORABLE_WEIGHTS,
    SUPPORT_UNFAVORABLE_WEIGHTS,
    USEFUL_GODS_METHOD,
    USEFUL_GODS_STATUS,
    USEFUL_GODS_V2_METHOD,
    USEFUL_GODS_V2_STATUS,
    build_candidate_details,
    build_climate_integration_scores,
    build_integrated_candidate_details,
    build_integrated_element_scores,
    build_support_balance_scores,
    build_useful_gods_v2_reasoning,
    determine_confidence,
    determine_element_relations,
    determine_favorable_elements,
    determine_neutral_elements,
    determine_strength_class,
    determine_unfavorable_elements,
    determine_useful_gods_v2_confidence,
    evaluate_useful_gods,
    evaluate_useful_gods_agreement,
    evaluate_useful_gods_v2,
    extract_element_scores,
    rank_integrated_useful_elements,
    validate_climate_useful_gods_result,
)


def make_weighted(
    scores=None,
):
    if scores is None:
        scores = {
            "木": 30.0,
            "火": 20.0,
            "土": 10.0,
            "金": 15.0,
            "水": 25.0,
        }

    return {
        "scores": scores,
        "method": (
            "weighted_five_elements_v1"
        ),
    }


def make_strength(
    label="balanced",
    confidence="medium",
):
    return {
        "technical_label": label,
        "label": label,
        "final_score": 50.0,
        "confidence": confidence,
        "method": (
            "final_strength_judgment_v2"
        ),
    }


def make_pattern():
    return {
        "primary_pattern": "偏財格",
        "technical_pattern": (
            "indirect_wealth"
        ),
        "overall_judgment": (
            "standard_pattern"
        ),
        "confidence": "medium",
        "method": "pattern_judgment_v2",
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
            element: (
                float(
                    len(elements)
                    - index
                )
                if element
                in elements
                else 0.0
            )
            for index, element
            in enumerate(
                ELEMENTS
            )
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
# v1 constants / relations
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


def test_elements_constant():
    assert ELEMENTS == (
        "木",
        "火",
        "土",
        "金",
        "水",
    )


def test_element_order_matches_elements():
    assert ELEMENT_ORDER == {
        element: index
        for index, element
        in enumerate(
            ELEMENTS
        )
    }


def test_stem_to_element():
    assert STEM_TO_ELEMENT[
        "甲"
    ] == "木"

    assert STEM_TO_ELEMENT[
        "乙"
    ] == "木"

    assert STEM_TO_ELEMENT[
        "丙"
    ] == "火"

    assert STEM_TO_ELEMENT[
        "丁"
    ] == "火"

    assert STEM_TO_ELEMENT[
        "戊"
    ] == "土"

    assert STEM_TO_ELEMENT[
        "己"
    ] == "土"

    assert STEM_TO_ELEMENT[
        "庚"
    ] == "金"

    assert STEM_TO_ELEMENT[
        "辛"
    ] == "金"

    assert STEM_TO_ELEMENT[
        "壬"
    ] == "水"

    assert STEM_TO_ELEMENT[
        "癸"
    ] == "水"


def test_generating_cycle():
    assert ELEMENT_GENERATES == {
        "木": "火",
        "火": "土",
        "土": "金",
        "金": "水",
        "水": "木",
    }


def test_controlling_cycle():
    assert ELEMENT_CONTROLS == {
        "木": "土",
        "火": "金",
        "土": "水",
        "金": "木",
        "水": "火",
    }


# =========================================================
# v1 score extraction
# =========================================================


def test_extract_element_scores():
    result = extract_element_scores(
        make_weighted()
    )

    assert result == {
        "木": 30.0,
        "火": 20.0,
        "土": 10.0,
        "金": 15.0,
        "水": 25.0,
    }


def test_extract_element_scores_missing_scores():
    with pytest.raises(
        ValueError
    ):
        extract_element_scores(
            {}
        )


def test_extract_element_scores_missing_element():
    weighted = make_weighted()

    del weighted[
        "scores"
    ][
        "水"
    ]

    with pytest.raises(
        ValueError
    ):
        extract_element_scores(
            weighted
        )


def test_extract_element_scores_invalid_number():
    weighted = make_weighted()

    weighted[
        "scores"
    ][
        "水"
    ] = True

    with pytest.raises(
        ValueError
    ):
        extract_element_scores(
            weighted
        )


# =========================================================
# v1 strength class
# =========================================================


@pytest.mark.parametrize(
    (
        "label",
        "expected",
    ),
    [
        ("very_strong", "very_strong"),
        ("strong", "strong"),
        ("balanced", "balanced"),
        ("weak", "weak"),
        ("very_weak", "very_weak"),
    ],
)
def test_determine_strength_class(
    label,
    expected,
):
    result = (
        determine_strength_class(
            make_strength(
                label
            )
        )
    )

    assert result == expected


def test_determine_strength_class_fallback_score():
    strength = {
        "final_score": 72.0,
    }

    assert (
        determine_strength_class(
            strength
        )
        == "strong"
    )


# =========================================================
# v1 relations
# =========================================================


def test_determine_element_relations_wood():
    result = (
        determine_element_relations(
            "木"
        )
    )

    assert (
        result[
            "self"
        ]
        == "木"
    )

    assert (
        result[
            "resource"
        ]
        == "水"
    )

    assert (
        result[
            "output"
        ]
        == "火"
    )

    assert (
        result[
            "wealth"
        ]
        == "土"
    )

    assert (
        result[
            "officer"
        ]
        == "金"
    )


@pytest.mark.parametrize(
    "element",
    ELEMENTS,
)
def test_determine_element_relations_all_elements(
    element,
):
    result = (
        determine_element_relations(
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


# =========================================================
# v1 favorable / unfavorable / neutral
# =========================================================


def test_favorable_strong():
    relations = (
        determine_element_relations(
            "木"
        )
    )

    result = (
        determine_favorable_elements(
            "strong",
            relations,
            make_pattern(),
        )
    )

    assert result[
        0
    ] in {
        "火",
        "土",
        "金",
    }

    assert set(
        result
    ) == {
        "火",
        "土",
        "金",
    }


def test_favorable_weak():
    relations = (
        determine_element_relations(
            "木"
        )
    )

    result = (
        determine_favorable_elements(
            "weak",
            relations,
            make_pattern(),
        )
    )

    assert set(
        result
    ) == {
        "木",
        "水",
    }


def test_unfavorable_strong():
    relations = (
        determine_element_relations(
            "木"
        )
    )

    result = (
        determine_unfavorable_elements(
            "strong",
            relations,
        )
    )

    assert set(
        result
    ) == {
        "木",
        "水",
    }


def test_unfavorable_weak():
    relations = (
        determine_element_relations(
            "木"
        )
    )

    result = (
        determine_unfavorable_elements(
            "weak",
            relations,
        )
    )

    assert set(
        result
    ) == {
        "火",
        "土",
        "金",
    }


def test_neutral_elements_are_disjoint():
    relations = (
        determine_element_relations(
            "木"
        )
    )

    favorable = (
        determine_favorable_elements(
            "balanced",
            relations,
            make_pattern(),
        )
    )

    unfavorable = (
        determine_unfavorable_elements(
            "balanced",
            relations,
        )
    )

    neutral = (
        determine_neutral_elements(
            favorable,
            unfavorable,
        )
    )

    assert set(
        favorable
    ).isdisjoint(
        neutral
    )

    assert set(
        unfavorable
    ).isdisjoint(
        neutral
    )


# =========================================================
# v1 candidates
# =========================================================


def test_build_candidate_details():
    scores = {
        "木": 30.0,
        "火": 20.0,
        "土": 10.0,
        "金": 15.0,
        "水": 25.0,
    }

    result = (
        build_candidate_details(
            [
                "水",
                "木",
            ],
            scores,
            "favorable",
        )
    )

    assert len(
        result
    ) == 2

    assert result[
        0
    ][
        "element"
    ] == "水"

    assert result[
        0
    ][
        "priority"
    ] == 1

    assert result[
        0
    ][
        "category"
    ] == "favorable"

    assert result[
        0
    ][
        "score"
    ] == 25.0


# =========================================================
# v1 main evaluator
# =========================================================


def test_evaluate_useful_gods_basic():
    result = evaluate_useful_gods(
        "乙",
        make_weighted(),
        make_strength(),
        make_pattern(),
    )

    assert isinstance(
        result,
        dict,
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

    assert isinstance(
        result[
            "favorable_elements"
        ],
        list,
    )

    assert isinstance(
        result[
            "unfavorable_elements"
        ],
        list,
    )

    assert isinstance(
        result[
            "neutral_elements"
        ],
        list,
    )


def test_evaluate_useful_gods_primary_consistency():
    result = evaluate_useful_gods(
        "乙",
        make_weighted(),
        make_strength(),
        make_pattern(),
    )

    favorable = result[
        "favorable_elements"
    ]

    if favorable:
        assert (
            result[
                "primary_useful_element"
            ]
            == favorable[0]
        )

        assert (
            result[
                "secondary_favorable_elements"
            ]
            == favorable[1:]
        )


def test_evaluate_useful_gods_evidence():
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
# v2 constants
# =========================================================


def test_v2_metadata_constants():
    assert (
        USEFUL_GODS_V2_METHOD
        == "useful_gods_v2"
    )

    assert (
        USEFUL_GODS_V2_STATUS
        == "provisional_useful_gods_v2"
    )


def test_v2_weights():
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
# v2 support-balance scores
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

    result = (
        build_support_balance_scores(
            support
        )
    )

    assert result == {
        "木": 2.0,
        "火": 1.0,
        "土": -2.5,
        "金": -1.5,
        "水": 3.0,
    }


def test_build_support_balance_scores_long_lists_clamped():
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


# =========================================================
# v2 climate integration scores
# =========================================================


def test_build_climate_integration_scores():
    climate = make_climate(
        [
            "水",
            "木",
            "火",
        ]
    )

    result = (
        build_climate_integration_scores(
            climate
        )
    )

    assert result == {
        "木": 1.5,
        "火": 1.0,
        "土": 0.0,
        "金": 0.0,
        "水": 3.0,
    }


def test_build_climate_integration_scores_empty():
    result = (
        build_climate_integration_scores(
            make_climate(
                []
            )
        )
    )

    assert result == {
        element: 0.0
        for element in ELEMENTS
    }


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

    climate = make_climate(
        [
            "水",
        ]
    )

    result = (
        evaluate_useful_gods_agreement(
            support,
            climate,
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

    climate = make_climate(
        [
            "水",
        ]
    )

    result = (
        evaluate_useful_gods_agreement(
            support,
            climate,
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

    climate = make_climate(
        [
            "水",
        ]
    )

    result = (
        evaluate_useful_gods_agreement(
            support,
            climate,
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

    climate = make_climate(
        [
            "水",
        ]
    )

    result = (
        evaluate_useful_gods_agreement(
            support,
            climate,
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

    climate = make_climate(
        []
    )

    result = (
        evaluate_useful_gods_agreement(
            support,
            climate,
        )
    )

    assert (
        result[
            "agreement_level"
        ]
        == "support_balance_only"
    )


# =========================================================
# v2 integrated scores
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

    # 水は扶抑 -2.5 + 調候 +3.0 = +0.5
    # conflict なので agreement bonus は付かない。
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


# =========================================================
# v2 ranking
# =========================================================


def test_rank_integrated_useful_elements():
    scores = {
        "木": 2.0,
        "火": -1.0,
        "土": 0.0,
        "金": 3.0,
        "水": 8.0,
    }

    assert (
        rank_integrated_useful_elements(
            scores
        )
        == [
            "水",
            "金",
            "木",
        ]
    )


def test_rank_integrated_ignores_zero_and_negative():
    scores = {
        "木": 0.0,
        "火": -1.0,
        "土": 0.0,
        "金": 1.0,
        "水": -2.0,
    }

    assert (
        rank_integrated_useful_elements(
            scores
        )
        == [
            "金",
        ]
    )


def test_rank_integrated_stable_tie():
    scores = {
        "木": 2.0,
        "火": 2.0,
        "土": 0.0,
        "金": 0.0,
        "水": 0.0,
    }

    assert (
        rank_integrated_useful_elements(
            scores
        )
        == [
            "木",
            "火",
        ]
    )


def test_rank_integrated_invalid_score():
    scores = {
        "木": True,
        "火": 2.0,
        "土": 0.0,
        "金": 0.0,
        "水": 0.0,
    }

    with pytest.raises(
        ValueError
    ):
        rank_integrated_useful_elements(
            scores
        )


# =========================================================
# v2 candidate details
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

    assert result[
        0
    ][
        "element"
    ] == "水"

    assert result[
        0
    ][
        "priority"
    ] == 1

    assert result[
        0
    ][
        "integrated_score"
    ] == 8.0

    assert result[
        0
    ][
        "support_balance_score"
    ] == 3.0

    assert result[
        0
    ][
        "climate_score"
    ] == 3.0

    assert result[
        0
    ][
        "agreement_bonus"
    ] == 2.0

    assert result[
        0
    ][
        "is_agreed"
    ] is True

    assert result[
        0
    ][
        "is_conflicted"
    ] is False


# =========================================================
# v2 confidence
# =========================================================


def test_v2_confidence_strong_agreement_high():
    support = {
        "confidence": "high",
    }

    climate = {
        "confidence": "high",
    }

    agreement = {
        "agreement_level": (
            "strong_agreement"
        ),
    }

    assert (
        determine_useful_gods_v2_confidence(
            support,
            climate,
            agreement,
        )
        == "high"
    )


def test_v2_confidence_strong_agreement_medium():
    support = {
        "confidence": "low",
    }

    climate = {
        "confidence": "high",
    }

    agreement = {
        "agreement_level": (
            "strong_agreement"
        ),
    }

    assert (
        determine_useful_gods_v2_confidence(
            support,
            climate,
            agreement,
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


# =========================================================
# v2 reasoning
# =========================================================


def test_v2_reasoning_strong_agreement():
    support = {
        "primary_useful_element": "水",
    }

    climate = {
        "primary_climate_element": "水",
    }

    agreement = {
        "agreement_level": (
            "strong_agreement"
        ),
    }

    result = (
        build_useful_gods_v2_reasoning(
            support,
            climate,
            agreement,
            [
                "水",
            ],
        )
    )

    assert isinstance(
        result,
        list,
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
            make_strength(),
            make_pattern(),
            make_climate(
                [
                    "水",
                ]
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


def test_evaluate_useful_gods_v2_metadata():
    result = (
        evaluate_useful_gods_v2(
            "乙",
            make_weighted(),
            make_strength(),
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


def test_evaluate_useful_gods_v2_primary_consistency():
    result = (
        evaluate_useful_gods_v2(
            "乙",
            make_weighted(),
            make_strength(),
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

    if final_elements:
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
    else:
        assert (
            result[
                "primary_useful_element"
            ]
            is None
        )


def test_evaluate_useful_gods_v2_candidate_priorities():
    result = (
        evaluate_useful_gods_v2(
            "乙",
            make_weighted(),
            make_strength(),
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


def test_evaluate_useful_gods_v2_evidence():
    weighted = make_weighted()
    strength = make_strength()
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


def test_evaluate_useful_gods_v2_preserves_v1_support_result():
    weighted = make_weighted()
    strength = make_strength()
    pattern = make_pattern()

    expected_v1 = (
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
        == expected_v1
    )


def test_evaluate_useful_gods_v2_day_master_mismatch():
    with pytest.raises(
        ValueError
    ):
        evaluate_useful_gods_v2(
            "乙",
            make_weighted(),
            make_strength(),
            make_pattern(),
            make_climate(
                [
                    "水",
                ],
                day_master_stem="甲",
            ),
        )


# =========================================================
# v2 scenario regression
# =========================================================


def test_v2_realistic_1985_wei_month_climate_is_water():
    """
    1985/07/17 21:50 石川の既知命式では
    日主=乙、月支=未。

    climate_useful_gods_v1 の現行仕様では
    未月 -> summer -> cooling -> 水。

    ここでは chart.py 未接続段階なので、
    climate結果をスタブとして渡し、
    v2統合の構造を固定する。
    """
    result = (
        evaluate_useful_gods_v2(
            "乙",
            make_weighted(),
            make_strength(),
            make_pattern(),
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
            "climate"
        ][
            "primary_climate_element"
        ]
        == "水"
    )

    assert (
        result[
            "climate"
        ][
            "month_branch"
        ]
        == "未"
    )

    assert (
        result[
            "method"
        ]
        == "useful_gods_v2"
    )


def test_v2_all_integrated_scores_are_numeric():
    result = (
        evaluate_useful_gods_v2(
            "乙",
            make_weighted(),
            make_strength(),
            make_pattern(),
            make_climate(
                [
                    "水",
                ]
            ),
        )
    )

    assert set(
        result[
            "integrated_element_scores"
        ].keys()
    ) == set(
        ELEMENTS
    )

    for value in result[
        "integrated_element_scores"
    ].values():
        assert isinstance(
            value,
            (int, float),
        )

        assert not isinstance(
            value,
            bool,
        )


def test_v2_reasoning_and_notes_exist():
    result = (
        evaluate_useful_gods_v2(
            "乙",
            make_weighted(),
            make_strength(),
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


def test_v2_confidence_is_valid():
    result = (
        evaluate_useful_gods_v2(
            "乙",
            make_weighted(),
            make_strength(),
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
