"""
engine.pattern_useful_gods の単体テスト。

対象:
- 入力検証
- 日主五行
- 五行関係
- 格局情報抽出
- 対応格局判定
- 格局ルール取得
- 五行量補正
- 候補生成・統合
- confidence
- reasoning
- 10種類の格局
- 候補なし / 未対応格局
- evidence / metadata
- 1985年検証スタイル
"""

import pytest

from engine.pattern_useful_gods import (
    ELEMENTS,
    PATTERN_RULES,
    VALID_TECHNICAL_PATTERNS,
    build_pattern_candidate,
    build_reasoning,
    calculate_pattern_useful_confidence,
    calculate_presence_adjustment,
    evaluate_pattern_useful_gods,
    extract_pattern_info,
    get_day_master_element,
    get_element_relations,
    get_element_score,
    get_pattern_rules,
    is_supported_pattern,
    merge_pattern_candidates,
    relation_to_element,
    validate_day_master_stem,
    validate_pattern_judgment,
    validate_weighted_five_elements,
)


# =========================================================
# Test helpers
# =========================================================


def make_pattern_judgment(
    *,
    has_pattern=True,
    primary_pattern="偏財格",
    technical_pattern="indirect_wealth",
    overall_judgment="provisional_possible",
    confidence="medium",
    primary_judgment=None,
):
    if (
        primary_judgment is None
        and has_pattern
    ):
        primary_judgment = {
            "pattern": primary_pattern,
            "technical_pattern": technical_pattern,
            "final_judgment": overall_judgment,
            "confidence": confidence,
        }

    return {
        "has_pattern_candidate": has_pattern,
        "has_pattern": has_pattern,
        "judgment_count": (
            1
            if has_pattern
            else 0
        ),
        "primary_pattern": (
            primary_pattern
            if has_pattern
            else None
        ),
        "technical_pattern": (
            technical_pattern
            if has_pattern
            else None
        ),
        "primary_judgment": (
            primary_judgment
            if has_pattern
            else None
        ),
        "judgments": (
            [
                primary_judgment
            ]
            if (
                has_pattern
                and primary_judgment
                is not None
            )
            else []
        ),
        "strong_count": 0,
        "possible_count": (
            1
            if (
                has_pattern
                and overall_judgment
                == "provisional_possible"
            )
            else 0
        ),
        "weakened_count": 0,
        "school_rule_count": (
            1
            if (
                has_pattern
                and overall_judgment
                == "requires_school_rule"
            )
            else 0
        ),
        "overall_judgment": (
            overall_judgment
            if has_pattern
            else "not_applicable"
        ),
        "confidence": (
            confidence
            if has_pattern
            else "low"
        ),
        "evidence": {},
        "method": "pattern_judgment_v2",
        "status": (
            "provisional_pattern_judgment_v2"
        ),
        "notes": [],
    }


def make_weighted_five_elements(
    *,
    wood=1.0,
    fire=1.0,
    earth=1.0,
    metal=1.0,
    water=1.0,
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
            "weighted_five_elements_test_fixture"
        ),
    }


# =========================================================
# Constants
# =========================================================


def test_elements():
    assert ELEMENTS == (
        "木",
        "火",
        "土",
        "金",
        "水",
    )


def test_valid_technical_patterns():
    assert VALID_TECHNICAL_PATTERNS == {
        "direct_officer",
        "seven_killings",
        "direct_wealth",
        "indirect_wealth",
        "direct_resource",
        "indirect_resource",
        "eating_god",
        "hurting_officer",
        "jianlu",
        "yangren",
    }


def test_pattern_rules_cover_supported_patterns():
    assert (
        set(
            PATTERN_RULES.keys()
        )
        == VALID_TECHNICAL_PATTERNS
    )


# =========================================================
# Validation
# =========================================================


@pytest.mark.parametrize(
    "stem",
    [
        "甲",
        "乙",
        "丙",
        "丁",
        "戊",
        "己",
        "庚",
        "辛",
        "壬",
        "癸",
    ],
)
def test_validate_day_master_stem_valid(
    stem,
):
    assert (
        validate_day_master_stem(
            stem
        )
        is None
    )


def test_validate_day_master_stem_type_error():
    with pytest.raises(
        TypeError,
        match="day_master_stemはstr型",
    ):
        validate_day_master_stem(
            1
        )


