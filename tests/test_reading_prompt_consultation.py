"""
tests/test_reading_prompt_consultation.py

reading_prompt.py と consultation_context_v1 の
接続契約を固定するテスト。

目的
----
1. 相談内容が user prompt に反映されること
2. 相談なしでは従来の prompt と互換であること
3. 相談内容が命式事実を書き換えないこと
4. consultation_context の安全指示が prompt に入ること
5. build_section_prompt / build_messages /
   build_reading_request / alias 群まで相談情報が伝播すること
6. 不正な consultation_context を拒否すること

このテストは OpenAI API を呼ばない。
"""

from __future__ import annotations

from copy import deepcopy

import pytest

from engine.consultation_context import (
    build_consultation_context,
)
from engine.reading_prompt import (
    DEFAULT_READING_SECTIONS,
    build_compact_reading_request,
    build_consultation_prompt_block,
    build_messages,
    build_reading_request,
    build_section_prompt,
    build_user_prompt,
    calculate_reading_prompt,
    prepare_ai_messages,
    prepare_ai_reading_request,
)


# ============================================================
# Test data
# ============================================================


def make_reading_context() -> dict:
    """
    reading_prompt が必要とする代表的な
    reading_context_v1 相当のテストデータ。

    既存 reading_prompt の入力契約に合わせ、
    prompt構築に必要な主要キーを持たせる。
    """

    return {
        "version": "reading_context_v1",
        "chart": {
            "pillars": {
                "year": {
                    "stem": "庚",
                    "branch": "午",
                    "ganzhi": "庚午",
                },
                "month": {
                    "stem": "辛",
                    "branch": "巳",
                    "ganzhi": "辛巳",
                },
                "day": {
                    "stem": "庚",
                    "branch": "辰",
                    "ganzhi": "庚辰",
                },
                "hour": {
                    "stem": "癸",
                    "branch": "未",
                    "ganzhi": "癸未",
                },
            },
            "day_master": "庚",
        },
        "day_master": "庚",
        "strength": {
            "label": "身強",
            "score": 60.0,
            "status": "calculated",
        },
        "pattern": {
            "name": "建禄格",
            "status": "calculated",
        },
        "useful_gods": {
            "primary": ["火"],
            "secondary": ["木"],
            "status": "calculated",
        },
        "five_elements": {
            "wood": 1,
            "fire": 2,
            "earth": 2,
            "metal": 3,
            "water": 1,
        },
        "ten_gods": {
            "summary": {
                "比肩": 1,
                "劫財": 1,
                "食神": 1,
            },
        },
        "twelve_stages": {
            "year": "沐浴",
            "month": "長生",
            "day": "養",
            "hour": "冠帯",
        },
        "major_luck": {
            "status": "calculated",
            "current": {
                "ganzhi": "甲申",
            },
        },
        "annual_luck": {
            "status": "calculated",
            "current": {
                "year": 2026,
                "ganzhi": "丙午",
            },
        },
        "calculation_rules": {
            "day_boundary": "00:00",
        },
        "metadata": {
            "recalculates_astrology": False,
            "ai_rewrites_chart_facts": False,
        },
    }


def make_consultation_context() -> dict:
    return build_consultation_context(
        concern=(
            "今の仕事を続けるか転職するか悩んでいます。"
            "収入にも不安があります。"
        ),
        desired_future=(
            "自分の強みを活かして"
            "安定した収入を得たいです。"
        ),
    )


def make_financial_consultation_context() -> dict:
    return build_consultation_context(
        concern=(
            "この投資をすべきか判断してください。"
        ),
        desired_future=(
            "資産を安定して増やしたいです。"
        ),
    )


# ============================================================
# Consultation block
# ============================================================


def test_consultation_prompt_block_contains_concern():
    context = make_consultation_context()

    block = build_consultation_prompt_block(
        context
    )

    assert (
        "今の仕事を続けるか転職するか悩んでいます。"
        in block
    )


def test_consultation_prompt_block_contains_desired_future():
    context = make_consultation_context()

    block = build_consultation_prompt_block(
        context
    )

    assert (
        "安定した収入を得たいです。"
        in block
    )


def test_consultation_prompt_block_contains_primary_focus():
    context = make_consultation_context()

    block = build_consultation_prompt_block(
        context
    )

    assert '"primary_focus": "career"' in block


