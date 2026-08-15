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
import re

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

PARTIAL_REPAIR_MAX_TARGETS = 32

PARTIAL_REPAIR_TASK = (
    "customer_facing_partial_repair_v1"
)


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
# Partial repair
# ============================================================


_PATH_TOKEN_RE = re.compile(
    r"""
    (?:
        ^|
        \.
    )
    (?P<key>[^.\[\]]+)
    |
    \[
        (?P<index>\d+)
    \]
    """,
    re.VERBOSE,
)


def _parse_json_path(
    path: str,
) -> tuple[str | int, ...]:
    path = _require_non_empty_string(
        path,
        "path",
    )

    tokens: list[str | int] = []
    position = 0

    for match in _PATH_TOKEN_RE.finditer(
        path
    ):
        if match.start() != position:
            raise ReadingRepairValidationError(
                "Auto-Repair対象pathを"
                "解析できません。 "
                f"path={path}"
            )

        key = match.group("key")
        index = match.group("index")

        if key is not None:
            tokens.append(key)
        elif index is not None:
            tokens.append(int(index))

        position = match.end()

    if (
        position != len(path)
        or not tokens
    ):
        raise ReadingRepairValidationError(
            "Auto-Repair対象pathを"
            "解析できません。 "
            f"path={path}"
        )

    return tuple(tokens)


def _get_json_path_value(
    root: Any,
    path: str,
) -> Any:
    current = root

    for token in _parse_json_path(
        path
    ):
        if isinstance(token, int):
            if (
                not isinstance(
                    current,
                    Sequence,
                )
                or isinstance(
                    current,
                    (
                        str,
                        bytes,
                        bytearray,
                    ),
                )
                or token < 0
                or token >= len(current)
            ):
                raise ReadingRepairValidationError(
                    "Auto-Repair対象pathが"
                    "元JSONに存在しません。 "
                    f"path={path}"
                )

            current = current[token]

        else:
            if (
                not isinstance(
                    current,
                    Mapping,
                )
                or token not in current
            ):
                raise ReadingRepairValidationError(
                    "Auto-Repair対象pathが"
                    "元JSONに存在しません。 "
                    f"path={path}"
                )

            current = current[token]

    return current


def _set_json_path_value(
    root: Any,
    path: str,
    value: Any,
) -> None:
    tokens = _parse_json_path(
        path
    )

    current = root

    for token in tokens[:-1]:
        if isinstance(token, int):
            if (
                not isinstance(
                    current,
                    list,
                )
                or token < 0
                or token >= len(current)
            ):
                raise ReadingRepairValidationError(
                    "Auto-Repair差し戻しpathが"
                    "不正です。 "
                    f"path={path}"
                )

            current = current[token]

        else:
            if (
                not isinstance(
                    current,
                    Mapping,
                )
                or token not in current
            ):
                raise ReadingRepairValidationError(
                    "Auto-Repair差し戻しpathが"
                    "不正です。 "
                    f"path={path}"
                )

            current = current[token]

    final_token = tokens[-1]

    if isinstance(final_token, int):
        if (
            not isinstance(
                current,
                list,
            )
            or final_token < 0
            or final_token >= len(current)
        ):
            raise ReadingRepairValidationError(
                "Auto-Repair差し戻しpathが"
                "不正です。 "
                f"path={path}"
            )

        current[final_token] = value
        return

    if (
        not isinstance(
            current,
            Mapping,
        )
        or final_token not in current
    ):
        raise ReadingRepairValidationError(
            "Auto-Repair差し戻しpathが"
            "不正です。 "
            f"path={path}"
        )

    current[final_token] = value


def _iter_string_leaf_paths(
    value: Any,
    *,
    prefix: str = "",
) -> tuple[
    tuple[str, str],
    ...,
]:
    result: list[
        tuple[str, str]
    ] = []

    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key)
            child_path = (
                f"{prefix}.{key_text}"
                if prefix
                else key_text
            )

            result.extend(
                _iter_string_leaf_paths(
                    child,
                    prefix=child_path,
                )
            )

        return tuple(result)

    if (
        isinstance(value, Sequence)
        and not isinstance(
            value,
            (
                str,
                bytes,
                bytearray,
            ),
        )
    ):
        for index, child in enumerate(value):
            child_path = (
                f"{prefix}[{index}]"
            )

            result.extend(
                _iter_string_leaf_paths(
                    child,
                    prefix=child_path,
                )
            )

        return tuple(result)

    if isinstance(value, str):
        result.append(
            (
                prefix,
                value,
            )
        )

    return tuple(result)


