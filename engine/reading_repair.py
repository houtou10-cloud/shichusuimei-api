"""
engine/reading_repair.py

四柱推命鑑定書
Reading Quality Auto-Repair v1

AIが生成した顧客向け鑑定文章について、
reading_quality が検出した問題をもとに
OpenAI Responses APIで文章のみを修正する。

重要な設計原則
--------------
・命式を再計算しない
・reading_contextを書き換えない
・consultation_contextを書き換えない
・占術上の事実を創作しない
・JSON構造を変更しない
・品質問題に関係する文章だけを修正する
・元の鑑定内容を可能な限り維持する
・修復回数は呼び出し側で制限する
"""

from __future__ import annotations

import json

from copy import deepcopy
from dataclasses import dataclass
from typing import (
    Any,
    Dict,
    Mapping,
    Optional,
    Sequence,
)


from engine.reading_generator import (
    ReadingGeneratorJSONError,
    ReadingGeneratorRequestError,
    ReadingGeneratorResponseError,
    create_openai_client,
    get_default_model,
    parse_reading_json,
    validate_generated_reading_json,
)

from engine.reading_quality import (
    QualityIssue,
    ReadingQualityReport,
    issue_severity,
)


# ============================================================
# Metadata
# ============================================================


READING_REPAIR_VERSION = (
    "reading_repair_v1"
)

READING_REPAIR_METHOD = (
    "openai_quality_issue_targeted_repair_v1"
)

READING_REPAIR_STATUS = (
    "experimental"
)


DEFAULT_MAX_OUTPUT_TOKENS = 8000

DEFAULT_REASONING_EFFORT = "minimal"

DEFAULT_STORE = False


# ============================================================
# Exceptions
# ============================================================


class ReadingRepairError(RuntimeError):
    """
    Reading Repair共通例外。
    """


class ReadingRepairConfigurationError(
    ReadingRepairError
):
    """
    Repair設定が不正な場合。
    """


class ReadingRepairRequestError(
    ReadingRepairError
):
    """
    OpenAI API呼び出しに失敗した場合。
    """


class ReadingRepairResponseError(
    ReadingRepairError
):
    """
    OpenAI responseが利用できない場合。
    """


class ReadingRepairValidationError(
    ReadingRepairError
):
    """
    修復後JSONが契約を満たさない場合。
    """


# ============================================================
# Result
# ============================================================


@dataclass(frozen=True)
class ReadingRepairResult:
    """
    1回のAuto-Repair結果。
    """

    original: Dict[str, Any]

    repaired: Dict[str, Any]

    issue_count: int

    error_count: int

    warning_count: int

    repaired_issue_codes: tuple[str, ...]

    response_id: Optional[str]

    response_status: Optional[str]

    usage: Any

    model: str

    method: str = READING_REPAIR_METHOD

    status: str = "completed"

    version: str = READING_REPAIR_VERSION

    @property
    def changed(self) -> bool:
        return (
            self.original
            != self.repaired
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "method": self.method,
            "status": self.status,
            "changed": self.changed,
            "issue_count": (
                self.issue_count
            ),
            "error_count": (
                self.error_count
            ),
            "warning_count": (
                self.warning_count
            ),
            "repaired_issue_codes": list(
                self.repaired_issue_codes
            ),
            "response_id": (
                self.response_id
            ),
            "response_status": (
                self.response_status
            ),
            "usage": deepcopy(
                self.usage
            ),
            "model": self.model,
        }


# ============================================================
# Generic validation
# ============================================================


def _require_mapping(
    value: Any,
    name: str,
) -> Mapping[str, Any]:

    if not isinstance(
        value,
        Mapping,
    ):
        raise TypeError(
            f"{name}はdict型である必要があります。"
        )

    return value


