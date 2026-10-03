"""Transport-neutral Reading API v2 envelopes (no HTTP route)."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from engine.reading_pdf_v2 import READING_PDF_V2_VERSION
from engine.reading_product_v2 import ReadingProductV2


READING_API_V2_SCHEMA_VERSION = "reading_api_envelope_v2"
READING_API_V2_ERROR_SCHEMA_VERSION = "reading_api_error_v2"
READING_API_V2_VERSION = "v2"

_CODES = ("input_error", "unsupported", "calculation_error", "generation_error")
_STAGES = (
    "input", "calculation", "reading_context", "judgment_metadata", "prompt",
    "generation", "quality_gate", "repair", "product", "pdf", "publication",
)


class ReadingApiV2ValidationError(ValueError):
    pass


def _sha(value: Any) -> bool:
    return type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def build_reading_api_v2_envelope(
    product: ReadingProductV2,
    *,
    pdf_artifact: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(product, ReadingProductV2):
        raise ReadingApiV2ValidationError("product must be ReadingProductV2")
    try:
        snapshot = ReadingProductV2(product.to_dict()).to_dict()
    except Exception:
        raise ReadingApiV2ValidationError("product invariant is invalid") from None
    artifact = None
    if pdf_artifact is not None:
        if not isinstance(pdf_artifact, Mapping):
            raise ReadingApiV2ValidationError("pdf_artifact is invalid")
        artifact = deepcopy(dict(pdf_artifact))
        if tuple(artifact) != ("type", "media_type", "size", "sha256") or not (
            artifact["type"] == "pdf"
            and artifact["media_type"] == "application/pdf"
            and type(artifact["size"]) is int and artifact["size"] > 0
            and _sha(artifact["sha256"])
        ):
            raise ReadingApiV2ValidationError("pdf_artifact is invalid")
    metadata = snapshot["metadata"]
    quality_report = snapshot["quality_report"]
    engine_metadata = snapshot["engine_result"].get("engine_metadata")
    rule_version = engine_metadata.get("rule_version") if isinstance(engine_metadata, dict) else None
    if type(rule_version) is not str or not rule_version:
        raise ReadingApiV2ValidationError("rule_version is invalid")
    return {
        "schema_version": READING_API_V2_SCHEMA_VERSION,
        "api_version": READING_API_V2_VERSION,
        "engine_version": metadata["engine_version"],
        "schema_versions": {
            "reading_context": metadata["reading_context_schema"],
            "ai_reading": metadata["ai_reading_version"],
            "quality_report": quality_report["schema_version"],
            "reading_product": snapshot["schema_version"],
            "pdf": READING_PDF_V2_VERSION,
        },
        "rule_versions": {"rule_version": rule_version},
        "quality": {
            "version": quality_report["version"],
            "status": quality_report["status"],
            "decision": quality_report["decision"],
        },
        "publication": {"eligible": True, "reason": "quality_gate_pass"},
        "reading_product": snapshot,
        "pdf_artifact": artifact,
        "warnings": deepcopy(snapshot["ai_reading"]["warnings"]),
        "uncertainty": deepcopy(snapshot["ai_reading"]["uncertainty"]),
    }


def build_reading_api_v2_error_envelope(
    *,
    code: str,
    message: str,
    stage: str | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    if code not in _CODES:
        raise ReadingApiV2ValidationError("error code is invalid")
    if type(message) is not str or not message.strip():
        raise ReadingApiV2ValidationError("public error message is invalid")
    lowered = message.casefold()
    if any(token in lowered for token in (
        "api key", "openai_api_key", "traceback", "exception", "system prompt",
        "user prompt", "provider raw", "sk-",
    )):
        raise ReadingApiV2ValidationError("public error message contains private data")
    if stage is not None and stage not in _STAGES:
        raise ReadingApiV2ValidationError("error stage is invalid")
    if request_id is not None and (type(request_id) is not str or not request_id.strip()):
        raise ReadingApiV2ValidationError("request_id is invalid")
    return {
        "schema_version": READING_API_V2_ERROR_SCHEMA_VERSION,
        "api_version": READING_API_V2_VERSION,
        "error": {
            "code": code,
            "message": message,
            "stage": stage,
            "request_id": request_id,
        },
    }


__all__ = [
    "READING_API_V2_SCHEMA_VERSION", "READING_API_V2_ERROR_SCHEMA_VERSION",
    "READING_API_V2_VERSION", "ReadingApiV2ValidationError",
    "build_reading_api_v2_envelope", "build_reading_api_v2_error_envelope",
]
