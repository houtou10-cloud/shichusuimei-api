"""Integrated public-function v1.2 completion pipeline tests."""

from copy import deepcopy
from datetime import datetime
import json
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

import tests.test_ai_reading_v2_e2e as base
import engine.reading_pdf_v2 as pdf_v2
from api.reading_contract_v2 import build_reading_api_v2_envelope
from engine.consultation_context import build_consultation_context
from engine.reading_pdf_v2 import render_reading_product_v2_pdf_bytes
from engine.reading_product_v2 import ReadingProductV2ValidationError, build_reading_product_v2
from engine.reading_quality_v2 import evaluate_ai_reading_quality_v2
from engine.reading_renderer_v2 import render_reading_product_v2_html
from engine.reading_repair_v2 import AIReadingRepairV2ConfigurationError, repair_ai_reading_v2
from tests.test_reading_pdf_v2 import Manager, Page


FIXED = datetime(2026, 1, 1, tzinfo=ZoneInfo("Asia/Tokyo"))


class SequenceAssessor:
    method = "completion_e2e_assessor"
    version = "v1"

    def __init__(self, results):
        self.results = deepcopy(results)
        self.calls = 0

    def assess(self, *args):
        result = self.results[min(self.calls, len(self.results) - 1)]
        self.calls += 1
        return deepcopy(result)


class Responses:
    def __init__(self, values):
        self.values = deepcopy(values)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(deepcopy(kwargs))
        value = self.values[len(self.calls) - 1]
        return SimpleNamespace(output_text=json.dumps(value, ensure_ascii=False, separators=(",", ":")))


def _finding(code="claim_type_mismatch", path="/sections/0/summary"):
    return {"code": code, "path": path, "evidence": [{"source_contract": "ai_reading_v2", "path": path}]}


def _pipeline(case="gc03", consultation=None):
    chart = (base.gc03_chart if case == "gc03" else base.gc10_chart).__wrapped__()
    return base._generate_pipeline(chart, consultation_context=consultation)


def _report(artifacts, assessor):
    return evaluate_ai_reading_quality_v2(
        artifacts.reading, artifacts.reading_context, artifacts.judgment_metadata,
        semantic_assessor=assessor,
    )


def _product(artifacts, report, **kwargs):
    return build_reading_product_v2(
        artifacts.chart, artifacts.reading_context, kwargs.pop("reading", artifacts.reading), report,
        generated_at=FIXED, **kwargs,
    )


def test_clean_public_pipeline_to_product_html_and_api():
    artifacts = _pipeline()
    before = deepcopy((
        artifacts.chart, artifacts.reading_context, artifacts.judgment_metadata,
        artifacts.request, artifacts.payload, artifacts.reading,
    ))
    report = _report(artifacts, SequenceAssessor([{"status": "completed", "findings": []}]))
    product = _product(artifacts, report)
    html = render_reading_product_v2_html(product)
    envelope = build_reading_api_v2_envelope(product)
    assert report.decision == "pass"
    assert product.status == "ready_for_publication"
    assert html.startswith("<!DOCTYPE html>")
    assert envelope["publication"]["eligible"] is True
    assert (
        artifacts.chart, artifacts.reading_context, artifacts.judgment_metadata,
        artifacts.request, artifacts.payload, artifacts.reading,
    ) == before


