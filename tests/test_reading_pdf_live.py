"""
tests/test_reading_pdf_live.py

四柱推命 AI鑑定 PDF
実環境 LIVE E2E テスト。

目的
----
実際の

出生情報
    ↓
calculate_chart
    ↓
reading_context
    ↓
OpenAI Responses API
    ↓
8セクション鑑定
    ↓
ReadingProduct
    ↓
reading_renderer
    ↓
Playwright / Chromium
    ↓
PDF

という商品生成フローを最後まで検証する。

このテストはLIVEテスト。
OpenAI APIを実際に呼び出すため、
API料金が発生する。

またPlaywright Chromiumを
実際に起動する。

必要環境
--------
OPENAI_API_KEY

Playwright:

    pip install playwright
    python -m playwright install chromium

実行例
------
PowerShell:

    $env:PYTHONPATH="."
    pytest .\\tests\\test_reading_pdf_live.py -v -s

Version
-------
reading_pdf_live_v1
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping

import pytest

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
    READING_PDF_STATUS,
    READING_PDF_VERSION,
    get_reading_pdf_metadata,
    write_reading_product_pdf,
)

from engine.reading_product import (
    ReadingProduct,
    build_reading_product,
)


# ============================================================
# Test metadata
# ============================================================


TEST_VERSION = (
    "reading_pdf_live_v1"
)


# ============================================================
# Fixed verified case
# ============================================================


BIRTH_DATE = "1985-07-17"

BIRTH_TIME = "21:50"

BIRTH_PLACE = "石川県"

GENDER = "female"


TARGET_DATETIME = datetime(
    2026,
    8,
    10,
    15,
    36,
)


EXPECTED_PILLARS = {
    "year": "乙丑",
    "month": "癸未",
    "day": "丁巳",
    "hour": "辛亥",
}


EXPECTED_PILLAR_SEQUENCE = (
    "乙丑",
    "癸未",
    "丁巳",
    "辛亥",
)


EXPECTED_DAY_MASTER = "丁"

EXPECTED_ANNUAL_GANZHI = "丙午"


# ============================================================
# Reading configuration
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


MODEL = None

LANGUAGE = "ja"

TONE = "professional_warm"

OUTPUT_FORMAT = "json"

MAX_OUTPUT_TOKENS = 8000

REASONING_EFFORT = "minimal"

STORE = False


# ============================================================
# PDF configuration
# ============================================================


PRODUCT_TITLE = (
    "四柱推命 AI鑑定書"
)


PDF_DOCUMENT_TITLE = (
    "四柱推命 AI鑑定書"
)


MIN_PDF_SIZE_BYTES = 10_000


# ============================================================
# Helpers
# ============================================================


def _require_mapping(
    value: Any,
    name: str,
) -> Mapping[str, Any]:

    assert isinstance(
        value,
        Mapping,
    ), (
        f"{name}がmappingではありません。"
    )

    return value


def _require_non_empty_string(
    value: Any,
    name: str,
) -> str:

    assert isinstance(
        value,
        str,
    ), (
        f"{name}が文字列ではありません。"
    )

    value = value.strip()

    assert value, (
        f"{name}が空です。"
    )

    return value


def _get_pillar(
    chart_result: Mapping[str, Any],
    position: str,
) -> str:

    chart = _require_mapping(
        chart_result.get("chart"),
        "chart_result.chart",
    )

    pillar_data = _require_mapping(
        chart.get(position),
        f"chart.{position}",
    )

    return _require_non_empty_string(
        pillar_data.get("pillar"),
        f"chart.{position}.pillar",
    )


def _get_context_pillar(
    reading_context: Mapping[str, Any],
    position: str,
) -> str:

    natal_chart = _require_mapping(
        reading_context.get(
            "natal_chart"
        ),
        "reading_context.natal_chart",
    )

    pillars = _require_mapping(
        natal_chart.get(
            "pillars"
        ),
        (
            "reading_context."
            "natal_chart.pillars"
        ),
    )

    pillar_data = _require_mapping(
        pillars.get(position),
        (
            "reading_context."
            f"pillars.{position}"
        ),
    )

    return _require_non_empty_string(
        pillar_data.get("pillar"),
        (
            "reading_context."
            f"{position}.pillar"
        ),
    )


def _assert_no_api_key(
    value: Any,
) -> None:

    api_key = os.getenv(
        OPENAI_API_KEY_ENV,
        "",
    ).strip()

    if not api_key:
        return

    if isinstance(
        value,
        bytes,
    ):
        assert (
            api_key.encode(
                "utf-8"
            )
            not in value
        )

        return

    if isinstance(
        value,
        str,
    ):
        text = value

    else:
        text = json.dumps(
            value,
            ensure_ascii=False,
            default=str,
        )

    assert (
        api_key
        not in text
    )


def _assert_no_private_prompt_fields(
    value: Any,
) -> None:

    text = json.dumps(
        value,
        ensure_ascii=False,
        default=str,
    )

    forbidden = (
        '"api_key"',
        '"system_prompt"',
        '"user_prompt"',
    )

    for marker in forbidden:
        assert (
            marker
            not in text
        ), (
            "非公開フィールドが"
            "商品データに含まれています: "
            f"{marker}"
        )


# ============================================================
# LIVE availability
# ============================================================


LIVE_AVAILABLE = (
    has_openai_api_key()
)


pytestmark = pytest.mark.skipif(
    not LIVE_AVAILABLE,
    reason=(
        f"{OPENAI_API_KEY_ENV} "
        "が設定されていないため"
        "LIVE PDFテストをskipします。"
    ),
)


# ============================================================
# Session fixtures
# ============================================================


@pytest.fixture(
    scope="module"
)
def live_model() -> str:

    model = (
        MODEL
        or get_default_model()
    )

    return _require_non_empty_string(
        model,
        "model",
    )


@pytest.fixture(
    scope="module"
)
def live_request():

    return SimpleNamespace(
        birth_date=BIRTH_DATE,
        birth_time=BIRTH_TIME,
        birth_place=BIRTH_PLACE,
        gender=GENDER,
    )


@pytest.fixture(
    scope="module"
)
def live_chart_result(
    live_request,
):

    result = calculate_chart(
        live_request,
        target_datetime=(
            TARGET_DATETIME
        ),
    )

    assert isinstance(
        result,
        Mapping,
    )

    return result


@pytest.fixture(
    scope="module"
)
def live_reading_context(
    live_chart_result,
):

    result = (
        build_reading_context(
            live_chart_result
        )
    )

    assert isinstance(
        result,
        Mapping,
    )

    return result


@pytest.fixture(
    scope="module"
)
def live_generation_result(
    live_reading_context,
    live_model,
):

    result = generate_reading(
        live_reading_context,
        model=live_model,
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

    assert isinstance(
        result,
        ReadingGenerationResult,
    )

    return result


@pytest.fixture(
    scope="module"
)
def live_product(
    live_reading_context,
    live_generation_result,
):

    product = (
        build_reading_product(
            live_reading_context,
            live_generation_result,
            title=PRODUCT_TITLE,
            sections=SECTIONS,
        )
    )

    assert isinstance(
        product,
        ReadingProduct,
    )

    return product


@pytest.fixture(
    scope="module"
)
def live_pdf_path(
    tmp_path_factory,
    live_product,
):

    output_dir = (
        tmp_path_factory.mktemp(
            "reading_pdf_live"
        )
    )

    output_path = (
        output_dir
        / "reading_product_live.pdf"
    )

    result = (
        write_reading_product_pdf(
            live_product,
            output_path,
            document_title=(
                PDF_DOCUMENT_TITLE
            ),
        )
    )

    assert isinstance(
        result,
        Path,
    )

    return result


@pytest.fixture(
    scope="module"
)
def live_pdf_bytes(
    live_pdf_path,
):

    return (
        live_pdf_path.read_bytes()
    )


# ============================================================
# 1. Chart
# ============================================================


@pytest.mark.parametrize(
    (
        "position",
        "expected",
    ),
    EXPECTED_PILLARS.items(),
)
def test_pdf_live_chart_pillars(
    live_chart_result,
    position,
    expected,
):

    actual = _get_pillar(
        live_chart_result,
        position,
    )

    assert (
        actual
        == expected
    )


def test_pdf_live_chart_day_master(
    live_chart_result,
):

    day_master = _require_mapping(
        live_chart_result.get(
            "day_master"
        ),
        "day_master",
    )

    assert (
        day_master.get("stem")
        == EXPECTED_DAY_MASTER
    )


# ============================================================
# 2. reading_context
# ============================================================


@pytest.mark.parametrize(
    (
        "position",
        "expected",
    ),
    EXPECTED_PILLARS.items(),
)
def test_pdf_live_context_pillars(
    live_reading_context,
    position,
    expected,
):

    actual = (
        _get_context_pillar(
            live_reading_context,
            position,
        )
    )

    assert (
        actual
        == expected
    )


def test_pdf_live_context_day_master(
    live_reading_context,
):

    day_master = _require_mapping(
        live_reading_context.get(
            "day_master"
        ),
        "reading_context.day_master",
    )

    assert (
        day_master.get("stem")
        == EXPECTED_DAY_MASTER
    )


def test_pdf_live_context_status(
    live_reading_context,
):

    assert (
        live_reading_context.get(
            "status"
        )
        == "ready_for_ai_reading"
    )


def test_pdf_live_context_annual_luck(
    live_reading_context,
):

    luck = _require_mapping(
        live_reading_context.get(
            "luck"
        ),
        "reading_context.luck",
    )

    annual_luck = _require_mapping(
        luck.get(
            "annual_luck"
        ),
        (
            "reading_context."
            "luck.annual_luck"
        ),
    )

    assert (
        annual_luck.get(
            "ganzhi"
        )
        == EXPECTED_ANNUAL_GANZHI
    )


# ============================================================
# 3. OpenAI generation
# ============================================================


def test_pdf_live_generation_completed(
    live_generation_result,
):

    assert (
        live_generation_result.status
        == "completed"
    )


def test_pdf_live_response_completed(
    live_generation_result,
):

    assert (
        live_generation_result
        .response_status
        in (
            None,
            "completed",
        )
    )


def test_pdf_live_response_id_exists(
    live_generation_result,
):

    response_id = (
        live_generation_result
        .response_id
    )

    if response_id is not None:
        _require_non_empty_string(
            response_id,
            "response_id",
        )


def test_pdf_live_generation_is_json(
    live_generation_result,
):

    assert (
        live_generation_result
        .output_format
        == "json"
    )

    assert isinstance(
        live_generation_result
        .parsed,
        Mapping,
    )


def test_pdf_live_generation_summary(
    live_generation_result,
):

    parsed = _require_mapping(
        live_generation_result.parsed,
        "parsed",
    )

    _require_non_empty_string(
        parsed.get("summary"),
        "summary",
    )


def test_pdf_live_generation_disclaimer(
    live_generation_result,
):

    parsed = _require_mapping(
        live_generation_result.parsed,
        "parsed",
    )

    disclaimer = (
        _require_non_empty_string(
            parsed.get(
                "disclaimer"
            ),
            "disclaimer",
        )
    )

    assert (
        "医学" in disclaimer
        or "医療" in disclaimer
    )

    assert (
        "専門家"
        in disclaimer
    )


def test_pdf_live_generation_sections(
    live_generation_result,
):

    parsed = _require_mapping(
        live_generation_result.parsed,
        "parsed",
    )

    sections = _require_mapping(
        parsed.get("sections"),
        "sections",
    )

    assert (
        tuple(
            sections.keys()
        )
        == SECTIONS
    )


@pytest.mark.parametrize(
    "section_key",
    SECTIONS,
)
def test_pdf_live_each_section_has_content(
    live_generation_result,
    section_key,
):

    parsed = _require_mapping(
        live_generation_result.parsed,
        "parsed",
    )

    sections = _require_mapping(
        parsed.get("sections"),
        "sections",
    )

    section = _require_mapping(
        sections.get(
            section_key
        ),
        f"sections.{section_key}",
    )

    _require_non_empty_string(
        section.get("title"),
        f"{section_key}.title",
    )

    _require_non_empty_string(
        section.get("summary"),
        f"{section_key}.summary",
    )

    _require_non_empty_string(
        section.get("detail"),
        f"{section_key}.detail",
    )

    evidence = section.get(
        "evidence"
    )

    advice = section.get(
        "advice"
    )

    assert isinstance(
        evidence,
        (list, tuple),
    )

    assert evidence

    assert isinstance(
        advice,
        (list, tuple),
    )

    assert advice


# ============================================================
# 4. ReadingProduct
# ============================================================


def test_pdf_live_product_ready(
    live_product,
):

    assert (
        live_product.status
        == "ready"
    )


def test_pdf_live_product_has_expected_pillars(
    live_product,
):

    sequence = (
        live_product
        .chart_summary
        .get(
            "pillar_sequence"
        )
    )

    assert (
        tuple(sequence)
        == EXPECTED_PILLAR_SEQUENCE
    )


def test_pdf_live_product_day_master(
    live_product,
):

    day_master = (
        _require_mapping(
            live_product
            .chart_summary
            .get(
                "day_master"
            ),
            (
                "product."
                "day_master"
            ),
        )
    )

    assert (
        day_master.get("stem")
        == EXPECTED_DAY_MASTER
    )


def test_pdf_live_product_annual_luck(
    live_product,
):

    annual_luck = (
        _require_mapping(
            live_product
            .chart_summary
            .get(
                "annual_luck"
            ),
            (
                "product."
                "annual_luck"
            ),
        )
    )

    assert (
        annual_luck.get(
            "ganzhi"
        )
        == EXPECTED_ANNUAL_GANZHI
    )


def test_pdf_live_product_has_eight_sections(
    live_product,
):

    assert (
        len(
            live_product.sections
        )
        == 8
    )


def test_pdf_live_product_section_order(
    live_product,
):

    actual = tuple(
        section.get("key")
        for section
        in live_product.sections
    )

    assert (
        actual
        == SECTIONS
    )


def test_pdf_live_product_summary_not_empty(
    live_product,
):

    _require_non_empty_string(
        live_product.summary,
        "product.summary",
    )


def test_pdf_live_product_disclaimer_not_empty(
    live_product,
):

    _require_non_empty_string(
        live_product.disclaimer,
        "product.disclaimer",
    )


# ============================================================
# 5. PDF generation
# ============================================================


def test_pdf_live_file_exists(
    live_pdf_path,
):

    assert (
        live_pdf_path.exists()
    )


def test_pdf_live_is_file(
    live_pdf_path,
):

    assert (
        live_pdf_path.is_file()
    )


def test_pdf_live_suffix(
    live_pdf_path,
):

    assert (
        live_pdf_path.suffix.lower()
        == ".pdf"
    )


def test_pdf_live_not_empty(
    live_pdf_path,
):

    assert (
        live_pdf_path.stat()
        .st_size
        > 0
    )


def test_pdf_live_has_minimum_realistic_size(
    live_pdf_path,
):

    assert (
        live_pdf_path.stat()
        .st_size
        >= MIN_PDF_SIZE_BYTES
    )


def test_pdf_live_magic_header(
    live_pdf_bytes,
):

    assert (
        live_pdf_bytes.startswith(
            b"%PDF-"
        )
    )


def test_pdf_live_has_pdf_eof_marker(
    live_pdf_bytes,
):

    tail = (
        live_pdf_bytes[
            -2048:
        ]
    )

    assert (
        b"%%EOF"
        in tail
    )


# ============================================================
# 6. Security
# ============================================================


def test_pdf_live_product_does_not_expose_api_key(
    live_product,
):

    _assert_no_api_key(
        live_product.to_dict()
    )


def test_pdf_live_product_does_not_expose_private_prompts(
    live_product,
):

    _assert_no_private_prompt_fields(
        live_product.to_dict()
    )


def test_pdf_live_pdf_does_not_expose_api_key(
    live_pdf_bytes,
):

    _assert_no_api_key(
        live_pdf_bytes
    )


# ============================================================
# 7. Usage
# ============================================================


def test_pdf_live_usage_valid_when_present(
    live_generation_result,
):

    usage = (
        live_generation_result
        .usage
    )

    if usage is None:
        return

    assert isinstance(
        usage,
        Mapping,
    )

    for key in (
        "input_tokens",
        "output_tokens",
        "total_tokens",
    ):

        if key not in usage:
            continue

        value = usage[key]

        assert isinstance(
            value,
            int,
        )

        assert (
            value >= 0
        )


# ============================================================
# 8. PDF metadata
# ============================================================


def test_pdf_live_metadata(
):

    metadata = (
        get_reading_pdf_metadata()
    )

    assert (
        metadata.get(
            "version"
        )
        == READING_PDF_VERSION
    )

    assert (
        metadata.get(
            "method"
        )
        == READING_PDF_METHOD
    )

    assert (
        metadata.get(
            "status"
        )
        == READING_PDF_STATUS
    )


def test_pdf_live_does_not_recalculate_astrology(
):

    metadata = (
        get_reading_pdf_metadata()
    )

    assert (
        metadata.get(
            "recalculates_astrology"
        )
        is False
    )


def test_pdf_live_does_not_rewrite_ai_reading(
):

    metadata = (
        get_reading_pdf_metadata()
    )

    assert (
        metadata.get(
            "rewrites_ai_reading"
        )
        is False
    )


def test_pdf_live_metadata_does_not_expose_api_key(
):

    metadata = (
        get_reading_pdf_metadata()
    )

    assert (
        metadata.get(
            "exposes_api_key"
        )
        is False
    )


# ============================================================
# 9. Cross-layer consistency
# ============================================================


@pytest.mark.parametrize(
    "position",
    (
        "year",
        "month",
        "day",
        "hour",
    ),
)
def test_pdf_live_chart_and_context_same_pillars(
    live_chart_result,
    live_reading_context,
    position,
):

    chart_pillar = (
        _get_pillar(
            live_chart_result,
            position,
        )
    )

    context_pillar = (
        _get_context_pillar(
            live_reading_context,
            position,
        )
    )

    assert (
        chart_pillar
        == context_pillar
    )


def test_pdf_live_context_and_product_same_day_master(
    live_reading_context,
    live_product,
):

    context_day_master = (
        _require_mapping(
            live_reading_context.get(
                "day_master"
            ),
            (
                "reading_context."
                "day_master"
            ),
        )
    )

    product_day_master = (
        _require_mapping(
            live_product
            .chart_summary
            .get(
                "day_master"
            ),
            (
                "product."
                "day_master"
            ),
        )
    )

    assert (
        context_day_master.get(
            "stem"
        )
        == product_day_master.get(
            "stem"
        )
        == EXPECTED_DAY_MASTER
    )


def test_pdf_live_context_and_product_same_annual_luck(
    live_reading_context,
    live_product,
):

    luck = _require_mapping(
        live_reading_context.get(
            "luck"
        ),
        "reading_context.luck",
    )

    context_annual = (
        _require_mapping(
            luck.get(
                "annual_luck"
            ),
            (
                "reading_context."
                "annual_luck"
            ),
        )
    )

    product_annual = (
        _require_mapping(
            live_product
            .chart_summary
            .get(
                "annual_luck"
            ),
            (
                "product."
                "annual_luck"
            ),
        )
    )

    assert (
        context_annual.get(
            "ganzhi"
        )
        == product_annual.get(
            "ganzhi"
        )
        == EXPECTED_ANNUAL_GANZHI
    )


# ============================================================
# 10. Final gate
# ============================================================


def test_reading_pdf_live_v1_final_gate(
    live_chart_result,
    live_reading_context,
    live_generation_result,
    live_product,
    live_pdf_path,
    live_pdf_bytes,
):

    # --------------------------------------------------------
    # Chart
    # --------------------------------------------------------

    actual_pillars = tuple(
        _get_pillar(
            live_chart_result,
            position,
        )
        for position
        in (
            "year",
            "month",
            "day",
            "hour",
        )
    )

    assert (
        actual_pillars
        == EXPECTED_PILLAR_SEQUENCE
    )

    # --------------------------------------------------------
    # Context
    # --------------------------------------------------------

    context_pillars = tuple(
        _get_context_pillar(
            live_reading_context,
            position,
        )
        for position
        in (
            "year",
            "month",
            "day",
            "hour",
        )
    )

    assert (
        context_pillars
        == EXPECTED_PILLAR_SEQUENCE
    )

    assert (
        live_reading_context.get(
            "status"
        )
        == "ready_for_ai_reading"
    )

    # --------------------------------------------------------
    # OpenAI
    # --------------------------------------------------------

    assert (
        live_generation_result.status
        == "completed"
    )

    assert (
        live_generation_result
        .response_status
        in (
            None,
            "completed",
        )
    )

    assert isinstance(
        live_generation_result.parsed,
        Mapping,
    )

    # --------------------------------------------------------
    # Product
    # --------------------------------------------------------

    assert (
        live_product.status
        == "ready"
    )

    assert (
        len(
            live_product.sections
        )
        == 8
    )

    assert (
        tuple(
            live_product
            .chart_summary
            .get(
                "pillar_sequence"
            )
        )
        == EXPECTED_PILLAR_SEQUENCE
    )

    # --------------------------------------------------------
    # PDF
    # --------------------------------------------------------

    assert (
        live_pdf_path.exists()
    )

    assert (
        live_pdf_path.is_file()
    )

    assert (
        live_pdf_path.suffix.lower()
        == ".pdf"
    )

    assert (
        live_pdf_path.stat()
        .st_size
        >= MIN_PDF_SIZE_BYTES
    )

    assert (
        live_pdf_bytes.startswith(
            b"%PDF-"
        )
    )

    assert (
        b"%%EOF"
        in live_pdf_bytes[
            -2048:
        ]
    )

    # --------------------------------------------------------
    # Security
    # --------------------------------------------------------

    _assert_no_api_key(
        live_product.to_dict()
    )

    _assert_no_api_key(
        live_pdf_bytes
    )

    _assert_no_private_prompt_fields(
        live_product.to_dict()
    )

    # --------------------------------------------------------
    # PDF layer contract
    # --------------------------------------------------------

    metadata = (
        get_reading_pdf_metadata()
    )

    assert (
        metadata.get(
            "version"
        )
        == "reading_pdf_v1"
    )

    assert (
        metadata.get(
            "status"
        )
        == "ready"
    )

    assert (
        metadata.get(
            "recalculates_astrology"
        )
        is False
    )

    assert (
        metadata.get(
            "rewrites_ai_reading"
        )
        is False
    )

    assert (
        metadata.get(
            "exposes_api_key"
        )
        is False
    )
