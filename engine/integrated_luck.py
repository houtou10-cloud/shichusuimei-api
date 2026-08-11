"""
tests/test_final_integrated_luck.py

integrated_luck_v1 最終回帰テスト。

検証対象:
- 定数 / メタデータ
- 現在大運ヘルパー
- 歳運ヘルパー
- 五行相互作用
- 用神関係スコア
- 現在大運 × 用神
- 歳運 × 用神
- 大運・歳運の用神一致
- 統合スコア
- 統合レベル
- confidence
- reasoning
- build_integrated_luck
- calculate_integrated_luck
- evaluate_integrated_luck
- 入力不変性
- 不正入力
- 現在大運が存在しないケース

重要:
integrated_luck_v1 は
「五行・用神を中心とした統合評価」。

干合・支合・三合・方合・冲・刑・害・破は
このv1の最終スコアには含めない。
"""

from copy import deepcopy

import pytest




# ============================================================
# Helpers
# ============================================================


def make_useful_gods():
    """
    テスト用 useful_gods_v3。

    primary:
        火

    secondary:
        土
        金

    unfavorable:
        水
        木
    """

    return {
        "primary_useful_element": "火",
        "final_useful_elements": [
            "火",
            "土",
            "金",
        ],
        "support_balance": {
            "unfavorable_elements": [
                "水",
                "木",
            ],
        },
        "method": "useful_gods_v3",
        "status": (
            "provisional_useful_gods_v3"
        ),
    }


def make_current_luck(
    *,
    stem="丙",
    branch="午",
    stem_element="火",
    branch_element="火",
    ganzhi="丙午",
    has_current=True,
):
    """
    current_luck_v1 相当の最小構造。
    """

    if not has_current:
        return {
            "has_current_luck": False,
            "phase": "before_first_luck",
            "current_luck_pillar": None,
            "method": "current_luck_v1",
            "status": "before_first_luck",
        }

    return {
        "has_current_luck": True,
        "phase": "in_luck_pillar",
        "current_luck_pillar": {
            "index": 1,
            "ganzhi": ganzhi,
            "stem": stem,
            "branch": branch,
            "stem_element": stem_element,
            "branch_element": branch_element,
            "start_age": 2.0,
            "end_age": 12.0,
        },
        "method": "current_luck_v1",
        "status": "current_luck_resolved",
    }


def make_annual_luck(
    *,
    ganzhi="丁未",
    stem="丁",
    branch="未",
    stem_element="火",
    branch_element="土",
    stem_relation=None,
    branch_relation=None,
    stem_ten_god="食神",
    twelve_stage="養",
):
    """
    annual_luck_v1 相当の最小構造。
    """

    result = {
        "ganzhi": ganzhi,
        "stem": stem,
        "branch": branch,
        "stem_element": stem_element,
        "branch_element": branch_element,
        "stem_ten_god": stem_ten_god,
        "twelve_stage": twelve_stage,
        "method": "annual_luck_v1",
    }

    if stem_relation is not None:
        result[
            "stem_useful_relation"
        ] = stem_relation

    if branch_relation is not None:
        result[
            "branch_useful_relation"
        ] = branch_relation

    return result


def primary_relation():
    return {
        "is_useful": True,
        "is_primary_useful": True,
        "priority": 1,
        "relationship": "primary_useful",
    }


def secondary_relation():
    return {
        "is_useful": True,
        "is_primary_useful": False,
        "priority": 2,
        "relationship": "secondary_useful",
    }


def unfavorable_relation():
    return {
        "is_useful": False,
        "is_primary_useful": False,
        "priority": None,
        "relationship": "support_unfavorable",
    }


def neutral_relation():
    return {
        "is_useful": False,
        "is_primary_useful": False,
        "priority": None,
        "relationship": "neutral",
    }


def unknown_relation():
    return {
        "relationship": "unknown",
    }


# ============================================================
# Constants / metadata
# ============================================================


def test_integrated_luck_method():
    assert (
        INTEGRATED_LUCK_METHOD
        == "integrated_luck_v1"
    )


def test_integrated_luck_status():
    assert (
        INTEGRATED_LUCK_STATUS
        == "provisional_integrated_luck_v1"
    )


def test_five_elements():
    assert FIVE_ELEMENTS == {
        "木",
        "火",
        "土",
        "金",
        "水",
    }


def test_relation_score():
    assert RELATION_SCORE == {
        "same": 1.0,
        "generates": 2.0,
        "generated_by": 1.0,
        "controls": -1.0,
        "controlled_by": -2.0,
        "unknown": 0.0,
    }


def test_useful_relation_score():
    assert USEFUL_RELATION_SCORE == {
        "primary_useful": 3.0,
        "secondary_useful": 2.0,
        "neutral": 0.0,
        "support_unfavorable": -2.0,
        "unknown": 0.0,
    }


# ============================================================
# Current luck helpers
# ============================================================


def test_get_current_luck_pillar():
    current = make_current_luck()

    result = get_current_luck_pillar(
        current
    )

    assert isinstance(
        result,
        dict,
    )

    assert result[
        "ganzhi"
    ] == "丙午"


def test_get_current_luck_pillar_none():
    current = make_current_luck(
        has_current=False
    )

    assert (
        get_current_luck_pillar(
            current
        )
        is None
    )


