"""Fast customer reading and on-demand detail contracts.

This module deliberately does not replace the frozen full Reading pipeline.
It creates a small, short-lived session containing the server-owned chart and
ReadingContext, then asks the provider only for the prose needed by the first
screen (or one requested detail).
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta
import json
import threading
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


def _provider_call(client: Any, *, model: str, instructions: str, context: Mapping[str, Any], schema: Mapping[str, Any]) -> dict[str, Any]:
    create = getattr(getattr(client, "responses", None), "create", None)
    if not callable(create):
        raise CustomerConfigurationError("fast provider unavailable", reason_code="responses_api_unavailable")
    response = create(
        model=model,
        instructions=instructions,
        input=[{"role": "user", "content": json.dumps(context, ensure_ascii=False, separators=(",", ":"))}],
        max_output_tokens=2500 if schema is _FAST_SCHEMA else 1400,
        reasoning={"effort": "low"},
        store=False,
        text={"format": {"type": "json_schema", "name": "fast_reading_v1", "schema": schema, "strict": True}},
    )
    payload = json.loads(_extract_text(response))
    errors = sorted(Draft202012Validator(schema).iter_errors(payload), key=lambda e: list(e.path))
    if errors:
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


def _build_context(value: CustomerReadingInput, reference_time: datetime) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    chart = calculate_chart(build_customer_chart_request(value), target_datetime=reference_time)
    consultation = (
        build_consultation_context(concern=value.consultation, desired_future="")
        if value.consultation
        else None
    )
    context = build_reading_context_v2(chart, consultation_context=consultation)
    metadata = build_common_judgment_metadata(chart)
    return chart, context, metadata


def _fast_fallback(context: Mapping[str, Any], metadata: Mapping[str, Any]) -> dict[str, str]:
    """Deterministic provider-free fallback used only by tests/offline tooling."""
    day_master = context.get("chart", {}).get("day_master") or "命式の日主"
    return {key: f"{label}は、{day_master}を中心に命式の根拠を確認しながら読み解きます。" for key, label in FAST_SECTIONS}


def run_fast_reading(value: CustomerReadingInput, *, client: Any | None = None, model: str | None = None, reference_time: datetime | None = None) -> dict[str, Any]:
    if not isinstance(value, CustomerReadingInput):
        raise TypeError("value must be CustomerReadingInput")
    now = reference_time or datetime.now().astimezone()
    chart, context, metadata = _build_context(value, now)
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
        )
    _validate_fast_texts(sections, context)
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
    return {"session_id": session_id, "chart": deepcopy(chart), "reading_context": deepcopy(context), "sections": deepcopy(sections)}


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


def run_detail(session_id: str, detail_type: str, *, client: Any | None = None, model: str | None = None) -> str:
    if detail_type not in DETAIL_TYPES:
        raise ValueError("invalid detail_type")
    session = get_session(session_id)
    if session is None:
        raise KeyError("session expired")
    if detail_type in session["details"]:
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
        )
        text = payload["text"]
    _validate_detail_text(text, session["reading_context"])
    if detail_type in {"career", "wealth", "relationships"} and any(
        term in text for term in ("大運", "歳運", "年運", "現在の運勢", "今後の流れ")
    ):
        raise ValueError("luck-only content in non-luck detail")
    with _LOCK:
        session["details"][detail_type] = text
    return text


__all__ = ["DETAIL_TYPES", "FAST_SECTIONS", "get_session", "run_detail", "run_fast_reading"]
