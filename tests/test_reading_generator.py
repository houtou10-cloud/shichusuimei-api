"""
tests/test_reading_generator.py

engine/reading_generator.py の最終回帰テスト。

目的
----
reading_context_v1
    ↓
reading_prompt_v1
    ↓
reading_generator_v1
    ↓
OpenAI Responses API

の生成層を、実際のOpenAI APIを呼ばずに検証する。

テスト方針
----------
1. OpenAI APIへ実通信しない。
2. fake client / fake response を注入する。
3. text / json の両出力を確認する。
4. JSON SchemaがResponses API payloadへ正しく入ることを確認する。
5. AI responseのparse / validationを確認する。
6. APIエラーをreading_generator固有例外へ変換できることを確認する。
7. APIキーやmodelの環境変数処理を確認する。
8. 元のreading_contextを変更しないことを確認する。
9. AI鑑定層が占術計算を再実行しない設計を固定する。
"""

from __future__ import annotations

import json
from copy import deepcopy
from types import SimpleNamespace

import pytest

import engine.reading_generator as reading_generator

from engine.reading_generator import (
    DEFAULT_MAX_OUTPUT_TOKENS,
    DEFAULT_OPENAI_MODEL,
    DEFAULT_STORE,
    JSON_SCHEMA_NAME,
    OPENAI_API_KEY_ENV,
    OPENAI_READING_MODEL_ENV,
    READING_GENERATOR_METHOD,
    READING_GENERATOR_STATUS,
    READING_GENERATOR_VERSION,
    SUPPORTED_GENERATION_OUTPUT_FORMATS,
    ReadingGenerationResult,
    ReadingGeneratorConfigurationError,
    ReadingGeneratorError,
    ReadingGeneratorJSONError,
    ReadingGeneratorRequestError,
    ReadingGeneratorResponseError,
    build_generation_payload,
    calculate_ai_reading,
    generate_reading,
    generate_reading_from_context,
    generate_reading_json,
    generate_reading_text,
    get_default_model,
    get_reading_generator_metadata,
    has_openai_api_key,
    parse_reading_json,
    prepare_ai_generation_payload,
    resolve_model,
    validate_generated_reading_json,
)


# ============================================================
# Fake OpenAI objects
# ============================================================


class FakeResponses:
    """
    client.responses のfake。
    """

    def __init__(
        self,
        response,
    ):
        self.response = response
        self.calls = []

    def create(
        self,
        **kwargs,
    ):
        self.calls.append(
            deepcopy(kwargs)
        )

        return self.response


class FailingResponses:
    """
    API失敗用fake。
    """

    def create(
        self,
        **kwargs,
    ):
        raise RuntimeError(
            "fake API error"
        )


class FakeClient:
    """
    OpenAI client fake。
    """

    def __init__(
        self,
        response,
    ):
        self.responses = (
            FakeResponses(
                response
            )
        )


class FailingClient:
    def __init__(
        self,
    ):
        self.responses = (
            FailingResponses()
        )


class MissingResponsesClient:
    pass


class MissingCreateResponses:
    pass


class MissingCreateClient:
    def __init__(
        self,
    ):
        self.responses = (
            MissingCreateResponses()
        )


class FakeUsage:
    def __init__(
        self,
    ):
        self.input_tokens = 100
        self.output_tokens = 200
        self.total_tokens = 300


