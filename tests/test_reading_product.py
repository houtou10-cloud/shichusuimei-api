"""
tests/test_reading_product.py

四柱推命AI鑑定 商品化レイヤー
engine/reading_product.py の非LIVE品質テスト。

目的
----
reading_context
    +
ReadingGenerationResult
    ↓
reading_product.py
    ↓
ReadingProduct
    ↓
PDF / HTML / Web / API向け商品データ

という商品化変換を、
OpenAI APIを一切呼ばずに検証する。

主な検証内容
------------
1. 商品用subjectがreading_contextから正しく抽出される。
2. 四柱・日主・五行・身強身弱・格局・用神・運勢が
   再計算されず、そのまま商品データへ渡る。
3. 現行AI JSON契約
   title / summary / detail / evidence / advice
   を正しく扱う。
4. 8セクションの順序と内容が維持される。
5. 部分セクションにも対応する。
6. AI未生成セクションを商品化しない。
7. JSON以外のReadingGenerationResultを拒否する。
8. parsed欠損・必須キー欠損を拒否する。
9. disclaimer欠損時のfallbackを確認する。
10. APIキー・prompt・生response objectを商品データへ含めない。
11. ReadingProduct.to_dict() がdeepcopyを返す。
12. JSON serializableである。
13. generate_reading_product() が
    build_reading_context() → generate_reading() →
    build_reading_product() の順で接続される。
14. API通信をmockして商品化レイヤーだけ検証する。
15. metadataが「再計算しない」「AI文章を書き換えない」
    方針を保持する。

このファイルは非LIVEテストなので、
OPENAI_API_KEYは不要。
API料金も発生しない。

Version
-------
reading_product_test_v1
"""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, Dict

import pytest

import engine.reading_product as reading_product_module
from engine.reading_generator import (
    ReadingGenerationResult,
)
from engine.reading_product import (
    DEFAULT_DISCLAIMER,
    DEFAULT_PRODUCT_TITLE,
    DEFAULT_SECTION_ORDER,
    READING_PRODUCT_METHOD,
    READING_PRODUCT_STATUS,
    READING_PRODUCT_VERSION,
    SECTION_TITLES,
    ReadingProduct,
    ReadingProductValidationError,
    build_chart_summary,
    build_generation_metadata,
    build_product_metadata,
    build_product_section,
    build_product_sections,
    build_product_subject,
    build_reading_product,
    create_product_from_generation,
    extract_product_disclaimer,
    extract_product_summary,
    generate_reading_product,
    generate_reading_product_dict,
    get_reading_product_metadata,
    normalize_product_sections,
    validate_generation_result,
)


# ============================================================
# Constants
# ============================================================


