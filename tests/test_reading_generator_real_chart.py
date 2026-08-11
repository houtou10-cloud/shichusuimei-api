"""
tests/test_reading_generator_real_chart.py

実命式を使用した
reading_context -> reading_prompt -> reading_generator
統合テスト。

目的
----
1985-07-17 21:50 石川県 女性
という外部照合済み実命式について、

    calculate_chart()
        ↓
    build_reading_context()
        ↓
    build_generation_payload()
        ↓
    generate_reading()
        ↓
    Fake OpenAI Responses API

までのAI鑑定生成パイプラインが
一貫して動作することを確認する。

重要
----
このテストでは実際のOpenAI APIを呼ばない。

Fake clientを注入することで、

- APIキー不要
- API課金なし
- ネットワーク不要
- CIで再現可能

な統合テストとする。

Verified natal chart
--------------------
年柱: 乙丑
月柱: 癸未
日柱: 丁巳
時柱: 辛亥
日主: 丁

target_datetime:
2026-08-10 15:36

歳運:
丙午

Version
-------
reading_generator_real_chart_v2
"""

from __future__ import annotations

import json
from datetime import datetime
from types import SimpleNamespace
from typing import Any, Dict

import pytest

from engine.chart import calculate_chart
from engine.reading_context import (
    build_reading_context,
)
from engine.reading_generator import (
    ReadingGenerationResult,
    build_generation_payload,
    calculate_ai_reading,
    generate_reading,
    generate_reading_from_context,
    generate_reading_json,
    generate_reading_text,
    prepare_ai_generation_payload,
)


# ============================================================
# Verified chart constants
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

TEST_MODEL = "gpt-5"


# ============================================================
# Request / chart fixtures
# ============================================================


@pytest.fixture
def verified_request():
    """
    外部照合済み実命式の入力。
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
    実際のcalculate_chart()を使用して
    命式を生成する。
    """

    return calculate_chart(
        verified_request,
        target_datetime=TARGET_DATETIME,
    )


@pytest.fixture
def real_reading_context(
    real_chart_result,
):
    """
    実際のchart_resultから
    reading_context_v1を生成する。
    """

    return build_reading_context(
        real_chart_result
    )


# ============================================================
# Fake OpenAI Responses API
# ============================================================


class FakeUsage:
    """
    OpenAI SDK usage objectの簡易Fake。
    """

    input_tokens = 1200
    output_tokens = 600
    total_tokens = 1800

    def model_dump(
        self,
    ) -> Dict[str, Any]:
        return {
            "input_tokens": (
                self.input_tokens
            ),
            "output_tokens": (
                self.output_tokens
            ),
            "total_tokens": (
                self.total_tokens
            ),
        }


class FakeTextResponse:
    """
    text出力用Fake response。
    """

    id = "resp_real_chart_text"
    status = "completed"

    output_text = (
        "全体要約\n"
        "この命式では日主は丁です。\n\n"
        "本質・性格\n"
        "丁の性質を中心に、"
        "命式全体のバランスから読み解きます。\n\n"
        "仕事・適職\n"
        "計算済みの命式を基に、"
        "能力を活かしやすい働き方を考えます。\n\n"
        "総合アドバイス\n"
        "運勢を絶対視せず、"
        "現実の状況と合わせて活用してください。"
    )

    usage = FakeUsage()


class FakeJSONResponse:
    """
    JSON出力用Fake response。
    """

    id = "resp_real_chart_json"
    status = "completed"

    usage = FakeUsage()

    def __init__(
        self,
        sections,
    ):
        section_data = {}

        titles = {
            "core_personality": "本質・性格",
            "career": "仕事・適職",
            "wealth": "金運",
            "relationships": "恋愛・人間関係",
            "health": "健康傾向",
            "current_luck": "現在の運勢",
            "future_flow": "今後の流れ",
            "advice": "総合アドバイス",
        }

        for section in sections:
            section_data[
                section
            ] = {
                "title": (
                    titles[
                        section
                    ]
                ),
                "summary": (
                    f"{titles[section]}の要約です。"
                ),
                "detail": (
                    "入力された計算済み命式を"
                    "変更せずに解釈した鑑定内容です。"
                ),
                "evidence": [
                    "日主は丁",
                    "命式は乙丑・癸未・丁巳・辛亥",
                ],
                "advice": [
                    "計算結果を現実の状況と"
                    "合わせて活用してください。"
                ],
            }

        payload = {
            "summary": (
                "計算済みの四柱推命データを基にした"
                "総合鑑定です。"
            ),
            "sections": (
                section_data
            ),
            "disclaimer": (
                "四柱推命は将来を確定するものではなく、"
                "傾向を考えるための参考情報です。"
            ),
        }

        self.output_text = (
            json.dumps(
                payload,
                ensure_ascii=False,
            )
        )


