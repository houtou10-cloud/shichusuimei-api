"""
tests/test_climate_useful_gods.py

engine/climate_useful_gods.py の単体テスト。

検証対象
--------
- 定数・メタデータ
- 日干検証
- 月支検証
- 日主五行変換
- 十二月支の季節分類
- 季節日本語表記
- 寒暖燥湿プロファイル
- 調候要求
- 調候五行スコア
- 候補順位
- 候補詳細
- confidence
- reasoning
- evaluate_climate_useful_gods
- 春夏秋冬の代表ケース
- 土用月
- 不正入力
"""

import pytest

from engine.climate_useful_gods import (
    BRANCHES,
    CLIMATE_FUNCTIONS,
    CLIMATE_USEFUL_GODS_METHOD,
    CLIMATE_USEFUL_GODS_STATUS,
    ELEMENTS,
    MONTH_BRANCH_CLIMATE_ADJUSTMENT,
    MONTH_BRANCH_TO_SEASON,
    SEASON_CLIMATE_PROFILE,
    SEASON_JAPANESE,
    STEMS,
    STEM_TO_ELEMENT,
    build_climate_candidate_details,
    build_climate_element_scores,
    build_climate_reasoning,
    calculate_climate_profile,
    determine_climate_confidence,
    determine_climate_needs,
    evaluate_climate_useful_gods,
    get_day_master_element,
    get_season,
    get_season_japanese,
    rank_climate_elements,
    validate_day_master_stem,
    validate_month_branch,
)


# =========================================================
# Constants
# =========================================================


def test_method_constant():
    assert (
        CLIMATE_USEFUL_GODS_METHOD
        == "climate_useful_gods_v1"
    )


def test_status_constant():
    assert (
        CLIMATE_USEFUL_GODS_STATUS
        == "provisional_climate_useful_gods"
    )


def test_elements_constant():
    assert ELEMENTS == (
        "木",
        "火",
        "土",
        "金",
        "水",
    )


def test_stems_constant():
    assert STEMS == (
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
    )


def test_branches_constant():
    assert BRANCHES == (
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
    )


def test_stem_to_element_has_all_stems():
    assert set(
        STEM_TO_ELEMENT.keys()
    ) == set(
        STEMS
    )


def test_month_branch_to_season_has_all_branches():
    assert set(
        MONTH_BRANCH_TO_SEASON.keys()
    ) == set(
        BRANCHES
    )


def test_branch_adjustment_has_all_branches():
    assert set(
        MONTH_BRANCH_CLIMATE_ADJUSTMENT.keys()
    ) == set(
        BRANCHES
    )


def test_season_profiles_exist():
    assert set(
        SEASON_CLIMATE_PROFILE.keys()
    ) == {
        "spring",
        "summer",
        "autumn",
        "winter",
    }


def test_climate_functions_have_all_elements():
    assert set(
        CLIMATE_FUNCTIONS.keys()
    ) == set(
        ELEMENTS
    )


# =========================================================
# Validation
# =========================================================


@pytest.mark.parametrize(
    "stem",
    STEMS,
)
def test_validate_day_master_stem_valid(
    stem,
):
    validate_day_master_stem(
        stem
    )


def test_validate_day_master_stem_type_error():
    with pytest.raises(
        TypeError
    ):
        validate_day_master_stem(
            123
        )


def test_validate_day_master_stem_value_error():
    with pytest.raises(
        ValueError
    ):
        validate_day_master_stem(
            "A"
        )


@pytest.mark.parametrize(
    "branch",
    BRANCHES,
)
def test_validate_month_branch_valid(
    branch,
):
    validate_month_branch(
        branch
    )


def test_validate_month_branch_type_error():
    with pytest.raises(
        TypeError
    ):
        validate_month_branch(
            123
        )


def test_validate_month_branch_value_error():
    with pytest.raises(
        ValueError
    ):
        validate_month_branch(
            "A"
        )


# =========================================================
# Day-master element
# =========================================================


@pytest.mark.parametrize(
    (
        "stem",
        "expected_element",
    ),
    [
        ("甲", "木"),
        ("乙", "木"),
        ("丙", "火"),
        ("丁", "火"),
        ("戊", "土"),
        ("己", "土"),
        ("庚", "金"),
        ("辛", "金"),
        ("壬", "水"),
        ("癸", "水"),
    ],
)
def test_get_day_master_element(
    stem,
    expected_element,
):
    assert (
        get_day_master_element(
            stem
        )
        == expected_element
    )