ALL_SECTIONS = (
    "core_personality",
    "career",
    "wealth",
    "relationships",
    "health",
    "current_luck",
    "future_flow",
    "advice",
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def sample_reading_context() -> Dict[str, Any]:
    """
    reading_context_v1を模した最小の商品化用fixture。

    engine/reading_product.pyは
    占術計算を再実行しないため、
    ここでは計算済み値を固定する。
    """

    return {
        "schema_version": "reading_context_v1",

        "subject": {
            "birth_date": "1985-07-17",
            "birth_time": "21:50",
            "birth_place": "石川県",
            "gender": "female",
            "timezone": "Asia/Tokyo",
        },

        "natal_chart": {
            "pillars": {
                "year": {
                    "position": "year",
                    "pillar": "乙丑",
                    "stem": "乙",
                    "branch": "丑",
                    "stem_ten_god": "偏印",
                    "twelve_stage": "墓",
                    "hidden_stems": [
                        "己",
                        "癸",
                        "辛",
                    ],
                    "main_hidden_stem": "己",
                    "main_hidden_stem_ten_god": "食神",
                },
                "month": {
                    "position": "month",
                    "pillar": "癸未",
                    "stem": "癸",
                    "branch": "未",
                    "stem_ten_god": "偏官",
                    "twelve_stage": "冠帯",
                    "hidden_stems": [
                        "己",
                        "丁",
                        "乙",
                    ],
                    "main_hidden_stem": "己",
                    "main_hidden_stem_ten_god": "食神",
                },
                "day": {
                    "position": "day",
                    "pillar": "丁巳",
                    "stem": "丁",
                    "branch": "巳",
                    "stem_ten_god": None,
                    "twelve_stage": "帝旺",
                    "hidden_stems": [
                        "丙",
                        "戊",
                        "庚",
                    ],
                    "main_hidden_stem": "丙",
                    "main_hidden_stem_ten_god": "劫財",
                },
                "hour": {
                    "position": "hour",
                    "pillar": "辛亥",
                    "stem": "辛",
                    "branch": "亥",
                    "stem_ten_god": "偏財",
                    "twelve_stage": "胎",
                    "hidden_stems": [
                        "壬",
                        "甲",
                    ],
                    "main_hidden_stem": "壬",
                    "main_hidden_stem_ten_god": "正官",
                },
            },
            "pillar_sequence": [
                "乙丑",
                "癸未",
                "丁巳",
                "辛亥",
            ],
        },

        "day_master": {
            "stem": "丁",
            "element": "火",
            "yin_yang": "陰",
            "day_pillar": "丁巳",
        },

        "five_elements": {
            "raw_scores": {
                "木": 2,
                "火": 3,
                "土": 3,
                "金": 2,
                "水": 4,
            },
            "weighted_scores": {
                "木": 18.5,
                "火": 24.0,
                "土": 22.5,
                "金": 12.0,
                "水": 31.0,
            },
            "strongest_element": "水",
            "weakest_element": "金",
            "weighted_method": (
                "weighted_five_elements_v1"
            ),
            "weighted_status": "calculated",
        },

        "strength": {
            "technical_label": "balanced",
            "label": "中和",
            "final_score": 50.0,
            "confidence": "high",
            "adjustment_total": 0.0,
            "method": (
                "final_strength_judgment_v1"
            ),
            "status": "final",
            "notes": [],
        },

        "pattern": {
            "primary_pattern": "食神格",
            "technical_pattern": "shokujin",
            "overall_judgment": "established",
            "confidence": "medium",
            "establishment_score": 72.0,
            "establishment_status": "established",
            "is_exposed": True,
            "breaking_factors": [],
            "rescue_factors": [],
            "method": "pattern_judgment_v1",
            "status": "final",
        },

        "useful_gods": {
            "has_useful_candidate": True,
            "primary_useful_element": "金",
            "secondary_useful_elements": [
                "水",
                "木",
                "土",
            ],
            "final_useful_elements": [
                "金",
                "水",
                "木",
                "土",
            ],
            "unfavorable_elements": [
                "火",
            ],
            "strength_class": "balanced",
            "confidence": "medium",
            "agreement_level": (
                "double_agreement"
            ),
            "triple_agreement_elements": [],
            "double_agreement_elements": [
                "金",
            ],
            "conflicted_elements": [],
            "candidates": [],
            "reasoning": [],
            "method": "useful_gods_v3",
            "status": "final",
        },

        "luck": {
            "luck_pillars": {
                "direction": "forward",
                "direction_japanese": "順行",
                "start_age": 7.0,
                "start_age_detail": {},
                "pillar_count": 8,
                "pillars": [],
                "method": "luck_pillars_v1",
                "status": "calculated",
            },

            "current_luck": {
                "has_current_luck": True,
                "phase": "current",
                "exact_age": 41.0,
                "calendar_age": 41,
                "current_pillar": {
                    "index": 4,
                    "ganzhi": "丁亥",
                    "stem": "丁",
                    "branch": "亥",
                    "stem_element": "火",
                    "branch_element": "水",
                    "stem_ten_god": "比肩",
                    "start_age": 37.0,
                    "end_age": 47.0,
                    "stem_useful_relation": {},
                    "branch_useful_relation": {},
                },
                "previous_pillar": None,
                "next_pillar": {
                    "index": 5,
                    "ganzhi": "戊子",
                    "stem": "戊",
                    "branch": "子",
                    "stem_element": "土",
                    "branch_element": "水",
                    "stem_ten_god": "傷官",
                    "start_age": 47.0,
                    "end_age": 57.0,
                    "stem_useful_relation": {},
                    "branch_useful_relation": {},
                },
                "progress": {
                    "progress_percent": 40.0,
                },
                "years_until_next_luck": 6.0,
                "method": "current_luck_v1",
                "status": "calculated",
            },

            "annual_luck": {
                "year": 2026,
                "calendar_year": 2026,
                "effective_year": 2026,
                "ganzhi": "丙午",
                "stem": "丙",
                "branch": "午",
                "stem_element": "火",
                "branch_element": "火",
                "stem_ten_god": "劫財",
                "twelve_stage": "建禄",
                "stem_useful_relation": {},
                "branch_useful_relation": {},
                "current_luck_relation": {},
                "year_boundary_applied": True,
                "year_boundary_rule": "立春",
                "reasoning": [],
                "method": "annual_luck_v1",
                "status": "calculated",
            },

            "integrated_luck": {
                "current_luck_ganzhi": "丁亥",
                "annual_luck_ganzhi": "丙午",
                "current_luck_elements": {},
                "annual_luck_elements": {},
                "element_interactions": {},
                "current_luck_useful": {},
                "annual_luck_useful": {},
                "agreement_level": "mixed",
                "score": {},
                "overall_score": 2.0,
                "overall_level": "mixed",
                "confidence": {
                    "level": "medium",
                },
                "annual_ten_god": "劫財",
                "annual_twelve_stage": "建禄",
                "reasoning": [],
                "method": "integrated_luck_v1",
                "status": "calculated",
            },
        },

        "reading_sections": {
            section: {
                "focus": [],
                "instruction": (
                    f"{section}を鑑定する。"
                ),
            }
            for section in ALL_SECTIONS
        },

        "source_metadata": {
            "strength": {
                "method": (
                    "final_strength_judgment_v1"
                ),
                "status": "final",
            },
            "pattern": {
                "method": "pattern_judgment_v1",
                "status": "final",
            },
            "useful_gods": {
                "method": "useful_gods_v3",
                "status": "final",
            },
            "luck_pillars": {
                "method": "luck_pillars_v1",
                "status": "calculated",
            },
            "current_luck": {
                "method": "current_luck_v1",
                "status": "calculated",
            },
            "annual_luck": {
                "method": "annual_luck_v1",
                "status": "calculated",
            },
            "integrated_luck": {
                "method": "integrated_luck_v1",
                "status": "calculated",
            },
        },

        "validation": {
            "valid": True,
            "missing_top_level_keys": [],
            "missing_pillars": [],
        },

        "method": "reading_context_v1",
        "status": "ready_for_ai_reading",

        "notes": [
            (
                "占術計算済みデータを"
                "AI鑑定文生成向けに整形済み。"
            )
        ],
    }


@pytest.fixture
def sample_parsed() -> Dict[str, Any]:
    """
    現行Structured Outputs契約に合わせた
    8セクションJSON fixture。
    """

    return {
        "summary": (
            "丁日主の温かさと食神格の創造性を活かし、"
            "仕組み化を加えることで安定しやすい命式です。"
        ),

        "sections": {
            section: {
                "title": SECTION_TITLES[
                    section
                ],
                "summary": (
                    f"{SECTION_TITLES[section]}の"
                    "要点をまとめた文章です。"
                ),
                "detail": (
                    f"{SECTION_TITLES[section]}について、"
                    "計算済み命式を根拠に詳しく"
                    "読み解いた商品向け鑑定文章です。"
                ),
                "evidence": [
                    "日主は丁です。",
                    "身強身弱は中和です。",
                ],
                "advice": [
                    "判断基準を先に決めましょう。",
                    "小さく試して改善しましょう。",
                ],
            }
            for section in ALL_SECTIONS
        },

        "disclaimer": (
            "本鑑定は計算済みデータを前提とした"
            "傾向の読み解きです。"
            "将来を確定的に断定するものではありません。"
        ),
    }


@pytest.fixture
def sample_generation_result(
    sample_parsed,
) -> ReadingGenerationResult:
    return ReadingGenerationResult(
        output_format="json",
        model="gpt-5",
        text=json.dumps(
            sample_parsed,
            ensure_ascii=False,
        ),
        parsed=deepcopy(
            sample_parsed
        ),
        response_id="resp_test_product_001",
        response_status="completed",
        usage={
            "input_tokens": 1000,
            "output_tokens": 2000,
            "total_tokens": 3000,
        },
        sections=ALL_SECTIONS,
        method="openai_responses_api_v1",
        status="completed",
    )


@pytest.fixture
def sample_product(
    sample_reading_context,
    sample_generation_result,
) -> ReadingProduct:
    return build_reading_product(
        sample_reading_context,
        sample_generation_result,
    )


# ============================================================
# Constants / metadata
# ============================================================


def test_reading_product_version():
    assert (
        READING_PRODUCT_VERSION
        == "reading_product_v1"
    )


def test_reading_product_method():
    assert (
        READING_PRODUCT_METHOD
        == "reading_product_v1"
    )


def test_reading_product_status():
    assert (
        READING_PRODUCT_STATUS
        == "ready"
    )


def test_default_product_title():
    assert (
        DEFAULT_PRODUCT_TITLE
        == "四柱推命鑑定書"
    )


def test_section_titles_have_all_sections():
    assert set(
        SECTION_TITLES.keys()
    ) == set(
        ALL_SECTIONS
    )


def test_default_section_order_matches_contract():
    assert (
        DEFAULT_SECTION_ORDER
        == ALL_SECTIONS
    )


def test_product_metadata_contract():
    metadata = (
        get_reading_product_metadata()
    )

    assert (
        metadata[
            "version"
        ]
        == READING_PRODUCT_VERSION
    )

    assert (
        metadata[
            "method"
        ]
        == READING_PRODUCT_METHOD
    )

    assert (
        metadata[
            "status"
        ]
        == READING_PRODUCT_STATUS
    )

    assert (
        metadata[
            "recalculates_astrology"
        ]
        is False
    )

    assert (
        metadata[
            "rewrites_ai_reading"
        ]
        is False
    )

    assert (
        metadata[
            "requires_json_generation"
        ]
        is True
    )


# ============================================================
# normalize_product_sections
# ============================================================


def test_normalize_sections_none_returns_all():
    assert (
        normalize_product_sections()
        == ALL_SECTIONS
    )


def test_normalize_sections_preserves_order():
    assert (
        normalize_product_sections(
            (
                "career",
                "wealth",
            )
        )
        == (
            "career",
            "wealth",
        )
    )


def test_normalize_sections_removes_duplicates():
    assert (
        normalize_product_sections(
            (
                "career",
                "career",
                "wealth",
            )
        )
        == (
            "career",
            "wealth",
        )
    )


def test_normalize_sections_strips_whitespace():
    assert (
        normalize_product_sections(
            (
                " career ",
                " wealth ",
            )
        )
        == (
            "career",
            "wealth",
        )
    )


def test_normalize_sections_rejects_string():
    with pytest.raises(
        TypeError
    ):
        normalize_product_sections(
            "career"
        )


def test_normalize_sections_rejects_empty():
    with pytest.raises(
        ValueError
    ):
        normalize_product_sections(
            ()
        )


def test_normalize_sections_rejects_blank_item():
    with pytest.raises(
        ValueError
    ):
        normalize_product_sections(
            (
                "career",
                " ",
            )
        )


def test_normalize_sections_rejects_unknown():
    with pytest.raises(
        ValueError
    ):
        normalize_product_sections(
            (
                "unknown_section",
            )
        )


def test_normalize_sections_rejects_non_string_item():
    with pytest.raises(
        TypeError
    ):
        normalize_product_sections(
            (
                "career",
                123,
            )
        )


# ============================================================
# Subject
# ============================================================


def test_build_product_subject(
    sample_reading_context,
):
    subject = build_product_subject(
        sample_reading_context
    )

    assert subject == {
        "birth_date": "1985-07-17",
        "birth_time": "21:50",
        "birth_place": "石川県",
        "gender": "female",
        "timezone": "Asia/Tokyo",
    }


def test_build_product_subject_is_copy(
    sample_reading_context,
):
    subject = build_product_subject(
        sample_reading_context
    )

    subject[
        "birth_place"
    ] = "変更"

    assert (
        sample_reading_context[
            "subject"
        ][
            "birth_place"
        ]
        == "石川県"
    )


def test_build_product_subject_rejects_non_mapping():
    with pytest.raises(
        TypeError
    ):
        build_product_subject(
            None
        )


# ============================================================
# Chart summary
# ============================================================


def test_chart_summary_has_four_pillars(
    sample_reading_context,
):
    summary = build_chart_summary(
        sample_reading_context
    )

    assert set(
        summary[
            "pillars"
        ].keys()
    ) == {
        "year",
        "month",
        "day",
        "hour",
    }


@pytest.mark.parametrize(
    (
        "position",
        "expected",
    ),
    (
        (
            "year",
            "乙丑",
        ),
        (
            "month",
            "癸未",
        ),
        (
            "day",
            "丁巳",
        ),
        (
            "hour",
            "辛亥",
        ),
    ),
)
def test_chart_summary_preserves_each_pillar(
    sample_reading_context,
    position,
    expected,
):
    summary = build_chart_summary(
        sample_reading_context
    )

    assert (
        summary[
            "pillars"
        ][
            position
        ][
            "pillar"
        ]
        == expected
    )


def test_chart_summary_preserves_pillar_sequence(
    sample_reading_context,
):
    summary = build_chart_summary(
        sample_reading_context
    )

    assert (
        summary[
            "pillar_sequence"
        ]
        == [
            "乙丑",
            "癸未",
            "丁巳",
            "辛亥",
        ]
    )


def test_chart_summary_preserves_day_master(
    sample_reading_context,
):
    summary = build_chart_summary(
        sample_reading_context
    )

    assert (
        summary[
            "day_master"
        ][
            "stem"
        ]
        == "丁"
    )

    assert (
        summary[
            "day_master"
        ][
            "day_pillar"
        ]
        == "丁巳"
    )


def test_chart_summary_preserves_five_elements(
    sample_reading_context,
):
    summary = build_chart_summary(
        sample_reading_context
    )

    assert (
        summary[
            "five_elements"
        ][
            "strongest_element"
        ]
        == "水"
    )

    assert (
        summary[
            "five_elements"
        ][
            "weakest_element"
        ]
        == "金"
    )


def test_chart_summary_preserves_strength(
    sample_reading_context,
):
    summary = build_chart_summary(
        sample_reading_context
    )

    assert (
        summary[
            "strength"
        ][
            "label"
        ]
        == "中和"
    )

    assert (
        summary[
            "strength"
        ][
            "final_score"
        ]
        == 50.0
    )


def test_chart_summary_preserves_pattern(
    sample_reading_context,
):
    summary = build_chart_summary(
        sample_reading_context
    )

    assert (
        summary[
            "pattern"
        ][
            "primary_pattern"
        ]
        == "食神格"
    )


def test_chart_summary_preserves_useful_gods(
    sample_reading_context,
):
    summary = build_chart_summary(
        sample_reading_context
    )

    assert (
        summary[
            "useful_gods"
        ][
            "primary_useful_element"
        ]
        == "金"
    )

    assert (
        summary[
            "useful_gods"
        ][
            "secondary_useful_elements"
        ]
        == [
            "水",
            "木",
            "土",
        ]
    )


def test_chart_summary_preserves_current_luck(
    sample_reading_context,
):
    summary = build_chart_summary(
        sample_reading_context
    )

    assert (
        summary[
            "current_luck"
        ][
            "ganzhi"
        ]
        == "丁亥"
    )


def test_chart_summary_preserves_annual_luck(
    sample_reading_context,
):
    summary = build_chart_summary(
        sample_reading_context
    )

    assert (
        summary[
            "annual_luck"
        ][
            "year"
        ]
        == 2026
    )

    assert (
        summary[
            "annual_luck"
        ][
            "ganzhi"
        ]
        == "丙午"
    )


def test_chart_summary_does_not_mutate_context(
    sample_reading_context,
):
    original = deepcopy(
        sample_reading_context
    )

    summary = build_chart_summary(
        sample_reading_context
    )

    summary[
        "pillar_sequence"
    ][
        0
    ] = "変更"

    assert (
        sample_reading_context
        == original
    )


# ============================================================
# validate_generation_result
# ============================================================


def test_validate_generation_result_passes(
    sample_generation_result,
):
    result = validate_generation_result(
        sample_generation_result
    )

    assert (
        result[
            "valid"
        ]
        is True
    )

    assert (
        result[
            "output_format"
        ]
        == "json"
    )


def test_validate_generation_result_rejects_wrong_type():
    with pytest.raises(
        TypeError
    ):
        validate_generation_result(
            {}
        )


def test_validate_generation_result_rejects_text():
    result = ReadingGenerationResult(
        output_format="text",
        model="gpt-5",
        text="文章",
        parsed=None,
        response_id="resp_text",
        response_status="completed",
        usage={},
        sections=(
            "career",
        ),
        status="completed",
    )

    with pytest.raises(
        ReadingProductValidationError
    ):
        validate_generation_result(
            result
        )


def test_validate_generation_result_rejects_none_parsed():
    result = ReadingGenerationResult(
        output_format="json",
        model="gpt-5",
        text="{}",
        parsed=None,
        response_id="resp_none",
        response_status="completed",
        usage={},
        sections=(
            "career",
        ),
        status="completed",
    )

    with pytest.raises(
        ReadingProductValidationError
    ):
        validate_generation_result(
            result
        )


@pytest.mark.parametrize(
    "missing_key",
    (
        "summary",
        "sections",
        "disclaimer",
    ),
)
def test_validate_generation_result_requires_top_level_keys(
    sample_generation_result,
    missing_key,
):
    parsed = deepcopy(
        sample_generation_result.parsed
    )

    del parsed[
        missing_key
    ]

    result = ReadingGenerationResult(
        output_format="json",
        model="gpt-5",
        text="{}",
        parsed=parsed,
        response_id="resp_missing",
        response_status="completed",
        usage={},
        sections=ALL_SECTIONS,
        status="completed",
    )

    with pytest.raises(
        ReadingProductValidationError
    ):
        validate_generation_result(
            result
        )


def test_validate_generation_result_requires_sections_mapping(
    sample_generation_result,
):
    parsed = deepcopy(
        sample_generation_result.parsed
    )

    parsed[
        "sections"
    ] = []

    result = ReadingGenerationResult(
        output_format="json",
        model="gpt-5",
        text="{}",
        parsed=parsed,
        response_id="resp_bad_sections",
        response_status="completed",
        usage={},
        sections=ALL_SECTIONS,
        status="completed",
    )

    with pytest.raises(
        ReadingProductValidationError
    ):
        validate_generation_result(
            result
        )


# ============================================================
# Product section
# ============================================================


def test_build_product_section_contract(
    sample_parsed,
):
    source = (
        sample_parsed[
            "sections"
        ][
            "career"
        ]
    )

    section = build_product_section(
        "career",
        source,
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


def test_build_product_section_uses_detail_not_reading(
    sample_parsed,
):
    source = (
        sample_parsed[
            "sections"
        ][
            "career"
        ]
    )

    section = build_product_section(
        "career",
        source,
    )

    assert (
        "detail"
        in section
    )

    assert (
        "reading"
        not in section
    )

    assert (
        section[
            "detail"
        ]
        == source[
            "detail"
        ]
    )


def test_build_product_section_preserves_ai_title(
    sample_parsed,
):
    source = deepcopy(
        sample_parsed[
            "sections"
        ][
            "career"
        ]
    )

    source[
        "title"
    ] = "AIが返した仕事タイトル"

    section = build_product_section(
        "career",
        source,
    )

    assert (
        section[
            "title"
        ]
        == "AIが返した仕事タイトル"
    )


def test_build_product_section_title_fallback():
    source = {
        "title": " ",
        "summary": "summary",
        "detail": "detail",
        "evidence": [],
        "advice": [],
    }

    section = build_product_section(
        "career",
        source,
    )

    assert (
        section[
            "title"
        ]
        == SECTION_TITLES[
            "career"
        ]
    )


def test_build_product_section_strips_evidence_and_advice():
    source = {
        "title": "仕事・適職",
        "summary": "summary",
        "detail": "detail",
        "evidence": [
            "  根拠1  ",
            "",
            "   ",
            "根拠2",
            123,
        ],
        "advice": [
            "  助言1 ",
            "",
            "助言2",
            None,
        ],
    }

    section = build_product_section(
        "career",
        source,
    )

    assert (
        section[
            "evidence"
        ]
        == [
            "根拠1",
            "根拠2",
        ]
    )

    assert (
        section[
            "advice"
        ]
        == [
            "助言1",
            "助言2",
        ]
    )


def test_build_product_section_rejects_unknown():
    with pytest.raises(
        ValueError
    ):
        build_product_section(
            "unknown",
            {},
        )


def test_build_product_section_rejects_non_mapping():
    with pytest.raises(
        TypeError
    ):
        build_product_section(
            "career",
            None,
        )


# ============================================================
# Product sections
# ============================================================


def test_build_product_sections_all(
    sample_parsed,
):
    sections = build_product_sections(
        sample_parsed,
        ALL_SECTIONS,
    )

    assert (
        len(sections)
        == 8
    )

    assert tuple(
        section[
            "key"
        ]
        for section in sections
    ) == ALL_SECTIONS


def test_build_product_sections_subset(
    sample_parsed,
):
    sections = build_product_sections(
        sample_parsed,
        (
            "career",
            "wealth",
        ),
    )

    assert tuple(
        section[
            "key"
        ]
        for section in sections
    ) == (
        "career",
        "wealth",
    )


def test_build_product_sections_missing_section_raises(
    sample_parsed,
):
    parsed = deepcopy(
        sample_parsed
    )

    del parsed[
        "sections"
    ][
        "career"
    ]

    with pytest.raises(
        ReadingProductValidationError
    ):
        build_product_sections(
            parsed,
            (
                "career",
            ),
        )


# ============================================================
# Summary / disclaimer
# ============================================================


def test_extract_product_summary(
    sample_parsed,
):
    assert (
        extract_product_summary(
            sample_parsed
        )
        == sample_parsed[
            "summary"
        ]
    )


def test_extract_product_summary_empty_if_missing():
    assert (
        extract_product_summary(
            {}
        )
        == ""
    )


def test_extract_product_disclaimer(
    sample_parsed,
):
    assert (
        extract_product_disclaimer(
            sample_parsed
        )
        == sample_parsed[
            "disclaimer"
        ]
    )


@pytest.mark.parametrize(
    "value",
    (
        None,
        "",
        "   ",
    ),
)
def test_extract_product_disclaimer_fallback(
    value,
):
    assert (
        extract_product_disclaimer(
            {
                "disclaimer": value,
            }
        )
        == DEFAULT_DISCLAIMER
    )


# ============================================================
# Generation metadata
# ============================================================


def test_generation_metadata(
    sample_generation_result,
):
    metadata = build_generation_metadata(
        sample_generation_result
    )

    assert (
        metadata[
            "model"
        ]
        == "gpt-5"
    )

    assert (
        metadata[
            "response_id"
        ]
        == "resp_test_product_001"
    )

    assert (
        metadata[
            "response_status"
        ]
        == "completed"
    )

    assert (
        metadata[
            "sections"
        ]
        == list(
            ALL_SECTIONS
        )
    )


def test_generation_metadata_does_not_include_text(
    sample_generation_result,
):
    metadata = build_generation_metadata(
        sample_generation_result
    )

    assert (
        "text"
        not in metadata
    )

    assert (
        "parsed"
        not in metadata
    )

    assert (
        "prompt"
        not in metadata
    )

    assert (
        "api_key"
        not in metadata
    )


def test_generation_metadata_usage_is_copy(
    sample_generation_result,
):
    metadata = build_generation_metadata(
        sample_generation_result
    )

    metadata[
        "usage"
    ][
        "total_tokens"
    ] = 999999

    assert (
        sample_generation_result.usage[
            "total_tokens"
        ]
        == 3000
    )


# ============================================================
# Product metadata
# ============================================================


def test_build_product_metadata(
    sample_reading_context,
):
    metadata = build_product_metadata(
        sample_reading_context
    )

    assert (
        metadata[
            "reading_context_schema"
        ]
        == "reading_context_v1"
    )

    assert (
        metadata[
            "reading_context_method"
        ]
        == "reading_context_v1"
    )

    assert (
        metadata[
            "reading_context_status"
        ]
        == "ready_for_ai_reading"
    )

    assert (
        metadata[
            "product_version"
        ]
        == READING_PRODUCT_VERSION
    )

    assert (
        metadata[
            "recalculates_astrology"
        ]
        is False
    )

    assert (
        metadata[
            "rewrites_ai_reading"
        ]
        is False
    )


def test_build_product_metadata_created_at_is_iso(
    sample_reading_context,
):
    metadata = build_product_metadata(
        sample_reading_context
    )

    created_at = metadata[
        "created_at"
    ]

    assert isinstance(
        created_at,
        str,
    )

    assert (
        "T"
        in created_at
    )

    assert (
        created_at.endswith(
            "+00:00"
        )
    )


def test_build_product_metadata_source_is_copy(
    sample_reading_context,
):
    metadata = build_product_metadata(
        sample_reading_context
    )

    metadata[
        "source_metadata"
    ][
        "strength"
    ][
        "status"
    ] = "changed"

    assert (
        sample_reading_context[
            "source_metadata"
        ][
            "strength"
        ][
            "status"
        ]
        == "final"
    )


# ============================================================
# Main build_reading_product
# ============================================================


def test_build_reading_product_type(
    sample_product,
):
    assert isinstance(
        sample_product,
        ReadingProduct,
    )


def test_build_reading_product_title(
    sample_product,
):
    assert (
        sample_product.title
        == DEFAULT_PRODUCT_TITLE
    )


def test_build_reading_product_custom_title(
    sample_reading_context,
    sample_generation_result,
):
    product = build_reading_product(
        sample_reading_context,
        sample_generation_result,
        title="八雲 四柱推命鑑定書",
    )

    assert (
        product.title
        == "八雲 四柱推命鑑定書"
    )


@pytest.mark.parametrize(
    "title",
    (
        "",
        "   ",
        None,
    ),
)
def test_build_reading_product_rejects_empty_title(
    sample_reading_context,
    sample_generation_result,
    title,
):
    with pytest.raises(
        ValueError
    ):
        build_reading_product(
            sample_reading_context,
            sample_generation_result,
            title=title,
        )


def test_build_reading_product_has_eight_sections(
    sample_product,
):
    assert (
        len(
            sample_product.sections
        )
        == 8
    )


def test_build_reading_product_section_order(
    sample_product,
):
    assert tuple(
        section[
            "key"
        ]
        for section
        in sample_product.sections
    ) == ALL_SECTIONS


def test_build_reading_product_summary(
    sample_product,
    sample_parsed,
):
    assert (
        sample_product.summary
        == sample_parsed[
            "summary"
        ]
    )


def test_build_reading_product_disclaimer(
    sample_product,
    sample_parsed,
):
    assert (
        sample_product.disclaimer
        == sample_parsed[
            "disclaimer"
        ]
    )


def test_build_reading_product_preserves_chart(
    sample_product,
):
    assert (
        sample_product.chart_summary[
            "pillar_sequence"
        ]
        == [
            "乙丑",
            "癸未",
            "丁巳",
            "辛亥",
        ]
    )

    assert (
        sample_product.chart_summary[
            "day_master"
        ][
            "stem"
        ]
        == "丁"
    )


def test_build_reading_product_preserves_current_and_annual_luck(
    sample_product,
):
    assert (
        sample_product.chart_summary[
            "current_luck"
        ][
            "ganzhi"
        ]
        == "丁亥"
    )

    assert (
        sample_product.chart_summary[
            "annual_luck"
        ][
            "ganzhi"
        ]
        == "丙午"
    )


def test_build_reading_product_subset(
    sample_reading_context,
    sample_generation_result,
):
    product = build_reading_product(
        sample_reading_context,
        sample_generation_result,
        sections=(
            "career",
            "wealth",
        ),
    )

    assert tuple(
        section[
            "key"
        ]
        for section
        in product.sections
    ) == (
        "career",
        "wealth",
    )


def test_build_reading_product_rejects_un_generated_section(
    sample_reading_context,
    sample_parsed,
):
    result = ReadingGenerationResult(
        output_format="json",
        model="gpt-5",
        text="{}",
        parsed={
            "summary": (
                sample_parsed[
                    "summary"
                ]
            ),
            "sections": {
                "career": deepcopy(
                    sample_parsed[
                        "sections"
                    ][
                        "career"
                    ]
                ),
            },
            "disclaimer": (
                sample_parsed[
                    "disclaimer"
                ]
            ),
        },
        response_id="resp_subset",
        response_status="completed",
        usage={},
        sections=(
            "career",
        ),
        status="completed",
    )

    with pytest.raises(
        ReadingProductValidationError
    ):
        build_reading_product(
            sample_reading_context,
            result,
            sections=(
                "career",
                "wealth",
            ),
        )


def test_build_reading_product_does_not_mutate_inputs(
    sample_reading_context,
    sample_generation_result,
):
    original_context = deepcopy(
        sample_reading_context
    )

    original_parsed = deepcopy(
        sample_generation_result.parsed
    )

    product = build_reading_product(
        sample_reading_context,
        sample_generation_result,
    )

    product.subject[
        "birth_place"
    ] = "変更"

    product.chart_summary[
        "pillar_sequence"
    ][
        0
    ] = "変更"

    product.sections[
        0
    ][
        "advice"
    ].append(
        "変更"
    )

    assert (
        sample_reading_context
        == original_context
    )

    assert (
        sample_generation_result.parsed
        == original_parsed
    )


# ============================================================
# ReadingProduct.to_dict
# ============================================================


def test_product_to_dict_contract(
    sample_product,
):
    data = sample_product.to_dict()

    assert set(
        data.keys()
    ) == {
        "schema_version",
        "title",
        "subject",
        "chart_summary",
        "sections",
        "summary",
        "disclaimer",
        "generation",
        "metadata",
        "method",
        "status",
    }


def test_product_to_dict_values(
    sample_product,
):
    data = sample_product.to_dict()

    assert (
        data[
            "schema_version"
        ]
        == READING_PRODUCT_VERSION
    )

    assert (
        data[
            "method"
        ]
        == READING_PRODUCT_METHOD
    )

    assert (
        data[
            "status"
        ]
        == READING_PRODUCT_STATUS
    )


def test_product_to_dict_sections_are_list(
    sample_product,
):
    data = sample_product.to_dict()

    assert isinstance(
        data[
            "sections"
        ],
        list,
    )


def test_product_to_dict_is_deepcopy(
    sample_product,
):
    data = sample_product.to_dict()

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

    data[
        "sections"
    ][
        0
    ][
        "advice"
    ].append(
        "変更"
    )

    assert (
        sample_product.subject[
            "birth_place"
        ]
        == "石川県"
    )

    assert (
        sample_product.chart_summary[
            "pillar_sequence"
        ][
            0
        ]
        == "乙丑"
    )

    assert (
        "変更"
        not in sample_product.sections[
            0
        ][
            "advice"
        ]
    )


def test_product_to_dict_is_json_serializable(
    sample_product,
):
    serialized = json.dumps(
        sample_product.to_dict(),
        ensure_ascii=False,
    )

    assert isinstance(
        serialized,
        str,
    )

    assert (
        "四柱推命鑑定書"
        in serialized
    )


# ============================================================
# create_product_from_generation
# ============================================================


def test_create_product_from_generation_returns_dict(
    sample_reading_context,
    sample_generation_result,
):
    result = create_product_from_generation(
        sample_reading_context,
        sample_generation_result,
    )

    assert isinstance(
        result,
        dict,
    )

    assert (
        result[
            "schema_version"
        ]
        == READING_PRODUCT_VERSION
    )


def test_create_product_from_generation_subset(
    sample_reading_context,
    sample_generation_result,
):
    result = create_product_from_generation(
        sample_reading_context,
        sample_generation_result,
        sections=(
            "career",
        ),
    )

    assert (
        len(
            result[
                "sections"
            ]
        )
        == 1
    )

    assert (
        result[
            "sections"
        ][
            0
        ][
            "key"
        ]
        == "career"
    )


# ============================================================
# Security / exposure
# ============================================================


def test_product_does_not_expose_raw_ai_text(
    sample_product,
):
    data = sample_product.to_dict()

    assert (
        "text"
        not in data[
            "generation"
        ]
    )

    assert (
        "parsed"
        not in data[
            "generation"
        ]
    )


def test_product_does_not_expose_prompt(
    sample_product,
):
    serialized = json.dumps(
        sample_product.to_dict(),
        ensure_ascii=False,
    )

    assert (
        "instructions"
        not in serialized
    )

    assert (
        "system_prompt"
        not in serialized
    )

    assert (
        "user_prompt"
        not in serialized
    )


def test_product_does_not_expose_api_key_field(
    sample_product,
):
    serialized = json.dumps(
        sample_product.to_dict(),
        ensure_ascii=False,
    )

    assert (
        "OPENAI_API_KEY"
        not in serialized
    )

    assert (
        '"api_key"'
        not in serialized
    )


# ============================================================
# generate_reading_product orchestration
# ============================================================


def test_generate_reading_product_orchestration(
    monkeypatch,
    sample_reading_context,
    sample_generation_result,
):
    calls = {
        "context": 0,
        "generation": 0,
    }

    chart_result = {
        "chart": "dummy",
    }

    def fake_build_reading_context(
        value,
        *,
        validate=True,
    ):
        calls[
            "context"
        ] += 1

        assert (
            value
            is chart_result
        )

        assert (
            validate
            is True
        )

        return deepcopy(
            sample_reading_context
        )

    def fake_generate_reading(
        reading_context,
        **kwargs,
    ):
        calls[
            "generation"
        ] += 1

        assert (
            reading_context[
                "day_master"
            ][
                "stem"
            ]
            == "丁"
        )

        assert (
            kwargs[
                "output_format"
            ]
            == "json"
        )

        assert (
            kwargs[
                "sections"
            ]
            == ALL_SECTIONS
        )

        assert (
            kwargs[
                "store"
            ]
            is False
        )

        return sample_generation_result

    monkeypatch.setattr(
        reading_product_module,
        "build_reading_context",
        fake_build_reading_context,
    )

    monkeypatch.setattr(
        reading_product_module,
        "generate_reading",
        fake_generate_reading,
    )

    product = generate_reading_product(
        chart_result
    )

    assert isinstance(
        product,
        ReadingProduct,
    )

    assert (
        calls[
            "context"
        ]
        == 1
    )

    assert (
        calls[
            "generation"
        ]
        == 1
    )


def test_generate_reading_product_passes_options(
    monkeypatch,
    sample_reading_context,
    sample_generation_result,
):
    captured = {}

    def fake_build_reading_context(
        value,
        *,
        validate=True,
    ):
        captured[
            "validate_context"
        ] = validate

        return deepcopy(
            sample_reading_context
        )

    def fake_generate_reading(
        reading_context,
        **kwargs,
    ):
        captured.update(
            kwargs
        )

        # 呼出しセクションと整合する
        # subset結果を返す。
        parsed = deepcopy(
            sample_generation_result.parsed
        )

        parsed[
            "sections"
        ] = {
            "career": parsed[
                "sections"
            ][
                "career"
            ],
            "wealth": parsed[
                "sections"
            ][
                "wealth"
            ],
        }

        return ReadingGenerationResult(
            output_format="json",
            model="custom-model",
            text="{}",
            parsed=parsed,
            response_id="resp_options",
            response_status="completed",
            usage={},
            sections=(
                "career",
                "wealth",
            ),
            status="completed",
        )

    monkeypatch.setattr(
        reading_product_module,
        "build_reading_context",
        fake_build_reading_context,
    )

    monkeypatch.setattr(
        reading_product_module,
        "generate_reading",
        fake_generate_reading,
    )

    fake_client = object()

    product = generate_reading_product(
        {
            "chart": "dummy",
        },
        client=fake_client,
        api_key="test-key",
        model="custom-model",
        sections=(
            "career",
            "wealth",
        ),
        language="ja",
        tone="gentle",
        title="商品タイトル",
        max_output_tokens=7777,
        reasoning_effort="minimal",
        store=False,
        validate_context=False,
    )

    assert (
        captured[
            "client"
        ]
        is fake_client
    )

    assert (
        captured[
            "api_key"
        ]
        == "test-key"
    )

    assert (
        captured[
            "model"
        ]
        == "custom-model"
    )

    assert (
        captured[
            "sections"
        ]
        == (
            "career",
            "wealth",
        )
    )

    assert (
        captured[
            "language"
        ]
        == "ja"
    )

    assert (
        captured[
            "tone"
        ]
        == "gentle"
    )

    assert (
        captured[
            "max_output_tokens"
        ]
        == 7777
    )

    assert (
        captured[
            "reasoning_effort"
        ]
        == "minimal"
    )

    assert (
        captured[
            "store"
        ]
        is False
    )

    assert (
        captured[
            "validate_context"
        ]
        is False
    )

    assert (
        product.title
        == "商品タイトル"
    )

    assert tuple(
        item[
            "key"
        ]
        for item
        in product.sections
    ) == (
        "career",
        "wealth",
    )


def test_generate_reading_product_rejects_non_mapping_chart():
    with pytest.raises(
        TypeError
    ):
        generate_reading_product(
            None
        )


# ============================================================
# generate_reading_product_dict
# ============================================================


def test_generate_reading_product_dict(
    monkeypatch,
    sample_product,
):
    captured = {}

    def fake_generate_product(
        chart_result,
        **kwargs,
    ):
        captured[
            "chart_result"
        ] = chart_result

        captured.update(
            kwargs
        )

        return sample_product

    monkeypatch.setattr(
        reading_product_module,
        "generate_reading_product",
        fake_generate_product,
    )

    result = generate_reading_product_dict(
        {
            "chart": "dummy",
        },
        sections=(
            "career",
        ),
        title="テスト鑑定書",
    )

    assert isinstance(
        result,
        dict,
    )

    assert (
        captured[
            "sections"
        ]
        == (
            "career",
        )
    )

    assert (
        captured[
            "title"
        ]
        == "テスト鑑定書"
    )


# ============================================================
# AI text preservation
# ============================================================


@pytest.mark.parametrize(
    "section",
    ALL_SECTIONS,
)
def test_product_preserves_section_summary_exactly(
    sample_product,
    sample_parsed,
    section,
):
    product_section = next(
        item
        for item
        in sample_product.sections
        if item[
            "key"
        ]
        == section
    )

    assert (
        product_section[
            "summary"
        ]
        == sample_parsed[
            "sections"
        ][
            section
        ][
            "summary"
        ]
    )


@pytest.mark.parametrize(
    "section",
    ALL_SECTIONS,
)
def test_product_preserves_section_detail_exactly(
    sample_product,
    sample_parsed,
    section,
):
    product_section = next(
        item
        for item
        in sample_product.sections
        if item[
            "key"
        ]
        == section
    )

    assert (
        product_section[
            "detail"
        ]
        == sample_parsed[
            "sections"
        ][
            section
        ][
            "detail"
        ]
    )


@pytest.mark.parametrize(
    "section",
    ALL_SECTIONS,
)
def test_product_preserves_section_evidence(
    sample_product,
    sample_parsed,
    section,
):
    product_section = next(
        item
        for item
        in sample_product.sections
        if item[
            "key"
        ]
        == section
    )

    assert (
        product_section[
            "evidence"
        ]
        == sample_parsed[
            "sections"
        ][
            section
        ][
            "evidence"
        ]
    )


@pytest.mark.parametrize(
    "section",
    ALL_SECTIONS,
)
def test_product_preserves_section_advice(
    sample_product,
    sample_parsed,
    section,
):
    product_section = next(
        item
        for item
        in sample_product.sections
        if item[
            "key"
        ]
        == section
    )

    assert (
        product_section[
            "advice"
        ]
        == sample_parsed[
            "sections"
        ][
            section
        ][
            "advice"
        ]
    )


# ============================================================
# Product invariants
# ============================================================


def test_product_schema_version(
    sample_product,
):
    assert (
        sample_product.schema_version
        == READING_PRODUCT_VERSION
    )


def test_product_method(
    sample_product,
):
    assert (
        sample_product.method
        == READING_PRODUCT_METHOD
    )


def test_product_status(
    sample_product,
):
    assert (
        sample_product.status
        == READING_PRODUCT_STATUS
    )


def test_product_metadata_says_no_recalculation(
    sample_product,
):
    assert (
        sample_product.metadata[
            "recalculates_astrology"
        ]
        is False
    )


def test_product_metadata_says_no_ai_rewrite(
    sample_product,
):
    assert (
        sample_product.metadata[
            "rewrites_ai_reading"
        ]
        is False
    )


def test_product_generation_keeps_response_trace(
    sample_product,
):
    assert (
        sample_product.generation[
            "response_id"
        ]
        == "resp_test_product_001"
    )

    assert (
        sample_product.generation[
            "model"
        ]
        == "gpt-5"
    )


def test_product_final_json_has_no_tuple(
    sample_product,
):
    data = sample_product.to_dict()

    # JSON化できればtuple等の
    # 非対応値が最終商品に残っていないことを確認できる。
    dumped = json.dumps(
        data,
        ensure_ascii=False,
    )

    loaded = json.loads(
        dumped
    )

    assert isinstance(
        loaded[
            "sections"
        ],
        list,
    )


# ============================================================
# Final gate
# ============================================================


def test_reading_product_v1_final_gate(
    sample_product,
):
    """
    reading_product_v1 の最終品質ゲート。
    """

    assert isinstance(
        sample_product,
        ReadingProduct,
    )

    assert (
        sample_product.schema_version
        == "reading_product_v1"
    )

    assert (
        sample_product.method
        == "reading_product_v1"
    )

    assert (
        sample_product.status
        == "ready"
    )

    assert (
        sample_product.title
        == "四柱推命鑑定書"
    )

    assert (
        sample_product.subject[
            "birth_date"
        ]
        == "1985-07-17"
    )

    assert (
        sample_product.subject[
            "birth_time"
        ]
        == "21:50"
    )

    assert (
        sample_product.subject[
            "birth_place"
        ]
        == "石川県"
    )

    assert (
        sample_product.chart_summary[
            "pillar_sequence"
        ]
        == [
            "乙丑",
            "癸未",
            "丁巳",
            "辛亥",
        ]
    )

    assert (
        sample_product.chart_summary[
            "day_master"
        ][
            "stem"
        ]
        == "丁"
    )

    assert (
        sample_product.chart_summary[
            "strength"
        ][
            "label"
        ]
        == "中和"
    )

    assert (
        sample_product.chart_summary[
            "pattern"
        ][
            "primary_pattern"
        ]
        == "食神格"
    )

    assert (
        sample_product.chart_summary[
            "useful_gods"
        ][
            "primary_useful_element"
        ]
        == "金"
    )

    assert (
        sample_product.chart_summary[
            "current_luck"
        ][
            "ganzhi"
        ]
        == "丁亥"
    )

    assert (
        sample_product.chart_summary[
            "annual_luck"
        ][
            "ganzhi"
        ]
        == "丙午"
    )

    assert (
        len(
            sample_product.sections
        )
        == 8
    )

    assert tuple(
        item[
            "key"
        ]
        for item
        in sample_product.sections
    ) == ALL_SECTIONS

    for section in (
        sample_product.sections
    ):
        assert (
            section[
                "summary"
            ]
        )

        assert (
            section[
                "detail"
            ]
        )

        assert (
            section[
                "evidence"
            ]
        )

        assert (
            section[
                "advice"
            ]
        )

        assert (
            "reading"
            not in section
        )

    assert (
        sample_product.summary
    )

    assert (
        sample_product.disclaimer
    )

    assert (
        sample_product.metadata[
            "recalculates_astrology"
        ]
        is False
    )

    assert (
        sample_product.metadata[
            "rewrites_ai_reading"
        ]
        is False
    )

    data = sample_product.to_dict()

    json.dumps(
        data,
        ensure_ascii=False,
    )

    serialized = json.dumps(
        data,
        ensure_ascii=False,
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
        '"prompt"'
        not in serialized
    )
