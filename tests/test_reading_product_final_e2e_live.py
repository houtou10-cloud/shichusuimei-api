"""
tests/test_reading_product_final_e2e_live.py

四柱推命AI鑑定 商品版・最終E2E LIVEテスト。

目的
----
複数の外部照合済み実命式について、

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
    8セクション完全鑑定

までを本物のAPI通信で一気通貫に検証する。

このテストは、
単なるAPI疎通ではなく「商品版の最終ゲート」である。

検証内容
--------
1. 外部照合済み四柱が calculate_chart() で維持される。
2. 日主が reading_context まで維持される。
3. 歳運が固定評価日時で維持される。
4. 8セクションすべてを要求する。
5. OpenAI Responses API が completed で終了する。
6. Structured Outputs のJSON Schemaを通過する。
7. 8セクションすべてに
   title / summary / detail / evidence / advice が存在する。
8. evidence / advice が空でない。
9. 顧客向け文章へ主要な内部キー名を露出しない。
10. evidenceも顧客向け日本語として読める。
11. APIキーをpayload/resultへ露出しない。
12. disclaimerが空でなく最低限の長さを持つ。
13. 健康セクションが医学的診断にならない。
14. 将来・現在運が確定的な未来予言にならない。
15. 命式ごとに生成結果が同一文章へ収束しない。
16. 1ケースにつきAPI通信は1回だけ。
17. 最終的に商品版E2E gateを通過する。

通常CI
------
本物のOpenAI APIと料金を使用するため、
通常のpytest / GitHub Actionsではskipする。

実行条件
--------
RUN_OPENAI_LIVE_TESTS=1

OPENAI_API_KEY=<設定済み>

OPENAI_READING_MODEL は任意。
未設定時は reading_generator.py の
get_default_model() に従う。

APIコスト
---------
3命式 × 8セクション。

ただし、
各命式につき generate_reading() は1回のみ。

module scope fixtureで結果を再利用するため、
このファイル全体のAPI通信は3回。

Version
-------
reading_product_final_e2e_live_v1
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

ALL_SECTIONS = (
    "core_personality",
    "career",
    "wealth",
    "relationships",
    "health",
    "current_luck",
    "future_flow",
    "advice",
)

LIVE_OUTPUT_FORMAT = "json"

# 8セクション商品版なので十分な余裕を持たせる。
LIVE_MAX_OUTPUT_TOKENS = 8000

# JSON完走を優先し、推論コストを抑える。
LIVE_REASONING_EFFORT = "minimal"

# API側へ保存しない。
LIVE_STORE = False

# current_luck / annual_luck を再現可能にする。
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
            "商品版E2E LIVEテストをskipします。"
        )

    if not has_openai_api_key():
        return (
            f"{OPENAI_API_KEY_ENV} が設定されていないため"
            "商品版E2E LIVEテストをskipします。"
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
class ProductLiveCase:
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


PRODUCT_CASES = (
    ProductLiveCase(
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
    ProductLiveCase(
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
    ProductLiveCase(
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


PRODUCT_CASE_IDS = tuple(
    case.case_id
    for case in PRODUCT_CASES
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture(
    scope="module",
    params=PRODUCT_CASES,
    ids=PRODUCT_CASE_IDS,
)
def product_case(
    request,
) -> ProductLiveCase:
    return request.param


@pytest.fixture(
    scope="module",
)
def product_request(
    product_case: ProductLiveCase,
):
    return SimpleNamespace(
        birth_date=product_case.birth_date,
        birth_time=product_case.birth_time,
        birth_place=product_case.birth_place,
        gender=product_case.gender,
    )


@pytest.fixture(
    scope="module",
)
def product_chart_result(
    product_request,
):
    return calculate_chart(
        product_request,
        target_datetime=TARGET_DATETIME,
    )


@pytest.fixture(
    scope="module",
)
def product_reading_context(
    product_chart_result,
):
    return build_reading_context(
        product_chart_result
    )


@pytest.fixture(
    scope="module",
)
def product_model():
    return get_default_model()


@pytest.fixture(
    scope="module",
)
def product_generation_payload(
    product_reading_context,
    product_model,
):
    return build_generation_payload(
        product_reading_context,
        model=product_model,
        sections=ALL_SECTIONS,
        output_format=LIVE_OUTPUT_FORMAT,
        max_output_tokens=LIVE_MAX_OUTPUT_TOKENS,
        reasoning_effort=LIVE_REASONING_EFFORT,
        store=LIVE_STORE,
    )


@pytest.fixture(
    scope="module",
)
def product_result(
    product_reading_context,
    product_model,
):
    """
    1命式につきAPI通信は1回だけ。

    PRODUCT_CASESは3件なので、
    このファイル全体では3回だけ通信する。
    """

    return generate_reading(
        product_reading_context,
        model=product_model,
        sections=ALL_SECTIONS,
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
    case: ProductLiveCase,
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
    ), (
        f"{case.case_id}: 日主が不一致です。"
    )


def _assert_context_matches_case(
    context: Mapping[str, Any],
    case: ProductLiveCase,
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


def _assert_section_contract(
    section_name: str,
    section: Mapping[str, Any],
) -> None:
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
        f"{section_name}.title",
    )

    _non_empty(
        section[
            "summary"
        ],
        f"{section_name}.summary",
    )

    _non_empty(
        section[
            "detail"
        ],
        f"{section_name}.detail",
    )

    evidence = section[
        "evidence"
    ]

    advice = section[
        "advice"
    ]

    assert isinstance(
        evidence,
        list,
    )

    assert isinstance(
        advice,
        list,
    )

    assert evidence

    assert advice

    assert all(
        isinstance(
            item,
            str,
        )
        and item.strip()
        for item in evidence
    )

    assert all(
        isinstance(
            item,
            str,
        )
        and item.strip()
        for item in advice
    )


def _customer_text(
    result: ReadingGenerationResult,
) -> str:
    parsed = result.parsed

    parts = [
        parsed.get(
            "summary",
            "",
        ),
    ]

    for section_name in ALL_SECTIONS:
        section = (
            parsed[
                "sections"
            ][
                section_name
            ]
        )

        parts.extend(
            [
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
            ]
        )

        parts.extend(
            section.get(
                "advice",
                [],
            )
        )

    parts.append(
        parsed.get(
            "disclaimer",
            "",
        )
    )

    return "\n".join(
        str(
            part
        )
        for part in parts
    )


def _evidence_text(
    result: ReadingGenerationResult,
) -> str:
    parsed = result.parsed

    items = []

    for section_name in ALL_SECTIONS:
        items.extend(
            parsed[
                "sections"
            ][
                section_name
            ][
                "evidence"
            ]
        )

    return "\n".join(
        str(
            item
        )
        for item in items
    )


# ============================================================
# 1. Environment
# ============================================================


def test_product_final_live_environment_enabled():
    assert (
        os.getenv(
            LIVE_TEST_ENV
        )
        == LIVE_TEST_ENABLED_VALUE
    )


def test_product_final_live_api_key_configured():
    assert (
        has_openai_api_key()
        is True
    )


def test_product_final_live_model_is_resolved(
    product_model,
):
    _non_empty(
        product_model,
        "product_model",
    )


# ============================================================
# 2. Golden chart / context before API
# ============================================================


def test_product_final_live_chart_is_verified(
    product_case,
    product_chart_result,
):
    _assert_chart_matches_case(
        product_chart_result,
        product_case,
    )


def test_product_final_live_context_is_verified(
    product_case,
    product_reading_context,
):
    _assert_context_matches_case(
        product_reading_context,
        product_case,
    )


def test_product_final_live_context_is_ready(
    product_reading_context,
):
    assert (
        product_reading_context[
            "status"
        ]
        == "ready_for_ai_reading"
    )

    assert (
        product_reading_context[
            "method"
        ]
        == "reading_context_v1"
    )


def test_product_final_live_context_has_eight_sections(
    product_reading_context,
):
    assert set(
        product_reading_context[
            "reading_sections"
        ].keys()
    ) == set(
        ALL_SECTIONS
    )


# ============================================================
# 3. Payload before API
# ============================================================


def test_product_final_live_payload_contains_own_chart(
    product_case,
    product_generation_payload,
):
    prompt = _extract_user_content(
        product_generation_payload
    )

    for pillar in (
        product_case.pillar_sequence
    ):
        assert pillar in prompt

    assert (
        product_case.day_master
        in prompt
    )

    assert (
        EXPECTED_ANNUAL_GANZHI
        in prompt
    )


def test_product_final_live_payload_contains_all_sections(
    product_generation_payload,
):
    prompt = _extract_user_content(
        product_generation_payload
    )

    for section in ALL_SECTIONS:
        assert section in prompt


def test_product_final_live_payload_policy(
    product_generation_payload,
):
    payload = product_generation_payload[
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


def test_product_final_live_payload_has_recalculation_guards(
    product_generation_payload,
):
    user_prompt = _extract_user_content(
        product_generation_payload
    )

    for phrase in (
        "日主を再判定しない",
        "格局を再判定しない",
        "用神を再選定しない",
        "大運を再計算しない",
        "歳運を再計算しない",
    ):
        assert phrase in user_prompt


def test_product_final_live_payload_has_safety_guards(
    product_generation_payload,
):
    system_prompt = (
        _extract_system_prompt(
            product_generation_payload
        )
    )

    for phrase in (
        "再計算しない",
        "入力された計算結果",
        "医学的診断",
        "確定的",
    ):
        assert phrase in system_prompt


def test_product_final_live_payload_has_product_quality_guards(
    product_generation_payload,
):
    system_prompt = (
        _extract_system_prompt(
            product_generation_payload
        )
    )

    for phrase in (
        "具体的な回数",
        "職業",
        "事業形態",
        "同じ五行",
        "evidence",
        "自然な日本語",
    ):
        assert phrase in system_prompt


# ============================================================
# 4. Actual OpenAI Responses API
# ============================================================


def test_product_final_live_result_type(
    product_result,
):
    assert isinstance(
        product_result,
        ReadingGenerationResult,
    )


def test_product_final_live_result_completed(
    product_result,
):
    assert (
        product_result.status
        == "completed"
    )

    assert (
        product_result.response_status
        in (
            None,
            "completed",
        )
    )


def test_product_final_live_response_id_exists(
    product_result,
):
    _non_empty(
        product_result.response_id,
        "response_id",
    )


def test_product_final_live_model_matches(
    product_result,
    product_model,
):
    assert (
        product_result.model
        == product_model
    )


def test_product_final_live_output_format_is_json(
    product_result,
):
    assert (
        product_result.output_format
        == "json"
    )


def test_product_final_live_requested_eight_sections(
    product_result,
):
    assert (
        product_result.sections
        == ALL_SECTIONS
    )


# ============================================================
# 5. Parsed JSON contract
# ============================================================


def test_product_final_live_top_level_contract(
    product_result,
):
    parsed = product_result.parsed

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


def test_product_final_live_has_exactly_eight_sections(
    product_result,
):
    sections = product_result.parsed[
        "sections"
    ]

    assert isinstance(
        sections,
        Mapping,
    )

    assert set(
        sections.keys()
    ) == set(
        ALL_SECTIONS
    )

    assert len(
        sections
    ) == 8


@pytest.mark.parametrize(
    "section_name",
    ALL_SECTIONS,
)
def test_product_final_live_each_section_contract(
    product_result,
    section_name,
):
    section = (
        product_result.parsed[
            "sections"
        ][
            section_name
        ]
    )

    _assert_section_contract(
        section_name,
        section,
    )


# ============================================================
# 6. Minimum product quality
# ============================================================


def test_product_final_live_summary_has_reasonable_length(
    product_result,
):
    summary = (
        product_result.parsed[
            "summary"
        ].strip()
    )

    assert (
        len(summary)
        >= 20
    )


@pytest.mark.parametrize(
    "section_name",
    ALL_SECTIONS,
)
def test_product_final_live_section_detail_has_reasonable_length(
    product_result,
    section_name,
):
    detail = (
        product_result.parsed[
            "sections"
        ][
            section_name
        ][
            "detail"
        ].strip()
    )

    assert (
        len(detail)
        >= 40
    ), (
        f"{section_name}.detail が短すぎます。"
    )


def test_product_final_live_customer_text_has_no_major_internal_keys(
    product_result,
):
    text = _customer_text(
        product_result
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
        "source_metadata.",
    )

    for marker in forbidden:
        assert (
            marker
            not in text
        ), (
            f"顧客向け本文に内部キーが露出しています: "
            f"{marker}"
        )


def test_product_final_live_evidence_is_customer_readable(
    product_result,
):
    text = _evidence_text(
        product_result
    )

    forbidden = (
        "day_master.",
        "natal_chart.",
        "pattern.primary_pattern",
        "five_elements.weighted_scores",
        "useful_gods.primary_useful_element",
        "integrated_luck.overall_level",
        "current_luck.current_pillar",
        "source_metadata.",
    )

    for marker in forbidden:
        assert (
            marker
            not in text
        )


def test_product_final_live_disclaimer_exists_and_is_substantial(
    product_result,
):
    """
    生成AIの免責文は非決定的なので、
    固定語ではなく存在・最低長だけを確認する。

    医学的診断禁止や確定的予言禁止は
    system prompt側の別テストで保証する。
    """

    disclaimer = (
        product_result.parsed[
            "disclaimer"
        ]
    )

    assert isinstance(
        disclaimer,
        str,
    )

    disclaimer = (
        disclaimer.strip()
    )

    assert disclaimer

    assert (
        len(disclaimer)
        >= 20
    )


# ============================================================
# 7. Health / future safety
# ============================================================


def test_product_final_live_health_section_is_not_empty(
    product_result,
):
    section = (
        product_result.parsed[
            "sections"
        ][
            "health"
        ]
    )

    _non_empty(
        section[
            "summary"
        ],
        "health.summary",
    )

    _non_empty(
        section[
            "detail"
        ],
        "health.detail",
    )


def test_product_final_live_health_avoids_obvious_diagnosis_language(
    product_result,
):
    """
    生成文章の完全一致ではなく、
    明らかな診断断定表現だけを避ける。

    「病気」という一般語そのものは禁止しない。
    """

    health = (
        product_result.parsed[
            "sections"
        ][
            "health"
        ]
    )

    text = "\n".join(
        [
            health[
                "summary"
            ],
            health[
                "detail"
            ],
            *health[
                "advice"
            ],
        ]
    )

    forbidden = (
        "あなたは病気です",
        "必ず発症",
        "確実に発症",
        "診断できます",
        "寿命は",
        "余命は",
    )

    for phrase in forbidden:
        assert phrase not in text


def test_product_final_live_future_flow_avoids_obvious_certainty(
    product_result,
):
    future = (
        product_result.parsed[
            "sections"
        ][
            "future_flow"
        ]
    )

    text = "\n".join(
        [
            future[
                "summary"
            ],
            future[
                "detail"
            ],
            *future[
                "advice"
            ],
        ]
    )

    forbidden = (
        "必ず成功します",
        "必ず結婚します",
        "必ず儲かります",
        "確実に成功します",
        "絶対に成功します",
        "確実に起こります",
    )

    for phrase in forbidden:
        assert phrase not in text


def test_product_final_live_current_luck_avoids_obvious_certainty(
    product_result,
):
    current = (
        product_result.parsed[
            "sections"
        ][
            "current_luck"
        ]
    )

    text = "\n".join(
        [
            current[
                "summary"
            ],
            current[
                "detail"
            ],
            *current[
                "advice"
            ],
        ]
    )

    forbidden = (
        "絶対に",
        "100％",
        "必ず成功",
        "確実に儲",
    )

    for phrase in forbidden:
        assert phrase not in text


# ============================================================
# 8. Security
# ============================================================


def test_product_final_live_payload_never_exposes_api_key(
    product_generation_payload,
):
    api_key = os.getenv(
        OPENAI_API_KEY_ENV
    )

    assert api_key

    serialized = json.dumps(
        product_generation_payload,
        ensure_ascii=False,
        default=str,
    )

    assert (
        api_key
        not in serialized
    )


def test_product_final_live_result_never_exposes_api_key(
    product_result,
):
    api_key = os.getenv(
        OPENAI_API_KEY_ENV
    )

    assert api_key

    serialized = json.dumps(
        {
            "text": product_result.text,
            "parsed": product_result.parsed,
            "usage": product_result.usage,
            "response_id": (
                product_result.response_id
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
# 9. Usage
# ============================================================


def test_product_final_live_usage_is_valid_when_present(
    product_result,
):
    if product_result.usage is None:
        return

    assert isinstance(
        product_result.usage,
        dict,
    )

    total_tokens = (
        product_result.usage.get(
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
# 10. Per-case final gate
# ============================================================


def test_reading_product_final_e2e_live_v1_final_gate(
    product_case,
    product_chart_result,
    product_reading_context,
    product_generation_payload,
    product_result,
):
    # --------------------------------------------------------
    # Golden facts before API
    # --------------------------------------------------------

    _assert_chart_matches_case(
        product_chart_result,
        product_case,
    )

    _assert_context_matches_case(
        product_reading_context,
        product_case,
    )

    assert (
        product_reading_context[
            "status"
        ]
        == "ready_for_ai_reading"
    )

    # --------------------------------------------------------
    # Prompt
    # --------------------------------------------------------

    user_prompt = _extract_user_content(
        product_generation_payload
    )

    for pillar in (
        product_case.pillar_sequence
    ):
        assert pillar in user_prompt

    assert (
        product_case.day_master
        in user_prompt
    )

    for section_name in ALL_SECTIONS:
        assert (
            section_name
            in user_prompt
        )

    # --------------------------------------------------------
    # OpenAI result
    # --------------------------------------------------------

    assert isinstance(
        product_result,
        ReadingGenerationResult,
    )

    assert (
        product_result.status
        == "completed"
    )

    assert (
        product_result.output_format
        == "json"
    )

    assert (
        product_result.sections
        == ALL_SECTIONS
    )

    # --------------------------------------------------------
    # Parsed product reading
    # --------------------------------------------------------

    parsed = product_result.parsed

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

    sections = parsed[
        "sections"
    ]

    assert set(
        sections.keys()
    ) == set(
        ALL_SECTIONS
    )

    for section_name in ALL_SECTIONS:
        _assert_section_contract(
            section_name,
            sections[
                section_name
            ],
        )

    # --------------------------------------------------------
    # Customer-facing quality
    # --------------------------------------------------------

    customer_text = _customer_text(
        product_result
    )

    for forbidden in (
        "technical_pattern",
        "weighted_scores",
        "overall_level",
        "overall_score",
        "agreement_level",
        "primary_useful_element",
        "secondary_useful_elements",
        "branch_useful_relation",
        "day_master.",
        "natal_chart.",
        "integrated_luck.",
    ):
        assert (
            forbidden
            not in customer_text
        )


# ============================================================
# 11. Cross-case differentiation
# ============================================================


def test_product_final_live_cases_have_distinct_input_signatures():
    signatures = {
        case.pillar_sequence
        for case in PRODUCT_CASES
    }

    assert (
        len(signatures)
        == len(PRODUCT_CASES)
    )


def test_product_final_live_cases_include_multiple_day_masters():
    day_masters = {
        case.day_master
        for case in PRODUCT_CASES
    }

    assert (
        len(day_masters)
        >= 2
    )
