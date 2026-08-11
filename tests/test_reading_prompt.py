"""
tests/test_reading_prompt.py

engine/reading_prompt.py の最終回帰テスト。

目的
----
reading_context_v1 から、
AI鑑定文生成用の system prompt / user prompt / messages /
reading request が安全かつ決定論的に生成されることを確認する。

このテストではAI APIを呼び出さない。
reading_prompt.py はプロンプト構築層としてのみ検証する。
"""

from __future__ import annotations

from copy import deepcopy

import pytest

from engine.reading_prompt import (
    DEFAULT_LANGUAGE,
    DEFAULT_MAX_SECTION_CHARS,
    DEFAULT_MAX_SUMMARY_CHARS,
    DEFAULT_MIN_SECTION_CHARS,
    DEFAULT_MIN_SUMMARY_CHARS,
    DEFAULT_READING_SECTIONS,
    DEFAULT_SECTION_ORDER,
    DEFAULT_TONE,
    READING_PROMPT_METHOD,
    READING_PROMPT_STATUS,
    READING_PROMPT_VERSION,
    SECTION_TITLES_JA,
    SUPPORTED_LANGUAGES,
    SUPPORTED_OUTPUT_FORMATS,
    SUPPORTED_TONES,
    audit_prompt_request,
    build_compact_reading_request,
    build_json_output_schema,
    build_messages,
    build_prompt_facts,
    build_reading_request,
    build_section_prompt,
    build_selected_section_instructions,
    build_system_prompt,
    build_user_prompt,
    calculate_reading_prompt,
    get_section_instruction,
    prepare_ai_messages,
    prepare_ai_reading_request,
    validate_reading_context,
)


# ============================================================
# Fixture
# ============================================================