def test_get_current_luck_pillar_missing_dict():
    current = {
        "has_current_luck": True,
        "current_luck_pillar": None,
    }

    assert (
        get_current_luck_pillar(
            current
        )
        is None
    )


def test_get_current_luck_pillar_invalid_current_luck():
    with pytest.raises(TypeError):
        get_current_luck_pillar(
            []
        )


def test_get_current_luck_ganzhi():
    assert (
        get_current_luck_ganzhi(
            make_current_luck()
        )
        == "丙午"
    )


def test_get_current_luck_ganzhi_none():
    assert (
        get_current_luck_ganzhi(
            make_current_luck(
                has_current=False
            )
        )
        is None
    )


def test_get_current_luck_ganzhi_compatibility_pillar():
    current = {
        "has_current_luck": True,
        "current_luck_pillar": {
            "pillar": "丙午",
        },
    }

    assert (
        get_current_luck_ganzhi(
            current
        )
        == "丙午"
    )


def test_current_elements_direct():
    result = get_current_luck_elements(
        make_current_luck()
    )

    assert result == {
        "stem": "火",
        "branch": "火",
    }


def test_current_elements_fallback_from_stem_branch():
    current = make_current_luck()

    del current[
        "current_luck_pillar"
    ][
        "stem_element"
    ]

    del current[
        "current_luck_pillar"
    ][
        "branch_element"
    ]

    result = get_current_luck_elements(
        current
    )

    assert result == {
        "stem": "火",
        "branch": "火",
    }


def test_current_elements_invalid_direct_values_fallback():
    current = make_current_luck()

    current[
        "current_luck_pillar"
    ][
        "stem_element"
    ] = "空"

    current[
        "current_luck_pillar"
    ][
        "branch_element"
    ] = "空"

    result = get_current_luck_elements(
        current
    )

    assert result == {
        "stem": "火",
        "branch": "火",
    }


def test_current_elements_none_without_current_luck():
    result = get_current_luck_elements(
        make_current_luck(
            has_current=False
        )
    )

    assert result == {
        "stem": None,
        "branch": None,
    }


def test_current_elements_invalid_stem_branch():
    current = {
        "has_current_luck": True,
        "current_luck_pillar": {
            "ganzhi": "XX",
            "stem": "X",
            "branch": "Y",
        },
    }

    result = get_current_luck_elements(
        current
    )

    assert result == {
        "stem": None,
        "branch": None,
    }


# ============================================================
# Annual luck helpers
# ============================================================


def test_annual_elements_direct():
    result = get_annual_luck_elements(
        make_annual_luck()
    )

    assert result == {
        "stem": "火",
        "branch": "土",
    }


def test_annual_elements_fallback_from_stem_branch():
    annual = make_annual_luck()

    del annual["stem_element"]
    del annual["branch_element"]

    result = get_annual_luck_elements(
        annual
    )

    assert result == {
        "stem": "火",
        "branch": "土",
    }


def test_annual_elements_invalid_direct_fallback():
    annual = make_annual_luck()

    annual["stem_element"] = "空"
    annual["branch_element"] = "空"

    result = get_annual_luck_elements(
        annual
    )

    assert result == {
        "stem": "火",
        "branch": "土",
    }


def test_annual_elements_unknown():
    annual = {
        "stem": "X",
        "branch": "Y",
    }

    result = get_annual_luck_elements(
        annual
    )

    assert result == {
        "stem": None,
        "branch": None,
    }


def test_get_annual_elements_invalid_type():
    with pytest.raises(TypeError):
        get_annual_luck_elements(
            []
        )


# ============================================================
# Element interaction
# ============================================================


