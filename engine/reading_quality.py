"""
Customer-facing reading quality gate.

OpenAI が生成した四柱推命鑑定結果を、
PDF・商品JSONへ渡す前に検査する最終品質ゲート。

v2 追加:
- 健康章の具体的な医学・生活習慣推測
- 同じ助言概念の章横断反復
- 同じ五行→同じ現代語への固定変換

重要:
- 四柱推命を再計算しない。
- reading_context を変更しない。
- AI文章を書き換えない。
- 問題を検出して報告するだけ。
- 既存v1の公開定数値は互換性維持のため変更しない。
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import json
import re
from typing import Any, Iterable, Mapping, Sequence


# 既存テスト・保存済みquality_reportとの互換性を維持する。
READING_QUALITY_VERSION = "reading_quality_v1"
READING_QUALITY_METHOD = "customer_facing_quality_gate_v1"
READING_QUALITY_STATUS = "ready_for_customer_facing_validation"

CUSTOMER_VALUE_QUALITY_VERSION = "customer_value_quality_v2"

# 品質問題の重大度。
#
# ERROR:
#   顧客向けPDFの生成を停止する。
#
# WARNING:
#   商品品質上は改善したいが、
#   それ単独ではPDF生成を停止しない。
WARNING_ISSUE_CODES = frozenset(
    {
        "cross_section_advice_repetition",
        "fixed_element_translation_overuse",
        "summary_detail_repetition",
        "within_section_text_repetition",
        "cross_section_phrase_repetition",
        "future_flow_yearly_repetition",
        "formulaic_phrase_overuse",
        "sentence_ending_overuse",
        "future_flow_style_repetition",
        "useful_gods_role_confusion",
    }
)


class ReadingQualityError(ValueError):
    """顧客向け鑑定文章が品質ゲートを通過しなかった場合の例外。"""


@dataclass(frozen=True)
class QualityIssue:
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
    valid: bool
    issues: tuple[QualityIssue, ...] = field(default_factory=tuple)
    version: str = READING_QUALITY_VERSION
    method: str = READING_QUALITY_METHOD
    status: str = READING_QUALITY_STATUS

    @property
    def issue_count(self) -> int:
        """
        ERROR + WARNING の総件数。
        既存コードとの互換性のため維持する。
        """
        return len(self.issues)

    @property
    def error_issues(self) -> tuple[QualityIssue, ...]:
        return tuple(
            issue
            for issue in self.issues
            if issue_severity(issue) == "error"
        )

    @property
    def warning_issues(self) -> tuple[QualityIssue, ...]:
        return tuple(
            issue
            for issue in self.issues
            if issue_severity(issue) == "warning"
        )

    @property
    def error_count(self) -> int:
        return len(self.error_issues)

    @property
    def warning_count(self) -> int:
        return len(self.warning_issues)

    def to_dict(self) -> dict[str, Any]:
        serialized_issues = []

        for issue in self.issues:
            item = issue.to_dict()
            item["severity"] = issue_severity(
                issue
            )
            serialized_issues.append(item)

        return {
            "valid": self.valid,
            "issue_count": self.issue_count,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "issues": serialized_issues,
            "version": self.version,
            "method": self.method,
            "status": self.status,
        }


@dataclass(frozen=True)
class CustomerFacingText:
    path: str
    text: str
    kind: str


def issue_severity(
    issue_or_code: QualityIssue | str,
) -> str:
    """
    品質問題の重大度を返す。

    warning:
        商品品質上の改善候補。
        これだけではPDF生成を止めない。

    error:
        顧客へ出すべきでない問題。
        PDF生成を停止する。
    """

    if isinstance(
        issue_or_code,
        QualityIssue,
    ):
        code = issue_or_code.code
    elif isinstance(
        issue_or_code,
        str,
    ):
        code = issue_or_code
    else:
        raise TypeError(
            "issue_or_codeはQualityIssue"
            "またはstrである必要があります。"
        )

    return (
        "warning"
        if code in WARNING_ISSUE_CODES
        else "error"
    )


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


INTERNAL_ENGLISH_LABELS = (
    "mixed",
    "overall",
    "positive",
    "negative",
    "neutral",
)

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
    "five_year_luck",
    "day_master",
    "strength_judgment",
    "weighted_strength_judgment",
    "pattern_judgment",
    "generation_payload",
    "ai_usage_policy",
    "schema_version",
)



# ============================================================
# Customer-facing style repetition rules
# ============================================================
#
# ここでは単語そのものではなく、
# 「AI鑑定で使い回されやすい説明の型」を見る。
#
# 一般的な丁寧語
#   - してください
#   - しましょう
#   - 傾向があります
#   - 流れです
# は対象外とする。
FORMULAIC_STYLE_PATTERNS = (
    (
        "示されています",
        re.compile(
            r"示されています"
        ),
    ),
    (
        "と読みます",
        re.compile(
            r"と読みます"
        ),
    ),
    (
        "が鍵です",
        re.compile(
            r"が鍵です"
        ),
    ),
    (
        "ことが重要です",
        re.compile(
            r"ことが重要です"
        ),
    ),
    (
        "と考えられます",
        re.compile(
            r"と考えられます"
        ),
    ),
)

# 章をまたいで同じ説明語尾が続くと、
# テンプレート感が強くなる表現だけを対象にする。
#
# 「です」「ます」単体は当然対象外。
SENTENCE_ENDING_STYLE_PATTERNS = (
    (
        "といえます",
        re.compile(
            r"といえます[。！？!?]?"
        ),
        5,
    ),
    (
        "でしょう",
        re.compile(
            r"でしょう[。！？!?]?"
        ),
        7,
    ),
)

FORMULAIC_STYLE_MIN_SECTIONS = 4
FUTURE_FLOW_STYLE_MIN_YEARS = 4


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
    r"(?:回|件|種類|個|本|人|社|項目|段階|つ)"
)

NUMERIC_FREQUENCY_RE = re.compile(
    r"(?:毎日|毎週|毎月|週に|月に|年に)"
    r"\s*"
    r"\d+(?:\.\d+)?"
    r"\s*"
    r"(?:回|件|日|時間|分)"
)

MONEY_TARGET_RE = re.compile(
    r"(?<!\d)"
    r"\d+(?:,\d{3})*(?:\.\d+)?"
    r"\s*(?:円|万円|億円)"
)

PERCENT_TARGET_RE = re.compile(
    r"(?<!\d)"
    r"\d+(?:\.\d+)?"
    r"\s*(?:%|％)"
)


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
# Customer-value v2
# ---------------------------------------------------------------------------

REPEATED_ADVICE_CONCEPTS = (
    "見える化",
    "可視化",
    "仕組み化",
    "標準化",
    "再現性",
    "情報収集",
    "人脈",
    "学習",
    "段階的",
    "チェックリスト",
    "抱え込み",
)

MAX_ADVICE_CONCEPT_SECTIONS = 3

ELEMENT_TRANSLATIONS = {
    "金": (
        "仕組み化",
        "品質",
        "品質基準",
        "ルール",
        "精度",
        "チェックリスト",
    ),
    "水": (
        "情報",
        "情報収集",
        "情報循環",
        "ネットワーク",
        "人脈",
    ),
    "木": (
        "学習",
        "企画",
        "成長",
    ),
    "土": (
        "安定",
        "安定運用",
        "運用",
        "段取り",
        "標準化",
    ),
    "火": (
        "表現",
        "行動力",
        "自己主張",
        "勢い",
    ),
}

MAX_ELEMENT_TRANSLATION_SECTIONS = 3

# 「健康」という一般論自体は禁止しない。
# 命式から具体的な身体状態・生活習慣を推測したときに問題となる語。
HEALTH_SPECIFIC_TERMS = (
    "夜更かし",
    "睡眠の質",
    "睡眠不足",
    "呼吸",
    "深呼吸",
    "姿勢",
    "換気",
    "有酸素",
    "血圧",
    "血糖",
    "自律神経",
    "胃腸",
    "肝臓",
    "腎臓",
    "心臓",
    "肺",
    "頭痛",
    "肩こり",
    "冷え",
    "むくみ",
    "不眠",
    "疲労",
)

HEALTH_ASTROLOGY_CAUSAL_RE = re.compile(
    r"(?:"
    r"五行|木|火|土|金|水|"
    r"日主|身強|身弱|用神|喜神|忌神|"
    r"命式|大運|歳運|年運"
    r")"
    r".{0,40}"
    r"(?:"
    + "|".join(
        re.escape(term)
        for term in HEALTH_SPECIFIC_TERMS
    )
    + r")"
)


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


def iter_customer_facing_texts(
    ai_reading: Mapping[str, Any],
) -> tuple[CustomerFacingText, ...]:
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

        base_path = f"sections.{section_name}"

        for field_name in CUSTOMER_SECTION_TEXT_FIELDS:
            text = _normalize_text(
                section_value.get(field_name)
            )

            if not text:
                continue

            results.append(
                CustomerFacingText(
                    path=f"{base_path}.{field_name}",
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

        # -------------------------------------------------
        # future_flow.yearly
        # -------------------------------------------------
        #
        # 5年運の年別文章も、通常セクションと同じ
        # 顧客向け品質ゲートへ流す。
        #
        # year は計算済みの構造データなので、
        # CustomerFacingText には含めない。
        #
        # パスは必ず sections.future_flow... 配下に
        # 維持する。これにより章横断の重複検査では
        # 5年分を5章ではなく future_flow という
        # 1章として扱える。
        if section_name == "future_flow":
            yearly = section_value.get(
                "yearly"
            )

            if (
                isinstance(yearly, Sequence)
                and not isinstance(
                    yearly,
                    (str, bytes, bytearray),
                )
            ):
                for yearly_index, yearly_value in enumerate(
                    yearly
                ):
                    if not isinstance(
                        yearly_value,
                        Mapping,
                    ):
                        continue

                    yearly_base_path = (
                        f"{base_path}."
                        f"yearly[{yearly_index}]"
                    )

                    for field_name in (
                        "title",
                        "summary",
                        "detail",
                    ):
                        yearly_text = _normalize_text(
                            yearly_value.get(
                                field_name
                            )
                        )

                        if not yearly_text:
                            continue

                        results.append(
                            CustomerFacingText(
                                path=(
                                    f"{yearly_base_path}."
                                    f"{field_name}"
                                ),
                                text=yearly_text,
                                kind=field_name,
                            )
                        )

                    for advice_index, advice_text in (
                        _iter_string_list(
                            yearly_value.get(
                                "advice"
                            )
                        )
                    ):
                        results.append(
                            CustomerFacingText(
                                path=(
                                    f"{yearly_base_path}."
                                    f"advice[{advice_index}]"
                                ),
                                text=advice_text,
                                kind="advice",
                            )
                        )

    return tuple(results)


def _section_name_from_path(
    path: str,
) -> str | None:
    match = re.match(
        r"^sections\.([^.]+)\.",
        path,
    )

    if match is None:
        return None

    return match.group(1)


def _section_text_map(
    ai_reading: Mapping[str, Any],
) -> dict[str, list[CustomerFacingText]]:
    result: dict[
        str,
        list[CustomerFacingText],
    ] = {}

    for item in iter_customer_facing_texts(
        ai_reading
    ):
        section_name = (
            _section_name_from_path(
                item.path
            )
        )

        if section_name is None:
            continue

        result.setdefault(
            section_name,
            [],
        ).append(item)

    return result


def find_internal_label_leaks(
    ai_reading: Mapping[str, Any],
) -> tuple[QualityIssue, ...]:
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


def find_internal_key_leaks(
    ai_reading: Mapping[str, Any],
) -> tuple[QualityIssue, ...]:
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


def find_overconfident_claims(
    ai_reading: Mapping[str, Any],
) -> tuple[QualityIssue, ...]:
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


def _collect_numeric_strings(
    value: Any,
) -> set[str]:
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



def _normalize_repetition_text(
    value: Any,
) -> str:
    """
    重複比較専用の軽い正規化。

    意味解析やAI判定は行わず、
    空白・句読点など表記差だけを吸収する。
    """

    text = _normalize_text(
        value
    )

    if not text:
        return ""

    return re.sub(
        r"[\s\u3000、。,.・!！?？"
        r"「」『』（）()【】［］\[\]"
        r"：:；;／/・\-―—～〜~]+",
        "",
        text,
    ).lower()


def _sentence_chunks(
    value: Any,
) -> tuple[str, ...]:
    """
    同一フィールド内の明確な文反復検出用。

    短すぎる断片は対象外とする。
    """

    text = _normalize_text(
        value
    )

    if not text:
        return ()

    raw_chunks = re.split(
        r"[。！？!?\n]+",
        text,
    )

    chunks = []

    for raw in raw_chunks:
        normalized = (
            _normalize_repetition_text(
                raw
            )
        )

        if len(normalized) < 10:
            continue

        chunks.append(
            normalized
        )

    return tuple(chunks)


def _substantial_overlap(
    first: Any,
    second: Any,
    *,
    min_chars: int = 18,
) -> bool:
    """
    一方の文章がもう一方へほぼ丸ごと含まれる
    明確な重複だけを検出する。

    キーワード共有だけではTrueにしない。
    """

    left = _normalize_repetition_text(
        first
    )
    right = _normalize_repetition_text(
        second
    )

    if (
        len(left) < min_chars
        or len(right) < min_chars
    ):
        return False

    if left == right:
        return True

    shorter, longer = (
        (left, right)
        if len(left) <= len(right)
        else (right, left)
    )

    return shorter in longer


def _section_customer_items(
    ai_reading: Mapping[str, Any],
    section_name: str,
) -> tuple[CustomerFacingText, ...]:
    return tuple(
        item
        for item in iter_customer_facing_texts(
            ai_reading
        )
        if (
            _section_name_from_path(
                item.path
            )
            == section_name
        )
    )



def _non_yearly_customer_texts_by_section(
    ai_reading: Mapping[str, Any],
) -> dict[str, tuple[CustomerFacingText, ...]]:
    """
    通常セクション本文を章単位で返す。

    future_flow.yearly は別の専用検査で扱う。
    titleは文体反復検査から除外する。
    """

    result: dict[
        str,
        list[CustomerFacingText],
    ] = {}

    for item in iter_customer_facing_texts(
        ai_reading
    ):
        if (
            not item.path.startswith(
                "sections."
            )
            or item.kind == "title"
            or ".yearly["
            in item.path
        ):
            continue

        section_name = (
            _section_name_from_path(
                item.path
            )
        )

        if not section_name:
            continue

        result.setdefault(
            section_name,
            [],
        ).append(
            item
        )

    return {
        section_name: tuple(items)
        for section_name, items
        in result.items()
    }


def find_formulaic_phrase_overuse(
    ai_reading: Mapping[str, Any],
    *,
    min_sections: int = (
        FORMULAIC_STYLE_MIN_SECTIONS
    ),
) -> tuple[QualityIssue, ...]:
    """
    AI鑑定で使い回されやすい定型表現が、
    多数の章にまたがって反復された場合に検出する。

    2～3章程度の自然な共有は許容する。
    """

    if (
        not isinstance(
            min_sections,
            int,
        )
        or isinstance(
            min_sections,
            bool,
        )
        or min_sections < 2
    ):
        raise ValueError(
            "min_sectionsは2以上のint"
            "である必要があります。"
        )

    section_map = (
        _non_yearly_customer_texts_by_section(
            ai_reading
        )
    )

    issues: list[
        QualityIssue
    ] = []

    for label, pattern in (
        FORMULAIC_STYLE_PATTERNS
    ):
        matched_sections: list[
            str
        ] = []

        for section_name, items in (
            section_map.items()
        ):
            if any(
                pattern.search(
                    item.text
                )
                is not None
                for item in items
            ):
                matched_sections.append(
                    section_name
                )

        if (
            len(
                matched_sections
            )
            < min_sections
        ):
            continue

        issues.append(
            QualityIssue(
                code=(
                    "formulaic_phrase_overuse"
                ),
                message=(
                    "同じ説明の定型表現が"
                    "多数のセクションで"
                    "繰り返されています。"
                ),
                path="sections",
                value=", ".join(
                    matched_sections
                ),
                matched=label,
            )
        )

    return tuple(
        issues
    )


def find_sentence_ending_overuse(
    ai_reading: Mapping[str, Any],
) -> tuple[QualityIssue, ...]:
    """
    同じ説明語尾が多数章で続く場合を検出する。

    一般的な「です・ます」や、
    adviceの「してください・しましょう」は
    対象にしない。
    """

    section_map = (
        _non_yearly_customer_texts_by_section(
            ai_reading
        )
    )

    issues: list[
        QualityIssue
    ] = []

    for label, pattern, min_sections in (
        SENTENCE_ENDING_STYLE_PATTERNS
    ):
        matched_sections: list[
            str
        ] = []

        for section_name, items in (
            section_map.items()
        ):
            # 語尾の単調さは主に説明本文で評価する。
            #
            # evidence は「〜と読みます」等の根拠説明が
            # 自然に反復しやすく、advice も丁寧語が
            # 繰り返されやすいため、sentence-ending
            # overuse の集計対象からは除外する。
            explanatory_items = (
                item
                for item in items
                if item.kind
                in {
                    "summary",
                    "detail",
                }
            )

            if any(
                pattern.search(
                    item.text
                )
                is not None
                for item in explanatory_items
            ):
                matched_sections.append(
                    section_name
                )

        if (
            len(
                matched_sections
            )
            < min_sections
        ):
            continue

        issues.append(
            QualityIssue(
                code=(
                    "sentence_ending_overuse"
                ),
                message=(
                    "同じ説明語尾が多数の"
                    "セクションで続いており、"
                    "文章が定型的に見えます。"
                ),
                path="sections",
                value=", ".join(
                    matched_sections
                ),
                matched=label,
            )
        )

    return tuple(
        issues
    )


def _future_flow_yearly_mappings(
    ai_reading: Mapping[str, Any],
) -> tuple[Mapping[str, Any], ...]:
    reading = _require_mapping(
        ai_reading,
        name="ai_reading",
    )

    sections = reading.get(
        "sections"
    )

    if not isinstance(
        sections,
        Mapping,
    ):
        return ()

    future_flow = sections.get(
        "future_flow"
    )

    if not isinstance(
        future_flow,
        Mapping,
    ):
        return ()

    yearly = future_flow.get(
        "yearly"
    )

    if not (
        isinstance(
            yearly,
            Sequence,
        )
        and not isinstance(
            yearly,
            (
                str,
                bytes,
                bytearray,
            ),
        )
    ):
        return ()

    return tuple(
        item
        for item in yearly
        if isinstance(
            item,
            Mapping,
        )
    )


def find_future_flow_style_repetition(
    ai_reading: Mapping[str, Any],
    *,
    min_years: int = (
        FUTURE_FLOW_STYLE_MIN_YEARS
    ),
) -> tuple[QualityIssue, ...]:
    """
    future_flow.yearly の年別文章で、
    同じ定型表現・説明語尾を
    4年以上にわたって使い回した場合に検出する。

    titleは対象外。
    adviceの一般的な命令語尾も対象外。
    """

    if (
        not isinstance(
            min_years,
            int,
        )
        or isinstance(
            min_years,
            bool,
        )
        or min_years < 2
    ):
        raise ValueError(
            "min_yearsは2以上のint"
            "である必要があります。"
        )

    yearly = (
        _future_flow_yearly_mappings(
            ai_reading
        )
    )

    if not yearly:
        return ()

    # 年ごとに summary / detail だけを対象にする。
    # adviceは「してください」等が自然に続くため除外。
    yearly_texts: list[
        str
    ] = []

    for item in yearly:
        yearly_texts.append(
            " ".join(
                value
                for value in (
                    _normalize_text(
                        item.get(
                            "summary"
                        )
                    ),
                    _normalize_text(
                        item.get(
                            "detail"
                        )
                    ),
                )
                if value
            )
        )

    style_patterns = tuple(
        (
            label,
            pattern,
        )
        for label, pattern in (
            FORMULAIC_STYLE_PATTERNS
        )
    ) + tuple(
        (
            label,
            pattern,
        )
        for (
            label,
            pattern,
            _min_sections,
        ) in (
            SENTENCE_ENDING_STYLE_PATTERNS
        )
    )

    issues: list[
        QualityIssue
    ] = []

    for label, pattern in (
        style_patterns
    ):
        matched_indexes = [
            index
            for index, text
            in enumerate(
                yearly_texts
            )
            if (
                text
                and pattern.search(
                    text
                )
                is not None
            )
        ]

        if (
            len(
                matched_indexes
            )
            < min_years
        ):
            continue

        matched_years: list[
            str
        ] = []

        for index in matched_indexes:
            raw_year = yearly[
                index
            ].get(
                "year"
            )

            year_text = (
                _normalize_text(
                    raw_year
                )
                or str(
                    index
                )
            )

            matched_years.append(
                year_text
            )

        issues.append(
            QualityIssue(
                code=(
                    "future_flow_style_repetition"
                ),
                message=(
                    "5年運の複数年で"
                    "同じ説明の型が"
                    "繰り返されています。"
                ),
                path=(
                    "sections.future_flow"
                ),
                value=", ".join(
                    matched_years
                ),
                matched=label,
            )
        )

    return tuple(
        issues
    )



def _extract_useful_gods_role_data(
    reading_context: Mapping[str, Any] | None,
) -> tuple[str | None, tuple[str, ...]]:
    """
    reading_contextから主用神と補助用神を取り出す。
    """

    if not isinstance(
        reading_context,
        Mapping,
    ):
        return (None, ())

    useful_gods = reading_context.get(
        "useful_gods"
    )

    if not isinstance(
        useful_gods,
        Mapping,
    ):
        return (None, ())

    primary_raw = useful_gods.get(
        "primary_useful_element"
    )

    if (
        not isinstance(primary_raw, str)
        or not primary_raw.strip()
    ):
        return (None, ())

    primary = primary_raw.strip()

    secondary_raw = useful_gods.get(
        "secondary_useful_elements"
    )

    secondary: list[str] = []

    if (
        isinstance(
            secondary_raw,
            Sequence,
        )
        and not isinstance(
            secondary_raw,
            (str, bytes, bytearray),
        )
    ):
        for value in secondary_raw:
            if (
                isinstance(value, str)
                and value.strip()
                and value.strip() != primary
            ):
                normalized = value.strip()

                if normalized not in secondary:
                    secondary.append(
                        normalized
                    )

    return (
        primary,
        tuple(secondary),
    )


def _useful_gods_sentence_chunks(
    text: str,
) -> tuple[str, ...]:
    """
    用神役割判定用に文章を文単位へ分ける。
    """

    normalized = _normalize_text(
        text
    )

    if not normalized:
        return ()

    chunks = [
        chunk.strip()
        for chunk in re.split(
            r"(?<=[。！？!?])|[\n\r]+",
            normalized,
        )
        if chunk.strip()
    ]

    return tuple(chunks)


def _chunk_has_explicit_secondary_role(
    chunk: str,
) -> bool:
    """
    同一文内で補助側の役割が明示されているか。
    """

    return any(
        marker in chunk
        for marker in (
            "補助",
            "補助用神",
            "副用神",
            "サポート",
        )
    )

def _chunk_has_explicit_secondary_role(
    chunk: str,
) -> bool:
    """
    同一文中で補助側の役割が明示されているか。
    """

    return any(
        marker in chunk
        for marker in (
            "補助",
            "補助用神",
            "副用神",
            "サポート",
        )
    )


def _chunk_has_explicit_primary_role(
    chunk: str,
    *,
    primary: str,
) -> bool:
    """
    同一文中で主用神が明示されているか。

    例:
    - 主用神は土
    - 主用神が土
    - 主用神として土
    - 主用神である土
    - 土が主用神
    - 土は主用神
    - 土を主用神とする
    """

    if not primary:
        return False

    patterns = (
        f"主用神は{primary}",
        f"主用神が{primary}",
        f"主用神として{primary}",
        f"主用神である{primary}",
        f"主用神の{primary}",
        f"{primary}が主用神",
        f"{primary}は主用神",
        f"{primary}を主用神",
        f"{primary}を主用神と",
    )

    return any(
        pattern in chunk
        for pattern in patterns
    )


def _find_confused_useful_god_chunk(
    text: str,
    *,
    primary: str,
    secondary: Sequence[str],
) -> str | None:
    """
    主用神と補助用神を同格の「用神」として
    表現している文を返す。

    誤検出防止:
    - 「金銭」「金運」などの一般語中の「金」は
      五行の金として扱わない。
    - 「水（大運）」「火（年運）」など、
      他の占術情報として五行が同一文中に登場しても、
      主用神が明示されている場合は、
      それだけでは役割混同と判定しない。

    一方で、
    - 「金は用神」
    - 「用神は金」
    などの直接的な誤表現は引き続き検出する。
    """

    all_elements = (
        "木",
        "火",
        "土",
        "金",
        "水",
    )

    secondary_set = set(
        secondary
    )

    # --------------------------------------------------------
    # 五行文字と衝突しやすい一般語
    # --------------------------------------------------------

    element_false_positive_terms = {
        "木": (
            "木曜日",
            "木材",
            "樹木",
            "草木",
        ),
        "火": (
            "火曜日",
            "火災",
            "火事",
        ),
        "土": (
            "土曜日",
            "土地",
            "国土",
            "土台",
        ),
        "金": (
            "金曜日",
            "金銭",
            "金運",
            "金額",
            "資金",
            "現金",
            "貯金",
            "預金",
            "年金",
            "税金",
            "料金",
            "賃金",
            "借金",
            "お金",
        ),
        "水": (
            "水曜日",
            "水分",
            "水準",
            "水面",
        ),
    }

    def has_element_reference(
        chunk: str,
        element: str,
    ) -> bool:
        """
        chunk内のelementが一般語の一部ではなく、
        五行として現れている可能性があるか判定する。
        """

        if element not in chunk:
            return False

        masked = chunk

        for term in (
            element_false_positive_terms.get(
                element,
                ()
            )
        ):
            masked = masked.replace(
                term,
                ""
            )

        return element in masked

    for chunk in _useful_gods_sentence_chunks(
        text
    ):
        # 用神について述べていない文は対象外。
        if "用神" not in chunk:
            continue

        # ----------------------------------------------------
        # 補助用神・副用神などと明示されている場合、
        # 主用神との役割差が表現されている。
        # ----------------------------------------------------

        if _chunk_has_explicit_secondary_role(
            chunk
        ):
            continue

        # ----------------------------------------------------
        # 一般語を除外したうえで、
        # 同一文に登場する五行を抽出する。
        # ----------------------------------------------------

        mentioned_elements = {
            element
            for element in all_elements
            if has_element_reference(
                chunk,
                element,
            )
        }

        non_primary = (
            mentioned_elements
            - {primary}
        )

        # ----------------------------------------------------
        # 主用神が明示されているか。
        #
        # 例:
        #
        # 水（大運）と火（年運）の要素が
        # せめぎ合うため、
        # 主用神である土を丁寧に置く。
        #
        # この場合、水・火は用神ではなく
        # 大運・年運の説明なので、
        # broad checkではNGにしない。
        # ----------------------------------------------------

        explicit_primary_role = (
            _chunk_has_explicit_primary_role(
                chunk,
                primary=primary,
            )
        )

        if (
            non_primary
            and not explicit_primary_role
        ):
            if (
                not secondary_set
                or non_primary
                & secondary_set
            ):
                return chunk

        # ----------------------------------------------------
        # 直接的な役割混同は、
        # 主用神が明示されていても検出する。
        #
        # 例:
        # 「主用神は土ですが、金も用神です」
        # ----------------------------------------------------

        for element in all_elements:
            if element == primary:
                continue

            direct_patterns = (
                f"{element}が用神",
                f"{element}は用神",
                f"{element}を用神",
                f"用神は{element}",
                f"用神が{element}",
                f"用神として{element}",
                f"用神（{element}",
                f"用神({element}",
                f"用神の{element}",
            )

            if any(
                pattern in chunk
                for pattern in direct_patterns
            ):
                return chunk

    return None


def find_useful_gods_role_confusion(
    ai_reading: Mapping[str, Any],
    *,
    reading_context: Mapping[str, Any] | None = None,
) -> tuple[QualityIssue, ...]:
    """
    主用神と補助用神の役割混同を検出する。

    primary_useful_element を主用神、
    secondary_useful_elements を補助用神として扱う。
    """

    _require_mapping(
        ai_reading,
        name="ai_reading",
    )

    primary, secondary = (
        _extract_useful_gods_role_data(
            reading_context
        )
    )

    if primary is None:
        return ()

    issues: list[QualityIssue] = []

    for item in iter_customer_facing_texts(
        ai_reading
    ):
        matched_chunk = (
            _find_confused_useful_god_chunk(
                item.text,
                primary=primary,
                secondary=secondary,
            )
        )

        if matched_chunk is None:
            continue

        issues.append(
            QualityIssue(
                code=(
                    "useful_gods_role_confusion"
                ),
                message=(
                    "主用神と補助用神が"
                    "同格の用神として"
                    "表現されています。"
                ),
                path=item.path,
                value=item.text,
                matched=matched_chunk,
            )
        )

    return tuple(
        issues
    )


def find_summary_detail_repetition(
    ai_reading: Mapping[str, Any],
) -> tuple[QualityIssue, ...]:
    """
    同一セクションのsummaryとdetailが
    ほぼ同文になっている場合を検出する。
    """

    reading = _require_mapping(
        ai_reading,
        name="ai_reading",
    )

    sections = reading.get(
        "sections"
    )

    if not isinstance(
        sections,
        Mapping,
    ):
        return ()

    issues: list[QualityIssue] = []

    for section_name, section in (
        sections.items()
    ):
        if (
            not isinstance(
                section_name,
                str,
            )
            or not isinstance(
                section,
                Mapping,
            )
        ):
            continue

        summary = section.get(
            "summary"
        )
        detail = section.get(
            "detail"
        )

        if not _substantial_overlap(
            summary,
            detail,
        ):
            continue

        issues.append(
            QualityIssue(
                code=(
                    "summary_detail_repetition"
                ),
                message=(
                    "要約と詳細本文の内容が"
                    "過度に重複しています。"
                ),
                path=(
                    f"sections.{section_name}"
                ),
                value=(
                    f"summary={_normalize_text(summary)!r}; "
                    f"detail={_normalize_text(detail)!r}"
                ),
                matched=(
                    _normalize_text(
                        summary
                    )
                ),
            )
        )

    return tuple(
        issues
    )


def find_within_section_text_repetition(
    ai_reading: Mapping[str, Any],
) -> tuple[QualityIssue, ...]:
    """
    同一セクション内の明確な文章コピーを検出する。

    - 同じフィールド内で同一文が2回以上
    - detail / adviceなど異なるフィールド間で
      長文がほぼ同一

    titleは対象外。
    future_flow.yearly固有の重複は別検査へ任せる。
    """

    issues: list[QualityIssue] = []
    section_map = _section_text_map(
        ai_reading
    )

    for section_name, items in (
        section_map.items()
    ):
        ordinary_items = [
            item
            for item in items
            if (
                item.kind != "title"
                and ".yearly["
                not in item.path
            )
        ]

        detected = False

        # 1フィールド内の同一文反復
        for item in ordinary_items:
            chunks = _sentence_chunks(
                item.text
            )

            if (
                len(chunks)
                != len(set(chunks))
            ):
                issues.append(
                    QualityIssue(
                        code=(
                            "within_section_text_repetition"
                        ),
                        message=(
                            "同一セクション内で"
                            "同じ文章が繰り返されています。"
                        ),
                        path=(
                            f"sections.{section_name}"
                        ),
                        value=item.text,
                        matched=next(
                            (
                                chunk
                                for chunk
                                in chunks
                                if chunks.count(
                                    chunk
                                ) > 1
                            ),
                            None,
                        ),
                    )
                )
                detected = True
                break

        if detected:
            continue

        # 異なるフィールド間のコピー
        for left_index, left in enumerate(
            ordinary_items
        ):
            for right in ordinary_items[
                left_index + 1:
            ]:
                # summary-detail は専用issueへ任せる
                if {
                    left.kind,
                    right.kind,
                } == {
                    "summary",
                    "detail",
                }:
                    continue

                if not _substantial_overlap(
                    left.text,
                    right.text,
                ):
                    continue

                issues.append(
                    QualityIssue(
                        code=(
                            "within_section_text_repetition"
                        ),
                        message=(
                            "同一セクション内の"
                            "複数フィールドで文章が"
                            "過度に重複しています。"
                        ),
                        path=(
                            f"sections.{section_name}"
                        ),
                        value=(
                            f"{left.path}: {left.text} | "
                            f"{right.path}: {right.text}"
                        ),
                        matched=(
                            left.text
                            if len(
                                _normalize_repetition_text(
                                    left.text
                                )
                            )
                            <= len(
                                _normalize_repetition_text(
                                    right.text
                                )
                            )
                            else right.text
                        ),
                    )
                )
                detected = True
                break

            if detected:
                break

    return tuple(
        issues
    )


def find_cross_section_phrase_repetition(
    ai_reading: Mapping[str, Any],
    *,
    min_sections: int = 3,
) -> tuple[QualityIssue, ...]:
    """
    3章以上で同一の長い文章が使い回された場合を検出する。

    2章程度の自然な重なりは許容する。
    """

    if (
        not isinstance(
            min_sections,
            int,
        )
        or isinstance(
            min_sections,
            bool,
        )
        or min_sections < 3
    ):
        raise ValueError(
            "min_sectionsは3以上のint"
            "である必要があります。"
        )

    section_map = _section_text_map(
        ai_reading
    )

    phrase_sections: dict[
        str,
        set[str],
    ] = {}

    phrase_original: dict[
        str,
        str,
    ] = {}

    for section_name, items in (
        section_map.items()
    ):
        for item in items:
            if (
                item.kind == "title"
                or ".yearly["
                in item.path
            ):
                continue

            normalized = (
                _normalize_repetition_text(
                    item.text
                )
            )

            if len(normalized) < 18:
                continue

            phrase_sections.setdefault(
                normalized,
                set(),
            ).add(
                section_name
            )

            phrase_original.setdefault(
                normalized,
                item.text,
            )

    issues: list[QualityIssue] = []

    for normalized, matched_sections in (
        phrase_sections.items()
    ):
        if (
            len(matched_sections)
            < min_sections
        ):
            continue

        issues.append(
            QualityIssue(
                code=(
                    "cross_section_phrase_repetition"
                ),
                message=(
                    "同じ長い文章が複数の"
                    "セクションで使い回されています。"
                ),
                path="sections",
                value=", ".join(
                    sorted(
                        matched_sections
                    )
                ),
                matched=(
                    phrase_original[
                        normalized
                    ]
                ),
            )
        )

    return tuple(
        issues
    )


def find_future_flow_yearly_repetition(
    ai_reading: Mapping[str, Any],
) -> tuple[QualityIssue, ...]:
    """
    future_flow総括とyearlyのコピー、
    または複数年で同じ年別本文を
    使い回しているケースを検出する。

    年別titleはテーマ名なので対象外。
    """

    reading = _require_mapping(
        ai_reading,
        name="ai_reading",
    )

    sections = reading.get(
        "sections"
    )

    if not isinstance(
        sections,
        Mapping,
    ):
        return ()

    future_flow = sections.get(
        "future_flow"
    )

    if not isinstance(
        future_flow,
        Mapping,
    ):
        return ()

    yearly = future_flow.get(
        "yearly"
    )

    if not (
        isinstance(
            yearly,
            Sequence,
        )
        and not isinstance(
            yearly,
            (str, bytes, bytearray),
        )
    ):
        return ()

    yearly_items = [
        item
        for item in yearly
        if isinstance(
            item,
            Mapping,
        )
    ]

    issues: list[QualityIssue] = []

    overview_texts = [
        future_flow.get(
            "summary"
        ),
        future_flow.get(
            "detail"
        ),
    ]

    for overview in overview_texts:
        if not _normalize_text(
            overview
        ):
            continue

        found = False

        for yearly_item in yearly_items:
            for field_name in (
                "summary",
                "detail",
            ):
                if not _substantial_overlap(
                    overview,
                    yearly_item.get(
                        field_name
                    ),
                ):
                    continue

                issues.append(
                    QualityIssue(
                        code=(
                            "future_flow_yearly_repetition"
                        ),
                        message=(
                            "5年間の総括と年別本文が"
                            "過度に重複しています。"
                        ),
                        path=(
                            "sections.future_flow"
                        ),
                        value=(
                            _normalize_text(
                                overview
                            )
                        ),
                        matched=(
                            _normalize_text(
                                yearly_item.get(
                                    field_name
                                )
                            )
                        ),
                    )
                )
                found = True
                break

            if found:
                break

        if found:
            return tuple(
                issues
            )

    # 複数年で同一本文を3回以上使い回すケース
    for field_name in (
        "summary",
        "detail",
    ):
        occurrences: dict[
            str,
            list[int],
        ] = {}

        originals: dict[
            str,
            str,
        ] = {}

        for index, yearly_item in enumerate(
            yearly_items
        ):
            raw = yearly_item.get(
                field_name
            )
            normalized = (
                _normalize_repetition_text(
                    raw
                )
            )

            if len(normalized) < 18:
                continue

            occurrences.setdefault(
                normalized,
                [],
            ).append(
                index
            )

            originals.setdefault(
                normalized,
                _normalize_text(
                    raw
                ),
            )

        for normalized, indexes in (
            occurrences.items()
        ):
            if len(indexes) < 3:
                continue

            issues.append(
                QualityIssue(
                    code=(
                        "future_flow_yearly_repetition"
                    ),
                    message=(
                        "複数年で同じ年別本文が"
                        "使い回されています。"
                    ),
                    path=(
                        "sections.future_flow"
                    ),
                    value=(
                        ",".join(
                            str(
                                index
                            )
                            for index
                            in indexes
                        )
                    ),
                    matched=(
                        originals[
                            normalized
                        ]
                    ),
                )
            )

            return tuple(
                issues
            )

    return tuple(
        issues
    )


def find_repeated_advice_concepts(
    ai_reading: Mapping[str, Any],
    *,
    max_sections: int = MAX_ADVICE_CONCEPT_SECTIONS,
) -> tuple[QualityIssue, ...]:
    """
    同じ助言概念が多数の章で繰り返される場合に検出する。

    単語の出現回数ではなく「何章にまたがるか」で判定する。
    同一章内の自然な反復はここでは問題にしない。
    """

    if (
        not isinstance(max_sections, int)
        or isinstance(max_sections, bool)
        or max_sections < 1
    ):
        raise ValueError(
            "max_sectionsは1以上のintである必要があります。"
        )

    section_map = _section_text_map(
        ai_reading
    )

    issues: list[QualityIssue] = []

    for concept in REPEATED_ADVICE_CONCEPTS:
        matched_sections: list[str] = []

        for section_name, items in (
            section_map.items()
        ):
            combined = " ".join(
                item.text
                for item in items
                if item.kind != "title"
            )

            if concept in combined:
                matched_sections.append(
                    section_name
                )

        if len(matched_sections) <= max_sections:
            continue

        issues.append(
            QualityIssue(
                code="cross_section_advice_repetition",
                message=(
                    "同じ助言概念が多くのセクションで"
                    "繰り返されています。"
                ),
                path="sections",
                value=", ".join(
                    matched_sections
                ),
                matched=concept,
            )
        )

    return tuple(issues)


def find_fixed_element_translation_overuse(
    ai_reading: Mapping[str, Any],
    *,
    max_sections: int = MAX_ELEMENT_TRANSLATION_SECTIONS,
) -> tuple[QualityIssue, ...]:
    """
    同じ五行を同じ現代語へ固定変換し、
    多数章で反復している場合に検出する。

    例:
        金 → 仕組み化
        水 → 情報収集
    """

    if (
        not isinstance(max_sections, int)
        or isinstance(max_sections, bool)
        or max_sections < 1
    ):
        raise ValueError(
            "max_sectionsは1以上のintである必要があります。"
        )

    section_map = _section_text_map(
        ai_reading
    )

    issues: list[QualityIssue] = []

    for element, translations in (
        ELEMENT_TRANSLATIONS.items()
    ):
        for translation in translations:
            matched_sections: list[str] = []

            for section_name, items in (
                section_map.items()
            ):
                combined = " ".join(
                    item.text
                    for item in items
                    if item.kind != "title"
                )

                if (
                    element in combined
                    and translation in combined
                ):
                    matched_sections.append(
                        section_name
                    )

            if (
                len(matched_sections)
                <= max_sections
            ):
                continue

            issues.append(
                QualityIssue(
                    code="fixed_element_translation_overuse",
                    message=(
                        "同じ五行が同じ現代語へ"
                        "固定的に変換され、多数章で"
                        "繰り返されています。"
                    ),
                    path="sections",
                    value=", ".join(
                        matched_sections
                    ),
                    matched=(
                        f"{element}→{translation}"
                    ),
                )
            )

    return tuple(issues)


def find_health_specific_overreach(
    ai_reading: Mapping[str, Any],
) -> tuple[QualityIssue, ...]:
    """
    health章で、命式・五行などを根拠として
    具体的な症状・身体状態・生活習慣を
    推測している文章を検出する。

    「医学的診断ではありません」等の免責そのものは
    問題にしない。
    """

    issues: list[QualityIssue] = []

    for item in iter_customer_facing_texts(
        ai_reading
    ):
        if not item.path.startswith(
            "sections.health."
        ):
            continue

        match = HEALTH_ASTROLOGY_CAUSAL_RE.search(
            item.text
        )

        if match is None:
            continue

        matched_term = next(
            (
                term
                for term in HEALTH_SPECIFIC_TERMS
                if term in match.group(0)
            ),
            match.group(0),
        )

        issues.append(
            QualityIssue(
                code="health_astrology_specific_overreach",
                message=(
                    "健康章で、命式・五行などから"
                    "具体的な身体状態または生活習慣を"
                    "直接推測しています。"
                ),
                path=item.path,
                value=item.text,
                matched=matched_term,
            )
        )

    return tuple(issues)


def validate_disclaimer(
    ai_reading: Mapping[str, Any],
) -> tuple[QualityIssue, ...]:
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


def validate_customer_facing_reading(
    ai_reading: Mapping[str, Any],
    *,
    reading_context: Mapping[str, Any] | None = None,
    consultation_context: Mapping[str, Any] | None = None,
) -> ReadingQualityReport:
    """
    顧客向けAI鑑定の最終品質検査。

    v1の安全・内部表現検査に加えて、
    v2の顧客価値検査も行う。

    文章の書き換えや命式の再計算はしない。
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

    # v2 customer-value checks
    issues.extend(
        find_health_specific_overreach(
            ai_reading
        )
    )

    # v1販売版の文章重複チェック。
    #
    # すべてwarning扱いとし、
    # 単独ではPDF生成を停止しない。
    issues.extend(
        find_summary_detail_repetition(
            ai_reading
        )
    )

    issues.extend(
        find_within_section_text_repetition(
            ai_reading
        )
    )

    issues.extend(
        find_cross_section_phrase_repetition(
            ai_reading
        )
    )

    issues.extend(
        find_future_flow_yearly_repetition(
            ai_reading
        )
    )

    # 販売版v1の文体品質チェック。
    #
    # 同じAI的な言い回し・説明語尾の
    # 過剰反復をwarningとして報告する。
    # 単独ではPDF生成を停止しない。
    issues.extend(
        find_formulaic_phrase_overuse(
            ai_reading
        )
    )

    issues.extend(
        find_sentence_ending_overuse(
            ai_reading
        )
    )

    issues.extend(
        find_future_flow_style_repetition(
            ai_reading
        )
    )

    # 用神と補助用神の役割整合性。
    # 計算済みreading_contextを正として、
    # 顧客向け文章の混同だけをwarningにする。
    issues.extend(
        find_useful_gods_role_confusion(
            ai_reading,
            reading_context=reading_context,
        )
    )

    issues.extend(
        find_repeated_advice_concepts(
            ai_reading
        )
    )

    issues.extend(
        find_fixed_element_translation_overuse(
            ai_reading
        )
    )

    issue_tuple = tuple(
        issues
    )

    has_error = any(
        issue_severity(issue)
        == "error"
        for issue in issue_tuple
    )

    return ReadingQualityReport(
        valid=not has_error,
        issues=issue_tuple,
    )


