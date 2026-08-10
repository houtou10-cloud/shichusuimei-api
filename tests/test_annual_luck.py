"""
tests/test_annual_luck.py

engine.annual_luck の単体テスト。

対象:
    annual_luck_v1

主な検証内容:
    1. 西暦年 -> 六十干支
    2. 立春境界
    3. 天干・地支
    4. 五行・陰陽
    5. 通変星
    6. 十二運
    7. 蔵干
    8. 本気
    9. useful_gods_v3 連携
    10. current_luck_v1 連携
    11. 複数年計算
    12. alias
    13. metadata
    14. 不正入力
"""

from datetime import datetime

import pytest

from engine.annual_luck import (
    ANNUAL_LUCK_METHOD,
    ANNUAL_LUCK_STATUS,
    BRANCH_ELEMENTS,
    CONTROLS,
    FIVE_ELEMENTS,
    GENERATES,
    build_annual_luck,
    build_annual_luck_reasoning,
    build_hidden_stem_data,
    calculate_annual_ganzhi,
    calculate_annual_ganzhi_for_datetime,
    calculate_annual_luck,
    calculate_annual_luck_for_datetime,
    calculate_annual_luck_range,
    evaluate_against_current_luck,
    evaluate_annual_luck,
    evaluate_element_against_useful_gods,
    get_branch_element,
    get_element_relationship,
)


# =========================================================
# Fixtures
# =========================================================


@pytest.fixture
def useful_gods_fixture():
    """
    useful_gods_v3 を模した最小fixture。

    primary:
        火

    final:
        火・木

    unfavorable:
        金・水

    neutral:
        土
    """

    return {
        "primary_useful_element": "火",
        "final_useful_elements": [
            "火",
            "木",
        ],
        "support_balance": {
            "unfavorable_elements": [
                "金",
                "水",
            ],
            "neutral_elements": [
                "土",
            ],
        },
        "method": "useful_gods_v3",
    }


@pytest.fixture
def current_luck_fixture():
    """
    current_luck_v1 を模したfixture。

    現在大運:
        甲申

    天干:
        甲 = 木

    地支:
        申 = 金
    """

    return {
        "has_current_luck": True,
        "current_luck_pillar": {
            "index": 1,
            "ganzhi": "甲申",
            "stem": "甲",
            "branch": "申",
            "stem_element": "木",
            "branch_element": "金",
        },
        "method": "current_luck_v1",
    }


@pytest.fixture
def current_luck_minimal_fixture():
    """
    五行情報を持たない current_luck fixture。

    annual_luck 側が stem / branch から
    五行を補完できることを確認する。
    """

    return {
        "has_current_luck": True,
        "current_luck_pillar": {
            "index": 1,
            "ganzhi": "甲申",
            "stem": "甲",
            "branch": "申",
        },
        "method": "current_luck_v1",
    }


# =========================================================
# Constants
# =========================================================


def test_annual_luck_method_constant():
    assert (
        ANNUAL_LUCK_METHOD
        == "annual_luck_v1"
    )


def test_annual_luck_status_constant():
    assert (
        ANNUAL_LUCK_STATUS
        == "provisional_annual_luck_v1"
    )


def test_five_elements():
    assert FIVE_ELEMENTS == {
        "木",
        "火",
        "土",
        "金",
        "水",
    }


def test_branch_elements_contains_all_branches():
    assert set(
        BRANCH_ELEMENTS.keys()
    ) == {
        "子",
        "丑",
        "寅",
        "卯",
        "辰",
        "巳",
        "午",
        "未",
        "申",
        "酉",
        "戌",
        "亥",
    }


def test_generates_cycle():
    assert GENERATES == {
        "木": "火",
        "火": "土",
        "土": "金",
        "金": "水",
        "水": "木",
    }


def test_controls_cycle():
    assert CONTROLS == {
        "木": "土",
        "火": "金",
        "土": "水",
        "金": "木",
        "水": "火",
    }


# =========================================================
# calculate_annual_ganzhi
# =========================================================