class FakeResponses:
    """
    client.responses.create() のFake。
    """

    def __init__(
        self,
        *,
        response_type: str = "text",
    ):
        self.response_type = (
            response_type
        )
        self.calls = []

    def create(
        self,
        **kwargs,
    ):
        """
        Responses APIへのpayloadを保存し、
        Fake responseを返す。
        """

        self.calls.append(
            kwargs
        )

        if (
            self.response_type
            == "json"
        ):
            sections = (
                _extract_sections_from_payload(
                    kwargs
                )
            )

            return FakeJSONResponse(
                sections
            )

        return FakeTextResponse()


class FakeClient:
    """
    OpenAI clientのFake。
    """

    def __init__(
        self,
        *,
        response_type: str = "text",
    ):
        self.responses = (
            FakeResponses(
                response_type=(
                    response_type
                )
            )
        )


# ============================================================
# Fake helper
# ============================================================


def _extract_sections_from_payload(
    payload: Dict[str, Any],
):
    """
    Structured OutputsのJSON Schemaから
    requested sectionsを取得する。

    schemaが存在しない場合は
    デフォルトの主要セクションを返す。
    """

    try:
        return list(
            payload[
                "text"
            ][
                "format"
            ][
                "schema"
            ][
                "properties"
            ][
                "sections"
            ][
                "properties"
            ].keys()
        )

    except (
        KeyError,
        TypeError,
        AttributeError,
    ):
        return [
            "core_personality",
            "career",
            "advice",
        ]


# ============================================================
# Real chart sanity checks
# ============================================================


def test_real_chart_pillars_are_verified(
    real_chart_result,
):
    """
    AI層へ渡す前に、
    元の命式そのものが正式基準と一致することを確認。

    calculate_chart() の正式構造は
    result["chart"][position]["pillar"]。
    """

    pillars = (
        real_chart_result[
            "chart"
        ]
    )

    for name, expected in (
        EXPECTED_PILLARS.items()
    ):
        assert (
            pillars[
                name
            ][
                "pillar"
            ]
            == expected
        )


def test_real_chart_day_master_is_verified(
    real_chart_result,
):
    """
    日主が丁であることを確認。

    calculate_chart() のday_masterは
    {"stem": "丁"} 形式。
    """

    assert (
        real_chart_result[
            "day_master"
        ][
            "stem"
        ]
        == EXPECTED_DAY_MASTER
    )


# ============================================================
# Reading context integration
# ============================================================


def test_real_reading_context_schema(
    real_reading_context,
):
    """
    reading_context_v1が生成される。
    """

    assert (
        real_reading_context[
            "schema_version"
        ]
        == "reading_context_v1"
    )


def test_real_reading_context_day_master(
    real_reading_context,
):
    """
    reading_contextでも日主丁が維持される。
    """

    day_master = (
        real_reading_context[
            "day_master"
        ]
    )

    assert isinstance(
        day_master,
        dict,
    )

    assert (
        day_master[
            "stem"
        ]
        == EXPECTED_DAY_MASTER
    )


def test_real_reading_context_pillars(
    real_reading_context,
):
    """
    reading_contextの四柱が
    元命式から変化していないことを確認。
    """

    pillars = (
        real_reading_context[
            "natal_chart"
        ][
            "pillars"
        ]
    )

    for name, expected in (
        EXPECTED_PILLARS.items()
    ):
        assert (
            pillars[
                name
            ][
                "pillar"
            ]
            == expected
        )


def test_real_reading_context_annual_luck(
    real_reading_context,
):
    """
    2026年歳運が丙午であることを確認。
    """

    annual = (
        real_reading_context[
            "luck"
        ][
            "annual_luck"
        ]
    )

    assert (
        annual[
            "ganzhi"
        ]
        == EXPECTED_ANNUAL_GANZHI
    )


# ============================================================
# Prompt / generation payload
# ============================================================


