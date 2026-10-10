"""Fast customer reading and on-demand detail contracts.

This module deliberately does not replace the frozen full Reading pipeline.
It creates a small, short-lived session containing the server-owned chart and
ReadingContext, then asks the provider only for the prose needed by the first
screen (or one requested detail).
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta
from collections import OrderedDict
import json
import sys
import threading
import time
from typing import Any, Mapping
from uuid import uuid4
import re

from jsonschema import Draft202012Validator

from api.customer_pipeline import (
    CustomerConfigurationError,
    CustomerReadingInput,
    build_customer_chart_request,
    configured_model,
    create_customer_provider_client,
)
from engine.chart import calculate_chart
from engine.annual_luck import calculate_annual_luck_range
from engine.consultation_context import build_consultation_context
from engine.judgment_metadata import build_common_judgment_metadata
from engine.reading_context_v2 import build_reading_context_v2


FAST_SECTIONS = (
    ("basic_type", "あなたの基本タイプ"),
    ("career", "仕事・適職"),
    ("wealth", "お金"),
    ("relationships", "人間関係"),
    ("current_luck", "現在の運勢"),
    ("future_flow", "今後の流れ"),
    ("advice", "今すべきこと"),
)
DETAIL_TYPES = {
    "career": "仕事・適職",
    "wealth": "お金",
    "relationships": "人間関係",
    "current_luck": "現在の運勢",
    "future_flow": "今後の流れ",
    "long_term_luck": "大運",
    "annual_luck": "歳運",
    "chart_explanation": "命式の詳しい解説",
}
_SESSION_TTL = timedelta(minutes=30)
_SESSIONS: dict[str, dict[str, Any]] = {}
_CHART_CACHE_TTL = timedelta(minutes=5)
_CHART_CACHE_MAX = 16
_CHART_WAIT_TIMEOUT = 60.0
_CHART_CACHE: OrderedDict[tuple[str, ...], tuple[datetime, dict[str, Any]]] = OrderedDict()
_CHART_INFLIGHT: dict[tuple[str, ...], threading.Event] = {}
_CHART_INFLIGHT_ERRORS: dict[tuple[str, ...], BaseException] = {}
_LOCK = threading.Lock()

_FAST_SCHEMA = {
    "type": "object",
    "properties": {
        key: {"type": "string", "minLength": 1, "maxLength": 900}
        for key, _ in FAST_SECTIONS
    },
    "required": [key for key, _ in FAST_SECTIONS],
    "additionalProperties": False,
}
_DETAIL_SCHEMA = {
    "type": "object",
    "properties": {"text": {"type": "string", "minLength": 1, "maxLength": 5000}},
    "required": ["text"],
    "additionalProperties": False,
}
_FAST_MAX_OUTPUT_TOKENS = 4000


def _usage_value(usage: Any, *names: str) -> Any:
    if isinstance(usage, Mapping):
        for name in names:
            if name in usage:
                return usage[name]
    for name in names:
        value = getattr(usage, name, None)
        if value is not None:
            return value
    details = getattr(usage, "input_tokens_details", None)
    if details is None and isinstance(usage, Mapping):
        details = usage.get("input_tokens_details")
    if details is not None and "cached_input_tokens" in names:
        value = _usage_value(details, "cached_tokens", "cached_input_tokens")
        if value is not None:
            return value
    details = getattr(usage, "output_tokens_details", None)
    if details is None and isinstance(usage, Mapping):
        details = usage.get("output_tokens_details")
    if details is not None and "reasoning_tokens" in names:
        value = _usage_value(details, "reasoning_tokens")
        if value is not None:
            return value
    return None


def _emit_perf(prefix: str, values: Mapping[str, Any]) -> None:
    rendered = " ".join(
        f"{key}={str(value).lower() if isinstance(value, bool) else value}"
        for key, value in values.items()
        if value is not None
    )
    sys.stderr.write(f"[{prefix}] {rendered}\n")
    sys.stderr.flush()


def _extract_text(response: Any) -> str:
    value = getattr(response, "output_text", None)
    if isinstance(value, str) and value.strip():
        return value
    output = getattr(response, "output", None)
    if isinstance(output, list):
        chunks: list[str] = []
        for item in output:
            content = getattr(item, "content", None)
            if isinstance(content, list):
                for part in content:
                    text = getattr(part, "text", None)
                    if isinstance(text, str):
                        chunks.append(text)
        if chunks:
            return "".join(chunks)
    raise ValueError("provider response has no text")


def _provider_call(client: Any, *, model: str, instructions: str, context: Mapping[str, Any], schema: Mapping[str, Any], performance: dict[str, Any] | None = None) -> dict[str, Any]:
    create = getattr(getattr(client, "responses", None), "create", None)
    if not callable(create):
        raise CustomerConfigurationError("fast provider unavailable", reason_code="responses_api_unavailable")
    content = json.dumps(context, ensure_ascii=False, separators=(",", ":"))
    if performance is not None:
        performance["provider_calls"] = 1
        performance["input_chars"] = len(content)
        performance["schema_bytes"] = len(json.dumps(schema, ensure_ascii=False, separators=(",", ":")))
    started = time.perf_counter()
    try:
        response = create(
            model=model,
            instructions=instructions,
            input=[{"role": "user", "content": content}],
            # Production logs showed repeated output_tokens=2500 responses;
            # that is the former Fast schema ceiling and can truncate JSON.
            max_output_tokens=_FAST_MAX_OUTPUT_TOKENS if schema is _FAST_SCHEMA else 1400,
            reasoning={"effort": "low"},
            store=False,
            text={"format": {"type": "json_schema", "name": "fast_reading_v1", "schema": schema, "strict": True}},
        )
        status = getattr(response, "status", None)
        if performance is not None and status is not None:
            performance["provider_status"] = status
        if status == "incomplete":
            if performance is not None:
                performance["failure_stage"] = "provider_response"
            details = getattr(response, "incomplete_details", None)
            reason = getattr(details, "reason", None) if details is not None else None
            if performance is not None and reason is not None:
                performance["incomplete_reason"] = reason
            raise ValueError("fast provider response incomplete")
        if isinstance(status, str) and status != "completed":
            if performance is not None:
                performance["failure_stage"] = "provider_response"
            raise ValueError("fast provider response not completed")
        usage = getattr(response, "usage", None)
        if performance is not None and usage is not None:
            performance["input_tokens"] = _usage_value(usage, "input_tokens", "prompt_tokens")
            performance["cached_input_tokens"] = _usage_value(usage, "cached_input_tokens", "prompt_cached_tokens")
            performance["output_tokens"] = _usage_value(usage, "output_tokens", "completion_tokens")
            performance["reasoning_tokens"] = _usage_value(usage, "reasoning_tokens")
            performance["total_tokens"] = _usage_value(usage, "total_tokens")
        raw_text = _extract_text(response)
        if performance is not None:
            performance["output_json_chars"] = len(raw_text)
        try:
            payload = json.loads(raw_text)
        except (TypeError, json.JSONDecodeError) as exc:
            if performance is not None:
                performance["failure_stage"] = "provider_json"
            raise ValueError("fast provider response invalid JSON") from exc
        return_payload = payload
    finally:
        if performance is not None:
            performance["provider_elapsed"] = time.perf_counter() - started
    payload = return_payload
    errors = sorted(Draft202012Validator(schema).iter_errors(payload), key=lambda e: list(e.path))
    if errors:
        if performance is not None:
            performance["failure_stage"] = "provider_schema"
        raise ValueError("fast provider payload invalid")
    return payload


def _trusted_projection(context: Mapping[str, Any], metadata: Mapping[str, Any]) -> dict[str, Any]:
    chart = context.get("chart", {})
    luck = context.get("luck", {})
    facts = []
    for item in context.get("facts", []):
        if isinstance(item, Mapping) and isinstance(item.get("code"), str):
            facts.append({"code": item["code"], "value": item.get("value")})
    def compact(value: Any) -> Any:
        if isinstance(value, Mapping):
            return {
                key: compact(item)
                for key, item in value.items()
                if key not in {"evidence", "warnings", "uncertainty"}
            }
        if isinstance(value, list):
            return [compact(item) for item in value]
        return deepcopy(value)

    return {
        "chart": {
            "pillars": deepcopy(chart.get("pillars", {})),
            "day_master": chart.get("day_master"),
        },
        "facts": facts,
        "strength": compact(metadata.get("components", {}).get("strength", {})),
        "pattern": compact(metadata.get("components", {}).get("pattern", {})),
        "useful_gods": compact(metadata.get("components", {}).get("useful_gods", {})),
        "current_luck": deepcopy(luck.get("current_luck")),
        "five_year_luck": deepcopy(luck.get("five_year_luck", [])),
    }


def _validate_fast_texts(sections: Mapping[str, Any], context: Mapping[str, Any]) -> None:
    if set(sections) != {key for key, _ in FAST_SECTIONS}:
        raise ValueError("fast sections incomplete")
    allowed_numbers = {
        str(item.get("year"))
        for item in context.get("luck", {}).get("five_year_luck", [])
        if isinstance(item, Mapping) and isinstance(item.get("year"), int)
    }
    for key, text in sections.items():
        if not isinstance(text, str) or not text.strip():
            raise ValueError("fast prose missing")
        if key in {"career", "wealth", "relationships"} and any(
            term in text for term in ("大運", "歳運", "年運", "現在の運勢", "今後の流れ")
        ):
            raise ValueError("luck-only content in non-luck fast section")
        for number in re.findall(r"(?<![A-Za-z])\d+(?:\.\d+)?", text):
            if number not in allowed_numbers:
                raise ValueError("unsupported numeric claim in fast prose")


def _validate_detail_text(text: str, context: Mapping[str, Any]) -> None:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("detail prose missing")
    allowed_numbers = {
        str(item.get("year"))
        for item in context.get("luck", {}).get("five_year_luck", [])
        if isinstance(item, Mapping) and isinstance(item.get("year"), int)
    }
    for number in re.findall(r"(?<![A-Za-z])\d+(?:\.\d+)?", text):
        if number not in allowed_numbers:
            raise ValueError("unsupported numeric claim in detail prose")


def _detail_projection(context: Mapping[str, Any], metadata: Mapping[str, Any], detail_type: str) -> dict[str, Any]:
    base = _trusted_projection(context, metadata)
    if detail_type in {"career", "wealth", "relationships", "chart_explanation"}:
        return {
            "chart": base["chart"],
            "facts": base["facts"],
            "strength": base["strength"],
            "pattern": base["pattern"],
            "useful_gods": base["useful_gods"],
        }
    if detail_type == "current_luck":
        return {
            "chart": base["chart"],
            "facts": base["facts"],
            "current_luck": base["current_luck"],
        }
    if detail_type in {"future_flow", "annual_luck"}:
        return {
            "chart": base["chart"],
            "facts": base["facts"],
            "current_luck": base["current_luck"],
            "five_year_luck": base["five_year_luck"],
        }
    return {
        "chart": base["chart"],
        "facts": base["facts"],
        "current_luck": base["current_luck"],
        "strength": base["strength"],
        "pattern": base["pattern"],
    }


def _build_context(value: CustomerReadingInput, reference_time: datetime, performance: dict[str, Any] | None = None) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    started = time.perf_counter()
    # Reuse only an exact-input, exact-second chart for a short bounded period.
    # This is a Fast Reading optimization; the astrology engine remains the
    # sole calculator and current-luck boundaries cannot be crossed by reuse.
    cache_key = (
        "fast-chart-v1",
        str(value.birth_date),
        str(value.birth_time),
        str(value.birth_place),
        str(value.gender),
        reference_time.replace(microsecond=0).isoformat(),
    )
    now = datetime.now().astimezone()
    cache_hit = False
    with _LOCK:
        cached = _CHART_CACHE.get(cache_key)
        if cached is not None and now - cached[0] <= _CHART_CACHE_TTL:
            _CHART_CACHE.move_to_end(cache_key)
            chart = deepcopy(cached[1])
            wait_for = None
            owner = False
            waited = False
            cache_hit = True
        else:
            chart = None
            wait_for = _CHART_INFLIGHT.get(cache_key)
            owner = wait_for is None
            waited = not owner
            if owner:
                _CHART_INFLIGHT_ERRORS.pop(cache_key, None)
                wait_for = threading.Event()
                _CHART_INFLIGHT[cache_key] = wait_for
    if chart is None and not owner:
        # Another request is already calculating this exact chart.  Waiting
        # avoids duplicate Skyfield work without sharing mutable results.
        assert wait_for is not None
        if not wait_for.wait(_CHART_WAIT_TIMEOUT):
            raise TimeoutError("timed out waiting for identical chart calculation")
        with _LOCK:
            error = _CHART_INFLIGHT_ERRORS.get(cache_key)
            cached = _CHART_CACHE.get(cache_key)
            if error is not None:
                raise error
            if cached is None:
                raise RuntimeError("chart calculation completed without a result")
            _CHART_CACHE.move_to_end(cache_key)
            chart = deepcopy(cached[1])
    elif chart is None:
        try:
            chart = calculate_chart(build_customer_chart_request(value), target_datetime=reference_time)
            with _LOCK:
                _CHART_CACHE[cache_key] = (now, deepcopy(chart))
                _CHART_CACHE.move_to_end(cache_key)
                while len(_CHART_CACHE) > _CHART_CACHE_MAX:
                    _CHART_CACHE.popitem(last=False)
        except BaseException as exc:
            with _LOCK:
                _CHART_INFLIGHT_ERRORS[cache_key] = exc
            raise
        finally:
            with _LOCK:
                event = _CHART_INFLIGHT.pop(cache_key, None)
                if event is not None:
                    event.set()
    if performance is not None:
        chart_status = chart.get("birth_time_status") if isinstance(chart, Mapping) else None
        chart_pillars = chart.get("chart") if isinstance(chart, Mapping) else None
        hour_pillar = chart_pillars.get("hour") if isinstance(chart_pillars, Mapping) else None
        performance["birth_time_known"] = value.birth_time is not None
        performance["birth_time_type"] = type(value.birth_time).__name__
        performance["chart_hour_none"] = hour_pillar is None
        if isinstance(chart_status, Mapping):
            performance["chart_time_scope"] = chart_status.get("calculation_scope")
    if performance is not None:
        performance["chart_cache_hit"] = cache_hit
        performance["chart_cache_wait"] = waited
    chart_elapsed = time.perf_counter() - started
    consultation = (
        build_consultation_context(concern=value.consultation, desired_future="")
        if value.consultation
        else None
    )
    context = build_reading_context_v2(chart, consultation_context=consultation)
    context_elapsed = time.perf_counter() - started - chart_elapsed
    metadata = build_common_judgment_metadata(chart)
    if performance is not None:
        performance["chart_elapsed"] = chart_elapsed
        performance["context_elapsed"] = context_elapsed
    return chart, context, metadata


def _fast_fallback(context: Mapping[str, Any], metadata: Mapping[str, Any]) -> dict[str, str]:
    """Deterministic provider-free fallback used only by tests/offline tooling."""
    day_master = context.get("chart", {}).get("day_master") or "命式の日主"
    return {key: f"{label}は、{day_master}を中心に命式の根拠を確認しながら読み解きます。" for key, label in FAST_SECTIONS}


def _chart_mapping(value: Any) -> Mapping[str, Any] | None:
    """Normalize mapping-like chart objects at the display boundary."""
    if isinstance(value, Mapping):
        return value
    dumper = getattr(value, "model_dump", None)
    if callable(dumper):
        dumped = dumper()
        return dumped if isinstance(dumped, Mapping) else None
    attrs = getattr(value, "__dict__", None)
    return attrs if isinstance(attrs, Mapping) else None


def _chart_structure_diagnostic(chart: Any, pillars: Any, position: str, raw_pillar: Any) -> None:
    """Emit type/key metadata only when the display boundary is malformed."""
    chart_keys = list(pillars.keys()) if isinstance(pillars, Mapping) else None
    top_keys = list(chart.keys()) if isinstance(chart, Mapping) else None
    _emit_perf(
        "FAST_CHART_DIAG",
        {
            "position": position,
            "chart_type": type(chart).__name__,
            "chart_chart_type": type(pillars).__name__,
            "pillar_type": type(raw_pillar).__name__,
            "pillar_none": raw_pillar is None,
            "top_keys": ",".join(str(key) for key in top_keys) if top_keys is not None else None,
            "chart_keys": ",".join(str(key) for key in chart_keys) if chart_keys is not None else None,
        },
    )


def _chart_card(chart: Mapping[str, Any]) -> dict[str, Any]:
    pillars = chart.get("chart", {}) if isinstance(chart, Mapping) else None
    if not isinstance(chart, Mapping):
        _chart_structure_diagnostic(chart, pillars, "chart", chart)
        raise TypeError("chart payload is not mapping-like")
    result: dict[str, Any] = {}
    for position in ("year", "month", "day", "hour"):
        raw_pillar = pillars.get(position, {}) if isinstance(pillars, Mapping) else {}
        pillar = _chart_mapping(raw_pillar)
        if pillar is None:
            if position == "hour" and raw_pillar is None:
                result[position] = {
                    "stem": None,
                    "branch": None,
                    "stem_ten_god": None,
                    "twelve_stage": None,
                    "hidden_stems": [],
                    "hidden_stem_ten_gods": [],
                    "unavailable": "出生時刻不明",
                }
                continue
            _chart_structure_diagnostic(chart, pillars, position, raw_pillar)
            raise TypeError(f"chart pillar {position} is not mapping-like")
        hidden = pillar.get("hidden_stem_ten_gods", [])
        result[position] = {
            "stem": pillar.get("stem"),
            "branch": pillar.get("branch"),
            "stem_ten_god": "―" if position == "day" else pillar.get("stem_ten_god"),
            "twelve_stage": pillar.get("twelve_stage"),
            "hidden_stems": list(pillar.get("hidden_stems", [])),
            "hidden_stem_ten_gods": [
                item.get("ten_god") for item in hidden if isinstance(item, Mapping)
            ],
        }
    return result


def _annual_card(chart: Mapping[str, Any]) -> list[dict[str, Any]]:
    current = chart.get("annual_luck", {})
    start_year = current.get("year") if isinstance(current, Mapping) else None
    day_master = chart.get("day_master", {})
    if not isinstance(start_year, int) or not isinstance(day_master, Mapping):
        return []
    try:
        return calculate_annual_luck_range(
            start_year=start_year,
            end_year=start_year + 9,
            day_master_stem=day_master.get("stem"),
            useful_gods=chart.get("useful_gods"),
            current_luck=chart.get("current_luck"),
        )
    except AttributeError:
        # Some legacy/current-luck payloads may lack optional mapping fields.
        # Annual year/ganzhi cards remain calculable without that optional
        # relation; do not turn a completed Fast Reading into a 503.
        try:
            return calculate_annual_luck_range(
                start_year=start_year,
                end_year=start_year + 9,
                day_master_stem=day_master.get("stem"),
                useful_gods=chart.get("useful_gods"),
                current_luck=None,
            )
        except (AttributeError, TypeError, ValueError, KeyError):
            return []
    except (TypeError, ValueError, KeyError):
        return []


def run_fast_reading(value: CustomerReadingInput, *, client: Any | None = None, model: str | None = None, reference_time: datetime | None = None, performance: dict[str, Any] | None = None) -> dict[str, Any]:
    if not isinstance(value, CustomerReadingInput):
        raise TypeError("value must be CustomerReadingInput")
    now = reference_time or datetime.now().astimezone()
    chart, context, metadata = _build_context(value, now, performance)
    if client is None:
        client = create_customer_provider_client()
    resolved_model = model.strip() if isinstance(model, str) and model.strip() else configured_model()
    projection = _trusted_projection(context, metadata)
    if client is None:
        sections = _fast_fallback(context, metadata)
    else:
        sections = _provider_call(
            client,
            model=resolved_model,
            instructions=(
                "短い顧客向け鑑定文だけを日本語で作成してください。各項目は100〜200文字。"
                "数値、割合、期限、順位を新しく作らず、渡された命式・信頼できる事実だけを使ってください。"
                "運の情報は運勢項目に限定し、仕事・お金・人間関係には運勢の時期断定を混ぜないでください。"
            ),
            context=projection,
            schema=_FAST_SCHEMA,
            performance=performance,
        )
    validation_started = time.perf_counter()
    _validate_fast_texts(sections, context)
    if performance is not None:
        performance["validation_elapsed"] = time.perf_counter() - validation_started
    if performance is not None:
        performance["fast_stage"] = "session_assembly"
    session_id = uuid4().hex
    session = {
        "created": now,
        "value": deepcopy(value),
        "chart": chart,
        "reading_context": context,
        "judgment_metadata": metadata,
        "sections": sections,
        "details": {},
    }
    with _LOCK:
        _SESSIONS[session_id] = session
    luck_data = chart.get("luck_pillars", {})
    luck_pillars = luck_data.get("pillars", []) if isinstance(luck_data, Mapping) else []
    annual_data = chart.get("annual_luck", {})
    current_year = annual_data.get("year") if isinstance(annual_data, Mapping) else None
    if performance is not None:
        performance["fast_stage"] = "chart_card"
    chart_card = _chart_card(chart)
    if performance is not None:
        performance["fast_stage"] = "annual_card"
    annual_card = _annual_card(chart)
    if performance is not None:
        performance["fast_stage"] = "result_assembly"
    return {
        "session_id": session_id,
        "chart": deepcopy(chart),
        "chart_card": chart_card,
        "luck_pillars": deepcopy(luck_pillars),
        "annual_luck_15": annual_card,
        "current_year": current_year,
        "reading_context": deepcopy(context),
        "sections": deepcopy(sections),
    }


def get_session(session_id: str) -> dict[str, Any] | None:
    if not isinstance(session_id, str) or len(session_id) != 32:
        return None
    with _LOCK:
        session = _SESSIONS.get(session_id)
        if session is None:
            return None
        if datetime.now().astimezone() - session["created"] > _SESSION_TTL:
            _SESSIONS.pop(session_id, None)
            return None
        return session


def run_detail(session_id: str, detail_type: str, *, client: Any | None = None, model: str | None = None, performance: dict[str, Any] | None = None) -> str:
    if detail_type not in DETAIL_TYPES:
        raise ValueError("invalid detail_type")
    session = get_session(session_id)
    if session is None:
        raise KeyError("session expired")
    if detail_type in session["details"]:
        if performance is not None:
            performance["cache_hit"] = True
        return session["details"][detail_type]
    if client is None:
        client = create_customer_provider_client()
    resolved_model = model.strip() if isinstance(model, str) and model.strip() else configured_model()
    context = _detail_projection(
        session["reading_context"], session["judgment_metadata"], detail_type
    )
    context = {"detail_type": detail_type, "label": DETAIL_TYPES[detail_type], "trusted": context}
    if client is None:
        text = f"{DETAIL_TYPES[detail_type]}について、命式の根拠を順に確認しながら読み解きます。"
    else:
        payload = _provider_call(
            client,
            model=resolved_model,
            instructions="指定された一項目だけを500〜1200文字程度で説明してください。未根拠の数値や断定を追加しないでください。",
            context=context,
            schema=_DETAIL_SCHEMA,
            performance=performance,
        )
        text = payload["text"]
    validation_started = time.perf_counter()
    _validate_detail_text(text, session["reading_context"])
    if detail_type in {"career", "wealth", "relationships"} and any(
        term in text for term in ("大運", "歳運", "年運", "現在の運勢", "今後の流れ")
    ):
        raise ValueError("luck-only content in non-luck detail")
    if performance is not None:
        performance["validation_elapsed"] = time.perf_counter() - validation_started
    with _LOCK:
        session["details"][detail_type] = text
    return text


__all__ = ["DETAIL_TYPES", "FAST_SECTIONS", "get_session", "run_detail", "run_fast_reading"]