@pytest.mark.parametrize(
    (
        "year",
        "expected",
    ),
    [
        (1984, "甲子"),
        (1985, "乙丑"),
        (2023, "癸卯"),
        (2024, "甲辰"),
        (2025, "乙巳"),
        (2026, "丙午"),
        (2027, "丁未"),
        (2043, "癸亥"),
        (2044, "甲子"),
    ],
)
def test_calculate_annual_ganzhi(
    year,
    expected,
):
    assert (
        calculate_annual_ganzhi(
            year
        )
        == expected
    )


def test_calculate_annual_ganzhi_cycle_60_years():
    assert (
        calculate_annual_ganzhi(
            1984
        )
        == calculate_annual_ganzhi(
            2044
        )
    )


def test_calculate_annual_ganzhi_previous_cycle():
    assert (
        calculate_annual_ganzhi(
            1924
        )
        == "甲子"
    )


def test_calculate_annual_ganzhi_bool_rejected():
    with pytest.raises(
        TypeError
    ):
        calculate_annual_ganzhi(
            True
        )


def test_calculate_annual_ganzhi_non_int():
    with pytest.raises(
        TypeError
    ):
        calculate_annual_ganzhi(
            2026.0
        )


def test_calculate_annual_ganzhi_zero():
    with pytest.raises(
        ValueError
    ):
        calculate_annual_ganzhi(
            0
        )


def test_calculate_annual_ganzhi_negative():
    with pytest.raises(
        ValueError
    ):
        calculate_annual_ganzhi(
            -1
        )


# =========================================================
# calculate_annual_ganzhi_for_datetime
# =========================================================


def test_annual_ganzhi_before_lichun():
    result = (
        calculate_annual_ganzhi_for_datetime(
            datetime(
                2026,
                2,
                3,
                23,
                59,
            )
        )
    )

    assert result[
        "calendar_year"
    ] == 2026

    assert result[
        "effective_year"
    ] == 2025

    assert result[
        "ganzhi"
    ] == "乙巳"


def test_annual_ganzhi_at_lichun():
    result = (
        calculate_annual_ganzhi_for_datetime(
            datetime(
                2026,
                2,
                4,
                0,
                0,
            )
        )
    )

    assert result[
        "effective_year"
    ] == 2026

    assert result[
        "ganzhi"
    ] == "丙午"


def test_annual_ganzhi_after_lichun():
    result = (
        calculate_annual_ganzhi_for_datetime(
            datetime(
                2026,
                8,
                10,
                12,
                0,
            )
        )
    )

    assert result[
        "calendar_year"
    ] == 2026

    assert result[
        "effective_year"
    ] == 2026

    assert result[
        "ganzhi"
    ] == "丙午"


def test_annual_ganzhi_datetime_invalid_type():
    with pytest.raises(
        TypeError
    ):
        calculate_annual_ganzhi_for_datetime(
            "2026-08-10"
        )


# =========================================================
# Branch elements
# =========================================================


@pytest.mark.parametrize(
    (
        "branch",
        "expected",
    ),
    [
        ("子", "水"),
        ("丑", "土"),
        ("寅", "木"),
        ("卯", "木"),
        ("辰", "土"),
        ("巳", "火"),
        ("午", "火"),
        ("未", "土"),
        ("申", "金"),
        ("酉", "金"),
        ("戌", "土"),
        ("亥", "水"),
    ],
)
def test_get_branch_element(
    branch,
    expected,
):
    assert (
        get_branch_element(
            branch
        )
        == expected
    )


def test_get_branch_element_invalid():
    with pytest.raises(
        ValueError
    ):
        get_branch_element(
            "A"
        )


# =========================================================
# Five-element relationships
# =========================================================


@pytest.mark.parametrize(
    (
        "source",
        "target",
        "expected",
    ),
    [
        (
            "木",
            "木",
            "same",
        ),
        (
            "木",
            "火",
            "generates",
        ),
        (
            "火",
            "木",
            "generated_by",
        ),
        (
            "木",
            "土",
            "controls",
        ),
        (
            "土",
            "木",
            "controlled_by",
        ),
        (
            "火",
            "土",
            "generates",
        ),
        (
            "金",
            "水",
            "generates",
        ),
        (
            "水",
            "木",
            "generates",
        ),
        (
            "火",
            "金",
            "controls",
        ),
        (
            "水",
            "火",
            "controls",
        ),
    ],
)
def test_get_element_relationship(
    source,
    target,
    expected,
):
    assert (
        get_element_relationship(
            source,
            target,
        )
        == expected
    )


