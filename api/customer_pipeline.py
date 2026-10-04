"""Application service for the customer-facing v1.2 reading flow.

This module only orchestrates the existing owner contracts.  It does not
calculate astrology, duplicate Quality Gate rules, or alter publication
content.
"""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import contextmanager
import contextvars
from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime
import json
import logging
import os
import time
import uuid
from typing import Any
from zoneinfo import ZoneInfo

from api.models import ChartRequest
from engine.chart import calculate_chart
from engine.consultation_context import MAX_CONCERN_CHARS, build_consultation_context
from engine.judgment_metadata import build_common_judgment_metadata
from engine.reading_context_v2 import build_reading_context_v2
from engine.reading_generator_v2 import (
    DEFAULT_OPENAI_MODEL,
    OPENAI_READING_MODEL_ENV,
    AIReadingGeneratorV2CandidateValidationError,
    AIReadingGeneratorV2ConfigurationError,
    AIReadingGeneratorV2JSONError,
    AIReadingGeneratorV2ProviderError,
    AIReadingGeneratorV2RequestValidationError,
    AIReadingGeneratorV2ResponseError,
    AIReadingGeneratorV2SemanticValidationError,
    AIReadingGeneratorV2StructuralValidationError,
    generate_ai_reading_v2,
)
from engine.reading_product_v2 import (
    ReadingProductV2,
    ReadingProductV2ValidationError,
    build_reading_product_v2,
)
from engine.reading_prompt_v2 import (
    AI_READING_V2_SECTION_SLOTS,
    build_ai_reading_request_v2,
)
from engine.reading_quality_v2 import (
    AIReadingQualityReportV2,
    SemanticAssessorV2,
    evaluate_ai_reading_quality_v2,
)
from engine.reading_repair_v2 import (
    AIReadingRepairV2CandidateValidationError,
    AIReadingRepairV2ConfigurationError,
    AIReadingRepairV2PatchValidationError,
    AIReadingRepairV2ProviderRequestError,
    AIReadingRepairV2ProviderResponseError,
    repair_ai_reading_v2,
)


JST = ZoneInfo("Asia/Tokyo")

_logger = logging.getLogger(__name__)
_performance_trace: contextvars.ContextVar["PerformanceTrace | None"] = (
    contextvars.ContextVar("yakumo_performance_trace", default=None)
)


class PerformanceTrace:
    """Request-scoped timing diagnostics; it never changes pipeline behavior."""

    def __init__(self) -> None:
        self.request_id = uuid.uuid4().hex[:12]
        self.started = time.perf_counter()
        self.provider_calls = 0
        self.auto_repair = False
        self._steps: set[str] = set()
        self._durations: dict[str, float] = {}

    @contextmanager
    def measure(self, step: str, *, executed: bool = True):
        if not executed:
            self.skip(step)
            yield
            return
        started = time.perf_counter()
        status = "ok"
        try:
            yield
        except BaseException:
            status = "error"
            raise
        finally:
            elapsed = time.perf_counter() - started
            self._steps.add(step)
            self._durations[step] = self._durations.get(step, 0.0) + elapsed
            _logger.info(
                "[PERF] request_id=%s step=%s status=%s executed=true elapsed=%.3fs",
                self.request_id, step, status, elapsed,
            )

    def skip(self, step: str) -> None:
        self._steps.add(step)
        _logger.info(
            "[PERF] request_id=%s step=%s status=not_executed executed=false elapsed=0.000s",
            self.request_id, step,
        )

    def provider_call(self) -> None:
        self.provider_calls += 1

    def has_step(self, step: str) -> bool:
        return step in self._steps

    def finish(self, *, status: str) -> None:
        elapsed = time.perf_counter() - self.started
        slowest, slowest_elapsed = (
            max(self._durations.items(), key=lambda item: item[1])
            if self._durations else ("none", 0.0)
        )
        _logger.info(
            "[PERF_SUMMARY] request_id=%s total=%.3fs slowest=%s slowest_elapsed=%.3fs provider_calls=%d auto_repair=%s status=%s",
            self.request_id, elapsed, slowest, slowest_elapsed,
            self.provider_calls, str(self.auto_repair).lower(), status,
        )


class _TimedSemanticAssessor:
    def __init__(self, assessor: Any, trace: PerformanceTrace, count_provider: bool):
        self._assessor = assessor
        self._trace = trace
        self._count_provider = count_provider

    @property
    def method(self):
        return self._assessor.method

    @property
    def version(self):
        return self._assessor.version

    def assess(self, ai_reading, reading_context, judgment_metadata):
        if self._count_provider:
            self._trace.provider_call()
        with self._trace.measure("semantic_assessment"):
            return self._assessor.assess(
                ai_reading, reading_context, judgment_metadata
            )

    def __getattr__(self, name: str):
        return getattr(self._assessor, name)


def set_performance_trace(trace: PerformanceTrace):
    return _performance_trace.set(trace)


def reset_performance_trace(token: contextvars.Token) -> None:
    _performance_trace.reset(token)


def current_performance_trace() -> PerformanceTrace | None:
    return _performance_trace.get()

PREFECTURES = (
    "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
    "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
    "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県",
    "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県",
    "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県",
    "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県",
    "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県",
)

SEMANTIC_ASSESSOR_METHOD = "openai_responses_semantic_assessor_v2"
SEMANTIC_ASSESSOR_VERSION = "v1"
SEMANTIC_ASSESSOR_SCHEMA_NAME = "semantic_assessment_v2"
# Capacity for the single semantic assessment response.  This is a runtime
# transport limit, independent from Generator/AutoRepair limits and policies.
SEMANTIC_ASSESSOR_DEFAULT_MAX_OUTPUT_TOKENS = 12000

