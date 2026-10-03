"""Transport-neutral API v2 contract tests."""

from copy import deepcopy
from hashlib import sha256

import pytest

from api.reading_contract_v2 import (
    READING_API_V2_ERROR_SCHEMA_VERSION,
    READING_API_V2_SCHEMA_VERSION,
    READING_API_V2_VERSION,
    ReadingApiV2ValidationError,
    build_reading_api_v2_envelope,
    build_reading_api_v2_error_envelope,
)
from tests.test_reading_pdf_v2 import _product


def test_success_envelope_exact_shape_and_sources():
    product = _product("gc10")
    before = product.to_dict()
    envelope = build_reading_api_v2_envelope(product)
    assert tuple(envelope) == (
        "schema_version", "api_version", "engine_version", "schema_versions",
        "rule_versions", "quality", "publication", "reading_product",
        "pdf_artifact", "warnings", "uncertainty",
    )
    assert envelope["schema_version"] == READING_API_V2_SCHEMA_VERSION
    assert envelope["api_version"] == READING_API_V2_VERSION
    assert tuple(envelope["schema_versions"]) == (
        "reading_context", "ai_reading", "quality_report", "reading_product", "pdf",
    )
    assert envelope["publication"] == {"eligible": True, "reason": "quality_gate_pass"}
    assert envelope["warnings"] == before["ai_reading"]["warnings"]
    assert envelope["uncertainty"] == before["ai_reading"]["uncertainty"]
    envelope["reading_product"]["status"] = "tampered"
    assert product.to_dict() == before


def test_optional_pdf_artifact_is_validated_and_copied():
    data = b"%PDF-api-v2"
    artifact = {
        "type": "pdf", "media_type": "application/pdf", "size": len(data),
        "sha256": sha256(data).hexdigest(),
    }
    before = deepcopy(artifact)
    envelope = build_reading_api_v2_envelope(_product(), pdf_artifact=artifact)
    artifact["size"] = 0
    assert envelope["pdf_artifact"] == before


@pytest.mark.parametrize("artifact", [{}, {"type": "pdf"}, {"type": "pdf", "media_type": "application/pdf", "size": True, "sha256": "0" * 64}])
def test_invalid_pdf_artifact_is_rejected(artifact):
    with pytest.raises(ReadingApiV2ValidationError):
        build_reading_api_v2_envelope(_product(), pdf_artifact=artifact)


def test_error_envelope_exact_contract():
    envelope = build_reading_api_v2_error_envelope(
        code="generation_error", message="処理を完了できませんでした。",
        stage="quality_gate", request_id=None,
    )
    assert tuple(envelope) == ("schema_version", "api_version", "error")
    assert envelope["schema_version"] == READING_API_V2_ERROR_SCHEMA_VERSION
    assert tuple(envelope["error"]) == ("code", "message", "stage", "request_id")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"code": "secret", "message": "safe"},
        {"code": "input_error", "message": " "},
        {"code": "input_error", "message": "API key sk-secret"},
        {"code": "input_error", "message": "safe", "stage": "unknown"},
        {"code": "input_error", "message": "safe", "request_id": " "},
    ],
)
def test_error_envelope_rejects_unknown_or_private_values(kwargs):
    with pytest.raises(ReadingApiV2ValidationError):
        build_reading_api_v2_error_envelope(**kwargs)


def test_no_http_v2_route_was_added():
    from pathlib import Path
    text = Path("api/reading_routes.py").read_text(encoding="utf-8")
    assert "reading_api_envelope_v2" not in text