def _candidate_paths_under_issue(
    ai_reading: Mapping[
        str,
        Any,
    ],
    issue: QualityIssue,
) -> tuple[str, ...]:
    issue_path = _require_non_empty_string(
        issue.path,
        "issue.path",
    )

    try:
        value = _get_json_path_value(
            ai_reading,
            issue_path,
        )
    except ReadingRepairValidationError:
        return ()

    if isinstance(value, str):
        return (issue_path,)

    leaf_paths = (
        _iter_string_leaf_paths(
            value,
            prefix=issue_path,
        )
    )

    if not leaf_paths:
        return ()

    matched = (
        issue.matched.strip()
        if isinstance(
            issue.matched,
            str,
        )
        else ""
    )

    if matched:
        exact_matches = tuple(
            path
            for path, leaf_value
            in leaf_paths
            if matched in leaf_value
        )

        if exact_matches:
            return exact_matches

    result = []

    for path, _leaf_value in leaf_paths:
        if (
            path.endswith(".summary")
            or path.endswith(".detail")
            or ".evidence[" in path
            or ".advice[" in path
        ):
            result.append(path)

    return tuple(result)


def collect_partial_repair_targets(
    ai_reading: Mapping[
        str,
        Any,
    ],
    quality_report: ReadingQualityReport,
    *,
    max_targets: int = (
        PARTIAL_REPAIR_MAX_TARGETS
    ),
) -> tuple[str, ...]:
    ai_reading = _require_mapping(
        ai_reading,
        "ai_reading",
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

    if (
        not isinstance(max_targets, int)
        or isinstance(max_targets, bool)
    ):
        raise TypeError(
            "max_targetsはint型で"
            "ある必要があります。"
        )

    if max_targets <= 0:
        raise ValueError(
            "max_targetsは1以上で"
            "ある必要があります。"
        )

    result: list[str] = []

    for issue in quality_report.issues:
        for path in _candidate_paths_under_issue(
            ai_reading,
            issue,
        ):
            if path in result:
                continue

            original_value = (
                _get_json_path_value(
                    ai_reading,
                    path,
                )
            )

            if not isinstance(
                original_value,
                str,
            ):
                continue

            result.append(path)

            if len(result) >= max_targets:
                return tuple(result)

    if not result:
        raise ReadingRepairConfigurationError(
            "QualityIssueから"
            "部分修復対象の文章pathを"
            "特定できませんでした。"
        )

    return tuple(result)


def build_partial_repair_instructions() -> str:
    return """
あなたは四柱推命鑑定書の文章品質修正担当です。

品質検査で問題になった文章だけを修正してください。
鑑定書全体を書き直してはいけません。

あなたの仕事は占術計算ではありません。
文章編集だけを行ってください。

【絶対ルール】

1. targets に指定された path だけを修正してください。
2. targets に存在しない path を出力してはいけません。
3. path は1文字も変更しないでください。
4. 命式・日主・五行・通変星・十二運・身強身弱・格局・用神・大運・歳運・five_year_luck などの計算済み情報を変更しないでください。
5. 相談者の悩みや理想の未来を別内容へ変更しないでください。
6. 元文章の意味をできるだけ維持し、QualityIssueだけを解消してください。
7. 問題のない文章へ修正範囲を広げないでください。
8. 健康・医療・法律・投資・金融について断定的な専門判断へ変更しないでください。
9. future_flow.yearly の対象年・年順・意味を変更しないでください。
10. 内部キー名やsnake_caseを顧客向け文章へ漏らさないでください。

【出力形式】

次のJSONだけを返してください。

{
  "repairs": [
    {
      "path": "targetsにあるpath",
      "value": "修正後の文章"
    }
  ]
}

説明文、Markdown、コードフェンス、修正理由、前置き、後書きは不要です。
同じpathを2回出力しないでください。
""".strip()


def build_partial_repair_input(
    *,
    ai_reading: Mapping[
        str,
        Any,
    ],
    quality_report: ReadingQualityReport,
    reading_context: Mapping[
        str,
        Any,
    ],
    consultation_context: Mapping[
        str,
        Any,
    ] | None = None,
    target_paths: Sequence[
        str
    ] | None = None,
) -> str:
    ai_reading = _require_mapping(
        ai_reading,
        "ai_reading",
    )

    reading_context = _require_mapping(
        reading_context,
        "reading_context",
    )

    if consultation_context is not None:
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

    if target_paths is None:
        resolved_paths = (
            collect_partial_repair_targets(
                ai_reading,
                quality_report,
            )
        )
    else:
        resolved_paths = tuple(
            _require_non_empty_string(
                path,
                "target_path",
            )
            for path in target_paths
        )

    targets = []

    for path in resolved_paths:
        value = _get_json_path_value(
            ai_reading,
            path,
        )

        if not isinstance(value, str):
            raise ReadingRepairConfigurationError(
                "部分修復対象はstr文章で"
                "ある必要があります。 "
                f"path={path}"
            )

        targets.append(
            {
                "path": path,
                "value": value,
            }
        )

    payload = {
        "task": PARTIAL_REPAIR_TASK,
        "quality_report": (
            serialize_quality_report(
                quality_report
            )
        ),
        "targets": targets,
        "consultation_context": (
            _json_safe_copy(
                consultation_context
            )
            if consultation_context
            is not None
            else None
        ),
        "protected_facts": (
            build_protected_facts(
                reading_context
            )
        ),
    }

    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def build_partial_repair_payload(
    *,
    ai_reading: Mapping[
        str,
        Any,
    ],
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
    target_paths: Sequence[
        str
    ] | None = None,
) -> Dict[str, Any]:
    resolved_model = (
        get_default_model()
        if model is None
        else _require_non_empty_string(
            model,
            "model",
        )
    )

    if (
        not isinstance(
            max_output_tokens,
            int,
        )
        or isinstance(
            max_output_tokens,
            bool,
        )
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

    if not isinstance(store, bool):
        raise TypeError(
            "storeはbool型である必要があります。"
        )

    return {
        "model": resolved_model,
        "instructions": (
            build_partial_repair_instructions()
        ),
        "input": (
            build_partial_repair_input(
                ai_reading=ai_reading,
                quality_report=(
                    quality_report
                ),
                reading_context=(
                    reading_context
                ),
                consultation_context=(
                    consultation_context
                ),
                target_paths=(
                    target_paths
                ),
            )
        ),
        "max_output_tokens": (
            max_output_tokens
        ),
        "reasoning": {
            "effort": reasoning_effort,
        },
        "store": store,
    }


def _strip_json_code_fence(
    text: str,
) -> str:
    text = text.strip()

    if text.startswith("```"):
        lines = text.splitlines()

        if lines:
            lines = lines[1:]

        if (
            lines
            and lines[-1].strip()
            == "```"
        ):
            lines = lines[:-1]

        text = "\n".join(
            lines
        ).strip()

    return text


def parse_partial_repair_response(
    text: str,
) -> Dict[str, str]:
    text = _require_non_empty_string(
        text,
        "text",
    )

    try:
        payload = json.loads(
            _strip_json_code_fence(
                text
            )
        )
    except json.JSONDecodeError as exc:
        raise ReadingRepairValidationError(
            "Auto-Repairの部分修復結果を"
            "JSONとして解析できませんでした。 "
            f"{exc}"
        ) from exc

    if not isinstance(payload, Mapping):
        raise ReadingRepairValidationError(
            "Auto-Repairの部分修復結果は"
            "dict型である必要があります。"
        )

    repairs = payload.get("repairs")

    if not isinstance(repairs, list):
        raise ReadingRepairValidationError(
            "Auto-Repairの部分修復結果に"
            "repairs配列がありません。"
        )

    result: Dict[str, str] = {}

    for item in repairs:
        if not isinstance(item, Mapping):
            raise ReadingRepairValidationError(
                "repairsの各要素は"
                "dict型である必要があります。"
            )

        path = item.get("path")
        value = item.get("value")

        if (
            not isinstance(path, str)
            or not path.strip()
        ):
            raise ReadingRepairValidationError(
                "repairs.pathは"
                "空でないstrである必要があります。"
            )

        if not isinstance(value, str):
            raise ReadingRepairValidationError(
                "repairs.valueは"
                "strである必要があります。 "
                f"path={path}"
            )

        path = path.strip()

        if path in result:
            raise ReadingRepairValidationError(
                "同じpathが部分修復結果に"
                "重複しています。 "
                f"path={path}"
            )

        result[path] = value

    if not result:
        raise ReadingRepairValidationError(
            "Auto-Repairの部分修復結果が"
            "空です。"
        )

    return result


def apply_partial_repairs(
    ai_reading: Mapping[
        str,
        Any,
    ],
    repairs: Mapping[
        str,
        str,
    ],
    *,
    allowed_paths: Sequence[
        str
    ],
) -> Dict[str, Any]:
    ai_reading = _require_mapping(
        ai_reading,
        "ai_reading",
    )

    repairs = _require_mapping(
        repairs,
        "repairs",
    )

    allowed = tuple(
        _require_non_empty_string(
            path,
            "allowed_path",
        )
        for path in allowed_paths
    )

    allowed_set = set(allowed)

    unknown_paths = [
        str(path)
        for path in repairs.keys()
        if str(path) not in allowed_set
    ]

    if unknown_paths:
        raise ReadingRepairValidationError(
            "Auto-Repairが許可されていない"
            "pathを変更しようとしました。 "
            f"paths={unknown_paths}"
        )

    repaired = _json_safe_copy(
        ai_reading
    )

    for path, new_value in repairs.items():
        original_value = (
            _get_json_path_value(
                ai_reading,
                path,
            )
        )

        if not isinstance(
            original_value,
            str,
        ):
            raise ReadingRepairValidationError(
                "部分修復対象の元値が"
                "strではありません。 "
                f"path={path}"
            )

        if not isinstance(new_value, str):
            raise ReadingRepairValidationError(
                "部分修復後の値が"
                "strではありません。 "
                f"path={path}"
            )

        if (
            original_value.strip()
            and not new_value.strip()
        ):
            raise ReadingRepairValidationError(
                "Auto-Repairによって"
                "既存文章が空にされました。 "
                f"path={path}"
            )

        _set_json_path_value(
            repaired,
            path,
            new_value,
        )

    validate_same_json_structure(
        ai_reading,
        repaired,
    )

    return repaired


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
    AI鑑定文章を1回だけ部分修復する。
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
            ai_reading.get("sections")
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

    target_paths = (
        collect_partial_repair_targets(
            ai_reading,
            quality_report,
        )
    )

    payload = (
        build_partial_repair_payload(
            ai_reading=ai_reading,
            quality_report=(
                quality_report
            ),
            reading_context=(
                reading_context
            ),
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
            target_paths=(
                target_paths
            ),
        )
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

    response_text = (
        _extract_response_text(
            response
        )
    )

    try:
        repairs = (
            parse_partial_repair_response(
                response_text
            )
        )

        repaired = apply_partial_repairs(
            ai_reading,
            repairs,
            allowed_paths=(
                target_paths
            ),
        )

    except ReadingRepairValidationError as partial_exc:
        # 既存テスト・旧fake responseとの互換用。
        # 本番partial promptでは通常ここへ入らない。
        try:
            legacy_repaired = (
                parse_reading_json(
                    response_text
                )
            )

        except (
            ReadingGeneratorJSONError,
            ValueError,
            TypeError,
        ) as legacy_exc:
            raise ReadingRepairValidationError(
                "Auto-Repair後の部分修復JSONを"
                "解析できませんでした。 "
                f"partial_error={partial_exc}; "
                f"legacy_error="
                f"{type(legacy_exc).__name__}: "
                f"{legacy_exc}"
            ) from legacy_exc

        repaired = _json_safe_copy(
            legacy_repaired
        )

        validate_same_json_structure(
            ai_reading,
            repaired,
        )

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
        "repair_scope": (
            "quality_issue_targeted_partial"
        ),
        "partial_repair_max_targets": (
            PARTIAL_REPAIR_MAX_TARGETS
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
    "PARTIAL_REPAIR_MAX_TARGETS",
    "PARTIAL_REPAIR_TASK",
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
    "collect_partial_repair_targets",
    "build_partial_repair_instructions",
    "build_partial_repair_input",
    "build_partial_repair_payload",
    "parse_partial_repair_response",
    "apply_partial_repairs",
    "validate_same_json_structure",
    "build_protected_facts",
    "build_repair_payload",
    "repair_reading",
    "repair_reading_json",
    "get_reading_repair_metadata",
]