def test_get_element_relationship_invalid_source():
    with pytest.raises(
        ValueError
    ):
        get_element_relationship(
            "風",
            "木",
        )


def test_get_element_relationship_invalid_target():
    with pytest.raises(
        ValueError
    ):
        get_element_relationship(
            "木",
            "風",
        )


# =========================================================
# Useful gods
# =========================================================


def test_useful_gods_none():
    result = (
        evaluate_element_against_useful_gods(
            "火",
            None,
        )
    )

    assert result[
        "is_useful"
    ] is None

    assert result[
        "is_primary_useful"
    ] is None

    assert result[
        "is_unfavorable"
    ] is None

    assert result[
        "priority"
    ] is None

    assert result[
        "relationship"
    ] == "unknown"


def test_primary_useful_element(
    useful_gods_fixture,
):
    result = (
        evaluate_element_against_useful_gods(
            "火",
            useful_gods_fixture,
        )
    )

    assert result[
        "is_useful"
    ] is True

    assert result[
        "is_primary_useful"
    ] is True

    assert result[
        "is_unfavorable"
    ] is False

    assert result[
        "priority"
    ] == 1

    assert result[
        "relationship"
    ] == "primary_useful"


def test_secondary_useful_element(
    useful_gods_fixture,
):
    result = (
        evaluate_element_against_useful_gods(
            "木",
            useful_gods_fixture,
        )
    )

    assert result[
        "is_useful"
    ] is True

    assert result[
        "is_primary_useful"
    ] is False

    assert result[
        "is_unfavorable"
    ] is False

    assert result[
        "priority"
    ] == 2

    assert result[
        "relationship"
    ] == "secondary_useful"


@pytest.mark.parametrize(
    "element",
    [
        "金",
        "水",
    ],
)
def test_unfavorable_element(
    useful_gods_fixture,
    element,
):
    result = (
        evaluate_element_against_useful_gods(
            element,
            useful_gods_fixture,
        )
    )

    assert result[
        "is_useful"
    ] is False

    assert result[
        "is_unfavorable"
    ] is True

    assert result[
        "relationship"
    ] == "support_unfavorable"


def test_neutral_element(
    useful_gods_fixture,
):
    result = (
        evaluate_element_against_useful_gods(
            "土",
            useful_gods_fixture,
        )
    )

    assert result[
        "is_useful"
    ] is False

    assert result[
        "is_unfavorable"
    ] is False

    assert result[
        "relationship"
    ] == "neutral"


def test_useful_gods_invalid_element():
    with pytest.raises(
        ValueError
    ):
        evaluate_element_against_useful_gods(
            "風",
            None,
        )


# =========================================================
# Hidden stems
# =========================================================


def test_build_hidden_stem_data_for_午():
    result = (
        build_hidden_stem_data(
            day_master_stem="乙",
            branch="午",
        )
    )

    assert "hidden_stems" in result

    assert "main_hidden_stem" in result

    assert (
        "main_hidden_stem_ten_god"
        in result
    )

    assert (
        "main_hidden_stem_element"
        in result
    )

    assert (
        "hidden_stem_ten_gods"
        in result
    )


def test_hidden_stem_data_not_empty():
    result = (
        build_hidden_stem_data(
            day_master_stem="乙",
            branch="午",
        )
    )

    assert len(
        result["hidden_stems"]
    ) >= 1


def test_hidden_stem_ten_gods_length():
    result = (
        build_hidden_stem_data(
            day_master_stem="乙",
            branch="午",
        )
    )

    assert len(
        result[
            "hidden_stem_ten_gods"
        ]
    ) == len(
        result[
            "hidden_stems"
        ]
    )


