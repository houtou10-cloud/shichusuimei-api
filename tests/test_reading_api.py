"""
tests/test_reading_api.py

api/reading_routes.py のAPI層回帰テスト。

目的
----
POST /reading
GET  /reading/status

について、実際のOpenAI APIを呼ばずに
FastAPIルート層の入出力・エラー処理・
engine接続を検証する。

テスト方針
----------
1. OpenAI APIへ実通信しない。
2. api.reading_routes.generate_reading をmonkeypatchする。
3. api.reading_routes.has_openai_api_key も必要に応じてpatchする。
4. calculate_chart / build_reading_context の受け渡しを確認する。
5. text / json のレスポンス両方を確認する。
6. sections / tone / model / max_output_tokens / store の受け渡しを確認する。
7. 入力エラー / API未設定 / 計算失敗 / AI失敗を確認する。
8. APIキーそのものがレスポンスへ漏れないことを確認する。
9. 既存FastAPIアプリへ直接統合せず、
   このテスト内で専用appを作成する。
"""

from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import api.reading_routes as reading_routes

from api.reading_routes import (
    ALLOWED_OUTPUT_FORMATS,
    ALLOWED_SECTIONS,
    ALLOWED_TONES,
    DEFAULT_SECTIONS,
    READING_API_VERSION,
    ReadingRequest,
    ReadingResponse,
    _build_chart_request,
    _build_response,
    _calculate_chart_for_reading,
    _extract_reading,
    _normalize_sections,
    _validate_output_format,
    _validate_tone,
    generate_shichusuimei_reading,
    get_reading_status,
    router,
)

