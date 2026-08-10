"""
tests/test_integrated_luck.py

engine.integrated_luck の単体テスト。

対象:
    integrated_luck_v1

主な検証内容
------------
1. current_luck の取得
2. current_luck の五行取得
3. annual_luck の五行取得
4. 五行関係
5. 用神スコア
6. 現在大運の用神評価
7. 歳運の用神評価
8. 用神一致判定
9. 統合スコア
10. 統合レベル
11. confidence
12. reasoning
13. evidence
14. alias
15. 入力非破壊
16. 不正入力
"""

from copy import deepcopy

import pytest

from engine.integrated_luck import (
    FIVE_ELEMENTS,
    INTEGRATED_LUCK_METHOD,
    INTEGRATED_LUCK_STATUS,
    RELATION_SCORE,
    USEFUL_RELATION_SCORE,
    build_element_interactions,
    build_integrated_luck,
    build_integrated_luck_reasoning,
    calculate_integrated_confidence,
    calculate_integrated_luck,
    calculate_integrated_score,
    classify_integrated_level,
    evaluate_annual_luck_useful_gods,
    evaluate_current_luck_useful_gods,
    evaluate_element_interaction,
    evaluate_integrated_luck,
    evaluate_useful_gods_agreement,
    get_annual_luck_elements,
    get_current_luck_elements,
    get_current_luck_ganzhi,
    get_current_luck_pillar,
    score_useful_relation,
)


# =========================================================
# Fixtures
# =========================================================


@pytest.fixture
def useful_gods_fixture():
    """
    useful_gods_v3 を模したfixture。

    primary:
        火

    secondary:
        木

    unfavorable:
        金・水

    neutral:
        土
    """

    return {
        "primary_useful_element": "火",
        "final_useful_elements": [
            "火",
            "木",
        ],
        "support_balance": {
            "unfavorable_elements": [
                "金",
                "水",
            ],
            "neutral_elements": [
                "土",
            ],
        },
        "method": "useful_gods_v3",
    }


@pytest.fixture
def current_luck_fixture():
    """
    現在大運:
        甲申

    甲:
        木

    申:
        金
    """

    return {
        "has_current_luck": True,
        "phase": "in_luck_pillar",
        "current_luck_pillar": {
            "index": 1,
            "ganzhi": "甲申",
            "stem": "甲",
            "branch": "申",
            "stem_element": "木",
            "branch_element": "金",
            "start_age": 7.0,
            "end_age": 17.0,
        },
        "method": "current_luck_v1",
        "status": "current_luck_resolved",
    }


@pytest.fixture
def current_luck_minimal_fixture():
    """
    五行情報を含めない current_luck。

    stem / branch から補完できることを
    検証する。
    """

    return {
        "has_current_luck": True,
        "current_luck_pillar": {
            "index": 1,
            "ganzhi": "甲申",
            "stem": "甲",
            "branch": "申",
        },
        "method": "current_luck_v1",
    }


@pytest.fixture
def no_current_luck_fixture():
    return {
        "has_current_luck": False,
        "phase": "before_first_luck",
        "current_luck_pillar": None,
        "method": "current_luck_v1",
    }


@pytest.fixture
def annual_luck_fixture():
    """
    2026:
        丙午

    丙:
        火

    午:
        火

    乙日主:
        丙 = 傷官
        午 = 長生
    """

    return {
        "year": 2026,
        "ganzhi": "丙午",
        "stem": "丙",
        "branch": "午",
        "stem_element": "火",
        "stem_yin_yang": "陽",
        "branch_element": "火",
        "day_master_stem": "乙",
        "day_master_element": "木",
        "stem_ten_god": "傷官",
        "twelve_stage": "長生",
        "stem_useful_relation": {
            "is_useful": True,
            "is_primary_useful": True,
            "is_unfavorable": False,
            "priority": 1,
            "relationship": (
                "primary_useful"
            ),
        },
        "branch_useful_relation": {
            "is_useful": True,
            "is_primary_useful": True,
            "is_unfavorable": False,
            "priority": 1,
            "relationship": (
                "primary_useful"
            ),
        },
        "method": "annual_luck_v1",
        "status": (
            "provisional_annual_luck_v1"
        ),
    }


@pytest.fixture
def annual_luck_minimal_fixture():
    """
    五行情報を含めない歳運。
    """

    return {
        "year": 2026,
        "ganzhi": "丙午",
        "stem": "丙",
        "branch": "午",
        "stem_ten_god": "傷官",
        "twelve_stage": "長生",
        "method": "annual_luck_v1",
    }


