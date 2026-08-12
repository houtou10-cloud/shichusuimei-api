"""
tests/test_reading_product_quality_multi_chart_live.py

複数の実命式を使った OpenAI LIVE 商品品質テスト。

目的
----
単一命式だけでなく、複数の外部照合済み命式について、

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
    商品向けJSON鑑定

までを本物のAPI通信で確認する。

このテストで確認すること
------------------------
1. 各命式の四柱・日主が正式値のまま維持される。
2. reading_contextへ正式値が維持される。
3. APIへ渡すpromptに各命式の正式値が含まれる。
4. OpenAI Responses APIが completed で終了する。
5. Structured Outputs のJSON Schemaを通過する。
6. requested sectionだけが返る。
7. summary / detail / evidence / advice が商品として最低限成立する。
8. 別命式の内容が混線しない。
9. 顧客向け文章に主要な内部キー名が露出しない。
10. 健康や未来について危険な断定をしないための
    prompt guardrail がAPI入力に存在する。
11. APIキーを結果やpayloadへ露出しない。

API料金について
--------------
このファイルは本物のOpenAI APIを使用する。

通常CIではskipする。

実行条件:
    RUN_OPENAI_LIVE_TESTS=1
    OPENAI_API_KEY=<設定済み>

API料金を抑えるため、
各命式につき core_personality 1セクションのみ生成する。

複数のtest関数で同じAPIレスポンスを再利用するため、
live_result fixtureは module scope とする。

Version
-------
reading_product_quality_multi_chart_live_v1
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from types import SimpleNamespace
from typing import Any, Dict, Mapping, Tuple

import pytest

from engine.chart import calculate_chart
from engine.reading_context import build_reading_context
from engine.reading_generator import (
    OPENAI_API_KEY_ENV,
    ReadingGenerationResult,
    build_generation_payload,
    generate_reading,
    get_default_model,
    has_openai_api_key,
)


# ============================================================
# Live configuration
# ============================================================


LIVE_TEST_ENV = "RUN_OPENAI_LIVE_TESTS"
LIVE_TEST_ENABLED_VALUE = "1"

LIVE_SECTIONS = (
    "core_personality",
)

LIVE_OUTPUT_FORMAT = "json"
LIVE_MAX_OUTPUT_TOKENS = 8000
LIVE_REASONING_EFFORT = "minimal"
LIVE_STORE = False

TARGET_DATETIME = datetime(
    2026,
    8,
    10,
    15,
    36,
)

EXPECTED_ANNUAL_GANZHI = "丙午"


def _live_test_enabled() -> bool:
    return (
        os.getenv(
            LIVE_TEST_ENV,
            "",
        ).strip()
        == LIVE_TEST_ENABLED_VALUE
    )


def _live_test_skip_reason() -> str | None:
    if not _live_test_enabled():
        return (
            f"{LIVE_TEST_ENV}=1 が設定されていないため"
            "multi-chart live testをskipします。"
        )

    if not has_openai_api_key():
        return (
            f"{OPENAI_API_KEY_ENV} が設定されていないため"
            "multi-chart live testをskipします。"
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
# Verified golden charts
# ============================================================


@dataclass(frozen=True)
class LiveChartCase:
    case_id: str
    birth_date: str
    birth_time: str
    birth_place: str
    gender: str

    year_pillar: str
    month_pillar: str
    day_pillar: str
    hour_pillar: str
    day_master: str

    @property
    def expected_pillars(
        self,
    ) -> Dict[str, str]:
        return {
            "year": self.year_pillar,
            "month": self.month_pillar,
            "day": self.day_pillar,
            "hour": self.hour_pillar,
        }

    @property
    def pillar_sequence(
        self,
    ) -> Tuple[str, str, str, str]:
        return (
            self.year_pillar,
            self.month_pillar,
            self.day_pillar,
            self.hour_pillar,
        )


LIVE_CASES = (
    LiveChartCase(
        case_id="1985_ishikawa_female",
        birth_date="1985-07-17",
        birth_time="21:50",
        birth_place="石川県",
        gender="female",
        year_pillar="乙丑",
        month_pillar="癸未",
        day_pillar="丁巳",
        hour_pillar="辛亥",
        day_master="丁",
    ),
    LiveChartCase(
        case_id="1984_hokkaido_female",
        birth_date="1984-07-22",
        birth_time="04:15",
        birth_place="北海道",
        gender="female",
        year_pillar="甲子",
        month_pillar="辛未",
        day_pillar="丁巳",
        hour_pillar="壬寅",
        day_master="丁",
    ),
    LiveChartCase(
        case_id="1984_tokyo_male",
        birth_date="1984-07-21",
        birth_time="12:00",
        birth_place="東京都",
        gender="male",
        year_pillar="甲子",
        month_pillar="辛未",
        day_pillar="丙辰",
        hour_pillar="甲午",
        day_master="丙",
    ),
)


LIVE_CASE_IDS = tuple(
    case.case_id
    for case in LIVE_CASES
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture(
    scope="module",
    params=LIVE_CASES,
    ids=LIVE_CASE_IDS,
)
def live_case(
    request,
) -> LiveChartCase:
    return request.param


@pytest.fixture(
    scope="module",
)
def live_request(
    live_case: LiveChartCase,
):
    return SimpleNamespace(
        birth_date=live_case.birth_date,
        birth_time=live_case.birth_time,
        birth_place=live_case.birth_place,
        gender=live_case.gender,
    )


@pytest.fixture(
    scope="module",
)
def live_chart_result(
    live_request,
):
    return calculate_chart(
        live_request,
        target_datetime=TARGET_DATETIME,
    )


@pytest.fixture(
    scope="module",
)
def live_reading_context(
    live_chart_result,
):
    return build_reading_context(
        live_chart_result
    )


@pytest.fixture(
    scope="module",
)
def live_model():
    return get_default_model()


@pytest.fixture(
    scope="module",
)
def live_generation_payload(
    live_reading_context,
    live_model,
):
    return build_generation_payload(
        live_reading_context,
        model=live_model,
        sections=LIVE_SECTIONS,
        output_format=LIVE_OUTPUT_FORMAT,
        max_output_tokens=LIVE_MAX_OUTPUT_TOKENS,
        reasoning_effort=LIVE_REASONING_EFFORT,
        store=LIVE_STORE,
    )


@pytest.fixture(
    scope="module",
)
def live_result(
    live_reading_context,
    live_model,
):
    """
    1命式につきAPIを1回だけ呼ぶ。

    LIVE_CASESが3件なので、
    このファイル全体でAPI通信は3回。
    """

    return generate_reading(
        live_reading_context,
        model=live_model,
        sections=LIVE_SECTIONS,
        output_format=LIVE_OUTPUT_FORMAT,
        max_output_tokens=LIVE_MAX_OUTPUT_TOKENS,
        reasoning_effort=LIVE_REASONING_EFFORT,
        store=LIVE_STORE,
    )


# ============================================================
# Helpers
# ============================================================


def _non_empty(
    value: Any,
    name: str,
) -> str:
    assert isinstance(
        value,
        str,
    ), (
        f"{name} はstrである必要があります。"
    )

    value = value.strip()

    assert value, (
        f"{name} が空です。"
    )

    return value


def _extract_user_content(
    generation: Mapping[str, Any],
) -> str:
    payload = generation[
        "payload"
    ]

    inputs = payload.get(
        "input"
    )

    assert isinstance(
        inputs,
        list,
    )

    assert inputs

    first = inputs[
        0
    ]

    assert isinstance(
        first,
        Mapping,
    )

    return _non_empty(
        first.get(
            "content"
        ),
        "payload.input[0].content",
    )


def _extract_system_prompt(
    generation: Mapping[str, Any],
) -> str:
    return _non_empty(
        generation[
            "payload"
        ].get(
            "instructions"
        ),
        "payload.instructions",
    )


def _assert_chart_matches_case(
    chart_result: Mapping[str, Any],
    case: LiveChartCase,
) -> None:
    chart = chart_result[
        "chart"
    ]

    for position, expected in (
        case.expected_pillars.items()
    ):
        actual = (
            chart[
                position
            ][
                "pillar"
            ]
        )

        assert (
            actual
            == expected
        ), (
            f"{case.case_id}: "
            f"{position}柱が不一致です。"
            f" expected={expected},"
            f" actual={actual}"
        )

    assert (
        chart_result[
            "day_master"
        ][
            "stem"
        ]
        == case.day_master
    )


def _assert_context_matches_case(
    context: Mapping[str, Any],
    case: LiveChartCase,
) -> None:
    pillars = (
        context[
            "natal_chart"
        ][
            "pillars"
        ]
    )

    for position, expected in (
        case.expected_pillars.items()
    ):
        actual = (
            pillars[
                position
            ][
                "pillar"
            ]
        )

        assert (
            actual
            == expected
        ), (
            f"{case.case_id}: "
            "reading_contextで"
            f"{position}柱が変化しています。"
        )

    assert (
        context[
            "day_master"
        ][
            "stem"
        ]
        == case.day_master
    )

    assert (
        context[
            "luck"
        ][
            "annual_luck"
        ][
            "ganzhi"
        ]
        == EXPECTED_ANNUAL_GANZHI
    )


def _section(
    result: ReadingGenerationResult,
) -> Mapping[str, Any]:
    parsed = result.parsed

    assert isinstance(
        parsed,
        dict,
    )

    sections = parsed[
        "sections"
    ]

    assert isinstance(
        sections,
        Mapping,
    )

    return sections[
        "core_personality"
    ]


def _customer_facing_text(
    result: ReadingGenerationResult,
) -> str:
    """
    顧客向け主要文章を1本へ結合する。

    evidenceは別テストで確認する。
    """

    parsed = result.parsed
    section = _section(
        result
    )

    parts = [
        parsed.get(
            "summary",
            "",
        ),
        section.get(
            "title",
            "",
        ),
        section.get(
            "summary",
            "",
        ),
        section.get(
            "detail",
            "",
        ),
        *section.get(
            "advice",
            [],
        ),
        parsed.get(
            "disclaimer",
            "",
        ),
    ]

    return "\n".join(
        str(
            part
        )
        for part in parts
    )


# ============================================================
# 1. Environment
# ============================================================


def test_multi_live_environment_enabled():
    assert (
        os.getenv(
            LIVE_TEST_ENV
        )
        == LIVE_TEST_ENABLED_VALUE
    )


def test_multi_live_api_key_configured():
    assert (
        has_openai_api_key()
        is True
    )


def test_multi_live_model_is_resolved(
    live_model,
):
    _non_empty(
        live_model,
        "live_model",
    )


# ============================================================
# 2. Golden chart before API
# ============================================================


def test_multi_live_chart_is_verified(
    live_case,
    live_chart_result,
):
    _assert_chart_matches_case(
        live_chart_result,
        live_case,
    )


def test_multi_live_context_is_verified(
    live_case,
    live_reading_context,
):
    _assert_context_matches_case(
        live_reading_context,
        live_case,
    )


def test_multi_live_context_is_ready(
    live_reading_context,
):
    assert (
        live_reading_context[
            "status"
        ]
        == "ready_for_ai_reading"
    )

    assert (
        live_reading_context[
            "method"
        ]
        == "reading_context_v1"
    )


# ============================================================
# 3. Payload before API
# ============================================================


def test_multi_live_payload_contains_own_chart(
    live_case,
    live_generation_payload,
):
    prompt = _extract_user_content(
        live_generation_payload
    )

    for pillar in (
        live_case.pillar_sequence
    ):
        assert pillar in prompt

    assert (
        live_case.day_master
        in prompt
    )

    assert (
        EXPECTED_ANNUAL_GANZHI
        in prompt
    )


def test_multi_live_payload_uses_expected_policy(
    live_generation_payload,
):
    payload = live_generation_payload[
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


def test_multi_live_payload_has_recalculation_guards(
    live_generation_payload,
):
    user_prompt = _extract_user_content(
        live_generation_payload
    )

    for phrase in (
        "日主を再判定しない",
        "格局を再判定しない",
        "用神を再選定しない",
        "大運を再計算しない",
        "歳運を再計算しない",
    ):
        assert phrase in user_prompt


def test_multi_live_payload_has_product_quality_guards(
    live_generation_payload,
):
    system_prompt = (
        _extract_system_prompt(
            live_generation_payload
        )
    )

    for phrase in (
        "再計算しない",
        "入力された計算結果",
        "医学的診断",
        "確定的",
        "具体的な回数",
        "職業",
        "事業形態",
        "同じ五行",
        "evidence",
        "自然な日本語",
    ):
        assert phrase in system_prompt


# ============================================================
# 4. Actual OpenAI API
# ============================================================


def test_multi_live_result_type(
    live_result,
):
    assert isinstance(
        live_result,
        ReadingGenerationResult,
    )


def test_multi_live_result_completed(
    live_result,
):
    assert (
        live_result.status
        == "completed"
    )

    assert (
        live_result.response_status
        in (
            None,
            "completed",
        )
    )


def test_multi_live_result_has_response_id(
    live_result,
):
    _non_empty(
        live_result.response_id,
        "response_id",
    )


def test_multi_live_result_model_matches(
    live_result,
    live_model,
):
    assert (
        live_result.model
        == live_model
    )


def test_multi_live_result_requested_section_only(
    live_result,
):
    assert (
        live_result.sections
        == LIVE_SECTIONS
    )

    parsed = live_result.parsed

    assert isinstance(
        parsed,
        dict,
    )

    assert set(
        parsed[
            "sections"
        ].keys()
    ) == set(
        LIVE_SECTIONS
    )


def test_multi_live_json_top_level_contract(
    live_result,
):
    parsed = live_result.parsed

    assert set(
        parsed.keys()
    ) == {
        "summary",
        "sections",
        "disclaimer",
    }

    _non_empty(
        parsed[
            "summary"
        ],
        "summary",
    )

    _non_empty(
        parsed[
            "disclaimer"
        ],
        "disclaimer",
    )


def test_multi_live_section_contract(
    live_result,
):
    section = _section(
        live_result
    )

    assert set(
        section.keys()
    ) == {
        "title",
        "summary",
        "detail",
        "evidence",
        "advice",
    }

    _non_empty(
        section[
            "title"
        ],
        "section.title",
    )

    _non_empty(
        section[
            "summary"
        ],
        "section.summary",
    )

    _non_empty(
        section[
            "detail"
        ],
        "section.detail",
    )

    assert isinstance(
        section[
            "evidence"
        ],
        list,
    )

    assert isinstance(
        section[
            "advice"
        ],
        list,
    )


# ============================================================
# 5. Minimum product quality
# ============================================================


def test_multi_live_evidence_has_content(
    live_result,
):
    evidence = (
        _section(
            live_result
        )[
            "evidence"
        ]
    )

    assert evidence

    assert all(
        isinstance(
            item,
            str,
        )
        and item.strip()
        for item in evidence
    )


def test_multi_live_advice_has_content(
    live_result,
):
    advice = (
        _section(
            live_result
        )[
            "advice"
        ]
    )

    assert advice

    assert all(
        isinstance(
            item,
            str,
        )
        and item.strip()
        for item in advice
    )


def test_multi_live_customer_text_has_no_major_internal_keys(
    live_result,
):
    """
    summary / detail / advice等へ
    実装内部キーが露出していないことを確認。
    """

    text = _customer_facing_text(
        live_result
    )

    forbidden = (
        "technical_pattern",
        "weighted_scores",
        "overall_level",
        "overall_score",
        "agreement_level",
        "primary_useful_element",
        "secondary_useful_elements",
        "branch_useful_relation",
        "progress_percent",
        "current_pillar=",
        "day_master.",
        "natal_chart.",
        "integrated_luck.",
    )

    for marker in forbidden:
        assert marker not in text


def test_multi_live_evidence_is_customer_readable(
    live_result,
):
    """
    evidenceでも代表的な内部パス露出を避ける。
    """

    evidence_text = "\n".join(
        _section(
            live_result
        )[
            "evidence"
        ]
    )

    forbidden = (
        "day_master.",
        "natal_chart.",
        "pattern.primary_pattern",
        "five_elements.weighted_scores",
        "useful_gods.primary_useful_element",
        "integrated_luck.overall_level",
        "current_luck.current_pillar",
    )

    for marker in forbidden:
        assert marker not in evidence_text


def test_multi_live_disclaimer_is_safe(
    live_result,
):
    disclaimer = (
        live_result.parsed[
            "disclaimer"
        ]
    )

    assert isinstance(
        disclaimer,
        str,
    )

    assert (
        disclaimer.strip()
    )

    # core_personalityのみを生成するLIVEテストでは、
    # 健康セクション自体を要求していない。
    # そのため「医学」「医療」という固定語ではなく、
    # 将来を断定しないことと、重要判断を占いだけで
    # 完結させないことを確認する。
    assert (
        "断定"
        in disclaimer
        or "傾向"
        in disclaimer
        or "参考"
        in disclaimer
    )

    assert (
        "専門家"
        in disclaimer
        or "現実"
        in disclaimer
        or "実際"
        in disclaimer
    )


# ============================================================
# 6. Security
# ============================================================


def test_multi_live_payload_never_exposes_api_key(
    live_generation_payload,
):
    api_key = os.getenv(
        OPENAI_API_KEY_ENV
    )

    assert api_key

    serialized = json.dumps(
        live_generation_payload,
        ensure_ascii=False,
        default=str,
    )

    assert (
        api_key
        not in serialized
    )


def test_multi_live_result_never_exposes_api_key(
    live_result,
):
    api_key = os.getenv(
        OPENAI_API_KEY_ENV
    )

    assert api_key

    serialized = json.dumps(
        {
            "text": live_result.text,
            "parsed": live_result.parsed,
            "usage": live_result.usage,
            "response_id": (
                live_result.response_id
            ),
        },
        ensure_ascii=False,
        default=str,
    )

    assert (
        api_key
        not in serialized
    )


# ============================================================
# 7. Usage
# ============================================================


def test_multi_live_usage_is_valid_when_present(
    live_result,
):
    if live_result.usage is None:
        return

    assert isinstance(
        live_result.usage,
        dict,
    )

    total_tokens = (
        live_result.usage.get(
            "total_tokens"
        )
    )

    if total_tokens is not None:
        assert isinstance(
            total_tokens,
            int,
        )

        assert (
            total_tokens
            > 0
        )


# ============================================================
# 8. Per-case final gate
# ============================================================


def test_reading_product_quality_multi_chart_live_v1_final_gate(
    live_case,
    live_chart_result,
    live_reading_context,
    live_generation_payload,
    live_result,
):
    # Pre-API facts
    _assert_chart_matches_case(
        live_chart_result,
        live_case,
    )

    _assert_context_matches_case(
        live_reading_context,
        live_case,
    )

    prompt = _extract_user_content(
        live_generation_payload
    )

    for pillar in (
        live_case.pillar_sequence
    ):
        assert pillar in prompt

    assert (
        live_case.day_master
        in prompt
    )

    # API result
    assert isinstance(
        live_result,
        ReadingGenerationResult,
    )

    assert (
        live_result.status
        == "completed"
    )

    assert (
        live_result.output_format
        == "json"
    )

    assert (
        live_result.sections
        == LIVE_SECTIONS
    )

    parsed = live_result.parsed

    assert isinstance(
        parsed,
        dict,
    )

    assert set(
        parsed.keys()
    ) == {
        "summary",
        "sections",
        "disclaimer",
    }

    assert set(
        parsed[
            "sections"
        ].keys()
    ) == set(
        LIVE_SECTIONS
    )

    section = _section(
        live_result
    )

    _non_empty(
        section[
            "summary"
        ],
        "section.summary",
    )

    _non_empty(
        section[
            "detail"
        ],
        "section.detail",
    )

    assert (
        section[
            "evidence"
        ]
    )

    assert (
        section[
            "advice"
        ]
    )