def test_validate_day_master_stem_value_error():
    with pytest.raises(
        ValueError,
        match="不正な日干",
    ):
        validate_day_master_stem(
            "A"
        )


def test_validate_pattern_judgment_valid():
    assert (
        validate_pattern_judgment(
            {}
        )
        is None
    )


def test_validate_pattern_judgment_type_error():
    with pytest.raises(
        TypeError,
        match="pattern_judgmentはdict型",
    ):
        validate_pattern_judgment(
            []
        )


def test_validate_weighted_five_elements_none():
    assert (
        validate_weighted_five_elements(
            None
        )
        is None
    )


def test_validate_weighted_five_elements_valid():
    assert (
        validate_weighted_five_elements(
            make_weighted_five_elements()
        )
        is None
    )


def test_validate_weighted_five_elements_without_scores():
    assert (
        validate_weighted_five_elements(
            {}
        )
        is None
    )


def test_validate_weighted_five_elements_type_error():
    with pytest.raises(
        TypeError,
        match=(
            "weighted_five_elementsは"
            "dict型またはNone"
        ),
    ):
        validate_weighted_five_elements(
            []
        )


def test_validate_weighted_scores_type_error():
    with pytest.raises(
        TypeError,
        match=(
            r"weighted_five_elements"
            r"\['scores'\]はdict型"
        ),
    ):
        validate_weighted_five_elements(
            {
                "scores": [],
            }
        )


# =========================================================
# Day master / element relations
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


@pytest.mark.parametrize(
    (
        "day_master_element",
        "expected",
    ),
    [
        (
            "木",
            {
                "peer": "木",
                "resource": "水",
                "output": "火",
                "wealth": "土",
                "officer": "金",
            },
        ),
        (
            "火",
            {
                "peer": "火",
                "resource": "木",
                "output": "土",
                "wealth": "金",
                "officer": "水",
            },
        ),
        (
            "土",
            {
                "peer": "土",
                "resource": "火",
                "output": "金",
                "wealth": "水",
                "officer": "木",
            },
        ),
        (
            "金",
            {
                "peer": "金",
                "resource": "土",
                "output": "水",
                "wealth": "木",
                "officer": "火",
            },
        ),
        (
            "水",
            {
                "peer": "水",
                "resource": "金",
                "output": "木",
                "wealth": "火",
                "officer": "土",
            },
        ),
    ],
)
def test_get_element_relations(
    day_master_element,
    expected,
):
    assert (
        get_element_relations(
            day_master_element
        )
        == expected
    )


def test_get_element_relations_invalid():
    with pytest.raises(
        ValueError,
        match="不正な五行",
    ):
        get_element_relations(
            "空"
        )


def test_relation_to_element():
    relations = (
        get_element_relations(
            "木"
        )
    )

    assert (
        relation_to_element(
            "resource",
            relations,
        )
        == "水"
    )

    assert (
        relation_to_element(
            "output",
            relations,
        )
        == "火"
    )

    assert (
        relation_to_element(
            "wealth",
            relations,
        )
        == "土"
    )

    assert (
        relation_to_element(
            "officer",
            relations,
        )
        == "金"
    )


def test_relation_to_element_invalid():
    with pytest.raises(
        ValueError,
        match="不正な五行関係",
    ):
        relation_to_element(
            "unknown",
            get_element_relations(
                "木"
            ),
        )


# =========================================================
# Pattern extraction / support
# =========================================================


def test_extract_pattern_info():
    judgment = make_pattern_judgment(
        primary_pattern="正官格",
        technical_pattern=(
            "direct_officer"
        ),
        overall_judgment=(
            "provisional_established"
        ),
        confidence="high",
    )

    result = extract_pattern_info(
        judgment
    )

    assert result[
        "has_pattern"
    ] is True

    assert result[
        "primary_pattern"
    ] == "正官格"

    assert result[
        "technical_pattern"
    ] == "direct_officer"

    assert result[
        "overall_judgment"
    ] == "provisional_established"

    assert result[
        "confidence"
    ] == "high"

    assert isinstance(
        result[
            "primary_judgment"
        ],
        dict,
    )


def test_extract_pattern_info_no_pattern():
    result = extract_pattern_info(
        make_pattern_judgment(
            has_pattern=False
        )
    )

    assert result == {
        "has_pattern": False,
        "primary_pattern": None,
        "technical_pattern": None,
        "primary_judgment": None,
        "overall_judgment": (
            "not_applicable"
        ),
        "confidence": "low",
    }


