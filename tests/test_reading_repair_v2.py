"""Frozen section 24 contract tests for Auto-Repair v2."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from hashlib import sha256
import inspect
import json
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

import engine.reading_repair_v2 as repair_v2
from engine.chart import calculate_chart
from engine.judgment_metadata import build_common_judgment_metadata
from engine.reading_context_v2 import build_reading_context_v2
from engine.reading_prompt_v2 import build_ai_reading_request_v2
from engine.reading_quality_v2 import evaluate_ai_reading_quality_v2
from engine.reading_repair_v2 import (
    AI_READING_REPAIR_V2_INSTRUCTIONS,
    AI_READING_REPAIR_V2_JSON_SCHEMA_NAME,
    AI_READING_REPAIR_V2_MAX_ATTEMPTS,
    AI_READING_REPAIR_V2_METHOD,
    AI_READING_REPAIR_V2_SCHEMA_VERSION,
    AI_READING_REPAIR_V2_VERSION,
    AIReadingRepairResultV2,
    AIReadingRepairV2CandidateValidationError,
    AIReadingRepairV2ConfigurationError,
    AIReadingRepairV2PatchValidationError,
    AIReadingRepairV2ProviderRequestError,
    AIReadingRepairV2ProviderResponseError,
    RepairAttemptLogV2,
    repair_ai_reading_v2,
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
RESULT_FIELDS = (
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
ATTEMPT_FIELDS = ("attempt", "issue_codes", "before_hash", "after_hash", "result")


def _block(text: str = "落ち着いて状況を整理しましょう。") -> dict:
    return {
        "text": text,
        "claim_type": "practical",
        "source_fact_codes": [],
        "source_components": [],
        "warnings": [],
        "uncertainty": [],
    }


def _valid_reading(request: dict, reading_context: dict) -> dict:
    sections = []
    for section_id, title in EXPECTED_SECTION_SLOTS:
        section = {
            "section_id": section_id,
            "title": title,
            "facts": [],
            "summary": _block(f"{title}の要点です。"),
            "detail": _block(f"{title}の詳細です。"),
            "evidence": [],
            "interpretation": [],
            "advice": [_block(f"{title}の実用的な助言です。")],
            "warnings": [],
            "uncertainty": [],
        }
        if section_id == "future_flow":
            section["yearly"] = [
                {
                    "year": entry["year"],
                    "summary": _block(f"{entry['year']}年の要点です。"),
                    "detail": _block(f"{entry['year']}年の詳細です。"),
                }
                for entry in reading_context["luck"]["five_year_luck"]
            ]
        sections.append(section)
    return {
        "schema_version": "ai_reading_v2",
        "engine_version": deepcopy(reading_context["engine_version"]),
        "summary": _block("全体を落ち着いて整理します。"),
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


def _semantic_finding(
    code: str = "claim_type_mismatch",
    path: str = "/sections/0/summary",
) -> dict:
    return {
        "code": code,
        "path": path,
        "evidence": [{"source_contract": "ai_reading_v2", "path": path}],
    }


class SequenceAssessor:
    def __init__(self, results: list[dict]):
        self.results = deepcopy(results)
        self.calls = 0
        self.received = []

    @property
    def method(self):
        return "repair_v2_test_assessor"

    @property
    def version(self):
        return "v1"

    def assess(self, ai_reading, reading_context, judgment_metadata):
        self.received.append(
            (deepcopy(ai_reading), deepcopy(reading_context), deepcopy(judgment_metadata))
        )
        index = min(self.calls, len(self.results) - 1)
        self.calls += 1
        return deepcopy(self.results[index])


def _completed(*findings: dict) -> dict:
    return {"status": "completed", "findings": list(findings)}


class FakeResponses:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(deepcopy(kwargs))
        output = self.outputs[len(self.calls) - 1]
        if isinstance(output, BaseException):
            raise output
        if isinstance(output, str):
            text = output
        else:
            text = json.dumps(
                output,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=False,
                allow_nan=False,
            )
        return SimpleNamespace(output_text=text, id="must_not_persist", usage={"x": 1})


class FakeClient:
    def __init__(self, outputs):
        self.responses = FakeResponses(outputs)


def _patch(path="/sections/0/summary/text", value="修正後の本文です。") -> dict:
    return {"patches": [{"op": "replace", "path": path, "value": value}]}


@pytest.fixture(scope="module")
def repair_inputs():
    chart = calculate_chart(
        SimpleNamespace(
            birth_date="1984-07-22",
            birth_time="13:40",
            birth_place="福岡県",
            gender="male",
        ),
        target_datetime=datetime(2026, 8, 10, 15, 36, tzinfo=ZoneInfo("Asia/Tokyo")),
    )
    reading_context = build_reading_context_v2(chart)
    judgment_metadata = build_common_judgment_metadata(chart)
    request = build_ai_reading_request_v2(reading_context, judgment_metadata)
    return {
        "ai_reading": _valid_reading(request, reading_context),
        "reading_context": reading_context,
        "judgment_metadata": judgment_metadata,
    }


def _initial_failure(inputs: dict, assessor: SequenceAssessor):
    return evaluate_ai_reading_quality_v2(
        inputs["ai_reading"],
        inputs["reading_context"],
        inputs["judgment_metadata"],
        semantic_assessor=assessor,
    )


def _repair(inputs: dict, report, assessor, client, **options):
    return repair_ai_reading_v2(
        inputs["ai_reading"],
        report,
        inputs["reading_context"],
        inputs["judgment_metadata"],
        semantic_assessor=assessor,
        client=client,
        model=" test-model ",
        **options,
    )


def _fabricated_result_arguments(inputs: dict, initial_report) -> dict:
    final_ai = deepcopy(inputs["ai_reading"])
    final_ai["summary"]["text"] = "fabricated repaired text"
    before_hash = repair_v2._canonical_hash(inputs["ai_reading"])
    after_hash = repair_v2._canonical_hash(final_ai)
    targets = tuple(
        finding
        for finding in initial_report.findings
        if finding.repairability == "auto"
    )
    finding_ids = [finding.finding_id for finding in targets] or ["finding_0001"]
    issue_codes = [finding.code for finding in targets] or ["fabricated_issue"]
    return {
        "initial_ai_reading": inputs["ai_reading"],
        "final_ai_reading": final_ai,
        "initial_quality_report": initial_report.to_dict(),
        "final_quality_report": initial_report.to_dict(),
        "target_finding_ids": finding_ids,
        "attempts": [
            RepairAttemptLogV2(
                attempt=1,
                issue_codes=issue_codes,
                before_hash=before_hash,
                after_hash=after_hash,
                result="repaired",
            )
        ],
    }


def _assert_public_exception_is_sanitized(error: BaseException, secret: str) -> None:
    assert secret not in str(error)
    assert secret not in repr(error.args)
    assert secret not in repr(vars(error))
    assert error.__cause__ is None
    assert error.__context__ is None


def test_public_identity_signature_and_one_attempt_pass(repair_inputs):
    assessor = SequenceAssessor(
        [_completed(_semantic_finding()), _completed()]
    )
    report = _initial_failure(repair_inputs, assessor)
    client = FakeClient([_patch()])
    before = deepcopy(repair_inputs)

    result = _repair(repair_inputs, report, assessor, client)
    value = result.to_dict()

    assert isinstance(result, AIReadingRepairResultV2)
    assert tuple(value) == RESULT_FIELDS
    assert value["schema_version"] == AI_READING_REPAIR_V2_SCHEMA_VERSION
    assert value["version"] == AI_READING_REPAIR_V2_VERSION
    assert value["method"] == AI_READING_REPAIR_V2_METHOD
    assert value["status"] == "pass"
    assert value["final_quality_report"]["decision"] == "pass"
    assert value["target_finding_ids"] == ["finding_0001"]
    assert tuple(value["attempts"][0]) == ATTEMPT_FIELDS
    assert value["attempts"][0]["result"] == "repaired"
    assert value["final_ai_reading"]["sections"][0]["summary"]["text"] == "修正後の本文です。"
    assert repair_inputs == before
    assert len(client.responses.calls) == 1
    assert assessor.calls == 2
    signature = inspect.signature(repair_ai_reading_v2)
    assert tuple(signature.parameters) == (
        "ai_reading",
        "quality_report",
        "reading_context",
        "judgment_metadata",
        "semantic_assessor",
        "client",
        "model",
        "max_output_tokens",
        "reasoning_effort",
        "store",
    )


@pytest.mark.parametrize("state", ["pass", "review", "non_auto_fail"])
def test_result_constructor_rejects_impossible_initial_repair_state(
    repair_inputs, state
):
    if state == "pass":
        assessor = SequenceAssessor(
            [_completed(_semantic_finding("overconfident_wording"))]
        )
        status = "pass"
    elif state == "review":
        assessor = SequenceAssessor([{"status": "inconclusive", "findings": []}])
        status = "exhausted"
    else:
        assessor = SequenceAssessor([_completed(_semantic_finding("prohibited_claim"))])
        status = "exhausted"
    report = _initial_failure(repair_inputs, assessor)
    arguments = _fabricated_result_arguments(repair_inputs, report)

    with pytest.raises(
        ValueError,
        match="initial_quality_report is not eligible for automatic repair",
    ):
        AIReadingRepairResultV2(status=status, **arguments)


def test_result_constructor_accepts_valid_initial_eligible_failure(repair_inputs):
    assessor = SequenceAssessor([_completed(_semantic_finding()), _completed()])
    report = _initial_failure(repair_inputs, assessor)
    result = _repair(repair_inputs, report, assessor, FakeClient([_patch()]))
    value = result.to_dict()

    reconstructed = AIReadingRepairResultV2(
        status=value["status"],
        initial_ai_reading=value["initial_ai_reading"],
        final_ai_reading=value["final_ai_reading"],
        initial_quality_report=value["initial_quality_report"],
        final_quality_report=value["final_quality_report"],
        target_finding_ids=value["target_finding_ids"],
        attempts=result.attempts,
    )

    assert reconstructed.to_dict() == value


def test_result_constructor_rejects_one_attempt_still_eligible_exhausted(
    repair_inputs,
):
    assessor = SequenceAssessor([_completed(_semantic_finding())])
    report = _initial_failure(repair_inputs, assessor)
    arguments = _fabricated_result_arguments(repair_inputs, report)

    with pytest.raises(
        ValueError,
        match="one-attempt exhausted result cannot remain eligible for repair",
    ):
        AIReadingRepairResultV2(status="exhausted", **arguments)


@pytest.mark.parametrize(
    "terminal_finding",
    [
        None,
        _semantic_finding("prohibited_claim"),
    ],
    ids=("review", "non-auto-fail"),
)
def test_result_constructor_accepts_one_attempt_terminal_exhausted(
    repair_inputs,
    terminal_finding,
):
    initial_finding = _semantic_finding()
    if terminal_finding is None:
        second_assessment = {"status": "inconclusive", "findings": []}
    else:
        second_assessment = _completed(terminal_finding)
    assessor = SequenceAssessor(
        [_completed(initial_finding), second_assessment]
    )
    report = _initial_failure(repair_inputs, assessor)
    result = _repair(repair_inputs, report, assessor, FakeClient([_patch()]))
    value = result.to_dict()

    reconstructed = AIReadingRepairResultV2(
        status="exhausted",
        initial_ai_reading=value["initial_ai_reading"],
        final_ai_reading=value["final_ai_reading"],
        initial_quality_report=value["initial_quality_report"],
        final_quality_report=value["final_quality_report"],
        target_finding_ids=value["target_finding_ids"],
        attempts=result.attempts,
    )

    assert reconstructed.to_dict() == value


def test_result_constructor_accepts_two_attempt_exhausted(repair_inputs):
    finding = _semantic_finding()
    assessor = SequenceAssessor([_completed(finding)] * 3)
    report = _initial_failure(repair_inputs, assessor)
    result = _repair(
        repair_inputs,
        report,
        assessor,
        FakeClient([_patch(value="first repair"), _patch(value="second repair")]),
    )
    value = result.to_dict()

    reconstructed = AIReadingRepairResultV2(
        status="exhausted",
        initial_ai_reading=value["initial_ai_reading"],
        final_ai_reading=value["final_ai_reading"],
        initial_quality_report=value["initial_quality_report"],
        final_quality_report=value["final_quality_report"],
        target_finding_ids=value["target_finding_ids"],
        attempts=result.attempts,
    )

    assert len(reconstructed.attempts) == 2
    assert reconstructed.to_dict() == value


def test_provider_payload_and_exact_five_field_input(repair_inputs):
    assessor = SequenceAssessor([_completed(_semantic_finding()), _completed()])
    report = _initial_failure(repair_inputs, assessor)
    client = FakeClient([_patch()])

    _repair(
        repair_inputs,
        report,
        assessor,
        client,
        max_output_tokens=321,
        reasoning_effort="minimal",
        store=True,
    )

    call = client.responses.calls[0]
    assert tuple(call) == (
        "model",
        "instructions",
        "input",
        "max_output_tokens",
        "reasoning",
        "store",
        "text",
    )
    assert call["model"] == "test-model"
    assert call["instructions"] == AI_READING_REPAIR_V2_INSTRUCTIONS
    assert call["max_output_tokens"] == 321
    assert call["reasoning"] == {"effort": "minimal"}
    assert call["store"] is True
    model_input = json.loads(call["input"][0]["content"])
    assert tuple(model_input) == (
        "schema_version",
        "attempt",
        "target_findings",
        "editable_blocks",
        "grounding_input",
    )
    assert tuple(model_input["editable_blocks"][0]) == ("path", "text")
    assert model_input["editable_blocks"] == [
        {
            "path": "/sections/0/summary/text",
            "text": repair_inputs["ai_reading"]["sections"][0]["summary"]["text"],
        }
    ]
    assert "messages" not in model_input
    assert "model_output_schema" not in model_input
    assert "quality_report" not in model_input
    assert "ai_reading" not in model_input
    expected_transport_schema = deepcopy(repair_v2._REPAIR_PATCH_SCHEMA)
    expected_transport_schema["properties"]["patches"]["items"]["properties"][
        "op"
    ]["type"] = "string"
    assert call["text"]["format"] == {
        "type": "json_schema",
        "name": AI_READING_REPAIR_V2_JSON_SCHEMA_NAME,
        "schema": expected_transport_schema,
        "strict": True,
    }
    assert "uniqueItems" not in json.dumps(call["text"]["format"]["schema"])


def test_openai_transport_schema_adds_only_op_string_type_without_mutation():
    canonical_before = deepcopy(repair_v2._REPAIR_PATCH_SCHEMA)

    transport = repair_v2._openai_transport_patch_schema()

    assert repair_v2._REPAIR_PATCH_SCHEMA == canonical_before
    assert repair_v2._REPAIR_PATCH_SCHEMA["properties"]["patches"]["items"][
        "properties"
    ]["op"] == {"const": "replace"}
    assert transport["properties"]["patches"]["items"]["properties"]["op"] == {
        "const": "replace",
        "type": "string",
    }

    expected = deepcopy(canonical_before)
    expected["properties"]["patches"]["items"]["properties"]["op"][
        "type"
    ] = "string"
    assert transport == expected

    transport["properties"]["patches"]["items"]["properties"]["op"][
        "const"
    ] = "mutated"
    assert repair_v2._REPAIR_PATCH_SCHEMA == canonical_before


@pytest.mark.parametrize("state", ["pass", "review", "human_fail"])
def test_ineligible_report_never_calls_provider(repair_inputs, state):
    if state == "pass":
        assessor = SequenceAssessor([_completed()])
    elif state == "review":
        assessor = SequenceAssessor([{"status": "inconclusive", "findings": []}])
    else:
        assessor = SequenceAssessor(
            [_completed(_semantic_finding("prohibited_claim"))]
        )
    report = _initial_failure(repair_inputs, assessor)
    client = FakeClient([_patch()])

    with pytest.raises(AIReadingRepairV2ConfigurationError):
        _repair(repair_inputs, report, assessor, client)

    assert client.responses.calls == []


def test_unresolvable_target_is_configuration_error_without_provider_call(repair_inputs):
    assessor = SequenceAssessor(
        [_completed(_semantic_finding(path="/sections/0"))]
    )
    report = _initial_failure(repair_inputs, assessor)
    client = FakeClient([_patch()])

    with pytest.raises(AIReadingRepairV2ConfigurationError):
        _repair(repair_inputs, report, assessor, client)

    assert client.responses.calls == []


def test_target_order_and_editable_path_deduplication(repair_inputs):
    findings = (
        _semantic_finding("judgment_status_wording_violation", "/sections/1/detail"),
        _semantic_finding("claim_type_mismatch", "/sections/0/summary/claim_type"),
        _semantic_finding("unsupported_numeric_claim", "/sections/0/summary/text"),
    )
    assessor = SequenceAssessor([_completed(*findings), _completed()])
    report = _initial_failure(repair_inputs, assessor)
    expected = [(f.finding_id, f.code, f.path) for f in report.findings]
    client = FakeClient(
        [
            {
                "patches": [
                    {
                        "op": "replace",
                        "path": "/sections/0/summary/text",
                        "value": "最初の修正文です。",
                    },
                    {
                        "op": "replace",
                        "path": "/sections/1/detail/text",
                        "value": "次の修正文です。",
                    },
                ]
            }
        ]
    )

    result = _repair(repair_inputs, report, assessor, client)

    assert result.target_finding_ids == tuple(item[0] for item in expected)
    sent = json.loads(client.responses.calls[0]["input"][0]["content"])
    assert [entry["path"] for entry in sent["editable_blocks"]] == [
        "/sections/0/summary/text",
        "/sections/1/detail/text",
    ]
    assert [entry["finding_id"] for entry in sent["target_findings"]] == list(
        result.target_finding_ids
    )


def test_two_attempts_then_pass_and_no_third_call(repair_inputs):
    finding = _semantic_finding()
    assessor = SequenceAssessor(
        [_completed(finding), _completed(finding), _completed()]
    )
    report = _initial_failure(repair_inputs, assessor)
    client = FakeClient(
        [
            _patch(value="一回目の修正文です。"),
            _patch(value="二回目の修正文です。"),
            _patch(value="呼ばれてはいけません。"),
        ]
    )

    result = _repair(repair_inputs, report, assessor, client)

    assert result.status == "pass"
    assert len(result.attempts) == AI_READING_REPAIR_V2_MAX_ATTEMPTS
    assert len(client.responses.calls) == 2
    second_input = json.loads(client.responses.calls[1]["input"][0]["content"])
    assert second_input["attempt"] == 2
    assert second_input["editable_blocks"][0]["text"] == "一回目の修正文です。"


def test_two_valid_attempts_exhaust_without_fabricating_pass(repair_inputs):
    finding = _semantic_finding()
    assessor = SequenceAssessor([_completed(finding)] * 3)
    report = _initial_failure(repair_inputs, assessor)
    client = FakeClient(
        [_patch(value="一回目。"), _patch(value="二回目。"), _patch(value="三回目。")]
    )

    result = _repair(repair_inputs, report, assessor, client)

    assert result.status == "exhausted"
    assert result.final_quality_report.decision == "fail"
    assert len(result.attempts) == 2
    assert len(client.responses.calls) == 2


def test_review_after_valid_attempt_is_terminal_exhausted(repair_inputs):
    assessor = SequenceAssessor(
        [
            _completed(_semantic_finding()),
            {"status": "inconclusive", "findings": []},
        ]
    )
    report = _initial_failure(repair_inputs, assessor)
    client = FakeClient([_patch(), _patch(value="呼ばれません。")])

    result = _repair(repair_inputs, report, assessor, client)

    assert result.status == "exhausted"
    assert result.final_quality_report.decision == "review"
    assert len(result.attempts) == 1
    assert len(client.responses.calls) == 1


def test_deterministic_numeric_failure_repairs_through_public_quality_gate(repair_inputs):
    inputs = deepcopy(repair_inputs)
    block = inputs["ai_reading"]["sections"][0]["summary"]
    inputs["ai_reading"]["sections"][0]["facts"] = ["day_master.stem"]
    block["claim_type"] = "astrology"
    block["source_fact_codes"] = ["day_master.stem"]
    block["text"] = "根拠のない数値999999を含みます。"
    assessor = SequenceAssessor([_completed()])
    report = _initial_failure(inputs, assessor)
    assert report.decision == "fail"
    assert report.semantic_assessment["status"] == "not_run"
    assert assessor.calls == 0
    assert [finding.code for finding in report.findings] == [
        "unsupported_numeric_claim"
    ]
    client = FakeClient(
        [
            _patch(
                path="/sections/0/summary/text",
                value="日主というtrusted factに沿って要点を説明します。",
            )
        ]
    )

    result = _repair(inputs, report, assessor, client)

    assert result.status == "pass"
    assert result.final_quality_report.semantic_assessment["status"] == "completed"
    assert assessor.calls == 1
    assert result.attempts[0].issue_codes == ("unsupported_numeric_claim",)


HOSTILE_PATHS = (
    "/",
    "/sections/0/summary",
    "/sections/0",
    "/sections",
    "/sections/0/summary/claim_type",
    "/sections/0/summary/references",
    "/sections/0/summary/fact_reference",
    "/sections/0/summary/luck_reference",
    "/sections/0/id",
    "/sections/0/title",
    "/sections/6/yearly/0/year",
    "/disclaimer",
    "/source_contracts",
    "/warnings",
    "/uncertainty",
    "/validation",
    "/sections~10~1summary~1text",
    "/sections/0/summary~1text",
    "/sections/0/summary~0/text",
    "#/sections/0/summary/text",
    "/sections%2F0%2Fsummary%2Ftext",
    "/sections/00/summary/text",
    "/sections/０/summary/text",
    "/ｓｅｃｔｉｏｎｓ/0/summary/text",
)


@pytest.mark.parametrize("path", HOSTILE_PATHS)
def test_hostile_paths_are_rejected_atomically(repair_inputs, path):
    assessor = SequenceAssessor([_completed(_semantic_finding())])
    report = _initial_failure(repair_inputs, assessor)
    client = FakeClient([_patch(path=path)])
    before = deepcopy(repair_inputs)

    with pytest.raises(AIReadingRepairV2PatchValidationError):
        _repair(repair_inputs, report, assessor, client)

    assert repair_inputs == before
    assert len(client.responses.calls) == 1
    assert assessor.calls == 1


@pytest.mark.parametrize(
    "patches",
    [
        [
            {"op": "replace", "path": "/sections/0/summary/text", "value": "A"},
            {"op": "replace", "path": "/sections/0/summary/text", "value": "B"},
        ],
        [{"op": "replace", "path": "/sections/0/summary/text", "value": "   "}],
        [
            {
                "op": "replace",
                "path": "/sections/0/summary/text",
                "value": "本質・性格の要点です。",
            }
        ],
    ],
)
def test_duplicate_whitespace_and_noop_patches_are_rejected(repair_inputs, patches):
    assessor = SequenceAssessor([_completed(_semantic_finding())])
    report = _initial_failure(repair_inputs, assessor)
    client = FakeClient([{"patches": patches}])

    with pytest.raises(AIReadingRepairV2PatchValidationError):
        _repair(repair_inputs, report, assessor, client)


def test_patch_order_must_be_editable_order_subsequence(repair_inputs):
    assessor = SequenceAssessor(
        [
            _completed(
                _semantic_finding("claim_type_mismatch", "/sections/0/summary"),
                _semantic_finding(
                    "judgment_status_wording_violation", "/sections/1/detail"
                ),
            )
        ]
    )
    report = _initial_failure(repair_inputs, assessor)
    client = FakeClient(
        [
            {
                "patches": [
                    {"op": "replace", "path": "/sections/1/detail/text", "value": "B"},
                    {"op": "replace", "path": "/sections/0/summary/text", "value": "A"},
                ]
            }
        ]
    )

    with pytest.raises(AIReadingRepairV2PatchValidationError):
        _repair(repair_inputs, report, assessor, client)


INVALID_RESPONSES = (
    "not json",
    '{"patches":[],"patches":[]}',
    '{"patches":NaN}',
    '{"patches":Infinity}',
    '{"patches":[]} trailing',
    '```json\n{"patches":[]}\n```',
    "[]",
    '{"patches":[]}',
    '{"patches":[],"extra":1}',
    '{"extra":1}',
    '{"patches":[{"op":"add","path":"/sections/0/summary/text","value":"x"}]}',
    '{"patches":[{"op":"replace","path":"","value":"x"}]}',
    '{"patches":[{"op":"replace","path":"/sections/0/summary/text","value":""}]}',
    '{"patches":[{"op":"replace","path":"/sections/0/summary/text","value":1}]}',
    '{"patches":[{"op":"replace","path":"/sections/0/summary/text"}]}',
    '{"patches":[{"op":"replace","path":"/sections/0/summary/text","value":"x","extra":1}]}',
)


@pytest.mark.parametrize("response_text", INVALID_RESPONSES)
def test_malformed_or_schema_invalid_response_is_rejected(repair_inputs, response_text):
    assessor = SequenceAssessor([_completed(_semantic_finding())])
    report = _initial_failure(repair_inputs, assessor)
    client = FakeClient([response_text])

    with pytest.raises(AIReadingRepairV2ProviderResponseError):
        _repair(repair_inputs, report, assessor, client)

    assert len(client.responses.calls) == 1


def test_output_content_fallback_extraction(repair_inputs):
    assessor = SequenceAssessor([_completed(_semantic_finding()), _completed()])
    report = _initial_failure(repair_inputs, assessor)
    client = FakeClient([])
    payload = json.dumps(_patch(), ensure_ascii=False, separators=(",", ":"))

    def create(**kwargs):
        client.responses.calls.append(deepcopy(kwargs))
        return SimpleNamespace(
            output_text=" ",
            output=[SimpleNamespace(content=[SimpleNamespace(text=payload)])],
        )

    client.responses.create = create
    result = _repair(repair_inputs, report, assessor, client)
    assert result.status == "pass"
    assert len(client.responses.calls) == 1


class _HostileString(str):
    def strip(self, *args, **kwargs):
        raise RuntimeError("SECRET_HOSTILE_STRING")


class _HostileList(list):
    def __iter__(self):
        raise RuntimeError("SECRET_HOSTILE_ITERATION")


class _HostileOutputText:
    @property
    def output_text(self):
        raise RuntimeError("SECRET_OUTPUT_TEXT_PROPERTY")


class _HostileNestedText:
    @property
    def text(self):
        raise RuntimeError("SECRET_NESTED_TEXT_PROPERTY")


@pytest.mark.parametrize(
    ("response", "secret"),
    [
        (SimpleNamespace(output_text=_HostileString("payload")), "SECRET_HOSTILE_STRING"),
        (_HostileOutputText(), "SECRET_OUTPUT_TEXT_PROPERTY"),
        (
            SimpleNamespace(output_text=" ", output=_HostileList()),
            "SECRET_HOSTILE_ITERATION",
        ),
        (
            SimpleNamespace(
                output_text=" ",
                output=[SimpleNamespace(content=_HostileList())],
            ),
            "SECRET_HOSTILE_ITERATION",
        ),
        (
            SimpleNamespace(
                output_text=" ",
                output=[SimpleNamespace(content=[_HostileNestedText()])],
            ),
            "SECRET_NESTED_TEXT_PROPERTY",
        ),
    ],
    ids=(
        "hostile-str-subclass",
        "hostile-output-text-property",
        "hostile-output-iteration",
        "hostile-content-iteration",
        "hostile-nested-text-property",
    ),
)
def test_provider_owned_extraction_operations_are_sanitized(
    repair_inputs,
    response,
    secret,
):
    assessor = SequenceAssessor([_completed(_semantic_finding())])
    report = _initial_failure(repair_inputs, assessor)
    client = FakeClient([])

    def create(**kwargs):
        client.responses.calls.append(deepcopy(kwargs))
        return response

    client.responses.create = create

    with pytest.raises(AIReadingRepairV2ProviderResponseError) as caught:
        _repair(repair_inputs, report, assessor, client)

    _assert_public_exception_is_sanitized(caught.value, secret)
    assert len(client.responses.calls) == 1


def test_provider_transport_failure_is_typed_and_not_retried(repair_inputs):
    assessor = SequenceAssessor([_completed(_semantic_finding())])
    report = _initial_failure(repair_inputs, assessor)
    secret = "API_KEY_SECRET raw provider response secret"
    client = FakeClient([RuntimeError(secret)])

    with pytest.raises(AIReadingRepairV2ProviderRequestError) as caught:
        _repair(repair_inputs, report, assessor, client)

    assert len(client.responses.calls) == 1
    _assert_public_exception_is_sanitized(caught.value, secret)
    assert caught.value.attempt == 1
    assert caught.value.issue_codes == ("claim_type_mismatch",)
    assert caught.value.before_hash is not None
    assert caught.value.after_hash is None


@pytest.mark.parametrize(
    ("status_code", "code", "expected_message"),
    [
        (None, None, "repair provider request failed"),
        (400, "invalid_json_schema", "repair provider request failed: schema_rejected"),
        (401, None, "repair provider request failed: authentication_failed"),
        (403, None, "repair provider request failed: authentication_failed"),
        (429, None, "repair provider request failed: rate_limited"),
        (400, None, "repair provider request failed: bad_request"),
        (503, None, "repair provider request failed: unavailable"),
    ],
)
def test_provider_transport_failure_has_safe_fixed_classification(
    repair_inputs,
    status_code,
    code,
    expected_message,
):
    assessor = SequenceAssessor([_completed(_semantic_finding())])
    report = _initial_failure(repair_inputs, assessor)
    secret = "API_KEY_SECRET raw provider body"
    provider_error = RuntimeError(secret)
    if status_code is not None:
        provider_error.status_code = status_code
    if code is not None:
        provider_error.code = code

    with pytest.raises(AIReadingRepairV2ProviderRequestError) as caught:
        _repair(repair_inputs, report, assessor, FakeClient([provider_error]))

    assert str(caught.value) == expected_message
    _assert_public_exception_is_sanitized(caught.value, secret)


@pytest.mark.parametrize(
    ("response_text", "secret"),
    [
        ('{"patches":[SECRET_RAW_RESPONSE', "SECRET_RAW_RESPONSE"),
        (
            '{"patches":[],"secret":"SECRET_SCHEMA_RESPONSE"}',
            "SECRET_SCHEMA_RESPONSE",
        ),
    ],
)
def test_provider_response_failure_retains_no_raw_response_chain(
    repair_inputs, response_text, secret
):
    assessor = SequenceAssessor([_completed(_semantic_finding())])
    report = _initial_failure(repair_inputs, assessor)
    client = FakeClient([response_text])

    with pytest.raises(AIReadingRepairV2ProviderResponseError) as caught:
        _repair(repair_inputs, report, assessor, client)

    _assert_public_exception_is_sanitized(caught.value, secret)
    assert caught.value.attempt == 1
    assert caught.value.issue_codes == ("claim_type_mismatch",)
    assert caught.value.before_hash is not None
    assert caught.value.after_hash is None
    assert len(client.responses.calls) == 1


def test_missing_provider_boundary_is_configuration_error(repair_inputs):
    assessor = SequenceAssessor([_completed(_semantic_finding())])
    report = _initial_failure(repair_inputs, assessor)

    with pytest.raises(AIReadingRepairV2ConfigurationError):
        _repair(repair_inputs, report, assessor, SimpleNamespace())


def test_quality_report_input_identity_mismatch_is_rejected(repair_inputs):
    assessor = SequenceAssessor([_completed(_semantic_finding())])
    report = _initial_failure(repair_inputs, assessor)
    mismatched = deepcopy(repair_inputs)
    mismatched["ai_reading"]["engine_version"] = "different"
    client = FakeClient([_patch()])

    with pytest.raises(AIReadingRepairV2ConfigurationError):
        _repair(mismatched, report, assessor, client)

    assert client.responses.calls == []


def test_final_contract_failure_is_typed_candidate_error(repair_inputs):
    assessor = SequenceAssessor([_completed(_semantic_finding())])
    report = _initial_failure(repair_inputs, assessor)
    invalid = deepcopy(repair_inputs)
    del invalid["ai_reading"]["disclaimer"]
    client = FakeClient([_patch()])

    with pytest.raises(AIReadingRepairV2CandidateValidationError) as caught:
        _repair(invalid, report, assessor, client)

    assert caught.value.attempt == 1
    assert len(client.responses.calls) == 1
    assert assessor.calls == 1


@pytest.mark.parametrize(
    "options",
    [
        {"model": ""},
        {"max_output_tokens": True},
        {"max_output_tokens": 0},
        {"reasoning_effort": "extreme"},
        {"store": 1},
    ],
)
def test_invalid_provider_options_fail_before_call(repair_inputs, options):
    assessor = SequenceAssessor([_completed(_semantic_finding())])
    report = _initial_failure(repair_inputs, assessor)
    client = FakeClient([_patch()])
    kwargs = {
        "semantic_assessor": assessor,
        "client": client,
        "model": "test-model",
    }
    kwargs.update(options)

    with pytest.raises(AIReadingRepairV2ConfigurationError):
        repair_ai_reading_v2(
            repair_inputs["ai_reading"],
            report,
            repair_inputs["reading_context"],
            repair_inputs["judgment_metadata"],
            **kwargs,
        )

    assert client.responses.calls == []


def test_result_and_provider_objects_are_defensively_isolated(repair_inputs):
    assessor = SequenceAssessor([_completed(_semantic_finding()), _completed()])
    report = _initial_failure(repair_inputs, assessor)
    provider_patch = _patch()
    client = FakeClient([provider_patch])
    result = _repair(repair_inputs, report, assessor, client)
    first = result.to_dict()

    provider_patch["patches"][0]["value"] = "外部変更"
    first["final_ai_reading"]["summary"]["text"] = "外部変更"
    first["attempts"][0]["issue_codes"].append("external")
    exposed_ai = result.final_ai_reading
    exposed_ai["summary"]["text"] = "外部変更"
    exposed_report = result.final_quality_report
    exposed_report.input_contracts["ai_reading_v2"]["version"] = "external"

    second = result.to_dict()
    assert second["final_ai_reading"]["summary"]["text"] != "外部変更"
    assert second["attempts"][0]["issue_codes"] == ["claim_type_mismatch"]
    assert result.final_quality_report.input_contracts["ai_reading_v2"]["version"] == "ai_reading_v2"


def test_input_immutability_on_exhausted_and_provider_failure(repair_inputs):
    before = deepcopy(repair_inputs)
    finding = _semantic_finding()
    assessor = SequenceAssessor([_completed(finding)] * 3)
    report = _initial_failure(repair_inputs, assessor)
    report_before = report.to_dict()
    _repair(
        repair_inputs,
        report,
        assessor,
        FakeClient([_patch(value="一回目"), _patch(value="二回目")]),
    )
    assert repair_inputs == before
    assert report.to_dict() == report_before

    failing_assessor = SequenceAssessor([_completed(finding)])
    failing_report = _initial_failure(repair_inputs, failing_assessor)
    with pytest.raises(AIReadingRepairV2ProviderRequestError):
        _repair(
            repair_inputs,
            failing_report,
            failing_assessor,
            FakeClient([RuntimeError("failure")]),
        )
    assert repair_inputs == before


def test_canonical_hash_known_vectors_order_unicode_nested_and_nonfinite():
    left = {"日本語": [1, {"b": True, "a": None}], "z": "値"}
    right = {"z": "値", "日本語": [1, {"a": None, "b": True}]}
    serialized = json.dumps(
        left,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    ).encode("utf-8")
    expected = sha256(serialized).hexdigest()

    assert repair_v2._canonical_hash(left) == expected
    assert repair_v2._canonical_hash(right) == expected
    assert repair_v2._canonical_hash({"value": 1}) != repair_v2._canonical_hash(
        {"value": 2}
    )
    assert len(expected) == 64 and expected == expected.lower()
    with pytest.raises(ValueError):
        repair_v2._canonical_hash({"value": float("nan")})
    with pytest.raises(ValueError):
        repair_v2._canonical_hash({"value": float("inf")})


def test_attempt_log_and_result_accessors_do_not_expose_mutable_snapshots(repair_inputs):
    digest = repair_v2._canonical_hash(repair_inputs["ai_reading"])
    log = RepairAttemptLogV2(
        attempt=1,
        issue_codes=["claim_type_mismatch"],
        before_hash=digest,
        after_hash=digest,
        result="failed",
    )
    assert tuple(log.to_dict()) == ATTEMPT_FIELDS
    values = log.to_dict()
    values["issue_codes"].append("external")
    assert log.issue_codes == ("claim_type_mismatch",)
