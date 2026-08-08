import pytest

from engine.stem_transformation import (
    evaluate_month_support,
    evaluate_single_transformation,
    evaluate_stem_transformations,
    get_month_branch_element,
)


def test_get_month_branch_element():
    assert get_month_branch_element(
        "寅"
    ) == "木"

    assert get_month_branch_element(
        "卯"
    ) == "木"

    assert get_month_branch_element(
        "辰"
    ) == "土"

    assert get_month_branch_element(
        "巳"
    ) == "火"

    assert get_month_branch_element(
        "午"
    ) == "火"

    assert get_month_branch_element(
        "未"
    ) == "土"

    assert get_month_branch_element(
        "申"
    ) == "金"

    assert get_month_branch_element(
        "酉"
    ) == "金"

    assert get_month_branch_element(
        "戌"
    ) == "土"

    assert get_month_branch_element(
        "亥"
    ) == "水"

    assert get_month_branch_element(
        "子"
    ) == "水"

    assert get_month_branch_element(
        "丑"
    ) == "土"


def test_invalid_month_branch():
    with pytest.raises(
        ValueError,
        match="不正な月支です",
    ):
        get_month_branch_element(
            "A"
        )


def test_month_support_strong():
    result = evaluate_month_support(
        result_element="土",
        month_branch="未",
    )

    assert result == {
        "month_branch": "未",
        "month_element": "土",
        "result_element": "土",
        "support_level": "strong",
        "support_score": 2.0,
    }


def test_month_support_supportive():
    result = evaluate_month_support(
        result_element="土",
        month_branch="午",
    )

    assert result == {
        "month_branch": "午",
        "month_element": "火",
        "result_element": "土",
        "support_level": "supportive",
        "support_score": 1.0,
    }


def test_month_support_weak():
    result = evaluate_month_support(
        result_element="土",
        month_branch="子",
    )

    assert result == {
        "month_branch": "子",
        "month_element": "水",
        "result_element": "土",
        "support_level": "weak",
        "support_score": 0.0,
    }


def test_invalid_result_element():
    with pytest.raises(
        ValueError,
        match="不正な五行です",
    ):
        evaluate_month_support(
            result_element="風",
            month_branch="未",
        )


def test_single_transformation_strong():
    combination = {
        "position_a": "year",
        "stem_a": "甲",
        "position_b": "month",
        "stem_b": "己",
        "combination_name": "甲己",
        "result_element": "土",
    }

    result = evaluate_single_transformation(
        combination,
        month_branch="未",
    )

    assert result[
        "position_a"
    ] == "year"

    assert result[
        "stem_a"
    ] == "甲"

    assert result[
        "position_b"
    ] == "month"

    assert result[
        "stem_b"
    ] == "己"

    assert result[
        "combination_name"
    ] == "甲己"

    assert result[
        "result_element"
    ] == "土"

    assert result[
        "transformation_status"
    ] == "possible"

    assert result[
        "confidence"
    ] == "high"

    assert result[
        "month_support"
    ] == {
        "month_branch": "未",
        "month_element": "土",
        "result_element": "土",
        "support_level": "strong",
        "support_score": 2.0,
    }


def test_single_transformation_supportive():
    combination = {
        "position_a": "year",
        "stem_a": "甲",
        "position_b": "month",
        "stem_b": "己",
        "combination_name": "甲己",
        "result_element": "土",
    }

    result = evaluate_single_transformation(
        combination,
        month_branch="午",
    )

    assert result[
        "transformation_status"
    ] == "possible"

    assert result[
        "confidence"
    ] == "medium"

    assert result[
        "month_support"
    ][
        "support_level"
    ] == "supportive"


def test_single_transformation_unsupported():
    combination = {
        "position_a": "year",
        "stem_a": "甲",
        "position_b": "month",
        "stem_b": "己",
        "combination_name": "甲己",
        "result_element": "土",
    }

    result = evaluate_single_transformation(
        combination,
        month_branch="子",
    )

    assert result[
        "transformation_status"
    ] == "unsupported"

    assert result[
        "confidence"
    ] == "low"

    assert result[
        "month_support"
    ][
        "support_level"
    ] == "weak"


def test_single_transformation_missing_result_element():
    combination = {
        "position_a": "year",
        "stem_a": "甲",
        "position_b": "month",
        "stem_b": "己",
    }

    with pytest.raises(
        ValueError,
        match="result_elementが必要です",
    ):
        evaluate_single_transformation(
            combination,
            month_branch="未",
        )


def test_no_stem_combinations():
    stem_combinations = {
        "has_combination": False,
        "combination_count": 0,
        "combinations": [],
    }

    chart_data = {
        "month": {
            "branch": "未",
        },
    }

    result = evaluate_stem_transformations(
        stem_combinations,
        chart_data,
    )

    assert (
        result["has_stem_combination"]
        is False
    )

    assert (
        result["transformation_count"]
        == 0
    )

    assert (
        result["possible_count"]
        == 0
    )

    assert (
        result["unsupported_count"]
        == 0
    )

    assert (
        result["overall_status"]
        == "not_applicable"
    )

    assert (
        result["transformations"]
        == []
    )

    assert (
        result["method"]
        == "stem_transformation_v1"
    )

    assert (
        result["status"]
        == "provisional_stem_transformation"
    )