# =========================================================
# Season
# =========================================================


@pytest.mark.parametrize(
    (
        "branch",
        "expected_season",
    ),
    [
        ("寅", "spring"),
        ("卯", "spring"),
        ("辰", "spring"),
        ("巳", "summer"),
        ("午", "summer"),
        ("未", "summer"),
        ("申", "autumn"),
        ("酉", "autumn"),
        ("戌", "autumn"),
        ("亥", "winter"),
        ("子", "winter"),
        ("丑", "winter"),
    ],
)
def test_get_season(
    branch,
    expected_season,
):
    assert (
        get_season(
            branch
        )
        == expected_season
    )


@pytest.mark.parametrize(
    (
        "season",
        "expected",
    ),
    [
        ("spring", "春"),
        ("summer", "夏"),
        ("autumn", "秋"),
        ("winter", "冬"),
    ],
)
def test_get_season_japanese(
    season,
    expected,
):
    assert (
        get_season_japanese(
            season
        )
        == expected
    )


def test_get_season_japanese_invalid():
    with pytest.raises(
        ValueError
    ):
        get_season_japanese(
            "rainy"
        )


# =========================================================
# Climate profile
# =========================================================


@pytest.mark.parametrize(
    "branch",
    BRANCHES,
)
def test_calculate_climate_profile_structure(
    branch,
):
    result = (
        calculate_climate_profile(
            branch
        )
    )

    required_keys = {
        "season",
        "season_japanese",
        "month_branch",
        "heat_score",
        "moisture_score",
        "temperature_label",
        "moisture_label",
        "base_profile",
        "branch_adjustment",
    }

    assert required_keys.issubset(
        result.keys()
    )

    assert (
        result[
            "month_branch"
        ]
        == branch
    )

    assert isinstance(
        result[
            "heat_score"
        ],
        float,
    )

    assert isinstance(
        result[
            "moisture_score"
        ],
        float,
    )


def test_climate_profile_child_month():
    result = (
        calculate_climate_profile(
            "子"
        )
    )

    assert (
        result["season"]
        == "winter"
    )

    assert (
        result[
            "season_japanese"
        ]
        == "冬"
    )

    assert (
        result[
            "heat_score"
        ]
        == -1.25
    )

    assert (
        result[
            "moisture_score"
        ]
        == 1.0
    )

    assert (
        result[
            "temperature_label"
        ]
        == "cold"
    )

    assert (
        result[
            "moisture_label"
        ]
        == "moist"
    )


def test_climate_profile_horse_month():
    result = (
        calculate_climate_profile(
            "午"
        )
    )

    assert (
        result["season"]
        == "summer"
    )

    assert (
        result[
            "heat_score"
        ]
        == 1.3
    )

    assert (
        result[
            "moisture_score"
        ]
        == -0.45
    )

    assert (
        result[
            "temperature_label"
        ]
        == "hot"
    )

    assert (
        result[
            "moisture_label"
        ]
        == "slightly_dry"
    )


def test_climate_profile_rooster_month():
    result = (
        calculate_climate_profile(
            "酉"
        )
    )

    assert (
        result["season"]
        == "autumn"
    )

    assert (
        result[
            "heat_score"
        ]
        == -0.35
    )

    assert (
        result[
            "moisture_score"
        ]
        == -1.25
    )

    assert (
        result[
            "temperature_label"
        ]
        == "slightly_cool"
    )

    assert (
        result[
            "moisture_label"
        ]
        == "dry"
    )


def test_climate_profile_rabbit_month():
    result = (
        calculate_climate_profile(
            "卯"
        )
    )

    assert (
        result["season"]
        == "spring"
    )

    assert (
        result[
            "heat_score"
        ]
        == 0.0
    )

    assert (
        result[
            "moisture_score"
        ]
        == 0.6
    )

    assert (
        result[
            "temperature_label"
        ]
        == "moderate"
    )

    assert (
        result[
            "moisture_label"
        ]
        == "slightly_moist"
    )


# =========================================================
# Climate needs
# =========================================================


def test_determine_climate_needs_cold_moist():
    profile = (
        calculate_climate_profile(
            "子"
        )
    )

    assert (
        determine_climate_needs(
            profile
        )
        == [
            "warming",
            "drying",
        ]
    )