_SEMANTIC_CODES = (
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

_SEMANTIC_DIAGNOSTIC_CODES = (
    "semantic_provider_schema_rejected",
    "semantic_provider_authentication_failed",
    "semantic_provider_rate_limited",
    "semantic_provider_bad_request",
    "semantic_provider_unavailable",
    "semantic_provider_request_failed",
    "semantic_provider_response_incomplete_max_output_tokens",
    "semantic_provider_response_incomplete",
    "semantic_provider_response_refused",
    "semantic_provider_response_not_completed",
    "semantic_provider_response_invalid",
    "semantic_result_finding_path_invalid",
    "semantic_result_evidence_missing",
    "semantic_result_evidence_path_invalid",
    "semantic_assessment_inconclusive",
)

_SEMANTIC_INSTRUCTIONS = (
    "あなたは八雲式四柱推命エンジンのQuality Gate v2意味評価器です。"
    "入力されたAIReadingV2を、ReadingContextV2とCommon Judgment Metadata v1だけを"
    "根拠に検査してください。占術を再計算せず、新しい占術値や判断を作らず、"
    "文章を書き換えないでください。問題がなければcompletedと空のfindingsを返します。"
    "問題がある場合は許可されたcode、AIReadingV2上のRFC6901 path、"
    "根拠ownerとRFC6901 pathだけを返してください。厳密なJSON以外を返さないでください。"
    "codeの意味は次のとおりです。"
    "claim_type_mismatch=claim_typeと本文意味の不一致。"
    "fact_semantic_mismatch=source_fact_codesが占術主張を意味的に支持しない。"
    "component_semantic_mismatch=source_componentsとcertainty/provenance表現の不整合。"
    "luck_semantic_mismatch=luck_astrology本文とtrusted luck sourceの不整合。"
    "engine_value_contradiction=本文とengine確定値またはlabelの矛盾。"
    "judgment_status_wording_violation=canonical judgment statusに反する確度表現。"
    "unknown_hour_derived_claim=出生時刻不明なのにhour由来の主張がある。"
    "missing_applicable_uncertainty=適用すべきuncertaintyが本文または参照にない。"
    "unsupported_numeric_claim=本文の数値をtrusted sourceで確認できない。"
    "consultation_astrology_leak=相談内容から新しい占術判断を生成している。"
    "prohibited_claim=医療・法律・投資の断定、将来保証、不安煽り等。"
    "overconfident_wording=過度に断定的な表現。"
    "evidence_interpretation_advice_confusion=evidence/interpretation/adviceの役割混同。"
    "astrology_wording_ambiguity=占術根拠または確度表現の曖昧さ。"
    "source_limitation_note=source limitationが適切に開示されている箇所。"
    "findingのpathは入力ai_reading内に実在する値を指すRFC6901 JSON Pointerに限定します。"
    "section_idをpath segmentに使わず、sections配列の固定indexを使用してください。"
    "index対応はcore_personality=0、career=1、wealth=2、relationships=3、health=4、"
    "current_luck=5、future_flow=6、advice=7です。"
    "top-level summaryは/summary、相談回答は/consultation_answer、各sectionのblockは"
    "/sections/{index}/summary、/sections/{index}/detail、"
    "/sections/{index}/evidence/{item_index}、/sections/{index}/interpretation/{item_index}、"
    "/sections/{index}/advice/{item_index}を使用します。future_flowの年次blockは"
    "/sections/6/yearly/{year_index}/summaryまたは/sections/6/yearly/{year_index}/detailであり、"
    "/future_flow_yearlyや/sections/future_flowなどのpathを作ってはいけません。"
    "pathは出力前に入力JSONを実際に辿って存在を確認してください。"
    "claim_type_mismatchは、1つのgrounded_text_blockで宣言されたclaim_typeとそのblockの"
    "textの意味が一致しない場合だけ宣言します。具体例があることだけを理由にせず、"
    "占術・luckの主張か一般的なpractical助言かをblock単位で判定してください。"
    "各findingには少なくとも1件、実在するowner pathをevidenceとして付けてください。"
    "evidence pathも該当source_contractの入力JSONからexact keyとarray indexを辿ってコピーし、"
    "dot notation、section_id名による代用、存在しない短縮pathを使用してはいけません。"
)


_SEMANTIC_INSTRUCTIONS += " long_term_luck paths use /long_term_luck/{index}/{field} or /long_term_luck/{index}/advice/{advice_index}; use luck_astrology with matching trusted luck_pillars only."
_SEMANTIC_INSTRUCTIONS += " For relationships evidence or interpretation grounded in branch-relation facts, the expected component is relations; relationships is only the AI section name, never a source component, and mixed provenance is invalid."
_SEMANTIC_INSTRUCTIONS += " The corresponding existing fact reference is chart.pillar_sequence; reject missing or invented relation fact references."


class CustomerInputError(ValueError):
    """Customer-submitted values are invalid."""

    def __init__(self, errors: Mapping[str, str]) -> None:
        self.errors = dict(errors)
        super().__init__("customer input is invalid")


class CustomerConfigurationError(RuntimeError):
    """The application cannot initialize its configured provider."""

    def __init__(self, message: str, *, reason_code: str = "configuration_invalid") -> None:
        self.stage = "configuration"
        self.reason_code = reason_code
        super().__init__(message)


class CustomerReadingUnavailableError(RuntimeError):
    """A reading could not reach the frozen publication gate."""

    def __init__(
        self,
        message: str,
        *,
        stage: str = "pipeline",
        reason_code: str = "reading_unavailable",
        decision: str | None = None,
        blocking_codes: tuple[str, ...] = (),
        diagnostic_codes: tuple[str, ...] = (),
        diagnostic_locations: tuple[str, ...] = (),
    ) -> None:
        self.stage = stage
        self.reason_code = reason_code
        self.decision = decision
        self.blocking_codes = tuple(blocking_codes)
        if diagnostic_codes or diagnostic_locations:
            self.diagnostic_codes = tuple(diagnostic_codes)
            self.diagnostic_locations = tuple(diagnostic_locations)
        super().__init__(message)


class SemanticAssessmentProviderError(RuntimeError):
    """The external semantic assessment failed without exposing provider data."""


@dataclass(frozen=True)
class CustomerReadingInput:
    birth_date: str
    birth_time: str | None
    birth_place: str
    gender: str
    consultation: str


def _single_text(values: Mapping[str, Any], field: str) -> str:
    value = values.get(field, "")
    return value if type(value) is str else ""


def validate_customer_input(values: Mapping[str, Any]) -> CustomerReadingInput:
    """Validate browser fields and map them to the existing chart contract."""

    birth_date = _single_text(values, "birth_date").strip()
    birth_place = _single_text(values, "birth_place").strip()
    gender = _single_text(values, "gender").strip()
    hour = _single_text(values, "birth_hour").strip()
    minute = _single_text(values, "birth_minute").strip()
    unknown = _single_text(values, "birth_time_unknown") == "1"
    consultation = _single_text(values, "consultation").strip()
    errors: dict[str, str] = {}

    if not birth_date:
        errors["birth_date"] = "生年月日を入力してください。"
    else:
        try:
            parsed_date = date.fromisoformat(birth_date)
        except ValueError:
            errors["birth_date"] = "実在する生年月日を入力してください。"
        else:
            if parsed_date > date.today():
                errors["birth_date"] = "未来の日付は指定できません。"

    if birth_place not in PREFECTURES:
        errors["birth_place"] = "出生地を都道府県から選択してください。"
    if gender not in ("male", "female"):
        errors["gender"] = "性別を選択してください。"

    birth_time: str | None
    if unknown:
        if hour or minute:
            errors["birth_time"] = (
                "出生時刻不明を選んだ場合は、時刻を指定しないでください。"
            )
        birth_time = None
    else:
        if not hour or not minute:
            errors["birth_time"] = (
                "出生時刻を入力するか、出生時刻不明を選択してください。"
            )
            birth_time = None
        elif not hour.isascii() or not hour.isdecimal() or not minute.isascii() or not minute.isdecimal():
            errors["birth_time"] = "出生時刻を正しく入力してください。"
            birth_time = None
        else:
            hour_value = int(hour)
            minute_value = int(minute)
            if hour_value not in range(24) or minute_value not in range(60):
                errors["birth_time"] = "出生時刻を正しく入力してください。"
                birth_time = None
            else:
                birth_time = f"{hour_value:02d}:{minute_value:02d}"

    if len(consultation) > MAX_CONCERN_CHARS:
        errors["consultation"] = (
            f"相談内容は{MAX_CONCERN_CHARS}文字以内で入力してください。"
        )
    if errors:
        raise CustomerInputError(errors)
    return CustomerReadingInput(
        birth_date=birth_date,
        birth_time=birth_time,
        birth_place=birth_place,
        gender=gender,
        consultation=consultation,
    )


def build_customer_chart_request(value: CustomerReadingInput) -> ChartRequest:
    if not isinstance(value, CustomerReadingInput):
        raise TypeError("value must be CustomerReadingInput")
    return ChartRequest(
        birth_date=value.birth_date,
        birth_time=value.birth_time,
        birth_place=value.birth_place,
        gender=value.gender,
    )


def configured_model() -> str:
    value = os.getenv(OPENAI_READING_MODEL_ENV)
    return value.strip() if value and value.strip() else DEFAULT_OPENAI_MODEL


def create_customer_provider_client() -> Any:
    """Create one explicit Responses client without exposing configuration data."""

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not api_key.strip():
        raise CustomerConfigurationError(
            "鑑定サービスの接続設定が完了していません。",
            reason_code="openai_api_key_missing",
        )
    sdk_available = True
    try:
        from openai import OpenAI
    except ImportError:
        sdk_available = False
        OpenAI = None  # type: ignore[assignment,misc]
    if not sdk_available:
        raise CustomerConfigurationError(
            "鑑定サービスを初期化できませんでした。",
            reason_code="openai_sdk_unavailable",
        )
    failed = False
    client: Any = None
    try:
        client = OpenAI(api_key=api_key.strip())  # type: ignore[misc]
    except Exception:
        failed = True
    if failed:
        raise CustomerConfigurationError(
            "鑑定サービスを初期化できませんでした。",
            reason_code="openai_client_initialization_failed",
        )
    return client


def _json_pointer_paths(value: Any, prefix: str = "") -> list[str]:
    """Return existing RFC6901 paths only; never synthesize provider paths."""
    paths = [prefix or ""]
    if isinstance(value, Mapping):
        for key, item in value.items():
            escaped = str(key).replace("~", "~0").replace("/", "~1")
            paths.extend(_json_pointer_paths(item, f"{prefix}/{escaped}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            paths.extend(_json_pointer_paths(item, f"{prefix}/{index}"))
    return paths


def _json_leaf_paths(value: Any, prefix: str = "") -> list[str]:
    if isinstance(value, Mapping):
        return [path for key, item in value.items()
                for path in _json_leaf_paths(item, f"{prefix}/{str(key).replace('~', '~0').replace('/', '~1')}")]
    if isinstance(value, list):
        return [path for index, item in enumerate(value)
                for path in _json_leaf_paths(item, f"{prefix}/{index}")]
    return [prefix or ""]


def _grounded_block_paths(
    value: Any,
    prefix: str = "",
    *,
    include_evidence: bool = True,
) -> list[str]:
    if isinstance(value, Mapping):
        if "text" in value and "claim_type" in value:
            return [prefix or ""]
        return [path for key, item in value.items()
                for path in _grounded_block_paths(
                    item,
                    f"{prefix}/{str(key).replace('~', '~0').replace('/', '~1')}",
                    include_evidence=include_evidence,
                )
                if include_evidence or key != "evidence"]
    if isinstance(value, list):
        return [path for index, item in enumerate(value)
                for path in _grounded_block_paths(
                    item, f"{prefix}/{index}", include_evidence=include_evidence
                )]
    return []


def _semantic_reference_catalog(
    ai_reading: Mapping[str, Any],
    reading_context: Mapping[str, Any],
    judgment_metadata: Mapping[str, Any],
) -> dict[str, Any]:
    sources = {
        "ai_reading_v2": ai_reading,
        "reading_context_v2": reading_context,
        "common_judgment_metadata_v1": judgment_metadata,
    }
    # Evidence blocks carry provenance for their containing claim. They remain
    # valid evidence-source paths, but are not independent assessor claims.
    finding_paths = _grounded_block_paths(ai_reading, include_evidence=False)
    evidence = []
    counter = 0
    for contract, value in sources.items():
        if contract == "ai_reading_v2":
            paths = _grounded_block_paths(value)
        elif contract == "reading_context_v2":
            paths = [
                "/" + str(item["context_path"]).replace(".", "/").replace("[", "/").replace("]", "")
                for item in value.get("facts", [])
                if isinstance(item, Mapping) and isinstance(item.get("context_path"), str)
            ]
            luck = value.get("luck", {})
            if isinstance(luck, Mapping):
                paths.extend(f"/luck/{key}" for key in luck if key != "five_year_luck")
                yearly = luck.get("five_year_luck", [])
                if isinstance(yearly, list):
                    paths.extend(f"/luck/five_year_luck/{index}" for index, _ in enumerate(yearly))
        else:
            components = value.get("components", {}) if isinstance(value, Mapping) else {}
            paths = [f"/components/{key}" for key in components]
        for path in paths:
            evidence.append({"id": f"e_{counter:04d}", "source_contract": contract, "path": path})
            counter += 1
    return {
        "finding_refs": [
            {"id": f"f_{index:04d}", "path": path}
            for index, path in enumerate(finding_paths)
        ],
        "evidence_refs": evidence,
    }


def _semantic_claim_contract_catalog(ai_reading: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Describe the already-decoded claim contract without exposing prose.

    The assessor receives the complete reading as input, but the distinction
    between a short customer-facing title and a detailed luck interpretation
    is otherwise implicit.  Supplying this deterministic, metadata-only
    catalogue prevents the provider from applying the detail-level contract
    to titles (or treating provenance metadata as a second claim).  It does
    not alter validation: the returned claim and evidence are still checked
    by the existing semantic and local validators.
    """
    contracts: list[dict[str, Any]] = []

    def add(path: str, block: Any, role: str) -> None:
        if not isinstance(block, Mapping) or "text" not in block:
            return
        contracts.append(
            {
                "path": path,
                "role": role,
                "claim_type": block.get("claim_type"),
                "source_components": list(block.get("source_components", [])),
                "source_fact_codes": list(block.get("source_fact_codes", [])),
            }
        )

    add("/summary", ai_reading.get("summary"), "overall_summary")
    sections = ai_reading.get("sections", [])
    if isinstance(sections, list):
        for index, section in enumerate(sections):
            if not isinstance(section, Mapping):
                continue
            for field in ("summary", "detail"):
                add(f"/sections/{index}/{field}", section.get(field), field)
            for field in ("evidence", "interpretation", "advice"):
                if field == "evidence":
                    continue
                values = section.get(field, [])
                if isinstance(values, list):
                    for item_index, block in enumerate(values):
                        add(f"/sections/{index}/{field}/{item_index}", block, field)
            if index == 6:
                yearly = section.get("yearly", [])
                if isinstance(yearly, list):
                    for year_index, entry in enumerate(yearly):
                        if not isinstance(entry, Mapping):
                            continue
                        for field in (
                            "title", "theme", "career", "wealth", "relationships",
                            "caution", "summary", "detail",
                        ):
                            add(
                                f"/sections/{index}/yearly/{year_index}/{field}",
                                entry.get(field),
                                "yearly_title" if field == "title" else "yearly_detail",
                            )
                        for advice_index, block in enumerate(entry.get("advice", [])):
                            add(
                                f"/sections/{index}/yearly/{year_index}/advice/{advice_index}",
                                block,
                                "yearly_advice",
                            )
    long_term = ai_reading.get("long_term_luck", [])
    if isinstance(long_term, list):
        for index, detail in enumerate(long_term):
            if not isinstance(detail, Mapping):
                continue
            for field in ("title", "theme", "career", "wealth", "relationships", "caution"):
                add(
                    f"/long_term_luck/{index}/{field}",
                    detail.get(field),
                    "long_term_title" if field == "title" else "long_term_detail",
                )
            for advice_index, block in enumerate(detail.get("advice", [])):
                add(
                    f"/long_term_luck/{index}/advice/{advice_index}",
                    block,
                    "long_term_advice",
                )
    consultation = ai_reading.get("consultation_answer")
    if consultation is not None:
        add("/consultation_answer", consultation, "consultation_answer")
    return contracts


def _semantic_schema(
    ai_reading: Mapping[str, Any] | None = None,
    reading_context: Mapping[str, Any] | None = None,
    judgment_metadata: Mapping[str, Any] | None = None,
    reference_catalog: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    ai_paths = _json_pointer_paths(ai_reading) if ai_reading is not None else None
    source_values = {
        "ai_reading_v2": ai_reading,
        "reading_context_v2": reading_context,
        "common_judgment_metadata_v1": judgment_metadata,
    }
    evidence_paths = None
    if any(value is not None for value in source_values.values()):
        evidence_paths = sorted({
            path
            for value in source_values.values()
            if value is not None
            for path in _json_pointer_paths(value)
        })
    finding_refs = [item["id"] for item in (reference_catalog or {}).get("finding_refs", [])]
    evidence_refs = [item["id"] for item in (reference_catalog or {}).get("evidence_refs", [])]
    return {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["completed", "inconclusive"]},
            "findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "enum": list(_SEMANTIC_CODES)},
                        "path": ({"type": "string", "enum": finding_refs}
                                 if finding_refs else ({"type": "string", "enum": ai_paths}
                                 if ai_paths else {"type": "string"})),
                        "evidence": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "source_contract": {
                                        "type": "string",
                                        "enum": [
                                            "ai_reading_v2",
                                            "reading_context_v2",
                                            "common_judgment_metadata_v1",
                                        ],
                                    },
                                    "path": ({"type": "string", "enum": evidence_refs}
                                             if evidence_refs else ({"type": "string", "enum": evidence_paths}
                                             if evidence_paths else {"type": "string"})),
                                },
                                "required": ["source_contract", "path"],
                                "additionalProperties": False,
                            },
                        },
                    },
                    "required": ["code", "path", "evidence"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["status", "findings"],
        "additionalProperties": False,
    }


def _pairs_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON member")
        result[key] = value
    return result


def _reject_json_constant(_value: str) -> None:
    raise ValueError("non-finite JSON number")


def _extract_provider_text(response: Any) -> str:
    """Extract only built-in response text types from an untrusted provider object."""

    direct = getattr(response, "output_text", None)
    if type(direct) is str and direct.strip():
        return direct.strip()
    output = getattr(response, "output", None)
    if type(output) not in (list, tuple):
        raise ValueError("provider output is unavailable")
    parts: list[str] = []
    for item in output:
        content = item.get("content") if type(item) is dict else getattr(item, "content", None)
        if type(content) not in (list, tuple):
            continue
        for entry in content:
            text = entry.get("text") if type(entry) is dict else getattr(entry, "text", None)
            if type(text) is str and text.strip():
                parts.append(text.strip())
    if not parts:
        raise ValueError("provider output is unavailable")
    return "\n".join(parts)


def _parse_semantic_result(text: str) -> dict[str, Any]:
    value = json.loads(
        text,
        object_pairs_hook=_pairs_without_duplicates,
        parse_constant=_reject_json_constant,
    )
    if type(value) is not dict or tuple(value) != ("status", "findings"):
        raise ValueError("semantic result shape is invalid")
    if type(value["status"]) is not str or value["status"] not in ("completed", "inconclusive"):
        raise ValueError("semantic status is invalid")
    if type(value["findings"]) is not list:
        raise ValueError("semantic findings are invalid")
    for finding in value["findings"]:
        if type(finding) is not dict or tuple(finding) != ("code", "path", "evidence"):
            raise ValueError("semantic finding shape is invalid")
        if type(finding["code"]) is not str or finding["code"] not in _SEMANTIC_CODES:
            raise ValueError("semantic finding code is invalid")
        if type(finding["path"]) is not str or type(finding["evidence"]) is not list:
            raise ValueError("semantic finding value is invalid")
        for evidence in finding["evidence"]:
            if type(evidence) is not dict or tuple(evidence) != ("source_contract", "path"):
                raise ValueError("semantic evidence shape is invalid")
            if type(evidence["source_contract"]) is not str or type(evidence["path"]) is not str:
                raise ValueError("semantic evidence value is invalid")
    return value


def _provider_field(value: Any, name: str, default: Any = None) -> Any:
    return value.get(name, default) if type(value) is dict else getattr(value, name, default)


def _semantic_provider_request_diagnostic(error: Exception) -> str:
    """Classify provider transport metadata without retaining provider data."""

    try:
        code = getattr(error, "code", None)
        if type(code) is not str:
            body = getattr(error, "body", None)
            if type(body) is dict:
                nested = body.get("error")
                code = nested.get("code") if type(nested) is dict else body.get("code")
        if code == "invalid_json_schema":
            return "semantic_provider_schema_rejected"
        status_code = getattr(error, "status_code", None)
        if type(status_code) is int:
            if status_code in {401, 403}:
                return "semantic_provider_authentication_failed"
            if status_code == 429:
                return "semantic_provider_rate_limited"
            if status_code == 400:
                return "semantic_provider_bad_request"
            if status_code >= 500:
                return "semantic_provider_unavailable"
    except Exception:
        pass
    return "semantic_provider_request_failed"


def _semantic_provider_response_diagnostic(response: Any) -> str | None:
    """Return a fixed code for non-completed Responses API states."""

    status = _provider_field(response, "status")
    if status == "incomplete":
        details = _provider_field(response, "incomplete_details")
        reason = _provider_field(details, "reason") if details is not None else None
        if reason == "max_output_tokens":
            return "semantic_provider_response_incomplete_max_output_tokens"
        return "semantic_provider_response_incomplete"
    if type(status) is str and status != "completed":
        return "semantic_provider_response_not_completed"
    output = _provider_field(response, "output", [])
    if type(output) not in (list, tuple):
        return None
    for item in output:
        content = _provider_field(item, "content", [])
        if type(content) not in (list, tuple):
            continue
        for content_item in content:
            if _provider_field(content_item, "type") == "refusal":
                return "semantic_provider_response_refused"
    return None


def _pointer_resolves(value: Any, pointer: str) -> bool:
    if type(pointer) is not str or (pointer and not pointer.startswith("/")):
        return False
    current = value
    if pointer == "":
        return True
    for raw_segment in pointer[1:].split("/"):
        segment = raw_segment.replace("~1", "/").replace("~0", "~")
        if type(current) is dict:
            if segment not in current:
                return False
            current = current[segment]
        elif type(current) is list:
            if not segment.isascii() or not segment.isdigit():
                return False
            index = int(segment)
            if index >= len(current):
                return False
            current = current[index]
        else:
            return False
    return True


def _semantic_location(path: str, ai_reading: Mapping[str, Any]) -> str | None:
    """Project an RFC6901 path to an allowlisted, non-content location."""

    if type(path) is not str or not path.startswith("/") or "~" in path:
        return None
    segments = path[1:].split("/")
    if segments[0] in {"summary", "consultation_answer"}:
        return segments[0]
    if segments[0] in {"warnings", "uncertainty"}:
        if len(segments) >= 2 and segments[1].isascii() and segments[1].isdigit():
            return f"{segments[0]}[{int(segments[1])}]"
        return segments[0]
    if len(segments) >= 3 and segments[0] == "future_flow_yearly":
        if not segments[1].isascii() or not segments[1].isdigit():
            return None
        if segments[2] not in {"summary", "detail"}:
            return None
        return f"future_flow_yearly[{int(segments[1])}].{segments[2]}"
    if len(segments) >= 3 and segments[0] == "long_term_luck":
        if not segments[1].isascii() or not segments[1].isdigit():
            return None
        if segments[2] in {"title", "theme", "career", "wealth", "relationships", "caution"}:
            return f"long_term_luck[{int(segments[1])}].{segments[2]}"
        if segments[2] == "advice" and len(segments) >= 4 and segments[3].isascii() and segments[3].isdigit():
            return f"long_term_luck[{int(segments[1])}].advice[{int(segments[3])}]"
        return None
    if len(segments) < 3 or segments[0] != "sections":
        return None
    sections = ai_reading.get("sections")
    section_ids = {slot[0] for slot in AI_READING_V2_SECTION_SLOTS}
    if segments[1].isascii() and segments[1].isdigit():
        index = int(segments[1])
        if type(sections) is not list or not 0 <= index < len(sections):
            return None
        section = sections[index]
        if type(section) is not dict or type(section.get("section_id")) is not str:
            return None
        section_id = section["section_id"]
    elif segments[1] in section_ids:
        # Diagnostic-only projection for a provider's invalid named-section pointer.
        # The pointer remains invalid and is rejected by the Quality Gate.
        section_id = segments[1]
    else:
        return None
    if section_id not in section_ids:
        return None
    field = segments[2]
    if field in {"summary", "detail"}:
        return f"{section_id}.{field}"
    if field not in {"evidence", "interpretation", "advice"}:
        return None
    if len(segments) < 4 or not segments[3].isascii() or not segments[3].isdigit():
        return f"{section_id}.{field}"
    return f"{section_id}.{field}[{int(segments[3])}]"


def _semantic_result_diagnostics(
    result: Mapping[str, Any],
    ai_reading: Mapping[str, Any],
    reading_context: Mapping[str, Any],
    judgment_metadata: Mapping[str, Any],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    codes: list[str] = []
    locations: list[str] = []
    sources = {
        "ai_reading_v2": ai_reading,
        "reading_context_v2": reading_context,
        "common_judgment_metadata_v1": judgment_metadata,
    }
    if result.get("status") == "inconclusive":
        codes.append("semantic_assessment_inconclusive")
    for finding in result.get("findings", []):
        code = finding["code"]
        path = finding["path"]
        if code not in codes:
            codes.append(code)
        location = _semantic_location(path, ai_reading)
        if location is not None and location not in locations:
            locations.append(location)
        if not _pointer_resolves(ai_reading, path):
            if "semantic_result_finding_path_invalid" not in codes:
                codes.append("semantic_result_finding_path_invalid")
        evidence = finding["evidence"]
        if not evidence:
            if "semantic_result_evidence_missing" not in codes:
                codes.append("semantic_result_evidence_missing")
        elif any(
            evidence_item["source_contract"] not in sources
            or not _pointer_resolves(
                sources.get(evidence_item["source_contract"]),
                evidence_item["path"],
            )
            for evidence_item in evidence
        ):
            if "semantic_result_evidence_path_invalid" not in codes:
                codes.append("semantic_result_evidence_path_invalid")
    return tuple(codes), tuple(locations)


class OpenAISemanticAssessorV2(SemanticAssessorV2):
    """One-call Responses adapter for the frozen semantic assessor Protocol."""

    def __init__(self, *, client: Any, model: str) -> None:
        if type(model) is not str or not model.strip():
            raise CustomerConfigurationError(
                "鑑定サービスのモデル設定が不正です。",
                reason_code="model_invalid",
            )
        responses = getattr(client, "responses", None)
        create = getattr(responses, "create", None)
        if not callable(create):
            raise CustomerConfigurationError(
                "鑑定サービスを初期化できませんでした。",
                reason_code="responses_api_unavailable",
            )
        self._create = create
        self._model = model.strip()
        self._diagnostic_codes: tuple[str, ...] = ()
        self._diagnostic_locations: tuple[str, ...] = ()

    @property
    def method(self) -> str:
        return SEMANTIC_ASSESSOR_METHOD

    @property
    def version(self) -> str:
        return SEMANTIC_ASSESSOR_VERSION

    @property
    def diagnostic_codes(self) -> tuple[str, ...]:
        return self._diagnostic_codes

    @property
    def diagnostic_locations(self) -> tuple[str, ...]:
        return self._diagnostic_locations

    def assess(
        self,
        ai_reading: Mapping[str, Any],
        reading_context: Mapping[str, Any],
        judgment_metadata: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        self._diagnostic_codes = ()
        self._diagnostic_locations = ()
        model_input = {
            "ai_reading": deepcopy(dict(ai_reading)),
            "reading_context": deepcopy(dict(reading_context)),
            "judgment_metadata": deepcopy(dict(judgment_metadata)),
        }
        content = json.dumps(
            model_input,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=False,
            allow_nan=False,
        )
        reference_catalog = _semantic_reference_catalog(
            ai_reading, reading_context, judgment_metadata
        )
        finding_map = {item["id"]: item["path"] for item in reference_catalog["finding_refs"]}
        evidence_map = {
            (item["source_contract"], item["id"]): item["path"]
            for item in reference_catalog["evidence_refs"]
        }
        instructions = (
            _SEMANTIC_INSTRUCTIONS
            + "\nUse only these deterministic reference identifiers; do not emit RFC6901 paths directly:"
            + json.dumps(reference_catalog, ensure_ascii=False, separators=(",", ":"))
            + "\nUse this metadata-only claim contract catalogue when judging scope:"
            + json.dumps(
                _semantic_claim_contract_catalog(ai_reading),
                ensure_ascii=False,
                separators=(",", ":"),
            )
            + "\nA long_term_title is a concise customer-facing summary of its bound luck pillar;"
            + " assess it for semantic coherence with that pillar at summary level, not literal"
            + " keyword overlap with the detailed luck fields. Evidence entries are provenance"
            + " for their containing customer claim unless they themselves have a text block path;"
            + " never invent a second claim from metadata alone."
        )
        payload = {
            "model": self._model,
            "instructions": instructions,
            "input": [{"role": "user", "content": content}],
            "max_output_tokens": SEMANTIC_ASSESSOR_DEFAULT_MAX_OUTPUT_TOKENS,
            "reasoning": {"effort": "low"},
            "store": False,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": SEMANTIC_ASSESSOR_SCHEMA_NAME,
                    "schema": _semantic_schema(
                        ai_reading, reading_context, judgment_metadata, reference_catalog
                    ),
                    "strict": True,
                }
            },
        }
        failure_code: str | None = None
        response: Any = None
        try:
            response = self._create(**deepcopy(payload))
        except Exception as exc:
            failure_code = _semantic_provider_request_diagnostic(exc)
        if failure_code is not None:
            self._diagnostic_codes = (failure_code,)
            raise SemanticAssessmentProviderError(
                "semantic assessment provider request failed"
            )
        response_failure_code: str | None = None
        result: dict[str, Any] | None = None
        try:
            response_failure_code = _semantic_provider_response_diagnostic(response)
            if response_failure_code is None:
                result = _parse_semantic_result(_extract_provider_text(response))
        except Exception:
            response_failure_code = "semantic_provider_response_invalid"
        response = None
        if response_failure_code is not None or result is None:
            self._diagnostic_codes = (
                response_failure_code or "semantic_provider_response_invalid",
            )
            raise SemanticAssessmentProviderError(
                "semantic assessment provider response is invalid"
            )
        for finding in result.get("findings", []):
            finding["path"] = finding_map.get(finding["path"], finding["path"])
            for evidence in finding.get("evidence", []):
                evidence["path"] = evidence_map.get(
                    (evidence["source_contract"], evidence["path"]), evidence["path"]
                )
        (
            self._diagnostic_codes,
            self._diagnostic_locations,
        ) = _semantic_result_diagnostics(
            result,
            ai_reading,
            reading_context,
            judgment_metadata,
        )
        return deepcopy(result)


def _eligible_for_auto_repair(report: AIReadingQualityReportV2) -> bool:
    blocking = tuple(finding for finding in report.findings if finding.blocking)
    return (
        report.decision == "fail"
        and bool(blocking)
        and all(finding.repairability == "auto" for finding in blocking)
    )


def _blocking_codes(report: AIReadingQualityReportV2) -> tuple[str, ...]:
    """Return only frozen catalog codes; never evidence, paths, or provider data."""
    return tuple(finding.code for finding in report.findings if finding.blocking)


def _is_safe_semantic_location(value: str) -> bool:
    if value in {"summary", "consultation_answer", "warnings", "uncertainty"}:
        return True
    for catalog in ("warnings", "uncertainty"):
        prefix = f"{catalog}["
        if value.startswith(prefix) and value.endswith("]"):
            index = value[len(prefix):-1]
            return bool(index) and index.isascii() and index.isdigit()
    yearly_prefix = "future_flow_yearly["
    if value.startswith(yearly_prefix):
        index, separator, field = value[len(yearly_prefix):].partition("].")
        return (
            separator == "]."
            and bool(index)
            and index.isascii()
            and index.isdigit()
            and field in {"summary", "detail"}
        )
    long_term_prefix = "long_term_luck["
    if value.startswith(long_term_prefix):
        index, separator, field = value[len(long_term_prefix):].partition("].")
        if separator != "]." or not index or not index.isascii() or not index.isdigit():
            return False
        if field in {"title", "theme", "career", "wealth", "relationships", "caution"}:
            return True
        base, bracket, advice_index = field.partition("[")
        return base == "advice" and bracket == "[" and advice_index.endswith("]") and advice_index[:-1].isdigit()
    section_ids = {slot[0] for slot in AI_READING_V2_SECTION_SLOTS}
    section_id, separator, field = value.partition(".")
    if separator != "." or section_id not in section_ids:
        return False
    if field in {"summary", "detail", "evidence", "interpretation", "advice"}:
        return True
    base_field, bracket, index = field.partition("[")
    return (
        bracket == "["
        and base_field in {"evidence", "interpretation", "advice"}
        and index.endswith("]")
        and bool(index[:-1])
        and index[:-1].isascii()
        and index[:-1].isdigit()
    )


def _semantic_assessor_diagnostics(
    semantic_assessor: SemanticAssessorV2,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Read only fixed allowlisted diagnostics; never provider-owned values."""

    try:
        raw_codes = semantic_assessor.diagnostic_codes
        raw_locations = semantic_assessor.diagnostic_locations
    except Exception:
        return (), ()
    allowed_codes = set(_SEMANTIC_CODES) | set(_SEMANTIC_DIAGNOSTIC_CODES)
    codes = tuple(
        code
        for code in raw_codes
        if type(code) is str and code in allowed_codes
    ) if type(raw_codes) is tuple else ()
    locations = tuple(
        location
        for location in raw_locations
        if type(location) is str and _is_safe_semantic_location(location)
    ) if type(raw_locations) is tuple else ()
    return tuple(dict.fromkeys(codes)), tuple(dict.fromkeys(locations))


def _generator_provider_reason(error: AIReadingGeneratorV2ProviderError) -> str:
    """Classify a provider failure without retaining or rendering provider data."""

    reason = "generator_provider_request_failed"
    try:
        provider_error = error.__cause__
        if provider_error is None:
            return reason
        code = getattr(provider_error, "code", None)
        if type(code) is not str:
            body = getattr(provider_error, "body", None)
            if type(body) is dict:
                nested = body.get("error")
                if type(nested) is dict:
                    code = nested.get("code")
                else:
                    code = body.get("code")
        if type(code) is str and code == "invalid_json_schema":
            return "generator_provider_schema_rejected"
        status_code = getattr(provider_error, "status_code", None)
        if type(status_code) is int:
            if status_code in {401, 403}:
                return "generator_provider_authentication_failed"
            if status_code == 429:
                return "generator_provider_rate_limited"
            if status_code == 400:
                return "generator_provider_bad_request"
            if status_code >= 500:
                return "generator_provider_unavailable"
    except Exception:
        return reason
    return reason


def _generator_response_reason(error: AIReadingGeneratorV2ResponseError) -> str:
    safe_message = str(error)
    if safe_message == "provider response is incomplete: max_output_tokens":
        return "generator_response_incomplete_max_output_tokens"
    if safe_message == "provider response is incomplete":
        return "generator_response_incomplete"
    if safe_message == "provider response contains a refusal":
        return "generator_response_refused"
    if safe_message == "provider response is not completed":
        return "generator_response_not_completed"
    return "generator_provider_response_invalid"


def _repair_provider_reason(error: AIReadingRepairV2ProviderRequestError) -> str:
    """Map sanitized repair errors without inspecting provider-owned data."""

    return {
        "repair provider request failed: schema_rejected": (
            "repair_provider_schema_rejected"
        ),
        "repair provider request failed: authentication_failed": (
            "repair_provider_authentication_failed"
        ),
        "repair provider request failed: rate_limited": (
            "repair_provider_rate_limited"
        ),
        "repair provider request failed: bad_request": (
            "repair_provider_bad_request"
        ),
        "repair provider request failed: unavailable": (
            "repair_provider_unavailable"
        ),
    }.get(str(error), "repair_provider_request_failed")


def _generator_semantic_diagnostics(
    error: AIReadingGeneratorV2SemanticValidationError,
    request: Mapping[str, Any],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    patterns = (
        ("unknown fact", "unknown_fact_reference"),
        ("unknown component", "unknown_component_reference"),
        ("unknown warning ID", "unknown_warning_reference"),
        ("unknown uncertainty ID", "unknown_uncertainty_reference"),
        ("is forbidden at this location", "claim_type_forbidden_at_location"),
        ("practical blocks require empty", "practical_has_grounding_references"),
        ("astrology blocks require at least one fact ref", "astrology_missing_fact_reference"),
        ("astrology blocks cannot use luck components", "astrology_has_luck_component"),
        ("luck_astrology blocks require at least one luck component", "luck_astrology_missing_luck_component"),
        ("luck crosswalk mismatch", "luck_crosswalk_mismatch"),
    )
    section_slots = request["trusted_attachments"]["sections"]
    codes: list[str] = []
    locations: list[str] = []
    for issue in error.issues:
        code = next(
            (fixed for fragment, fixed in patterns if fragment in issue),
            "unclassified_semantic_error",
        )
        raw_path = issue.split(":", 1)[0]
        segments = raw_path.strip("/").split("/") if raw_path else []
        location = "unknown"
        if segments and segments[0] == "summary":
            location = "summary"
        elif segments and segments[0] == "consultation_answer":
            location = "consultation_answer"
        elif len(segments) >= 2 and segments[0] == "future_flow_yearly":
            index = segments[1] if segments[1].isascii() and segments[1].isdigit() else "unknown"
            field = segments[2] if len(segments) >= 3 else "container"
            location = f"future_flow_yearly[{index}].{field}"
        elif len(segments) >= 2 and segments[0] == "long_term_luck":
            index = segments[1] if segments[1].isascii() and segments[1].isdigit() else "unknown"
            field = segments[2] if len(segments) >= 3 else "container"
            if field == "advice" and len(segments) >= 4:
                field = f"advice[{segments[3]}]"
            location = f"long_term_luck[{index}].{field}"
        elif len(segments) >= 2 and segments[0] == "sections":
            index_text = segments[1]
            if index_text.isascii() and index_text.isdigit():
                index = int(index_text)
                if 0 <= index < len(section_slots):
                    field = segments[2] if len(segments) >= 3 else "container"
                    location = f"{section_slots[index]['section_id']}.{field}"
        if code not in codes:
            codes.append(code)
        if location not in locations:
            locations.append(location)
    return tuple(codes), tuple(locations)


def _build_publishable_product(
    chart: Mapping[str, Any],
    reading_context: Mapping[str, Any],
    ai_reading: Mapping[str, Any],
    report: AIReadingQualityReportV2,
    *,
    generated_at: datetime,
    repair_result: Any = None,
) -> ReadingProductV2:
    product_failed = False
    product: ReadingProductV2 | None = None
    try:
        product = build_reading_product_v2(
            chart,
            reading_context,
            ai_reading,
            report,
            generated_at=generated_at,
            repair_result=repair_result,
        )
    except ReadingProductV2ValidationError:
        product_failed = True
    if product_failed or product is None:
        raise CustomerReadingUnavailableError(
            "鑑定結果を公開用に構成できませんでした。",
            stage="reading_product",
            reason_code="product_validation_failed",
            decision=report.decision,
            blocking_codes=_blocking_codes(report),
        )
    return product


def run_customer_reading(
    value: CustomerReadingInput,
    *,
    client: Any | None = None,
    model: str | None = None,
    reference_time: datetime | None = None,
    semantic_assessor: SemanticAssessorV2 | None = None,
) -> ReadingProductV2:
    """Execute the existing trusted pipeline and return only a publishable Product."""

    if not isinstance(value, CustomerReadingInput):
        raise TypeError("value must be CustomerReadingInput")
    trace = current_performance_trace()
    using_real_provider = client is None
    generated_at = reference_time or datetime.now(JST).replace(microsecond=0)
    if generated_at.tzinfo is None or generated_at.utcoffset() is None:
        raise CustomerConfigurationError(
            "鑑定基準時刻の設定が不正です。",
            reason_code="reference_time_invalid",
        )
    generated_at = generated_at.replace(microsecond=0)
    resolved_model = model.strip() if type(model) is str and model.strip() else configured_model()
    provider_client = client if client is not None else create_customer_provider_client()
    assessor = semantic_assessor or OpenAISemanticAssessorV2(
        client=provider_client,
        model=resolved_model,
    )
    measured_assessor = (
        _TimedSemanticAssessor(assessor, trace, using_real_provider)
        if trace is not None
        else assessor
    )

    chart_request = build_customer_chart_request(value)
    if trace is None:
        chart = calculate_chart(chart_request, target_datetime=generated_at)
    else:
        with trace.measure("chart_calculation"):
            chart = calculate_chart(chart_request, target_datetime=generated_at)
    if trace is None:
        consultation_context = (
            build_consultation_context(concern=value.consultation, desired_future="")
            if value.consultation
            else None
        )
        reading_context = build_reading_context_v2(
            chart,
            consultation_context=consultation_context,
        )
    else:
        with trace.measure("reading_context_build"):
            consultation_context = (
                build_consultation_context(concern=value.consultation, desired_future="")
                if value.consultation
                else None
            )
            reading_context = build_reading_context_v2(
                chart,
                consultation_context=consultation_context,
            )
    if trace is None:
        judgment_metadata = build_common_judgment_metadata(chart)
        prompt_request = build_ai_reading_request_v2(reading_context, judgment_metadata)
    else:
        with trace.measure("prompt_build"):
            judgment_metadata = build_common_judgment_metadata(chart)
            prompt_request = build_ai_reading_request_v2(reading_context, judgment_metadata)
    generation_failure: str | None = None
    generation_diagnostic_codes: tuple[str, ...] = ()
    generation_diagnostic_locations: tuple[str, ...] = ()
    generated = None
    try:
        if trace is not None and using_real_provider:
            trace.provider_call()
        if trace is None:
            generated = generate_ai_reading_v2(
                prompt_request,
                client=provider_client,
                model=resolved_model,
            )
        else:
            with trace.measure("ai_generation"):
                generated = generate_ai_reading_v2(
                    prompt_request,
                    client=provider_client,
                    model=resolved_model,
                )
    except AIReadingGeneratorV2ConfigurationError:
        generation_failure = "generator_configuration_invalid"
    except AIReadingGeneratorV2RequestValidationError:
        generation_failure = "generator_request_validation_failed"
    except AIReadingGeneratorV2ProviderError as exc:
        generation_failure = _generator_provider_reason(exc)
    except AIReadingGeneratorV2JSONError:
        generation_failure = "generator_json_invalid"
    except AIReadingGeneratorV2StructuralValidationError:
        generation_failure = "generator_structural_validation_failed"
    except AIReadingGeneratorV2SemanticValidationError as exc:
        (
            generation_diagnostic_codes,
            generation_diagnostic_locations,
        ) = _generator_semantic_diagnostics(exc, prompt_request)
        generation_failure = (
            "generator_semantic_" + generation_diagnostic_codes[0]
            if len(generation_diagnostic_codes) == 1
            else "generator_semantic_validation_failed"
        )
    except AIReadingGeneratorV2CandidateValidationError:
        generation_failure = "generator_candidate_validation_failed"
    except AIReadingGeneratorV2ResponseError as exc:
        generation_failure = _generator_response_reason(exc)
    except Exception:
        generation_failure = "generator_unexpected_failure"
    if generation_failure == "generator_configuration_invalid":
        raise CustomerConfigurationError(
            "鑑定サービスを初期化できませんでした。",
            reason_code=generation_failure,
        )
    if generation_failure is not None or generated is None:
        raise CustomerReadingUnavailableError(
            "鑑定結果を生成できませんでした。",
            stage="generator",
            reason_code=generation_failure or "generator_missing_result",
            diagnostic_codes=generation_diagnostic_codes,
            diagnostic_locations=generation_diagnostic_locations,
        )

    quality_failed = False
    report: AIReadingQualityReportV2 | None = None
    try:
        if trace is None:
            report = evaluate_ai_reading_quality_v2(
                generated.reading,
                reading_context,
                judgment_metadata,
                semantic_assessor=measured_assessor,
            )
        else:
            with trace.measure("quality_gate_first"):
                report = evaluate_ai_reading_quality_v2(
                    generated.reading,
                    reading_context,
                    judgment_metadata,
                    semantic_assessor=measured_assessor,
                )
    except Exception:
        quality_failed = True
    if quality_failed or report is None:
        raise CustomerReadingUnavailableError(
            "鑑定結果の品質確認を実行できませんでした。",
            stage="quality_gate",
            reason_code="quality_gate_evaluation_failed",
        )
    if report.decision == "pass":
        if trace is not None:
            if not trace.has_step("semantic_assessment"):
                trace.skip("semantic_assessment")
            trace.skip("auto_repair")
            trace.skip("quality_gate_second")
        if trace is None:
            return _build_publishable_product(
                chart, reading_context, generated.reading, report,
                generated_at=generated_at,
            )
        with trace.measure("reading_product_build"):
            return _build_publishable_product(
                chart, reading_context, generated.reading, report,
                generated_at=generated_at,
            )

    if _eligible_for_auto_repair(report):
        if trace is not None:
            trace.auto_repair = True
        repair = None
        repair_failure: str | None = None
        try:
            if trace is not None and using_real_provider:
                trace.provider_call()
            if trace is None:
                repair = repair_ai_reading_v2(
                    generated.reading, report, reading_context, judgment_metadata,
                    semantic_assessor=measured_assessor, client=provider_client, model=resolved_model,
                )
            else:
                with trace.measure("auto_repair"):
                    repair = repair_ai_reading_v2(
                        generated.reading, report, reading_context, judgment_metadata,
                        semantic_assessor=measured_assessor, client=provider_client, model=resolved_model,
                    )
        except AIReadingRepairV2ConfigurationError:
            repair_failure = "repair_configuration_failed"
        except AIReadingRepairV2ProviderRequestError as exc:
            repair_failure = _repair_provider_reason(exc)
        except AIReadingRepairV2ProviderResponseError:
            repair_failure = "repair_provider_response_invalid"
        except AIReadingRepairV2PatchValidationError:
            repair_failure = "repair_patch_validation_failed"
        except AIReadingRepairV2CandidateValidationError:
            repair_failure = "repair_candidate_validation_failed"
        except Exception:
            repair_failure = "repair_unexpected_failure"
        if repair_failure is not None or repair is None:
            raise CustomerReadingUnavailableError(
                "鑑定結果の確認処理を完了できませんでした。",
                stage="auto_repair",
                reason_code=repair_failure or "repair_missing_result",
                decision=report.decision,
                blocking_codes=_blocking_codes(report),
            )
        if repair.status == "pass":
            if trace is not None:
                trace.skip("quality_gate_second")
                with trace.measure("reading_product_build"):
                    return _build_publishable_product(
                        chart, reading_context, repair.final_ai_reading,
                        repair.final_quality_report, generated_at=generated_at,
                        repair_result=repair,
                    )
            return _build_publishable_product(
                chart, reading_context, repair.final_ai_reading,
                repair.final_quality_report, generated_at=generated_at,
                repair_result=repair,
            )
        diagnostic_codes, diagnostic_locations = _semantic_assessor_diagnostics(assessor)
        raise CustomerReadingUnavailableError(
            "鑑定結果の修復後確認が完了しませんでした。",
            stage="post_repair_quality_gate",
            reason_code="repair_exhausted",
            decision=repair.final_quality_report.decision,
            blocking_codes=_blocking_codes(repair.final_quality_report),
            diagnostic_codes=diagnostic_codes,
            diagnostic_locations=diagnostic_locations,
        )

    if trace is not None:
        trace.skip("auto_repair")
        trace.skip("quality_gate_second")
    reason_code = (
        "quality_gate_review"
        if report.decision == "review"
        else "quality_gate_non_auto_fail"
        if report.decision == "fail"
        else "quality_gate_non_publishable"
    )
    diagnostic_codes, diagnostic_locations = _semantic_assessor_diagnostics(assessor)
    raise CustomerReadingUnavailableError(
        "鑑定結果の公開前確認が完了しませんでした。",
        stage="quality_gate",
        reason_code=reason_code,
        decision=report.decision,
        blocking_codes=_blocking_codes(report),
        diagnostic_codes=diagnostic_codes,
        diagnostic_locations=diagnostic_locations,
    )


__all__ = [
    "PREFECTURES",
    "PerformanceTrace",
    "CustomerInputError",
    "CustomerConfigurationError",
    "CustomerReadingUnavailableError",
    "SemanticAssessmentProviderError",
    "CustomerReadingInput",
    "OpenAISemanticAssessorV2",
    "validate_customer_input",
    "build_customer_chart_request",
    "create_customer_provider_client",
    "run_customer_reading",
]