def _require_non_empty_string(
    value: Any,
    name: str,
) -> str:

    if not isinstance(
        value,
        str,
    ):
        raise TypeError(
            f"{name}は文字列である必要があります。"
        )

    normalized = value.strip()

    if not normalized:
        raise ValueError(
            f"{name}が空です。"
        )

    return normalized


def _json_safe_copy(
    value: Any,
) -> Any:
    """
    JSON round-trip可能なdeepcopyを作る。
    """

    return json.loads(
        json.dumps(
            value,
            ensure_ascii=False,
            default=str,
        )
    )


# ============================================================
# Issue helpers
# ============================================================


def serialize_quality_issue(
    issue: QualityIssue,
) -> Dict[str, Any]:
    """
    QualityIssueをRepair用dictへ変換する。
    """

    if not isinstance(
        issue,
        QualityIssue,
    ):
        raise TypeError(
            "issueはQualityIssueである必要があります。"
        )

    return {
        "code": issue.code,
        "severity": issue_severity(
            issue
        ),
        "path": issue.path,
        "message": issue.message,
        "matched": issue.matched,
    }


def serialize_quality_report(
    report: ReadingQualityReport,
) -> Dict[str, Any]:
    """
    Repair APIへ渡すために
    Quality Reportを最小限へ変換する。

    元文章全文はissue.valueとして
    二重送信しない。
    """

    if not isinstance(
        report,
        ReadingQualityReport,
    ):
        raise TypeError(
            "reportはReadingQualityReport"
            "である必要があります。"
        )

    return {
        "valid": report.valid,
        "issue_count": (
            report.issue_count
        ),
        "error_count": (
            report.error_count
        ),
        "warning_count": (
            report.warning_count
        ),
        "issues": [
            serialize_quality_issue(
                issue
            )
            for issue in report.issues
        ],
    }


def get_issue_codes(
    report: ReadingQualityReport,
) -> tuple[str, ...]:
    """
    issue codeを重複なしで返す。
    元の検出順序を維持する。
    """

    if not isinstance(
        report,
        ReadingQualityReport,
    ):
        raise TypeError(
            "reportはReadingQualityReport"
            "である必要があります。"
        )

    result: list[str] = []

    for issue in report.issues:
        if issue.code not in result:
            result.append(
                issue.code
            )

    return tuple(result)


# ============================================================
# Repair policy
# ============================================================