def test_determine_climate_needs_hot():
    profile = (
        calculate_climate_profile(
            "午"
        )
    )

    assert (
        determine_climate_needs(
            profile
        )
        == [
            "cooling",
        ]
    )


def test_determine_climate_needs_dry():
    profile = (
        calculate_climate_profile(
            "酉"
        )
    )

    assert (
        determine_climate_needs(
            profile
        )
        == [
            "moistening",
        ]
    )


def test_determine_climate_needs_moderate():
    profile = (
        calculate_climate_profile(
            "卯"
        )
    )

    assert (
        determine_climate_needs(
            profile
        )
        == []
    )


def test_determine_climate_needs_type_error():
    with pytest.raises(
        TypeError
    ):
        determine_climate_needs(
            []
        )


def test_determine_climate_needs_missing_heat():
    with pytest.raises(
        ValueError
    ):
        determine_climate_needs(
            {
                "moisture_score": 0.0,
            }
        )


def test_determine_climate_needs_missing_moisture():
    with pytest.raises(
        ValueError
    ):
        determine_climate_needs(
            {
                "heat_score": 0.0,
            }
        )


def test_determine_climate_needs_bool_invalid():
    with pytest.raises(
        ValueError
    ):
        determine_climate_needs(
            {
                "heat_score": True,
                "moisture_score": 0.0,
            }
        )


# =========================================================
# Climate element scores
# =========================================================


def test_build_climate_element_scores_warming():
    result = (
        build_climate_element_scores(
            [
                "warming",
            ]
        )
    )

    assert result == {
        "木": 0.0,
        "火": 2.0,
        "土": 0.0,
        "金": 0.0,
        "水": 0.0,
    }


def test_build_climate_element_scores_cooling():
    result = (
        build_climate_element_scores(
            [
                "cooling",
            ]
        )
    )

    assert result[
        "水"
    ] == 2.0

    assert result[
        "火"
    ] == 0.0


def test_build_climate_element_scores_moistening():
    result = (
        build_climate_element_scores(
            [
                "moistening",
            ]
        )
    )

    assert result[
        "水"
    ] == 1.5

    assert result[
        "木"
    ] == 0.5


def test_build_climate_element_scores_drying():
    result = (
        build_climate_element_scores(
            [
                "drying",
            ]
        )
    )

    assert result[
        "火"
    ] == 1.0

    assert result[
        "土"
    ] == 0.5


def test_build_climate_element_scores_combined():
    result = (
        build_climate_element_scores(
            [
                "warming",
                "drying",
            ]
        )
    )

    assert result[
        "火"
    ] == 3.0

    assert result[
        "土"
    ] == 0.5


def test_build_climate_element_scores_empty():
    result = (
        build_climate_element_scores(
            []
        )
    )

    assert result == {
        "木": 0.0,
        "火": 0.0,
        "土": 0.0,
        "金": 0.0,
        "水": 0.0,
    }


def test_build_climate_element_scores_type_error():
    with pytest.raises(
        TypeError
    ):
        build_climate_element_scores(
            "warming"
        )


def test_build_climate_element_scores_invalid_need():
    with pytest.raises(
        ValueError
    ):
        build_climate_element_scores(
            [
                "heating",
            ]
        )


# =========================================================
# Climate element ranking
# =========================================================


def test_rank_climate_elements():
    scores = {
        "木": 0.5,
        "火": 0.0,
        "土": 0.0,
        "金": 0.0,
        "水": 1.5,
    }

    assert (
        rank_climate_elements(
            scores
        )
        == [
            "水",
            "木",
        ]
    )


def test_rank_climate_elements_ignores_zero():
    scores = {
        "木": 0.0,
        "火": 2.0,
        "土": 0.0,
        "金": 0.0,
        "水": 0.0,
    }

    assert (
        rank_climate_elements(
            scores
        )
        == [
            "火",
        ]
    )


def test_rank_climate_elements_empty():
    scores = {
        element: 0.0
        for element in ELEMENTS
    }

    assert (
        rank_climate_elements(
            scores
        )
        == []
    )


def test_rank_climate_elements_stable_tie():
    scores = {
        "木": 1.0,
        "火": 1.0,
        "土": 0.0,
        "金": 0.0,
        "水": 0.0,
    }

    assert (
        rank_climate_elements(
            scores
        )
        == [
            "木",
            "火",
        ]
    )


