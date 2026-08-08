import pytest

from engine.transformation_root import (
    evaluate_transformation_root,
    evaluate_transformation_roots,
    find_element_roots_in_pillar,
    get_available_positions,
    get_stem_element,
)


def make_pillar(
    stem: str,
    branch: str,
    hidden_stems: list[str],
) -> dict:
    """
    テスト用の柱データを作成します。
    """
    return {
        "stem": stem,
        "branch": branch,
        "hidden_stems": hidden_stems,
    }


def make_chart_data() -> dict:
    """
    通根テスト用の標準命式を作成します。

    年支：子 → 癸（水）
    月支：未 → 己・丁・乙（土・火・木）
    日支：巳 → 丙・庚・戊（火・金・土）
    時支：亥 → 壬・甲（水・木）
    """
    return {
        "year": make_pillar(
            "甲",
            "子",
            ["癸"],
        ),
        "month": make_pillar(
            "己",
            "未",
            ["己", "丁", "乙"],
        ),
        "day": make_pillar(
            "乙",
            "巳",
            ["丙", "庚", "戊"],
        ),
        "hour": make_pillar(
            "壬",
            "亥",
            ["壬", "甲"],
        ),
    }


def test_get_stem_element():
    assert get_stem_element("甲") == "木"
    assert get_stem_element("乙") == "木"

    assert get_stem_element("丙") == "火"
    assert get_stem_element("丁") == "火"

    assert get_stem_element("戊") == "土"
    assert get_stem_element("己") == "土"

    assert get_stem_element("庚") == "金"
    assert get_stem_element("辛") == "金"

    assert get_stem_element("壬") == "水"
    assert get_stem_element("癸") == "水"


def test_invalid_stem():
    with pytest.raises(
        ValueError,
        match="不正な天干です",
    ):
        get_stem_element("A")


def test_get_available_positions():
    chart_data = make_chart_data()

    result = get_available_positions(
        chart_data
    )

    assert result == [
        "year",
        "month",
        "day",
        "hour",
    ]


def test_get_available_positions_without_hour():
    chart_data = make_chart_data()

    chart_data["hour"] = None

    result = get_available_positions(
        chart_data
    )

    assert result == [
        "year",
        "month",
        "day",
    ]


def test_find_element_root_in_main_hidden_stem():
    pillar_data = make_pillar(
        "己",
        "未",
        ["己", "丁", "乙"],
    )

    result = find_element_roots_in_pillar(
        position="month",
        pillar_data=pillar_data,
        target_element="土",
    )

    assert result == [
        {
            "position": "month",
            "branch": "未",
            "stem": "己",
            "element": "土",
            "hidden_stem_rank": 1,
            "hidden_stem_weight": 1.0,
            "position_weight": 1.5,
            "root_score": 1.5,
        }
    ]


def test_find_element_root_in_second_hidden_stem():
    pillar_data = make_pillar(
        "己",
        "未",
        ["己", "丁", "乙"],
    )

    result = find_element_roots_in_pillar(
        position="month",
        pillar_data=pillar_data,
        target_element="火",
    )

    assert result == [
        {
            "position": "month",
            "branch": "未",
            "stem": "丁",
            "element": "火",
            "hidden_stem_rank": 2,
            "hidden_stem_weight": 0.5,
            "position_weight": 1.5,
            "root_score": 0.75,
        }
    ]


def test_find_element_root_in_third_hidden_stem():
    pillar_data = make_pillar(
        "己",
        "未",
        ["己", "丁", "乙"],
    )

    result = find_element_roots_in_pillar(
        position="month",
        pillar_data=pillar_data,
        target_element="木",
    )

    assert result == [
        {
            "position": "month",
            "branch": "未",
            "stem": "乙",
            "element": "木",
            "hidden_stem_rank": 3,
            "hidden_stem_weight": 0.3,
            "position_weight": 1.5,
            "root_score": 0.45,
        }
    ]


def test_find_element_without_root():
    pillar_data = make_pillar(
        "己",
        "未",
        ["己", "丁", "乙"],
    )

    result = find_element_roots_in_pillar(
        position="month",
        pillar_data=pillar_data,
        target_element="水",
    )

    assert result == []


def test_invalid_target_element():
    pillar_data = make_pillar(
        "己",
        "未",
        ["己", "丁", "乙"],
    )

    with pytest.raises(
        ValueError,
        match="不正な五行です",
    ):
        find_element_roots_in_pillar(
            position="month",
            pillar_data=pillar_data,
            target_element="風",
        )


def test_invalid_hidden_stems_type():
    pillar_data = {
        "stem": "己",
        "branch": "未",
        "hidden_stems": "己",
    }

    with pytest.raises(
        TypeError,
        match="hidden_stemsはlist型",
    ):
        find_element_roots_in_pillar(
            position="month",
            pillar_data=pillar_data,
            target_element="土",
        )


