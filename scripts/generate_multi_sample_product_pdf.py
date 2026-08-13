"""
scripts/generate_multi_sample_product_pdf.py

複数の検証済み命式について、

出生情報
    ↓
calculate_chart
    ↓
reading_context
    ↓
OpenAI 8セクション鑑定
    ↓
ReadingProduct
    ↓
Playwright / Chromium
    ↓
商品PDF

を一括生成・検証する最終商品品質確認スクリプト。

重要
----
OpenAI APIを呼ぶ前に、
全ケースの命式をPRECHECKする。

1ケースでも期待値と不一致なら、
OpenAI APIを1回も呼ばず停止する。

Version
-------
generate_multi_sample_product_pdf_v1_3
"""

from __future__ import annotations

import json
import os
import sys

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping

from engine.chart import calculate_chart

from engine.reading_context import (
    build_reading_context,
)

from engine.reading_generator import (
    OPENAI_API_KEY_ENV,
    ReadingGenerationResult,
    generate_reading,
    get_default_model,
    has_openai_api_key,
)

from engine.reading_pdf import (
    READING_PDF_METHOD,
    READING_PDF_VERSION,
    get_reading_pdf_metadata,
    write_reading_product_pdf,
)

from engine.reading_product import (
    ReadingProduct,
    build_reading_product,
)


# ============================================================
# Version
# ============================================================


SCRIPT_VERSION = (
    "generate_multi_sample_product_pdf_v1_3"
)


# ============================================================
# Generation configuration
# ============================================================


SECTIONS = (
    "core_personality",
    "career",
    "wealth",
    "relationships",
    "health",
    "current_luck",
    "future_flow",
    "advice",
)


LANGUAGE = "ja"

TONE = "professional_warm"

OUTPUT_FORMAT = "json"

MAX_OUTPUT_TOKENS = 8000

REASONING_EFFORT = "minimal"

STORE = False


PRODUCT_TITLE = (
    "四柱推命鑑定書"
)


# ============================================================
# Target datetime
# ============================================================


TARGET_DATETIME = datetime(
    2026,
    8,
    10,
    15,
    36,
)


EXPECTED_ANNUAL_GANZHI = (
    "丙午"
)


# ============================================================
# Disclaimer validation
# ============================================================


MEDICAL_TERMS = (
    "医学",
    "医療",
    "健康",
    "診断",
)


CONSULTATION_TERMS = (
    "専門家",
    "医師",
    "医療機関",
    "医療専門職",
    "専門医",
    "医療従事者",
    "専門職",
    "相談",
)


# ============================================================
# Case definition
# ============================================================


@dataclass(
    frozen=True
)
class SampleCase:

    case_id: str

    birth_date: str

    birth_time: str

    birth_place: str

    gender: str

    expected_year: str

    expected_month: str

    expected_day: str

    expected_hour: str

    expected_day_master: str

    @property
    def expected_pillars(
        self,
    ) -> tuple[
        str,
        str,
        str,
        str,
    ]:

        return (
            self.expected_year,
            self.expected_month,
            self.expected_day,
            self.expected_hour,
        )


# ============================================================
# Cases
# ============================================================


CASES = (

    # --------------------------------------------------------
    # Case 1
    # 1985-07-17 21:50 石川県 女性
    # --------------------------------------------------------

    SampleCase(
        case_id=(
            "1985_ishikawa_female"
        ),
        birth_date="1985-07-17",
        birth_time="21:50",
        birth_place="石川県",
        gender="female",
        expected_year="乙丑",
        expected_month="癸未",
        expected_day="丁巳",
        expected_hour="辛亥",
        expected_day_master="丁",
    ),

    # --------------------------------------------------------
    # Case 2
    # 1984-07-22 04:15 北海道 女性
    #
    # 現行engine.chart.calculate_chart()
    # 実計算確認値:
    #
    # 甲子 / 辛未 / 丁巳 / 壬寅
    # 日主: 丁
    # --------------------------------------------------------

    SampleCase(
        case_id=(
            "1984_hokkaido_female"
        ),
        birth_date="1984-07-22",
        birth_time="04:15",
        birth_place="北海道",
        gender="female",
        expected_year="甲子",
        expected_month="辛未",
        expected_day="丁巳",
        expected_hour="壬寅",
        expected_day_master="丁",
    ),

    # --------------------------------------------------------
    # Case 3
    # 1984-07-21 12:00 東京都 男性
    #
    # 現行engine.chart.calculate_chart()
    # PRECHECK実計算確認値:
    #
    # 甲子 / 辛未 / 丙辰 / 甲午
    # 日主: 丙
    # --------------------------------------------------------

    SampleCase(
        case_id=(
            "1984_tokyo_male"
        ),
        birth_date="1984-07-21",
        birth_time="12:00",
        birth_place="東京都",
        gender="male",
        expected_year="甲子",
        expected_month="辛未",
        expected_day="丙辰",
        expected_hour="甲午",
        expected_day_master="丙",
    ),
)