# =========================================================
# Constants
# =========================================================


def test_integrated_luck_method_constant():
    assert (
        INTEGRATED_LUCK_METHOD
        == "integrated_luck_v1"
    )


def test_integrated_luck_status_constant():
    assert (
        INTEGRATED_LUCK_STATUS
        == (
            "provisional_integrated_luck_v1"
        )
    )


def test_integrated_luck_five_elements():
    assert FIVE_ELEMENTS == {
        "木",
        "火",
        "土",
        "金",
        "水",
    }


def test_relation_score_keys():
    assert {
        "same",
        "generates",
        "generated_by",
        "controls",
        "controlled_by",
        "unknown",
    }.issubset(
        RELATION_SCORE.keys()
    )


def test_useful_relation_score_keys():
    assert {
        "primary_useful",
        "secondary_useful",
        "neutral",
        "support_unfavorable",
        "unknown",
    }.issubset(
        USEFUL_RELATION_SCORE.keys()
    )


# =========================================================
# Current luck pillar
# =========================================================


def test_get_current_luck_pillar(
    current_luck_fixture,
):
    pillar = get_current_luck_pillar(
        current_luck_fixture
    )

    assert isinstance(
        pillar,
        dict,
    )

    assert (
        pillar[
            "ganzhi"
        ]
        == "甲申"
    )


def test_get_current_luck_pillar_none(
    no_current_luck_fixture,
):
    assert (
        get_current_luck_pillar(
            no_current_luck_fixture
        )
        is None
    )


def test_get_current_luck_pillar_invalid_type():
    with pytest.raises(
        TypeError
    ):
        get_current_luck_pillar(
            []
        )


# =========================================================
# Current luck ganzhi
# =========================================================


def test_get_current_luck_ganzhi(
    current_luck_fixture,
):
    assert (
        get_current_luck_ganzhi(
            current_luck_fixture
        )
        == "甲申"
    )


def test_get_current_luck_ganzhi_none(
    no_current_luck_fixture,
):
    assert (
        get_current_luck_ganzhi(
            no_current_luck_fixture
        )
        is None
    )


def test_get_current_luck_ganzhi_compatibility_pillar():
    current_luck = {
        "has_current_luck": True,
        "current_luck_pillar": {
            "pillar": "甲申",
        },
    }

    assert (
        get_current_luck_ganzhi(
            current_luck
        )
        == "甲申"
    )


# =========================================================
# Current luck elements
# =========================================================


def test_get_current_luck_elements(
    current_luck_fixture,
):
    result = (
        get_current_luck_elements(
            current_luck_fixture
        )
    )

    assert result == {
        "stem": "木",
        "branch": "金",
    }


def test_current_luck_elements_are_inferred(
    current_luck_minimal_fixture,
):
    result = (
        get_current_luck_elements(
            current_luck_minimal_fixture
        )
    )

    assert result[
        "stem"
    ] == "木"

    assert result[
        "branch"
    ] == "金"


def test_current_luck_elements_none(
    no_current_luck_fixture,
):
    result = (
        get_current_luck_elements(
            no_current_luck_fixture
        )
    )

    assert result == {
        "stem": None,
        "branch": None,
    }


# =========================================================
# Annual luck elements
# =========================================================


def test_get_annual_luck_elements(
    annual_luck_fixture,
):
    result = (
        get_annual_luck_elements(
            annual_luck_fixture
        )
    )

    assert result == {
        "stem": "火",
        "branch": "火",
    }


def test_annual_luck_elements_are_inferred(
    annual_luck_minimal_fixture,
):
    result = (
        get_annual_luck_elements(
            annual_luck_minimal_fixture
        )
    )

    assert result[
        "stem"
    ] == "火"

    assert result[
        "branch"
    ] == "火"


def test_get_annual_luck_elements_invalid_type():
    with pytest.raises(
        TypeError
    ):
        get_annual_luck_elements(
            []
        )


# =========================================================
# Element interaction
# =========================================================