def test_extract_pattern_info_invalid_primary_judgment():
    judgment = make_pattern_judgment()
    judgment[
        "primary_judgment"
    ] = []

    result = extract_pattern_info(
        judgment
    )

    assert (
        result[
            "primary_judgment"
        ]
        is None
    )


@pytest.mark.parametrize(
    "technical_pattern",
    sorted(
        VALID_TECHNICAL_PATTERNS
    ),
)
def test_is_supported_pattern_true(
    technical_pattern,
):
    assert (
        is_supported_pattern(
            technical_pattern
        )
        is True
    )


@pytest.mark.parametrize(
    "technical_pattern",
    [
        None,
        "follow_wealth",
        "transformation",
        "unknown",
    ],
)
def test_is_supported_pattern_false(
    technical_pattern,
):
    assert (
        is_supported_pattern(
            technical_pattern
        )
        is False
    )


def test_get_pattern_rules_supported():
    rules = get_pattern_rules(
        "direct_officer"
    )

    assert len(
        rules
    ) == 2

    assert rules[0] == {
        "relation": "resource",
        "role": "protect_officer",
        "weight": 3.0,
    }


def test_get_pattern_rules_unsupported():
    assert (
        get_pattern_rules(
            "unknown"
        )
        == ()
    )


# =========================================================
# Weighted element helpers
# =========================================================


def test_get_element_score_none():
    assert (
        get_element_score(
            "木",
            None,
        )
        is None
    )


def test_get_element_score_without_scores():
    assert (
        get_element_score(
            "木",
            {},
        )
        is None
    )


def test_get_element_score_numeric():
    weighted = (
        make_weighted_five_elements(
            wood=2.5
        )
    )

    assert (
        get_element_score(
            "木",
            weighted,
        )
        == 2.5
    )


def test_get_element_score_bool_is_none():
    weighted = (
        make_weighted_five_elements()
    )

    weighted[
        "scores"
    ][
        "木"
    ] = True

    assert (
        get_element_score(
            "木",
            weighted,
        )
        is None
    )


def test_get_element_score_non_numeric_is_none():
    weighted = (
        make_weighted_five_elements()
    )

    weighted[
        "scores"
    ][
        "木"
    ] = "1.0"

    assert (
        get_element_score(
            "木",
            weighted,
        )
        is None
    )


@pytest.mark.parametrize(
    (
        "score",
        "expected",
    ),
    [
        (None, 0.0),
        (-1.0, 0.5),
        (0.0, 0.5),
        (0.5, 0.3),
        (0.999, 0.3),
        (1.0, 0.0),
        (3.999, 0.0),
        (4.0, -0.3),
        (10.0, -0.3),
    ],
)
def test_calculate_presence_adjustment(
    score,
    expected,
):
    assert (
        calculate_presence_adjustment(
            score
        )
        == expected
    )


# =========================================================
# Candidate building / merging
# =========================================================


def test_build_pattern_candidate_without_weighted():
    result = build_pattern_candidate(
        element="水",
        relation="resource",
        role="protect_officer",
        base_weight=3.0,
        weighted_five_elements=None,
    )

    assert result == {
        "element": "水",
        "relation": "resource",
        "role": "protect_officer",
        "base_weight": 3.0,
        "element_score": None,
        "presence_adjustment": 0.0,
        "score": 3.0,
    }


def test_build_pattern_candidate_low_element_bonus():
    weighted = (
        make_weighted_five_elements(
            water=0.5
        )
    )

    result = build_pattern_candidate(
        element="水",
        relation="resource",
        role="protect_officer",
        base_weight=3.0,
        weighted_five_elements=weighted,
    )

    assert result[
        "element_score"
    ] == 0.5

    assert result[
        "presence_adjustment"
    ] == 0.3

    assert result[
        "score"
    ] == 3.3


def test_build_pattern_candidate_absent_bonus():
    weighted = (
        make_weighted_five_elements(
            water=0.0
        )
    )

    result = build_pattern_candidate(
        element="水",
        relation="resource",
        role="protect_officer",
        base_weight=3.0,
        weighted_five_elements=weighted,
    )

    assert result[
        "presence_adjustment"
    ] == 0.5

    assert result[
        "score"
    ] == 3.5


