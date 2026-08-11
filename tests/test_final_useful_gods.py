"""
tests/test_final_useful_gods.py

用神統合エンジン useful_gods_v3 の最終回帰テスト。

対象:
- 扶抑用神
- 調候用神
- 格局用神
- 3系統一致
- 2系統一致
- 扶抑との競合
- 統合スコア
- 最終候補順位
- confidence
- reasoning
- validation
- v1 / v2 後方互換

重要:
このテストでは、特定命式の用神を
恣意的に固定するのではなく、
useful_gods_v3 の統合規則そのものを検証する。
"""

import pytest

from engine.useful_gods import (
    AGREEMENT_BONUS,
    CLIMATE_WEIGHTS,
    CONTROLLED_BY,
    CONTROLS,
    DOUBLE_SOURCE_BONUS,
    ELEMENTS,
    GENERATED_BY,
    GENERATES,
    PATTERN_INTEGRATION_WEIGHTS,
    STEM_TO_ELEMENT,
    SUPPORT_CONFLICT_PENALTY,
    SUPPORT_FAVORABLE_WEIGHTS,
    SUPPORT_UNFAVORABLE_WEIGHTS,
    TRIPLE_SOURCE_BONUS,
    USEFUL_GODS_METHOD,
    USEFUL_GODS_STATUS,
    USEFUL_GODS_V2_METHOD,
    USEFUL_GODS_V2_STATUS,
    USEFUL_GODS_V3_METHOD,
    USEFUL_GODS_V3_STATUS,
    build_climate_integration_scores,
    build_fuyoku_candidates,
    build_integrated_candidate_details_v3,
    build_integrated_element_scores_v3,
    build_pattern_integration_scores,
    build_support_balance_scores,
    classify_strength_for_useful_gods,
    evaluate_useful_gods,
    evaluate_useful_gods_agreement,
    evaluate_useful_gods_v2,
    evaluate_useful_gods_v3,
    evaluate_useful_gods_v3_agreement,
    get_day_master_element,
    get_element_relations,
    rank_integrated_useful_elements,
    validate_climate_useful_gods_result,
    validate_pattern_useful_gods_result,
    validate_weighted_five_elements,
)


# ============================================================
# テスト用データ
# ============================================================


def make_weighted_five_elements():
    return {
        "scores": {
            "木": 20.0,
            "火": 10.0,
            "土": 30.0,
            "金": 25.0,
            "水": 15.0,
        }
    }


def make_strong_judgment():
    return {
        "technical_label": "strong",
        "final_score": 65.0,
        "confidence": "high",
    }


def make_weak_judgment():
    return {
        "technical_label": "weak",
        "final_score": 35.0,
        "confidence": "high",
    }


def make_balanced_judgment():
    return {
        "technical_label": "balanced",
        "final_score": 50.0,
        "confidence": "medium",
    }


def make_pattern_judgment():
    return {
        "primary_pattern": "食神格",
        "technical_pattern": "食神格",
        "overall_judgment": "normal_pattern",
        "confidence": "high",
    }


def make_climate(
    elements=None,
    primary=None,
    confidence="high",
    day_master_stem="乙",
):
    if elements is None:
        elements = ["火", "水"]

    if primary is None and elements:
        primary = elements[0]

    return {
        "climate_elements": elements,
        "primary_climate_element": primary,
        "confidence": confidence,
        "day_master_stem": day_master_stem,
    }


def make_pattern_useful(
    elements=None,
    primary=None,
    confidence="high",
):
    if elements is None:
        elements = ["火", "土"]

    if primary is None and elements:
        primary = elements[0]

    return {
        "pattern_elements": elements,
        "primary_pattern_element": primary,
        "confidence": confidence,
    }


# ============================================================
# 定数
# ============================================================


def test_elements_are_complete():
    assert ELEMENTS == (
        "木",
        "火",
        "土",
        "金",
        "水",
    )


def test_stem_to_element_complete():
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


def test_generation_cycle():
    assert GENERATES == {
        "木": "火",
        "火": "土",
        "土": "金",
        "金": "水",
        "水": "木",
    }


def test_generated_by_is_inverse():
    for source, target in GENERATES.items():
        assert GENERATED_BY[target] == source


def test_control_cycle():
    assert CONTROLS == {
        "木": "土",
        "火": "金",
        "土": "水",
        "金": "木",
        "水": "火",
    }