# ============================================================
# Output
# ============================================================


OUTPUT_DIR = (
    Path("output")
    / "multi_product_pdf"
)


# ============================================================
# Helpers
# ============================================================


def require_mapping(
    value: Any,
    name: str,
) -> Mapping[str, Any]:

    if not isinstance(
        value,
        Mapping,
    ):
        raise TypeError(
            f"{name}はmapping"
            "である必要があります。"
        )

    return value


def require_string(
    value: Any,
    name: str,
) -> str:

    if not isinstance(
        value,
        str,
    ):
        raise TypeError(
            f"{name}は文字列"
            "である必要があります。"
        )

    value = value.strip()

    if not value:
        raise ValueError(
            f"{name}が空です。"
        )

    return value


def contains_any_term(
    text: str,
    terms: tuple[str, ...],
) -> bool:

    return any(
        term in text
        for term
        in terms
    )


# ============================================================
# Environment
# ============================================================


def validate_environment() -> str:

    if not has_openai_api_key():

        raise RuntimeError(
            f"{OPENAI_API_KEY_ENV} "
            "が設定されていません。"
        )

    model = (
        get_default_model()
    )

    return require_string(
        model,
        "OpenAI model",
    )


# ============================================================
# Request
# ============================================================


def build_request(
    case: SampleCase,
):

    return SimpleNamespace(
        birth_date=(
            case.birth_date
        ),
        birth_time=(
            case.birth_time
        ),
        birth_place=(
            case.birth_place
        ),
        gender=(
            case.gender
        ),
    )


# ============================================================
# Chart helpers
# ============================================================


def get_actual_chart_signature(
    result: Mapping[
        str,
        Any,
    ],
) -> tuple[
    tuple[
        str,
        str,
        str,
        str,
    ],
    str,
]:

    result = require_mapping(
        result,
        "chart_result",
    )

    chart = require_mapping(
        result.get(
            "chart"
        ),
        "chart_result.chart",
    )

    pillars = []

    for position in (
        "year",
        "month",
        "day",
        "hour",
    ):

        pillar_data = (
            require_mapping(
                chart.get(
                    position
                ),
                (
                    f"chart."
                    f"{position}"
                ),
            )
        )

        pillar = require_string(
            pillar_data.get(
                "pillar"
            ),
            (
                f"chart."
                f"{position}."
                "pillar"
            ),
        )

        pillars.append(
            pillar
        )

    day_master = (
        require_mapping(
            result.get(
                "day_master"
            ),
            "day_master",
        )
    )

    day_master_stem = (
        require_string(
            day_master.get(
                "stem"
            ),
            "day_master.stem",
        )
    )

    return (
        tuple(
            pillars
        ),
        day_master_stem,
    )


def validate_chart(
    case: SampleCase,
    result: Mapping[
        str,
        Any,
    ],
) -> None:

    (
        actual_pillars,
        actual_day_master,
    ) = get_actual_chart_signature(
        result
    )

    if (
        actual_pillars
        != case.expected_pillars
    ):

        raise RuntimeError(
            f"{case.case_id}: "
            "四柱が期待値と"
            "不一致です。 "
            f"expected="
            f"{case.expected_pillars}, "
            f"actual="
            f"{actual_pillars}"
        )

    if (
        actual_day_master
        != case.expected_day_master
    ):

        raise RuntimeError(
            f"{case.case_id}: "
            "日主が期待値と"
            "不一致です。 "
            f"expected="
            f"{case.expected_day_master}, "
            f"actual="
            f"{actual_day_master}"
        )