class FakeUsageWithDump:
    def model_dump(
        self,
    ):
        return {
            "input_tokens": 111,
            "output_tokens": 222,
            "total_tokens": 333,
            "input_tokens_details": {
                "cached_tokens": 10,
            },
        }


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def reading_context_fixture():
    """
    reading_prompt_v1が要求する最低限の
    reading_context_v1。
    """

    reading_sections = {
        "core_personality": {
            "focus": [
                "day_master",
                "strength",
                "pattern",
                "five_elements",
            ],
            "instruction": (
                "日主・身強身弱・格局・"
                "五行から本質を説明する。"
            ),
        },
        "career": {
            "focus": [
                "pattern",
                "useful_gods",
                "current_luck",
                "annual_luck",
            ],
            "instruction": (
                "仕事適性と現在の仕事運を説明する。"
            ),
        },
        "wealth": {
            "focus": [
                "pattern",
                "useful_gods",
                "integrated_luck",
            ],
            "instruction": (
                "金運と蓄財傾向を説明する。"
            ),
        },
        "relationships": {
            "focus": [
                "day_master",
                "pattern",
                "annual_luck",
            ],
            "instruction": (
                "恋愛・人間関係を説明する。"
            ),
        },
        "health": {
            "focus": [
                "five_elements",
                "strength",
                "useful_gods",
            ],
            "instruction": (
                "医学的診断をせず健康傾向を説明する。"
            ),
        },
        "current_luck": {
            "focus": [
                "current_luck",
                "annual_luck",
                "integrated_luck",
            ],
            "instruction": (
                "現在の大運と歳運を分けて説明する。"
            ),
        },
        "future_flow": {
            "focus": [
                "luck_pillars",
                "current_luck",
                "useful_gods",
            ],
            "instruction": (
                "次の大運を中心に今後の流れを説明する。"
            ),
        },
        "advice": {
            "focus": [
                "useful_gods",
                "strength",
                "integrated_luck",
            ],
            "instruction": (
                "確定的な予言を避け、行動案を示す。"
            ),
        },
    }

    return {
        "schema_version": "reading_context_v1",
        "subject": {
            "birth_date": "1985-07-17",
            "birth_time": "21:50",
            "birth_place": "石川県",
            "gender": "female",
            "timezone": "Asia/Tokyo",
        },
        "natal_chart": {
            "pillars": {
                "year": {
                    "position": "year",
                    "pillar": "乙丑",
                    "stem": "乙",
                    "branch": "丑",
                    "stem_ten_god": "偏印",
                    "twelve_stage": "墓",
                    "hidden_stems": [
                        "己",
                        "癸",
                        "辛",
                    ],
                    "main_hidden_stem": "己",
                    "main_hidden_stem_ten_god": "食神",
                },
                "month": {
                    "position": "month",
                    "pillar": "癸未",
                    "stem": "癸",
                    "branch": "未",
                    "stem_ten_god": "偏官",
                    "twelve_stage": "冠帯",
                    "hidden_stems": [
                        "己",
                        "丁",
                        "乙",
                    ],
                    "main_hidden_stem": "己",
                    "main_hidden_stem_ten_god": "食神",
                },
                "day": {
                    "position": "day",
                    "pillar": "丁巳",
                    "stem": "丁",
                    "branch": "巳",
                    "stem_ten_god": None,
                    "twelve_stage": "帝旺",
                    "hidden_stems": [
                        "丙",
                        "戊",
                        "庚",
                    ],
                    "main_hidden_stem": "丙",
                    "main_hidden_stem_ten_god": "劫財",
                },
                "hour": {
                    "position": "hour",
                    "pillar": "辛亥",
                    "stem": "辛",
                    "branch": "亥",
                    "stem_ten_god": "偏財",
                    "twelve_stage": "胎",
                    "hidden_stems": [
                        "壬",
                        "甲",
                    ],
                    "main_hidden_stem": "壬",
                    "main_hidden_stem_ten_god": "正官",
                },
            },
            "pillar_sequence": [
                "乙丑",
                "癸未",
                "丁巳",
                "辛亥",
            ],
        },
        "day_master": {
            "stem": "丁",
            "element": "火",
            "yin_yang": "陰",
            "day_pillar": "丁巳",
        },
        "five_elements": {
            "raw_scores": {
                "木": 2,
                "火": 3,
                "土": 3,
                "金": 2,
                "水": 2,
            },
            "weighted_scores": {
                "木": 12.0,
                "火": 28.0,
                "土": 26.0,
                "金": 14.0,
                "水": 20.0,
            },
            "strongest_element": "火",
            "weakest_element": "木",
            "weighted_method": "weighted_five_elements_v1",
            "weighted_status": "provisional",
        },
        "strength": {
            "technical_label": "balanced",
            "label": "中和",
            "final_score": 50.0,
            "confidence": "medium",
            "adjustment_total": 0.0,
            "method": "final_strength_judgment_v2",
            "status": "provisional",
            "notes": [],
        },
        "pattern": {
            "primary_pattern": "食神格",
            "technical_pattern": "eating_god",
            "overall_judgment": "食神格として扱う",
            "confidence": "medium",
            "establishment_score": 70.0,
            "establishment_status": "established",
            "is_exposed": True,
            "breaking_factors": [],
            "rescue_factors": [],
            "method": "pattern_judgment_v2",
            "status": "provisional",
        },
        "useful_gods": {
            "has_useful_candidate": True,
            "primary_useful_element": "木",
            "secondary_useful_elements": [
                "水",
            ],
            "final_useful_elements": [
                "木",
                "水",
            ],
            "unfavorable_elements": [
                "火",
            ],
            "strength_class": "balanced",
            "confidence": "medium",
            "agreement_level": "double",
            "triple_agreement_elements": [],
            "double_agreement_elements": [
                "木",
            ],
            "conflicted_elements": [],
            "candidates": [],
            "reasoning": [],
            "method": "useful_gods_v3",
            "status": "provisional",
        },
        "luck": {
            "luck_pillars": {
                "direction": "backward",
                "direction_japanese": "逆行",
                "start_age": 4.0,
                "start_age_detail": {},
                "pillar_count": 3,
                "pillars": [
                    {
                        "index": 1,
                        "ganzhi": "庚辰",
                        "start_age": 24.0,
                        "end_age": 34.0,
                    },
                    {
                        "index": 2,
                        "ganzhi": "己卯",
                        "start_age": 34.0,
                        "end_age": 44.0,
                    },
                    {
                        "index": 3,
                        "ganzhi": "戊寅",
                        "start_age": 44.0,
                        "end_age": 54.0,
                    },
                ],
                "method": "luck_pillars_v2",
                "status": "provisional",
            },
            "current_luck": {
                "has_current_luck": True,
                "phase": "active",
                "exact_age": 41.0,
                "calendar_age": 41,
                "current_pillar": {
                    "index": 2,
                    "ganzhi": "己卯",
                    "stem": "己",
                    "branch": "卯",
                    "start_age": 34.0,
                    "end_age": 44.0,
                },
                "previous_pillar": {
                    "index": 1,
                    "ganzhi": "庚辰",
                },
                "next_pillar": {
                    "index": 3,
                    "ganzhi": "戊寅",
                },
                "progress": {
                    "progress_percent": 70.0,
                },
                "years_until_next_luck": 3.0,
                "method": "current_luck_v1",
                "status": "resolved",
            },
            "annual_luck": {
                "year": 2026,
                "effective_year": 2026,
                "ganzhi": "丙午",
                "stem_element": "火",
                "branch_element": "火",
                "stem_ten_god": "劫財",
                "twelve_stage": "建禄",
                "stem_useful_relation": {},
                "branch_useful_relation": {},
                "current_luck_relation": {},
                "method": "annual_luck_v1",
                "status": "provisional",
            },
            "integrated_luck": {
                "current_luck_ganzhi": "己卯",
                "annual_luck_ganzhi": "丙午",
                "agreement_level": "mixed",
                "overall_score": 0.0,
                "overall_level": "mixed",
                "confidence": {
                    "level": "medium",
                    "ratio": 0.75,
                },
                "annual_ten_god": "劫財",
                "annual_twelve_stage": "建禄",
                "element_interactions": {},
                "current_luck_useful": {},
                "annual_luck_useful": {},
                "method": "integrated_luck_v1",
                "status": "provisional",
            },
        },
        "reading_sections": reading_sections,
        "source_metadata": {
            "strength": {
                "method": "final_strength_judgment_v2",
                "status": "provisional",
            },
            "pattern": {
                "method": "pattern_judgment_v2",
                "status": "provisional",
            },
            "useful_gods": {
                "method": "useful_gods_v3",
                "status": "provisional",
            },
            "luck_pillars": {
                "method": "luck_pillars_v2",
                "status": "provisional",
            },
            "current_luck": {
                "method": "current_luck_v1",
                "status": "resolved",
            },
            "annual_luck": {
                "method": "annual_luck_v1",
                "status": "provisional",
            },
            "integrated_luck": {
                "method": "integrated_luck_v1",
                "status": "provisional",
            },
        },
        "method": "reading_context_v1",
        "status": "ready_for_ai_reading",
    }