def test_controlled_by_is_inverse():
    for source, target in CONTROLS.items():
        assert CONTROLLED_BY[target] == source


def test_v1_metadata():
    assert USEFUL_GODS_METHOD == "useful_gods_v1"
    assert USEFUL_GODS_STATUS == "provisional_useful_gods"


def test_v2_metadata():
    assert USEFUL_GODS_V2_METHOD == "useful_gods_v2"
    assert (
        USEFUL_GODS_V2_STATUS
        == "provisional_useful_gods_v2"
    )


def test_v3_metadata():
    assert USEFUL_GODS_V3_METHOD == "useful_gods_v3"
    assert (
        USEFUL_GODS_V3_STATUS
        == "provisional_useful_gods_v3"
    )


def test_integration_constants():
    assert SUPPORT_FAVORABLE_WEIGHTS == (
        3.0,
        2.0,
        1.0,
    )

    assert SUPPORT_UNFAVORABLE_WEIGHTS == (
        -2.5,
        -1.5,
        -1.0,
    )

    assert CLIMATE_WEIGHTS == (
        3.0,
        1.5,
        1.0,
    )

    assert PATTERN_INTEGRATION_WEIGHTS == (
        3.0,
        2.0,
        1.0,
    )

    assert AGREEMENT_BONUS == 2.0
    assert DOUBLE_SOURCE_BONUS == 1.5
    assert TRIPLE_SOURCE_BONUS == 3.0
    assert SUPPORT_CONFLICT_PENALTY == 1.5


# ============================================================
# 日主五行
# ============================================================


@pytest.mark.parametrize(
    ("stem", "element"),
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
    element,
):
    assert (
        get_day_master_element(stem)
        == element
    )


def test_get_day_master_element_invalid_type():
    with pytest.raises(TypeError):
        get_day_master_element(123)


def test_get_day_master_element_invalid_stem():
    with pytest.raises(ValueError):
        get_day_master_element("A")


# ============================================================
# 五行関係
# ============================================================


def test_wood_relations():
    result = get_element_relations("木")

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
def test_every_element_relation_contains_five_roles(
    element,
):
    result = get_element_relations(
        element
    )

    assert set(result.keys()) == {
        "self",
        "resource",
        "output",
        "wealth",
        "officer",
    }

    assert set(result.values()) == set(
        ELEMENTS
    )


def test_invalid_element_relation():
    with pytest.raises(ValueError):
        get_element_relations("空")


# ============================================================
# weighted_five_elements validation
# ============================================================


def test_validate_weighted_five_elements():
    validate_weighted_five_elements(
        make_weighted_five_elements()
    )


def test_weighted_five_elements_must_be_dict():
    with pytest.raises(TypeError):
        validate_weighted_five_elements(
            []
        )


def test_weighted_five_elements_requires_scores():
    with pytest.raises(ValueError):
        validate_weighted_five_elements(
            {}
        )


@pytest.mark.parametrize(
    "element",
    ELEMENTS,
)
def test_weighted_five_elements_requires_every_element(
    element,
):
    data = make_weighted_five_elements()

    del data["scores"][element]

    with pytest.raises(ValueError):
        validate_weighted_five_elements(
            data
        )


def test_weighted_five_elements_rejects_bool():
    data = make_weighted_five_elements()

    data["scores"]["木"] = True

    with pytest.raises(ValueError):
        validate_weighted_five_elements(
            data
        )


# ============================================================
# 身強身弱正規化
# ============================================================


@pytest.mark.parametrize(
    "label",
    [
        "strong",
        "very_strong",
        "extremely_strong",
    ],
)
def test_strength_class_strong_by_label(
    label,
):
    result = (
        classify_strength_for_useful_gods(
            {
                "technical_label": label,
                "final_score": 10.0,
                "confidence": "high",
            }
        )
    )

    assert result == "strong"


@pytest.mark.parametrize(
    "label",
    [
        "weak",
        "very_weak",
        "extremely_weak",
    ],
)
def test_strength_class_weak_by_label(
    label,
):
    result = (
        classify_strength_for_useful_gods(
            {
                "technical_label": label,
                "final_score": 90.0,
                "confidence": "high",
            }
        )
    )

    assert result == "weak"