def test_build_pattern_candidate_excess_penalty():
    weighted = (
        make_weighted_five_elements(
            water=4.0
        )
    )

    result = build_pattern_candidate(
        element="水",
        relation="resource",
        role="protect_officer",
        base_weight=3.0,
        weighted_five_elements=weighted,
    )

    assert result[
        "presence_adjustment"
    ] == -0.3

    assert result[
        "score"
    ] == 2.7


def test_merge_pattern_candidates_empty():
    assert (
        merge_pattern_candidates(
            []
        )
        == []
    )


def test_merge_pattern_candidates_priority():
    result = merge_pattern_candidates(
        [
            {
                "element": "金",
                "relation": "officer",
                "role": "role_b",
                "base_weight": 2.0,
                "element_score": 1.0,
                "presence_adjustment": 0.0,
                "score": 2.0,
            },
            {
                "element": "火",
                "relation": "output",
                "role": "role_a",
                "base_weight": 3.0,
                "element_score": 1.0,
                "presence_adjustment": 0.0,
                "score": 3.0,
            },
        ]
    )

    assert [
        item[
            "element"
        ]
        for item in result
    ] == [
        "火",
        "金",
    ]

    assert [
        item[
            "priority"
        ]
        for item in result
    ] == [
        1,
        2,
    ]


def test_merge_pattern_candidates_same_element():
    result = merge_pattern_candidates(
        [
            {
                "element": "水",
                "relation": "resource",
                "role": "role_a",
                "base_weight": 2.0,
                "element_score": 1.0,
                "presence_adjustment": 0.0,
                "score": 2.0,
            },
            {
                "element": "水",
                "relation": "officer",
                "role": "role_b",
                "base_weight": 3.0,
                "element_score": 1.0,
                "presence_adjustment": 0.0,
                "score": 3.0,
            },
        ]
    )

    assert len(
        result
    ) == 1

    candidate = result[0]

    assert candidate[
        "element"
    ] == "水"

    assert candidate[
        "score"
    ] == 3.0

    assert candidate[
        "roles"
    ] == [
        "role_a",
        "role_b",
    ]

    assert candidate[
        "relations"
    ] == [
        "resource",
        "officer",
    ]

    assert candidate[
        "base_weights"
    ] == [
        2.0,
        3.0,
    ]

    assert candidate[
        "priority"
    ] == 1


def test_merge_pattern_candidates_stable_element_order():
    result = merge_pattern_candidates(
        [
            {
                "element": "水",
                "relation": "resource",
                "role": "a",
                "base_weight": 2.0,
                "element_score": None,
                "presence_adjustment": 0.0,
                "score": 2.0,
            },
            {
                "element": "木",
                "relation": "peer",
                "role": "b",
                "base_weight": 2.0,
                "element_score": None,
                "presence_adjustment": 0.0,
                "score": 2.0,
            },
        ]
    )

    assert [
        item[
            "element"
        ]
        for item in result
    ] == [
        "木",
        "水",
    ]


# =========================================================
# Confidence
# =========================================================


def test_confidence_no_candidates():
    result = (
        calculate_pattern_useful_confidence(
            {
                "overall_judgment": (
                    "provisional_established"
                ),
                "confidence": "high",
            },
            [],
        )
    )

    assert result == "low"


def test_confidence_high():
    result = (
        calculate_pattern_useful_confidence(
            {
                "overall_judgment": (
                    "provisional_established"
                ),
                "confidence": "high",
            },
            [
                {
                    "element": "水",
                },
            ],
        )
    )

    assert result == "high"


@pytest.mark.parametrize(
    "overall_judgment",
    [
        "provisional_established",
        "provisional_possible",
    ],
)
def test_confidence_medium(
    overall_judgment,
):
    result = (
        calculate_pattern_useful_confidence(
            {
                "overall_judgment": (
                    overall_judgment
                ),
                "confidence": "medium",
            },
            [
                {
                    "element": "水",
                },
            ],
        )
    )

    assert result == "medium"


@pytest.mark.parametrize(
    "overall_judgment",
    [
        "provisional_weakened",
        "requires_school_rule",
        "not_applicable",
    ],
)
def test_confidence_low(
    overall_judgment,
):
    result = (
        calculate_pattern_useful_confidence(
            {
                "overall_judgment": (
                    overall_judgment
                ),
                "confidence": "high",
            },
            [
                {
                    "element": "水",
                },
            ],
        )
    )

    assert result == "low"