@pytest.mark.parametrize(
    (
        "source",
        "target",
        "relationship",
        "score",
    ),
    [
        (
            "木",
            "木",
            "same",
            1.0,
        ),
        (
            "木",
            "火",
            "generates",
            2.0,
        ),
        (
            "火",
            "木",
            "generated_by",
            1.0,
        ),
        (
            "木",
            "土",
            "controls",
            -1.0,
        ),
        (
            "土",
            "木",
            "controlled_by",
            -2.0,
        ),
    ],
)
def test_evaluate_element_interaction(
    source,
    target,
    relationship,
    score,
):
    result = (
        evaluate_element_interaction(
            source,
            target,
        )
    )

    assert result[
        "source_element"
    ] == source

    assert result[
        "target_element"
    ] == target

    assert result[
        "relationship"
    ] == relationship

    assert result[
        "score"
    ] == score


def test_evaluate_element_interaction_unknown_source():
    result = (
        evaluate_element_interaction(
            None,
            "火",
        )
    )

    assert result[
        "relationship"
    ] == "unknown"

    assert result[
        "score"
    ] == 0.0


def test_evaluate_element_interaction_unknown_target():
    result = (
        evaluate_element_interaction(
            "木",
            None,
        )
    )

    assert result[
        "relationship"
    ] == "unknown"

    assert result[
        "score"
    ] == 0.0


def test_evaluate_element_interaction_invalid_element():
    result = (
        evaluate_element_interaction(
            "風",
            "火",
        )
    )

    assert result[
        "relationship"
    ] == "unknown"

    assert result[
        "score"
    ] == 0.0


# =========================================================
# Element interactions
# =========================================================


def test_build_element_interactions(
    current_luck_fixture,
    annual_luck_fixture,
):
    result = (
        build_element_interactions(
            current_luck_fixture,
            annual_luck_fixture,
        )
    )

    assert result[
        "current_luck_elements"
    ] == {
        "stem": "木",
        "branch": "金",
    }

    assert result[
        "annual_luck_elements"
    ] == {
        "stem": "火",
        "branch": "火",
    }

    # 木 -> 火
    assert result[
        "stem_relation"
    ][
        "relationship"
    ] == "generates"

    # 金 -> 火
    # 火剋金なので、
    # source=金,target=火 は controlled_by
    assert result[
        "branch_relation"
    ][
        "relationship"
    ] == "controlled_by"

    assert result[
        "score"
    ] == 0.0


# =========================================================
# Useful relation score
# =========================================================


@pytest.mark.parametrize(
    (
        "relationship",
        "expected",
    ),
    [
        (
            "primary_useful",
            3.0,
        ),
        (
            "secondary_useful",
            2.0,
        ),
        (
            "neutral",
            0.0,
        ),
        (
            "support_unfavorable",
            -2.0,
        ),
        (
            "unknown",
            0.0,
        ),
    ],
)
def test_score_useful_relation(
    relationship,
    expected,
):
    result = (
        score_useful_relation(
            {
                "relationship": (
                    relationship
                )
            }
        )
    )

    assert result == expected


def test_score_useful_relation_none():
    assert (
        score_useful_relation(
            None
        )
        == 0.0
    )


# =========================================================
# Current luck useful gods
# =========================================================


def test_evaluate_current_luck_useful_gods(
    current_luck_fixture,
    useful_gods_fixture,
):
    result = (
        evaluate_current_luck_useful_gods(
            current_luck_fixture,
            useful_gods_fixture,
        )
    )

    # 甲 = 木 = secondary
    assert result[
        "stem_relation"
    ][
        "relationship"
    ] == "secondary_useful"

    # 申 = 金 = unfavorable
    assert result[
        "branch_relation"
    ][
        "relationship"
    ] == "support_unfavorable"

    assert result[
        "stem_score"
    ] == 2.0

    assert result[
        "branch_score"
    ] == -2.0

    assert result[
        "score"
    ] == 0.0


def test_evaluate_current_luck_without_useful_gods(
    current_luck_fixture,
):
    result = (
        evaluate_current_luck_useful_gods(
            current_luck_fixture,
            None,
        )
    )

    assert result[
        "stem_relation"
    ][
        "relationship"
    ] == "unknown"

    assert result[
        "branch_relation"
    ][
        "relationship"
    ] == "unknown"

    assert result[
        "score"
    ] == 0.0


def test_evaluate_current_luck_no_active_luck(
    no_current_luck_fixture,
    useful_gods_fixture,
):
    result = (
        evaluate_current_luck_useful_gods(
            no_current_luck_fixture,
            useful_gods_fixture,
        )
    )

    assert result[
        "stem_element"
    ] is None

    assert result[
        "branch_element"
    ] is None

    assert result[
        "score"
    ] == 0.0


# =========================================================
# Annual useful gods
# =========================================================