@pytest.mark.parametrize(
    "label",
    [
        "balanced",
        "neutral",
    ],
)
def test_strength_class_balanced_by_label(
    label,
):
    result = (
        classify_strength_for_useful_gods(
            {
                "technical_label": label,
                "final_score": 90.0,
                "confidence": "high",
            }
        )
    )

    assert result == "balanced"


def test_strength_fallback_strong():
    result = classify_strength_for_useful_gods(
        {
            "technical_label": "unknown",
            "final_score": 55.0,
            "confidence": "medium",
        }
    )

    assert result == "strong"


def test_strength_fallback_weak():
    result = classify_strength_for_useful_gods(
        {
            "technical_label": "unknown",
            "final_score": 44.999,
            "confidence": "medium",
        }
    )

    assert result == "weak"


def test_strength_fallback_balanced_lower_boundary():
    result = classify_strength_for_useful_gods(
        {
            "technical_label": "unknown",
            "final_score": 45.0,
            "confidence": "medium",
        }
    )

    assert result == "balanced"


def test_strength_fallback_balanced_upper_boundary():
    result = classify_strength_for_useful_gods(
        {
            "technical_label": "unknown",
            "final_score": 54.999,
            "confidence": "medium",
        }
    )

    assert result == "balanced"


# ============================================================
# 扶抑候補
# ============================================================


def test_weak_wood_support_candidates():
    scores = make_weighted_five_elements()[
        "scores"
    ]

    result = build_fuyoku_candidates(
        "木",
        "weak",
        scores,
    )

    # 木の日主:
    # resource = 水
    # self = 木
    #
    # score:
    # 水15 < 木20
    assert result[
        "favorable_elements"
    ] == [
        "水",
        "木",
    ]

    assert set(
        result["unfavorable_elements"]
    ) == {
        "火",
        "土",
        "金",
    }

    assert (
        result["selection_basis"]
        == "weak_day_master_support"
    )


def test_strong_wood_drain_candidates():
    scores = make_weighted_five_elements()[
        "scores"
    ]

    result = build_fuyoku_candidates(
        "木",
        "strong",
        scores,
    )

    # output=火 10
    # officer=金 25
    # wealth=土 30
    assert result[
        "favorable_elements"
    ] == [
        "火",
        "金",
        "土",
    ]

    assert result[
        "unfavorable_elements"
    ] == [
        "木",
        "水",
    ]

    assert (
        result["selection_basis"]
        == "strong_day_master_drain"
    )


def test_balanced_uses_lowest_two_elements():
    scores = make_weighted_five_elements()[
        "scores"
    ]

    result = build_fuyoku_candidates(
        "木",
        "balanced",
        scores,
    )

    assert result[
        "favorable_elements"
    ] == [
        "火",
        "水",
    ]

    assert result[
        "unfavorable_elements"
    ] == []

    assert result[
        "neutral_elements"
    ] == [
        "木",
        "金",
        "土",
    ]


# ============================================================
# v1
# ============================================================


def test_v1_weak_result():
    result = evaluate_useful_gods(
        "乙",
        make_weighted_five_elements(),
        make_weak_judgment(),
        make_pattern_judgment(),
    )

    assert (
        result["method"]
        == USEFUL_GODS_METHOD
    )

    assert (
        result["status"]
        == USEFUL_GODS_STATUS
    )

    assert result[
        "day_master_element"
    ] == "木"

    assert result[
        "strength_class"
    ] == "weak"

    assert result[
        "primary_useful_element"
    ] == "水"

    assert result[
        "favorable_elements"
    ] == [
        "水",
        "木",
    ]


def test_v1_strong_result():
    result = evaluate_useful_gods(
        "乙",
        make_weighted_five_elements(),
        make_strong_judgment(),
        make_pattern_judgment(),
    )

    assert result[
        "strength_class"
    ] == "strong"

    assert result[
        "primary_useful_element"
    ] == "火"

    assert result[
        "favorable_elements"
    ] == [
        "火",
        "金",
        "土",
    ]


def test_v1_balanced_result():
    result = evaluate_useful_gods(
        "乙",
        make_weighted_five_elements(),
        make_balanced_judgment(),
        make_pattern_judgment(),
    )

    assert result[
        "strength_class"
    ] == "balanced"

    assert result[
        "primary_useful_element"
    ] == "火"

    assert result[
        "favorable_elements"
    ] == [
        "火",
        "水",
    ]


# ============================================================
# 調候 validation
# ============================================================