# =========================================================
# Reasoning
# =========================================================


def test_build_reasoning_uses_primary_pattern():
    result = build_reasoning(
        {
            "primary_pattern": "正官格",
            "technical_pattern": (
                "direct_officer"
            ),
        },
        [
            {
                "roles": [
                    "protect_officer",
                ],
            },
        ],
    )

    assert result[0] == (
        "代表格局を正官格として評価しました。"
    )

    assert any(
        "正官を保護"
        in message
        for message in result
    )


def test_build_reasoning_falls_back_to_japanese_name():
    result = build_reasoning(
        {
            "primary_pattern": None,
            "technical_pattern": (
                "direct_officer"
            ),
        },
        [],
    )

    assert result == [
        (
            "代表格局を正官格として"
            "評価しました。"
        ),
    ]


def test_build_reasoning_deduplicates_roles():
    result = build_reasoning(
        {
            "primary_pattern": "正官格",
            "technical_pattern": (
                "direct_officer"
            ),
        },
        [
            {
                "roles": [
                    "protect_officer",
                ],
            },
            {
                "roles": [
                    "protect_officer",
                ],
            },
        ],
    )

    assert (
        sum(
            1
            for message in result
            if "正官を保護"
            in message
        )
        == 1
    )


# =========================================================
# Main evaluator - standard patterns
# 日主は甲（木）で固定
#
# peer     = 木
# resource = 水
# output   = 火
# wealth   = 土
# officer  = 金
# =========================================================


@pytest.mark.parametrize(
    (
        "primary_pattern",
        "technical_pattern",
        "expected_elements",
    ),
    [
        (
            "正官格",
            "direct_officer",
            [
                "水",
                "土",
            ],
        ),
        (
            "偏官格",
            "seven_killings",
            [
                "火",
                "水",
            ],
        ),
        (
            "正財格",
            "direct_wealth",
            [
                "火",
                "金",
            ],
        ),
        (
            "偏財格",
            "indirect_wealth",
            [
                "火",
                "金",
            ],
        ),
        (
            "印綬格",
            "direct_resource",
            [
                "金",
                "木",
            ],
        ),
        (
            "偏印格",
            "indirect_resource",
            [
                "土",
                "金",
            ],
        ),
        (
            "食神格",
            "eating_god",
            [
                "土",
                "火",
            ],
        ),
        (
            "傷官格",
            "hurting_officer",
            [
                "土",
                "水",
            ],
        ),
        (
            "建禄格",
            "jianlu",
            [
                "火",
                "土",
                "金",
            ],
        ),
        (
            "羊刃格",
            "yangren",
            [
                "金",
                "火",
                "土",
            ],
        ),
    ],
)
def test_evaluate_supported_pattern_for_wood_day_master(
    primary_pattern,
    technical_pattern,
    expected_elements,
):
    judgment = make_pattern_judgment(
        primary_pattern=primary_pattern,
        technical_pattern=technical_pattern,
    )

    result = evaluate_pattern_useful_gods(
        "甲",
        judgment,
    )

    assert (
        result[
            "has_pattern_useful_candidate"
        ]
        is True
    )

    assert (
        result[
            "supported_pattern"
        ]
        is True
    )

    assert (
        result[
            "primary_pattern"
        ]
        == primary_pattern
    )

    assert (
        result[
            "technical_pattern"
        ]
        == technical_pattern
    )

    assert (
        result[
            "pattern_elements"
        ]
        == expected_elements
    )

    assert (
        result[
            "primary_pattern_element"
        ]
        == expected_elements[0]
    )

    assert (
        result[
            "secondary_pattern_elements"
        ]
        == expected_elements[1:]
    )


# =========================================================
# Main evaluator - different day masters
# =========================================================


@pytest.mark.parametrize(
    (
        "stem",
        "expected_resource",
        "expected_wealth",
    ),
    [
        ("甲", "水", "土"),
        ("丙", "木", "金"),
        ("戊", "火", "水"),
        ("庚", "土", "木"),
        ("壬", "金", "火"),
    ],
)
def test_direct_officer_changes_with_day_master(
    stem,
    expected_resource,
    expected_wealth,
):
    result = evaluate_pattern_useful_gods(
        stem,
        make_pattern_judgment(
            primary_pattern="正官格",
            technical_pattern=(
                "direct_officer"
            ),
        ),
    )

    assert (
        result[
            "pattern_elements"
        ]
        == [
            expected_resource,
            expected_wealth,
        ]
    )


