"""Contract tests for AI Reading v2 generation and trusted assembly."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import inspect
import json
from types import SimpleNamespace
from typing import Any

import pytest
from jsonschema import Draft202012Validator

import engine.reading_generator_v2 as generator_v2
from engine.chart import calculate_chart
from engine.consultation_context import build_consultation_context
from engine.judgment_metadata import build_common_judgment_metadata
from engine.reading_context_v2 import build_reading_context_v2
from engine.reading_generator_v2 import (
    AIReadingGenerationResultV2,
    AIReadingGeneratorV2CandidateValidationError,
    AIReadingGeneratorV2JSONError,
    AIReadingGeneratorV2ProviderError,
    AIReadingGeneratorV2RequestValidationError,
    AIReadingGeneratorV2ResponseError,
    AIReadingGeneratorV2SemanticValidationError,
    AIReadingGeneratorV2StructuralValidationError,
    generate_ai_reading_v2,
)
from engine.reading_prompt_v2 import build_ai_reading_request_v2


TARGET_DATETIME = datetime(2026, 8, 10, 15, 36)
EXPECTED_SECTION_SLOTS = [
    {"section_id": "core_personality", "title": "本質・性格"},
    {"section_id": "career", "title": "仕事・適職"},
    {"section_id": "wealth", "title": "金運"},
    {"section_id": "relationships", "title": "恋愛・人間関係"},
    {"section_id": "health", "title": "健康傾向"},
    {"section_id": "current_luck", "title": "現在の運勢"},
    {"section_id": "future_flow", "title": "今後の流れ"},
    {"section_id": "advice", "title": "総合アドバイス"},
]
SECTION_IDS = tuple(item["section_id"] for item in EXPECTED_SECTION_SLOTS)
EXPECTED_DISCLAIMER = (
    "本鑑定は八雲式四柱推命エンジンの計算結果に基づく参考情報です。"
    "将来の出来事を保証するものではなく、医療・法律・投資その他の"
    "専門的判断を代替するものではありません。重要な意思決定は、"
    "必要に応じて適切な専門家へご相談ください。"
)
VALID_REPORT = {
    "valid": True,
    "errors": [],
    "missing_required_fields": [],
    "unknown_fields": [],
}


def _birth_request(*, birth_time: str | None) -> SimpleNamespace:
    return SimpleNamespace(
        birth_date="1985-07-17",
        birth_time=birth_time,
        birth_place="石川県",
        gender="female",
    )


@pytest.fixture(scope="module")
def four_pillar_chart() -> dict[str, Any]:
    return calculate_chart(
        _birth_request(birth_time="21:50"),
        target_datetime=TARGET_DATETIME,
    )


@pytest.fixture(scope="module")
def three_pillar_chart() -> dict[str, Any]:
    return calculate_chart(
        _birth_request(birth_time=None),
        target_datetime=TARGET_DATETIME,
    )


@pytest.fixture(scope="module")
def four_pillar_request(four_pillar_chart) -> dict[str, Any]:
    return build_ai_reading_request_v2(
        build_reading_context_v2(four_pillar_chart),
        build_common_judgment_metadata(four_pillar_chart),
    )


@pytest.fixture(scope="module")
def three_pillar_request(three_pillar_chart) -> dict[str, Any]:
    return build_ai_reading_request_v2(
        build_reading_context_v2(three_pillar_chart),
        build_common_judgment_metadata(three_pillar_chart),
    )


@pytest.fixture(scope="module")
def consultation_request(four_pillar_chart) -> dict[str, Any]:
    consultation = build_consultation_context(
        concern="仕事について相談したい",
        desired_future="落ち着いて働きたい",
    )
    return build_ai_reading_request_v2(
        build_reading_context_v2(
            four_pillar_chart,
            consultation_context=consultation,
        ),
        build_common_judgment_metadata(four_pillar_chart),
    )


def _block(
    *,
    claim_type: str = "practical",
    fact_codes: list[str] | None = None,
    components: list[str] | None = None,
    warnings: list[str] | None = None,
    uncertainty: list[str] | None = None,
    text: str = "実用的な案内です。",
) -> dict[str, Any]:
    return {
        "text": text,
        "claim_type": claim_type,
        "source_fact_codes": list(fact_codes or []),
        "source_components": list(components or []),
        "warnings": list(warnings or []),
        "uncertainty": list(uncertainty or []),
    }


def _model_payload(request: dict[str, Any]) -> dict[str, Any]:
    sections = []
    for _ in range(8):
        sections.append(
            {
                "facts": [],
                "summary": _block(),
                "detail": _block(),
                "evidence": [],
                "interpretation": [],
                "advice": [_block()],
                "warnings": [],
                "uncertainty": [],
            }
        )
    yearly = [
        {
            "title": _block(), "theme": _block(), "career": _block(),
            "wealth": _block(), "relationships": _block(), "caution": _block(),
            "advice": [_block(), _block()],
            "summary": _block(), "detail": _block(),
        }
        for _ in request["trusted_attachments"]["future_flow_years"]
    ]
    answer = _block() if request["trusted_attachments"]["consultation_present"] else None
    long_term = []
    for _ in request["trusted_attachments"].get("long_term_luck_pillars", []):
        def luck_block():
            return _block(claim_type="luck_astrology", components=["luck_pillars"])
        long_term.append({
            "title": luck_block(), "theme": luck_block(), "career": luck_block(),
            "wealth": luck_block(), "relationships": luck_block(), "caution": luck_block(),
            "advice": [luck_block(), luck_block()],
        })
    return {
        "summary": _block(),
        "sections": sections,
        "future_flow_yearly": yearly,
        "long_term_luck": long_term,
        "consultation_answer": answer,
    }


def _transport_payload(payload: Any) -> Any:
    result = deepcopy(payload)
    if isinstance(result, dict) and isinstance(result.get("sections"), list):
        sections = result["sections"]
        if len(sections) == len(SECTION_IDS):
            result["sections"] = {
                section_id: section
                for section_id, section in zip(SECTION_IDS, sections)
            }
    return result


class FakeResponses:
    def __init__(self, payload: Any, *, failure: Exception | None = None):
        self.payload = deepcopy(payload)
        self.failure = failure
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs):
        self.calls.append(deepcopy(kwargs))
        if self.failure is not None:
            raise self.failure
        provider_value = _transport_payload(self.payload)
        text = provider_value if isinstance(provider_value, str) else json.dumps(
            provider_value,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        return SimpleNamespace(
            id="resp_v2",
            status="completed",
            output_text=text,
            usage={"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
        )


class FakeClient:
    def __init__(self, payload: Any, *, failure: Exception | None = None):
        self.responses = FakeResponses(payload, failure=failure)


def _generate(request: dict[str, Any], payload: Any):
    client = FakeClient(payload)
    result = generate_ai_reading_v2(
        deepcopy(request),
        client=client,
        model="test-model",
    )
    return result, client


def _first_fact(request: dict[str, Any]) -> str:
    return request["trusted_catalogs"]["fact_codes"][0]


def _contains_schema_keyword(value: Any, keyword: str) -> bool:
    if isinstance(value, dict):
        return keyword in value or any(
            _contains_schema_keyword(item, keyword) for item in value.values()
        )
    if isinstance(value, list):
        return any(_contains_schema_keyword(item, keyword) for item in value)
    return False


def test_valid_four_pillar_success(four_pillar_request):
    result, client = _generate(four_pillar_request, _model_payload(four_pillar_request))
    assert isinstance(result, AIReadingGenerationResultV2)
    assert result.reading["validation"] == VALID_REPORT
    assert result.reading["status"] == "completed"
    assert result.response_id == "resp_v2"
    assert len(client.responses.calls) == 1


def test_long_term_luck_details_are_current_plus_next_four_and_owner_sourced(four_pillar_request):
    result, _ = _generate(four_pillar_request, _model_payload(four_pillar_request))
    details = result.reading["long_term_luck"]
    pillars = four_pillar_request["trusted_attachments"]["long_term_luck_pillars"]
    assert len(details) == min(5, len(pillars))
    assert [item["index"] for item in details] == [item["index"] for item in pillars]
    assert [item["ganzhi"] for item in details] == [item["ganzhi"] for item in pillars]
    assert all(len(item["advice"]) == 2 for item in details)
    for item, pillar in zip(details, pillars):
        assert item["start_age"] == pillar["start_age"]
        assert item["end_age"] == pillar["end_age"]


def test_yearly_detail_fields_round_trip_and_follow_trusted_year_order(four_pillar_request):
    result, _ = _generate(four_pillar_request, _model_payload(four_pillar_request))
    yearly = result.reading["sections"][6]["yearly"]
    expected_years = four_pillar_request["trusted_attachments"]["future_flow_years"]
    assert [item["year"] for item in yearly] == expected_years
    for item in yearly:
        assert all(field in item for field in ("title", "theme", "career", "wealth", "relationships", "caution", "advice"))
        assert 2 <= len(item["advice"]) <= 4


def test_valid_three_pillar_success_preserves_uncertainty(three_pillar_request):
    result, _ = _generate(three_pillar_request, _model_payload(three_pillar_request))
    assert result.reading["uncertainty"] == three_pillar_request["trusted_catalogs"][
        "uncertainty"
    ]
    embedded = three_pillar_request["model_input"]["reading_context"]
    assert embedded["birth_time_status"]["known"] is False
    assert embedded["birth_time_status"]["calculation_scope"] == "three_pillars"


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value["messages"][0].update(content="tampered"),
        lambda value: value["trusted_catalogs"]["fact_codes"].clear(),
        lambda value: value["trusted_attachments"].update(final_status="tampered"),
        lambda value: value["model_output_schema"].update(additionalProperties=True),
        lambda value: value["source_contracts"]["reading_context"].update(status="bad"),
    ],
)
def test_canonical_request_tampering_is_rejected(four_pillar_request, mutation):
    request = deepcopy(four_pillar_request)
    mutation(request)
    with pytest.raises(AIReadingGeneratorV2RequestValidationError):
        generate_ai_reading_v2(
            request,
            client=FakeClient(_model_payload(four_pillar_request)),
            model="test-model",
        )


def test_request_top_level_order_tampering_is_rejected(four_pillar_request):
    request = {key: deepcopy(four_pillar_request[key]) for key in reversed(four_pillar_request)}
    with pytest.raises(AIReadingGeneratorV2RequestValidationError):
        generate_ai_reading_v2(request, client=FakeClient({}), model="test-model")


def test_model_output_schema_root_order_tampering_is_rejected_before_provider(
    four_pillar_request,
):
    request = deepcopy(four_pillar_request)
    schema = request["model_output_schema"]
    request["model_output_schema"] = {
        key: schema[key]
        for key in reversed(schema)
    }
    client = FakeClient(_model_payload(four_pillar_request))
    with pytest.raises(AIReadingGeneratorV2RequestValidationError):
        generate_ai_reading_v2(request, client=client, model="test-model")
    assert client.responses.calls == []


def test_model_output_schema_defs_order_tampering_is_rejected_before_provider(
    four_pillar_request,
):
    request = deepcopy(four_pillar_request)
    definitions = request["model_output_schema"]["$defs"]
    request["model_output_schema"]["$defs"] = {
        key: definitions[key]
        for key in reversed(definitions)
    }
    client = FakeClient(_model_payload(four_pillar_request))
    with pytest.raises(AIReadingGeneratorV2RequestValidationError):
        generate_ai_reading_v2(request, client=client, model="test-model")
    assert client.responses.calls == []


def test_non_mapping_request_is_rejected_before_provider_call():
    client = FakeClient({})
    with pytest.raises(TypeError, match="request"):
        generate_ai_reading_v2([], client=client, model="test-model")
    assert client.responses.calls == []


def test_deterministic_assembly(four_pillar_request):
    payload = _model_payload(four_pillar_request)
    first, _ = _generate(four_pillar_request, payload)
    second, _ = _generate(four_pillar_request, payload)
    assert first.reading == second.reading


def test_provider_receives_unique_items_compatible_transport_schema_once(
    four_pillar_request,
):
    request_before = deepcopy(four_pillar_request)
    _, client = _generate(four_pillar_request, _model_payload(four_pillar_request))
    call = client.responses.calls[0]
    canonical_schema = four_pillar_request["model_output_schema"]
    transport_format = call["text"]["format"]
    assert transport_format["type"] == "json_schema"
    assert transport_format["name"] == "ai_reading_v2"
    assert transport_format["strict"] is True
    assert _contains_schema_keyword(canonical_schema, "uniqueItems")
    assert not _contains_schema_keyword(transport_format["schema"], "uniqueItems")
    assert set(transport_format) == {"type", "name", "schema", "strict"}
    assert call["instructions"] == four_pillar_request["messages"][0]["content"]
    assert call["input"] == [
        {"role": "user", "content": four_pillar_request["messages"][1]["content"]}
    ]
    assert call["max_output_tokens"] == 25000
    assert four_pillar_request == request_before
    assert len(client.responses.calls) == 1


def test_provider_transport_sections_are_fixed_key_object(four_pillar_request):
    schema = generator_v2._openai_transport_schema(
        four_pillar_request["model_output_schema"]
    )
    sections = schema["properties"]["sections"]
    assert sections["type"] == "object"
    assert tuple(sections["properties"]) == SECTION_IDS
    assert sections["required"] == list(SECTION_IDS)
    assert sections["additionalProperties"] is False
    assert four_pillar_request["model_output_schema"]["properties"]["sections"][
        "type"
    ] == "array"


def test_transport_decode_is_exact_deterministic_container_conversion(
    four_pillar_request,
):
    canonical_payload = _model_payload(four_pillar_request)
    transport_payload = _transport_payload(canonical_payload)
    before = deepcopy(transport_payload)
    first = generator_v2._decode_openai_transport_payload(transport_payload)
    second = generator_v2._decode_openai_transport_payload(transport_payload)
    assert first == canonical_payload
    assert second == canonical_payload
    assert transport_payload == before


def _set_transport_block(
    payload: dict[str, Any],
    *,
    section_id: str | None,
    field: str,
    block: dict[str, Any],
    yearly: bool = False,
) -> None:
    if section_id is None:
        payload[field] = block
    elif yearly:
        payload["future_flow_yearly"][0][field] = block
    elif field in ("evidence", "interpretation", "advice"):
        payload["sections"][section_id][field] = [block]
    else:
        payload["sections"][section_id][field] = block


_LOCATION_MATRIX = [
    (None, "summary", False, ("practical", "astrology")),
    *[
        (
            section_id,
            field,
            False,
            (
                ("astrology", "luck_astrology")
                if section_id in ("current_luck", "future_flow")
                and field in ("evidence", "interpretation")
                else (
                    ("practical", "astrology", "luck_astrology")
                    if section_id in ("current_luck", "future_flow")
                    else (
                        ("astrology",)
                        if field in ("evidence", "interpretation")
                        else ("practical", "astrology")
                    )
                )
            ),
        )
        for section_id in SECTION_IDS
        for field in ("summary", "detail", "evidence", "interpretation", "advice")
    ],
    ("future_flow", "summary", True, ("practical", "astrology", "luck_astrology")),
    ("future_flow", "detail", True, ("practical", "astrology", "luck_astrology")),
]


@pytest.mark.parametrize(
    ("section_id", "field", "yearly", "allowed"),
    _LOCATION_MATRIX,
)
def test_transport_schema_enforces_complete_location_claim_type_matrix(
    four_pillar_request,
    section_id,
    field,
    yearly,
    allowed,
):
    schema = generator_v2._openai_transport_schema(
        four_pillar_request["model_output_schema"]
    )
    validator = Draft202012Validator(schema)
    for claim_type in ("practical", "astrology", "luck_astrology"):
        payload = _transport_payload(_model_payload(four_pillar_request))
        _set_transport_block(
            payload,
            section_id=section_id,
            field=field,
            block=_block(claim_type=claim_type),
            yearly=yearly,
        )
        errors = list(validator.iter_errors(payload))
        assert (not errors) is (claim_type in allowed)


def test_transport_schema_enforces_consultation_claim_types(consultation_request):
    schema = generator_v2._openai_transport_schema(
        consultation_request["model_output_schema"]
    )
    validator = Draft202012Validator(schema)
    for claim_type in ("practical", "astrology", "luck_astrology"):
        payload = _transport_payload(_model_payload(consultation_request))
        payload["consultation_answer"] = _block(claim_type=claim_type)
        errors = list(validator.iter_errors(payload))
        assert (not errors) is (claim_type in ("practical", "astrology"))


def test_health_interpretation_transport_claim_type_is_astrology_only(
    four_pillar_request,
):
    schema = generator_v2._openai_transport_schema(
        four_pillar_request["model_output_schema"]
    )
    block_schema = schema["properties"]["sections"]["properties"]["health"][
        "properties"
    ]["interpretation"]["items"]
    assert block_schema["properties"]["claim_type"]["enum"] == ["astrology"]


def test_decode_is_followed_by_canonical_and_semantic_validation(
    four_pillar_request,
):
    canonical_payload = _model_payload(four_pillar_request)
    transport_payload = _transport_payload(canonical_payload)
    decoded = generator_v2._decode_openai_transport_payload(transport_payload)
    generator_v2._validate_structure(
        decoded,
        four_pillar_request["model_output_schema"],
    )
    generator_v2._validate_semantics(decoded, four_pillar_request)


def test_provider_duplicate_array_item_is_rejected_by_canonical_local_schema(
    four_pillar_request,
):
    payload = _model_payload(four_pillar_request)
    fact_code = _first_fact(four_pillar_request)
    payload["summary"]["source_fact_codes"] = [fact_code, fact_code]
    client = FakeClient(payload)

    with pytest.raises(AIReadingGeneratorV2StructuralValidationError):
        generate_ai_reading_v2(
            deepcopy(four_pillar_request),
            client=client,
            model="test-model",
        )

    assert len(client.responses.calls) == 1
    assert not _contains_schema_keyword(
        client.responses.calls[0]["text"]["format"]["schema"],
        "uniqueItems",
    )
    assert _contains_schema_keyword(
        four_pillar_request["model_output_schema"],
        "uniqueItems",
    )


@pytest.mark.parametrize("text", ["not-json", '{"summary":', "NaN"])
def test_malformed_json_is_rejected(four_pillar_request, text):
    with pytest.raises(AIReadingGeneratorV2JSONError):
        _generate(four_pillar_request, text)


@pytest.mark.parametrize("payload", [[], "text", 1, None])
def test_non_object_json_is_rejected(four_pillar_request, payload):
    with pytest.raises(AIReadingGeneratorV2JSONError):
        _generate(four_pillar_request, payload)


def test_invalid_json_schema_is_rejected_before_semantics():
    with pytest.raises(AIReadingGeneratorV2StructuralValidationError):
        generator_v2._validate_structure({}, {"type": "not-a-json-schema-type"})


def test_structural_errors_have_deterministic_order(four_pillar_request):
    payload = _model_payload(four_pillar_request)
    payload.pop("summary")
    payload["extra"] = True
    with pytest.raises(AIReadingGeneratorV2StructuralValidationError) as first:
        generator_v2._validate_structure(payload, four_pillar_request["model_output_schema"])
    with pytest.raises(AIReadingGeneratorV2StructuralValidationError) as second:
        generator_v2._validate_structure(payload, four_pillar_request["model_output_schema"])
    assert first.value.issues == second.value.issues


def test_extra_model_field_is_rejected(four_pillar_request):
    payload = _model_payload(four_pillar_request)
    payload["schema_version"] = "ai_reading_v2"
    with pytest.raises(AIReadingGeneratorV2StructuralValidationError):
        _generate(four_pillar_request, payload)


@pytest.mark.parametrize("count", [7, 9])
def test_wrong_section_count_is_rejected(four_pillar_request, count):
    payload = _model_payload(four_pillar_request)
    payload["sections"] = (payload["sections"] * 2)[:count]
    with pytest.raises(AIReadingGeneratorV2StructuralValidationError):
        _generate(four_pillar_request, payload)


@pytest.mark.parametrize("delta", [-1, 1])
def test_wrong_future_year_count_is_rejected(four_pillar_request, delta):
    payload = _model_payload(four_pillar_request)
    target = len(payload["future_flow_yearly"]) + delta
    payload["future_flow_yearly"] = (payload["future_flow_yearly"] * 2)[:target]
    with pytest.raises(AIReadingGeneratorV2StructuralValidationError):
        _generate(four_pillar_request, payload)


def test_consultation_absent_must_be_null(four_pillar_request):
    payload = _model_payload(four_pillar_request)
    payload["consultation_answer"] = _block()
    with pytest.raises(AIReadingGeneratorV2StructuralValidationError):
        _generate(four_pillar_request, payload)


def test_consultation_present_requires_block(consultation_request):
    payload = _model_payload(consultation_request)
    payload["consultation_answer"] = None
    with pytest.raises(AIReadingGeneratorV2StructuralValidationError):
        _generate(consultation_request, payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_fact_codes", ["invented.fact"]),
        ("source_components", ["invented_component"]),
        ("warnings", ["warning_9999"]),
        ("uncertainty", ["uncertainty_9999"]),
    ],
)
def test_unknown_dynamic_reference_is_rejected(four_pillar_request, field, value):
    payload = _model_payload(four_pillar_request)
    payload["summary"][field] = value
    with pytest.raises(AIReadingGeneratorV2StructuralValidationError):
        _generate(four_pillar_request, payload)


def test_practical_with_reference_is_rejected(four_pillar_request):
    payload = _model_payload(four_pillar_request)
    payload["summary"]["source_fact_codes"] = [_first_fact(four_pillar_request)]
    with pytest.raises(AIReadingGeneratorV2SemanticValidationError):
        _generate(four_pillar_request, payload)


def test_astrology_without_fact_is_rejected(four_pillar_request):
    payload = _model_payload(four_pillar_request)
    payload["summary"]["claim_type"] = "astrology"
    with pytest.raises(AIReadingGeneratorV2SemanticValidationError):
        _generate(four_pillar_request, payload)


@pytest.mark.parametrize("field", ["detail", "evidence", "interpretation"])
def test_relationship_astrology_blocks_use_relations_and_existing_pillar_fact(
    four_pillar_request, field
):
    payload = _model_payload(four_pillar_request)
    block = _block(
        claim_type="astrology",
        fact_codes=["chart.pillar_sequence"],
        components=["relations"],
    )
    if field in {"detail", "evidence", "interpretation"}:
        if field == "detail":
            payload["sections"][3][field] = block
        else:
            payload["sections"][3][field] = [block]
    result, _ = _generate(four_pillar_request, payload)
    output_block = result.reading["sections"][3][field]
    if field != "detail":
        output_block = output_block[0]
    assert output_block["claim_type"] == "astrology"
    assert output_block["source_components"] == ["relations"]
    assert output_block["source_fact_codes"] == ["chart.pillar_sequence"]


@pytest.mark.parametrize("field", ["detail", "evidence", "interpretation"])
def test_relationship_astrology_blocks_without_fact_are_rejected(
    four_pillar_request, field
):
    payload = _model_payload(four_pillar_request)
    block = _block(claim_type="astrology", components=["relations"])
    if field == "detail":
        payload["sections"][3][field] = block
    else:
        payload["sections"][3][field] = [block]
    with pytest.raises(AIReadingGeneratorV2SemanticValidationError):
        _generate(four_pillar_request, payload)


def test_astrology_with_luck_component_is_rejected(four_pillar_request):
    payload = _model_payload(four_pillar_request)
    payload["sections"][5]["summary"] = _block(
        claim_type="astrology",
        fact_codes=[_first_fact(four_pillar_request)],
        components=["current_luck"],
    )
    with pytest.raises(AIReadingGeneratorV2SemanticValidationError):
        _generate(four_pillar_request, payload)


def test_luck_astrology_without_luck_component_is_rejected(four_pillar_request):
    payload = _model_payload(four_pillar_request)
    payload["sections"][5]["summary"]["claim_type"] = "luck_astrology"
    with pytest.raises(AIReadingGeneratorV2SemanticValidationError):
        _generate(four_pillar_request, payload)


def test_luck_astrology_is_forbidden_in_top_summary(four_pillar_request):
    payload = _model_payload(four_pillar_request)
    payload["summary"] = _block(
        claim_type="luck_astrology",
        components=["current_luck"],
    )
    with pytest.raises(AIReadingGeneratorV2SemanticValidationError):
        generator_v2._validate_semantics(payload, four_pillar_request)


def test_luck_astrology_is_forbidden_in_non_luck_section(four_pillar_request):
    payload = _model_payload(four_pillar_request)
    payload["sections"][0]["summary"] = _block(
        claim_type="luck_astrology",
        components=["current_luck"],
    )
    with pytest.raises(AIReadingGeneratorV2SemanticValidationError):
        generator_v2._validate_semantics(payload, four_pillar_request)


def test_practical_evidence_is_forbidden(four_pillar_request):
    payload = _model_payload(four_pillar_request)
    payload["sections"][0]["evidence"] = [_block()]
    with pytest.raises(AIReadingGeneratorV2SemanticValidationError):
        generator_v2._validate_semantics(payload, four_pillar_request)


def test_current_luck_crosswalk_is_accepted(four_pillar_request):
    payload = _model_payload(four_pillar_request)
    payload["sections"][5]["summary"] = _block(
        claim_type="luck_astrology",
        components=["luck_pillars"],
    )
    result, _ = _generate(four_pillar_request, payload)
    assert result.reading["sections"][5]["summary"]["source_components"] == [
        "luck_pillars"
    ]


def test_provider_transport_yearly_detail_object_is_strict_and_complete(four_pillar_request):
    schema = generator_v2._openai_transport_schema(
        four_pillar_request["model_output_schema"]
    )
    yearly = schema["properties"]["future_flow_yearly"]["items"]
    assert set(yearly["properties"]) == set(yearly["required"])
    assert {"title", "theme", "career", "wealth", "relationships", "caution", "advice"} <= set(yearly["required"])
    assert yearly["additionalProperties"] is False


def test_future_flow_non_yearly_crosswalk_is_accepted(four_pillar_request):
    payload = _model_payload(four_pillar_request)
    payload["sections"][6]["detail"] = _block(
        claim_type="luck_astrology",
        components=["annual_luck"],
    )
    result, _ = _generate(four_pillar_request, payload)
    assert result.reading["sections"][6]["detail"]["source_components"] == [
        "annual_luck"
    ]


def test_future_flow_rejects_luck_pillars_component(four_pillar_request):
    payload = _model_payload(four_pillar_request)
    payload["sections"][6]["summary"] = _block(
        claim_type="luck_astrology",
        components=["luck_pillars"],
    )
    with pytest.raises(AIReadingGeneratorV2SemanticValidationError):
        _generate(four_pillar_request, payload)


def test_yearly_crosswalk_uses_trusted_index_and_year(four_pillar_request):
    payload = _model_payload(four_pillar_request)
    payload["future_flow_yearly"][0]["summary"] = _block(
        claim_type="luck_astrology",
        components=["integrated_luck"],
    )
    result, _ = _generate(four_pillar_request, payload)
    yearly = result.reading["sections"][6]["yearly"]
    assert [item["year"] for item in yearly] == four_pillar_request[
        "trusted_attachments"
    ]["future_flow_years"]
    assert yearly[0]["summary"]["source_components"] == ["integrated_luck"]


def test_multiple_luck_components_are_each_validated(four_pillar_request):
    payload = _model_payload(four_pillar_request)
    payload["sections"][5]["summary"] = _block(
        claim_type="luck_astrology",
        components=["current_luck", "annual_luck", "integrated_luck"],
    )
    result, _ = _generate(four_pillar_request, payload)
    assert result.reading["sections"][5]["summary"]["source_components"] == [
        "current_luck",
        "annual_luck",
        "integrated_luck",
    ]


def test_fixed_trusted_assembly(four_pillar_request):
    result, _ = _generate(four_pillar_request, _model_payload(four_pillar_request))
    reading = result.reading
    assert [
        {"section_id": item["section_id"], "title": item["title"]}
        for item in reading["sections"]
    ] == EXPECTED_SECTION_SLOTS
    assert reading["disclaimer"] == EXPECTED_DISCLAIMER
    assert reading["method"] == "openai_responses_api_v2"
    assert reading["schema_version"] == "ai_reading_v2"
    assert reading["version"] == "ai_reading_v2"
    assert "yearly" not in reading["sections"][0]
    assert "yearly" in reading["sections"][6]


def test_validation_report_is_attached_once_and_non_circular(four_pillar_request):
    result, _ = _generate(four_pillar_request, _model_payload(four_pillar_request))
    assert result.reading["validation"] == VALID_REPORT
    assert tuple(result.reading) == (
        "schema_version",
        "engine_version",
        "summary",
        "sections",
        "long_term_luck",
        "consultation_answer",
        "warnings",
        "uncertainty",
        "source_contracts",
        "disclaimer",
        "validation",
        "method",
        "version",
        "status",
    )


def test_candidate_validation_rejects_trusted_year_mutation(four_pillar_request):
    payload = _model_payload(four_pillar_request)
    candidate = generator_v2._assemble_candidate(payload, four_pillar_request)
    candidate["sections"][6]["yearly"][0]["year"] += 1
    report = generator_v2._validate_candidate(candidate, four_pillar_request)
    assert report["valid"] is False
    with pytest.raises(AIReadingGeneratorV2CandidateValidationError):
        raise AIReadingGeneratorV2CandidateValidationError(report)


def test_candidate_validation_rechecks_model_owned_blocks(four_pillar_request):
    payload = _model_payload(four_pillar_request)
    candidate = generator_v2._assemble_candidate(payload, four_pillar_request)
    candidate["sections"][0]["summary"]["claim_type"] = "astrology"
    report = generator_v2._validate_candidate(candidate, four_pillar_request)
    assert report["valid"] is False
    assert any("at least one fact ref" in error for error in report["errors"])


def test_inputs_request_and_model_payload_are_not_mutated(four_pillar_request):
    request = deepcopy(four_pillar_request)
    payload = _model_payload(request)
    request_before = deepcopy(request)
    payload_before = deepcopy(payload)
    client = FakeClient(payload)
    generate_ai_reading_v2(request, client=client, model="test-model")
    assert request == request_before
    assert payload == payload_before


def test_result_to_dict_isolation(four_pillar_request):
    result, _ = _generate(four_pillar_request, _model_payload(four_pillar_request))
    serialized = result.to_dict()
    serialized["reading"]["sections"].clear()
    serialized["usage"]["total_tokens"] = 0
    assert len(result.reading["sections"]) == 8
    assert result.usage["total_tokens"] == 30


def test_provider_failure_is_wrapped_without_retry(four_pillar_request):
    client = FakeClient({}, failure=RuntimeError("provider down"))
    with pytest.raises(AIReadingGeneratorV2ProviderError):
        generate_ai_reading_v2(
            deepcopy(four_pillar_request),
            client=client,
            model="test-model",
        )
    assert len(client.responses.calls) == 1


def test_unusable_provider_response_is_rejected(four_pillar_request):
    class EmptyResponses:
        def __init__(self):
            self.calls = 0

        def create(self, **kwargs):
            self.calls += 1
            return SimpleNamespace(
                id="resp_empty",
                status="incomplete",
                output_text="",
                output=[],
                usage=None,
            )

    responses = EmptyResponses()
    client = SimpleNamespace(responses=responses)
    with pytest.raises(AIReadingGeneratorV2ResponseError):
        generate_ai_reading_v2(
            deepcopy(four_pillar_request),
            client=client,
            model="test-model",
        )
    assert responses.calls == 1


def test_incomplete_partial_output_is_not_misclassified_as_invalid_json(
    four_pillar_request,
):
    secret = "PARTIAL_PROVIDER_OUTPUT_SECRET"

    class IncompleteResponses:
        def __init__(self):
            self.calls = 0

        def create(self, **_kwargs):
            self.calls += 1
            return SimpleNamespace(
                id="resp_incomplete",
                status="incomplete",
                incomplete_details=SimpleNamespace(reason="max_output_tokens"),
                output_text='{"summary":"' + secret,
                output=[],
                usage=None,
            )

    responses = IncompleteResponses()
    with pytest.raises(AIReadingGeneratorV2ResponseError) as captured:
        generate_ai_reading_v2(
            deepcopy(four_pillar_request),
            client=SimpleNamespace(responses=responses),
            model="test-model",
        )
    error = captured.value
    assert type(error) is AIReadingGeneratorV2ResponseError
    assert str(error) == "provider response is incomplete: max_output_tokens"
    assert secret not in str(error)
    assert responses.calls == 1


def test_completed_sdk_output_fallback_extracts_structured_text(
    four_pillar_request,
):
    payload = _transport_payload(_model_payload(four_pillar_request))
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    class SDKLikeResponses:
        def __init__(self):
            self.calls = 0

        def create(self, **_kwargs):
            self.calls += 1
            return SimpleNamespace(
                id="resp_sdk_shape",
                status="completed",
                output_text="",
                output=[
                    SimpleNamespace(type="reasoning", content=[]),
                    SimpleNamespace(
                        type="message",
                        content=[SimpleNamespace(type="output_text", text=text)],
                    ),
                ],
                usage=None,
            )

    responses = SDKLikeResponses()
    result = generate_ai_reading_v2(
        deepcopy(four_pillar_request),
        client=SimpleNamespace(responses=responses),
        model="test-model",
    )
    assert result.reading["status"] == "completed"
    assert responses.calls == 1


def test_structured_output_refusal_is_rejected_without_retaining_text(
    four_pillar_request,
):
    secret = "REFUSAL_PROVIDER_TEXT_SECRET"

    class RefusalResponses:
        def create(self, **_kwargs):
            return SimpleNamespace(
                id="resp_refusal",
                status="completed",
                output_text="",
                output=[
                    SimpleNamespace(
                        type="message",
                        content=[SimpleNamespace(type="refusal", refusal=secret)],
                    )
                ],
                usage=None,
            )

    with pytest.raises(AIReadingGeneratorV2ResponseError) as captured:
        generate_ai_reading_v2(
            deepcopy(four_pillar_request),
            client=SimpleNamespace(responses=RefusalResponses()),
            model="test-model",
        )
    assert type(captured.value) is AIReadingGeneratorV2ResponseError
    assert str(captured.value) == "provider response contains a refusal"
    assert secret not in str(captured.value)


def test_generator_source_has_no_repair_quality_or_astrology_calculation_calls():
    source = inspect.getsource(generator_v2)
    forbidden_imports = (
        "engine.reading_quality",
        "engine.reading_repair",
        "engine.chart",
        "engine.pillars",
        "engine.strength",
        "engine.luck",
    )
    assert all(item not in source for item in forbidden_imports)
    assert "retry" not in source.lower()
    assert "keyword" not in source.lower()
    assert "heuristic" not in source.lower()


def test_claim_type_text_mismatch_is_not_nlp_classified(four_pillar_request):
    payload = _model_payload(four_pillar_request)
    payload["summary"]["text"] = "今年は仕事運が上がります"
    payload["summary"]["claim_type"] = "practical"
    result, _ = _generate(four_pillar_request, payload)
    assert result.reading["summary"]["claim_type"] == "practical"
    assert result.reading["summary"]["text"] == "今年は仕事運が上がります"


def test_existing_v1_generator_is_not_imported():
    source = inspect.getsource(generator_v2)
    assert "engine.reading_generator import" not in source
