"""
Customer-facing reading quality gate.

このモジュールは、OpenAI が生成した四柱推命鑑定結果を
PDF・商品JSONなどへ渡す前に検査するための最終品質ゲートです。

重要:
- 四柱推命の再計算は行わない。
- reading_context の計算済み事実を変更しない。
- AI生成文章を書き換えない。
- 問題を検出して報告するだけにする。
- 内部JSONキーそのものではなく、
  顧客が読む文章フィールドだけを検査する。

主な検査対象:
1. 内部評価ラベルの流出
2. snake_case / JSON path / field=value の流出
3. 過度に断定的な表現
4. 根拠のない具体的数値による助言
5. disclaimer の最低限の安全性
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import re
from typing import Any, Iterable, Mapping, Sequence


READING_QUALITY_VERSION = "reading_quality_v1"
READING_QUALITY_METHOD = "customer_facing_quality_gate_v1"
READING_QUALITY_STATUS = "ready_for_customer_facing_validation"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ReadingQualityError(ValueError):
    """顧客向け鑑定文章が品質ゲートを通過しなかった場合の例外。"""


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class QualityIssue:
    """
    1件の品質問題。

    code:
        機械判定用コード。

    message:
        人間が確認するための説明。

    path:
        ai_reading 内の位置。
        例:
            sections.wealth.evidence[4]

    value:
        問題が見つかった文章。

    matched:
        実際に検出された文字列。
    """

    code: str
    message: str
    path: str
    value: str
    matched: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "path": self.path,
            "value": self.value,
            "matched": self.matched,
        }


@dataclass(frozen=True)
class ReadingQualityReport:
    """
    品質検査結果。

    valid=True の場合のみ、
    顧客向け商品へ進めることを想定する。
    """

    valid: bool
    issues: tuple[QualityIssue, ...] = field(
        default_factory=tuple
    )
    version: str = READING_QUALITY_VERSION
    method: str = READING_QUALITY_METHOD
    status: str = READING_QUALITY_STATUS

    @property
    def issue_count(self) -> int:
        return len(self.issues)

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "issue_count": self.issue_count,
            "issues": [
                issue.to_dict()
                for issue in self.issues
            ],
            "version": self.version,
            "method": self.method,
            "status": self.status,
        }


@dataclass(frozen=True)
class CustomerFacingText:
    """
    顧客が実際に読む文章と、そのJSON上の位置。
    """

    path: str
    text: str
    kind: str


# ---------------------------------------------------------------------------
# Customer-facing schema
# ---------------------------------------------------------------------------


CUSTOMER_SECTION_TEXT_FIELDS = (
    "title",
    "summary",
    "detail",
)

CUSTOMER_SECTION_LIST_FIELDS = (
    "evidence",
    "advice",
)

ROOT_CUSTOMER_TEXT_FIELDS = (
    "summary",
    "disclaimer",
)


# ---------------------------------------------------------------------------
# Internal labels
# ---------------------------------------------------------------------------


# 単語境界を使える英語ラベル。
INTERNAL_ENGLISH_LABELS = (
    "mixed",
    "overall",
    "positive",
    "negative",
    "neutral",
)


# 顧客文章にそのまま出す必要がない代表的内部キー。
#
# 注意:
# JSON構造のキーとして存在することは禁止しない。
# 顧客向け文章内にそのまま現れた場合だけ検出する。
INTERNAL_FIELD_NAMES = (
    "overall_score",
    "overall_level",
    "current_luck",
    "future_flow",
    "core_personality",
    "useful_gods",
    "reading_context",
    "consultation_context",
    "integrated_luck",
    "day_master",
    "strength_judgment",
    "weighted_strength_judgment",
    "pattern_judgment",
    "generation_payload",
    "ai_usage_policy",
    "schema_version",
)


# ---------------------------------------------------------------------------
# Regex
# ---------------------------------------------------------------------------


SNAKE_CASE_RE = re.compile(
    r"(?<![A-Za-z0-9])"
    r"[a-z][a-z0-9]*(?:_[a-z0-9]+)+"
    r"(?![A-Za-z0-9])"
)


JSON_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_])"
    r"(?:[A-Za-z_][A-Za-z0-9_]*\.)+"
    r"[A-Za-z_][A-Za-z0-9_]*"
)


FIELD_ASSIGNMENT_RE = re.compile(
    r"(?<![A-Za-z0-9_])"
    r"[A-Za-z_][A-Za-z0-9_]*"
    r"\s*=\s*"
    r"[A-Za-z0-9_.\-]+"
)


# 「2〜3種類」のようなAIが作りやすい数量助言を検出する。
#
# すべての数字を禁止するわけではない。
# 年、干支、スコアなどの計算済み数値は別途
# reading_context / consultation_context と照合する。
NUMERIC_RANGE_RE = re.compile(
    r"(?<!\d)"
    r"\d+(?:\.\d+)?"
    r"\s*(?:〜|～|~|-)"
    r"\s*\d+(?:\.\d+)?"
    r"\s*"
    r"(?:"
    r"回|件|種類|個|本|人|社|項目|段階|つ|"
    r"日|週間|週|か月|ヶ月|月|年|"
    r"円|万円|億円|%|％"
    r")"
)


NUMERIC_COUNT_RE = re.compile(
    r"(?<!\d)"
    r"\d+(?:\.\d+)?"
    r"\s*"
    r"(?:"
    r"回|件|種類|個|本|人|社|項目|段階|つ"
    r")"
)


NUMERIC_FREQUENCY_RE = re.compile(
    r"(?:"
    r"毎日|毎週|毎月|週に|月に|年に"
    r")"
    r"\s*"
    r"\d+(?:\.\d+)?"
    r"\s*"
    r"(?:回|件|日|時間|分)"
)


MONEY_TARGET_RE = re.compile(
    r"(?<!\d)"
    r"\d+(?:,\d{3})*(?:\.\d+)?"
    r"\s*"
    r"(?:円|万円|億円)"
)


PERCENT_TARGET_RE = re.compile(
    r"(?<!\d)"
    r"\d+(?:\.\d+)?"
    r"\s*(?:%|％)"
)


# ---------------------------------------------------------------------------
# Overconfidence / unsafe certainty
# ---------------------------------------------------------------------------


OVERCONFIDENT_PATTERNS: tuple[
    tuple[str, re.Pattern[str]],
    ...
] = (
    (
        "guaranteed_success",
        re.compile(
            r"(?:必ず|確実に|絶対に)"
            r".{0,16}"
            r"(?:成功|うまくいく|達成)"
        ),
    ),
    (
        "guaranteed_profit",
        re.compile(
            r"(?:必ず|確実に|絶対に)"
            r".{0,16}"
            r"(?:儲かる|利益|収益|稼げる)"
        ),
    ),
    (
        "guaranteed_marriage",
        re.compile(
            r"(?:必ず|確実に|絶対に)"
            r".{0,16}"
            r"(?:結婚|復縁|恋人)"
        ),
    ),
    (
        "guaranteed_job_change",
        re.compile(
            r"(?:必ず|確実に|絶対に)"
            r".{0,16}"
            r"(?:転職|独立|起業)"
        ),
    ),
    (
        "medical_diagnosis",
        re.compile(
            r"(?:"
            r"病気になります|"
            r"病気になるでしょう|"
            r"発症します|"
            r"発症するでしょう|"
            r"寿命は\d+"
            r")"
        ),
    ),
)


# ---------------------------------------------------------------------------
# Disclaimer
# ---------------------------------------------------------------------------


DISCLAIMER_REQUIRED_CONCEPTS = {
    "medical": (
        "医学",
        "医療",
        "診断",
        "健康",
    ),
    "financial": (
        "投資",
        "金融",
        "資産",
        "金銭",
    ),
    "future_uncertainty": (
        "断定",
        "保証",
        "約束",
        "確実",
    ),
}


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _require_mapping(
    value: Any,
    *,
    name: str,
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(
            f"{name}はMappingである必要があります。"
        )
    return value


def _optional_mapping(
    value: Any,
    *,
    name: str,
) -> Mapping[str, Any] | None:
    if value is None:
        return None

    return _require_mapping(
        value,
        name=name,
    )


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""

    if not isinstance(value, str):
        return ""

    return value.strip()


def _iter_string_list(
    value: Any,
) -> Iterable[tuple[int, str]]:
    if not isinstance(value, Sequence):
        return

    if isinstance(
        value,
        (str, bytes, bytearray),
    ):
        return

    for index, item in enumerate(value):
        if isinstance(item, str):
            text = item.strip()
            if text:
                yield index, text


# ---------------------------------------------------------------------------
# Customer-facing text extraction
# ---------------------------------------------------------------------------


def iter_customer_facing_texts(
    ai_reading: Mapping[str, Any],
) -> tuple[CustomerFacingText, ...]:
    """
    ai_reading のうち、
    顧客が実際に読む文章だけを抽出する。

    内部metadataなどは検査対象にしない。
    """

    reading = _require_mapping(
        ai_reading,
        name="ai_reading",
    )

    results: list[CustomerFacingText] = []

    for field_name in ROOT_CUSTOMER_TEXT_FIELDS:
        text = _normalize_text(
            reading.get(field_name)
        )

        if text:
            results.append(
                CustomerFacingText(
                    path=field_name,
                    text=text,
                    kind=field_name,
                )
            )

    sections = reading.get("sections")

    if sections is None:
        return tuple(results)

    if not isinstance(sections, Mapping):
        raise TypeError(
            "ai_reading.sectionsは"
            "Mappingである必要があります。"
        )

    for section_name, section_value in sections.items():
        if not isinstance(section_name, str):
            continue

        if not isinstance(section_value, Mapping):
            continue

        base_path = (
            f"sections.{section_name}"
        )

        for field_name in CUSTOMER_SECTION_TEXT_FIELDS:
            text = _normalize_text(
                section_value.get(field_name)
            )

            if not text:
                continue

            results.append(
                CustomerFacingText(
                    path=(
                        f"{base_path}.{field_name}"
                    ),
                    text=text,
                    kind=field_name,
                )
            )

        for field_name in CUSTOMER_SECTION_LIST_FIELDS:
            raw_items = section_value.get(
                field_name
            )

            for index, text in _iter_string_list(
                raw_items
            ):
                results.append(
                    CustomerFacingText(
                        path=(
                            f"{base_path}."
                            f"{field_name}[{index}]"
                        ),
                        text=text,
                        kind=field_name,
                    )
                )

    return tuple(results)


# ---------------------------------------------------------------------------
# Internal label leak detection
# ---------------------------------------------------------------------------


def find_internal_label_leaks(
    ai_reading: Mapping[str, Any],
) -> tuple[QualityIssue, ...]:
    """
    mixed / overall 等の内部評価ラベルが
    顧客向け文章へ漏れていないか確認する。
    """

    issues: list[QualityIssue] = []

    texts = iter_customer_facing_texts(
        ai_reading
    )

    for item in texts:
        for label in INTERNAL_ENGLISH_LABELS:
            pattern = re.compile(
                rf"(?<![A-Za-z0-9_])"
                rf"{re.escape(label)}"
                rf"(?![A-Za-z0-9_])",
                re.IGNORECASE,
            )

            match = pattern.search(item.text)

            if match is None:
                continue

            issues.append(
                QualityIssue(
                    code="internal_label_leak",
                    message=(
                        "顧客向け文章に内部評価"
                        "ラベルが残っています。"
                    ),
                    path=item.path,
                    value=item.text,
                    matched=match.group(0),
                )
            )

    return tuple(issues)


# ---------------------------------------------------------------------------
# Internal key leak detection
# ---------------------------------------------------------------------------


def find_internal_key_leaks(
    ai_reading: Mapping[str, Any],
) -> tuple[QualityIssue, ...]:
    """
    snake_case、JSON path、field=value、
    代表的内部キーの顧客向け流出を検出する。
    """

    issues: list[QualityIssue] = []

    texts = iter_customer_facing_texts(
        ai_reading
    )

    for item in texts:
        detected: set[
            tuple[str, str]
        ] = set()

        for match in SNAKE_CASE_RE.finditer(
            item.text
        ):
            detected.add(
                (
                    "snake_case_leak",
                    match.group(0),
                )
            )

        for match in JSON_PATH_RE.finditer(
            item.text
        ):
            detected.add(
                (
                    "json_path_leak",
                    match.group(0),
                )
            )

        for match in FIELD_ASSIGNMENT_RE.finditer(
            item.text
        ):
            detected.add(
                (
                    "field_assignment_leak",
                    match.group(0),
                )
            )

        lowered = item.text.lower()

        for field_name in INTERNAL_FIELD_NAMES:
            if field_name.lower() in lowered:
                detected.add(
                    (
                        "internal_field_leak",
                        field_name,
                    )
                )

        for code, matched in sorted(
            detected
        ):
            if code == "snake_case_leak":
                message = (
                    "顧客向け文章にsnake_caseの"
                    "内部表現が残っています。"
                )
            elif code == "json_path_leak":
                message = (
                    "顧客向け文章にJSONパス形式の"
                    "内部表現が残っています。"
                )
            elif code == "field_assignment_leak":
                message = (
                    "顧客向け文章にfield=value形式の"
                    "内部表現が残っています。"
                )
            else:
                message = (
                    "顧客向け文章に内部フィールド名が"
                    "残っています。"
                )

            issues.append(
                QualityIssue(
                    code=code,
                    message=message,
                    path=item.path,
                    value=item.text,
                    matched=matched,
                )
            )

    return tuple(issues)


# ---------------------------------------------------------------------------
# Overconfident claim detection
# ---------------------------------------------------------------------------


def find_overconfident_claims(
    ai_reading: Mapping[str, Any],
) -> tuple[QualityIssue, ...]:
    """
    将来・成功・利益・健康等について、
    明らかに強すぎる断定を検出する。
    """

    issues: list[QualityIssue] = []

    for item in iter_customer_facing_texts(
        ai_reading
    ):
        for code, pattern in OVERCONFIDENT_PATTERNS:
            match = pattern.search(item.text)

            if match is None:
                continue

            issues.append(
                QualityIssue(
                    code=code,
                    message=(
                        "顧客向け文章に確定的すぎる"
                        "表現が含まれています。"
                    ),
                    path=item.path,
                    value=item.text,
                    matched=match.group(0),
                )
            )

    return tuple(issues)


# ---------------------------------------------------------------------------
# Numeric grounding
# ---------------------------------------------------------------------------


def _collect_numeric_strings(
    value: Any,
) -> set[str]:
    """
    reading_context / consultation_context に
    実際に存在する数値を文字列化して収集する。

    AIが作った数値か、
    入力データ由来かを判定する補助に使う。
    """

    results: set[str] = set()

    def walk(current: Any) -> None:
        if current is None:
            return

        if isinstance(current, bool):
            return

        if isinstance(current, int):
            results.add(str(current))
            return

        if isinstance(current, float):
            results.add(str(current))

            if current.is_integer():
                results.add(
                    str(int(current))
                )

            return

        if isinstance(current, str):
            for match in re.finditer(
                r"(?<!\d)"
                r"\d+(?:\.\d+)?"
                r"(?!\d)",
                current,
            ):
                results.add(
                    match.group(0)
                )
            return

        if isinstance(current, Mapping):
            for child in current.values():
                walk(child)
            return

        if isinstance(
            current,
            Sequence,
        ) and not isinstance(
            current,
            (str, bytes, bytearray),
        ):
            for child in current:
                walk(child)

    walk(value)

    return results


def _numbers_in_text(
    text: str,
) -> tuple[str, ...]:
    return tuple(
        match.group(0)
        for match in re.finditer(
            r"(?<!\d)"
            r"\d+(?:\.\d+)?"
            r"(?!\d)",
            text,
        )
    )


def _numeric_claim_is_grounded(
    matched_text: str,
    allowed_numbers: set[str],
) -> bool:
    numbers = _numbers_in_text(
        matched_text
    )

    if not numbers:
        return True

    return all(
        number in allowed_numbers
        for number in numbers
    )


def find_unsupported_numeric_claims(
    ai_reading: Mapping[str, Any],
    *,
    reading_context: Mapping[str, Any] | None = None,
    consultation_context: Mapping[str, Any] | None = None,
) -> tuple[QualityIssue, ...]:
    """
    顧客向け助言に含まれる、
    根拠のない具体的数量を検出する。

    特に advice を厳しく見る。

    年号や計算済みスコアなど、
    reading_context に存在する数字は
    原則として問題にしない。
    """

    reading_context = _optional_mapping(
        reading_context,
        name="reading_context",
    )

    consultation_context = _optional_mapping(
        consultation_context,
        name="consultation_context",
    )

    allowed_numbers: set[str] = set()

    if reading_context is not None:
        allowed_numbers.update(
            _collect_numeric_strings(
                reading_context
            )
        )

    if consultation_context is not None:
        allowed_numbers.update(
            _collect_numeric_strings(
                consultation_context
            )
        )

    issues: list[QualityIssue] = []

    patterns = (
        (
            "unsupported_numeric_range",
            NUMERIC_RANGE_RE,
        ),
        (
            "unsupported_numeric_count",
            NUMERIC_COUNT_RE,
        ),
        (
            "unsupported_numeric_frequency",
            NUMERIC_FREQUENCY_RE,
        ),
        (
            "unsupported_money_target",
            MONEY_TARGET_RE,
        ),
        (
            "unsupported_percent_target",
            PERCENT_TARGET_RE,
        ),
    )

    seen: set[
        tuple[str, str, str]
    ] = set()

    for item in iter_customer_facing_texts(
        ai_reading
    ):
        # 数値の助言を最も厳しく見るのは advice。
        #
        # summary/detail/evidence に存在する
        # 計算済み年号・スコア等を過剰検出しないため、
        # 基本的には advice を対象にする。
        if item.kind != "advice":
            continue

        for code, pattern in patterns:
            for match in pattern.finditer(
                item.text
            ):
                matched = match.group(0)

                if _numeric_claim_is_grounded(
                    matched,
                    allowed_numbers,
                ):
                    continue

                identity = (
                    item.path,
                    code,
                    matched,
                )

                if identity in seen:
                    continue

                seen.add(identity)

                issues.append(
                    QualityIssue(
                        code=code,
                        message=(
                            "顧客向け助言に、"
                            "reading_contextまたは"
                            "consultation_contextで"
                            "根拠を確認できない具体的数値が"
                            "含まれています。"
                        ),
                        path=item.path,
                        value=item.text,
                        matched=matched,
                    )
                )

    return tuple(issues)


# ---------------------------------------------------------------------------
# Disclaimer validation
# ---------------------------------------------------------------------------


def validate_disclaimer(
    ai_reading: Mapping[str, Any],
) -> tuple[QualityIssue, ...]:
    """
    disclaimer が最低限の安全概念を
    含んでいるか確認する。
    """

    reading = _require_mapping(
        ai_reading,
        name="ai_reading",
    )

    disclaimer = _normalize_text(
        reading.get("disclaimer")
    )

    if not disclaimer:
        return (
            QualityIssue(
                code="missing_disclaimer",
                message=(
                    "顧客向け鑑定にdisclaimerが"
                    "ありません。"
                ),
                path="disclaimer",
                value="",
                matched=None,
            ),
        )

    issues: list[QualityIssue] = []

    for concept, keywords in (
        DISCLAIMER_REQUIRED_CONCEPTS.items()
    ):
        if any(
            keyword in disclaimer
            for keyword in keywords
        ):
            continue

        issues.append(
            QualityIssue(
                code=(
                    "disclaimer_missing_"
                    f"{concept}"
                ),
                message=(
                    "disclaimerに必要な安全上の"
                    f"概念が不足しています: {concept}"
                ),
                path="disclaimer",
                value=disclaimer,
                matched=None,
            )
        )

    return tuple(issues)


# ---------------------------------------------------------------------------
# Full validation
# ---------------------------------------------------------------------------


def validate_customer_facing_reading(
    ai_reading: Mapping[str, Any],
    *,
    reading_context: Mapping[str, Any] | None = None,
    consultation_context: Mapping[str, Any] | None = None,
) -> ReadingQualityReport:
    """
    顧客向けAI鑑定の最終品質検査。

    この関数は文章を書き換えない。
    検出のみ行う。
    """

    _require_mapping(
        ai_reading,
        name="ai_reading",
    )

    _optional_mapping(
        reading_context,
        name="reading_context",
    )

    _optional_mapping(
        consultation_context,
        name="consultation_context",
    )

    issues: list[QualityIssue] = []

    issues.extend(
        find_internal_label_leaks(
            ai_reading
        )
    )

    issues.extend(
        find_internal_key_leaks(
            ai_reading
        )
    )

    issues.extend(
        find_overconfident_claims(
            ai_reading
        )
    )

    issues.extend(
        find_unsupported_numeric_claims(
            ai_reading,
            reading_context=reading_context,
            consultation_context=(
                consultation_context
            ),
        )
    )

    issues.extend(
        validate_disclaimer(
            ai_reading
        )
    )

    return ReadingQualityReport(
        valid=not issues,
        issues=tuple(issues),
    )


# ---------------------------------------------------------------------------
# Raise helper
# ---------------------------------------------------------------------------


def ensure_customer_facing_reading_quality(
    ai_reading: Mapping[str, Any],
    *,
    reading_context: Mapping[str, Any] | None = None,
    consultation_context: Mapping[str, Any] | None = None,
) -> ReadingQualityReport:
    """
    品質ゲートを実行し、
    問題があれば ReadingQualityError を送出する。

    PDF生成直前で使用する想定。
    """

    report = validate_customer_facing_reading(
        ai_reading,
        reading_context=reading_context,
        consultation_context=consultation_context,
    )

    if report.valid:
        return report

    lines = [
        "顧客向け鑑定文章が品質ゲートを"
        "通過しませんでした。",
        f"issue_count={report.issue_count}",
    ]

    for issue in report.issues:
        matched = (
            f" matched={issue.matched!r}"
            if issue.matched is not None
            else ""
        )

        lines.append(
            f"- [{issue.code}] "
            f"{issue.path}: "
            f"{issue.message}"
            f"{matched}"
        )

    raise ReadingQualityError(
        "\n".join(lines)
    )


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


def quality_report_to_json(
    report: ReadingQualityReport,
    *,
    ensure_ascii: bool = False,
    indent: int = 2,
) -> str:
    if not isinstance(
        report,
        ReadingQualityReport,
    ):
        raise TypeError(
            "reportはReadingQualityReport"
            "である必要があります。"
        )

    return json.dumps(
        report.to_dict(),
        ensure_ascii=ensure_ascii,
        indent=indent,
    )


__all__ = [
    "READING_QUALITY_VERSION",
    "READING_QUALITY_METHOD",
    "READING_QUALITY_STATUS",
    "ReadingQualityError",
    "QualityIssue",
    "ReadingQualityReport",
    "CustomerFacingText",
    "iter_customer_facing_texts",
    "find_internal_label_leaks",
    "find_internal_key_leaks",
    "find_overconfident_claims",
    "find_unsupported_numeric_claims",
    "validate_disclaimer",
    "validate_customer_facing_reading",
    "ensure_customer_facing_reading_quality",
    "quality_report_to_json",
]
