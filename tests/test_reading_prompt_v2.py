"""Contract tests for the trusted AI Reading v2 request builder."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import inspect
import json
from types import SimpleNamespace
from typing import Any

import pytest

import engine.reading_prompt_v2 as reading_prompt_v2_module
from engine.chart import calculate_chart
from engine.consultation_context import build_consultation_context
from engine.judgment_metadata import (
    build_common_judgment_metadata,
    validate_common_judgment_metadata,
)
from engine.reading_context_v2 import build_reading_context_v2
from engine.reading_prompt_v2 import (
    AI_READING_REQUEST_V2_FIELDS,
    AI_READING_V2_CLAIM_TYPES,
    AI_READING_V2_DISCLAIMER,
    AI_READING_V2_SECTION_SLOTS,
    AI_READING_V2_SUPPORTED_TONES,
    AI_READING_V2_SYSTEM_PROMPT,
    AI_READING_V2_USER_PROMPT_PREFIX,
    build_ai_reading_request_v2,
    validate_ai_reading_prompt_inputs_v2,
)


TARGET_DATETIME = datetime(2026, 8, 10, 15, 36)
VALID_REPORT = {
    "valid": True,
    "errors": [],
    "missing_required_fields": [],
    "unknown_fields": [],
}
EXPECTED_COMPONENTS = [
    "five_elements",
    "month_command.basic",
    "month_command.weighted",
    "month_command.seasonal",
    "month_command.integrated",
    "roots",
    "strength",
    "relations",
    "pattern",
    "useful_gods",
    "luck_pillars",
    "current_luck",
    "annual_luck",
    "integrated_luck",
]
EXPECTED_SYSTEM_PROMPT = (
    "あなたは八雲式四柱推命エンジンのAI Reading v2文章化レイヤーです。"
    "出力言語は日本語、toneはprofessional_warmとし、model_output_schemaに"
    "厳密に一致するJSONだけを返してください。\n"
    "sectionsは提示された順序どおりのexactly 8 positional slotsとし、"
    "section ID、title、yearその他のtrusted fieldを返さないでください。\n"
    "占術上の主張は、提示されたfacts、source components、および許可された"
    "luck crosswalkだけを根拠とし、referenceを新規作成してはいけません。\n"
    "warningとuncertaintyは提示されたcatalog IDからだけ選択し、新規作成、"
    "変更、正規化、重複排除をしてはいけません。\n"
    "出生時間不明の場合はknown_pillars_onlyを守り、時柱または時柱由来の"
    "解釈を推定せず、strength confidenceを強化せず、estimated timingと"
    "applicable uncertaintyを保持し、internal_reference_timeを出生時刻として"
    "扱わないでください。\n"
    "四柱、蔵干、通変星、十二運、五行score、身強身弱、干支関係、格局、"
    "用神、大運、歳運、current luck、integrated luckを再計算、再判定、"
    "再分類してはいけません。\n"
    "missing hour、true solar time、timezone correction、location correctionを"
    "推定してはいけません。\n"
    "consultationは説明の優先順位とpractical contextにだけ使用し、占術結果を"
    "生成または変更してはいけません。\n"
    "すべてのgrounded_text_blockでclaim_typeを宣言し、意図するtextと一致"
    "させてください。practicalに占術またはluckの主張を含めず、astrologyは"
    "factでgroundし、luck_astrologyは許可されたlocationとluck crosswalkで"
    "groundしてください。占術またはluckの主張をpracticalとして偽装しては"
    "いけません。\n"
    "返してよいのはmodel-owned payloadだけです。section_id、title、year、"
    "disclaimer、catalog、source contract、engine_version、schema_version、"
    "version、method、status、validationを返してはいけません。\n"
    "source_fact_codes、source_components、warning IDs、uncertainty IDsは"
    "提示されたallowed valuesからだけ選択し、strict JSONとして返してください。"
)


def _request(*, birth_time: str | None) -> SimpleNamespace:
    return SimpleNamespace(
        birth_date="1985-07-17",
        birth_time=birth_time,
        birth_place="石川県",
        gender="female",
    )


@pytest.fixture(scope="module")
def four_pillar_chart() -> dict[str, Any]:
    return calculate_chart(
        _request(birth_time="21:50"),
        target_datetime=TARGET_DATETIME,
    )


@pytest.fixture(scope="module")
def three_pillar_chart() -> dict[str, Any]:
    return calculate_chart(
        _request(birth_time=None),
        target_datetime=TARGET_DATETIME,
    )


@pytest.fixture(scope="module")
def four_pillar_context(four_pillar_chart) -> dict[str, Any]:
    return build_reading_context_v2(four_pillar_chart)


@pytest.fixture(scope="module")
def three_pillar_context(three_pillar_chart) -> dict[str, Any]:
    return build_reading_context_v2(three_pillar_chart)


@pytest.fixture(scope="module")
def consultation_context(four_pillar_chart) -> dict[str, Any]:
    consultation = build_consultation_context(
        concern="仕事について相談したい",
        desired_future="落ち着いて働きたい",
    )
    return build_reading_context_v2(
        four_pillar_chart,
        consultation_context=consultation,
    )


@pytest.fixture(scope="module")
def four_pillar_metadata(four_pillar_chart) -> dict[str, Any]:
    return build_common_judgment_metadata(four_pillar_chart)


@pytest.fixture(scope="module")
def three_pillar_metadata(three_pillar_chart) -> dict[str, Any]:
    return build_common_judgment_metadata(three_pillar_chart)


@pytest.fixture(scope="module")
def four_pillar_request(
    four_pillar_context,
    four_pillar_metadata,
) -> dict[str, Any]:
    return build_ai_reading_request_v2(
        four_pillar_context,
        four_pillar_metadata,
    )


@pytest.fixture(scope="module")
def three_pillar_request(
    three_pillar_context,
    three_pillar_metadata,
) -> dict[str, Any]:
    return build_ai_reading_request_v2(
        three_pillar_context,
        three_pillar_metadata,
    )


def _missing_record() -> dict[str, Any]:
    return {
        "source_path": None,
        "method": None,
        "version": None,
        "status": None,
        "component_status": None,
        "evidence": None,
        "warnings": [],
        "uncertainty": [],
    }


def _uncertainty(code: str, scope: str) -> dict[str, Any]:
    return {
        "code": code,
        "category": "rule_uncertainty",
        "status": "uncertain",
        "severity": "warning",
        "scope": [scope],
        "message": f"{code} message",
    }


def _metadata_with_no_present_sources(
    metadata: dict[str, Any],
) -> dict[str, Any]:
    result = deepcopy(metadata)
    for key in tuple(result["components"]):
        if key == "month_command":
            for nested_key in tuple(
                result["components"][key]["components"]
            ):
                result["components"][key]["components"][nested_key] = (
                    _missing_record()
                )
        else:
            result["components"][key] = _missing_record()
    return result


def test_valid_four_pillar_request(four_pillar_request):
    assert four_pillar_request["validation"] == VALID_REPORT
    assert four_pillar_request["status"] == "ready_for_ai_generation"


def test_valid_three_pillar_request(three_pillar_request):
    assert three_pillar_request["validation"] == VALID_REPORT
    assert three_pillar_request["model_input"]["reading_context"][
        "birth_time_status"
    ]["calculation_scope"] == "three_pillars"


def test_request_is_deterministic(four_pillar_context, four_pillar_metadata):
    first = build_ai_reading_request_v2(
        four_pillar_context,
        four_pillar_metadata,
    )
    second = build_ai_reading_request_v2(
        four_pillar_context,
        four_pillar_metadata,
    )
    assert first == second


def test_builder_does_not_mutate_inputs(
    four_pillar_context,
    four_pillar_metadata,
):
    context_before = deepcopy(four_pillar_context)
    metadata_before = deepcopy(four_pillar_metadata)
    build_ai_reading_request_v2(four_pillar_context, four_pillar_metadata)
    assert four_pillar_context == context_before
    assert four_pillar_metadata == metadata_before


def test_output_mutation_does_not_mutate_inputs(
    four_pillar_context,
    four_pillar_metadata,
):
    request = build_ai_reading_request_v2(
        four_pillar_context,
        four_pillar_metadata,
    )
    request["model_input"]["reading_context"]["facts"].clear()
    request["model_input"]["judgment_metadata"]["components"][
        "strength"
    ]["warnings"].append("mutation")
    assert four_pillar_context["facts"]
    assert "mutation" not in four_pillar_metadata["components"]["strength"][
        "warnings"
    ]


def test_non_mapping_reading_context_raises_type_error(four_pillar_metadata):
    with pytest.raises(TypeError, match="reading_context"):
        validate_ai_reading_prompt_inputs_v2([], four_pillar_metadata)


def test_non_mapping_metadata_raises_type_error(four_pillar_context):
    with pytest.raises(TypeError, match="judgment_metadata"):
        validate_ai_reading_prompt_inputs_v2(four_pillar_context, [])


def test_owner_invalid_reading_context_returns_invalid_report(
    four_pillar_context,
    four_pillar_metadata,
):
    invalid = deepcopy(four_pillar_context)
    invalid.pop("schema_version")
    report = validate_ai_reading_prompt_inputs_v2(
        invalid,
        four_pillar_metadata,
    )
    assert report["valid"] is False
    assert "reading_context.schema_version" in report[
        "missing_required_fields"
    ]


def test_owner_invalid_metadata_returns_invalid_report(
    four_pillar_context,
    four_pillar_metadata,
):
    invalid = deepcopy(four_pillar_metadata)
    invalid["unexpected"] = True
    report = validate_ai_reading_prompt_inputs_v2(
        four_pillar_context,
        invalid,
    )
    assert report["valid"] is False
    assert "judgment_metadata.unexpected" in report["unknown_fields"]


def test_builder_rejects_owner_invalid_input(
    four_pillar_context,
    four_pillar_metadata,
):
    invalid = deepcopy(four_pillar_context)
    invalid.pop("method")
    with pytest.raises(ValueError, match="invalid AI Reading v2 prompt inputs"):
        build_ai_reading_request_v2(invalid, four_pillar_metadata)


def test_sections_non_none_is_rejected(
    four_pillar_context,
    four_pillar_metadata,
):
    with pytest.raises(ValueError, match="sections must be None"):
        build_ai_reading_request_v2(
            four_pillar_context,
            four_pillar_metadata,
            sections=("career",),
        )


def test_non_ja_language_is_rejected(
    four_pillar_context,
    four_pillar_metadata,
):
    with pytest.raises(ValueError, match="language must be 'ja'"):
        build_ai_reading_request_v2(
            four_pillar_context,
            four_pillar_metadata,
            language="en",
        )


def test_unsupported_tone_is_rejected(
    four_pillar_context,
    four_pillar_metadata,
):
    assert AI_READING_V2_SUPPORTED_TONES == ("professional_warm",)
    with pytest.raises(ValueError, match="unsupported AI Reading v2 tone"):
        build_ai_reading_request_v2(
            four_pillar_context,
            four_pillar_metadata,
            tone="formal",
        )


def test_claim_type_vocabulary_is_exact():
    assert AI_READING_V2_CLAIM_TYPES == (
        "practical",
        "astrology",
        "luck_astrology",
    )


def test_request_has_exact_top_level_fields(four_pillar_request):
    expected_fields = (
        "schema_version",
        "version",
        "method",
        "status",
        "language",
        "tone",
        "source_contracts",
        "trusted_catalogs",
        "trusted_attachments",
        "model_input",
        "messages",
        "model_output_schema",
        "validation",
    )
    assert AI_READING_REQUEST_V2_FIELDS == expected_fields
    assert tuple(four_pillar_request) == expected_fields
    assert four_pillar_request["schema_version"] == "ai_reading_request_v2"
    assert four_pillar_request["version"] == "ai_reading_request_v2"
    assert four_pillar_request["method"] == "reading_prompt_v2"
    assert four_pillar_request["language"] == "ja"
    assert four_pillar_request["tone"] == "professional_warm"


def test_source_contracts_are_exact(four_pillar_request):
    assert four_pillar_request["source_contracts"] == {
        "reading_context": {
            "schema_version": "reading_context_v2",
            "method": "reading_context_v2",
            "version": "reading_context_v2",
            "status": "ready_for_ai_reading",
        },
        "judgment_metadata": {
            "schema_version": "common_judgment_metadata_v1",
        },
    }


def test_phase_1_1_preserves_catalog_shape_and_user_prefix(
    four_pillar_request,
):
    assert tuple(four_pillar_request["trusted_catalogs"]) == (
        "fact_codes",
        "source_components",
        "warnings",
        "uncertainty",
        "luck_value_sources",
    )
    assert AI_READING_V2_USER_PROMPT_PREFIX == (
        "以下のmodel_inputだけを使用し、model_output_schemaに厳密に一致するJSONを"
        "生成してください。\n"
        "model_input="
    )


def test_exact_eight_section_slots(four_pillar_request):
    slots = four_pillar_request["trusted_attachments"]["sections"]
    assert len(slots) == 8
    assert [slot["section_id"] for slot in slots] == [
        item[0] for item in AI_READING_V2_SECTION_SLOTS
    ]


def test_exact_fixed_titles(four_pillar_request):
    assert four_pillar_request["trusted_attachments"]["sections"] == [
        {"section_id": section_id, "title": title}
        for section_id, title in (
            ("core_personality", "本質・性格"),
            ("career", "仕事・適職"),
            ("wealth", "金運"),
            ("relationships", "恋愛・人間関係"),
            ("health", "健康傾向"),
            ("current_luck", "現在の運勢"),
            ("future_flow", "今後の流れ"),
            ("advice", "総合アドバイス"),
        )
    ]


def test_exact_trusted_disclaimer(four_pillar_request):
    assert AI_READING_V2_DISCLAIMER == (
        "本鑑定は八雲式四柱推命エンジンの計算結果に基づく参考情報です。"
        "将来の出来事を保証するものではなく、医療・法律・投資その他の"
        "専門的判断を代替するものではありません。重要な意思決定は、"
        "必要に応じて適切な専門家へご相談ください。"
    )
    assert (
        four_pillar_request["trusted_attachments"]["disclaimer"]
        == AI_READING_V2_DISCLAIMER
    )


def test_consultation_absent_uses_null_schema(four_pillar_request):
    assert four_pillar_request["trusted_attachments"][
        "consultation_present"
    ] is False
    schema = four_pillar_request["model_output_schema"]
    assert schema["properties"]["consultation_answer"] == {"type": "null"}


def test_consultation_present_uses_grounded_block_schema(
    consultation_context,
    four_pillar_metadata,
):
    request = build_ai_reading_request_v2(
        consultation_context,
        four_pillar_metadata,
    )
    assert request["trusted_attachments"]["consultation_present"] is True
    assert request["model_output_schema"]["properties"][
        "consultation_answer"
    ] == {"$ref": "#/$defs/grounded_text_block"}
    assert request["model_input"]["reading_context"]["consultation"] == (
        consultation_context["consultation"]
    )


def test_fact_catalog_is_exact_input_order(
    four_pillar_context,
    four_pillar_request,
):
    assert four_pillar_request["trusted_catalogs"]["fact_codes"] == [
        fact["code"] for fact in four_pillar_context["facts"]
    ]


def test_component_catalog_uses_registry_order(four_pillar_request):
    assert four_pillar_request["trusted_catalogs"][
        "source_components"
    ] == EXPECTED_COMPONENTS


def test_warning_catalog_is_deterministic_exact_projection(
    three_pillar_context,
    three_pillar_request,
):
    catalog = three_pillar_request["trusted_catalogs"]["warnings"]
    assert [entry["warning_id"] for entry in catalog] == [
        f"warning_{index:04d}"
        for index in range(1, len(catalog) + 1)
    ]
    assert catalog == [
        {
            "warning_id": f"warning_{index + 1:04d}",
            "source_contract": "reading_context_v2",
            "source_path": f"warnings[{index}]",
            "value": value,
        }
        for index, value in enumerate(three_pillar_context["warnings"])
    ]


def test_uncertainty_catalog_uses_frozen_traversal_order(
    three_pillar_request,
):
    catalog = three_pillar_request["trusted_catalogs"]["uncertainty"]
    assert [entry["uncertainty_id"] for entry in catalog] == [
        "uncertainty_0001",
        "uncertainty_0002",
        "uncertainty_0003",
    ]
    assert [entry["source_path"] for entry in catalog] == [
        "uncertainty[0]",
        "components.strength.uncertainty[0]",
        "components.strength.uncertainty[1]",
    ]
    assert [entry["value"]["code"] for entry in catalog] == [
        "birth_time_unknown",
        "season_transition_adjustment_not_applied",
        "birth_time_unknown_strength_confidence_reduced",
    ]


def test_current_luck_crosswalk_is_exact(four_pillar_request):
    entries = four_pillar_request["trusted_catalogs"]["luck_value_sources"]
    assert entries[:4] == [
        {
            "section_id": "current_luck",
            "year": None,
            "source_component": component,
            "context_path": f"luck.{component}",
        }
        for component in (
            "luck_pillars",
            "current_luck",
            "annual_luck",
            "integrated_luck",
        )
    ]


def test_five_year_luck_crosswalk_is_exact(four_pillar_request):
    entries = four_pillar_request["trusted_catalogs"]["luck_value_sources"]
    future = entries[4:]
    years = four_pillar_request["trusted_attachments"]["future_flow_years"]
    expected = []
    for index, year in enumerate(years):
        for component in ("current_luck", "annual_luck", "integrated_luck"):
            expected.append(
                {
                    "section_id": "future_flow",
                    "year": year,
                    "source_component": component,
                    "context_path": (
                        f"luck.five_year_luck[{index}].{component}"
                    ),
                }
            )
    assert future == expected


def test_null_source_path_is_excluded(
    four_pillar_context,
    four_pillar_metadata,
):
    metadata = deepcopy(four_pillar_metadata)
    metadata["components"]["annual_luck"] = _missing_record()
    request = build_ai_reading_request_v2(four_pillar_context, metadata)
    assert "annual_luck" not in request["trusted_catalogs"][
        "source_components"
    ]
    assert all(
        entry["source_component"] != "annual_luck"
        for entry in request["trusted_catalogs"]["luck_value_sources"]
    )


def test_month_command_aggregate_is_excluded(four_pillar_request):
    components = four_pillar_request["trusted_catalogs"]["source_components"]
    assert "month_command" not in components
    assert components[1:5] == [
        "month_command.basic",
        "month_command.weighted",
        "month_command.seasonal",
        "month_command.integrated",
    ]


def test_canonical_messages_are_exact(four_pillar_request):
    messages = four_pillar_request["messages"]
    assert messages[0] == {"role": "system", "content": EXPECTED_SYSTEM_PROMPT}
    assert AI_READING_V2_SYSTEM_PROMPT == EXPECTED_SYSTEM_PROMPT
    expected_user = AI_READING_V2_USER_PROMPT_PREFIX + json.dumps(
        four_pillar_request["model_input"],
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=False,
        allow_nan=False,
    )
    assert messages[1] == {"role": "user", "content": expected_user}
    assert json.loads(messages[1]["content"].removeprefix(
        AI_READING_V2_USER_PROMPT_PREFIX
    )) == four_pillar_request["model_input"]


def test_v1_prompt_is_not_imported_or_reused():
    source = inspect.getsource(reading_prompt_v2_module)
    assert "from engine.reading_prompt import" not in source
    assert "import engine.reading_prompt" not in source
    assert "SUPPORTED_TONES" not in source.replace(
        "AI_READING_V2_SUPPORTED_TONES",
        "",
    )


def test_model_output_schema_has_exact_root(four_pillar_request):
    schema = four_pillar_request["model_output_schema"]
    assert tuple(schema) == (
        "$defs",
        "type",
        "properties",
        "required",
        "additionalProperties",
    )
    assert schema["type"] == "object"
    assert tuple(schema["properties"]) == (
        "summary",
        "sections",
        "future_flow_yearly",
        "consultation_answer",
    )
    assert schema["required"] == list(schema["properties"])
    assert schema["additionalProperties"] is False


def test_grounded_text_block_schema_is_exact(four_pillar_request):
    block = four_pillar_request["model_output_schema"]["$defs"][
        "grounded_text_block"
    ]
    assert tuple(block["properties"]) == (
        "text",
        "claim_type",
        "source_fact_codes",
        "source_components",
        "warnings",
        "uncertainty",
    )
    assert block["required"] == list(block["properties"])
    assert block["additionalProperties"] is False
    assert block["properties"]["claim_type"] == {
        "type": "string",
        "enum": ["practical", "astrology", "luck_astrology"],
    }


@pytest.mark.parametrize(
    ("has_facts", "has_luck_sources", "expected"),
    (
        pytest.param(
            True,
            True,
            ["practical", "astrology", "luck_astrology"],
            id="facts-and-luck",
        ),
        pytest.param(
            True,
            False,
            ["practical", "astrology"],
            id="facts-only",
        ),
        pytest.param(
            False,
            True,
            ["practical", "luck_astrology"],
            id="luck-only",
        ),
        pytest.param(
            False,
            False,
            ["practical"],
            id="neither",
        ),
    ),
)
def test_available_claim_type_enum_is_exact_and_never_empty(
    four_pillar_context,
    four_pillar_metadata,
    has_facts,
    has_luck_sources,
    expected,
):
    context = deepcopy(four_pillar_context)
    metadata = deepcopy(four_pillar_metadata)
    if not has_facts:
        context["facts"] = []
    if not has_luck_sources:
        metadata = _metadata_with_no_present_sources(metadata)

    request = build_ai_reading_request_v2(context, metadata)
    claim_type_schema = request["model_output_schema"]["$defs"][
        "grounded_text_block"
    ]["properties"]["claim_type"]

    assert claim_type_schema == {"type": "string", "enum": expected}
    assert claim_type_schema["enum"]


def test_model_section_schema_is_exact(four_pillar_request):
    section = four_pillar_request["model_output_schema"]["$defs"][
        "model_section_payload"
    ]
    assert tuple(section["properties"]) == (
        "facts",
        "summary",
        "detail",
        "evidence",
        "interpretation",
        "advice",
        "warnings",
        "uncertainty",
    )
    assert section["required"] == list(section["properties"])
    assert section["additionalProperties"] is False


def test_sections_schema_requires_exactly_eight(four_pillar_request):
    sections = four_pillar_request["model_output_schema"]["properties"][
        "sections"
    ]
    assert sections == {
        "type": "array",
        "items": {"$ref": "#/$defs/model_section_payload"},
        "minItems": 8,
        "maxItems": 8,
    }


def test_future_year_schema_uses_trusted_cardinality(four_pillar_request):
    years = four_pillar_request["trusted_attachments"]["future_flow_years"]
    yearly = four_pillar_request["model_output_schema"]["properties"][
        "future_flow_yearly"
    ]
    assert yearly["minItems"] == len(years)
    assert yearly["maxItems"] == len(years)
    assert years == [2026, 2027, 2028, 2029, 2030]


def test_empty_dynamic_enum_representation(
    four_pillar_context,
    four_pillar_metadata,
):
    context = deepcopy(four_pillar_context)
    context["facts"] = []
    context["warnings"] = []
    context["uncertainty"] = []
    metadata = _metadata_with_no_present_sources(four_pillar_metadata)
    request = build_ai_reading_request_v2(context, metadata)
    definitions = request["model_output_schema"]["$defs"]
    expected = {
        "type": "array",
        "items": {"type": "string"},
        "minItems": 0,
        "maxItems": 0,
        "uniqueItems": True,
    }
    for key in (
        "fact_code_array",
        "source_component_array",
        "warning_id_array",
        "uncertainty_id_array",
    ):
        assert definitions[key] == expected


def test_schema_never_contains_empty_enum(
    four_pillar_context,
    four_pillar_metadata,
):
    context = deepcopy(four_pillar_context)
    context["facts"] = []
    context["warnings"] = []
    context["uncertainty"] = []
    metadata = _metadata_with_no_present_sources(four_pillar_metadata)
    schema = build_ai_reading_request_v2(context, metadata)[
        "model_output_schema"
    ]
    assert '"enum":[]' not in json.dumps(schema, separators=(",", ":"))


def test_module_does_not_import_or_call_astrology_calculation():
    source = inspect.getsource(reading_prompt_v2_module)
    for prohibited in (
        "engine.chart",
        "calculate_chart",
        "calculate_four_pillars",
        "calculate_luck",
    ):
        assert prohibited not in source


def test_three_pillar_hour_remains_null(three_pillar_request):
    context = three_pillar_request["model_input"]["reading_context"]
    assert context["chart"]["pillars"]["hour"] is None
    assert context["chart"]["pillar_sequence"][3] is None


def test_three_pillar_uncertainty_is_preserved(
    three_pillar_context,
    three_pillar_request,
):
    assert three_pillar_request["model_input"]["reading_context"][
        "uncertainty"
    ] == three_pillar_context["uncertainty"]
    assert three_pillar_request["trusted_catalogs"]["uncertainty"][0][
        "value"
    ] == three_pillar_context["uncertainty"][0]


def test_invalid_prompt_prerequisite_causes_value_error(
    four_pillar_context,
    four_pillar_metadata,
):
    invalid = deepcopy(four_pillar_context)
    invalid["warnings"] = [1]
    report = validate_ai_reading_prompt_inputs_v2(
        invalid,
        four_pillar_metadata,
    )
    assert report["valid"] is False
    assert "type:reading_context.warnings:array_of_string" in report["errors"]
    with pytest.raises(ValueError, match="invalid AI Reading v2 prompt inputs"):
        build_ai_reading_request_v2(invalid, four_pillar_metadata)


def test_duplicate_future_year_is_prompt_invalid(
    four_pillar_context,
    four_pillar_metadata,
):
    invalid = deepcopy(four_pillar_context)
    invalid["luck"]["five_year_luck"][1]["year"] = invalid["luck"][
        "five_year_luck"
    ][0]["year"]
    report = validate_ai_reading_prompt_inputs_v2(
        invalid,
        four_pillar_metadata,
    )
    assert report["valid"] is False
    assert any(error.startswith("duplicate_year:") for error in report["errors"])


def test_missing_five_year_luck_is_prompt_invalid(
    four_pillar_context,
    four_pillar_metadata,
):
    invalid = deepcopy(four_pillar_context)
    invalid["luck"].pop("five_year_luck")
    report = validate_ai_reading_prompt_inputs_v2(
        invalid,
        four_pillar_metadata,
    )
    assert report["valid"] is False
    assert "reading_context.luck.five_year_luck" in report[
        "missing_required_fields"
    ]


def test_validation_report_has_exact_fields(
    four_pillar_context,
    four_pillar_metadata,
):
    report = validate_ai_reading_prompt_inputs_v2(
        four_pillar_context,
        four_pillar_metadata,
    )
    assert tuple(report) == (
        "valid",
        "errors",
        "missing_required_fields",
        "unknown_fields",
    )
    assert report == VALID_REPORT


def test_model_input_is_separate_and_exact_deep_copy(
    four_pillar_context,
    four_pillar_metadata,
    four_pillar_request,
):
    model_input = four_pillar_request["model_input"]
    assert tuple(model_input) == (
        "reading_context",
        "judgment_metadata",
        "trusted_catalogs",
        "section_slots",
        "future_flow_years",
    )
    assert model_input["reading_context"] == four_pillar_context
    assert model_input["reading_context"] is not four_pillar_context
    assert model_input["judgment_metadata"] == four_pillar_metadata
    assert model_input["judgment_metadata"] is not four_pillar_metadata


def test_trusted_attachments_have_exact_fields(four_pillar_request):
    attachments = four_pillar_request["trusted_attachments"]
    assert tuple(attachments) == (
        "final_schema_version",
        "final_version",
        "final_method",
        "final_status",
        "engine_version",
        "sections",
        "future_flow_years",
        "consultation_present",
        "disclaimer",
    )
    assert attachments["final_schema_version"] == "ai_reading_v2"
    assert attachments["final_version"] == "ai_reading_v2"
    assert attachments["final_method"] == "openai_responses_api_v2"
    assert attachments["final_status"] == "completed"


def test_common_metadata_source_path_is_used_as_presence_assertion(
    four_pillar_context,
    four_pillar_metadata,
):
    request = build_ai_reading_request_v2(
        four_pillar_context,
        four_pillar_metadata,
    )
    assert request["trusted_catalogs"]["source_components"] == (
        EXPECTED_COMPONENTS
    )
    signature = inspect.signature(build_ai_reading_request_v2)
    assert tuple(signature.parameters) == (
        "reading_context",
        "judgment_metadata",
        "sections",
        "language",
        "tone",
    )


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    (
        pytest.param(
            "source_path",
            "unregistered_strength_source",
            id="registered-source-path-mismatch",
        ),
        pytest.param("method", None, id="present-source-method-missing"),
    ),
)
def test_component_trust_boundary_rejects_invalid_present_source(
    four_pillar_context,
    four_pillar_metadata,
    field,
    invalid_value,
):
    assert validate_common_judgment_metadata(four_pillar_metadata) == (
        VALID_REPORT
    )
    invalid = deepcopy(four_pillar_metadata)
    invalid["components"]["strength"][field] = invalid_value

    report = validate_ai_reading_prompt_inputs_v2(
        four_pillar_context,
        invalid,
    )

    assert report["valid"] is False
    with pytest.raises(ValueError, match="invalid AI Reading v2 prompt inputs"):
        build_ai_reading_request_v2(four_pillar_context, invalid)


@pytest.mark.parametrize(
    "case",
    (
        "missing_required_field",
        "unknown_field",
        "wrong_field_type",
        "invalid_vocabulary",
    ),
)
def test_malformed_uncertainty_is_prompt_invalid(
    four_pillar_context,
    four_pillar_metadata,
    case,
):
    invalid = deepcopy(four_pillar_context)
    uncertainty = _uncertainty("malformed_fixture", "strength")
    if case == "missing_required_field":
        uncertainty.pop("message")
    elif case == "unknown_field":
        uncertainty["unexpected"] = True
    elif case == "wrong_field_type":
        uncertainty["scope"] = "strength"
    else:
        uncertainty["category"] = "invented_uncertainty_category"
    invalid["uncertainty"] = [uncertainty]

    report = validate_ai_reading_prompt_inputs_v2(
        invalid,
        four_pillar_metadata,
    )

    assert report["valid"] is False
    with pytest.raises(ValueError, match="invalid AI Reading v2 prompt inputs"):
        build_ai_reading_request_v2(invalid, four_pillar_metadata)


@pytest.mark.parametrize(
    "case",
    (
        "non_mapping_entry",
        "non_integer_year",
        "missing_current_luck",
        "missing_annual_luck",
        "missing_integrated_luck",
        "invalid_current_luck",
        "invalid_annual_luck",
        "invalid_integrated_luck",
    ),
)
def test_malformed_five_year_entry_is_prompt_invalid(
    four_pillar_context,
    four_pillar_metadata,
    case,
):
    invalid = deepcopy(four_pillar_context)
    if case == "non_mapping_entry":
        invalid["luck"]["five_year_luck"][0] = None
    else:
        entry = invalid["luck"]["five_year_luck"][0]
        if case == "non_integer_year":
            entry["year"] = "2026"
        elif case.startswith("missing_"):
            entry.pop(case.removeprefix("missing_"))
        else:
            entry[case.removeprefix("invalid_")] = []

    report = validate_ai_reading_prompt_inputs_v2(
        invalid,
        four_pillar_metadata,
    )

    assert report["valid"] is False
    with pytest.raises(ValueError, match="invalid AI Reading v2 prompt inputs"):
        build_ai_reading_request_v2(invalid, four_pillar_metadata)


@pytest.mark.parametrize(
    ("component", "case"),
    tuple(
        (component, case)
        for component in (
            "luck_pillars",
            "current_luck",
            "annual_luck",
            "integrated_luck",
        )
        for case in ("missing", "invalid_type")
    ),
)
def test_malformed_top_level_luck_component_is_prompt_invalid(
    four_pillar_context,
    four_pillar_metadata,
    component,
    case,
):
    invalid = deepcopy(four_pillar_context)
    if case == "missing":
        invalid["luck"].pop(component)
    else:
        invalid["luck"][component] = []

    report = validate_ai_reading_prompt_inputs_v2(
        invalid,
        four_pillar_metadata,
    )

    assert report["valid"] is False
    with pytest.raises(ValueError, match="invalid AI Reading v2 prompt inputs"):
        build_ai_reading_request_v2(invalid, four_pillar_metadata)


def test_empty_five_year_luck_is_valid_and_has_zero_cardinality(
    four_pillar_context,
    four_pillar_metadata,
):
    context = deepcopy(four_pillar_context)
    context["luck"]["five_year_luck"] = []

    report = validate_ai_reading_prompt_inputs_v2(
        context,
        four_pillar_metadata,
    )
    request = build_ai_reading_request_v2(context, four_pillar_metadata)
    future_schema = request["model_output_schema"]["properties"][
        "future_flow_yearly"
    ]

    assert report == VALID_REPORT
    assert request["trusted_attachments"]["future_flow_years"] == []
    assert all(
        entry["section_id"] != "future_flow"
        for entry in request["trusted_catalogs"]["luck_value_sources"]
    )
    assert future_schema["minItems"] == 0
    assert future_schema["maxItems"] == 0


def test_null_luck_values_are_valid_and_excluded_from_crosswalk(
    four_pillar_context,
    four_pillar_metadata,
):
    context = deepcopy(four_pillar_context)
    context["luck"]["annual_luck"] = None
    context["luck"]["five_year_luck"][0]["integrated_luck"] = None

    report = validate_ai_reading_prompt_inputs_v2(
        context,
        four_pillar_metadata,
    )
    request = build_ai_reading_request_v2(context, four_pillar_metadata)
    paths = [
        entry["context_path"]
        for entry in request["trusted_catalogs"]["luck_value_sources"]
    ]

    assert report == VALID_REPORT
    assert "luck.annual_luck" not in paths
    assert "luck.five_year_luck[0].integrated_luck" not in paths
    assert "luck.five_year_luck[0].current_luck" in paths


def test_notice_catalogs_follow_full_registry_without_transformation(
    four_pillar_context,
    four_pillar_metadata,
):
    context = deepcopy(four_pillar_context)
    context["warnings"] = ["reading-context warning"]
    context["uncertainty"] = [
        _uncertainty("reading_context_uncertainty", "global")
    ]
    context["notes"] = ["developer-only note must not become a notice"]

    metadata = deepcopy(four_pillar_metadata)
    records = metadata["components"]
    month = records["month_command"]["components"]
    month["basic"]["warnings"] = ["duplicate warning"]
    month["basic"]["uncertainty"] = [
        _uncertainty("month_basic_uncertainty", "month_command")
    ]
    month["weighted"]["warnings"] = ["weighted warning"]
    month["weighted"]["uncertainty"] = []
    records["strength"]["warnings"] = ["duplicate warning"]
    records["strength"]["uncertainty"] = [
        _uncertainty("strength_uncertainty", "strength")
    ]
    records["useful_gods"]["warnings"] = []
    records["useful_gods"]["uncertainty"] = [
        _uncertainty("useful_gods_uncertainty", "useful_gods")
    ]
    records["current_luck"]["warnings"] = ["current luck warning"]
    records["current_luck"]["uncertainty"] = []
    records["integrated_luck"]["warnings"] = []
    records["integrated_luck"]["uncertainty"] = [
        _uncertainty("integrated_luck_uncertainty", "integrated_luck")
    ]

    assert validate_common_judgment_metadata(metadata) == VALID_REPORT
    request = build_ai_reading_request_v2(context, metadata)
    warning_catalog = request["trusted_catalogs"]["warnings"]
    uncertainty_catalog = request["trusted_catalogs"]["uncertainty"]

    assert warning_catalog == [
        {
            "warning_id": "warning_0001",
            "source_contract": "reading_context_v2",
            "source_path": "warnings[0]",
            "value": "reading-context warning",
        },
        {
            "warning_id": "warning_0002",
            "source_contract": "common_judgment_metadata_v1",
            "source_path": (
                "components.month_command.components.basic.warnings[0]"
            ),
            "value": "duplicate warning",
        },
        {
            "warning_id": "warning_0003",
            "source_contract": "common_judgment_metadata_v1",
            "source_path": (
                "components.month_command.components.weighted.warnings[0]"
            ),
            "value": "weighted warning",
        },
        {
            "warning_id": "warning_0004",
            "source_contract": "common_judgment_metadata_v1",
            "source_path": "components.strength.warnings[0]",
            "value": "duplicate warning",
        },
        {
            "warning_id": "warning_0005",
            "source_contract": "common_judgment_metadata_v1",
            "source_path": "components.current_luck.warnings[0]",
            "value": "current luck warning",
        },
    ]
    assert uncertainty_catalog == [
        {
            "uncertainty_id": "uncertainty_0001",
            "source_contract": "reading_context_v2",
            "source_path": "uncertainty[0]",
            "value": _uncertainty(
                "reading_context_uncertainty",
                "global",
            ),
        },
        {
            "uncertainty_id": "uncertainty_0002",
            "source_contract": "common_judgment_metadata_v1",
            "source_path": (
                "components.month_command.components.basic.uncertainty[0]"
            ),
            "value": _uncertainty(
                "month_basic_uncertainty",
                "month_command",
            ),
        },
        {
            "uncertainty_id": "uncertainty_0003",
            "source_contract": "common_judgment_metadata_v1",
            "source_path": "components.strength.uncertainty[0]",
            "value": _uncertainty("strength_uncertainty", "strength"),
        },
        {
            "uncertainty_id": "uncertainty_0004",
            "source_contract": "common_judgment_metadata_v1",
            "source_path": "components.useful_gods.uncertainty[0]",
            "value": _uncertainty(
                "useful_gods_uncertainty",
                "useful_gods",
            ),
        },
        {
            "uncertainty_id": "uncertainty_0005",
            "source_contract": "common_judgment_metadata_v1",
            "source_path": "components.integrated_luck.uncertainty[0]",
            "value": _uncertainty(
                "integrated_luck_uncertainty",
                "integrated_luck",
            ),
        },
    ]

    assert [entry["value"] for entry in warning_catalog].count(
        "duplicate warning"
    ) == 2
    assert all(
        entry["value"] != "developer-only note must not become a notice"
        for entry in warning_catalog
    )
    assert all(isinstance(entry["value"], str) for entry in warning_catalog)
    assert all(
        isinstance(entry["value"], dict) for entry in uncertainty_catalog
    )

    warning_catalog[1]["value"] = "output mutation"
    uncertainty_catalog[1]["value"]["scope"].append("output mutation")
    assert month["basic"]["warnings"] == ["duplicate warning"]
    assert month["basic"]["uncertainty"][0]["scope"] == ["month_command"]