@pytest.fixture
def reading_context_fixture():
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
                "水": 2,
            },
            "weighted_scores": {
                "木": 12.0,
                "火": 28.0,
                "土": 26.0,
                "金": 14.0,
                "水": 20.0,
            },
            "strongest_element": "火",
            "weakest_element": "木",
            "weighted_method": "weighted_five_elements_v1",
            "weighted_status": "provisional",
        },
        "strength": {
            "technical_label": "balanced",
            "label": "中和",
            "final_score": 50.0,
            "confidence": "medium",
            "adjustment_total": 0.0,
            "method": "final_strength_judgment_v2",
            "status": "provisional_final_strength_judgment_v2",
            "notes": [],
        },
        "pattern": {
            "primary_pattern": "食神格",
            "technical_pattern": "eating_god",
            "overall_judgment": "食神格として扱う",
            "confidence": "medium",
            "establishment_score": 70.0,
            "establishment_status": "established",
            "is_exposed": True,
            "breaking_factors": [],
            "rescue_factors": [],
            "method": "pattern_judgment_v2",
            "status": "provisional_pattern_judgment_v2",
        },
        "useful_gods": {
            "has_useful_candidate": True,
            "primary_useful_element": "木",
            "secondary_useful_elements": [
                "水",
            ],
            "final_useful_elements": [
                "木",
                "水",
            ],
            "unfavorable_elements": [
                "火",
            ],
            "strength_class": "balanced",
            "confidence": "medium",
            "agreement_level": "double",
            "triple_agreement_elements": [],
            "double_agreement_elements": [
                "木",
            ],
            "conflicted_elements": [],
            "candidates": [],
            "reasoning": [],
            "method": "useful_gods_v3",
            "status": "provisional_useful_gods_v3",
        },
        "luck": {
            "luck_pillars": {
                "direction": "backward",
                "direction_japanese": "逆行",
                "start_age": 4.0,
                "start_age_detail": {},
                "pillar_count": 5,
                "pillars": [
                    {
                        "index": 1,
                        "ganzhi": "壬午",
                        "stem": "壬",
                        "branch": "午",
                        "stem_element": "水",
                        "branch_element": "火",
                        "stem_ten_god": "正官",
                        "start_age": 4.0,
                        "end_age": 14.0,
                    },
                    {
                        "index": 2,
                        "ganzhi": "辛巳",
                        "stem": "辛",
                        "branch": "巳",
                        "stem_element": "金",
                        "branch_element": "火",
                        "stem_ten_god": "偏財",
                        "start_age": 14.0,
                        "end_age": 24.0,
                    },
                    {
                        "index": 3,
                        "ganzhi": "庚辰",
                        "stem": "庚",
                        "branch": "辰",
                        "stem_element": "金",
                        "branch_element": "土",
                        "stem_ten_god": "正財",
                        "start_age": 24.0,
                        "end_age": 34.0,
                    },
                    {
                        "index": 4,
                        "ganzhi": "己卯",
                        "stem": "己",
                        "branch": "卯",
                        "stem_element": "土",
                        "branch_element": "木",
                        "stem_ten_god": "食神",
                        "start_age": 34.0,
                        "end_age": 44.0,
                    },
                    {
                        "index": 5,
                        "ganzhi": "戊寅",
                        "stem": "戊",
                        "branch": "寅",
                        "stem_element": "土",
                        "branch_element": "木",
                        "stem_ten_god": "傷官",
                        "start_age": 44.0,
                        "end_age": 54.0,
                    },
                ],
                "method": "luck_pillars_v2",
                "status": "provisional_luck_pillars_v2",
            },
            "current_luck": {
                "has_current_luck": True,
                "phase": "active",
                "exact_age": 41.0,
                "calendar_age": 41,
                "current_pillar": {
                    "index": 4,
                    "ganzhi": "己卯",
                    "stem": "己",
                    "branch": "卯",
                    "stem_element": "土",
                    "branch_element": "木",
                    "stem_ten_god": "食神",
                    "start_age": 34.0,
                    "end_age": 44.0,
                },
                "previous_pillar": {
                    "index": 3,
                    "ganzhi": "庚辰",
                },
                "next_pillar": {
                    "index": 5,
                    "ganzhi": "戊寅",
                },
                "progress": {
                    "progress_percent": 70.0,
                },
                "years_until_next_luck": 3.0,
                "method": "current_luck_v1",
                "status": "current_luck_resolved",
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
                "year_boundary_applied": False,
                "year_boundary_rule": "astronomical_lichun",
                "reasoning": [],
                "method": "annual_luck_v1",
                "status": "provisional_annual_luck_v1",
            },
            "integrated_luck": {
                "current_luck_ganzhi": "己卯",
                "annual_luck_ganzhi": "丙午",
                "current_luck_elements": {
                    "stem": "土",
                    "branch": "木",
                },
                "annual_luck_elements": {
                    "stem": "火",
                    "branch": "火",
                },
                "element_interactions": {
                    "stem_relation": {},
                    "branch_relation": {},
                    "score": 0.0,
                },
                "current_luck_useful": {},
                "annual_luck_useful": {},
                "agreement_level": "mixed",
                "score": {
                    "total_score": 0.0,
                },
                "overall_score": 0.0,
                "overall_level": "mixed",
                "confidence": {
                    "level": "medium",
                    "ratio": 0.75,
                    "available_sources": 3,
                    "total_sources": 4,
                },
                "annual_ten_god": "劫財",
                "annual_twelve_stage": "建禄",
                "reasoning": [],
                "method": "integrated_luck_v1",
                "status": "provisional_integrated_luck_v1",
            },
        },
        "reading_sections": {
            "core_personality": {
                "focus": [
                    "day_master",
                    "strength",
                    "pattern",
                    "five_elements",
                ],
                "instruction": (
                    "性格・価値観・行動傾向を、"
                    "日主・身強身弱・格局・五行バランスから読む。"
                ),
            },
            "career": {
                "focus": [
                    "pattern",
                    "useful_gods",
                    "day_master",
                    "current_luck",
                    "annual_luck",
                ],
                "instruction": (
                    "仕事適性・働き方・現在の仕事運を、"
                    "格局・用神・通変星・大運・歳運から読む。"
                ),
            },
            "wealth": {
                "focus": [
                    "pattern",
                    "useful_gods",
                    "five_elements",
                    "current_luck",
                    "annual_luck",
                    "integrated_luck",
                ],
                "instruction": (
                    "金運・収入傾向・蓄財傾向を、"
                    "命式構造と現在運を分けて読む。"
                ),
            },
            "relationships": {
                "focus": [
                    "day_master",
                    "pattern",
                    "five_elements",
                    "current_luck",
                    "annual_luck",
                ],
                "instruction": (
                    "対人・恋愛傾向を命式の性質として読み、"
                    "現在運による変化と区別して説明する。"
                ),
            },
            "health": {
                "focus": [
                    "five_elements",
                    "strength",
                    "useful_gods",
                    "current_luck",
                    "annual_luck",
                ],
                "instruction": (
                    "健康は医学的診断を行わず、"
                    "五行上の偏りや生活上の注意傾向として表現する。"
                ),
            },
            "current_luck": {
                "focus": [
                    "current_luck",
                    "annual_luck",
                    "integrated_luck",
                    "useful_gods",
                ],
                "instruction": (
                    "現在の大運と歳運を分けて説明し、"
                    "最後に統合運の意味を補足する。"
                ),
            },
            "future_flow": {
                "focus": [
                    "luck_pillars",
                    "current_luck",
                    "annual_luck",
                    "useful_gods",
                ],
                "instruction": (
                    "現在大運の次の大運を中心に、"
                    "長期的な変化の方向性を説明する。"
                ),
            },
            "advice": {
                "focus": [
                    "useful_gods",
                    "strength",
                    "integrated_luck",
                    "pattern",
                ],
                "instruction": (
                    "断定的な未来予言ではなく、"
                    "命式上活かしやすい方向と具体的な行動案を示す。"
                ),
            },
        },
        "source_metadata": {
            "strength": {
                "method": "final_strength_judgment_v2",
                "status": "provisional",
            },
            "pattern": {
                "method": "pattern_judgment_v2",
                "status": "provisional",
            },
            "useful_gods": {
                "method": "useful_gods_v3",
                "status": "provisional",
            },
            "luck_pillars": {
                "method": "luck_pillars_v2",
                "status": "provisional",
            },
            "current_luck": {
                "method": "current_luck_v1",
                "status": "current_luck_resolved",
            },
            "annual_luck": {
                "method": "annual_luck_v1",
                "status": "provisional",
            },
            "integrated_luck": {
                "method": "integrated_luck_v1",
                "status": "provisional",
            },
        },
        "method": "reading_context_v1",
        "status": "ready_for_ai_reading",
    }


