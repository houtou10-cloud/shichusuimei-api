"""
tests/test_unknown_birth_time.py

出生時刻不明モードの回帰テスト。

目的
----
birth_time=None の入力が、

    calculate_chart()
        ↓
    build_reading_context()
        ↓
    build_reading_request()
        ↓
    build_generation_payload()

まで安全に伝播し、AIへ時柱の推測・補完をさせないことを固定する。

このテストは OpenAI API を呼ばない。

確認事項
--------
1. 出生時刻不明を正式に受け付ける。
2. 時柱は None になる。
3. birth_time_status が three_pillars / known_pillars_only になる。
4. 五行・身強身弱・格局・用神は三柱範囲の暫定評価になる。
5. 大運開始時期・現在大運の時期精度は estimated になる。
6. reading_context に不確実性が伝播する。
7. prompt facts に birth_time_status が含まれる。
8. user prompt に出生時刻不明専用ガードが入る。
9. 時柱の推測・補完・創作を禁止する。
10. 五行欠如を命式全体の確定事項として断定させない。
11. 身強身弱・格局・用神をAIに再計算させない。
12. estimated の大運時期を確定値として断定させない。
13. generation payload まで正常に生成できる。
14. 出生時刻ありでは通常の四柱モードを維持する。
15. 同じ入力から同じcontext / promptを生成する。
"""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from typing import Any, Mapping

import pytest

from engine.chart import calculate_chart
from engine.reading_context import (
    build_reading_context,
    validate_chart_result_for_reading,
)
from engine.reading_generator import (
    build_generation_payload,
)
from engine.reading_prompt import (
    build_birth_time_prompt_block,
    build_prompt_facts,
    build_reading_request,
    validate_reading_context,
)


TARGET_DATETIME = datetime(
    2026,
    8,
    10,
    15,
    36,
)

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

TEST_MODEL = "test-model"


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture(scope="module")
def unknown_time_request():
    return SimpleNamespace(
        birth_date="1985-07-17",
        birth_time=None,
        birth_place="石川県",
        gender="female",
    )


@pytest.fixture(scope="module")
def known_time_request():
    return SimpleNamespace(
        birth_date="1985-07-17",
        birth_time="21:50",
        birth_place="石川県",
        gender="female",
    )


@pytest.fixture(scope="module")
def unknown_chart_result(
    unknown_time_request,
):
    return calculate_chart(
        unknown_time_request,
        target_datetime=TARGET_DATETIME,
    )


@pytest.fixture(scope="module")
def known_chart_result(
    known_time_request,
):
    return calculate_chart(
        known_time_request,
        target_datetime=TARGET_DATETIME,
    )


@pytest.fixture(scope="module")
def unknown_reading_context(
    unknown_chart_result,
):
    return build_reading_context(
        unknown_chart_result
    )


@pytest.fixture(scope="module")
def known_reading_context(
    known_chart_result,
):
    return build_reading_context(
        known_chart_result
    )


@pytest.fixture(scope="module")
def unknown_reading_request(
    unknown_reading_context,
):
    return build_reading_request(
        unknown_reading_context,
        sections=ALL_SECTIONS,
        output_format="json",
    )


@pytest.fixture(scope="module")
def unknown_generation_payload(
    unknown_reading_context,
):
    return build_generation_payload(
        unknown_reading_context,
        model=TEST_MODEL,
        sections=ALL_SECTIONS,
        output_format="json",
        max_output_tokens=8000,
        reasoning_effort="minimal",
        store=False,
    )


# ============================================================
# Helpers
# ============================================================