def build_repair_instructions() -> str:
    """
    Repair専用system instructions。
    """

    return """
あなたは四柱推命鑑定書の文章品質修正担当です。

すでに完成している鑑定JSONについて、
品質検査で指摘された問題だけを修正してください。

あなたの仕事は占術計算ではありません。
文章編集だけを行ってください。


【絶対ルール】

1.
入力された命式・日主・五行・通変星・十二運・
身強身弱・格局・用神・大運・歳運などの
計算済み占術情報を変更しないでください。

2.
reading_contextの情報を再計算、
推測、補完、創作しないでください。

3.
相談者の悩みや理想の未来を
別の内容へ変更しないでください。

4.
元のJSON構造を変更しないでください。

5.
キーを追加しないでください。

6.
キーを削除しないでください。

7.
配列の構造を変更しないでください。

8.
品質検査で問題になっていない文章は、
必要がない限り変更しないでください。

9.
文章全体をゼロから書き直さないでください。

10.
品質問題を別表現へ置き換えただけで
同じ問題を再発させないでください。


【健康章】

命式・五行・通変星・格局・用神・運勢から、
具体的な病気、症状、臓器、体質、
睡眠状態、疲労状態、食欲、消化、
血流、冷え、身体的な姿勢などを
直接推測しないでください。

健康章では、
一般的な生活バランス、
無理をしすぎないこと、
生活リズムを整えることなど、
非診断的な一般論に限定してください。

「姿勢」という語を使う場合は、
身体的な姿勢と誤認される可能性があるため、
可能なら「取り組み方」「向き合い方」
などへ置き換えてください。


【章間反復】

同じ助言概念を複数章で
繰り返さないでください。

たとえば、

・学習
・情報収集
・準備
・可視化
・再現性
・仕組み化
・対話
・記録
・ルール化

などが多数章で反復している場合、
各章の役割に最も合う章だけへ残し、
他章では別の具体的観点へ変更してください。


【五行の固定翻訳】

同じ五行を、
毎回同じ現代語へ機械的に
翻訳しないでください。

たとえば、

水＝情報
土＝安定
火＝勢い
金＝ルール
木＝成長

という固定対応を
多数章で繰り返さないでください。

五行名を出す必要がなければ、
無理に出さなくて構いません。

五行を説明する場合も、
その章固有の文脈に合わせてください。


【各章の主担当】

core_personality:
生来の性格、意思決定、行動傾向。

career:
仕事の性質、役割、環境、
仕事相談への具体的回答。

wealth:
収支、蓄積、金銭判断、
リスク管理。

relationships:
対人距離、伝え方、
関係構築。

health:
一般的な生活バランス。
医学的推測は禁止。

current_luck:
現在の運勢と、
今の時期に意識すること。

future_flow:
今後の流れと変化。
current_luckの言い換えにしない。

【5年間の年運構造】

five_year_luck は計算済みの5年間の年運情報です。
future_flow 内の yearly は、この five_year_luck に基づく年別鑑定です。

yearly の構造を変更しないでください。
元の yearly が5件なら、修正後も必ず5件を維持してください。
各年の year、title、summary、detail、advice など、
既存のキーを追加・削除・変更しないでください。
年の順序を入れ替えないでください。
5年間の対象年を変更しないでください。
five_year_luck の計算済み内容を再計算、推測、補完しないでください。
文章品質の修正が必要な場合も、yearly の各年を独立した年運として維持してください。

advice:
最終判断、優先順位、
最初の具体的行動。


【安全性】

医療・法律・投資・金融などについて、
断定的な専門判断を行わないでください。

disclaimerに必要な安全上の注意がある場合、
削除しないでください。


【出力】

修正後のJSONだけを返してください。

説明文、
Markdown、
コードフェンス、
修正理由、
前置き、
後書きは不要です。
""".strip()


# ============================================================
# Repair input
# ============================================================


def build_repair_input(
    *,
    ai_reading: Mapping[str, Any],
    quality_report: ReadingQualityReport,
    reading_context: Mapping[
        str,
        Any,
    ],
    consultation_context: Mapping[
        str,
        Any,
    ] | None = None,
) -> str:
    """
    Repair APIへ渡すuser inputを生成する。
    """

    ai_reading = _require_mapping(
        ai_reading,
        "ai_reading",
    )

    reading_context = _require_mapping(
        reading_context,
        "reading_context",
    )

    if (
        consultation_context
        is not None
    ):
        consultation_context = (
            _require_mapping(
                consultation_context,
                "consultation_context",
            )
        )

    if not isinstance(
        quality_report,
        ReadingQualityReport,
    ):
        raise TypeError(
            "quality_reportは"
            "ReadingQualityReport"
            "である必要があります。"
        )

    payload = {
        "task": (
            "quality_issue_targeted_repair"
        ),
        "quality_report": (
            serialize_quality_report(
                quality_report
            )
        ),
        "original_ai_reading": (
            _json_safe_copy(
                ai_reading
            )
        ),
        "reading_context": (
            _json_safe_copy(
                reading_context
            )
        ),
        "consultation_context": (
            _json_safe_copy(
                consultation_context
            )
            if consultation_context
            is not None
            else None
        ),
    }

    return json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
    )


# ============================================================
# Structural protection
# ============================================================