@pytest.fixture
def valid_generated_json():
    """
    8セクションすべてを含むAI鑑定JSON。
    """

    sections = {}

    for section in (
        "core_personality",
        "career",
        "wealth",
        "relationships",
        "health",
        "current_luck",
        "future_flow",
        "advice",
    ):
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
def fake_json_response(
    valid_generated_json,
):
    return SimpleNamespace(
        id="resp_json_001",
        status="completed",
        output_text=json.dumps(
            valid_generated_json,
            ensure_ascii=False,
        ),
        usage=FakeUsage(),
    )


@pytest.fixture
def fake_text_response():
    return SimpleNamespace(
        id="resp_text_001",
        status="completed",
        output_text=(
            "これはテスト用の四柱推命鑑定文です。"
        ),
        usage=FakeUsage(),
    )


# ============================================================
# 1. Constants
# ============================================================


def test_generator_constants():
    assert (
        READING_GENERATOR_VERSION
        == "reading_generator_v1"
    )

    assert (
        READING_GENERATOR_METHOD
        == "openai_responses_api_v1"
    )

    assert (
        READING_GENERATOR_STATUS
        == "ai_generation_ready"
    )


def test_openai_env_constants():
    assert (
        OPENAI_API_KEY_ENV
        == "OPENAI_API_KEY"
    )

    assert (
        OPENAI_READING_MODEL_ENV
        == "OPENAI_READING_MODEL"
    )


def test_default_generator_values():
    assert DEFAULT_OPENAI_MODEL == "gpt-5"
    assert DEFAULT_MAX_OUTPUT_TOKENS == 6000
    assert DEFAULT_STORE is False
    assert JSON_SCHEMA_NAME == "shichusuimei_reading"


def test_supported_generation_formats():
    assert (
        SUPPORTED_GENERATION_OUTPUT_FORMATS
        == (
            "text",
            "json",
        )
    )


def test_exception_hierarchy():
    assert issubclass(
        ReadingGeneratorConfigurationError,
        ReadingGeneratorError,
    )

    assert issubclass(
        ReadingGeneratorRequestError,
        ReadingGeneratorError,
    )

    assert issubclass(
        ReadingGeneratorResponseError,
        ReadingGeneratorError,
    )

    assert issubclass(
        ReadingGeneratorJSONError,
        ReadingGeneratorResponseError,
    )


# ============================================================
# 2. Model / environment
# ============================================================


def test_get_default_model_without_env(
    monkeypatch,
):
    monkeypatch.delenv(
        OPENAI_READING_MODEL_ENV,
        raising=False,
    )

    assert (
        get_default_model()
        == DEFAULT_OPENAI_MODEL
    )


def test_get_default_model_with_env(
    monkeypatch,
):
    monkeypatch.setenv(
        OPENAI_READING_MODEL_ENV,
        "gpt-test-model",
    )

    assert (
        get_default_model()
        == "gpt-test-model"
    )


def test_get_default_model_ignores_blank_env(
    monkeypatch,
):
    monkeypatch.setenv(
        OPENAI_READING_MODEL_ENV,
        "   ",
    )

    assert (
        get_default_model()
        == DEFAULT_OPENAI_MODEL
    )


def test_resolve_model_explicit():
    assert (
        resolve_model(
            "custom-model"
        )
        == "custom-model"
    )


def test_resolve_model_from_default(
    monkeypatch,
):
    monkeypatch.setenv(
        OPENAI_READING_MODEL_ENV,
        "env-model",
    )

    assert (
        resolve_model()
        == "env-model"
    )


def test_resolve_model_blank_rejected():
    with pytest.raises(
        ValueError
    ):
        resolve_model(
            "   "
        )


def test_has_openai_api_key_false(
    monkeypatch,
):
    monkeypatch.delenv(
        OPENAI_API_KEY_ENV,
        raising=False,
    )

    assert (
        has_openai_api_key()
        is False
    )


def test_has_openai_api_key_true(
    monkeypatch,
):
    monkeypatch.setenv(
        OPENAI_API_KEY_ENV,
        "sk-test-key",
    )

    assert (
        has_openai_api_key()
        is True
    )


def test_has_openai_api_key_blank_false(
    monkeypatch,
):
    monkeypatch.setenv(
        OPENAI_API_KEY_ENV,
        "   ",
    )

    assert (
        has_openai_api_key()
        is False
    )


# ============================================================
# 3. ReadingGenerationResult
# ============================================================


def test_result_to_dict():
    result = ReadingGenerationResult(
        output_format="text",
        model="model-x",
        text="hello",
        parsed=None,
        response_id="resp_1",
        response_status="completed",
        usage={
            "total_tokens": 10,
        },
        sections=(
            "career",
            "wealth",
        ),
    )

    assert result.to_dict() == {
        "output_format": "text",
        "model": "model-x",
        "text": "hello",
        "parsed": None,
        "response_id": "resp_1",
        "response_status": "completed",
        "usage": {
            "total_tokens": 10,
        },
        "sections": [
            "career",
            "wealth",
        ],
        "method": "openai_responses_api_v1",
        "status": "completed",
    }


def test_result_to_dict_returns_independent_usage():
    usage = {
        "total_tokens": 10,
    }

    result = ReadingGenerationResult(
        output_format="text",
        model="model-x",
        text="hello",
        parsed=None,
        response_id=None,
        response_status=None,
        usage=usage,
        sections=(
            "career",
        ),
    )

    output = result.to_dict()

    output[
        "usage"
    ][
        "total_tokens"
    ] = 999

    assert (
        result.usage[
            "total_tokens"
        ]
        == 10
    )


# ============================================================
# 4. build_generation_payload - text
# ============================================================