def test_hidden_stem_entries_required_keys():
    result = (
        build_hidden_stem_data(
            day_master_stem="乙",
            branch="午",
        )
    )

    for item in result[
        "hidden_stem_ten_gods"
    ]:
        assert {
            "stem",
            "ten_god",
            "element",
            "yin_yang",
        }.issubset(
            item.keys()
        )


def test_main_hidden_stem_is_in_hidden_stems():
    result = (
        build_hidden_stem_data(
            day_master_stem="乙",
            branch="午",
        )
    )

    assert (
        result[
            "main_hidden_stem"
        ]
        in result[
            "hidden_stems"
        ]
    )


# =========================================================
# Current luck relation
# =========================================================


def test_current_luck_none():
    result = (
        evaluate_against_current_luck(
            annual_stem_element="火",
            annual_branch_element="火",
            current_luck=None,
        )
    )

    assert result[
        "has_current_luck"
    ] is None

    assert result[
        "status"
    ] == "unknown"


def test_current_luck_not_active():
    result = (
        evaluate_against_current_luck(
            annual_stem_element="火",
            annual_branch_element="火",
            current_luck={
                "has_current_luck": False,
                "current_luck_pillar": None,
            },
        )
    )

    assert result[
        "has_current_luck"
    ] is False

    assert result[
        "status"
    ] == "no_current_luck"


def test_current_luck_relation(
    current_luck_fixture,
):
    result = (
        evaluate_against_current_luck(
            annual_stem_element="火",
            annual_branch_element="火",
            current_luck=(
                current_luck_fixture
            ),
        )
    )

    assert result[
        "has_current_luck"
    ] is True

    assert result[
        "current_luck_ganzhi"
    ] == "甲申"

    assert result[
        "current_luck_stem_element"
    ] == "木"

    assert result[
        "current_luck_branch_element"
    ] == "金"

    # 木 -> 火
    assert result[
        "stem_element_relation"
    ] == "generates"

    # 金と火:
    # 火が金を剋すため、
    # source=金 / target=火 では
    # controlled_by
    assert result[
        "branch_element_relation"
    ] == "controlled_by"

    assert result[
        "status"
    ] == "evaluated"


def test_current_luck_elements_can_be_inferred(
    current_luck_minimal_fixture,
):
    result = (
        evaluate_against_current_luck(
            annual_stem_element="火",
            annual_branch_element="火",
            current_luck=(
                current_luck_minimal_fixture
            ),
        )
    )

    assert result[
        "current_luck_stem_element"
    ] == "木"

    assert result[
        "current_luck_branch_element"
    ] == "金"

    assert result[
        "status"
    ] == "evaluated"


# =========================================================
# Core annual luck
# =========================================================


def test_calculate_annual_luck_2026():
    result = (
        calculate_annual_luck(
            year=2026,
            day_master_stem="乙",
        )
    )

    assert result[
        "year"
    ] == 2026

    assert result[
        "ganzhi"
    ] == "丙午"

    assert result[
        "stem"
    ] == "丙"

    assert result[
        "branch"
    ] == "午"


def test_annual_luck_2026_elements():
    result = (
        calculate_annual_luck(
            year=2026,
            day_master_stem="乙",
        )
    )

    assert result[
        "stem_element"
    ] == "火"

    assert result[
        "branch_element"
    ] == "火"


def test_annual_luck_2026_stem_yin_yang():
    result = (
        calculate_annual_luck(
            year=2026,
            day_master_stem="乙",
        )
    )

    assert result[
        "stem_yin_yang"
    ] == "陽"


def test_annual_luck_day_master():
    result = (
        calculate_annual_luck(
            year=2026,
            day_master_stem="乙",
        )
    )

    assert result[
        "day_master_stem"
    ] == "乙"

    assert result[
        "day_master_element"
    ] == "木"


def test_annual_luck_2026_ten_god():
    """
    乙 -> 丙

    木が火を生じるため output。

    乙 = 陰
    丙 = 陽

    陰陽が異なるので傷官。
    """

    result = (
        calculate_annual_luck(
            year=2026,
            day_master_stem="乙",
        )
    )

    assert result[
        "stem_ten_god"
    ] == "傷官"