def test_rank_climate_elements_type_error():
    with pytest.raises(
        TypeError
    ):
        rank_climate_elements(
            []
        )


def test_rank_climate_elements_missing_score():
    scores = {
        "木": 1.0,
        "火": 1.0,
        "土": 0.0,
        "金": 0.0,
    }

    with pytest.raises(
        ValueError
    ):
        rank_climate_elements(
            scores
        )


def test_rank_climate_elements_bool_invalid():
    scores = {
        "木": True,
        "火": 0.0,
        "土": 0.0,
        "金": 0.0,
        "水": 0.0,
    }

    with pytest.raises(
        ValueError
    ):
        rank_climate_elements(
            scores
        )


# =========================================================
# Candidate details
# =========================================================


def test_build_climate_candidate_details_moistening():
    scores = (
        build_climate_element_scores(
            [
                "moistening",
            ]
        )
    )

    ranked = (
        rank_climate_elements(
            scores
        )
    )

    result = (
        build_climate_candidate_details(
            ranked,
            scores,
            [
                "moistening",
            ],
        )
    )

    assert len(
        result
    ) == 2

    assert result[0][
        "element"
    ] == "水"

    assert result[0][
        "priority"
    ] == 1

    assert result[0][
        "climate_score"
    ] == 1.5

    assert result[0][
        "matched_needs"
    ] == [
        "moistening",
    ]

    assert result[1][
        "element"
    ] == "木"

    assert result[1][
        "priority"
    ] == 2


def test_build_climate_candidate_details_warming_drying():
    scores = (
        build_climate_element_scores(
            [
                "warming",
                "drying",
            ]
        )
    )

    ranked = (
        rank_climate_elements(
            scores
        )
    )

    result = (
        build_climate_candidate_details(
            ranked,
            scores,
            [
                "warming",
                "drying",
            ],
        )
    )

    assert result[0][
        "element"
    ] == "火"

    assert result[0][
        "matched_needs"
    ] == [
        "warming",
        "drying",
    ]

    assert result[1][
        "element"
    ] == "土"

    assert result[1][
        "matched_needs"
    ] == [
        "drying",
    ]


def test_build_climate_candidate_details_type_error():
    with pytest.raises(
        TypeError
    ):
        build_climate_candidate_details(
            "火",
            {
                element: 0.0
                for element in ELEMENTS
            },
            [],
        )


# =========================================================
# Confidence
# =========================================================


def test_determine_climate_confidence_high():
    profile = (
        calculate_climate_profile(
            "子"
        )
    )

    needs = (
        determine_climate_needs(
            profile
        )
    )

    assert (
        determine_climate_confidence(
            profile,
            needs,
        )
        == "high"
    )


def test_determine_climate_confidence_medium():
    profile = {
        "heat_score": 0.6,
        "moisture_score": 0.0,
    }

    assert (
        determine_climate_confidence(
            profile,
            [
                "cooling",
            ],
        )
        == "medium"
    )


def test_determine_climate_confidence_low_no_need():
    profile = (
        calculate_climate_profile(
            "卯"
        )
    )

    assert (
        determine_climate_confidence(
            profile,
            [],
        )
        == "low"
    )


# =========================================================
# Reasoning
# =========================================================


def test_build_climate_reasoning_has_content():
    profile = (
        calculate_climate_profile(
            "子"
        )
    )

    needs = (
        determine_climate_needs(
            profile
        )
    )

    scores = (
        build_climate_element_scores(
            needs
        )
    )

    ranked = (
        rank_climate_elements(
            scores
        )
    )

    result = (
        build_climate_reasoning(
            profile,
            needs,
            ranked,
        )
    )

    assert isinstance(
        result,
        list,
    )

    assert len(
        result
    ) >= 3

    assert any(
        "子"
        in item
        for item in result
    )

    assert any(
        "火"
        in item
        for item in result
    )


def test_build_climate_reasoning_no_need():
    profile = (
        calculate_climate_profile(
            "卯"
        )
    )

    result = (
        build_climate_reasoning(
            profile,
            [],
            [],
        )
    )

    assert isinstance(
        result,
        list,
    )

    assert any(
        "強い調候要求"
        in item
        for item in result
    )


