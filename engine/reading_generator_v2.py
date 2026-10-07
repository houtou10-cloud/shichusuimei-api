"""AI Reading v2 generation, validation, and trusted assembly.

This module consumes the canonical request produced by
``engine.reading_prompt_v2``.  It invokes the Responses API exactly once,
validates the model-owned payload, and attaches trusted fields without
performing astrology calculations, prose repair, or Quality Gate checks.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
import json
import os
import time
from typing import Any, Callable

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from engine.reading_prompt_v2 import (
    AI_READING_V2_LONG_TERM_LUCK_COUNT,
    AI_READING_V2_SECTION_SLOTS,
    AI_READING_REQUEST_V2_FIELDS,
    AI_READING_V2_USER_PROMPT_PREFIX,
    build_ai_reading_request_v2,
    build_provider_model_input_v2,
)


READING_GENERATOR_V2_VERSION = "reading_generator_v2"
READING_GENERATOR_V2_METHOD = "openai_responses_api_v2"
OPENAI_READING_MODEL_ENV = "OPENAI_READING_MODEL"
DEFAULT_OPENAI_MODEL = "gpt-5"
DEFAULT_MAX_OUTPUT_TOKENS = 25000
DEFAULT_REASONING_EFFORT = "low"
SUPPORTED_REASONING_EFFORTS = ("minimal", "low", "medium", "high")
DEFAULT_STORE = False
JSON_SCHEMA_NAME = "ai_reading_v2"

_FINAL_FIELDS_WITHOUT_VALIDATION = (
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
    "method",
    "version",
    "status",
)
_FINAL_FIELDS = (
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
_VALIDATION_FIELDS = (
    "valid",
    "errors",
    "missing_required_fields",
    "unknown_fields",
)
_MODEL_SECTION_FIELDS = (
    "facts",
    "summary",
    "detail",
    "evidence",
    "interpretation",
    "advice",
    "warnings",
    "uncertainty",
)
_LUCK_COMPONENTS = frozenset(
    ("luck_pillars", "current_luck", "annual_luck", "integrated_luck")
)
_CURRENT_LUCK_PATHS = {
    "luck_pillars": "luck.luck_pillars",
    "current_luck": "luck.current_luck",
    "annual_luck": "luck.annual_luck",
    "integrated_luck": "luck.integrated_luck",
}
_FUTURE_LUCK_COMPONENTS = frozenset(
    ("current_luck", "annual_luck", "integrated_luck")
)
_SECTION_IDS = tuple(section_id for section_id, _title in AI_READING_V2_SECTION_SLOTS)


class AIReadingGeneratorV2Error(RuntimeError):
    """Base error for AI Reading v2 generation."""


class AIReadingGeneratorV2ConfigurationError(AIReadingGeneratorV2Error):
    """Provider or generator configuration is invalid."""


class AIReadingGeneratorV2RequestValidationError(AIReadingGeneratorV2Error):
    """The supplied trusted request is not canonical."""


class AIReadingGeneratorV2ProviderError(AIReadingGeneratorV2Error):
    """The model provider call failed."""


class AIReadingGeneratorV2ResponseError(AIReadingGeneratorV2Error):
    """The provider response cannot be consumed."""


class AIReadingGeneratorV2JSONError(AIReadingGeneratorV2ResponseError):
    """The model output is not a strict top-level JSON object."""


class _ValidationFailure(AIReadingGeneratorV2Error):
    """Base class for deterministic validation failures."""

    def __init__(self, message: str, issues: Sequence[str]) -> None:
        self.issues = tuple(issues)
        suffix = "; ".join(self.issues)
        super().__init__(f"{message}: {suffix}" if suffix else message)


class AIReadingGeneratorV2StructuralValidationError(_ValidationFailure):
    """The model output violates its Draft 2020-12 schema."""


class AIReadingGeneratorV2SemanticValidationError(_ValidationFailure):
    """The model output violates claim/reference semantics."""


class AIReadingGeneratorV2CandidateValidationError(_ValidationFailure):
    """The deterministically assembled final candidate is invalid."""

    def __init__(self, report: Mapping[str, Any]) -> None:
        self.report = deepcopy(dict(report))
        super().__init__("AI Reading v2 final candidate is invalid", report["errors"])


@dataclass(frozen=True)
class AIReadingGenerationResultV2:
    """Successful v2 reading plus normalized provider metadata."""

    reading: dict[str, Any]
    model: str
    response_id: str | None
    response_status: str | None
    usage: dict[str, Any]
    method: str = READING_GENERATOR_V2_METHOD
    status: str = "completed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "reading": deepcopy(self.reading),
            "model": self.model,
            "response_id": self.response_id,
            "response_status": self.response_status,
            "usage": deepcopy(self.usage),
            "method": self.method,
            "status": self.status,
        }


def _canonical_request(request: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(request, Mapping):
        raise TypeError("request must be a Mapping")
    if tuple(request) != AI_READING_REQUEST_V2_FIELDS:
        raise AIReadingGeneratorV2RequestValidationError(
            "request fields/order do not match ai_reading_request_v2"
        )
    model_input = request.get("model_input")
    if not isinstance(model_input, Mapping):
        raise AIReadingGeneratorV2RequestValidationError(
            "request.model_input must be a Mapping"
        )
    reading_context = model_input.get("reading_context")
    judgment_metadata = model_input.get("judgment_metadata")
    try:
        expected = build_ai_reading_request_v2(
            reading_context,
            judgment_metadata,
            sections=None,
            language=request.get("language"),
            tone=request.get("tone"),
        )
    except Exception as exc:
        raise AIReadingGeneratorV2RequestValidationError(
            "embedded prompt inputs cannot rebuild a canonical request"
        ) from exc
    actual = dict(request)
    if actual != expected:
        raise AIReadingGeneratorV2RequestValidationError(
            "request does not exactly match its canonical trusted rebuild"
        )
    try:
        actual_serialized = json.dumps(
            actual,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=False,
            allow_nan=False,
        )
        expected_serialized = json.dumps(
            expected,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=False,
            allow_nan=False,
        )
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        raise AIReadingGeneratorV2RequestValidationError(
            "request cannot be serialized for canonical order validation"
        ) from exc
    if actual_serialized != expected_serialized:
        raise AIReadingGeneratorV2RequestValidationError(
            "request key order does not match its canonical trusted rebuild"
        )
    return deepcopy(expected)


def _non_empty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AIReadingGeneratorV2ConfigurationError(
            f"{field} must be a non-empty string"
        )
    return value.strip()


def _resolve_model(model: str | None) -> str:
    if model is not None:
        return _non_empty_string(model, "model")
    configured = os.getenv(OPENAI_READING_MODEL_ENV)
    return configured.strip() if configured and configured.strip() else DEFAULT_OPENAI_MODEL


def _create_openai_client(*, api_key: str | None = None) -> Any:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise AIReadingGeneratorV2ConfigurationError(
            "OpenAI Python SDK is not installed"
        ) from exc
    try:
        if api_key is not None:
            return OpenAI(api_key=_non_empty_string(api_key, "api_key"))
        return OpenAI()
    except Exception as exc:
        raise AIReadingGeneratorV2ConfigurationError(
            "OpenAI client initialization failed"
        ) from exc


def _provider_payload(
    request: Mapping[str, Any],
    *,
    model: str,
    max_output_tokens: int,
    reasoning_effort: str,
    store: bool,
) -> dict[str, Any]:
    if isinstance(max_output_tokens, bool) or not isinstance(max_output_tokens, int):
        raise TypeError("max_output_tokens must be an integer")
    if max_output_tokens <= 0:
        raise ValueError("max_output_tokens must be positive")
    if reasoning_effort not in SUPPORTED_REASONING_EFFORTS:
        raise ValueError("unsupported reasoning_effort")
    if not isinstance(store, bool):
        raise TypeError("store must be bool")
    messages = request["messages"]
    # The canonical request retains the complete trusted metadata for local
    # validation.  Only the provider transport receives the compact
    # projection, avoiding duplicated evidence trees in the prompt.
    provider_model_input = build_provider_model_input_v2(request["model_input"])
    provider_user_content = AI_READING_V2_USER_PROMPT_PREFIX + json.dumps(
        provider_model_input,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=False,
        allow_nan=False,
    )
    return {
        "model": model,
        "instructions": messages[0]["content"],
        "input": [{"role": "user", "content": provider_user_content}],
        "max_output_tokens": max_output_tokens,
        "reasoning": {"effort": reasoning_effort},
        "store": store,
        "text": {
            "format": {
                "type": "json_schema",
                "name": JSON_SCHEMA_NAME,
                "schema": _openai_transport_schema(request["model_output_schema"]),
                "strict": True,
            }
        },
    }


def _without_openai_unsupported_unique_items(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            key: _without_openai_unsupported_unique_items(item)
            for key, item in value.items()
            if key != "uniqueItems"
        }
    if isinstance(value, list):
        return [_without_openai_unsupported_unique_items(item) for item in value]
    return deepcopy(value)


def _transport_block_schema(
    canonical_block_schema: Mapping[str, Any],
    canonical_claim_types: Sequence[str],
    *,
    location_kind: str,
    section_id: str | None,
    field: str,
) -> dict[str, Any]:
    # Provider-owned blocks contain only prose and the minimum grounding
    # association.  Warning/uncertainty IDs are trusted catalog metadata and
    # are reconstructed locally after decode; asking the model to repeat them
    # for every block adds substantial structured-output overhead.
    canonical_properties = canonical_block_schema["properties"]
    result = {
        "type": "object",
        "properties": {
            "t": deepcopy(canonical_properties["text"]),
            "k": deepcopy(canonical_properties["claim_type"]),
            "f": deepcopy(canonical_properties["source_fact_codes"]),
            "c": deepcopy(canonical_properties["source_components"]),
        },
        "required": [
            "t",
            "k",
            "f",
            "c",
        ],
        "additionalProperties": False,
    }
    allowed = _allowed_claim_types(location_kind, section_id, field)
    result["properties"]["k"]["enum"] = [
        claim_type
        for claim_type in canonical_claim_types
        if claim_type in allowed
    ]
    return result


def _transport_section_schema(
    canonical_section_schema: Mapping[str, Any],
    canonical_block_schema: Mapping[str, Any],
    canonical_claim_types: Sequence[str],
    *,
    section_id: str,
) -> dict[str, Any]:
    result = deepcopy(dict(canonical_section_schema))
    properties = result["properties"]
    for field in ("summary", "detail"):
        properties[field] = _transport_block_schema(
            canonical_block_schema,
            canonical_claim_types,
            location_kind="section",
            section_id=section_id,
            field=field,
        )
    for field in ("evidence", "interpretation", "advice"):
        properties[field]["items"] = _transport_block_schema(
            canonical_block_schema,
            canonical_claim_types,
            location_kind="section",
            section_id=section_id,
            field=field,
        )
    return result


def _transport_long_term_schema(
    canonical_schema: Mapping[str, Any],
    canonical_block_schema: Mapping[str, Any],
    canonical_claim_types: Sequence[str],
) -> dict[str, Any]:
    result = deepcopy(dict(canonical_schema))
    for field in ("title", "theme", "career", "wealth", "relationships", "caution"):
        result["properties"][field] = _transport_block_schema(
            canonical_block_schema, canonical_claim_types,
            location_kind="long_term", section_id="long_term_luck", field=field,
        )
    result["properties"]["advice"]["items"] = _transport_block_schema(
        canonical_block_schema, canonical_claim_types,
        location_kind="long_term", section_id="long_term_luck", field="advice",
    )
    return result


def _openai_transport_schema(canonical_schema: Mapping[str, Any]) -> dict[str, Any]:
    """Build the approved OpenAI-only encoding of the canonical model schema."""

    canonical = deepcopy(dict(canonical_schema))
    canonical_definitions = canonical["$defs"]
    canonical_block = canonical_definitions["grounded_text_block"]
    canonical_section = canonical_definitions["model_section_payload"]
    canonical_year = canonical_definitions["model_year_payload"]
    canonical_long_term = canonical_definitions["long_term_luck_payload"]
    canonical_claim_types = canonical_block["properties"]["claim_type"]["enum"]

    definitions = {
        name: deepcopy(canonical_definitions[name])
        for name in (
            "fact_code_array",
            "source_component_array",
            "warning_id_array",
            "uncertainty_id_array",
        )
    }
    section_properties = {
        section_id: _transport_section_schema(
            canonical_section,
            canonical_block,
            canonical_claim_types,
            section_id=section_id,
        )
        for section_id in _SECTION_IDS
    }
    year_schema = deepcopy(canonical_year)
    for field in (
        "title", "theme", "career", "wealth", "relationships", "caution",
        "summary", "detail",
    ):
        year_schema["properties"][field] = _transport_block_schema(
            canonical_block,
            canonical_claim_types,
            location_kind="yearly",
            section_id="future_flow",
            field=field,
        )
    advice_schema = year_schema["properties"]["advice"]
    advice_schema["items"] = _transport_block_schema(
        canonical_block,
        canonical_claim_types,
        location_kind="yearly",
        section_id="future_flow",
        field="advice",
    )
    # OpenAI strict structured outputs require every property of an object to
    # be listed in required.  The canonical yearly payload keeps the new
    # detail fields additive for local/legacy compatibility; the provider
    # projection makes that object strict without mutating the canonical copy.
    year_schema["required"] = list(year_schema["properties"])
    long_term_schema = _transport_long_term_schema(
        canonical_long_term, canonical_block, canonical_claim_types
    )

    properties = canonical["properties"]
    transport_properties = {
        "summary": _transport_block_schema(
            canonical_block,
            canonical_claim_types,
            location_kind="top",
            section_id=None,
            field="summary",
        ),
        "sections": {
            "type": "object",
            "properties": section_properties,
            "required": list(_SECTION_IDS),
            "additionalProperties": False,
        },
        "future_flow_yearly": {
            **deepcopy(properties["future_flow_yearly"]),
            "items": year_schema,
        },
        "long_term_luck": {
            **deepcopy(properties["long_term_luck"]),
            "items": long_term_schema,
        },
        "consultation_answer": (
            _transport_block_schema(
                canonical_block,
                canonical_claim_types,
                location_kind="consultation",
                section_id=None,
                field="consultation_answer",
            )
            if properties["consultation_answer"].get("type") != "null"
            else {"type": "null"}
        ),
    }
    transport = {
        "$defs": definitions,
        "type": "object",
        "properties": transport_properties,
        "required": deepcopy(canonical["required"]),
        "additionalProperties": False,
    }
    return _without_openai_unsupported_unique_items(transport)


def _decode_openai_transport_payload(
    transport_payload: Mapping[str, Any],
    canonical_schema: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Decode only the approved fixed-key section container representation."""

    sections = transport_payload["sections"]
    result = deepcopy(dict(transport_payload))
    result["sections"] = [deepcopy(sections[section_id]) for section_id in _SECTION_IDS]

    def restore_block_metadata(value: Any) -> Any:
        if isinstance(value, Mapping):
            if {"t", "k", "f", "c"}.issubset(value):
                restored = {
                    "text": restore_block_metadata(value["t"]),
                    "claim_type": restore_block_metadata(value["k"]),
                    "source_fact_codes": restore_block_metadata(value["f"]),
                    "source_components": restore_block_metadata(value["c"]),
                }
                restored.setdefault("warnings", [])
                restored.setdefault("uncertainty", [])
                return restored
            if {"text", "claim_type", "source_fact_codes", "source_components"}.issubset(value):
                restored = {key: restore_block_metadata(item) for key, item in value.items()}
                restored.setdefault("warnings", [])
                restored.setdefault("uncertainty", [])
                return restored
            return {key: restore_block_metadata(item) for key, item in value.items()}
        if isinstance(value, list):
            return [restore_block_metadata(item) for item in value]
        return value

    result = restore_block_metadata(result)
    return result