def test_annual_luck_2026_twelve_stage():
    """
    乙 × 午 = 長生
    """

    result = (
        calculate_annual_luck(
            year=2026,
            day_master_stem="乙",
        )
    )

    assert result[
        "twelve_stage"
    ] == "長生"


def test_annual_luck_hidden_stems():
    result = (
        calculate_annual_luck(
            year=2026,
            day_master_stem="乙",
        )
    )

    assert isinstance(
        result[
            "hidden_stems"
        ],
        list,
    )

    assert len(
        result[
            "hidden_stems"
        ]
    ) >= 1


def test_annual_luck_main_hidden_stem():
    result = (
        calculate_annual_luck(
            year=2026,
            day_master_stem="乙",
        )
    )

    assert (
        result[
            "main_hidden_stem"
        ]
        in result[
            "hidden_stems"
        ]
    )


def test_annual_luck_hidden_stem_ten_gods():
    result = (
        calculate_annual_luck(
            year=2026,
            day_master_stem="乙",
        )
    )

    assert isinstance(
        result[
            "hidden_stem_ten_gods"
        ],
        list,
    )

    assert len(
        result[
            "hidden_stem_ten_gods"
        ]
    ) == len(
        result[
            "hidden_stems"
        ]
    )


# =========================================================
# Required keys
# =========================================================


def test_annual_luck_required_keys():
    result = (
        calculate_annual_luck(
            year=2026,
            day_master_stem="乙",
        )
    )

    required = {
        "year",
        "ganzhi",
        "stem",
        "branch",
        "stem_element",
        "stem_yin_yang",
        "branch_element",
        "day_master_stem",
        "day_master_element",
        "stem_ten_god",
        "twelve_stage",
        "hidden_stems",
        "main_hidden_stem",
        "main_hidden_stem_ten_god",
        "main_hidden_stem_element",
        "hidden_stem_ten_gods",
        "stem_useful_relation",
        "branch_useful_relation",
        "current_luck_relation",
        "reasoning",
        "evidence",
        "method",
        "status",
        "notes",
    }

    assert required.issubset(
        result.keys()
    )


# =========================================================
# Metadata
# =========================================================


def test_annual_luck_metadata():
    result = (
        calculate_annual_luck(
            year=2026,
            day_master_stem="乙",
        )
    )

    assert result[
        "method"
    ] == "annual_luck_v1"

    assert result[
        "status"
    ] == (
        "provisional_annual_luck_v1"
    )


def test_annual_luck_notes():
    result = (
        calculate_annual_luck(
            year=2026,
            day_master_stem="乙",
        )
    )

    assert isinstance(
        result["notes"],
        list,
    )

    assert len(
        result["notes"]
    ) >= 1


def test_annual_luck_reasoning():
    result = (
        calculate_annual_luck(
            year=2026,
            day_master_stem="乙",
        )
    )

    assert isinstance(
        result["reasoning"],
        list,
    )

    assert len(
        result["reasoning"]
    ) >= 1


def test_annual_luck_evidence():
    result = (
        calculate_annual_luck(
            year=2026,
            day_master_stem="乙",
        )
    )

    evidence = result[
        "evidence"
    ]

    assert evidence[
        "year"
    ] == result[
        "year"
    ]

    assert evidence[
        "ganzhi"
    ] == result[
        "ganzhi"
    ]

    assert evidence[
        "day_master_stem"
    ] == result[
        "day_master_stem"
    ]

    assert evidence[
        "stem_ten_god"
    ] == result[
        "stem_ten_god"
    ]

    assert evidence[
        "twelve_stage"
    ] == result[
        "twelve_stage"
    ]


# =========================================================
# Useful gods integration
# =========================================================


def test_annual_luck_useful_gods(
    useful_gods_fixture,
):
    result = (
        calculate_annual_luck(
            year=2026,
            day_master_stem="乙",
            useful_gods=(
                useful_gods_fixture
            ),
        )
    )

    # 丙 = 火
    assert result[
        "stem_useful_relation"
    ][
        "relationship"
    ] == "primary_useful"

    # 午 = 火
    assert result[
        "branch_useful_relation"
    ][
        "relationship"
    ] == "primary_useful"


