"""Targeted, fail-closed Auto-Repair v2 for final AI Reading v2 text.

This module owns the frozen section 24 contract.  It never recalculates
astrology and never delegates ownership of trusted fields to the provider.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from hashlib import sha256
import json
import math
from typing import Any

from engine.judgment_metadata import validate_common_judgment_metadata
from engine.reading_context_v2 import validate_reading_context_v2
from engine.reading_prompt_v2 import build_ai_reading_request_v2
from engine.reading_quality_v2 import (
    AIReadingQualityFindingV2,
    AIReadingQualityReportV2,
    SemanticAssessorV2,
    evaluate_ai_reading_quality_v2,
)


AI_READING_REPAIR_V2_SCHEMA_VERSION = "ai_reading_repair_result_v2"
AI_READING_REPAIR_V2_VERSION = "ai_reading_repair_v2"
AI_READING_REPAIR_V2_METHOD = "openai_quality_issue_targeted_patch_v2"
AI_READING_REPAIR_V2_MAX_ATTEMPTS = 2

AI_READING_REPAIR_V2_JSON_SCHEMA_NAME = "ai_reading_repair_patch_v2"
AI_READING_REPAIR_V2_INSTRUCTIONS = (
    "You repair only the supplied AI Reading v2 text fields. "
    "Return only JSON matching the supplied strict schema. "
    "Use only op=replace and only an allowed path. "
    "Return patches in the exact order of editable_blocks. "
    "Do not invent or modify trusted facts, references, identities, catalogs, "
    "section metadata, years, disclaimer, or validation data. "
    "For a relationships.interpretation target, preserve claim_type=astrology and repair "
    "the text as an astrology observation grounded in the trusted branch-relation facts "
    "followed by its astrology interpretation. Keep source_components exactly relations and "
    "source_fact_codes exactly chart.pillar_sequence. Do not put generic advice or action "
    "proposals in interpretation; leave practical actions to advice."
)

_SUPPORTED_REASONING_EFFORTS = ("minimal", "low", "medium", "high")
_REPAIR_REQUEST_FIELDS = (
    "schema_version",
    "attempt",
    "target_findings",
    "editable_blocks",
    "grounding_input",
)
_EDITABLE_BLOCK_FIELDS = ("path", "text")
_PATCH_RESPONSE_FIELDS = ("patches",)
_PATCH_FIELDS = ("op", "path", "value")
_PROVIDER_REQUEST_FAILURE_MESSAGES = {
    "schema_rejected": "repair provider request failed: schema_rejected",
    "authentication_failed": "repair provider request failed: authentication_failed",
    "rate_limited": "repair provider request failed: rate_limited",
    "bad_request": "repair provider request failed: bad_request",
    "unavailable": "repair provider request failed: unavailable",
    "request_failed": "repair provider request failed",
}
_ATTEMPT_LOG_FIELDS = (
    "attempt",
    "issue_codes",
    "before_hash",
    "after_hash",
    "result",
)
_RESULT_FIELDS = (
    "schema_version",
    "version",
    "method",
    "status",
    "initial_ai_reading",
    "final_ai_reading",
    "initial_quality_report",
    "final_quality_report",
    "target_finding_ids",
    "attempts",
)
_CANDIDATE_CONTRACT_CODES = frozenset(
    (
        "input_contract_invalid",
        "input_contract_mismatch",
        "ai_reading_contract_invalid",
        "trusted_field_mismatch",
        "reference_resolution_error",
        "warning_uncertainty_not_preserved",
        "disclaimer_mismatch",
        "future_year_integrity_error",
    )
)
_REPAIR_PATCH_SCHEMA = {
    "type": "object",
    "properties": {
        "patches": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "properties": {
                    "op": {"const": "replace"},
                    "path": {"type": "string", "minLength": 1},
                    "value": {"type": "string", "minLength": 1},
                },
                "required": ["op", "path", "value"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["patches"],
    "additionalProperties": False,
}


def _openai_transport_patch_schema() -> dict[str, Any]:
    """Return the approved OpenAI-only projection of the repair schema."""

    transport = deepcopy(_REPAIR_PATCH_SCHEMA)
    transport["properties"]["patches"]["items"]["properties"]["op"][
        "type"
    ] = "string"
    return transport


class AIReadingRepairV2Error(RuntimeError):
    """Base error with sanitized, optional attempt diagnostics."""

    def __init__(
        self,
        message: str,
        *,
        attempt: int | None = None,
        issue_codes: Sequence[str] = (),
        before_hash: str | None = None,
        after_hash: str | None = None,
    ) -> None:
        super().__init__(message)
        self._attempt = attempt
        self._issue_codes = tuple(issue_codes)
        self._before_hash = before_hash
        self._after_hash = after_hash

    @property
    def attempt(self) -> int | None:
        return self._attempt

    @property
    def issue_codes(self) -> tuple[str, ...]:
        return self._issue_codes

    @property
    def before_hash(self) -> str | None:
        return self._before_hash

    @property
    def after_hash(self) -> str | None:
        return self._after_hash


class AIReadingRepairV2ConfigurationError(AIReadingRepairV2Error):
    """The caller inputs, trigger, or provider dependency are invalid."""


class AIReadingRepairV2ProviderRequestError(AIReadingRepairV2Error):
    """The single provider call for an attempt failed."""


class AIReadingRepairV2ProviderResponseError(AIReadingRepairV2Error):
    """The provider response is not the frozen strict response schema."""


class AIReadingRepairV2PatchValidationError(AIReadingRepairV2Error):
    """A schema-valid patch violates the local editable-text boundary."""


class AIReadingRepairV2CandidateValidationError(AIReadingRepairV2Error):
    """The patched candidate violates final or trusted-field invariants."""


class RepairAttemptLogV2:
    """One immutable, ordered Auto-Repair v2 attempt record."""

    __slots__ = ("_attempt", "_issue_codes", "_before_hash", "_after_hash", "_result")

    def __init__(
        self,
        *,
        attempt: int,
        issue_codes: Sequence[str],
        before_hash: str,
        after_hash: str,
        result: str,
    ) -> None:
        if type(attempt) is not int or attempt not in (1, 2):
            raise ValueError("attempt must be 1 or 2")
        if isinstance(issue_codes, (str, bytes, bytearray)):
            raise TypeError("issue_codes must be an array")
        codes = tuple(issue_codes)
        if not codes or any(type(code) is not str for code in codes):
            raise ValueError("issue_codes must be a non-empty string array")
        if not _is_sha256(before_hash) or not _is_sha256(after_hash):
            raise ValueError("attempt hashes must be lowercase SHA-256")
        if result not in ("repaired", "failed"):
            raise ValueError("attempt result is invalid")
        self._attempt = attempt
        self._issue_codes = codes
        self._before_hash = before_hash
        self._after_hash = after_hash
        self._result = result

    @property
    def attempt(self) -> int:
        return self._attempt

    @property
    def issue_codes(self) -> tuple[str, ...]:
        return self._issue_codes

    @property
    def before_hash(self) -> str:
        return self._before_hash

    @property
    def after_hash(self) -> str:
        return self._after_hash

    @property
    def result(self) -> str:
        return self._result

    def to_dict(self) -> dict[str, Any]:
        value = {
            "attempt": self.attempt,
            "issue_codes": list(self.issue_codes),
            "before_hash": self.before_hash,
            "after_hash": self.after_hash,
            "result": self.result,
        }
        if tuple(value) != _ATTEMPT_LOG_FIELDS:
            raise AssertionError("repair attempt log field order drifted")
        return value


class AIReadingRepairResultV2:
    """Immutable Auto-Repair v2 result with defensive snapshot accessors."""

    __slots__ = (
        "_status",
        "_initial_ai_reading",
        "_final_ai_reading",
        "_initial_quality_report",
        "_final_quality_report",
        "_target_finding_ids",
        "_attempts",
    )

    def __init__(
        self,
        *,
        status: str,
        initial_ai_reading: Mapping[str, Any],
        final_ai_reading: Mapping[str, Any],
        initial_quality_report: Mapping[str, Any],
        final_quality_report: Mapping[str, Any],
        target_finding_ids: Sequence[str],
        attempts: Sequence[RepairAttemptLogV2],
    ) -> None:
        if status not in ("pass", "exhausted"):
            raise ValueError("repair result status is invalid")
        initial_ai = _plain_json_snapshot(initial_ai_reading)
        final_ai = _plain_json_snapshot(final_ai_reading)
        initial_report = _plain_json_snapshot(initial_quality_report)
        final_report = _plain_json_snapshot(final_quality_report)
        initial_report_owner = _quality_report_from_snapshot(initial_report)
        final_report_owner = _quality_report_from_snapshot(final_report)
        initial_blocking = tuple(
            finding for finding in initial_report_owner.findings if finding.blocking
        )
        if (
            initial_report_owner.decision != "fail"
            or not initial_blocking
            or any(
                finding.repairability != "auto" for finding in initial_blocking
            )
        ):
            raise ValueError(
                "initial_quality_report is not eligible for automatic repair"
            )
        if isinstance(target_finding_ids, (str, bytes, bytearray)):
            raise TypeError("target_finding_ids must be an array")
        finding_ids = tuple(target_finding_ids)
        if isinstance(attempts, (str, bytes, bytearray)):
            raise TypeError("attempts must be an array")
        attempt_values = tuple(attempts)
        if not finding_ids or any(type(value) is not str for value in finding_ids):
            raise ValueError("target_finding_ids must be a non-empty string array")
        if not 1 <= len(attempt_values) <= AI_READING_REPAIR_V2_MAX_ATTEMPTS:
            raise ValueError("attempts must contain one or two entries")
        if any(type(value) is not RepairAttemptLogV2 for value in attempt_values):
            raise TypeError("attempts must contain RepairAttemptLogV2 values")
        if tuple(item.attempt for item in attempt_values) != tuple(
            range(1, len(attempt_values) + 1)
        ):
            raise ValueError("attempt logs must use consecutive attempt order")
        if any(item.result != "repaired" for item in attempt_values):
            raise ValueError("public repair results contain only completed valid attempts")
        expected_initial_targets = tuple(
            finding.finding_id
            for finding in initial_report_owner.findings
            if finding.repairability == "auto"
        )
        if finding_ids != expected_initial_targets:
            raise ValueError("target_finding_ids do not match the initial report order")
        if attempt_values[0].issue_codes != tuple(
            finding.code
            for finding in initial_report_owner.findings
            if finding.repairability == "auto"
        ):
            raise ValueError("first attempt issue_codes do not match initial targets")
        if attempt_values[0].before_hash != _canonical_hash(initial_ai):
            raise ValueError("first attempt before_hash does not bind initial_ai_reading")
        if attempt_values[-1].after_hash != _canonical_hash(final_ai):
            raise ValueError("final attempt after_hash does not bind final_ai_reading")
        if any(
            left.after_hash != right.before_hash
            for left, right in zip(attempt_values, attempt_values[1:])
        ):
            raise ValueError("attempt hash chain is invalid")
        expected_decision = "pass" if status == "pass" else None
        if expected_decision is not None and final_report_owner.decision != expected_decision:
            raise ValueError("pass result requires a PASS final report")
        if status == "exhausted" and final_report_owner.decision == "pass":
            raise ValueError("exhausted result cannot contain a PASS final report")
        if (
            status == "exhausted"
            and len(attempt_values) < AI_READING_REPAIR_V2_MAX_ATTEMPTS
            and _automatic_repair_plan(
                final_report_owner,
                final_ai,
                initial=False,
            )
            is not None
        ):
            raise ValueError(
                "one-attempt exhausted result cannot remain eligible for repair"
            )
        self._status = status
        self._initial_ai_reading = initial_ai
        self._final_ai_reading = final_ai
        self._initial_quality_report = initial_report
        self._final_quality_report = final_report
        self._target_finding_ids = finding_ids
        self._attempts = attempt_values

    @property
    def schema_version(self) -> str:
        return AI_READING_REPAIR_V2_SCHEMA_VERSION

    @property
    def version(self) -> str:
        return AI_READING_REPAIR_V2_VERSION

    @property
    def method(self) -> str:
        return AI_READING_REPAIR_V2_METHOD

    @property
    def status(self) -> str:
        return self._status

    @property
    def initial_ai_reading(self) -> dict[str, Any]:
        return deepcopy(self._initial_ai_reading)

    @property
    def final_ai_reading(self) -> dict[str, Any]:
        return deepcopy(self._final_ai_reading)

    @property
    def initial_quality_report(self) -> AIReadingQualityReportV2:
        return _quality_report_from_snapshot(self._initial_quality_report)

    @property
    def final_quality_report(self) -> AIReadingQualityReportV2:
        return _quality_report_from_snapshot(self._final_quality_report)

    @property
    def target_finding_ids(self) -> tuple[str, ...]:
        return self._target_finding_ids

    @property
    def attempts(self) -> tuple[RepairAttemptLogV2, ...]:
        return self._attempts

    def to_dict(self) -> dict[str, Any]:
        value = {
            "schema_version": self.schema_version,
            "version": self.version,
            "method": self.method,
            "status": self.status,
            "initial_ai_reading": self.initial_ai_reading,
            "final_ai_reading": self.final_ai_reading,
            "initial_quality_report": self.initial_quality_report.to_dict(),
            "final_quality_report": self.final_quality_report.to_dict(),
            "target_finding_ids": list(self.target_finding_ids),
            "attempts": [item.to_dict() for item in self.attempts],
        }
        if tuple(value) != _RESULT_FIELDS:
            raise AssertionError("repair result field order drifted")
        return value


def _is_sha256(value: Any) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _plain_json_snapshot(value: Any, active: set[int] | None = None) -> Any:
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
            snapshot: dict[str, Any] = {}
            for key in value:
                if type(key) is not str:
                    raise TypeError("JSON object keys must be plain strings")
                snapshot[key] = _plain_json_snapshot(value[key], active)
            return snapshot
        return [_plain_json_snapshot(item, active) for item in value]
    finally:
        active.remove(identity)


def _canonical_hash(value: Any) -> str:
    return sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _snapshot_quality_report(
    value: Any,
) -> tuple[AIReadingQualityReportV2, dict[str, Any]]:
    if not isinstance(value, AIReadingQualityReportV2):
        raise AIReadingRepairV2ConfigurationError(
            "quality_report must be AIReadingQualityReportV2"
        )
    validation_failed = False
    try:
        canonical = AIReadingQualityReportV2(
            schema_version=value.schema_version,
            version=value.version,
            method=value.method,
            status=value.status,
            decision=value.decision,
            blocking=value.blocking,
            human_review_required=value.human_review_required,
            error_count=value.error_count,
            warning_count=value.warning_count,
            info_count=value.info_count,
            input_contracts=deepcopy(value.input_contracts),
            semantic_assessment=deepcopy(value.semantic_assessment),
            findings=tuple(value.findings),
        )
        return canonical, _plain_json_snapshot(canonical.to_dict())
    except Exception:
        validation_failed = True
    if validation_failed:
        raise AIReadingRepairV2ConfigurationError(
            "quality_report violates its owner contract"
        )
    raise AssertionError("unreachable quality report validation state")


def _quality_report_from_snapshot(
    value: Mapping[str, Any],
) -> AIReadingQualityReportV2:
    findings = tuple(
        AIReadingQualityFindingV2(
            finding_id=item["finding_id"],
            code=item["code"],
            severity=item["severity"],
            blocking=item["blocking"],
            path=item["path"],
            message=item["message"],
            evidence=tuple(deepcopy(item["evidence"])),
            repairability=item["repairability"],
            requires_human_review=item["requires_human_review"],
        )
        for item in value["findings"]
    )
    return AIReadingQualityReportV2(
        schema_version=value["schema_version"],
        version=value["version"],
        method=value["method"],
        status=value["status"],
        decision=value["decision"],
        blocking=value["blocking"],
        human_review_required=value["human_review_required"],
        error_count=value["error_count"],
        warning_count=value["warning_count"],
        info_count=value["info_count"],
        input_contracts=deepcopy(value["input_contracts"]),
        semantic_assessment=deepcopy(value["semantic_assessment"]),
        findings=findings,
    )


def _identity_projection(value: Mapping[str, Any], fields: Sequence[str]) -> dict[str, Any]:
    return {
        field: value.get(field) if type(value.get(field)) is str else None
        for field in fields
    }


def _validate_report_inputs(
    report: AIReadingQualityReportV2,
    ai_reading: Mapping[str, Any],
    reading_context: Mapping[str, Any],
    judgment_metadata: Mapping[str, Any],
) -> None:
    expected = {
        "ai_reading_v2": _identity_projection(
            ai_reading,
            ("schema_version", "version", "method", "status", "engine_version"),
        ),
        "reading_context_v2": _identity_projection(
            reading_context,
            ("schema_version", "version", "method", "status"),
        ),
        "common_judgment_metadata_v1": _identity_projection(
            judgment_metadata,
            ("schema_version",),
        ),
    }
    if report.input_contracts != expected:
        raise AIReadingRepairV2ConfigurationError(
            "quality_report input identities do not match repair inputs"
        )


def _validate_owner_inputs(
    ai_reading: Any,
    reading_context: Any,
    judgment_metadata: Any,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    for name, value in (
        ("ai_reading", ai_reading),
        ("reading_context", reading_context),
        ("judgment_metadata", judgment_metadata),
    ):
        if not isinstance(value, Mapping):
            raise AIReadingRepairV2ConfigurationError(f"{name} must be a Mapping")
    snapshot_failed = False
    try:
        ai_snapshot = _plain_json_snapshot(ai_reading)
        context_snapshot = _plain_json_snapshot(reading_context)
        metadata_snapshot = _plain_json_snapshot(judgment_metadata)
    except Exception:
        snapshot_failed = True
    if snapshot_failed:
        raise AIReadingRepairV2ConfigurationError(
            "repair inputs must be finite plain JSON trees"
        )
    validation_failed = False
    try:
        context_report = validate_reading_context_v2(context_snapshot)
        metadata_report = validate_common_judgment_metadata(metadata_snapshot)
    except Exception:
        validation_failed = True
    if validation_failed:
        raise AIReadingRepairV2ConfigurationError(
            "repair input owner validation failed"
        )
    if context_report.get("valid") is not True or metadata_report.get("valid") is not True:
        raise AIReadingRepairV2ConfigurationError(
            "repair input owner validation failed"
        )
    return ai_snapshot, context_snapshot, metadata_snapshot


def _validate_provider_options(
    *,
    client: Any,
    model: Any,
    max_output_tokens: Any,
    reasoning_effort: Any,
    store: Any,
) -> tuple[Any, str]:
    if not isinstance(model, str) or not model.strip():
        raise AIReadingRepairV2ConfigurationError(
            "model must be a non-empty caller-supplied string"
        )
    if (
        isinstance(max_output_tokens, bool)
        or not isinstance(max_output_tokens, int)
        or max_output_tokens <= 0
    ):
        raise AIReadingRepairV2ConfigurationError(
            "max_output_tokens must be a positive built-in integer"
        )
    if type(reasoning_effort) is not str or reasoning_effort not in _SUPPORTED_REASONING_EFFORTS:
        raise AIReadingRepairV2ConfigurationError("reasoning_effort is unsupported")
    if type(store) is not bool:
        raise AIReadingRepairV2ConfigurationError("store must be a built-in boolean")
    boundary_failed = False
    try:
        responses = getattr(client, "responses")
        create = getattr(responses, "create")
    except Exception:
        boundary_failed = True
    if boundary_failed:
        raise AIReadingRepairV2ConfigurationError(
            "client.responses.create is unavailable"
        )
    if not callable(create):
        raise AIReadingRepairV2ConfigurationError(
            "client.responses.create is unavailable"
        )
    return create, model.strip()


def _blocking_targets(
    report: AIReadingQualityReportV2,
    *,
    initial: bool,
) -> tuple[AIReadingQualityFindingV2, ...] | None:
    blocking = tuple(finding for finding in report.findings if finding.blocking)
    eligible = (
        report.decision == "fail"
        and bool(blocking)
        and all(finding.repairability == "auto" for finding in blocking)
    )
    if not eligible:
        if initial:
            raise AIReadingRepairV2ConfigurationError(
                "quality_report is not eligible for automatic repair"
            )
        return None
    targets = tuple(
        finding for finding in report.findings if finding.repairability == "auto"
    )
    if not targets:
        if initial:
            raise AIReadingRepairV2ConfigurationError(
                "quality_report has no automatic repair targets"
            )
        return None
    return targets


def _block_roots(ai_reading: Mapping[str, Any]) -> list[tuple[str, Mapping[str, Any]]]:
    roots: list[tuple[str, Mapping[str, Any]]] = []

    def append(path: str, value: Any) -> None:
        if isinstance(value, Mapping) and type(value.get("text")) is str:
            roots.append((path, value))

    append("/summary", ai_reading.get("summary"))
    sections = ai_reading.get("sections")
    if isinstance(sections, list):
        for section_index, section in enumerate(sections):
            if not isinstance(section, Mapping):
                continue
            for field in ("summary", "detail"):
                append(f"/sections/{section_index}/{field}", section.get(field))
            for field in ("evidence", "interpretation", "advice"):
                blocks = section.get(field)
                if not isinstance(blocks, list):
                    continue
                for block_index, block in enumerate(blocks):
                    append(
                        f"/sections/{section_index}/{field}/{block_index}",
                        block,
                    )
            if section.get("section_id") == "future_flow":
                yearly = section.get("yearly")
                if isinstance(yearly, list):
                    for year_index, entry in enumerate(yearly):
                        if not isinstance(entry, Mapping):
                            continue
                        for field in (
                            "title", "theme", "career", "wealth", "relationships", "caution",
                            "summary", "detail",
                        ):
                            append(
                                f"/sections/{section_index}/yearly/{year_index}/{field}",
                                entry.get(field),
                            )
                        advice = entry.get("advice")
                        if isinstance(advice, list):
                            for advice_index, block in enumerate(advice):
                                append(
                                    f"/sections/{section_index}/yearly/{year_index}/advice/{advice_index}",
                                    block,
                                )
    consultation = ai_reading.get("consultation_answer")
    if consultation is not None:
        append("/consultation_answer", consultation)
    long_term = ai_reading.get("long_term_luck")
    if isinstance(long_term, list):
        for index, detail in enumerate(long_term):
            if not isinstance(detail, Mapping):
                continue
            for field in ("title", "theme", "career", "wealth", "relationships", "caution"):
                append(f"/long_term_luck/{index}/{field}", detail.get(field))
            advice = detail.get("advice")
            if isinstance(advice, list):
                for advice_index, block in enumerate(advice):
                    append(f"/long_term_luck/{index}/advice/{advice_index}", block)
    return roots


def _derive_editable_blocks(
    ai_reading: Mapping[str, Any],
    targets: Sequence[AIReadingQualityFindingV2],
) -> list[dict[str, str]]:
    roots = _block_roots(ai_reading)
    editable: list[dict[str, str]] = []
    seen: set[str] = set()
    for finding in targets:
        matches = [
            (root, block)
            for root, block in roots
            if finding.path == root or finding.path.startswith(root + "/")
        ]
        if not matches:
            raise AIReadingRepairV2ConfigurationError(
                "target finding does not resolve to an editable text block"
            )
        longest = max(len(root) for root, _ in matches)
        longest_matches = [(root, block) for root, block in matches if len(root) == longest]
        if len(longest_matches) != 1:
            raise AIReadingRepairV2ConfigurationError(
                "target finding does not uniquely resolve to an editable text block"
            )
        root, block = longest_matches[0]
        path = root + "/text"
        if path not in seen:
            seen.add(path)
            editable.append({"path": path, "text": block["text"]})
    return editable


def _automatic_repair_plan(
    report: AIReadingQualityReportV2,
    ai_reading: Mapping[str, Any],
    *,
    initial: bool,
) -> tuple[
    tuple[AIReadingQualityFindingV2, ...],
    list[dict[str, str]],
] | None:
    targets = _blocking_targets(report, initial=initial)
    if targets is None:
        return None
    try:
        editable_blocks = _derive_editable_blocks(ai_reading, targets)
    except AIReadingRepairV2ConfigurationError:
        if initial:
            raise
        return None
    return targets, editable_blocks


def _repair_model_input(
    *,
    attempt: int,
    targets: Sequence[AIReadingQualityFindingV2],
    editable_blocks: Sequence[Mapping[str, str]],
    reading_context: Mapping[str, Any],
    judgment_metadata: Mapping[str, Any],
) -> dict[str, Any]:
    grounding_failed = False
    try:
        request = build_ai_reading_request_v2(reading_context, judgment_metadata)
        grounding_input = _plain_json_snapshot(request["model_input"])
    except Exception:
        grounding_failed = True
    if grounding_failed:
        raise AIReadingRepairV2ConfigurationError(
            "repair grounding input cannot be built"
        )
    value = {
        "schema_version": "ai_reading_repair_request_v2",
        "attempt": attempt,
        "target_findings": [finding.to_dict() for finding in targets],
        "editable_blocks": [dict(block) for block in editable_blocks],
        "grounding_input": grounding_input,
    }
    if tuple(value) != _REPAIR_REQUEST_FIELDS or any(
        tuple(block) != _EDITABLE_BLOCK_FIELDS for block in value["editable_blocks"]
    ):
        raise AssertionError("repair request field order drifted")
    return value


def _provider_payload(
    repair_model_input: Mapping[str, Any],
    *,
    model: str,
    max_output_tokens: int,
    reasoning_effort: str,
    store: bool,
) -> dict[str, Any]:
    serialized = json.dumps(
        repair_model_input,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=False,
        allow_nan=False,
    )
    return {
        "model": model,
        "instructions": AI_READING_REPAIR_V2_INSTRUCTIONS,
        "input": [{"role": "user", "content": serialized}],
        "max_output_tokens": max_output_tokens,
        "reasoning": {"effort": reasoning_effort},
        "store": store,
        "text": {
            "format": {
                "type": "json_schema",
                "name": AI_READING_REPAIR_V2_JSON_SCHEMA_NAME,
                "schema": _openai_transport_patch_schema(),
                "strict": True,
            }
        },
    }


def _provider_request_failure_message(error: BaseException) -> str:
    """Return only an allowlisted provider failure class, never provider data."""

    reason = "request_failed"
    try:
        code = getattr(error, "code", None)
        if type(code) is not str:
            body = getattr(error, "body", None)
            if type(body) is dict:
                nested = body.get("error")
                if type(nested) is dict:
                    code = nested.get("code")
                else:
                    code = body.get("code")
        if type(code) is str and code == "invalid_json_schema":
            reason = "schema_rejected"
        else:
            status_code = getattr(error, "status_code", None)
            if type(status_code) is int:
                if status_code in {401, 403}:
                    reason = "authentication_failed"
                elif status_code == 429:
                    reason = "rate_limited"
                elif status_code == 400:
                    reason = "bad_request"
                elif status_code >= 500:
                    reason = "unavailable"
    except Exception:
        reason = "request_failed"
    return _PROVIDER_REQUEST_FAILURE_MESSAGES[reason]


def _get_field(value: Any, name: str, default: Any = None) -> Any:
    access_failed = False
    try:
        if isinstance(value, Mapping):
            return value.get(name, default)
        return getattr(value, name, default)
    except Exception:
        access_failed = True
    if access_failed:
        raise AIReadingRepairV2ProviderResponseError(
            "provider response field access failed"
        )
    raise AssertionError("unreachable provider response field access state")


def _extract_output_text_untrusted(response: Any) -> str:
    direct = _get_field(response, "output_text")
    if type(direct) is str and direct.strip():
        return direct.strip()
    parts: list[str] = []
    output = _get_field(response, "output", [])
    if type(output) in (list, tuple):
        for item in output:
            content = _get_field(item, "content", [])
            if type(content) not in (list, tuple):
                continue
            for content_item in content:
                text = _get_field(content_item, "text")
                if type(text) is str and text.strip():
                    parts.append(text.strip())
    if parts:
        return "\n".join(parts)
    raise AIReadingRepairV2ProviderResponseError(
        "provider response contains no usable model output"
    )


def _extract_output_text(response: Any) -> str:
    error_message: str | None = None
    try:
        return _extract_output_text_untrusted(response)
    except AIReadingRepairV2ProviderResponseError as exc:
        error_message = str(exc)
    except Exception:
        error_message = "provider response extraction failed"
    raise AIReadingRepairV2ProviderResponseError(error_message)


def _reject_constant(value: str) -> None:
    raise ValueError("non-standard JSON constant")


def _object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON object key")
        value[key] = item
    return value


def _parse_response(text: str) -> dict[str, Any]:
    parse_failed = False
    try:
        value = json.loads(
            text,
            parse_constant=_reject_constant,
            object_pairs_hook=_object_without_duplicates,
        )
    except (json.JSONDecodeError, ValueError, TypeError, RecursionError):
        parse_failed = True
    if parse_failed:
        raise AIReadingRepairV2ProviderResponseError(
            "provider output is not strict duplicate-free JSON"
        )
    if not isinstance(value, dict) or tuple(value) != _PATCH_RESPONSE_FIELDS:
        raise AIReadingRepairV2ProviderResponseError(
            "provider output top-level schema is invalid"
        )
    patches = value["patches"]
    if type(patches) is not list or not patches:
        raise AIReadingRepairV2ProviderResponseError(
            "provider output patches must be a non-empty array"
        )
    for patch in patches:
        if not isinstance(patch, dict) or tuple(patch) != _PATCH_FIELDS:
            raise AIReadingRepairV2ProviderResponseError(
                "provider patch schema is invalid"
            )
        if patch["op"] != "replace":
            raise AIReadingRepairV2ProviderResponseError(
                "provider patch operation is invalid"
            )
        if type(patch["path"]) is not str or not patch["path"]:
            raise AIReadingRepairV2ProviderResponseError(
                "provider patch path is invalid"
            )
        if type(patch["value"]) is not str or not patch["value"]:
            raise AIReadingRepairV2ProviderResponseError(
                "provider patch value is invalid"
            )
    return value


def _validate_patches(
    response: Mapping[str, Any],
    editable_blocks: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    allowed = [block["path"] for block in editable_blocks]
    current = {block["path"]: block["text"] for block in editable_blocks}
    patches = response["patches"]
    paths = [patch["path"] for patch in patches]
    if len(paths) != len(set(paths)):
        raise AIReadingRepairV2PatchValidationError("duplicate patch path")
    for index, left in enumerate(paths):
        for right in paths[index + 1 :]:
            if left.startswith(right + "/") or right.startswith(left + "/"):
                raise AIReadingRepairV2PatchValidationError(
                    "patch paths have an ancestor relationship"
                )
    if any(path not in current for path in paths):
        raise AIReadingRepairV2PatchValidationError(
            "patch path is not an exact locally-derived editable path"
        )
    positions = [allowed.index(path) for path in paths]
    if positions != sorted(positions):
        raise AIReadingRepairV2PatchValidationError(
            "patch paths are not an editable-order subsequence"
        )
    validated: list[dict[str, str]] = []
    for patch in patches:
        value = patch["value"]
        if not value.strip():
            raise AIReadingRepairV2PatchValidationError(
                "patch value must not be whitespace-only"
            )
        if value == current[patch["path"]]:
            raise AIReadingRepairV2PatchValidationError("patch must not be a no-op")
        validated.append({"op": "replace", "path": patch["path"], "value": value})
    return validated


def _resolve_parent(value: Any, pointer: str) -> tuple[Any, str | int]:
    tokens = pointer[1:].split("/")
    current = value
    for token in tokens[:-1]:
        if isinstance(current, dict):
            current = current[token]
        elif isinstance(current, list):
            current = current[int(token)]
        else:
            raise KeyError(pointer)
    final = tokens[-1]
    if isinstance(current, list):
        return current, int(final)
    return current, final


def _set_pointer(value: Any, pointer: str, replacement: str) -> None:
    parent, key = _resolve_parent(value, pointer)
    parent[key] = replacement


def _apply_patches(
    current: Mapping[str, Any],
    patches: Sequence[Mapping[str, str]],
    *,
    attempt: int,
    issue_codes: Sequence[str],
    before_hash: str,
) -> dict[str, Any]:
    candidate = deepcopy(dict(current))
    candidate_failed = False
    try:
        for patch in patches:
            _set_pointer(candidate, patch["path"], patch["value"])
        candidate = _plain_json_snapshot(candidate)
        restored = deepcopy(candidate)
        for patch in patches:
            parent, key = _resolve_parent(current, patch["path"])
            _set_pointer(restored, patch["path"], parent[key])
        if _canonical_hash(restored) != _canonical_hash(current):
            raise ValueError("non-text field changed")
    except Exception:
        candidate_failed = True
    if candidate_failed:
        raise AIReadingRepairV2CandidateValidationError(
            "patched candidate violates the text-only invariant",
            attempt=attempt,
            issue_codes=issue_codes,
            before_hash=before_hash,
        )
    return candidate


def _evaluate_candidate(
    candidate: Mapping[str, Any],
    reading_context: Mapping[str, Any],
    judgment_metadata: Mapping[str, Any],
    semantic_assessor: SemanticAssessorV2 | None,
    *,
    attempt: int,
    issue_codes: Sequence[str],
    before_hash: str,
    after_hash: str,
) -> AIReadingQualityReportV2:
    evaluation_failed = False
    try:
        report = evaluate_ai_reading_quality_v2(
            candidate,
            reading_context,
            judgment_metadata,
            semantic_assessor=semantic_assessor,
        )
        canonical, _ = _snapshot_quality_report(report)
    except AIReadingRepairV2Error:
        raise
    except Exception:
        evaluation_failed = True
    if evaluation_failed:
        raise AIReadingRepairV2CandidateValidationError(
            "Quality Gate v2 could not evaluate the patched candidate",
            attempt=attempt,
            issue_codes=issue_codes,
            before_hash=before_hash,
            after_hash=after_hash,
        )
    if any(
        finding.code in _CANDIDATE_CONTRACT_CODES for finding in canonical.findings
    ):
        raise AIReadingRepairV2CandidateValidationError(
            "patched candidate violates final or trusted-field invariants",
            attempt=attempt,
            issue_codes=issue_codes,
            before_hash=before_hash,
            after_hash=after_hash,
        )
    return canonical


def repair_ai_reading_v2(
    ai_reading: Mapping[str, Any],
    quality_report: AIReadingQualityReportV2,
    reading_context: Mapping[str, Any],
    judgment_metadata: Mapping[str, Any],
    *,
    semantic_assessor: SemanticAssessorV2 | None,
    client: Any,
    model: str,
    max_output_tokens: int = 6000,
    reasoning_effort: str = "low",
    store: bool = False,
) -> AIReadingRepairResultV2:
    """Repair eligible model-owned text with at most two provider calls."""

    ai_snapshot, context_snapshot, metadata_snapshot = _validate_owner_inputs(
        ai_reading,
        reading_context,
        judgment_metadata,
    )
    initial_report, initial_report_snapshot = _snapshot_quality_report(quality_report)
    _validate_report_inputs(
        initial_report,
        ai_snapshot,
        context_snapshot,
        metadata_snapshot,
    )
    initial_plan = _automatic_repair_plan(
        initial_report,
        ai_snapshot,
        initial=True,
    )
    assert initial_plan is not None
    targets, initial_editable = initial_plan
    initial_target_ids = tuple(finding.finding_id for finding in targets)

    current_ai = ai_snapshot
    current_report = initial_report
    attempts: list[RepairAttemptLogV2] = []
    create = None
    resolved_model = ""

    for attempt in range(1, AI_READING_REPAIR_V2_MAX_ATTEMPTS + 1):
        if attempt == 1:
            current_targets = targets
            editable_blocks = initial_editable
        else:
            current_plan = _automatic_repair_plan(
                current_report,
                current_ai,
                initial=False,
            )
            if current_plan is None:
                break
            current_targets, editable_blocks = current_plan
        issue_codes = tuple(finding.code for finding in current_targets)
        before_hash = _canonical_hash(current_ai)
        if create is None:
            create, resolved_model = _validate_provider_options(
                client=client,
                model=model,
                max_output_tokens=max_output_tokens,
                reasoning_effort=reasoning_effort,
                store=store,
            )
        repair_input = _repair_model_input(
            attempt=attempt,
            targets=current_targets,
            editable_blocks=editable_blocks,
            reading_context=context_snapshot,
            judgment_metadata=metadata_snapshot,
        )
        payload = _provider_payload(
            repair_input,
            model=resolved_model,
            max_output_tokens=max_output_tokens,
            reasoning_effort=reasoning_effort,
            store=store,
        )
        provider_failure_message: str | None = None
        try:
            response = create(**deepcopy(payload))
        except Exception as exc:
            provider_failure_message = _provider_request_failure_message(exc)
        if provider_failure_message is not None:
            create = None
            payload = None
            repair_input = None
            raise AIReadingRepairV2ProviderRequestError(
                provider_failure_message,
                attempt=attempt,
                issue_codes=issue_codes,
                before_hash=before_hash,
            )
        response_error_type: type[AIReadingRepairV2Error] | None = None
        response_error_message = ""
        try:
            response_value = _parse_response(_extract_output_text(response))
        except AIReadingRepairV2Error as exc:
            if exc.attempt is not None:
                raise
            response_error_type = type(exc)
            response_error_message = str(exc)
        if response_error_type is not None:
            response = None
            payload = None
            repair_input = None
            raise response_error_type(
                response_error_message,
                attempt=attempt,
                issue_codes=issue_codes,
                before_hash=before_hash,
            )
        patch_error_message: str | None = None
        try:
            patches = _validate_patches(response_value, editable_blocks)
        except AIReadingRepairV2PatchValidationError as exc:
            patch_error_message = str(exc)
        if patch_error_message is not None:
            response = None
            response_value = None
            payload = None
            repair_input = None
            raise AIReadingRepairV2PatchValidationError(
                patch_error_message,
                attempt=attempt,
                issue_codes=issue_codes,
                before_hash=before_hash,
            )
        candidate = _apply_patches(
            current_ai,
            patches,
            attempt=attempt,
            issue_codes=issue_codes,
            before_hash=before_hash,
        )
        after_hash = _canonical_hash(candidate)
        if after_hash == before_hash:
            raise AIReadingRepairV2CandidateValidationError(
                "patched candidate hash did not change",
                attempt=attempt,
                issue_codes=issue_codes,
                before_hash=before_hash,
                after_hash=after_hash,
            )
        current_report = _evaluate_candidate(
            candidate,
            context_snapshot,
            metadata_snapshot,
            semantic_assessor,
            attempt=attempt,
            issue_codes=issue_codes,
            before_hash=before_hash,
            after_hash=after_hash,
        )
        attempts.append(
            RepairAttemptLogV2(
                attempt=attempt,
                issue_codes=issue_codes,
                before_hash=before_hash,
                after_hash=after_hash,
                result="repaired",
            )
        )
        current_ai = candidate
        if current_report.decision == "pass":
            status = "pass"
            break
    else:
        status = "exhausted"

    if current_report.decision != "pass":
        status = "exhausted"
    final_report_snapshot = _snapshot_quality_report(current_report)[1]
    return AIReadingRepairResultV2(
        status=status,
        initial_ai_reading=ai_snapshot,
        final_ai_reading=current_ai,
        initial_quality_report=initial_report_snapshot,
        final_quality_report=final_report_snapshot,
        target_finding_ids=initial_target_ids,
        attempts=attempts,
    )


__all__ = [
    "AI_READING_REPAIR_V2_SCHEMA_VERSION",
    "AI_READING_REPAIR_V2_VERSION",
    "AI_READING_REPAIR_V2_METHOD",
    "AI_READING_REPAIR_V2_MAX_ATTEMPTS",
    "AI_READING_REPAIR_V2_JSON_SCHEMA_NAME",
    "AI_READING_REPAIR_V2_INSTRUCTIONS",
    "RepairAttemptLogV2",
    "AIReadingRepairResultV2",
    "AIReadingRepairV2Error",
    "AIReadingRepairV2ConfigurationError",
    "AIReadingRepairV2ProviderRequestError",
    "AIReadingRepairV2ProviderResponseError",
    "AIReadingRepairV2PatchValidationError",
    "AIReadingRepairV2CandidateValidationError",
    "repair_ai_reading_v2",
]
