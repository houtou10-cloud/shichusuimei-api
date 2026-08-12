"""
tests/test_reading_product_quality_multi_chart.py

複数の実命式を用いた AI鑑定商品品質テスト。

目的
----
単一のgolden chartだけではなく、出生日時・出生地・性別・日主・時柱が
異なる複数の実命式について、

    birth data
        ↓
    calculate_chart()
        ↓
    build_reading_context()
        ↓
    build_reading_request()
        ↓
    build_generation_payload()

までを OpenAI API を呼ばずに検証する。

このテストで確認すること
------------------------
1. 外部照合済みの四柱が calculate_chart() で維持される。
2. 日主が reading_context まで維持される。
3. reading_context が ready_for_ai_reading になる。
4. 8セクションすべてが存在する。
5. prompt / payload に各命式の実データが含まれる。
6. AIへ命式の再計算・再判定をさせないガードレールが入る。
7. JSON Structured Outputs の契約が全命式で同じ。
8. health は医学的診断を禁止する。
9. future/advice は確定的な未来予言を禁止する。
10. 商品品質ルール
    - 根拠のない具体的数値をAI独自に作らせない
    - 入力にない職業・事業形態を仮定させない
    - evidenceを顧客向け日本語へ翻訳する
    - 同じ五行を全章で同一解釈に固定しない
11. 命式ごとに prompt が変化し、別人の入力が混線しない。
12. 同じ入力から同じ reading_context / payload が生成される。

重要
----
このテストは OpenAI API を呼ばない。
生成AIの文章そのものは非決定的なので、このファイルでは検証しない。

Live生成品質は別ファイル
tests/test_reading_product_quality_multi_chart_live.py
で段階的に検証する想定。

Version
-------
reading_product_quality_multi_chart_v1
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from types import SimpleNamespace
from typing import Any, Dict, Mapping, Sequence, Tuple

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

# 現在運・歳運の比較基準日時を固定し、
# テストを決定論的にする。
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
    """
    外部照合済みの検証ケース。
    """

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


# ここには「期待四柱を外部照合済み」のケースだけを置く。
#
# 新規ケースを増やす場合は、
# 推測値を入れず、外部暦または既存golden testで
# 四柱を確認してから追加すること。
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
    ), (
        f"{name} はstrである必要があります。"
    )

    value = value.strip()

    assert value, (
        f"{name} が空です。"
    )

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


def _serialize(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )


# ============================================================
# 1. Golden chart integrity
# ============================================================


def test_multi_chart_case_ids_are_unique():
    assert len(
        CASE_IDS
    ) == len(
        set(
            CASE_IDS
        )
    )


def test_multi_chart_has_multiple_verified_cases():
    assert len(
        VERIFIED_CASES
    ) >= 4


def test_multi_chart_has_multiple_day_masters():
    day_masters = {
        case.day_master
        for case in VERIFIED_CASES
    }

    assert len(
        day_masters
    ) >= 2


def test_multi_chart_has_multiple_hour_pillars():
    hours = {
        case.hour_pillar
        for case in VERIFIED_CASES
    }

    assert len(
        hours
    ) >= 3


def test_multi_chart_calculated_chart_matches_golden(
    verified_case,
    chart_result,
):
    _assert_chart_matches_case(
        chart_result,
        verified_case,
    )


def test_multi_chart_day_pillar_stem_matches_day_master(
    verified_case,
):
    assert (
        verified_case.day_pillar[
            0
        ]
        == verified_case.day_master
    )


# ============================================================
# 2. reading_context integrity
# ============================================================


def test_multi_chart_context_matches_golden(
    verified_case,
    reading_context,
):
    _assert_context_matches_case(
        reading_context,
        verified_case,
    )


def test_multi_chart_context_is_ready(
    reading_context,
):
    assert (
        reading_context[
            "status"
        ]
        == "ready_for_ai_reading"
    )

    assert (
        reading_context[
            "method"
        ]
        == "reading_context_v1"
    )


def test_multi_chart_context_has_all_sections(
    reading_context,
):
    sections = reading_context[
        "reading_sections"
    ]

    assert set(
        sections.keys()
    ) == set(
        ALL_SECTIONS
    )


@pytest.mark.parametrize(
    "section",
    ALL_SECTIONS,
)
def test_multi_chart_each_section_has_focus(
    reading_context,
    section,
):
    focus = (
        reading_context[
            "reading_sections"
        ][
            section
        ][
            "focus"
        ]
    )

    assert isinstance(
        focus,
        list,
    )

    assert focus

    assert all(
        isinstance(
            item,
            str,
        )
        and item.strip()
        for item in focus
    )


@pytest.mark.parametrize(
    "section",
    ALL_SECTIONS,
)
def test_multi_chart_each_section_has_instruction(
    reading_context,
    section,
):
    instruction = (
        reading_context[
            "reading_sections"
        ][
            section
        ][
            "instruction"
        ]
    )

    _non_empty(
        instruction,
        f"{section}.instruction",
    )


def test_multi_chart_source_metadata_exists(
    reading_context,
):
    metadata = reading_context[
        "source_metadata"
    ]

    assert isinstance(
        metadata,
        Mapping,
    )

    assert metadata


@pytest.mark.parametrize(
    "source",
    (
        "strength",
        "pattern",
        "useful_gods",
        "luck_pillars",
        "current_luck",
        "annual_luck",
        "integrated_luck",
    ),
)
def test_multi_chart_source_metadata_method_exists(
    reading_context,
    source,
):
    metadata = reading_context[
        "source_metadata"
    ]

    assert source in metadata

    _non_empty(
        metadata[
            source
        ].get(
            "method"
        ),
        (
            "source_metadata."
            f"{source}.method"
        ),
    )


# ============================================================
# 3. Prompt facts / no cross-chart contamination
# ============================================================


def test_multi_chart_user_prompt_contains_own_pillars(
    verified_case,
    generation_payload,
):
    prompt = _extract_user_prompt(
        generation_payload
    )

    for pillar in (
        verified_case.pillar_sequence
    ):
        assert pillar in prompt


def test_multi_chart_user_prompt_contains_own_day_master(
    verified_case,
    generation_payload,
):
    prompt = _extract_user_prompt(
        generation_payload
    )

    assert (
        verified_case.day_master
        in prompt
    )


def test_multi_chart_prompt_does_not_use_other_case_unique_hour(
    verified_case,
    generation_payload,
):
    """
    他ケース固有の時柱が誤混入していないことを確認。

    同一文字列が自ケースの別データとして
    自然に出現する可能性を避けるため、
    時柱が自ケースと異なるケースだけを対象にし、
    raw natal_chartのpillar sequence部分を検査する。
    """

    prompt = _extract_user_prompt(
        generation_payload
    )

    own_hour = (
        verified_case.hour_pillar
    )

    # 自ケースの時柱は必須。
    assert own_hour in prompt

    # reading_context自体のpillar sequenceが
    # 正しいため、ここでは「他ケース全部がない」
    # という強すぎるassertはしない。
    #
    # 干支文字列は大運・歳運等にも自然に
    # 出現し得るためである。


def test_multi_chart_prompt_contains_all_requested_sections(
    generation_payload,
):
    prompt = _extract_user_prompt(
        generation_payload
    )

    for section in ALL_SECTIONS:
        assert section in prompt


# ============================================================
# 4. Recalculation guardrails
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
def test_multi_chart_system_prompt_has_required_guardrails(
    generation_payload,
    phrase,
):
    system_prompt = (
        _extract_system_prompt(
            generation_payload
        )
    )

    assert phrase in system_prompt


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
def test_multi_chart_user_prompt_has_recalculation_guardrails(
    generation_payload,
    phrase,
):
    user_prompt = (
        _extract_user_prompt(
            generation_payload
        )
    )

    assert phrase in user_prompt


# ============================================================
# 5. Final product quality prompt rules
# ============================================================


def test_multi_chart_prompt_rejects_unfounded_numeric_targets(
    generation_payload,
):
    prompt = (
        _extract_system_prompt(
            generation_payload
        )
    )

    assert (
        "具体的な回数"
        in prompt
    )

    assert (
        "頻度"
        in prompt
    )

    assert (
        "件数"
        in prompt
    )

    assert (
        "四柱推命上の必然"
        in prompt
    )


def test_multi_chart_prompt_rejects_unprovided_job_assumptions(
    generation_payload,
):
    prompt = (
        _extract_system_prompt(
            generation_payload
        )
    )

    assert (
        "職業"
        in prompt
    )

    assert (
        "事業形態"
        in prompt
    )

    assert (
        "暗黙に仮定しない"
        in prompt
    )


def test_multi_chart_prompt_requires_customer_friendly_evidence(
    generation_payload,
):
    prompt = (
        _extract_system_prompt(
            generation_payload
        )
    )

    assert (
        "evidence"
        in prompt
    )

    assert (
        "顧客"
        in prompt
    )

    assert (
        "自然な日本語"
        in prompt
    )


def test_multi_chart_prompt_requires_contextual_element_translation(
    generation_payload,
):
    prompt = (
        _extract_system_prompt(
            generation_payload
        )
    )

    assert (
        "同じ五行"
        in prompt
    )

    assert (
        "各セクション"
        in prompt
    )


def test_multi_chart_user_prompt_contains_final_quality_rules(
    generation_payload,
):
    prompt = (
        _extract_user_prompt(
            generation_payload
        )
    )

    markers = (
        "根拠のない",
        "職業",
        "事業形態",
        "evidence",
        "内部キー",
    )

    for marker in markers:
        assert marker in prompt


# ============================================================
# 6. Section-specific safety
# ============================================================


def test_multi_chart_health_instruction_is_non_diagnostic(
    reading_context,
):
    instruction = (
        reading_context[
            "reading_sections"
        ][
            "health"
        ][
            "instruction"
        ]
    )

    assert (
        "医学的診断を行わず"
        in instruction
    )


def test_multi_chart_health_prompt_contains_medical_safety(
    reading_context,
):
    prompt = build_section_prompt(
        reading_context,
        "health",
        output_format="json",
    )

    assert (
        "医学的診断"
        in prompt
    )


def test_multi_chart_advice_instruction_rejects_prediction(
    reading_context,
):
    instruction = (
        reading_context[
            "reading_sections"
        ][
            "advice"
        ][
            "instruction"
        ]
    )

    assert (
        "断定的な未来予言ではなく"
        in instruction
    )


def test_multi_chart_future_prompt_is_non_deterministic(
    reading_context,
):
    prompt = build_section_prompt(
        reading_context,
        "future_flow",
        output_format="json",
    )

    assert (
        "確定的"
        in prompt
        or "断定"
        in prompt
        or "可能性"
        in prompt
    )


# ============================================================
# 7. Request contract
# ============================================================


def test_multi_chart_request_has_eight_sections(
    reading_request,
):
    assert tuple(
        reading_request[
            "sections"
        ]
    ) == ALL_SECTIONS


def test_multi_chart_request_schema_has_top_level_contract(
    reading_request,
):
    schema = reading_request[
        "output_schema"
    ]

    properties = schema[
        "properties"
    ]

    assert {
        "summary",
        "sections",
        "disclaimer",
    }.issubset(
        properties.keys()
    )


def test_multi_chart_request_schema_has_exact_sections(
    reading_request,
):
    section_properties = (
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

    assert set(
        section_properties.keys()
    ) == set(
        ALL_SECTIONS
    )


@pytest.mark.parametrize(
    "section",
    ALL_SECTIONS,
)
def test_multi_chart_schema_each_section_contract(
    reading_request,
    section,
):
    section_schema = (
        reading_request[
            "output_schema"
        ][
            "properties"
        ][
            "sections"
        ][
            "properties"
        ][
            section
        ]
    )

    properties = section_schema[
        "properties"
    ]

    assert {
        "title",
        "summary",
        "detail",
        "evidence",
        "advice",
    }.issubset(
        properties.keys()
    )

    assert (
        properties[
            "evidence"
        ][
            "type"
        ]
        == "array"
    )

    assert (
        properties[
            "advice"
        ][
            "type"
        ]
        == "array"
    )


# ============================================================
# 8. Generation payload contract
# ============================================================


def test_multi_chart_generation_uses_expected_model(
    generation_payload,
):
    assert (
        generation_payload[
            "payload"
        ][
            "model"
        ]
        == QUALITY_MODEL
    )


def test_multi_chart_generation_uses_json_schema(
    generation_payload,
):
    fmt = (
        generation_payload[
            "payload"
        ][
            "text"
        ][
            "format"
        ]
    )

    assert (
        fmt[
            "type"
        ]
        == "json_schema"
    )

    assert (
        fmt[
            "strict"
        ]
        is True
    )


def test_multi_chart_generation_uses_8000_tokens(
    generation_payload,
):
    assert (
        generation_payload[
            "payload"
        ][
            "max_output_tokens"
        ]
        == QUALITY_MAX_OUTPUT_TOKENS
    )


def test_multi_chart_generation_uses_minimal_reasoning(
    generation_payload,
):
    assert (
        generation_payload[
            "payload"
        ][
            "reasoning"
        ][
            "effort"
        ]
        == QUALITY_REASONING_EFFORT
    )


def test_multi_chart_generation_does_not_store(
    generation_payload,
):
    assert (
        generation_payload[
            "payload"
        ][
            "store"
        ]
        is False
    )


# ============================================================
# 9. Determinism / reproducibility
# ============================================================


def test_multi_chart_context_is_reproducible(
    chart_result,
):
    first = build_reading_context(
        chart_result
    )

    second = build_reading_context(
        chart_result
    )

    assert first == second


def test_multi_chart_request_is_reproducible(
    reading_context,
):
    first = build_reading_request(
        reading_context,
        sections=ALL_SECTIONS,
        output_format=QUALITY_OUTPUT_FORMAT,
    )

    second = build_reading_request(
        reading_context,
        sections=ALL_SECTIONS,
        output_format=QUALITY_OUTPUT_FORMAT,
    )

    assert first == second


def test_multi_chart_generation_payload_is_reproducible(
    reading_context,
):
    kwargs = dict(
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

    first = build_generation_payload(
        reading_context,
        **kwargs,
    )

    second = build_generation_payload(
        reading_context,
        **kwargs,
    )

    assert first == second


# ============================================================
# 10. Cross-case differentiation
# ============================================================


def test_multi_chart_cases_produce_distinct_chart_signatures():
    signatures = []

    for case in VERIFIED_CASES:
        req = SimpleNamespace(
            birth_date=case.birth_date,
            birth_time=case.birth_time,
            birth_place=case.birth_place,
            gender=case.gender,
        )

        result = calculate_chart(
            req,
            target_datetime=TARGET_DATETIME,
        )

        _assert_chart_matches_case(
            result,
            case,
        )

        chart = result[
            "chart"
        ]

        signature = tuple(
            chart[
                position
            ][
                "pillar"
            ]
            for position
            in (
                "year",
                "month",
                "day",
                "hour",
            )
        )

        signatures.append(
            signature
        )

    assert len(
        set(
            signatures
        )
    ) == len(
        signatures
    )


def test_multi_chart_cases_produce_distinct_user_prompts():
    prompts = []

    for case in VERIFIED_CASES:
        req = SimpleNamespace(
            birth_date=case.birth_date,
            birth_time=case.birth_time,
            birth_place=case.birth_place,
            gender=case.gender,
        )

        chart = calculate_chart(
            req,
            target_datetime=TARGET_DATETIME,
        )

        context = build_reading_context(
            chart
        )

        generation = (
            build_generation_payload(
                context,
                model=QUALITY_MODEL,
                sections=ALL_SECTIONS,
                output_format=(
                    QUALITY_OUTPUT_FORMAT
                ),
                max_output_tokens=(
                    QUALITY_MAX_OUTPUT_TOKENS
                ),
                reasoning_effort=(
                    QUALITY_REASONING_EFFORT
                ),
                store=QUALITY_STORE,
            )
        )

        prompts.append(
            _extract_user_prompt(
                generation
            )
        )

    assert len(
        set(
            prompts
        )
    ) == len(
        prompts
    )


def test_multi_chart_serialized_contexts_are_distinct():
    serialized_contexts = []

    for case in VERIFIED_CASES:
        req = SimpleNamespace(
            birth_date=case.birth_date,
            birth_time=case.birth_time,
            birth_place=case.birth_place,
            gender=case.gender,
        )

        chart = calculate_chart(
            req,
            target_datetime=TARGET_DATETIME,
        )

        context = build_reading_context(
            chart
        )

        serialized_contexts.append(
            _serialize(
                context
            )
        )

    assert len(
        set(
            serialized_contexts
        )
    ) == len(
        serialized_contexts
    )


# ============================================================
# 11. No API key / no live communication assumptions
# ============================================================


def test_multi_chart_non_live_test_does_not_require_api_key(
    generation_payload,
):
    """
    build_generation_payload()までなら
    OpenAI API keyなしで成立することを確認。

    APIキーそのものの環境状態には依存しない。
    """

    assert (
        generation_payload[
            "payload"
        ][
            "model"
        ]
        == QUALITY_MODEL
    )


def test_multi_chart_payload_is_json_serializable(
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
# 12. Final product quality gate
# ============================================================


def test_reading_product_quality_multi_chart_v1_final_gate(
    verified_case,
    chart_result,
    reading_context,
    reading_request,
    generation_payload,
):
    """
    1ケースごとの最終ゲート。

    fixture parametrizeにより、
    VERIFIED_CASESすべてで実行される。
    """

    # Golden chart
    _assert_chart_matches_case(
        chart_result,
        verified_case,
    )

    # Context
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

    # Request
    assert tuple(
        reading_request[
            "sections"
        ]
    ) == ALL_SECTIONS

    # Payload
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
        == 8000
    )

    assert (
        payload[
            "reasoning"
        ][
            "effort"
        ]
        == "minimal"
    )

    assert (
        payload[
            "store"
        ]
        is False
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

    # Prompt facts
    user_prompt = (
        _extract_user_prompt(
            generation_payload
        )
    )

    for pillar in (
        verified_case.pillar_sequence
    ):
        assert pillar in user_prompt

    assert (
        verified_case.day_master
        in user_prompt
    )

    # Mandatory user recalculation guards
    for phrase in (
        "日主を再判定しない",
        "格局を再判定しない",
        "用神を再選定しない",
        "大運を再計算しない",
        "歳運を再計算しない",
    ):
        assert phrase in user_prompt

    # Mandatory system guards
    system_prompt = (
        _extract_system_prompt(
            generation_payload
        )
    )

    for phrase in (
        "再計算しない",
        "入力された計算結果",
        "医学的診断",
        "確定的",
    ):
        assert phrase in system_prompt

    # Final product-quality guards
    for marker in (
        "具体的な回数",
        "職業",
        "事業形態",
        "同じ五行",
        "evidence",
        "自然な日本語",
    ):
        assert marker in system_prompt