def test_annual_luck_without_useful_gods():
    result = (
        calculate_annual_luck(
            year=2026,
            day_master_stem="乙",
        )
    )

    assert result[
        "stem_useful_relation"
    ][
        "relationship"
    ] == "unknown"

    assert result[
        "branch_useful_relation"
    ][
        "relationship"
    ] == "unknown"


# =========================================================
# Current luck integration
# =========================================================


def test_annual_luck_current_luck(
    current_luck_fixture,
):
    result = (
        calculate_annual_luck(
            year=2026,
            day_master_stem="乙",
            current_luck=(
                current_luck_fixture
            ),
        )
    )

    relation = result[
        "current_luck_relation"
    ]

    assert relation[
        "has_current_luck"
    ] is True

    assert relation[
        "current_luck_ganzhi"
    ] == "甲申"

    assert relation[
        "stem_element_relation"
    ] == "generates"

    assert relation[
        "branch_element_relation"
    ] == "controlled_by"


def test_annual_luck_without_current_luck():
    result = (
        calculate_annual_luck(
            year=2026,
            day_master_stem="乙",
        )
    )

    assert result[
        "current_luck_relation"
    ][
        "status"
    ] == "unknown"


# =========================================================
# Combined integration
# =========================================================


def test_annual_luck_with_useful_and_current(
    useful_gods_fixture,
    current_luck_fixture,
):
    result = (
        calculate_annual_luck(
            year=2026,
            day_master_stem="乙",
            useful_gods=(
                useful_gods_fixture
            ),
            current_luck=(
                current_luck_fixture
            ),
        )
    )

    assert result[
        "stem_useful_relation"
    ][
        "relationship"
    ] == "primary_useful"

    assert result[
        "current_luck_relation"
    ][
        "status"
    ] == "evaluated"


# =========================================================
# build_annual_luck
# =========================================================


def test_build_annual_luck_direct():
    result = (
        build_annual_luck(
            year=2026,
            day_master_stem="乙",
        )
    )

    assert result[
        "ganzhi"
    ] == "丙午"

    assert result[
        "stem_ten_god"
    ] == "傷官"

    assert result[
        "twelve_stage"
    ] == "長生"


# =========================================================
# Reasoning builder
# =========================================================


def test_build_annual_luck_reasoning():
    reasoning = (
        build_annual_luck_reasoning(
            year=2026,
            ganzhi="丙午",
            stem_ten_god="傷官",
            twelve_stage="長生",
            stem_useful_relation={
                "relationship": (
                    "primary_useful"
                )
            },
            branch_useful_relation={
                "relationship": (
                    "primary_useful"
                )
            },
        )
    )

    assert isinstance(
        reasoning,
        list,
    )

    assert len(
        reasoning
    ) >= 5

    joined = "".join(
        reasoning
    )

    assert "2026" in joined
    assert "丙午" in joined
    assert "傷官" in joined
    assert "長生" in joined


# =========================================================
# Datetime annual luck
# =========================================================


def test_annual_luck_datetime_before_lichun():
    result = (
        calculate_annual_luck_for_datetime(
            target_datetime=datetime(
                2026,
                2,
                3,
                23,
                59,
            ),
            day_master_stem="乙",
        )
    )

    assert result[
        "calendar_year"
    ] == 2026

    assert result[
        "effective_year"
    ] == 2025

    assert result[
        "year"
    ] == 2025

    assert result[
        "ganzhi"
    ] == "乙巳"

    assert result[
        "year_boundary_applied"
    ] is True


def test_annual_luck_datetime_at_lichun():
    result = (
        calculate_annual_luck_for_datetime(
            target_datetime=datetime(
                2026,
                2,
                4,
                0,
                0,
            ),
            day_master_stem="乙",
        )
    )

    assert result[
        "effective_year"
    ] == 2026

    assert result[
        "year"
    ] == 2026

    assert result[
        "ganzhi"
    ] == "丙午"


