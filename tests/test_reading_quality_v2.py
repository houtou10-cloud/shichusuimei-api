"""Contract tests for the AI Reading Quality Gate v2 kernel."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import FrozenInstanceError, fields
from datetime import datetime
import inspect
import json
from types import SimpleNamespace

import pytest

import engine.reading_quality_v2 as quality_v2
from engine.chart import calculate_chart
from engine.judgment_metadata import (
    build_common_judgment_metadata,
    validate_common_judgment_metadata,
)
from engine.reading_context_v2 import (
    build_reading_context_v2,
    validate_reading_context_v2,
)
from engine.reading_generator_v2 import generate_ai_reading_v2
from engine.reading_prompt_v2 import (
    build_ai_reading_request_v2,
    validate_ai_reading_prompt_inputs_v2,
)
from engine.reading_quality_v2 import (
    AI_READING_QUALITY_REPORT_V2_METHOD,
    AI_READING_QUALITY_REPORT_V2_SCHEMA_VERSION,
    AI_READING_QUALITY_REPORT_V2_STATUS,
    AI_READING_QUALITY_REPORT_V2_VERSION,
    AIReadingQualityFindingV2,
    AIReadingQualityReportV2,
    SemanticAssessorV2,
    evaluate_ai_reading_quality_v2,
)


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
FINDING_FIELDS = (
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
EXPECTED_ISSUES = (
    ("input_contract_invalid", "ERROR", True, "none", False),
    ("input_contract_mismatch", "ERROR", True, "none", False),
    ("ai_reading_contract_invalid", "ERROR", True, "none", False),
    ("trusted_field_mismatch", "ERROR", True, "none", False),
    ("reference_resolution_error", "ERROR", True, "none", False),
    ("warning_uncertainty_not_preserved", "ERROR", True, "none", False),
    ("disclaimer_mismatch", "ERROR", True, "none", False),
    ("future_year_integrity_error", "ERROR", True, "none", False),
    ("claim_type_mismatch", "ERROR", True, "auto", False),
    ("fact_semantic_mismatch", "ERROR", True, "human", True),
    ("component_semantic_mismatch", "ERROR", True, "human", True),
    ("luck_semantic_mismatch", "ERROR", True, "human", True),
    ("engine_value_contradiction", "ERROR", True, "human", True),
    ("judgment_status_wording_violation", "ERROR", True, "auto", False),
    ("unknown_hour_derived_claim", "ERROR", True, "human", True),
    ("missing_applicable_uncertainty", "ERROR", True, "human", True),
    ("unsupported_numeric_claim", "ERROR", True, "auto", False),
    ("consultation_astrology_leak", "ERROR", True, "human", True),
    ("prohibited_claim", "ERROR", True, "human", True),
    ("overconfident_wording", "WARNING", False, "auto", False),
    (
        "evidence_interpretation_advice_confusion",
        "WARNING",
        False,
        "auto",
        False,
    ),
    ("astrology_wording_ambiguity", "WARNING", False, "auto", False),
    ("semantic_assessment_unavailable", "WARNING", True, "human", True),
    ("semantic_assessment_failed", "WARNING", True, "human", True),
    ("semantic_assessment_inconclusive", "WARNING", True, "human", True),
    ("source_limitation_note", "INFO", False, "none", False),
)
EXPECTED_SEMANTIC_CODES = (
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
EXPECTED_MESSAGES = (
    "入力contractがowner validationまたはprompt prerequisite validationを通過しません。",
    "AI Readingと検証入力のtrusted identityが一致しません。",
    "AI Reading v2の構造がfinal contractに一致しません。",
    "AI Reading v2のtrusted fieldが再構築値と一致しません。",
    "参照がtrusted sourceへ解決できません。",
    "warningまたはuncertaintyが保持されていません。",
    "disclaimerがtrusted constantと一致しません。",
    "future_flowのyearまたは順序がtrusted inputと一致しません。",
    "claim_typeが本文の意味と一致しません。",
    "source_fact_codesが本文の占術主張を意味的に支持しません。",
    "source_componentsが本文のcertaintyまたはprovenance表現と整合しません。",
    "luck_astrology本文がtrusted luck sourceと整合しません。",
    "本文がengine確定値またはlabelと矛盾します。",
    "本文の確度表現がcanonical judgment status policyに違反します。",
    "出生時刻不明入力からhour由来の主張を生成しています。",
    "適用可能なuncertaintyが本文または参照に保持されていません。",
    "本文の数値主張をtrusted sourceで確認できません。",
    "consultationから新しい占術判断を生成しています。",
    "医療・法律・投資の断定、将来保証、不安煽りまたはその他の禁止主張が含まれています。",
    "本文に過度に断定的な表現があります。",
    "evidence、interpretation、adviceの役割が混同されています。",
    "占術上の根拠または確度の表現が曖昧です。",
    "semantic assessorが未設定またはidentity不正のため意味検査を実行できません。",
    "semantic assessorの実行または出力検証に失敗しました。",
    "semantic assessorが一つ以上の意味検査を確定できませんでした。",
    "source limitationが適切に開示されています。",
)

EXPECTED_SECTION_SLOTS = (
    ("core_personality", "本質・性格"),
    ("career", "仕事・適職"),
    ("wealth", "金運"),
    ("relationships", "恋愛・人間関係"),
    ("health", "健康傾向"),
    ("current_luck", "現在の運勢"),
    ("future_flow", "今後の流れ"),
    ("advice", "総合アドバイス"),
)
EXPECTED_DISCLAIMER = (
    "本鑑定は八雲式四柱推命エンジンの計算結果に基づく参考情報です。"
    "将来の出来事を保証するものではなく、医療・法律・投資その他の"
    "専門的判断を代替するものではありません。重要な意思決定は、"
    "必要に応じて適切な専門家へご相談ください。"
)


def _input_contracts() -> dict:
    return {
        "ai_reading_v2": {
            "schema_version": "ai_reading_v2",
            "version": "ai_reading_v2",
            "method": "openai_responses_api_v2",
            "status": "completed",
            "engine_version": None,
        },
        "reading_context_v2": {
            "schema_version": "reading_context_v2",
            "version": "reading_context_v2",
            "method": "reading_context_v2",
            "status": "ready_for_ai_reading",
        },
        "common_judgment_metadata_v1": {
            "schema_version": "common_judgment_metadata_v1",
        },
    }


def _semantic(status: str = "completed") -> dict:
    if status in ("not_run", "unavailable"):
        return {"status": status, "method": None, "version": None}
    return {"status": status, "method": "assessor_method", "version": "1.0"}


def _evidence(
    source_contract: str = "ai_reading_v2",
    path: str = "/summary",
) -> list[dict[str, str]]:
    return [{"source_contract": source_contract, "path": path}]


def _candidate(
    code: str,
    path: str = "/summary",
    evidence: list[dict[str, str]] | None = None,
) -> dict:
    return {
        "code": code,
        "path": path,
        "evidence": _evidence(path=path) if evidence is None else evidence,
    }


def _report(
    status: str = "completed",
    candidates: list[dict] | None = None,
    *,
    semantic_candidates: list[dict] | None = None,
):
    return quality_v2._build_quality_report_v2(
        _input_contracts(),
        _semantic(status),
        [] if candidates is None else candidates,
        semantic_finding_candidates=(
            [] if semantic_candidates is None else semantic_candidates
        ),
    )


def _finding_with_id(finding_id: str) -> AIReadingQualityFindingV2:
    return AIReadingQualityFindingV2(
        finding_id=finding_id,
        code="source_limitation_note",
        severity="INFO",
        blocking=False,
        path="/summary",
        message="source limitationが適切に開示されています。",
        evidence=({"source_contract": "ai_reading_v2", "path": "/summary"},),
        repairability="none",
        requires_human_review=False,
    )


def _phase2_block() -> dict:
    return {
        "text": "実用的な案内です。",
        "claim_type": "practical",
        "source_fact_codes": [],
        "source_components": [],
        "warnings": [],
        "uncertainty": [],
    }


def _phase2_valid_reading(request: dict, reading_context: dict) -> dict:
    sections = []
    for section_id, title in EXPECTED_SECTION_SLOTS:
        section = {
            "section_id": section_id,
            "title": title,
            "facts": [],
            "summary": _phase2_block(),
            "detail": _phase2_block(),
            "evidence": [],
            "interpretation": [],
            "advice": [_phase2_block()],
            "warnings": [],
            "uncertainty": [],
        }
        if section_id == "future_flow":
            section["yearly"] = [
                {
                    "year": entry["year"],
                    "summary": _phase2_block(),
                    "detail": _phase2_block(),
                }
                for entry in reading_context["luck"]["five_year_luck"]
            ]
        sections.append(section)
    return {
        "schema_version": "ai_reading_v2",
        "engine_version": deepcopy(reading_context["engine_version"]),
        "summary": _phase2_block(),
        "sections": sections,
        "consultation_answer": None,
        "warnings": deepcopy(request["trusted_catalogs"]["warnings"]),
        "uncertainty": deepcopy(request["trusted_catalogs"]["uncertainty"]),
        "source_contracts": deepcopy(request["source_contracts"]),
        "disclaimer": EXPECTED_DISCLAIMER,
        "validation": {
            "valid": True,
            "errors": [],
            "missing_required_fields": [],
            "unknown_fields": [],
        },
        "method": "openai_responses_api_v2",
        "version": "ai_reading_v2",
        "status": "completed",
    }


def _phase2_model_payload(reading: dict) -> dict:
    section_fields = (
        "facts",
        "summary",
        "detail",
        "evidence",
        "interpretation",
        "advice",
        "warnings",
        "uncertainty",
    )
    return {
        "summary": deepcopy(reading["summary"]),
        "sections": [
            {field: deepcopy(section[field]) for field in section_fields}
            for section in reading["sections"]
        ],
        "future_flow_yearly": [
            {
                "summary": deepcopy(entry["summary"]),
                "detail": deepcopy(entry["detail"]),
            }
            for entry in reading["sections"][6]["yearly"]
        ],
        "consultation_answer": deepcopy(reading["consultation_answer"]),
    }


class _StaticResponses:
    def __init__(self, payload: dict):
        self.payload = deepcopy(payload)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(deepcopy(kwargs))
        return SimpleNamespace(
            id="resp_quality_v2",
            status="completed",
            output_text=json.dumps(
                self.payload,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=False,
                allow_nan=False,
            ),
            usage=None,
        )


def _reordered(value: dict) -> dict:
    return dict(reversed(list(value.items())))


@pytest.fixture(scope="module")
def phase2_inputs():
    chart = calculate_chart(
        SimpleNamespace(
            birth_date="1985-07-17",
            birth_time="21:50",
            birth_place="石川県",
            gender="female",
        ),
        target_datetime=datetime(2026, 8, 10, 15, 36),
    )
    reading_context = build_reading_context_v2(chart)
    judgment_metadata = build_common_judgment_metadata(chart)
    request = build_ai_reading_request_v2(reading_context, judgment_metadata)
    return {
        "ai_reading": _phase2_valid_reading(request, reading_context),
        "reading_context": reading_context,
        "judgment_metadata": judgment_metadata,
    }


@pytest.fixture(scope="module")
def three_pillar_generated_inputs():
    chart = calculate_chart(
        SimpleNamespace(
            birth_date="1985-07-17",
            birth_time=None,
            birth_place="石川県",
            gender="female",
        ),
        target_datetime=datetime(2026, 8, 10, 15, 36),
    )
    reading_context = build_reading_context_v2(chart)
    judgment_metadata = build_common_judgment_metadata(chart)
    assert reading_context["uncertainty"]
    reading_context["uncertainty"][0] = _reordered(
        reading_context["uncertainty"][0]
    )

    assert validate_reading_context_v2(reading_context)["valid"] is True
    assert validate_common_judgment_metadata(judgment_metadata)["valid"] is True
    assert validate_ai_reading_prompt_inputs_v2(
        reading_context,
        judgment_metadata,
    )["valid"] is True

    request = build_ai_reading_request_v2(reading_context, judgment_metadata)
    reading_template = _phase2_valid_reading(request, reading_context)
    responses = _StaticResponses(_phase2_model_payload(reading_template))
    result = generate_ai_reading_v2(
        request,
        client=SimpleNamespace(responses=responses),
        model="test-model",
    )
    assert len(responses.calls) == 1
    return {
        "ai_reading": result.reading,
        "reading_context": reading_context,
        "judgment_metadata": judgment_metadata,
    }


class ExplodingAssessor:
    @property
    def method(self):
        raise AssertionError("semantic assessor identity must not be read in Phase 2")

    @property
    def version(self):
        raise AssertionError("semantic assessor identity must not be read in Phase 2")

    def assess(self, *args):
        raise AssertionError("semantic assessor must not run in Phase 2")


def test_public_identity_constants_are_exact():
    assert AI_READING_QUALITY_REPORT_V2_SCHEMA_VERSION == "ai_reading_quality_report_v2"
    assert AI_READING_QUALITY_REPORT_V2_VERSION == "ai_reading_quality_report_v2"
    assert AI_READING_QUALITY_REPORT_V2_METHOD == "ai_reading_quality_gate_v2"
    assert AI_READING_QUALITY_REPORT_V2_STATUS == "completed"


def test_report_and_finding_have_exact_field_count_and_order():
    assert tuple(field.name for field in fields(AIReadingQualityReportV2)) == REPORT_FIELDS
    assert tuple(field.name for field in fields(AIReadingQualityFindingV2)) == FINDING_FIELDS
    report = _report().to_dict()
    assert tuple(report) == REPORT_FIELDS
    assert len(report) == 13


def test_report_output_has_exact_contract_types():
    report = _report(candidates=[_candidate("source_limitation_note")]).to_dict()
    assert all(isinstance(report[field], str) for field in REPORT_FIELDS[:5])
    assert type(report["blocking"]) is bool
    assert type(report["human_review_required"]) is bool
    assert all(
        type(report[field]) is int
        for field in ("error_count", "warning_count", "info_count")
    )
    assert isinstance(report["input_contracts"], dict)
    assert isinstance(report["semantic_assessment"], dict)
    assert isinstance(report["findings"], list)
    finding = report["findings"][0]
    assert isinstance(finding["evidence"], list)
    assert type(finding["blocking"]) is bool
    assert type(finding["requires_human_review"]) is bool


def test_report_and_finding_dataclasses_are_frozen():
    report = _report()
    with pytest.raises(FrozenInstanceError):
        report.decision = "review"
    finding = _report(
        candidates=[_candidate("source_limitation_note")]
    ).findings[0]
    with pytest.raises(FrozenInstanceError):
        finding.code = "overconfident_wording"


def test_report_to_dict_returns_deep_copy_with_exact_nested_shapes():
    report = _report(candidates=[_candidate("source_limitation_note")])
    first = report.to_dict()
    second = report.to_dict()
    first["input_contracts"]["ai_reading_v2"]["version"] = "changed"
    first["semantic_assessment"]["method"] = "changed"
    first["findings"][0]["evidence"][0]["path"] = "/changed"
    assert second["input_contracts"]["ai_reading_v2"]["version"] == "ai_reading_v2"
    assert second["semantic_assessment"]["method"] == "assessor_method"
    assert second["findings"][0]["evidence"] == _evidence()
    assert tuple(second["findings"][0]) == FINDING_FIELDS
    assert tuple(second["findings"][0]["evidence"][0]) == (
        "source_contract",
        "path",
    )


def test_issue_catalog_has_exact_26_codes_and_mappings():
    actual = tuple(
        (
            item.code,
            item.severity,
            item.blocking,
            item.repairability,
            item.requires_human_review,
        )
        for item in quality_v2._ISSUE_CATALOG
    )
    assert len(actual) == 26
    assert actual == EXPECTED_ISSUES
    assert len({item[0] for item in actual}) == 26


def test_issue_catalog_fixed_messages_are_all_exact():
    messages = tuple(item.message for item in quality_v2._ISSUE_CATALOG)
    assert messages == EXPECTED_MESSAGES
    assert all(isinstance(message, str) and message for message in messages)


def test_semantic_allowlist_is_exact_ordered_15_codes():
    assert quality_v2._SEMANTIC_ISSUE_CODES == EXPECTED_SEMANTIC_CODES
    assert len(quality_v2._SEMANTIC_ISSUE_CODES) == 15


@pytest.mark.parametrize(
    "code",
    [
        "semantic_assessment_unavailable",
        "semantic_assessment_failed",
        "semantic_assessment_inconclusive",
    ],
)
def test_only_infrastructure_codes_accept_empty_evidence(code):
    status = code.removeprefix("semantic_assessment_")
    report = _report(status, [_candidate(code, path="", evidence=[])])
    finding = report.to_dict()["findings"][0]
    assert finding["path"] == ""
    assert finding["evidence"] == []


def test_non_infrastructure_finding_rejects_empty_evidence():
    with pytest.raises(ValueError, match="require evidence"):
        _report(candidates=[_candidate("overconfident_wording", evidence=[])])


def test_infrastructure_finding_rejects_nonempty_evidence_or_path():
    with pytest.raises(ValueError, match="empty path and evidence"):
        _report(
            "unavailable",
            [_candidate("semantic_assessment_unavailable", path="/summary")],
        )


def test_evidence_requires_exact_two_fields_and_order():
    wrong_order = [{"path": "/summary", "source_contract": "ai_reading_v2"}]
    with pytest.raises(ValueError, match="fields/order"):
        _report(candidates=[_candidate("source_limitation_note", evidence=wrong_order)])
    with pytest.raises(ValueError, match="fields/order"):
        _report(
            candidates=[
                _candidate(
                    "source_limitation_note",
                    evidence=[
                        {
                            "source_contract": "ai_reading_v2",
                            "path": "/summary",
                            "extra": True,
                        }
                    ],
                )
            ]
        )


def test_evidence_sort_dedup_and_canonical_json_are_exact():
    evidence = [
        {"source_contract": "reading_context_v2", "path": "/chart"},
        {"source_contract": "ai_reading_v2", "path": "/sections/0"},
        {"source_contract": "ai_reading_v2", "path": "/sections/0"},
        {"source_contract": "ai_reading_v2", "path": "/summary"},
    ]
    expected = (
        {"source_contract": "ai_reading_v2", "path": "/sections/0"},
        {"source_contract": "ai_reading_v2", "path": "/summary"},
        {"source_contract": "reading_context_v2", "path": "/chart"},
    )
    assert quality_v2._normalize_evidence(evidence) == expected
    assert quality_v2._canonical_evidence_json(evidence) == (
        '[{"source_contract":"ai_reading_v2","path":"/sections/0"},'
        '{"source_contract":"ai_reading_v2","path":"/summary"},'
        '{"source_contract":"reading_context_v2","path":"/chart"}]'
    )
    assert quality_v2._canonical_evidence_json([]) == "[]"


def test_evidence_validation_rejects_unknown_contract_and_invalid_pointer():
    with pytest.raises(ValueError, match="source_contract"):
        quality_v2._normalize_evidence(
            [{"source_contract": "chart_result", "path": "/value"}]
        )
    with pytest.raises(ValueError, match="RFC 6901"):
        quality_v2._normalize_evidence(
            [{"source_contract": "ai_reading_v2", "path": "summary"}]
        )
    with pytest.raises(ValueError, match="RFC 6901"):
        quality_v2._normalize_evidence(
            [{"source_contract": "ai_reading_v2", "path": "/bad~2escape"}]
        )


def test_finding_sort_dedup_and_ids_are_deterministic():
    candidates = [
        _candidate("source_limitation_note", "/z"),
        _candidate("overconfident_wording", "/summary"),
        _candidate("claim_type_mismatch", "/sections/1/detail"),
        _candidate("claim_type_mismatch", "/sections/0/summary"),
        _candidate("claim_type_mismatch", "/sections/0/summary"),
    ]
    report = _report(semantic_candidates=candidates).to_dict()
    assert [(item["finding_id"], item["code"], item["path"]) for item in report["findings"]] == [
        ("finding_0001", "claim_type_mismatch", "/sections/0/summary"),
        ("finding_0002", "claim_type_mismatch", "/sections/1/detail"),
        ("finding_0003", "overconfident_wording", "/summary"),
        ("finding_0004", "source_limitation_note", "/z"),
    ]


def test_pass_decision_and_report_invariants():
    report = _report(
        semantic_candidates=[_candidate("overconfident_wording")]
    ).to_dict()
    assert report["decision"] == "pass"
    assert report["blocking"] is False
    assert report["human_review_required"] is False
    assert (report["error_count"], report["warning_count"], report["info_count"]) == (
        0,
        1,
        0,
    )


def test_fail_decision_and_human_review_invariant():
    report = _report(
        semantic_candidates=[_candidate("fact_semantic_mismatch")]
    ).to_dict()
    assert report["decision"] == "fail"
    assert report["blocking"] is True
    assert report["human_review_required"] is True
    assert report["error_count"] == 1


def test_review_decision_for_incomplete_semantic_assessment():
    report = _report(
        "unavailable",
        [_candidate("semantic_assessment_unavailable", path="", evidence=[])],
    ).to_dict()
    assert report["decision"] == "review"
    assert report["blocking"] is True
    assert report["human_review_required"] is True
    assert report["warning_count"] == 1


def test_not_run_requires_deterministic_error_and_produces_fail():
    report = _report(
        "not_run",
        [_candidate("trusted_field_mismatch")],
    ).to_dict()
    assert report["semantic_assessment"] == {
        "status": "not_run",
        "method": None,
        "version": None,
    }
    assert report["decision"] == "fail"
    with pytest.raises(ValueError, match="deterministic ERROR"):
        _report("not_run", [])


def test_inconclusive_retains_error_and_forces_fail():
    report = _report(
        "inconclusive",
        [_candidate("semantic_assessment_inconclusive", path="", evidence=[])],
        semantic_candidates=[_candidate("fact_semantic_mismatch")],
    ).to_dict()
    assert report["decision"] == "fail"
    assert report["error_count"] == 1
    assert report["warning_count"] == 1
    assert report["human_review_required"] is True


def test_semantic_status_requires_exact_infrastructure_finding():
    with pytest.raises(ValueError, match="exactly one"):
        _report("failed", [])
    with pytest.raises(ValueError, match="cannot contain"):
        _report(
            "completed",
            [_candidate("semantic_assessment_failed", path="", evidence=[])],
        )


@pytest.mark.parametrize(
    ("status", "infrastructure_code"),
    [
        ("unavailable", "semantic_assessment_unavailable"),
        ("failed", "semantic_assessment_failed"),
    ],
)
def test_deterministic_error_requires_not_run(status, infrastructure_code):
    with pytest.raises(ValueError, match="deterministic ERROR requires not_run"):
        _report(
            status,
            [
                _candidate("trusted_field_mismatch"),
                _candidate(infrastructure_code, path="", evidence=[]),
            ],
        )


def test_completed_retains_semantic_error_and_forces_fail():
    report = _report(
        "completed",
        semantic_candidates=[_candidate("claim_type_mismatch")],
    ).to_dict()
    assert report["decision"] == "fail"
    assert [finding["code"] for finding in report["findings"]] == [
        "claim_type_mismatch"
    ]


def test_failed_rejects_semantic_declarations_instead_of_retaining_them():
    with pytest.raises(ValueError, match="cannot retain semantic assessor declarations"):
        _report(
            "failed",
            [_candidate("semantic_assessment_failed", path="", evidence=[])],
            semantic_candidates=[_candidate("overconfident_wording")],
        )


def test_exact_counts_include_all_severities():
    report = _report(
        semantic_candidates=[
            _candidate("claim_type_mismatch", "/sections/0/summary"),
            _candidate("overconfident_wording", "/sections/0/detail"),
            _candidate("source_limitation_note", "/sections/0/advice/0"),
        ]
    ).to_dict()
    assert (report["error_count"], report["warning_count"], report["info_count"]) == (
        1,
        1,
        1,
    )
    assert report["decision"] == "fail"


def test_same_inputs_produce_same_report_without_mutation():
    input_contracts = _input_contracts()
    semantic = _semantic()
    candidates = [
        _candidate("source_limitation_note", evidence=_evidence("reading_context_v2", "/facts/0")),
        _candidate("overconfident_wording"),
    ]
    before = deepcopy((input_contracts, semantic, candidates))
    first = quality_v2._build_quality_report_v2(
        input_contracts,
        semantic,
        [],
        semantic_finding_candidates=candidates,
    ).to_dict()
    second = quality_v2._build_quality_report_v2(
        input_contracts,
        semantic,
        [],
        semantic_finding_candidates=candidates,
    ).to_dict()
    assert first == second
    assert (input_contracts, semantic, candidates) == before


@pytest.mark.parametrize("finding_id", ["finding_0000", "finding_00001"])
def test_finding_rejects_noncanonical_ids(finding_id):
    with pytest.raises(ValueError, match="finding_id"):
        _finding_with_id(finding_id)


@pytest.mark.parametrize(
    "finding_id",
    ["finding_0001", "finding_9999", "finding_10000"],
)
def test_finding_accepts_canonical_id_boundaries(finding_id):
    assert _finding_with_id(finding_id).finding_id == finding_id


def test_report_builder_assigns_canonical_ids_after_sort_and_dedup():
    report = _report(
        semantic_candidates=[
            _candidate("source_limitation_note", "/z"),
            _candidate("claim_type_mismatch", "/a"),
            _candidate("claim_type_mismatch", "/a"),
        ]
    ).to_dict()
    assert [finding["finding_id"] for finding in report["findings"]] == [
        "finding_0001",
        "finding_0002",
    ]


def test_input_contracts_and_semantic_metadata_require_exact_shape_and_order():
    reordered = dict(reversed(list(_input_contracts().items())))
    with pytest.raises(ValueError, match="fields/order"):
        quality_v2._build_quality_report_v2(reordered, _semantic(), [])
    semantic = {"method": "assessor_method", "status": "completed", "version": "1.0"}
    with pytest.raises(ValueError, match="fields/order"):
        quality_v2._build_quality_report_v2(_input_contracts(), semantic, [])


def test_public_evaluator_signature_is_exact():
    signature = inspect.signature(evaluate_ai_reading_quality_v2)
    assert tuple(signature.parameters) == (
        "ai_reading",
        "reading_context",
        "judgment_metadata",
        "semantic_assessor",
    )
    assert signature.parameters["semantic_assessor"].kind is inspect.Parameter.KEYWORD_ONLY
    assert signature.parameters["semantic_assessor"].default is None


def test_semantic_assessor_protocol_declares_read_only_identity_and_assess():
    assert isinstance(SemanticAssessorV2.method, property)
    assert isinstance(SemanticAssessorV2.version, property)
    assert callable(SemanticAssessorV2.assess)


def test_module_has_no_generator_v1_or_astrology_dependencies():
    source = inspect.getsource(quality_v2)
    forbidden = (
        "engine.reading_generator_v2",
        "engine.reading_quality import",
        "engine.chart",
        "engine.luck",
    )
    assert all(item not in source for item in forbidden)


@pytest.mark.parametrize(
    "field",
    ("ai_reading", "reading_context", "judgment_metadata"),
)
def test_phase2_non_mapping_input_raises_type_error(phase2_inputs, field):
    inputs = deepcopy(phase2_inputs)
    inputs[field] = []
    with pytest.raises(TypeError, match=field):
        evaluate_ai_reading_quality_v2(**inputs)


@pytest.mark.parametrize(
    ("field", "source_contract"),
    (
        ("reading_context", "reading_context_v2"),
        ("judgment_metadata", "common_judgment_metadata_v1"),
    ),
)
def test_phase2_owner_invalid_contract_returns_one_root_finding(
    phase2_inputs,
    field,
    source_contract,
):
    inputs = deepcopy(phase2_inputs)
    inputs[field]["schema_version"] = "invalid_contract"
    report = evaluate_ai_reading_quality_v2(
        **inputs,
        semantic_assessor=ExplodingAssessor(),
    ).to_dict()

    assert report["decision"] == "fail"
    assert report["semantic_assessment"] == {
        "status": "not_run",
        "method": None,
        "version": None,
    }
    assert len(report["findings"]) == 1
    assert report["findings"][0]["code"] == "input_contract_invalid"
    assert report["findings"][0]["path"] == ""
    assert report["findings"][0]["evidence"] == [
        {"source_contract": source_contract, "path": ""}
    ]


def test_phase2_ai_reading_contract_invalid_returns_one_root_finding(
    phase2_inputs,
):
    inputs = deepcopy(phase2_inputs)
    inputs["ai_reading"].pop("summary")
    report = evaluate_ai_reading_quality_v2(
        **inputs,
        semantic_assessor=ExplodingAssessor(),
    ).to_dict()

    assert len(report["findings"]) == 1
    assert report["findings"][0]["code"] == "ai_reading_contract_invalid"
    assert report["findings"][0]["evidence"] == [
        {"source_contract": "ai_reading_v2", "path": ""}
    ]


def test_phase2_multiple_invalid_contracts_do_not_fail_fast(phase2_inputs):
    inputs = deepcopy(phase2_inputs)
    inputs["reading_context"]["schema_version"] = "invalid_context"
    inputs["judgment_metadata"]["schema_version"] = "invalid_metadata"
    inputs["ai_reading"].pop("summary")
    report = evaluate_ai_reading_quality_v2(**inputs).to_dict()

    assert report["error_count"] == 3
    assert [finding["code"] for finding in report["findings"]] == [
        "ai_reading_contract_invalid",
        "input_contract_invalid",
        "input_contract_invalid",
    ]
    assert {
        finding["evidence"][0]["source_contract"]
        for finding in report["findings"]
    } == {
        "ai_reading_v2",
        "reading_context_v2",
        "common_judgment_metadata_v1",
    }


def test_phase2_prompt_prerequisite_invalid_uses_two_contract_roots(
    phase2_inputs,
):
    inputs = deepcopy(phase2_inputs)
    inputs["reading_context"]["warnings"] = [1]
    report = evaluate_ai_reading_quality_v2(
        **inputs,
        semantic_assessor=ExplodingAssessor(),
    ).to_dict()

    assert len(report["findings"]) == 1
    finding = report["findings"][0]
    assert finding["code"] == "input_contract_invalid"
    assert finding["evidence"] == [
        {"source_contract": "common_judgment_metadata_v1", "path": ""},
        {"source_contract": "reading_context_v2", "path": ""},
    ]
    assert all("warnings" not in entry["path"] for entry in finding["evidence"])


@pytest.mark.parametrize(
    ("raw_value", "projected"),
    (("", ""), (None, None), (1, None), (False, None)),
)
def test_phase2_invalid_identity_projection_is_raw_or_null(
    phase2_inputs,
    raw_value,
    projected,
):
    inputs = deepcopy(phase2_inputs)
    inputs["reading_context"]["schema_version"] = raw_value
    report = evaluate_ai_reading_quality_v2(**inputs).to_dict()
    assert report["input_contracts"]["reading_context_v2"][
        "schema_version"
    ] == projected


def test_phase2_missing_ai_identity_projects_null_without_completion(
    phase2_inputs,
):
    inputs = deepcopy(phase2_inputs)
    inputs["ai_reading"].pop("version")
    report = evaluate_ai_reading_quality_v2(**inputs).to_dict()
    assert report["input_contracts"]["ai_reading_v2"]["version"] is None
    assert report["findings"][0]["code"] == "ai_reading_contract_invalid"


def test_phase2_engine_version_projection_and_mismatch(phase2_inputs):
    inputs = deepcopy(phase2_inputs)
    inputs["reading_context"]["engine_version"] = ""
    report = evaluate_ai_reading_quality_v2(**inputs).to_dict()

    assert report["input_contracts"]["reading_context_v2"] == {
        "schema_version": "reading_context_v2",
        "version": "reading_context_v2",
        "method": "reading_context_v2",
        "status": "ready_for_ai_reading",
    }
    assert report["input_contracts"]["ai_reading_v2"]["engine_version"] == (
        phase2_inputs["ai_reading"]["engine_version"]
    )
    assert [finding["code"] for finding in report["findings"]] == [
        "input_contract_mismatch"
    ]


@pytest.mark.parametrize(
    "mutation",
    ("engine_version", "reading_context_identity", "metadata_identity"),
)
def test_phase2_trusted_identity_mismatch_is_deterministic(
    phase2_inputs,
    mutation,
):
    inputs = deepcopy(phase2_inputs)
    if mutation == "engine_version":
        inputs["ai_reading"]["engine_version"] = "different-engine"
    elif mutation == "reading_context_identity":
        inputs["ai_reading"]["source_contracts"]["reading_context"][
            "status"
        ] = "different-status"
    else:
        inputs["ai_reading"]["source_contracts"]["judgment_metadata"][
            "schema_version"
        ] = "different-metadata"

    report = evaluate_ai_reading_quality_v2(
        **inputs,
        semantic_assessor=ExplodingAssessor(),
    ).to_dict()
    assert report["semantic_assessment"]["status"] == "not_run"
    assert [finding["code"] for finding in report["findings"]] == [
        "input_contract_mismatch"
    ]
    assert report["findings"][0]["evidence"] == [
        {"source_contract": "ai_reading_v2", "path": ""},
        {"source_contract": "common_judgment_metadata_v1", "path": ""},
        {"source_contract": "reading_context_v2", "path": ""},
    ]


def test_phase2_malformed_source_contracts_is_ai_contract_invalid(
    phase2_inputs,
):
    inputs = deepcopy(phase2_inputs)
    inputs["ai_reading"].pop("source_contracts")
    report = evaluate_ai_reading_quality_v2(**inputs).to_dict()
    assert [finding["code"] for finding in report["findings"]] == [
        "ai_reading_contract_invalid"
    ]


def test_phase2_reordered_owner_valid_three_pillar_uncertainty_reaches_next_phase(
    three_pillar_generated_inputs,
):
    with pytest.raises(NotImplementedError, match="deterministic Phase 2"):
        evaluate_ai_reading_quality_v2(
            **deepcopy(three_pillar_generated_inputs),
            semantic_assessor=ExplodingAssessor(),
        )


@pytest.mark.parametrize(
    "mapping_name",
    (
        "top_level",
        "section",
        "yearly_entry",
        "catalog_entry",
        "source_contracts",
        "source_contract_identity",
        "validation",
    ),
)
def test_phase2_unfrozen_ai_reading_mapping_order_is_not_required(
    three_pillar_generated_inputs,
    mapping_name,
):
    inputs = deepcopy(three_pillar_generated_inputs)
    reading = inputs["ai_reading"]
    if mapping_name == "top_level":
        inputs["ai_reading"] = _reordered(reading)
    elif mapping_name == "section":
        reading["sections"][0] = _reordered(reading["sections"][0])
    elif mapping_name == "yearly_entry":
        reading["sections"][6]["yearly"][0] = _reordered(
            reading["sections"][6]["yearly"][0]
        )
    elif mapping_name == "catalog_entry":
        reading["uncertainty"][0] = _reordered(reading["uncertainty"][0])
    elif mapping_name == "source_contracts":
        reading["source_contracts"] = _reordered(reading["source_contracts"])
    elif mapping_name == "source_contract_identity":
        reading["source_contracts"]["reading_context"] = _reordered(
            reading["source_contracts"]["reading_context"]
        )
    else:
        reading["validation"] = _reordered(reading["validation"])

    with pytest.raises(NotImplementedError, match="deterministic Phase 2"):
        evaluate_ai_reading_quality_v2(
            **inputs,
            semantic_assessor=ExplodingAssessor(),
        )


def test_phase2_grounded_text_block_order_remains_required(phase2_inputs):
    inputs = deepcopy(phase2_inputs)
    inputs["ai_reading"]["summary"] = _reordered(
        inputs["ai_reading"]["summary"]
    )
    report = evaluate_ai_reading_quality_v2(**inputs).to_dict()
    assert [finding["code"] for finding in report["findings"]] == [
        "ai_reading_contract_invalid"
    ]


@pytest.mark.parametrize("invalid_shape", ("missing", "unknown", "wrong_type"))
def test_phase2_exact_key_set_still_rejects_invalid_shape(
    phase2_inputs,
    invalid_shape,
):
    inputs = deepcopy(phase2_inputs)
    section = inputs["ai_reading"]["sections"][0]
    if invalid_shape == "missing":
        section.pop("detail")
    elif invalid_shape == "unknown":
        section["unexpected"] = None
    else:
        section["warnings"] = "not-an-array"

    report = evaluate_ai_reading_quality_v2(**inputs).to_dict()
    assert [finding["code"] for finding in report["findings"]] == [
        "ai_reading_contract_invalid"
    ]


def test_phase2_inputs_are_not_mutated(phase2_inputs):
    inputs = deepcopy(phase2_inputs)
    inputs["reading_context"]["schema_version"] = "invalid_context"
    before = deepcopy(inputs)
    evaluate_ai_reading_quality_v2(**inputs)
    assert inputs == before


def test_phase2_valid_inputs_do_not_return_a_temporary_report(phase2_inputs):
    with pytest.raises(NotImplementedError, match="deterministic Phase 2"):
        evaluate_ai_reading_quality_v2(
            **deepcopy(phase2_inputs),
            semantic_assessor=ExplodingAssessor(),
        )