def test_consultation_prompt_block_says_focus_only():
    context = make_consultation_context()

    block = build_consultation_prompt_block(
        context
    )

    assert (
        "重点的に説明するか"
        in block
    )

    assert (
        "四柱推命上の計算結果・根拠ではありません"
        in block
    )


def test_consultation_prompt_block_forbids_recalculation():
    context = make_consultation_context()

    block = build_consultation_prompt_block(
        context
    )

    assert "再計算" in block
    assert "変更" in block
    assert "創作" in block


def test_consultation_prompt_block_forbids_customer_pleasing():
    context = make_consultation_context()

    block = build_consultation_prompt_block(
        context
    )

    assert (
        "相談者が望む結論へ迎合しない"
        in block
    )


def test_consultation_prompt_block_forbids_certainty():
    context = make_consultation_context()

    block = build_consultation_prompt_block(
        context
    )

    assert "確定的に断言しない" in block


def test_consultation_prompt_block_none_is_empty():
    assert (
        build_consultation_prompt_block(
            None
        )
        == ""
    )


def test_consultation_prompt_block_empty_input_is_empty():
    context = build_consultation_context(
        concern="",
        desired_future="",
    )

    assert (
        build_consultation_prompt_block(
            context
        )
        == ""
    )


# ============================================================
# Safety
# ============================================================


def test_financial_consultation_safety_is_in_prompt():
    context = (
        make_financial_consultation_context()
    )

    block = build_consultation_prompt_block(
        context
    )

    assert (
        '"financial_decision_caution": true'
        in block
    )


def test_financial_consultation_instruction_is_in_prompt():
    context = (
        make_financial_consultation_context()
    )

    block = build_consultation_prompt_block(
        context
    )

    assert "投資" in block
    assert "利益を保証しない" in block


def test_medical_consultation_safety_is_in_prompt():
    context = build_consultation_context(
        concern=(
            "病名を診断して、"
            "治療をどうすべきか教えてください。"
        ),
        desired_future=(
            "健康になりたいです。"
        ),
    )

    block = build_consultation_prompt_block(
        context
    )

    assert (
        '"medical_decision_caution": true'
        in block
    )

    assert "医学的診断" in block


def test_certainty_consultation_safety_is_in_prompt():
    context = build_consultation_context(
        concern=(
            "転職すれば絶対成功しますか？"
        ),
        desired_future=(
            "必ず成功したいです。"
        ),
    )

    block = build_consultation_prompt_block(
        context
    )

    assert (
        '"certainty_caution": true'
        in block
    )

    assert "断定" in block


# ============================================================
# build_user_prompt
# ============================================================


def test_user_prompt_contains_consultation():
    reading_context = (
        make_reading_context()
    )

    consultation_context = (
        make_consultation_context()
    )

    prompt = build_user_prompt(
        reading_context,
        consultation_context=(
            consultation_context
        ),
    )

    assert "【相談内容】" in prompt

    assert (
        "今の仕事を続けるか転職するか悩んでいます。"
        in prompt
    )

    assert (
        "安定した収入を得たいです。"
        in prompt
    )


def test_user_prompt_still_contains_astrology_facts():
    reading_context = (
        make_reading_context()
    )

    consultation_context = (
        make_consultation_context()
    )

    prompt = build_user_prompt(
        reading_context,
        consultation_context=(
            consultation_context
        ),
    )

    # reading_context由来の事実が
    # promptから消えていないこと。
    assert "庚" in prompt
    assert "庚午" in prompt
    assert "辛巳" in prompt
    assert "庚辰" in prompt
    assert "癸未" in prompt


def test_user_prompt_without_consultation_has_no_consultation_block():
    reading_context = (
        make_reading_context()
    )

    prompt = build_user_prompt(
        reading_context
    )

    assert "【相談内容】" not in prompt


def test_user_prompt_none_consultation_equals_legacy_call():
    reading_context = (
        make_reading_context()
    )

    legacy = build_user_prompt(
        reading_context
    )

    explicit_none = build_user_prompt(
        reading_context,
        consultation_context=None,
    )

    assert explicit_none == legacy