# ============================================================
# PRECHECK
# ============================================================


def precheck_all_cases(
) -> dict[
    str,
    Mapping[str, Any],
]:

    print(
        "=" * 72
    )

    print(
        "PRECHECK: 全ケース命式照合"
    )

    print(
        "=" * 72
    )

    print()

    results: dict[
        str,
        Mapping[str, Any],
    ] = {}

    mismatches: list[
        str
    ] = []

    for (
        index,
        case,
    ) in enumerate(
        CASES,
        start=1,
    ):

        print(
            f"[PRECHECK "
            f"{index}/"
            f"{len(CASES)}] "
            f"{case.case_id}"
        )

        request = (
            build_request(
                case
            )
        )

        chart_result = (
            calculate_chart(
                request,
                target_datetime=(
                    TARGET_DATETIME
                ),
            )
        )

        (
            actual_pillars,
            actual_day_master,
        ) = get_actual_chart_signature(
            chart_result
        )

        print(
            "  expected pillars: "
            + " / ".join(
                case.expected_pillars
            )
        )

        print(
            "  actual pillars  : "
            + " / ".join(
                actual_pillars
            )
        )

        print(
            "  expected DM: "
            f"{case.expected_day_master}"
        )

        print(
            "  actual DM  : "
            f"{actual_day_master}"
        )

        if (
            actual_pillars
            != case.expected_pillars
            or
            actual_day_master
            != case.expected_day_master
        ):

            mismatches.append(
                (
                    f"{case.case_id}: "
                    f"expected="
                    f"{case.expected_pillars}/"
                    f"{case.expected_day_master}, "
                    f"actual="
                    f"{actual_pillars}/"
                    f"{actual_day_master}"
                )
            )

            print(
                "  RESULT: MISMATCH"
            )

        else:

            results[
                case.case_id
            ] = (
                chart_result
            )

            print(
                "  RESULT: OK"
            )

        print()

    if mismatches:

        detail = "\n".join(
            (
                f"- {item}"
            )
            for item
            in mismatches
        )

        raise RuntimeError(
            "PRECHECKで命式不一致を"
            "検出しました。"
            "\nOpenAI APIは呼びません。"
            "\n"
            f"{detail}"
        )

    print(
        "PRECHECK: ALL OK"
    )

    print()

    return results


# ============================================================
# reading_context validation
# ============================================================


def validate_context(
    case: SampleCase,
    context: Mapping[
        str,
        Any,
    ],
) -> None:

    context = require_mapping(
        context,
        "reading_context",
    )

    if (
        context.get(
            "status"
        )
        != "ready_for_ai_reading"
    ):

        raise RuntimeError(
            f"{case.case_id}: "
            "reading_contextが"
            "readyではありません。"
        )

    natal_chart = (
        require_mapping(
            context.get(
                "natal_chart"
            ),
            "natal_chart",
        )
    )

    pillars = (
        require_mapping(
            natal_chart.get(
                "pillars"
            ),
            (
                "natal_chart."
                "pillars"
            ),
        )
    )

    actual_pillars = []

    for position in (
        "year",
        "month",
        "day",
        "hour",
    ):

        pillar_data = (
            require_mapping(
                pillars.get(
                    position
                ),
                (
                    f"pillars."
                    f"{position}"
                ),
            )
        )

        actual = (
            require_string(
                pillar_data.get(
                    "pillar"
                ),
                (
                    f"context."
                    f"{position}."
                    "pillar"
                ),
            )
        )

        actual_pillars.append(
            actual
        )

    if (
        tuple(
            actual_pillars
        )
        != case.expected_pillars
    ):

        raise RuntimeError(
            f"{case.case_id}: "
            "reading_contextで"
            "四柱が変化しています。 "
            f"expected="
            f"{case.expected_pillars}, "
            f"actual="
            f"{tuple(actual_pillars)}"
        )

    day_master = (
        require_mapping(
            context.get(
                "day_master"
            ),
            "context.day_master",
        )
    )

    actual_day_master = (
        require_string(
            day_master.get(
                "stem"
            ),
            (
                "context."
                "day_master.stem"
            ),
        )
    )

    if (
        actual_day_master
        != case.expected_day_master
    ):

        raise RuntimeError(
            f"{case.case_id}: "
            "reading_contextで"
            "日主が変化しています。"
        )

    luck = require_mapping(
        context.get(
            "luck"
        ),
        "context.luck",
    )

    annual_luck = (
        require_mapping(
            luck.get(
                "annual_luck"
            ),
            (
                "luck."
                "annual_luck"
            ),
        )
    )

    actual_annual_ganzhi = (
        require_string(
            annual_luck.get(
                "ganzhi"
            ),
            (
                "luck."
                "annual_luck."
                "ganzhi"
            ),
        )
    )

    if (
        actual_annual_ganzhi
        != EXPECTED_ANNUAL_GANZHI
    ):

        raise RuntimeError(
            f"{case.case_id}: "
            "歳運が期待値と"
            "不一致です。 "
            f"expected="
            f"{EXPECTED_ANNUAL_GANZHI}, "
            f"actual="
            f"{actual_annual_ganzhi}"
        )