def _structure_signature(
    value: Any,
) -> Any:
    """
    JSONの構造だけをsignature化する。

    dict:
        キー構造を保持。

    list:
        長さと各要素構造を保持。

    scalar:
        型名のみ保持。
    """

    if isinstance(
        value,
        Mapping,
    ):
        return {
            str(key): (
                _structure_signature(
                    child
                )
            )
            for key, child
            in value.items()
        }

    if isinstance(
        value,
        list,
    ):
        return [
            _structure_signature(
                item
            )
            for item in value
        ]

    if value is None:
        return "null"

    if isinstance(
        value,
        bool,
    ):
        return "bool"

    if isinstance(
        value,
        int,
    ):
        return "int"

    if isinstance(
        value,
        float,
    ):
        return "float"

    if isinstance(
        value,
        str,
    ):
        return "str"

    return type(value).__name__


def validate_same_json_structure(
    original: Mapping[str, Any],
    repaired: Mapping[str, Any],
) -> None:
    """
    Repair前後でJSON構造が同一か検証する。
    """

    original = _require_mapping(
        original,
        "original",
    )

    repaired = _require_mapping(
        repaired,
        "repaired",
    )

    original_signature = (
        _structure_signature(
            original
        )
    )

    repaired_signature = (
        _structure_signature(
            repaired
        )
    )

    if (
        original_signature
        != repaired_signature
    ):
        raise ReadingRepairValidationError(
            "Auto-Repairによって"
            "AI鑑定JSONの構造が変更されました。"
        )


# ============================================================
# Protected-value helpers
# ============================================================


PROTECTED_CONTEXT_KEYS = frozenset(
    {
        "chart",
        "day_master",
        "final_strength_judgment",
        "pattern_judgment",
        "useful_gods",
        "luck_pillars",
        "current_luck",
        "annual_luck",
        "five_year_luck",
        "integrated_luck",
        "birth_time_status",
    }
)


def build_protected_facts(
    reading_context: Mapping[
        str,
        Any,
    ],
) -> Dict[str, Any]:
    """
    AIへ「変更禁止の事実」として渡す
    reading_contextの主要領域を抽出する。

    Repair後JSONとの直接比較ではなく、
    Repairプロンプト上の固定事実として利用する。
    """

    reading_context = _require_mapping(
        reading_context,
        "reading_context",
    )

    protected: Dict[
        str,
        Any,
    ] = {}

    for key in PROTECTED_CONTEXT_KEYS:
        if key in reading_context:
            protected[key] = (
                _json_safe_copy(
                    reading_context[
                        key
                    ]
                )
            )

    return protected


# ============================================================
# OpenAI response helpers
# ============================================================


def _extract_response_text(
    response: Any,
) -> str:
    """
    Responses API responseから
    output_textを安全に取り出す。
    """

    if response is None:
        raise ReadingRepairResponseError(
            "OpenAI responseがありません。"
        )

    output_text = getattr(
        response,
        "output_text",
        None,
    )

    if isinstance(
        output_text,
        str,
    ):
        output_text = (
            output_text.strip()
        )

        if output_text:
            return output_text

    if isinstance(
        response,
        Mapping,
    ):
        output_text = response.get(
            "output_text"
        )

        if isinstance(
            output_text,
            str,
        ):
            output_text = (
                output_text.strip()
            )

            if output_text:
                return output_text

    raise ReadingRepairResponseError(
        "OpenAI responseから"
        "修復後JSON文章を取得できませんでした。"
    )


def _extract_response_metadata(
    response: Any,
) -> Dict[str, Any]:
    """
    Responses API response metadataを抽出する。
    """

    if isinstance(
        response,
        Mapping,
    ):
        response_id = response.get(
            "id"
        )
        response_status = response.get(
            "status"
        )
        usage = response.get(
            "usage"
        )

    else:
        response_id = getattr(
            response,
            "id",
            None,
        )
        response_status = getattr(
            response,
            "status",
            None,
        )
        usage = getattr(
            response,
            "usage",
            None,
        )

    if hasattr(
        usage,
        "model_dump",
    ):
        usage = usage.model_dump()

    elif hasattr(
        usage,
        "to_dict",
    ):
        usage = usage.to_dict()

    return {
        "response_id": (
            str(response_id)
            if response_id
            is not None
            else None
        ),
        "response_status": (
            str(response_status)
            if response_status
            is not None
            else None
        ),
        "usage": (
            _json_safe_copy(
                usage
            )
            if usage
            is not None
            else None
        ),
    }