def test_user_prompt_empty_consultation_equals_legacy_call():
    reading_context = (
        make_reading_context()
    )

    empty_consultation = (
        build_consultation_context(
            concern="",
            desired_future="",
        )
    )

    legacy = build_user_prompt(
        reading_context
    )

    with_empty = build_user_prompt(
        reading_context,
        consultation_context=(
            empty_consultation
        ),
    )

    assert with_empty == legacy


# ============================================================
# No mutation / no astrology rewrite
# ============================================================


def test_build_user_prompt_does_not_mutate_reading_context():
    reading_context = (
        make_reading_context()
    )

    original = deepcopy(
        reading_context
    )

    build_user_prompt(
        reading_context,
        consultation_context=(
            make_consultation_context()
        ),
    )

    assert reading_context == original


def test_build_user_prompt_does_not_mutate_consultation_context():
    consultation_context = (
        make_consultation_context()
    )

    original = deepcopy(
        consultation_context
    )

    build_user_prompt(
        make_reading_context(),
        consultation_context=(
            consultation_context
        ),
    )

    assert (
        consultation_context
        == original
    )


def test_consultation_does_not_change_reading_context_day_master():
    reading_context = (
        make_reading_context()
    )

    original_day_master = (
        reading_context[
            "day_master"
        ]
    )

    consultation_context = (
        build_consultation_context(
            concern=(
                "私は木の性質だと思います。"
                "その前提で鑑定してください。"
            ),
            desired_future=(
                "木の才能を活かしたいです。"
            ),
        )
    )

    build_user_prompt(
        reading_context,
        consultation_context=(
            consultation_context
        ),
    )

    assert (
        reading_context[
            "day_master"
        ]
        == original_day_master
    )


def test_consultation_does_not_change_chart_pillars():
    reading_context = (
        make_reading_context()
    )

    original_pillars = deepcopy(
        reading_context[
            "chart"
        ][
            "pillars"
        ]
    )

    build_user_prompt(
        reading_context,
        consultation_context=(
            make_consultation_context()
        ),
    )

    assert (
        reading_context[
            "chart"
        ][
            "pillars"
        ]
        == original_pillars
    )


def test_consultation_does_not_change_strength():
    reading_context = (
        make_reading_context()
    )

    original_strength = deepcopy(
        reading_context[
            "strength"
        ]
    )

    build_user_prompt(
        reading_context,
        consultation_context=(
            make_consultation_context()
        ),
    )

    assert (
        reading_context[
            "strength"
        ]
        == original_strength
    )


def test_consultation_does_not_change_pattern():
    reading_context = (
        make_reading_context()
    )

    original_pattern = deepcopy(
        reading_context[
            "pattern"
        ]
    )

    build_user_prompt(
        reading_context,
        consultation_context=(
            make_consultation_context()
        ),
    )

    assert (
        reading_context[
            "pattern"
        ]
        == original_pattern
    )


def test_consultation_does_not_change_useful_gods():
    reading_context = (
        make_reading_context()
    )

    original_useful_gods = deepcopy(
        reading_context[
            "useful_gods"
        ]
    )

    build_user_prompt(
        reading_context,
        consultation_context=(
            make_consultation_context()
        ),
    )

    assert (
        reading_context[
            "useful_gods"
        ]
        == original_useful_gods
    )


# ============================================================
# Section prompt
# ============================================================


@pytest.mark.parametrize(
    "section",
    DEFAULT_READING_SECTIONS,
)
def test_section_prompt_receives_consultation(
    section: str,
):
    prompt = build_section_prompt(
        make_reading_context(),
        section,
        consultation_context=(
            make_consultation_context()
        ),
    )

    assert "【相談内容】" in prompt

    assert (
        "今の仕事を続けるか転職するか悩んでいます。"
        in prompt
    )


# ============================================================
# Messages
# ============================================================


def test_build_messages_passes_consultation_to_user_message():
    messages = build_messages(
        make_reading_context(),
        consultation_context=(
            make_consultation_context()
        ),
    )

    assert len(messages) == 2

    assert (
        messages[0][
            "role"
        ]
        == "system"
    )

    assert (
        messages[1][
            "role"
        ]
        == "user"
    )

    assert (
        "【相談内容】"
        in messages[1][
            "content"
        ]
    )


