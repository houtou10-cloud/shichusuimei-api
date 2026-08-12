"""
tests/test_reading_generator_live.py

OpenAI Responses APIを実際に呼び出す
四柱推命AI鑑定のLIVE統合テスト。

重要
----
このテストは通常のpytest / GitHub Actionsでは実行しない。

実行には次の2条件が必要。

1. RUN_OPENAI_LIVE_TESTS=1
2. OPENAI_API_KEY が設定されている

つまり通常の

    PYTHONPATH=. pytest

では自動的にSKIPされる。

明示的にLIVEテストを行う場合だけ、

Linux / macOS:
    RUN_OPENAI_LIVE_TESTS=1 \
    OPENAI_API_KEY=... \
    PYTHONPATH=. \
    pytest tests/test_reading_generator_live.py -v

PowerShell:
    $env:RUN_OPENAI_LIVE_TESTS="1"
    $env:OPENAI_API_KEY="..."
    $env:PYTHONPATH="."
    pytest tests/test_reading_generator_live.py -v

を使用する。

目的
----
実際のパイプライン

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
Structured Outputs JSON
    ↓
JSON validation

が本番APIでも成立することを確認する。

注意
----
このテストはAPI料金を発生させる可能性がある。
CIの通常テストへ常時組み込まないこと。
"""

from __future__ import annotations

import os
from datetime import datetime
from types import SimpleNamespace

import pytest

from engine.chart import calculate_chart
from engine.reading_context import (
    build_reading_context,
)
from engine.reading_generator import (
    OPENAI_API_KEY_ENV,
    OPENAI_READING_MODEL_ENV,
    ReadingGenerationResult,
    generate_reading,
    get_default_model,
    has_openai_api_key,
)


# ============================================================
# Constants
# ============================================================


LIVE_TEST_ENV = "RUN_OPENAI_LIVE_TESTS"

# API料金と応答時間を抑えるため、
# LIVEテストでは1セクションだけ生成する。
LIVE_TEST_SECTIONS = (
    "career",
)

LIVE_TEST_MAX_OUTPUT_TOKENS = 8000
LIVE_TEST_REASONING_EFFORT = "minimal"

# 回帰基準として固定する出生データ。
VERIFIED_BIRTH_DATE = "1985-07-17"
VERIFIED_BIRTH_TIME = "21:50"
VERIFIED_BIRTH_PLACE = "石川県"
VERIFIED_GENDER = "female"

# 歳運を固定するためtarget_datetimeも固定する。
TARGET_DATETIME = datetime(
    2026,
    8,
    10,
    15,
    36,
)


# ============================================================
# LIVE test gate
# ============================================================


def _live_test_requested() -> bool:
    """
    RUN_OPENAI_LIVE_TESTS=1 の場合だけTrue。
    """

    value = os.getenv(
        LIVE_TEST_ENV,
        "",
    )

    return (
        isinstance(
            value,
            str,
        )
        and value.strip()
        == "1"
    )


LIVE_TEST_REQUESTED = (
    _live_test_requested()
)

API_KEY_CONFIGURED = (
    has_openai_api_key()
)


pytestmark = [
    pytest.mark.skipif(
        not LIVE_TEST_REQUESTED,
        reason=(
            "OpenAI LIVE test disabled. "
            "Set RUN_OPENAI_LIVE_TESTS=1 "
            "to enable."
        ),
    ),
    pytest.mark.skipif(
        not API_KEY_CONFIGURED,
        reason=(
            "OPENAI_API_KEY is not configured."
        ),
    ),
]


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture(
    scope="module"
)
def verified_request():
    """
    calculate_chart()用の固定入力。
    """

    return SimpleNamespace(
        birth_date=VERIFIED_BIRTH_DATE,
        birth_time=VERIFIED_BIRTH_TIME,
        birth_place=VERIFIED_BIRTH_PLACE,
        gender=VERIFIED_GENDER,
    )


@pytest.fixture(
    scope="module"
)
def verified_chart_result(
    verified_request,
):
    """
    実エンジンで命式を計算する。
    """

    return calculate_chart(
        verified_request,
        target_datetime=TARGET_DATETIME,
    )


@pytest.fixture(
    scope="module"
)
def live_reading_context(
    verified_chart_result,
):
    """
    実計算結果からreading_context_v1を生成する。
    """

    return build_reading_context(
        verified_chart_result
    )


