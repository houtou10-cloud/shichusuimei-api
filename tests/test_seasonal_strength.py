import pytest

from engine.seasonal_strength import (
    evaluate_seasonal_strength,
)


def test_wood_in_spring():
    result = evaluate_seasonal_strength(
        "乙",
        "卯",
    )

    assert result["day_element"] == "木"
    assert result["state"] == "旺"
    assert result["score"] == 12.0


def test_wood_in_wei_month():
    result = evaluate_seasonal_strength(
        "乙",
        "未",
    )

    assert result["day_element"] == "木"
    assert result["state"] == "囚"
    assert result["score"] == -6.0

    assert (
        result["method"]
        == "seasonal_state_v1"
    )


def test_water_in_winter():
    result = evaluate_seasonal_strength(
        "癸",
        "子",
    )

    assert result["day_element"] == "水"
    assert result["state"] == "旺"
    assert result["score"] == 12.0


def test_invalid_month_branch():
    with pytest.raises(ValueError):
        evaluate_seasonal_strength(
            "乙",
            "無",
        )