# ============================================================
# Constants
# ============================================================


def test_reading_prompt_constants():
    assert READING_PROMPT_VERSION == "reading_prompt_v1"
    assert READING_PROMPT_METHOD == "reading_prompt_v1"
    assert READING_PROMPT_STATUS == "ready_for_ai_generation"


def test_supported_output_formats():
    assert SUPPORTED_OUTPUT_FORMATS == (
        "text",
        "json",
    )


def test_supported_languages():
    assert SUPPORTED_LANGUAGES == (
        "ja",
        "ja-JP",
    )


def test_supported_tones():
    assert SUPPORTED_TONES == (
        "professional_warm",
        "gentle",
        "concise",
        "detailed",
    )


def test_default_values():
    assert DEFAULT_LANGUAGE == "ja"
    assert DEFAULT_TONE == "professional_warm"
    assert DEFAULT_MIN_SECTION_CHARS == 180
    assert DEFAULT_MAX_SECTION_CHARS == 700
    assert DEFAULT_MIN_SUMMARY_CHARS == 120
    assert DEFAULT_MAX_SUMMARY_CHARS == 400


def test_default_sections():
    assert DEFAULT_READING_SECTIONS == (
        "core_personality",
        "career",
        "wealth",
        "relationships",
        "health",
        "current_luck",
        "future_flow",
        "advice",
    )

    assert (
        DEFAULT_SECTION_ORDER
        == DEFAULT_READING_SECTIONS
    )


def test_section_titles():
    assert SECTION_TITLES_JA == {
        "core_personality": "本質・性格",
        "career": "仕事・適職",
        "wealth": "金運",
        "relationships": "恋愛・人間関係",
        "health": "健康傾向",
        "current_luck": "現在の運勢",
        "future_flow": "今後の流れ",
        "advice": "総合アドバイス",
    }


# ============================================================
# Validation
# ============================================================


def test_validate_reading_context_success(
    reading_context_fixture,
):
    result = validate_reading_context(
        reading_context_fixture
    )

    assert result == {
        "valid": True,
        "schema_version": "reading_context_v1",
        "missing_top_level_keys": [],
        "missing_pillars": [],
        "missing_luck_keys": [],
    }


def test_validate_requires_mapping():
    with pytest.raises(
        TypeError
    ):
        validate_reading_context(
            []
        )


def test_validate_missing_top_level_key(
    reading_context_fixture,
):
    source = deepcopy(
        reading_context_fixture
    )

    del source[
        "day_master"
    ]

    with pytest.raises(
        ValueError
    ):
        validate_reading_context(
            source
        )


def test_validate_wrong_schema(
    reading_context_fixture,
):
    source = deepcopy(
        reading_context_fixture
    )

    source[
        "schema_version"
    ] = "reading_context_v999"

    with pytest.raises(
        ValueError
    ):
        validate_reading_context(
            source
        )


def test_validate_missing_pillar(
    reading_context_fixture,
):
    source = deepcopy(
        reading_context_fixture
    )

    del source[
        "natal_chart"
    ][
        "pillars"
    ][
        "hour"
    ]

    with pytest.raises(
        ValueError
    ):
        validate_reading_context(
            source
        )


def test_validate_missing_luck(
    reading_context_fixture,
):
    source = deepcopy(
        reading_context_fixture
    )

    del source[
        "luck"
    ][
        "integrated_luck"
    ]

    with pytest.raises(
        ValueError
    ):
        validate_reading_context(
            source
        )


# ============================================================
# Prompt facts
# ============================================================