# =========================================================
# Main evaluator structure
# =========================================================


@pytest.mark.parametrize(
    (
        "stem",
        "branch",
    ),
    [
        ("甲", "寅"),
        ("乙", "卯"),
        ("丙", "巳"),
        ("丁", "午"),
        ("戊", "辰"),
        ("己", "未"),
        ("庚", "申"),
        ("辛", "酉"),
        ("壬", "亥"),
        ("癸", "子"),
    ],
)
def test_evaluate_climate_useful_gods_structure(
    stem,
    branch,
):
    result = (
        evaluate_climate_useful_gods(
            stem,
            branch,
        )
    )

    required_keys = {
        "has_climate_candidate",
        "primary_climate_element",
        "secondary_climate_elements",
        "climate_elements",
        "climate_candidates",
        "day_master_stem",
        "day_master_element",
        "month_branch",
        "season",
        "season_japanese",
        "temperature_label",
        "moisture_label",
        "heat_score",
        "moisture_score",
        "climate_needs",
        "climate_element_scores",
        "confidence",
        "reasoning",
        "evidence",
        "method",
        "status",
        "notes",
    }

    assert required_keys.issubset(
        result.keys()
    )

    assert (
        result[
            "day_master_stem"
        ]
        == stem
    )

    assert (
        result[
            "month_branch"
        ]
        == branch
    )


def test_evaluate_method_and_status():
    result = (
        evaluate_climate_useful_gods(
            "乙",
            "未",
        )
    )

    assert (
        result[
            "method"
        ]
        == "climate_useful_gods_v1"
    )

    assert (
        result[
            "status"
        ]
        == "provisional_climate_useful_gods"
    )


# =========================================================
# Representative seasonal cases
# =========================================================


def test_winter_child_month_primary_fire():
    result = (
        evaluate_climate_useful_gods(
            "乙",
            "子",
        )
    )

    assert (
        result[
            "season"
        ]
        == "winter"
    )

    assert (
        "warming"
        in result[
            "climate_needs"
        ]
    )

    assert (
        result[
            "primary_climate_element"
        ]
        == "火"
    )

    assert (
        result[
            "climate_elements"
        ][0]
        == "火"
    )

    assert (
        result[
            "confidence"
        ]
        == "high"
    )


def test_summer_horse_month_primary_water():
    result = (
        evaluate_climate_useful_gods(
            "乙",
            "午",
        )
    )

    assert (
        result[
            "season"
        ]
        == "summer"
    )

    assert (
        result[
            "climate_needs"
        ]
        == [
            "cooling",
        ]
    )

    assert (
        result[
            "primary_climate_element"
        ]
        == "水"
    )

    assert (
        result[
            "climate_elements"
        ]
        == [
            "水",
        ]
    )

    assert (
        result[
            "confidence"
        ]
        == "high"
    )


def test_autumn_rooster_month_primary_water():
    result = (
        evaluate_climate_useful_gods(
            "乙",
            "酉",
        )
    )

    assert (
        result[
            "season"
        ]
        == "autumn"
    )

    assert (
        result[
            "climate_needs"
        ]
        == [
            "moistening",
        ]
    )

    assert (
        result[
            "primary_climate_element"
        ]
        == "水"
    )

    assert (
        result[
            "secondary_climate_elements"
        ]
        == [
            "木",
        ]
    )


def test_spring_rabbit_month_has_no_candidate():
    result = (
        evaluate_climate_useful_gods(
            "乙",
            "卯",
        )
    )

    assert (
        result[
            "season"
        ]
        == "spring"
    )

    assert (
        result[
            "climate_needs"
        ]
        == []
    )

    assert (
        result[
            "has_climate_candidate"
        ]
        is False
    )

    assert (
        result[
            "primary_climate_element"
        ]
        is None
    )

    assert (
        result[
            "secondary_climate_elements"
        ]
        == []
    )

    assert (
        result[
            "climate_elements"
        ]
        == []
    )

    assert (
        result[
            "climate_candidates"
        ]
        == []
    )

    assert (
        result[
            "confidence"
        ]
        == "low"
    )


# =========================================================
# Earth-transition months
# =========================================================


