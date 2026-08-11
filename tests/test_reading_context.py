"""
tests/test_reading_context.py

engine/reading_context.py の最終回帰テスト。

目的
----
calculate_chart() が返す計算結果から、
AI鑑定用 reading_context が
安全かつ一貫して生成されることを確認する。

重要
----
ChartRequest は engine.chart には存在しないため使用しない。
既存の calculate_chart() テストと同様に SimpleNamespace を使用する。

現在の正式回帰基準:
    1985-07-17 21:50 石川県 女性

    年柱: 乙丑
    月柱: 癸未
    日柱: 丁巳
    時柱: 辛亥
    日主: 丁

2026-08-10 の歳運:
    丙午

丁日主に対する2026年:
    通変星: 劫財
    十二運: 建禄
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from types import SimpleNamespace

import pytest

from engine.chart import calculate_chart

from engine.reading_context import (
    PILLAR_POSITIONS,
    READING_CONTEXT_METHOD,
    READING_CONTEXT_SCHEMA_VERSION,
    READING_CONTEXT_STATUS,
    READING_SECTION_KEYS,
    build_annual_luck_context,
    build_current_luck_context,
    build_day_master_context,
    build_five_elements_context,
    build_integrated_luck_context,
    build_luck_pillars_context,
    build_natal_chart_context,
    build_pattern_context,
    build_pillar_context,
    build_reading_context,
    build_reading_sections,
    build_source_metadata,
    build_strength_context,
    build_subject_context,
    build_useful_gods_context,
    calculate_reading_context,
    prepare_ai_reading_context,
    validate_chart_result_for_reading,
)


# ============================================================
# Constants
# ============================================================


VERIFIED_BIRTH_DATE = "1985-07-17"
VERIFIED_BIRTH_TIME = "21:50"
VERIFIED_BIRTH_PLACE = "石川県"
VERIFIED_GENDER = "female"

TARGET_DATETIME = datetime(
    2026,
    8,
    10,
    15,
    36,
)

EXPECTED_YEAR_PILLAR = "乙丑"
EXPECTED_MONTH_PILLAR = "癸未"
EXPECTED_DAY_PILLAR = "丁巳"
EXPECTED_HOUR_PILLAR = "辛亥"

EXPECTED_DAY_MASTER = "丁"

EXPECTED_ANNUAL_GANZHI = "丙午"
EXPECTED_ANNUAL_TEN_GOD = "劫財"
EXPECTED_ANNUAL_TWELVE_STAGE = "建禄"


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def verified_request():
    """
    calculate_chart() 用のリクエスト。

    engine.chart に ChartRequest は存在しないため、
    calculate_chart() が必要とする属性だけを持つ
    SimpleNamespace を使用する。
    """

    return SimpleNamespace(
        birth_date=VERIFIED_BIRTH_DATE,
        birth_time=VERIFIED_BIRTH_TIME,
        birth_place=VERIFIED_BIRTH_PLACE,
        gender=VERIFIED_GENDER,
    )


@pytest.fixture
def verified_chart_result(
    verified_request,
):
    """
    calculate_chart() の実結果。
    """

    return calculate_chart(
        verified_request,
        target_datetime=TARGET_DATETIME,
    )


@pytest.fixture
def reading_context(
    verified_chart_result,
):
    """
    reading_context.py で整形した結果。
    """

    return build_reading_context(
        verified_chart_result
    )


# ============================================================
# 1. Module constants
# ============================================================


def test_reading_context_schema_version():
    assert (
        READING_CONTEXT_SCHEMA_VERSION
        == "reading_context_v1"
    )


def test_reading_context_method_constant():
    assert (
        READING_CONTEXT_METHOD
        == "reading_context_v1"
    )


def test_reading_context_status_constant():
    assert (
        READING_CONTEXT_STATUS
        == "ready_for_ai_reading"
    )


def test_pillar_positions():
    assert PILLAR_POSITIONS == (
        "year",
        "month",
        "day",
        "hour",
    )


def test_reading_section_keys():
    assert READING_SECTION_KEYS == (
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
# 2. Full context basic structure
# ============================================================


def test_build_reading_context_returns_dict(
    reading_context,
):
    assert isinstance(
        reading_context,
        dict,
    )


def test_reading_context_required_top_level_keys(
    reading_context,
):
    required_keys = {
        "schema_version",
        "subject",
        "natal_chart",
        "day_master",
        "five_elements",
        "strength",
        "pattern",
        "useful_gods",
        "luck",
        "reading_sections",
        "source_metadata",
        "validation",
        "method",
        "status",
        "notes",
    }

    assert required_keys.issubset(
        reading_context.keys()
    )


def test_reading_context_metadata(
    reading_context,
):
    assert (
        reading_context["schema_version"]
        == "reading_context_v1"
    )

    assert (
        reading_context["method"]
        == "reading_context_v1"
    )

    assert (
        reading_context["status"]
        == "ready_for_ai_reading"
    )


def test_reading_context_notes_exist(
    reading_context,
):
    notes = reading_context["notes"]

    assert isinstance(
        notes,
        list,
    )

    assert notes


# ============================================================
# 3. Subject
# ============================================================


def test_subject_context(
    reading_context,
):
    subject = reading_context["subject"]

    assert (
        subject["birth_date"]
        == VERIFIED_BIRTH_DATE
    )

    assert (
        subject["birth_time"]
        == VERIFIED_BIRTH_TIME
    )

    assert (
        subject["birth_place"]
        == VERIFIED_BIRTH_PLACE
    )

    assert (
        subject["gender"]
        == VERIFIED_GENDER
    )

    assert (
        subject["timezone"]
        == "Asia/Tokyo"
    )


def test_build_subject_context_directly(
    verified_chart_result,
):
    subject = build_subject_context(
        verified_chart_result
    )

    assert (
        subject["birth_date"]
        == VERIFIED_BIRTH_DATE
    )


# ============================================================
# 4. Natal chart
# ============================================================


def test_natal_chart_contains_four_pillars(
    reading_context,
):
    pillars = reading_context[
        "natal_chart"
    ]["pillars"]

    assert set(
        pillars.keys()
    ) == {
        "year",
        "month",
        "day",
        "hour",
    }


def test_verified_year_pillar(
    reading_context,
):
    assert (
        reading_context[
            "natal_chart"
        ][
            "pillars"
        ][
            "year"
        ][
            "pillar"
        ]
        == EXPECTED_YEAR_PILLAR
    )


def test_verified_month_pillar(
    reading_context,
):
    assert (
        reading_context[
            "natal_chart"
        ][
            "pillars"
        ][
            "month"
        ][
            "pillar"
        ]
        == EXPECTED_MONTH_PILLAR
    )


def test_verified_day_pillar(
    reading_context,
):
    assert (
        reading_context[
            "natal_chart"
        ][
            "pillars"
        ][
            "day"
        ][
            "pillar"
        ]
        == EXPECTED_DAY_PILLAR
    )


def test_verified_hour_pillar(
    reading_context,
):
    assert (
        reading_context[
            "natal_chart"
        ][
            "pillars"
        ][
            "hour"
        ][
            "pillar"
        ]
        == EXPECTED_HOUR_PILLAR
    )


def test_verified_pillar_sequence(
    reading_context,
):
    assert (
        reading_context[
            "natal_chart"
        ][
            "pillar_sequence"
        ]
        == [
            EXPECTED_YEAR_PILLAR,
            EXPECTED_MONTH_PILLAR,
            EXPECTED_DAY_PILLAR,
            EXPECTED_HOUR_PILLAR,
        ]
    )


def test_build_natal_chart_context_directly(
    verified_chart_result,
):
    natal = (
        build_natal_chart_context(
            verified_chart_result
        )
    )

    assert (
        natal["pillar_sequence"][2]
        == EXPECTED_DAY_PILLAR
    )


# ============================================================
# 5. Pillar context
# ============================================================


def test_build_pillar_context_minimum():
    source = {
        "pillar": "甲子",
        "stem": "甲",
        "branch": "子",
        "ten_god": "劫財",
        "twelve_stage": "沐浴",
        "hidden_stems": [
            "癸",
        ],
        "main_hidden_stem": "癸",
    }

    result = build_pillar_context(
        source,
        "year",
    )

    assert (
        result["position"]
        == "year"
    )

    assert (
        result["pillar"]
        == "甲子"
    )

    assert (
        result["stem"]
        == "甲"
    )

    assert (
        result["branch"]
        == "子"
    )

    assert (
        result["stem_ten_god"]
        == "劫財"
    )

    assert (
        result["twelve_stage"]
        == "沐浴"
    )


def test_build_pillar_context_does_not_mutate_source():
    source = {
        "pillar": "甲子",
        "hidden_stems": [
            "癸",
        ],
    }

    before = deepcopy(
        source
    )

    build_pillar_context(
        source,
        "year",
    )

    assert source == before


# ============================================================
# 6. Day master
# ============================================================


def test_day_master_context(
    reading_context,
):
    day_master = reading_context[
        "day_master"
    ]

    assert (
        day_master["stem"]
        == EXPECTED_DAY_MASTER
    )

    assert (
        day_master["day_pillar"]
        == EXPECTED_DAY_PILLAR
    )


def test_day_master_matches_day_pillar_stem(
    reading_context,
):
    day_master = reading_context[
        "day_master"
    ]["stem"]

    day_stem = reading_context[
        "natal_chart"
    ][
        "pillars"
    ][
        "day"
    ][
        "stem"
    ]

    assert day_master == day_stem


def test_build_day_master_context_directly(
    verified_chart_result,
):
    result = (
        build_day_master_context(
            verified_chart_result
        )
    )

    assert (
        result["stem"]
        == EXPECTED_DAY_MASTER
    )


# ============================================================
# 7. Five elements
# ============================================================


def test_five_elements_context_exists(
    reading_context,
):
    five_elements = reading_context[
        "five_elements"
    ]

    assert isinstance(
        five_elements,
        dict,
    )

    assert (
        "raw_scores"
        in five_elements
    )

    assert (
        "weighted_scores"
        in five_elements
    )


def test_five_elements_scores_are_dicts(
    reading_context,
):
    five_elements = reading_context[
        "five_elements"
    ]

    assert isinstance(
        five_elements["raw_scores"],
        dict,
    )

    assert isinstance(
        five_elements[
            "weighted_scores"
        ],
        dict,
    )


def test_five_elements_strongest_and_weakest_are_valid(
    reading_context,
):
    five_elements = reading_context[
        "five_elements"
    ]

    valid_elements = {
        "木",
        "火",
        "土",
        "金",
        "水",
        None,
    }

    assert (
        five_elements[
            "strongest_element"
        ]
        in valid_elements
    )

    assert (
        five_elements[
            "weakest_element"
        ]
        in valid_elements
    )


def test_build_five_elements_context_directly(
    verified_chart_result,
):
    result = (
        build_five_elements_context(
            verified_chart_result
        )
    )

    assert isinstance(
        result,
        dict,
    )


# ============================================================
# 8. Strength
# ============================================================


def test_strength_context_exists(
    reading_context,
):
    strength = reading_context[
        "strength"
    ]

    assert isinstance(
        strength,
        dict,
    )


def test_strength_context_required_keys(
    reading_context,
):
    required_keys = {
        "technical_label",
        "label",
        "final_score",
        "confidence",
        "adjustment_total",
        "method",
        "status",
        "notes",
    }

    assert required_keys.issubset(
        reading_context[
            "strength"
        ].keys()
    )


def test_strength_method_preserved(
    reading_context,
    verified_chart_result,
):
    assert (
        reading_context[
            "strength"
        ][
            "method"
        ]
        == verified_chart_result[
            "final_strength_judgment"
        ].get(
            "method"
        )
    )


def test_build_strength_context_directly(
    verified_chart_result,
):
    result = (
        build_strength_context(
            verified_chart_result
        )
    )

    assert isinstance(
        result,
        dict,
    )


# ============================================================
# 9. Pattern
# ============================================================


def test_pattern_context_exists(
    reading_context,
):
    assert isinstance(
        reading_context[
            "pattern"
        ],
        dict,
    )


def test_pattern_context_required_keys(
    reading_context,
):
    required_keys = {
        "primary_pattern",
        "technical_pattern",
        "overall_judgment",
        "confidence",
        "establishment_score",
        "establishment_status",
        "is_exposed",
        "breaking_factors",
        "rescue_factors",
        "method",
        "status",
    }

    assert required_keys.issubset(
        reading_context[
            "pattern"
        ].keys()
    )


def test_pattern_method_preserved(
    reading_context,
    verified_chart_result,
):
    assert (
        reading_context[
            "pattern"
        ][
            "method"
        ]
        == verified_chart_result[
            "pattern_judgment"
        ].get(
            "method"
        )
    )


def test_build_pattern_context_directly(
    verified_chart_result,
):
    result = (
        build_pattern_context(
            verified_chart_result
        )
    )

    assert isinstance(
        result,
        dict,
    )


# ============================================================
# 10. Useful gods
# ============================================================


def test_useful_gods_context_exists(
    reading_context,
):
    useful = reading_context[
        "useful_gods"
    ]

    assert isinstance(
        useful,
        dict,
    )


def test_useful_gods_required_keys(
    reading_context,
):
    required_keys = {
        "has_useful_candidate",
        "primary_useful_element",
        "secondary_useful_elements",
        "final_useful_elements",
        "unfavorable_elements",
        "strength_class",
        "confidence",
        "agreement_level",
        "triple_agreement_elements",
        "double_agreement_elements",
        "conflicted_elements",
        "candidates",
        "reasoning",
        "method",
        "status",
    }

    assert required_keys.issubset(
        reading_context[
            "useful_gods"
        ].keys()
    )


def test_useful_gods_method_is_v3(
    reading_context,
):
    assert (
        reading_context[
            "useful_gods"
        ][
            "method"
        ]
        == "useful_gods_v3"
    )


def test_useful_gods_elements_are_lists(
    reading_context,
):
    useful = reading_context[
        "useful_gods"
    ]

    assert isinstance(
        useful[
            "secondary_useful_elements"
        ],
        list,
    )

    assert isinstance(
        useful[
            "final_useful_elements"
        ],
        list,
    )

    assert isinstance(
        useful[
            "unfavorable_elements"
        ],
        list,
    )


def test_build_useful_gods_context_directly(
    verified_chart_result,
):
    result = (
        build_useful_gods_context(
            verified_chart_result
        )
    )

    assert (
        result["method"]
        == "useful_gods_v3"
    )


# ============================================================
# 11. Luck container
# ============================================================


def test_luck_container_required_keys(
    reading_context,
):
    luck = reading_context["luck"]

    assert set(
        luck.keys()
    ) == {
        "luck_pillars",
        "current_luck",
        "annual_luck",
        "integrated_luck",
    }


# ============================================================
# 12. Luck pillars
# ============================================================


def test_luck_pillars_context_exists(
    reading_context,
):
    luck_pillars = reading_context[
        "luck"
    ][
        "luck_pillars"
    ]

    assert isinstance(
        luck_pillars,
        dict,
    )


def test_luck_pillars_method_is_v2(
    reading_context,
):
    assert (
        reading_context[
            "luck"
        ][
            "luck_pillars"
        ][
            "method"
        ]
        == "luck_pillars_v2"
    )


def test_luck_pillars_count_matches_list(
    reading_context,
):
    luck_pillars = reading_context[
        "luck"
    ][
        "luck_pillars"
    ]

    assert (
        luck_pillars[
            "pillar_count"
        ]
        == len(
            luck_pillars[
                "pillars"
            ]
        )
    )


def test_verified_luck_pillars_count(
    reading_context,
):
    assert (
        reading_context[
            "luck"
        ][
            "luck_pillars"
        ][
            "pillar_count"
        ]
        == 10
    )


def test_build_luck_pillars_context_directly(
    verified_chart_result,
):
    result = (
        build_luck_pillars_context(
            verified_chart_result
        )
    )

    assert (
        result["method"]
        == "luck_pillars_v2"
    )


# ============================================================
# 13. Current luck
# ============================================================


def test_current_luck_context_exists(
    reading_context,
):
    current = reading_context[
        "luck"
    ][
        "current_luck"
    ]

    assert isinstance(
        current,
        dict,
    )


def test_current_luck_method_is_v1(
    reading_context,
):
    assert (
        reading_context[
            "luck"
        ][
            "current_luck"
        ][
            "method"
        ]
        == "current_luck_v1"
    )


def test_current_luck_has_current_luck(
    reading_context,
):
    assert (
        reading_context[
            "luck"
        ][
            "current_luck"
        ][
            "has_current_luck"
        ]
        is True
    )


def test_current_luck_current_pillar_exists(
    reading_context,
):
    current = reading_context[
        "luck"
    ][
        "current_luck"
    ]

    assert isinstance(
        current["current_pillar"],
        dict,
    )

    assert (
        current[
            "current_pillar"
        ][
            "ganzhi"
        ]
        is not None
    )


def test_build_current_luck_context_directly(
    verified_chart_result,
):
    result = (
        build_current_luck_context(
            verified_chart_result
        )
    )

    assert (
        result["method"]
        == "current_luck_v1"
    )


# ============================================================
# 14. Annual luck
# ============================================================


def test_annual_luck_context_exists(
    reading_context,
):
    annual = reading_context[
        "luck"
    ][
        "annual_luck"
    ]

    assert isinstance(
        annual,
        dict,
    )


def test_annual_luck_method_is_v1(
    reading_context,
):
    assert (
        reading_context[
            "luck"
        ][
            "annual_luck"
        ][
            "method"
        ]
        == "annual_luck_v1"
    )


def test_verified_2026_annual_ganzhi(
    reading_context,
):
    assert (
        reading_context[
            "luck"
        ][
            "annual_luck"
        ][
            "ganzhi"
        ]
        == EXPECTED_ANNUAL_GANZHI
    )


def test_verified_2026_annual_ten_god(
    reading_context,
):
    assert (
        reading_context[
            "luck"
        ][
            "annual_luck"
        ][
            "stem_ten_god"
        ]
        == EXPECTED_ANNUAL_TEN_GOD
    )


def test_verified_2026_annual_twelve_stage(
    reading_context,
):
    assert (
        reading_context[
            "luck"
        ][
            "annual_luck"
        ][
            "twelve_stage"
        ]
        == EXPECTED_ANNUAL_TWELVE_STAGE
    )


def test_annual_luck_ten_god_preserved(
    reading_context,
    verified_chart_result,
):
    assert (
        reading_context[
            "luck"
        ][
            "annual_luck"
        ][
            "stem_ten_god"
        ]
        == verified_chart_result[
            "annual_luck"
        ][
            "stem_ten_god"
        ]
    )


def test_annual_luck_twelve_stage_preserved(
    reading_context,
    verified_chart_result,
):
    assert (
        reading_context[
            "luck"
        ][
            "annual_luck"
        ][
            "twelve_stage"
        ]
        == verified_chart_result[
            "annual_luck"
        ][
            "twelve_stage"
        ]
    )


def test_build_annual_luck_context_directly(
    verified_chart_result,
):
    result = (
        build_annual_luck_context(
            verified_chart_result
        )
    )

    assert (
        result["ganzhi"]
        == EXPECTED_ANNUAL_GANZHI
    )


# ============================================================
# 15. Integrated luck
# ============================================================


def test_integrated_luck_context_exists(
    reading_context,
):
    integrated = reading_context[
        "luck"
    ][
        "integrated_luck"
    ]

    assert isinstance(
        integrated,
        dict,
    )


def test_integrated_luck_method_is_v1(
    reading_context,
):
    assert (
        reading_context[
            "luck"
        ][
            "integrated_luck"
        ][
            "method"
        ]
        == "integrated_luck_v1"
    )


def test_integrated_luck_annual_ganzhi_matches_annual(
    reading_context,
):
    integrated = reading_context[
        "luck"
    ][
        "integrated_luck"
    ]

    annual = reading_context[
        "luck"
    ][
        "annual_luck"
    ]

    assert (
        integrated[
            "annual_luck_ganzhi"
        ]
        == annual["ganzhi"]
    )


def test_integrated_luck_current_ganzhi_matches_current(
    reading_context,
):
    integrated = reading_context[
        "luck"
    ][
        "integrated_luck"
    ]

    current = reading_context[
        "luck"
    ][
        "current_luck"
    ]

    assert (
        integrated[
            "current_luck_ganzhi"
        ]
        == current[
            "current_pillar"
        ][
            "ganzhi"
        ]
    )


def test_integrated_luck_overall_level_valid(
    reading_context,
):
    level = reading_context[
        "luck"
    ][
        "integrated_luck"
    ][
        "overall_level"
    ]

    assert level in {
        "very_supportive",
        "supportive",
        "mixed",
        "challenging",
        "very_challenging",
    }


def test_integrated_luck_confidence_valid(
    reading_context,
):
    confidence = reading_context[
        "luck"
    ][
        "integrated_luck"
    ][
        "confidence"
    ]

    assert (
        confidence["level"]
        in {
            "high",
            "medium",
            "low",
        }
    )


def test_build_integrated_luck_context_directly(
    verified_chart_result,
):
    result = (
        build_integrated_luck_context(
            verified_chart_result
        )
    )

    assert (
        result["method"]
        == "integrated_luck_v1"
    )


# ============================================================
# 16. Reading sections
# ============================================================


def test_reading_sections_exist(
    reading_context,
):
    sections = reading_context[
        "reading_sections"
    ]

    assert isinstance(
        sections,
        dict,
    )


def test_reading_sections_all_present(
    reading_context,
):
    sections = reading_context[
        "reading_sections"
    ]

    assert set(
        sections.keys()
    ) == set(
        READING_SECTION_KEYS
    )


@pytest.mark.parametrize(
    "section_name",
    READING_SECTION_KEYS,
)
def test_each_reading_section_has_focus_and_instruction(
    reading_context,
    section_name,
):
    section = reading_context[
        "reading_sections"
    ][
        section_name
    ]

    assert isinstance(
        section,
        dict,
    )

    assert (
        "focus"
        in section
    )

    assert (
        "instruction"
        in section
    )

    assert isinstance(
        section["focus"],
        list,
    )

    assert section["focus"]

    assert isinstance(
        section["instruction"],
        str,
    )

    assert section[
        "instruction"
    ]


def test_health_section_contains_health_safety_instruction(
    reading_context,
):
    instruction = reading_context[
        "reading_sections"
    ][
        "health"
    ][
        "instruction"
    ]

    assert (
        "医学的診断"
        in instruction
    )


def test_build_reading_sections_directly():
    result = (
        build_reading_sections(
            {
                "day_master": {},
                "five_elements": {},
                "strength": {},
                "pattern": {},
                "useful_gods": {},
                "luck_pillars": {},
                "current_luck": {},
                "annual_luck": {},
                "integrated_luck": {},
            }
        )
    )

    assert set(
        result.keys()
    ) == set(
        READING_SECTION_KEYS
    )


# ============================================================
# 17. Source metadata
# ============================================================


def test_source_metadata_exists(
    reading_context,
):
    metadata = reading_context[
        "source_metadata"
    ]

    assert isinstance(
        metadata,
        dict,
    )


def test_source_metadata_required_keys(
    reading_context,
):
    required_keys = {
        "strength",
        "pattern",
        "useful_gods",
        "luck_pillars",
        "current_luck",
        "annual_luck",
        "integrated_luck",
    }

    assert set(
        reading_context[
            "source_metadata"
        ].keys()
    ) == required_keys


def test_source_metadata_useful_gods_method(
    reading_context,
):
    assert (
        reading_context[
            "source_metadata"
        ][
            "useful_gods"
        ][
            "method"
        ]
        == "useful_gods_v3"
    )


def test_source_metadata_luck_methods(
    reading_context,
):
    metadata = reading_context[
        "source_metadata"
    ]

    assert (
        metadata[
            "luck_pillars"
        ][
            "method"
        ]
        == "luck_pillars_v2"
    )

    assert (
        metadata[
            "current_luck"
        ][
            "method"
        ]
        == "current_luck_v1"
    )

    assert (
        metadata[
            "annual_luck"
        ][
            "method"
        ]
        == "annual_luck_v1"
    )

    assert (
        metadata[
            "integrated_luck"
        ][
            "method"
        ]
        == "integrated_luck_v1"
    )


def test_build_source_metadata_directly(
    verified_chart_result,
):
    result = (
        build_source_metadata(
            verified_chart_result
        )
    )

    assert (
        result[
            "annual_luck"
        ][
            "method"
        ]
        == "annual_luck_v1"
    )


# ============================================================
# 18. Validation
# ============================================================


def test_validate_chart_result_success(
    verified_chart_result,
):
    result = (
        validate_chart_result_for_reading(
            verified_chart_result
        )
    )

    assert (
        result["valid"]
        is True
    )

    assert (
        result[
            "missing_top_level_keys"
        ]
        == []
    )

    assert (
        result[
            "missing_pillars"
        ]
        == []
    )


def test_reading_context_validation_success(
    reading_context,
):
    validation = reading_context[
        "validation"
    ]

    assert (
        validation["valid"]
        is True
    )


def test_validation_missing_top_level_key():
    source = {
        "chart": {
            "year": {},
            "month": {},
            "day": {},
            "hour": {},
        }
    }

    with pytest.raises(
        ValueError
    ):
        validate_chart_result_for_reading(
            source
        )


def test_validation_missing_pillar():
    source = {
        "chart": {
            "year": {},
            "month": {},
            "day": {},
        },
        "day_master": {},
        "final_strength_judgment": {},
        "pattern_judgment": {},
        "useful_gods": {},
        "luck_pillars": {},
        "current_luck": {},
        "annual_luck": {},
        "integrated_luck": {},
    }

    with pytest.raises(
        ValueError
    ):
        validate_chart_result_for_reading(
            source
        )


def test_validation_requires_mapping():
    with pytest.raises(
        TypeError
    ):
        validate_chart_result_for_reading(
            []
        )


# ============================================================
# 19. validate=False
# ============================================================


def test_build_reading_context_validate_false():
    source = {
        "input": {},
        "chart": {},
    }

    result = build_reading_context(
        source,
        validate=False,
    )

    assert (
        result[
            "validation"
        ][
            "valid"
        ]
        is None
    )


def test_validate_parameter_requires_bool(
    verified_chart_result,
):
    with pytest.raises(
        TypeError
    ):
        build_reading_context(
            verified_chart_result,
            validate="yes",
        )


# ============================================================
# 20. Immutability
# ============================================================


def test_build_reading_context_does_not_mutate_source(
    verified_chart_result,
):
    before = deepcopy(
        verified_chart_result
    )

    build_reading_context(
        verified_chart_result
    )

    assert (
        verified_chart_result
        == before
    )


def test_reading_context_is_independent_copy(
    verified_chart_result,
):
    context = build_reading_context(
        verified_chart_result
    )

    original_birth_place = (
        verified_chart_result[
            "input"
        ][
            "birth_place"
        ]
    )

    context[
        "subject"
    ][
        "birth_place"
    ] = "変更値"

    assert (
        verified_chart_result[
            "input"
        ][
            "birth_place"
        ]
        == original_birth_place
    )


# ============================================================
# 21. Compatibility aliases
# ============================================================


def test_calculate_reading_context_alias(
    verified_chart_result,
):
    direct = build_reading_context(
        verified_chart_result
    )

    alias = (
        calculate_reading_context(
            verified_chart_result
        )
    )

    assert alias == direct


def test_prepare_ai_reading_context_alias(
    verified_chart_result,
):
    direct = build_reading_context(
        verified_chart_result
    )

    alias = (
        prepare_ai_reading_context(
            verified_chart_result
        )
    )

    assert alias == direct


# ============================================================
# 22. Reproducibility
# ============================================================


def test_reading_context_reproducible(
    verified_chart_result,
):
    first = build_reading_context(
        verified_chart_result
    )

    second = build_reading_context(
        verified_chart_result
    )

    assert first == second


# ============================================================
# 23. Cross-layer consistency
# ============================================================


def test_day_master_consistency_across_layers(
    reading_context,
):
    day_master = reading_context[
        "day_master"
    ][
        "stem"
    ]

    day_pillar_stem = reading_context[
        "natal_chart"
    ][
        "pillars"
    ][
        "day"
    ][
        "stem"
    ]

    assert (
        day_master
        == day_pillar_stem
        == EXPECTED_DAY_MASTER
    )


def test_annual_ganzhi_consistency_across_layers(
    reading_context,
):
    annual = reading_context[
        "luck"
    ][
        "annual_luck"
    ]

    integrated = reading_context[
        "luck"
    ][
        "integrated_luck"
    ]

    assert (
        annual["ganzhi"]
        == integrated[
            "annual_luck_ganzhi"
        ]
        == EXPECTED_ANNUAL_GANZHI
    )


def test_current_ganzhi_consistency_across_layers(
    reading_context,
):
    current = reading_context[
        "luck"
    ][
        "current_luck"
    ]

    integrated = reading_context[
        "luck"
    ][
        "integrated_luck"
    ]

    assert (
        current[
            "current_pillar"
        ][
            "ganzhi"
        ]
        == integrated[
            "current_luck_ganzhi"
        ]
    )


def test_integrated_annual_ten_god_matches_annual(
    reading_context,
):
    annual = reading_context[
        "luck"
    ][
        "annual_luck"
    ]

    integrated = reading_context[
        "luck"
    ][
        "integrated_luck"
    ]

    assert (
        integrated[
            "annual_ten_god"
        ]
        == annual[
            "stem_ten_god"
        ]
    )


def test_integrated_annual_twelve_stage_matches_annual(
    reading_context,
):
    annual = reading_context[
        "luck"
    ][
        "annual_luck"
    ]

    integrated = reading_context[
        "luck"
    ][
        "integrated_luck"
    ]

    assert (
        integrated[
            "annual_twelve_stage"
        ]
        == annual[
            "twelve_stage"
        ]
    )


# ============================================================
# 24. AI input safety
# ============================================================


def test_reading_context_does_not_expose_full_chart_result(
    reading_context,
):
    """
    AI入力層へ元の巨大なchart_resultを
    丸ごと格納していないことを確認する。
    """

    assert (
        "raw_chart_result"
        not in reading_context
    )

    assert (
        "chart_result"
        not in reading_context
    )


def test_integrated_context_does_not_copy_evidence_tree(
    reading_context,
):
    integrated = reading_context[
        "luck"
    ][
        "integrated_luck"
    ]

    assert (
        "evidence"
        not in integrated
    )


def test_annual_context_does_not_copy_evidence_tree(
    reading_context,
):
    annual = reading_context[
        "luck"
    ][
        "annual_luck"
    ]

    assert (
        "evidence"
        not in annual
    )


# ============================================================
# 25. Final real-chart smoke test
# ============================================================


def test_verified_real_chart_reading_context_end_to_end(
    reading_context,
):
    """
    最終スモークテスト。

    現在の正式回帰基準:
    1985-07-17 21:50 石川県 女性

    命式:
        年柱 乙丑
        月柱 癸未
        日柱 丁巳
        時柱 辛亥
        日主 丁

    2026年:
        丙午
        劫財
        建禄

    これらがAI鑑定contextまで
    正しく到達することを確認する。
    """

    assert (
        reading_context[
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
        reading_context[
            "day_master"
        ][
            "stem"
        ]
        == "丁"
    )

    assert (
        reading_context[
            "useful_gods"
        ][
            "method"
        ]
        == "useful_gods_v3"
    )

    assert (
        reading_context[
            "luck"
        ][
            "luck_pillars"
        ][
            "method"
        ]
        == "luck_pillars_v2"
    )

    assert (
        reading_context[
            "luck"
        ][
            "current_luck"
        ][
            "method"
        ]
        == "current_luck_v1"
    )

    assert (
        reading_context[
            "luck"
        ][
            "annual_luck"
        ][
            "ganzhi"
        ]
        == "丙午"
    )

    assert (
        reading_context[
            "luck"
        ][
            "annual_luck"
        ][
            "stem_ten_god"
        ]
        == "劫財"
    )

    assert (
        reading_context[
            "luck"
        ][
            "annual_luck"
        ][
            "twelve_stage"
        ]
        == "建禄"
    )

    assert (
        reading_context[
            "luck"
        ][
            "annual_luck"
        ][
            "method"
        ]
        == "annual_luck_v1"
    )

    assert (
        reading_context[
            "luck"
        ][
            "integrated_luck"
        ][
            "method"
        ]
        == "integrated_luck_v1"
    )

    assert (
        reading_context[
            "status"
        ]
        == "ready_for_ai_reading"
    )
