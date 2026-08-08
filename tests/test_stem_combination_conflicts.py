import pytest

from engine.stem_combination_conflicts import (
    build_position_usage,
    evaluate_stem_combination_conflicts,
    find_duplicate_combination_names,
    find_position_conflicts,
    get_combination_positions,
    validate_stem_combinations,
)


def make_combination(
    position_a: str,
    stem_a: str,
    position_b: str,
    stem_b: str,
    combination_name: str,
    result_element: str,
) -> dict:
    """
    テスト用の干合候補を作成します。
    """
    return {
        "position_a": position_a,
        "stem_a": stem_a,
        "position_b": position_b,
        "stem_b": stem_b,
        "relation": "干合",
        "combination_name": combination_name,
        "result_element": result_element,
        "transformation_status": "not_evaluated",
    }


def make_chart_data() -> dict:
    """
    テスト用の命式データを作成します。
    """
    return {
        "year": {
            "stem": "甲",
            "branch": "子",
        },
        "month": {
            "stem": "己",
            "branch": "未",
        },
        "day": {
            "stem": "己",
            "branch": "巳",
        },
        "hour": {
            "stem": "丁",
            "branch": "亥",
        },
    }


def test_validate_stem_combinations():
    stem_combinations = {
        "combinations": [
            make_combination(
                "year",
                "甲",
                "month",
                "己",
                "甲己",
                "土",
            ),
        ],
    }

    result = validate_stem_combinations(
        stem_combinations
    )

    assert len(result) == 1

    assert (
        result[0]["combination_name"]
        == "甲己"
    )


def test_validate_empty_stem_combinations():
    result = validate_stem_combinations(
        {}
    )

    assert result == []


def test_invalid_stem_combinations_type():
    with pytest.raises(
        TypeError,
        match="stem_combinationsはdict型",
    ):
        validate_stem_combinations(
            []
        )


def test_invalid_combinations_type():
    with pytest.raises(
        TypeError,
        match="combinationsはlist型",
    ):
        validate_stem_combinations(
            {
                "combinations": {},
            }
        )


def test_get_combination_positions():
    combination = make_combination(
        "year",
        "甲",
        "month",
        "己",
        "甲己",
        "土",
    )

    result = get_combination_positions(
        combination
    )

    assert result == (
        "year",
        "month",
    )


def test_invalid_combination_type():
    with pytest.raises(
        TypeError,
        match="combinationはdict型",
    ):
        get_combination_positions(
            []
        )


def test_build_position_usage():
    combinations = [
        make_combination(
            "year",
            "甲",
            "month",
            "己",
            "甲己",
            "土",
        ),
        make_combination(
            "year",
            "甲",
            "day",
            "己",
            "甲己",
            "土",
        ),
    ]

    usage = build_position_usage(
        combinations
    )

    assert len(
        usage["year"]
    ) == 2

    assert len(
        usage["month"]
    ) == 1

    assert len(
        usage["day"]
    ) == 1

    assert (
        usage["hour"]
        == []
    )


def test_build_position_usage_invalid_item():
    with pytest.raises(
        TypeError,
        match="combinationはdict型",
    ):
        build_position_usage(
            [
                [],
            ]
        )


def test_build_position_usage_invalid_position():
    combinations = [
        make_combination(
            "invalid",
            "甲",
            "month",
            "己",
            "甲己",
            "土",
        ),
    ]

    with pytest.raises(
        ValueError,
        match="不正なpositionです",
    ):
        build_position_usage(
            combinations
        )


def test_no_position_conflict():
    combinations = [
        make_combination(
            "year",
            "甲",
            "month",
            "己",
            "甲己",
            "土",
        ),
        make_combination(
            "day",
            "丁",
            "hour",
            "壬",
            "丁壬",
            "木",
        ),
    ]

    result = find_position_conflicts(
        combinations,
        {
            "year": {
                "stem": "甲",
            },
            "month": {
                "stem": "己",
            },
            "day": {
                "stem": "丁",
            },
            "hour": {
                "stem": "壬",
            },
        },
    )

    assert result == []