def test_transformation_root_with_month_root():
    chart_data = make_chart_data()

    result = evaluate_transformation_root(
        result_element="土",
        chart_data=chart_data,
    )

    assert (
        result["result_element"]
        == "土"
    )

    assert (
        result["has_root"]
        is True
    )

    assert (
        result["has_month_root"]
        is True
    )

    assert (
        result["root_count"]
        == 2
    )

    assert (
        result["root_positions"]
        == [
            "month",
            "day",
        ]
    )

    # 月支 未：己
    # 1.0 × 1.5 = 1.5
    #
    # 日支 巳：戊（3番目）
    # 0.3 × 1.2 = 0.36
    assert (
        result["total_root_score"]
        == 1.86
    )

    assert (
        result["month_root_score"]
        == 1.5
    )

    assert (
        result["root_strength"]
        == "strong"
    )

    assert (
        result["method"]
        == "transformation_root_v1"
    )

    assert (
        result["status"]
        == "provisional_transformation_root"
    )


def test_transformation_root_present_without_month_root():
    chart_data = make_chart_data()

    result = evaluate_transformation_root(
        result_element="水",
        chart_data=chart_data,
    )

    assert (
        result["has_root"]
        is True
    )

    assert (
        result["has_month_root"]
        is False
    )

    assert (
        result["root_count"]
        == 2
    )

    assert (
        result["root_positions"]
        == [
            "year",
            "hour",
        ]
    )

    # 年支 子：癸
    # 1.0 × 0.8 = 0.8
    #
    # 時支 亥：壬
    # 1.0 × 1.0 = 1.0
    assert (
        result["total_root_score"]
        == 1.8
    )

    assert (
        result["month_root_score"]
        == 0
    )

    assert (
        result["root_strength"]
        == "present"
    )


def test_transformation_root_none():
    chart_data = {
        "year": make_pillar(
            "甲",
            "寅",
            ["甲", "丙", "戊"],
        ),
        "month": make_pillar(
            "乙",
            "卯",
            ["乙"],
        ),
        "day": make_pillar(
            "丙",
            "午",
            ["丁", "己"],
        ),
        "hour": None,
    }

    result = evaluate_transformation_root(
        result_element="水",
        chart_data=chart_data,
    )

    assert (
        result["has_root"]
        is False
    )

    assert (
        result["has_month_root"]
        is False
    )

    assert (
        result["root_count"]
        == 0
    )

    assert (
        result["root_positions"]
        == []
    )

    assert (
        result["total_root_score"]
        == 0
    )

    assert (
        result["month_root_score"]
        == 0
    )

    assert (
        result["root_strength"]
        == "none"
    )

    assert (
        result["roots"]
        == []
    )


def test_transformation_root_without_hour():
    chart_data = make_chart_data()

    chart_data["hour"] = None

    result = evaluate_transformation_root(
        result_element="水",
        chart_data=chart_data,
    )

    assert (
        result["has_root"]
        is True
    )

    assert (
        result["root_count"]
        == 1
    )

    assert (
        result["root_positions"]
        == ["year"]
    )

    assert (
        result["total_root_score"]
        == 0.8
    )


def test_invalid_transformation_element():
    with pytest.raises(
        ValueError,
        match="不正な五行です",
    ):
        evaluate_transformation_root(
            result_element="風",
            chart_data=make_chart_data(),
        )


def test_invalid_chart_data_type():
    with pytest.raises(
        TypeError,
        match="chart_dataはdict型",
    ):
        evaluate_transformation_root(
            result_element="土",
            chart_data=[],
        )


def test_evaluate_transformation_roots():
    stem_transformations = {
        "transformations": [
            {
                "combination_name": "甲己",
                "result_element": "土",
                "transformation_status": (
                    "possible"
                ),
                "confidence": "high",
            },
            {
                "combination_name": "乙庚",
                "result_element": "金",
                "transformation_status": (
                    "unsupported"
                ),
                "confidence": "low",
            },
        ],
    }

    chart_data = make_chart_data()

    result = evaluate_transformation_roots(
        stem_transformations,
        chart_data,
    )

    assert (
        result[
            "has_transformation_candidate"
        ]
        is True
    )

    assert (
        result["transformation_count"]
        == 2
    )

    # 土:
    # 月支 未・日支 巳に根あり
    #
    # 金:
    # 日支 巳の庚に根あり
    assert (
        result["rooted_count"]
        == 2
    )

    assert (
        result["month_rooted_count"]
        == 1
    )

    assert (
        result["overall_root_status"]
        == "rooted"
    )

    assert (
        len(
            result["results"]
        )
        == 2
    )

    assert (
        result["method"]
        == "transformation_roots_v1"
    )

    assert (
        result["status"]
        == "provisional_transformation_roots"
    )


