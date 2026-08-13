"""
tests/test_reading_quality_real_chart.py

8セクション品質ゲート。
OpenAI APIは呼ばず、実命式→reading_context→prompt→payloadまでを検証する。
"""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from typing import Any, Mapping

import pytest

from engine.chart import calculate_chart
from engine.reading_context import build_reading_context
from engine.reading_generator import build_generation_payload
from engine.reading_prompt import build_reading_request, build_section_prompt


ALL_SECTIONS = (
    "core_personality",
    "career",
    "wealth",
    "relationships",
    "health",
    "current_luck",
    "future_flow",
    "advice",
)

EXPECTED_PILLARS = {
    "year": "乙丑",
    "month": "癸未",
    "day": "丁巳",
    "hour": "辛亥",
}

EXPECTED_DAY_MASTER = "丁"
EXPECTED_ANNUAL_GANZHI = "丙午"

TARGET_DATETIME = datetime(2026, 8, 10, 15, 36)

QUALITY_MODEL = "gpt-5"
QUALITY_OUTPUT_FORMAT = "json"
QUALITY_MAX_OUTPUT_TOKENS = 8000
QUALITY_REASONING_EFFORT = "minimal"
QUALITY_STORE = False


@pytest.fixture
def verified_request():
    return SimpleNamespace(
        birth_date="1985-07-17",
        birth_time="21:50",
        birth_place="石川県",
        gender="female",
    )


@pytest.fixture
def real_chart_result(verified_request):
    return calculate_chart(
        verified_request,
        target_datetime=TARGET_DATETIME,
    )


@pytest.fixture
def real_reading_context(real_chart_result):
    return build_reading_context(real_chart_result)


@pytest.fixture
def all_section_request(real_reading_context):
    return build_reading_request(
        real_reading_context,
        sections=ALL_SECTIONS,
        output_format=QUALITY_OUTPUT_FORMAT,
    )


@pytest.fixture
def all_section_generation(real_reading_context):
    return build_generation_payload(
        real_reading_context,
        model=QUALITY_MODEL,
        sections=ALL_SECTIONS,
        output_format=QUALITY_OUTPUT_FORMAT,
        max_output_tokens=QUALITY_MAX_OUTPUT_TOKENS,
        reasoning_effort=QUALITY_REASONING_EFFORT,
        store=QUALITY_STORE,
    )


def _non_empty(value: Any, name: str) -> str:
    assert isinstance(value, str), f"{name} はstrである必要があります。"
    value = value.strip()
    assert value, f"{name} が空です。"
    return value


def _user_prompt(generation: Mapping[str, Any]) -> str:
    payload = generation["payload"]
    inputs = payload["input"]
    assert isinstance(inputs, list)
    assert inputs

    first = inputs[0]
    assert isinstance(first, Mapping)

    return _non_empty(
        first.get("content"),
        "payload.input[0].content",
    )


def _system_prompt(generation: Mapping[str, Any]) -> str:
    return _non_empty(
        generation["payload"].get("instructions"),
        "payload.instructions",
    )


def _assert_verified_chart(chart_result: Mapping[str, Any]) -> None:
    chart = chart_result["chart"]

    for position, expected in EXPECTED_PILLARS.items():
        assert chart[position]["pillar"] == expected

    assert chart_result["day_master"]["stem"] == EXPECTED_DAY_MASTER


def _assert_verified_context(context: Mapping[str, Any]) -> None:
    pillars = context["natal_chart"]["pillars"]

    for position, expected in EXPECTED_PILLARS.items():
        assert pillars[position]["pillar"] == expected

    assert context["day_master"]["stem"] == EXPECTED_DAY_MASTER
    assert (
        context["luck"]["annual_luck"]["ganzhi"]
        == EXPECTED_ANNUAL_GANZHI
    )


def test_quality_real_chart_is_verified(real_chart_result):
    _assert_verified_chart(real_chart_result)


def test_quality_real_context_is_verified(real_reading_context):
    _assert_verified_context(real_reading_context)


def test_quality_context_is_ready_for_ai(real_reading_context):
    assert real_reading_context["status"] == "ready_for_ai_reading"
    assert real_reading_context["method"] == "reading_context_v1"


def test_quality_has_exactly_eight_sections():
    assert len(ALL_SECTIONS) == 8
    assert len(set(ALL_SECTIONS)) == 8