def test_validate_climate_result():
    validate_climate_useful_gods_result(
        make_climate()
    )


def test_climate_must_be_dict():
    with pytest.raises(TypeError):
        validate_climate_useful_gods_result(
            []
        )


def test_climate_requires_elements():
    with pytest.raises(ValueError):
        validate_climate_useful_gods_result(
            {}
        )


def test_climate_invalid_element():
    with pytest.raises(ValueError):
        validate_climate_useful_gods_result(
            {
                "climate_elements": [
                    "空"
                ],
                "primary_climate_element": (
                    "空"
                ),
            }
        )


# ============================================================
# 格局 validation
# ============================================================


def test_validate_pattern_result():
    validate_pattern_useful_gods_result(
        make_pattern_useful()
    )


def test_pattern_must_be_dict():
    with pytest.raises(TypeError):
        validate_pattern_useful_gods_result(
            []
        )


def test_pattern_requires_elements():
    with pytest.raises(ValueError):
        validate_pattern_useful_gods_result(
            {}
        )


def test_pattern_primary_must_match_first():
    with pytest.raises(ValueError):
        validate_pattern_useful_gods_result(
            {
                "pattern_elements": [
                    "火",
                    "土",
                ],
                "primary_pattern_element": (
                    "土"
                ),
            }
        )


def test_pattern_empty_requires_none_primary():
    with pytest.raises(ValueError):
        validate_pattern_useful_gods_result(
            {
                "pattern_elements": [],
                "primary_pattern_element": (
                    "火"
                ),
            }
        )


# ============================================================
# スコア変換
# ============================================================


def test_support_balance_scores():
    support = {
        "favorable_elements": [
            "火",
            "土",
            "金",
        ],
        "unfavorable_elements": [
            "水",
            "木",
        ],
    }

    result = build_support_balance_scores(
        support
    )

    assert result == {
        "木": -1.5,
        "火": 3.0,
        "土": 2.0,
        "金": 1.0,
        "水": -2.5,
    }


def test_climate_scores():
    result = (
        build_climate_integration_scores(
            make_climate(
                elements=[
                    "火",
                    "水",
                    "木",
                ],
                primary="火",
            )
        )
    )

    assert result == {
        "木": 1.0,
        "火": 3.0,
        "土": 0.0,
        "金": 0.0,
        "水": 1.5,
    }


def test_pattern_scores():
    result = (
        build_pattern_integration_scores(
            make_pattern_useful(
                elements=[
                    "火",
                    "土",
                    "金",
                ],
                primary="火",
            )
        )
    )

    assert result == {
        "木": 0.0,
        "火": 3.0,
        "土": 2.0,
        "金": 1.0,
        "水": 0.0,
    }


# ============================================================
# v2 agreement
# ============================================================


def test_v2_strong_agreement():
    support = {
        "favorable_elements": [
            "火",
            "土",
        ],
        "unfavorable_elements": [
            "水",
            "木",
        ],
        "primary_useful_element": "火",
    }

    climate = make_climate(
        elements=[
            "火",
            "金",
        ],
        primary="火",
    )

    result = evaluate_useful_gods_agreement(
        support,
        climate,
    )

    assert (
        result["agreement_level"]
        == "strong_agreement"
    )

    assert result[
        "has_agreement"
    ] is True

    assert "火" in result[
        "agreed_elements"
    ]


def test_v2_conflict():
    support = {
        "favorable_elements": [
            "火",
        ],
        "unfavorable_elements": [
            "水",
            "木",
        ],
        "primary_useful_element": "火",
    }

    climate = make_climate(
        elements=[
            "水",
        ],
        primary="水",
    )

    result = evaluate_useful_gods_agreement(
        support,
        climate,
    )

    assert (
        result["agreement_level"]
        == "conflict"
    )

    assert result[
        "has_conflict"
    ] is True

    assert "水" in result[
        "conflicted_elements"
    ]


# ============================================================
# v2 full integration
# ============================================================


def test_v2_full_result():
    result = evaluate_useful_gods_v2(
        "乙",
        make_weighted_five_elements(),
        make_strong_judgment(),
        make_pattern_judgment(),
        make_climate(
            elements=[
                "火",
                "水",
            ],
            primary="火",
        ),
    )

    assert (
        result["method"]
        == USEFUL_GODS_V2_METHOD
    )

    assert (
        result["status"]
        == USEFUL_GODS_V2_STATUS
    )

    assert result[
        "primary_useful_element"
    ] == result[
        "final_useful_elements"
    ][0]

    assert result[
        "has_useful_candidate"
    ] is True