def _call_provider(client: Any, payload: Mapping[str, Any]) -> Any:
    responses = getattr(client, "responses", None)
    create = getattr(responses, "create", None)
    if not callable(create):
        raise AIReadingGeneratorV2ConfigurationError(
            "client.responses.create is unavailable"
        )
    try:
        return create(**deepcopy(dict(payload)))
    except Exception as exc:
        raise AIReadingGeneratorV2ProviderError(
            f"OpenAI Responses API call failed: {type(exc).__name__}: {exc}"
        ) from exc


def _get(value: Any, name: str, default: Any = None) -> Any:
    return value.get(name, default) if isinstance(value, Mapping) else getattr(value, name, default)


def _validate_provider_response_state(response: Any) -> None:
    status = _get(response, "status")
    if status == "incomplete":
        details = _get(response, "incomplete_details")
        reason = _get(details, "reason") if details is not None else None
        if reason == "max_output_tokens":
            raise AIReadingGeneratorV2ResponseError(
                "provider response is incomplete: max_output_tokens"
            )
        raise AIReadingGeneratorV2ResponseError("provider response is incomplete")
    if isinstance(status, str) and status != "completed":
        raise AIReadingGeneratorV2ResponseError("provider response is not completed")

    output = _get(response, "output", [])
    if not isinstance(output, (list, tuple)):
        return
    for item in output:
        content = _get(item, "content", [])
        if not isinstance(content, (list, tuple)):
            continue
        for content_item in content:
            if _get(content_item, "type") == "refusal":
                raise AIReadingGeneratorV2ResponseError(
                    "provider response contains a refusal"
                )