def test_auto_repair_to_pass_product_pdf_and_api(monkeypatch):
    artifacts = _pipeline()
    assessor = SequenceAssessor([
        {"status": "completed", "findings": [_finding()]},
        {"status": "completed", "findings": []},
    ])
    initial = _report(artifacts, assessor)
    responses = Responses([{"patches": [{
        "op": "replace", "path": "/sections/0/summary/text", "value": "repair completed",
    }]}])
    repair = repair_ai_reading_v2(
        artifacts.reading, initial, artifacts.reading_context, artifacts.judgment_metadata,
        semantic_assessor=assessor, client=SimpleNamespace(responses=responses), model="test-model",
    )
    product = _product(
        artifacts, repair.final_quality_report,
        reading=repair.final_ai_reading, repair_result=repair,
    )
    monkeypatch.setattr(pdf_v2, "_load_playwright", lambda: lambda: Manager(Page()))
    data = render_reading_product_v2_pdf_bytes(product)
    envelope = build_reading_api_v2_envelope(product, pdf_artifact={
        "type": "pdf", "media_type": "application/pdf", "size": len(data),
        "sha256": __import__("hashlib").sha256(data).hexdigest(),
    })
    assert repair.status == "pass" and len(responses.calls) == 1
    assert data.startswith(b"%PDF")
    assert envelope["reading_product"]["repair_history"]["state"] == "auto_repair_v2"


def test_exhausted_repair_cannot_publish():
    artifacts = _pipeline()
    finding = _finding()
    assessor = SequenceAssessor([{"status": "completed", "findings": [finding]}] * 3)
    initial = _report(artifacts, assessor)
    responses = Responses([
        {"patches": [{"op": "replace", "path": "/sections/0/summary/text", "value": "attempt one"}]},
        {"patches": [{"op": "replace", "path": "/sections/0/summary/text", "value": "attempt two"}]},
    ])
    repair = repair_ai_reading_v2(
        artifacts.reading, initial, artifacts.reading_context, artifacts.judgment_metadata,
        semantic_assessor=assessor, client=SimpleNamespace(responses=responses), model="test-model",
    )
    assert repair.status == "exhausted" and len(responses.calls) == 2
    with pytest.raises(ReadingProductV2ValidationError):
        _product(artifacts, repair.final_quality_report, reading=repair.final_ai_reading, repair_result=repair)


@pytest.mark.parametrize("kind", ["review", "non_auto_fail"])
def test_review_and_non_auto_fail_have_no_repair_or_product_path(kind):
    artifacts = _pipeline()
    result = ({"status": "inconclusive", "findings": []} if kind == "review" else
              {"status": "completed", "findings": [_finding("prohibited_claim")]})
    assessor = SequenceAssessor([result])
    report = _report(artifacts, assessor)
    client = SimpleNamespace(responses=Responses([]))
    with pytest.raises(AIReadingRepairV2ConfigurationError):
        repair_ai_reading_v2(
            artifacts.reading, report, artifacts.reading_context, artifacts.judgment_metadata,
            semantic_assessor=assessor, client=client, model="test-model",
        )
    assert client.responses.calls == []
    with pytest.raises(ReadingProductV2ValidationError):
        _product(artifacts, report)


def test_unknown_hour_final_warning_authority_survives_product_and_html():
    artifacts = _pipeline("gc10")
    report = _report(artifacts, SequenceAssessor([{"status": "completed", "findings": []}]))
    product = _product(artifacts, report)
    html = render_reading_product_v2_html(product)
    assert artifacts.reading_context["birth_time_status"]["known"] is False
    assert artifacts.reading_context["chart"]["pillars"]["hour"] is None
    assert product.to_dict()["ai_reading"]["warnings"] == artifacts.reading["warnings"]
    assert all(entry["value"] in html for entry in artifacts.reading["warnings"])
    assert all(entry["warning_id"] not in html for entry in artifacts.reading["warnings"])
    assert "出生時刻不明" in html


def test_future_and_consultation_reach_dedicated_final_sections():
    consultation = build_consultation_context(
        concern="仕事について相談したい", desired_future="落ち着いて働きたい",
    )
    artifacts = _pipeline(consultation=consultation)
    report = _report(artifacts, SequenceAssessor([{"status": "completed", "findings": []}]))
    html = render_reading_product_v2_html(_product(artifacts, report))
    assert "今後の流れ" in html
    assert "相談への回答" in html
    assert artifacts.reading["consultation_answer"]["text"] in html