def test_evaluate_annual_luck_useful_gods(
    annual_luck_fixture,
    useful_gods_fixture,
):
    result = (
        evaluate_annual_luck_useful_gods(
            annual_luck_fixture,
            useful_gods_fixture,
        )
    )

    assert result[
        "stem_relation"
    ][
        "relationship"
    ] == "primary_useful"

    assert result[
        "branch_relation"
    ][
        "relationship"
    ] == "primary_useful"

    assert result[
        "stem_score"
    ] == 3.0

    assert result[
        "branch_score"
    ] == 3.0

    assert result[
        "score"
    ] == 6.0


def test_annual_useful_gods_is_recalculated_if_missing(
    annual_luck_minimal_fixture,
    useful_gods_fixture,
):
    result = (
        evaluate_annual_luck_useful_gods(
            annual_luck_minimal_fixture,
            useful_gods_fixture,
        )
    )

    assert result[
        "stem_relation"
    ][
        "relationship"
    ] == "primary_useful"

    assert result[
        "branch_relation"
    ][
        "relationship"
    ] == "primary_useful"

    assert result[
        "score"
    ] == 6.0


# =========================================================
# Useful gods agreement
# =========================================================


def test_useful_gods_agreement_mixed():
    current = {
        "stem_relation": {
            "relationship": (
                "secondary_useful"
            )
        },
        "branch_relation": {
            "relationship": (
                "support_unfavorable"
            )
        },
    }

    annual = {
        "stem_relation": {
            "relationship": (
                "primary_useful"
            )
        },
        "branch_relation": {
            "relationship": (
                "primary_useful"
            )
        },
    }

    result = (
        evaluate_useful_gods_agreement(
            current,
            annual,
        )
    )

    assert result[
        "useful_count"
    ] == 3

    assert result[
        "unfavorable_count"
    ] == 1

    assert result[
        "has_useful_alignment"
    ] is True

    assert result[
        "has_unfavorable_alignment"
    ] is True

    assert result[
        "has_mixed_signal"
    ] is True

    assert result[
        "agreement_level"
    ] == "mixed"


def test_useful_gods_agreement_strong_useful():
    current = {
        "stem_relation": {
            "relationship": (
                "primary_useful"
            )
        },
        "branch_relation": {
            "relationship": (
                "secondary_useful"
            )
        },
    }

    annual = {
        "stem_relation": {
            "relationship": (
                "primary_useful"
            )
        },
        "branch_relation": {
            "relationship": (
                "secondary_useful"
            )
        },
    }

    result = (
        evaluate_useful_gods_agreement(
            current,
            annual,
        )
    )

    assert (
        result[
            "agreement_level"
        ]
        == "strong_useful_alignment"
    )

    assert result[
        "useful_count"
    ] == 4

    assert result[
        "unfavorable_count"
    ] == 0


def test_useful_gods_agreement_strong_unfavorable():
    current = {
        "stem_relation": {
            "relationship": (
                "support_unfavorable"
            )
        },
        "branch_relation": {
            "relationship": (
                "support_unfavorable"
            )
        },
    }

    annual = {
        "stem_relation": {
            "relationship": (
                "support_unfavorable"
            )
        },
        "branch_relation": {
            "relationship": (
                "support_unfavorable"
            )
        },
    }

    result = (
        evaluate_useful_gods_agreement(
            current,
            annual,
        )
    )

    assert (
        result[
            "agreement_level"
        ]
        == "strong_unfavorable_alignment"
    )


def test_useful_gods_agreement_unknown():
    unknown = {
        "stem_relation": {
            "relationship": "unknown"
        },
        "branch_relation": {
            "relationship": "unknown"
        },
    }

    result = (
        evaluate_useful_gods_agreement(
            unknown,
            unknown,
        )
    )

    assert (
        result[
            "agreement_level"
        ]
        == "unknown"
    )

    assert result[
        "known_count"
    ] == 0


# =========================================================
# Integrated score
# =========================================================


def test_calculate_integrated_score():
    result = (
        calculate_integrated_score(
            element_interactions={
                "score": 1.0,
            },
            current_useful={
                "score": 2.0,
            },
            annual_useful={
                "score": 6.0,
            },
        )
    )

    assert result[
        "element_interaction_score"
    ] == 1.0

    assert result[
        "current_luck_useful_score"
    ] == 2.0

    assert result[
        "annual_luck_useful_score"
    ] == 6.0

    assert result[
        "total_score"
    ] == 9.0


# =========================================================
# Integrated level
# =========================================================


