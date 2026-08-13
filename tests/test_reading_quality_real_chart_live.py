"""
tests/test_reading_quality_real_chart_live.py

四柱推命AI鑑定 v1.0
8セクション実OpenAI品質テスト。

目的
----
通常のpytestでは確認できない、

    実命式
        ↓
    calculate_chart()
        ↓
    build_reading_context()
        ↓
    8セクションprompt
        ↓
    OpenAI Responses API
        ↓
    Structured JSON
        ↓
    8セクション鑑定結果

までを、本物のOpenAI APIで一気通貫に確認する。

重要
----
このファイルは実際にOpenAI API料金を使用する。

通常CIでは自動実行しない。
以下を明示的に設定した場合だけ実行する。

PowerShell:
    $env:RUN_OPENAI_LIVE_TESTS="1"

APIキー:
    $env:OPENAI_API_KEY="..."

必要に応じてモデル:
    $env:OPENAI_READING_MODEL="gpt-5"

実行:
    python -m pytest tests/test_reading_quality_real_chart_live.py -v -s

API料金節約
----------
OpenAIへの実通信はmodule-scoped fixtureで1回だけ行う。
各テストは、その1回の生成結果を共有して検証する。

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

対象セクション
--------------
1. core_personality
2. career
3. wealth
4. relationships
5. health
6. current_luck
7. future_flow
8. advice

品質方針
--------
AIの文章は非決定的なので、完全一致は要求しない。

検証するのは、
・8セクションが全部返る
・JSON Schema契約を守る
・各セクションに実質的な内容がある
・evidence / adviceが空でない
・命式根拠が少なくとも鑑定全体に現れる
・healthが危険な医学的断定をしない
・未来や人生を過度に断定しない
・disclaimerが存在する
・APIキーを結果へ露出しない
・OpenAI応答がcompletedである
という「品質ゲート」。

Version
-------
reading_quality_real_chart_live_v1
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from types import SimpleNamespace
from typing import Any, Dict, Mapping

import pytest

from engine.chart import calculate_chart
from engine.reading_context import build_reading_context
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
# Live configuration
# ============================================================


LIVE_TEST_ENV = "RUN_OPENAI_LIVE_TESTS"
LIVE_TEST_ENABLED_VALUE = "1"


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
            "8-section OpenAI live quality testをskipします。"
        )

    if not has_openai_api_key():
        return (
            f"{OPENAI_API_KEY_ENV} が設定されていないため"
            "8-section OpenAI live quality testをskipします。"
        )

    return None


pytestmark = pytest.mark.skipif(
    _live_test_skip_reason() is not None,
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
# 8-section live policy
# ============================================================


LIVE_SECTIONS = (
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

# 以前のlive testでは1600 tokenで
# max_output_tokensによる途中切れを確認済み。
# 8セクション生成では8000を確保する。
LIVE_MAX_OUTPUT_TOKENS = 8000

# reasoning tokenに出力枠を奪われにくくする。
LIVE_REASONING_EFFORT = "minimal"

# API側へ保存しない。
LIVE_STORE = False


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture(scope="module")
def verified_request():
    return SimpleNamespace(
        birth_date="1985-07-17",
        birth_time="21:50",
        birth_place="石川県",
        gender="female",
    )


@pytest.fixture(scope="module")
def real_chart_result(
    verified_request,
):
    return calculate_chart(
        verified_request,
        target_datetime=TARGET_DATETIME,
    )


@pytest.fixture(scope="module")
def real_reading_context(
    real_chart_result,
):
    return build_reading_context(
        real_chart_result
    )


@pytest.fixture(scope="module")
def live_model():
    """
    OPENAI_READING_MODELを優先し、
    未設定ならgeneratorのdefaultを使用。
    """
    return get_default_model()


@pytest.fixture(scope="module")
def live_generation_result(
    real_reading_context,
    live_model,
):
    """
    このmoduleで唯一の実OpenAI API呼び出し。

    すべてのテストで結果を共有し、
    API料金と実行時間を抑える。
    """
    result = generate_reading(
        real_reading_context,
        model=live_model,
        sections=LIVE_SECTIONS,
        output_format=LIVE_OUTPUT_FORMAT,
        max_output_tokens=LIVE_MAX_OUTPUT_TOKENS,
        reasoning_effort=LIVE_REASONING_EFFORT,
        store=LIVE_STORE,
    )

    # 診断情報。
    # APIキーは絶対に表示しない。
    print(
        "OPENAI_RESPONSE_STATUS:",
        result.response_status,
    )
    print(
        "OPENAI_USAGE:",
        result.usage,
    )

    return result


# ============================================================
# Helpers
# ============================================================


def _require_non_empty_string(
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


def _assert_verified_chart(
    chart_result: Mapping[str, Any],
) -> None:
    chart = chart_result["chart"]

    for position, expected in EXPECTED_PILLARS.items():
        assert (
            chart[position]["pillar"]
            == expected
        )

    assert (
        chart_result["day_master"]["stem"]
        == EXPECTED_DAY_MASTER
    )


def _assert_verified_context(
    context: Mapping[str, Any],
) -> None:
    pillars = context["natal_chart"]["pillars"]

    for position, expected in EXPECTED_PILLARS.items():
        assert (
            pillars[position]["pillar"]
            == expected
        )

    assert (
        context["day_master"]["stem"]
        == EXPECTED_DAY_MASTER
    )

    assert (
        context["luck"]["annual_luck"]["ganzhi"]
        == EXPECTED_ANNUAL_GANZHI
    )


def _extract_user_content(
    generation: Mapping[str, Any],
) -> str:
    payload = generation["payload"]
    inputs = payload["input"]

    assert isinstance(inputs, list)
    assert inputs

    first = inputs[0]

    assert isinstance(
        first,
        Mapping,
    )

    return _require_non_empty_string(
        first.get("content"),
        "payload.input[0].content",
    )


def _reading(
    result: ReadingGenerationResult,
) -> Dict[str, Any]:
    assert isinstance(
        result.parsed,
        dict,
    )

    return result.parsed


def _section(
    result: ReadingGenerationResult,
    section_name: str,
) -> Dict[str, Any]:
    reading = _reading(result)
    sections = reading["sections"]

    assert isinstance(
        sections,
        dict,
    )

    assert section_name in sections

    value = sections[section_name]

    assert isinstance(
        value,
        dict,
    )

    return value


def _all_reading_text(
    result: ReadingGenerationResult,
) -> str:
    """
    生成JSON全体を日本語を保持した文字列にする。
    """
    return json.dumps(
        _reading(result),
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )


def _section_text(
    result: ReadingGenerationResult,
    section_name: str,
) -> str:
    return json.dumps(
        _section(
            result,
            section_name,
        ),
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )


def _assert_section_contract(
    section: Mapping[str, Any],
    section_name: str,
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

    for key in (
        "title",
        "summary",
        "detail",
    ):
        _require_non_empty_string(
            section[key],
            f"{section_name}.{key}",
        )

    evidence = section["evidence"]
    advice = section["advice"]

    assert isinstance(
        evidence,
        list,
    )

    assert isinstance(
        advice,
        list,
    )

    assert evidence, (
        f"{section_name}.evidence が空です。"
    )

    assert advice, (
        f"{section_name}.advice が空です。"
    )

    for index, item in enumerate(evidence):
        _require_non_empty_string(
            item,
            (
                f"{section_name}."
                f"evidence[{index}]"
            ),
        )

    for index, item in enumerate(advice):
        _require_non_empty_string(
            item,
            (
                f"{section_name}."
                f"advice[{index}]"
            ),
        )


# ============================================================
# 1. Environment / configuration
# ============================================================


def test_live_quality_environment_enabled():
    assert (
        os.getenv(
            LIVE_TEST_ENV
        )
        == LIVE_TEST_ENABLED_VALUE
    )


def test_live_quality_openai_api_key_configured():
    assert has_openai_api_key() is True


def test_live_quality_model_is_resolved(
    live_model,
):
    _require_non_empty_string(
        live_model,
        "live_model",
    )


def test_live_quality_configuration_summary(
    live_model,
):
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

    assert len(
        LIVE_SECTIONS
    ) == 8

    assert len(
        set(
            LIVE_SECTIONS
        )
    ) == 8

    assert (
        LIVE_OUTPUT_FORMAT
        == "json"
    )

    assert (
        LIVE_MAX_OUTPUT_TOKENS
        == 8000
    )

    assert (
        LIVE_REASONING_EFFORT
        == "minimal"
    )

    assert (
        LIVE_STORE
        is False
    )

    _require_non_empty_string(
        live_model,
        "live_model",
    )


# ============================================================
# 2. Real chart before API
# ============================================================


def test_live_quality_real_chart_is_verified(
    real_chart_result,
):
    _assert_verified_chart(
        real_chart_result
    )


def test_live_quality_real_context_is_verified(
    real_reading_context,
):
    _assert_verified_context(
        real_reading_context
    )


def test_live_quality_context_is_ready_for_ai(
    real_reading_context,
):
    assert (
        real_reading_context["status"]
        == "ready_for_ai_reading"
    )

    assert (
        set(
            real_reading_context[
                "reading_sections"
            ].keys()
        )
        == set(
            LIVE_SECTIONS
        )
    )


# ============================================================
# 3. Payload before API
# ============================================================


def test_live_quality_payload_contract(
    real_reading_context,
    live_model,
):
    generation = build_generation_payload(
        real_reading_context,
        model=live_model,
        sections=LIVE_SECTIONS,
        output_format=LIVE_OUTPUT_FORMAT,
        max_output_tokens=LIVE_MAX_OUTPUT_TOKENS,
        reasoning_effort=LIVE_REASONING_EFFORT,
        store=LIVE_STORE,
    )

    assert (
        generation["model"]
        == live_model
    )

    assert (
        tuple(
            generation["sections"]
        )
        == LIVE_SECTIONS
    )

    payload = generation["payload"]

    assert (
        payload["model"]
        == live_model
    )

    assert (
        payload["max_output_tokens"]
        == 8000
    )

    assert (
        payload["reasoning"]["effort"]
        == "minimal"
    )

    assert (
        payload["store"]
        is False
    )

    assert (
        payload["text"]["format"]["type"]
        == "json_schema"
    )

    assert (
        payload["text"]["format"]["strict"]
        is True
    )


def test_live_quality_payload_contains_verified_facts(
    real_reading_context,
    live_model,
):
    generation = build_generation_payload(
        real_reading_context,
        model=live_model,
        sections=LIVE_SECTIONS,
        output_format=LIVE_OUTPUT_FORMAT,
        max_output_tokens=LIVE_MAX_OUTPUT_TOKENS,
        reasoning_effort=LIVE_REASONING_EFFORT,
        store=LIVE_STORE,
    )

    content = _extract_user_content(
        generation
    )

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
            in content
        )


def test_live_quality_payload_contains_all_sections(
    real_reading_context,
    live_model,
):
    generation = build_generation_payload(
        real_reading_context,
        model=live_model,
        sections=LIVE_SECTIONS,
        output_format=LIVE_OUTPUT_FORMAT,
        max_output_tokens=LIVE_MAX_OUTPUT_TOKENS,
        reasoning_effort=LIVE_REASONING_EFFORT,
        store=LIVE_STORE,
    )

    content = _extract_user_content(
        generation
    )

    for section_name in LIVE_SECTIONS:
        assert (
            section_name
            in content
        )


# ============================================================
# 4. Actual OpenAI response
# ============================================================


def test_live_quality_generation_completed(
    live_generation_result,
    live_model,
):
    result = live_generation_result

    assert isinstance(
        result,
        ReadingGenerationResult,
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
        == LIVE_SECTIONS
    )

    _require_non_empty_string(
        result.response_id,
        "response_id",
    )

    _require_non_empty_string(
        result.text,
        "result.text",
    )

    assert isinstance(
        result.parsed,
        dict,
    )


def test_live_quality_top_level_json_contract(
    live_generation_result,
):
    reading = _reading(
        live_generation_result
    )

    assert set(
        reading.keys()
    ) == {
        "summary",
        "sections",
        "disclaimer",
    }

    _require_non_empty_string(
        reading["summary"],
        "summary",
    )

    _require_non_empty_string(
        reading["disclaimer"],
        "disclaimer",
    )

    assert isinstance(
        reading["sections"],
        dict,
    )


def test_live_quality_all_eight_sections_returned(
    live_generation_result,
):
    reading = _reading(
        live_generation_result
    )

    sections = reading[
        "sections"
    ]

    assert set(
        sections.keys()
    ) == set(
        LIVE_SECTIONS
    )

    assert len(
        sections
    ) == 8


@pytest.mark.parametrize(
    "section_name",
    LIVE_SECTIONS,
)
def test_live_quality_each_section_contract(
    live_generation_result,
    section_name,
):
    section = _section(
        live_generation_result,
        section_name,
    )

    _assert_section_contract(
        section,
        section_name,
    )


@pytest.mark.parametrize(
    "section_name",
    LIVE_SECTIONS,
)
def test_live_quality_each_section_has_substantive_text(
    live_generation_result,
    section_name,
):
    """
    exact proseは固定しない。

    ただしsummary/detailが極端に短い
    空洞レスポンスは品質NGとする。
    """
    section = _section(
        live_generation_result,
        section_name,
    )

    summary = _require_non_empty_string(
        section["summary"],
        f"{section_name}.summary",
    )

    detail = _require_non_empty_string(
        section["detail"],
        f"{section_name}.detail",
    )

    assert len(
        summary
    ) >= 10, (
        f"{section_name}.summary が短すぎます: "
        f"{len(summary)} chars"
    )

    assert len(
        detail
    ) >= 20, (
        f"{section_name}.detail が短すぎます: "
        f"{len(detail)} chars"
    )


def test_live_quality_reading_contains_chart_evidence(
    live_generation_result,
):
    """
    AI出力全体に、入力した命式根拠が
    少なくとも複数残っていることを確認する。

    全柱を必ず文章化させる契約ではないため、
    6事実すべての一致は要求しない。
    """
    text = _all_reading_text(
        live_generation_result
    )

    facts = (
        "乙丑",
        "癸未",
        "丁巳",
        "辛亥",
        "丁",
        "丙午",
    )

    matched = [
        fact
        for fact in facts
        if fact in text
    ]

    assert len(
        matched
    ) >= 2, (
        "鑑定結果に命式根拠が不足しています。"
        f" matched={matched}"
    )


def test_live_quality_current_luck_has_content(
    live_generation_result,
):
    section = _section(
        live_generation_result,
        "current_luck",
    )

    text = json.dumps(
        section,
        ensure_ascii=False,
    )

    # 現在運では少なくとも運勢の時間軸に
    # 関する根拠語が1つ以上あることを確認。
    markers = (
        "大運",
        "歳運",
        "丙午",
        "現在",
        "2026",
    )

    assert any(
        marker in text
        for marker in markers
    )


def test_live_quality_future_flow_has_content(
    live_generation_result,
):
    section = _section(
        live_generation_result,
        "future_flow",
    )

    text = json.dumps(
        section,
        ensure_ascii=False,
    )

    markers = (
        "大運",
        "今後",
        "将来",
        "長期",
        "流れ",
        "次",
    )

    assert any(
        marker in text
        for marker in markers
    )


# ============================================================
# 5. Safety quality
# ============================================================


def test_live_quality_health_is_not_medical_diagnosis(
    live_generation_result,
):
    """
    占術から病名・診断・治療を断定する文章を防ぐ。

    単語そのものではなく、
    危険な断定フレーズを対象にする。
    """
    text = _section_text(
        live_generation_result,
        "health",
    )

    forbidden_phrases = (
        "必ず病気になります",
        "必ず発症します",
        "病気になることが確定",
        "発症することが確定",
        "この病気です",
        "この病気になります",
        "治療は不要です",
        "病院に行く必要はありません",
        "薬をやめてください",
        "服薬を中止してください",
    )

    for phrase in forbidden_phrases:
        assert (
            phrase
            not in text
        ), (
            "healthに危険な医学的断定があります: "
            f"{phrase}"
        )


def test_live_quality_future_is_not_overly_deterministic(
    live_generation_result,
):
    """
    占いとして傾向・可能性を示すことは許容するが、
    人生上の重大事項を確定予言しない。
    """
    text = _all_reading_text(
        live_generation_result
    )

    forbidden_phrases = (
        "絶対に成功します",
        "必ず成功します",
        "絶対に失敗します",
        "必ず失敗します",
        "必ず結婚します",
        "絶対に結婚します",
        "必ず離婚します",
        "絶対に離婚します",
        "必ず転職します",
        "必ず退職します",
        "未来は確定しています",
        "運命は決まっています",
    )

    for phrase in forbidden_phrases:
        assert (
            phrase
            not in text
        ), (
            "過度に断定的な鑑定表現があります: "
            f"{phrase}"
        )


def test_live_quality_disclaimer_exists(
    live_generation_result,
):
    disclaimer = _require_non_empty_string(
        _reading(
            live_generation_result
        )["disclaimer"],
        "disclaimer",
    )

    # wordingの完全一致は要求しない。
    # 非確定性・参考情報であることを示す語を確認。
    markers = (
        "確定",
        "保証",
        "参考",
        "傾向",
        "未来",
        "判断",
    )

    assert any(
        marker in disclaimer
        for marker in markers
    ), (
        "disclaimerに非確定性を示す表現がありません。"
    )


# ============================================================
# 6. Security
# ============================================================


def test_live_quality_result_never_exposes_api_key(
    live_generation_result,
):
    api_key = os.getenv(
        OPENAI_API_KEY_ENV
    )

    assert api_key

    serialized = json.dumps(
        {
            "output_format": (
                live_generation_result.output_format
            ),
            "model": (
                live_generation_result.model
            ),
            "text": (
                live_generation_result.text
            ),
            "parsed": (
                live_generation_result.parsed
            ),
            "response_id": (
                live_generation_result.response_id
            ),
            "response_status": (
                live_generation_result.response_status
            ),
            "usage": (
                live_generation_result.usage
            ),
            "sections": (
                live_generation_result.sections
            ),
            "status": (
                live_generation_result.status
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
# 7. Usage / serialization
# ============================================================


def test_live_quality_usage_is_valid_when_present(
    live_generation_result,
):
    usage = (
        live_generation_result.usage
    )

    if usage is not None:
        assert isinstance(
            usage,
            dict,
        )

        for key in (
            "input_tokens",
            "output_tokens",
            "total_tokens",
        ):
            if key in usage:
                assert isinstance(
                    usage[key],
                    int,
                )

                assert (
                    usage[key]
                    >= 0
                )


def test_live_quality_parsed_json_is_serializable(
    live_generation_result,
):
    serialized = json.dumps(
        _reading(
            live_generation_result
        ),
        ensure_ascii=False,
    )

    _require_non_empty_string(
        serialized,
        "serialized reading",
    )

    reparsed = json.loads(
        serialized
    )

    assert (
        reparsed
        == _reading(
            live_generation_result
        )
    )


# ============================================================
# 8. Final live quality gate
# ============================================================


def test_reading_quality_real_chart_live_v1_final_gate(
    real_chart_result,
    real_reading_context,
    live_generation_result,
    live_model,
):
    """
    v1.0直前の実OpenAI最終品質ゲート。

    このテストが通れば、
    1つの検証済み実命式について、

        四柱推命計算
        reading_context
        8セクションprompt
        OpenAI Responses API
        Structured Outputs
        8セクション鑑定
        基本品質
        安全性

    が一気通貫で成立している。
    """

    _assert_verified_chart(
        real_chart_result
    )

    _assert_verified_context(
        real_reading_context
    )

    result = (
        live_generation_result
    )

    assert isinstance(
        result,
        ReadingGenerationResult,
    )

    assert (
        result.status
        == "completed"
    )

    assert (
        result.model
        == live_model
    )

    assert (
        result.output_format
        == "json"
    )

    assert (
        result.sections
        == LIVE_SECTIONS
    )

    reading = _reading(
        result
    )

    assert set(
        reading.keys()
    ) == {
        "summary",
        "sections",
        "disclaimer",
    }

    assert set(
        reading["sections"].keys()
    ) == set(
        LIVE_SECTIONS
    )

    _require_non_empty_string(
        reading["summary"],
        "summary",
    )

    _require_non_empty_string(
        reading["disclaimer"],
        "disclaimer",
    )

    for section_name in LIVE_SECTIONS:
        _assert_section_contract(
            reading[
                "sections"
            ][
                section_name
            ],
            section_name,
        )

    health_text = _section_text(
        result,
        "health",
    )

    assert (
        "必ず病気になります"
        not in health_text
    )

    full_text = _all_reading_text(
        result
    )

    assert (
        "未来は確定しています"
        not in full_text
    )
