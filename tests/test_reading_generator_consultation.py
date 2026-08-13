"""
tests/test_reading_generator_consultation.py

consultation_context_v1
    ↓
reading_prompt_v1
    ↓
reading_generator_v1
    ↓
Fake OpenAI Responses API

の相談内容連動を検証する非LIVE統合テスト。

目的
----
1. consultation_context が OpenAI payload まで届く
2. 相談内容は user input に入り、system instructions を汚染しない
3. consultation_context=None なら従来動作と互換
4. text / json の両生成経路で相談情報が伝播する
5. convenience API / alias 群でも相談情報が伝播する
6. reading_context / consultation_context を変更しない
7. 顧客の思い込みで命式事実を書き換えない
8. 医療・金融・確実性の注意が payload に残る
9. 実際の OpenAI API は呼ばない

このテストは APIキー不要・課金なし・ネットワーク不要。
"""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime
from types import SimpleNamespace
from typing import Any

import pytest

from engine.chart import calculate_chart

from engine.consultation_context import (
    build_consultation_context,
)

from engine.reading_context import (
    build_reading_context,
)

from engine.reading_generator import (
    READING_GENERATOR_METHOD,
    READING_GENERATOR_STATUS,
    READING_GENERATOR_VERSION,
    ReadingGenerationResult,
    build_generation_payload,
    calculate_ai_reading,
    generate_reading,
    generate_reading_from_context,
    generate_reading_json,
    generate_reading_text,
    prepare_ai_generation_payload,
)


# ============================================================
# Constants
# ============================================================


TEST_MODEL = "test-model"

TARGET_DATETIME = datetime(
    2026,
    8,
    10,
    15,
    36,
)

EXPECTED_PILLARS = {
    "year": "乙丑",
    "month": "癸未",
    "day": "丁巳",
    "hour": "辛亥",
}

EXPECTED_DAY_MASTER = "丁"

READING_SECTIONS = (
    "core_personality",
    "career",
    "wealth",
    "relationships",
    "health",
    "current_luck",
    "future_flow",
    "advice",
)


# ============================================================
# Fake OpenAI Responses API
# ============================================================


class FakeResponses:
    """
    client.responses のfake。

    create()へ渡されたpayloadを保存する。
    """

    def __init__(
        self,
        response: Any,
    ):
        self.response = response
        self.calls = []

    def create(
        self,
        **kwargs,
    ):
        self.calls.append(
            deepcopy(
                kwargs
            )
        )

        return self.response


class FakeClient:
    """
    OpenAI client fake。
    """

    def __init__(
        self,
        response: Any,
    ):
        self.responses = FakeResponses(
            response
        )


class FakeUsage:
    input_tokens = 100
    output_tokens = 200
    total_tokens = 300


