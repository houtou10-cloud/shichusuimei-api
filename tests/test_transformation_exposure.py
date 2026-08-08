import pytest

from engine.transformation_exposure import (
    evaluate_transformation_exposure,
    evaluate_transformation_exposures,
    find_element_exposures,
    get_available_positions,
    get_stem_element,
)


def make_pillar(
    stem: str,
    branch: str,
) -> dict:
    """
    テスト用の柱データを作成します。
    """
    return {
        "stem": stem,
        "branch": branch,
    }


def make_chart_data() -> dict:
    """
    透干テスト用の標準命式を作成します。

    年干：甲
    月干：己
    日干：戊
    時干：乙

    土の天干は、
    月干の己と日干の戊です。
    """
    return {
        "year": make_pillar(
            "甲",
            "子",
        ),
        "month": make_pillar(
            "己",
            "未",
        ),
        "day": make_pillar(
            "戊",
            "巳",
        ),
        "hour": make_pillar(
            "乙",
            "亥",
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
        get_stem_element(
            "A"
        )


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


def test_find_element_exposures():
    chart_data = make_chart_data()

    result = find_element_exposures(
        result_element="土",
        chart_data=chart_data,
    )

    assert result == [
        {
            "position": "month",
            "stem": "己",
            "element": "土",
            "position_weight": 1.3,
        },
        {
            "position": "day",
            "stem": "戊",
            "element": "土",
            "position_weight": 1.2,
        },
    ]


def test_find_element_exposures_none():
    chart_data = {
        "year": make_pillar(
            "甲",
            "寅",
        ),
        "month": make_pillar(
            "乙",
            "卯",
        ),
        "day": make_pillar(
            "丙",
            "午",
        ),
        "hour": None,
    }

    result = find_element_exposures(
        result_element="水",
        chart_data=chart_data,
    )

    assert result == []


def test_find_element_exposures_without_hour():
    chart_data = {
        "year": make_pillar(
            "壬",
            "子",
        ),
        "month": make_pillar(
            "甲",
            "寅",
        ),
        "day": make_pillar(
            "癸",
            "亥",
        ),
        "hour": None,
    }

    result = find_element_exposures(
        result_element="水",
        chart_data=chart_data,
    )

    assert result == [
        {
            "position": "year",
            "stem": "壬",
            "element": "水",
            "position_weight": 0.8,
        },
        {
            "position": "day",
            "stem": "癸",
            "element": "水",
            "position_weight": 1.2,
        },
    ]


def test_invalid_result_element():
    with pytest.raises(
        ValueError,
        match="不正な五行です",
    ):
        find_element_exposures(
            result_element="風",
            chart_data=make_chart_data(),
        )


def test_invalid_chart_data_type():
    with pytest.raises(
        TypeError,
        match="chart_dataはdict型",
    ):
        find_element_exposures(
            result_element="土",
            chart_data=[],
        )


def test_missing_stem():
    chart_data = make_chart_data()

    chart_data["year"] = {
        "branch": "子",
    }

    with pytest.raises(
        ValueError,
        match="year柱にstemが必要です",
    ):
        find_element_exposures(
            result_element="土",
            chart_data=chart_data,
        )


def test_invalid_pillar_type():
    chart_data = make_chart_data()

    chart_data["year"] = "甲子"

    with pytest.raises(
        TypeError,
        match="year柱はdict型",
    ):
        find_element_exposures(
            result_element="土",
            chart_data=chart_data,
        )


def test_external_exposure():
    """
    甲己の干合で土化候補。

    甲：year
    己：month

    日干に戊があるため、
    干合参加者以外から
    土が透干しています。
    """
    transformation = {
        "position_a": "year",
        "stem_a": "甲",
        "position_b": "month",
        "stem_b": "己",
        "combination_name": "甲己",
        "result_element": "土",
        "transformation_status": "possible",
        "confidence": "high",
    }

    result = (
        evaluate_transformation_exposure(
            transformation,
            make_chart_data(),
        )
    )

    assert (
        result["combination_name"]
        == "甲己"
    )

    assert (
        result["result_element"]
        == "土"
    )

    assert (
        result["has_exposure"]
        is True
    )

    assert (
        result["exposure_count"]
        == 2
    )

    assert (
        result["exposure_positions"]
        == [
            "month",
            "day",
        ]
    )

    assert (
        result[
            "participant_exposure_count"
        ]
        == 1
    )

    assert (
        result[
            "participant_exposures"
        ]
        == [
            {
                "position": "month",
                "stem": "己",
                "element": "土",
                "position_weight": 1.3,
            },
        ]
    )

    assert (
        result[
            "has_external_exposure"
        ]
        is True
    )

    assert (
        result[
            "external_exposure_count"
        ]
        == 1
    )

    assert (
        result[
            "external_exposure_positions"
        ]
        == [
            "day",
        ]
    )

    assert (
        result[
            "external_exposures"
        ]
        == [
            {
                "position": "day",
                "stem": "戊",
                "element": "土",
                "position_weight": 1.2,
            },
        ]
    )

    assert (
        result[
            "total_exposure_score"
        ]
        == 2.5
    )

    assert (
        result[
            "external_exposure_score"
        ]
        == 1.2
    )

    assert (
        result[
            "exposure_strength"
        ]
        == "strong"
    )

    assert (
        result["method"]
        == "transformation_exposure_v1"
    )

    assert (
        result["status"]
        == "provisional_transformation_exposure"
    )


def test_participant_only_exposure():
    """
    甲己の土化候補だが、
    土の天干が干合参加者の己だけの場合。
    """
    transformation = {
        "position_a": "year",
        "stem_a": "甲",
        "position_b": "month",
        "stem_b": "己",
        "combination_name": "甲己",
        "result_element": "土",
    }

    chart_data = {
        "year": make_pillar(
            "甲",
            "子",
        ),
        "month": make_pillar(
            "己",
            "未",
        ),
        "day": make_pillar(
            "乙",
            "卯",
        ),
        "hour": make_pillar(
            "丙",
            "午",
        ),
    }

    result = (
        evaluate_transformation_exposure(
            transformation,
            chart_data,
        )
    )

    assert (
        result["has_exposure"]
        is True
    )

    assert (
        result["exposure_count"]
        == 1
    )

    assert (
        result[
            "participant_exposure_count"
        ]
        == 1
    )

    assert (
        result[
            "has_external_exposure"
        ]
        is False
    )

    assert (
        result[
            "external_exposure_count"
        ]
        == 0
    )

    assert (
        result[
            "external_exposure_positions"
        ]
        == []
    )

    assert (
        result[
            "external_exposures"
        ]
        == []
    )

    assert (
        result[
            "external_exposure_score"
        ]
        == 0
    )

    assert (
        result[
            "exposure_strength"
        ]
        == "participant_only"
    )


def test_no_exposure():
    transformation = {
        "position_a": "year",
        "stem_a": "丙",
        "position_b": "month",
        "stem_b": "辛",
        "combination_name": "丙辛",
        "result_element": "水",
    }

    chart_data = {
        "year": make_pillar(
            "丙",
            "午",
        ),
        "month": make_pillar(
            "辛",
            "酉",
        ),
        "day": make_pillar(
            "甲",
            "寅",
        ),
        "hour": make_pillar(
            "乙",
            "卯",
        ),
    }

    result = (
        evaluate_transformation_exposure(
            transformation,
            chart_data,
        )
    )

    assert (
        result["has_exposure"]
        is False
    )

    assert (
        result["exposure_count"]
        == 0
    )

    assert (
        result[
            "participant_exposure_count"
        ]
        == 0
    )

    assert (
        result[
            "has_external_exposure"
        ]
        is False
    )

    assert (
        result[
            "external_exposure_count"
        ]
        == 0
    )

    assert (
        result[
            "total_exposure_score"
        ]
        == 0
    )

    assert (
        result[
            "external_exposure_score"
        ]
        == 0
    )

    assert (
        result[
            "exposure_strength"
        ]
        == "none"
    )


def test_evaluate_transformation_exposures():
    stem_transformations = {
        "transformations": [
            {
                "position_a": "year",
                "stem_a": "甲",
                "position_b": "month",
                "stem_b": "己",
                "combination_name": "甲己",
                "result_element": "土",
                "transformation_status": (
                    "possible"
                ),
                "confidence": "high",
            },
        ],
    }

    result = (
        evaluate_transformation_exposures(
            stem_transformations,
            make_chart_data(),
        )
    )

    assert (
        result[
            "has_transformation_candidate"
        ]
        is True
    )

    assert (
        result["transformation_count"]
        == 1
    )

    assert (
        result["exposed_count"]
        == 1
    )

    assert (
        result[
            "external_exposed_count"
        ]
        == 1
    )

    assert (
        result[
            "overall_exposure_status"
        ]
        == "externally_exposed"
    )

    assert (
        len(
            result["results"]
        )
        == 1
    )

    assert (
        result["results"][0][
            "combination_name"
        ]
        == "甲己"
    )

    assert (
        result["method"]
        == "transformation_exposures_v1"
    )

    assert (
        result["status"]
        == "provisional_transformation_exposures"
    )


def test_evaluate_multiple_transformations_mixed():
    stem_transformations = {
        "transformations": [
            {
                "position_a": "year",
                "stem_a": "甲",
                "position_b": "month",
                "stem_b": "己",
                "combination_name": "甲己",
                "result_element": "土",
                "transformation_status": (
                    "possible"
                ),
                "confidence": "high",
            },
            {
                "position_a": "day",
                "stem_a": "丙",
                "position_b": "hour",
                "stem_b": "辛",
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
            "子",
        ),
        "month": make_pillar(
            "己",
            "未",
        ),
        "day": make_pillar(
            "丙",
            "午",
        ),
        "hour": make_pillar(
            "辛",
            "酉",
        ),
    }

    result = (
        evaluate_transformation_exposures(
            stem_transformations,
            chart_data,
        )
    )

    assert (
        result["transformation_count"]
        == 2
    )

    # 甲己→土:
    # 己は参加者だが外部の土干はなし
    #
    # 丙辛→水:
    # 水干なし
    assert (
        result["exposed_count"]
        == 1
    )

    assert (
        result[
            "external_exposed_count"
        ]
        == 0
    )

    assert (
        result[
            "overall_exposure_status"
        ]
        == "participant_only"
    )


def test_true_mixed_external_exposure():
    stem_transformations = {
        "transformations": [
            {
                "position_a": "year",
                "stem_a": "甲",
                "position_b": "month",
                "stem_b": "己",
                "combination_name": "甲己",
                "result_element": "土",
                "transformation_status": (
                    "possible"
                ),
                "confidence": "high",
            },
            {
                "position_a": "day",
                "stem_a": "丁",
                "position_b": "hour",
                "stem_b": "壬",
                "combination_name": "丁壬",
                "result_element": "木",
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
            "子",
        ),
        "month": make_pillar(
            "己",
            "未",
        ),
        "day": make_pillar(
            "丁",
            "午",
        ),
        "hour": make_pillar(
            "壬",
            "亥",
        ),
    }

    result = (
        evaluate_transformation_exposures(
            stem_transformations,
            chart_data,
        )
    )

    # 甲己→土:
    # 己のみ。外部土なし。
    #
    # 丁壬→木:
    # yearの甲が外部透干。
    assert (
        result["transformation_count"]
        == 2
    )

    assert (
        result["exposed_count"]
        == 2
    )

    assert (
        result[
            "external_exposed_count"
        ]
        == 1
    )

    assert (
        result[
            "overall_exposure_status"
        ]
        == "mixed"
    )


def test_participant_only_overall_status():
    stem_transformations = {
        "transformations": [
            {
                "position_a": "year",
                "stem_a": "甲",
                "position_b": "month",
                "stem_b": "己",
                "combination_name": "甲己",
                "result_element": "土",
            },
        ],
    }

    chart_data = {
        "year": make_pillar(
            "甲",
            "子",
        ),
        "month": make_pillar(
            "己",
            "未",
        ),
        "day": make_pillar(
            "乙",
            "卯",
        ),
        "hour": None,
    }

    result = (
        evaluate_transformation_exposures(
            stem_transformations,
            chart_data,
        )
    )

    assert (
        result["exposed_count"]
        == 1
    )

    assert (
        result[
            "external_exposed_count"
        ]
        == 0
    )

    assert (
        result[
            "overall_exposure_status"
        ]
        == "participant_only"
    )


def test_unexposed_overall_status():
    stem_transformations = {
        "transformations": [
            {
                "position_a": "year",
                "stem_a": "丙",
                "position_b": "month",
                "stem_b": "辛",
                "combination_name": "丙辛",
                "result_element": "水",
            },
        ],
    }

    chart_data = {
        "year": make_pillar(
            "丙",
            "午",
        ),
        "month": make_pillar(
            "辛",
            "酉",
        ),
        "day": make_pillar(
            "甲",
            "寅",
        ),
        "hour": None,
    }

    result = (
        evaluate_transformation_exposures(
            stem_transformations,
            chart_data,
        )
    )

    assert (
        result["exposed_count"]
        == 0
    )

    assert (
        result[
            "external_exposed_count"
        ]
        == 0
    )

    assert (
        result[
            "overall_exposure_status"
        ]
        == "unexposed"
    )


def test_not_applicable():
    stem_transformations = {
        "transformations": [],
    }

    result = (
        evaluate_transformation_exposures(
            stem_transformations,
            make_chart_data(),
        )
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
        result["exposed_count"]
        == 0
    )

    assert (
        result[
            "external_exposed_count"
        ]
        == 0
    )

    assert (
        result[
            "overall_exposure_status"
        ]
        == "not_applicable"
    )

    assert (
        result["results"]
        == []
    )


def test_invalid_transformation_type():
    with pytest.raises(
        TypeError,
        match="transformationはdict型",
    ):
        evaluate_transformation_exposure(
            transformation=[],
            chart_data=make_chart_data(),
        )


def test_invalid_transformation_chart_data():
    with pytest.raises(
        TypeError,
        match="chart_dataはdict型",
    ):
        evaluate_transformation_exposure(
            transformation={
                "result_element": "土",
            },
            chart_data=[],
        )


def test_missing_result_element():
    with pytest.raises(
        ValueError,
        match=(
            "transformationに"
            "result_elementが必要です"
        ),
    ):
        evaluate_transformation_exposure(
            transformation={
                "combination_name": "甲己",
            },
            chart_data=make_chart_data(),
        )


def test_invalid_stem_transformations_type():
    with pytest.raises(
        TypeError,
        match="stem_transformationsはdict型",
    ):
        evaluate_transformation_exposures(
            stem_transformations=[],
            chart_data=make_chart_data(),
        )


def test_invalid_transformations_type():
    with pytest.raises(
        TypeError,
        match="transformationsはlist型",
    ):
        evaluate_transformation_exposures(
            stem_transformations={
                "transformations": {},
            },
            chart_data=make_chart_data(),
        )


def test_missing_result_element_in_collection():
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
        evaluate_transformation_exposures(
            stem_transformations,
            make_chart_data(),
        )


def test_result_contains_notes():
    result = (
        evaluate_transformation_exposures(
            {
                "transformations": [],
            },
            make_chart_data(),
        )
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