def test_find_single_position_conflict():
    combinations = [
        make_combination(
            "year",
            "甲",
            "month",
            "己",
            "甲己",
            "土",
        ),
        make_combination(
            "year",
            "甲",
            "day",
            "己",
            "甲己",
            "土",
        ),
    ]

    chart_data = make_chart_data()

    result = find_position_conflicts(
        combinations,
        chart_data,
    )

    assert result == [
        {
            "position": "year",
            "stem": "甲",
            "combination_count": 2,
            "combination_names": [
                "甲己",
                "甲己",
            ],
            "partner_positions": [
                "month",
                "day",
            ],
            "conflict_type": (
                "competing_combination"
            ),
        }
    ]


def test_find_position_conflict_without_chart_data():
    combinations = [
        make_combination(
            "year",
            "甲",
            "month",
            "己",
            "甲己",
            "土",
        ),
        make_combination(
            "year",
            "甲",
            "day",
            "己",
            "甲己",
            "土",
        ),
    ]

    result = find_position_conflicts(
        combinations,
        None,
    )

    assert len(result) == 1

    assert (
        result[0]["position"]
        == "year"
    )

    assert (
        result[0]["stem"]
        is None
    )


def test_find_multiple_position_conflicts():
    combinations = [
        make_combination(
            "year",
            "甲",
            "month",
            "己",
            "甲己",
            "土",
        ),
        make_combination(
            "year",
            "甲",
            "day",
            "己",
            "甲己",
            "土",
        ),
        make_combination(
            "month",
            "己",
            "hour",
            "甲",
            "甲己",
            "土",
        ),
    ]

    chart_data = {
        "year": {
            "stem": "甲",
        },
        "month": {
            "stem": "己",
        },
        "day": {
            "stem": "己",
        },
        "hour": {
            "stem": "甲",
        },
    }

    result = find_position_conflicts(
        combinations,
        chart_data,
    )

    assert len(result) == 2

    assert (
        result[0]["position"]
        == "year"
    )

    assert (
        result[1]["position"]
        == "month"
    )

    assert (
        result[0]["combination_count"]
        == 2
    )

    assert (
        result[1]["combination_count"]
        == 2
    )


def test_no_duplicate_combination_names():
    combinations = [
        make_combination(
            "year",
            "甲",
            "month",
            "己",
            "甲己",
            "土",
        ),
        make_combination(
            "day",
            "丁",
            "hour",
            "壬",
            "丁壬",
            "木",
        ),
    ]

    result = (
        find_duplicate_combination_names(
            combinations
        )
    )

    assert result == []


def test_find_duplicate_combination_names():
    combinations = [
        make_combination(
            "year",
            "甲",
            "month",
            "己",
            "甲己",
            "土",
        ),
        make_combination(
            "year",
            "甲",
            "day",
            "己",
            "甲己",
            "土",
        ),
    ]

    result = (
        find_duplicate_combination_names(
            combinations
        )
    )

    assert result == [
        {
            "combination_name": "甲己",
            "combination_count": 2,
            "pairs": [
                {
                    "position_a": "year",
                    "stem_a": "甲",
                    "position_b": "month",
                    "stem_b": "己",
                },
                {
                    "position_a": "year",
                    "stem_a": "甲",
                    "position_b": "day",
                    "stem_b": "己",
                },
            ],
            "conflict_type": (
                "duplicated_combination"
            ),
        }
    ]


def test_duplicate_name_ignores_missing_name():
    combinations = [
        {
            "position_a": "year",
            "stem_a": "甲",
            "position_b": "month",
            "stem_b": "己",
        },
        {
            "position_a": "day",
            "stem_a": "乙",
            "position_b": "hour",
            "stem_b": "庚",
        },
    ]

    result = (
        find_duplicate_combination_names(
            combinations
        )
    )

    assert result == []


def test_duplicate_names_invalid_item():
    with pytest.raises(
        TypeError,
        match="combinationはdict型",
    ):
        find_duplicate_combination_names(
            [
                [],
            ]
        )


def test_evaluate_no_stem_combination():
    result = (
        evaluate_stem_combination_conflicts(
            {
                "combinations": [],
            },
            make_chart_data(),
        )
    )

    assert (
        result["has_stem_combination"]
        is False
    )

    assert (
        result["combination_count"]
        == 0
    )

    assert (
        result["has_conflict"]
        is False
    )

    assert (
        result["conflict_count"]
        == 0
    )

    assert (
        result[
            "position_conflict_count"
        ]
        == 0
    )

    assert (
        result[
            "duplicate_combination_count"
        ]
        == 0
    )

    assert (
        result["position_conflicts"]
        == []
    )

    assert (
        result["duplicate_combinations"]
        == []
    )

    assert (
        result["overall_status"]
        == "not_applicable"
    )

    assert (
        result["method"]
        == "stem_combination_conflict_v1"
    )

    assert (
        result["status"]
        == "detected_stem_combination_conflicts"
    )