def test_real_chart_build_generation_payload(
    real_reading_context,
):
    """
    実命式reading_contextから
    Responses API payloadを生成できる。
    """

    result = (
        build_generation_payload(
            real_reading_context,
            model=TEST_MODEL,
            sections=[
                "core_personality",
                "career",
                "advice",
            ],
            output_format="text",
            store=False,
        )
    )

    assert (
        result[
            "status"
        ]
        == "request_ready"
    )

    assert (
        result[
            "model"
        ]
        == TEST_MODEL
    )

    assert result[
        "sections"
    ] == [
        "core_personality",
        "career",
        "advice",
    ]

    payload = (
        result[
            "payload"
        ]
    )

    assert (
        payload[
            "model"
        ]
        == TEST_MODEL
    )

    assert (
        payload[
            "store"
        ]
        is False
    )

    assert (
        payload[
            "reasoning"
        ][
            "effort"
        ]
        == "low"
    )

    assert isinstance(
        payload[
            "instructions"
        ],
        str,
    )

    assert (
        payload[
            "instructions"
        ]
    )

    assert isinstance(
        payload[
            "input"
        ],
        list,
    )


def test_real_chart_prompt_contains_verified_day_master(
    real_reading_context,
):
    """
    AIへ送信するuser promptに
    日主丁が含まれていることを確認。
    """

    result = (
        build_generation_payload(
            real_reading_context,
            model=TEST_MODEL,
            sections=[
                "core_personality",
            ],
            output_format="text",
        )
    )

    user_content = (
        result[
            "payload"
        ][
            "input"
        ][
            0
        ][
            "content"
        ]
    )

    assert (
        "丁"
        in user_content
    )


def test_real_chart_prompt_contains_verified_pillars(
    real_reading_context,
):
    """
    AIへ送るpromptに
    正式な四柱が保持されていることを確認。
    """

    result = (
        build_generation_payload(
            real_reading_context,
            model=TEST_MODEL,
            sections=[
                "core_personality",
            ],
            output_format="text",
        )
    )

    user_content = (
        result[
            "payload"
        ][
            "input"
        ][
            0
        ][
            "content"
        ]
    )

    for ganzhi in (
        "乙丑",
        "癸未",
        "丁巳",
        "辛亥",
    ):
        assert (
            ganzhi
            in user_content
        )


def test_real_chart_prompt_does_not_replace_day_pillar(
    real_reading_context,
):
    """
    正式日柱丁巳が
    AI入力まで保持されていることを確認。
    """

    result = (
        build_generation_payload(
            real_reading_context,
            model=TEST_MODEL,
            sections=[
                "core_personality",
            ],
            output_format="text",
        )
    )

    user_content = (
        result[
            "payload"
        ][
            "input"
        ][
            0
        ][
            "content"
        ]
    )

    assert (
        "丁巳"
        in user_content
    )


def test_prepare_ai_generation_payload_real_chart(
    real_reading_context,
):
    """
    prepare_ai_generation_payload aliasでも
    実命式payloadを生成できる。
    """

    result = (
        prepare_ai_generation_payload(
            real_reading_context,
            model=TEST_MODEL,
            sections=[
                "career",
                "advice",
            ],
            output_format="text",
        )
    )

    assert (
        result[
            "status"
        ]
        == "request_ready"
    )

    assert result[
        "sections"
    ] == [
        "career",
        "advice",
    ]


# ============================================================
# Fake Responses API - text
# ============================================================


def test_generate_reading_real_chart_text(
    real_reading_context,
):
    """
    実命式からFake Responses APIを通して
    text鑑定を生成できる。
    """

    client = FakeClient(
        response_type="text"
    )

    result = generate_reading(
        real_reading_context,
        client=client,
        model=TEST_MODEL,
        sections=[
            "core_personality",
            "career",
            "advice",
        ],
        output_format="text",
        store=False,
    )

    assert isinstance(
        result,
        ReadingGenerationResult,
    )

    assert (
        result.output_format
        == "text"
    )

    assert (
        result.model
        == TEST_MODEL
    )

    assert (
        result.status
        == "completed"
    )

    assert (
        result.response_status
        == "completed"
    )

    assert (
        result.response_id
        == "resp_real_chart_text"
    )

    assert result.sections == (
        "core_personality",
        "career",
        "advice",
    )

    assert isinstance(
        result.text,
        str,
    )

    assert result.text

    assert (
        "丁"
        in result.text
    )

    assert (
        result.parsed
        is None
    )


