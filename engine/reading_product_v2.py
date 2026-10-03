"""Immutable PASS-only publication product for AI Reading v2."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from datetime import datetime
from hashlib import sha256
import json
import math
from typing import Any

from engine.reading_context_v2 import validate_reading_context_v2
from engine.reading_quality_v2 import (
    AIReadingQualityFindingV2,
    AIReadingQualityReportV2,
    _is_ai_reading_v2_final_contract,
)
from engine.reading_repair_v2 import AIReadingRepairResultV2, RepairAttemptLogV2


READING_PRODUCT_V2_SCHEMA_VERSION = "reading_product_v2"
READING_PRODUCT_V2_VERSION = "reading_product_v2"
READING_PRODUCT_V2_METHOD = "reading_product_v2"
READING_PRODUCT_V2_STATUS = "ready_for_publication"

_TOP_FIELDS = (
    "schema_version", "version", "method", "status", "engine_result",
    "reading_context", "ai_reading", "quality_report", "repair_history", "metadata",
)
_REPAIR_FIELDS = ("state", "result")
_METADATA_FIELDS = (
    "product_version", "engine_version", "reading_context_schema",
    "ai_reading_version", "ai_generation_method", "quality_gate_version",
    "quality_status", "generated_at", "recalculates_astrology",
    "rewrites_ai_reading", "snapshot_hashes", "source_bundle_sha256",
)
_HASH_FIELDS = (
    "engine_result", "reading_context", "ai_reading", "quality_report", "repair_history",
)


class ReadingProductV2ValidationError(ValueError):
    """A source or product violates the frozen ReadingProduct v2 contract."""


def _plain(value: Any, active: set[int] | None = None) -> Any:
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("JSON numbers must be finite")
        return value
    if not isinstance(value, Mapping) and type(value) is not list:
        raise TypeError("value is not plain JSON")
    active = set() if active is None else active
    identity = id(value)
    if identity in active:
        raise ValueError("JSON data must not contain cycles")
    active.add(identity)
    try:
        if isinstance(value, Mapping):
            result: dict[str, Any] = {}
            for key in value:
                if type(key) is not str:
                    raise TypeError("JSON keys must be strings")
                result[key] = _plain(value[key], active)
            return result
        return [_plain(item, active) for item in value]
    finally:
        active.remove(identity)


def _hash(value: Any) -> str:
    return sha256(json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True, allow_nan=False,
    ).encode("utf-8")).hexdigest()


def _report_snapshot(value: Any) -> tuple[AIReadingQualityReportV2, dict[str, Any]]:
    if not isinstance(value, AIReadingQualityReportV2):
        raise ReadingProductV2ValidationError(
            "quality_report must be AIReadingQualityReportV2"
        )
    try:
        owner = AIReadingQualityReportV2(
            schema_version=value.schema_version, version=value.version, method=value.method,
            status=value.status, decision=value.decision, blocking=value.blocking,
            human_review_required=value.human_review_required,
            error_count=value.error_count, warning_count=value.warning_count,
            info_count=value.info_count, input_contracts=deepcopy(value.input_contracts),
            semantic_assessment=deepcopy(value.semantic_assessment), findings=tuple(value.findings),
        )
        snapshot = _plain(owner.to_dict())
    except Exception:
        owner = None
        snapshot = None
    if owner is None or snapshot is None:
        raise ReadingProductV2ValidationError("quality_report owner contract is invalid")
    return owner, snapshot


def _report_from_snapshot(value: Any) -> AIReadingQualityReportV2:
    if not isinstance(value, Mapping) or tuple(value) != (
        "schema_version", "version", "method", "status", "decision", "blocking",
        "human_review_required", "error_count", "warning_count", "info_count",
        "input_contracts", "semantic_assessment", "findings",
    ):
        raise ValueError("quality report snapshot shape is invalid")
    findings_value = value["findings"]
    if type(findings_value) is not list:
        raise ValueError("quality report findings must be an array")
    findings = tuple(AIReadingQualityFindingV2(
        finding_id=item["finding_id"], code=item["code"], severity=item["severity"],
        blocking=item["blocking"], path=item["path"], message=item["message"],
        evidence=tuple(item["evidence"]), repairability=item["repairability"],
        requires_human_review=item["requires_human_review"],
    ) for item in findings_value if isinstance(item, Mapping) and tuple(item) == (
        "finding_id", "code", "severity", "blocking", "path", "message",
        "evidence", "repairability", "requires_human_review",
    ))
    if len(findings) != len(findings_value):
        raise ValueError("quality report finding shape is invalid")
    return AIReadingQualityReportV2(
        schema_version=value["schema_version"], version=value["version"],
        method=value["method"], status=value["status"], decision=value["decision"],
        blocking=value["blocking"], human_review_required=value["human_review_required"],
        error_count=value["error_count"], warning_count=value["warning_count"],
        info_count=value["info_count"], input_contracts=deepcopy(value["input_contracts"]),
        semantic_assessment=deepcopy(value["semantic_assessment"]), findings=findings,
    )


def _repair_from_snapshot(value: Any) -> AIReadingRepairResultV2:
    if not isinstance(value, Mapping) or tuple(value) != (
        "schema_version", "version", "method", "status", "initial_ai_reading",
        "final_ai_reading", "initial_quality_report", "final_quality_report",
        "target_finding_ids", "attempts",
    ):
        raise ValueError("repair result snapshot shape is invalid")
    attempts_value = value["attempts"]
    if type(attempts_value) is not list:
        raise ValueError("repair attempts must be an array")
    attempts = tuple(RepairAttemptLogV2(
        attempt=item["attempt"], issue_codes=tuple(item["issue_codes"]),
        before_hash=item["before_hash"], after_hash=item["after_hash"],
        result=item["result"],
    ) for item in attempts_value if isinstance(item, Mapping) and tuple(item) == (
        "attempt", "issue_codes", "before_hash", "after_hash", "result",
    ))
    if len(attempts) != len(attempts_value):
        raise ValueError("repair attempt shape is invalid")
    return AIReadingRepairResultV2(
        status=value["status"], initial_ai_reading=value["initial_ai_reading"],
        final_ai_reading=value["final_ai_reading"],
        initial_quality_report=value["initial_quality_report"],
        final_quality_report=value["final_quality_report"],
        target_finding_ids=tuple(value["target_finding_ids"]), attempts=attempts,
    )


def _identity(value: Mapping[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    return {field: value.get(field) if type(value.get(field)) is str else None for field in fields}


def _validate_generated_at(value: Any) -> str:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
        or value.microsecond != 0
    ):
        raise ReadingProductV2ValidationError(
            "generated_at must be timezone-aware with zero microseconds"
        )
    return value.isoformat(timespec="seconds")


def _validate_repair(
    repair_result: Any,
    ai_reading: Mapping[str, Any],
    quality_report: AIReadingQualityReportV2,
) -> dict[str, Any]:
    if repair_result is None:
        return {"state": "not_repaired", "result": None}
    if not isinstance(repair_result, AIReadingRepairResultV2):
        raise ReadingProductV2ValidationError("repair_result contract is invalid")
    try:
        result = _plain(repair_result.to_dict())
        attempts = repair_result.attempts
        valid = (
            repair_result.status == "pass"
            and repair_result.final_ai_reading == ai_reading
            and repair_result.final_quality_report.to_dict() == quality_report.to_dict()
            and len(attempts) in (1, 2)
            and attempts[0].before_hash == _hash(repair_result.initial_ai_reading)
            and attempts[-1].after_hash == _hash(ai_reading)
            and all(left.after_hash == right.before_hash for left, right in zip(attempts, attempts[1:]))
        )
    except Exception:
        valid = False
        result = None
    if not valid or result is None:
        raise ReadingProductV2ValidationError("repair_result provenance is inconsistent")
    return {"state": "auto_repair_v2", "result": result}


def _validate_cross_sources(
    engine_result: Mapping[str, Any],
    reading_context: Mapping[str, Any],
    ai_reading: Mapping[str, Any],
    report: AIReadingQualityReportV2,
) -> str:
    if validate_reading_context_v2(reading_context).get("valid") is not True:
        raise ReadingProductV2ValidationError("reading_context owner contract is invalid")
    if not _is_ai_reading_v2_final_contract(ai_reading):
        raise ReadingProductV2ValidationError("ai_reading final contract is invalid")
    if ai_reading.get("status") != "completed" or ai_reading.get("validation", {}).get("valid") is not True:
        raise ReadingProductV2ValidationError("ai_reading is not completed and valid")
    if report.status != "completed" or report.decision != "pass":
        raise ReadingProductV2ValidationError("quality_report must be completed PASS")
    expected_ai = _identity(ai_reading, (
        "schema_version", "version", "method", "status", "engine_version",
    ))
    expected_rc = _identity(reading_context, (
        "schema_version", "version", "method", "status",
    ))
    if report.input_contracts.get("ai_reading_v2") != expected_ai:
        raise ReadingProductV2ValidationError("quality_report AI identity mismatch")
    if report.input_contracts.get("reading_context_v2") != expected_rc:
        raise ReadingProductV2ValidationError("quality_report context identity mismatch")
    source_contracts = ai_reading.get("source_contracts")
    if not isinstance(source_contracts, Mapping):
        raise ReadingProductV2ValidationError("ai_reading source contracts are invalid")
    if report.input_contracts.get("common_judgment_metadata_v1") != source_contracts.get("judgment_metadata"):
        raise ReadingProductV2ValidationError("judgment metadata identity mismatch")
    if source_contracts.get("reading_context") != expected_rc:
        raise ReadingProductV2ValidationError("reading context source identity mismatch")
    metadata = engine_result.get("engine_metadata")
    engine_version = metadata.get("engine_version") if isinstance(metadata, Mapping) else None
    if (
        type(engine_version) is not str or not engine_version
        or reading_context.get("engine_version") != engine_version
        or ai_reading.get("engine_version") != engine_version
    ):
        raise ReadingProductV2ValidationError("engine version mismatch")
    return engine_version


class ReadingProductV2:
    """Immutable owner object exposing defensive JSON snapshots."""

    __slots__ = ("_snapshot",)

    def __init__(self, snapshot: Mapping[str, Any]) -> None:
        value = _plain(snapshot)
        _validate_product_snapshot(value)
        self._snapshot = value

    @property
    def status(self) -> str:
        return self._snapshot["status"]

    @property
    def quality_report(self) -> dict[str, Any]:
        return deepcopy(self._snapshot["quality_report"])

    @property
    def metadata(self) -> dict[str, Any]:
        return deepcopy(self._snapshot["metadata"])

    def to_dict(self) -> dict[str, Any]:
        return deepcopy(self._snapshot)


def _validate_product_snapshot(value: Mapping[str, Any]) -> None:
    try:
        if tuple(value) != _TOP_FIELDS:
            raise ValueError
        if (
            value["schema_version"] != READING_PRODUCT_V2_SCHEMA_VERSION
            or value["version"] != READING_PRODUCT_V2_VERSION
            or value["method"] != READING_PRODUCT_V2_METHOD
            or value["status"] != READING_PRODUCT_V2_STATUS
        ):
            raise ValueError
        report = _report_from_snapshot(value["quality_report"])
        engine_version = _validate_cross_sources(
            value["engine_result"], value["reading_context"], value["ai_reading"], report,
        )
        repair = value["repair_history"]
        metadata = value["metadata"]
        if tuple(repair) != _REPAIR_FIELDS or tuple(metadata) != _METADATA_FIELDS:
            raise ValueError
        if repair["state"] == "not_repaired":
            if repair["result"] is not None:
                raise ValueError
        elif repair["state"] == "auto_repair_v2":
            repair_result = _repair_from_snapshot(repair["result"])
            if (
                repair_result.status != "pass"
                or repair_result.final_ai_reading != value["ai_reading"]
                or repair_result.final_quality_report.to_dict() != value["quality_report"]
            ):
                raise ValueError
        else:
            raise ValueError
        generated_at = datetime.fromisoformat(metadata["generated_at"])
        if (
            generated_at.tzinfo is None or generated_at.utcoffset() is None
            or generated_at.microsecond != 0
            or generated_at.isoformat(timespec="seconds") != metadata["generated_at"]
        ):
            raise ValueError
        expected_metadata = {
            "product_version": READING_PRODUCT_V2_VERSION,
            "engine_version": engine_version,
            "reading_context_schema": value["reading_context"]["schema_version"],
            "ai_reading_version": value["ai_reading"]["version"],
            "ai_generation_method": value["ai_reading"]["method"],
            "quality_gate_version": report.version,
            "quality_status": report.decision,
        }
        if any(metadata[field] != expected for field, expected in expected_metadata.items()):
            raise ValueError
        if tuple(metadata["snapshot_hashes"]) != _HASH_FIELDS:
            raise ValueError
        for field in _HASH_FIELDS:
            if metadata["snapshot_hashes"][field] != _hash(value[field]):
                raise ValueError
        bundle = {field: value[field] for field in _HASH_FIELDS}
        if metadata["source_bundle_sha256"] != _hash(bundle):
            raise ValueError
        if metadata["recalculates_astrology"] is not False:
            raise ValueError
        if metadata["rewrites_ai_reading"] != (
            "none" if repair["state"] == "not_repaired" else "auto_repair_v2"
        ):
            raise ValueError
    except Exception:
        raise ReadingProductV2ValidationError("ReadingProductV2 snapshot is invalid") from None


def build_reading_product_v2(
    engine_result: Mapping[str, Any],
    reading_context: Mapping[str, Any],
    ai_reading: Mapping[str, Any],
    quality_report: AIReadingQualityReportV2,
    *,
    generated_at: datetime,
    repair_result: AIReadingRepairResultV2 | None = None,
) -> ReadingProductV2:
    """Build the frozen four-source, PASS-only publication snapshot."""
    try:
        engine_snapshot = _plain(engine_result)
        context_snapshot = _plain(reading_context)
        ai_snapshot = _plain(ai_reading)
    except Exception:
        raise ReadingProductV2ValidationError("source inputs must be plain JSON objects") from None
    if not all(isinstance(item, dict) for item in (engine_snapshot, context_snapshot, ai_snapshot)):
        raise ReadingProductV2ValidationError("source inputs must be JSON objects")
    report, report_snapshot = _report_snapshot(quality_report)
    engine_version = _validate_cross_sources(
        engine_snapshot, context_snapshot, ai_snapshot, report,
    )
    repair_history = _validate_repair(repair_result, ai_snapshot, report)
    generated_at_value = _validate_generated_at(generated_at)
    hashes = {
        "engine_result": _hash(engine_snapshot),
        "reading_context": _hash(context_snapshot),
        "ai_reading": _hash(ai_snapshot),
        "quality_report": _hash(report_snapshot),
        "repair_history": _hash(repair_history),
    }
    bundle = {
        "engine_result": engine_snapshot,
        "reading_context": context_snapshot,
        "ai_reading": ai_snapshot,
        "quality_report": report_snapshot,
        "repair_history": repair_history,
    }
    metadata = {
        "product_version": READING_PRODUCT_V2_VERSION,
        "engine_version": engine_version,
        "reading_context_schema": context_snapshot["schema_version"],
        "ai_reading_version": ai_snapshot["version"],
        "ai_generation_method": ai_snapshot["method"],
        "quality_gate_version": report.version,
        "quality_status": report.decision,
        "generated_at": generated_at_value,
        "recalculates_astrology": False,
        "rewrites_ai_reading": repair_history["state"] if repair_result is not None else "none",
        "snapshot_hashes": hashes,
        "source_bundle_sha256": _hash(bundle),
    }
    product = {
        "schema_version": READING_PRODUCT_V2_SCHEMA_VERSION,
        "version": READING_PRODUCT_V2_VERSION,
        "method": READING_PRODUCT_V2_METHOD,
        "status": READING_PRODUCT_V2_STATUS,
        **bundle,
        "metadata": metadata,
    }
    return ReadingProductV2(product)


__all__ = [
    "READING_PRODUCT_V2_SCHEMA_VERSION", "READING_PRODUCT_V2_VERSION",
    "READING_PRODUCT_V2_METHOD", "READING_PRODUCT_V2_STATUS",
    "ReadingProductV2ValidationError", "ReadingProductV2", "build_reading_product_v2",
]
