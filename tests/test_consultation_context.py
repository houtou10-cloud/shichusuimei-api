"""
tests/test_consultation_context.py

engine/consultation_context.py の非LIVE品質テスト。

目的
----
顧客から受け取った、

- 現在のお悩み
- 理想の未来

を、

    命式 = 事実
    相談 = 焦点
    AI   = 説明

という責務分離を維持しながら、
AI鑑定向けの consultation_context へ
安全に変換できることを検証する。

主な検証内容
------------
1. version / method / status
2. 空相談
3. 仕事相談
4. 金銭相談
5. 恋愛相談
6. 健康相談
7. 現在運相談
8. 将来相談
9. 自己理解相談
10. secondary focus
11. priority / relevant sections
12. 医療注意
13. 金銭・投資注意
14. 確実性注意
15. AI usage policy
16. 占術再計算禁止
17. 命式事実書き換え禁止
18. 入力文字数制限
19. 非文字列拒否
20. whitespace正規化
21. compact context
22. aliases
23. metadata
24. immutability
25. final gate

このテストは非LIVE。
OpenAI API料金は発生しない。

Version
-------
consultation_context_test_v1
"""

from __future__ import annotations

from copy import deepcopy

import pytest

from engine.consultation_context import (
    CONSULTATION_CONTEXT_METHOD,
    CONSULTATION_CONTEXT_STATUS,
    CONSULTATION_CONTEXT_VERSION,
    FOCUS_CATEGORIES,
    MAX_COMBINED_CHARS,
    MAX_CONCERN_CHARS,
    MAX_DESIRED_FUTURE_CHARS,
    READING_SECTION_KEYS,
    analyze_consultation_categories,
    analyze_consultation_safety,
    build_ai_usage_policy,
    build_compact_consultation_context,
    build_consultation_context,
    build_consultation_instructions,
    build_relevant_sections,
    calculate_consultation_context,
    get_consultation_context_metadata,
    prepare_consultation_context,
    validate_consultation_context,
    validate_consultation_input,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def career_context():
    return build_consultation_context(
        concern=(
            "今の仕事を続けるか転職するか悩んでいます。"
            "収入にも不安があります。"
        ),
        desired_future=(
            "自分の強みを活かして、"
            "安定した収入を得たいです。"
        ),
    )


@pytest.fixture
def relationship_context():
    return build_consultation_context(
        concern=(
            "恋愛と結婚について悩んでいます。"
            "今のパートナーとの関係も気になります。"
        ),
        desired_future=(
            "安心できる相手と結婚して、"
            "穏やかな家庭を築きたいです。"
        ),
    )


@pytest.fixture
def wealth_context():
    return build_consultation_context(
        concern=(
            "収入が増えず、"
            "お金や貯金について不安があります。"
        ),
        desired_future=(
            "経済的に安定して、"
            "無理なく資産を増やしたいです。"
        ),
    )


@pytest.fixture
def health_context():
    return build_consultation_context(
        concern=(
            "最近疲れやすく、"
            "健康や体調について気になります。"
        ),
        desired_future=(
            "心身ともに安定して"
            "元気に生活したいです。"
        ),
    )


# ============================================================
# 1. Constants
# ============================================================


def test_version_constant():
    assert (
        CONSULTATION_CONTEXT_VERSION
        == "consultation_context_v1"
    )


def test_method_constant():
    assert (
        CONSULTATION_CONTEXT_METHOD
        == "consultation_context_v1"
    )


def test_status_constant():
    assert (
        CONSULTATION_CONTEXT_STATUS
        == "ready_for_ai_reading"
    )


def test_limits_are_positive():
    assert MAX_CONCERN_CHARS > 0
    assert MAX_DESIRED_FUTURE_CHARS > 0
    assert MAX_COMBINED_CHARS > 0


def test_combined_limit_is_reasonable():
    assert (
        MAX_COMBINED_CHARS
        <= (
            MAX_CONCERN_CHARS
            + MAX_DESIRED_FUTURE_CHARS
        )
    )


def test_section_keys_exact():
    assert READING_SECTION_KEYS == (
        "core_personality",
        "career",
        "wealth",
        "relationships",
        "health",
        "current_luck",
        "future_flow",
        "advice",
    )


def test_focus_categories_contains_general():
    assert (
        "general"
        in FOCUS_CATEGORIES
    )


# ============================================================
# 2. Empty consultation
# ============================================================


def test_empty_consultation_is_valid():
    result = (
        build_consultation_context()
    )

    assert (
        result[
            "validation"
        ][
            "valid"
        ]
        is True
    )


def test_empty_consultation_has_no_consultation():
    result = (
        build_consultation_context()
    )

    assert (
        result[
            "has_consultation"
        ]
        is False
    )


def test_empty_consultation_primary_general():
    result = (
        build_consultation_context()
    )

    assert (
        result[
            "focus"
        ][
            "primary"
        ]
        == "general"
    )


def test_empty_consultation_input_strings():
    result = (
        build_consultation_context()
    )

    assert (
        result[
            "input"
        ][
            "concern"
        ]
        == ""
    )

    assert (
        result[
            "input"
        ][
            "desired_future"
        ]
        == ""
    )


# ============================================================
# 3. Career
# ============================================================


def test_career_primary_focus(
    career_context,
):
    assert (
        career_context[
            "focus"
        ][
            "primary"
        ]
        == "career"
    )


def test_career_detected_category(
    career_context,
):
    assert (
        "career"
        in career_context[
            "focus"
        ][
            "detected_categories"
        ]
    )


def test_career_priority_sections(
    career_context,
):
    priority = (
        career_context[
            "focus"
        ][
            "priority_sections"
        ]
    )

    assert (
        "career"
        in priority
    )

    assert (
        "current_luck"
        in priority
    )

    assert (
        "future_flow"
        in priority
    )

    assert (
        "advice"
        in priority
    )


def test_career_relevant_sections_include_wealth(
    career_context,
):
    assert (
        "wealth"
        in career_context[
            "focus"
        ][
            "relevant_sections"
        ]
    )


# ============================================================
# 4. Wealth
# ============================================================


def test_wealth_primary_focus(
    wealth_context,
):
    assert (
        wealth_context[
            "focus"
        ][
            "primary"
        ]
        == "wealth"
    )


def test_wealth_priority_contains_wealth(
    wealth_context,
):
    assert (
        "wealth"
        in wealth_context[
            "focus"
        ][
            "priority_sections"
        ]
    )


def test_wealth_has_consultation(
    wealth_context,
):
    assert (
        wealth_context[
            "has_consultation"
        ]
        is True
    )


# ============================================================
# 5. Relationships
# ============================================================


def test_relationship_primary_focus(
    relationship_context,
):
    assert (
        relationship_context[
            "focus"
        ][
            "primary"
        ]
        == "relationships"
    )


def test_relationship_priority_contains_relationships(
    relationship_context,
):
    assert (
        "relationships"
        in relationship_context[
            "focus"
        ][
            "priority_sections"
        ]
    )


# ============================================================
# 6. Health
# ============================================================


def test_health_primary_focus(
    health_context,
):
    assert (
        health_context[
            "focus"
        ][
            "primary"
        ]
        == "health"
    )


def test_health_priority_contains_health(
    health_context,
):
    assert (
        "health"
        in health_context[
            "focus"
        ][
            "priority_sections"
        ]
    )


# ============================================================
# 7. Current luck
# ============================================================


def test_current_luck_primary():
    result = (
        build_consultation_context(
            concern=(
                "今の運勢と今年のタイミングが"
                "気になります。"
            ),
            desired_future="",
        )
    )

    assert (
        result[
            "focus"
        ][
            "primary"
        ]
        == "current_luck"
    )


# ============================================================
# 8. Future flow
# ============================================================


def test_future_flow_primary():
    result = (
        build_consultation_context(
            concern=(
                "これから数年後に"
                "どうなるのか知りたいです。"
            ),
            desired_future=(
                "将来の方向性を"
                "見つけたいです。"
            ),
        )
    )

    assert (
        result[
            "focus"
        ][
            "primary"
        ]
        == "future_flow"
    )


# ============================================================
# 9. Self understanding
# ============================================================


def test_self_understanding_primary():
    result = (
        build_consultation_context(
            concern=(
                "自分の強みや才能、"
                "性格について知りたいです。"
            ),
            desired_future="",
        )
    )

    assert (
        result[
            "focus"
        ][
            "primary"
        ]
        == "self_understanding"
    )


def test_self_understanding_relevant_core_personality():
    result = (
        build_consultation_context(
            concern=(
                "自分の本質と強みを"
                "知りたいです。"
            )
        )
    )

    assert (
        "core_personality"
        in result[
            "focus"
        ][
            "relevant_sections"
        ]
    )


def test_self_understanding_does_not_force_relationships():
    result = (
        build_consultation_context(
            concern=(
                "自分の強みや才能を"
                "仕事に活かしたいです。"
            )
        )
    )

    # consultation_context.py 側で
    # self_understanding から
    # relationships を外した場合の
    # 商品品質契約。
    assert (
        "relationships"
        not in result[
            "focus"
        ][
            "priority_sections"
        ]
    )


# ============================================================
# 10. Category analysis directly
# ============================================================


def test_category_analysis_returns_scores():
    result = (
        analyze_consultation_categories(
            concern=(
                "仕事と転職で悩んでいます。"
            ),
            desired_future=(
                "収入を増やしたいです。"
            ),
        )
    )

    assert isinstance(
        result[
            "category_scores"
        ],
        dict,
    )

    assert (
        result[
            "category_scores"
        ][
            "career"
        ]
        > 0
    )


def test_category_analysis_general_when_no_hits():
    result = (
        analyze_consultation_categories(
            concern=(
                "なんとなく気になります。"
            ),
            desired_future="",
        )
    )

    assert (
        result[
            "primary_focus"
        ]
        == "general"
    )


def test_secondary_focus_is_list():
    result = (
        analyze_consultation_categories(
            concern=(
                "仕事と収入について"
                "悩んでいます。"
            ),
            desired_future=(
                "自分の強みを"
                "活かしたいです。"
            ),
        )
    )

    assert isinstance(
        result[
            "secondary_focus"
        ],
        list,
    )


# ============================================================
# 11. Relevant sections
# ============================================================


def test_build_relevant_sections_career():
    result = (
        build_relevant_sections(
            {
                "primary_focus": (
                    "career"
                ),
                "detected_categories": [
                    "career",
                ],
            }
        )
    )

    assert (
        "career"
        in result[
            "relevant_sections"
        ]
    )


def test_relevant_sections_only_valid_keys():
    result = (
        build_relevant_sections(
            {
                "primary_focus": (
                    "career"
                ),
                "detected_categories": [
                    "career",
                    "wealth",
                ],
            }
        )
    )

    assert all(
        section
        in READING_SECTION_KEYS
        for section
        in result[
            "relevant_sections"
        ]
    )


def test_relevant_sections_preserve_official_order():
    result = (
        build_relevant_sections(
            {
                "primary_focus": (
                    "wealth"
                ),
                "detected_categories": [
                    "wealth",
                    "career",
                ],
            }
        )
    )

    indexes = [
        READING_SECTION_KEYS.index(
            section
        )
        for section
        in result[
            "relevant_sections"
        ]
    ]

    assert indexes == sorted(
        indexes
    )


def test_build_relevant_sections_requires_mapping():
    with pytest.raises(
        TypeError
    ):
        build_relevant_sections(
            []
        )


# ============================================================
# 12. Medical safety
# ============================================================


def test_medical_safety_detected():
    result = (
        analyze_consultation_safety(
            concern=(
                "この病気の病名を"
                "診断してください。"
            ),
            desired_future="",
        )
    )

    assert (
        result[
            "medical_decision_caution"
        ]
        is True
    )


def test_medical_requires_cautious_language():
    result = (
        build_consultation_context(
            concern=(
                "この病気は治るのか"
                "教えてください。"
            )
        )
    )

    assert (
        result[
            "safety"
        ][
            "requires_cautious_language"
        ]
        is True
    )


def test_medical_warning_exists():
    result = (
        build_consultation_context(
            concern=(
                "病名を診断してほしいです。"
            )
        )
    )

    assert (
        result[
            "safety"
        ][
            "warnings"
        ]
    )


# ============================================================
# 13. Financial safety
# ============================================================


def test_financial_safety_detected():
    result = (
        analyze_consultation_safety(
            concern=(
                "この株を買うべきか"
                "教えてください。"
            ),
            desired_future="",
        )
    )

    assert (
        result[
            "financial_decision_caution"
        ]
        is True
    )


def test_financial_warning_exists():
    result = (
        build_consultation_context(
            concern=(
                "この投資をすべきか"
                "判断してください。"
            )
        )
    )

    assert (
        result[
            "safety"
        ][
            "financial_decision_caution"
        ]
        is True
    )


# ============================================================
# 14. Certainty safety
# ============================================================


@pytest.mark.parametrize(
    "text",
    (
        "絶対に転職すべきですか？",
        "必ず結婚できますか？",
        "確実に成功できますか？",
        "100%稼げますか？",
        "未来を断言してください。",
    ),
)
def test_certainty_markers_detected(
    text,
):
    result = (
        analyze_consultation_safety(
            concern=text,
            desired_future="",
        )
    )

    assert (
        result[
            "certainty_caution"
        ]
        is True
    )


# ============================================================
# 15. AI usage policy
# ============================================================


def test_ai_usage_policy_focus_only():
    policy = (
        build_ai_usage_policy()
    )

    assert (
        policy[
            "consultation_role"
        ]
        == "focus_only"
    )


def test_ai_usage_policy_astrology_source_of_facts():
    policy = (
        build_ai_usage_policy()
    )

    assert (
        policy[
            "astrology_is_source_of_facts"
        ]
        is True
    )


@pytest.mark.parametrize(
    "key",
    (
        "consultation_may_change_astrology",
        "consultation_may_change_pillars",
        "consultation_may_change_day_master",
        "consultation_may_change_strength",
        "consultation_may_change_pattern",
        "consultation_may_change_useful_gods",
        "consultation_may_change_luck",
    ),
)
def test_ai_policy_never_changes_astrology(
    key,
):
    policy = (
        build_ai_usage_policy()
    )

    assert (
        policy[
            key
        ]
        is False
    )


def test_customer_concern_not_evidence():
    policy = (
        build_ai_usage_policy()
    )

    assert (
        policy[
            "customer_concern_is_not_evidence"
        ]
        is True
    )


def test_customer_desire_not_evidence():
    policy = (
        build_ai_usage_policy()
    )

    assert (
        policy[
            "customer_desire_is_not_evidence"
        ]
        is True
    )


# ============================================================
# 16. Core safety invariants
# ============================================================


def test_context_never_recalculates_astrology(
    career_context,
):
    assert (
        career_context[
            "recalculates_astrology"
        ]
        is False
    )


def test_context_never_rewrites_chart_facts(
    career_context,
):
    assert (
        career_context[
            "rewrites_chart_facts"
        ]
        is False
    )


def test_source_astrology_is_reading_context(
    career_context,
):
    assert (
        career_context[
            "source"
        ][
            "astrology_source"
        ]
        == "reading_context"
    )


# ============================================================
# 17. Instructions
# ============================================================


def test_instructions_non_empty(
    career_context,
):
    assert isinstance(
        career_context[
            "instructions"
        ],
        list,
    )

    assert (
        career_context[
            "instructions"
        ]
    )


def test_instructions_forbid_fact_rewrite(
    career_context,
):
    joined = "\n".join(
        career_context[
            "instructions"
        ]
    )

    assert (
        "変更しない"
        in joined
    )


def test_instructions_forbid_certainty(
    career_context,
):
    joined = "\n".join(
        career_context[
            "instructions"
        ]
    )

    assert (
        "断言しない"
        in joined
    )


def test_build_consultation_instructions_medical():
    result = (
        build_consultation_instructions(
            has_input=True,
            primary_focus="health",
            relevant_sections=[
                "health",
                "advice",
            ],
            safety={
                "medical_decision_caution": (
                    True
                ),
                "financial_decision_caution": (
                    False
                ),
                "certainty_caution": (
                    False
                ),
            },
        )
    )

    joined = "\n".join(
        result
    )

    assert (
        "医学的診断"
        in joined
    )


# ============================================================
# 18. Input limits
# ============================================================


def test_concern_exact_limit_allowed():
    concern = (
        "あ"
        * MAX_CONCERN_CHARS
    )

    result = (
        validate_consultation_input(
            concern=concern,
            desired_future="",
        )
    )

    assert (
        result[
            "valid"
        ]
        is True
    )


def test_concern_over_limit_rejected():
    concern = (
        "あ"
        * (
            MAX_CONCERN_CHARS
            + 1
        )
    )

    with pytest.raises(
        ValueError
    ):
        build_consultation_context(
            concern=concern
        )


def test_desired_future_over_limit_rejected():
    value = (
        "あ"
        * (
            MAX_DESIRED_FUTURE_CHARS
            + 1
        )
    )

    with pytest.raises(
        ValueError
    ):
        build_consultation_context(
            desired_future=value
        )


def test_combined_limit_rejected():
    concern = (
        "あ"
        * (
            MAX_COMBINED_CHARS
            // 2
            + 1
        )
    )

    desired = (
        "い"
        * (
            MAX_COMBINED_CHARS
            // 2
            + 1
        )
    )

    with pytest.raises(
        ValueError
    ):
        build_consultation_context(
            concern=concern,
            desired_future=desired,
        )


# ============================================================
# 19. Type validation
# ============================================================


@pytest.mark.parametrize(
    "bad_value",
    (
        123,
        [],
        {},
        True,
        1.5,
    ),
)
def test_concern_non_string_rejected(
    bad_value,
):
    with pytest.raises(
        TypeError
    ):
        build_consultation_context(
            concern=bad_value
        )


@pytest.mark.parametrize(
    "bad_value",
    (
        123,
        [],
        {},
        True,
        1.5,
    ),
)
def test_desired_future_non_string_rejected(
    bad_value,
):
    with pytest.raises(
        TypeError
    ):
        build_consultation_context(
            desired_future=bad_value
        )


def test_none_is_allowed():
    result = (
        build_consultation_context(
            concern=None,
            desired_future=None,
        )
    )

    assert (
        result[
            "has_consultation"
        ]
        is False
    )


# ============================================================
# 20. Whitespace normalization
# ============================================================


def test_whitespace_normalization():
    result = (
        build_consultation_context(
            concern=(
                "  仕事について   "
                "悩んでいます。  "
            ),
            desired_future="",
        )
    )

    assert (
        result[
            "input"
        ][
            "concern"
        ]
        == (
            "仕事について "
            "悩んでいます。"
        )
    )


def test_full_width_space_normalization():
    result = (
        build_consultation_context(
            concern=(
                "仕事について　"
                "悩んでいます。"
            ),
        )
    )

    assert (
        "\u3000"
        not in result[
            "input"
        ][
            "concern"
        ]
    )


# ============================================================
# 21. Context validation
# ============================================================


def test_validate_context_success(
    career_context,
):
    result = (
        validate_consultation_context(
            career_context
        )
    )

    assert (
        result[
            "valid"
        ]
        is True
    )


def test_validate_context_requires_mapping():
    with pytest.raises(
        TypeError
    ):
        validate_consultation_context(
            []
        )


def test_validate_context_missing_key():
    result = (
        build_consultation_context(
            concern="仕事の悩み"
        )
    )

    result.pop(
        "status"
    )

    with pytest.raises(
        ValueError
    ):
        validate_consultation_context(
            result
        )


def test_validate_context_wrong_version():
    result = (
        build_consultation_context()
    )

    result[
        "version"
    ] = "bad"

    with pytest.raises(
        ValueError
    ):
        validate_consultation_context(
            result
        )


def test_validate_context_recalculate_forbidden():
    result = (
        build_consultation_context()
    )

    result[
        "recalculates_astrology"
    ] = True

    with pytest.raises(
        ValueError
    ):
        validate_consultation_context(
            result
        )


def test_validate_context_rewrite_forbidden():
    result = (
        build_consultation_context()
    )

    result[
        "rewrites_chart_facts"
    ] = True

    with pytest.raises(
        ValueError
    ):
        validate_consultation_context(
            result
        )


# ============================================================
# 22. Compact context
# ============================================================


def test_compact_context_success(
    career_context,
):
    compact = (
        build_compact_consultation_context(
            career_context
        )
    )

    assert (
        compact[
            "primary_focus"
        ]
        == "career"
    )


def test_compact_context_preserves_concern(
    career_context,
):
    compact = (
        build_compact_consultation_context(
            career_context
        )
    )

    assert (
        compact[
            "concern"
        ]
        == career_context[
            "input"
        ][
            "concern"
        ]
    )


def test_compact_context_never_recalculates(
    career_context,
):
    compact = (
        build_compact_consultation_context(
            career_context
        )
    )

    assert (
        compact[
            "recalculates_astrology"
        ]
        is False
    )


def test_compact_context_never_rewrites(
    career_context,
):
    compact = (
        build_compact_consultation_context(
            career_context
        )
    )

    assert (
        compact[
            "rewrites_chart_facts"
        ]
        is False
    )


# ============================================================
# 23. Aliases
# ============================================================


def test_prepare_alias():
    direct = (
        build_consultation_context(
            concern=(
                "仕事で悩んでいます。"
            ),
            desired_future=(
                "安定したいです。"
            ),
        )
    )

    alias = (
        prepare_consultation_context(
            concern=(
                "仕事で悩んでいます。"
            ),
            desired_future=(
                "安定したいです。"
            ),
        )
    )

    assert alias == direct


def test_calculate_alias():
    direct = (
        build_consultation_context(
            concern=(
                "恋愛で悩んでいます。"
            ),
        )
    )

    alias = (
        calculate_consultation_context(
            concern=(
                "恋愛で悩んでいます。"
            ),
        )
    )

    assert alias == direct


# ============================================================
# 24. Metadata
# ============================================================


def test_metadata_version():
    metadata = (
        get_consultation_context_metadata()
    )

    assert (
        metadata[
            "version"
        ]
        == CONSULTATION_CONTEXT_VERSION
    )


def test_metadata_method():
    metadata = (
        get_consultation_context_metadata()
    )

    assert (
        metadata[
            "method"
        ]
        == CONSULTATION_CONTEXT_METHOD
    )


def test_metadata_status():
    metadata = (
        get_consultation_context_metadata()
    )

    assert (
        metadata[
            "status"
        ]
        == CONSULTATION_CONTEXT_STATUS
    )


def test_metadata_never_recalculates():
    metadata = (
        get_consultation_context_metadata()
    )

    assert (
        metadata[
            "recalculates_astrology"
        ]
        is False
    )


def test_metadata_never_rewrites():
    metadata = (
        get_consultation_context_metadata()
    )

    assert (
        metadata[
            "rewrites_chart_facts"
        ]
        is False
    )


def test_metadata_customer_concern_not_evidence():
    metadata = (
        get_consultation_context_metadata()
    )

    assert (
        metadata[
            "customer_concern_is_evidence"
        ]
        is False
    )


def test_metadata_customer_desire_not_evidence():
    metadata = (
        get_consultation_context_metadata()
    )

    assert (
        metadata[
            "customer_desire_is_evidence"
        ]
        is False
    )


# ============================================================
# 25. Immutability
# ============================================================


def test_build_relevant_sections_does_not_mutate():
    source = {
        "primary_focus": (
            "career"
        ),
        "detected_categories": [
            "career",
            "wealth",
        ],
    }

    before = deepcopy(
        source
    )

    build_relevant_sections(
        source
    )

    assert (
        source
        == before
    )


def test_compact_does_not_mutate_source(
    career_context,
):
    before = deepcopy(
        career_context
    )

    build_compact_consultation_context(
        career_context
    )

    assert (
        career_context
        == before
    )


# ============================================================
# 26. Customer example
# ============================================================


def test_customer_sample_case():
    result = (
        build_consultation_context(
            concern=(
                "現在の仕事をこのまま"
                "続けるべきか悩んでいます。"
                "収入面にも不安があり、"
                "副業や独立にも興味がありますが、"
                "自分にどのような仕事が"
                "向いているのか分かりません。"
            ),
            desired_future=(
                "自分の強みを活かせる仕事を見つけ、"
                "安定した収入を得ながら、"
                "将来的には自分の力で"
                "仕事を選べるようになりたいです。"
            ),
        )
    )

    assert (
        result[
            "focus"
        ][
            "primary"
        ]
        == "career"
    )

    assert (
        "wealth"
        in result[
            "focus"
        ][
            "detected_categories"
        ]
    )

    assert (
        "self_understanding"
        in result[
            "focus"
        ][
            "detected_categories"
        ]
    )

    assert (
        result[
            "recalculates_astrology"
        ]
        is False
    )

    assert (
        result[
            "rewrites_chart_facts"
        ]
        is False
    )


# ============================================================
# 27. Final gate
# ============================================================


def test_consultation_context_v1_final_gate():
    """
    consultation_context_v1 最終品質ゲート。
    """

    context = (
        build_consultation_context(
            concern=(
                "今の仕事を続けるか"
                "転職するか悩んでいます。"
                "収入にも不安があります。"
            ),
            desired_future=(
                "自分の強みを活かし、"
                "安定した収入を得たいです。"
            ),
        )
    )

    validation = (
        validate_consultation_context(
            context
        )
    )

    compact = (
        build_compact_consultation_context(
            context
        )
    )

    assert (
        validation[
            "valid"
        ]
        is True
    )

    assert (
        context[
            "version"
        ]
        == "consultation_context_v1"
    )

    assert (
        context[
            "method"
        ]
        == "consultation_context_v1"
    )

    assert (
        context[
            "status"
        ]
        == "ready_for_ai_reading"
    )

    assert (
        context[
            "has_consultation"
        ]
        is True
    )

    assert (
        context[
            "focus"
        ][
            "primary"
        ]
        == "career"
    )

    assert (
        "career"
        in context[
            "focus"
        ][
            "relevant_sections"
        ]
    )

    assert (
        "current_luck"
        in context[
            "focus"
        ][
            "relevant_sections"
        ]
    )

    assert (
        "future_flow"
        in context[
            "focus"
        ][
            "relevant_sections"
        ]
    )

    assert (
        context[
            "recalculates_astrology"
        ]
        is False
    )

    assert (
        context[
            "rewrites_chart_facts"
        ]
        is False
    )

    assert (
        context[
            "ai_usage_policy"
        ][
            "customer_concern_is_not_evidence"
        ]
        is True
    )

    assert (
        context[
            "ai_usage_policy"
        ][
            "customer_desire_is_not_evidence"
        ]
        is True
    )

    assert (
        context[
            "instructions"
        ]
    )

    assert (
        compact[
            "primary_focus"
        ]
        == "career"
    )

    assert (
        compact[
            "recalculates_astrology"
        ]
        is False
    )

    assert (
        compact[
            "rewrites_chart_facts"
        ]
        is False
    )