def test_generate_reading_real_chart_calls_responses_api_once(
    real_reading_context,
):
    """
    Responses APIが1回だけ呼ばれる。
    """

    client = FakeClient(
        response_type="text"
    )

    generate_reading(
        real_reading_context,
        client=client,
        model=TEST_MODEL,
        sections=[
            "core_personality",
        ],
        output_format="text",
    )

    assert (
        len(
            client.responses.calls
        )
        == 1
    )


def test_generate_reading_real_chart_payload_reaches_client(
    real_reading_context,
):
    """
    model/store/reasoning等の設定が
    Fake clientまで到達する。
    """

    client = FakeClient(
        response_type="text"
    )

    generate_reading(
        real_reading_context,
        client=client,
        model=TEST_MODEL,
        sections=[
            "career",
        ],
        output_format="text",
        max_output_tokens=4321,
        reasoning_effort="low",
        store=False,
    )

    call = (
        client.responses.calls[
            0
        ]
    )

    assert (
        call[
            "model"
        ]
        == TEST_MODEL
    )

    assert (
        call[
            "max_output_tokens"
        ]
        == 4321
    )

    assert (
        call[
            "reasoning"
        ][
            "effort"
        ]
        == "low"
    )

    assert (
        call[
            "store"
        ]
        is False
    )


def test_generate_reading_text_real_chart(
    real_reading_context,
):
    """
    generate_reading_text() convenience API。
    """

    client = FakeClient(
        response_type="text"
    )

    text = generate_reading_text(
        real_reading_context,
        client=client,
        model=TEST_MODEL,
        sections=[
            "core_personality",
            "career",
            "advice",
        ],
    )

    assert isinstance(
        text,
        str,
    )

    assert text

    assert (
        "丁"
        in text
    )


# ============================================================
# Fake Responses API - JSON
# ============================================================


def test_generate_reading_real_chart_json(
    real_reading_context,
):
    """
    実命式からStructured Outputs形式の
    JSON鑑定を生成できる。
    """

    client = FakeClient(
        response_type="json"
    )

    result = generate_reading(
        real_reading_context,
        client=client,
        model=TEST_MODEL,
        sections=[
            "core_personality",
            "career",
            "advice",
        ],
        output_format="json",
        store=False,
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
        result.status
        == "completed"
    )

    assert isinstance(
        result.parsed,
        dict,
    )

    assert (
        "summary"
        in result.parsed
    )

    assert (
        "sections"
        in result.parsed
    )

    assert (
        "disclaimer"
        in result.parsed
    )

    assert set(
        result.parsed[
            "sections"
        ].keys()
    ) == {
        "core_personality",
        "career",
        "advice",
    }


def test_generate_reading_json_real_chart(
    real_reading_context,
):
    """
    generate_reading_json() convenience API。
    """

    client = FakeClient(
        response_type="json"
    )

    result = generate_reading_json(
        real_reading_context,
        client=client,
        model=TEST_MODEL,
        sections=[
            "career",
            "advice",
        ],
    )

    assert isinstance(
        result,
        dict,
    )

    assert set(
        result[
            "sections"
        ].keys()
    ) == {
        "career",
        "advice",
    }


def test_json_generation_uses_strict_schema(
    real_reading_context,
):
    """
    JSON生成時にResponses APIへ
    strict JSON Schemaが渡される。
    """

    client = FakeClient(
        response_type="json"
    )

    generate_reading(
        real_reading_context,
        client=client,
        model=TEST_MODEL,
        sections=[
            "core_personality",
            "career",
        ],
        output_format="json",
    )

    call = (
        client.responses.calls[
            0
        ]
    )

    text_config = (
        call[
            "text"
        ]
    )

    assert (
        text_config[
            "format"
        ][
            "type"
        ]
        == "json_schema"
    )

    assert (
        text_config[
            "format"
        ][
            "strict"
        ]
        is True
    )

    schema = (
        text_config[
            "format"
        ][
            "schema"
        ]
    )

    assert (
        schema[
            "additionalProperties"
        ]
        is False
    )


# ============================================================
# Service layer aliases
# ============================================================


def test_generate_reading_from_context_real_chart(
    real_reading_context,
):
    """
    API/service layer向けdict API。
    """

    client = FakeClient(
        response_type="text"
    )

    result = generate_reading_from_context(
        real_reading_context,
        client=client,
        model=TEST_MODEL,
        sections=[
            "career",
            "advice",
        ],
        output_format="text",
    )

    assert isinstance(
        result,
        dict,
    )

    assert (
        result[
            "output_format"
        ]
        == "text"
    )

    assert (
        result[
            "model"
        ]
        == TEST_MODEL
    )

    assert (
        result[
            "status"
        ]
        == "completed"
    )

    assert result[
        "sections"
    ] == [
        "career",
        "advice",
    ]

    assert isinstance(
        result[
            "text"
        ],
        str,
    )

    assert (
        result[
            "text"
        ]
    )