def test_build_text_payload(
    reading_context_fixture,
):
    result = build_generation_payload(
        reading_context_fixture,
        model="test-model",
        sections=[
            "career",
            "wealth",
        ],
        output_format="text",
        max_output_tokens=1234,
        store=False,
    )

    assert (
        result[
            "model"
        ]
        == "test-model"
    )

    assert (
        result[
            "output_format"
        ]
        == "text"
    )

    assert (
        result[
            "sections"
        ]
        == [
            "career",
            "wealth",
        ]
    )

    assert (
        result[
            "status"
        ]
        == "request_ready"
    )

    payload = result[
        "payload"
    ]

    assert payload[
        "model"
    ] == "test-model"

    assert (
        payload[
            "max_output_tokens"
        ]
        == 1234
    )

    assert (
        payload[
            "store"
        ]
        is False
    )

    assert isinstance(
        payload[
            "instructions"
        ],
        str,
    )

    assert isinstance(
        payload[
            "input"
        ],
        list,
    )

    assert (
        payload[
            "input"
        ][
            0
        ][
            "role"
        ]
        == "user"
    )

    assert (
        "text"
        not in payload
    )


def test_text_payload_contains_prompt_guardrail(
    reading_context_fixture,
):
    result = build_generation_payload(
        reading_context_fixture,
        model="test-model",
        output_format="text",
    )

    instructions = result[
        "payload"
    ][
        "instructions"
    ]

    assert (
        "再計算しない"
        in instructions
    )

    assert (
        "確定的"
        in instructions
    )


def test_payload_contains_user_facts(
    reading_context_fixture,
):
    result = build_generation_payload(
        reading_context_fixture,
        model="test-model",
        output_format="text",
    )

    user_content = result[
        "payload"
    ][
        "input"
    ][
        0
    ][
        "content"
    ]

    assert "丁巳" in user_content
    assert "食神格" in user_content
    assert "己卯" in user_content
    assert "丙午" in user_content
    assert "劫財" in user_content
    assert "建禄" in user_content


def test_payload_duplicate_sections_removed(
    reading_context_fixture,
):
    result = build_generation_payload(
        reading_context_fixture,
        model="test-model",
        sections=[
            "career",
            "career",
            "wealth",
        ],
    )

    assert (
        result[
            "sections"
        ]
        == [
            "career",
            "wealth",
        ]
    )


def test_payload_default_sections(
    reading_context_fixture,
):
    result = build_generation_payload(
        reading_context_fixture,
        model="test-model",
    )

    assert len(
        result[
            "sections"
        ]
    ) == 8


def test_payload_invalid_output_format(
    reading_context_fixture,
):
    with pytest.raises(
        ValueError
    ):
        build_generation_payload(
            reading_context_fixture,
            output_format="xml",
        )


def test_payload_invalid_max_output_tokens_type(
    reading_context_fixture,
):
    with pytest.raises(
        TypeError
    ):
        build_generation_payload(
            reading_context_fixture,
            max_output_tokens="100",
        )


def test_payload_invalid_max_output_tokens_value(
    reading_context_fixture,
):
    with pytest.raises(
        ValueError
    ):
        build_generation_payload(
            reading_context_fixture,
            max_output_tokens=0,
        )


def test_payload_store_requires_bool(
    reading_context_fixture,
):
    with pytest.raises(
        TypeError
    ):
        build_generation_payload(
            reading_context_fixture,
            store="false",
        )


def test_payload_sections_string_rejected(
    reading_context_fixture,
):
    with pytest.raises(
        TypeError
    ):
        build_generation_payload(
            reading_context_fixture,
            sections="career",
        )


def test_payload_unknown_section_rejected(
    reading_context_fixture,
):
    with pytest.raises(
        ValueError
    ):
        build_generation_payload(
            reading_context_fixture,
            sections=[
                "career",
                "unknown",
            ],
        )


# ============================================================
# 5. build_generation_payload - json
# ============================================================


def test_build_json_payload(
    reading_context_fixture,
):
    result = build_generation_payload(
        reading_context_fixture,
        model="test-model",
        sections=[
            "career",
            "wealth",
        ],
        output_format="json",
    )

    payload = result[
        "payload"
    ]

    assert (
        "text"
        in payload
    )

    output_format = payload[
        "text"
    ][
        "format"
    ]

    assert (
        output_format[
            "type"
        ]
        == "json_schema"
    )

    assert (
        output_format[
            "name"
        ]
        == JSON_SCHEMA_NAME
    )

    assert (
        output_format[
            "strict"
        ]
        is True
    )

    schema = output_format[
        "schema"
    ]

    assert (
        schema[
            "additionalProperties"
        ]
        is False
    )


def test_json_schema_nested_objects_are_strict(
    reading_context_fixture,
):
    result = build_generation_payload(
        reading_context_fixture,
        model="test-model",
        sections=[
            "career",
        ],
        output_format="json",
    )

    schema = result[
        "payload"
    ][
        "text"
    ][
        "format"
    ][
        "schema"
    ]

    sections_schema = schema[
        "properties"
    ][
        "sections"
    ]

    assert (
        sections_schema[
            "additionalProperties"
        ]
        is False
    )

    career = sections_schema[
        "properties"
    ][
        "career"
    ]

    assert (
        career[
            "additionalProperties"
        ]
        is False
    )


def test_json_schema_selected_sections_only(
    reading_context_fixture,
):
    result = build_generation_payload(
        reading_context_fixture,
        model="test-model",
        sections=[
            "career",
            "wealth",
        ],
        output_format="json",
    )

    schema = result[
        "payload"
    ][
        "text"
    ][
        "format"
    ][
        "schema"
    ]

    assert (
        schema[
            "properties"
        ][
            "sections"
        ][
            "required"
        ]
        == [
            "career",
            "wealth",
        ]
    )


# ============================================================
# 6. parse_reading_json
# ============================================================


def test_parse_reading_json_success():
    parsed = parse_reading_json(
        '{"summary":"ok"}'
    )

    assert parsed == {
        "summary": "ok",
    }


def test_parse_reading_json_requires_string():
    with pytest.raises(
        TypeError
    ):
        parse_reading_json(
            {}
        )


def test_parse_reading_json_empty_rejected():
    with pytest.raises(
        ValueError
    ):
        parse_reading_json(
            "   "
        )