@pytest.mark.parametrize("section", ALL_SECTIONS)
def test_quality_context_contains_section(real_reading_context, section):
    assert section in real_reading_context["reading_sections"]


@pytest.mark.parametrize("section", ALL_SECTIONS)
def test_quality_each_section_has_focus(real_reading_context, section):
    focus = real_reading_context["reading_sections"][section]["focus"]
    assert isinstance(focus, list)
    assert focus
    assert all(isinstance(item, str) and item.strip() for item in focus)


@pytest.mark.parametrize("section", ALL_SECTIONS)
def test_quality_each_section_has_instruction(real_reading_context, section):
    instruction = real_reading_context["reading_sections"][section]["instruction"]
    _non_empty(instruction, f"{section}.instruction")


def test_quality_request_contains_all_sections(all_section_request):
    assert tuple(all_section_request["sections"]) == ALL_SECTIONS


def test_quality_generation_contains_all_sections(all_section_generation):
    assert tuple(all_section_generation["sections"]) == ALL_SECTIONS


def test_quality_core_personality_focus(real_reading_context):
    focus = set(
        real_reading_context["reading_sections"]["core_personality"]["focus"]
    )
    assert {
        "day_master",
        "strength",
        "pattern",
        "five_elements",
    }.issubset(focus)


def test_quality_career_focus(real_reading_context):
    focus = set(real_reading_context["reading_sections"]["career"]["focus"])
    assert {
        "pattern",
        "useful_gods",
        "day_master",
        "current_luck",
        "annual_luck",
    }.issubset(focus)


def test_quality_wealth_focus(real_reading_context):
    focus = set(real_reading_context["reading_sections"]["wealth"]["focus"])
    assert {
        "pattern",
        "useful_gods",
        "five_elements",
        "current_luck",
        "annual_luck",
        "integrated_luck",
    }.issubset(focus)


def test_quality_relationships_focus(real_reading_context):
    focus = set(
        real_reading_context["reading_sections"]["relationships"]["focus"]
    )
    assert {
        "day_master",
        "pattern",
        "five_elements",
        "current_luck",
        "annual_luck",
    }.issubset(focus)


def test_quality_health_focus(real_reading_context):
    focus = set(real_reading_context["reading_sections"]["health"]["focus"])
    assert {
        "five_elements",
        "strength",
        "useful_gods",
        "current_luck",
        "annual_luck",
    }.issubset(focus)


def test_quality_current_luck_focus(real_reading_context):
    focus = set(
        real_reading_context["reading_sections"]["current_luck"]["focus"]
    )
    assert {
        "current_luck",
        "annual_luck",
        "integrated_luck",
        "useful_gods",
    }.issubset(focus)


def test_quality_future_flow_focus(real_reading_context):
    focus = set(
        real_reading_context["reading_sections"]["future_flow"]["focus"]
    )
    assert {
        "luck_pillars",
        "current_luck",
        "annual_luck",
        "useful_gods",
    }.issubset(focus)


def test_quality_advice_focus(real_reading_context):
    focus = set(real_reading_context["reading_sections"]["advice"]["focus"])
    assert {
        "useful_gods",
        "strength",
        "integrated_luck",
        "pattern",
    }.issubset(focus)


def test_quality_health_instruction_is_non_diagnostic(real_reading_context):
    instruction = (
        real_reading_context["reading_sections"]["health"]["instruction"]
    )
    assert "医学的診断を行わず" in instruction
    assert "生活上の注意" in instruction


def test_quality_relationships_separates_natal_and_current_luck(
    real_reading_context,
):
    instruction = (
        real_reading_context["reading_sections"]["relationships"]["instruction"]
    )
    assert "命式" in instruction
    assert "現在運" in instruction
    assert "区別" in instruction


def test_quality_wealth_separates_structure_and_current_luck(
    real_reading_context,
):
    instruction = (
        real_reading_context["reading_sections"]["wealth"]["instruction"]
    )
    assert "命式構造" in instruction
    assert "現在運" in instruction
    assert "分けて" in instruction


def test_quality_current_luck_separates_three_layers(real_reading_context):
    instruction = (
        real_reading_context["reading_sections"]["current_luck"]["instruction"]
    )
    assert "大運" in instruction
    assert "歳運" in instruction
    assert "統合運" in instruction