def test_build_prompt_facts(
    reading_context_fixture,
):
    result = build_prompt_facts(
        reading_context_fixture
    )

    assert (
        result[
            "subject"
        ][
            "birth_date"
        ]
        == "1985-07-17"
    )

    assert (
        result[
            "natal_chart"
        ][
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
        result[
            "day_master"
        ][
            "stem"
        ]
        == "丁"
    )


def test_prompt_facts_strength_compact(
    reading_context_fixture,
):
    result = build_prompt_facts(
        reading_context_fixture
    )

    assert result[
        "strength"
    ] == {
        "technical_label": "balanced",
        "label": "中和",
        "final_score": 50.0,
        "confidence": "medium",
    }


def test_prompt_facts_pattern_compact(
    reading_context_fixture,
):
    result = build_prompt_facts(
        reading_context_fixture
    )

    assert result[
        "pattern"
    ] == {
        "primary_pattern": "食神格",
        "technical_pattern": "eating_god",
        "overall_judgment": "食神格として扱う",
        "confidence": "medium",
    }


def test_prompt_facts_annual_luck(
    reading_context_fixture,
):
    result = build_prompt_facts(
        reading_context_fixture
    )

    annual = result[
        "luck"
    ][
        "annual_luck"
    ]

    assert annual[
        "ganzhi"
    ] == "丙午"

    assert annual[
        "stem_ten_god"
    ] == "劫財"

    assert annual[
        "twelve_stage"
    ] == "建禄"


def test_prompt_facts_integrated_luck(
    reading_context_fixture,
):
    result = build_prompt_facts(
        reading_context_fixture
    )

    integrated = result[
        "luck"
    ][
        "integrated_luck"
    ]

    assert (
        integrated[
            "current_luck_ganzhi"
        ]
        == "己卯"
    )

    assert (
        integrated[
            "annual_luck_ganzhi"
        ]
        == "丙午"
    )


def test_prompt_facts_does_not_mutate(
    reading_context_fixture,
):
    before = deepcopy(
        reading_context_fixture
    )

    build_prompt_facts(
        reading_context_fixture
    )

    assert (
        reading_context_fixture
        == before
    )


# ============================================================
# Sections
# ============================================================


@pytest.mark.parametrize(
    (
        "section",
        "title",
    ),
    [
        ("core_personality", "本質・性格"),
        ("career", "仕事・適職"),
        ("wealth", "金運"),
        ("relationships", "恋愛・人間関係"),
        ("health", "健康傾向"),
        ("current_luck", "現在の運勢"),
        ("future_flow", "今後の流れ"),
        ("advice", "総合アドバイス"),
    ],
)
def test_get_section_instruction(
    reading_context_fixture,
    section,
    title,
):
    result = get_section_instruction(
        reading_context_fixture,
        section,
    )

    assert result[
        "section"
    ] == section

    assert result[
        "title"
    ] == title

    assert isinstance(
        result[
            "focus"
        ],
        list,
    )

    assert isinstance(
        result[
            "instruction"
        ],
        str,
    )


def test_get_section_invalid(
    reading_context_fixture,
):
    with pytest.raises(
        ValueError
    ):
        get_section_instruction(
            reading_context_fixture,
            "unknown",
        )


def test_selected_sections_default(
    reading_context_fixture,
):
    result = (
        build_selected_section_instructions(
            reading_context_fixture
        )
    )

    assert [
        item[
            "section"
        ]
        for item
        in result
    ] == list(
        DEFAULT_READING_SECTIONS
    )


def test_selected_sections_subset(
    reading_context_fixture,
):
    result = (
        build_selected_section_instructions(
            reading_context_fixture,
            [
                "career",
                "wealth",
            ],
        )
    )

    assert [
        item[
            "section"
        ]
        for item
        in result
    ] == [
        "career",
        "wealth",
    ]


def test_duplicate_sections_removed(
    reading_context_fixture,
):
    result = (
        build_selected_section_instructions(
            reading_context_fixture,
            [
                "career",
                "career",
                "wealth",
            ],
        )
    )

    assert [
        item[
            "section"
        ]
        for item
        in result
    ] == [
        "career",
        "wealth",
    ]


def test_sections_string_rejected(
    reading_context_fixture,
):
    with pytest.raises(
        TypeError
    ):
        build_selected_section_instructions(
            reading_context_fixture,
            "career",
        )


def test_sections_empty_rejected(
    reading_context_fixture,
):
    with pytest.raises(
        ValueError
    ):
        build_selected_section_instructions(
            reading_context_fixture,
            [],
        )


# ============================================================
# System prompt
# ============================================================


def test_system_prompt_returns_string():
    result = build_system_prompt()

    assert isinstance(
        result,
        str,
    )

    assert result


def test_system_prompt_guardrails():
    result = build_system_prompt()

    required = (
        "再計算しない",
        "入力された計算結果",
        "医学的診断",
        "確定的",
        "利益保証",
    )

    for phrase in required:
        assert phrase in result


@pytest.mark.parametrize(
    "tone",
    SUPPORTED_TONES,
)
def test_system_prompt_supported_tones(
    tone,
):
    assert build_system_prompt(
        tone=tone
    )


@pytest.mark.parametrize(
    "language",
    SUPPORTED_LANGUAGES,
)
def test_system_prompt_supported_languages(
    language,
):
    assert build_system_prompt(
        language=language
    )


@pytest.mark.parametrize(
    "output_format",
    SUPPORTED_OUTPUT_FORMATS,
)
def test_system_prompt_supported_formats(
    output_format,
):
    assert build_system_prompt(
        output_format=output_format
    )


def test_system_prompt_text_format():
    result = build_system_prompt(
        output_format="text"
    )

    assert (
        "通常の日本語文章として出力"
        in result
    )


def test_system_prompt_json_format():
    result = build_system_prompt(
        output_format="json"
    )

    assert (
        "JSON以外の文字を出力しない"
        in result
    )


def test_system_prompt_invalid_language():
    with pytest.raises(
        ValueError
    ):
        build_system_prompt(
            language="en"
        )


def test_system_prompt_invalid_tone():
    with pytest.raises(
        ValueError
    ):
        build_system_prompt(
            tone="unknown"
        )


def test_system_prompt_invalid_format():
    with pytest.raises(
        ValueError
    ):
        build_system_prompt(
            output_format="xml"
        )


# ============================================================
# JSON schema
# ============================================================


def test_json_schema_default():
    schema = (
        build_json_output_schema()
    )

    assert schema[
        "type"
    ] == "object"

    assert schema[
        "required"
    ] == [
        "summary",
        "sections",
        "disclaimer",
    ]

    assert (
        schema[
            "properties"
        ][
            "sections"
        ][
            "required"
        ]
        == list(
            DEFAULT_READING_SECTIONS
        )
    )


def test_json_schema_subset():
    schema = (
        build_json_output_schema(
            [
                "career",
                "wealth",
            ]
        )
    )

    sections = schema[
        "properties"
    ][
        "sections"
    ]

    assert sections[
        "required"
    ] == [
        "career",
        "wealth",
    ]

    assert set(
        sections[
            "properties"
        ]
    ) == {
        "career",
        "wealth",
    }


def test_json_schema_section_fields():
    schema = (
        build_json_output_schema(
            [
                "career",
            ]
        )
    )

    career = schema[
        "properties"
    ][
        "sections"
    ][
        "properties"
    ][
        "career"
    ]

    assert career[
        "required"
    ] == [
        "title",
        "summary",
        "detail",
        "evidence",
        "advice",
    ]


# ============================================================
# User prompt
# ============================================================


def test_user_prompt_returns_string(
    reading_context_fixture,
):
    result = build_user_prompt(
        reading_context_fixture
    )

    assert isinstance(
        result,
        str,
    )

    assert result


def test_user_prompt_guardrails(
    reading_context_fixture,
):
    result = build_user_prompt(
        reading_context_fixture
    )

    required = (
        "日主を再判定しない",
        "身強身弱を再判定しない",
        "格局を再判定しない",
        "用神を再選定しない",
        "大運を再計算しない",
        "歳運を再計算しない",
        "通変星を再計算しない",
        "十二運を再計算しない",
    )

    for phrase in required:
        assert phrase in result


def test_user_prompt_contains_default_sections(
    reading_context_fixture,
):
    result = build_user_prompt(
        reading_context_fixture
    )

    for title in (
        "本質・性格",
        "仕事・適職",
        "金運",
        "恋愛・人間関係",
        "健康傾向",
        "現在の運勢",
        "今後の流れ",
        "総合アドバイス",
    ):
        assert title in result


def test_user_prompt_subset(
    reading_context_fixture,
):
    result = build_user_prompt(
        reading_context_fixture,
        sections=[
            "career",
            "wealth",
        ],
    )

    assert (
        "仕事・適職 (career)"
        in result
    )

    assert (
        "金運 (wealth)"
        in result
    )

    assert (
        "健康傾向 (health)"
        not in result
    )


def test_user_prompt_character_range(
    reading_context_fixture,
):
    result = build_user_prompt(
        reading_context_fixture,
        min_section_chars=200,
        max_section_chars=500,
    )

    assert (
        "200〜500文字程度"
        in result
    )


def test_user_prompt_json(
    reading_context_fixture,
):
    result = build_user_prompt(
        reading_context_fixture,
        sections=[
            "career",
        ],
        output_format="json",
    )

    assert (
        "JSONのみを返してください"
        in result
    )

    assert (
        "JSON Schema:"
        in result
    )


def test_user_prompt_raw_facts_default(
    reading_context_fixture,
):
    result = build_user_prompt(
        reading_context_fixture
    )

    assert (
        "【計算済みデータ】"
        in result
    )

    assert "丁巳" in result
    assert "丙午" in result
    assert "劫財" in result
    assert "建禄" in result


def test_user_prompt_exclude_raw_facts(
    reading_context_fixture,
):
    result = build_user_prompt(
        reading_context_fixture,
        include_raw_facts=False,
    )

    assert (
        "【計算済みデータ】"
        not in result
    )


def test_user_prompt_invalid_format(
    reading_context_fixture,
):
    with pytest.raises(
        ValueError
    ):
        build_user_prompt(
            reading_context_fixture,
            output_format="xml",
        )


def test_user_prompt_invalid_min_type(
    reading_context_fixture,
):
    with pytest.raises(
        TypeError
    ):
        build_user_prompt(
            reading_context_fixture,
            min_section_chars="180",
        )


def test_user_prompt_invalid_min_value(
    reading_context_fixture,
):
    with pytest.raises(
        ValueError
    ):
        build_user_prompt(
            reading_context_fixture,
            min_section_chars=0,
        )


def test_user_prompt_invalid_max_value(
    reading_context_fixture,
):
    with pytest.raises(
        ValueError
    ):
        build_user_prompt(
            reading_context_fixture,
            max_section_chars=0,
        )


def test_user_prompt_max_less_than_min(
    reading_context_fixture,
):
    with pytest.raises(
        ValueError
    ):
        build_user_prompt(
            reading_context_fixture,
            min_section_chars=500,
            max_section_chars=200,
        )


def test_user_prompt_raw_facts_requires_bool(
    reading_context_fixture,
):
    with pytest.raises(
        TypeError
    ):
        build_user_prompt(
            reading_context_fixture,
            include_raw_facts="yes",
        )


# ============================================================
# Section prompt
# ============================================================


def test_section_prompt(
    reading_context_fixture,
):
    result = build_section_prompt(
        reading_context_fixture,
        "career",
    )

    assert (
        "仕事・適職 (career)"
        in result
    )

    assert (
        "健康傾向 (health)"
        not in result
    )


def test_section_prompt_custom_chars(
    reading_context_fixture,
):
    result = build_section_prompt(
        reading_context_fixture,
        "wealth",
        min_chars=250,
        max_chars=450,
    )

    assert (
        "250〜450文字程度"
        in result
    )


def test_section_prompt_invalid(
    reading_context_fixture,
):
    with pytest.raises(
        ValueError
    ):
        build_section_prompt(
            reading_context_fixture,
            "unknown",
        )


# ============================================================
# Messages
# ============================================================


def test_messages_structure(
    reading_context_fixture,
):
    messages = build_messages(
        reading_context_fixture
    )

    assert len(
        messages
    ) == 2

    assert messages[
        0
    ][
        "role"
    ] == "system"

    assert messages[
        1
    ][
        "role"
    ] == "user"

    assert isinstance(
        messages[
            0
        ][
            "content"
        ],
        str,
    )

    assert isinstance(
        messages[
            1
        ][
            "content"
        ],
        str,
    )


def test_messages_match_builders(
    reading_context_fixture,
):
    messages = build_messages(
        reading_context_fixture
    )

    assert (
        messages[
            0
        ][
            "content"
        ]
        == build_system_prompt()
    )

    assert (
        messages[
            1
        ][
            "content"
        ]
        == build_user_prompt(
            reading_context_fixture
        )
    )


def test_messages_json(
    reading_context_fixture,
):
    messages = build_messages(
        reading_context_fixture,
        output_format="json",
    )

    assert (
        "JSON以外の文字を出力しない"
        in messages[
            0
        ][
            "content"
        ]
    )

    assert (
        "JSONのみを返してください"
        in messages[
            1
        ][
            "content"
        ]
    )


# ============================================================
# Reading request
# ============================================================


def test_reading_request_default(
    reading_context_fixture,
):
    result = build_reading_request(
        reading_context_fixture
    )

    assert (
        result[
            "version"
        ]
        == "reading_prompt_v1"
    )

    assert (
        result[
            "method"
        ]
        == "reading_prompt_v1"
    )

    assert (
        result[
            "status"
        ]
        == "ready_for_ai_generation"
    )

    assert (
        result[
            "language"
        ]
        == "ja"
    )

    assert (
        result[
            "tone"
        ]
        == "professional_warm"
    )

    assert (
        result[
            "output_format"
        ]
        == "text"
    )

    assert (
        result[
            "output_schema"
        ]
        is None
    )

    assert (
        result[
            "validation"
        ][
            "valid"
        ]
        is True
    )


def test_reading_request_json(
    reading_context_fixture,
):
    result = build_reading_request(
        reading_context_fixture,
        sections=[
            "career",
            "wealth",
        ],
        output_format="json",
    )

    assert (
        result[
            "sections"
        ]
        == [
            "career",
            "wealth",
        ]
    )

    assert isinstance(
        result[
            "output_schema"
        ],
        dict,
    )


def test_reading_request_duplicate_sections(
    reading_context_fixture,
):
    result = build_reading_request(
        reading_context_fixture,
        sections=[
            "career",
            "career",
            "wealth",
        ],
    )

    assert (
        result[
            "sections"
        ]
        == [
            "career",
            "wealth",
        ]
    )


def test_reading_request_custom_tone_language(
    reading_context_fixture,
):
    result = build_reading_request(
        reading_context_fixture,
        language="ja-JP",
        tone="detailed",
    )

    assert (
        result[
            "language"
        ]
        == "ja-JP"
    )

    assert (
        result[
            "tone"
        ]
        == "detailed"
    )


# ============================================================
# Compact request
# ============================================================


def test_compact_request(
    reading_context_fixture,
):
    result = (
        build_compact_reading_request(
            reading_context_fixture
        )
    )

    assert set(
        result.keys()
    ) == {
        "version",
        "messages",
        "output_format",
        "output_schema",
        "method",
        "status",
    }


def test_compact_request_json(
    reading_context_fixture,
):
    result = (
        build_compact_reading_request(
            reading_context_fixture,
            sections=[
                "career",
            ],
            output_format="json",
        )
    )

    assert isinstance(
        result[
            "output_schema"
        ],
        dict,
    )


# ============================================================
# Audit
# ============================================================


def test_audit_success(
    reading_context_fixture,
):
    request = build_reading_request(
        reading_context_fixture
    )

    result = audit_prompt_request(
        request
    )

    assert result == {
        "valid": True,
        "message_count": 2,
        "system_rule_check": True,
        "user_rule_check": True,
        "method": "reading_prompt_audit_v1",
    }


def test_audit_requires_mapping():
    with pytest.raises(
        TypeError
    ):
        audit_prompt_request(
            []
        )


def test_audit_messages_requires_list():
    with pytest.raises(
        TypeError
    ):
        audit_prompt_request(
            {
                "messages": "invalid",
            }
        )


def test_audit_requires_two_messages():
    with pytest.raises(
        ValueError
    ):
        audit_prompt_request(
            {
                "messages": [
                    {
                        "role": "system",
                        "content": "x",
                    }
                ],
            }
        )


def test_audit_role_order():
    with pytest.raises(
        ValueError
    ):
        audit_prompt_request(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": "x",
                    },
                    {
                        "role": "system",
                        "content": "x",
                    },
                ],
            }
        )