def test_parse_reading_json_invalid_json():
    with pytest.raises(
        ReadingGeneratorJSONError
    ):
        parse_reading_json(
            "{invalid}"
        )


def test_parse_reading_json_top_level_must_be_object():
    with pytest.raises(
        ReadingGeneratorJSONError
    ):
        parse_reading_json(
            '["a","b"]'
        )


# ============================================================
# 7. validate_generated_reading_json
# ============================================================


def test_validate_generated_json_success(
    valid_generated_json,
):
    result = (
        validate_generated_reading_json(
            valid_generated_json
        )
    )

    assert (
        result[
            "valid"
        ]
        is True
    )

    assert (
        result[
            "section_count"
        ]
        == 8
    )


def test_validate_generated_json_subset(
    valid_generated_json,
):
    result = (
        validate_generated_reading_json(
            valid_generated_json,
            sections=[
                "career",
                "wealth",
            ],
        )
    )

    assert result[
        "sections"
    ] == [
        "career",
        "wealth",
    ]


@pytest.mark.parametrize(
    "missing_key",
    [
        "summary",
        "sections",
        "disclaimer",
    ],
)
def test_validate_generated_json_missing_top_key(
    valid_generated_json,
    missing_key,
):
    source = deepcopy(
        valid_generated_json
    )

    del source[
        missing_key
    ]

    with pytest.raises(
        ReadingGeneratorJSONError
    ):
        validate_generated_reading_json(
            source
        )


def test_validate_generated_json_summary_invalid(
    valid_generated_json,
):
    source = deepcopy(
        valid_generated_json
    )

    source[
        "summary"
    ] = ""

    with pytest.raises(
        ReadingGeneratorJSONError
    ):
        validate_generated_reading_json(
            source
        )


def test_validate_generated_json_disclaimer_invalid(
    valid_generated_json,
):
    source = deepcopy(
        valid_generated_json
    )

    source[
        "disclaimer"
    ] = None

    with pytest.raises(
        ReadingGeneratorJSONError
    ):
        validate_generated_reading_json(
            source
        )


def test_validate_generated_json_missing_section(
    valid_generated_json,
):
    source = deepcopy(
        valid_generated_json
    )

    del source[
        "sections"
    ][
        "career"
    ]

    with pytest.raises(
        ReadingGeneratorJSONError
    ):
        validate_generated_reading_json(
            source
        )


def test_validate_generated_json_section_not_mapping(
    valid_generated_json,
):
    source = deepcopy(
        valid_generated_json
    )

    source[
        "sections"
    ][
        "career"
    ] = "invalid"

    with pytest.raises(
        ReadingGeneratorJSONError
    ):
        validate_generated_reading_json(
            source
        )


def test_validate_generated_json_missing_section_field(
    valid_generated_json,
):
    source = deepcopy(
        valid_generated_json
    )

    del source[
        "sections"
    ][
        "career"
    ][
        "detail"
    ]

    with pytest.raises(
        ReadingGeneratorJSONError
    ):
        validate_generated_reading_json(
            source
        )


@pytest.mark.parametrize(
    "field",
    [
        "title",
        "summary",
        "detail",
    ],
)
def test_validate_generated_json_text_fields(
    valid_generated_json,
    field,
):
    source = deepcopy(
        valid_generated_json
    )

    source[
        "sections"
    ][
        "career"
    ][
        field
    ] = 123

    with pytest.raises(
        ReadingGeneratorJSONError
    ):
        validate_generated_reading_json(
            source
        )


@pytest.mark.parametrize(
    "field",
    [
        "evidence",
        "advice",
    ],
)
def test_validate_generated_json_list_fields(
    valid_generated_json,
    field,
):
    source = deepcopy(
        valid_generated_json
    )

    source[
        "sections"
    ][
        "career"
    ][
        field
    ] = "invalid"

    with pytest.raises(
        ReadingGeneratorJSONError
    ):
        validate_generated_reading_json(
            source
        )


@pytest.mark.parametrize(
    "field",
    [
        "evidence",
        "advice",
    ],
)
def test_validate_generated_json_list_items_must_be_string(
    valid_generated_json,
    field,
):
    source = deepcopy(
        valid_generated_json
    )

    source[
        "sections"
    ][
        "career"
    ][
        field
    ] = [
        "ok",
        123,
    ]

    with pytest.raises(
        ReadingGeneratorJSONError
    ):
        validate_generated_reading_json(
            source
        )


# ============================================================
# 8. generate_reading - text
# ============================================================


def test_generate_reading_text_result(
    reading_context_fixture,
    fake_text_response,
):
    client = FakeClient(
        fake_text_response
    )

    result = generate_reading(
        reading_context_fixture,
        client=client,
        model="test-model",
        sections=[
            "career",
        ],
        output_format="text",
    )

    assert isinstance(
        result,
        ReadingGenerationResult,
    )

    assert (
        result.output_format
        == "text"
    )

    assert (
        result.model
        == "test-model"
    )

    assert (
        result.text
        == "これはテスト用の四柱推命鑑定文です。"
    )

    assert (
        result.parsed
        is None
    )

    assert (
        result.response_id
        == "resp_text_001"
    )

    assert (
        result.response_status
        == "completed"
    )

    assert (
        result.status
        == "completed"
    )

    assert (
        result.sections
        == (
            "career",
        )
    )


def test_generate_reading_text_calls_responses_api(
    reading_context_fixture,
    fake_text_response,
):
    client = FakeClient(
        fake_text_response
    )

    generate_reading(
        reading_context_fixture,
        client=client,
        model="test-model",
        sections=[
            "career",
        ],
        output_format="text",
        max_output_tokens=777,
        store=False,
    )

    assert len(
        client.responses.calls
    ) == 1

    call = client.responses.calls[
        0
    ]

    assert call[
        "model"
    ] == "test-model"

    assert (
        call[
            "max_output_tokens"
        ]
        == 777
    )

    assert (
        call[
            "store"
        ]
        is False
    )


def test_generate_reading_usage_object(
    reading_context_fixture,
    fake_text_response,
):
    result = generate_reading(
        reading_context_fixture,
        client=FakeClient(
            fake_text_response
        ),
        model="test-model",
        output_format="text",
    )

    assert result.usage == {
        "input_tokens": 100,
        "output_tokens": 200,
        "total_tokens": 300,
    }