# ============================================================
# Real reading_context fixture
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
    実際の計算エンジンを使用して
    reading_context_v1を生成する。
    """

    chart_result = calculate_chart(
        make_request(),
        target_datetime=TARGET_DATETIME,
    )

    return build_reading_context(
        chart_result
    )


# ============================================================
# consultation_context fixtures
# ============================================================


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


@pytest.fixture
def medical_consultation():
    return build_consultation_context(
        concern=(
            "病名を診断して、"
            "治療をどうすべきか教えてください。"
        ),
        desired_future=(
            "健康に暮らしたいです。"
        ),
    )


@pytest.fixture
def certainty_consultation():
    return build_consultation_context(
        concern=(
            "転職すれば絶対成功しますか？"
        ),
        desired_future=(
            "必ず成功したいです。"
        ),
    )


# ============================================================
# Generated JSON fixture
# ============================================================


@pytest.fixture
def valid_generated_json():
    sections = {}

    for section in READING_SECTIONS:
        sections[
            section
        ] = {
            "title": section,
            "summary": (
                f"{section} summary"
            ),
            "detail": (
                f"{section} detail"
            ),
            "evidence": [
                "evidence 1",
            ],
            "advice": [
                "advice 1",
            ],
        }

    return {
        "summary": "全体要約",
        "sections": sections,
        "disclaimer": (
            "本鑑定は傾向を示すものであり、"
            "確定的な未来を保証するものではありません。"
        ),
    }


@pytest.fixture
def fake_text_response():
    return SimpleNamespace(
        id="resp_consultation_text",
        status="completed",
        output_text=(
            "これは相談内容連動の"
            "テスト用四柱推命鑑定文です。"
        ),
        usage=FakeUsage(),
    )


@pytest.fixture
def fake_json_response(
    valid_generated_json,
):
    return SimpleNamespace(
        id="resp_consultation_json",
        status="completed",
        output_text=json.dumps(
            valid_generated_json,
            ensure_ascii=False,
        ),
        usage=FakeUsage(),
    )


# ============================================================
# Helpers
# ============================================================


def payload_user_content(
    generation: dict,
) -> str:
    """
    build_generation_payload() が返した
    Responses API payloadのuser contentを取得する。
    """

    payload = generation[
        "payload"
    ]

    messages = payload[
        "input"
    ]

    assert len(
        messages
    ) == 1

    assert (
        messages[0][
            "role"
        ]
        == "user"
    )

    return messages[0][
        "content"
    ]


def call_user_content(
    client: FakeClient,
) -> str:
    """
    実際にFake Responses APIへ渡された
    user contentを取得する。
    """

    assert len(
        client.responses.calls
    ) == 1

    call = client.responses.calls[
        0
    ]

    messages = call[
        "input"
    ]

    assert len(
        messages
    ) == 1

    return messages[0][
        "content"
    ]


def actual_pillars(
    reading_context,
):
    pillars = (
        reading_context[
            "natal_chart"
        ][
            "pillars"
        ]
    )

    return {
        position: (
            pillars[
                position
            ][
                "pillar"
            ]
        )
        for position
        in (
            "year",
            "month",
            "day",
            "hour",
        )
    }


# ============================================================
# 1. Fixture sanity
# ============================================================


def test_real_reading_context_pillars(
    reading_context,
):
    assert (
        actual_pillars(
            reading_context
        )
        == EXPECTED_PILLARS
    )


def test_real_reading_context_day_master(
    reading_context,
):
    assert (
        reading_context[
            "day_master"
        ][
            "stem"
        ]
        == EXPECTED_DAY_MASTER
    )


def test_career_consultation_primary_focus(
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


# ============================================================
# 2. build_generation_payload
# ============================================================


def test_payload_contains_consultation_block(
    reading_context,
    career_consultation,
):
    generation = (
        build_generation_payload(
            reading_context,
            consultation_context=(
                career_consultation
            ),
            model=TEST_MODEL,
            output_format="text",
        )
    )

    content = payload_user_content(
        generation
    )

    assert "【相談内容】" in content


def test_payload_contains_concern(
    reading_context,
    career_consultation,
):
    generation = (
        build_generation_payload(
            reading_context,
            consultation_context=(
                career_consultation
            ),
            model=TEST_MODEL,
            output_format="text",
        )
    )

    content = payload_user_content(
        generation
    )

    assert (
        career_consultation[
            "input"
        ][
            "concern"
        ]
        in content
    )


def test_payload_contains_desired_future(
    reading_context,
    career_consultation,
):
    generation = (
        build_generation_payload(
            reading_context,
            consultation_context=(
                career_consultation
            ),
            model=TEST_MODEL,
            output_format="text",
        )
    )

    content = payload_user_content(
        generation
    )

    assert (
        career_consultation[
            "input"
        ][
            "desired_future"
        ]
        in content
    )


def test_payload_contains_primary_focus(
    reading_context,
    career_consultation,
):
    generation = (
        build_generation_payload(
            reading_context,
            consultation_context=(
                career_consultation
            ),
            model=TEST_MODEL,
            output_format="text",
        )
    )

    content = payload_user_content(
        generation
    )

    assert (
        '"primary_focus": "career"'
        in content
    )


def test_payload_contains_focus_only_guardrail(
    reading_context,
    career_consultation,
):
    generation = (
        build_generation_payload(
            reading_context,
            consultation_context=(
                career_consultation
            ),
            model=TEST_MODEL,
            output_format="text",
        )
    )

    content = payload_user_content(
        generation
    )

    assert (
        "四柱推命上の計算結果・根拠ではありません"
        in content
    )

    assert (
        "相談者の希望そのものを"
        "占術上の根拠にしない"
        in content
    )


def test_payload_keeps_system_guardrails(
    reading_context,
    career_consultation,
):
    generation = (
        build_generation_payload(
            reading_context,
            consultation_context=(
                career_consultation
            ),
            model=TEST_MODEL,
            output_format="text",
        )
    )

    instructions = (
        generation[
            "payload"
        ][
            "instructions"
        ]
    )

    assert (
        "再計算しない"
        in instructions
    )

    assert (
        "断定"
        in instructions
    )


def test_customer_consultation_not_in_system_instructions(
    reading_context,
    career_consultation,
):
    generation = (
        build_generation_payload(
            reading_context,
            consultation_context=(
                career_consultation
            ),
            model=TEST_MODEL,
            output_format="text",
        )
    )

    instructions = (
        generation[
            "payload"
        ][
            "instructions"
        ]
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
        not in instructions
    )


def test_payload_none_consultation_equals_legacy(
    reading_context,
):
    legacy = (
        build_generation_payload(
            reading_context,
            model=TEST_MODEL,
            output_format="text",
        )
    )

    explicit_none = (
        build_generation_payload(
            reading_context,
            consultation_context=None,
            model=TEST_MODEL,
            output_format="text",
        )
    )

    assert (
        explicit_none
        == legacy
    )


def test_empty_consultation_payload_equals_legacy(
    reading_context,
):
    empty = (
        build_consultation_context(
            concern="",
            desired_future="",
        )
    )

    legacy = (
        build_generation_payload(
            reading_context,
            model=TEST_MODEL,
            output_format="text",
        )
    )

    with_empty = (
        build_generation_payload(
            reading_context,
            consultation_context=empty,
            model=TEST_MODEL,
            output_format="text",
        )
    )

    assert (
        with_empty
        == legacy
    )


# ============================================================
# 3. Safety propagation
# ============================================================


def test_financial_safety_reaches_payload(
    reading_context,
    financial_consultation,
):
    generation = (
        build_generation_payload(
            reading_context,
            consultation_context=(
                financial_consultation
            ),
            model=TEST_MODEL,
            output_format="text",
        )
    )

    content = payload_user_content(
        generation
    )

    assert (
        '"financial_decision_caution": true'
        in content
    )

    assert (
        "利益を保証しない"
        in content
    )


def test_medical_safety_reaches_payload(
    reading_context,
    medical_consultation,
):
    generation = (
        build_generation_payload(
            reading_context,
            consultation_context=(
                medical_consultation
            ),
            model=TEST_MODEL,
            output_format="text",
        )
    )

    content = payload_user_content(
        generation
    )

    assert (
        '"medical_decision_caution": true'
        in content
    )

    assert (
        "医学的診断"
        in content
    )


def test_certainty_safety_reaches_payload(
    reading_context,
    certainty_consultation,
):
    generation = (
        build_generation_payload(
            reading_context,
            consultation_context=(
                certainty_consultation
            ),
            model=TEST_MODEL,
            output_format="text",
        )
    )

    content = payload_user_content(
        generation
    )

    assert (
        '"certainty_caution": true'
        in content
    )

    assert (
        "確定的に断言しない"
        in content
    )


# ============================================================
# 4. Text generation E2E
# ============================================================


def test_generate_reading_text_e2e(
    reading_context,
    career_consultation,
    fake_text_response,
):
    client = FakeClient(
        fake_text_response
    )

    result = generate_reading(
        reading_context,
        consultation_context=(
            career_consultation
        ),
        client=client,
        model=TEST_MODEL,
        output_format="text",
    )

    assert isinstance(
        result,
        ReadingGenerationResult,
    )

    assert (
        result.status
        == "completed"
    )

    assert (
        result.response_id
        == "resp_consultation_text"
    )

    content = call_user_content(
        client
    )

    assert "【相談内容】" in content


def test_generate_reading_text_e2e_contains_concern_in_api_call(
    reading_context,
    career_consultation,
    fake_text_response,
):
    client = FakeClient(
        fake_text_response
    )

    generate_reading(
        reading_context,
        consultation_context=(
            career_consultation
        ),
        client=client,
        model=TEST_MODEL,
        output_format="text",
    )

    content = call_user_content(
        client
    )

    assert (
        career_consultation[
            "input"
        ][
            "concern"
        ]
        in content
    )


def test_generate_reading_text_convenience(
    reading_context,
    career_consultation,
    fake_text_response,
):
    client = FakeClient(
        fake_text_response
    )

    result = generate_reading_text(
        reading_context,
        consultation_context=(
            career_consultation
        ),
        client=client,
        model=TEST_MODEL,
    )

    assert (
        result
        == (
            "これは相談内容連動の"
            "テスト用四柱推命鑑定文です。"
        )
    )

    assert (
        "【相談内容】"
        in call_user_content(
            client
        )
    )


# ============================================================
# 5. JSON generation E2E
# ============================================================


def test_generate_reading_json_e2e(
    reading_context,
    career_consultation,
    fake_json_response,
    valid_generated_json,
):
    client = FakeClient(
        fake_json_response
    )

    result = generate_reading(
        reading_context,
        consultation_context=(
            career_consultation
        ),
        client=client,
        model=TEST_MODEL,
        output_format="json",
    )

    assert (
        result.status
        == "completed"
    )

    assert (
        result.parsed
        == valid_generated_json
    )

    assert (
        "【相談内容】"
        in call_user_content(
            client
        )
    )


def test_json_api_call_keeps_json_schema(
    reading_context,
    career_consultation,
    fake_json_response,
):
    client = FakeClient(
        fake_json_response
    )

    generate_reading(
        reading_context,
        consultation_context=(
            career_consultation
        ),
        client=client,
        model=TEST_MODEL,
        output_format="json",
    )

    call = (
        client.responses.calls[
            0
        ]
    )

    assert (
        call[
            "text"
        ][
            "format"
        ][
            "type"
        ]
        == "json_schema"
    )

    assert (
        call[
            "text"
        ][
            "format"
        ][
            "strict"
        ]
        is True
    )


def test_generate_reading_json_convenience(
    reading_context,
    career_consultation,
    fake_json_response,
    valid_generated_json,
):
    client = FakeClient(
        fake_json_response
    )

    result = generate_reading_json(
        reading_context,
        consultation_context=(
            career_consultation
        ),
        client=client,
        model=TEST_MODEL,
    )

    assert (
        result
        == valid_generated_json
    )

    assert (
        "【相談内容】"
        in call_user_content(
            client
        )
    )


# ============================================================
# 6. Convenience APIs / aliases
# ============================================================


def test_generate_reading_from_context_passes_consultation(
    reading_context,
    career_consultation,
    fake_text_response,
):
    client = FakeClient(
        fake_text_response
    )

    result = generate_reading_from_context(
        reading_context,
        consultation_context=(
            career_consultation
        ),
        client=client,
        model=TEST_MODEL,
        output_format="text",
    )

    assert (
        result[
            "status"
        ]
        == "completed"
    )

    assert (
        "【相談内容】"
        in call_user_content(
            client
        )
    )


def test_calculate_ai_reading_passes_consultation(
    reading_context,
    career_consultation,
    fake_text_response,
):
    client = FakeClient(
        fake_text_response
    )

    result = calculate_ai_reading(
        reading_context,
        consultation_context=(
            career_consultation
        ),
        client=client,
        model=TEST_MODEL,
        output_format="text",
    )

    assert (
        result[
            "status"
        ]
        == "completed"
    )

    assert (
        "【相談内容】"
        in call_user_content(
            client
        )
    )


def test_prepare_ai_generation_payload_passes_consultation(
    reading_context,
    career_consultation,
):
    generation = (
        prepare_ai_generation_payload(
            reading_context,
            consultation_context=(
                career_consultation
            ),
            model=TEST_MODEL,
            output_format="text",
        )
    )

    assert (
        "【相談内容】"
        in payload_user_content(
            generation
        )
    )


# ============================================================
# 7. Sections
# ============================================================


@pytest.mark.parametrize(
    "section",
    READING_SECTIONS,
)
def test_each_section_accepts_consultation(
    reading_context,
    career_consultation,
    fake_text_response,
    section,
):
    client = FakeClient(
        fake_text_response
    )

    result = generate_reading(
        reading_context,
        consultation_context=(
            career_consultation
        ),
        client=client,
        model=TEST_MODEL,
        sections=[
            section,
        ],
        output_format="text",
    )

    assert (
        result.sections
        == (
            section,
        )
    )

    assert (
        "【相談内容】"
        in call_user_content(
            client
        )
    )


# ============================================================
# 8. Immutability
# ============================================================


def test_build_payload_does_not_mutate_reading_context(
    reading_context,
    career_consultation,
):
    before = deepcopy(
        reading_context
    )

    build_generation_payload(
        reading_context,
        consultation_context=(
            career_consultation
        ),
        model=TEST_MODEL,
        output_format="text",
    )

    assert (
        reading_context
        == before
    )


def test_build_payload_does_not_mutate_consultation_context(
    reading_context,
    career_consultation,
):
    before = deepcopy(
        career_consultation
    )

    build_generation_payload(
        reading_context,
        consultation_context=(
            career_consultation
        ),
        model=TEST_MODEL,
        output_format="text",
    )

    assert (
        career_consultation
        == before
    )


def test_generate_reading_does_not_mutate_reading_context(
    reading_context,
    career_consultation,
    fake_text_response,
):
    before = deepcopy(
        reading_context
    )

    generate_reading(
        reading_context,
        consultation_context=(
            career_consultation
        ),
        client=FakeClient(
            fake_text_response
        ),
        model=TEST_MODEL,
        output_format="text",
    )

    assert (
        reading_context
        == before
    )


def test_generate_reading_does_not_mutate_consultation_context(
    reading_context,
    career_consultation,
    fake_text_response,
):
    before = deepcopy(
        career_consultation
    )

    generate_reading(
        reading_context,
        consultation_context=(
            career_consultation
        ),
        client=FakeClient(
            fake_text_response
        ),
        model=TEST_MODEL,
        output_format="text",
    )

    assert (
        career_consultation
        == before
    )


# ============================================================
# 9. Astrology invariants
# ============================================================


def test_consultation_does_not_change_pillars(
    reading_context,
    career_consultation,
):
    before = actual_pillars(
        reading_context
    )

    build_generation_payload(
        reading_context,
        consultation_context=(
            career_consultation
        ),
        model=TEST_MODEL,
        output_format="text",
    )

    after = actual_pillars(
        reading_context
    )

    assert after == before


def test_consultation_does_not_change_day_master(
    reading_context,
    career_consultation,
):
    before = deepcopy(
        reading_context[
            "day_master"
        ]
    )

    build_generation_payload(
        reading_context,
        consultation_context=(
            career_consultation
        ),
        model=TEST_MODEL,
        output_format="text",
    )

    assert (
        reading_context[
            "day_master"
        ]
        == before
    )


@pytest.mark.parametrize(
    "key",
    (
        "strength",
        "pattern",
        "useful_gods",
        "luck",
    ),
)
def test_consultation_does_not_change_calculated_astrology(
    reading_context,
    career_consultation,
    key,
):
    before = deepcopy(
        reading_context[
            key
        ]
    )

    build_generation_payload(
        reading_context,
        consultation_context=(
            career_consultation
        ),
        model=TEST_MODEL,
        output_format="text",
    )

    assert (
        reading_context[
            key
        ]
        == before
    )


def test_wrong_customer_day_master_assumption_does_not_override_chart(
    reading_context,
):
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

    generation = (
        build_generation_payload(
            reading_context,
            consultation_context=(
                consultation
            ),
            model=TEST_MODEL,
            output_format="text",
        )
    )

    content = payload_user_content(
        generation
    )

    assert (
        "私は日主が甲だと思っています。"
        in content
    )

    assert (
        "相談者の希望そのものを"
        "占術上の根拠にしない"
        in content
    )

    assert (
        reading_context[
            "day_master"
        ][
            "stem"
        ]
        == EXPECTED_DAY_MASTER
    )

    assert (
        reading_context
        == before
    )


# ============================================================
# 10. Invalid consultation_context
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
        build_generation_payload(
            reading_context,
            consultation_context=(
                bad_value
            ),
            model=TEST_MODEL,
            output_format="text",
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
        build_generation_payload(
            reading_context,
            consultation_context=broken,
            model=TEST_MODEL,
            output_format="text",
        )


def test_consultation_recalculation_true_rejected(
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
        build_generation_payload(
            reading_context,
            consultation_context=broken,
            model=TEST_MODEL,
            output_format="text",
        )


def test_consultation_rewrite_true_rejected(
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
        build_generation_payload(
            reading_context,
            consultation_context=broken,
            model=TEST_MODEL,
            output_format="text",
        )


# ============================================================
# 11. Generator identity / compatibility
# ============================================================


def test_generator_version_kept():
    assert (
        READING_GENERATOR_VERSION
        == "reading_generator_v1"
    )


def test_generator_method_kept():
    assert (
        READING_GENERATOR_METHOD
        == "openai_responses_api_v1"
    )


def test_generator_status_kept():
    assert (
        READING_GENERATOR_STATUS
        == "ready_for_ai_generation"
    )


def test_payload_generator_identity_kept(
    reading_context,
    career_consultation,
):
    generation = (
        build_generation_payload(
            reading_context,
            consultation_context=(
                career_consultation
            ),
            model=TEST_MODEL,
            output_format="text",
        )
    )

    assert (
        generation[
            "method"
        ]
        == READING_GENERATOR_METHOD
    )

    assert (
        generation[
            "status"
        ]
        == "request_ready"
    )


# ============================================================
# 12. Final gate
# ============================================================


def test_reading_generator_consultation_v1_final_gate(
    reading_context,
    career_consultation,
    fake_json_response,
    valid_generated_json,
):
    """
    consultation_context_v1
        ↓
    reading_prompt_v1
        ↓
    reading_generator_v1
        ↓
    Fake OpenAI Responses API

    の最終品質ゲート。
    """

    before_reading = deepcopy(
        reading_context
    )

    before_consultation = deepcopy(
        career_consultation
    )

    client = FakeClient(
        fake_json_response
    )

    result = generate_reading(
        reading_context,
        consultation_context=(
            career_consultation
        ),
        client=client,
        model=TEST_MODEL,
        output_format="json",
    )

    assert isinstance(
        result,
        ReadingGenerationResult,
    )

    assert (
        result.status
        == "completed"
    )

    assert (
        result.output_format
        == "json"
    )

    assert (
        result.parsed
        == valid_generated_json
    )

    assert (
        result.response_id
        == "resp_consultation_json"
    )

    assert (
        result.method
        == READING_GENERATOR_METHOD
    )

    call = (
        client.responses.calls[
            0
        ]
    )

    assert (
        call[
            "model"
        ]
        == TEST_MODEL
    )

    assert (
        call[
            "store"
        ]
        is False
    )

    assert (
        call[
            "text"
        ][
            "format"
        ][
            "type"
        ]
        == "json_schema"
    )

    user_content = call[
        "input"
    ][0][
        "content"
    ]

    assert (
        "【相談内容】"
        in user_content
    )

    assert (
        career_consultation[
            "input"
        ][
            "concern"
        ]
        in user_content
    )

    assert (
        career_consultation[
            "input"
        ][
            "desired_future"
        ]
        in user_content
    )

    assert (
        '"primary_focus": "career"'
        in user_content
    )

    assert (
        "相談者の希望そのものを"
        "占術上の根拠にしない"
        in user_content
    )

    assert (
        "計算結果を変更しない"
        in user_content
    )

    assert (
        actual_pillars(
            reading_context
        )
        == EXPECTED_PILLARS
    )

    assert (
        reading_context[
            "day_master"
        ][
            "stem"
        ]
        == EXPECTED_DAY_MASTER
    )

    assert (
        reading_context
        == before_reading
    )

    assert (
        career_consultation
        == before_consultation
    )