from engine.reading_generator import (
    ReadingGenerationResult,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def app():
    """
    reading_routesだけを載せた専用FastAPI app。
    """

    application = FastAPI()

    application.include_router(
        router
    )

    return application


@pytest.fixture
def client(
    app,
):
    return TestClient(
        app
    )


@pytest.fixture
def valid_request_payload():
    return {
        "birth_date": "1985-07-17",
        "birth_time": "21:50",
        "birth_place": "石川県",
        "gender": "female",
        "target_datetime": (
            "2026-08-10T15:36:00"
        ),
        "sections": [
            "career",
            "wealth",
        ],
        "tone": "professional_warm",
        "output_format": "json",
        "model": "test-model",
        "max_output_tokens": 2000,
        "store": False,
    }


@pytest.fixture
def fake_chart_result():
    return {
        "pillars": {
            "year": {
                "pillar": "乙丑",
            },
            "month": {
                "pillar": "癸未",
            },
            "day": {
                "pillar": "丁巳",
            },
            "hour": {
                "pillar": "辛亥",
            },
        },
        "day_master": "丁",
        "method": "fake_chart",
        "status": "success",
    }


@pytest.fixture
def fake_reading_context():
    return {
        "schema_version": "reading_context_v1",
        "subject": {
            "birth_date": "1985-07-17",
            "birth_time": "21:50",
            "birth_place": "石川県",
            "gender": "female",
            "timezone": "Asia/Tokyo",
        },
        "natal_chart": {
            "pillars": {
                "year": {
                    "pillar": "乙丑",
                },
                "month": {
                    "pillar": "癸未",
                },
                "day": {
                    "pillar": "丁巳",
                },
                "hour": {
                    "pillar": "辛亥",
                },
            },
            "pillar_sequence": [
                "乙丑",
                "癸未",
                "丁巳",
                "辛亥",
            ],
        },
        "day_master": {
            "stem": "丁",
            "element": "火",
            "yin_yang": "陰",
            "day_pillar": "丁巳",
        },
        "five_elements": {},
        "strength": {},
        "pattern": {},
        "useful_gods": {},
        "luck": {
            "luck_pillars": {},
            "current_luck": {},
            "annual_luck": {},
            "integrated_luck": {},
        },
        "reading_sections": {},
        "source_metadata": {},
        "method": "reading_context_v1",
        "status": "ready_for_ai_reading",
    }


@pytest.fixture
def fake_generation_json_result():
    return ReadingGenerationResult(
        output_format="json",
        model="test-model",
        text=(
            '{"summary":"test"}'
        ),
        parsed={
            "summary": "テスト鑑定",
            "sections": {
                "career": {
                    "title": "仕事・適職",
                    "summary": "仕事の要約",
                    "detail": "仕事の詳細",
                    "evidence": [
                        "食神格",
                    ],
                    "advice": [
                        "得意分野を活かす",
                    ],
                },
                "wealth": {
                    "title": "金運",
                    "summary": "金運の要約",
                    "detail": "金運の詳細",
                    "evidence": [
                        "丙午",
                    ],
                    "advice": [
                        "収支を管理する",
                    ],
                },
            },
            "disclaimer": (
                "未来を確定するものではありません。"
            ),
        },
        response_id="resp_test_json",
        response_status="completed",
        usage={
            "input_tokens": 100,
            "output_tokens": 200,
            "total_tokens": 300,
        },
        sections=(
            "career",
            "wealth",
        ),
        status="completed",
    )


@pytest.fixture
def fake_generation_text_result():
    return ReadingGenerationResult(
        output_format="text",
        model="test-model",
        text=(
            "これはテスト用鑑定文です。"
        ),
        parsed=None,
        response_id="resp_test_text",
        response_status="completed",
        usage={
            "input_tokens": 50,
            "output_tokens": 100,
            "total_tokens": 150,
        },
        sections=(
            "career",
        ),
        status="completed",
    )


# ============================================================
# 1. Constants
# ============================================================


def test_reading_api_constants():
    assert (
        READING_API_VERSION
        == "reading_api_v1"
    )


def test_allowed_output_formats():
    assert (
        ALLOWED_OUTPUT_FORMATS
        == {
            "text",
            "json",
        }
    )


def test_allowed_tones():
    assert (
        ALLOWED_TONES
        == {
            "professional_warm",
            "gentle",
            "concise",
            "detailed",
        }
    )


def test_default_sections_are_subset_of_allowed():
    assert set(
        DEFAULT_SECTIONS
    ).issubset(
        ALLOWED_SECTIONS
    )


# ============================================================
# 2. Helper validation
# ============================================================


def test_normalize_sections_default():
    result = _normalize_sections(
        None
    )

    assert (
        result
        == DEFAULT_SECTIONS
    )


def test_normalize_sections_subset():
    result = _normalize_sections(
        [
            "career",
            "wealth",
        ]
    )

    assert result == (
        "career",
        "wealth",
    )


def test_normalize_sections_removes_duplicates():
    result = _normalize_sections(
        [
            "career",
            "career",
            "wealth",
        ]
    )

    assert result == (
        "career",
        "wealth",
    )


def test_normalize_sections_requires_list():
    with pytest.raises(
        ValueError
    ):
        _normalize_sections(
            "career"
        )


def test_normalize_sections_empty_rejected():
    with pytest.raises(
        ValueError
    ):
        _normalize_sections(
            []
        )


def test_normalize_sections_unknown_rejected():
    with pytest.raises(
        ValueError
    ):
        _normalize_sections(
            [
                "career",
                "unknown",
            ]
        )


def test_validate_tone_success():
    assert (
        _validate_tone(
            "gentle"
        )
        == "gentle"
    )


def test_validate_tone_trims():
    assert (
        _validate_tone(
            " gentle "
        )
        == "gentle"
    )


def test_validate_tone_invalid():
    with pytest.raises(
        ValueError
    ):
        _validate_tone(
            "unknown"
        )


def test_validate_output_format_text():
    assert (
        _validate_output_format(
            "text"
        )
        == "text"
    )


def test_validate_output_format_json():
    assert (
        _validate_output_format(
            "json"
        )
        == "json"
    )


def test_validate_output_format_invalid():
    with pytest.raises(
        ValueError
    ):
        _validate_output_format(
            "xml"
        )


# ============================================================
# 3. ReadingRequest / adapter
# ============================================================


def test_reading_request_model(
    valid_request_payload,
):
    request = ReadingRequest(
        **valid_request_payload
    )

    assert (
        request.birth_date
        == "1985-07-17"
    )

    assert (
        request.birth_time
        == "21:50"
    )

    assert (
        request.birth_place
        == "石川県"
    )

    assert (
        request.gender
        == "female"
    )

    assert (
        request.output_format
        == "json"
    )


def test_build_chart_request(
    valid_request_payload,
):
    request = ReadingRequest(
        **valid_request_payload
    )

    chart_request = (
        _build_chart_request(
            request
        )
    )

    assert (
        chart_request.birth_date
        == "1985-07-17"
    )

    assert (
        chart_request.birth_time
        == "21:50"
    )

    assert (
        chart_request.birth_place
        == "石川県"
    )

    assert (
        chart_request.gender
        == "female"
    )


def test_calculate_chart_without_target_datetime(
    monkeypatch,
):
    captured = {}

    def fake_calculate_chart(
        request,
    ):
        captured[
            "request"
        ] = request

        return {
            "ok": True,
        }

    monkeypatch.setattr(
        reading_routes,
        "calculate_chart",
        fake_calculate_chart,
    )

    request = ReadingRequest(
        birth_date="1985-07-17",
        birth_time="21:50",
        birth_place="石川県",
        gender="female",
    )

    result = (
        _calculate_chart_for_reading(
            request
        )
    )

    assert result == {
        "ok": True,
    }

    assert (
        captured[
            "request"
        ].birth_date
        == "1985-07-17"
    )


def test_calculate_chart_with_target_datetime(
    monkeypatch,
    valid_request_payload,
):
    captured = {}

    def fake_calculate_chart(
        request,
        *,
        target_datetime,
    ):
        captured[
            "request"
        ] = request

        captured[
            "target_datetime"
        ] = target_datetime

        return {
            "ok": True,
        }

    monkeypatch.setattr(
        reading_routes,
        "calculate_chart",
        fake_calculate_chart,
    )

    request = ReadingRequest(
        **valid_request_payload
    )

    result = (
        _calculate_chart_for_reading(
            request
        )
    )

    assert result == {
        "ok": True,
    }

    assert (
        captured[
            "target_datetime"
        ]
        == request.target_datetime
    )


# ============================================================
# 4. Reading result extraction
# ============================================================


def test_extract_reading_json(
    fake_generation_json_result,
):
    result = _extract_reading(
        fake_generation_json_result
    )

    assert (
        result
        == fake_generation_json_result.parsed
    )


def test_extract_reading_text(
    fake_generation_text_result,
):
    result = _extract_reading(
        fake_generation_text_result
    )

    assert (
        result
        == "これはテスト用鑑定文です。"
    )


def test_build_response_json(
    fake_chart_result,
    fake_generation_json_result,
):
    response = _build_response(
        chart_result=(
            fake_chart_result
        ),
        generation_result=(
            fake_generation_json_result
        ),
    )

    assert isinstance(
        response,
        ReadingResponse,
    )

    assert (
        response.api_version
        == "reading_api_v1"
    )

    assert (
        response.status
        == "completed"
    )

    assert (
        response.output_format
        == "json"
    )

    assert (
        response.reading
        == fake_generation_json_result.parsed
    )

    assert (
        response.calculation
        == fake_chart_result
    )


# ============================================================
# 5. GET /reading/status
# ============================================================


def test_status_endpoint(
    client,
    monkeypatch,
):
    monkeypatch.setattr(
        reading_routes,
        "has_openai_api_key",
        lambda: True,
    )

    monkeypatch.setattr(
        reading_routes,
        "get_default_model",
        lambda: "test-model",
    )

    response = client.get(
        "/reading/status"
    )

    assert (
        response.status_code
        == 200
    )

    body = response.json()

    assert (
        body[
            "api_version"
        ]
        == "reading_api_v1"
    )

    assert (
        body[
            "status"
        ]
        == "ok"
    )

    assert (
        body[
            "openai_configured"
        ]
        is True
    )

    assert (
        body[
            "default_model"
        ]
        == "test-model"
    )


def test_status_endpoint_api_key_not_leaked(
    client,
    monkeypatch,
):
    secret = (
        "sk-secret-value"
    )

    monkeypatch.setattr(
        reading_routes,
        "has_openai_api_key",
        lambda: True,
    )

    monkeypatch.setattr(
        reading_routes,
        "get_default_model",
        lambda: "test-model",
    )

    response = client.get(
        "/reading/status"
    )

    serialized = response.text

    assert (
        secret
        not in serialized
    )


# ============================================================
# 6. POST /reading success - JSON
# ============================================================


def test_post_reading_json_success(
    client,
    monkeypatch,
    valid_request_payload,
    fake_chart_result,
    fake_reading_context,
    fake_generation_json_result,
):
    monkeypatch.setattr(
        reading_routes,
        "has_openai_api_key",
        lambda: True,
    )

    monkeypatch.setattr(
        reading_routes,
        "calculate_chart",
        lambda request, **kwargs: deepcopy(
            fake_chart_result
        ),
    )

    monkeypatch.setattr(
        reading_routes,
        "build_reading_context",
        lambda chart: deepcopy(
            fake_reading_context
        ),
    )

    monkeypatch.setattr(
        reading_routes,
        "generate_reading",
        lambda *args, **kwargs: (
            fake_generation_json_result
        ),
    )

    response = client.post(
        "/reading",
        json=valid_request_payload,
    )

    assert (
        response.status_code
        == 200
    )

    body = response.json()

    assert (
        body[
            "api_version"
        ]
        == "reading_api_v1"
    )

    assert (
        body[
            "status"
        ]
        == "completed"
    )

    assert (
        body[
            "model"
        ]
        == "test-model"
    )

    assert (
        body[
            "response_id"
        ]
        == "resp_test_json"
    )

    assert (
        body[
            "output_format"
        ]
        == "json"
    )

    assert (
        body[
            "sections"
        ]
        == [
            "career",
            "wealth",
        ]
    )

    assert (
        body[
            "reading"
        ][
            "summary"
        ]
        == "テスト鑑定"
    )


def test_post_reading_passes_generation_options(
    client,
    monkeypatch,
    valid_request_payload,
    fake_chart_result,
    fake_reading_context,
    fake_generation_json_result,
):
    captured = {}

    monkeypatch.setattr(
        reading_routes,
        "has_openai_api_key",
        lambda: True,
    )

    monkeypatch.setattr(
        reading_routes,
        "calculate_chart",
        lambda request, **kwargs: deepcopy(
            fake_chart_result
        ),
    )

    monkeypatch.setattr(
        reading_routes,
        "build_reading_context",
        lambda chart: deepcopy(
            fake_reading_context
        ),
    )

    def fake_generate_reading(
        context,
        **kwargs,
    ):
        captured[
            "context"
        ] = deepcopy(
            context
        )

        captured[
            "kwargs"
        ] = deepcopy(
            kwargs
        )

        return (
            fake_generation_json_result
        )

    monkeypatch.setattr(
        reading_routes,
        "generate_reading",
        fake_generate_reading,
    )

    response = client.post(
        "/reading",
        json=valid_request_payload,
    )

    assert (
        response.status_code
        == 200
    )

    kwargs = captured[
        "kwargs"
    ]

    assert (
        kwargs[
            "model"
        ]
        == "test-model"
    )

    assert (
        kwargs[
            "sections"
        ]
        == (
            "career",
            "wealth",
        )
    )

    assert (
        kwargs[
            "tone"
        ]
        == "professional_warm"
    )

    assert (
        kwargs[
            "output_format"
        ]
        == "json"
    )

    assert (
        kwargs[
            "max_output_tokens"
        ]
        == 2000
    )

    assert (
        kwargs[
            "store"
        ]
        is False
    )


# ============================================================
# 7. POST /reading success - TEXT
# ============================================================


def test_post_reading_text_success(
    client,
    monkeypatch,
    fake_chart_result,
    fake_reading_context,
    fake_generation_text_result,
):
    monkeypatch.setattr(
        reading_routes,
        "has_openai_api_key",
        lambda: True,
    )

    monkeypatch.setattr(
        reading_routes,
        "calculate_chart",
        lambda request, **kwargs: deepcopy(
            fake_chart_result
        ),
    )

    monkeypatch.setattr(
        reading_routes,
        "build_reading_context",
        lambda chart: deepcopy(
            fake_reading_context
        ),
    )

    monkeypatch.setattr(
        reading_routes,
        "generate_reading",
        lambda *args, **kwargs: (
            fake_generation_text_result
        ),
    )

    payload = {
        "birth_date": "1985-07-17",
        "birth_time": "21:50",
        "birth_place": "石川県",
        "gender": "female",
        "sections": [
            "career",
        ],
        "output_format": "text",
        "model": "test-model",
    }

    response = client.post(
        "/reading",
        json=payload,
    )

    assert (
        response.status_code
        == 200
    )

    body = response.json()

    assert (
        body[
            "output_format"
        ]
        == "text"
    )

    assert (
        body[
            "reading"
        ]
        == "これはテスト用鑑定文です。"
    )


# ============================================================
# 8. API key errors
# ============================================================


def test_post_reading_api_key_missing(
    client,
    valid_request_payload,
    monkeypatch,
):
    monkeypatch.setattr(
        reading_routes,
        "has_openai_api_key",
        lambda: False,
    )

    response = client.post(
        "/reading",
        json=valid_request_payload,
    )

    assert (
        response.status_code
        == 503
    )

    assert (
        "OPENAI_API_KEY"
        in response.json()[
            "detail"
        ]
    )


# ============================================================
# 9. Request validation errors
# ============================================================


def test_post_reading_unknown_section(
    client,
    monkeypatch,
    valid_request_payload,
):
    monkeypatch.setattr(
        reading_routes,
        "has_openai_api_key",
        lambda: True,
    )

    payload = deepcopy(
        valid_request_payload
    )

    payload[
        "sections"
    ] = [
        "career",
        "unknown",
    ]

    response = client.post(
        "/reading",
        json=payload,
    )

    assert (
        response.status_code
        == 400
    )


def test_post_reading_empty_sections(
    client,
    monkeypatch,
    valid_request_payload,
):
    monkeypatch.setattr(
        reading_routes,
        "has_openai_api_key",
        lambda: True,
    )

    payload = deepcopy(
        valid_request_payload
    )

    payload[
        "sections"
    ] = []

    response = client.post(
        "/reading",
        json=payload,
    )

    assert (
        response.status_code
        == 400
    )


def test_post_reading_invalid_tone(
    client,
    monkeypatch,
    valid_request_payload,
):
    monkeypatch.setattr(
        reading_routes,
        "has_openai_api_key",
        lambda: True,
    )

    payload = deepcopy(
        valid_request_payload
    )

    payload[
        "tone"
    ] = "unknown"

    response = client.post(
        "/reading",
        json=payload,
    )

    assert (
        response.status_code
        == 400
    )


def test_post_reading_invalid_output_format_rejected_by_pydantic(
    client,
    monkeypatch,
    valid_request_payload,
):
    monkeypatch.setattr(
        reading_routes,
        "has_openai_api_key",
        lambda: True,
    )

    payload = deepcopy(
        valid_request_payload
    )

    payload[
        "output_format"
    ] = "xml"

    response = client.post(
        "/reading",
        json=payload,
    )

    # Literal["text", "json"]なのでFastAPI/Pydanticが422。
    assert (
        response.status_code
        == 422
    )


def test_post_reading_max_tokens_too_small(
    client,
    monkeypatch,
    valid_request_payload,
):
    monkeypatch.setattr(
        reading_routes,
        "has_openai_api_key",
        lambda: True,
    )

    payload = deepcopy(
        valid_request_payload
    )

    payload[
        "max_output_tokens"
    ] = 10

    response = client.post(
        "/reading",
        json=payload,
    )

    assert (
        response.status_code
        == 422
    )


def test_post_reading_max_tokens_too_large(
    client,
    monkeypatch,
    valid_request_payload,
):
    monkeypatch.setattr(
        reading_routes,
        "has_openai_api_key",
        lambda: True,
    )

    payload = deepcopy(
        valid_request_payload
    )

    payload[
        "max_output_tokens"
    ] = 999999

    response = client.post(
        "/reading",
        json=payload,
    )

    assert (
        response.status_code
        == 422
    )


# ============================================================
# 10. Chart errors
# ============================================================


def test_post_reading_chart_value_error(
    client,
    monkeypatch,
    valid_request_payload,
):
    monkeypatch.setattr(
        reading_routes,
        "has_openai_api_key",
        lambda: True,
    )

    def fail_chart(
        *args,
        **kwargs,
    ):
        raise ValueError(
            "invalid birth data"
        )

    monkeypatch.setattr(
        reading_routes,
        "calculate_chart",
        fail_chart,
    )

    response = client.post(
        "/reading",
        json=valid_request_payload,
    )

    assert (
        response.status_code
        == 400
    )

    assert (
        "命式計算入力が不正"
        in response.json()[
            "detail"
        ]
    )


def test_post_reading_chart_unexpected_error(
    client,
    monkeypatch,
    valid_request_payload,
):
    monkeypatch.setattr(
        reading_routes,
        "has_openai_api_key",
        lambda: True,
    )

    def fail_chart(
        *args,
        **kwargs,
    ):
        raise RuntimeError(
            "unexpected"
        )

    monkeypatch.setattr(
        reading_routes,
        "calculate_chart",
        fail_chart,
    )

    response = client.post(
        "/reading",
        json=valid_request_payload,
    )

    assert (
        response.status_code
        == 500
    )

    assert (
        "命式計算中に"
        in response.json()[
            "detail"
        ]
    )


# ============================================================
# 11. Reading context errors
# ============================================================


def test_post_reading_context_error(
    client,
    monkeypatch,
    valid_request_payload,
    fake_chart_result,
):
    monkeypatch.setattr(
        reading_routes,
        "has_openai_api_key",
        lambda: True,
    )

    monkeypatch.setattr(
        reading_routes,
        "calculate_chart",
        lambda *args, **kwargs: deepcopy(
            fake_chart_result
        ),
    )

    def fail_context(
        chart,
    ):
        raise KeyError(
            "missing"
        )

    monkeypatch.setattr(
        reading_routes,
        "build_reading_context",
        fail_context,
    )

    response = client.post(
        "/reading",
        json=valid_request_payload,
    )

    assert (
        response.status_code
        == 500
    )

    assert (
        "AI鑑定コンテキスト"
        in response.json()[
            "detail"
        ]
    )


# ============================================================
# 12. AI generation errors
# ============================================================


def test_post_reading_generation_value_error(
    client,
    monkeypatch,
    valid_request_payload,
    fake_chart_result,
    fake_reading_context,
):
    monkeypatch.setattr(
        reading_routes,
        "has_openai_api_key",
        lambda: True,
    )

    monkeypatch.setattr(
        reading_routes,
        "calculate_chart",
        lambda *args, **kwargs: deepcopy(
            fake_chart_result
        ),
    )

    monkeypatch.setattr(
        reading_routes,
        "build_reading_context",
        lambda chart: deepcopy(
            fake_reading_context
        ),
    )

    def fail_generate(
        *args,
        **kwargs,
    ):
        raise ValueError(
            "bad generation options"
        )

    monkeypatch.setattr(
        reading_routes,
        "generate_reading",
        fail_generate,
    )

    response = client.post(
        "/reading",
        json=valid_request_payload,
    )

    assert (
        response.status_code
        == 400
    )

    assert (
        "AI鑑定生成条件"
        in response.json()[
            "detail"
        ]
    )


def test_post_reading_generation_unexpected_error(
    client,
    monkeypatch,
    valid_request_payload,
    fake_chart_result,
    fake_reading_context,
):
    monkeypatch.setattr(
        reading_routes,
        "has_openai_api_key",
        lambda: True,
    )

    monkeypatch.setattr(
        reading_routes,
        "calculate_chart",
        lambda *args, **kwargs: deepcopy(
            fake_chart_result
        ),
    )

    monkeypatch.setattr(
        reading_routes,
        "build_reading_context",
        lambda chart: deepcopy(
            fake_reading_context
        ),
    )

    def fail_generate(
        *args,
        **kwargs,
    ):
        raise RuntimeError(
            "AI failed"
        )

    monkeypatch.setattr(
        reading_routes,
        "generate_reading",
        fail_generate,
    )

    response = client.post(
        "/reading",
        json=valid_request_payload,
    )

    assert (
        response.status_code
        == 500
    )

    assert (
        "AI鑑定生成中に"
        in response.json()[
            "detail"
        ]
    )


def test_post_reading_generation_not_completed(
    client,
    monkeypatch,
    valid_request_payload,
    fake_chart_result,
    fake_reading_context,
):
    monkeypatch.setattr(
        reading_routes,
        "has_openai_api_key",
        lambda: True,
    )

    monkeypatch.setattr(
        reading_routes,
        "calculate_chart",
        lambda *args, **kwargs: deepcopy(
            fake_chart_result
        ),
    )

    monkeypatch.setattr(
        reading_routes,
        "build_reading_context",
        lambda chart: deepcopy(
            fake_reading_context
        ),
    )

    result = ReadingGenerationResult(
        output_format="json",
        model="test-model",
        text="{}",
        parsed={},
        response_id="resp_incomplete",
        response_status="incomplete",
        usage={},
        sections=(
            "career",
            "wealth",
        ),
        status="incomplete",
    )

    monkeypatch.setattr(
        reading_routes,
        "generate_reading",
        lambda *args, **kwargs: result,
    )

    response = client.post(
        "/reading",
        json=valid_request_payload,
    )

    assert (
        response.status_code
        == 500
    )

    assert (
        "正常完了しませんでした"
        in response.json()[
            "detail"
        ]
    )


# ============================================================
# 13. Empty reading errors
# ============================================================


def test_post_reading_json_none(
    client,
    monkeypatch,
    valid_request_payload,
    fake_chart_result,
    fake_reading_context,
):
    monkeypatch.setattr(
        reading_routes,
        "has_openai_api_key",
        lambda: True,
    )

    monkeypatch.setattr(
        reading_routes,
        "calculate_chart",
        lambda *args, **kwargs: deepcopy(
            fake_chart_result
        ),
    )

    monkeypatch.setattr(
        reading_routes,
        "build_reading_context",
        lambda chart: deepcopy(
            fake_reading_context
        ),
    )

    result = ReadingGenerationResult(
        output_format="json",
        model="test-model",
        text="",
        parsed=None,
        response_id="resp_none",
        response_status="completed",
        usage={},
        sections=(
            "career",
            "wealth",
        ),
        status="completed",
    )

    monkeypatch.setattr(
        reading_routes,
        "generate_reading",
        lambda *args, **kwargs: result,
    )

    response = client.post(
        "/reading",
        json=valid_request_payload,
    )

    assert (
        response.status_code
        == 500
    )

    assert (
        "AI鑑定結果が空"
        in response.json()[
            "detail"
        ]
    )


def test_post_reading_text_empty_string(
    client,
    monkeypatch,
    fake_chart_result,
    fake_reading_context,
):
    monkeypatch.setattr(
        reading_routes,
        "has_openai_api_key",
        lambda: True,
    )

    monkeypatch.setattr(
        reading_routes,
        "calculate_chart",
        lambda *args, **kwargs: deepcopy(
            fake_chart_result
        ),
    )

    monkeypatch.setattr(
        reading_routes,
        "build_reading_context",
        lambda chart: deepcopy(
            fake_reading_context
        ),
    )

    result = ReadingGenerationResult(
        output_format="text",
        model="test-model",
        text="   ",
        parsed=None,
        response_id="resp_empty",
        response_status="completed",
        usage={},
        sections=(
            "career",
        ),
        status="completed",
    )

    monkeypatch.setattr(
        reading_routes,
        "generate_reading",
        lambda *args, **kwargs: result,
    )

    payload = {
        "birth_date": "1985-07-17",
        "birth_time": "21:50",
        "birth_place": "石川県",
        "gender": "female",
        "sections": [
            "career",
        ],
        "output_format": "text",
        "model": "test-model",
    }

    response = client.post(
        "/reading",
        json=payload,
    )

    assert (
        response.status_code
        == 500
    )

    assert (
        "空文字"
        in response.json()[
            "detail"
        ]
    )


# ============================================================
# 14. Model fallback
# ============================================================


def test_post_reading_model_fallback(
    client,
    monkeypatch,
    fake_chart_result,
    fake_reading_context,
    fake_generation_json_result,
):
    captured = {}

    monkeypatch.setattr(
        reading_routes,
        "has_openai_api_key",
        lambda: True,
    )

    monkeypatch.setattr(
        reading_routes,
        "get_default_model",
        lambda: "fallback-model",
    )

    monkeypatch.setattr(
        reading_routes,
        "calculate_chart",
        lambda *args, **kwargs: deepcopy(
            fake_chart_result
        ),
    )

    monkeypatch.setattr(
        reading_routes,
        "build_reading_context",
        lambda chart: deepcopy(
            fake_reading_context
        ),
    )

    def fake_generate(
        context,
        **kwargs,
    ):
        captured[
            "model"
        ] = kwargs[
            "model"
        ]

        return (
            fake_generation_json_result
        )

    monkeypatch.setattr(
        reading_routes,
        "generate_reading",
        fake_generate,
    )

    payload = {
        "birth_date": "1985-07-17",
        "birth_time": "21:50",
        "birth_place": "石川県",
        "gender": "female",
        "sections": [
            "career",
            "wealth",
        ],
        "output_format": "json",
    }

    response = client.post(
        "/reading",
        json=payload,
    )

    assert (
        response.status_code
        == 200
    )

    assert (
        captured[
            "model"
        ]
        == "fallback-model"
    )


# ============================================================
# 15. Default sections
# ============================================================


def test_post_reading_default_sections(
    client,
    monkeypatch,
    fake_chart_result,
    fake_reading_context,
):
    captured = {}

    monkeypatch.setattr(
        reading_routes,
        "has_openai_api_key",
        lambda: True,
    )

    monkeypatch.setattr(
        reading_routes,
        "calculate_chart",
        lambda *args, **kwargs: deepcopy(
            fake_chart_result
        ),
    )

    monkeypatch.setattr(
        reading_routes,
        "build_reading_context",
        lambda chart: deepcopy(
            fake_reading_context
        ),
    )

    result = ReadingGenerationResult(
        output_format="json",
        model="test-model",
        text="{}",
        parsed={
            "summary": "summary",
            "sections": {},
            "disclaimer": "disclaimer",
        },
        response_id="resp_default",
        response_status="completed",
        usage={},
        sections=tuple(
            DEFAULT_SECTIONS
        ),
        status="completed",
    )

    def fake_generate(
        context,
        **kwargs,
    ):
        captured[
            "sections"
        ] = kwargs[
            "sections"
        ]

        return result

    monkeypatch.setattr(
        reading_routes,
        "generate_reading",
        fake_generate,
    )

    payload = {
        "birth_date": "1985-07-17",
        "birth_time": "21:50",
        "birth_place": "石川県",
        "gender": "female",
        "output_format": "json",
        "model": "test-model",
    }

    response = client.post(
        "/reading",
        json=payload,
    )

    assert (
        response.status_code
        == 200
    )

    assert (
        captured[
            "sections"
        ]
        == DEFAULT_SECTIONS
    )


# ============================================================
# 16. Privacy / secret handling
# ============================================================


def test_post_reading_response_does_not_include_api_key(
    client,
    monkeypatch,
    valid_request_payload,
    fake_chart_result,
    fake_reading_context,
    fake_generation_json_result,
):
    secret = (
        "sk-super-secret-never-return"
    )

    monkeypatch.setattr(
        reading_routes,
        "has_openai_api_key",
        lambda: True,
    )

    monkeypatch.setattr(
        reading_routes,
        "calculate_chart",
        lambda *args, **kwargs: deepcopy(
            fake_chart_result
        ),
    )

    monkeypatch.setattr(
        reading_routes,
        "build_reading_context",
        lambda chart: deepcopy(
            fake_reading_context
        ),
    )

    monkeypatch.setattr(
        reading_routes,
        "generate_reading",
        lambda *args, **kwargs: (
            fake_generation_json_result
        ),
    )

    response = client.post(
        "/reading",
        json=valid_request_payload,
    )

    assert (
        response.status_code
        == 200
    )

    assert (
        secret
        not in response.text
    )


# ============================================================
# 17. OpenAPI
# ============================================================


def test_openapi_contains_reading_routes(
    app,
):
    schema = app.openapi()

    assert (
        "/reading"
        in schema[
            "paths"
        ]
    )

    assert (
        "/reading/status"
        in schema[
            "paths"
        ]
    )


def test_openapi_operation_ids(
    app,
):
    schema = app.openapi()

    assert (
        schema[
            "paths"
        ][
            "/reading"
        ][
            "post"
        ][
            "operationId"
        ]
        == "generateShichusuimeiReading"
    )

    assert (
        schema[
            "paths"
        ][
            "/reading/status"
        ][
            "get"
        ][
            "operationId"
        ]
        == "getReadingStatus"
    )


# ============================================================
# 18. Final API smoke
# ============================================================


def test_reading_api_end_to_end_fake(
    client,
    monkeypatch,
    valid_request_payload,
    fake_chart_result,
    fake_reading_context,
    fake_generation_json_result,
):
    """
    HTTP request
        ↓
    ReadingRequest
        ↓
    calculate_chart(fake)
        ↓
    build_reading_context(fake)
        ↓
    generate_reading(fake)
        ↓
    ReadingResponse
        ↓
    HTTP 200

    を1本で確認する。
    """

    calls = {
        "chart": 0,
        "context": 0,
        "generation": 0,
    }

    monkeypatch.setattr(
        reading_routes,
        "has_openai_api_key",
        lambda: True,
    )

    def fake_chart(
        request,
        **kwargs,
    ):
        calls[
            "chart"
        ] += 1

        assert (
            request.birth_date
            == "1985-07-17"
        )

        return deepcopy(
            fake_chart_result
        )

    def fake_context(
        chart,
    ):
        calls[
            "context"
        ] += 1

        assert (
            chart[
                "day_master"
            ]
            == "丁"
        )

        return deepcopy(
            fake_reading_context
        )

    def fake_generation(
        context,
        **kwargs,
    ):
        calls[
            "generation"
        ] += 1

        assert (
            context[
                "schema_version"
            ]
            == "reading_context_v1"
        )

        assert (
            kwargs[
                "sections"
            ]
            == (
                "career",
                "wealth",
            )
        )

        return (
            fake_generation_json_result
        )

    monkeypatch.setattr(
        reading_routes,
        "calculate_chart",
        fake_chart,
    )

    monkeypatch.setattr(
        reading_routes,
        "build_reading_context",
        fake_context,
    )

    monkeypatch.setattr(
        reading_routes,
        "generate_reading",
        fake_generation,
    )

    response = client.post(
        "/reading",
        json=valid_request_payload,
    )

    assert (
        response.status_code
        == 200
    )

    assert calls == {
        "chart": 1,
        "context": 1,
        "generation": 1,
    }

    body = response.json()

    assert (
        body[
            "reading"
        ][
            "sections"
        ][
            "career"
        ][
            "title"
        ]
        == "仕事・適職"
    )

    assert (
        body[
            "usage"
        ][
            "total_tokens"
        ]
        == 300
    )
