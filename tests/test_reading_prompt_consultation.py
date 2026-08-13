"""
tests/test_reading_prompt_consultation.py

reading_prompt.py と consultation_context_v1 の
接続契約を固定する非LIVEテスト。

重要
----
このテストでは fake の reading_context を手書きしない。

実際の
    calculate_chart()
        ↓
    build_reading_context()
を通して reading_context_v1 を生成する。

これにより reading_prompt.py が要求する、

- schema_version
- subject
- natal_chart
- day_master
- five_elements
- strength
- pattern
- useful_gods
- luck
- reading_sections
- source_metadata
- method
- status

という正式構造と常に整合させる。

OpenAI APIは呼ばない。
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from types import SimpleNamespace

import pytest

from engine.chart import calculate_chart

from engine.consultation_context import (
    build_consultation_context,
)

from engine.reading_context import (
    build_reading_context,
)

from engine.reading_prompt import (
    DEFAULT_READING_SECTIONS,
    READING_PROMPT_METHOD,
    READING_PROMPT_STATUS,
    READING_PROMPT_VERSION,
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
# Fixed real reading_context
# ============================================================


def make_request():
    return SimpleNamespace(
        birth_date="1985-07-17",
        birth_time="21:50",
        birth_place="石川県",
        gender="female",
    )


@pytest.fixture(scope="module")
def reading_context():
    """
    実際の計算エンジンから
    reading_context_v1を生成する。
    """

    chart_result = calculate_chart(
        make_request(),
        target_datetime=datetime(
            2026,
            8,
            10,
            15,
            36,
        ),
    )

    return build_reading_context(
        chart_result
    )


@pytest.fixture
def career_consultation():
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


@pytest.fixture
def financial_consultation():
    return build_consultation_context(
        concern=(
            "この投資をすべきか判断してください。"
        ),
        desired_future=(
            "資産を安定して増やしたいです。"
        ),
    )


# ============================================================
# 1. Base fixture sanity
# ============================================================


def test_real_reading_context_schema(
    reading_context,
):
    assert (
        reading_context[
            "schema_version"
        ]
        == "reading_context_v1"
    )


def test_real_reading_context_has_required_top_level(
    reading_context,
):
    required = {
        "schema_version",
        "subject",
        "natal_chart",
        "day_master",
        "five_elements",
        "strength",
        "pattern",
        "useful_gods",
        "luck",
        "reading_sections",
        "source_metadata",
        "method",
        "status",
    }

    assert required.issubset(
        reading_context.keys()
    )


def test_real_reading_context_has_four_pillars(
    reading_context,
):
    pillars = (
        reading_context[
            "natal_chart"
        ][
            "pillars"
        ]
    )

    assert set(
        pillars.keys()
    ) >= {
        "year",
        "month",
        "day",
        "hour",
    }


# ============================================================
# 2. Consultation block
# ============================================================


def test_consultation_block_contains_concern(
    career_consultation,
):
    block = (
        build_consultation_prompt_block(
            career_consultation
        )
    )

    assert (
        "今の仕事を続けるか転職するか悩んでいます。"
        in block
    )


def test_consultation_block_contains_desired_future(
    career_consultation,
):
    block = (
        build_consultation_prompt_block(
            career_consultation
        )
    )

    assert (
        "安定した収入を得たいです。"
        in block
    )


def test_consultation_block_contains_career_focus(
    career_consultation,
):
    block = (
        build_consultation_prompt_block(
            career_consultation
        )
    )

    assert (
        '"primary_focus": "career"'
        in block
    )


def test_consultation_block_marks_input_as_non_astrology_evidence(
    career_consultation,
):
    block = (
        build_consultation_prompt_block(
            career_consultation
        )
    )

    assert (
        "四柱推命上の計算結果・根拠ではありません"
        in block
    )


def test_consultation_block_forbids_recalculation(
    career_consultation,
):
    block = (
        build_consultation_prompt_block(
            career_consultation
        )
    )

    assert "再計算" in block
    assert "変更" in block
    assert "創作" in block


def test_consultation_block_forbids_customer_pleasing(
    career_consultation,
):
    block = (
        build_consultation_prompt_block(
            career_consultation
        )
    )

    assert (
        "相談者が望む結論へ迎合しない"
        in block
    )


def test_consultation_block_forbids_certainty(
    career_consultation,
):
    block = (
        build_consultation_prompt_block(
            career_consultation
        )
    )

    assert (
        "確定的に断言しない"
        in block
    )


def test_none_consultation_block_is_empty():
    assert (
        build_consultation_prompt_block(
            None
        )
        == ""
    )


def test_empty_consultation_block_is_empty():
    context = (
        build_consultation_context(
            concern="",
            desired_future="",
        )
    )

    assert (
        build_consultation_prompt_block(
            context
        )
        == ""
    )


# ============================================================
# 3. Safety propagation
# ============================================================


def test_financial_caution_is_in_block(
    financial_consultation,
):
    block = (
        build_consultation_prompt_block(
            financial_consultation
        )
    )

    assert (
        '"financial_decision_caution": true'
        in block
    )


def test_financial_safety_instruction_is_in_block(
    financial_consultation,
):
    block = (
        build_consultation_prompt_block(
            financial_consultation
        )
    )

    assert "投資" in block
    assert (
        "利益を保証しない"
        in block
    )


def test_medical_caution_is_in_block():
    context = (
        build_consultation_context(
            concern=(
                "病名を診断して、"
                "治療をどうすべきか教えてください。"
            ),
            desired_future=(
                "健康になりたいです。"
            ),
        )
    )

    block = (
        build_consultation_prompt_block(
            context
        )
    )

    assert (
        '"medical_decision_caution": true'
        in block
    )

    assert "医学的診断" in block


def test_certainty_caution_is_in_block():
    context = (
        build_consultation_context(
            concern=(
                "転職すれば絶対成功しますか？"
            ),
            desired_future=(
                "必ず成功したいです。"
            ),
        )
    )

    block = (
        build_consultation_prompt_block(
            context
        )
    )

    assert (
        '"certainty_caution": true'
        in block
    )

    assert "断定" in block


# ============================================================
# 4. build_user_prompt
# ============================================================


def test_user_prompt_contains_consultation(
    reading_context,
    career_consultation,
):
    prompt = build_user_prompt(
        reading_context,
        consultation_context=(
            career_consultation
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


def test_user_prompt_keeps_astrology_block(
    reading_context,
    career_consultation,
):
    prompt = build_user_prompt(
        reading_context,
        consultation_context=(
            career_consultation
        ),
    )

    assert (
        "【計算済みデータ】"
        in prompt
    )

    assert (
        "再計算・修正・置換をしない"
        in prompt
    )


def test_user_prompt_keeps_day_master_fact(
    reading_context,
    career_consultation,
):
    stem = (
        reading_context[
            "day_master"
        ][
            "stem"
        ]
    )

    prompt = build_user_prompt(
        reading_context,
        consultation_context=(
            career_consultation
        ),
    )

    assert stem in prompt


def test_legacy_user_prompt_has_no_consultation_block(
    reading_context,
):
    prompt = build_user_prompt(
        reading_context
    )

    assert (
        "【相談内容】"
        not in prompt
    )


def test_explicit_none_user_prompt_equals_legacy(
    reading_context,
):
    legacy = build_user_prompt(
        reading_context
    )

    explicit_none = (
        build_user_prompt(
            reading_context,
            consultation_context=None,
        )
    )

    assert explicit_none == legacy


def test_empty_consultation_user_prompt_equals_legacy(
    reading_context,
):
    empty = (
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
        consultation_context=empty,
    )

    assert with_empty == legacy


# ============================================================
# 5. Immutability
# ============================================================


def test_user_prompt_does_not_mutate_reading_context(
    reading_context,
    career_consultation,
):
    before = deepcopy(
        reading_context
    )

    build_user_prompt(
        reading_context,
        consultation_context=(
            career_consultation
        ),
    )

    assert (
        reading_context
        == before
    )


def test_user_prompt_does_not_mutate_consultation(
    reading_context,
    career_consultation,
):
    before = deepcopy(
        career_consultation
    )

    build_user_prompt(
        reading_context,
        consultation_context=(
            career_consultation
        ),
    )

    assert (
        career_consultation
        == before
    )


@pytest.mark.parametrize(
    "key",
    (
        "day_master",
        "strength",
        "pattern",
        "useful_gods",
        "luck",
    ),
)
def test_consultation_does_not_change_astrology_sections(
    reading_context,
    career_consultation,
    key,
):
    before = deepcopy(
        reading_context[
            key
        ]
    )

    build_user_prompt(
        reading_context,
        consultation_context=(
            career_consultation
        ),
    )

    assert (
        reading_context[
            key
        ]
        == before
    )


def test_consultation_does_not_change_pillars(
    reading_context,
    career_consultation,
):
    before = deepcopy(
        reading_context[
            "natal_chart"
        ][
            "pillars"
        ]
    )

    build_user_prompt(
        reading_context,
        consultation_context=(
            career_consultation
        ),
    )

    assert (
        reading_context[
            "natal_chart"
        ][
            "pillars"
        ]
        == before
    )


# ============================================================
# 6. Section prompt propagation
# ============================================================


@pytest.mark.parametrize(
    "section",
    DEFAULT_READING_SECTIONS,
)
def test_section_prompt_receives_consultation(
    reading_context,
    career_consultation,
    section,
):
    prompt = build_section_prompt(
        reading_context,
        section,
        consultation_context=(
            career_consultation
        ),
    )

    assert (
        "【相談内容】"
        in prompt
    )

    assert (
        "今の仕事を続けるか転職するか悩んでいます。"
        in prompt
    )


# ============================================================
# 7. Messages propagation
# ============================================================


def test_messages_put_consultation_in_user_message(
    reading_context,
    career_consultation,
):
    messages = build_messages(
        reading_context,
        consultation_context=(
            career_consultation
        ),
    )

    assert len(
        messages
    ) == 2

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


def test_messages_do_not_put_customer_text_in_system(
    reading_context,
    career_consultation,
):
    messages = build_messages(
        reading_context,
        consultation_context=(
            career_consultation
        ),
    )

    concern = (
        career_consultation[
            "input"
        ][
            "concern"
        ]
    )

    assert (
        concern
        not in messages[0][
            "content"
        ]
    )

    assert (
        concern
        in messages[1][
            "content"
        ]
    )


def test_messages_none_equals_legacy(
    reading_context,
):
    legacy = build_messages(
        reading_context
    )

    explicit_none = (
        build_messages(
            reading_context,
            consultation_context=None,
        )
    )

    assert explicit_none == legacy


# ============================================================
# 8. Reading request
# ============================================================


def test_reading_request_receives_consultation(
    reading_context,
    career_consultation,
):
    request = (
        build_reading_request(
            reading_context,
            consultation_context=(
                career_consultation
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


def test_reading_request_version_unchanged(
    reading_context,
    career_consultation,
):
    request = (
        build_reading_request(
            reading_context,
            consultation_context=(
                career_consultation
            ),
        )
    )

    assert (
        request[
            "version"
        ]
        == READING_PROMPT_VERSION
        == "reading_prompt_v1"
    )


def test_reading_request_method_unchanged(
    reading_context,
    career_consultation,
):
    request = (
        build_reading_request(
            reading_context,
            consultation_context=(
                career_consultation
            ),
        )
    )

    assert (
        request[
            "method"
        ]
        == READING_PROMPT_METHOD
        == "reading_prompt_v1"
    )


def test_reading_request_status_unchanged(
    reading_context,
    career_consultation,
):
    request = (
        build_reading_request(
            reading_context,
            consultation_context=(
                career_consultation
            ),
        )
    )

    assert (
        request[
            "status"
        ]
        == READING_PROMPT_STATUS
        == "ready_for_ai_generation"
    )


def test_reading_request_validation_still_valid(
    reading_context,
    career_consultation,
):
    request = (
        build_reading_request(
            reading_context,
            consultation_context=(
                career_consultation
            ),
        )
    )

    assert (
        request[
            "validation"
        ][
            "valid"
        ]
        is True
    )


def test_reading_request_none_equals_legacy(
    reading_context,
):
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
# 9. Compact request
# ============================================================


def test_compact_request_receives_consultation(
    reading_context,
    career_consultation,
):
    request = (
        build_compact_reading_request(
            reading_context,
            consultation_context=(
                career_consultation
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


def test_compact_request_version_unchanged(
    reading_context,
    career_consultation,
):
    request = (
        build_compact_reading_request(
            reading_context,
            consultation_context=(
                career_consultation
            ),
        )
    )

    assert (
        request[
            "version"
        ]
        == "reading_prompt_v1"
    )


# ============================================================
# 10. Compatibility aliases
# ============================================================


def test_calculate_alias_receives_consultation(
    reading_context,
    career_consultation,
):
    request = (
        calculate_reading_prompt(
            reading_context,
            consultation_context=(
                career_consultation
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


def test_prepare_messages_alias_receives_consultation(
    reading_context,
    career_consultation,
):
    messages = (
        prepare_ai_messages(
            reading_context,
            consultation_context=(
                career_consultation
            ),
        )
    )

    assert (
        "【相談内容】"
        in messages[1][
            "content"
        ]
    )


def test_prepare_request_alias_receives_consultation(
    reading_context,
    career_consultation,
):
    request = (
        prepare_ai_reading_request(
            reading_context,
            consultation_context=(
                career_consultation
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
# 11. Invalid consultation_context
# ============================================================


@pytest.mark.parametrize(
    "bad_value",
    (
        1,
        1.5,
        True,
        [],
        (),
        "consultation",
    ),
)
def test_non_mapping_consultation_rejected(
    reading_context,
    bad_value,
):
    with pytest.raises(
        (TypeError, ValueError)
    ):
        build_user_prompt(
            reading_context,
            consultation_context=(
                bad_value
            ),
        )


def test_invalid_consultation_version_rejected(
    reading_context,
    career_consultation,
):
    broken = deepcopy(
        career_consultation
    )

    broken[
        "version"
    ] = "bad_version"

    with pytest.raises(
        ValueError
    ):
        build_user_prompt(
            reading_context,
            consultation_context=broken,
        )


def test_recalculation_flag_true_rejected(
    reading_context,
    career_consultation,
):
    broken = deepcopy(
        career_consultation
    )

    broken[
        "recalculates_astrology"
    ] = True

    with pytest.raises(
        ValueError
    ):
        build_user_prompt(
            reading_context,
            consultation_context=broken,
        )


def test_rewrite_flag_true_rejected(
    reading_context,
    career_consultation,
):
    broken = deepcopy(
        career_consultation
    )

    broken[
        "rewrites_chart_facts"
    ] = True

    with pytest.raises(
        ValueError
    ):
        build_user_prompt(
            reading_context,
            consultation_context=broken,
        )


# ============================================================
# 12. Customer assumption must not override chart
# ============================================================


def test_customer_wrong_day_master_assumption_keeps_real_chart(
    reading_context,
):
    real_stem = (
        reading_context[
            "day_master"
        ][
            "stem"
        ]
    )

    consultation = (
        build_consultation_context(
            concern=(
                "私は日主が甲だと思っています。"
                "甲として鑑定してください。"
            ),
            desired_future=(
                "木の性質を活かしたいです。"
            ),
        )
    )

    before = deepcopy(
        reading_context
    )

    prompt = build_user_prompt(
        reading_context,
        consultation_context=(
            consultation
        ),
    )

    assert (
        "私は日主が甲だと思っています。"
        in prompt
    )

    assert (
        "相談者の希望そのものを"
        "占術上の根拠にしない"
        in prompt
    )

    assert (
        reading_context[
            "day_master"
        ][
            "stem"
        ]
        == real_stem
    )

    assert (
        reading_context
        == before
    )


# ============================================================
# 13. Focus mapping
# ============================================================


def test_career_focus_priority(
    career_consultation,
):
    assert (
        career_consultation[
            "focus"
        ][
            "primary"
        ]
        == "career"
    )

    assert (
        "career"
        in career_consultation[
            "focus"
        ][
            "priority_sections"
        ]
    )


def test_self_understanding_does_not_force_relationships():
    consultation = (
        build_consultation_context(
            concern=(
                "自分の強みと才能を知りたいです。"
            ),
            desired_future=(
                "自分らしい生き方を見つけたいです。"
            ),
        )
    )

    assert (
        "relationships"
        not in consultation[
            "focus"
        ][
            "priority_sections"
        ]
    )


# ============================================================
# 14. Final gate
# ============================================================


def test_reading_prompt_consultation_v1_final_gate(
    reading_context,
    career_consultation,
):
    before_reading = deepcopy(
        reading_context
    )

    before_consultation = deepcopy(
        career_consultation
    )

    request = (
        build_reading_request(
            reading_context,
            consultation_context=(
                career_consultation
            ),
            output_format="json",
        )
    )

    assert (
        request[
            "version"
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
        == "ready_for_ai_generation"
    )

    assert (
        request[
            "validation"
        ][
            "valid"
        ]
        is True
    )

    assert (
        request[
            "output_schema"
        ]
        is not None
    )

    user_prompt = (
        request[
            "messages"
        ][1][
            "content"
        ]
    )

    assert (
        "【相談内容】"
        in user_prompt
    )

    assert (
        "今の仕事を続けるか転職するか悩んでいます。"
        in user_prompt
    )

    assert (
        "安定した収入を得たいです。"
        in user_prompt
    )

    assert (
        "相談者の希望そのものを"
        "占術上の根拠にしない"
        in user_prompt
    )

    assert (
        "入力された計算結果を変更しない"
        in user_prompt
    )

    assert (
        reading_context
        == before_reading
    )

    assert (
        career_consultation
        == before_consultation
    )