def _non_empty_string(
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


def _request_system_prompt(
    request: Mapping[str, Any],
) -> str:
    messages = request["messages"]

    assert isinstance(
        messages,
        list,
    )

    assert len(messages) == 2

    return _non_empty_string(
        messages[0].get(
            "content"
        ),
        "system prompt",
    )


def _request_user_prompt(
    request: Mapping[str, Any],
) -> str:
    messages = request["messages"]

    assert isinstance(
        messages,
        list,
    )

    assert len(messages) == 2

    return _non_empty_string(
        messages[1].get(
            "content"
        ),
        "user prompt",
    )


def _payload_system_prompt(
    generation: Mapping[str, Any],
) -> str:
    return _non_empty_string(
        generation[
            "payload"
        ].get(
            "instructions"
        ),
        "payload.instructions",
    )


def _payload_user_prompt(
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

    first = inputs[0]

    assert isinstance(
        first,
        Mapping,
    )

    return _non_empty_string(
        first.get(
            "content"
        ),
        "payload.input[0].content",
    )


# ============================================================
# 1. Chart layer
# ============================================================


def test_unknown_birth_time_is_preserved_as_none(
    unknown_chart_result,
):
    assert (
        unknown_chart_result[
            "input"
        ][
            "birth_time"
        ]
        is None
    )


def test_unknown_birth_time_has_no_hour_pillar(
    unknown_chart_result,
):
    chart = unknown_chart_result[
        "chart"
    ]

    assert "hour" in chart

    assert chart[
        "hour"
    ] is None


def test_unknown_birth_time_status_is_three_pillars(
    unknown_chart_result,
):
    status = unknown_chart_result[
        "birth_time_status"
    ]

    assert status[
        "known"
    ] is False

    assert status[
        "hour_pillar_available"
    ] is False

    assert (
        status[
            "calculation_scope"
        ]
        == "three_pillars"
    )

    assert (
        status[
            "interpretation_scope"
        ]
        == "known_pillars_only"
    )


@pytest.mark.parametrize(
    "key",
    (
        "five_elements_scope",
        "root_scope",
        "strength_scope",
        "pattern_scope",
        "useful_gods_scope",
        "relationship_scope",
    ),
)
def test_unknown_birth_time_scopes_are_known_pillars_only(
    unknown_chart_result,
    key,
):
    status = unknown_chart_result[
        "birth_time_status"
    ]

    assert (
        status[key]
        == "known_pillars_only"
    )


def test_unknown_birth_time_luck_timing_is_estimated(
    unknown_chart_result,
):
    status = unknown_chart_result[
        "birth_time_status"
    ]

    assert (
        status[
            "luck_start_timing_precision"
        ]
        == "estimated"
    )

    assert (
        status[
            "current_luck_precision"
        ]
        == "estimated"
    )

    assert (
        status[
            "is_provisional_due_to_unknown_birth_time"
        ]
        is True
    )


def test_unknown_birth_time_chart_validation_passes(
    unknown_chart_result,
):
    validation = (
        validate_chart_result_for_reading(
            unknown_chart_result
        )
    )

    assert validation[
        "valid"
    ] is True

    assert validation[
        "birth_time_known"
    ] is False

    assert validation[
        "hour_pillar_available"
    ] is False


# ============================================================
# 2. Reading context layer
# ============================================================


def test_unknown_birth_time_context_keeps_status(
    unknown_reading_context,
):
    status = unknown_reading_context[
        "birth_time_status"
    ]

    assert status[
        "known"
    ] is False

    assert (
        status[
            "calculation_scope"
        ]
        == "three_pillars"
    )

    assert (
        status[
            "interpretation_scope"
        ]
        == "known_pillars_only"
    )


def test_unknown_birth_time_context_hour_is_empty_not_invented(
    unknown_reading_context,
):
    hour = (
        unknown_reading_context[
            "natal_chart"
        ][
            "pillars"
        ][
            "hour"
        ]
    )

    assert isinstance(
        hour,
        Mapping,
    )

    assert hour.get(
        "pillar"
    ) is None

    assert hour.get(
        "stem"
    ) is None

    assert hour.get(
        "branch"
    ) is None


@pytest.mark.parametrize(
    "section,expected_scope",
    (
        (
            "five_elements",
            "known_pillars_only",
        ),
        (
            "strength",
            "known_pillars_only",
        ),
        (
            "pattern",
            "known_pillars_only",
        ),
        (
            "useful_gods",
            "known_pillars_only",
        ),
    ),
)
def test_unknown_birth_time_context_marks_partial_evaluation(
    unknown_reading_context,
    section,
    expected_scope,
):
    data = unknown_reading_context[
        section
    ]

    assert (
        data[
            "scope"
        ]
        == expected_scope
    )

    assert (
        data[
            "is_complete_chart_evaluation"
        ]
        is False
    )

    assert (
        data[
            "provisional_due_to_unknown_birth_time"
        ]
        is True
    )


def test_unknown_birth_time_context_luck_is_estimated(
    unknown_reading_context,
):
    luck = unknown_reading_context[
        "luck"
    ]

    assert (
        luck[
            "luck_pillars"
        ][
            "timing_precision"
        ]
        == "estimated"
    )

    assert (
        luck[
            "luck_pillars"
        ][
            "timing_is_estimated"
        ]
        is True
    )

    assert (
        luck[
            "current_luck"
        ][
            "timing_precision"
        ]
        == "estimated"
    )

    assert (
        luck[
            "current_luck"
        ][
            "timing_is_estimated"
        ]
        is True
    )

    assert (
        luck[
            "integrated_luck"
        ][
            "timing_is_estimated"
        ]
        is True
    )


def test_unknown_birth_time_reading_context_validation_passes(
    unknown_reading_context,
):
    validation = (
        validate_reading_context(
            unknown_reading_context
        )
    )

    assert validation[
        "valid"
    ] is True


# ============================================================
# 3. Prompt facts
# ============================================================


def test_prompt_facts_contains_birth_time_status(
    unknown_reading_context,
):
    facts = build_prompt_facts(
        unknown_reading_context
    )

    status = facts[
        "birth_time_status"
    ]

    assert status[
        "known"
    ] is False

    assert (
        status[
            "calculation_scope"
        ]
        == "three_pillars"
    )

    assert (
        status[
            "interpretation_scope"
        ]
        == "known_pillars_only"
    )

    assert (
        status[
            "luck_start_timing_precision"
        ]
        == "estimated"
    )

    assert (
        status[
            "current_luck_precision"
        ]
        == "estimated"
    )


def test_prompt_facts_does_not_create_hour_pillar(
    unknown_reading_context,
):
    facts = build_prompt_facts(
        unknown_reading_context
    )

    hour = (
        facts[
            "natal_chart"
        ][
            "pillars"
        ][
            "hour"
        ]
    )

    assert hour.get(
        "pillar"
    ) is None


# ============================================================
# 4. Birth-time prompt guard
# ============================================================


def test_birth_time_prompt_block_is_enabled_for_unknown_time(
    unknown_reading_context,
):
    block = (
        build_birth_time_prompt_block(
            unknown_reading_context
        )
    )

    assert block

    assert (
        "出生時刻不明時の絶対条件"
        in block
    )


@pytest.mark.parametrize(
    "phrase",
    (
        "時柱を推測しない",
        "仮の時柱を作成・補完しない",
        "時干・時支",
        "年柱・月柱・日柱",
        "命式全体で確定している",
        "欠如を断定しない",
        "通根",
        "身強身弱",
        "格局",
        "用神",
        "大運開始年齢",
        "timing_precision",
        "estimated",
        "不明な情報は不明のまま扱い",
    ),
)
def test_birth_time_prompt_block_contains_required_guardrails(
    unknown_reading_context,
    phrase,
):
    block = (
        build_birth_time_prompt_block(
            unknown_reading_context
        )
    )

    assert phrase in block


def test_birth_time_prompt_block_is_empty_for_known_time(
    known_reading_context,
):
    block = (
        build_birth_time_prompt_block(
            known_reading_context
        )
    )

    assert block == ""


# ============================================================
# 5. Reading request
# ============================================================


def test_unknown_birth_time_user_prompt_contains_guard_block(
    unknown_reading_request,
):
    prompt = _request_user_prompt(
        unknown_reading_request
    )

    assert (
        "出生時刻不明時の絶対条件"
        in prompt
    )

    assert (
        "時柱を推測しない"
        in prompt
    )

    assert (
        "known_pillars_only"
        in prompt
    )

    assert (
        "estimated"
        in prompt
    )


def test_unknown_birth_time_system_prompt_contains_generic_guardrails(
    unknown_reading_request,
):
    prompt = _request_system_prompt(
        unknown_reading_request
    )

    assert (
        "出生時刻が不明"
        in prompt
    )

    assert (
        "時柱を推測"
        in prompt
    )

    assert (
        "命式全体"
        in prompt
    )

    assert (
        "estimated"
        in prompt
    )


@pytest.mark.parametrize(
    "phrase",
    (
        "身強身弱は入力された計算結果を再判定せず",
        "格局は入力された計算結果を再判定せず",
        "用神は入力された計算結果を再選定せず",
    ),
)
def test_unknown_birth_time_prompt_prohibits_ai_recalculation(
    unknown_reading_request,
    phrase,
):
    prompt = _request_user_prompt(
        unknown_reading_request
    )

    assert phrase in prompt


def test_unknown_birth_time_prompt_rejects_complete_element_absence_claim(
    unknown_reading_request,
):
    prompt = _request_user_prompt(
        unknown_reading_request
    )

    assert (
        "五行バランスは確認可能な三柱の範囲"
        in prompt
    )

    assert (
        "欠如を断定しない"
        in prompt
    )


def test_unknown_birth_time_prompt_marks_luck_timing_as_non_exact(
    unknown_reading_request,
):
    prompt = _request_user_prompt(
        unknown_reading_request
    )

    assert (
        "厳密な確定値として断定しない"
        in prompt
    )

    assert (
        "切り替わり時期に幅"
        in prompt
    )


# ============================================================
# 6. Generation payload
# ============================================================


def test_unknown_birth_time_generation_payload_is_ready(
    unknown_generation_payload,
):
    assert (
        unknown_generation_payload[
            "status"
        ]
        == "request_ready"
    )

    assert (
        unknown_generation_payload[
            "model"
        ]
        == TEST_MODEL
    )

    assert (
        unknown_generation_payload[
            "output_format"
        ]
        == "json"
    )


def test_unknown_birth_time_generation_payload_keeps_guardrails(
    unknown_generation_payload,
):
    system_prompt = (
        _payload_system_prompt(
            unknown_generation_payload
        )
    )

    user_prompt = (
        _payload_user_prompt(
            unknown_generation_payload
        )
    )

    assert (
        "出生時刻が不明"
        in system_prompt
    )

    assert (
        "出生時刻不明時の絶対条件"
        in user_prompt
    )

    assert (
        "時柱を推測しない"
        in user_prompt
    )

    assert (
        "known_pillars_only"
        in user_prompt
    )


def test_unknown_birth_time_generation_uses_strict_json_schema(
    unknown_generation_payload,
):
    fmt = (
        unknown_generation_payload[
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


# ============================================================
# 7. Known-time backward compatibility
# ============================================================


def test_known_birth_time_remains_four_pillars(
    known_chart_result,
):
    status = known_chart_result[
        "birth_time_status"
    ]

    assert status[
        "known"
    ] is True

    assert status[
        "hour_pillar_available"
    ] is True

    assert (
        status[
            "calculation_scope"
        ]
        == "four_pillars"
    )

    assert (
        status[
            "interpretation_scope"
        ]
        == "full_chart"
    )

    assert (
        known_chart_result[
            "chart"
        ][
            "hour"
        ]
        is not None
    )


def test_known_birth_time_context_is_complete(
    known_reading_context,
):
    for section in (
        "five_elements",
        "strength",
        "pattern",
        "useful_gods",
    ):
        data = known_reading_context[
            section
        ]

        assert (
            data[
                "is_complete_chart_evaluation"
            ]
            is True
        )

        assert (
            data[
                "provisional_due_to_unknown_birth_time"
            ]
            is False
        )

    assert (
        known_reading_context[
            "luck"
        ][
            "luck_pillars"
        ][
            "timing_precision"
        ]
        == "normal"
    )

    assert (
        known_reading_context[
            "luck"
        ][
            "current_luck"
        ][
            "timing_precision"
        ]
        == "normal"
    )


def test_known_birth_time_user_prompt_has_no_conditional_guard_block(
    known_reading_context,
):
    request = build_reading_request(
        known_reading_context,
        sections=ALL_SECTIONS,
        output_format="json",
    )

    user_prompt = (
        _request_user_prompt(
            request
        )
    )

    assert (
        "【出生時刻不明時の絶対条件】"
        not in user_prompt
    )


# ============================================================
# 8. Determinism
# ============================================================


def test_unknown_birth_time_context_is_reproducible(
    unknown_chart_result,
):
    first = build_reading_context(
        unknown_chart_result
    )

    second = build_reading_context(
        unknown_chart_result
    )

    assert first == second


def test_unknown_birth_time_request_is_reproducible(
    unknown_reading_context,
):
    kwargs = {
        "sections": ALL_SECTIONS,
        "output_format": "json",
    }

    first = build_reading_request(
        unknown_reading_context,
        **kwargs,
    )

    second = build_reading_request(
        unknown_reading_context,
        **kwargs,
    )

    assert first == second


# ============================================================
# Final gate
# ============================================================


def test_unknown_birth_time_v1_final_gate(
    unknown_chart_result,
    unknown_reading_context,
    unknown_reading_request,
    unknown_generation_payload,
):
    chart_status = unknown_chart_result[
        "birth_time_status"
    ]

    context_status = unknown_reading_context[
        "birth_time_status"
    ]

    user_prompt = _request_user_prompt(
        unknown_reading_request
    )

    payload_prompt = _payload_user_prompt(
        unknown_generation_payload
    )

    assert (
        unknown_chart_result[
            "chart"
        ][
            "hour"
        ]
        is None
    )

    assert (
        chart_status[
            "calculation_scope"
        ]
        == "three_pillars"
    )

    assert (
        context_status[
            "interpretation_scope"
        ]
        == "known_pillars_only"
    )

    assert (
        unknown_reading_context[
            "luck"
        ][
            "luck_pillars"
        ][
            "timing_precision"
        ]
        == "estimated"
    )

    for phrase in (
        "時柱を推測しない",
        "欠如を断定しない",
        "身強身弱",
        "格局",
        "用神",
        "estimated",
    ):
        assert phrase in user_prompt
        assert phrase in payload_prompt

    assert (
        unknown_generation_payload[
            "status"
        ]
        == "request_ready"
    )