# ============================================================
# AI generation validation
# ============================================================


def validate_generation(
    case: SampleCase,
    result: ReadingGenerationResult,
) -> None:

    if not isinstance(
        result,
        ReadingGenerationResult,
    ):

        raise TypeError(
            f"{case.case_id}: "
            "ReadingGenerationResult"
            "ではありません。"
        )

    if (
        result.status
        != "completed"
    ):

        raise RuntimeError(
            f"{case.case_id}: "
            "AI生成がcompleted"
            "ではありません。 "
            f"status="
            f"{result.status}"
        )

    if (
        result.response_status
        not in (
            None,
            "completed",
        )
    ):

        raise RuntimeError(
            f"{case.case_id}: "
            "OpenAI responseが"
            "completedではありません。 "
            f"response_status="
            f"{result.response_status}"
        )

    parsed = require_mapping(
        result.parsed,
        "generation.parsed",
    )

    require_string(
        parsed.get(
            "summary"
        ),
        "summary",
    )

    disclaimer = (
        require_string(
            parsed.get(
                "disclaimer"
            ),
            "disclaimer",
        )
    )

    if not contains_any_term(
        disclaimer,
        MEDICAL_TERMS,
    ):

        raise RuntimeError(
            f"{case.case_id}: "
            "免責事項に健康・医療上の"
            "注意表現がありません。 "
            f"disclaimer="
            f"{disclaimer!r}"
        )

    if not contains_any_term(
        disclaimer,
        CONSULTATION_TERMS,
    ):

        raise RuntimeError(
            f"{case.case_id}: "
            "免責事項に専門的な"
            "相談を促す表現がありません。 "
            f"disclaimer="
            f"{disclaimer!r}"
        )

    sections = require_mapping(
        parsed.get(
            "sections"
        ),
        "sections",
    )

    actual_section_keys = (
        tuple(
            sections.keys()
        )
    )

    if (
        actual_section_keys
        != SECTIONS
    ):

        raise RuntimeError(
            f"{case.case_id}: "
            "8セクション構成が"
            "一致しません。 "
            f"expected="
            f"{SECTIONS}, "
            f"actual="
            f"{actual_section_keys}"
        )

    for section_key in SECTIONS:

        section = (
            require_mapping(
                sections.get(
                    section_key
                ),
                (
                    f"sections."
                    f"{section_key}"
                ),
            )
        )

        for field in (
            "title",
            "summary",
            "detail",
        ):

            require_string(
                section.get(
                    field
                ),
                (
                    f"{section_key}."
                    f"{field}"
                ),
            )

        evidence = (
            section.get(
                "evidence"
            )
        )

        advice = (
            section.get(
                "advice"
            )
        )

        if not isinstance(
            evidence,
            (list, tuple),
        ) or not evidence:

            raise RuntimeError(
                f"{case.case_id}: "
                f"{section_key}."
                "evidenceが不正です。"
            )

        if not isinstance(
            advice,
            (list, tuple),
        ) or not advice:

            raise RuntimeError(
                f"{case.case_id}: "
                f"{section_key}."
                "adviceが不正です。"
            )


