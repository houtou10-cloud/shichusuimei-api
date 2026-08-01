import pytest

from engine.five_elements import (
    calculate_five_elements,
    count_pillar_elements,
    get_branch_element,
    get_stem_element,
)


def test_get_stem_element():
    assert get_stem_element("甲") == "木"
    assert get_stem_element("丁") == "火"
    assert get_stem_element("己") == "土"
    assert get_stem_element("辛") == "金"
    assert get_stem_element("癸") == "水"


def test_get_branch_element():
    assert get_branch_element("寅") == "木"
    assert get_branch_element("午") == "火"
    assert get_branch_element("未") == "土"
    assert get_branch_element("酉") == "金"
    assert get_branch_element("亥") == "水"


def test_count_single_pillar():
    pillar_data = {
        "stem": "乙",
        "branch": "丑",
        "hidden_stems": [
            "己",
            "癸",
            "辛",
        ],
    }

    result = count_pillar_elements(
        pillar_data
    )

    assert result == {
        "木": 1,
        "火": 0,
        "土": 2,
        "金": 1,
        "水": 1,
    }


def test_verified_chart_five_elements():
    chart = {
        "year": {
            "stem": "乙",
            "branch": "丑",
            "hidden_stems": [
                "己",
                "癸",
                "辛",
            ],
        },
        "month": {
            "stem": "癸",
            "branch": "未",
            "hidden_stems": [
                "己",
                "丁",
                "乙",
            ],
        },
        "day": {
            "stem": "乙",
            "branch": "巳",
            "hidden_stems": [
                "丙",
                "戊",
                "庚",
            ],
        },
        "hour": {
            "stem": "丁",
            "branch": "亥",
            "hidden_stems": [
                "壬",
                "甲",
            ],
        },
    }

    result = calculate_five_elements(chart)

    assert result["counts"] == {
        "木": 4,
        "火": 4,
        "土": 4,
        "金": 2,
        "水": 4,
    }

    assert result["total"] == 18
    assert result["method"] == "simple_count_v1"


def test_invalid_values():
    with pytest.raises(ValueError):
        get_stem_element("無")

    with pytest.raises(ValueError):
        get_branch_element("無")