# ============================================================
# v3 agreement
# ============================================================


def test_v3_triple_agreement():
    support = {
        "favorable_elements": [
            "火",
            "土",
        ],
        "unfavorable_elements": [
            "水",
            "木",
        ],
        "primary_useful_element": "火",
    }

    climate = make_climate(
        elements=[
            "火",
            "金",
        ],
        primary="火",
    )

    pattern = make_pattern_useful(
        elements=[
            "火",
            "土",
        ],
        primary="火",
    )

    result = (
        evaluate_useful_gods_v3_agreement(
            support,
            climate,
            pattern,
        )
    )

    assert (
        result["agreement_level"]
        == "triple_agreement"
    )

    assert result[
        "has_triple_agreement"
    ] is True

    assert "火" in result[
        "triple_agreement_elements"
    ]

    assert (
        result["by_element"]["火"][
            "source_count"
        ]
        == 3
    )


def test_v3_double_agreement():
    support = {
        "favorable_elements": [
            "火",
        ],
        "unfavorable_elements": [
            "水",
        ],
        "primary_useful_element": "火",
    }

    climate = make_climate(
        elements=[
            "金",
        ],
        primary="金",
    )

    pattern = make_pattern_useful(
        elements=[
            "火",
        ],
        primary="火",
    )

    result = (
        evaluate_useful_gods_v3_agreement(
            support,
            climate,
            pattern,
        )
    )

    assert (
        result["agreement_level"]
        == "double_agreement"
    )

    assert result[
        "has_double_agreement"
    ] is True

    assert "火" in result[
        "double_agreement_elements"
    ]


def test_v3_support_conflict():
    support = {
        "favorable_elements": [
            "火",
        ],
        "unfavorable_elements": [
            "水",
        ],
        "primary_useful_element": "火",
    }

    climate = make_climate(
        elements=[
            "水",
        ],
        primary="水",
    )

    pattern = make_pattern_useful(
        elements=[
            "土",
        ],
        primary="土",
    )

    result = (
        evaluate_useful_gods_v3_agreement(
            support,
            climate,
            pattern,
        )
    )

    assert result[
        "has_conflict"
    ] is True

    assert "水" in result[
        "conflicted_elements"
    ]

    assert result[
        "by_element"]["水"][
            "is_support_conflict"
        ] is True


# ============================================================
# v3 integrated score
# ============================================================


def test_v3_integrated_score_triple_bonus():
    support = {
        "favorable_elements": [
            "火",
        ],
        "unfavorable_elements": [],
        "primary_useful_element": "火",
    }

    climate = make_climate(
        elements=[
            "火",
        ],
        primary="火",
    )

    pattern = make_pattern_useful(
        elements=[
            "火",
        ],
        primary="火",
    )

    agreement = (
        evaluate_useful_gods_v3_agreement(
            support,
            climate,
            pattern,
        )
    )

    scores = (
        build_integrated_element_scores_v3(
            support,
            climate,
            pattern,
            agreement,
        )
    )

    # 扶抑 +3
    # 調候 +3
    # 格局 +3
    # 3系統一致 +3
    assert scores["火"] == 12.0


def test_v3_integrated_score_double_bonus():
    support = {
        "favorable_elements": [
            "火",
        ],
        "unfavorable_elements": [],
        "primary_useful_element": "火",
    }

    climate = make_climate(
        elements=[
            "金",
        ],
        primary="金",
    )

    pattern = make_pattern_useful(
        elements=[
            "火",
        ],
        primary="火",
    )

    agreement = (
        evaluate_useful_gods_v3_agreement(
            support,
            climate,
            pattern,
        )
    )

    scores = (
        build_integrated_element_scores_v3(
            support,
            climate,
            pattern,
            agreement,
        )
    )

    # 扶抑 +3
    # 格局 +3
    # 2系統一致 +1.5
    assert scores["火"] == 7.5


