"""Phase 1 through Phase 4.1 foundations for AI Reading Quality Gate v2.

The exact report/finding contract kernel, input validation, and trusted identity
reconstruction are implemented together with the provider-independent semantic
assessor lifecycle and trusted-reference deterministic checks.  Remaining
deterministic checks and concrete prose-level semantic assessment stay
deliberately unavailable until later phases.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
import json
import math
import re
from typing import Any, Protocol

from engine.judgment_metadata import validate_common_judgment_metadata
from engine.reading_context_v2 import validate_reading_context_v2
from engine.reading_prompt_v2 import (
    AI_READING_V2_CLAIM_TYPES,
    AI_READING_V2_SECTION_SLOTS,
    build_ai_reading_request_v2,
    validate_ai_reading_prompt_inputs_v2,
)


AI_READING_QUALITY_REPORT_V2_SCHEMA_VERSION = "ai_reading_quality_report_v2"
AI_READING_QUALITY_REPORT_V2_VERSION = "ai_reading_quality_report_v2"
AI_READING_QUALITY_REPORT_V2_METHOD = "ai_reading_quality_gate_v2"
AI_READING_QUALITY_REPORT_V2_STATUS = "completed"

_REPORT_FIELDS = (
    "schema_version",
    "version",
    "method",
    "status",
    "decision",
    "blocking",
    "human_review_required",
    "error_count",
    "warning_count",
    "info_count",
    "input_contracts",
    "semantic_assessment",
    "findings",
)
_FINDING_FIELDS = (
    "finding_id",
    "code",
    "severity",
    "blocking",
    "path",
    "message",
    "evidence",
    "repairability",
    "requires_human_review",
)
_EVIDENCE_FIELDS = ("source_contract", "path")
_FINDING_CANDIDATE_FIELDS = ("code", "path", "evidence")
_INPUT_CONTRACT_FIELDS = (
    "ai_reading_v2",
    "reading_context_v2",
    "common_judgment_metadata_v1",
)
_INPUT_CONTRACT_NESTED_FIELDS = {
    "ai_reading_v2": (
        "schema_version",
        "version",
        "method",
        "status",
        "engine_version",
    ),
    "reading_context_v2": ("schema_version", "version", "method", "status"),
    "common_judgment_metadata_v1": ("schema_version",),
}
_SEMANTIC_ASSESSMENT_FIELDS = ("status", "method", "version")
_SEMANTIC_ASSESSMENT_STATUSES = (
    "not_run",
    "completed",
    "unavailable",
    "failed",
    "inconclusive",
)
_SEMANTIC_RESULT_FIELDS = ("status", "findings")
_SEMANTIC_DECLARATION_FIELDS = ("code", "path", "evidence")
_AI_READING_FIELDS = (
    "schema_version",
    "engine_version",
    "summary",
    "sections",
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
_GROUNDED_TEXT_BLOCK_FIELDS = (
    "text",
    "claim_type",
    "source_fact_codes",
    "source_components",
    "warnings",
    "uncertainty",
)
_SECTION_MODEL_FIELDS = (
    "facts",
    "summary",
    "detail",
    "evidence",
    "interpretation",
    "advice",
    "warnings",
    "uncertainty",
)
_WARNING_CATALOG_FIELDS = (
    "warning_id",
    "source_contract",
    "source_path",
    "value",
)
_UNCERTAINTY_CATALOG_FIELDS = (
    "uncertainty_id",
    "source_contract",
    "source_path",
    "value",
)
_UNCERTAINTY_VALUE_FIELDS = (
    "code",
    "category",
    "status",
    "severity",
    "scope",
    "message",
)
_SOURCE_CONTRACT_FIELDS = ("reading_context", "judgment_metadata")
_READING_CONTEXT_IDENTITY_FIELDS = (
    "schema_version",
    "method",
    "version",
    "status",
)
_JUDGMENT_METADATA_IDENTITY_FIELDS = ("schema_version",)
_FINAL_VALIDATION_FIELDS = (
    "valid",
    "errors",
    "missing_required_fields",
    "unknown_fields",
)
_SOURCE_CONTRACTS = (
    "ai_reading_v2",
    "reading_context_v2",
    "common_judgment_metadata_v1",
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
_SEVERITY_RANK = {"ERROR": 0, "WARNING": 1, "INFO": 2}
_REPAIRABILITIES = ("auto", "human", "none")
_FINDING_ID_PATTERN = re.compile(r"finding_[0-9]+\Z")


@dataclass(frozen=True)
class _IssueDefinition:
    code: str
    severity: str
    blocking: bool
    repairability: str
    requires_human_review: bool
    message: str


_ISSUE_CATALOG = (
    _IssueDefinition(
        "input_contract_invalid",
        "ERROR",
        True,
        "none",
        False,
        "入力contractがowner validationまたはprompt prerequisite validationを通過しません。",
    ),
    _IssueDefinition(
        "input_contract_mismatch",
        "ERROR",
        True,
        "none",
        False,
        "AI Readingと検証入力のtrusted identityが一致しません。",
    ),
    _IssueDefinition(
        "ai_reading_contract_invalid",
        "ERROR",
        True,
        "none",
        False,
        "AI Reading v2の構造がfinal contractに一致しません。",
    ),
    _IssueDefinition(
        "trusted_field_mismatch",
        "ERROR",
        True,
        "none",
        False,
        "AI Reading v2のtrusted fieldが再構築値と一致しません。",
    ),
    _IssueDefinition(
        "reference_resolution_error",
        "ERROR",
        True,
        "none",
        False,
        "参照がtrusted sourceへ解決できません。",
    ),
    _IssueDefinition(
        "warning_uncertainty_not_preserved",
        "ERROR",
        True,
        "none",
        False,
        "warningまたはuncertaintyが保持されていません。",
    ),
    _IssueDefinition(
        "disclaimer_mismatch",
        "ERROR",
        True,
        "none",
        False,
        "disclaimerがtrusted constantと一致しません。",
    ),
    _IssueDefinition(
        "future_year_integrity_error",
        "ERROR",
        True,
        "none",
        False,
        "future_flowのyearまたは順序がtrusted inputと一致しません。",
    ),
    _IssueDefinition(
        "claim_type_mismatch",
        "ERROR",
        True,
        "auto",
        False,
        "claim_typeが本文の意味と一致しません。",
    ),
    _IssueDefinition(
        "fact_semantic_mismatch",
        "ERROR",
        True,
        "human",
        True,
        "source_fact_codesが本文の占術主張を意味的に支持しません。",
    ),
    _IssueDefinition(
        "component_semantic_mismatch",
        "ERROR",
        True,
        "human",
        True,
        "source_componentsが本文のcertaintyまたはprovenance表現と整合しません。",
    ),
    _IssueDefinition(
        "luck_semantic_mismatch",
        "ERROR",
        True,
        "human",
        True,
        "luck_astrology本文がtrusted luck sourceと整合しません。",
    ),
    _IssueDefinition(
        "engine_value_contradiction",
        "ERROR",
        True,
        "human",
        True,
        "本文がengine確定値またはlabelと矛盾します。",
    ),
    _IssueDefinition(
        "judgment_status_wording_violation",
        "ERROR",
        True,
        "auto",
        False,
        "本文の確度表現がcanonical judgment status policyに違反します。",
    ),
    _IssueDefinition(
        "unknown_hour_derived_claim",
        "ERROR",
        True,
        "human",
        True,
        "出生時刻不明入力からhour由来の主張を生成しています。",
    ),
    _IssueDefinition(
        "missing_applicable_uncertainty",
        "ERROR",
        True,
        "human",
        True,
        "適用可能なuncertaintyが本文または参照に保持されていません。",
    ),
    _IssueDefinition(
        "unsupported_numeric_claim",
        "ERROR",
        True,
        "auto",
        False,
        "本文の数値主張をtrusted sourceで確認できません。",
    ),
    _IssueDefinition(
        "consultation_astrology_leak",
        "ERROR",
        True,
        "human",
        True,
        "consultationから新しい占術判断を生成しています。",
    ),
    _IssueDefinition(
        "prohibited_claim",
        "ERROR",
        True,
        "human",
        True,
        "医療・法律・投資の断定、将来保証、不安煽りまたはその他の禁止主張が含まれています。",
    ),
    _IssueDefinition(
        "overconfident_wording",
        "WARNING",
        False,
        "auto",
        False,
        "本文に過度に断定的な表現があります。",
    ),
    _IssueDefinition(
        "evidence_interpretation_advice_confusion",
        "WARNING",
        False,
        "auto",
        False,
        "evidence、interpretation、adviceの役割が混同されています。",
    ),
    _IssueDefinition(
        "astrology_wording_ambiguity",
        "WARNING",
        False,
        "auto",
        False,
        "占術上の根拠または確度の表現が曖昧です。",
    ),
    _IssueDefinition(
        "semantic_assessment_unavailable",
        "WARNING",
        True,
        "human",
        True,
        "semantic assessorが未設定またはidentity不正のため意味検査を実行できません。",
    ),
    _IssueDefinition(
        "semantic_assessment_failed",
        "WARNING",
        True,
        "human",
        True,
        "semantic assessorの実行または出力検証に失敗しました。",
    ),
    _IssueDefinition(
        "semantic_assessment_inconclusive",
        "WARNING",
        True,
        "human",
        True,
        "semantic assessorが一つ以上の意味検査を確定できませんでした。",
    ),
    _IssueDefinition(
        "source_limitation_note",
        "INFO",
        False,
        "none",
        False,
        "source limitationが適切に開示されています。",
    ),
)
_ISSUE_BY_CODE = {definition.code: definition for definition in _ISSUE_CATALOG}

_SEMANTIC_ISSUE_CODES = (
    "claim_type_mismatch",
    "fact_semantic_mismatch",
    "component_semantic_mismatch",
    "luck_semantic_mismatch",
    "engine_value_contradiction",
    "judgment_status_wording_violation",
    "unknown_hour_derived_claim",
    "missing_applicable_uncertainty",
    "unsupported_numeric_claim",
    "consultation_astrology_leak",
    "prohibited_claim",
    "overconfident_wording",
    "evidence_interpretation_advice_confusion",
    "astrology_wording_ambiguity",
    "source_limitation_note",
)
_INFRASTRUCTURE_CODES = (
    "semantic_assessment_unavailable",
    "semantic_assessment_failed",
    "semantic_assessment_inconclusive",
)
_INFRASTRUCTURE_CODE_BY_STATUS = {
    "unavailable": "semantic_assessment_unavailable",
    "failed": "semantic_assessment_failed",
    "inconclusive": "semantic_assessment_inconclusive",
}


class SemanticAssessorV2(Protocol):
    """Provider-independent semantic assessor contract."""

    @property
    def method(self) -> str:
        """Return the assessor method identity."""

        ...

    @property
    def version(self) -> str:
        """Return the assessor version identity."""

        ...

    def assess(
        self,
        ai_reading: Mapping[str, Any],
        reading_context: Mapping[str, Any],
        judgment_metadata: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        """Return an exact SemanticAssessmentResultV2 mapping."""

        ...


def _is_string_array(value: Any) -> bool:
    return (
        type(value) is list
        and all(type(item) is str for item in value)
        and len(value) == len(set(value))
    )


def _has_exact_keys(value: Mapping[str, Any], fields: tuple[str, ...]) -> bool:
    actual_fields = tuple(value)
    return (
        len(actual_fields) == len(fields)
        and all(type(field) is str for field in actual_fields)
        and set(actual_fields) == set(fields)
    )


def _has_exact_ordered_keys(
    value: Mapping[str, Any],
    fields: tuple[str, ...],
) -> bool:
    actual_fields = tuple(value)
    return all(type(field) is str for field in actual_fields) and (
        actual_fields == fields
    )


def _is_json_contract_tree(value: Any, active: set[int] | None = None) -> bool:
    if value is None or type(value) in (str, bool, int):
        return True
    if type(value) is float:
        return math.isfinite(value)
    if not isinstance(value, Mapping) and type(value) is not list:
        return False

    active = set() if active is None else active
    identity = id(value)
    if identity in active:
        return False
    active.add(identity)
    try:
        if isinstance(value, Mapping):
            return all(
                type(key) is str
                and _is_json_contract_tree(item, active)
                for key, item in value.items()
            )
        return all(_is_json_contract_tree(item, active) for item in value)
    finally:
        active.remove(identity)


def _plain_json_snapshot(value: Any, active: set[int] | None = None) -> Any:
    """Copy one validated JSON tree without invoking user copy hooks."""

    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("JSON numbers must be finite")
        return value
    if not isinstance(value, Mapping) and type(value) is not list:
        raise TypeError("value is not plain JSON data")

    active = set() if active is None else active
    identity = id(value)
    if identity in active:
        raise ValueError("JSON data must not contain cycles")
    active.add(identity)
    try:
        if isinstance(value, Mapping):
            tuple(value.items())
            snapshot: dict[str, Any] = {}
            for key in value:
                if type(key) is not str:
                    raise TypeError("JSON object keys must be plain strings")
                item = value[key]
                snapshot[key] = _plain_json_snapshot(item, active)
            return snapshot
        return [_plain_json_snapshot(item, active) for item in value]
    finally:
        active.remove(identity)


def _try_plain_json_snapshot(value: Any) -> Any | None:
    try:
        return _plain_json_snapshot(value)
    except Exception:
        return None


def _json_values_equal(actual: Any, expected: Any) -> bool:
    """Compare validated JSON values without invoking container equality."""

    if isinstance(actual, Mapping) and isinstance(expected, Mapping):
        actual_fields = tuple(actual)
        expected_fields = tuple(expected)
        if (
            len(actual_fields) != len(expected_fields)
            or any(type(field) is not str for field in actual_fields)
            or set(actual_fields) != set(expected_fields)
        ):
            return False
        return all(
            _json_values_equal(actual[field], expected[field])
            for field in expected_fields
        )
    if type(actual) is list and type(expected) is list:
        return len(actual) == len(expected) and all(
            _json_values_equal(actual_item, expected_item)
            for actual_item, expected_item in zip(actual, expected)
        )
    if type(actual) is not type(expected):
        return False
    return actual == expected


def _is_grounded_text_block(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    if not _has_exact_ordered_keys(value, _GROUNDED_TEXT_BLOCK_FIELDS):
        return False
    return (
        isinstance(value["text"], str)
        and isinstance(value["claim_type"], str)
        and value["claim_type"] in AI_READING_V2_CLAIM_TYPES
        and _is_string_array(value["source_fact_codes"])
        and _is_string_array(value["source_components"])
        and _is_string_array(value["warnings"])
        and _is_string_array(value["uncertainty"])
    )


def _is_uncertainty_value(value: Any) -> bool:
    if not isinstance(value, Mapping) or not _has_exact_keys(
        value,
        _UNCERTAINTY_VALUE_FIELDS,
    ):
        return False
    return (
        isinstance(value["code"], str)
        and isinstance(value["category"], str)
        and isinstance(value["status"], str)
        and isinstance(value["severity"], str)
        and isinstance(value["scope"], list)
        and all(isinstance(item, str) for item in value["scope"])
        and (value["message"] is None or isinstance(value["message"], str))
    )


def _is_catalog(
    value: Any,
    *,
    fields: tuple[str, ...],
    id_field: str,
    uncertainty: bool,
) -> bool:
    if not isinstance(value, list):
        return False
    for entry in value:
        if not isinstance(entry, Mapping) or not _has_exact_keys(entry, fields):
            return False
        if not isinstance(entry[id_field], str):
            return False
        if (
            not isinstance(entry["source_contract"], str)
            or entry["source_contract"]
            not in (
                "reading_context_v2",
                "common_judgment_metadata_v1",
            )
        ):
            return False
        if not isinstance(entry["source_path"], str):
            return False
        if uncertainty:
            if not _is_uncertainty_value(entry["value"]):
                return False
        elif not isinstance(entry["value"], str):
            return False
    return True


def _is_final_validation_report(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and _has_exact_keys(value, _FINAL_VALIDATION_FIELDS)
        and value["valid"] is True
        and isinstance(value["errors"], list)
        and len(value["errors"]) == 0
        and isinstance(value["missing_required_fields"], list)
        and len(value["missing_required_fields"]) == 0
        and isinstance(value["unknown_fields"], list)
        and len(value["unknown_fields"]) == 0
    )


def _is_source_contracts(value: Any) -> bool:
    if not isinstance(value, Mapping) or not _has_exact_keys(
        value,
        _SOURCE_CONTRACT_FIELDS,
    ):
        return False
    reading_context = value["reading_context"]
    judgment_metadata = value["judgment_metadata"]
    return (
        isinstance(reading_context, Mapping)
        and _has_exact_keys(reading_context, _READING_CONTEXT_IDENTITY_FIELDS)
        and all(isinstance(reading_context[field], str) for field in reading_context)
        and isinstance(judgment_metadata, Mapping)
        and _has_exact_keys(judgment_metadata, _JUDGMENT_METADATA_IDENTITY_FIELDS)
        and isinstance(judgment_metadata["schema_version"], str)
    )


def _is_section(value: Any, index: int) -> bool:
    section_id, _ = AI_READING_V2_SECTION_SLOTS[index]
    expected_fields = (
        ("section_id", "title")
        + _SECTION_MODEL_FIELDS
        + (("yearly",) if section_id == "future_flow" else ())
    )
    if not isinstance(value, Mapping) or not _has_exact_keys(value, expected_fields):
        return False
    if not isinstance(value["section_id"], str) or not isinstance(value["title"], str):
        return False
    if not _is_string_array(value["facts"]):
        return False
    if not _is_grounded_text_block(value["summary"]):
        return False
    if not _is_grounded_text_block(value["detail"]):
        return False
    for field in ("evidence", "interpretation", "advice"):
        if not isinstance(value[field], list) or any(
            not _is_grounded_text_block(block) for block in value[field]
        ):
            return False
    if not _is_string_array(value["warnings"]):
        return False
    if not _is_string_array(value["uncertainty"]):
        return False
    if section_id != "future_flow":
        return True
    yearly = value["yearly"]
    if not isinstance(yearly, list):
        return False
    for entry in yearly:
        if not isinstance(entry, Mapping) or not _has_exact_keys(
            entry,
            ("year", "summary", "detail"),
        ):
            return False
        if not isinstance(entry["year"], int) or isinstance(entry["year"], bool):
            return False
        if not _is_grounded_text_block(entry["summary"]):
            return False
        if not _is_grounded_text_block(entry["detail"]):
            return False
    return True


def _is_ai_reading_v2_final_contract(value: Mapping[str, Any]) -> bool:
    if not _has_exact_keys(value, _AI_READING_FIELDS):
        return False
    if (
        not isinstance(value["schema_version"], str)
        or value["schema_version"] != "ai_reading_v2"
    ):
        return False
    if not isinstance(value["version"], str) or value["version"] != "ai_reading_v2":
        return False
    if (
        not isinstance(value["method"], str)
        or value["method"] != "openai_responses_api_v2"
    ):
        return False
    if not isinstance(value["status"], str) or value["status"] != "completed":
        return False
    if value["engine_version"] is not None and not isinstance(
        value["engine_version"], str
    ):
        return False
    if not _is_grounded_text_block(value["summary"]):
        return False
    sections = value["sections"]
    if not isinstance(sections, list) or len(sections) != 8:
        return False
    if any(not _is_section(section, index) for index, section in enumerate(sections)):
        return False
    consultation_answer = value["consultation_answer"]
    if consultation_answer is not None and not _is_grounded_text_block(
        consultation_answer
    ):
        return False
    if not _is_catalog(
        value["warnings"],
        fields=_WARNING_CATALOG_FIELDS,
        id_field="warning_id",
        uncertainty=False,
    ):
        return False
    if not _is_catalog(
        value["uncertainty"],
        fields=_UNCERTAINTY_CATALOG_FIELDS,
        id_field="uncertainty_id",
        uncertainty=True,
    ):
        return False
    return (
        _is_source_contracts(value["source_contracts"])
        and isinstance(value["disclaimer"], str)
        and _is_final_validation_report(value["validation"])
    )


def _project_identity_fields(
    value: Any,
    fields: tuple[str, ...],
) -> dict[str, str | None]:
    if not isinstance(value, Mapping):
        return {field: None for field in fields}
    try:
        actual_fields = (
            tuple(dict.keys(value))
            if isinstance(value, dict)
            else tuple(value)
        )
    except Exception:
        actual_fields = ()
    exact_string_fields = {
        field for field in actual_fields if type(field) is str
    }
    projected: dict[str, str | None] = {}
    for field in fields:
        if field not in exact_string_fields:
            projected[field] = None
            continue
        try:
            field_value = value[field]
        except Exception:
            field_value = None
        projected[field] = field_value if type(field_value) is str else None
    return projected


def _project_input_contracts(
    ai_reading: Mapping[str, Any],
    reading_context: Mapping[str, Any],
    judgment_metadata: Mapping[str, Any],
) -> dict[str, dict[str, str | None]]:
    return {
        "ai_reading_v2": _project_identity_fields(
            ai_reading,
            ("schema_version", "version", "method", "status", "engine_version"),
        ),
        "reading_context_v2": _project_identity_fields(
            reading_context,
            ("schema_version", "version", "method", "status"),
        ),
        "common_judgment_metadata_v1": _project_identity_fields(
            judgment_metadata,
            ("schema_version",),
        ),
    }


def _root_evidence(source_contract: str) -> dict[str, str]:
    return {"source_contract": source_contract, "path": ""}


def _input_error_candidate(
    code: str,
    *source_contracts: str,
) -> dict[str, Any]:
    return {
        "code": code,
        "path": "",
        "evidence": [_root_evidence(contract) for contract in source_contracts],
    }


def _trusted_identity_mismatch(
    ai_reading: Mapping[str, Any],
    request: Mapping[str, Any],
) -> bool:
    return (
        not _json_values_equal(
            ai_reading["engine_version"],
            request["trusted_attachments"]["engine_version"],
        )
        or not _json_values_equal(
            ai_reading["source_contracts"],
            request["source_contracts"],
        )
    )


def _ai_reading_candidate(code: str, path: str) -> dict[str, Any]:
    return {
        "code": code,
        "path": path,
        "evidence": [{"source_contract": "ai_reading_v2", "path": path}],
    }


def _iter_final_blocks(
    ai_reading: Mapping[str, Any],
    request: Mapping[str, Any],
):
    yield "/summary", ai_reading["summary"], "top", None, None, "summary"
    slots = request["trusted_attachments"]["sections"]
    for index, section in enumerate(ai_reading["sections"]):
        section_id = slots[index]["section_id"]
        for field in ("summary", "detail"):
            yield (
                f"/sections/{index}/{field}",
                section[field],
                "section",
                section_id,
                None,
                field,
            )
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
        if section_id == "future_flow":
            for year_index, entry in enumerate(section["yearly"]):
                for field in ("summary", "detail"):
                    yield (
                        f"/sections/{index}/yearly/{year_index}/{field}",
                        entry[field],
                        "yearly",
                        section_id,
                        year_index,
                        field,
                    )
    if ai_reading["consultation_answer"] is not None:
        yield (
            "/consultation_answer",
            ai_reading["consultation_answer"],
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


def _luck_component_resolves(
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
        return expected_path is not None and sum(
            entry["section_id"] == "current_luck"
            and entry["year"] is None
            and entry["source_component"] == component
            and entry["context_path"] == expected_path
            for entry in entries
        ) == 1
    if location_kind == "section" and section_id == "future_flow":
        if component not in _FUTURE_LUCK_COMPONENTS or not years:
            return False
        actual = [
            (entry["year"], entry["context_path"])
            for entry in entries
            if entry["section_id"] == "future_flow"
            and entry["source_component"] == component
        ]
        expected = [
            (year, f"luck.five_year_luck[{index}].{component}")
            for index, year in enumerate(years)
        ]
        return actual == expected
    if location_kind == "yearly" and year_index is not None:
        if component not in _FUTURE_LUCK_COMPONENTS or year_index >= len(years):
            return False
        expected_year = years[year_index]
        expected_path = f"luck.five_year_luck[{year_index}].{component}"
        return sum(
            entry["section_id"] == "future_flow"
            and entry["year"] == expected_year
            and entry["source_component"] == component
            and entry["context_path"] == expected_path
            for entry in entries
        ) == 1
    return False


def _reference_candidates(
    ai_reading: Mapping[str, Any],
    request: Mapping[str, Any],
) -> list[dict[str, Any]]:
    catalogs = request["trusted_catalogs"]
    allowed = {
        "source_fact_codes": tuple(catalogs["fact_codes"]),
        "source_components": tuple(catalogs["source_components"]),
        "warnings": tuple(
            entry["warning_id"] for entry in catalogs["warnings"]
        ),
        "uncertainty": tuple(
            entry["uncertainty_id"] for entry in catalogs["uncertainty"]
        ),
    }
    candidates: list[dict[str, Any]] = []

    def check_array(
        path: str,
        values: list[str],
        field: str,
        *,
        catalog_field: str | None = None,
    ) -> None:
        allowed_values = allowed[field if catalog_field is None else catalog_field]
        for index, value in enumerate(values):
            if value not in allowed_values:
                candidates.append(
                    _ai_reading_candidate(
                        "reference_resolution_error",
                        f"{path}/{field}/{index}",
                    )
                )

    for section_index, section in enumerate(ai_reading["sections"]):
        section_path = f"/sections/{section_index}"
        check_array(
            section_path,
            section["facts"],
            "facts",
            catalog_field="source_fact_codes",
        )
        check_array(section_path, section["warnings"], "warnings")
        check_array(section_path, section["uncertainty"], "uncertainty")

    for path, block, kind, section_id, year_index, field in _iter_final_blocks(
        ai_reading,
        request,
    ):
        for ref_field in (
            "source_fact_codes",
            "source_components",
            "warnings",
            "uncertainty",
        ):
            check_array(path, block[ref_field], ref_field)

        claim_type = block["claim_type"]
        if claim_type not in _allowed_claim_types(kind, section_id, field):
            candidates.append(
                _ai_reading_candidate(
                    "reference_resolution_error",
                    f"{path}/claim_type",
                )
            )
        fact_refs = block["source_fact_codes"]
        component_refs = block["source_components"]
        luck_refs = [item for item in component_refs if item in _LUCK_COMPONENTS]
        if claim_type == "practical":
            if fact_refs:
                candidates.append(
                    _ai_reading_candidate(
                        "reference_resolution_error",
                        f"{path}/source_fact_codes",
                    )
                )
            if component_refs:
                candidates.append(
                    _ai_reading_candidate(
                        "reference_resolution_error",
                        f"{path}/source_components",
                    )
                )
        elif claim_type == "astrology":
            if not fact_refs:
                candidates.append(
                    _ai_reading_candidate(
                        "reference_resolution_error",
                        f"{path}/source_fact_codes",
                    )
                )
            if luck_refs:
                candidates.append(
                    _ai_reading_candidate(
                        "reference_resolution_error",
                        f"{path}/source_components",
                    )
                )
        elif claim_type == "luck_astrology":
            if not luck_refs:
                candidates.append(
                    _ai_reading_candidate(
                        "reference_resolution_error",
                        f"{path}/source_components",
                    )
                )
            elif any(
                not _luck_component_resolves(
                    component,
                    location_kind=kind,
                    section_id=section_id,
                    year_index=year_index,
                    request=request,
                )
                for component in luck_refs
            ):
                candidates.append(
                    _ai_reading_candidate(
                        "reference_resolution_error",
                        f"{path}/source_components",
                    )
                )
    return candidates


def _trusted_reference_candidates(
    ai_reading: Mapping[str, Any],
    request: Mapping[str, Any],
) -> list[dict[str, Any]]:
    attachments = request["trusted_attachments"]
    catalogs = request["trusted_catalogs"]
    candidates: list[dict[str, Any]] = []

    for index, slot in enumerate(attachments["sections"]):
        section = ai_reading["sections"][index]
        for field in ("section_id", "title"):
            if not _json_values_equal(section[field], slot[field]):
                candidates.append(
                    _ai_reading_candidate(
                        "trusted_field_mismatch",
                        f"/sections/{index}/{field}",
                    )
                )

    consultation_present = ai_reading["consultation_answer"] is not None
    if consultation_present != attachments["consultation_present"]:
        candidates.append(
            _ai_reading_candidate(
                "trusted_field_mismatch",
                "/consultation_answer",
            )
        )
    if not _json_values_equal(ai_reading["warnings"], catalogs["warnings"]):
        candidates.append(
            _ai_reading_candidate(
                "warning_uncertainty_not_preserved",
                "/warnings",
            )
        )
    if not _json_values_equal(
        ai_reading["uncertainty"],
        catalogs["uncertainty"],
    ):
        candidates.append(
            _ai_reading_candidate(
                "warning_uncertainty_not_preserved",
                "/uncertainty",
            )
        )
    if not _json_values_equal(ai_reading["disclaimer"], attachments["disclaimer"]):
        candidates.append(
            _ai_reading_candidate("disclaimer_mismatch", "/disclaimer")
        )

    future_section = ai_reading["sections"][6]
    actual_years = [entry["year"] for entry in future_section["yearly"]]
    if not _json_values_equal(actual_years, attachments["future_flow_years"]):
        candidates.append(
            _ai_reading_candidate(
                "future_year_integrity_error",
                "/sections/6/yearly",
            )
        )

    candidates.extend(_reference_candidates(ai_reading, request))
    return candidates


def _is_json_pointer(value: Any) -> bool:
    if type(value) is not str:
        return False
    if value == "":
        return True
    if not value.startswith("/"):
        return False
    index = 0
    while index < len(value):
        if value[index] != "~":
            index += 1
            continue
        if index + 1 >= len(value) or value[index + 1] not in ("0", "1"):
            return False
        index += 2
    return True


def _json_pointer_resolves(value: Any, pointer: str) -> bool:
    if not _is_json_pointer(pointer):
        return False
    if pointer == "":
        return True
    current = value
    for encoded_token in pointer[1:].split("/"):
        token = encoded_token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, Mapping):
            if token not in current:
                return False
            current = current[token]
            continue
        if isinstance(current, list):
            if not token.isdigit() or (len(token) > 1 and token.startswith("0")):
                return False
            index = int(token)
            if index >= len(current):
                return False
            current = current[index]
            continue
        return False
    return True


def _normalize_evidence(value: Any) -> tuple[dict[str, str], ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise TypeError("evidence must be an array")
    normalized: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for entry in value:
        if not isinstance(entry, Mapping):
            raise TypeError("evidence entry must be a Mapping")
        if not _has_exact_ordered_keys(entry, _EVIDENCE_FIELDS):
            raise ValueError("evidence entry fields/order must be source_contract, path")
        source_contract = entry["source_contract"]
        path = entry["path"]
        if (
            type(source_contract) is not str
            or source_contract not in _SOURCE_CONTRACTS
        ):
            raise ValueError("evidence source_contract is not allowed")
        if not _is_json_pointer(path):
            raise ValueError("evidence path must be an RFC 6901 JSON Pointer")
        identity = (source_contract, path)
        if identity not in seen:
            seen.add(identity)
            normalized.append(
                {"source_contract": source_contract, "path": path}
            )
    normalized.sort(key=lambda entry: (entry["source_contract"], entry["path"]))
    return tuple(normalized)


def _canonical_evidence_json(evidence: Any) -> str:
    canonical_evidence = [dict(entry) for entry in _normalize_evidence(evidence)]
    return json.dumps(
        canonical_evidence,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=False,
        allow_nan=False,
    )


def _snapshot_semantic_assessor_identity(
    semantic_assessor: SemanticAssessorV2 | None,
) -> tuple[str, str] | None:
    if semantic_assessor is None:
        return None
    try:
        method = semantic_assessor.method
    except Exception:
        return None
    try:
        version = semantic_assessor.version
    except Exception:
        return None
    if type(method) is not str or method == "":
        return None
    if type(version) is not str or version == "":
        return None
    return method, version


def _validate_semantic_assessor_result(
    value: Any,
    ai_reading: Mapping[str, Any],
    reading_context: Mapping[str, Any],
    judgment_metadata: Mapping[str, Any],
) -> tuple[str, tuple[dict[str, Any], ...]]:
    if not _is_json_contract_tree(value):
        raise ValueError("semantic assessor result is not plain JSON data")
    if not isinstance(value, Mapping) or not _has_exact_ordered_keys(
        value,
        _SEMANTIC_RESULT_FIELDS,
    ):
        raise ValueError("semantic assessor result fields/order are invalid")
    status = value["status"]
    if type(status) is not str or status not in (
        "completed",
        "inconclusive",
    ):
        raise ValueError("semantic assessor result status is invalid")
    declarations = value["findings"]
    if not isinstance(declarations, list):
        raise TypeError("semantic assessor findings must be an array")
    sources = {
        "ai_reading_v2": ai_reading,
        "reading_context_v2": reading_context,
        "common_judgment_metadata_v1": judgment_metadata,
    }
    candidates: list[dict[str, Any]] = []
    for declaration in declarations:
        if not isinstance(declaration, Mapping):
            raise TypeError("semantic assessor finding must be a Mapping")
        if not _has_exact_ordered_keys(
            declaration,
            _SEMANTIC_DECLARATION_FIELDS,
        ):
            raise ValueError("semantic assessor finding fields/order are invalid")
        code = declaration["code"]
        path = declaration["path"]
        evidence_value = declaration["evidence"]
        if type(code) is not str or code not in _SEMANTIC_ISSUE_CODES:
            raise ValueError("semantic assessor finding code is not allowed")
        if not _is_json_pointer(path) or not _json_pointer_resolves(ai_reading, path):
            raise ValueError("semantic assessor finding path does not resolve")
        if not isinstance(evidence_value, list):
            raise TypeError("semantic assessor evidence must be an array")
        evidence = _normalize_evidence(evidence_value)
        if not evidence:
            raise ValueError("semantic assessor finding requires evidence")
        if any(
            not _json_pointer_resolves(sources[entry["source_contract"]], entry["path"])
            for entry in evidence
        ):
            raise ValueError("semantic assessor evidence path does not resolve")
        candidates.append(
            {
                "code": code,
                "path": path,
                "evidence": [dict(entry) for entry in evidence],
            }
        )
    return status, tuple(candidates)


@dataclass(frozen=True)
class AIReadingQualityFindingV2:
    """One canonical Quality Gate v2 finding."""

    finding_id: str
    code: str
    severity: str
    blocking: bool
    path: str
    message: str
    evidence: tuple[dict[str, str], ...]
    repairability: str
    requires_human_review: bool

    def __post_init__(self) -> None:
        if type(self.finding_id) is not str or not _FINDING_ID_PATTERN.fullmatch(
            self.finding_id
        ):
            raise ValueError("finding_id must use finding_0001 format")
        finding_number = int(self.finding_id.removeprefix("finding_"))
        if finding_number < 1 or self.finding_id != f"finding_{finding_number:04d}":
            raise ValueError("finding_id must use canonical zero-padded format")
        if type(self.code) is not str:
            raise TypeError("finding code must be a string")
        definition = _ISSUE_BY_CODE.get(self.code)
        if definition is None:
            raise ValueError("finding code is not in the frozen issue catalog")
        if type(self.severity) is not str or (
            self.severity not in _SEVERITY_RANK
            or self.severity != definition.severity
        ):
            raise ValueError("finding severity does not match the issue catalog")
        if type(self.blocking) is not bool or self.blocking != definition.blocking:
            raise ValueError("finding blocking does not match the issue catalog")
        if not _is_json_pointer(self.path):
            raise ValueError("finding path must be an RFC 6901 JSON Pointer")
        if type(self.message) is not str or self.message != definition.message:
            raise ValueError("finding message does not match the issue catalog")
        if type(self.repairability) is not str or (
            self.repairability not in _REPAIRABILITIES
            or self.repairability != definition.repairability
        ):
            raise ValueError("finding repairability does not match the issue catalog")
        if type(self.requires_human_review) is not bool or (
            self.requires_human_review != definition.requires_human_review
        ):
            raise ValueError("finding human review flag does not match the issue catalog")
        canonical_evidence = _normalize_evidence(self.evidence)
        if self.code in _INFRASTRUCTURE_CODES:
            if self.path != "" or canonical_evidence:
                raise ValueError(
                    "semantic infrastructure findings require an empty path and evidence"
                )
        elif not canonical_evidence:
            raise ValueError("non-infrastructure findings require evidence")
        object.__setattr__(self, "evidence", canonical_evidence)

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "code": self.code,
            "severity": self.severity,
            "blocking": self.blocking,
            "path": self.path,
            "message": self.message,
            "evidence": deepcopy(list(self.evidence)),
            "repairability": self.repairability,
            "requires_human_review": self.requires_human_review,
        }


def _copy_input_contracts(value: Any) -> dict[str, dict[str, str | None]]:
    if not isinstance(value, Mapping) or not _has_exact_ordered_keys(
        value,
        _INPUT_CONTRACT_FIELDS,
    ):
        raise ValueError("input_contracts fields/order do not match the v2 report contract")
    copied: dict[str, dict[str, str | None]] = {}
    for contract in _INPUT_CONTRACT_FIELDS:
        identity = value[contract]
        expected_fields = _INPUT_CONTRACT_NESTED_FIELDS[contract]
        if not isinstance(identity, Mapping) or not _has_exact_ordered_keys(
            identity,
            expected_fields,
        ):
            raise ValueError(f"input_contracts.{contract} fields/order are invalid")
        projected: dict[str, str | None] = {}
        for field in expected_fields:
            field_value = identity[field]
            if field_value is not None and type(field_value) is not str:
                raise TypeError(f"input_contracts.{contract}.{field} must be string or null")
            projected[field] = field_value
        copied[contract] = projected
    return copied


def _copy_semantic_assessment(value: Any) -> dict[str, str | None]:
    if not isinstance(value, Mapping) or not _has_exact_ordered_keys(
        value,
        _SEMANTIC_ASSESSMENT_FIELDS,
    ):
        raise ValueError("semantic_assessment fields/order do not match the v2 report contract")
    status = value["status"]
    method = value["method"]
    version = value["version"]
    if type(status) is not str or status not in _SEMANTIC_ASSESSMENT_STATUSES:
        raise ValueError("semantic_assessment.status is invalid")
    if status in ("not_run", "unavailable"):
        if method is not None or version is not None:
            raise ValueError(f"{status} semantic assessment requires null identity")
    else:
        if type(method) is not str or method == "":
            raise ValueError(f"{status} semantic assessment requires a non-empty method")
        if type(version) is not str or version == "":
            raise ValueError(f"{status} semantic assessment requires a non-empty version")
    return {"status": status, "method": method, "version": version}


def _finding_sort_key(
    code: str,
    path: str,
    canonical_evidence_json: str,
) -> tuple[int, str, str, str]:
    return (
        _SEVERITY_RANK[_ISSUE_BY_CODE[code].severity],
        path,
        code,
        canonical_evidence_json,
    )


def _canonicalize_finding_candidates(
    candidates: Any,
) -> tuple[AIReadingQualityFindingV2, ...]:
    if not isinstance(candidates, Sequence) or isinstance(
        candidates, (str, bytes, bytearray)
    ):
        raise TypeError("finding candidates must be an array")
    normalized: list[tuple[str, str, tuple[dict[str, str], ...], str]] = []
    seen: set[tuple[str, str, str]] = set()
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            raise TypeError("finding candidate must be a Mapping")
        if not _has_exact_ordered_keys(candidate, _FINDING_CANDIDATE_FIELDS):
            raise ValueError("finding candidate fields/order must be code, path, evidence")
        code = candidate["code"]
        path = candidate["path"]
        if type(code) is not str or code not in _ISSUE_BY_CODE:
            raise ValueError("finding code is not in the frozen issue catalog")
        if not _is_json_pointer(path):
            raise ValueError("finding path must be an RFC 6901 JSON Pointer")
        evidence = _normalize_evidence(candidate["evidence"])
        if code in _INFRASTRUCTURE_CODES:
            if path != "" or evidence:
                raise ValueError(
                    "semantic infrastructure findings require an empty path and evidence"
                )
        elif not evidence:
            raise ValueError("non-infrastructure findings require evidence")
        evidence_json = _canonical_evidence_json(evidence)
        identity = (code, path, evidence_json)
        if identity in seen:
            continue
        seen.add(identity)
        normalized.append((code, path, evidence, evidence_json))
    normalized.sort(key=lambda item: _finding_sort_key(item[0], item[1], item[3]))
    findings: list[AIReadingQualityFindingV2] = []
    for index, (code, path, evidence, _) in enumerate(normalized, start=1):
        definition = _ISSUE_BY_CODE[code]
        findings.append(
            AIReadingQualityFindingV2(
                finding_id=f"finding_{index:04d}",
                code=code,
                severity=definition.severity,
                blocking=definition.blocking,
                path=path,
                message=definition.message,
                evidence=evidence,
                repairability=definition.repairability,
                requires_human_review=definition.requires_human_review,
            )
        )
    return tuple(findings)


def _validate_semantic_lifecycle(
    semantic_assessment: Mapping[str, str | None],
    findings: Sequence[AIReadingQualityFindingV2],
) -> None:
    status = semantic_assessment["status"]
    has_error = any(finding.severity == "ERROR" for finding in findings)
    infrastructure_codes = [
        finding.code for finding in findings if finding.code in _INFRASTRUCTURE_CODES
    ]
    if status == "not_run":
        if infrastructure_codes:
            raise ValueError("not_run cannot contain semantic infrastructure findings")
        if not has_error:
            raise ValueError("not_run requires at least one deterministic ERROR")
        return
    if status == "completed":
        if infrastructure_codes:
            raise ValueError("completed cannot contain semantic infrastructure findings")
        return
    expected_code = _INFRASTRUCTURE_CODE_BY_STATUS[status]
    if infrastructure_codes != [expected_code]:
        raise ValueError(f"{status} requires exactly one {expected_code} finding")
    if status in ("unavailable", "failed") and has_error:
        raise ValueError(f"deterministic ERROR requires not_run, not {status}")


def _validate_finding_origins(
    semantic_status: str,
    deterministic_findings: Sequence[AIReadingQualityFindingV2],
    semantic_findings: Sequence[AIReadingQualityFindingV2],
) -> None:
    if any(finding.severity == "ERROR" for finding in deterministic_findings):
        if semantic_status != "not_run":
            raise ValueError("deterministic ERROR requires not_run")
    if semantic_findings and semantic_status not in ("completed", "inconclusive"):
        raise ValueError(
            f"{semantic_status} cannot retain semantic assessor declarations"
        )
    if any(finding.code not in _SEMANTIC_ISSUE_CODES for finding in semantic_findings):
        raise ValueError("semantic finding code is not in the assessor allowlist")


def _expected_decision(
    findings: Sequence[AIReadingQualityFindingV2],
    semantic_status: str,
) -> str:
    if any(finding.severity == "ERROR" for finding in findings):
        return "fail"
    if semantic_status != "completed" or any(
        finding.requires_human_review for finding in findings
    ):
        return "review"
    return "pass"


@dataclass(frozen=True)
class AIReadingQualityReportV2:
    """Exact, completed Quality Report v2 contract."""

    schema_version: str
    version: str
    method: str
    status: str
    decision: str
    blocking: bool
    human_review_required: bool
    error_count: int
    warning_count: int
    info_count: int
    input_contracts: dict[str, dict[str, str | None]]
    semantic_assessment: dict[str, str | None]
    findings: tuple[AIReadingQualityFindingV2, ...]

    def __post_init__(self) -> None:
        identities = (
            (self.schema_version, AI_READING_QUALITY_REPORT_V2_SCHEMA_VERSION),
            (self.version, AI_READING_QUALITY_REPORT_V2_VERSION),
            (self.method, AI_READING_QUALITY_REPORT_V2_METHOD),
            (self.status, AI_READING_QUALITY_REPORT_V2_STATUS),
        )
        if any(
            type(actual) is not str or actual != expected
            for actual, expected in identities
        ):
            raise ValueError("Quality Report v2 identity is invalid")
        if type(self.decision) is not str or self.decision not in (
            "pass",
            "fail",
            "review",
        ):
            raise ValueError("Quality Report v2 decision is invalid")
        if type(self.blocking) is not bool or type(self.human_review_required) is not bool:
            raise TypeError("Quality Report v2 flags must be boolean")
        for field, value in (
            ("error_count", self.error_count),
            ("warning_count", self.warning_count),
            ("info_count", self.info_count),
        ):
            if type(value) is not int or value < 0:
                raise TypeError(f"{field} must be a non-negative integer")
        input_contracts = _copy_input_contracts(self.input_contracts)
        semantic_assessment = _copy_semantic_assessment(self.semantic_assessment)
        if not isinstance(self.findings, Sequence) or isinstance(
            self.findings, (str, bytes, bytearray)
        ):
            raise TypeError("findings must be an array")
        findings = tuple(self.findings)
        if any(not isinstance(item, AIReadingQualityFindingV2) for item in findings):
            raise TypeError("findings must contain AIReadingQualityFindingV2 values")
        expected_ids = tuple(
            f"finding_{index:04d}" for index in range(1, len(findings) + 1)
        )
        if tuple(finding.finding_id for finding in findings) != expected_ids:
            raise ValueError("finding IDs are not canonical")
        keys = [
            _finding_sort_key(
                finding.code,
                finding.path,
                _canonical_evidence_json(finding.evidence),
            )
            for finding in findings
        ]
        if keys != sorted(keys) or len(
            {(item.code, item.path, _canonical_evidence_json(item.evidence)) for item in findings}
        ) != len(findings):
            raise ValueError("findings are not canonically sorted and deduplicated")
        _validate_semantic_lifecycle(semantic_assessment, findings)
        expected_counts = {
            "ERROR": sum(item.severity == "ERROR" for item in findings),
            "WARNING": sum(item.severity == "WARNING" for item in findings),
            "INFO": sum(item.severity == "INFO" for item in findings),
        }
        if (
            self.error_count != expected_counts["ERROR"]
            or self.warning_count != expected_counts["WARNING"]
            or self.info_count != expected_counts["INFO"]
        ):
            raise ValueError("Quality Report v2 severity counts are invalid")
        expected_human_review = any(item.requires_human_review for item in findings)
        if self.human_review_required != expected_human_review:
            raise ValueError("Quality Report v2 human-review invariant is invalid")
        expected_decision = _expected_decision(findings, semantic_assessment["status"])
        if self.decision != expected_decision:
            raise ValueError("Quality Report v2 decision is invalid")
        if self.blocking != (self.decision != "pass"):
            raise ValueError("Quality Report v2 blocking invariant is invalid")
        object.__setattr__(self, "input_contracts", input_contracts)
        object.__setattr__(self, "semantic_assessment", semantic_assessment)
        object.__setattr__(self, "findings", findings)

    def to_dict(self) -> dict[str, Any]:
        report = {
            "schema_version": self.schema_version,
            "version": self.version,
            "method": self.method,
            "status": self.status,
            "decision": self.decision,
            "blocking": self.blocking,
            "human_review_required": self.human_review_required,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "info_count": self.info_count,
            "input_contracts": deepcopy(self.input_contracts),
            "semantic_assessment": deepcopy(self.semantic_assessment),
            "findings": [finding.to_dict() for finding in self.findings],
        }
        if tuple(report) != _REPORT_FIELDS:
            raise AssertionError("Quality Report v2 field order drifted")
        return report


def _build_quality_report_v2(
    input_contracts: Mapping[str, Any],
    semantic_assessment: Mapping[str, Any],
    finding_candidates: Sequence[Mapping[str, Any]],
    *,
    semantic_finding_candidates: Sequence[Mapping[str, Any]] = (),
) -> AIReadingQualityReportV2:
    """Build a report from already validated contract-kernel inputs."""

    copied_input_contracts = _copy_input_contracts(input_contracts)
    copied_semantic_assessment = _copy_semantic_assessment(semantic_assessment)
    deterministic_findings = _canonicalize_finding_candidates(finding_candidates)
    semantic_findings = _canonicalize_finding_candidates(
        semantic_finding_candidates
    )
    _validate_finding_origins(
        copied_semantic_assessment["status"],
        deterministic_findings,
        semantic_findings,
    )
    findings = _canonicalize_finding_candidates(
        tuple(finding_candidates) + tuple(semantic_finding_candidates)
    )
    _validate_semantic_lifecycle(copied_semantic_assessment, findings)
    error_count = sum(item.severity == "ERROR" for item in findings)
    warning_count = sum(item.severity == "WARNING" for item in findings)
    info_count = sum(item.severity == "INFO" for item in findings)
    decision = _expected_decision(findings, copied_semantic_assessment["status"])
    return AIReadingQualityReportV2(
        schema_version=AI_READING_QUALITY_REPORT_V2_SCHEMA_VERSION,
        version=AI_READING_QUALITY_REPORT_V2_VERSION,
        method=AI_READING_QUALITY_REPORT_V2_METHOD,
        status=AI_READING_QUALITY_REPORT_V2_STATUS,
        decision=decision,
        blocking=decision != "pass",
        human_review_required=any(
            item.requires_human_review for item in findings
        ),
        error_count=error_count,
        warning_count=warning_count,
        info_count=info_count,
        input_contracts=copied_input_contracts,
        semantic_assessment=copied_semantic_assessment,
        findings=findings,
    )


def _semantic_infrastructure_candidate(code: str) -> dict[str, Any]:
    return {"code": code, "path": "", "evidence": []}


def _run_semantic_assessor_v2(
    input_contracts: Mapping[str, Any],
    deterministic_candidates: Sequence[Mapping[str, Any]],
    ai_reading: Mapping[str, Any],
    reading_context: Mapping[str, Any],
    judgment_metadata: Mapping[str, Any],
    semantic_assessor: SemanticAssessorV2 | None,
) -> AIReadingQualityReportV2:
    deterministic_candidates = tuple(deterministic_candidates)
    deterministic_findings = _canonicalize_finding_candidates(
        deterministic_candidates
    )
    if any(finding.severity == "ERROR" for finding in deterministic_findings):
        return _build_quality_report_v2(
            input_contracts,
            {"status": "not_run", "method": None, "version": None},
            deterministic_candidates,
        )

    reference_ai_reading = _plain_json_snapshot(ai_reading)
    reference_reading_context = _plain_json_snapshot(reading_context)
    reference_judgment_metadata = _plain_json_snapshot(judgment_metadata)

    identity = _snapshot_semantic_assessor_identity(semantic_assessor)
    if identity is None:
        return _build_quality_report_v2(
            input_contracts,
            {"status": "unavailable", "method": None, "version": None},
            deterministic_candidates
            + (
                _semantic_infrastructure_candidate(
                    "semantic_assessment_unavailable"
                ),
            ),
        )

    method, version = identity
    semantic_assessment = {
        "status": "failed",
        "method": method,
        "version": version,
    }
    try:
        result = semantic_assessor.assess(
            _plain_json_snapshot(reference_ai_reading),
            _plain_json_snapshot(reference_reading_context),
            _plain_json_snapshot(reference_judgment_metadata),
        )
    except Exception:
        return _build_quality_report_v2(
            input_contracts,
            semantic_assessment,
            deterministic_candidates
            + (_semantic_infrastructure_candidate("semantic_assessment_failed"),),
        )

    try:
        status, semantic_candidates = _validate_semantic_assessor_result(
            result,
            reference_ai_reading,
            reference_reading_context,
            reference_judgment_metadata,
        )
    except Exception:
        return _build_quality_report_v2(
            input_contracts,
            semantic_assessment,
            deterministic_candidates
            + (_semantic_infrastructure_candidate("semantic_assessment_failed"),),
        )

    semantic_assessment["status"] = status
    if status == "inconclusive":
        deterministic_candidates += (
            _semantic_infrastructure_candidate(
                "semantic_assessment_inconclusive"
            ),
        )
    return _build_quality_report_v2(
        input_contracts,
        semantic_assessment,
        deterministic_candidates,
        semantic_finding_candidates=semantic_candidates,
    )


def evaluate_ai_reading_quality_v2(
    ai_reading: Mapping[str, Any],
    reading_context: Mapping[str, Any],
    judgment_metadata: Mapping[str, Any],
    *,
    semantic_assessor: SemanticAssessorV2 | None = None,
) -> AIReadingQualityReportV2:
    """Validate inputs and run the provider-independent semantic lifecycle."""

    for name, value in (
        ("ai_reading", ai_reading),
        ("reading_context", reading_context),
        ("judgment_metadata", judgment_metadata),
    ):
        if not isinstance(value, Mapping):
            raise TypeError(f"{name} must be a Mapping")

    input_contracts = _project_input_contracts(
        ai_reading,
        reading_context,
        judgment_metadata,
    )
    deterministic_candidates: list[dict[str, Any]] = []

    reading_context_snapshot = _try_plain_json_snapshot(reading_context)
    reading_context_report = (
        validate_reading_context_v2(reading_context_snapshot)
        if reading_context_snapshot is not None
        else {"valid": False}
    )

    judgment_metadata_snapshot = _try_plain_json_snapshot(judgment_metadata)
    judgment_metadata_report = (
        validate_common_judgment_metadata(judgment_metadata_snapshot)
        if judgment_metadata_snapshot is not None
        else {"valid": False}
    )

    ai_reading_snapshot = _try_plain_json_snapshot(ai_reading)
    ai_reading_valid = (
        ai_reading_snapshot is not None
        and _is_ai_reading_v2_final_contract(ai_reading_snapshot)
    )

    if not reading_context_report["valid"]:
        deterministic_candidates.append(
            _input_error_candidate(
                "input_contract_invalid",
                "reading_context_v2",
            )
        )
    if not judgment_metadata_report["valid"]:
        deterministic_candidates.append(
            _input_error_candidate(
                "input_contract_invalid",
                "common_judgment_metadata_v1",
            )
        )
    if not ai_reading_valid:
        deterministic_candidates.append(
            _input_error_candidate(
                "ai_reading_contract_invalid",
                "ai_reading_v2",
            )
        )

    prompt_report: Mapping[str, Any] | None = None
    if reading_context_report["valid"] and judgment_metadata_report["valid"]:
        prompt_report = validate_ai_reading_prompt_inputs_v2(
            reading_context_snapshot,
            judgment_metadata_snapshot,
        )
        if not prompt_report["valid"]:
            deterministic_candidates.append(
                _input_error_candidate(
                    "input_contract_invalid",
                    "reading_context_v2",
                    "common_judgment_metadata_v1",
                )
            )

    if ai_reading_valid and prompt_report is not None and prompt_report["valid"]:
        request = build_ai_reading_request_v2(
            reading_context_snapshot,
            judgment_metadata_snapshot,
        )
        if _trusted_identity_mismatch(ai_reading_snapshot, request):
            deterministic_candidates.append(
                _input_error_candidate(
                    "input_contract_mismatch",
                    "ai_reading_v2",
                    "reading_context_v2",
                    "common_judgment_metadata_v1",
                )
            )
        deterministic_candidates.extend(
            _trusted_reference_candidates(ai_reading_snapshot, request)
        )

    report = _run_semantic_assessor_v2(
        input_contracts,
        deterministic_candidates,
        ai_reading_snapshot if ai_reading_snapshot is not None else ai_reading,
        (
            reading_context_snapshot
            if reading_context_snapshot is not None
            else reading_context
        ),
        (
            judgment_metadata_snapshot
            if judgment_metadata_snapshot is not None
            else judgment_metadata
        ),
        semantic_assessor,
    )
    if report.decision == "pass":
        raise NotImplementedError(
            "Quality Gate v2 pass requires remaining deterministic checks"
        )
    return report


__all__ = [
    "AI_READING_QUALITY_REPORT_V2_METHOD",
    "AI_READING_QUALITY_REPORT_V2_SCHEMA_VERSION",
    "AI_READING_QUALITY_REPORT_V2_STATUS",
    "AI_READING_QUALITY_REPORT_V2_VERSION",
    "AIReadingQualityFindingV2",
    "AIReadingQualityReportV2",
    "SemanticAssessorV2",
    "evaluate_ai_reading_quality_v2",
]
