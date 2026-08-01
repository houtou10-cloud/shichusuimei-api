import pytest

from engine.day_master_strength import (
    classify_five_elements_for_day_master,
    get_day_master_element,
    get_draining_elements,
    get_supporting_elements,
)


def test_day_master_element():
    assert get_day_master_element(
        "乙"
    ) == "木"

    assert get_day_master_element(
        "丙"
    ) == "火"

    assert get_day_master_element(
        "癸"
    ) == "水"


def test_supporting_elements_for_yi():
    assert get_supporting_elements(
        "乙"
    ) == [
        "木",
        "水",
    ]


def test_draining_elements_for_yi():
    assert get_draining_elements(
        "乙"
    ) == [
        "火",
        "土",
        "金",
    ]


def test_classify_verified_chart():
    five_elements = {
        "counts": {
            "木": 4,
            "火": 4,
            "土": 5,
            "金": 2,
            "水": 4,
        }
    }

    result = (
        classify_five_elements_for_day_master(
            "乙",
            five_elements,
        )
    )

    assert result["day_element"] == "木"

    assert result[
        "supporting_elements"
    ] == [
        "木",
        "水",
    ]

    assert result[
        "draining_elements"
    ] == [
        "火",
        "土",
        "金",
    ]

    assert result[
        "supporting_score"
    ] == 8

    assert result[
        "draining_score"
    ] == 11

    assert result[
        "supporting_ratio"
    ] == 42.11

    assert result[
        "draining_ratio"
    ] == 57.89

    assert result["status"] == (
        "classification_only"
    )


def test_invalid_day_stem():
    with pytest.raises(ValueError):
        get_day_master_element("無")