def test_all_transformations_possible():
    stem_combinations = {
        "has_combination": True,
        "combination_count": 2,
        "combinations": [
            {
                "position_a": "year",
                "stem_a": "甲",
                "position_b": "month",
                "stem_b": "己",
                "combination_name": "甲己",
                "result_element": "土",
            },
            {
                "position_a": "day",
                "stem_a": "戊",
                "position_b": "hour",
                "stem_b": "癸",
                "combination_name": "戊癸",
                "result_element": "火",
            },
        ],
    }

    chart_data = {
        "month": {
            "branch": "午",
        },
    }

    result = evaluate_stem_transformations(
        stem_combinations,
        chart_data,
    )

    assert (
        result["has_stem_combination"]
        is True
    )

    assert (
        result["transformation_count"]
        == 2
    )

    assert (
        result["possible_count"]
        == 2
    )

    assert (
        result["unsupported_count"]
        == 0
    )

    assert (
        result["overall_status"]
        == "possible"
    )


def test_all_transformations_unsupported():
    stem_combinations = {
        "has_combination": True,
        "combination_count": 2,
        "combinations": [
            {
                "position_a": "year",
                "stem_a": "甲",
                "position_b": "month",
                "stem_b": "己",
                "combination_name": "甲己",
                "result_element": "土",
            },
            {
                "position_a": "day",
                "stem_a": "乙",
                "position_b": "hour",
                "stem_b": "庚",
                "combination_name": "乙庚",
                "result_element": "金",
            },
        ],
    }

    chart_data = {
        "month": {
            "branch": "子",
        },
    }

    result = evaluate_stem_transformations(
        stem_combinations,
        chart_data,
    )

    assert (
        result["transformation_count"]
        == 2
    )

    assert (
        result["possible_count"]
        == 0
    )

    assert (
        result["unsupported_count"]
        == 2
    )

    assert (
        result["overall_status"]
        == "unsupported"
    )


def test_mixed_transformations():
    stem_combinations = {
        "has_combination": True,
        "combination_count": 2,
        "combinations": [
            {
                "position_a": "year",
                "stem_a": "甲",
                "position_b": "month",
                "stem_b": "己",
                "combination_name": "甲己",
                "result_element": "土",
            },
            {
                "position_a": "day",
                "stem_a": "乙",
                "position_b": "hour",
                "stem_b": "庚",
                "combination_name": "乙庚",
                "result_element": "金",
            },
        ],
    }

    chart_data = {
        "month": {
            "branch": "午",
        },
    }

    result = evaluate_stem_transformations(
        stem_combinations,
        chart_data,
    )

    assert (
        result["transformation_count"]
        == 2
    )

    assert (
        result["possible_count"]
        == 1
    )

    assert (
        result["unsupported_count"]
        == 1
    )

    assert (
        result["overall_status"]
        == "mixed"
    )


def test_invalid_stem_combinations_type():
    with pytest.raises(
        TypeError,
        match="stem_combinationsはdict型",
    ):
        evaluate_stem_transformations(
            stem_combinations=[],
            chart_data={
                "month": {
                    "branch": "未",
                },
            },
        )


def test_invalid_chart_data_type():
    with pytest.raises(
        TypeError,
        match="chart_dataはdict型",
    ):
        evaluate_stem_transformations(
            stem_combinations={
                "combinations": [],
            },
            chart_data=[],
        )


def test_missing_month_pillar():
    with pytest.raises(
        ValueError,
        match="month柱が必要です",
    ):
        evaluate_stem_transformations(
            stem_combinations={
                "combinations": [],
            },
            chart_data={},
        )


def test_missing_month_branch():
    with pytest.raises(
        ValueError,
        match="month柱にbranchが必要です",
    ):
        evaluate_stem_transformations(
            stem_combinations={
                "combinations": [],
            },
            chart_data={
                "month": {},
            },
        )


def test_invalid_combinations_type():
    with pytest.raises(
        TypeError,
        match="combinationsはlist型",
    ):
        evaluate_stem_transformations(
            stem_combinations={
                "combinations": {},
            },
            chart_data={
                "month": {
                    "branch": "未",
                },
            },
        )


def test_result_contains_notes():
    stem_combinations = {
        "combinations": [],
    }

    chart_data = {
        "month": {
            "branch": "未",
        },
    }

    result = evaluate_stem_transformations(
        stem_combinations,
        chart_data,
    )

    assert isinstance(
        result["notes"],
        list,
    )

    assert (
        len(
            result["notes"]
        )
        >= 1
    )