def test_annual_luck_datetime_after_lichun():
    result = (
        calculate_annual_luck_for_datetime(
            target_datetime=datetime(
                2026,
                8,
                10,
                15,
                0,
            ),
            day_master_stem="乙",
        )
    )

    assert result[
        "calendar_year"
    ] == 2026

    assert result[
        "effective_year"
    ] == 2026

    assert result[
        "ganzhi"
    ] == "丙午"

    assert (
        result[
            "target_datetime"
        ]
        == "2026-08-10T15:00:00"
    )

    assert (
        result[
            "year_boundary_rule"
        ]
        == "暫定：立春2月4日00:00"
    )


def test_annual_luck_datetime_invalid():
    with pytest.raises(
        TypeError
    ):
        calculate_annual_luck_for_datetime(
            target_datetime=2026,
            day_master_stem="乙",
        )


# =========================================================
# Range
# =========================================================


def test_annual_luck_range():
    result = (
        calculate_annual_luck_range(
            start_year=2024,
            end_year=2027,
            day_master_stem="乙",
        )
    )

    assert len(
        result
    ) == 4

    assert [
        item["year"]
        for item in result
    ] == [
        2024,
        2025,
        2026,
        2027,
    ]

    assert [
        item["ganzhi"]
        for item in result
    ] == [
        "甲辰",
        "乙巳",
        "丙午",
        "丁未",
    ]


def test_annual_luck_range_single_year():
    result = (
        calculate_annual_luck_range(
            start_year=2026,
            end_year=2026,
            day_master_stem="乙",
        )
    )

    assert len(
        result
    ) == 1

    assert result[
        0
    ][
        "ganzhi"
    ] == "丙午"


def test_annual_luck_range_invalid_order():
    with pytest.raises(
        ValueError
    ):
        calculate_annual_luck_range(
            start_year=2027,
            end_year=2026,
            day_master_stem="乙",
        )


def test_annual_luck_range_invalid_start_year():
    with pytest.raises(
        ValueError
    ):
        calculate_annual_luck_range(
            start_year=0,
            end_year=2026,
            day_master_stem="乙",
        )


def test_annual_luck_range_invalid_end_year():
    with pytest.raises(
        ValueError
    ):
        calculate_annual_luck_range(
            start_year=2026,
            end_year=0,
            day_master_stem="乙",
        )


# =========================================================
# Alias
# =========================================================


def test_evaluate_annual_luck_alias():
    direct = (
        calculate_annual_luck(
            year=2026,
            day_master_stem="乙",
        )
    )

    alias = (
        evaluate_annual_luck(
            year=2026,
            day_master_stem="乙",
        )
    )

    assert alias == direct


# =========================================================
# Invalid day master
# =========================================================


def test_invalid_day_master():
    with pytest.raises(
        ValueError
    ):
        calculate_annual_luck(
            year=2026,
            day_master_stem="A",
        )


def test_empty_day_master():
    with pytest.raises(
        ValueError
    ):
        calculate_annual_luck(
            year=2026,
            day_master_stem="",
        )


# =========================================================
# Multiple day masters
# =========================================================


@pytest.mark.parametrize(
    "day_master",
    [
        "甲",
        "乙",
        "丙",
        "丁",
        "戊",
        "己",
        "庚",
        "辛",
        "壬",
        "癸",
    ],
)
def test_all_day_masters_supported(
    day_master,
):
    result = (
        calculate_annual_luck(
            year=2026,
            day_master_stem=(
                day_master
            ),
        )
    )

    assert result[
        "day_master_stem"
    ] == day_master

    assert result[
        "ganzhi"
    ] == "丙午"

    assert isinstance(
        result[
            "stem_ten_god"
        ],
        str,
    )

    assert isinstance(
        result[
            "twelve_stage"
        ],
        str,
    )


# =========================================================
# Known ten-god relationships
# =========================================================