def _validate_response_status(
    response: Any,
) -> None:
    """
    Responses APIのstatusを検証する。

    incomplete時は、
    incomplete_details.reason も
    エラーメッセージへ含める。
    """

    metadata = (
        _extract_response_metadata(
            response
        )
    )

    status = metadata[
        "response_status"
    ]

    if status in (
        None,
        "completed",
    ):
        return

    incomplete_details = None

    if isinstance(
        response,
        Mapping,
    ):
        incomplete_details = (
            response.get(
                "incomplete_details"
            )
        )

    else:
        incomplete_details = getattr(
            response,
            "incomplete_details",
            None,
        )

    if hasattr(
        incomplete_details,
        "model_dump",
    ):
        incomplete_details = (
            incomplete_details.model_dump()
        )

    elif hasattr(
        incomplete_details,
        "to_dict",
    ):
        incomplete_details = (
            incomplete_details.to_dict()
        )

    reason = None

    if isinstance(
        incomplete_details,
        Mapping,
    ):
        reason = (
            incomplete_details.get(
                "reason"
            )
        )

    elif incomplete_details is not None:
        reason = getattr(
            incomplete_details,
            "reason",
            None,
        )

    raise ReadingRepairResponseError(
        "Auto-RepairのOpenAI responseが"
        "completedではありません。 "
        f"status={status}, "
        f"incomplete_reason={reason}"
    )


# ============================================================
# OpenAI request
# ============================================================


def _execute_repair_request(
    client: Any,
    payload: Dict[str, Any],
) -> Any:
    """
    Responses APIを呼び出す。

    テストではfake clientを注入可能。
    """

    try:
        return client.responses.create(
            **payload
        )

    except Exception as exc:
        raise ReadingRepairRequestError(
            "OpenAI Responses APIによる"
            "鑑定文Auto-Repairに失敗しました。 "
            f"{type(exc).__name__}: {exc}"
        ) from exc


# ============================================================
# Payload
# ============================================================


def build_repair_payload(
    *,
    ai_reading: Mapping[str, Any],
    quality_report: ReadingQualityReport,
    reading_context: Mapping[
        str,
        Any,
    ],
    consultation_context: Mapping[
        str,
        Any,
    ] | None = None,
    model: str | None = None,
    max_output_tokens: int = (
        DEFAULT_MAX_OUTPUT_TOKENS
    ),
    reasoning_effort: str = (
        DEFAULT_REASONING_EFFORT
    ),
    store: bool = DEFAULT_STORE,
) -> Dict[str, Any]:
    """
    Responses API用payloadを生成する。
    """

    if model is None:
        model = get_default_model()

    model = _require_non_empty_string(
        model,
        "model",
    )

    if not isinstance(
        max_output_tokens,
        int,
    ):
        raise TypeError(
            "max_output_tokensはint型で"
            "ある必要があります。"
        )

    if max_output_tokens <= 0:
        raise ValueError(
            "max_output_tokensは1以上で"
            "ある必要があります。"
        )

    reasoning_effort = (
        _require_non_empty_string(
            reasoning_effort,
            "reasoning_effort",
        )
    )

    if not isinstance(
        store,
        bool,
    ):
        raise TypeError(
            "storeはbool型である必要があります。"
        )

    repair_input = build_repair_input(
        ai_reading=ai_reading,
        quality_report=quality_report,
        reading_context=reading_context,
        consultation_context=(
            consultation_context
        ),
    )

    protected_facts = (
        build_protected_facts(
            reading_context
        )
    )

    protected_text = json.dumps(
        protected_facts,
        ensure_ascii=False,
        indent=2,
    )

    user_input = (
        repair_input
        + "\n\n"
        + "【変更禁止の計算済み事実】\n"
        + protected_text
    )

    return {
        "model": model,
        "instructions": (
            build_repair_instructions()
        ),
        "input": user_input,
        "max_output_tokens": (
            max_output_tokens
        ),
        "reasoning": {
            "effort": (
                reasoning_effort
            ),
        },
        "store": store,
    }


