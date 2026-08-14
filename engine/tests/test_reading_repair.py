"""
tests/test_reading_repair.py

engine.reading_repair の単体テスト。

Reading Quality Auto-Repair v1 が、

・品質問題を正しくRepair入力へ変換する
・既存の鑑定JSON構造を維持する
・元データを破壊しない
・不正なAI応答を拒否する
・API失敗を適切な例外へ変換する
・品質問題がない場合はRepairしない

ことを確認する。
"""

from __future__ import annotations

import json

from copy import deepcopy

import pytest


from engine.reading_quality import (
    QualityIssue,
    ReadingQualityReport,
)

from engine.reading_repair import (
    DEFAULT_MAX_OUTPUT_TOKENS,
    DEFAULT_REASONING_EFFORT,
    DEFAULT_STORE,
    READING_REPAIR_METHOD,
    READING_REPAIR_STATUS,
    READING_REPAIR_VERSION,
    ReadingRepairConfigurationError,
    ReadingRepairRequestError,
    ReadingRepairResponseError,
    ReadingRepairResult,
    ReadingRepairValidationError,
    build_protected_facts,
    build_repair_input,
    build_repair_instructions,
    build_repair_payload,
    get_issue_codes,
    get_reading_repair_metadata,
    repair_reading,
    repair_reading_json,
    serialize_quality_issue,
    serialize_quality_report,
    validate_same_json_structure,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def sample_ai_reading():
    """
    Repair対象となる最小限の鑑定JSON。

    reading_generator側の契約を意識して、
    8セクションとdisclaimerを持たせる。
    """

    return {
        "sections": {
            "core_personality": {
                "summary": (
                    "丁の性質を持ち、"
                    "周囲を見ながら判断する傾向があります。"
                ),
                "detail": (
                    "自分の考えを持ちながら、"
                    "状況に応じて柔軟に動けます。"
                ),
                "advice": (
                    "自分の判断軸を大切にしてください。"
                ),
            },
            "career": {
                "summary": (
                    "仕事では調整力を活かしやすい傾向です。"
                ),
                "detail": (
                    "水を情報、土を安定として活かすことで、"
                    "仕事を整えやすくなります。"
                ),
                "advice": (
                    "情報を整理し、"
                    "再現性のある仕事の進め方を作りましょう。"
                ),
            },
            "wealth": {
                "summary": (
                    "金銭面では計画性を意識するとよいでしょう。"
                ),
                "detail": (
                    "水を情報、土を安定として捉え、"
                    "収支を確認することが大切です。"
                ),
                "advice": (
                    "再現性のある管理方法を作りましょう。"
                ),
            },
            "relationships": {
                "summary": (
                    "人間関係では丁寧な対話が役立ちます。"
                ),
                "detail": (
                    "相手との距離を見ながら"
                    "関係を築く傾向があります。"
                ),
                "advice": (
                    "結論を急がず、"
                    "相手の考えも確認してください。"
                ),
            },
            "health": {
                "summary": (
                    "健康面は一般的な生活管理を"
                    "大切にしてください。"
                ),
                "detail": (
                    "生活環境を整える姿勢が"
                    "全体の安定につながります。"
                ),
                "advice": (
                    "無理を続けず、"
                    "生活リズムを整えてください。"
                ),
            },
            "current_luck": {
                "summary": (
                    "現在は環境を見直しやすい時期です。"
                ),
                "detail": (
                    "火を勢いとして活かしながら、"
                    "水の情報も確認するとよいでしょう。"
                ),
                "advice": (
                    "急いで決めず、"
                    "必要な情報を確認してください。"
                ),
            },
            "future_flow": {
                "summary": (
                    "今後は選択肢が広がりやすい流れです。"
                ),
                "detail": (
                    "火の勢いを活かしながら、"
                    "段階的に方向を定めるとよいでしょう。"
                ),
                "advice": (
                    "準備を進めながら"
                    "次の機会を見極めてください。"
                ),
            },
            "advice": {
                "summary": (
                    "現職を続けるか転職するかを"
                    "二択だけで考える必要はありません。"
                ),
                "detail": (
                    "現職で役割を調整する方法と、"
                    "転職準備を並行する方法があります。"
                ),
                "advice": (
                    "まず判断条件を整理し、"
                    "小さく行動してください。"
                ),
            },
        },
        "disclaimer": (
            "本鑑定は四柱推命に基づく参考情報です。"
            "医学的診断、法律上の助言、"
            "投資・金融上の専門的助言ではありません。"
            "重要な判断では必要に応じて"
            "専門家や現実の情報も確認してください。"
        ),
    }


@pytest.fixture
def repaired_ai_reading(
    sample_ai_reading,
):
    """
    品質問題を修正した想定JSON。
    """

    result = deepcopy(
        sample_ai_reading
    )

    result[
        "sections"
    ][
        "career"
    ][
        "detail"
    ] = (
        "仕事では、必要な条件を整理し、"
        "関係者との認識を合わせながら"
        "進める力を活かしやすいでしょう。"
    )

    result[
        "sections"
    ][
        "career"
    ][
        "advice"
    ] = (
        "今の職場で役割を変えられる余地を"
        "具体的に確認してみてください。"
    )

    result[
        "sections"
    ][
        "wealth"
    ][
        "detail"
    ] = (
        "金銭面では、収入と固定費を分けて確認し、"
        "長期的に無理のない状態を"
        "維持することが重要です。"
    )

    result[
        "sections"
    ][
        "wealth"
    ][
        "advice"
    ] = (
        "転職を検討する場合も、"
        "必要生活費と収入条件を"
        "先に確認しておきましょう。"
    )

    result[
        "sections"
    ][
        "health"
    ][
        "detail"
    ] = (
        "健康面では占術から身体状態を断定せず、"
        "日々の生活全体を無理なく"
        "整える視点を大切にしてください。"
    )

    result[
        "sections"
    ][
        "current_luck"
    ][
        "detail"
    ] = (
        "現在は、すぐに結論を出すよりも、"
        "目の前の状況を比較しながら"
        "方向を定めやすい時期です。"
    )

    result[
        "sections"
    ][
        "future_flow"
    ][
        "detail"
    ] = (
        "今後は選択肢を広げながら、"
        "自分に合う働き方を"
        "段階的に絞り込む流れを意識してください。"
    )

    return result


@pytest.fixture
def sample_reading_context():
    """
    Repair時に固定事実として渡す
    reading_context。
    """

    return {
        "chart": {
            "year": {
                "stem": "乙",
                "branch": "丑",
            },
            "month": {
                "stem": "癸",
                "branch": "未",
            },
            "day": {
                "stem": "丁",
                "branch": "巳",
            },
            "hour": None,
        },
        "day_master": {
            "stem": "丁",
            "element": "火",
        },
        "final_strength_judgment": {
            "label": "身弱寄り",
        },
        "pattern_judgment": {
            "pattern": "食神格",
        },
        "useful_gods": {
            "primary": "木",
        },
        "luck_pillars": {
            "status": "estimated",
        },
        "current_luck": {
            "status": "available",
        },
        "annual_luck": {
            "status": "available",
        },
        "integrated_luck": {
            "status": "available",
        },
        "birth_time_status": {
            "known": False,
        },
        "unrelated_internal_value": {
            "should_not_be_protected": True,
        },
    }


@pytest.fixture
def sample_consultation_context():
    return {
        "primary_focus": "career",
        "current_concern": (
            "今の仕事を続けるべきか、"
            "転職した方がよいのか悩んでいます。"
        ),
        "ideal_future": (
            "自分に合った仕事を見つけ、"
            "安定した収入を得ながら"
            "長く働きたいです。"
        ),
    }


@pytest.fixture
def sample_quality_report():
    """
    今回のLIVE生成に近い問題を持つ
    Quality Report。
    """

    issues = (
        QualityIssue(
            code=(
                "health_astrology_specific_overreach"
            ),
            path="sections.health.detail",
            message=(
                "健康章で、命式・五行などから"
                "具体的な身体状態または生活習慣を"
                "直接推測しています。"
            ),
            value=(
                "生活環境を整える姿勢が"
                "全体の安定につながります。"
            ),
            matched="姿勢",
        ),
        QualityIssue(
            code=(
                "cross_section_advice_repetition"
            ),
            path="sections",
            message=(
                "同じ助言概念が多くの"
                "セクションで繰り返されています。"
            ),
            value="再現性",
            matched="再現性",
        ),
        QualityIssue(
            code=(
                "fixed_element_translation_overuse"
            ),
            path="sections",
            message=(
                "同じ五行が同じ現代語へ"
                "固定的に変換されています。"
            ),
            value="水→情報",
            matched="水→情報",
        ),
    )

    return ReadingQualityReport(
        valid=False,
        issues=issues,
    )


@pytest.fixture
def empty_quality_report():
    return ReadingQualityReport(
        valid=True,
        issues=(),
    )


# ============================================================
# Fake OpenAI objects
# ============================================================


class FakeUsage:

    def model_dump(self):
        return {
            "input_tokens": 100,
            "output_tokens": 200,
            "total_tokens": 300,
        }


class FakeResponse:

    def __init__(
        self,
        output_text,
        *,
        response_id=(
            "resp_repair_test_001"
        ),
        status="completed",
        usage=None,
    ):
        self.output_text = output_text
        self.id = response_id
        self.status = status
        self.usage = (
            usage
            if usage is not None
            else FakeUsage()
        )


class FakeResponses:

    def __init__(
        self,
        response,
    ):
        self.response = response
        self.calls = []

    def create(
        self,
        **kwargs,
    ):
        self.calls.append(
            deepcopy(kwargs)
        )
        return self.response


class FakeClient:

    def __init__(
        self,
        response,
    ):
        self.responses = FakeResponses(
            response
        )


class RaisingResponses:

    def create(
        self,
        **kwargs,
    ):
        raise RuntimeError(
            "fake API failure"
        )


class RaisingClient:

    def __init__(self):
        self.responses = (
            RaisingResponses()
        )


# ============================================================
# Constants / metadata
# ============================================================


def test_repair_constants():

    assert (
        READING_REPAIR_VERSION
        == "reading_repair_v1"
    )

    assert (
        READING_REPAIR_METHOD
        == (
            "openai_quality_issue_"
            "targeted_repair_v1"
        )
    )

    assert (
        READING_REPAIR_STATUS
        == "experimental"
    )

    assert (
        DEFAULT_MAX_OUTPUT_TOKENS
        == 8000
    )

    assert (
        DEFAULT_REASONING_EFFORT
        == "minimal"
    )

    assert DEFAULT_STORE is False


def test_get_reading_repair_metadata():

    metadata = (
        get_reading_repair_metadata()
    )

    assert (
        metadata["version"]
        == READING_REPAIR_VERSION
    )

    assert (
        metadata["method"]
        == READING_REPAIR_METHOD
    )

    assert (
        metadata["status"]
        == READING_REPAIR_STATUS
    )

    assert (
        metadata[
            "recalculates_astrology"
        ]
        is False
    )

    assert (
        metadata[
            "changes_reading_context"
        ]
        is False
    )

    assert (
        metadata[
            "changes_consultation_context"
        ]
        is False
    )

    assert (
        metadata[
            "max_repair_attempts"
        ]
        == "caller_controlled"
    )


# ============================================================
# Issue serialization
# ============================================================


def test_serialize_quality_issue(
    sample_quality_report,
):

    issue = (
        sample_quality_report.issues[0]
    )

    result = (
        serialize_quality_issue(
            issue
        )
    )

    assert result["code"] == (
        "health_astrology_specific_overreach"
    )

    assert result["path"] == (
        "sections.health.detail"
    )

    assert result["matched"] == "姿勢"

    assert result["severity"] in {
        "error",
        "warning",
    }


def test_serialize_quality_issue_rejects_bad_type():

    with pytest.raises(
        TypeError
    ):
        serialize_quality_issue(
            {
                "code": "dummy",
            }
        )


def test_serialize_quality_report(
    sample_quality_report,
):

    result = (
        serialize_quality_report(
            sample_quality_report
        )
    )

    assert result["valid"] is False

    assert (
        result["issue_count"]
        == 3
    )

    assert len(
        result["issues"]
    ) == 3

    assert (
        result["issues"][0]["code"]
        == (
            "health_astrology_"
            "specific_overreach"
        )
    )


def test_serialize_quality_report_does_not_include_value(
    sample_quality_report,
):

    result = (
        serialize_quality_report(
            sample_quality_report
        )
    )

    for issue in result["issues"]:
        assert "value" not in issue


def test_get_issue_codes_preserves_order(
    sample_quality_report,
):

    result = get_issue_codes(
        sample_quality_report
    )

    assert result == (
        "health_astrology_specific_overreach",
        "cross_section_advice_repetition",
        "fixed_element_translation_overuse",
    )


# ============================================================
# Instructions
# ============================================================


@pytest.mark.parametrize(
    "required_text",
    (
        "文章編集だけ",
        "命式",
        "再計算",
        "JSON構造",
        "健康章",
        "姿勢",
        "章間反復",
        "五行の固定翻訳",
        "水＝情報",
        "土＝安定",
        "火＝勢い",
        "current_luck",
        "future_flow",
        "advice",
    ),
)
def test_repair_instructions_contains_required_policy(
    required_text,
):

    instructions = (
        build_repair_instructions()
    )

    assert required_text in instructions


# ============================================================
# Protected facts
# ============================================================


def test_build_protected_facts(
    sample_reading_context,
):

    result = build_protected_facts(
        sample_reading_context
    )

    assert result["chart"] == (
        sample_reading_context["chart"]
    )

    assert result["day_master"] == (
        sample_reading_context[
            "day_master"
        ]
    )

    assert (
        "final_strength_judgment"
        in result
    )

    assert "pattern_judgment" in result

    assert "useful_gods" in result

    assert "luck_pillars" in result

    assert "current_luck" in result

    assert "annual_luck" in result

    assert "integrated_luck" in result

    assert "birth_time_status" in result

    assert (
        "unrelated_internal_value"
        not in result
    )


def test_build_protected_facts_returns_copy(
    sample_reading_context,
):

    result = build_protected_facts(
        sample_reading_context
    )

    result["chart"]["year"]["stem"] = (
        "甲"
    )

    assert (
        sample_reading_context[
            "chart"
        ][
            "year"
        ][
            "stem"
        ]
        == "乙"
    )


# ============================================================
# Repair input
# ============================================================


def test_build_repair_input(
    sample_ai_reading,
    sample_quality_report,
    sample_reading_context,
    sample_consultation_context,
):

    text = build_repair_input(
        ai_reading=sample_ai_reading,
        quality_report=(
            sample_quality_report
        ),
        reading_context=(
            sample_reading_context
        ),
        consultation_context=(
            sample_consultation_context
        ),
    )

    payload = json.loads(
        text
    )

    assert payload["task"] == (
        "quality_issue_targeted_repair"
    )

    assert (
        payload[
            "quality_report"
        ][
            "issue_count"
        ]
        == 3
    )

    assert (
        payload[
            "original_ai_reading"
        ]
        == sample_ai_reading
    )

    assert (
        payload[
            "reading_context"
        ]
        == sample_reading_context
    )

    assert (
        payload[
            "consultation_context"
        ]
        == sample_consultation_context
    )


def test_build_repair_input_without_consultation(
    sample_ai_reading,
    sample_quality_report,
    sample_reading_context,
):

    text = build_repair_input(
        ai_reading=sample_ai_reading,
        quality_report=(
            sample_quality_report
        ),
        reading_context=(
            sample_reading_context
        ),
    )

    payload = json.loads(
        text
    )

    assert (
        payload[
            "consultation_context"
        ]
        is None
    )


# ============================================================
# Structural protection
# ============================================================


def test_validate_same_json_structure_accepts_text_changes(
    sample_ai_reading,
    repaired_ai_reading,
):

    validate_same_json_structure(
        sample_ai_reading,
        repaired_ai_reading,
    )


def test_validate_same_json_structure_rejects_missing_key(
    sample_ai_reading,
):

    repaired = deepcopy(
        sample_ai_reading
    )

    del repaired[
        "sections"
    ][
        "career"
    ][
        "advice"
    ]

    with pytest.raises(
        ReadingRepairValidationError
    ):
        validate_same_json_structure(
            sample_ai_reading,
            repaired,
        )


def test_validate_same_json_structure_rejects_added_key(
    sample_ai_reading,
):

    repaired = deepcopy(
        sample_ai_reading
    )

    repaired[
        "sections"
    ][
        "career"
    ][
        "new_field"
    ] = "追加"

    with pytest.raises(
        ReadingRepairValidationError
    ):
        validate_same_json_structure(
            sample_ai_reading,
            repaired,
        )


def test_validate_same_json_structure_rejects_changed_scalar_type(
    sample_ai_reading,
):

    repaired = deepcopy(
        sample_ai_reading
    )

    repaired[
        "sections"
    ][
        "career"
    ][
        "summary"
    ] = [
        "文字列ではなく配列"
    ]

    with pytest.raises(
        ReadingRepairValidationError
    ):
        validate_same_json_structure(
            sample_ai_reading,
            repaired,
        )


# ============================================================
# Payload
# ============================================================


def test_build_repair_payload(
    sample_ai_reading,
    sample_quality_report,
    sample_reading_context,
    sample_consultation_context,
):

    payload = build_repair_payload(
        ai_reading=sample_ai_reading,
        quality_report=(
            sample_quality_report
        ),
        reading_context=(
            sample_reading_context
        ),
        consultation_context=(
            sample_consultation_context
        ),
        model="gpt-5",
    )

    assert payload["model"] == "gpt-5"

    assert (
        payload["max_output_tokens"]
        == 8000
    )

    assert payload["reasoning"] == {
        "effort": "minimal",
    }

    assert payload["store"] is False

    assert isinstance(
        payload["instructions"],
        str,
    )

    assert isinstance(
        payload["input"],
        str,
    )

    assert (
        "変更禁止の計算済み事実"
        in payload["input"]
    )

    assert "乙" in payload["input"]

    assert "丁" in payload["input"]


@pytest.mark.parametrize(
    "value",
    (
        0,
        -1,
    ),
)
def test_build_repair_payload_rejects_bad_max_tokens(
    sample_ai_reading,
    sample_quality_report,
    sample_reading_context,
    value,
):

    with pytest.raises(
        ValueError
    ):
        build_repair_payload(
            ai_reading=sample_ai_reading,
            quality_report=(
                sample_quality_report
            ),
            reading_context=(
                sample_reading_context
            ),
            model="gpt-5",
            max_output_tokens=value,
        )


def test_build_repair_payload_rejects_non_int_max_tokens(
    sample_ai_reading,
    sample_quality_report,
    sample_reading_context,
):

    with pytest.raises(
        TypeError
    ):
        build_repair_payload(
            ai_reading=sample_ai_reading,
            quality_report=(
                sample_quality_report
            ),
            reading_context=(
                sample_reading_context
            ),
            model="gpt-5",
            max_output_tokens="8000",
        )


# ============================================================
# Repair main
# ============================================================


def test_repair_reading_success(
    sample_ai_reading,
    repaired_ai_reading,
    sample_quality_report,
    sample_reading_context,
    sample_consultation_context,
):

    response = FakeResponse(
        json.dumps(
            repaired_ai_reading,
            ensure_ascii=False,
        )
    )

    client = FakeClient(
        response
    )

    original_copy = deepcopy(
        sample_ai_reading
    )

    result = repair_reading(
        sample_ai_reading,
        sample_quality_report,
        reading_context=(
            sample_reading_context
        ),
        consultation_context=(
            sample_consultation_context
        ),
        client=client,
        model="gpt-5",
    )

    assert isinstance(
        result,
        ReadingRepairResult,
    )

    assert (
        result.repaired
        == repaired_ai_reading
    )

    assert (
        result.original
        == original_copy
    )

    assert result.changed is True

    assert result.issue_count == 3

    assert result.response_id == (
        "resp_repair_test_001"
    )

    assert (
        result.response_status
        == "completed"
    )

    assert result.model == "gpt-5"

    assert result.usage == {
        "input_tokens": 100,
        "output_tokens": 200,
        "total_tokens": 300,
    }

    assert (
        sample_ai_reading
        == original_copy
    )

    assert len(
        client.responses.calls
    ) == 1


def test_repair_reading_result_to_dict(
    sample_ai_reading,
    repaired_ai_reading,
    sample_quality_report,
    sample_reading_context,
):

    response = FakeResponse(
        json.dumps(
            repaired_ai_reading,
            ensure_ascii=False,
        )
    )

    result = repair_reading(
        sample_ai_reading,
        sample_quality_report,
        reading_context=(
            sample_reading_context
        ),
        client=FakeClient(
            response
        ),
        model="gpt-5",
    )

    data = result.to_dict()

    assert data["version"] == (
        "reading_repair_v1"
    )

    assert data["changed"] is True

    assert data["issue_count"] == 3

    assert (
        "health_astrology_specific_overreach"
        in data[
            "repaired_issue_codes"
        ]
    )


def test_repair_reading_json_returns_dict(
    sample_ai_reading,
    repaired_ai_reading,
    sample_quality_report,
    sample_reading_context,
):

    response = FakeResponse(
        json.dumps(
            repaired_ai_reading,
            ensure_ascii=False,
        )
    )

    result = repair_reading_json(
        sample_ai_reading,
        sample_quality_report,
        reading_context=(
            sample_reading_context
        ),
        client=FakeClient(
            response
        ),
        model="gpt-5",
    )

    assert isinstance(
        result,
        dict,
    )

    assert (
        result
        == repaired_ai_reading
    )


# ============================================================
# No issue
# ============================================================


def test_repair_reading_rejects_zero_issues(
    sample_ai_reading,
    empty_quality_report,
    sample_reading_context,
):

    with pytest.raises(
        ReadingRepairConfigurationError
    ):
        repair_reading(
            sample_ai_reading,
            empty_quality_report,
            reading_context=(
                sample_reading_context
            ),
            client=FakeClient(
                FakeResponse("{}")
            ),
            model="gpt-5",
        )


def test_zero_issues_does_not_call_api(
    sample_ai_reading,
    empty_quality_report,
    sample_reading_context,
):

    client = FakeClient(
        FakeResponse("{}")
    )

    with pytest.raises(
        ReadingRepairConfigurationError
    ):
        repair_reading(
            sample_ai_reading,
            empty_quality_report,
            reading_context=(
                sample_reading_context
            ),
            client=client,
            model="gpt-5",
        )

    assert (
        client.responses.calls
        == []
    )


# ============================================================
# API failure
# ============================================================


def test_repair_reading_wraps_api_failure(
    sample_ai_reading,
    sample_quality_report,
    sample_reading_context,
):

    with pytest.raises(
        ReadingRepairRequestError
    ) as exc_info:
        repair_reading(
            sample_ai_reading,
            sample_quality_report,
            reading_context=(
                sample_reading_context
            ),
            client=RaisingClient(),
            model="gpt-5",
        )

    assert (
        "fake API failure"
        in str(
            exc_info.value
        )
    )


# ============================================================
# Bad response status
# ============================================================


@pytest.mark.parametrize(
    "status",
    (
        "failed",
        "incomplete",
        "cancelled",
    ),
)
def test_repair_reading_rejects_bad_response_status(
    sample_ai_reading,
    repaired_ai_reading,
    sample_quality_report,
    sample_reading_context,
    status,
):

    response = FakeResponse(
        json.dumps(
            repaired_ai_reading,
            ensure_ascii=False,
        ),
        status=status,
    )

    with pytest.raises(
        ReadingRepairResponseError
    ):
        repair_reading(
            sample_ai_reading,
            sample_quality_report,
            reading_context=(
                sample_reading_context
            ),
            client=FakeClient(
                response
            ),
            model="gpt-5",
        )


# ============================================================
# Invalid JSON
# ============================================================


@pytest.mark.parametrize(
    "bad_output",
    (
        "",
        "これはJSONではありません",
        "{",
        "[1, 2, 3]",
    ),
)
def test_repair_reading_rejects_invalid_json(
    sample_ai_reading,
    sample_quality_report,
    sample_reading_context,
    bad_output,
):

    response = FakeResponse(
        bad_output
    )

    with pytest.raises(
        (
            ReadingRepairResponseError,
            ReadingRepairValidationError,
        )
    ):
        repair_reading(
            sample_ai_reading,
            sample_quality_report,
            reading_context=(
                sample_reading_context
            ),
            client=FakeClient(
                response
            ),
            model="gpt-5",
        )


# ============================================================
# Structure mutation
# ============================================================


def test_repair_reading_rejects_structure_mutation(
    sample_ai_reading,
    repaired_ai_reading,
    sample_quality_report,
    sample_reading_context,
):

    bad_repair = deepcopy(
        repaired_ai_reading
    )

    bad_repair[
        "sections"
    ][
        "career"
    ][
        "extra"
    ] = "勝手に追加"

    response = FakeResponse(
        json.dumps(
            bad_repair,
            ensure_ascii=False,
        )
    )

    with pytest.raises(
        ReadingRepairValidationError
    ):
        repair_reading(
            sample_ai_reading,
            sample_quality_report,
            reading_context=(
                sample_reading_context
            ),
            client=FakeClient(
                response
            ),
            model="gpt-5",
        )


# ============================================================
# Original immutability
# ============================================================


def test_repair_does_not_mutate_original_reading(
    sample_ai_reading,
    repaired_ai_reading,
    sample_quality_report,
    sample_reading_context,
):

    original = deepcopy(
        sample_ai_reading
    )

    response = FakeResponse(
        json.dumps(
            repaired_ai_reading,
            ensure_ascii=False,
        )
    )

    repair_reading(
        sample_ai_reading,
        sample_quality_report,
        reading_context=(
            sample_reading_context
        ),
        client=FakeClient(
            response
        ),
        model="gpt-5",
    )

    assert (
        sample_ai_reading
        == original
    )


def test_repair_result_original_is_independent_copy(
    sample_ai_reading,
    repaired_ai_reading,
    sample_quality_report,
    sample_reading_context,
):

    response = FakeResponse(
        json.dumps(
            repaired_ai_reading,
            ensure_ascii=False,
        )
    )

    result = repair_reading(
        sample_ai_reading,
        sample_quality_report,
        reading_context=(
            sample_reading_context
        ),
        client=FakeClient(
            response
        ),
        model="gpt-5",
    )

    sample_ai_reading[
        "sections"
    ][
        "career"
    ][
        "summary"
    ] = "外部で変更"

    assert (
        result.original[
            "sections"
        ][
            "career"
        ][
            "summary"
        ]
        != "外部で変更"
    )


# ============================================================
# API call configuration
# ============================================================


def test_repair_passes_expected_configuration_to_api(
    sample_ai_reading,
    repaired_ai_reading,
    sample_quality_report,
    sample_reading_context,
):

    response = FakeResponse(
        json.dumps(
            repaired_ai_reading,
            ensure_ascii=False,
        )
    )

    client = FakeClient(
        response
    )

    repair_reading(
        sample_ai_reading,
        sample_quality_report,
        reading_context=(
            sample_reading_context
        ),
        client=client,
        model="gpt-5",
        max_output_tokens=7000,
        reasoning_effort="minimal",
        store=False,
    )

    assert len(
        client.responses.calls
    ) == 1

    call = (
        client.responses.calls[0]
    )

    assert call["model"] == "gpt-5"

    assert (
        call["max_output_tokens"]
        == 7000
    )

    assert call["reasoning"] == {
        "effort": "minimal",
    }

    assert call["store"] is False

    assert isinstance(
        call["instructions"],
        str,
    )

    assert isinstance(
        call["input"],
        str,
    )


# ============================================================
# Frozen result
# ============================================================


def test_repair_result_is_frozen(
    sample_ai_reading,
    repaired_ai_reading,
    sample_quality_report,
    sample_reading_context,
):

    response = FakeResponse(
        json.dumps(
            repaired_ai_reading,
            ensure_ascii=False,
        )
    )

    result = repair_reading(
        sample_ai_reading,
        sample_quality_report,
        reading_context=(
            sample_reading_context
        ),
        client=FakeClient(
            response
        ),
        model="gpt-5",
    )

    with pytest.raises(
        Exception
    ):
        result.status = "changed"
