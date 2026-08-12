"""
engine/reading_product.py

四柱推命 AI鑑定 商品化レイヤー v1

目的
----
calculate_chart()
    ↓
reading_context_v1
    ↓
reading_generator_v1
    ↓
ReadingGenerationResult
    ↓
reading_product_v1
    ↓
鑑定商品用データ

このモジュールは占術計算を行わず、
既存エンジンが算出・生成した結果を
PDF / HTML / Web / API向けの商品データへ整形する。

Version
-------
reading_product_v1
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from engine.reading_context import (
    READING_SECTION_KEYS,
    build_reading_context,
)
from engine.reading_generator import (
    DEFAULT_MAX_OUTPUT_TOKENS,
    DEFAULT_REASONING_EFFORT,
    DEFAULT_STORE,
    ReadingGenerationResult,
    generate_reading,
)

READING_PRODUCT_VERSION = "reading_product_v1"
READING_PRODUCT_METHOD = "reading_product_v1"
READING_PRODUCT_STATUS = "ready"

DEFAULT_PRODUCT_TITLE = "四柱推命鑑定書"

DEFAULT_DISCLAIMER = (
    "本鑑定は四柱推命の計算結果をもとに、"
    "性質や運勢の傾向を読み解いたものです。"
    "将来を確定的に予言するものではありません。"
    "また、健康に関する内容は医学的診断や"
    "医療上の助言ではありません。"
    "重要な判断については、必要に応じて"
    "各分野の専門家へご相談ください。"
)

SECTION_TITLES: Dict[str, str] = {
    "core_personality": "本質・性格",
    "career": "仕事・適職",
    "wealth": "金運",
    "relationships": "恋愛・人間関係",
    "health": "健康傾向",
    "current_luck": "現在の運勢",
    "future_flow": "今後の流れ",
    "advice": "開運アドバイス",
}

DEFAULT_SECTION_ORDER: Tuple[str, ...] = tuple(
    READING_SECTION_KEYS
)


class ReadingProductError(Exception):
    """reading_product.py の基底例外。"""


class ReadingProductValidationError(
    ReadingProductError
):
    """商品化対象データが不正。"""


def _require_mapping(
    value: Any,
    name: str,
) -> Mapping[str, Any]:
    if not isinstance(
        value,
        Mapping,
    ):
        raise TypeError(
            f"{name}はdict型で指定してください。"
        )
    return value


def _safe_dict(
    value: Any,
) -> Dict[str, Any]:
    if not isinstance(
        value,
        Mapping,
    ):
        return {}
    return deepcopy(
        dict(value)
    )


def _safe_list(
    value: Any,
) -> List[Any]:
    if isinstance(
        value,
        list,
    ):
        return deepcopy(value)
    if isinstance(
        value,
        tuple,
    ):
        return deepcopy(
            list(value)
        )
    return []


def _optional_string(
    value: Any,
) -> Optional[str]:
    if not isinstance(
        value,
        str,
    ):
        return None

    value = value.strip()

    if not value:
        return None

    return value


def _string_or_empty(
    value: Any,
) -> str:
    return (
        _optional_string(
            value
        )
        or ""
    )


def _utc_now_iso() -> str:
    return (
        datetime.now(
            timezone.utc
        )
        .replace(
            microsecond=0
        )
        .isoformat()
    )


def normalize_product_sections(
    sections: Optional[
        Sequence[str]
    ] = None,
) -> Tuple[str, ...]:
    if sections is None:
        return DEFAULT_SECTION_ORDER

    if isinstance(
        sections,
        str,
    ):
        raise TypeError(
            "sectionsは文字列ではなく"
            "文字列の配列で指定してください。"
        )

    if not isinstance(
        sections,
        Sequence,
    ):
        raise TypeError(
            "sectionsは配列で指定してください。"
        )

    normalized: List[str] = []

    for section in sections:
        if not isinstance(
            section,
            str,
        ):
            raise TypeError(
                "sectionsの各要素は"
                "文字列で指定してください。"
            )

        section = section.strip()

        if not section:
            raise ValueError(
                "sectionsに空文字は指定できません。"
            )

        if section not in READING_SECTION_KEYS:
            raise ValueError(
                "未対応の鑑定セクションです: "
                f"{section}"
            )

        if section not in normalized:
            normalized.append(
                section
            )

    if not normalized:
        raise ValueError(
            "sectionsには1件以上指定してください。"
        )

    return tuple(normalized)


@dataclass(frozen=True)
class ReadingProduct:
    title: str
    subject: Dict[str, Any]
    chart_summary: Dict[str, Any]
    sections: Tuple[
        Dict[str, Any],
        ...,
    ]
    summary: str
    disclaimer: str
    generation: Dict[str, Any]
    metadata: Dict[str, Any]
    schema_version: str = (
        READING_PRODUCT_VERSION
    )
    method: str = (
        READING_PRODUCT_METHOD
    )
    status: str = (
        READING_PRODUCT_STATUS
    )

    def to_dict(
        self,
    ) -> Dict[str, Any]:
        return {
            "schema_version": (
                self.schema_version
            ),
            "title": self.title,
            "subject": deepcopy(
                self.subject
            ),
            "chart_summary": deepcopy(
                self.chart_summary
            ),
            "sections": deepcopy(
                list(
                    self.sections
                )
            ),
            "summary": self.summary,
            "disclaimer": (
                self.disclaimer
            ),
            "generation": deepcopy(
                self.generation
            ),
            "metadata": deepcopy(
                self.metadata
            ),
            "method": self.method,
            "status": self.status,
        }


def build_product_subject(
    reading_context: Mapping[
        str,
        Any,
    ],
) -> Dict[str, Any]:
    reading_context = _require_mapping(
        reading_context,
        "reading_context",
    )

    subject = _safe_dict(
        reading_context.get(
            "subject"
        )
    )

    return {
        "birth_date": subject.get(
            "birth_date"
        ),
        "birth_time": subject.get(
            "birth_time"
        ),
        "birth_place": subject.get(
            "birth_place"
        ),
        "gender": subject.get(
            "gender"
        ),
        "timezone": subject.get(
            "timezone"
        ),
    }


def _extract_pillar(
    natal_chart: Mapping[
        str,
        Any,
    ],
    position: str,
) -> Dict[str, Any]:
    pillars = _safe_dict(
        natal_chart.get(
            "pillars"
        )
    )

    pillar = _safe_dict(
        pillars.get(
            position
        )
    )

    return {
        "position": position,
        "pillar": pillar.get(
            "pillar"
        ),
        "stem": pillar.get(
            "stem"
        ),
        "branch": pillar.get(
            "branch"
        ),
        "stem_ten_god": pillar.get(
            "stem_ten_god"
        ),
        "twelve_stage": pillar.get(
            "twelve_stage"
        ),
        "main_hidden_stem": pillar.get(
            "main_hidden_stem"
        ),
        "main_hidden_stem_ten_god": (
            pillar.get(
                "main_hidden_stem_ten_god"
            )
        ),
    }


def build_chart_summary(
    reading_context: Mapping[
        str,
        Any,
    ],
) -> Dict[str, Any]:
    reading_context = _require_mapping(
        reading_context,
        "reading_context",
    )

    natal_chart = _safe_dict(
        reading_context.get(
            "natal_chart"
        )
    )
    day_master = _safe_dict(
        reading_context.get(
            "day_master"
        )
    )
    five_elements = _safe_dict(
        reading_context.get(
            "five_elements"
        )
    )
    strength = _safe_dict(
        reading_context.get(
            "strength"
        )
    )
    pattern = _safe_dict(
        reading_context.get(
            "pattern"
        )
    )
    useful_gods = _safe_dict(
        reading_context.get(
            "useful_gods"
        )
    )
    luck = _safe_dict(
        reading_context.get(
            "luck"
        )
    )
    annual_luck = _safe_dict(
        luck.get(
            "annual_luck"
        )
    )
    current_luck = _safe_dict(
        luck.get(
            "current_luck"
        )
    )
    current_pillar = _safe_dict(
        current_luck.get(
            "current_pillar"
        )
    )

    pillars = {
        position: _extract_pillar(
            natal_chart,
            position,
        )
        for position
        in (
            "year",
            "month",
            "day",
            "hour",
        )
    }

    return {
        "pillars": pillars,
        "pillar_sequence": _safe_list(
            natal_chart.get(
                "pillar_sequence"
            )
        ),
        "day_master": {
            "stem": day_master.get(
                "stem"
            ),
            "element": day_master.get(
                "element"
            ),
            "yin_yang": day_master.get(
                "yin_yang"
            ),
            "day_pillar": day_master.get(
                "day_pillar"
            ),
        },
        "five_elements": {
            "weighted_scores": _safe_dict(
                five_elements.get(
                    "weighted_scores"
                )
            ),
            "strongest_element": (
                five_elements.get(
                    "strongest_element"
                )
            ),
            "weakest_element": (
                five_elements.get(
                    "weakest_element"
                )
            ),
        },
        "strength": {
            "technical_label": (
                strength.get(
                    "technical_label"
                )
            ),
            "label": strength.get(
                "label"
            ),
            "final_score": strength.get(
                "final_score"
            ),
            "confidence": strength.get(
                "confidence"
            ),
        },
        "pattern": {
            "primary_pattern": pattern.get(
                "primary_pattern"
            ),
            "technical_pattern": (
                pattern.get(
                    "technical_pattern"
                )
            ),
            "overall_judgment": (
                pattern.get(
                    "overall_judgment"
                )
            ),
            "confidence": pattern.get(
                "confidence"
            ),
        },
        "useful_gods": {
            "primary_useful_element": (
                useful_gods.get(
                    "primary_useful_element"
                )
            ),
            "secondary_useful_elements": (
                _safe_list(
                    useful_gods.get(
                        "secondary_useful_elements"
                    )
                )
            ),
            "final_useful_elements": _safe_list(
                useful_gods.get(
                    "final_useful_elements"
                )
            ),
            "unfavorable_elements": _safe_list(
                useful_gods.get(
                    "unfavorable_elements"
                )
            ),
            "confidence": useful_gods.get(
                "confidence"
            ),
        },
        "current_luck": {
            "ganzhi": current_pillar.get(
                "ganzhi"
            ),
            "stem_ten_god": current_pillar.get(
                "stem_ten_god"
            ),
            "start_age": current_pillar.get(
                "start_age"
            ),
            "end_age": current_pillar.get(
                "end_age"
            ),
        },
        "annual_luck": {
            "year": annual_luck.get(
                "year"
            ),
            "ganzhi": annual_luck.get(
                "ganzhi"
            ),
            "stem_ten_god": annual_luck.get(
                "stem_ten_god"
            ),
            "twelve_stage": annual_luck.get(
                "twelve_stage"
            ),
        },
    }


def validate_generation_result(
    generation_result: ReadingGenerationResult,
) -> Dict[str, Any]:
    if not isinstance(
        generation_result,
        ReadingGenerationResult,
    ):
        raise TypeError(
            "generation_resultは"
            "ReadingGenerationResultで"
            "指定してください。"
        )

    if (
        generation_result.output_format
        != "json"
    ):
        raise ReadingProductValidationError(
            "reading_productでは"
            "JSON形式の鑑定結果が必要です。"
        )

    if not isinstance(
        generation_result.parsed,
        Mapping,
    ):
        raise ReadingProductValidationError(
            "parse済みJSON鑑定結果がありません。"
        )

    parsed = generation_result.parsed

    for field in (
        "summary",
        "sections",
        "disclaimer",
    ):
        if field not in parsed:
            raise ReadingProductValidationError(
                "AI鑑定JSONに必須キーがありません: "
                f"{field}"
            )

    if not isinstance(
        parsed.get(
            "sections"
        ),
        Mapping,
    ):
        raise ReadingProductValidationError(
            "AI鑑定JSONのsectionsは"
            "dict型である必要があります。"
        )

    return {
        "valid": True,
        "output_format": generation_result.output_format,
        "model": generation_result.model,
        "sections": list(
            generation_result.sections
        ),
        "status": generation_result.status,
    }


def _extract_section_data(
    parsed: Mapping[
        str,
        Any,
    ],
    section: str,
) -> Dict[str, Any]:
    parsed_sections = _safe_dict(
        parsed.get(
            "sections"
        )
    )

    raw = parsed_sections.get(
        section
    )

    if not isinstance(
        raw,
        Mapping,
    ):
        raise ReadingProductValidationError(
            "AI鑑定結果に"
            "セクションがありません: "
            f"{section}"
        )

    return deepcopy(
        dict(raw)
    )


def build_product_section(
    section: str,
    section_data: Mapping[
        str,
        Any,
    ],
) -> Dict[str, Any]:
    if section not in SECTION_TITLES:
        raise ValueError(
            "未対応の鑑定セクションです: "
            f"{section}"
        )

    section_data = _require_mapping(
        section_data,
        "section_data",
    )

    source_title = _optional_string(
        section_data.get(
            "title"
        )
    )

    return {
        "key": section,
        "title": (
            source_title
            or SECTION_TITLES[
                section
            ]
        ),
        "summary": _string_or_empty(
            section_data.get(
                "summary"
            )
        ),
        "detail": _string_or_empty(
            section_data.get(
                "detail"
            )
        ),
        "evidence": [
            item.strip()
            for item
            in _safe_list(
                section_data.get(
                    "evidence"
                )
            )
            if isinstance(
                item,
                str,
            )
            and item.strip()
        ],
        "advice": [
            item.strip()
            for item
            in _safe_list(
                section_data.get(
                    "advice"
                )
            )
            if isinstance(
                item,
                str,
            )
            and item.strip()
        ],
    }


def build_product_sections(
    parsed: Mapping[
        str,
        Any,
    ],
    sections: Sequence[str],
) -> Tuple[
    Dict[str, Any],
    ...,
]:
    parsed = _require_mapping(
        parsed,
        "parsed",
    )

    normalized_sections = (
        normalize_product_sections(
            sections
        )
    )

    result: List[
        Dict[str, Any]
    ] = []

    for section in normalized_sections:
        section_data = (
            _extract_section_data(
                parsed,
                section,
            )
        )

        result.append(
            build_product_section(
                section,
                section_data,
            )
        )

    return tuple(result)


def extract_product_summary(
    parsed: Mapping[
        str,
        Any,
    ],
) -> str:
    parsed = _require_mapping(
        parsed,
        "parsed",
    )

    return _string_or_empty(
        parsed.get(
            "summary"
        )
    )


def extract_product_disclaimer(
    parsed: Mapping[
        str,
        Any,
    ],
) -> str:
    parsed = _require_mapping(
        parsed,
        "parsed",
    )

    disclaimer = _optional_string(
        parsed.get(
            "disclaimer"
        )
    )

    if disclaimer:
        return disclaimer

    return DEFAULT_DISCLAIMER


def build_generation_metadata(
    generation_result: ReadingGenerationResult,
) -> Dict[str, Any]:
    return {
        "model": generation_result.model,
        "response_id": (
            generation_result.response_id
        ),
        "response_status": (
            generation_result.response_status
        ),
        "usage": deepcopy(
            generation_result.usage
        ),
        "sections": list(
            generation_result.sections
        ),
        "method": generation_result.method,
        "status": generation_result.status,
    }


def build_product_metadata(
    reading_context: Mapping[
        str,
        Any,
    ],
) -> Dict[str, Any]:
    reading_context = _require_mapping(
        reading_context,
        "reading_context",
    )

    return {
        "created_at": _utc_now_iso(),
        "reading_context_schema": (
            reading_context.get(
                "schema_version"
            )
        ),
        "reading_context_method": (
            reading_context.get(
                "method"
            )
        ),
        "reading_context_status": (
            reading_context.get(
                "status"
            )
        ),
        "source_metadata": _safe_dict(
            reading_context.get(
                "source_metadata"
            )
        ),
        "product_version": (
            READING_PRODUCT_VERSION
        ),
        "recalculates_astrology": False,
        "rewrites_ai_reading": False,
    }


def build_reading_product(
    reading_context: Mapping[
        str,
        Any,
    ],
    generation_result: ReadingGenerationResult,
    *,
    title: str = DEFAULT_PRODUCT_TITLE,
    sections: Optional[
        Sequence[str]
    ] = None,
) -> ReadingProduct:
    reading_context = _require_mapping(
        reading_context,
        "reading_context",
    )

    validate_generation_result(
        generation_result
    )

    title = _string_or_empty(
        title
    )

    if not title:
        raise ValueError(
            "titleは空文字にできません。"
        )

    parsed = generation_result.parsed

    if not isinstance(
        parsed,
        Mapping,
    ):
        raise ReadingProductValidationError(
            "AI鑑定JSONがありません。"
        )

    if sections is None:
        product_sections = tuple(
            generation_result.sections
        )
    else:
        product_sections = (
            normalize_product_sections(
                sections
            )
        )

    if not product_sections:
        raise ReadingProductValidationError(
            "商品化対象の"
            "鑑定セクションがありません。"
        )

    generated_sections = set(
        generation_result.sections
    )

    missing_sections = [
        section
        for section
        in product_sections
        if section
        not in generated_sections
    ]

    if missing_sections:
        raise ReadingProductValidationError(
            "AI生成されていない"
            "セクションを商品化しようとしています: "
            + ", ".join(
                missing_sections
            )
        )

    return ReadingProduct(
        title=title,
        subject=build_product_subject(
            reading_context
        ),
        chart_summary=build_chart_summary(
            reading_context
        ),
        sections=build_product_sections(
            parsed,
            product_sections,
        ),
        summary=extract_product_summary(
            parsed
        ),
        disclaimer=extract_product_disclaimer(
            parsed
        ),
        generation=build_generation_metadata(
            generation_result
        ),
        metadata=build_product_metadata(
            reading_context
        ),
    )


def generate_reading_product(
    chart_result: Mapping[
        str,
        Any,
    ],
    *,
    client: Any = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    sections: Optional[
        Sequence[str]
    ] = None,
    language: str = "ja",
    tone: str = "professional_warm",
    title: str = DEFAULT_PRODUCT_TITLE,
    max_output_tokens: int = (
        DEFAULT_MAX_OUTPUT_TOKENS
    ),
    reasoning_effort: str = (
        DEFAULT_REASONING_EFFORT
    ),
    store: bool = DEFAULT_STORE,
    validate_context: bool = True,
) -> ReadingProduct:
    chart_result = _require_mapping(
        chart_result,
        "chart_result",
    )

    normalized_sections = (
        normalize_product_sections(
            sections
        )
    )

    reading_context = (
        build_reading_context(
            chart_result,
            validate=validate_context,
        )
    )

    generation_result = (
        generate_reading(
            reading_context,
            client=client,
            api_key=api_key,
            model=model,
            sections=normalized_sections,
            language=language,
            tone=tone,
            output_format="json",
            max_output_tokens=max_output_tokens,
            reasoning_effort=reasoning_effort,
            store=store,
        )
    )

    return build_reading_product(
        reading_context,
        generation_result,
        title=title,
        sections=normalized_sections,
    )


def generate_reading_product_dict(
    chart_result: Mapping[
        str,
        Any,
    ],
    *,
    client: Any = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    sections: Optional[
        Sequence[str]
    ] = None,
    language: str = "ja",
    tone: str = "professional_warm",
    title: str = DEFAULT_PRODUCT_TITLE,
    max_output_tokens: int = (
        DEFAULT_MAX_OUTPUT_TOKENS
    ),
    reasoning_effort: str = (
        DEFAULT_REASONING_EFFORT
    ),
    store: bool = DEFAULT_STORE,
    validate_context: bool = True,
) -> Dict[str, Any]:
    product = generate_reading_product(
        chart_result,
        client=client,
        api_key=api_key,
        model=model,
        sections=sections,
        language=language,
        tone=tone,
        title=title,
        max_output_tokens=max_output_tokens,
        reasoning_effort=reasoning_effort,
        store=store,
        validate_context=validate_context,
    )

    return product.to_dict()


def create_product_from_generation(
    reading_context: Mapping[
        str,
        Any,
    ],
    generation_result: ReadingGenerationResult,
    *,
    title: str = DEFAULT_PRODUCT_TITLE,
    sections: Optional[
        Sequence[str]
    ] = None,
) -> Dict[str, Any]:
    product = build_reading_product(
        reading_context,
        generation_result,
        title=title,
        sections=sections,
    )

    return product.to_dict()


def get_reading_product_metadata() -> Dict[
    str,
    Any,
]:
    return {
        "version": (
            READING_PRODUCT_VERSION
        ),
        "method": (
            READING_PRODUCT_METHOD
        ),
        "status": (
            READING_PRODUCT_STATUS
        ),
        "default_title": (
            DEFAULT_PRODUCT_TITLE
        ),
        "section_order": list(
            DEFAULT_SECTION_ORDER
        ),
        "section_titles": deepcopy(
            SECTION_TITLES
        ),
        "recalculates_astrology": False,
        "rewrites_ai_reading": False,
        "requires_json_generation": True,
    }


__all__ = [
    "READING_PRODUCT_VERSION",
    "READING_PRODUCT_METHOD",
    "READING_PRODUCT_STATUS",
    "DEFAULT_PRODUCT_TITLE",
    "DEFAULT_DISCLAIMER",
    "SECTION_TITLES",
    "DEFAULT_SECTION_ORDER",
    "ReadingProductError",
    "ReadingProductValidationError",
    "ReadingProduct",
    "normalize_product_sections",
    "build_product_subject",
    "build_chart_summary",
    "validate_generation_result",
    "build_product_section",
    "build_product_sections",
    "extract_product_summary",
    "extract_product_disclaimer",
    "build_generation_metadata",
    "build_product_metadata",
    "build_reading_product",
    "generate_reading_product",
    "generate_reading_product_dict",
    "create_product_from_generation",
    "get_reading_product_metadata",
]