def test_audit_empty_content():
    with pytest.raises(
        ValueError
    ):
        audit_prompt_request(
            {
                "messages": [
                    {
                        "role": "system",
                        "content": "",
                    },
                    {
                        "role": "user",
                        "content": "x",
                    },
                ],
            }
        )


def test_audit_missing_guardrails():
    with pytest.raises(
        ValueError
    ):
        audit_prompt_request(
            {
                "messages": [
                    {
                        "role": "system",
                        "content": "system",
                    },
                    {
                        "role": "user",
                        "content": "user",
                    },
                ],
            }
        )


# ============================================================
# Aliases
# ============================================================


def test_calculate_reading_prompt_alias(
    reading_context_fixture,
):
    assert (
        calculate_reading_prompt(
            reading_context_fixture
        )
        == build_reading_request(
            reading_context_fixture
        )
    )


def test_prepare_ai_messages_alias(
    reading_context_fixture,
):
    assert (
        prepare_ai_messages(
            reading_context_fixture
        )
        == build_messages(
            reading_context_fixture
        )
    )


def test_prepare_ai_reading_request_alias(
    reading_context_fixture,
):
    assert (
        prepare_ai_reading_request(
            reading_context_fixture
        )
        == build_reading_request(
            reading_context_fixture
        )
    )