# =========================================================
# Main evaluator - structure
# =========================================================


def test_evaluate_pattern_useful_gods_required_keys():
    result = evaluate_pattern_useful_gods(
        "甲",
        make_pattern_judgment(),
    )

    required_keys = {
        "has_pattern_useful_candidate",
        "primary_pattern_element",
        "secondary_pattern_elements",
        "pattern_elements",
        "pattern_candidates",
        "day_master_stem",
        "day_master_element",
        "primary_pattern",
        "technical_pattern",
        "pattern_overall_judgment",
        "pattern_confidence",
        "supported_pattern",
        "element_relations",
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


def test_evaluate_pattern_useful_gods_metadata():
    result = evaluate_pattern_useful_gods(
        "甲",
        make_pattern_judgment(),
    )

    assert (
        result[
            "method"
        ]
        == "pattern_useful_gods_v1"
    )

    assert (
        result[
            "status"
        ]
        == "provisional_pattern_useful_gods"
    )

    assert (
        result[
            "day_master_stem"
        ]
        == "甲"
    )

    assert (
        result[
            "day_master_element"
        ]
        == "木"
    )


def test_evaluate_pattern_useful_gods_element_relations():
    result = evaluate_pattern_useful_gods(
        "甲",
        make_pattern_judgment(),
    )

    assert result[
        "element_relations"
    ] == {
        "peer": "木",
        "resource": "水",
        "output": "火",
        "wealth": "土",
        "officer": "金",
    }


def test_evaluate_pattern_useful_gods_candidate_priorities():
    result = evaluate_pattern_useful_gods(
        "甲",
        make_pattern_judgment(
            primary_pattern="建禄格",
            technical_pattern="jianlu",
        ),
    )

    candidates = result[
        "pattern_candidates"
    ]

    assert [
        candidate[
            "priority"
        ]
        for candidate in candidates
    ] == [
        1,
        2,
        3,
    ]

    assert [
        candidate[
            "element"
        ]
        for candidate in candidates
    ] == result[
        "pattern_elements"
    ]


def test_evaluate_pattern_useful_gods_evidence():
    judgment = make_pattern_judgment()
    weighted = (
        make_weighted_five_elements()
    )

    result = evaluate_pattern_useful_gods(
        "甲",
        judgment,
        weighted,
    )

    evidence = result[
        "evidence"
    ]

    assert (
        evidence[
            "pattern_judgment"
        ]
        == judgment
    )

    assert (
        evidence[
            "weighted_five_elements"
        ]
        == weighted
    )

    assert (
        evidence[
            "pattern_info"
        ][
            "technical_pattern"
        ]
        == "indirect_wealth"
    )

    assert isinstance(
        evidence[
            "raw_candidates"
        ],
        list,
    )

    assert len(
        evidence[
            "raw_candidates"
        ]
    ) == 2


def test_evaluate_pattern_useful_gods_reasoning_and_notes():
    result = evaluate_pattern_useful_gods(
        "甲",
        make_pattern_judgment(),
    )

    assert isinstance(
        result[
            "reasoning"
        ],
        list,
    )

    assert len(
        result[
            "reasoning"
        ]
    ) >= 1

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
    ) >= 4


# =========================================================
# No pattern / unsupported pattern
# =========================================================


def test_evaluate_no_pattern():
    result = evaluate_pattern_useful_gods(
        "甲",
        make_pattern_judgment(
            has_pattern=False
        ),
    )

    assert (
        result[
            "has_pattern_useful_candidate"
        ]
        is False
    )

    assert (
        result[
            "primary_pattern_element"
        ]
        is None
    )

    assert (
        result[
            "secondary_pattern_elements"
        ]
        == []
    )

    assert (
        result[
            "pattern_elements"
        ]
        == []
    )

    assert (
        result[
            "pattern_candidates"
        ]
        == []
    )

    assert (
        result[
            "supported_pattern"
        ]
        is False
    )

    assert (
        result[
            "confidence"
        ]
        == "low"
    )

    assert any(
        "有効な格局がない"
        in note
        for note in result[
            "notes"
        ]
    )