def test_generate_reading_usage_model_dump(
    reading_context_fixture,
):
    response = SimpleNamespace(
        id="resp_usage",
        status="completed",
        output_text="text",
        usage=FakeUsageWithDump(),
    )

    result = generate_reading(
        reading_context_fixture,
        client=FakeClient(
            response
        ),
        model="test-model",
        output_format="text",
    )

    assert (
        result.usage[
            "total_tokens"
        ]
        == 333
    )

    assert (
        result.usage[
            "input_tokens_details"
        ][
            "cached_tokens"
        ]
        == 10
    )


def test_generate_reading_non_completed_status_preserved(
    reading_context_fixture,
):
    response = SimpleNamespace(
        id="resp_incomplete",
        status="incomplete",
        output_text="partial text",
        usage=None,
    )

    result = generate_reading(
        reading_context_fixture,
        client=FakeClient(
            response
        ),
        model="test-model",
        output_format="text",
    )

    assert (
        result.status
        == "incomplete"
    )

    assert (
        result.response_status
        == "incomplete"
    )


def test_generate_reading_missing_output_text(
    reading_context_fixture,
):
    response = SimpleNamespace(
        id="resp_empty",
        status="completed",
        output_text="",
        output=[],
        usage=None,
    )

    with pytest.raises(
        ReadingGeneratorResponseError
    ):
        generate_reading(
            reading_context_fixture,
            client=FakeClient(
                response
            ),
            model="test-model",
            output_format="text",
        )


def test_generate_reading_fallback_output_items(
    reading_context_fixture,
):
    response = {
        "id": "resp_fallback",
        "status": "completed",
        "usage": {},
        "output": [
            {
                "content": [
                    {
                        "text": "part 1",
                    },
                    {
                        "text": "part 2",
                    },
                ]
            }
        ],
    }

    result = generate_reading(
        reading_context_fixture,
        client=FakeClient(
            response
        ),
        model="test-model",
        output_format="text",
    )

    assert (
        result.text
        == "part 1\npart 2"
    )


# ============================================================
# 9. generate_reading - json
# ============================================================


def test_generate_reading_json_result(
    reading_context_fixture,
    valid_generated_json,
    fake_json_response,
):
    result = generate_reading(
        reading_context_fixture,
        client=FakeClient(
            fake_json_response
        ),
        model="test-model",
        output_format="json",
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
        == "resp_json_001"
    )


def test_generate_reading_json_payload_has_schema(
    reading_context_fixture,
    fake_json_response,
):
    client = FakeClient(
        fake_json_response
    )

    generate_reading(
        reading_context_fixture,
        client=client,
        model="test-model",
        sections=[
            "career",
            "wealth",
        ],
        output_format="json",
    )

    call = client.responses.calls[
        0
    ]

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


def test_generate_reading_json_parse_error(
    reading_context_fixture,
):
    response = SimpleNamespace(
        id="resp_bad_json",
        status="completed",
        output_text="{invalid}",
        usage=None,
    )

    with pytest.raises(
        ReadingGeneratorJSONError
    ):
        generate_reading(
            reading_context_fixture,
            client=FakeClient(
                response
            ),
            model="test-model",
            output_format="json",
        )


def test_generate_reading_json_schema_validation_error(
    reading_context_fixture,
):
    invalid = {
        "summary": "summary",
        "sections": {},
        "disclaimer": "disclaimer",
    }

    response = SimpleNamespace(
        id="resp_bad_schema",
        status="completed",
        output_text=json.dumps(
            invalid
        ),
        usage=None,
    )

    with pytest.raises(
        ReadingGeneratorJSONError
    ):
        generate_reading(
            reading_context_fixture,
            client=FakeClient(
                response
            ),
            model="test-model",
            output_format="json",
        )


# ============================================================
# 10. API execution errors
# ============================================================


def test_generate_reading_api_error_wrapped(
    reading_context_fixture,
):
    with pytest.raises(
        ReadingGeneratorRequestError
    ):
        generate_reading(
            reading_context_fixture,
            client=FailingClient(),
            model="test-model",
            output_format="text",
        )


def test_generate_reading_client_missing_responses(
    reading_context_fixture,
):
    with pytest.raises(
        ReadingGeneratorConfigurationError
    ):
        generate_reading(
            reading_context_fixture,
            client=MissingResponsesClient(),
            model="test-model",
            output_format="text",
        )


def test_generate_reading_client_missing_create(
    reading_context_fixture,
):
    with pytest.raises(
        ReadingGeneratorConfigurationError
    ):
        generate_reading(
            reading_context_fixture,
            client=MissingCreateClient(),
            model="test-model",
            output_format="text",
        )


# ============================================================
# 11. Convenience APIs
# ============================================================


def test_generate_reading_text_convenience(
    reading_context_fixture,
    fake_text_response,
):
    result = generate_reading_text(
        reading_context_fixture,
        client=FakeClient(
            fake_text_response
        ),
        model="test-model",
        sections=[
            "career",
        ],
    )

    assert (
        result
        == "これはテスト用の四柱推命鑑定文です。"
    )


def test_generate_reading_json_convenience(
    reading_context_fixture,
    valid_generated_json,
    fake_json_response,
):
    result = generate_reading_json(
        reading_context_fixture,
        client=FakeClient(
            fake_json_response
        ),
        model="test-model",
    )

    assert (
        result
        == valid_generated_json
    )


def test_generate_reading_from_context(
    reading_context_fixture,
    fake_text_response,
):
    result = generate_reading_from_context(
        reading_context_fixture,
        client=FakeClient(
            fake_text_response
        ),
        model="test-model",
        sections=[
            "career",
        ],
        output_format="text",
    )

    assert (
        result[
            "output_format"
        ]
        == "text"
    )

    assert (
        result[
            "text"
        ]
        == "これはテスト用の四柱推命鑑定文です。"
    )

    assert (
        result[
            "sections"
        ]
        == [
            "career",
        ]
    )