def test_evaluate_transformation_roots_mixed():
    stem_transformations = {
        "transformations": [
            {
                "combination_name": "甲己",
                "result_element": "土",
                "transformation_status": (
                    "possible"
                ),
                "confidence": "high",
            },
            {
                "combination_name": "丙辛",
                "result_element": "水",
                "transformation_status": (
                    "possible"
                ),
                "confidence": "medium",
            },
        ],
    }

    chart_data = {
        "year": make_pillar(
            "甲",
            "辰",
            ["戊", "乙", "癸"],
        ),
        "month": make_pillar(
            "己",
            "未",
            ["己", "丁", "乙"],
        ),
        "day": make_pillar(
            "丙",
            "午",
            ["丁", "己"],
        ),
        "hour": None,
    }

    result = evaluate_transformation_roots(
        stem_transformations,
        chart_data,
    )

    assert (
        result["transformation_count"]
        == 2
    )

    # 土には根あり。
    # 水にも辰の3番目の癸があるため、
    # この命式では両方ともrootedになります。
    assert (
        result["rooted_count"]
        == 2
    )

    assert (
        result["overall_root_status"]
        == "rooted"
    )


def test_evaluate_transformation_roots_true_mixed():
    stem_transformations = {
        "transformations": [
            {
                "combination_name": "甲己",
                "result_element": "土",
                "transformation_status": (
                    "possible"
                ),
                "confidence": "high",
            },
            {
                "combination_name": "丙辛",
                "result_element": "水",
                "transformation_status": (
                    "unsupported"
                ),
                "confidence": "low",
            },
        ],
    }

    chart_data = {
        "year": make_pillar(
            "甲",
            "寅",
            ["甲", "丙", "戊"],
        ),
        "month": make_pillar(
            "己",
            "未",
            ["己", "丁", "乙"],
        ),
        "day": make_pillar(
            "丙",
            "午",
            ["丁", "己"],
        ),
        "hour": None,
    }

    result = evaluate_transformation_roots(
        stem_transformations,
        chart_data,
    )

    assert (
        result["transformation_count"]
        == 2
    )

    assert (
        result["rooted_count"]
        == 1
    )

    assert (
        result["overall_root_status"]
        == "mixed"
    )


def test_evaluate_transformation_roots_unrooted():
    stem_transformations = {
        "transformations": [
            {
                "combination_name": "丙辛",
                "result_element": "水",
                "transformation_status": (
                    "unsupported"
                ),
                "confidence": "low",
            },
        ],
    }

    chart_data = {
        "year": make_pillar(
            "甲",
            "寅",
            ["甲", "丙", "戊"],
        ),
        "month": make_pillar(
            "乙",
            "卯",
            ["乙"],
        ),
        "day": make_pillar(
            "丙",
            "午",
            ["丁", "己"],
        ),
        "hour": None,
    }

    result = evaluate_transformation_roots(
        stem_transformations,
        chart_data,
    )

    assert (
        result["transformation_count"]
        == 1
    )

    assert (
        result["rooted_count"]
        == 0
    )

    assert (
        result["month_rooted_count"]
        == 0
    )

    assert (
        result["overall_root_status"]
        == "unrooted"
    )


def test_evaluate_transformation_roots_not_applicable():
    stem_transformations = {
        "transformations": [],
    }

    result = evaluate_transformation_roots(
        stem_transformations,
        make_chart_data(),
    )

    assert (
        result[
            "has_transformation_candidate"
        ]
        is False
    )

    assert (
        result["transformation_count"]
        == 0
    )

    assert (
        result["rooted_count"]
        == 0
    )

    assert (
        result["month_rooted_count"]
        == 0
    )

    assert (
        result["overall_root_status"]
        == "not_applicable"
    )

    assert (
        result["results"]
        == []
    )


def test_invalid_stem_transformations_type():
    with pytest.raises(
        TypeError,
        match="stem_transformationsはdict型",
    ):
        evaluate_transformation_roots(
            stem_transformations=[],
            chart_data=make_chart_data(),
        )


def test_invalid_transformations_type():
    with pytest.raises(
        TypeError,
        match="transformationsはlist型",
    ):
        evaluate_transformation_roots(
            stem_transformations={
                "transformations": {},
            },
            chart_data=make_chart_data(),
        )


def test_missing_result_element():
    stem_transformations = {
        "transformations": [
            {
                "combination_name": "甲己",
            },
        ],
    }

    with pytest.raises(
        ValueError,
        match=(
            "transformationに"
            "result_elementが必要です"
        ),
    ):
        evaluate_transformation_roots(
            stem_transformations,
            make_chart_data(),
        )


def test_result_contains_notes():
    result = evaluate_transformation_roots(
        {
            "transformations": [],
        },
        make_chart_data(),
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