@pytest.fixture(
    scope="module"
)
def live_result(
    live_reading_context,
):
    """
    OpenAI Responses APIを1回だけ呼ぶ。

    module scopeにすることで、
    LIVEテスト全体でAPI呼び出しを
    1回に限定する。
    """

    return generate_reading(
        live_reading_context,
        model=get_default_model(),
        sections=LIVE_TEST_SECTIONS,
        output_format="json",
        max_output_tokens=(
            LIVE_TEST_MAX_OUTPUT_TOKENS
        ),
        store=False,
    )


# ============================================================
# 1. Gate / configuration
# ============================================================


def test_live_environment_enabled():
    """
    LIVEテストが意図的に有効化されていることを確認。
    """

    assert (
        os.getenv(
            LIVE_TEST_ENV
        )
        == "1"
    )


def test_live_api_key_is_configured():
    """
    APIキーの値そのものは確認・表示しない。
    """

    assert (
        has_openai_api_key()
        is True
    )


def test_live_model_is_non_empty():
    """
    実際に使用するmodel名が取得できることを確認。
    """

    model = get_default_model()

    assert isinstance(
        model,
        str,
    )

    assert (
        model.strip()
    )


# ============================================================
# 2. Pre-AI real engine validation
# ============================================================


def test_live_context_schema(
    live_reading_context,
):
    assert (
        live_reading_context[
            "schema_version"
        ]
        == "reading_context_v1"
    )

    assert (
        live_reading_context[
            "status"
        ]
        == "ready_for_ai_reading"
    )


def test_live_context_verified_four_pillars(
    live_reading_context,
):
    """
    AIへ送信する前の四柱が
    回帰基準どおりであることを確認する。

    AIはこの値を再計算してはならない。
    """

    assert (
        live_reading_context[
            "natal_chart"
        ][
            "pillar_sequence"
        ]
        == [
            "乙丑",
            "癸未",
            "丁巳",
            "辛亥",
        ]
    )


def test_live_context_verified_day_master(
    live_reading_context,
):
    assert (
        live_reading_context[
            "day_master"
        ][
            "stem"
        ]
        == "丁"
    )


def test_live_context_verified_2026_annual_luck(
    live_reading_context,
):
    annual = live_reading_context[
        "luck"
    ][
        "annual_luck"
    ]

    assert (
        annual[
            "ganzhi"
        ]
        == "丙午"
    )

    assert (
        annual[
            "stem_ten_god"
        ]
        == "劫財"
    )

    assert (
        annual[
            "twelve_stage"
        ]
        == "建禄"
    )


# ============================================================
# 3. OpenAI LIVE response
# ============================================================


def test_live_result_type(
    live_result,
):
    assert isinstance(
        live_result,
        ReadingGenerationResult,
    )


def test_live_result_completed(
    live_result,
):
    """
    Responses APIが正常完了したことを確認する。
    """

    assert (
        live_result.response_status
        == "completed"
    )

    assert (
        live_result.status
        == "completed"
    )


def test_live_result_has_response_id(
    live_result,
):
    """
    OpenAI response idが返ることを確認する。
    """

    assert isinstance(
        live_result.response_id,
        str,
    )

    assert (
        live_result.response_id.strip()
    )


def test_live_result_is_json(
    live_result,
):
    assert (
        live_result.output_format
        == "json"
    )

    assert isinstance(
        live_result.parsed,
        dict,
    )


def test_live_result_model(
    live_result,
):
    assert (
        live_result.model
        == get_default_model()
    )


def test_live_result_sections(
    live_result,
):
    assert (
        live_result.sections
        == LIVE_TEST_SECTIONS
    )


# ============================================================
# 4. Structured Outputs contract
# ============================================================


def test_live_json_top_level_contract(
    live_result,
):
    parsed = live_result.parsed

    assert parsed is not None

    assert set(
        parsed.keys()
    ) == {
        "summary",
        "sections",
        "disclaimer",
    }


def test_live_json_summary(
    live_result,
):
    parsed = live_result.parsed

    assert parsed is not None

    summary = parsed[
        "summary"
    ]

    assert isinstance(
        summary,
        str,
    )

    assert (
        summary.strip()
    )


def test_live_json_disclaimer(
    live_result,
):
    parsed = live_result.parsed

    assert parsed is not None

    disclaimer = parsed[
        "disclaimer"
    ]

    assert isinstance(
        disclaimer,
        str,
    )

    assert (
        disclaimer.strip()
    )


def test_live_json_contains_only_requested_section(
    live_result,
):
    parsed = live_result.parsed

    assert parsed is not None

    assert set(
        parsed[
            "sections"
        ].keys()
    ) == {
        "career",
    }


