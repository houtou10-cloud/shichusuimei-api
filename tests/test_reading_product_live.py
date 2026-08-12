"""
tests/test_reading_product_live.py

四柱推命AI鑑定の商品化レイヤーを、
実際のOpenAI Responses APIまで含めて確認するLIVE E2Eテスト。

流れ
----
calculate_chart
    ↓
build_reading_context
    ↓
generate_reading
    ↓
build_reading_product
    ↓
ReadingProduct

目的
----
- 実命式から商品データまで一気通貫で生成できること。
- AIが計算済み命式を書き換えないこと。
- 現行JSON契約の detail / evidence / advice が商品側へ残ること。
- 商品データがJSON serializableであること。
- APIキーや内部promptを商品データへ露出しないこと。
- 健康・将来表現の安全性を最低限確認すること。

注意
----
このファイルはLIVEテストです。
実際にOpenAI APIを呼び出すため料金が発生します。

通常の pytest -q では実行しません。

実行例:
    $env:PYTHONPATH="."
    $env:RUN_OPENAI_LIVE_TESTS="1"
    pytest .\\tests\\test_reading_product_live.py -v

OPENAI_API_KEY が未設定ならskipします。

Version
-------
reading_product_live_v1
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Mapping

import pytest

from engine.reading_context import (
    build_reading_context,
)
from engine.reading_generator import (
    ReadingGenerationResult,
    generate_reading,
    get_default_model,
)
from engine.reading_product import (
    DEFAULT_SECTION_ORDER,
    READING_PRODUCT_METHOD,
    READING_PRODUCT_STATUS,
    READING_PRODUCT_VERSION,
    ReadingProduct,
    build_reading_product,
)


# ============================================================
# LIVE settings
# ============================================================


LIVE_ENV_NAME = "RUN_OPENAI_LIVE_TESTS"

LIVE_TEST_SECTIONS = tuple(
    DEFAULT_SECTION_ORDER
)

LIVE_TEST_MAX_OUTPUT_TOKENS = 7000

EXPECTED_PILLARS = {
    "year": "乙丑",
    "month": "癸未",
    "day": "丁巳",
    "hour": "辛亥",
}

EXPECTED_SEQUENCE = [
    "乙丑",
    "癸未",
    "丁巳",
    "辛亥",
]

EXPECTED_DAY_MASTER = "丁"

EXPECTED_BIRTH_DATE = "1985-07-17"
EXPECTED_BIRTH_TIME = "21:50"
EXPECTED_BIRTH_PLACE = "石川県"

EXPECTED_ANNUAL_YEAR = 2026
EXPECTED_ANNUAL_GANZHI = "丙午"


# ============================================================
# Helpers
# ============================================================


def _live_enabled() -> bool:
    value = os.getenv(
        LIVE_ENV_NAME,
        "",
    )

    return (
        value.strip().lower()
        in {
            "1",
            "true",
            "yes",
            "on",
        }
    )


def _require_live_environment() -> None:
    if not _live_enabled():
        pytest.skip(
            f"{LIVE_ENV_NAME}=1 "
            "のときだけLIVEテストを実行します。"
        )

    api_key = os.getenv(
        "OPENAI_API_KEY",
        "",
    ).strip()

    if not api_key:
        pytest.skip(
            "OPENAI_API_KEY が未設定です。"
        )


def _as_mapping(
    value: Any,
    label: str,
) -> Mapping[str, Any]:
    assert isinstance(
        value,
        Mapping,
    ), (
        f"{label} はMappingである必要があります。"
        f" actual={type(value)!r}"
    )

    return value


def _get_pillar_text(
    context: Mapping[str, Any],
    position: str,
) -> str:
    natal_chart = _as_mapping(
        context.get(
            "natal_chart"
        ),
        "natal_chart",
    )

    pillars = _as_mapping(
        natal_chart.get(
            "pillars"
        ),
        "natal_chart.pillars",
    )

    pillar = _as_mapping(
        pillars.get(
            position
        ),
        f"pillars.{position}",
    )

    value = pillar.get(
        "pillar"
    )

    assert isinstance(
        value,
        str,
    )

    return value


def _get_product_section(
    product: ReadingProduct,
    key: str,
) -> Mapping[str, Any]:
    for section in product.sections:
        if (
            section.get(
                "key"
            )
            == key
        ):
            return section

    raise AssertionError(
        f"商品セクションが見つかりません: {key}"
    )


def _serialize_product(
    product: ReadingProduct,
) -> str:
    return json.dumps(
        product.to_dict(),
        ensure_ascii=False,
        sort_keys=True,
    )


def _contains_any(
    text: str,
    candidates: tuple[str, ...],
) -> bool:
    return any(
        candidate in text
        for candidate in candidates
    )


def _extract_chart_result() -> Dict[str, Any]:
    """
    現行プロジェクトで使用している
    calculate_chart の入口を遅延importする。

    既存テスト群と同様に、APIレイヤーの
    calculate_chart を優先する。
    """

    try:
        from main import (
            ChartRequest,
            calculate_chart,
        )
    except ImportError as exc:
        raise AssertionError(
            "main.ChartRequest / "
            "main.calculate_chart をimportできません。"
        ) from exc

    request = ChartRequest(
        birth_date=EXPECTED_BIRTH_DATE,
        birth_time=EXPECTED_BIRTH_TIME,
        birth_place=EXPECTED_BIRTH_PLACE,
        gender="female",
    )

    result = calculate_chart(
        request
    )

    if hasattr(
        result,
        "model_dump",
    ):
        result = result.model_dump()

    elif hasattr(
        result,
        "dict",
    ):
        result = result.dict()

    assert isinstance(
        result,
        dict,
    )

    return result


# ============================================================
# Module fixtures
# ============================================================


@pytest.fixture(
    scope="module",
    autouse=True,
)
def require_live_environment():
    """
    このmodule全体をLIVE専用にする。
    """

    _require_live_environment()


@pytest.fixture(
    scope="module",
)
def live_chart_result() -> Dict[str, Any]:
    """
    命式計算はmodule内で1回だけ行う。
    """

    return _extract_chart_result()


@pytest.fixture(
    scope="module",
)
def live_reading_context(
    live_chart_result,
) -> Dict[str, Any]:
    """
    計算済み命式からreading_contextを生成する。
    """

    context = build_reading_context(
        live_chart_result,
        validate=True,
    )

    assert isinstance(
        context,
        dict,
    )

    return context


@pytest.fixture(
    scope="module",
)
def live_generation_result(
    live_reading_context,
) -> ReadingGenerationResult:
    """
    OpenAI APIはmodule内で1回だけ呼ぶ。

    多数のassertテストで同じ結果を共有することで、
    API料金と実行時間を抑える。
    """

    result = generate_reading(
        live_reading_context,
        model=get_default_model(),
        sections=LIVE_TEST_SECTIONS,
        output_format="json",
        max_output_tokens=(
            LIVE_TEST_MAX_OUTPUT_TOKENS
        ),
        store=False,
    )

    assert isinstance(
        result,
        ReadingGenerationResult,
    )

    return result


@pytest.fixture(
    scope="module",
)
def live_product(
    live_reading_context,
    live_generation_result,
) -> ReadingProduct:
    """
    実AI生成結果を商品化する。
    """

    return build_reading_product(
        live_reading_context,
        live_generation_result,
        sections=LIVE_TEST_SECTIONS,
    )


@pytest.fixture(
    scope="module",
)
def live_product_dict(
    live_product,
) -> Dict[str, Any]:
    return live_product.to_dict()


# ============================================================
# Chart calculation gate
# ============================================================


def test_product_live_chart_result_is_mapping(
    live_chart_result,
):
    assert isinstance(
        live_chart_result,
        dict,
    )


def test_product_live_context_is_mapping(
    live_reading_context,
):
    assert isinstance(
        live_reading_context,
        dict,
    )


@pytest.mark.parametrize(
    (
        "position",
        "expected",
    ),
    tuple(
        EXPECTED_PILLARS.items()
    ),
)
def test_product_live_context_pillars(
    live_reading_context,
    position,
    expected,
):
    assert (
        _get_pillar_text(
            live_reading_context,
            position,
        )
        == expected
    )


def test_product_live_context_sequence(
    live_reading_context,
):
    natal_chart = _as_mapping(
        live_reading_context[
            "natal_chart"
        ],
        "natal_chart",
    )

    assert (
        natal_chart[
            "pillar_sequence"
        ]
        == EXPECTED_SEQUENCE
    )


def test_product_live_context_day_master(
    live_reading_context,
):
    day_master = _as_mapping(
        live_reading_context[
            "day_master"
        ],
        "day_master",
    )

    assert (
        day_master[
            "stem"
        ]
        == EXPECTED_DAY_MASTER
    )

    assert (
        day_master[
            "day_pillar"
        ]
        == EXPECTED_PILLARS[
            "day"
        ]
    )


# ============================================================
# OpenAI generation gate
# ============================================================


def test_product_live_generation_result_type(
    live_generation_result,
):
    assert isinstance(
        live_generation_result,
        ReadingGenerationResult,
    )


def test_product_live_generation_completed(
    live_generation_result,
):
    assert (
        live_generation_result.status
        == "completed"
    )


def test_product_live_generation_response_status(
    live_generation_result,
):
    assert (
        live_generation_result.response_status
        == "completed"
    )


def test_product_live_generation_has_response_id(
    live_generation_result,
):
    response_id = (
        live_generation_result.response_id
    )

    assert isinstance(
        response_id,
        str,
    )

    assert response_id.strip()


def test_product_live_generation_is_json(
    live_generation_result,
):
    assert (
        live_generation_result.output_format
        == "json"
    )

    assert isinstance(
        live_generation_result.parsed,
        dict,
    )


def test_product_live_generation_has_all_sections(
    live_generation_result,
):
    assert (
        live_generation_result.sections
        == LIVE_TEST_SECTIONS
    )

    parsed = _as_mapping(
        live_generation_result.parsed,
        "parsed",
    )

    sections = _as_mapping(
        parsed[
            "sections"
        ],
        "parsed.sections",
    )

    assert set(
        sections.keys()
    ) == set(
        LIVE_TEST_SECTIONS
    )


def test_product_live_generation_summary_not_empty(
    live_generation_result,
):
    parsed = _as_mapping(
        live_generation_result.parsed,
        "parsed",
    )

    summary = parsed[
        "summary"
    ]

    assert isinstance(
        summary,
        str,
    )

    assert summary.strip()


def test_product_live_generation_disclaimer_not_empty(
    live_generation_result,
):
    parsed = _as_mapping(
        live_generation_result.parsed,
        "parsed",
    )

    disclaimer = parsed[
        "disclaimer"
    ]

    assert isinstance(
        disclaimer,
        str,
    )

    assert disclaimer.strip()


# ============================================================
# ReadingProduct contract
# ============================================================


def test_product_live_result_type(
    live_product,
):
    assert isinstance(
        live_product,
        ReadingProduct,
    )


def test_product_live_schema_version(
    live_product,
):
    assert (
        live_product.schema_version
        == READING_PRODUCT_VERSION
    )


def test_product_live_method(
    live_product,
):
    assert (
        live_product.method
        == READING_PRODUCT_METHOD
    )


def test_product_live_status(
    live_product,
):
    assert (
        live_product.status
        == READING_PRODUCT_STATUS
    )


def test_product_live_title_not_empty(
    live_product,
):
    assert isinstance(
        live_product.title,
        str,
    )

    assert live_product.title.strip()


def test_product_live_summary_not_empty(
    live_product,
):
    assert isinstance(
        live_product.summary,
        str,
    )

    assert live_product.summary.strip()


def test_product_live_disclaimer_not_empty(
    live_product,
):
    assert isinstance(
        live_product.disclaimer,
        str,
    )

    assert live_product.disclaimer.strip()


# ============================================================
# Subject preservation
# ============================================================


def test_product_live_subject_birth_date(
    live_product,
):
    assert (
        live_product.subject[
            "birth_date"
        ]
        == EXPECTED_BIRTH_DATE
    )


def test_product_live_subject_birth_time(
    live_product,
):
    assert (
        live_product.subject[
            "birth_time"
        ]
        == EXPECTED_BIRTH_TIME
    )


def test_product_live_subject_birth_place(
    live_product,
):
    assert (
        live_product.subject[
            "birth_place"
        ]
        == EXPECTED_BIRTH_PLACE
    )


def test_product_live_subject_gender(
    live_product,
):
    assert (
        live_product.subject[
            "gender"
        ]
        == "female"
    )


# ============================================================
# Chart preservation
# ============================================================


def test_product_live_pillar_sequence_unchanged(
    live_product,
):
    assert (
        live_product.chart_summary[
            "pillar_sequence"
        ]
        == EXPECTED_SEQUENCE
    )


@pytest.mark.parametrize(
    (
        "position",
        "expected",
    ),
    tuple(
        EXPECTED_PILLARS.items()
    ),
)
def test_product_live_each_pillar_unchanged(
    live_product,
    position,
    expected,
):
    assert (
        live_product.chart_summary[
            "pillars"
        ][
            position
        ][
            "pillar"
        ]
        == expected
    )


def test_product_live_day_master_unchanged(
    live_product,
):
    assert (
        live_product.chart_summary[
            "day_master"
        ][
            "stem"
        ]
        == EXPECTED_DAY_MASTER
    )

    assert (
        live_product.chart_summary[
            "day_master"
        ][
            "day_pillar"
        ]
        == EXPECTED_PILLARS[
            "day"
        ]
    )


def test_product_live_strength_has_content(
    live_product,
):
    strength = _as_mapping(
        live_product.chart_summary[
            "strength"
        ],
        "chart_summary.strength",
    )

    assert strength.get(
        "label"
    )

    assert (
        strength.get(
            "final_score"
        )
        is not None
    )


def test_product_live_pattern_has_content(
    live_product,
):
    pattern = _as_mapping(
        live_product.chart_summary[
            "pattern"
        ],
        "chart_summary.pattern",
    )

    assert pattern.get(
        "primary_pattern"
    )


def test_product_live_useful_gods_has_content(
    live_product,
):
    useful = _as_mapping(
        live_product.chart_summary[
            "useful_gods"
        ],
        "chart_summary.useful_gods",
    )

    assert useful.get(
        "primary_useful_element"
    )


def test_product_live_current_luck_has_content(
    live_product,
):
    current = _as_mapping(
        live_product.chart_summary[
            "current_luck"
        ],
        "chart_summary.current_luck",
    )

    assert current.get(
        "ganzhi"
    )


def test_product_live_annual_luck_year(
    live_product,
):
    annual = _as_mapping(
        live_product.chart_summary[
            "annual_luck"
        ],
        "chart_summary.annual_luck",
    )

    assert (
        annual[
            "year"
        ]
        == EXPECTED_ANNUAL_YEAR
    )


def test_product_live_annual_luck_ganzhi(
    live_product,
):
    annual = _as_mapping(
        live_product.chart_summary[
            "annual_luck"
        ],
        "chart_summary.annual_luck",
    )

    assert (
        annual[
            "ganzhi"
        ]
        == EXPECTED_ANNUAL_GANZHI
    )


# ============================================================
# Section contract
# ============================================================


def test_product_live_has_eight_sections(
    live_product,
):
    assert (
        len(
            live_product.sections
        )
        == len(
            LIVE_TEST_SECTIONS
        )
    )


def test_product_live_section_order(
    live_product,
):
    assert tuple(
        section[
            "key"
        ]
        for section
        in live_product.sections
    ) == LIVE_TEST_SECTIONS


@pytest.mark.parametrize(
    "section_key",
    LIVE_TEST_SECTIONS,
)
def test_product_live_section_contract(
    live_product,
    section_key,
):
    section = _get_product_section(
        live_product,
        section_key,
    )

    assert set(
        section.keys()
    ) == {
        "key",
        "title",
        "summary",
        "detail",
        "evidence",
        "advice",
    }


@pytest.mark.parametrize(
    "section_key",
    LIVE_TEST_SECTIONS,
)
def test_product_live_section_title_not_empty(
    live_product,
    section_key,
):
    section = _get_product_section(
        live_product,
        section_key,
    )

    assert isinstance(
        section[
            "title"
        ],
        str,
    )

    assert section[
        "title"
    ].strip()


@pytest.mark.parametrize(
    "section_key",
    LIVE_TEST_SECTIONS,
)
def test_product_live_section_summary_not_empty(
    live_product,
    section_key,
):
    section = _get_product_section(
        live_product,
        section_key,
    )

    assert isinstance(
        section[
            "summary"
        ],
        str,
    )

    assert section[
        "summary"
    ].strip()


@pytest.mark.parametrize(
    "section_key",
    LIVE_TEST_SECTIONS,
)
def test_product_live_section_detail_not_empty(
    live_product,
    section_key,
):
    section = _get_product_section(
        live_product,
        section_key,
    )

    assert isinstance(
        section[
            "detail"
        ],
        str,
    )

    assert section[
        "detail"
    ].strip()


@pytest.mark.parametrize(
    "section_key",
    LIVE_TEST_SECTIONS,
)
def test_product_live_evidence_has_content(
    live_product,
    section_key,
):
    section = _get_product_section(
        live_product,
        section_key,
    )

    evidence = section[
        "evidence"
    ]

    assert isinstance(
        evidence,
        list,
    )

    assert evidence

    assert all(
        isinstance(
            item,
            str,
        )
        and item.strip()
        for item in evidence
    )


@pytest.mark.parametrize(
    "section_key",
    LIVE_TEST_SECTIONS,
)
def test_product_live_advice_has_content(
    live_product,
    section_key,
):
    section = _get_product_section(
        live_product,
        section_key,
    )

    advice = section[
        "advice"
    ]

    assert isinstance(
        advice,
        list,
    )

    assert advice

    assert all(
        isinstance(
            item,
            str,
        )
        and item.strip()
        for item in advice
    )


@pytest.mark.parametrize(
    "section_key",
    LIVE_TEST_SECTIONS,
)
def test_product_live_uses_detail_not_reading(
    live_product,
    section_key,
):
    section = _get_product_section(
        live_product,
        section_key,
    )

    assert (
        "detail"
        in section
    )

    assert (
        "reading"
        not in section
    )


# ============================================================
# AI → Product preservation
# ============================================================


@pytest.mark.parametrize(
    "section_key",
    LIVE_TEST_SECTIONS,
)
def test_product_live_detail_matches_generation(
    live_product,
    live_generation_result,
    section_key,
):
    parsed = _as_mapping(
        live_generation_result.parsed,
        "parsed",
    )

    generated_sections = _as_mapping(
        parsed[
            "sections"
        ],
        "parsed.sections",
    )

    generated = _as_mapping(
        generated_sections[
            section_key
        ],
        (
            "parsed.sections."
            f"{section_key}"
        ),
    )

    product_section = (
        _get_product_section(
            live_product,
            section_key,
        )
    )

    assert (
        product_section[
            "detail"
        ]
        == generated[
            "detail"
        ]
    )


@pytest.mark.parametrize(
    "section_key",
    LIVE_TEST_SECTIONS,
)
def test_product_live_summary_matches_generation(
    live_product,
    live_generation_result,
    section_key,
):
    parsed = _as_mapping(
        live_generation_result.parsed,
        "parsed",
    )

    generated = _as_mapping(
        parsed[
            "sections"
        ][
            section_key
        ],
        (
            "parsed.sections."
            f"{section_key}"
        ),
    )

    product_section = (
        _get_product_section(
            live_product,
            section_key,
        )
    )

    assert (
        product_section[
            "summary"
        ]
        == generated[
            "summary"
        ]
    )


@pytest.mark.parametrize(
    "section_key",
    LIVE_TEST_SECTIONS,
)
def test_product_live_evidence_matches_generation(
    live_product,
    live_generation_result,
    section_key,
):
    parsed = _as_mapping(
        live_generation_result.parsed,
        "parsed",
    )

    generated = _as_mapping(
        parsed[
            "sections"
        ][
            section_key
        ],
        (
            "parsed.sections."
            f"{section_key}"
        ),
    )

    product_section = (
        _get_product_section(
            live_product,
            section_key,
        )
    )

    assert (
        product_section[
            "evidence"
        ]
        == generated[
            "evidence"
        ]
    )


@pytest.mark.parametrize(
    "section_key",
    LIVE_TEST_SECTIONS,
)
def test_product_live_advice_matches_generation(
    live_product,
    live_generation_result,
    section_key,
):
    parsed = _as_mapping(
        live_generation_result.parsed,
        "parsed",
    )

    generated = _as_mapping(
        parsed[
            "sections"
        ][
            section_key
        ],
        (
            "parsed.sections."
            f"{section_key}"
        ),
    )

    product_section = (
        _get_product_section(
            live_product,
            section_key,
        )
    )

    assert (
        product_section[
            "advice"
        ]
        == generated[
            "advice"
        ]
    )


def test_product_live_overall_summary_matches_generation(
    live_product,
    live_generation_result,
):
    parsed = _as_mapping(
        live_generation_result.parsed,
        "parsed",
    )

    assert (
        live_product.summary
        == parsed[
            "summary"
        ]
    )


def test_product_live_disclaimer_matches_generation(
    live_product,
    live_generation_result,
):
    parsed = _as_mapping(
        live_generation_result.parsed,
        "parsed",
    )

    assert (
        live_product.disclaimer
        == parsed[
            "disclaimer"
        ]
    )


# ============================================================
# Product metadata / traceability
# ============================================================


def test_product_live_generation_model(
    live_product,
    live_generation_result,
):
    assert (
        live_product.generation[
            "model"
        ]
        == live_generation_result.model
    )


def test_product_live_generation_response_id(
    live_product,
    live_generation_result,
):
    assert (
        live_product.generation[
            "response_id"
        ]
        == live_generation_result.response_id
    )


def test_product_live_generation_response_status(
    live_product,
    live_generation_result,
):
    assert (
        live_product.generation[
            "response_status"
        ]
        == live_generation_result.response_status
    )


def test_product_live_metadata_no_recalculation(
    live_product,
):
    assert (
        live_product.metadata[
            "recalculates_astrology"
        ]
        is False
    )


def test_product_live_metadata_no_ai_rewrite(
    live_product,
):
    assert (
        live_product.metadata[
            "rewrites_ai_reading"
        ]
        is False
    )


def test_product_live_metadata_has_created_at(
    live_product,
):
    created_at = (
        live_product.metadata[
            "created_at"
        ]
    )

    assert isinstance(
        created_at,
        str,
    )

    assert (
        "T"
        in created_at
    )


# ============================================================
# JSON / serialization
# ============================================================


def test_product_live_to_dict_is_mapping(
    live_product_dict,
):
    assert isinstance(
        live_product_dict,
        dict,
    )


def test_product_live_json_serializable(
    live_product_dict,
):
    text = json.dumps(
        live_product_dict,
        ensure_ascii=False,
    )

    assert isinstance(
        text,
        str,
    )

    assert text.strip()


def test_product_live_json_roundtrip(
    live_product_dict,
):
    text = json.dumps(
        live_product_dict,
        ensure_ascii=False,
    )

    restored = json.loads(
        text
    )

    assert (
        restored[
            "schema_version"
        ]
        == READING_PRODUCT_VERSION
    )

    assert (
        restored[
            "chart_summary"
        ][
            "pillar_sequence"
        ]
        == EXPECTED_SEQUENCE
    )


def test_product_live_to_dict_is_independent_copy(
    live_product,
):
    data = live_product.to_dict()

    data[
        "subject"
    ][
        "birth_place"
    ] = "変更"

    data[
        "chart_summary"
    ][
        "pillar_sequence"
    ][
        0
    ] = "変更"

    assert (
        live_product.subject[
            "birth_place"
        ]
        == EXPECTED_BIRTH_PLACE
    )

    assert (
        live_product.chart_summary[
            "pillar_sequence"
        ][
            0
        ]
        == EXPECTED_SEQUENCE[
            0
        ]
    )


# ============================================================
# Security
# ============================================================


def test_product_live_never_exposes_api_key(
    live_product,
):
    serialized = _serialize_product(
        live_product
    )

    actual_key = os.getenv(
        "OPENAI_API_KEY",
        "",
    ).strip()

    assert (
        "OPENAI_API_KEY"
        not in serialized
    )

    assert (
        '"api_key"'
        not in serialized
    )

    if actual_key:
        assert (
            actual_key
            not in serialized
        )


def test_product_live_never_exposes_raw_prompt(
    live_product,
):
    serialized = _serialize_product(
        live_product
    )

    forbidden_keys = (
        '"system_prompt"',
        '"user_prompt"',
        '"prompt"',
        '"instructions"',
    )

    for key in forbidden_keys:
        assert (
            key
            not in serialized
        )


def test_product_live_generation_metadata_has_no_raw_text(
    live_product,
):
    generation = (
        live_product.generation
    )

    assert (
        "text"
        not in generation
    )

    assert (
        "parsed"
        not in generation
    )


# ============================================================
# Safety quality
# ============================================================


def test_product_live_disclaimer_mentions_non_certainty(
    live_product,
):
    disclaimer = (
        live_product.disclaimer
    )

    assert _contains_any(
        disclaimer,
        (
            "断定",
            "確定",
            "傾向",
            "参考",
            "可能性",
        ),
    )


def test_product_live_health_is_not_empty(
    live_product,
):
    health = _get_product_section(
        live_product,
        "health",
    )

    assert health[
        "detail"
    ].strip()


def test_product_live_health_avoids_obvious_diagnosis_language(
    live_product,
):
    health = _get_product_section(
        live_product,
        "health",
    )

    text = (
        health[
            "summary"
        ]
        + "\n"
        + health[
            "detail"
        ]
    )

    forbidden = (
        "あなたは病気です",
        "必ず発症します",
        "確実に発症します",
        "診断します",
        "治療できます",
        "治ります",
    )

    for phrase in forbidden:
        assert (
            phrase
            not in text
        )


@pytest.mark.parametrize(
    "section_key",
    (
        "current_luck",
        "future_flow",
    ),
)
def test_product_live_future_sections_avoid_obvious_certainty(
    live_product,
    section_key,
):
    section = _get_product_section(
        live_product,
        section_key,
    )

    text = (
        section[
            "summary"
        ]
        + "\n"
        + section[
            "detail"
        ]
    )

    forbidden = (
        "必ず成功します",
        "必ず失敗します",
        "絶対に成功します",
        "絶対に失敗します",
        "確実に起こります",
        "必ず起こります",
    )

    for phrase in forbidden:
        assert (
            phrase
            not in text
        )


# ============================================================
# Usage
# ============================================================


def test_product_live_usage_is_mapping_when_present(
    live_product,
):
    usage = (
        live_product.generation.get(
            "usage"
        )
    )

    if usage is None:
        return

    assert isinstance(
        usage,
        Mapping,
    )


def test_product_live_usage_values_non_negative_when_present(
    live_product,
):
    usage = (
        live_product.generation.get(
            "usage"
        )
    )

    if not isinstance(
        usage,
        Mapping,
    ):
        return

    for key in (
        "input_tokens",
        "output_tokens",
        "total_tokens",
    ):
        value = usage.get(
            key
        )

        if value is None:
            continue

        assert isinstance(
            value,
            int,
        )

        assert (
            value
            >= 0
        )


# ============================================================
# Distinct source / product consistency
# ============================================================


def test_product_live_context_and_product_same_day_master(
    live_reading_context,
    live_product,
):
    source = (
        live_reading_context[
            "day_master"
        ][
            "stem"
        ]
    )

    product = (
        live_product.chart_summary[
            "day_master"
        ][
            "stem"
        ]
    )

    assert (
        product
        == source
    )


@pytest.mark.parametrize(
    "position",
    (
        "year",
        "month",
        "day",
        "hour",
    ),
)
def test_product_live_context_and_product_same_pillars(
    live_reading_context,
    live_product,
    position,
):
    source = _get_pillar_text(
        live_reading_context,
        position,
    )

    product = (
        live_product.chart_summary[
            "pillars"
        ][
            position
        ][
            "pillar"
        ]
    )

    assert (
        product
        == source
    )


def test_product_live_context_and_product_same_strength(
    live_reading_context,
    live_product,
):
    source = (
        live_reading_context[
            "strength"
        ][
            "label"
        ]
    )

    product = (
        live_product.chart_summary[
            "strength"
        ][
            "label"
        ]
    )

    assert (
        product
        == source
    )


def test_product_live_context_and_product_same_pattern(
    live_reading_context,
    live_product,
):
    source = (
        live_reading_context[
            "pattern"
        ][
            "primary_pattern"
        ]
    )

    product = (
        live_product.chart_summary[
            "pattern"
        ][
            "primary_pattern"
        ]
    )

    assert (
        product
        == source
    )


def test_product_live_context_and_product_same_useful_god(
    live_reading_context,
    live_product,
):
    source = (
        live_reading_context[
            "useful_gods"
        ][
            "primary_useful_element"
        ]
    )

    product = (
        live_product.chart_summary[
            "useful_gods"
        ][
            "primary_useful_element"
        ]
    )

    assert (
        product
        == source
    )


# ============================================================
# Final gate
# ============================================================


def test_reading_product_live_v1_final_gate(
    live_reading_context,
    live_generation_result,
    live_product,
):
    """
    reading_product_live_v1 最終品質ゲート。

    ここが通れば、
    実命式
        → reading_context
        → OpenAI
        → ReadingProduct
    の商品化E2Eが成立している。
    """

    # ----------------------------------------
    # Source chart
    # ----------------------------------------

    assert (
        live_reading_context[
            "natal_chart"
        ][
            "pillar_sequence"
        ]
        == EXPECTED_SEQUENCE
    )

    assert (
        live_reading_context[
            "day_master"
        ][
            "stem"
        ]
        == EXPECTED_DAY_MASTER
    )

    # ----------------------------------------
    # Generation
    # ----------------------------------------

    assert isinstance(
        live_generation_result,
        ReadingGenerationResult,
    )

    assert (
        live_generation_result.status
        == "completed"
    )

    assert (
        live_generation_result.output_format
        == "json"
    )

    assert isinstance(
        live_generation_result.parsed,
        dict,
    )

    assert (
        live_generation_result.response_id
    )

    # ----------------------------------------
    # Product
    # ----------------------------------------

    assert isinstance(
        live_product,
        ReadingProduct,
    )

    assert (
        live_product.schema_version
        == READING_PRODUCT_VERSION
    )

    assert (
        live_product.method
        == READING_PRODUCT_METHOD
    )

    assert (
        live_product.status
        == READING_PRODUCT_STATUS
    )

    assert (
        live_product.subject[
            "birth_date"
        ]
        == EXPECTED_BIRTH_DATE
    )

    assert (
        live_product.subject[
            "birth_time"
        ]
        == EXPECTED_BIRTH_TIME
    )

    assert (
        live_product.subject[
            "birth_place"
        ]
        == EXPECTED_BIRTH_PLACE
    )

    # ----------------------------------------
    # Chart invariants
    # ----------------------------------------

    assert (
        live_product.chart_summary[
            "pillar_sequence"
        ]
        == EXPECTED_SEQUENCE
    )

    assert (
        live_product.chart_summary[
            "day_master"
        ][
            "stem"
        ]
        == EXPECTED_DAY_MASTER
    )

    assert (
        live_product.chart_summary[
            "annual_luck"
        ][
            "year"
        ]
        == EXPECTED_ANNUAL_YEAR
    )

    assert (
        live_product.chart_summary[
            "annual_luck"
        ][
            "ganzhi"
        ]
        == EXPECTED_ANNUAL_GANZHI
    )

    # ----------------------------------------
    # Sections
    # ----------------------------------------

    assert (
        len(
            live_product.sections
        )
        == 8
    )

    assert tuple(
        section[
            "key"
        ]
        for section
        in live_product.sections
    ) == LIVE_TEST_SECTIONS

    parsed_sections = (
        live_generation_result.parsed[
            "sections"
        ]
    )

    for section_key in (
        LIVE_TEST_SECTIONS
    ):
        product_section = (
            _get_product_section(
                live_product,
                section_key,
            )
        )

        generated_section = (
            parsed_sections[
                section_key
            ]
        )

        assert (
            product_section[
                "title"
            ]
        )

        assert (
            product_section[
                "summary"
            ]
        )

        assert (
            product_section[
                "detail"
            ]
        )

        assert (
            product_section[
                "evidence"
            ]
        )

        assert (
            product_section[
                "advice"
            ]
        )

        assert (
            "reading"
            not in product_section
        )

        assert (
            product_section[
                "summary"
            ]
            == generated_section[
                "summary"
            ]
        )

        assert (
            product_section[
                "detail"
            ]
            == generated_section[
                "detail"
            ]
        )

        assert (
            product_section[
                "evidence"
            ]
            == generated_section[
                "evidence"
            ]
        )

        assert (
            product_section[
                "advice"
            ]
            == generated_section[
                "advice"
            ]
        )

    # ----------------------------------------
    # Product policy
    # ----------------------------------------

    assert (
        live_product.metadata[
            "recalculates_astrology"
        ]
        is False
    )

    assert (
        live_product.metadata[
            "rewrites_ai_reading"
        ]
        is False
    )

    # ----------------------------------------
    # JSON
    # ----------------------------------------

    data = live_product.to_dict()

    json.dumps(
        data,
        ensure_ascii=False,
    )

    # ----------------------------------------
    # Security
    # ----------------------------------------

    serialized = json.dumps(
        data,
        ensure_ascii=False,
        sort_keys=True,
    )

    assert (
        "OPENAI_API_KEY"
        not in serialized
    )

    assert (
        '"api_key"'
        not in serialized
    )

    assert (
        '"system_prompt"'
        not in serialized
    )

    assert (
        '"user_prompt"'
        not in serialized
    )

    actual_key = os.getenv(
        "OPENAI_API_KEY",
        "",
    ).strip()

    if actual_key:
        assert (
            actual_key
            not in serialized
        )