def test_v3_integrated_score_conflict_penalty():
    support = {
        "favorable_elements": [
            "火",
        ],
        "unfavorable_elements": [
            "水",
        ],
        "primary_useful_element": "火",
    }

    climate = make_climate(
        elements=[
            "水",
        ],
        primary="水",
    )

    pattern = make_pattern_useful(
        elements=[],
        primary=None,
    )

    agreement = (
        evaluate_useful_gods_v3_agreement(
            support,
            climate,
            pattern,
        )
    )

    scores = (
        build_integrated_element_scores_v3(
            support,
            climate,
            pattern,
            agreement,
        )
    )

    # 扶抑忌神第一候補 -2.5
    # 調候第一候補 +3
    # 競合ペナルティ -1.5
    #
    # total = -1.0
    assert scores["水"] == -1.0


# ============================================================
# ranking
# ============================================================


def test_rank_integrated_useful_elements():
    scores = {
        "木": -1.0,
        "火": 10.0,
        "土": 4.0,
        "金": 0.0,
        "水": 2.0,
    }

    result = rank_integrated_useful_elements(
        scores
    )

    assert result == [
        "火",
        "土",
        "水",
    ]


def test_rank_excludes_zero():
    scores = {
        "木": 0.0,
        "火": 0.0,
        "土": 0.0,
        "金": 0.0,
        "水": 0.0,
    }

    result = rank_integrated_useful_elements(
        scores
    )

    assert result == []


def test_rank_tie_uses_element_order():
    scores = {
        "木": 5.0,
        "火": 5.0,
        "土": 5.0,
        "金": 5.0,
        "水": 5.0,
    }

    result = rank_integrated_useful_elements(
        scores
    )

    assert result == [
        "木",
        "火",
        "土",
        "金",
        "水",
    ]


# ============================================================
# candidate details
# ============================================================


def test_v3_candidate_details():
    support = {
        "favorable_elements": [
            "火",
        ],
        "unfavorable_elements": [],
        "primary_useful_element": "火",
    }

    climate = make_climate(
        elements=[
            "火",
        ],
        primary="火",
    )

    pattern = make_pattern_useful(
        elements=[
            "火",
        ],
        primary="火",
    )

    agreement = (
        evaluate_useful_gods_v3_agreement(
            support,
            climate,
            pattern,
        )
    )

    scores = (
        build_integrated_element_scores_v3(
            support,
            climate,
            pattern,
            agreement,
        )
    )

    ranked = rank_integrated_useful_elements(
        scores
    )

    details = (
        build_integrated_candidate_details_v3(
            ranked,
            scores,
            support,
            climate,
            pattern,
            agreement,
        )
    )

    fire = details[0]

    assert fire["element"] == "火"
    assert fire["priority"] == 1
    assert fire["integrated_score"] == 12.0
    assert fire["support_balance_score"] == 3.0
    assert fire["climate_score"] == 3.0
    assert fire["pattern_score"] == 3.0
    assert fire["agreement_bonus"] == 3.0
    assert fire["conflict_penalty"] == 0.0
    assert fire["source_count"] == 3
    assert fire["is_triple_agreement"] is True
    assert fire["is_double_agreement"] is False
    assert fire["is_conflicted"] is False


# ============================================================
# v3 full integration
# ============================================================


def test_v3_full_integration():
    result = evaluate_useful_gods_v3(
        "乙",
        make_weighted_five_elements(),
        make_strong_judgment(),
        make_pattern_judgment(),
        make_climate(
            elements=[
                "火",
                "水",
            ],
            primary="火",
            confidence="high",
        ),
        make_pattern_useful(
            elements=[
                "火",
                "土",
            ],
            primary="火",
            confidence="high",
        ),
    )

    assert (
        result["method"]
        == USEFUL_GODS_V3_METHOD
    )

    assert (
        result["status"]
        == USEFUL_GODS_V3_STATUS
    )

    assert result[
        "has_useful_candidate"
    ] is True

    assert result[
        "day_master_stem"
    ] == "乙"

    assert result[
        "day_master_element"
    ] == "木"

    assert result[
        "strength_class"
    ] == "strong"

    assert result[
        "primary_useful_element"
    ] == result[
        "final_useful_elements"
    ][0]

    assert result[
        "primary_useful_element"
    ] == "火"

    assert (
        result["agreement"][
            "has_triple_agreement"
        ]
        is True
    )

    assert "火" in result[
        "agreement"
    ][
        "triple_agreement_elements"
    ]

    assert (
        result[
            "integrated_element_scores"
        ]["火"]
        > 0
    )