# ============================================================
# Product validation
# ============================================================


def validate_product(
    case: SampleCase,
    product: ReadingProduct,
) -> None:

    if not isinstance(
        product,
        ReadingProduct,
    ):

        raise TypeError(
            f"{case.case_id}: "
            "ReadingProductでは"
            "ありません。"
        )

    if (
        product.status
        != "ready"
    ):

        raise RuntimeError(
            f"{case.case_id}: "
            "ReadingProductが"
            "readyではありません。 "
            f"status="
            f"{product.status}"
        )

    sequence = tuple(
        product
        .chart_summary
        .get(
            "pillar_sequence",
            (),
        )
    )

    if (
        sequence
        != case.expected_pillars
    ):

        raise RuntimeError(
            f"{case.case_id}: "
            "ReadingProductの"
            "四柱が不一致です。 "
            f"expected="
            f"{case.expected_pillars}, "
            f"actual="
            f"{sequence}"
        )

    day_master = (
        require_mapping(
            product
            .chart_summary
            .get(
                "day_master"
            ),
            "product.day_master",
        )
    )

    actual_day_master = (
        require_string(
            day_master.get(
                "stem"
            ),
            (
                "product."
                "day_master.stem"
            ),
        )
    )

    if (
        actual_day_master
        != case.expected_day_master
    ):

        raise RuntimeError(
            f"{case.case_id}: "
            "ReadingProductで"
            "日主が変化しています。"
        )

    if (
        len(
            product.sections
        )
        != len(
            SECTIONS
        )
    ):

        raise RuntimeError(
            f"{case.case_id}: "
            "ReadingProductが"
            "8セクションではありません。 "
            f"actual="
            f"{len(product.sections)}"
        )

    actual_section_order = (
        tuple(
            section.get(
                "key"
            )
            for section
            in product.sections
        )
    )

    if (
        actual_section_order
        != SECTIONS
    ):

        raise RuntimeError(
            f"{case.case_id}: "
            "ReadingProductの"
            "セクション順が"
            "一致しません。 "
            f"actual="
            f"{actual_section_order}"
        )

    require_string(
        product.summary,
        "product.summary",
    )

    require_string(
        product.disclaimer,
        "product.disclaimer",
    )


# ============================================================
# Security
# ============================================================


def validate_security(
    case: SampleCase,
    product: ReadingProduct,
    pdf_path: Path,
) -> None:

    api_key = os.getenv(
        OPENAI_API_KEY_ENV,
        "",
    ).strip()

    product_text = (
        json.dumps(
            product.to_dict(),
            ensure_ascii=False,
            default=str,
        )
    )

    forbidden = (
        '"api_key"',
        '"system_prompt"',
        '"user_prompt"',
    )

    for marker in forbidden:

        if marker in product_text:

            raise RuntimeError(
                f"{case.case_id}: "
                "非公開フィールドが"
                "商品データに"
                "露出しています。 "
                f"{marker}"
            )

    if (
        api_key
        and api_key
        in product_text
    ):

        raise RuntimeError(
            f"{case.case_id}: "
            "APIキーが商品JSONに"
            "露出しています。"
        )

    if api_key:

        pdf_bytes = (
            pdf_path.read_bytes()
        )

        if (
            api_key.encode(
                "utf-8"
            )
            in pdf_bytes
        ):

            raise RuntimeError(
                f"{case.case_id}: "
                "APIキーがPDFに"
                "露出しています。"
            )


# ============================================================
# PDF validation
# ============================================================