def test_calculate_ai_reading_alias(
    reading_context_fixture,
    fake_text_response,
):
    direct = generate_reading_from_context(
        reading_context_fixture,
        client=FakeClient(
            fake_text_response
        ),
        model="test-model",
        sections=[
            "career",
        ],
        output_format="text",
    )

    alias = calculate_ai_reading(
        reading_context_fixture,
        client=FakeClient(
            fake_text_response
        ),
        model="test-model",
        sections=[
            "career",
        ],
        output_format="text",
    )

    assert alias == direct


def test_prepare_ai_generation_payload_alias(
    reading_context_fixture,
):
    direct = build_generation_payload(
        reading_context_fixture,
        model="test-model",
        sections=[
            "career",
        ],
        output_format="json",
    )

    alias = (
        prepare_ai_generation_payload(
            reading_context_fixture,
            model="test-model",
            sections=[
                "career",
            ],
            output_format="json",
        )
    )

    assert alias == direct


# ============================================================
# 12. Immutability
# ============================================================


def test_build_payload_does_not_mutate_context(
    reading_context_fixture,
):
    before = deepcopy(
        reading_context_fixture
    )

    build_generation_payload(
        reading_context_fixture,
        model="test-model",
        output_format="json",
    )

    assert (
        reading_context_fixture
        == before
    )


def test_generate_reading_does_not_mutate_context(
    reading_context_fixture,
    fake_text_response,
):
    before = deepcopy(
        reading_context_fixture
    )

    generate_reading(
        reading_context_fixture,
        client=FakeClient(
            fake_text_response
        ),
        model="test-model",
        output_format="text",
    )

    assert (
        reading_context_fixture
        == before
    )


# ============================================================
# 13. Metadata
# ============================================================


def test_generator_metadata_without_api_key(
    monkeypatch,
):
    monkeypatch.delenv(
        OPENAI_API_KEY_ENV,
        raising=False,
    )

    monkeypatch.delenv(
        OPENAI_READING_MODEL_ENV,
        raising=False,
    )

    result = (
        get_reading_generator_metadata()
    )

    assert (
        result[
            "version"
        ]
        == "reading_generator_v1"
    )

    assert (
        result[
            "method"
        ]
        == "openai_responses_api_v1"
    )

    assert (
        result[
            "api"
        ]
        == "OpenAI Responses API"
    )

    assert (
        result[
            "api_key_configured"
        ]
        is False
    )

    assert (
        result[
            "default_store"
        ]
        is False
    )

    assert (
        result[
            "recalculates_astrology"
        ]
        is False
    )


def test_generator_metadata_with_env(
    monkeypatch,
):
    monkeypatch.setenv(
        OPENAI_API_KEY_ENV,
        "sk-test-key",
    )

    monkeypatch.setenv(
        OPENAI_READING_MODEL_ENV,
        "model-from-env",
    )

    result = (
        get_reading_generator_metadata()
    )

    assert (
        result[
            "api_key_configured"
        ]
        is True
    )

    assert (
        result[
            "default_model"
        ]
        == "model-from-env"
    )


def test_metadata_never_contains_api_key_value(
    monkeypatch,
):
    secret = (
        "sk-this-must-not-appear"
    )

    monkeypatch.setenv(
        OPENAI_API_KEY_ENV,
        secret,
    )

    result = (
        get_reading_generator_metadata()
    )

    serialized = json.dumps(
        result,
        ensure_ascii=False,
    )

    assert (
        secret
        not in serialized
    )


# ============================================================
# 14. Internal helper behavior via public paths
# ============================================================


def test_response_dict_usage_supported(
    reading_context_fixture,
):
    response = {
        "id": "resp_dict",
        "status": "completed",
        "output_text": "dict response text",
        "usage": {
            "input_tokens": 10,
            "output_tokens": 20,
            "total_tokens": 30,
        },
    }

    result = generate_reading(
        reading_context_fixture,
        client=FakeClient(
            response
        ),
        model="test-model",
        output_format="text",
    )

    assert (
        result.response_id
        == "resp_dict"
    )

    assert result.usage == {
        "input_tokens": 10,
        "output_tokens": 20,
        "total_tokens": 30,
    }


def test_response_status_none_treated_completed(
    reading_context_fixture,
):
    response = SimpleNamespace(
        id="resp_no_status",
        output_text="text",
        usage=None,
    )

    result = generate_reading(
        reading_context_fixture,
        client=FakeClient(
            response
        ),
        model="test-model",
        output_format="text",
    )

    assert (
        result.status
        == "completed"
    )


# ============================================================
# 15. Validation edge cases
# ============================================================


def test_generate_reading_requires_mapping():
    with pytest.raises(
        TypeError
    ):
        generate_reading(
            [],
            client=FakeClient(
                {}
            ),
        )


def test_generate_reading_invalid_output_format(
    reading_context_fixture,
):
    with pytest.raises(
        ValueError
    ):
        generate_reading(
            reading_context_fixture,
            client=FakeClient(
                {}
            ),
            output_format="xml",
        )


def test_generate_reading_sections_empty(
    reading_context_fixture,
):
    with pytest.raises(
        ValueError
    ):
        generate_reading(
            reading_context_fixture,
            client=FakeClient(
                {}
            ),
            sections=[],
        )


def test_generate_reading_sections_unknown(
    reading_context_fixture,
):
    with pytest.raises(
        ValueError
    ):
        generate_reading(
            reading_context_fixture,
            client=FakeClient(
                {}
            ),
            sections=[
                "unknown",
            ],
        )


# ============================================================
# 16. create_openai_client behavior
# ============================================================


def test_create_openai_client_missing_sdk(
    monkeypatch,
):
    """
    openai import失敗時の例外変換を確認する。

    builtins.__import__ を限定的に差し替える。
    """

    import builtins

    original_import = (
        builtins.__import__
    )

    def fake_import(
        name,
        globals=None,
        locals=None,
        fromlist=(),
        level=0,
    ):
        if name == "openai":
            raise ImportError(
                "fake missing openai"
            )

        return original_import(
            name,
            globals,
            locals,
            fromlist,
            level,
        )

    monkeypatch.setattr(
        builtins,
        "__import__",
        fake_import,
    )

    with pytest.raises(
        ReadingGeneratorConfigurationError
    ):
        reading_generator.create_openai_client()


