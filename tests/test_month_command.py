import pytest

from engine.month_command import (
    classify_month_relationship,
    get_day_element,
    get_month_element,
)


def test_get_day_element():
    assert get_day_element("甲") == "木"
    assert get_day_element("乙") == "木"
    assert get_day_element("丙") == "火"
    assert get_day_element("癸") == "水"


def test_get_month_element():
    assert get_month_element("寅") == "木"
    assert get_month_element("午") == "火"
    assert get_month_element("未") == "土"
    assert get_month_element("酉") == "金"
    assert get_month_element("亥") == "水"


def test_yi_wood_in_wei_month():
    result = classify_month_relationship(
        "乙",
        "未",
    )

    assert result["day_element"] == "木"
    assert result["month_element"] == "土"
    assert result["relationship"] == "wealth"
    assert result["relationship_label"] == "財星"
    assert result["effect"] == "draining"
    assert result["supports_day_master"] is False


def test_supporting_month():
    # 乙木に対する亥水は印星
    result = classify_month_relationship(
        "乙",
        "亥",
    )

    assert result["relationship"] == "resource"
    assert result["effect"] == "supporting"
    assert result["supports_day_master"] is True


def test_same_element_month():
    # 乙木に対する寅木は比劫
    result = classify_month_relationship(
        "乙",
        "寅",
    )

    assert result["relationship"] == "same"
    assert result["effect"] == "supporting"


def test_invalid_values():
    with pytest.raises(ValueError):
        classify_month_relationship(
            "無",
            "未",
        )

    with pytest.raises(ValueError):
        classify_month_relationship(
            "乙",
            "無",
        )