def ensure_customer_facing_reading_quality(
    ai_reading: Mapping[str, Any],
    *,
    reading_context: Mapping[str, Any] | None = None,
    consultation_context: Mapping[str, Any] | None = None,
) -> ReadingQualityReport:
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
        f"error_count={report.error_count}",
        f"warning_count={report.warning_count}",
    ]

    for issue in report.issues:
        matched = (
            f" matched={issue.matched!r}"
            if issue.matched is not None
            else ""
        )

        severity = (
            issue_severity(issue)
            .upper()
        )

        lines.append(
            f"- [{severity}] "
            f"[{issue.code}] "
            f"{issue.path}: "
            f"{issue.message}"
            f"{matched}"
        )

    raise ReadingQualityError(
        "\n".join(lines)
    )


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
    "CUSTOMER_VALUE_QUALITY_VERSION",
    "WARNING_ISSUE_CODES",
    "ReadingQualityError",
    "QualityIssue",
    "ReadingQualityReport",
    "CustomerFacingText",
    "issue_severity",
    "iter_customer_facing_texts",
    "find_internal_label_leaks",
    "find_internal_key_leaks",
    "find_overconfident_claims",
    "find_unsupported_numeric_claims",
    "find_summary_detail_repetition",
    "find_within_section_text_repetition",
    "find_cross_section_phrase_repetition",
    "find_future_flow_yearly_repetition",
    "find_formulaic_phrase_overuse",
    "find_sentence_ending_overuse",
    "find_future_flow_style_repetition",
    "find_useful_gods_role_confusion",
    "find_repeated_advice_concepts",
    "find_fixed_element_translation_overuse",
    "find_health_specific_overreach",
    "validate_disclaimer",
    "validate_customer_facing_reading",
    "ensure_customer_facing_reading_quality",
    "quality_report_to_json",
]