def test_build_messages_does_not_put_consultation_in_system_message():
    messages = build_messages(
        make_reading_context(),
        consultation_context=(
            make_consultation_context()
        ),
    )

    assert (
        "今の仕事を続けるか転職するか悩んでいます。"
        not in messages[0][
            "content"
        ]
    )

    assert (
        "今の仕事を続けるか転職するか悩んでいます。"
        in messages[1][
            "content"
        ]
    )


def test_build_messages_none_consultation_equals_legacy():
    reading_context = (
        make_reading_context()
    )

    legacy = build_messages(
        reading_context
    )

    explicit_none = build_messages(
        reading_context,
        consultation_context=None,
    )

    assert explicit_none == legacy


# ============================================================
# Reading request
# ============================================================


def test_build_reading_request_passes_consultation():
    request = build_reading_request(
        make_reading_context(),
        consultation_context=(
            make_consultation_context()
        ),
    )

    assert (
        "【相談内容】"
        in request[
            "messages"
        ][1][
            "content"
        ]
    )


def test_build_reading_request_keeps_schema_version():
    request = build_reading_request(
        make_reading_context(),
        consultation_context=(
            make_consultation_context()
        ),
    )

    assert (
        request[
            "schema_version"
        ]
        == "reading_prompt_v1"
    )


def test_build_reading_request_keeps_method():
    request = build_reading_request(
        make_reading_context(),
        consultation_context=(
            make_consultation_context()
        ),
    )

    assert (
        request[
            "method"
        ]
        == "reading_prompt_v1"
    )


def test_build_reading_request_keeps_status():
    request = build_reading_request(
        make_reading_context(),
        consultation_context=(
            make_consultation_context()
        ),
    )

    assert (
        request[
            "status"
        ]
        == "ready_for_ai"
    )


def test_build_reading_request_still_forbids_recalculation():
    request = build_reading_request(
        make_reading_context(),
        consultation_context=(
            make_consultation_context()
        ),
    )

    assert (
        request[
            "recalculates_astrology"
        ]
        is False
    )


def test_build_reading_request_still_forbids_chart_rewrite():
    request = build_reading_request(
        make_reading_context(),
        consultation_context=(
            make_consultation_context()
        ),
    )

    assert (
        request[
            "ai_rewrites_chart_facts"
        ]
        is False
    )


def test_build_reading_request_none_consultation_equals_legacy():
    reading_context = (
        make_reading_context()
    )

    legacy = build_reading_request(
        reading_context
    )

    explicit_none = (
        build_reading_request(
            reading_context,
            consultation_context=None,
        )
    )

    assert explicit_none == legacy


# ============================================================
# Compact request
# ============================================================


def test_compact_request_passes_consultation():
    request = (
        build_compact_reading_request(
            make_reading_context(),
            consultation_context=(
                make_consultation_context()
            ),
        )
    )

    assert (
        "【相談内容】"
        in request[
            "user_prompt"
        ]
    )


def test_compact_request_keeps_no_recalculation():
    request = (
        build_compact_reading_request(
            make_reading_context(),
            consultation_context=(
                make_consultation_context()
            ),
        )
    )

    assert (
        request[
            "recalculates_astrology"
        ]
        is False
    )


# ============================================================
# Compatibility aliases
# ============================================================


def test_calculate_reading_prompt_passes_consultation():
    request = calculate_reading_prompt(
        make_reading_context(),
        consultation_context=(
            make_consultation_context()
        ),
    )

    assert (
        "【相談内容】"
        in request[
            "messages"
        ][1][
            "content"
        ]
    )


def test_prepare_ai_messages_passes_consultation():
    messages = prepare_ai_messages(
        make_reading_context(),
        consultation_context=(
            make_consultation_context()
        ),
    )

    assert (
        "【相談内容】"
        in messages[1][
            "content"
        ]
    )


def test_prepare_ai_reading_request_passes_consultation():
    request = (
        prepare_ai_reading_request(
            make_reading_context(),
            consultation_context=(
                make_consultation_context()
            ),
        )
    )

    assert (
        "【相談内容】"
        in request[
            "messages"
        ][1][
            "content"
        ]
    )


# ============================================================
# Invalid consultation_context
# ============================================================