def test_quality_future_flow_uses_next_luck_pillar(real_reading_context):
    instruction = (
        real_reading_context["reading_sections"]["future_flow"]["instruction"]
    )
    assert "次の大運" in instruction
    assert "長期的" in instruction


def test_quality_advice_rejects_deterministic_prediction(real_reading_context):
    instruction = (
        real_reading_context["reading_sections"]["advice"]["instruction"]
    )
    assert "断定的な未来予言ではなく" in instruction
    assert "具体的な行動案" in instruction


@pytest.mark.parametrize("section", ALL_SECTIONS)
def test_quality_section_prompt_is_non_empty(real_reading_context, section):
    prompt = build_section_prompt(
        real_reading_context,
        section,
        output_format="json",
    )
    _non_empty(prompt, f"{section} prompt")


@pytest.mark.parametrize("section", ALL_SECTIONS)
def test_quality_section_prompt_contains_section_name(
    real_reading_context,
    section,
):
    prompt = build_section_prompt(
        real_reading_context,
        section,
        output_format="json",
    )
    assert section in prompt


def test_quality_health_prompt_contains_safety_rule(real_reading_context):
    prompt = build_section_prompt(
        real_reading_context,
        "health",
        output_format="json",
    )
    assert "医学的診断" in prompt


def test_quality_current_luck_prompt_mentions_luck_layers(
    real_reading_context,
):
    prompt = build_section_prompt(
        real_reading_context,
        "current_luck",
        output_format="json",
    )
    for keyword in ("大運", "歳運", "統合運"):
        assert keyword in prompt


def test_quality_advice_prompt_contains_non_deterministic_rule(
    real_reading_context,
):
    prompt = build_section_prompt(
        real_reading_context,
        "advice",
        output_format="json",
    )
    assert "断定" in prompt
    assert "行動" in prompt


def test_quality_full_prompt_contains_all_four_pillars(
    all_section_generation,
):
    prompt = _user_prompt(all_section_generation)

    for pillar in ("乙丑", "癸未", "丁巳", "辛亥"):
        assert pillar in prompt


def test_quality_full_prompt_contains_day_master(all_section_generation):
    prompt = _user_prompt(all_section_generation)
    assert EXPECTED_DAY_MASTER in prompt


def test_quality_full_prompt_contains_annual_luck(all_section_generation):
    prompt = _user_prompt(all_section_generation)
    assert EXPECTED_ANNUAL_GANZHI in prompt


def test_quality_full_prompt_contains_reading_sections(all_section_generation):
    prompt = _user_prompt(all_section_generation)

    for section in ALL_SECTIONS:
        assert section in prompt


def test_quality_system_instructions_are_present(all_section_generation):
    instructions = _system_prompt(all_section_generation)
    assert len(instructions) >= 100


def test_quality_system_instructions_prevent_recalculation(
    all_section_generation,
):
    instructions = _system_prompt(all_section_generation)

    markers = (
        "再計算",
        "計算し直",
        "既存の計算結果",
        "計算済み",
        "事実として扱",
    )

    assert any(marker in instructions for marker in markers)


def test_quality_payload_uses_expected_model(all_section_generation):
    assert all_section_generation["payload"]["model"] == QUALITY_MODEL


def test_quality_payload_has_sufficient_output_tokens(
    all_section_generation,
):
    payload = all_section_generation["payload"]
    assert payload["max_output_tokens"] == QUALITY_MAX_OUTPUT_TOKENS
    assert payload["max_output_tokens"] >= 8000


def test_quality_payload_uses_minimal_reasoning(all_section_generation):
    payload = all_section_generation["payload"]
    assert payload["reasoning"]["effort"] == "minimal"


def test_quality_payload_store_is_false(all_section_generation):
    assert all_section_generation["payload"]["store"] is False


def test_quality_payload_uses_structured_outputs(all_section_generation):
    fmt = all_section_generation["payload"]["text"]["format"]
    assert fmt["type"] == "json_schema"
    assert fmt["strict"] is True


def test_quality_payload_schema_is_object(all_section_generation):
    schema = all_section_generation["payload"]["text"]["format"]["schema"]
    assert isinstance(schema, Mapping)
    assert schema.get("type") == "object"


def test_quality_output_schema_has_top_level_contract(
    all_section_request,
):
    properties = all_section_request["output_schema"]["properties"]

    assert {
        "summary",
        "sections",
        "disclaimer",
    }.issubset(properties.keys())