def validate_pdf(
    case: SampleCase,
    pdf_path: Path,
) -> None:

    if not isinstance(
        pdf_path,
        Path,
    ):

        raise TypeError(
            f"{case.case_id}: "
            "PDF出力結果がPath"
            "ではありません。"
        )

    if not pdf_path.exists():

        raise RuntimeError(
            f"{case.case_id}: "
            "PDFが生成されて"
            "いません。"
        )

    if not pdf_path.is_file():

        raise RuntimeError(
            f"{case.case_id}: "
            "PDF出力先が"
            "ファイルではありません。"
        )

    if (
        pdf_path.suffix.lower()
        != ".pdf"
    ):

        raise RuntimeError(
            f"{case.case_id}: "
            "拡張子が.pdfでは"
            "ありません。"
        )

    size = (
        pdf_path.stat()
        .st_size
    )

    if size < 10_000:

        raise RuntimeError(
            f"{case.case_id}: "
            "PDFサイズが"
            "小さすぎます。 "
            f"size="
            f"{size}"
        )

    data = (
        pdf_path.read_bytes()
    )

    if not data.startswith(
        b"%PDF-"
    ):

        raise RuntimeError(
            f"{case.case_id}: "
            "PDF magic headerが"
            "ありません。"
        )

    if (
        b"%%EOF"
        not in data[
            -2048:
        ]
    ):

        raise RuntimeError(
            f"{case.case_id}: "
            "PDF EOF markerが"
            "ありません。"
        )


# ============================================================
# Save JSON
# ============================================================


def save_json(
    path: Path,
    value: Any,
) -> None:

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )


# ============================================================
# Generate single case
# ============================================================