# ============================================================
# Main repair
# ============================================================


def repair_reading(
    ai_reading: Mapping[str, Any],
    quality_report: ReadingQualityReport,
    *,
    reading_context: Mapping[
        str,
        Any,
    ],
    consultation_context: Mapping[
        str,
        Any,
    ] | None = None,
    client: Any = None,
    api_key: str | None = None,
    model: str | None = None,
    sections: Sequence[str] | None = None,
    max_output_tokens: int = (
        DEFAULT_MAX_OUTPUT_TOKENS
    ),
    reasoning_effort: str = (
        DEFAULT_REASONING_EFFORT
    ),
    store: bool = DEFAULT_STORE,
) -> ReadingRepairResult:
    """
    品質問題をもとに
    AI鑑定文章を1回だけ修復する。

    この関数自身は再試行ループを持たない。
    最大修復回数は呼び出し側が管理する。
    """

    ai_reading = _require_mapping(
        ai_reading,
        "ai_reading",
    )

    reading_context = _require_mapping(
        reading_context,
        "reading_context",
    )

    if not isinstance(
        quality_report,
        ReadingQualityReport,
    ):
        raise TypeError(
            "quality_reportは"
            "ReadingQualityReport"
            "である必要があります。"
        )

    if quality_report.issue_count <= 0:
        raise ReadingRepairConfigurationError(
            "品質問題が0件のため"
            "Auto-Repairは実行できません。"
        )

    if sections is None:
        sections_value = (
            ai_reading.get(
                "sections"
            )
        )

        if isinstance(
            sections_value,
            Mapping,
        ):
            normalized_sections = tuple(
                str(key)
                for key
                in sections_value.keys()
            )
        else:
            normalized_sections = tuple()

    else:
        normalized_sections = tuple(
            _require_non_empty_string(
                section,
                "section",
            )
            for section in sections
        )

    if not normalized_sections:
        raise ReadingRepairConfigurationError(
            "鑑定セクションを"
            "特定できませんでした。"
        )

    resolved_model = (
        get_default_model()
        if model is None
        else _require_non_empty_string(
            model,
            "model",
        )
    )

    payload = build_repair_payload(
        ai_reading=ai_reading,
        quality_report=quality_report,
        reading_context=reading_context,
        consultation_context=(
            consultation_context
        ),
        model=resolved_model,
        max_output_tokens=(
            max_output_tokens
        ),
        reasoning_effort=(
            reasoning_effort
        ),
        store=store,
    )

    if client is None:
        try:
            client = create_openai_client(
                api_key=api_key
            )
        except Exception as exc:
            raise ReadingRepairConfigurationError(
                "OpenAI clientを"
                "生成できませんでした。 "
                f"{type(exc).__name__}: {exc}"
            ) from exc

    response = _execute_repair_request(
        client,
        payload,
    )

    _validate_response_status(
        response
    )

    text = _extract_response_text(
        response
    )

    try:
        repaired = parse_reading_json(
            text
        )

    except (
        ReadingGeneratorJSONError,
        ValueError,
        TypeError,
    ) as exc:
        raise ReadingRepairValidationError(
            "Auto-Repair後の文章を"
            "JSONとして解析できませんでした。 "
            f"{type(exc).__name__}: {exc}"
        ) from exc

    try:
        validate_generated_reading_json(
            repaired,
            sections=(
                normalized_sections
            ),
        )

    except Exception as exc:
        raise ReadingRepairValidationError(
            "Auto-Repair後JSONが"
            "鑑定JSON契約を満たしていません。 "
            f"{type(exc).__name__}: {exc}"
        ) from exc

    validate_same_json_structure(
        ai_reading,
        repaired,
    )

    metadata = (
        _extract_response_metadata(
            response
        )
    )

    return ReadingRepairResult(
        original=_json_safe_copy(
            ai_reading
        ),
        repaired=_json_safe_copy(
            repaired
        ),
        issue_count=(
            quality_report.issue_count
        ),
        error_count=(
            quality_report.error_count
        ),
        warning_count=(
            quality_report.warning_count
        ),
        repaired_issue_codes=(
            get_issue_codes(
                quality_report
            )
        ),
        response_id=metadata[
            "response_id"
        ],
        response_status=metadata[
            "response_status"
        ],
        usage=metadata[
            "usage"
        ],
        model=resolved_model,
    )