def test_evaluate_clear_combination():
    combinations = [
        make_combination(
            "year",
            "甲",
            "month",
            "己",
            "甲己",
            "土",
        ),
    ]

    result = (
        evaluate_stem_combination_conflicts(
            {
                "combinations": combinations,
            },
            make_chart_data(),
        )
    )

    assert (
        result["has_stem_combination"]
        is True
    )

    assert (
        result["combination_count"]
        == 1
    )

    assert (
        result["has_conflict"]
        is False
    )

    assert (
        result["conflict_count"]
        == 0
    )

    assert (
        result["overall_status"]
        == "clear"
    )


def test_evaluate_competing_combination():
    combinations = [
        make_combination(
            "year",
            "甲",
            "month",
            "己",
            "甲己",
            "土",
        ),
        make_combination(
            "year",
            "甲",
            "day",
            "己",
            "甲己",
            "土",
        ),
    ]

    result = (
        evaluate_stem_combination_conflicts(
            {
                "combinations": combinations,
            },
            make_chart_data(),
        )
    )

    assert (
        result["has_stem_combination"]
        is True
    )

    assert (
        result["combination_count"]
        == 2
    )

    assert (
        result["has_conflict"]
        is True
    )

    assert (
        result["conflict_count"]
        == 2
    )

    assert (
        result[
            "position_conflict_count"
        ]
        == 1
    )

    assert (
        result[
            "duplicate_combination_count"
        ]
        == 1
    )

    assert (
        result["overall_status"]
        == "conflicted"
    )

    assert (
        len(
            result["position_conflicts"]
        )
        == 1
    )

    assert (
        len(
            result["duplicate_combinations"]
        )
        == 1
    )


def test_evaluate_separate_combinations():
    combinations = [
        make_combination(
            "year",
            "甲",
            "month",
            "己",
            "甲己",
            "土",
        ),
        make_combination(
            "day",
            "丁",
            "hour",
            "壬",
            "丁壬",
            "木",
        ),
    ]

    chart_data = {
        "year": {
            "stem": "甲",
        },
        "month": {
            "stem": "己",
        },
        "day": {
            "stem": "丁",
        },
        "hour": {
            "stem": "壬",
        },
    }

    result = (
        evaluate_stem_combination_conflicts(
            {
                "combinations": combinations,
            },
            chart_data,
        )
    )

    assert (
        result["combination_count"]
        == 2
    )

    assert (
        result["has_conflict"]
        is False
    )

    assert (
        result["conflict_count"]
        == 0
    )

    assert (
        result["overall_status"]
        == "clear"
    )


def test_evaluate_without_hour():
    combinations = [
        make_combination(
            "year",
            "甲",
            "month",
            "己",
            "甲己",
            "土",
        ),
    ]

    chart_data = {
        "year": {
            "stem": "甲",
        },
        "month": {
            "stem": "己",
        },
        "day": {
            "stem": "乙",
        },
        "hour": None,
    }

    result = (
        evaluate_stem_combination_conflicts(
            {
                "combinations": combinations,
            },
            chart_data,
        )
    )

    assert (
        result["has_stem_combination"]
        is True
    )

    assert (
        result["combination_count"]
        == 1
    )

    assert (
        result["has_conflict"]
        is False
    )

    assert (
        result["overall_status"]
        == "clear"
    )


def test_invalid_chart_data_type():
    with pytest.raises(
        TypeError,
        match=(
            "chart_dataはdict型またはNone"
        ),
    ):
        evaluate_stem_combination_conflicts(
            {
                "combinations": [],
            },
            [],
        )


def test_evaluate_invalid_combinations_type():
    with pytest.raises(
        TypeError,
        match="combinationsはlist型",
    ):
        evaluate_stem_combination_conflicts(
            {
                "combinations": {},
            },
            None,
        )


def test_result_contains_notes():
    result = (
        evaluate_stem_combination_conflicts(
            {
                "combinations": [],
            },
            make_chart_data(),
        )
    )

    assert isinstance(
        result["notes"],
        list,
    )

    assert len(
        result["notes"]
    ) >= 1