def test_evaluate_unsupported_pattern():
    judgment = make_pattern_judgment(
        primary_pattern="従財格",
        technical_pattern="follow_wealth",
    )

    result = evaluate_pattern_useful_gods(
        "甲",
        judgment,
    )

    assert (
        result[
            "has_pattern_useful_candidate"
        ]
        is False
    )

    assert (
        result[
            "supported_pattern"
        ]
        is False
    )

    assert (
        result[
            "pattern_elements"
        ]
        == []
    )

    assert (
        result[
            "confidence"
        ]
        == "low"
    )

    assert any(
        "未対応の格局"
        in note
        for note in result[
            "notes"
        ]
    )


# =========================================================
# Weighted five-element adjustment
# =========================================================


def test_weighted_adjustment_can_change_priority():
    # 甲日主・正官格:
    # resource=水 base 3.0
    # wealth=土   base 2.0
    #
    # 水が過多でも 2.7。
    # 土が欠けても 2.5。
    # v1では格局ルールの基本優先度を
    # 五行量補正が逆転させすぎない設計。
    weighted = (
        make_weighted_five_elements(
            earth=0.0,
            water=4.0,
        )
    )

    result = evaluate_pattern_useful_gods(
        "甲",
        make_pattern_judgment(
            primary_pattern="正官格",
            technical_pattern=(
                "direct_officer"
            ),
        ),
        weighted,
    )

    assert (
        result[
            "pattern_elements"
        ]
        == [
            "水",
            "土",
        ]
    )

    assert (
        result[
            "pattern_candidates"
        ][0][
            "score"
        ]
        == 2.7
    )

    assert (
        result[
            "pattern_candidates"
        ][1][
            "score"
        ]
        == 2.5
    )


def test_weighted_adjustment_bonus_and_penalty_recorded():
    weighted = (
        make_weighted_five_elements(
            fire=0.0,
            metal=4.0,
        )
    )

    result = evaluate_pattern_useful_gods(
        "甲",
        make_pattern_judgment(
            primary_pattern="偏財格",
            technical_pattern=(
                "indirect_wealth"
            ),
        ),
        weighted,
    )

    fire = result[
        "pattern_candidates"
    ][0]

    metal = result[
        "pattern_candidates"
    ][1]

    assert fire[
        "element"
    ] == "火"

    assert fire[
        "presence_adjustment"
    ] == 0.5

    assert fire[
        "score"
    ] == 3.5

    assert metal[
        "element"
    ] == "金"

    assert metal[
        "presence_adjustment"
    ] == -0.3

    assert metal[
        "score"
    ] == 1.7


# =========================================================
# Confidence through main evaluator
# =========================================================


def test_evaluate_high_confidence():
    result = evaluate_pattern_useful_gods(
        "甲",
        make_pattern_judgment(
            primary_pattern="正官格",
            technical_pattern=(
                "direct_officer"
            ),
            overall_judgment=(
                "provisional_established"
            ),
            confidence="high",
        ),
    )

    assert (
        result[
            "confidence"
        ]
        == "high"
    )


def test_evaluate_medium_confidence():
    result = evaluate_pattern_useful_gods(
        "甲",
        make_pattern_judgment(
            overall_judgment=(
                "provisional_possible"
            ),
            confidence="medium",
        ),
    )

    assert (
        result[
            "confidence"
        ]
        == "medium"
    )


def test_evaluate_school_rule_confidence_low():
    result = evaluate_pattern_useful_gods(
        "甲",
        make_pattern_judgment(
            primary_pattern="羊刃格",
            technical_pattern="yangren",
            overall_judgment=(
                "requires_school_rule"
            ),
            confidence="medium",
        ),
    )

    assert (
        result[
            "confidence"
        ]
        == "low"
    )


# =========================================================
# Invalid main inputs
# =========================================================


def test_evaluate_invalid_day_master_type():
    with pytest.raises(
        TypeError,
        match="day_master_stemはstr型",
    ):
        evaluate_pattern_useful_gods(
            1,
            make_pattern_judgment(),
        )


def test_evaluate_invalid_day_master_value():
    with pytest.raises(
        ValueError,
        match="不正な日干",
    ):
        evaluate_pattern_useful_gods(
            "A",
            make_pattern_judgment(),
        )


def test_evaluate_invalid_pattern_judgment():
    with pytest.raises(
        TypeError,
        match="pattern_judgmentはdict型",
    ):
        evaluate_pattern_useful_gods(
            "甲",
            [],
        )