def test_calculate_ai_reading_real_chart(
    real_reading_context,
):
    """
    calculate_ai_reading() aliasも
    実命式で正常動作する。
    """

    client = FakeClient(
        response_type="text"
    )

    result = calculate_ai_reading(
        real_reading_context,
        client=client,
        model=TEST_MODEL,
        sections=[
            "core_personality",
        ],
        output_format="text",
    )

    assert (
        result[
            "status"
        ]
        == "completed"
    )

    assert result[
        "sections"
    ] == [
        "core_personality"
    ]


# ============================================================
# Data integrity
# ============================================================


def test_generation_does_not_mutate_real_reading_context(
    real_reading_context,
):
    """
    AI生成処理がreading_contextを
    書き換えないことを確認。
    """

    before = json.dumps(
        real_reading_context,
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )

    client = FakeClient(
        response_type="text"
    )

    generate_reading(
        real_reading_context,
        client=client,
        model=TEST_MODEL,
        sections=[
            "core_personality",
            "career",
        ],
        output_format="text",
    )

    after = json.dumps(
        real_reading_context,
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )

    assert (
        after
        == before
    )


def test_generation_is_reproducible_with_fake_client(
    real_reading_context,
):
    """
    同一reading_contextとFake responseなら
    同じ生成結果になる。
    """

    first_client = FakeClient(
        response_type="text"
    )

    second_client = FakeClient(
        response_type="text"
    )

    first = generate_reading(
        real_reading_context,
        client=first_client,
        model=TEST_MODEL,
        sections=[
            "core_personality",
            "career",
        ],
        output_format="text",
    )

    second = generate_reading(
        real_reading_context,
        client=second_client,
        model=TEST_MODEL,
        sections=[
            "core_personality",
            "career",
        ],
        output_format="text",
    )

    assert (
        first.text
        == second.text
    )

    assert (
        first.sections
        == second.sections
    )

    assert (
        first.model
        == second.model
    )


def test_api_key_is_not_exposed_in_generation_result(
    real_reading_context,
):
    """
    AI生成結果にAPIキーが含まれないことを確認。
    """

    client = FakeClient(
        response_type="text"
    )

    result = generate_reading(
        real_reading_context,
        client=client,
        model=TEST_MODEL,
        sections=[
            "core_personality",
        ],
        output_format="text",
    )

    result_dict = (
        result.to_dict()
    )

    serialized = json.dumps(
        result_dict,
        ensure_ascii=False,
    )

    assert (
        "OPENAI_API_KEY"
        not in serialized
    )

    assert (
        "api_key"
        not in serialized.lower()
    )


# ============================================================
# Full real-chart -> AI pipeline
# ============================================================


