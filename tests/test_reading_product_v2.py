"""Frozen section 25 ReadingProduct v2 contract tests."""

from copy import deepcopy
from datetime import datetime
from hashlib import sha256
import json
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

import tests.test_ai_reading_v2_e2e as e2e
from engine.reading_product_v2 import (
    READING_PRODUCT_V2_METHOD,
    READING_PRODUCT_V2_SCHEMA_VERSION,
    READING_PRODUCT_V2_STATUS,
    READING_PRODUCT_V2_VERSION,
    ReadingProductV2,
    ReadingProductV2ValidationError,
    build_reading_product_v2,
)
from engine.reading_quality_v2 import evaluate_ai_reading_quality_v2
from engine.reading_repair_v2 import repair_ai_reading_v2


GENERATED_AT = datetime(2026, 1, 1, 0, 0, tzinfo=ZoneInfo("Asia/Tokyo"))
TOP_FIELDS = (
    "schema_version", "version", "method", "status", "engine_result",
    "reading_context", "ai_reading", "quality_report", "repair_history", "metadata",
)


class Assessor:
    method = "product_v2_test_assessor"
    version = "v1"

    def __init__(self, findings=()):
        self.findings = list(findings)
        self.calls = 0

    def assess(self, ai_reading, reading_context, judgment_metadata):
        self.calls += 1
        return {"status": "completed", "findings": deepcopy(self.findings)}


class SequenceAssessor(Assessor):
    def __init__(self, outputs):
        self.outputs = deepcopy(outputs)
        self.calls = 0

    def assess(self, ai_reading, reading_context, judgment_metadata):
        result = self.outputs[min(self.calls, len(self.outputs) - 1)]
        self.calls += 1
        return deepcopy(result)


class FakeResponses:
    def __init__(self, payload):
        self.payload = deepcopy(payload)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(deepcopy(kwargs))
        return SimpleNamespace(
            output_text=json.dumps(self.payload, ensure_ascii=False, separators=(",", ":"))
        )


@pytest.fixture(scope="module")
def source():
    chart = e2e.gc03_chart.__wrapped__()
    artifacts = e2e._generate_pipeline(chart)
    assessor = Assessor()
    report = evaluate_ai_reading_quality_v2(
        artifacts.reading, artifacts.reading_context, artifacts.judgment_metadata,
        semantic_assessor=assessor,
    )
    return artifacts, report


def _build(source, **overrides):
    artifacts, report = source
    values = {
        "engine_result": artifacts.chart,
        "reading_context": artifacts.reading_context,
        "ai_reading": artifacts.reading,
        "quality_report": report,
        "generated_at": GENERATED_AT,
    }
    values.update(overrides)
    return build_reading_product_v2(**values)


def test_builds_exact_pass_only_four_source_product(source):
    product = _build(source)
    value = product.to_dict()
    assert isinstance(product, ReadingProductV2)
    assert tuple(value) == TOP_FIELDS
    assert value["schema_version"] == READING_PRODUCT_V2_SCHEMA_VERSION
    assert value["version"] == READING_PRODUCT_V2_VERSION
    assert value["method"] == READING_PRODUCT_V2_METHOD
    assert value["status"] == READING_PRODUCT_V2_STATUS
    assert value["repair_history"] == {"state": "not_repaired", "result": None}
    assert tuple(value["metadata"]["snapshot_hashes"]) == (
        "engine_result", "reading_context", "ai_reading", "quality_report", "repair_history",
    )
    assert "judgment_metadata" not in value
    assert "prompt" not in value and "provider_response" not in value


@pytest.mark.parametrize("kind", ["review", "fail"])
def test_review_and_fail_are_rejected(source, kind):
    artifacts, _ = source
    findings = [] if kind == "review" else [{
        "code": "prohibited_claim", "path": "/summary",
        "evidence": [{"source_contract": "ai_reading_v2", "path": "/summary"}],
    }]
    assessor = Assessor(findings)
    if kind == "review":
        assessor.assess = lambda *args: {"status": "inconclusive", "findings": []}
    report = evaluate_ai_reading_quality_v2(
        artifacts.reading, artifacts.reading_context, artifacts.judgment_metadata,
        semantic_assessor=assessor,
    )
    with pytest.raises(ReadingProductV2ValidationError):
        _build(source, quality_report=report)