@pytest.mark.parametrize(
    (
        "branch",
        "expected_season",
    ),
    [
        ("辰", "spring"),
        ("未", "summer"),
        ("戌", "autumn"),
        ("丑", "winter"),
    ],
)
def test_earth_transition_month_season(
    branch,
    expected_season,
):
    result = (
        evaluate_climate_useful_gods(
            "乙",
            branch,
        )
    )

    assert (
        result[
            "season"
        ]
        == expected_season
    )

    assert (
        result[
            "month_branch"
        ]
        == branch
    )


def test_wei_month_profile():
    result = (
        evaluate_climate_useful_gods(
            "乙",
            "未",
        )
    )

    assert (
        result[
            "heat_score"
        ]
        == 1.15
    )

    assert (
        result[
            "moisture_score"
        ]
        == -0.4
    )

    assert (
        result[
            "temperature_label"
        ]
        == "hot"
    )

    assert (
        result[
            "moisture_label"
        ]
        == "slightly_dry"
    )

    assert (
        result[
            "climate_needs"
        ]
        == [
            "cooling",
        ]
    )

    assert (
        result[
            "primary_climate_element"
        ]
        == "水"
    )


def test_chou_month_profile():
    result = (
        evaluate_climate_useful_gods(
            "乙",
            "丑",
        )
    )

    assert (
        result[
            "heat_score"
        ]
        == -1.1
    )

    assert (
        result[
            "moisture_score"
        ]
        == 0.95
    )

    assert (
        result[
            "climate_needs"
        ]
        == [
            "warming",
            "drying",
        ]
    )

    assert (
        result[
            "primary_climate_element"
        ]
        == "火"
    )


# =========================================================
# Candidate consistency
# =========================================================


@pytest.mark.parametrize(
    "branch",
    BRANCHES,
)
def test_primary_candidate_matches_first_element(
    branch,
):
    result = (
        evaluate_climate_useful_gods(
            "乙",
            branch,
        )
    )

    elements = result[
        "climate_elements"
    ]

    if elements:
        assert (
            result[
                "primary_climate_element"
            ]
            == elements[0]
        )

        assert (
            result[
                "secondary_climate_elements"
            ]
            == elements[1:]
        )

        assert (
            result[
                "has_climate_candidate"
            ]
            is True
        )
    else:
        assert (
            result[
                "primary_climate_element"
            ]
            is None
        )

        assert (
            result[
                "secondary_climate_elements"
            ]
            == []
        )

        assert (
            result[
                "has_climate_candidate"
            ]
            is False
        )


@pytest.mark.parametrize(
    "branch",
    BRANCHES,
)
def test_candidate_priorities_are_sequential(
    branch,
):
    result = (
        evaluate_climate_useful_gods(
            "乙",
            branch,
        )
    )

    candidates = result[
        "climate_candidates"
    ]

    assert (
        len(
            candidates
        )
        == len(
            result[
                "climate_elements"
            ]
        )
    )

    for index, candidate in enumerate(
        candidates,
        start=1,
    ):
        assert (
            candidate[
                "priority"
            ]
            == index
        )

        assert (
            candidate[
                "element"
            ]
            == result[
                "climate_elements"
            ][
                index - 1
            ]
        )


@pytest.mark.parametrize(
    "branch",
    BRANCHES,
)
def test_climate_scores_have_all_elements(
    branch,
):
    result = (
        evaluate_climate_useful_gods(
            "乙",
            branch,
        )
    )

    assert set(
        result[
            "climate_element_scores"
        ].keys()
    ) == set(
        ELEMENTS
    )


# =========================================================
# Evidence
# =========================================================


def test_evidence_structure():
    result = (
        evaluate_climate_useful_gods(
            "乙",
            "未",
        )
    )

    evidence = result[
        "evidence"
    ]

    assert {
        "climate_profile",
        "season_source",
        "day_master_usage",
    }.issubset(
        evidence.keys()
    )

    assert (
        evidence[
            "season_source"
        ]
        == "month_branch"
    )

    assert (
        evidence[
            "day_master_usage"
        ]
        == "metadata_only_in_v1"
    )


def test_evidence_profile_matches_result():
    result = (
        evaluate_climate_useful_gods(
            "乙",
            "未",
        )
    )

    profile = result[
        "evidence"
    ][
        "climate_profile"
    ]

    assert (
        profile[
            "month_branch"
        ]
        == result[
            "month_branch"
        ]
    )

    assert (
        profile[
            "season"
        ]
        == result[
            "season"
        ]
    )

    assert (
        profile[
            "heat_score"
        ]
        == result[
            "heat_score"
        ]
    )

    assert (
        profile[
            "moisture_score"
        ]
        == result[
            "moisture_score"
        ]
    )