@pytest.mark.parametrize(
    "invalid_context",
    [
        1,
        1.5,
        True,
        [],
        (),
        "consultation",
    ],
)
def test_rejects_non_mapping_consultation_context(
    invalid_context,
):
    with pytest.raises(
        (TypeError, ValueError)
    ):
        build_user_prompt(
            make_reading_context(),
            consultation_context=(
                invalid_context
            ),
        )


def test_rejects_invalid_consultation_version():
    context = make_consultation_context()

    context[
        "version"
    ] = "invalid_version"

    with pytest.raises(
        ValueError
    ):
        build_user_prompt(
            make_reading_context(),
            consultation_context=context,
        )


def test_rejects_consultation_that_recalculates_astrology():
    context = make_consultation_context()

    context[
        "recalculates_astrology"
    ] = True

    with pytest.raises(
        ValueError
    ):
        build_user_prompt(
            make_reading_context(),
            consultation_context=context,
        )


def test_rejects_consultation_that_rewrites_chart_facts():
    context = make_consultation_context()

    context[
        "rewrites_chart_facts"
    ] = True

    with pytest.raises(
        ValueError
    ):
        build_user_prompt(
            make_reading_context(),
            consultation_context=context,
        )


# ============================================================
# Focus behavior
# ============================================================


def test_career_consultation_has_career_priority():
    context = make_consultation_context()

    block = build_consultation_prompt_block(
        context
    )

    assert '"primary_focus": "career"' in block
    assert "career" in block
    assert "current_luck" in block
    assert "future_flow" in block
    assert "advice" in block


def test_self_understanding_does_not_force_relationships_in_prompt():
    context = build_consultation_context(
        concern=(
            "自分の強みと才能を知りたいです。"
        ),
        desired_future=(
            "自分らしい生き方を見つけたいです。"
        ),
    )

    assert (
        "relationships"
        not in context[
            "focus"
        ][
            "priority_sections"
        ]
    )


# ============================================================
# Consultation text must not become chart evidence
# ============================================================


def test_customer_assumption_is_present_only_as_consultation_text():
    reading_context = (
        make_reading_context()
    )

    consultation_context = (
        build_consultation_context(
            concern=(
                "私は日主が甲だと思っています。"
            ),
            desired_future=(
                "木の性質を活かしたいです。"
            ),
        )
    )

    prompt = build_user_prompt(
        reading_context,
        consultation_context=(
            consultation_context
        ),
    )

    # 顧客入力は相談文としては残す。
    assert (
        "私は日主が甲だと思っています。"
        in prompt
    )

    # 同時に、命式事実を変更してはならない
    # というガードレールも存在する。
    assert (
        "相談者の希望そのものを占術上の根拠にしない"
        in prompt
    )

    assert (
        "計算結果を変更しない"
        in prompt
    )


# ============================================================
# Final gate
# ============================================================


def test_reading_prompt_consultation_v1_final_gate():
    reading_context = (
        make_reading_context()
    )

    consultation_context = (
        make_consultation_context()
    )

    original_reading_context = deepcopy(
        reading_context
    )

    original_consultation_context = deepcopy(
        consultation_context
    )

    request = build_reading_request(
        reading_context,
        consultation_context=(
            consultation_context
        ),
    )

    assert (
        request[
            "schema_version"
        ]
        == "reading_prompt_v1"
    )

    assert (
        request[
            "method"
        ]
        == "reading_prompt_v1"
    )

    assert (
        request[
            "status"
        ]
        == "ready_for_ai"
    )

    assert (
        request[
            "recalculates_astrology"
        ]
        is False
    )

    assert (
        request[
            "ai_rewrites_chart_facts"
        ]
        is False
    )

    user_prompt = (
        request[
            "messages"
        ][1][
            "content"
        ]
    )

    assert "【相談内容】" in user_prompt

    assert (
        "今の仕事を続けるか転職するか悩んでいます。"
        in user_prompt
    )

    assert (
        "安定した収入を得たいです。"
        in user_prompt
    )

    assert (
        "相談者の希望そのものを占術上の根拠にしない"
        in user_prompt
    )

    assert (
        "計算結果を変更しない"
        in user_prompt
    )

    assert (
        reading_context
        == original_reading_context
    )

    assert (
        consultation_context
        == original_consultation_context
    )