@pytest.mark.parametrize(
    "generated_at",
    [datetime(2026, 1, 1), datetime(2026, 1, 1, tzinfo=ZoneInfo("Asia/Tokyo"), microsecond=1)],
)
def test_timestamp_must_be_caller_supplied_aware_seconds(source, generated_at):
    with pytest.raises(ReadingProductV2ValidationError):
        _build(source, generated_at=generated_at)


def test_timestamp_and_hashes_are_deterministic(source):
    assert _build(source).to_dict() == _build(source).to_dict()
    assert _build(source).metadata["generated_at"] == "2026-01-01T00:00:00+09:00"


def test_inputs_and_accessors_are_isolated(source):
    artifacts, report = source
    before = deepcopy((artifacts.chart, artifacts.reading_context, artifacts.reading, report.to_dict()))
    product = _build(source)
    exposed = product.to_dict()
    exposed["ai_reading"]["summary"]["text"] = "tampered"
    assert product.to_dict()["ai_reading"]["summary"]["text"] != "tampered"
    assert (artifacts.chart, artifacts.reading_context, artifacts.reading, report.to_dict()) == before


def test_mismatched_source_identity_is_rejected(source):
    artifacts, _ = source
    reading = deepcopy(artifacts.reading)
    reading["engine_version"] = "wrong"
    with pytest.raises(ReadingProductV2ValidationError):
        _build(source, ai_reading=reading)


def test_product_snapshot_detects_hash_tampering(source):
    value = _build(source).to_dict()
    value["ai_reading"]["summary"]["text"] = "tampered"
    with pytest.raises(ReadingProductV2ValidationError):
        ReadingProductV2(value)


def test_product_snapshot_rejects_owner_invalid_self_hashed_source(source):
    value = _build(source).to_dict()
    value["ai_reading"]["engine_version"] = "wrong"

    def canonical(item):
        return sha256(json.dumps(
            item, ensure_ascii=False, separators=(",", ":"), sort_keys=True,
            allow_nan=False,
        ).encode("utf-8")).hexdigest()

    value["metadata"]["snapshot_hashes"]["ai_reading"] = canonical(value["ai_reading"])
    bundle = {field: value[field] for field in (
        "engine_result", "reading_context", "ai_reading", "quality_report", "repair_history",
    )}
    value["metadata"]["source_bundle_sha256"] = canonical(bundle)
    with pytest.raises(ReadingProductV2ValidationError):
        ReadingProductV2(value)


def test_auto_repair_provenance_is_bound(source):
    artifacts, _ = source
    finding = {
        "code": "claim_type_mismatch", "path": "/sections/0/summary",
        "evidence": [{"source_contract": "ai_reading_v2", "path": "/sections/0/summary"}],
    }
    assessor = SequenceAssessor([
        {"status": "completed", "findings": [finding]},
        {"status": "completed", "findings": []},
    ])
    initial = evaluate_ai_reading_quality_v2(
        artifacts.reading, artifacts.reading_context, artifacts.judgment_metadata,
        semantic_assessor=assessor,
    )
    client = SimpleNamespace(responses=FakeResponses({
        "patches": [{"op": "replace", "path": "/sections/0/summary/text", "value": "repaired text"}]
    }))
    repair = repair_ai_reading_v2(
        artifacts.reading, initial, artifacts.reading_context, artifacts.judgment_metadata,
        semantic_assessor=assessor, client=client, model="test-model",
    )
    product = _build(
        source, ai_reading=repair.final_ai_reading,
        quality_report=repair.final_quality_report, repair_result=repair,
    ).to_dict()
    assert product["repair_history"]["state"] == "auto_repair_v2"
    assert product["repair_history"]["result"] == repair.to_dict()
    assert product["metadata"]["rewrites_ai_reading"] == "auto_repair_v2"
    assert len(client.responses.calls) == 1


def test_tampered_or_exhausted_repair_provenance_is_rejected(source):
    with pytest.raises(ReadingProductV2ValidationError):
        _build(source, repair_result=object())
