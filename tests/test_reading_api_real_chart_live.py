"""
tests/test_reading_api_real_chart_live.py

POST /reading を本物のOpenAI Responses APIまで通す
実命式ライブE2Eテスト。

目的
----
実際のHTTP/FastAPI経路で、

    TestClient
        ↓
    POST /reading
        ↓
    reading_routes.py
        ↓
    calculate_chart()
        ↓
    build_reading_context()
        ↓
    reading_prompt.py
        ↓
    reading_generator.py
        ↓
    OpenAI Responses API
        ↓
    HTTP 200
        ↓
    鑑定JSON

までを一気通貫で確認する。

通常CIでは実行しない
--------------------
このテストは外部API通信とAPI料金を伴う。

そのため通常のpytestではskipし、
以下の条件が両方成立した場合だけ実行する。

1.
    RUN_OPENAI_LIVE_TESTS=1

2.
    OPENAI_API_KEY が設定済み

注意
----
APIレスポンスの自然言語本文は非決定的なので、
文章完全一致は要求しない。

検証するのは、

・HTTP 200
・reading_api_v1
・completed
・正しいoutput_format
・要求sectionが保持される
・readingがJSON object
・summary / sections / disclaimerが存在
・career sectionのschemaが成立
・response_idが存在
・APIキーをレスポンスへ露出しない

というAPI契約。

固定実命式
----------
1985-07-17
21:50
石川県
女性

現在の検証済み命式:
    年柱 乙丑
    月柱 癸未
    日柱 丁巳
    時柱 辛亥
    日主 丁

評価日時:
    2026-08-10 15:36

API料金節約
----------
live POSTはcareer 1セクションだけ。

Version
-------
reading_api_real_chart_live_v1
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient

from main import app

from engine.reading_generator import (
    OPENAI_API_KEY_ENV,
    OPENAI_READING_MODEL_ENV,
    get_default_model,
    has_openai_api_key,
)


# ============================================================
# Live configuration
# ============================================================


LIVE_TEST_ENV = (
    "RUN_OPENAI_LIVE_TESTS"
)

LIVE_TEST_ENABLED_VALUE = "1"


def _live_enabled() -> bool:
    return (
        os.getenv(
            LIVE_TEST_ENV,
            "",
        ).strip()
        == LIVE_TEST_ENABLED_VALUE
    )


def _live_skip_reason() -> str | None:
    if not _live_enabled():
        return (
            f"{LIVE_TEST_ENV}=1 が設定されていないため"
            "reading API live testをskipします。"
        )

    if not has_openai_api_key():
        return (
            f"{OPENAI_API_KEY_ENV} が設定されていないため"
            "reading API live testをskipします。"
        )

    return None


pytestmark = pytest.mark.skipif(
    _live_skip_reason()
    is not None,
    reason=(
        _live_skip_reason()
        or ""
    ),
)


# ============================================================
# Client
# ============================================================


client = TestClient(
    app
)


# ============================================================
# Fixed request
# ============================================================


LIVE_SECTIONS = [
    "career",
]

LIVE_OUTPUT_FORMAT = "json"

LIVE_TONE = "professional_warm"

LIVE_MAX_OUTPUT_TOKENS = 8000

LIVE_STORE = False


def make_live_request() -> Dict[str, Any]:
    """
    /readingへ送る実命式リクエスト。

    modelは意図的に送らない。

    理由:
    Swaggerの自動例で "string" をそのまま送ると、
    存在しないモデルとして400になるため。

    モデルはOPENAI_READING_MODEL、
    未設定ならreading_generator.pyの
    default modelへ委ねる。
    """

    return {
        "birth_date": "1985-07-17",
        "birth_time": "21:50",
        "birth_place": "石川県",
        "gender": "female",
        "target_date_time": (
            "2026-08-10T15:36:00"
        ),
        "sections": list(
            LIVE_SECTIONS
        ),
        "tone": LIVE_TONE,
        "output_format": (
            LIVE_OUTPUT_FORMAT
        ),
        "max_output_tokens": (
            LIVE_MAX_OUTPUT_TOKENS
        ),
        "store": LIVE_STORE,
    }


# ============================================================
# Helpers
# ============================================================


def _assert_non_empty_string(
    value: Any,
    name: str,
) -> None:
    assert isinstance(
        value,
        str,
    ), (
        f"{name} はstrである必要があります。"
    )

    assert (
        value.strip()
    ), (
        f"{name} が空です。"
    )


def _assert_reading_schema(
    reading: Dict[str, Any],
) -> None:
    """
    reading_generatorのJSON Schemaに対応する
    最低限の構造を検証する。
    """

    assert isinstance(
        reading,
        dict,
    )

    assert {
        "summary",
        "sections",
        "disclaimer",
    }.issubset(
        reading.keys()
    )

    _assert_non_empty_string(
        reading[
            "summary"
        ],
        "reading.summary",
    )

    _assert_non_empty_string(
        reading[
            "disclaimer"
        ],
        "reading.disclaimer",
    )

    sections = reading[
        "sections"
    ]

    assert isinstance(
        sections,
        dict,
    )

    assert set(
        sections.keys()
    ) == {
        "career",
    }

    career = sections[
        "career"
    ]

    assert isinstance(
        career,
        dict,
    )

    required = {
        "title",
        "summary",
        "detail",
        "evidence",
        "advice",
    }

    assert required.issubset(
        career.keys()
    )

    for key in (
        "title",
        "summary",
        "detail",
    ):
        _assert_non_empty_string(
            career[
                key
            ],
            f"career.{key}",
        )

    assert isinstance(
        career[
            "evidence"
        ],
        list,
    )

    assert isinstance(
        career[
            "advice"
        ],
        list,
    )


# ============================================================
# 1. Environment
# ============================================================


def test_reading_api_live_environment_enabled():
    assert (
        _live_enabled()
        is True
    )


def test_reading_api_live_key_is_configured():
    assert (
        has_openai_api_key()
        is True
    )


def test_reading_api_live_model_resolves():
    model = (
        get_default_model()
    )

    _assert_non_empty_string(
        model,
        "default_model",
    )


# ============================================================
# 2. Status endpoint
# ============================================================


def test_reading_api_live_status_endpoint():
    """
    /reading/status自体はOpenAI APIを呼ばない。
    """

    response = client.get(
        "/reading/status"
    )

    assert (
        response.status_code
        == 200
    )

    data = response.json()

    assert (
        data[
            "api_version"
        ]
        == "reading_api_v1"
    )

    assert (
        data[
            "status"
        ]
        == "ok"
    )

    assert (
        data[
            "openai_configured"
        ]
        is True
    )

    assert (
        "career"
        in data[
            "supported_sections"
        ]
    )

    assert (
        "professional_warm"
        in data[
            "supported_tones"
        ]
    )

    assert (
        "json"
        in data[
            "supported_output_formats"
        ]
    )


# ============================================================
# 3. Request contract
# ============================================================


def test_reading_api_live_request_contract():
    payload = (
        make_live_request()
    )

    assert payload[
        "birth_date"
    ] == "1985-07-17"

    assert payload[
        "birth_time"
    ] == "21:50"

    assert payload[
        "birth_place"
    ] == "石川県"

    assert payload[
        "gender"
    ] == "female"

    assert payload[
        "sections"
    ] == [
        "career"
    ]

    assert (
        payload[
            "output_format"
        ]
        == "json"
    )

    assert (
        payload[
            "tone"
        ]
        == "professional_warm"
    )

    assert (
        payload[
            "store"
        ]
        is False
    )

    # "string"モデル事故を防ぐ。
    assert (
        "model"
        not in payload
    )


# ============================================================
# 4. Actual POST /reading
# ============================================================


@pytest.fixture(scope="module")
def live_reading_response():
    """
    本物のAPI通信はモジュール中1回だけ行う。

    複数テストで同じresponseを共有し、
    API料金の無駄な増加を防ぐ。
    """

    payload = (
        make_live_request()
    )

    response = client.post(
        "/reading",
        json=payload,
    )

    return response


def test_reading_api_live_http_200(
    live_reading_response,
):
    """
    最重要:
    FastAPI -> OpenAIまで通ってHTTP 200になる。
    """

    assert (
        live_reading_response.status_code
        == 200
    ), (
        "POST /reading failed: "
        f"{live_reading_response.text}"
    )


def test_reading_api_live_top_level_contract(
    live_reading_response,
):
    data = (
        live_reading_response.json()
    )

    assert (
        data[
            "api_version"
        ]
        == "reading_api_v1"
    )

    assert (
        data[
            "status"
        ]
        == "completed"
    )

    assert (
        data[
            "output_format"
        ]
        == "json"
    )

    assert (
        data[
            "sections"
        ]
        == [
            "career"
        ]
    )

    _assert_non_empty_string(
        data[
            "model"
        ],
        "model",
    )


def test_reading_api_live_response_id(
    live_reading_response,
):
    data = (
        live_reading_response.json()
    )

    _assert_non_empty_string(
        data[
            "response_id"
        ],
        "response_id",
    )

    assert (
        data[
            "response_status"
        ]
        in (
            None,
            "completed",
        )
    )


def test_reading_api_live_reading_schema(
    live_reading_response,
):
    data = (
        live_reading_response.json()
    )

    _assert_reading_schema(
        data[
            "reading"
        ]
    )


# ============================================================
# 5. Content sanity
# ============================================================


def test_reading_api_live_career_has_content(
    live_reading_response,
):
    """
    AI文章の完全一致は要求しない。

    career本文が実際に生成されていることだけ確認。
    """

    reading = (
        live_reading_response.json()[
            "reading"
        ]
    )

    career = reading[
        "sections"
    ][
        "career"
    ]

    combined = (
        career[
            "title"
        ]
        + career[
            "summary"
        ]
        + career[
            "detail"
        ]
    )

    assert (
        len(
            combined.strip()
        )
        >= 20
    )


def test_reading_api_live_disclaimer_exists(
    live_reading_response,
):
    reading = (
        live_reading_response.json()[
            "reading"
        ]
    )

    disclaimer = reading[
        "disclaimer"
    ]

    _assert_non_empty_string(
        disclaimer,
        "disclaimer",
    )


# ============================================================
# 6. Security
# ============================================================


def test_reading_api_live_response_never_exposes_api_key(
    live_reading_response,
):
    """
    OpenAI APIキーがHTTP responseへ混入しない。
    """

    api_key = os.getenv(
        OPENAI_API_KEY_ENV
    )

    assert api_key

    text = (
        live_reading_response.text
    )

    assert (
        api_key
        not in text
    )

    lower = text.lower()

    assert (
        "openai_api_key"
        not in lower
    )


def test_reading_api_live_response_is_json_serializable(
    live_reading_response,
):
    """
    FastAPIレスポンスが通常JSONとして扱えること。
    """

    data = (
        live_reading_response.json()
    )

    serialized = json.dumps(
        data,
        ensure_ascii=False,
    )

    assert isinstance(
        serialized,
        str,
    )

    assert (
        serialized
    )


# ============================================================
# 7. Model configuration consistency
# ============================================================


def test_reading_api_live_model_matches_config(
    live_reading_response,
):
    """
    modelをrequestで指定していないため、
    server側のdefault modelが使われる。

    OPENAI_READING_MODELが設定されている場合も
    get_default_model()が同じ値を返す。
    """

    data = (
        live_reading_response.json()
    )

    assert (
        data[
            "model"
        ]
        == get_default_model()
    )


# ============================================================
# 8. No unwanted sections
# ============================================================


def test_reading_api_live_requested_section_only(
    live_reading_response,
):
    """
    careerだけ要求したため、
    他sectionを勝手に追加しない。
    """

    data = (
        live_reading_response.json()
    )

    reading_sections = (
        data[
            "reading"
        ][
            "sections"
        ]
    )

    assert set(
        reading_sections.keys()
    ) == {
        "career"
    }


# ============================================================
# 9. Final E2E smoke
# ============================================================


def test_reading_api_real_chart_live_end_to_end(
    live_reading_response,
):
    """
    最終live smoke test。

    1回のPOST /readingの結果から
    API全体の重要契約をまとめて確認。
    """

    assert (
        live_reading_response.status_code
        == 200
    )

    data = (
        live_reading_response.json()
    )

    assert (
        data[
            "api_version"
        ]
        == "reading_api_v1"
    )

    assert (
        data[
            "status"
        ]
        == "completed"
    )

    assert (
        data[
            "output_format"
        ]
        == "json"
    )

    assert (
        data[
            "sections"
        ]
        == [
            "career"
        ]
    )

    _assert_non_empty_string(
        data[
            "response_id"
        ],
        "response_id",
    )

    _assert_non_empty_string(
        data[
            "model"
        ],
        "model",
    )

    _assert_reading_schema(
        data[
            "reading"
        ]
    )