@pytest.mark.parametrize(
    (
        "score",
        "expected",
    ),
    [
        (
            10.0,
            "very_supportive",
        ),
        (
            8.0,
            "very_supportive",
        ),
        (
            7.9,
            "supportive",
        ),
        (
            4.0,
            "supportive",
        ),
        (
            3.9,
            "mixed",
        ),
        (
            0.0,
            "mixed",
        ),
        (
            -3.9,
            "mixed",
        ),
        (
            -4.0,
            "challenging",
        ),
        (
            -7.9,
            "challenging",
        ),
        (
            -8.0,
            "very_challenging",
        ),
        (
            -10.0,
            "very_challenging",
        ),
    ],
)
def test_classify_integrated_level(
    score,
    expected,
):
    assert (
        classify_integrated_level(
            score
        )
        == expected
    )


# =========================================================
# Confidence
# =========================================================


def test_integrated_confidence_high(
    current_luck_fixture,
    annual_luck_fixture,
    useful_gods_fixture,
):
    result = (
        calculate_integrated_confidence(
            current_luck=(
                current_luck_fixture
            ),
            annual_luck=(
                annual_luck_fixture
            ),
            useful_gods=(
                useful_gods_fixture
            ),
        )
    )

    assert result[
        "available_sources"
    ] == 3

    assert result[
        "total_sources"
    ] == 3

    assert result[
        "ratio"
    ] == 1.0

    assert result[
        "level"
    ] == "high"


def test_integrated_confidence_medium(
    current_luck_fixture,
    annual_luck_fixture,
):
    result = (
        calculate_integrated_confidence(
            current_luck=(
                current_luck_fixture
            ),
            annual_luck=(
                annual_luck_fixture
            ),
            useful_gods=None,
        )
    )

    assert result[
        "available_sources"
    ] == 2

    assert (
        result[
            "level"
        ]
        == "medium"
    )


def test_integrated_confidence_low(
    no_current_luck_fixture,
):
    result = (
        calculate_integrated_confidence(
            current_luck=(
                no_current_luck_fixture
            ),
            annual_luck={},
            useful_gods=None,
        )
    )

    assert result[
        "available_sources"
    ] == 0

    assert result[
        "level"
    ] == "low"


# =========================================================
# Reasoning
# =========================================================


def test_build_integrated_luck_reasoning():
    reasoning = (
        build_integrated_luck_reasoning(
            current_luck_ganzhi="甲申",
            annual_luck_ganzhi="丙午",
            element_interactions={
                "stem_relation": {
                    "relationship": (
                        "generates"
                    ),
                },
                "branch_relation": {
                    "relationship": (
                        "controlled_by"
                    ),
                },
            },
            agreement={
                "agreement_level": "mixed",
            },
            score_data={
                "total_score": 6.0,
            },
            overall_level="supportive",
            annual_ten_god="傷官",
            annual_twelve_stage="長生",
        )
    )

    assert isinstance(
        reasoning,
        list,
    )

    assert (
        len(
            reasoning
        )
        >= 7
    )

    joined = "".join(
        reasoning
    )

    assert "甲申" in joined
    assert "丙午" in joined
    assert "generates" in joined
    assert "controlled_by" in joined
    assert "傷官" in joined
    assert "長生" in joined
    assert "supportive" in joined


# =========================================================
# Main integrated luck
# =========================================================


def test_calculate_integrated_luck(
    current_luck_fixture,
    annual_luck_fixture,
    useful_gods_fixture,
):
    result = (
        calculate_integrated_luck(
            current_luck=(
                current_luck_fixture
            ),
            annual_luck=(
                annual_luck_fixture
            ),
            useful_gods=(
                useful_gods_fixture
            ),
        )
    )

    assert (
        result[
            "current_luck_ganzhi"
        ]
        == "甲申"
    )

    assert (
        result[
            "annual_luck_ganzhi"
        ]
        == "丙午"
    )


