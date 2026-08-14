"""
tests/test_reading_product_customer_facing.py

四柱推命鑑定商品
顧客向け最終品質ゲート（non-live）

目的
----
AIへ渡す prompt / schema / payload が、最終顧客向け文章として
次の品質を要求していることを OpenAI API を呼ばずに検証する。

1. evidence を顧客向けの自然な日本語にする。
2. evidence に JSONパス・snake_case・内部変数名・key=value を出さない。
3. 内部評価ラベルを顧客向け文章へそのまま露出させない。
4. 仕事・適職は「仕事の性質・役割・環境」を先に説明する。
5. 入力にない職業・事業形態を暗黙に仮定しない。
6. 根拠のない具体的数値・事業モデルを四柱推命上の必然にしない。
7. 命式・日主等の計算済み事実をAIに再計算させない。
8. 4つの外部照合済み命式で同じ品質契約が成立する。

重要
----
このファイルは OpenAI API を呼ばない。
実際の生成文章そのものの禁止語検査は live test 側で行う。
non-live では「AIに何を要求しているか」を決定論的に固定する。

Version
-------
reading_product_customer_facing_v1
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from types import SimpleNamespace
from typing import Any, Dict, Mapping, Tuple

import pytest

from engine.chart import calculate_chart
from engine.reading_context import build_reading_context
from engine.reading_generator import build_generation_payload
from engine.reading_prompt import (
    build_reading_request,
    build_section_prompt,
)


# ============================================================
# Configuration
# ============================================================


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

QUALITY_MODEL = "gpt-5"
QUALITY_OUTPUT_FORMAT = "json"
QUALITY_MAX_OUTPUT_TOKENS = 8000
QUALITY_REASONING_EFFORT = "minimal"
QUALITY_STORE = False

TARGET_DATETIME = datetime(
    2026,
    8,
    10,
    15,
    36,
)


# ============================================================
# Golden chart definitions
# ============================================================


@dataclass(frozen=True)
class VerifiedChartCase:
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


VERIFIED_CASES = (
    VerifiedChartCase(
        case_id="1985_07_17_2150_ishikawa_female",
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
    VerifiedChartCase(
        case_id="1984_07_22_0415_hokkaido_female",
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
    VerifiedChartCase(
        case_id="1984_07_22_1340_fukuoka_male",
        birth_date="1984-07-22",
        birth_time="13:40",
        birth_place="福岡県",
        gender="male",
        year_pillar="甲子",
        month_pillar="辛未",
        day_pillar="丁巳",
        hour_pillar="丁未",
        day_master="丁",
    ),
    VerifiedChartCase(
        case_id="1984_07_21_1200_tokyo_male",
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

CASE_IDS = tuple(
    case.case_id
    for case in VERIFIED_CASES
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture(
    params=VERIFIED_CASES,
    ids=CASE_IDS,
)
def verified_case(
    request,
) -> VerifiedChartCase:
    return request.param


@pytest.fixture
def verified_request(
    verified_case: VerifiedChartCase,
):
    return SimpleNamespace(
        birth_date=verified_case.birth_date,
        birth_time=verified_case.birth_time,
        birth_place=verified_case.birth_place,
        gender=verified_case.gender,
    )


@pytest.fixture
def chart_result(
    verified_request,
):
    return calculate_chart(
        verified_request,
        target_datetime=TARGET_DATETIME,
    )


@pytest.fixture
def reading_context(
    chart_result,
):
    return build_reading_context(
        chart_result
    )


@pytest.fixture
def reading_request(
    reading_context,
):
    return build_reading_request(
        reading_context,
        sections=ALL_SECTIONS,
        output_format=QUALITY_OUTPUT_FORMAT,
    )


@pytest.fixture
def generation_payload(
    reading_context,
):
    return build_generation_payload(
        reading_context,
        model=QUALITY_MODEL,
        sections=ALL_SECTIONS,
        output_format=QUALITY_OUTPUT_FORMAT,
        max_output_tokens=(
            QUALITY_MAX_OUTPUT_TOKENS
        ),
        reasoning_effort=(
            QUALITY_REASONING_EFFORT
        ),
        store=QUALITY_STORE,
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
    ), f"{name} はstrである必要があります。"

    value = value.strip()

    assert value, f"{name} が空です。"

    return value


def _extract_user_prompt(
    generation: Mapping[str, Any],
) -> str:
    payload = generation[
        "payload"
    ]

    inputs = payload[
        "input"
    ]

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
    case: VerifiedChartCase,
) -> None:
    chart = chart_result[
        "chart"
    ]

    for position, expected in (
        case.expected_pillars.items()
    ):
        assert (
            chart[
                position
            ][
                "pillar"
            ]
            == expected
        ), (
            f"{case.case_id}: "
            f"{position}柱が不一致です。"
        )

    assert (
        chart_result[
            "day_master"
        ][
            "stem"
        ]
        == case.day_master
    ), (
        f"{case.case_id}: "
        "日主が不一致です。"
    )


def _assert_context_matches_case(
    context: Mapping[str, Any],
    case: VerifiedChartCase,
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
        assert (
            pillars[
                position
            ][
                "pillar"
            ]
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
    ), (
        f"{case.case_id}: "
        "reading_contextで日主が変化しています。"
    )


# ============================================================
# 1. Basic integrity
# ============================================================


def test_customer_facing_cases_are_unique():
    assert len(
        CASE_IDS
    ) == len(
        set(
            CASE_IDS
        )
    )


def test_customer_facing_has_four_verified_cases():
    assert len(
        VERIFIED_CASES
    ) >= 4


def test_customer_facing_chart_matches_golden(
    verified_case,
    chart_result,
):
    _assert_chart_matches_case(
        chart_result,
        verified_case,
    )


def test_customer_facing_context_matches_golden(
    verified_case,
    reading_context,
):
    _assert_context_matches_case(
        reading_context,
        verified_case,
    )


def test_customer_facing_context_ready(
    reading_context,
):
    assert (
        reading_context[
            "status"
        ]
        == "ready_for_ai_reading"
    )


# ============================================================
# 2. Evidence must be customer-facing
# ============================================================


@pytest.mark.parametrize(
    "phrase",
    (
        "evidence",
        "顧客",
        "自然な日本語",
        "計算済み事実",
    ),
)
def test_customer_facing_system_prompt_requires_readable_evidence(
    generation_payload,
    phrase,
):
    prompt = _extract_system_prompt(
        generation_payload
    )

    assert phrase in prompt


@pytest.mark.parametrize(
    "phrase",
    (
        "JSONパス",
        "snake_case",
        "内部変数名",
        "field=value",
    ),
)
def test_customer_facing_system_prompt_forbids_internal_evidence_notation(
    generation_payload,
    phrase,
):
    prompt = _extract_system_prompt(
        generation_payload
    )

    assert phrase in prompt


@pytest.mark.parametrize(
    "phrase",
    (
        "JSONパス",
        "snake_case",
        "内部変数名",
        "field=value",
    ),
)
def test_customer_facing_user_prompt_forbids_internal_evidence_notation(
    generation_payload,
    phrase,
):
    prompt = _extract_user_prompt(
        generation_payload
    )

    assert phrase in prompt


def test_customer_facing_json_schema_has_evidence_array(
    reading_request,
):
    sections_schema = (
        reading_request[
            "output_schema"
        ][
            "properties"
        ][
            "sections"
        ][
            "properties"
        ]
    )

    for section in ALL_SECTIONS:
        evidence_schema = (
            sections_schema[
                section
            ][
                "properties"
            ][
                "evidence"
            ]
        )

        assert (
            evidence_schema[
                "type"
            ]
            == "array"
        )

        assert (
            evidence_schema[
                "items"
            ][
                "type"
            ]
            == "string"
        )


# ============================================================
# 3. Internal labels / implementation details
# ============================================================


@pytest.mark.parametrize(
    "phrase",
    (
        "内部キー名",
        "内部変数名",
        "デバッグ用ラベル",
    ),
)
def test_customer_facing_system_prompt_rejects_internal_labels(
    generation_payload,
    phrase,
):
    prompt = _extract_system_prompt(
        generation_payload
    )

    assert phrase in prompt


def test_customer_facing_prompt_explicitly_treats_evidence_as_final_copy(
    generation_payload,
):
    prompt = _extract_system_prompt(
        generation_payload
    )

    assert (
        "そのまま提示"
        in prompt
        or "そのまま掲載"
        in prompt
    )


# ============================================================
# 4. Career must explain characteristics before examples
# ============================================================


@pytest.mark.parametrize(
    "phrase",
    (
        "役割",
        "環境",
        "仕事の性質",
        "例えば",
    ),
)
def test_customer_facing_career_prompt_is_characteristic_first(
    generation_payload,
    phrase,
):
    prompt = _extract_system_prompt(
        generation_payload
    )

    assert phrase in prompt


@pytest.mark.parametrize(
    "phrase",
    (
        "職業",
        "事業形態",
        "雇用形態",
        "暗黙に仮定しない",
    ),
)
def test_customer_facing_prompt_rejects_unprovided_work_assumptions(
    generation_payload,
    phrase,
):
    prompt = _extract_system_prompt(
        generation_payload
    )

    assert phrase in prompt


def test_customer_facing_career_section_prompt_keeps_example_rule(
    reading_context,
):
    prompt = build_section_prompt(
        reading_context,
        "career",
        output_format="json",
    )

    assert "職業" in prompt
    assert (
        "例"
        in prompt
        or "例えば"
        in prompt
    )


# ============================================================
# 5. No unfounded numeric or business-model certainty
# ============================================================


@pytest.mark.parametrize(
    "phrase",
    (
        "具体的な回数",
        "頻度",
        "件数",
        "金額",
        "数値目標",
        "四柱推命上の必然",
    ),
)
def test_customer_facing_prompt_rejects_unfounded_numeric_certainty(
    generation_payload,
    phrase,
):
    prompt = _extract_system_prompt(
        generation_payload
    )

    assert phrase in prompt


def test_customer_facing_prompt_does_not_present_job_examples_as_certainty(
    generation_payload,
):
    prompt = _extract_system_prompt(
        generation_payload
    )

    assert (
        "職業例"
        in prompt
    )

    assert (
        "確定"
        in prompt
        or "例示"
        in prompt
    )


# ============================================================
# 6. Contextual five-element translation
# ============================================================


@pytest.mark.parametrize(
    "phrase",
    (
        "同じ五行",
        "各セクション",
        "文脈",
    ),
)
def test_customer_facing_prompt_requires_contextual_element_translation(
    generation_payload,
    phrase,
):
    prompt = _extract_system_prompt(
        generation_payload
    )

    assert phrase in prompt


# ============================================================
# 7. Recalculation and safety remain intact
# ============================================================


@pytest.mark.parametrize(
    "phrase",
    (
        "再計算しない",
        "入力された計算結果",
        "医学的診断",
        "確定的",
    ),
)
def test_customer_facing_system_guardrails_remain(
    generation_payload,
    phrase,
):
    prompt = _extract_system_prompt(
        generation_payload
    )

    assert phrase in prompt


@pytest.mark.parametrize(
    "phrase",
    (
        "日主を再判定しない",
        "格局を再判定しない",
        "用神を再選定しない",
        "大運を再計算しない",
        "歳運を再計算しない",
    ),
)
def test_customer_facing_user_recalculation_guards_remain(
    generation_payload,
    phrase,
):
    prompt = _extract_user_prompt(
        generation_payload
    )

    assert phrase in prompt


# ============================================================
# 8. Payload contract
# ============================================================


def test_customer_facing_payload_contract(
    generation_payload,
):
    payload = generation_payload[
        "payload"
    ]

    assert (
        payload[
            "model"
        ]
        == QUALITY_MODEL
    )

    assert (
        payload[
            "max_output_tokens"
        ]
        == QUALITY_MAX_OUTPUT_TOKENS
    )

    assert (
        payload[
            "reasoning"
        ][
            "effort"
        ]
        == QUALITY_REASONING_EFFORT
    )

    assert (
        payload[
            "store"
        ]
        is QUALITY_STORE
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


def test_customer_facing_payload_is_json_serializable(
    generation_payload,
):
    serialized = json.dumps(
        generation_payload,
        ensure_ascii=False,
        default=str,
    )

    assert isinstance(
        serialized,
        str,
    )

    assert serialized


# ============================================================
# 9. Detection helpers for future live-output tests
# ============================================================


def test_internal_path_regex_detects_json_path():
    pattern = re.compile(
        r"\b[a-z][a-z0-9_]*"
        r"(?:\.[a-z][a-z0-9_]*)+\b"
    )

    assert pattern.search(
        "pattern.primary_pattern=偏官格"
    )


def test_snake_case_regex_detects_internal_field():
    pattern = re.compile(
        r"\b[a-z][a-z0-9]*"
        r"(?:_[a-z0-9]+)+\b"
    )

    assert pattern.search(
        "final_useful_elements"
    )


def test_assignment_regex_detects_internal_assignment():
    pattern = re.compile(
        r"\b[a-z][a-z0-9_.]*\s*="
    )

    assert pattern.search(
        "current_luck.status=mixed"
    )


# ============================================================
# 10. Final gate
# ============================================================


def test_reading_product_customer_facing_v1_final_gate(
    verified_case,
    chart_result,
    reading_context,
    reading_request,
    generation_payload,
):
    # Golden chart is preserved.
    _assert_chart_matches_case(
        chart_result,
        verified_case,
    )

    _assert_context_matches_case(
        reading_context,
        verified_case,
    )

    assert (
        reading_context[
            "status"
        ]
        == "ready_for_ai_reading"
    )

    assert set(
        reading_context[
            "reading_sections"
        ].keys()
    ) == set(
        ALL_SECTIONS
    )

    # Prompt rules.
    system_prompt = _extract_system_prompt(
        generation_payload
    )

    user_prompt = _extract_user_prompt(
        generation_payload
    )

    for marker in (
        "evidence",
        "顧客",
        "自然な日本語",
        "JSONパス",
        "snake_case",
        "内部変数名",
        "field=value",
        "仕事の性質",
        "職業例",
        "暗黙に仮定しない",
        "具体的な回数",
        "件数",
        "四柱推命上の必然",
        "同じ五行",
        "各セクション",
    ):
        assert marker in system_prompt

    for marker in (
        "日主を再判定しない",
        "格局を再判定しない",
        "用神を再選定しない",
        "大運を再計算しない",
        "歳運を再計算しない",
        "JSONパス",
        "snake_case",
        "field=value",
    ):
        assert marker in user_prompt

    # Own chart facts are still supplied.
    for pillar in (
        verified_case.pillar_sequence
    ):
        assert pillar in user_prompt

    assert (
        verified_case.day_master
        in user_prompt
    )

    # Structured output contract.
    assert tuple(
        reading_request[
            "sections"
        ]
    ) == ALL_SECTIONS

    payload = generation_payload[
        "payload"
    ]

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