def _extract_output_text(response: Any) -> str:
    _validate_provider_response_state(response)
    direct = _get(response, "output_text")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()
    parts: list[str] = []
    output = _get(response, "output", [])
    if isinstance(output, (list, tuple)):
        for item in output:
            content = _get(item, "content", [])
            if not isinstance(content, (list, tuple)):
                continue
            for content_item in content:
                text = _get(content_item, "text")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
    if parts:
        return "\n".join(parts)
    raise AIReadingGeneratorV2ResponseError(
        "provider response contains no usable model output"
    )


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant: {value}")


def _parse_model_json(text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(text, parse_constant=_reject_json_constant)
    except (json.JSONDecodeError, ValueError) as exc:
        raise AIReadingGeneratorV2JSONError(
            "model output is not strict JSON"
        ) from exc
    if not isinstance(parsed, dict):
        raise AIReadingGeneratorV2JSONError(
            "model output top level must be an object"
        )
    return parsed


def _json_pointer(path: Sequence[Any]) -> str:
    if not path:
        return ""
    return "/" + "/".join(
        str(segment).replace("~", "~0").replace("/", "~1")
        for segment in path
    )


def _validate_structure(payload: Mapping[str, Any], schema: Mapping[str, Any]) -> None:
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        raise AIReadingGeneratorV2StructuralValidationError(
            "model_output_schema is invalid",
            (str(exc),),
        ) from exc
    validator = Draft202012Validator(schema)
    errors = sorted(
        validator.iter_errors(payload),
        key=lambda error: (
            _json_pointer(error.absolute_path),
            _json_pointer(error.absolute_schema_path),
            str(error.validator),
            error.message,
        ),
    )
    if errors:
        issues = tuple(
            "instance="
            + _json_pointer(error.absolute_path)
            + "; schema="
            + _json_pointer(error.absolute_schema_path)
            + f"; validator={error.validator}; message={error.message}"
            for error in errors
        )
        raise AIReadingGeneratorV2StructuralValidationError(
            "model payload failed Draft 2020-12 validation",
            issues,
        )


def _iter_blocks(
    payload: Mapping[str, Any],
    request: Mapping[str, Any],
):
    yield "/summary", payload["summary"], "top", None, None, "summary"
    slots = request["trusted_attachments"]["sections"]
    for index, section in enumerate(payload["sections"]):
        section_id = slots[index]["section_id"]
        for field in ("summary", "detail"):
            yield f"/sections/{index}/{field}", section[field], "section", section_id, None, field
        for field in ("evidence", "interpretation", "advice"):
            for item_index, block in enumerate(section[field]):
                yield (
                    f"/sections/{index}/{field}/{item_index}",
                    block,
                    "section",
                    section_id,
                    None,
                    field,
                )
    for index, year_payload in enumerate(payload["future_flow_yearly"]):
        for field in (
            "title", "theme", "career", "wealth", "relationships", "caution",
            "summary", "detail",
        ):
            if field not in year_payload:
                continue
            yield (
                f"/future_flow_yearly/{index}/{field}",
                year_payload[field],
                "yearly",
                "future_flow",
                index,
                field,
            )
        for advice_index, block in enumerate(year_payload.get("advice", [])):
            yield (
                f"/future_flow_yearly/{index}/advice/{advice_index}", block,
                "yearly", "future_flow", index, "advice",
            )
    for index, detail in enumerate(payload["long_term_luck"]):
        for field in ("title", "theme", "career", "wealth", "relationships", "caution"):
            yield (
                f"/long_term_luck/{index}/{field}", detail[field],
                "long_term", "long_term_luck", index, field,
            )
        for advice_index, block in enumerate(detail["advice"]):
            yield (
                f"/long_term_luck/{index}/advice/{advice_index}", block,
                "long_term", "long_term_luck", index, "advice",
            )
    if payload["consultation_answer"] is not None:
        yield (
            "/consultation_answer",
            payload["consultation_answer"],
            "consultation",
            None,
            None,
            "consultation_answer",
        )


def _allowed_claim_types(
    location_kind: str,
    section_id: str | None,
    field: str,
) -> frozenset[str]:
    if location_kind in ("top", "consultation"):
        return frozenset(("practical", "astrology"))
    if location_kind == "yearly":
        return frozenset(("practical", "astrology", "luck_astrology"))
    if location_kind == "long_term":
        return frozenset(("luck_astrology", "practical"))
    luck_section = section_id in ("current_luck", "future_flow")
    if field in ("evidence", "interpretation"):
        return (
            frozenset(("astrology", "luck_astrology"))
            if luck_section
            else frozenset(("astrology",))
        )
    return (
        frozenset(("practical", "astrology", "luck_astrology"))
        if luck_section
        else frozenset(("practical", "astrology"))
    )


def _validate_luck_component(
    component: str,
    *,
    location_kind: str,
    section_id: str | None,
    year_index: int | None,
    request: Mapping[str, Any],
) -> bool:
    entries = request["trusted_catalogs"]["luck_value_sources"]
    years = request["trusted_attachments"]["future_flow_years"]
    if location_kind == "section" and section_id == "current_luck":
        expected_path = _CURRENT_LUCK_PATHS.get(component)
        matches = [
            entry
            for entry in entries
            if entry["section_id"] == "current_luck"
            and entry["year"] is None
            and entry["source_component"] == component
            and entry["context_path"] == expected_path
        ]
        return expected_path is not None and len(matches) == 1
    if location_kind == "section" and section_id == "future_flow":
        if component not in _FUTURE_LUCK_COMPONENTS:
            return False
        matches = [
            entry
            for entry in entries
            if entry["section_id"] == "future_flow"
            and entry["source_component"] == component
        ]
        if not matches:
            return False
        expected = [
            (year, f"luck.five_year_luck[{index}].{component}")
            for index, year in enumerate(years)
        ]
        actual = [(entry["year"], entry["context_path"]) for entry in matches]
        return actual == [item for item in expected if item in actual]
    if location_kind == "yearly" and year_index is not None:
        if component not in _FUTURE_LUCK_COMPONENTS or year_index >= len(years):
            return False
        expected_year = years[year_index]
        expected_path = f"luck.five_year_luck[{year_index}].{component}"
        matches = [
            entry
            for entry in entries
            if entry["section_id"] == "future_flow"
            and entry["year"] == expected_year
            and entry["source_component"] == component
            and entry["context_path"] == expected_path
        ]
        return len(matches) == 1
    if location_kind == "long_term" and year_index is not None:
        pillars = request["trusted_attachments"]["long_term_luck_pillars"]
        if component != "luck_pillars" or year_index >= len(pillars):
            return False
        pillar = pillars[year_index]
        return any(
            entry["section_id"] == "long_term_luck"
            and entry["year"] == pillar["index"]
            and entry["source_component"] == "luck_pillars"
            and entry["context_path"] == f"luck.luck_pillars.pillars[{year_index}]"
            for entry in entries
        )
    return False


def _validate_semantics(
    payload: Mapping[str, Any],
    request: Mapping[str, Any],
) -> None:
    catalogs = request["trusted_catalogs"]
    fact_codes = set(catalogs["fact_codes"])
    components = set(catalogs["source_components"])
    warning_ids = {entry["warning_id"] for entry in catalogs["warnings"]}
    uncertainty_ids = {
        entry["uncertainty_id"] for entry in catalogs["uncertainty"]
    }
    issues: list[str] = []

    def require_refs(path: str, block: Mapping[str, Any]) -> None:
        for code in block["source_fact_codes"]:
            if code not in fact_codes:
                issues.append(f"{path}/source_fact_codes: unknown fact {code!r}")
        for component in block["source_components"]:
            if component not in components:
                issues.append(f"{path}/source_components: unknown component {component!r}")
        for warning_id in block["warnings"]:
            if warning_id not in warning_ids:
                issues.append(f"{path}/warnings: unknown warning ID {warning_id!r}")
        for uncertainty_id in block["uncertainty"]:
            if uncertainty_id not in uncertainty_ids:
                issues.append(
                    f"{path}/uncertainty: unknown uncertainty ID {uncertainty_id!r}"
                )

    for index, section in enumerate(payload["sections"]):
        for code in section["facts"]:
            if code not in fact_codes:
                issues.append(f"/sections/{index}/facts: unknown fact {code!r}")
        for warning_id in section["warnings"]:
            if warning_id not in warning_ids:
                issues.append(f"/sections/{index}/warnings: unknown warning ID {warning_id!r}")
        for uncertainty_id in section["uncertainty"]:
            if uncertainty_id not in uncertainty_ids:
                issues.append(
                    f"/sections/{index}/uncertainty: unknown uncertainty ID {uncertainty_id!r}"
                )

    for path, block, kind, section_id, year_index, field in _iter_blocks(payload, request):
        require_refs(path, block)
        claim_type = block["claim_type"]
        if claim_type not in _allowed_claim_types(kind, section_id, field):
            issues.append(f"{path}/claim_type: {claim_type!r} is forbidden at this location")
        fact_refs = block["source_fact_codes"]
        component_refs = block["source_components"]
        luck_refs = [item for item in component_refs if item in _LUCK_COMPONENTS]
        if claim_type == "practical":
            if fact_refs or component_refs:
                issues.append(f"{path}: practical blocks require empty fact/component refs")
        elif claim_type == "astrology":
            if not fact_refs:
                issues.append(f"{path}: astrology blocks require at least one fact ref")
            if luck_refs:
                issues.append(f"{path}: astrology blocks cannot use luck components")
        elif claim_type == "luck_astrology":
            if not luck_refs:
                issues.append(
                    f"{path}: luck_astrology blocks require at least one luck component"
                )
            for component in luck_refs:
                if not _validate_luck_component(
                    component,
                    location_kind=kind,
                    section_id=section_id,
                    year_index=year_index,
                    request=request,
                ):
                    issues.append(
                        f"{path}/source_components: luck crosswalk mismatch for {component!r}"
                    )

    if issues:
        raise AIReadingGeneratorV2SemanticValidationError(
            "model payload failed semantic validation",
            tuple(sorted(issues)),
        )


def _assemble_candidate(
    payload: Mapping[str, Any],
    request: Mapping[str, Any],
) -> dict[str, Any]:
    attachments = request["trusted_attachments"]
    sections: list[dict[str, Any]] = []
    for index, model_section in enumerate(payload["sections"]):
        slot = attachments["sections"][index]
        assembled = {
            "section_id": slot["section_id"],
            "title": slot["title"],
        }
        for field in _MODEL_SECTION_FIELDS:
            assembled[field] = deepcopy(model_section[field])
        if slot["section_id"] == "future_flow":
            assembled["yearly"] = [
                {
                    "year": attachments["future_flow_years"][year_index],
                    "summary": deepcopy(year_payload["summary"]),
                    "detail": deepcopy(year_payload["detail"]),
                }
                | {
                    field: deepcopy(year_payload[field])
                    for field in (
                        "title", "theme", "career", "wealth", "relationships",
                        "caution", "advice",
                    )
                    if field in year_payload
                }
                for year_index, year_payload in enumerate(
                    payload["future_flow_yearly"]
                )
            ]
        sections.append(assembled)
    long_term_luck = []
    long_term_fields = ("title", "theme", "career", "wealth", "relationships", "caution", "advice")
    for index, model_detail in enumerate(payload["long_term_luck"]):
        pillar = attachments["long_term_luck_pillars"][index]
        item = {
            "index": pillar["index"],
            "ganzhi": pillar["ganzhi"],
            "start_age": pillar["start_age"],
            "end_age": pillar["end_age"],
            "stem_ten_god": pillar["stem_ten_god"],
            "stem_element": pillar["stem_element"],
            "branch_element": pillar["branch_element"],
        }
        for field in long_term_fields:
            item[field] = deepcopy(model_detail[field])
        long_term_luck.append(item)
    return {
        "schema_version": attachments["final_schema_version"],
        "engine_version": deepcopy(attachments["engine_version"]),
        "summary": deepcopy(payload["summary"]),
        "sections": sections,
        "long_term_luck": long_term_luck,
        "consultation_answer": deepcopy(payload["consultation_answer"]),
        "warnings": deepcopy(request["trusted_catalogs"]["warnings"]),
        "uncertainty": deepcopy(request["trusted_catalogs"]["uncertainty"]),
        "source_contracts": deepcopy(request["source_contracts"]),
        "disclaimer": attachments["disclaimer"],
        "method": attachments["final_method"],
        "version": attachments["final_version"],
        "status": attachments["final_status"],
    }


def _validate_candidate(
    candidate: Mapping[str, Any],
    request: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    missing = [field for field in _FINAL_FIELDS_WITHOUT_VALIDATION if field not in candidate]
    unknown = [field for field in candidate if field not in _FINAL_FIELDS_WITHOUT_VALIDATION]
    attachments = request["trusted_attachments"]
    exact_values = {
        "schema_version": attachments["final_schema_version"],
        "engine_version": attachments["engine_version"],
        "warnings": request["trusted_catalogs"]["warnings"],
        "uncertainty": request["trusted_catalogs"]["uncertainty"],
        "source_contracts": request["source_contracts"],
        "disclaimer": attachments["disclaimer"],
        "method": attachments["final_method"],
        "version": attachments["final_version"],
        "status": attachments["final_status"],
    }
    for field, expected in exact_values.items():
        if field in candidate and candidate[field] != expected:
            errors.append(f"/{field}: trusted value mismatch")
    sections = candidate.get("sections")
    if not isinstance(sections, list) or len(sections) != 8:
        errors.append("/sections: must contain exactly 8 sections")
    else:
        for index, slot in enumerate(attachments["sections"]):
            section = sections[index]
            if not isinstance(section, Mapping):
                errors.append(f"/sections/{index}: must be an object")
                continue
            expected_fields = (
                ("section_id", "title")
                + _MODEL_SECTION_FIELDS
                + (("yearly",) if slot["section_id"] == "future_flow" else ())
            )
            if tuple(section) != expected_fields:
                errors.append(f"/sections/{index}: exact field shape mismatch")
            if section.get("section_id") != slot["section_id"]:
                errors.append(f"/sections/{index}/section_id: trusted value mismatch")
            if section.get("title") != slot["title"]:
                errors.append(f"/sections/{index}/title: trusted value mismatch")
            if slot["section_id"] == "future_flow":
                yearly = section.get("yearly")
                years = attachments["future_flow_years"]
                if not isinstance(yearly, list) or len(yearly) != len(years):
                    errors.append("/sections/6/yearly: trusted cardinality mismatch")
                elif [entry.get("year") for entry in yearly] != years:
                    errors.append("/sections/6/yearly: trusted year/order mismatch")

    long_term = candidate.get("long_term_luck")
    pillars = attachments["long_term_luck_pillars"]
    if not isinstance(long_term, list) or len(long_term) != len(pillars):
        errors.append("/long_term_luck: trusted cardinality mismatch")
    elif [item.get("index") for item in long_term] != [item["index"] for item in pillars]:
        errors.append("/long_term_luck: trusted order mismatch")

    try:
        reconstructed_sections = [
                {
                    field: deepcopy(section[field])
                    for field in _MODEL_SECTION_FIELDS
                }
                for section in sections
            ]
        reconstructed_yearly = [
                {
                    "summary": deepcopy(entry["summary"]),
                    "detail": deepcopy(entry["detail"]),
                }
                for entry in sections[6]["yearly"]
            ]
        reconstructed_payload = {
                "summary": deepcopy(candidate["summary"]),
                "sections": reconstructed_sections,
                "future_flow_yearly": reconstructed_yearly,
                "long_term_luck": [
                    {field: deepcopy(item[field]) for field in ("title", "theme", "career", "wealth", "relationships", "caution", "advice")}
                    for item in candidate["long_term_luck"]
                ],
                "consultation_answer": deepcopy(candidate["consultation_answer"]),
            }
        _validate_structure(
                reconstructed_payload,
                request["model_output_schema"],
            )
        _validate_semantics(reconstructed_payload, request)
    except (KeyError, TypeError, IndexError) as exc:
        errors.append(
                "/sections: cannot reconstruct exact model-owned payload "
                f"({type(exc).__name__})"
            )
    except (
            AIReadingGeneratorV2StructuralValidationError,
            AIReadingGeneratorV2SemanticValidationError,
        ) as exc:
        errors.extend(
                f"/model_payload: {issue}"
                for issue in exc.issues
            )
    report = {
        "valid": not (errors or missing or unknown),
        "errors": sorted(errors),
        "missing_required_fields": sorted(missing),
        "unknown_fields": sorted(unknown),
    }
    return report


def _validate_report_shape(report: Mapping[str, Any]) -> None:
    if not isinstance(report, Mapping) or tuple(report) != _VALIDATION_FIELDS:
        raise AIReadingGeneratorV2CandidateValidationError(
            {
                "valid": False,
                "errors": ["/validation: exact field shape mismatch"],
                "missing_required_fields": [],
                "unknown_fields": [],
            }
        )
    if not isinstance(report["valid"], bool) or not all(
        isinstance(report[field], list)
        and all(isinstance(item, str) for item in report[field])
        for field in _VALIDATION_FIELDS[1:]
    ):
        raise AIReadingGeneratorV2CandidateValidationError(
            {
                "valid": False,
                "errors": ["/validation: invalid field type"],
                "missing_required_fields": [],
                "unknown_fields": [],
            }
        )


def _normalize_usage(usage: Any) -> dict[str, Any]:
    if usage is None:
        return {}
    if isinstance(usage, Mapping):
        return deepcopy(dict(usage))
    model_dump = getattr(usage, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        if isinstance(dumped, Mapping):
            return deepcopy(dict(dumped))
    result: dict[str, Any] = {}
    for field in ("input_tokens", "output_tokens", "total_tokens"):
        value = getattr(usage, field, None)
        if value is not None:
            result[field] = value
    return result


def generate_ai_reading_v2(
    request: Mapping[str, Any],
    *,
    client: Any = None,
    api_key: str | None = None,
    model: str | None = None,
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    reasoning_effort: str = DEFAULT_REASONING_EFFORT,
    store: bool = DEFAULT_STORE,
    provider_perf_callback: Callable[..., Any] | None = None,
) -> AIReadingGenerationResultV2:
    """Generate one structurally and semantically validated AI Reading v2."""

    canonical = _canonical_request(request)
    resolved_model = _resolve_model(model)
    provider_payload = _provider_payload(
        canonical,
        model=resolved_model,
        max_output_tokens=max_output_tokens,
        reasoning_effort=reasoning_effort,
        store=store,
    )
    if client is None:
        client = _create_openai_client(api_key=api_key)
    provider_started = time.perf_counter()
    response = _call_provider(client, provider_payload)
    # Emit provider timing immediately after the response arrives.  The
    # generator may still reject the payload during local structural/semantic
    # validation; callers must retain provider diagnostics in that case too.
    if provider_perf_callback is not None:
        try:
            raw_usage = _normalize_usage(_get(response, "usage"))
            provider_perf_callback(
                provider="generator",
                model=resolved_model,
                elapsed=time.perf_counter() - provider_started,
                usage=raw_usage,
                output_stats={
                    "output_json_chars": len(_extract_output_text(response)),
                },
            )
        except Exception:
            # Performance diagnostics must never alter the reading contract.
            pass
    text = _extract_output_text(response)
    transport_payload = _parse_model_json(text)
    transport_schema = provider_payload["text"]["format"]["schema"]
    _validate_structure(transport_payload, transport_schema)
    model_payload = _decode_openai_transport_payload(
        transport_payload,
        canonical["model_output_schema"],
    )
    _validate_structure(model_payload, canonical["model_output_schema"])
    _validate_semantics(model_payload, canonical)
    candidate = _assemble_candidate(model_payload, canonical)
    report = _validate_candidate(candidate, canonical)
    if not report["valid"]:
        raise AIReadingGeneratorV2CandidateValidationError(report)
    reading = {
        "schema_version": candidate["schema_version"],
        "engine_version": candidate["engine_version"],
        "summary": candidate["summary"],
        "sections": candidate["sections"],
        "long_term_luck": candidate["long_term_luck"],
        "consultation_answer": candidate["consultation_answer"],
        "warnings": candidate["warnings"],
        "uncertainty": candidate["uncertainty"],
        "source_contracts": candidate["source_contracts"],
        "disclaimer": candidate["disclaimer"],
        "validation": deepcopy(report),
        "method": candidate["method"],
        "version": candidate["version"],
        "status": candidate["status"],
    }
    _validate_report_shape(reading["validation"])
    if tuple(reading) != _FINAL_FIELDS:
        raise AIReadingGeneratorV2CandidateValidationError(
            {
                "valid": False,
                "errors": ["final wrapper exact field order mismatch"],
                "missing_required_fields": [],
                "unknown_fields": [],
            }
        )
    return AIReadingGenerationResultV2(
        reading=deepcopy(reading),
        model=resolved_model,
        response_id=_get(response, "id"),
        response_status=_get(response, "status"),
        usage=_normalize_usage(_get(response, "usage")),
    )


__all__ = [
    "AIReadingGenerationResultV2",
    "AIReadingGeneratorV2Error",
    "AIReadingGeneratorV2ConfigurationError",
    "AIReadingGeneratorV2RequestValidationError",
    "AIReadingGeneratorV2ProviderError",
    "AIReadingGeneratorV2ResponseError",
    "AIReadingGeneratorV2JSONError",
    "AIReadingGeneratorV2StructuralValidationError",
    "AIReadingGeneratorV2SemanticValidationError",
    "AIReadingGeneratorV2CandidateValidationError",
    "READING_GENERATOR_V2_VERSION",
    "READING_GENERATOR_V2_METHOD",
    "generate_ai_reading_v2",
]