def test_quality_output_schema_contains_all_sections(
    all_section_request,
):
    section_properties = (
        all_section_request["output_schema"]
        ["properties"]["sections"]["properties"]
    )

    assert set(section_properties.keys()) == set(ALL_SECTIONS)


@pytest.mark.parametrize("section", ALL_SECTIONS)
def test_quality_each_output_section_has_required_fields(
    all_section_request,
    section,
):
    properties = (
        all_section_request["output_schema"]
        ["properties"]["sections"]["properties"][section]["properties"]
    )

    assert {
        "title",
        "summary",
        "detail",
        "evidence",
        "advice",
    }.issubset(properties.keys())


@pytest.mark.parametrize("section", ALL_SECTIONS)
def test_quality_evidence_and_advice_are_arrays(
    all_section_request,
    section,
):
    properties = (
        all_section_request["output_schema"]
        ["properties"]["sections"]["properties"][section]["properties"]
    )

    assert properties["evidence"]["type"] == "array"
    assert properties["advice"]["type"] == "array"


def test_quality_source_metadata_exists(real_reading_context):
    metadata = real_reading_context["source_metadata"]
    assert isinstance(metadata, Mapping)
    assert metadata


def test_quality_source_metadata_has_core_engines(real_reading_context):
    metadata = real_reading_context["source_metadata"]

    assert {
        "strength",
        "pattern",
        "useful_gods",
        "luck_pillars",
        "current_luck",
        "annual_luck",
        "integrated_luck",
    }.issubset(metadata.keys())


@pytest.mark.parametrize(
    "source",
    (
        "strength",
        "pattern",
        "useful_gods",
        "luck_pillars",
        "current_luck",
        "annual_luck",
        "integrated_luck",
    ),
)
def test_quality_source_metadata_has_method(real_reading_context, source):
    method = real_reading_context["source_metadata"][source].get("method")
    _non_empty(method, f"source_metadata.{source}.method")


def test_quality_reading_context_does_not_expose_full_chart_key(
    real_reading_context,
):
    assert "chart_result" not in real_reading_context


def test_quality_real_context_is_reproducible(real_chart_result):
    first = build_reading_context(real_chart_result)
    second = build_reading_context(real_chart_result)
    assert first == second


def test_quality_generation_payload_is_reproducible(
    real_reading_context,
):
    kwargs = dict(
        model=QUALITY_MODEL,
        sections=ALL_SECTIONS,
        output_format=QUALITY_OUTPUT_FORMAT,
        max_output_tokens=QUALITY_MAX_OUTPUT_TOKENS,
        reasoning_effort=QUALITY_REASONING_EFFORT,
        store=QUALITY_STORE,
    )

    first = build_generation_payload(real_reading_context, **kwargs)
    second = build_generation_payload(real_reading_context, **kwargs)

    assert first == second


def test_reading_quality_real_chart_v1_final_gate(
    real_chart_result,
    real_reading_context,
    all_section_request,
    all_section_generation,
):
    _assert_verified_chart(real_chart_result)
    _assert_verified_context(real_reading_context)

    assert real_reading_context["status"] == "ready_for_ai_reading"

    assert set(
        real_reading_context["reading_sections"].keys()
    ) == set(ALL_SECTIONS)

    assert tuple(all_section_request["sections"]) == ALL_SECTIONS
    assert tuple(all_section_generation["sections"]) == ALL_SECTIONS

    payload = all_section_generation["payload"]

    assert payload["max_output_tokens"] == 8000
    assert payload["reasoning"]["effort"] == "minimal"
    assert payload["store"] is False
    assert payload["text"]["format"]["type"] == "json_schema"
    assert payload["text"]["format"]["strict"] is True

    prompt = _user_prompt(all_section_generation)

    for fact in (
        "乙丑",
        "癸未",
        "丁巳",
        "辛亥",
        "丁",
        "丙午",
    ):
        assert fact in prompt

    health_instruction = (
        real_reading_context["reading_sections"]["health"]["instruction"]
    )
    assert "医学的診断を行わず" in health_instruction

    advice_instruction = (
        real_reading_context["reading_sections"]["advice"]["instruction"]
    )
    assert "断定的な未来予言ではなく" in advice_instruction