def test_real_chart_to_ai_generation_end_to_end(
    verified_request,
):
    """
    最重要E2Eテスト。

    birth data
        ↓
    calculate_chart
        ↓
    reading_context
        ↓
    reading_prompt
        ↓
    Responses API payload
        ↓
    Fake OpenAI
        ↓
    ReadingGenerationResult

    を一気通貫で確認する。
    """

    chart_result = (
        calculate_chart(
            verified_request,
            target_datetime=(
                TARGET_DATETIME
            ),
        )
    )

    # ----------------------------------------
    # Natal chart verification
    #
    # calculate_chart() の正式構造:
    #
    # chart_result["chart"][position]["pillar"]
    # chart_result["day_master"]["stem"]
    # ----------------------------------------

    assert (
        chart_result[
            "chart"
        ][
            "year"
        ][
            "pillar"
        ]
        == "乙丑"
    )

    assert (
        chart_result[
            "chart"
        ][
            "month"
        ][
            "pillar"
        ]
        == "癸未"
    )

    assert (
        chart_result[
            "chart"
        ][
            "day"
        ][
            "pillar"
        ]
        == "丁巳"
    )

    assert (
        chart_result[
            "chart"
        ][
            "hour"
        ][
            "pillar"
        ]
        == "辛亥"
    )

    assert (
        chart_result[
            "day_master"
        ][
            "stem"
        ]
        == "丁"
    )

    # ----------------------------------------
    # Reading context
    # ----------------------------------------

    reading_context = (
        build_reading_context(
            chart_result
        )
    )

    assert (
        reading_context[
            "schema_version"
        ]
        == "reading_context_v1"
    )

    assert (
        reading_context[
            "natal_chart"
        ][
            "pillars"
        ][
            "day"
        ][
            "pillar"
        ]
        == "丁巳"
    )

    assert (
        reading_context[
            "day_master"
        ][
            "stem"
        ]
        == "丁"
    )

    assert (
        reading_context[
            "luck"
        ][
            "annual_luck"
        ][
            "ganzhi"
        ]
        == "丙午"
    )

    # ----------------------------------------
    # Fake OpenAI
    # ----------------------------------------

    client = FakeClient(
        response_type="text"
    )

    result = generate_reading(
        reading_context,
        client=client,
        model=TEST_MODEL,
        sections=[
            "core_personality",
            "career",
            "advice",
        ],
        output_format="text",
        max_output_tokens=4000,
        reasoning_effort="low",
        store=False,
    )

    # ----------------------------------------
    # Generation result
    # ----------------------------------------

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
        == "completed"
    )

    assert (
        result.model
        == TEST_MODEL
    )

    assert result.sections == (
        "core_personality",
        "career",
        "advice",
    )

    assert isinstance(
        result.text,
        str,
    )

    assert result.text

    # ----------------------------------------
    # Responses API call
    # ----------------------------------------

    assert (
        len(
            client.responses.calls
        )
        == 1
    )

    call = (
        client.responses.calls[
            0
        ]
    )

    assert (
        call[
            "model"
        ]
        == TEST_MODEL
    )

    assert (
        call[
            "store"
        ]
        is False
    )

    assert (
        call[
            "max_output_tokens"
        ]
        == 4000
    )

    assert (
        call[
            "reasoning"
        ][
            "effort"
        ]
        == "low"
    )

    # ----------------------------------------
    # Most important:
    # verified chart facts reached AI prompt
    # ----------------------------------------

    user_content = (
        call[
            "input"
        ][
            0
        ][
            "content"
        ]
    )

    assert (
        "乙丑"
        in user_content
    )

    assert (
        "癸未"
        in user_content
    )

    assert (
        "丁巳"
        in user_content
    )

    assert (
        "辛亥"
        in user_content
    )

    assert (
        "丁"
        in user_content
    )

    assert (
        "丙午"
        in user_content
    )


# ============================================================
# Final regression summary
# ============================================================


def test_real_chart_generator_golden_summary(
    real_chart_result,
    real_reading_context,
):
    """
    calculate_chart -> reading_context の
    命式整合性をまとめて固定する。
    """

    actual = {
        "chart_year": (
            real_chart_result[
                "chart"
            ][
                "year"
            ][
                "pillar"
            ]
        ),
        "chart_month": (
            real_chart_result[
                "chart"
            ][
                "month"
            ][
                "pillar"
            ]
        ),
        "chart_day": (
            real_chart_result[
                "chart"
            ][
                "day"
            ][
                "pillar"
            ]
        ),
        "chart_hour": (
            real_chart_result[
                "chart"
            ][
                "hour"
            ][
                "pillar"
            ]
        ),
        "chart_day_master": (
            real_chart_result[
                "day_master"
            ][
                "stem"
            ]
        ),
        "context_year": (
            real_reading_context[
                "natal_chart"
            ][
                "pillars"
            ][
                "year"
            ][
                "pillar"
            ]
        ),
        "context_month": (
            real_reading_context[
                "natal_chart"
            ][
                "pillars"
            ][
                "month"
            ][
                "pillar"
            ]
        ),
        "context_day": (
            real_reading_context[
                "natal_chart"
            ][
                "pillars"
            ][
                "day"
            ][
                "pillar"
            ]
        ),
        "context_hour": (
            real_reading_context[
                "natal_chart"
            ][
                "pillars"
            ][
                "hour"
            ][
                "pillar"
            ]
        ),
        "context_day_master": (
            real_reading_context[
                "day_master"
            ][
                "stem"
            ]
        ),
    }

    assert actual == {
        "chart_year": "乙丑",
        "chart_month": "癸未",
        "chart_day": "丁巳",
        "chart_hour": "辛亥",
        "chart_day_master": "丁",
        "context_year": "乙丑",
        "context_month": "癸未",
        "context_day": "丁巳",
        "context_hour": "辛亥",
        "context_day_master": "丁",
    }