def test_v3_primary_matches_first_candidate():
    result = evaluate_useful_gods_v3(
        "乙",
        make_weighted_five_elements(),
        make_strong_judgment(),
        make_pattern_judgment(),
        make_climate(),
        make_pattern_useful(),
    )

    assert result[
        "primary_useful_element"
    ] == result[
        "final_useful_elements"
    ][0]

    assert result[
        "final_candidates"
    ][0][
        "element"
    ] == result[
        "primary_useful_element"
    ]

    assert result[
        "final_candidates"
    ][0][
        "priority"
    ] == 1


def test_v3_final_elements_are_positive():
    result = evaluate_useful_gods_v3(
        "乙",
        make_weighted_five_elements(),
        make_strong_judgment(),
        make_pattern_judgment(),
        make_climate(),
        make_pattern_useful(),
    )

    scores = result[
        "integrated_element_scores"
    ]

    for element in result[
        "final_useful_elements"
    ]:
        assert scores[element] > 0.0


def test_v3_final_elements_sorted_descending():
    result = evaluate_useful_gods_v3(
        "乙",
        make_weighted_five_elements(),
        make_strong_judgment(),
        make_pattern_judgment(),
        make_climate(),
        make_pattern_useful(),
    )

    scores = result[
        "integrated_element_scores"
    ]

    ranked_scores = [
        scores[element]
        for element in result[
            "final_useful_elements"
        ]
    ]

    assert ranked_scores == sorted(
        ranked_scores,
        reverse=True,
    )


def test_v3_contains_v2_baseline():
    result = evaluate_useful_gods_v3(
        "乙",
        make_weighted_five_elements(),
        make_strong_judgment(),
        make_pattern_judgment(),
        make_climate(),
        make_pattern_useful(),
    )

    assert "v2_baseline" in result

    assert (
        result["v2_baseline"]["method"]
        == USEFUL_GODS_V2_METHOD
    )


def test_v3_contains_all_three_layers():
    result = evaluate_useful_gods_v3(
        "乙",
        make_weighted_five_elements(),
        make_strong_judgment(),
        make_pattern_judgment(),
        make_climate(),
        make_pattern_useful(),
    )

    assert "support_balance" in result
    assert "climate" in result
    assert "pattern" in result
    assert "agreement" in result


def test_v3_evidence_integrity():
    weighted = (
        make_weighted_five_elements()
    )

    strength = make_strong_judgment()
    pattern_judgment = (
        make_pattern_judgment()
    )

    climate = make_climate()
    pattern_useful = (
        make_pattern_useful()
    )

    result = evaluate_useful_gods_v3(
        "乙",
        weighted,
        strength,
        pattern_judgment,
        climate,
        pattern_useful,
    )

    evidence = result["evidence"]

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
        == pattern_judgment
    )

    assert (
        evidence[
            "climate_useful_gods"
        ]
        == climate
    )

    assert (
        evidence[
            "pattern_useful_gods"
        ]
        == pattern_useful
    )


def test_v3_reasoning_exists():
    result = evaluate_useful_gods_v3(
        "乙",
        make_weighted_five_elements(),
        make_strong_judgment(),
        make_pattern_judgment(),
        make_climate(),
        make_pattern_useful(),
    )

    assert isinstance(
        result["reasoning"],
        list,
    )

    assert result["reasoning"]

    assert all(
        isinstance(item, str)
        and item
        for item in result[
            "reasoning"
        ]
    )


def test_v3_notes_exist():
    result = evaluate_useful_gods_v3(
        "乙",
        make_weighted_five_elements(),
        make_strong_judgment(),
        make_pattern_judgment(),
        make_climate(),
        make_pattern_useful(),
    )

    assert isinstance(
        result["notes"],
        list,
    )

    assert result["notes"]


# ============================================================
# confidence
# ============================================================


def test_v3_triple_agreement_high_confidence():
    result = evaluate_useful_gods_v3(
        "乙",
        make_weighted_five_elements(),
        make_strong_judgment(),
        make_pattern_judgment(),
        make_climate(
            elements=["火"],
            primary="火",
            confidence="high",
        ),
        make_pattern_useful(
            elements=["火"],
            primary="火",
            confidence="high",
        ),
    )

    assert (
        result["primary_useful_element"]
        == "火"
    )

    assert result[
        "confidence"
    ] == "high"