# ============================================================
# Immutability
# ============================================================


def test_user_prompt_does_not_mutate_context(
    reading_context_fixture,
):
    before = deepcopy(
        reading_context_fixture
    )

    build_user_prompt(
        reading_context_fixture
    )

    assert (
        reading_context_fixture
        == before
    )


def test_messages_do_not_mutate_context(
    reading_context_fixture,
):
    before = deepcopy(
        reading_context_fixture
    )

    build_messages(
        reading_context_fixture
    )

    assert (
        reading_context_fixture
        == before
    )


def test_request_does_not_mutate_context(
    reading_context_fixture,
):
    before = deepcopy(
        reading_context_fixture
    )

    build_reading_request(
        reading_context_fixture
    )

    assert (
        reading_context_fixture
        == before
    )


# ============================================================
# Reproducibility
# ============================================================


def test_system_prompt_reproducible():
    assert (
        build_system_prompt()
        == build_system_prompt()
    )


def test_user_prompt_reproducible(
    reading_context_fixture,
):
    assert (
        build_user_prompt(
            reading_context_fixture
        )
        == build_user_prompt(
            reading_context_fixture
        )
    )


def test_messages_reproducible(
    reading_context_fixture,
):
    assert (
        build_messages(
            reading_context_fixture
        )
        == build_messages(
            reading_context_fixture
        )
    )