def test_live_career_section_contract(
    live_result,
):
    parsed = live_result.parsed

    assert parsed is not None

    career = parsed[
        "sections"
    ][
        "career"
    ]

    assert set(
        career.keys()
    ) == {
        "title",
        "summary",
        "detail",
        "evidence",
        "advice",
    }

    assert isinstance(
        career[
            "title"
        ],
        str,
    )

    assert isinstance(
        career[
            "summary"
        ],
        str,
    )

    assert isinstance(
        career[
            "detail"
        ],
        str,
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


def test_live_career_text_is_not_empty(
    live_result,
):
    parsed = live_result.parsed

    assert parsed is not None

    career = parsed[
        "sections"
    ][
        "career"
    ]

    assert (
        career[
            "title"
        ].strip()
    )

    assert (
        career[
            "summary"
        ].strip()
    )

    assert (
        career[
            "detail"
        ].strip()
    )


# ============================================================
# 5. Fact-preservation smoke checks
# ============================================================


def test_live_reading_does_not_change_day_master(
    live_result,
):
    """
    AI文章内の表現を完全一致させるテストではなく、
    evidence/detailで別の日主を事実として
    作っていないかを見る最低限のスモークテスト。

    Structured Outputの自由文は表現揺れがあるため、
    正しい語が必ず登場することまでは要求しない。
    """

    parsed = live_result.parsed

    assert parsed is not None

    serialized = str(
        parsed
    )

    # 明確に別の日主へ置き換える事故を防ぐ。
    forbidden_phrases = (
        "日主は甲",
        "日主は乙",
        "日主は丙",
        "日主は戊",
        "日主は己",
        "日主は庚",
        "日主は辛",
        "日主は壬",
        "日主は癸",
    )

    for phrase in (
        forbidden_phrases
    ):
        assert (
            phrase
            not in serialized
        )


def test_live_reading_does_not_change_annual_ganzhi(
    live_result,
):
    """
    2026年歳運を別干支へ再計算する事故の
    最低限チェック。

    AIが干支そのものを書かない可能性もあるため、
    「丙午の記載必須」にはしない。
    """

    parsed = live_result.parsed

    assert parsed is not None

    serialized = str(
        parsed
    )

    obvious_wrong_2026_phrases = (
        "2026年は乙巳",
        "2026年は丁未",
        "2026年の歳運は乙巳",
        "2026年の歳運は丁未",
    )

    for phrase in (
        obvious_wrong_2026_phrases
    ):
        assert (
            phrase
            not in serialized
        )


# ============================================================
# 6. Usage / privacy
# ============================================================


def test_live_result_usage_is_mapping(
    live_result,
):
    assert isinstance(
        live_result.usage,
        dict,
    )


def test_live_store_is_disabled_by_design(
    live_reading_context,
    monkeypatch,
):
    """
    実APIを追加で呼ばず、
    build payloadをpatchして
    LIVE fixtureの方針と同じstore=Falseを確認する。
    """

    from engine.reading_generator import (
        build_generation_payload,
    )

    generated = (
        build_generation_payload(
            live_reading_context,
            model=get_default_model(),
            sections=LIVE_TEST_SECTIONS,
            output_format="json",
            max_output_tokens=(
                LIVE_TEST_MAX_OUTPUT_TOKENS
            ),
            store=False,
        )
    )

    assert (
        generated[
            "payload"
        ][
            "store"
        ]
        is False
    )


# ============================================================
# 7. Final LIVE smoke
# ============================================================


def test_live_end_to_end_smoke(
    live_reading_context,
    live_result,
):
    """
    最終LIVEスモークテスト。

    実命式
        ↓
    reading_context
        ↓
    reading_prompt
        ↓
    OpenAI Responses API
        ↓
    Structured Outputs JSON

    が1本につながっていることを確認する。
    """

    assert (
        live_reading_context[
            "day_master"
        ][
            "stem"
        ]
        == "丁"
    )

    assert (
        live_reading_context[
            "luck"
        ][
            "annual_luck"
        ][
            "ganzhi"
        ]
        == "丙午"
    )

    assert (
        live_result.response_status
        == "completed"
    )

    assert (
        live_result.parsed
        is not None
    )

    assert (
        "career"
        in live_result.parsed[
            "sections"
        ]
    )

    career = live_result.parsed[
        "sections"
    ][
        "career"
    ]

    assert (
        career[
            "detail"
        ].strip()
    )

    assert (
        isinstance(
            career[
                "evidence"
            ],
            list,
        )
    )

    assert (
        isinstance(
            career[
                "advice"
            ],
            list,
        )
    )