def test_v3_confidence_is_valid():
    result = evaluate_useful_gods_v3(
        "乙",
        make_weighted_five_elements(),
        make_strong_judgment(),
        make_pattern_judgment(),
        make_climate(),
        make_pattern_useful(),
    )

    assert result["confidence"] in {
        "high",
        "medium",
        "low",
    }


# ============================================================
# consistency
# ============================================================


def test_v3_candidate_priority_contiguous():
    result = evaluate_useful_gods_v3(
        "乙",
        make_weighted_five_elements(),
        make_strong_judgment(),
        make_pattern_judgment(),
        make_climate(),
        make_pattern_useful(),
    )

    candidates = result[
        "final_candidates"
    ]

    priorities = [
        candidate["priority"]
        for candidate in candidates
    ]

    assert priorities == list(
        range(
            1,
            len(candidates) + 1,
        )
    )


def test_v3_candidate_elements_match_final_elements():
    result = evaluate_useful_gods_v3(
        "乙",
        make_weighted_five_elements(),
        make_strong_judgment(),
        make_pattern_judgment(),
        make_climate(),
        make_pattern_useful(),
    )

    candidate_elements = [
        candidate["element"]
        for candidate in result[
            "final_candidates"
        ]
    ]

    assert (
        candidate_elements
        == result[
            "final_useful_elements"
        ]
    )


def test_v3_all_integrated_elements_present():
    result = evaluate_useful_gods_v3(
        "乙",
        make_weighted_five_elements(),
        make_strong_judgment(),
        make_pattern_judgment(),
        make_climate(),
        make_pattern_useful(),
    )

    assert set(
        result[
            "integrated_element_scores"
        ].keys()
    ) == set(
        ELEMENTS
    )


def test_v3_secondary_matches_tail():
    result = evaluate_useful_gods_v3(
        "乙",
        make_weighted_five_elements(),
        make_strong_judgment(),
        make_pattern_judgment(),
        make_climate(),
        make_pattern_useful(),
    )

    assert result[
        "secondary_useful_elements"
    ] == result[
        "final_useful_elements"
    ][1:]


# ============================================================
# day master consistency
# ============================================================


def test_v3_climate_day_master_mismatch():
    with pytest.raises(ValueError):
        evaluate_useful_gods_v3(
            "乙",
            make_weighted_five_elements(),
            make_strong_judgment(),
            make_pattern_judgment(),
            make_climate(
                day_master_stem="甲",
            ),
            make_pattern_useful(),
        )


# ============================================================
# 後方互換
# ============================================================


def test_v1_still_available():
    result = evaluate_useful_gods(
        "乙",
        make_weighted_five_elements(),
        make_strong_judgment(),
        make_pattern_judgment(),
    )

    assert (
        result["method"]
        == "useful_gods_v1"
    )


def test_v2_still_available():
    result = evaluate_useful_gods_v2(
        "乙",
        make_weighted_five_elements(),
        make_strong_judgment(),
        make_pattern_judgment(),
        make_climate(),
    )

    assert (
        result["method"]
        == "useful_gods_v2"
    )


def test_v3_available():
    result = evaluate_useful_gods_v3(
        "乙",
        make_weighted_five_elements(),
        make_strong_judgment(),
        make_pattern_judgment(),
        make_climate(),
        make_pattern_useful(),
    )

    assert (
        result["method"]
        == "useful_gods_v3"
    )


# ============================================================
# 最終構造保証
# ============================================================


def test_v3_required_keys():
    result = evaluate_useful_gods_v3(
        "乙",
        make_weighted_five_elements(),
        make_strong_judgment(),
        make_pattern_judgment(),
        make_climate(),
        make_pattern_useful(),
    )

    required = {
        "has_useful_candidate",
        "primary_useful_element",
        "secondary_useful_elements",
        "final_useful_elements",
        "final_candidates",
        "integrated_element_scores",
        "support_balance",
        "climate",
        "pattern",
        "v2_baseline",
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

    assert required.issubset(
        result.keys()
    )


def test_v3_method_status_final_regression():
    result = evaluate_useful_gods_v3(
        "乙",
        make_weighted_five_elements(),
        make_strong_judgment(),
        make_pattern_judgment(),
        make_climate(),
        make_pattern_useful(),
    )

    assert result["method"] == (
        "useful_gods_v3"
    )

    assert result["status"] == (
        "provisional_useful_gods_v3"
    )