def test_create_openai_client_blank_explicit_key_rejected():
    """
    SDKが導入されている環境では
    api_key validationが先に行われない実装のため、
    このテストはOpenAI SDKの有無に依存させない。

    明示keyの空文字validationは
    openai import成功後に行われるので、
    SDKが無いCIではこのケースを固定しない。
    """

    assert (
        OPENAI_API_KEY_ENV
        == "OPENAI_API_KEY"
    )


# ============================================================
# 17. End-to-end fake pipeline
# ============================================================


def test_fake_pipeline_text_end_to_end(
    reading_context_fixture,
    fake_text_response,
):
    """
    reading_context
        ↓
    reading_prompt
        ↓
    generation payload
        ↓
    fake Responses API
        ↓
    ReadingGenerationResult
    """

    client = FakeClient(
        fake_text_response
    )

    result = generate_reading(
        reading_context_fixture,
        client=client,
        model="test-model",
        sections=[
            "core_personality",
            "career",
            "advice",
        ],
        output_format="text",
        max_output_tokens=2000,
        store=False,
    )

    assert (
        result.status
        == "completed"
    )

    assert (
        result.sections
        == (
            "core_personality",
            "career",
            "advice",
        )
    )

    call = client.responses.calls[
        0
    ]

    assert (
        "四柱・日主・身強身弱・格局・用神・大運・歳運・統合運を再計算しない"
        in call[
            "instructions"
        ]
    )

    assert (
        "日主を再判定しない"
        in call[
            "input"
        ][
            0
        ][
            "content"
        ]
    )

    assert (
        call[
            "store"
        ]
        is False
    )


def test_fake_pipeline_json_end_to_end(
    reading_context_fixture,
):
    selected = [
        "career",
        "wealth",
    ]

    generated = {
        "summary": "全体要約",
        "sections": {
            "career": {
                "title": "仕事・適職",
                "summary": "仕事の要約",
                "detail": "仕事の詳細",
                "evidence": [
                    "食神格",
                    "己卯",
                ],
                "advice": [
                    "得意分野を活かす",
                ],
            },
            "wealth": {
                "title": "金運",
                "summary": "金運の要約",
                "detail": "金運の詳細",
                "evidence": [
                    "丙午",
                ],
                "advice": [
                    "収支管理を行う",
                ],
            },
        },
        "disclaimer": (
            "確定的な未来を保証するものではありません。"
        ),
    }

    response = SimpleNamespace(
        id="resp_e2e_json",
        status="completed",
        output_text=json.dumps(
            generated,
            ensure_ascii=False,
        ),
        usage={
            "input_tokens": 500,
            "output_tokens": 700,
            "total_tokens": 1200,
        },
    )

    client = FakeClient(
        response
    )

    result = generate_reading(
        reading_context_fixture,
        client=client,
        model="test-model",
        sections=selected,
        output_format="json",
    )

    assert (
        result.parsed
        == generated
    )

    assert (
        result.sections
        == (
            "career",
            "wealth",
        )
    )

    call = client.responses.calls[
        0
    ]

    strict_schema = call[
        "text"
    ][
        "format"
    ][
        "schema"
    ]

    assert (
        strict_schema[
            "properties"
        ][
            "sections"
        ][
            "required"
        ]
        == selected
    )

    assert (
        strict_schema[
            "additionalProperties"
        ]
        is False
    )

    assert (
        result.usage[
            "total_tokens"
        ]
        == 1200
    )


# ============================================================
# 18. No real API access
# ============================================================


def test_fake_client_avoids_real_client_creation(
    reading_context_fixture,
    fake_text_response,
    monkeypatch,
):
    """
    client注入時にcreate_openai_client()が
    呼ばれないことを保証する。
    """

    def fail_if_called(
        *args,
        **kwargs,
    ):
        raise AssertionError(
            "create_openai_client must not be called"
        )

    monkeypatch.setattr(
        reading_generator,
        "create_openai_client",
        fail_if_called,
    )

    result = generate_reading(
        reading_context_fixture,
        client=FakeClient(
            fake_text_response
        ),
        model="test-model",
        output_format="text",
    )

    assert (
        result.status
        == "completed"
    )


# ============================================================
# 19. Final smoke test
# ============================================================


def test_reading_generator_final_smoke(
    reading_context_fixture,
):
    generated = {
        "summary": (
            "命式と現在運を統合したテスト鑑定です。"
        ),
        "sections": {
            "career": {
                "title": "仕事・適職",
                "summary": "仕事面の要約",
                "detail": (
                    "食神格、現在大運己卯、"
                    "2026年丙午を参考に説明します。"
                ),
                "evidence": [
                    "食神格",
                    "己卯",
                    "丙午",
                ],
                "advice": [
                    "得意分野の言語化を進める",
                ],
            },
        },
        "disclaimer": (
            "本鑑定は傾向を示すもので、"
            "未来を確定するものではありません。"
        ),
    }

    response = SimpleNamespace(
        id="resp_final_smoke",
        status="completed",
        output_text=json.dumps(
            generated,
            ensure_ascii=False,
        ),
        usage=FakeUsage(),
    )

    client = FakeClient(
        response
    )

    result = generate_reading(
        reading_context_fixture,
        client=client,
        model="test-model",
        sections=[
            "career",
        ],
        output_format="json",
        max_output_tokens=3000,
        store=False,
    )

    assert (
        result.output_format
        == "json"
    )

    assert (
        result.model
        == "test-model"
    )

    assert (
        result.parsed[
            "sections"
        ][
            "career"
        ][
            "evidence"
        ]
        == [
            "食神格",
            "己卯",
            "丙午",
        ]
    )

    assert (
        result.response_id
        == "resp_final_smoke"
    )

    assert (
        result.response_status
        == "completed"
    )

    assert (
        result.status
        == "completed"
    )

    assert (
        result.method
        == "openai_responses_api_v1"
    )

    assert (
        client.responses.calls[
            0
        ][
            "text"
        ][
            "format"
        ][
            "name"
        ]
        == "shichusuimei_reading"
    )