def test_evaluate_invalid_weighted_five_elements():
    with pytest.raises(
        TypeError,
        match=(
            "weighted_five_elementsは"
            "dict型またはNone"
        ),
    ):
        evaluate_pattern_useful_gods(
            "甲",
            make_pattern_judgment(),
            [],
        )


def test_evaluate_invalid_weighted_scores():
    with pytest.raises(
        TypeError,
        match=(
            r"weighted_five_elements"
            r"\['scores'\]はdict型"
        ),
    ):
        evaluate_pattern_useful_gods(
            "甲",
            make_pattern_judgment(),
            {
                "scores": [],
            },
        )


# =========================================================
# Verified 1985-style case
# 乙丑 / 癸未 / 乙巳 / 丁亥
#
# 現行pattern_judgment_v2の回帰ケース:
# primary_pattern    = 偏財格
# technical_pattern  = indirect_wealth
# overall_judgment   = provisional_possible
# confidence         = medium
#
# 乙日主 = 木
# 偏財格:
# output  = 火
# officer = 金
# =========================================================


def test_verified_1985_style_pattern_useful_gods():
    judgment = make_pattern_judgment(
        primary_pattern="偏財格",
        technical_pattern=(
            "indirect_wealth"
        ),
        overall_judgment=(
            "provisional_possible"
        ),
        confidence="medium",
        primary_judgment={
            "pattern": "偏財格",
            "technical_pattern": (
                "indirect_wealth"
            ),
            "is_exposed": False,
            "exposure_positions": [],
            "final_judgment": (
                "provisional_possible"
            ),
            "confidence": "medium",
        },
    )

    result = evaluate_pattern_useful_gods(
        "乙",
        judgment,
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
            "pattern_overall_judgment"
        ]
        == "provisional_possible"
    )

    assert (
        result[
            "pattern_confidence"
        ]
        == "medium"
    )

    assert (
        result[
            "pattern_elements"
        ]
        == [
            "火",
            "金",
        ]
    )

    assert (
        result[
            "primary_pattern_element"
        ]
        == "火"
    )

    assert (
        result[
            "secondary_pattern_elements"
        ]
        == [
            "金",
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
            "method"
        ]
        == "pattern_useful_gods_v1"
    )

    assert (
        result[
            "status"
        ]
        == "provisional_pattern_useful_gods"
    )


def test_verified_1985_style_candidate_roles():
    judgment = make_pattern_judgment(
        primary_pattern="偏財格",
        technical_pattern=(
            "indirect_wealth"
        ),
    )

    result = evaluate_pattern_useful_gods(
        "乙",
        judgment,
    )

    candidates = result[
        "pattern_candidates"
    ]

    assert len(
        candidates
    ) == 2

    assert candidates[0][
        "element"
    ] == "火"

    assert candidates[0][
        "relations"
    ] == [
        "output",
    ]

    assert candidates[0][
        "roles"
    ] == [
        "generate_wealth",
    ]

    assert candidates[0][
        "priority"
    ] == 1

    assert candidates[1][
        "element"
    ] == "金"

    assert candidates[1][
        "relations"
    ] == [
        "officer",
    ]

    assert candidates[1][
        "roles"
    ] == [
        "protect_wealth",
    ]

    assert candidates[1][
        "priority"
    ] == 2


def test_verified_1985_style_evidence_preserved():
    judgment = make_pattern_judgment(
        primary_pattern="偏財格",
        technical_pattern=(
            "indirect_wealth"
        ),
    )

    weighted = (
        make_weighted_five_elements(
            wood=2.0,
            fire=1.5,
            earth=2.5,
            metal=0.5,
            water=2.0,
        )
    )

    result = evaluate_pattern_useful_gods(
        "乙",
        judgment,
        weighted,
    )

    assert (
        result[
            "evidence"
        ][
            "pattern_judgment"
        ]
        == judgment
    )

    assert (
        result[
            "evidence"
        ][
            "weighted_five_elements"
        ]
        == weighted
    )

    assert (
        result[
            "evidence"
        ][
            "pattern_info"
        ][
            "technical_pattern"
        ]
        == "indirect_wealth"
    )

    assert (
        len(
            result[
                "evidence"
            ][
                "raw_candidates"
            ]
        )
        == 2
    )