def test_request_reproducible(
    reading_context_fixture,
):
    assert (
        build_reading_request(
            reading_context_fixture
        )
        == build_reading_request(
            reading_context_fixture
        )
    )


# ============================================================
# Fact preservation
# ============================================================


def test_prompt_preserves_core_facts(
    reading_context_fixture,
):
    prompt = build_user_prompt(
        reading_context_fixture
    )

    for value in (
        "乙丑",
        "癸未",
        "丁巳",
        "辛亥",
        "食神格",
        "eating_god",
        "己卯",
        "丙午",
        "劫財",
        "建禄",
    ):
        assert value in prompt


# ============================================================
# Safety
# ============================================================


def test_health_guardrail():
    prompt = build_system_prompt()

    assert (
        "医学的診断を行わない"
        in prompt
    )

    assert (
        "病名・発症・寿命を断定しない"
        in prompt
    )


def test_financial_guardrail():
    prompt = build_system_prompt()

    assert "利益保証" in prompt
    assert "金融判断" in prompt


def test_future_guardrail():
    prompt = build_system_prompt()

    assert "必ず起こる" in prompt
    assert "確実に成功する" in prompt


# ============================================================
# Request + audit integration
# ============================================================


@pytest.mark.parametrize(
    "output_format",
    SUPPORTED_OUTPUT_FORMATS,
)
def test_request_audit_formats(
    reading_context_fixture,
    output_format,
):
    request = build_reading_request(
        reading_context_fixture,
        output_format=output_format,
    )

    assert (
        audit_prompt_request(
            request
        )[
            "valid"
        ]
        is True
    )