# =========================================================
# Reasoning / notes
# =========================================================


@pytest.mark.parametrize(
    "branch",
    BRANCHES,
)
def test_reasoning_exists(
    branch,
):
    result = (
        evaluate_climate_useful_gods(
            "乙",
            branch,
        )
    )

    assert isinstance(
        result[
            "reasoning"
        ],
        list,
    )

    assert (
        len(
            result[
                "reasoning"
            ]
        )
        >= 2
    )


@pytest.mark.parametrize(
    "branch",
    BRANCHES,
)
def test_notes_exist(
    branch,
):
    result = (
        evaluate_climate_useful_gods(
            "乙",
            branch,
        )
    )

    assert isinstance(
        result[
            "notes"
        ],
        list,
    )

    assert (
        len(
            result[
                "notes"
            ]
        )
        >= 1
    )


# =========================================================
# All stems
# =========================================================


@pytest.mark.parametrize(
    (
        "stem",
        "expected_element",
    ),
    [
        ("甲", "木"),
        ("乙", "木"),
        ("丙", "火"),
        ("丁", "火"),
        ("戊", "土"),
        ("己", "土"),
        ("庚", "金"),
        ("辛", "金"),
        ("壬", "水"),
        ("癸", "水"),
    ],
)
def test_all_day_master_stems(
    stem,
    expected_element,
):
    result = (
        evaluate_climate_useful_gods(
            stem,
            "午",
        )
    )

    assert (
        result[
            "day_master_stem"
        ]
        == stem
    )

    assert (
        result[
            "day_master_element"
        ]
        == expected_element
    )


# =========================================================
# Verified-chart style regression
#
# 1985/07/17 21:50 石川
# 年 乙丑
# 月 癸未
# 日 乙巳
# 時 丁亥
#
# 日主 = 乙
# 月支 = 未
#
# v1:
# 未 -> summer
# heat = 1.0 + 0.15 = 1.15
# moisture = -0.25 - 0.15 = -0.40
# cooling が必要
# 水が第一候補
# =========================================================


def test_verified_1985_style_climate_case():
    result = (
        evaluate_climate_useful_gods(
            "乙",
            "未",
        )
    )

    assert (
        result[
            "day_master_stem"
        ]
        == "乙"
    )

    assert (
        result[
            "day_master_element"
        ]
        == "木"
    )

    assert (
        result[
            "month_branch"
        ]
        == "未"
    )

    assert (
        result[
            "season"
        ]
        == "summer"
    )

    assert (
        result[
            "season_japanese"
        ]
        == "夏"
    )

    assert (
        result[
            "heat_score"
        ]
        == 1.15
    )

    assert (
        result[
            "moisture_score"
        ]
        == -0.4
    )

    assert (
        result[
            "climate_needs"
        ]
        == [
            "cooling",
        ]
    )

    assert (
        result[
            "primary_climate_element"
        ]
        == "水"
    )

    assert (
        result[
            "secondary_climate_elements"
        ]
        == []
    )

    assert (
        result[
            "climate_elements"
        ]
        == [
            "水",
        ]
    )

    assert (
        result[
            "confidence"
        ]
        == "high"
    )

    assert (
        result[
            "method"
        ]
        == "climate_useful_gods_v1"
    )

    assert (
        result[
            "status"
        ]
        == "provisional_climate_useful_gods"
    )


# =========================================================
# Invalid main evaluator inputs
# =========================================================


def test_evaluate_invalid_stem_type():
    with pytest.raises(
        TypeError
    ):
        evaluate_climate_useful_gods(
            123,
            "未",
        )


def test_evaluate_invalid_stem_value():
    with pytest.raises(
        ValueError
    ):
        evaluate_climate_useful_gods(
            "A",
            "未",
        )


def test_evaluate_invalid_branch_type():
    with pytest.raises(
        TypeError
    ):
        evaluate_climate_useful_gods(
            "乙",
            123,
        )


def test_evaluate_invalid_branch_value():
    with pytest.raises(
        ValueError
    ):
        evaluate_climate_useful_gods(
            "乙",
            "A",
        )