# ============================================================
# Convenience
# ============================================================


def repair_reading_json(
    ai_reading: Mapping[str, Any],
    quality_report: ReadingQualityReport,
    *,
    reading_context: Mapping[
        str,
        Any,
    ],
    consultation_context: Mapping[
        str,
        Any,
    ] | None = None,
    client: Any = None,
    api_key: str | None = None,
    model: str | None = None,
    sections: Sequence[str] | None = None,
    max_output_tokens: int = (
        DEFAULT_MAX_OUTPUT_TOKENS
    ),
    reasoning_effort: str = (
        DEFAULT_REASONING_EFFORT
    ),
    store: bool = DEFAULT_STORE,
) -> Dict[str, Any]:
    """
    修復済みJSONだけが必要な場合の
    convenience API。
    """

    result = repair_reading(
        ai_reading,
        quality_report,
        reading_context=reading_context,
        consultation_context=(
            consultation_context
        ),
        client=client,
        api_key=api_key,
        model=model,
        sections=sections,
        max_output_tokens=(
            max_output_tokens
        ),
        reasoning_effort=(
            reasoning_effort
        ),
        store=store,
    )

    return deepcopy(
        result.repaired
    )


# ============================================================
# Metadata
# ============================================================


def get_reading_repair_metadata() -> Dict[str, Any]:
    """
    Reading Repair metadata。
    APIキーは含めない。
    """

    return {
        "version": (
            READING_REPAIR_VERSION
        ),
        "method": (
            READING_REPAIR_METHOD
        ),
        "status": (
            READING_REPAIR_STATUS
        ),
        "default_model": (
            get_default_model()
        ),
        "default_max_output_tokens": (
            DEFAULT_MAX_OUTPUT_TOKENS
        ),
        "default_reasoning_effort": (
            DEFAULT_REASONING_EFFORT
        ),
        "default_store": (
            DEFAULT_STORE
        ),
        "recalculates_astrology": False,
        "changes_reading_context": False,
        "changes_consultation_context": False,
        "max_repair_attempts": (
            "caller_controlled"
        ),
    }


# ============================================================
# Public API
# ============================================================


__all__ = [
    "READING_REPAIR_VERSION",
    "READING_REPAIR_METHOD",
    "READING_REPAIR_STATUS",
    "DEFAULT_MAX_OUTPUT_TOKENS",
    "DEFAULT_REASONING_EFFORT",
    "DEFAULT_STORE",
    "ReadingRepairError",
    "ReadingRepairConfigurationError",
    "ReadingRepairRequestError",
    "ReadingRepairResponseError",
    "ReadingRepairValidationError",
    "ReadingRepairResult",
    "serialize_quality_issue",
    "serialize_quality_report",
    "get_issue_codes",
    "build_repair_instructions",
    "build_repair_input",
    "validate_same_json_structure",
    "build_protected_facts",
    "build_repair_payload",
    "repair_reading",
    "repair_reading_json",
    "get_reading_repair_metadata",
]
