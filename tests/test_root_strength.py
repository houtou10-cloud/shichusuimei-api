import pytest

from engine.root_strength import (
    find_roots,
    get_stem_element,
)


def test_get_stem_element():
    assert get_stem_element("甲") == "木"
    assert get_stem_element("乙") == "木"
    assert get_stem_element("丁") == "火"
    assert get_stem_element("己") == "土"
    assert get_stem_element("辛") == "金"
    assert get_stem_element("癸") == "水"


def test_verified_yi_wood_roots():
    chart = {
        "year": {
            "branch": "丑",
            "hidden_stems": [
                "己",
                "癸",
                "辛",
            ],
        },
        "month": {
            "branch": "未",
            "hidden_stems": [
                "己",
                "丁",
                "乙",
            ],
        },
        "day": {
            "branch": "巳",
            "hidden_stems": [
                "丙",
                "戊",
                "庚",
            ],
        },
        "hour": {
            "branch": "亥",
            "hidden_stems": [
                "壬",
                "甲",
            ],
        },
    }

    result = find_roots(
        "乙",
        chart,
    )

    assert result["has_root"] is True
    assert result["root_count"] == 2

    assert result["root_positions"] == [
        "month",
        "hour",
    ]

    assert result["roots"] == [
        {
            "position": "month",
            "branch": "未",
            "root_stems": ["乙"],
            "root_count": 1,
        },
        {
            "position": "hour",
            "branch": "亥",
            "root_stems": ["甲"],
            "root_count": 1,
        },
    ]


def test_no_roots():
    chart = {
        "year": {
            "branch": "午",
            "hidden_stems": [
                "丁",
                "己",
            ],
        },
        "month": {
            "branch": "巳",
            "hidden_stems": [
                "丙",
                "戊",
                "庚",
            ],
        },
        "day": {
            "branch": "酉",
            "hidden_stems": [
                "辛",
            ],
        },
        "hour": None,
    }

    result = find_roots(
        "乙",
        chart,
    )

    assert result["has_root"] is False
    assert result["root_count"] == 0
    assert result["root_positions"] == []
    assert result["roots"] == []


def test_invalid_day_stem():
    with pytest.raises(ValueError):
        find_roots(
            "無",
            {},
        )
