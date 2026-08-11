"""
tests/test_reading_context_real_chart.py

実命式を使用した reading_context 統合回帰テスト。

目的
----
calculate_chart()
    ↓
四柱
    ↓
日主
    ↓
身強身弱
    ↓
格局
    ↓
用神
    ↓
大運
    ↓
現在運
    ↓
歳運
    ↓
統合運
    ↓
build_reading_context()

という実際のAI鑑定データ経路が、
最後まで正常につながることを確認する。

重要
----
このテストではAI APIを呼び出さない。

検証対象は、

    四柱推命計算エンジン
        ↓
    reading_context

まで。

したがって、

・OpenAI API Key
・OpenAI SDK通信
・Responses API
・課金状態

には依存しない。

固定実命式
----------
1985-07-17
21:50
石川県
女性

現行エンジン回帰値:

年柱 乙丑
月柱 癸未
日柱 乙巳
時柱 丁亥

日主 乙

評価日時は固定し、
テスト実行日によって結果が変化しないようにする。
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from types import SimpleNamespace

import pytest

from engine.chart import calculate_chart
from engine.reading_context import (
    READING_CONTEXT_METHOD,
    READING_CONTEXT_SCHEMA_VERSION,
    READING_CONTEXT_STATUS,
    READING_SECTION_KEYS,
    build_reading_context,
    calculate_reading_context,
    prepare_ai_reading_context,
    validate_chart_result_for_reading,
)


# ============================================================
# Constants
# ============================================================


EXPECTED_PILLARS = {
    "year": "乙丑",
    "month": "癸未",
    "day": "乙巳",
    "hour": "丁亥",
}


EXPECTED_DAY_MASTER = "乙"


EXPECTED_ANNUAL_GANZHI = "丙午"


EXPECTED_SOURCE_METHODS = {
    "useful_gods": (
        "useful_gods_v3"
    ),
    "luck_pillars": (
        "luck_pillars_v2"
    ),
    "current_luck": (
        "current_luck_v1"
    ),
    "annual_luck": (
        "annual_luck_v1"
    ),
    "integrated_luck": (
        "integrated_luck_v1"
    ),
}


# ============================================================
# Request
# ============================================================


def make_request(
    birth_date: str,
    birth_time: str | None,
    birth_place: str,
    gender: str,
):
    """
    calculate_chart()へ渡す
    最小requestを作る。
    """

    return SimpleNamespace(
        birth_date=birth_date,
        birth_time=birth_time,
        birth_place=birth_place,
        gender=gender,
    )


def make_verified_request():
    """
    実命式統合テスト用の固定request。
    """

    return make_request(
        birth_date="1985-07-17",
        birth_time="21:50",
        birth_place="石川県",
        gender="female",
    )


# ============================================================
# Fixed target datetime
# ============================================================


@pytest.fixture
def target_datetime():
    """
    運勢計算の基準日時。

    現在時刻を使用すると、
    年を跨いだだけでテスト結果が変化するため、
    2026年8月10日へ固定する。
    """

    return datetime(
        2026,
        8,
        10,
        15,
        36,
    )


# ============================================================
# Chart fixture
# ============================================================


@pytest.fixture
def real_chart_result(
    target_datetime,
):
    """
    実際のcalculate_chart()から
    完全な命式結果を生成する。
    """

    request = (
        make_verified_request()
    )

    return calculate_chart(
        request,
        target_datetime=(
            target_datetime
        ),
    )


# ============================================================
# Reading context fixture
# ============================================================


@pytest.fixture
def real_reading_context(
    real_chart_result,
):
    """
    実際のchart_resultから
    reading_contextを生成する。
    """

    return build_reading_context(
        real_chart_result
    )


# ============================================================
# 1. Chart sanity check
# ============================================================


def test_real_chart_known_pillars(
    real_chart_result,
):
    """
    reading_contextを検証する前に、
    入力となる命式そのものを確認する。
    """

    chart = real_chart_result[
        "chart"
    ]

    for position, expected in (
        EXPECTED_PILLARS.items()
    ):
        assert (
            chart[
                position
            ][
                "pillar"
            ]
            == expected
        )


def test_real_chart_day_master(
    real_chart_result,
):
    assert (
        real_chart_result[
            "day_master"
        ][
            "stem"
        ]
        == EXPECTED_DAY_MASTER
    )


# ============================================================
# 2. Full calculation layers exist
# ============================================================


def test_real_chart_contains_required_reading_layers(
    real_chart_result,
):
    """
    reading_contextへ渡す前に、
    必須計算レイヤーが揃っていることを確認する。
    """

    required_keys = {
        "chart",
        "day_master",
        "final_strength_judgment",
        "pattern_judgment",
        "useful_gods",
        "luck_pillars",
        "current_luck",
        "annual_luck",
        "integrated_luck",
    }

    assert required_keys.issubset(
        real_chart_result.keys()
    )


# ============================================================
# 3. Validation
# ============================================================


def test_real_chart_is_valid_for_reading(
    real_chart_result,
):
    result = (
        validate_chart_result_for_reading(
            real_chart_result
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


# ============================================================
# 4. Reading context basic structure
# ============================================================


def test_real_reading_context_is_dict(
    real_reading_context,
):
    assert isinstance(
        real_reading_context,
        dict,
    )


def test_real_reading_context_schema_version(
    real_reading_context,
):
    assert (
        real_reading_context[
            "schema_version"
        ]
        == READING_CONTEXT_SCHEMA_VERSION
    )


def test_real_reading_context_method(
    real_reading_context,
):
    assert (
        real_reading_context[
            "method"
        ]
        == READING_CONTEXT_METHOD
    )


def test_real_reading_context_status(
    real_reading_context,
):
    assert (
        real_reading_context[
            "status"
        ]
        == READING_CONTEXT_STATUS
    )


# ============================================================
# 5. Subject
# ============================================================


def test_real_subject_context(
    real_reading_context,
):
    subject = real_reading_context[
        "subject"
    ]

    assert (
        subject["birth_date"]
        == "1985-07-17"
    )

    assert (
        subject["birth_time"]
        == "21:50"
    )

    assert (
        subject["birth_place"]
        == "石川県"
    )

    assert (
        subject["gender"]
        == "female"
    )


def test_real_subject_timezone(
    real_reading_context,
):
    assert (
        real_reading_context[
            "subject"
        ][
            "timezone"
        ]
        == "Asia/Tokyo"
    )


# ============================================================
# 6. Natal chart
# ============================================================


def test_real_natal_chart_has_four_pillars(
    real_reading_context,
):
    pillars = real_reading_context[
        "natal_chart"
    ][
        "pillars"
    ]

    assert set(
        pillars.keys()
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
    tuple(
        EXPECTED_PILLARS.items()
    ),
)
def test_real_natal_chart_pillars(
    real_reading_context,
    position,
    expected,
):
    assert (
        real_reading_context[
            "natal_chart"
        ][
            "pillars"
        ][
            position
        ][
            "pillar"
        ]
        == expected
    )


# ============================================================
# 7. Pillar detail
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
def test_real_natal_pillar_has_required_fields(
    real_reading_context,
    position,
):
    pillar = real_reading_context[
        "natal_chart"
    ][
        "pillars"
    ][
        position
    ]

    required = {
        "position",
        "pillar",
        "stem",
        "branch",
        "stem_ten_god",
        "twelve_stage",
        "hidden_stems",
        "main_hidden_stem",
        "main_hidden_stem_ten_god",
    }

    assert required.issubset(
        pillar.keys()
    )


def test_real_month_hidden_stem_context(
    real_reading_context,
):
    month = real_reading_context[
        "natal_chart"
    ][
        "pillars"
    ][
        "month"
    ]

    assert (
        month["stem"]
        == "癸"
    )

    assert (
        month["branch"]
        == "未"
    )

    assert (
        month[
            "main_hidden_stem"
        ]
        == "己"
    )

    assert (
        month[
            "main_hidden_stem_ten_god"
        ]
        == "偏財"
    )


# ============================================================
# 8. Day master
# ============================================================


def test_real_day_master_context(
    real_reading_context,
):
    day_master = real_reading_context[
        "day_master"
    ]

    assert (
        day_master["stem"]
        == EXPECTED_DAY_MASTER
    )


def test_real_day_master_matches_day_pillar(
    real_reading_context,
):
    day_master = real_reading_context[
        "day_master"
    ][
        "stem"
    ]

    day_pillar_stem = (
        real_reading_context[
            "natal_chart"
        ][
            "pillars"
        ][
            "day"
        ][
            "stem"
        ]
    )

    assert (
        day_master
        == day_pillar_stem
        == EXPECTED_DAY_MASTER
    )


# ============================================================
# 9. Five elements
# ============================================================


def test_real_five_elements_context_exists(
    real_reading_context,
):
    result = real_reading_context[
        "five_elements"
    ]

    assert isinstance(
        result,
        dict,
    )

    assert result


# ============================================================
# 10. Strength
# ============================================================


def test_real_strength_context_exists(
    real_reading_context,
):
    strength = real_reading_context[
        "strength"
    ]

    assert isinstance(
        strength,
        dict,
    )

    assert strength


def test_real_strength_has_method_and_status(
    real_reading_context,
):
    strength = real_reading_context[
        "strength"
    ]

    assert (
        "method"
        in strength
    )

    assert (
        "status"
        in strength
    )


# ============================================================
# 11. Pattern
# ============================================================


def test_real_pattern_context_exists(
    real_reading_context,
):
    pattern = real_reading_context[
        "pattern"
    ]

    assert isinstance(
        pattern,
        dict,
    )

    assert pattern


def test_real_pattern_has_method_and_status(
    real_reading_context,
):
    pattern = real_reading_context[
        "pattern"
    ]

    assert (
        "method"
        in pattern
    )

    assert (
        "status"
        in pattern
    )


# ============================================================
# 12. Useful gods
# ============================================================


def test_real_useful_gods_context_exists(
    real_reading_context,
):
    useful = real_reading_context[
        "useful_gods"
    ]

    assert isinstance(
        useful,
        dict,
    )

    assert useful


def test_real_useful_gods_method(
    real_reading_context,
):
    assert (
        real_reading_context[
            "useful_gods"
        ][
            "method"
        ]
        == "useful_gods_v3"
    )


# ============================================================
# 13. Luck container
# ============================================================


def test_real_luck_container(
    real_reading_context,
):
    luck = real_reading_context[
        "luck"
    ]

    assert set(
        luck.keys()
    ) == {
        "luck_pillars",
        "current_luck",
        "annual_luck",
        "integrated_luck",
    }


# ============================================================
# 14. Luck pillars
# ============================================================


def test_real_luck_pillars_context(
    real_reading_context,
):
    luck_pillars = (
        real_reading_context[
            "luck"
        ][
            "luck_pillars"
        ]
    )

    assert isinstance(
        luck_pillars,
        dict,
    )

    assert (
        luck_pillars[
            "method"
        ]
        == "luck_pillars_v2"
    )


# ============================================================
# 15. Current luck
# ============================================================


def test_real_current_luck_context(
    real_reading_context,
):
    current = (
        real_reading_context[
            "luck"
        ][
            "current_luck"
        ]
    )

    assert isinstance(
        current,
        dict,
    )

    assert (
        current["method"]
        == "current_luck_v1"
    )


# ============================================================
# 16. Annual luck
# ============================================================


def test_real_annual_luck_context(
    real_reading_context,
):
    annual = (
        real_reading_context[
            "luck"
        ][
            "annual_luck"
        ]
    )

    assert isinstance(
        annual,
        dict,
    )

    assert (
        annual["method"]
        == "annual_luck_v1"
    )


def test_real_2026_annual_ganzhi(
    real_reading_context,
):
    annual = (
        real_reading_context[
            "luck"
        ][
            "annual_luck"
        ]
    )

    assert (
        annual["ganzhi"]
        == EXPECTED_ANNUAL_GANZHI
    )


# ============================================================
# 17. Integrated luck
# ============================================================


def test_real_integrated_luck_context(
    real_reading_context,
):
    integrated = (
        real_reading_context[
            "luck"
        ][
            "integrated_luck"
        ]
    )

    assert isinstance(
        integrated,
        dict,
    )

    assert (
        integrated["method"]
        == "integrated_luck_v1"
    )


# ============================================================
# 18. Annual / integrated consistency
# ============================================================


def test_real_annual_ganzhi_consistency(
    real_reading_context,
):
    annual = (
        real_reading_context[
            "luck"
        ][
            "annual_luck"
        ]
    )

    integrated = (
        real_reading_context[
            "luck"
        ][
            "integrated_luck"
        ]
    )

    assert (
        annual["ganzhi"]
        == integrated[
            "annual_luck_ganzhi"
        ]
        == EXPECTED_ANNUAL_GANZHI
    )


def test_real_annual_ten_god_consistency(
    real_reading_context,
):
    annual = (
        real_reading_context[
            "luck"
        ][
            "annual_luck"
        ]
    )

    integrated = (
        real_reading_context[
            "luck"
        ][
            "integrated_luck"
        ]
    )

    assert (
        integrated[
            "annual_ten_god"
        ]
        == annual[
            "stem_ten_god"
        ]
    )


def test_real_annual_twelve_stage_consistency(
    real_reading_context,
):
    annual = (
        real_reading_context[
            "luck"
        ][
            "annual_luck"
        ]
    )

    integrated = (
        real_reading_context[
            "luck"
        ][
            "integrated_luck"
        ]
    )

    assert (
        integrated[
            "annual_twelve_stage"
        ]
        == annual[
            "twelve_stage"
        ]
    )


# ============================================================
# 19. Current / integrated consistency
# ============================================================


def test_real_current_ganzhi_consistency(
    real_reading_context,
):
    current = (
        real_reading_context[
            "luck"
        ][
            "current_luck"
        ]
    )

    integrated = (
        real_reading_context[
            "luck"
        ][
            "integrated_luck"
        ]
    )

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


# ============================================================
# 20. Reading sections
# ============================================================


def test_real_reading_sections_exist(
    real_reading_context,
):
    sections = (
        real_reading_context[
            "reading_sections"
        ]
    )

    assert isinstance(
        sections,
        dict,
    )

    assert set(
        sections.keys()
    ) == set(
        READING_SECTION_KEYS
    )


@pytest.mark.parametrize(
    "section_name",
    READING_SECTION_KEYS,
)
def test_real_reading_section_structure(
    real_reading_context,
    section_name,
):
    section = (
        real_reading_context[
            "reading_sections"
        ][
            section_name
        ]
    )

    assert isinstance(
        section,
        dict,
    )

    assert isinstance(
        section["focus"],
        list,
    )

    assert (
        section["focus"]
    )

    assert isinstance(
        section["instruction"],
        str,
    )

    assert (
        section["instruction"]
    )


# ============================================================
# 21. Health safety
# ============================================================


def test_real_health_section_safety(
    real_reading_context,
):
    instruction = (
        real_reading_context[
            "reading_sections"
        ][
            "health"
        ][
            "instruction"
        ]
    )

    assert (
        "医学的診断"
        in instruction
    )


# ============================================================
# 22. Source metadata
# ============================================================


def test_real_source_metadata(
    real_reading_context,
):
    metadata = (
        real_reading_context[
            "source_metadata"
        ]
    )

    required = {
        "strength",
        "pattern",
        "useful_gods",
        "luck_pillars",
        "current_luck",
        "annual_luck",
        "integrated_luck",
    }

    assert set(
        metadata.keys()
    ) == required


@pytest.mark.parametrize(
    (
        "key",
        "expected_method",
    ),
    tuple(
        EXPECTED_SOURCE_METHODS.items()
    ),
)
def test_real_source_metadata_methods(
    real_reading_context,
    key,
    expected_method,
):
    metadata = (
        real_reading_context[
            "source_metadata"
        ]
    )

    assert (
        metadata[
            key
        ][
            "method"
        ]
        == expected_method
    )


# ============================================================
# 23. Validation stored in context
# ============================================================


def test_real_context_validation(
    real_reading_context,
):
    validation = (
        real_reading_context[
            "validation"
        ]
    )

    assert (
        validation["valid"]
        is True
    )

    assert (
        validation[
            "missing_top_level_keys"
        ]
        == []
    )

    assert (
        validation[
            "missing_pillars"
        ]
        == []
    )


# ============================================================
# 24. Compatibility aliases
# ============================================================


def test_real_calculate_reading_context_alias(
    real_chart_result,
):
    direct = (
        build_reading_context(
            real_chart_result
        )
    )

    alias = (
        calculate_reading_context(
            real_chart_result
        )
    )

    assert (
        alias
        == direct
    )


def test_real_prepare_ai_reading_context_alias(
    real_chart_result,
):
    direct = (
        build_reading_context(
            real_chart_result
        )
    )

    alias = (
        prepare_ai_reading_context(
            real_chart_result
        )
    )

    assert (
        alias
        == direct
    )


# ============================================================
# 25. Immutability
# ============================================================


def test_real_build_reading_context_does_not_mutate_chart(
    real_chart_result,
):
    before = deepcopy(
        real_chart_result
    )

    build_reading_context(
        real_chart_result
    )

    assert (
        real_chart_result
        == before
    )


def test_real_context_is_independent_copy(
    real_chart_result,
):
    context = (
        build_reading_context(
            real_chart_result
        )
    )

    original_place = (
        real_chart_result[
            "input"
        ][
            "birth_place"
        ]
    )

    context[
        "subject"
    ][
        "birth_place"
    ] = "変更テスト"

    assert (
        real_chart_result[
            "input"
        ][
            "birth_place"
        ]
        == original_place
    )


# ============================================================
# 26. Reproducibility
# ============================================================


def test_real_reading_context_reproducible(
    real_chart_result,
):
    first = (
        build_reading_context(
            real_chart_result
        )
    )

    second = (
        build_reading_context(
            real_chart_result
        )
    )

    assert (
        first
        == second
    )


# ============================================================
# 27. AI input safety
# ============================================================


def test_real_context_does_not_expose_raw_chart_result(
    real_reading_context,
):
    assert (
        "raw_chart_result"
        not in real_reading_context
    )

    assert (
        "chart_result"
        not in real_reading_context
    )


def test_real_integrated_context_does_not_copy_evidence(
    real_reading_context,
):
    integrated = (
        real_reading_context[
            "luck"
        ][
            "integrated_luck"
        ]
    )

    assert (
        "evidence"
        not in integrated
    )


def test_real_annual_context_does_not_copy_evidence(
    real_reading_context,
):
    annual = (
        real_reading_context[
            "luck"
        ][
            "annual_luck"
        ]
    )

    assert (
        "evidence"
        not in annual
    )


# ============================================================
# 28. Notes / safety instructions
# ============================================================


def test_real_context_notes_exist(
    real_reading_context,
):
    notes = (
        real_reading_context[
            "notes"
        ]
    )

    assert isinstance(
        notes,
        list,
    )

    assert notes


def test_real_context_notes_contain_health_safety(
    real_reading_context,
):
    notes = (
        real_reading_context[
            "notes"
        ]
    )

    assert any(
        "医学的診断"
        in note
        for note in notes
    )


def test_real_context_notes_contain_future_safety(
    real_reading_context,
):
    notes = (
        real_reading_context[
            "notes"
        ]
    )

    assert any(
        "確定的な予言"
        in note
        for note in notes
    )


# ============================================================
# 29. Complete end-to-end
# ============================================================


def test_reading_context_real_chart_end_to_end(
    target_datetime,
):
    """
    最重要統合テスト。

    request
        ↓
    calculate_chart
        ↓
    build_reading_context
        ↓
    AI入力context

    が実命式で最後まで成立することを確認する。
    """

    request = (
        make_verified_request()
    )

    chart_result = (
        calculate_chart(
            request,
            target_datetime=(
                target_datetime
            ),
        )
    )

    context = (
        build_reading_context(
            chart_result
        )
    )

    # 命式
    assert (
        context[
            "natal_chart"
        ][
            "pillars"
        ][
            "year"
        ][
            "pillar"
        ]
        == "乙丑"
    )

    assert (
        context[
            "natal_chart"
        ][
            "pillars"
        ][
            "month"
        ][
            "pillar"
        ]
        == "癸未"
    )

    assert (
        context[
            "natal_chart"
        ][
            "pillars"
        ][
            "day"
        ][
            "pillar"
        ]
        == "乙巳"
    )

    assert (
        context[
            "natal_chart"
        ][
            "pillars"
        ][
            "hour"
        ][
            "pillar"
        ]
        == "丁亥"
    )

    # 日主
    assert (
        context[
            "day_master"
        ][
            "stem"
        ]
        == "乙"
    )

    # 用神
    assert (
        context[
            "useful_gods"
        ][
            "method"
        ]
        == "useful_gods_v3"
    )

    # 大運
    assert (
        context[
            "luck"
        ][
            "luck_pillars"
        ][
            "method"
        ]
        == "luck_pillars_v2"
    )

    # 現在運
    assert (
        context[
            "luck"
        ][
            "current_luck"
        ][
            "method"
        ]
        == "current_luck_v1"
    )

    # 歳運
    assert (
        context[
            "luck"
        ][
            "annual_luck"
        ][
            "method"
        ]
        == "annual_luck_v1"
    )

    assert (
        context[
            "luck"
        ][
            "annual_luck"
        ][
            "ganzhi"
        ]
        == "丙午"
    )

    # 統合運
    assert (
        context[
            "luck"
        ][
            "integrated_luck"
        ][
            "method"
        ]
        == "integrated_luck_v1"
    )

    assert (
        context[
            "luck"
        ][
            "integrated_luck"
        ][
            "annual_luck_ganzhi"
        ]
        == "丙午"
    )

    # reading sections
    assert set(
        context[
            "reading_sections"
        ].keys()
    ) == set(
        READING_SECTION_KEYS
    )

    # validation
    assert (
        context[
            "validation"
        ][
            "valid"
        ]
        is True
    )

    # AI入力安全性
    assert (
        "raw_chart_result"
        not in context
    )

    assert (
        "chart_result"
        not in context
    )