def generate_case(
    case: SampleCase,
    model: str,
    chart_result: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:

    print(
        "=" * 72
    )

    print(
        f"CASE: "
        f"{case.case_id}"
    )

    print(
        "=" * 72
    )

    print()

    # --------------------------------------------------------
    # 1. Chart
    # --------------------------------------------------------

    print(
        "1. 命式確認"
    )

    validate_chart(
        case,
        chart_result,
    )

    print(
        "   OK: "
        + " / ".join(
            case.expected_pillars
        )
    )

    print()

    # --------------------------------------------------------
    # 2. Context
    # --------------------------------------------------------

    print(
        "2. reading_context生成"
    )

    context = (
        build_reading_context(
            chart_result
        )
    )

    validate_context(
        case,
        context,
    )

    print(
        "   OK"
    )

    print()

    # --------------------------------------------------------
    # 3. OpenAI
    # --------------------------------------------------------

    print(
        "3. OpenAIで"
        "8セクション鑑定生成"
    )

    generation = (
        generate_reading(
            context,
            model=model,
            sections=SECTIONS,
            language=LANGUAGE,
            tone=TONE,
            output_format=(
                OUTPUT_FORMAT
            ),
            max_output_tokens=(
                MAX_OUTPUT_TOKENS
            ),
            reasoning_effort=(
                REASONING_EFFORT
            ),
            store=STORE,
        )
    )

    validate_generation(
        case,
        generation,
    )

    print(
        "   OK"
    )

    print(
        "   response_status: "
        f"{generation.response_status}"
    )

    print(
        "   response_id: "
        f"{generation.response_id}"
    )

    print()

    # --------------------------------------------------------
    # 4. Product
    # --------------------------------------------------------

    print(
        "4. ReadingProduct生成"
    )

    product = (
        build_reading_product(
            context,
            generation,
            title=(
                PRODUCT_TITLE
            ),
            sections=(
                SECTIONS
            ),
        )
    )

    validate_product(
        case,
        product,
    )

    print(
        "   OK"
    )

    print()

    # --------------------------------------------------------
    # Output directory
    # --------------------------------------------------------

    case_dir = (
        OUTPUT_DIR
        / case.case_id
    )

    case_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # 5. JSON
    # --------------------------------------------------------

    print(
        "5. JSON保存"
    )

    product_json_path = (
        case_dir
        / "product.json"
    )

    reading_json_path = (
        case_dir
        / "ai_reading.json"
    )

    save_json(
        product_json_path,
        product.to_dict(),
    )

    save_json(
        reading_json_path,
        generation.parsed,
    )

    print(
        "   OK"
    )

    print()

    # --------------------------------------------------------
    # 6. PDF
    # --------------------------------------------------------

    print(
        "6. 商品PDF生成"
    )

    pdf_path = (
        case_dir
        / "reading.pdf"
    )

    pdf_path = (
        write_reading_product_pdf(
            product,
            pdf_path,
            document_title=(
                f"{PRODUCT_TITLE} "
                f"{case.case_id}"
            ),
        )
    )

    validate_pdf(
        case,
        pdf_path,
    )

    validate_security(
        case,
        product,
        pdf_path,
    )

    pdf_size = (
        pdf_path.stat()
        .st_size
    )

    print(
        "   OK"
    )

    print(
        "   size: "
        f"{pdf_size:,} bytes"
    )

    print()

    result = {
        "case_id": (
            case.case_id
        ),
        "birth_date": (
            case.birth_date
        ),
        "birth_time": (
            case.birth_time
        ),
        "birth_place": (
            case.birth_place
        ),
        "gender": (
            case.gender
        ),
        "pillars": list(
            case.expected_pillars
        ),
        "day_master": (
            case.expected_day_master
        ),
        "response_status": (
            generation
            .response_status
        ),
        "response_id": (
            generation
            .response_id
        ),
        "usage": (
            generation.usage
        ),
        "pdf": str(
            pdf_path.resolve()
        ),
        "pdf_size": (
            pdf_size
        ),
        "product_json": str(
            product_json_path
            .resolve()
        ),
        "reading_json": str(
            reading_json_path
            .resolve()
        ),
        "status": (
            "completed"
        ),
    }

    print(
        "CASE生成完了"
    )

    print(
        "PDF: "
        f"{pdf_path.resolve()}"
    )

    print()

    return result


# ============================================================
# Cross-case validation
# ============================================================


def validate_cross_case_results(
    results: list[
        dict[str, Any]
    ],
) -> None:

    if (
        len(
            results
        )
        != len(
            CASES
        )
    ):

        raise RuntimeError(
            "生成結果件数が"
            "ケース数と一致しません。"
        )

    case_ids = {
        result[
            "case_id"
        ]
        for result
        in results
    }

    if (
        len(
            case_ids
        )
        != len(
            CASES
        )
    ):

        raise RuntimeError(
            "case_idが重複しています。"
        )

    pillar_signatures = {
        tuple(
            result[
                "pillars"
            ]
        )
        for result
        in results
    }

    if (
        len(
            pillar_signatures
        )
        != len(
            CASES
        )
    ):

        raise RuntimeError(
            "複数ケースの"
            "命式signatureが"
            "重複しています。"
        )

    day_masters = {
        result[
            "day_master"
        ]
        for result
        in results
    }

    if (
        len(
            day_masters
        )
        < 2
    ):

        raise RuntimeError(
            "複数日主ケースの"
            "検証になっていません。"
        )

    for result in results:

        if (
            result[
                "status"
            ]
            != "completed"
        ):

            raise RuntimeError(
                f"{result['case_id']}: "
                "未完了です。"
            )

        if (
            result[
                "pdf_size"
            ]
            < 10_000
        ):

            raise RuntimeError(
                f"{result['case_id']}: "
                "異常に小さいPDFです。"
            )


# ============================================================
# PDF metadata
# ============================================================


def validate_pdf_metadata() -> None:

    metadata = (
        get_reading_pdf_metadata()
    )

    if (
        metadata.get(
            "version"
        )
        != READING_PDF_VERSION
    ):

        raise RuntimeError(
            "PDF versionが"
            "一致しません。 "
            f"expected="
            f"{READING_PDF_VERSION}, "
            f"actual="
            f"{metadata.get('version')}"
        )

    if (
        metadata.get(
            "method"
        )
        != READING_PDF_METHOD
    ):

        raise RuntimeError(
            "PDF methodが"
            "一致しません。 "
            f"expected="
            f"{READING_PDF_METHOD}, "
            f"actual="
            f"{metadata.get('method')}"
        )

    if (
        metadata.get(
            "recalculates_astrology"
        )
        is not False
    ):

        raise RuntimeError(
            "PDF層が占術再計算を"
            "行う設定です。"
        )

    if (
        metadata.get(
            "rewrites_ai_reading"
        )
        is not False
    ):

        raise RuntimeError(
            "PDF層がAI鑑定文を"
            "書き換える設定です。"
        )

    if (
        metadata.get(
            "exposes_api_key"
        )
        is not False
    ):

        raise RuntimeError(
            "PDF層のAPIキー"
            "非露出保証が不正です。"
        )


# ============================================================
# Main
# ============================================================


def main() -> int:

    try:

        model = (
            validate_environment()
        )

        OUTPUT_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        print(
            "# 複数命式 "
            "商品PDF最終確認"
        )

        print()

        print(
            f"script_version: "
            f"{SCRIPT_VERSION}"
        )

        print(
            f"model: "
            f"{model}"
        )

        print(
            f"cases: "
            f"{len(CASES)}"
        )

        print(
            f"pdf_version: "
            f"{READING_PDF_VERSION}"
        )

        print(
            f"pdf_method: "
            f"{READING_PDF_METHOD}"
        )

        print()

        # ----------------------------------------------------
        # PRECHECK
        #
        # 全ケースをAPI呼び出し前に検証。
        # ----------------------------------------------------

        prechecked_charts = (
            precheck_all_cases()
        )

        # ----------------------------------------------------
        # Generate
        # ----------------------------------------------------

        results: list[
            dict[str, Any]
        ] = []

        for (
            index,
            case,
        ) in enumerate(
            CASES,
            start=1,
        ):

            print(
                f"[{index}/"
                f"{len(CASES)}]"
            )

            chart_result = (
                prechecked_charts[
                    case.case_id
                ]
            )

            result = (
                generate_case(
                    case,
                    model,
                    chart_result,
                )
            )

            results.append(
                result
            )

        # ----------------------------------------------------
        # Cross-case validation
        # ----------------------------------------------------

        print(
            "=" * 72
        )

        print(
            "複数ケース横断確認"
        )

        print(
            "=" * 72
        )

        validate_cross_case_results(
            results
        )

        print(
            "OK"
        )

        print()

        # ----------------------------------------------------
        # PDF metadata
        # ----------------------------------------------------

        print(
            "PDF metadata確認"
        )

        validate_pdf_metadata()

        print(
            "OK"
        )

        print()

        # ----------------------------------------------------
        # Summary JSON
        # ----------------------------------------------------

        summary_path = (
            OUTPUT_DIR
            / "summary.json"
        )

        summary = {
            "script_version": (
                SCRIPT_VERSION
            ),
            "model": (
                model
            ),
            "target_datetime": (
                TARGET_DATETIME
                .isoformat()
            ),
            "case_count": (
                len(
                    CASES
                )
            ),
            "pdf_version": (
                READING_PDF_VERSION
            ),
            "pdf_method": (
                READING_PDF_METHOD
            ),
            "results": (
                results
            ),
            "status": (
                "completed"
            ),
        }

        save_json(
            summary_path,
            summary,
        )

        # ----------------------------------------------------
        # Complete
        # ----------------------------------------------------

        print(
            "=" * 72
        )

        print(
            "全ケース生成完了"
        )

        print(
            "=" * 72
        )

        print()

        for result in results:

            print(
                result[
                    "case_id"
                ]
            )

            print(
                "  pillars: "
                + " / ".join(
                    result[
                        "pillars"
                    ]
                )
            )

            print(
                "  day_master: "
                f"{result['day_master']}"
            )

            print(
                "  pdf_size: "
                f"{result['pdf_size']:,} "
                "bytes"
            )

            print(
                "  PDF: "
                f"{result['pdf']}"
            )

            print()

        print(
            "Summary: "
            f"{summary_path.resolve()}"
        )

        print()

        print(
            "STATUS: COMPLETED"
        )

        return 0

    except Exception as exc:

        print(
            "",
            file=sys.stderr,
        )

        print(
            "=" * 72,
            file=sys.stderr,
        )

        print(
            "生成失敗",
            file=sys.stderr,
        )

        print(
            "=" * 72,
            file=sys.stderr,
        )

        print(
            f"{type(exc).__name__}: "
            f"{exc}",
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":

    raise SystemExit(
        main()
    )