@pytest.mark.parametrize(
    "source,target,relationship,score",
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
            "金",
            "木",
            "controls",
            -1.0,
        ),
        (
            "木",
            "金",
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


@pytest.mark.parametrize(
    "source,target",
    [
        (None, "火"),
        ("木", None),
        ("空", "火"),
        ("木", "空"),
        (None, None),
    ],
)
def test_element_interaction_unknown(
    source,
    target,
):
    result = (
        evaluate_element_interaction(
            source,
            target,
        )
    )

    assert result[
        "relationship"
    ] == "unknown"

    assert result[
        "score"
    ] == 0.0


def test_build_element_interactions():
    current = make_current_luck(
        stem="甲",
        branch="寅",
        stem_element="木",
        branch_element="木",
        ganzhi="甲寅",
    )

    annual = make_annual_luck(
        ganzhi="丙午",
        stem="丙",
        branch="午",
        stem_element="火",
        branch_element="火",
    )

    result = build_element_interactions(
        current,
        annual,
    )

    assert result[
        "current_luck_elements"
    ] == {
        "stem": "木",
        "branch": "木",
    }

    assert result[
        "annual_luck_elements"
    ] == {
        "stem": "火",
        "branch": "火",
    }

    assert result[
        "stem_relation"
    ][
        "relationship"
    ] == "generates"

    assert result[
        "branch_relation"
    ][
        "relationship"
    ] == "generates"

    assert result[
        "score"
    ] == 4.0


def test_build_element_interactions_without_current_luck():
    result = build_element_interactions(
        make_current_luck(
            has_current=False
        ),
        make_annual_luck(),
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


# ============================================================
# Useful relation score
# ============================================================


@pytest.mark.parametrize(
    "relation,expected",
    [
        (
            primary_relation(),
            3.0,
        ),
        (
            secondary_relation(),
            2.0,
        ),
        (
            neutral_relation(),
            0.0,
        ),
        (
            unfavorable_relation(),
            -2.0,
        ),
        (
            unknown_relation(),
            0.0,
        ),
        (
            None,
            0.0,
        ),
        (
            [],
            0.0,
        ),
    ],
)
def test_score_useful_relation(
    relation,
    expected,
):
    assert (
        score_useful_relation(
            relation
        )
        == expected
    )


def test_unknown_useful_relationship_value():
    result = score_useful_relation(
        {
            "relationship": "something_new",
        }
    )

    assert result == 0.0


# ============================================================
# Current luck useful gods
# ============================================================


def test_current_luck_useful_primary_primary():
    current = make_current_luck(
        stem="丙",
        branch="午",
        stem_element="火",
        branch_element="火",
        ganzhi="丙午",
    )

    result = (
        evaluate_current_luck_useful_gods(
            current,
            make_useful_gods(),
        )
    )

    assert result[
        "stem_element"
    ] == "火"

    assert result[
        "branch_element"
    ] == "火"

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


def test_current_luck_useful_secondary_and_unfavorable():
    current = make_current_luck(
        stem="戊",
        branch="子",
        stem_element="土",
        branch_element="水",
        ganzhi="戊子",
    )

    result = (
        evaluate_current_luck_useful_gods(
            current,
            make_useful_gods(),
        )
    )

    assert result[
        "stem_relation"
    ][
        "relationship"
    ] == "secondary_useful"

    assert result[
        "branch_relation"
    ][
        "relationship"
    ] == "support_unfavorable"

    assert result[
        "score"
    ] == 0.0


def test_current_luck_useful_no_current_luck():
    result = (
        evaluate_current_luck_useful_gods(
            make_current_luck(
                has_current=False
            ),
            make_useful_gods(),
        )
    )

    assert result[
        "stem_element"
    ] is None

    assert result[
        "branch_element"
    ] is None

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


def test_current_luck_useful_without_useful_gods():
    result = (
        evaluate_current_luck_useful_gods(
            make_current_luck(),
            None,
        )
    )

    assert result[
        "stem_score"
    ] == 0.0

    assert result[
        "branch_score"
    ] == 0.0

    assert result[
        "score"
    ] == 0.0


# ============================================================
# Annual luck useful gods
# ============================================================


def test_annual_luck_prefers_existing_relations():
    annual = make_annual_luck(
        stem_relation=(
            unfavorable_relation()
        ),
        branch_relation=(
            primary_relation()
        ),
    )

    result = (
        evaluate_annual_luck_useful_gods(
            annual,
            make_useful_gods(),
        )
    )

    assert result[
        "stem_relation"
    ][
        "relationship"
    ] == "support_unfavorable"

    assert result[
        "branch_relation"
    ][
        "relationship"
    ] == "primary_useful"

    assert result[
        "stem_score"
    ] == -2.0

    assert result[
        "branch_score"
    ] == 3.0

    assert result[
        "score"
    ] == 1.0


def test_annual_luck_recalculates_missing_relations():
    annual = make_annual_luck(
        stem="丁",
        branch="未",
        stem_element="火",
        branch_element="土",
    )

    result = (
        evaluate_annual_luck_useful_gods(
            annual,
            make_useful_gods(),
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
    ] == "secondary_useful"

    assert result[
        "stem_score"
    ] == 3.0

    assert result[
        "branch_score"
    ] == 2.0

    assert result[
        "score"
    ] == 5.0


def test_annual_luck_useful_without_useful_gods():
    result = (
        evaluate_annual_luck_useful_gods(
            make_annual_luck(),
            None,
        )
    )

    assert result[
        "score"
    ] == 0.0


def test_annual_luck_unknown_elements():
    annual = {
        "stem": "X",
        "branch": "Y",
    }

    result = (
        evaluate_annual_luck_useful_gods(
            annual,
            make_useful_gods(),
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


# ============================================================
# Useful gods agreement
# ============================================================


def make_useful_bundle(
    stem_relation,
    branch_relation,
):
    return {
        "stem_relation": stem_relation,
        "branch_relation": branch_relation,
    }


def test_agreement_unknown():
    result = (
        evaluate_useful_gods_agreement(
            make_useful_bundle(
                unknown_relation(),
                unknown_relation(),
            ),
            make_useful_bundle(
                unknown_relation(),
                unknown_relation(),
            ),
        )
    )

    assert result[
        "agreement_level"
    ] == "unknown"

    assert result[
        "known_count"
    ] == 0


def test_agreement_strong_useful_alignment():
    result = (
        evaluate_useful_gods_agreement(
            make_useful_bundle(
                primary_relation(),
                secondary_relation(),
            ),
            make_useful_bundle(
                primary_relation(),
                neutral_relation(),
            ),
        )
    )

    assert result[
        "useful_count"
    ] == 3

    assert result[
        "unfavorable_count"
    ] == 0

    assert (
        result[
            "agreement_level"
        ]
        == "strong_useful_alignment"
    )

    assert result[
        "has_useful_alignment"
    ] is True

    assert result[
        "has_mixed_signal"
    ] is False


def test_agreement_strong_unfavorable_alignment():
    result = (
        evaluate_useful_gods_agreement(
            make_useful_bundle(
                unfavorable_relation(),
                unfavorable_relation(),
            ),
            make_useful_bundle(
                unfavorable_relation(),
                neutral_relation(),
            ),
        )
    )

    assert result[
        "useful_count"
    ] == 0

    assert result[
        "unfavorable_count"
    ] == 3

    assert (
        result[
            "agreement_level"
        ]
        == "strong_unfavorable_alignment"
    )


def test_agreement_mixed():
    result = (
        evaluate_useful_gods_agreement(
            make_useful_bundle(
                primary_relation(),
                unfavorable_relation(),
            ),
            make_useful_bundle(
                neutral_relation(),
                neutral_relation(),
            ),
        )
    )

    assert (
        result[
            "agreement_level"
        ]
        == "mixed"
    )

    assert result[
        "has_useful_alignment"
    ] is True

    assert result[
        "has_unfavorable_alignment"
    ] is True

    assert result[
        "has_mixed_signal"
    ] is True


def test_agreement_useful_alignment():
    result = (
        evaluate_useful_gods_agreement(
            make_useful_bundle(
                primary_relation(),
                neutral_relation(),
            ),
            make_useful_bundle(
                neutral_relation(),
                neutral_relation(),
            ),
        )
    )

    assert (
        result[
            "agreement_level"
        ]
        == "useful_alignment"
    )


def test_agreement_unfavorable_alignment():
    result = (
        evaluate_useful_gods_agreement(
            make_useful_bundle(
                unfavorable_relation(),
                neutral_relation(),
            ),
            make_useful_bundle(
                neutral_relation(),
                neutral_relation(),
            ),
        )
    )

    assert (
        result[
            "agreement_level"
        ]
        == "unfavorable_alignment"
    )


def test_agreement_neutral():
    result = (
        evaluate_useful_gods_agreement(
            make_useful_bundle(
                neutral_relation(),
                neutral_relation(),
            ),
            make_useful_bundle(
                neutral_relation(),
                neutral_relation(),
            ),
        )
    )

    assert (
        result[
            "agreement_level"
        ]
        == "neutral"
    )

    assert result[
        "known_count"
    ] == 4


# ============================================================
# Integrated score
# ============================================================


def test_calculate_integrated_score():
    result = calculate_integrated_score(
        element_interactions={
            "score": 4.0,
        },
        current_useful={
            "score": 6.0,
        },
        annual_useful={
            "score": 5.0,
        },
    )

    assert result[
        "element_interaction_score"
    ] == 4.0

    assert result[
        "current_luck_useful_score"
    ] == 6.0

    assert result[
        "annual_luck_useful_score"
    ] == 5.0

    assert result[
        "total_score"
    ] == 15.0


def test_integrated_score_defaults_zero():
    result = calculate_integrated_score(
        element_interactions={},
        current_useful={},
        annual_useful={},
    )

    assert result == {
        "element_interaction_score": 0.0,
        "current_luck_useful_score": 0.0,
        "annual_luck_useful_score": 0.0,
        "total_score": 0.0,
    }


def test_integrated_score_negative():
    result = calculate_integrated_score(
        element_interactions={
            "score": -4.0,
        },
        current_useful={
            "score": -4.0,
        },
        annual_useful={
            "score": -4.0,
        },
    )

    assert result[
        "total_score"
    ] == -12.0


# ============================================================
# Integrated level thresholds
# ============================================================


@pytest.mark.parametrize(
    "score,expected",
    [
        (100.0, "very_supportive"),
        (8.0, "very_supportive"),
        (7.999, "supportive"),
        (4.0, "supportive"),
        (3.999, "mixed"),
        (0.0, "mixed"),
        (-3.999, "mixed"),
        (-4.0, "challenging"),
        (-7.999, "challenging"),
        (-8.0, "very_challenging"),
        (-100.0, "very_challenging"),
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


# ============================================================
# Confidence
# ============================================================


def test_confidence_high():
    result = (
        calculate_integrated_confidence(
            current_luck=(
                make_current_luck()
            ),
            annual_luck=(
                make_annual_luck()
            ),
            useful_gods=(
                make_useful_gods()
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


def test_confidence_medium_without_useful_gods():
    result = (
        calculate_integrated_confidence(
            current_luck=(
                make_current_luck()
            ),
            annual_luck=(
                make_annual_luck()
            ),
            useful_gods=None,
        )
    )

    assert result[
        "available_sources"
    ] == 2

    assert result[
        "level"
    ] == "medium"


def test_confidence_medium_without_current_luck():
    result = (
        calculate_integrated_confidence(
            current_luck=(
                make_current_luck(
                    has_current=False
                )
            ),
            annual_luck=(
                make_annual_luck()
            ),
            useful_gods=(
                make_useful_gods()
            ),
        )
    )

    assert result[
        "available_sources"
    ] == 2

    assert result[
        "level"
    ] == "medium"


def test_confidence_low_one_source():
    result = (
        calculate_integrated_confidence(
            current_luck=(
                make_current_luck(
                    has_current=False
                )
            ),
            annual_luck={},
            useful_gods=(
                make_useful_gods()
            ),
        )
    )

    assert result[
        "available_sources"
    ] == 1

    assert result[
        "level"
    ] == "low"


def test_confidence_low_zero_source():
    result = (
        calculate_integrated_confidence(
            current_luck=(
                make_current_luck(
                    has_current=False
                )
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


# ============================================================
# Reasoning
# ============================================================


def test_reasoning_contains_core_information():
    reasoning = (
        build_integrated_luck_reasoning(
            current_luck_ganzhi="丙午",
            annual_luck_ganzhi="丁未",
            element_interactions={
                "stem_relation": {
                    "relationship": "same",
                },
                "branch_relation": {
                    "relationship": "generates",
                },
            },
            agreement={
                "agreement_level": (
                    "strong_useful_alignment"
                ),
            },
            score_data={
                "total_score": 10.0,
            },
            overall_level=(
                "very_supportive"
            ),
            annual_ten_god="食神",
            annual_twelve_stage="養",
        )
    )

    assert isinstance(
        reasoning,
        list,
    )

    assert reasoning

    joined = "\n".join(
        reasoning
    )

    assert "丙午" in joined
    assert "丁未" in joined
    assert "same" in joined
    assert "generates" in joined
    assert "strong_useful_alignment" in joined
    assert "食神" in joined
    assert "養" in joined
    assert "10.0" in joined
    assert "very_supportive" in joined


def test_reasoning_without_current_luck():
    reasoning = (
        build_integrated_luck_reasoning(
            current_luck_ganzhi=None,
            annual_luck_ganzhi="丁未",
            element_interactions={
                "stem_relation": {
                    "relationship": "unknown",
                },
                "branch_relation": {
                    "relationship": "unknown",
                },
            },
            agreement={
                "agreement_level": "unknown",
            },
            score_data={
                "total_score": 0.0,
            },
            overall_level="mixed",
            annual_ten_god=None,
            annual_twelve_stage=None,
        )
    )

    assert (
        "現在大運は特定されていません。"
        in reasoning
    )


def test_reasoning_mentions_v1_limitation():
    reasoning = (
        build_integrated_luck_reasoning(
            current_luck_ganzhi="丙午",
            annual_luck_ganzhi="丁未",
            element_interactions={
                "stem_relation": {
                    "relationship": "same",
                },
                "branch_relation": {
                    "relationship": "same",
                },
            },
            agreement={
                "agreement_level": "neutral",
            },
            score_data={
                "total_score": 0.0,
            },
            overall_level="mixed",
            annual_ten_god=None,
            annual_twelve_stage=None,
        )
    )

    joined = "\n".join(
        reasoning
    )

    assert "干合" in joined
    assert "支合" in joined
    assert "冲" in joined
    assert "刑" in joined
    assert "害" in joined


# ============================================================
# Full integration - very supportive
# ============================================================


def test_build_integrated_luck_very_supportive():
    """
    大運:
        丙午 = 火 / 火

    歳運:
        丁未 = 火 / 土

    用神:
        火 primary
        土 secondary

    大運×歳運:
        火 -> 火 = same +1
        火 -> 土 = generates +2
        interaction = +3

    大運用神:
        火 +3
        火 +3
        = +6

    歳運用神:
        火 +3
        土 +2
        = +5

    total:
        3 + 6 + 5 = 14

    => very_supportive
    """

    result = build_integrated_luck(
        current_luck=(
            make_current_luck()
        ),
        annual_luck=(
            make_annual_luck()
        ),
        useful_gods=(
            make_useful_gods()
        ),
    )

    assert result[
        "current_luck_ganzhi"
    ] == "丙午"

    assert result[
        "annual_luck_ganzhi"
    ] == "丁未"

    assert result[
        "current_luck_elements"
    ] == {
        "stem": "火",
        "branch": "火",
    }

    assert result[
        "annual_luck_elements"
    ] == {
        "stem": "火",
        "branch": "土",
    }

    assert result[
        "element_interactions"
    ][
        "stem_relation"
    ][
        "relationship"
    ] == "same"

    assert result[
        "element_interactions"
    ][
        "branch_relation"
    ][
        "relationship"
    ] == "generates"

    assert result[
        "element_interactions"
    ][
        "score"
    ] == 3.0

    assert result[
        "current_luck_useful"
    ][
        "score"
    ] == 6.0

    assert result[
        "annual_luck_useful"
    ][
        "score"
    ] == 5.0

    assert result[
        "score"
    ][
        "total_score"
    ] == 14.0

    assert result[
        "overall_score"
    ] == 14.0

    assert result[
        "overall_level"
    ] == "very_supportive"

    assert result[
        "confidence"
    ][
        "level"
    ] == "high"

    assert result[
        "annual_ten_god"
    ] == "食神"

    assert result[
        "annual_twelve_stage"
    ] == "養"

    assert result[
        "method"
    ] == "integrated_luck_v1"

    assert result[
        "status"
    ] == (
        "provisional_integrated_luck_v1"
    )


# ============================================================
# Full integration - challenging
# ============================================================


def test_build_integrated_luck_unfavorable():
    """
    大運:
        壬子 = 水 / 水
        -> 用神上 unfavorable / unfavorable

    歳運:
        癸亥 = 水 / 水
        -> 用神上 unfavorable / unfavorable

    五行関係:
        水 -> 水 = same +1
        水 -> 水 = same +1
        interaction = +2

    current useful:
        -2 + -2 = -4

    annual useful:
        -2 + -2 = -4

    total:
        +2 -4 -4 = -6

    => challenging
    """

    current = make_current_luck(
        stem="壬",
        branch="子",
        stem_element="水",
        branch_element="水",
        ganzhi="壬子",
    )

    annual = make_annual_luck(
        ganzhi="癸亥",
        stem="癸",
        branch="亥",
        stem_element="水",
        branch_element="水",
    )

    result = build_integrated_luck(
        current_luck=current,
        annual_luck=annual,
        useful_gods=(
            make_useful_gods()
        ),
    )

    assert result[
        "element_interactions"
    ][
        "score"
    ] == 2.0

    assert result[
        "current_luck_useful"
    ][
        "score"
    ] == -4.0

    assert result[
        "annual_luck_useful"
    ][
        "score"
    ] == -4.0

    assert result[
        "overall_score"
    ] == -6.0

    assert result[
        "overall_level"
    ] == "challenging"

    assert (
        result[
            "useful_gods_agreement"
        ][
            "agreement_level"
        ]
        == "strong_unfavorable_alignment"
    )


# ============================================================
# Full integration - no useful gods
# ============================================================


def test_build_integrated_luck_without_useful_gods():
    result = build_integrated_luck(
        current_luck=(
            make_current_luck()
        ),
        annual_luck=(
            make_annual_luck()
        ),
        useful_gods=None,
    )

    assert result[
        "current_luck_useful"
    ][
        "score"
    ] == 0.0

    assert result[
        "annual_luck_useful"
    ][
        "score"
    ] == 0.0

    assert result[
        "overall_score"
    ] == 3.0

    assert result[
        "overall_level"
    ] == "mixed"

    assert result[
        "confidence"
    ][
        "level"
    ] == "medium"


# ============================================================
# Full integration - no current luck
# ============================================================


def test_build_integrated_luck_before_first_luck():
    result = build_integrated_luck(
        current_luck=(
            make_current_luck(
                has_current=False
            )
        ),
        annual_luck=(
            make_annual_luck()
        ),
        useful_gods=(
            make_useful_gods()
        ),
    )

    assert result[
        "current_luck_ganzhi"
    ] is None

    assert result[
        "current_luck_elements"
    ] == {
        "stem": None,
        "branch": None,
    }

    assert result[
        "element_interactions"
    ][
        "score"
    ] == 0.0

    assert result[
        "current_luck_useful"
    ][
        "score"
    ] == 0.0

    assert result[
        "annual_luck_useful"
    ][
        "score"
    ] == 5.0

    assert result[
        "overall_score"
    ] == 5.0

    assert result[
        "overall_level"
    ] == "supportive"

    assert result[
        "confidence"
    ][
        "level"
    ] == "medium"


# ============================================================
# Existing annual useful relations take priority
# ============================================================


def test_build_integrated_luck_respects_annual_existing_relations():
    annual = make_annual_luck(
        stem_relation=(
            unfavorable_relation()
        ),
        branch_relation=(
            unfavorable_relation()
        ),
    )

    result = build_integrated_luck(
        current_luck=(
            make_current_luck()
        ),
        annual_luck=annual,
        useful_gods=(
            make_useful_gods()
        ),
    )

    assert (
        result[
            "annual_luck_useful"
        ][
            "stem_relation"
        ][
            "relationship"
        ]
        == "support_unfavorable"
    )

    assert (
        result[
            "annual_luck_useful"
        ][
            "branch_relation"
        ][
            "relationship"
        ]
        == "support_unfavorable"
    )

    assert result[
        "annual_luck_useful"
    ][
        "score"
    ] == -4.0


# ============================================================
# Agreement integration
# ============================================================


def test_full_useful_agreement_strong():
    result = build_integrated_luck(
        current_luck=(
            make_current_luck()
        ),
        annual_luck=(
            make_annual_luck()
        ),
        useful_gods=(
            make_useful_gods()
        ),
    )

    agreement = result[
        "useful_gods_agreement"
    ]

    assert (
        agreement[
            "agreement_level"
        ]
        == "strong_useful_alignment"
    )

    assert agreement[
        "useful_count"
    ] == 4

    assert agreement[
        "unfavorable_count"
    ] == 0


def test_full_useful_agreement_mixed():
    current = make_current_luck(
        stem="丙",
        branch="子",
        stem_element="火",
        branch_element="水",
        ganzhi="丙子",
    )

    annual = make_annual_luck(
        ganzhi="丁亥",
        stem="丁",
        branch="亥",
        stem_element="火",
        branch_element="水",
    )

    result = build_integrated_luck(
        current_luck=current,
        annual_luck=annual,
        useful_gods=(
            make_useful_gods()
        ),
    )

    assert (
        result[
            "useful_gods_agreement"
        ][
            "agreement_level"
        ]
        == "mixed"
    )

    assert result[
        "useful_gods_agreement"
    ][
        "useful_count"
    ] == 2

    assert result[
        "useful_gods_agreement"
    ][
        "unfavorable_count"
    ] == 2


# ============================================================
# Evidence
# ============================================================


def test_integrated_luck_evidence_integrity():
    result = build_integrated_luck(
        current_luck=(
            make_current_luck()
        ),
        annual_luck=(
            make_annual_luck()
        ),
        useful_gods=(
            make_useful_gods()
        ),
    )

    evidence = result[
        "evidence"
    ]

    assert evidence[
        "current_luck_ganzhi"
    ] == "丙午"

    assert evidence[
        "annual_luck_ganzhi"
    ] == "丁未"

    assert (
        evidence[
            "element_interactions"
        ]
        == result[
            "element_interactions"
        ]
    )

    assert (
        evidence[
            "current_luck_useful"
        ]
        == result[
            "current_luck_useful"
        ]
    )

    assert (
        evidence[
            "annual_luck_useful"
        ]
        == result[
            "annual_luck_useful"
        ]
    )

    assert (
        evidence[
            "useful_gods_agreement"
        ]
        == result[
            "useful_gods_agreement"
        ]
    )

    assert evidence[
        "annual_ten_god"
    ] == "食神"

    assert evidence[
        "annual_twelve_stage"
    ] == "養"

    assert (
        evidence["score"]
        == result["score"]
    )


# ============================================================
# Reasoning output
# ============================================================


def test_full_reasoning_is_non_empty():
    result = build_integrated_luck(
        current_luck=(
            make_current_luck()
        ),
        annual_luck=(
            make_annual_luck()
        ),
        useful_gods=(
            make_useful_gods()
        ),
    )

    assert isinstance(
        result[
            "reasoning"
        ],
        list,
    )

    assert result[
        "reasoning"
    ]

    assert all(
        isinstance(item, str)
        and item
        for item in result[
            "reasoning"
        ]
    )


def test_full_reasoning_contains_ganzhi():
    result = build_integrated_luck(
        current_luck=(
            make_current_luck()
        ),
        annual_luck=(
            make_annual_luck()
        ),
        useful_gods=(
            make_useful_gods()
        ),
    )

    joined = "\n".join(
        result[
            "reasoning"
        ]
    )

    assert "丙午" in joined
    assert "丁未" in joined


# ============================================================
# Notes
# ============================================================


def test_integrated_luck_notes():
    result = build_integrated_luck(
        current_luck=(
            make_current_luck()
        ),
        annual_luck=(
            make_annual_luck()
        ),
        useful_gods=(
            make_useful_gods()
        ),
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

    joined = "\n".join(
        result[
            "notes"
        ]
    )

    assert "integrated_luck_v1" in joined
    assert "useful_gods_v3" in joined
    assert "絶対的な吉凶値" in joined


# ============================================================
# Required output keys
# ============================================================


def test_integrated_luck_required_keys():
    result = build_integrated_luck(
        current_luck=(
            make_current_luck()
        ),
        annual_luck=(
            make_annual_luck()
        ),
        useful_gods=(
            make_useful_gods()
        ),
    )

    required = {
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

    assert required.issubset(
        result.keys()
    )


# ============================================================
# Alias APIs
# ============================================================


def test_calculate_integrated_luck_matches_builder():
    kwargs = {
        "current_luck": (
            make_current_luck()
        ),
        "annual_luck": (
            make_annual_luck()
        ),
        "useful_gods": (
            make_useful_gods()
        ),
    }

    direct = build_integrated_luck(
        **kwargs
    )

    calculated = (
        calculate_integrated_luck(
            **kwargs
        )
    )

    assert calculated == direct


def test_evaluate_integrated_luck_matches_calculate():
    kwargs = {
        "current_luck": (
            make_current_luck()
        ),
        "annual_luck": (
            make_annual_luck()
        ),
        "useful_gods": (
            make_useful_gods()
        ),
    }

    calculated = (
        calculate_integrated_luck(
            **kwargs
        )
    )

    evaluated = (
        evaluate_integrated_luck(
            **kwargs
        )
    )

    assert evaluated == calculated


# ============================================================
# Validation
# ============================================================


@pytest.mark.parametrize(
    "current_luck",
    [
        None,
        [],
        "current",
    ],
)
def test_invalid_current_luck(
    current_luck,
):
    with pytest.raises(TypeError):
        build_integrated_luck(
            current_luck=current_luck,
            annual_luck=(
                make_annual_luck()
            ),
            useful_gods=(
                make_useful_gods()
            ),
        )


@pytest.mark.parametrize(
    "annual_luck",
    [
        None,
        [],
        "annual",
    ],
)
def test_invalid_annual_luck(
    annual_luck,
):
    with pytest.raises(TypeError):
        build_integrated_luck(
            current_luck=(
                make_current_luck()
            ),
            annual_luck=annual_luck,
            useful_gods=(
                make_useful_gods()
            ),
        )


@pytest.mark.parametrize(
    "useful_gods",
    [
        [],
        "useful",
        123,
    ],
)
def test_invalid_useful_gods(
    useful_gods,
):
    with pytest.raises(TypeError):
        build_integrated_luck(
            current_luck=(
                make_current_luck()
            ),
            annual_luck=(
                make_annual_luck()
            ),
            useful_gods=useful_gods,
        )


# ============================================================
# Input immutability
# ============================================================


def test_build_integrated_luck_does_not_mutate_inputs():
    current = make_current_luck()
    annual = make_annual_luck()
    useful = make_useful_gods()

    current_before = deepcopy(
        current
    )

    annual_before = deepcopy(
        annual
    )

    useful_before = deepcopy(
        useful
    )

    build_integrated_luck(
        current_luck=current,
        annual_luck=annual,
        useful_gods=useful,
    )

    assert current == current_before
    assert annual == annual_before
    assert useful == useful_before


# ============================================================
# Determinism
# ============================================================


def test_integrated_luck_is_deterministic():
    current = make_current_luck()
    annual = make_annual_luck()
    useful = make_useful_gods()

    first = build_integrated_luck(
        current_luck=current,
        annual_luck=annual,
        useful_gods=useful,
    )

    second = build_integrated_luck(
        current_luck=current,
        annual_luck=annual,
        useful_gods=useful,
    )

    assert first == second


# ============================================================
# Annual ten god / twelve stage pass-through
# ============================================================


def test_annual_ten_god_passthrough():
    annual = make_annual_luck(
        stem_ten_god="偏財",
    )

    result = build_integrated_luck(
        current_luck=(
            make_current_luck()
        ),
        annual_luck=annual,
        useful_gods=(
            make_useful_gods()
        ),
    )

    assert result[
        "annual_ten_god"
    ] == "偏財"


def test_annual_twelve_stage_passthrough():
    annual = make_annual_luck(
        twelve_stage="帝旺",
    )

    result = build_integrated_luck(
        current_luck=(
            make_current_luck()
        ),
        annual_luck=annual,
        useful_gods=(
            make_useful_gods()
        ),
    )

    assert result[
        "annual_twelve_stage"
    ] == "帝旺"


def test_missing_annual_ten_god_and_stage():
    annual = make_annual_luck()

    del annual[
        "stem_ten_god"
    ]

    del annual[
        "twelve_stage"
    ]

    result = build_integrated_luck(
        current_luck=(
            make_current_luck()
        ),
        annual_luck=annual,
        useful_gods=(
            make_useful_gods()
        ),
    )

    assert result[
        "annual_ten_god"
    ] is None

    assert result[
        "annual_twelve_stage"
    ] is None


# ============================================================
# Score consistency
# ============================================================


def test_overall_score_matches_score_total():
    result = build_integrated_luck(
        current_luck=(
            make_current_luck()
        ),
        annual_luck=(
            make_annual_luck()
        ),
        useful_gods=(
            make_useful_gods()
        ),
    )

    assert (
        result[
            "overall_score"
        ]
        == result[
            "score"
        ][
            "total_score"
        ]
    )


def test_overall_level_matches_classifier():
    result = build_integrated_luck(
        current_luck=(
            make_current_luck()
        ),
        annual_luck=(
            make_annual_luck()
        ),
        useful_gods=(
            make_useful_gods()
        ),
    )

    assert (
        result[
            "overall_level"
        ]
        == classify_integrated_level(
            result[
                "overall_score"
            ]
        )
    )


# ============================================================
# Current / annual elements consistency
# ============================================================


def test_current_elements_match_interaction_evidence():
    result = build_integrated_luck(
        current_luck=(
            make_current_luck()
        ),
        annual_luck=(
            make_annual_luck()
        ),
        useful_gods=(
            make_useful_gods()
        ),
    )

    assert (
        result[
            "current_luck_elements"
        ]
        == result[
            "element_interactions"
        ][
            "current_luck_elements"
        ]
    )


def test_annual_elements_match_interaction_evidence():
    result = build_integrated_luck(
        current_luck=(
            make_current_luck()
        ),
        annual_luck=(
            make_annual_luck()
        ),
        useful_gods=(
            make_useful_gods()
        ),
    )

    assert (
        result[
            "annual_luck_elements"
        ]
        == result[
            "element_interactions"
        ][
            "annual_luck_elements"
        ]
    )


# ============================================================
# Final representative regression
# ============================================================


def test_final_integrated_luck_regression():
    """
    integrated_luck_v1 の代表ケース。

    現在大運:
        丙午

    歳運:
        丁未

    用神:
        火 = primary
        土 = secondary

    統合結果:
        interaction +3
        current useful +6
        annual useful +5
        total +14

    overall:
        very_supportive
    """

    result = calculate_integrated_luck(
        current_luck=(
            make_current_luck()
        ),
        annual_luck=(
            make_annual_luck()
        ),
        useful_gods=(
            make_useful_gods()
        ),
    )

    assert result[
        "current_luck_ganzhi"
    ] == "丙午"

    assert result[
        "annual_luck_ganzhi"
    ] == "丁未"

    assert result[
        "score"
    ] == {
        "element_interaction_score": 3.0,
        "current_luck_useful_score": 6.0,
        "annual_luck_useful_score": 5.0,
        "total_score": 14.0,
    }

    assert result[
        "overall_score"
    ] == 14.0

    assert result[
        "overall_level"
    ] == "very_supportive"

    assert (
        result[
            "useful_gods_agreement"
        ][
            "agreement_level"
        ]
        == "strong_useful_alignment"
    )

    assert result[
        "confidence"
    ] == {
        "available_sources": 3,
        "total_sources": 3,
        "ratio": 1.0,
        "level": "high",
    }

    assert result[
        "annual_ten_god"
    ] == "食神"

    assert result[
        "annual_twelve_stage"
    ] == "養"

    assert result[
        "method"
    ] == "integrated_luck_v1"

    assert result[
        "status"
    ] == (
        "provisional_integrated_luck_v1"
    )