@pytest.mark.parametrize(
    (
        "day_master",
        "expected",
    ),
    [
        (
            "甲",
            "食神",
        ),
        (
            "乙",
            "傷官",
        ),
        (
            "丙",
            "比肩",
        ),
        (
            "丁",
            "劫財",
        ),
        (
            "戊",
            "偏印",
        ),
        (
            "己",
            "印綬",
        ),
        (
            "庚",
            "偏官",
        ),
        (
            "辛",
            "正官",
        ),
        (
            "壬",
            "偏財",
        ),
        (
            "癸",
            "正財",
        ),
    ],
)
def test_2026_stem_ten_gods(
    day_master,
    expected,
):
    """
    2026年の天干は丙。

    各日主に対する丙の
    通変星を固定する。
    """

    result = (
        calculate_annual_luck(
            year=2026,
            day_master_stem=(
                day_master
            ),
        )
    )

    assert result[
        "stem"
    ] == "丙"

    assert result[
        "stem_ten_god"
    ] == expected


# =========================================================
# Known twelve stages
# =========================================================


@pytest.mark.parametrize(
    (
        "day_master",
        "expected",
    ),
    [
        (
            "甲",
            "死",
        ),
        (
            "乙",
            "長生",
        ),
        (
            "丙",
            "帝旺",
        ),
        (
            "丁",
            "建禄",
        ),
        (
            "戊",
            "帝旺",
        ),
        (
            "己",
            "建禄",
        ),
        (
            "庚",
            "沐浴",
        ),
        (
            "辛",
            "病",
        ),
        (
            "壬",
            "胎",
        ),
        (
            "癸",
            "絶",
        ),
    ],
)
def test_2026_twelve_stages(
    day_master,
    expected,
):
    """
    2026年の地支は午。

    各日主 × 午の十二運を固定する。
    """

    result = (
        calculate_annual_luck(
            year=2026,
            day_master_stem=(
                day_master
            ),
        )
    )

    assert result[
        "branch"
    ] == "午"

    assert result[
        "twelve_stage"
    ] == expected


# =========================================================
# Regression: verified-style chart
# =========================================================


def test_verified_1985_style_2026_annual_luck():
    """
    既存検証命式:

        1985-07-17 21:50
        石川県
        女性

    日柱:
        乙巳

    日主:
        乙

    2026年:
        丙午

    よって:
        丙 = 傷官
        午 = 長生
    """

    result = (
        calculate_annual_luck(
            year=2026,
            day_master_stem="乙",
        )
    )

    assert result[
        "ganzhi"
    ] == "丙午"

    assert result[
        "stem"
    ] == "丙"

    assert result[
        "branch"
    ] == "午"

    assert result[
        "stem_ten_god"
    ] == "傷官"

    assert result[
        "twelve_stage"
    ] == "長生"

    assert result[
        "method"
    ] == "annual_luck_v1"


# =========================================================
# Data independence
# =========================================================


def test_useful_gods_input_not_mutated(
    useful_gods_fixture,
):
    original = {
        "primary_useful_element": (
            useful_gods_fixture[
                "primary_useful_element"
            ]
        ),
        "final_useful_elements": list(
            useful_gods_fixture[
                "final_useful_elements"
            ]
        ),
        "support_balance": {
            "unfavorable_elements": list(
                useful_gods_fixture[
                    "support_balance"
                ][
                    "unfavorable_elements"
                ]
            ),
            "neutral_elements": list(
                useful_gods_fixture[
                    "support_balance"
                ][
                    "neutral_elements"
                ]
            ),
        },
        "method": (
            useful_gods_fixture[
                "method"
            ]
        ),
    }

    calculate_annual_luck(
        year=2026,
        day_master_stem="乙",
        useful_gods=(
            useful_gods_fixture
        ),
    )

    assert (
        useful_gods_fixture
        == original
    )


def test_current_luck_input_not_mutated(
    current_luck_fixture,
):
    original = {
        "has_current_luck": True,
        "current_luck_pillar": {
            "index": 1,
            "ganzhi": "甲申",
            "stem": "甲",
            "branch": "申",
            "stem_element": "木",
            "branch_element": "金",
        },
        "method": "current_luck_v1",
    }

    calculate_annual_luck(
        year=2026,
        day_master_stem="乙",
        current_luck=(
            current_luck_fixture
        ),
    )

    assert (
        current_luck_fixture
        == original
    )
