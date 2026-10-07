"""Engine-level public-function E2E tests for AI Reading v2."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
import json
import re
from types import SimpleNamespace
from typing import Any, Callable
from zoneinfo import ZoneInfo

import pytest

from engine.chart import calculate_chart
from engine.consultation_context import (
    build_consultation_context,
    validate_consultation_context,
)
from engine.judgment_metadata import (
    build_common_judgment_metadata,
    validate_common_judgment_metadata,
)
from engine.reading_context_v2 import (
    build_reading_context_v2,
    validate_reading_context_v2,
)
from engine.reading_generator_v2 import (
    AIReadingGeneratorV2StructuralValidationError,
    generate_ai_reading_v2,
)
from engine.reading_prompt_v2 import (
    AI_READING_V2_SECTION_SLOTS,
    build_ai_reading_request_v2,
)
from engine.reading_quality_v2 import evaluate_ai_reading_quality_v2


TARGET_DATETIME = datetime(
    2026,
    8,
    10,
    15,
    36,
    tzinfo=ZoneInfo("Asia/Tokyo"),
)
VALID_REPORT = {
    "valid": True,
    "errors": [],
    "missing_required_fields": [],
    "unknown_fields": [],
}
REPORT_FIELDS = (
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


def _birth_request(
    *,
    birth_date: str,
    birth_time: str | None,
    birth_place: str,
    gender: str,
) -> SimpleNamespace:
    return SimpleNamespace(
        birth_date=birth_date,
        birth_time=birth_time,
        birth_place=birth_place,
        gender=gender,
    )


@pytest.fixture(scope="module")
def gc03_chart() -> dict[str, Any]:
    return calculate_chart(
        _birth_request(
            birth_date="1984-07-22",
            birth_time="13:40",
            birth_place="福岡県",
            gender="male",
        ),
        target_datetime=TARGET_DATETIME,
    )


@pytest.fixture(scope="module")
def gc10_chart() -> dict[str, Any]:
    return calculate_chart(
        _birth_request(
            birth_date="1985-07-17",
            birth_time=None,
            birth_place="石川県",
            gender="female",
        ),
        target_datetime=TARGET_DATETIME,
    )


def _block(
    *,
    text: str = "実用的な指針です。",
    claim_type: str = "practical",
    fact_codes: list[str] | None = None,
    components: list[str] | None = None,
    warnings: list[str] | None = None,
    uncertainty: list[str] | None = None,
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
    sections = [
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
        for _ in range(8)
    ]
    yearly = [
        {
            "title": _block(), "theme": _block(), "career": _block(),
            "wealth": _block(), "relationships": _block(), "caution": _block(),
            "advice": [_block(), _block()],
            "summary": _block(), "detail": _block(),
        }
        for _ in request["trusted_attachments"]["future_flow_years"]
    ]
    consultation_answer = (
        _block()
        if request["trusted_attachments"]["consultation_present"]
        else None
    )
    long_term = []
    for _ in request["trusted_attachments"].get("long_term_luck_pillars", []):
        def luck_block(text: str = "螟ｧ驕九・譁ｰ逕溘・縺ｮ謗｡縺ｧ縺吶・"):
            return _block(text=text, claim_type="luck_astrology", components=["luck_pillars"])
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
        "consultation_answer": consultation_answer,
    }


def _transport_payload(payload: Any) -> Any:
    result = deepcopy(payload)

    def compact_empty_block_metadata(value: Any) -> Any:
        if isinstance(value, dict):
            compacted = {
                key: compact_empty_block_metadata(item)
                for key, item in value.items()
            }
            if "text" in compacted:
                compacted = {
                    "t": compacted.pop("text"),
                    "k": compacted.pop("claim_type"),
                    "f": compacted.pop("source_fact_codes"),
                    "c": compacted.pop("source_components"),
                    **compacted,
                }
                if compacted.get("warnings") == []:
                    compacted.pop("warnings", None)
                    compacted.pop("uncertainty", None)
            return compacted
        if isinstance(value, list):
            return [compact_empty_block_metadata(item) for item in value]
        return value

    result = compact_empty_block_metadata(result)
    if isinstance(result, dict) and isinstance(result.get("sections"), list):
        section_ids = tuple(
            section_id for section_id, _title in AI_READING_V2_SECTION_SLOTS
        )
        sections = result["sections"]
        if len(sections) == len(section_ids):
            result["sections"] = {
                section_id: section
                for section_id, section in zip(section_ids, sections)
            }
    return result


class FakeResponses:
    def __init__(self, payload: Any):
        self.payload = deepcopy(payload)
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs):
        self.calls.append(deepcopy(kwargs))
        provider_value = _transport_payload(self.payload)
        output_text = (
            provider_value
            if isinstance(provider_value, str)
            else json.dumps(
                provider_value,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=False,
                allow_nan=False,
            )
        )
        return SimpleNamespace(
            id="resp_e2e_v2",
            status="completed",
            output_text=output_text,
            usage={
                "input_tokens": 10,
                "output_tokens": 20,
                "total_tokens": 30,
            },
        )


class FakeClient:
    def __init__(self, payload: Any):
        self.responses = FakeResponses(payload)


class RecordingSemanticAssessor:
    def __init__(self, result: dict[str, Any] | None = None):
        self.result = deepcopy(
            {"status": "completed", "findings": []}
            if result is None
            else result
        )
        self.method_reads = 0
        self.version_reads = 0
        self.calls = 0
        self.received: tuple[Any, Any, Any] | None = None

    @property
    def method(self) -> str:
        self.method_reads += 1
        return "phase6_e2e_assessor"

    @property
    def version(self) -> str:
        self.version_reads += 1
        return "1.0"

    def assess(self, ai_reading, reading_context, judgment_metadata):
        self.calls += 1
        self.received = (ai_reading, reading_context, judgment_metadata)
        return deepcopy(self.result)


@dataclass
class PipelineArtifacts:
    chart: dict[str, Any]
    reading_context: dict[str, Any]
    judgment_metadata: dict[str, Any]
    request: dict[str, Any]
    payload: dict[str, Any]
    reading: dict[str, Any]
    client: FakeClient


def _generate_pipeline(
    chart: dict[str, Any],
    *,
    consultation_context: dict[str, Any] | None = None,
    mutate_payload: Callable[[dict[str, Any], dict[str, Any]], None] | None = None,
) -> PipelineArtifacts:
    chart_before = deepcopy(chart)
    reading_context = build_reading_context_v2(
        chart,
        consultation_context=consultation_context,
    )
    judgment_metadata = build_common_judgment_metadata(chart)
    assert chart == chart_before
    assert validate_reading_context_v2(reading_context) == VALID_REPORT
    assert validate_common_judgment_metadata(judgment_metadata) == VALID_REPORT

    context_before = deepcopy(reading_context)
    metadata_before = deepcopy(judgment_metadata)
    request = build_ai_reading_request_v2(reading_context, judgment_metadata)
    assert reading_context == context_before
    assert judgment_metadata == metadata_before

    payload = _model_payload(request)
    if mutate_payload is not None:
        mutate_payload(payload, request)
    request_before = deepcopy(request)
    payload_before = deepcopy(payload)
    client = FakeClient(payload)
    result = generate_ai_reading_v2(
        request,
        client=client,
        model="test-model",
    )
    assert request == request_before
    assert payload == payload_before
    assert len(client.responses.calls) == 1
    return PipelineArtifacts(
        chart=chart,
        reading_context=reading_context,
        judgment_metadata=judgment_metadata,
        request=request,
        payload=payload,
        reading=result.reading,
        client=client,
    )


@pytest.fixture(scope="module")
def gc03_clean(gc03_chart) -> PipelineArtifacts:
    return _generate_pipeline(gc03_chart)


@pytest.fixture(scope="module")
def gc10_clean(gc10_chart) -> PipelineArtifacts:
    return _generate_pipeline(gc10_chart)


def _evaluate(
    artifacts: PipelineArtifacts,
    assessor: RecordingSemanticAssessor,
    *,
    reading: dict[str, Any] | None = None,
):
    target_reading = artifacts.reading if reading is None else reading
    inputs_before = deepcopy(
        (
            target_reading,
            artifacts.reading_context,
            artifacts.judgment_metadata,
        )
    )
    report = evaluate_ai_reading_quality_v2(
        target_reading,
        artifacts.reading_context,
        artifacts.judgment_metadata,
        semantic_assessor=assessor,
    ).to_dict()
    assert (
        target_reading,
        artifacts.reading_context,
        artifacts.judgment_metadata,
    ) == inputs_before
    return report


def _resolve_context_path(root: dict[str, Any], path: str) -> Any:
    current: Any = root
    for key, index in re.findall(r"(?:^|\.)([^.\[]+)|\[(\d+)\]", path):
        current = current[int(index)] if index else current[key]
    return current


def _first_plain_number(value: Any) -> int | float:
    if type(value) in (int, float):
        return value
    if type(value) is dict:
        for nested in value.values():
            try:
                return _first_plain_number(nested)
            except LookupError:
                pass
    if type(value) is list:
        for nested in value:
            try:
                return _first_plain_number(nested)
            except LookupError:
                pass
    raise LookupError("trusted source contains no plain JSON number")


def _numeric_text(value: int | float) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def _semantic_error_result() -> dict[str, Any]:
    path = "/sections/0/summary"
    return {
        "status": "completed",
        "findings": [
            {
                "code": "engine_value_contradiction",
                "path": path,
                "evidence": [{"source_contract": "ai_reading_v2", "path": path}],
            }
        ],
    }


def test_normal_four_pillar_public_chain_returns_clean_pass(gc03_clean):
    assert gc03_clean.reading_context["chart"]["pillar_sequence"] == [
        "甲子",
        "辛未",
        "丁巳",
        "丁未",
    ]
    assert gc03_clean.reading_context["status"] == "ready_for_ai_reading"
    assert gc03_clean.request["schema_version"] == "ai_reading_request_v2"
    assert gc03_clean.reading["validation"] == VALID_REPORT
    assert len(gc03_clean.client.responses.calls) == 1

    assessor = RecordingSemanticAssessor()
    report = _evaluate(gc03_clean, assessor)
    assert report["decision"] == "pass"
    assert report["blocking"] is False
    assert report["human_review_required"] is False
    assert report["semantic_assessment"]["status"] == "completed"
    assert (report["error_count"], report["warning_count"], report["info_count"]) == (
        0,
        0,
        0,
    )
    assert report["input_contracts"]["reading_context_v2"]["schema_version"] == (
        "reading_context_v2"
    )
    assert report["input_contracts"]["common_judgment_metadata_v1"] == {
        "schema_version": "common_judgment_metadata_v1"
    }
    assert (assessor.method_reads, assessor.version_reads, assessor.calls) == (1, 1, 1)


def test_unknown_hour_public_chain_preserves_three_pillar_scope(gc10_clean):
    context = gc10_clean.reading_context
    assert context["chart"]["pillars"]["hour"] is None
    assert context["chart"]["pillar_sequence"] == ["乙丑", "癸未", "丁巳", None]
    assert context["birth_time_status"]["known"] is False
    assert context["birth_time_status"]["calculation_scope"] == "three_pillars"
    assert "時柱" not in json.dumps(gc10_clean.payload, ensure_ascii=False)

    report = _evaluate(gc10_clean, RecordingSemanticAssessor())
    assert report["decision"] == "pass"
    assert report["semantic_assessment"]["status"] == "completed"


def test_unknown_hour_warning_and_uncertainty_survive_full_chain(gc10_clean):
    assert gc10_clean.chart["warnings"]
    assert gc10_clean.chart["uncertainty"]
    assert gc10_clean.reading_context["warnings"] == gc10_clean.chart["warnings"]
    assert gc10_clean.reading_context["uncertainty"] == gc10_clean.chart["uncertainty"]
    assert gc10_clean.request["trusted_catalogs"]["warnings"]
    assert gc10_clean.request["trusted_catalogs"]["uncertainty"]
    assert gc10_clean.reading["warnings"] == gc10_clean.request["trusted_catalogs"][
        "warnings"
    ]
    assert gc10_clean.reading["uncertainty"] == gc10_clean.request[
        "trusted_catalogs"
    ]["uncertainty"]

    report = _evaluate(gc10_clean, RecordingSemanticAssessor())
    assert report["decision"] == "pass"
    assert all(
        finding["code"] != "warning_uncertainty_not_preserved"
        for finding in report["findings"]
    )


def test_current_luck_uses_only_prompt_trusted_component_and_value(gc03_chart):
    selected: dict[str, Any] = {}

    def add_current_luck(payload, request):
        source = next(
            item
            for item in request["trusted_catalogs"]["luck_value_sources"]
            if item["section_id"] == "current_luck"
            and item["source_component"] == "current_luck"
        )
        source_value = _resolve_context_path(
            request["model_input"]["reading_context"],
            source["context_path"],
        )
        number = _first_plain_number(source_value)
        selected.update(source=deepcopy(source), number=number)
        payload["sections"][5]["summary"] = _block(
            text=f"信頼された値は{_numeric_text(number)}です。",
            claim_type="luck_astrology",
            components=[source["source_component"]],
        )

    artifacts = _generate_pipeline(gc03_chart, mutate_payload=add_current_luck)
    block = artifacts.reading["sections"][5]["summary"]
    assert selected["source"] in artifacts.request["trusted_catalogs"][
        "luck_value_sources"
    ]
    assert block["source_components"] == [selected["source"]["source_component"]]
    assert _numeric_text(selected["number"]) in block["text"]

    report = _evaluate(artifacts, RecordingSemanticAssessor())
    assert report["decision"] == "pass"
    assert not {
        "unsupported_numeric_claim",
        "reference_resolution_error",
        "luck_semantic_mismatch",
    }.intersection(finding["code"] for finding in report["findings"])


def test_future_yearly_uses_prompt_attached_year_and_exact_source(gc03_chart):
    selected: dict[str, Any] = {}

    def add_future_year(payload, request):
        year = request["trusted_attachments"]["future_flow_years"][0]
        source = next(
            item
            for item in request["trusted_catalogs"]["luck_value_sources"]
            if item["section_id"] == "future_flow"
            and item["year"] == year
            and item["source_component"] == "integrated_luck"
        )
        selected.update(year=year, source=deepcopy(source))
        payload["future_flow_yearly"][0]["summary"] = _block(
            text=f"{year}年の流れです。",
            claim_type="luck_astrology",
            components=[source["source_component"]],
        )

    artifacts = _generate_pipeline(gc03_chart, mutate_payload=add_future_year)
    yearly = artifacts.reading["sections"][6]["yearly"]
    assert yearly[0]["year"] == selected["year"]
    assert yearly[0]["summary"]["source_components"] == [
        selected["source"]["source_component"]
    ]
    assert selected["source"]["context_path"].startswith("luck.five_year_luck[0]")

    report = _evaluate(artifacts, RecordingSemanticAssessor())
    assert report["decision"] == "pass"
    assert not {
        "future_year_integrity_error",
        "unsupported_numeric_claim",
    }.intersection(finding["code"] for finding in report["findings"])


def test_consultation_public_chain_keeps_practical_answer_isolated(gc03_chart):
    consultation = build_consultation_context(
        concern="仕事について相談したい",
        desired_future="落ち着いて働きたい",
    )
    assert validate_consultation_context(consultation)["valid"] is True
    artifacts = _generate_pipeline(
        gc03_chart,
        consultation_context=consultation,
    )
    assert artifacts.reading_context["consultation"] == consultation
    assert artifacts.request["trusted_attachments"]["consultation_present"] is True
    answer = artifacts.reading["consultation_answer"]
    assert answer is not None
    assert answer["claim_type"] == "practical"
    assert answer["source_fact_codes"] == []
    assert answer["source_components"] == []

    report = _evaluate(artifacts, RecordingSemanticAssessor())
    assert report["decision"] == "pass"
    assert all(
        finding["code"] != "consultation_astrology_leak"
        for finding in report["findings"]
    )


def test_generator_invalid_output_stops_chain_before_quality_gate(gc03_chart):
    reading_context = build_reading_context_v2(gc03_chart)
    metadata = build_common_judgment_metadata(gc03_chart)
    request = build_ai_reading_request_v2(reading_context, metadata)
    payload = _model_payload(request)
    payload.pop("summary")
    client = FakeClient(payload)
    quality_gate_calls = 0

    def forbidden_quality_gate(*args, **kwargs):
        nonlocal quality_gate_calls
        quality_gate_calls += 1
        raise AssertionError("quality gate must not run after generator rejection")

    def run_chain():
        generated = generate_ai_reading_v2(
            request,
            client=client,
            model="test-model",
        )
        return forbidden_quality_gate(
            generated.reading,
            reading_context,
            metadata,
        )

    with pytest.raises(AIReadingGeneratorV2StructuralValidationError):
        run_chain()
    assert len(client.responses.calls) == 1
    assert quality_gate_calls == 0


def test_tampered_generated_copy_fails_without_touching_assessor(gc03_clean):
    original_before = deepcopy(gc03_clean.reading)
    tampered = deepcopy(gc03_clean.reading)
    tampered["sections"][0]["title"] = "改変された見出し"
    assessor = RecordingSemanticAssessor()

    report = _evaluate(gc03_clean, assessor, reading=tampered)
    assert report["decision"] == "fail"
    assert report["semantic_assessment"] == {
        "status": "not_run",
        "method": None,
        "version": None,
    }
    assert "trusted_field_mismatch" in [
        finding["code"] for finding in report["findings"]
    ]
    assert (assessor.method_reads, assessor.version_reads, assessor.calls) == (0, 0, 0)
    assert gc03_clean.reading == original_before


def test_inconclusive_semantic_assessment_returns_review(gc03_clean):
    assessor = RecordingSemanticAssessor(
        {"status": "inconclusive", "findings": []}
    )
    report = _evaluate(gc03_clean, assessor)
    assert report["semantic_assessment"]["status"] == "inconclusive"
    assert report["decision"] == "review"
    assert report["blocking"] is True
    assert report["human_review_required"] is True
    assert [finding["code"] for finding in report["findings"]] == [
        "semantic_assessment_inconclusive"
    ]
    assert assessor.calls == 1


def test_completed_semantic_error_returns_fail(gc03_clean):
    assessor = RecordingSemanticAssessor(_semantic_error_result())
    report = _evaluate(gc03_clean, assessor)
    assert report["semantic_assessment"]["status"] == "completed"
    assert report["decision"] == "fail"
    assert report["error_count"] >= 1
    assert report["blocking"] is True
    assert "engine_value_contradiction" in [
        finding["code"] for finding in report["findings"]
    ]
    assert assessor.calls == 1


@pytest.mark.parametrize(
    ("mode", "expected_decision"),
    (("pass", "pass"), ("review", "review"), ("fail", "fail")),
)
def test_quality_gate_preserves_all_pipeline_inputs(
    gc03_clean,
    mode,
    expected_decision,
):
    reading = deepcopy(gc03_clean.reading)
    if mode == "review":
        result = {"status": "inconclusive", "findings": []}
    elif mode == "fail":
        result = _semantic_error_result()
    else:
        result = {"status": "completed", "findings": []}
    assessor = RecordingSemanticAssessor(result)
    before = deepcopy(
        (
            gc03_clean.chart,
            gc03_clean.reading_context,
            gc03_clean.judgment_metadata,
            gc03_clean.request,
            reading,
        )
    )

    report = _evaluate(gc03_clean, assessor, reading=reading)
    assert report["decision"] == expected_decision
    assert (
        gc03_clean.chart,
        gc03_clean.reading_context,
        gc03_clean.judgment_metadata,
        gc03_clean.request,
        reading,
    ) == before
    assert tuple(report) == REPORT_FIELDS


@pytest.mark.parametrize("variant", range(10))
def test_repeated_legal_provenance_variations_remain_publishable(variant):
    def mutate(payload, _request):
        payload["summary"]["text"] = f"合法な表現バリエーション {variant}"
        payload["sections"][1]["detail"]["text"] = f"仕事に関する説明 {variant}"

    artifacts = _generate_pipeline(
        gc03_chart.__wrapped__(), mutate_payload=mutate
    )
    report = _evaluate(artifacts, RecordingSemanticAssessor())
    assert report["decision"] == "pass"