@pytest.mark.parametrize(
    "tone",
    SUPPORTED_TONES,
)
def test_request_audit_tones(
    reading_context_fixture,
    tone,
):
    request = build_reading_request(
        reading_context_fixture,
        tone=tone,
    )

    assert (
        audit_prompt_request(
            request
        )[
            "valid"
        ]
        is True
    )


@pytest.mark.parametrize(
    "sections",
    [
        [
            "core_personality",
        ],
        [
            "career",
            "wealth",
        ],
        [
            "health",
            "advice",
        ],
        list(
            DEFAULT_READING_SECTIONS
        ),
    ],
)
def test_request_audit_sections(
    reading_context_fixture,
    sections,
):
    request = build_reading_request(
        reading_context_fixture,
        sections=sections,
    )

    assert (
        audit_prompt_request(
            request
        )[
            "valid"
        ]
        is True
    )


# ============================================================
# Final smoke test
# ============================================================


def test_reading_prompt_end_to_end(
    reading_context_fixture,
):
    request = build_reading_request(
        reading_context_fixture,
        sections=list(
            DEFAULT_READING_SECTIONS
        ),
        language="ja",
        tone="professional_warm",
        output_format="json",
    )

    assert (
        request[
            "version"
        ]
        == "reading_prompt_v1"
    )

    assert (
        request[
            "status"
        ]
        == "ready_for_ai_generation"
    )

    assert (
        request[
            "output_format"
        ]
        == "json"
    )

    assert (
        len(
            request[
                "messages"
            ]
        )
        == 2
    )

    system_prompt = request[
        "messages"
    ][
        0
    ][
        "content"
    ]

    user_prompt = request[
        "messages"
    ][
        1
    ][
        "content"
    ]

    assert (
        "四柱・日主・身強身弱・格局・用神・大運・歳運・統合運を再計算しない"
        in system_prompt
    )

    assert (
        "日主を再判定しない"
        in user_prompt
    )

    assert (
        "格局を再判定しない"
        in user_prompt
    )

    assert (
        "用神を再選定しない"
        in user_prompt
    )

    assert (
        "大運を再計算しない"
        in user_prompt
    )

    assert (
        "歳運を再計算しない"
        in user_prompt
    )

    assert "丁巳" in user_prompt
    assert "食神格" in user_prompt
    assert "己卯" in user_prompt
    assert "丙午" in user_prompt
    assert "劫財" in user_prompt
    assert "建禄" in user_prompt

    assert isinstance(
        request[
            "output_schema"
        ],
        dict,
    )

    audit = audit_prompt_request(
        request
    )

    assert (
        audit[
            "valid"
        ]
        is True
    )