def test_integrated_luck_required_keys(
    current_luck_fixture,
    annual_luck_fixture,
    useful_gods_fixture,
):
    result = (
        calculate_integrated_luck(
            current_luck=(
                current_luck_fixture
            ),
            annual_luck=(
                annual_luck_fixture
            ),
            useful_gods=(
                useful_gods_fixture
            ),
        )
    )

    required_keys = {
        "current_luck_ganzhi",
        "annual_luck_ganzhi",
        "current_luck_elements",
        "annual_luck_elements",
        "element_interactions",
        "current_luck_useful",
        "annual_luck_useful",
        "useful_gods_agreement",
        "annual_ten_god",
        "annual_twelve_stage",
        "score",
        "overall_score",
        "overall_level",
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


def test_integrated_luck_metadata(
    current_luck_fixture,
    annual_luck_fixture,
    useful_gods_fixture,
):
    result = (
        calculate_integrated_luck(
            current_luck=(
                current_luck_fixture
            ),
            annual_luck=(
                annual_luck_fixture
            ),
            useful_gods=(
                useful_gods_fixture
            ),
        )
    )

    assert (
        result[
            "method"
        ]
        == "integrated_luck_v1"
    )

    assert (
        result[
            "status"
        ]
        == (
            "provisional_integrated_luck_v1"
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
# Verified score
# =========================================================


def test_integrated_luck_verified_score(
    current_luck_fixture,
    annual_luck_fixture,
    useful_gods_fixture,
):
    """
    fixture条件:

    大運:
        甲申
        木 / 金

    歳運:
        丙午
        火 / 火

    五行:
        木 -> 火
            generates = +2

        金 -> 火
            controlled_by = -2

        interaction total = 0

    大運 useful:
        木 = secondary = +2
        金 = unfavorable = -2

        current total = 0

    歳運 useful:
        火 = primary = +3
        火 = primary = +3

        annual total = +6

    総合:
        0 + 0 + 6 = 6
    """

    result = (
        calculate_integrated_luck(
            current_luck=(
                current_luck_fixture
            ),
            annual_luck=(
                annual_luck_fixture
            ),
            useful_gods=(
                useful_gods_fixture
            ),
        )
    )

    assert (
        result[
            "element_interactions"
        ][
            "score"
        ]
        == 0.0
    )

    assert (
        result[
            "current_luck_useful"
        ][
            "score"
        ]
        == 0.0
    )

    assert (
        result[
            "annual_luck_useful"
        ][
            "score"
        ]
        == 6.0
    )

    assert (
        result[
            "overall_score"
        ]
        == 6.0
    )

    assert (
        result[
            "overall_level"
        ]
        == "supportive"
    )


def test_integrated_luck_verified_agreement(
    current_luck_fixture,
    annual_luck_fixture,
    useful_gods_fixture,
):
    result = (
        calculate_integrated_luck(
            current_luck=(
                current_luck_fixture
            ),
            annual_luck=(
                annual_luck_fixture
            ),
            useful_gods=(
                useful_gods_fixture
            ),
        )
    )

    agreement = result[
        "useful_gods_agreement"
    ]

    assert (
        agreement[
            "useful_count"
        ]
        == 3
    )

    assert (
        agreement[
            "unfavorable_count"
        ]
        == 1
    )

    assert (
        agreement[
            "agreement_level"
        ]
        == "mixed"
    )


def test_integrated_luck_annual_ten_god(
    current_luck_fixture,
    annual_luck_fixture,
    useful_gods_fixture,
):
    result = (
        calculate_integrated_luck(
            current_luck=(
                current_luck_fixture
            ),
            annual_luck=(
                annual_luck_fixture
            ),
            useful_gods=(
                useful_gods_fixture
            ),
        )
    )

    assert (
        result[
            "annual_ten_god"
        ]
        == "傷官"
    )


def test_integrated_luck_annual_twelve_stage(
    current_luck_fixture,
    annual_luck_fixture,
    useful_gods_fixture,
):
    result = (
        calculate_integrated_luck(
            current_luck=(
                current_luck_fixture
            ),
            annual_luck=(
                annual_luck_fixture
            ),
            useful_gods=(
                useful_gods_fixture
            ),
        )
    )

    assert (
        result[
            "annual_twelve_stage"
        ]
        == "長生"
    )


# =========================================================
# Evidence
# =========================================================


def test_integrated_luck_evidence(
    current_luck_fixture,
    annual_luck_fixture,
    useful_gods_fixture,
):
    result = (
        calculate_integrated_luck(
            current_luck=(
                current_luck_fixture
            ),
            annual_luck=(
                annual_luck_fixture
            ),
            useful_gods=(
                useful_gods_fixture
            ),
        )
    )

    evidence = result[
        "evidence"
    ]

    assert (
        evidence[
            "current_luck_ganzhi"
        ]
        == result[
            "current_luck_ganzhi"
        ]
    )

    assert (
        evidence[
            "annual_luck_ganzhi"
        ]
        == result[
            "annual_luck_ganzhi"
        ]
    )

    assert (
        evidence[
            "annual_ten_god"
        ]
        == result[
            "annual_ten_god"
        ]
    )

    assert (
        evidence[
            "annual_twelve_stage"
        ]
        == result[
            "annual_twelve_stage"
        ]
    )

    assert (
        evidence[
            "score"
        ]
        == result[
            "score"
        ]
    )


# =========================================================
# Reasoning in main result
# =========================================================


def test_integrated_luck_reasoning_exists(
    current_luck_fixture,
    annual_luck_fixture,
    useful_gods_fixture,
):
    result = (
        calculate_integrated_luck(
            current_luck=(
                current_luck_fixture
            ),
            annual_luck=(
                annual_luck_fixture
            ),
            useful_gods=(
                useful_gods_fixture
            ),
        )
    )

    reasoning = result[
        "reasoning"
    ]

    assert isinstance(
        reasoning,
        list,
    )

    assert (
        len(
            reasoning
        )
        >= 1
    )

    joined = "".join(
        reasoning
    )

    assert "甲申" in joined
    assert "丙午" in joined
    assert "傷官" in joined
    assert "長生" in joined


# =========================================================
# Without useful gods
# =========================================================


def test_integrated_luck_without_useful_gods(
    current_luck_fixture,
    annual_luck_minimal_fixture,
):
    result = (
        calculate_integrated_luck(
            current_luck=(
                current_luck_fixture
            ),
            annual_luck=(
                annual_luck_minimal_fixture
            ),
            useful_gods=None,
        )
    )

    assert (
        result[
            "current_luck_ganzhi"
        ]
        == "甲申"
    )

    assert (
        result[
            "annual_luck_ganzhi"
        ]
        == "丙午"
    )

    assert (
        result[
            "current_luck_useful"
        ][
            "score"
        ]
        == 0.0
    )

    assert (
        result[
            "annual_luck_useful"
        ][
            "score"
        ]
        == 0.0
    )

    assert (
        result[
            "confidence"
        ][
            "level"
        ]
        == "medium"
    )


# =========================================================
# Without current luck
# =========================================================


def test_integrated_luck_without_current_luck(
    no_current_luck_fixture,
    annual_luck_fixture,
    useful_gods_fixture,
):
    result = (
        calculate_integrated_luck(
            current_luck=(
                no_current_luck_fixture
            ),
            annual_luck=(
                annual_luck_fixture
            ),
            useful_gods=(
                useful_gods_fixture
            ),
        )
    )

    assert (
        result[
            "current_luck_ganzhi"
        ]
        is None
    )

    assert result[
        "current_luck_elements"
    ] == {
        "stem": None,
        "branch": None,
    }

    assert (
        result[
            "element_interactions"
        ][
            "stem_relation"
        ][
            "relationship"
        ]
        == "unknown"
    )

    assert (
        result[
            "element_interactions"
        ][
            "branch_relation"
        ][
            "relationship"
        ]
        == "unknown"
    )


# =========================================================
# Minimal input compatibility
# =========================================================


def test_minimal_inputs_supported(
    current_luck_minimal_fixture,
    annual_luck_minimal_fixture,
    useful_gods_fixture,
):
    result = (
        calculate_integrated_luck(
            current_luck=(
                current_luck_minimal_fixture
            ),
            annual_luck=(
                annual_luck_minimal_fixture
            ),
            useful_gods=(
                useful_gods_fixture
            ),
        )
    )

    assert (
        result[
            "current_luck_elements"
        ][
            "stem"
        ]
        == "木"
    )

    assert (
        result[
            "current_luck_elements"
        ][
            "branch"
        ]
        == "金"
    )

    assert (
        result[
            "annual_luck_elements"
        ][
            "stem"
        ]
        == "火"
    )

    assert (
        result[
            "annual_luck_elements"
        ][
            "branch"
        ]
        == "火"
    )


# =========================================================
# Alias
# =========================================================


def test_evaluate_integrated_luck_alias(
    current_luck_fixture,
    annual_luck_fixture,
    useful_gods_fixture,
):
    direct = (
        calculate_integrated_luck(
            current_luck=(
                current_luck_fixture
            ),
            annual_luck=(
                annual_luck_fixture
            ),
            useful_gods=(
                useful_gods_fixture
            ),
        )
    )

    alias = (
        evaluate_integrated_luck(
            current_luck=(
                current_luck_fixture
            ),
            annual_luck=(
                annual_luck_fixture
            ),
            useful_gods=(
                useful_gods_fixture
            ),
        )
    )

    assert alias == direct


def test_build_integrated_luck_direct(
    current_luck_fixture,
    annual_luck_fixture,
    useful_gods_fixture,
):
    result = (
        build_integrated_luck(
            current_luck=(
                current_luck_fixture
            ),
            annual_luck=(
                annual_luck_fixture
            ),
            useful_gods=(
                useful_gods_fixture
            ),
        )
    )

    assert (
        result[
            "method"
        ]
        == "integrated_luck_v1"
    )


# =========================================================
# Input immutability
# =========================================================


def test_current_luck_input_not_mutated(
    current_luck_fixture,
    annual_luck_fixture,
    useful_gods_fixture,
):
    original = deepcopy(
        current_luck_fixture
    )

    calculate_integrated_luck(
        current_luck=(
            current_luck_fixture
        ),
        annual_luck=(
            annual_luck_fixture
        ),
        useful_gods=(
            useful_gods_fixture
        ),
    )

    assert (
        current_luck_fixture
        == original
    )


def test_annual_luck_input_not_mutated(
    current_luck_fixture,
    annual_luck_fixture,
    useful_gods_fixture,
):
    original = deepcopy(
        annual_luck_fixture
    )

    calculate_integrated_luck(
        current_luck=(
            current_luck_fixture
        ),
        annual_luck=(
            annual_luck_fixture
        ),
        useful_gods=(
            useful_gods_fixture
        ),
    )

    assert (
        annual_luck_fixture
        == original
    )


def test_useful_gods_input_not_mutated(
    current_luck_fixture,
    annual_luck_fixture,
    useful_gods_fixture,
):
    original = deepcopy(
        useful_gods_fixture
    )

    calculate_integrated_luck(
        current_luck=(
            current_luck_fixture
        ),
        annual_luck=(
            annual_luck_fixture
        ),
        useful_gods=(
            useful_gods_fixture
        ),
    )

    assert (
        useful_gods_fixture
        == original
    )


# =========================================================
# Invalid input
# =========================================================


def test_invalid_current_luck_type(
    annual_luck_fixture,
):
    with pytest.raises(
        TypeError
    ):
        calculate_integrated_luck(
            current_luck=[],
            annual_luck=(
                annual_luck_fixture
            ),
        )


def test_invalid_annual_luck_type(
    current_luck_fixture,
):
    with pytest.raises(
        TypeError
    ):
        calculate_integrated_luck(
            current_luck=(
                current_luck_fixture
            ),
            annual_luck=[],
        )


def test_invalid_useful_gods_type(
    current_luck_fixture,
    annual_luck_fixture,
):
    with pytest.raises(
        TypeError
    ):
        calculate_integrated_luck(
            current_luck=(
                current_luck_fixture
            ),
            annual_luck=(
                annual_luck_fixture
            ),
            useful_gods=[],
        )


# =========================================================
# Regression
# =========================================================


def test_verified_style_2026_integrated_luck(
    current_luck_fixture,
    annual_luck_fixture,
    useful_gods_fixture,
):
    """
    統合評価代表ケース。

    大運:
        甲申

    歳運:
        丙午

    日主:
        乙

    歳運:
        傷官
        長生

    useful fixture:
        火 = primary
        木 = secondary
        金・水 = unfavorable

    期待:
        score = 6
        supportive
        mixed
    """

    result = (
        calculate_integrated_luck(
            current_luck=(
                current_luck_fixture
            ),
            annual_luck=(
                annual_luck_fixture
            ),
            useful_gods=(
                useful_gods_fixture
            ),
        )
    )

    assert (
        result[
            "current_luck_ganzhi"
        ]
        == "甲申"
    )

    assert (
        result[
            "annual_luck_ganzhi"
        ]
        == "丙午"
    )

    assert (
        result[
            "annual_ten_god"
        ]
        == "傷官"
    )

    assert (
        result[
            "annual_twelve_stage"
        ]
        == "長生"
    )

    assert (
        result[
            "overall_score"
        ]
        == 6.0
    )

    assert (
        result[
            "overall_level"
        ]
        == "supportive"
    )

    assert (
        result[
            "useful_gods_agreement"
        ][
            "agreement_level"
        ]
        == "mixed"
    )

    assert (
        result[
            "confidence"
        ][
            "level"
        ]
        == "high"
    )

    assert (
        result[
            "method"
        ]
        == "integrated_luck_v1"
    )
