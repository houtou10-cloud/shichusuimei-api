"""
tests/test_reading_generator_real_chart_live.py

本物のOpenAI Responses APIを使用する
実命式ライブE2Eテスト。

目的
----
外部暦照合済み実命式について、

    出生データ
        ↓
    calculate_chart()
        ↓
    build_reading_context()
        ↓
    build_generation_payload()
        ↓
    OpenAI Responses API
        ↓
    generate_reading()
        ↓
    実際のAI鑑定結果

までを本物のAPI通信で確認する。

通常CIでは実行しない
--------------------
このテストはAPI料金と外部通信を伴うため、
通常のpytest / GitHub Actionsではskipする。

実行には以下の2条件が必要。

1.
    RUN_OPENAI_LIVE_TESTS=1

2.
    OPENAI_API_KEY が設定済み

モデル
------
OPENAI_READING_MODEL が設定されていればそれを使用する。

未設定の場合は reading_generator.py の
DEFAULT_OPENAI_MODEL / get_default_model() に従う。

重要
----
このテストはAIの「文章内容そのもの」を
完全一致では検証しない。

生成AIの文章は非決定的だからである。

代わりに、

・実命式が正式値である
・reading_contextへ正式値が届く
・AI payloadへ正式値が届く
・Responses APIが成功する
・結果がcompletedになる
・JSONならschema validationを通過する
・APIキーを結果へ露出しない

というシステム契約を検証する。

固定実命式
----------
1985-07-17
21:50
石川県
女性

Verified:
    年柱 乙丑
    月柱 癸未
    日柱 丁巳
    時柱 辛亥
    日主 丁

評価日時:
    2026-08-10 15:36

歳運:
    丙午

Version
-------
reading_generator_real_chart_live_v1
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from types import SimpleNamespace
from typing import Any, Dict

import pytest

from engine.chart import calculate_chart
from engine.reading_context import (
    build_reading_context,
)
from engine.reading_generator import (
    OPENAI_API_KEY_ENV,
    OPENAI_READING_MODEL_ENV,
    ReadingGenerationResult,
    build_generation_payload,
    generate_reading,
    get_default_model,
    has_openai_api_key,
)


# ============================================================
# Live test configuration
# ============================================================


LIVE_TEST_ENV = (
    "RUN_OPENAI_LIVE_TESTS"
)

LIVE_TEST_ENABLED_VALUE = "1"


def _live_test_enabled() -> bool:
    """
    明示的にlive testが有効化されているか。
    """

    return (
        os.getenv(
            LIVE_TEST_ENV,
            "",
        ).strip()
        == LIVE_TEST_ENABLED_VALUE
    )


def _live_test_skip_reason() -> str | None:
    """
    Live testを実行できない理由を返す。

    実行可能ならNone。
    """

    if not _live_test_enabled():
        return (
            f"{LIVE_TEST_ENV}=1 が設定されていないため"
            "OpenAI live testをskipします。"
        )

    if not has_openai_api_key():
        return (
            f"{OPENAI_API_KEY_ENV} が設定されていないため"
            "OpenAI live testをskipします。"
        )

    return None


pytestmark = pytest.mark.skipif(
    _live_test_skip_reason()
    is not None,
    reason=(
        _live_test_skip_reason()
        or ""
    ),
)


# ============================================================
# Golden data
# ============================================================


EXPECTED_PILLARS = {
    "year": "乙丑",
    "month": "癸未",
    "day": "丁巳",
    "hour": "辛亥",
}

EXPECTED_DAY_MASTER = "丁"

EXPECTED_ANNUAL_GANZHI = "丙午"


TARGET_DATETIME = datetime(
    2026,
    8,
    10,
    15,
    36,
)


# ============================================================
# Live generation policy
# ============================================================

# API料金を抑えるため、
# live testでは1セクションだけ生成する。
LIVE_SECTIONS = [
    "core_personality",
]

# JSON Schemaまで実APIで検証する。
LIVE_OUTPUT_FORMAT = "json"

# 通常の鑑定より小さめ。
# ただしsummary + section + disclaimerを
# 返せる余裕は残す。
LIVE_MAX_OUTPUT_TOKENS = 1600

# 推論コストを抑える。
LIVE_REASONING_EFFORT = "low"

# API側へ保存しない。
LIVE_STORE = False


# ============================================================
# Request fixtures
# ============================================================


@pytest.fixture
def verified_request():
    """
    外部暦照合済み実命式。
    """

    return SimpleNamespace(
        birth_date="1985-07-17",
        birth_time="21:50",
        birth_place="石川県",
        gender="female",
    )


@pytest.fixture
def real_chart_result(
    verified_request,
):
    """
    実際の四柱推命エンジンで命式を生成。
    """

    return calculate_chart(
        verified_request,
        target_datetime=(
            TARGET_DATETIME
        ),
    )


@pytest.fixture
def real_reading_context(
    real_chart_result,
):
    """
    実命式からAI入力contextを生成。
    """

    return build_reading_context(
        real_chart_result
    )


@pytest.fixture
def live_model():
    """
    実際に使用するモデル。

    OPENAI_READING_MODELがあれば優先。
    """

    return get_default_model()


# ============================================================
# Helpers
# ============================================================


def _extract_user_content(
    generation_payload: Dict[str, Any],
) -> str:
    """
    Responses API payloadから
    user prompt本文を取り出す。
    """

    payload = generation_payload[
        "payload"
    ]

    inputs = payload.get(
        "input"
    )

    if not isinstance(
        inputs,
        list,
    ):
        raise AssertionError(
            "payload['input']がlistではありません。"
        )

    if not inputs:
        raise AssertionError(
            "payload['input']が空です。"
        )

    first = inputs[
        0
    ]

    if not isinstance(
        first,
        dict,
    ):
        raise AssertionError(
            "payload['input'][0]がdictではありません。"
        )

    content = first.get(
        "content"
    )

    if not isinstance(
        content,
        str,
    ):
        raise AssertionError(
            "AIへ渡すcontentが文字列ではありません。"
        )

    if not content.strip():
        raise AssertionError(
            "AIへ渡すcontentが空です。"
        )

    return content


def _assert_verified_chart(
    chart_result: Dict[str, Any],
) -> None:
    """
    calculate_chart()の正式命式を検証。
    """

    chart = chart_result[
        "chart"
    ]

    for position, expected in (
        EXPECTED_PILLARS.items()
    ):
        assert (
            chart[
                position
            ][
                "pillar"
            ]
            == expected
        )

    assert (
        chart_result[
            "day_master"
        ][
            "stem"
        ]
        == EXPECTED_DAY_MASTER
    )


def _assert_verified_context(
    reading_context: Dict[str, Any],
) -> None:
    """
    reading_contextへ命式が正しく転送されたことを検証。
    """

    pillars = (
        reading_context[
            "natal_chart"
        ][
            "pillars"
        ]
    )

    for position, expected in (
        EXPECTED_PILLARS.items()
    ):
        assert (
            pillars[
                position
            ][
                "pillar"
            ]
            == expected
        )

    assert (
        reading_context[
            "day_master"
        ][
            "stem"
        ]
        == EXPECTED_DAY_MASTER
    )

    assert (
        reading_context[
            "luck"
        ][
            "annual_luck"
        ][
            "ganzhi"
        ]
        == EXPECTED_ANNUAL_GANZHI
    )


def _assert_verified_prompt_facts(
    user_content: str,
) -> None:
    """
    OpenAIへ送る直前のpromptに
    verified factsが存在することを確認。

    AIの出力文章ではなく、
    API入力を固定するテスト。
    """

    for fact in (
        "乙丑",
        "癸未",
        "丁巳",
        "辛亥",
        "丁",
        "丙午",
    ):
        assert (
            fact
            in user_content
        )


# ============================================================
# 1. Environment
# ============================================================


def test_live_environment_enabled():
    """
    pytestmarkを通過した場合、
    live test明示フラグが有効である。
    """

    assert (
        os.getenv(
            LIVE_TEST_ENV
        )
        == LIVE_TEST_ENABLED_VALUE
    )


def test_live_openai_api_key_configured():
    """
    APIキーが設定されていることだけ確認。

    値そのものは絶対にassert messageへ出さない。
    """

    assert (
        has_openai_api_key()
        is True
    )


def test_live_model_is_resolved(
    live_model,
):
    """
    モデル名が空でない。
    """

    assert isinstance(
        live_model,
        str,
    )

    assert (
        live_model.strip()
    )


# ============================================================
# 2. Real chart before API
# ============================================================


def test_live_real_chart_is_verified(
    real_chart_result,
):
    """
    API料金を使う前段で、
    元命式が正しいことを確認する。
    """

    _assert_verified_chart(
        real_chart_result
    )


def test_live_real_reading_context_is_verified(
    real_reading_context,
):
    """
    reading_contextまで正式値が維持される。
    """

    _assert_verified_context(
        real_reading_context
    )


# ============================================================
# 3. Payload before API
# ============================================================


def test_live_payload_contains_verified_chart(
    real_reading_context,
    live_model,
):
    """
    実APIへ渡す直前のpayloadに
    正しい命式が入っていることを確認する。

    このテスト自体はAPI通信しない。
    """

    generation = (
        build_generation_payload(
            real_reading_context,
            model=live_model,
            sections=(
                LIVE_SECTIONS
            ),
            output_format=(
                LIVE_OUTPUT_FORMAT
            ),
            max_output_tokens=(
                LIVE_MAX_OUTPUT_TOKENS
            ),
            reasoning_effort=(
                LIVE_REASONING_EFFORT
            ),
            store=(
                LIVE_STORE
            ),
        )
    )

    assert (
        generation[
            "model"
        ]
        == live_model
    )

    assert (
        generation[
            "sections"
        ]
        == LIVE_SECTIONS
    )

    payload = generation[
        "payload"
    ]

    assert (
        payload[
            "store"
        ]
        is False
    )

    assert (
        payload[
            "max_output_tokens"
        ]
        == LIVE_MAX_OUTPUT_TOKENS
    )

    assert (
        payload[
            "reasoning"
        ][
            "effort"
        ]
        == LIVE_REASONING_EFFORT
    )

    # JSON live testなので
    # Structured Outputsが有効。
    assert (
        payload[
            "text"
        ][
            "format"
        ][
            "type"
        ]
        == "json_schema"
    )

    assert (
        payload[
            "text"
        ][
            "format"
        ][
            "strict"
        ]
        is True
    )

    user_content = (
        _extract_user_content(
            generation
        )
    )

    _assert_verified_prompt_facts(
        user_content
    )


# ============================================================
# 4. Actual OpenAI Responses API
# ============================================================


def test_live_real_chart_openai_json_generation(
    real_reading_context,
    live_model,
):
    """
    本物のOpenAI Responses APIへ接続する
    最重要live E2Eテスト。

    ここだけが実際にAPI料金を使用する。

    JSON Schema validationは
    generate_reading()内部でも実行される。
    """

    result = generate_reading(
        real_reading_context,
        model=live_model,
        sections=(
            LIVE_SECTIONS
        ),
        output_format=(
            LIVE_OUTPUT_FORMAT
        ),
        max_output_tokens=(
            LIVE_MAX_OUTPUT_TOKENS
        ),
        reasoning_effort=(
            LIVE_REASONING_EFFORT
        ),
        store=(
            LIVE_STORE
        ),
    )

    assert isinstance(
        result,
        ReadingGenerationResult,
    )

    assert (
        result.output_format
        == "json"
    )

    assert (
        result.model
        == live_model
    )

    assert (
        result.sections
        == tuple(
            LIVE_SECTIONS
        )
    )

    assert (
        result.status
        == "completed"
    )

    assert (
        result.response_status
        in (
            None,
            "completed",
        )
    )

    assert isinstance(
        result.response_id,
        str,
    )

    assert (
        result.response_id.strip()
    )

    assert isinstance(
        result.text,
        str,
    )

    assert (
        result.text.strip()
    )

    assert isinstance(
        result.parsed,
        dict,
    )

    parsed = result.parsed

    # --------------------------------------------------------
    # Top-level JSON schema
    # --------------------------------------------------------

    assert set(
        parsed.keys()
    ) == {
        "summary",
        "sections",
        "disclaimer",
    }

    assert isinstance(
        parsed[
            "summary"
        ],
        str,
    )

    assert (
        parsed[
            "summary"
        ].strip()
    )

    assert isinstance(
        parsed[
            "disclaimer"
        ],
        str,
    )

    assert (
        parsed[
            "disclaimer"
        ].strip()
    )

    # --------------------------------------------------------
    # Requested sections only
    # --------------------------------------------------------

    sections = parsed[
        "sections"
    ]

    assert isinstance(
        sections,
        dict,
    )

    assert set(
        sections.keys()
    ) == set(
        LIVE_SECTIONS
    )

    personality = sections[
        "core_personality"
    ]

    assert set(
        personality.keys()
    ) == {
        "title",
        "summary",
        "detail",
        "evidence",
        "advice",
    }

    assert isinstance(
        personality[
            "title"
        ],
        str,
    )

    assert (
        personality[
            "title"
        ].strip()
    )

    assert isinstance(
        personality[
            "summary"
        ],
        str,
    )

    assert (
        personality[
            "summary"
        ].strip()
    )

    assert isinstance(
        personality[
            "detail"
        ],
        str,
    )

    assert (
        personality[
            "detail"
        ].strip()
    )

    assert isinstance(
        personality[
            "evidence"
        ],
        list,
    )

    assert isinstance(
        personality[
            "advice"
        ],
        list,
    )

    # --------------------------------------------------------
    # Usage
    # --------------------------------------------------------

    # SDK/API仕様によりusageがNoneのケースも
    # 理論上あり得るため、存在時だけ型確認。
    if result.usage is not None:
        assert isinstance(
            result.usage,
            dict,
        )


# ============================================================
# 5. Security
# ============================================================


def test_live_result_does_not_expose_api_key(
    real_reading_context,
    live_model,
):
    """
    APIキー値を結果に露出しないことを確認。

    注意:
    このテストもAPIを1回呼ぶと料金が増えるため、
    実通信はしない。

    build_generation_payloadだけで確認する。
    """

    api_key = os.getenv(
        OPENAI_API_KEY_ENV
    )

    assert api_key

    generation = (
        build_generation_payload(
            real_reading_context,
            model=live_model,
            sections=(
                LIVE_SECTIONS
            ),
            output_format=(
                LIVE_OUTPUT_FORMAT
            ),
            max_output_tokens=(
                LIVE_MAX_OUTPUT_TOKENS
            ),
            reasoning_effort=(
                LIVE_REASONING_EFFORT
            ),
            store=(
                LIVE_STORE
            ),
        )
    )

    serialized = json.dumps(
        generation,
        ensure_ascii=False,
        default=str,
    )

    assert (
        api_key
        not in serialized
    )


# ============================================================
# 6. Configuration diagnostics
# ============================================================


def test_live_configuration_summary(
    live_model,
):
    """
    Live test設定の最低限の整合性確認。

    APIキー値そのものは出力しない。
    """

    assert (
        LIVE_TEST_ENV
        == "RUN_OPENAI_LIVE_TESTS"
    )

    assert (
        OPENAI_API_KEY_ENV
        == "OPENAI_API_KEY"
    )

    assert (
        OPENAI_READING_MODEL_ENV
        == "OPENAI_READING_MODEL"
    )

    assert (
        LIVE_OUTPUT_FORMAT
        == "json"
    )

    assert (
        LIVE_STORE
        is False
    )

    assert (
        LIVE_REASONING_EFFORT
        == "low"
    )

    assert (
        LIVE_MAX_OUTPUT_TOKENS
        > 0
    )

    assert isinstance(
        live_model,
        str,
    )
