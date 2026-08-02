from engine.integrated_month_strength import (
    calculate_integrated_month_strength,
)


def test_wood_in_wei_month():
    seasonal_strength = {
        "state": "囚",
        "score": -6.0,
    }

    weighted_month_command = {
        "supporting_ratio": 10.0,
        "draining_ratio": 90.0,
    }

    result = calculate_integrated_month_strength(
        seasonal_strength,
        weighted_month_command,
    )

    assert result["seasonal_state"] == "囚"
    assert result["seasonal_score"] == -6.0
    assert result["supporting_ratio"] == 10.0
    assert result["draining_ratio"] == 90.0
    assert result["hidden_stem_balance"] == -0.8
    assert result["hidden_stem_adjustment"] == -3.2
    assert result["integrated_score"] == -9.2

    assert (
        result["method"]
        == "integrated_month_strength_v1"
    )

    assert (
        result["status"]
        == "provisional_integrated_month_strength"
    )


def test_prosperous_supporting_month():
    seasonal_strength = {
        "state": "旺",
        "score": 12.0,
    }

    weighted_month_command = {
        "supporting_ratio": 80.0,
        "draining_ratio": 20.0,
    }

    result = calculate_integrated_month_strength(
        seasonal_strength,
        weighted_month_command,
    )

    assert result["hidden_stem_balance"] == 0.6
    assert result["hidden_stem_adjustment"] == 2.4
    assert result["integrated_score"] == 14.4


def test_balanced_hidden_stems():
    seasonal_strength = {
        "state": "休",
        "score": 2.0,
    }

    weighted_month_command = {
        "supporting_ratio": 50.0,
        "draining_ratio": 50.0,
    }

    result = calculate_integrated_month_strength(
        seasonal_strength,
        weighted_month_command,
    )

    assert result["hidden_stem_balance"] == 0.0
    assert result["hidden_stem_adjustment"] == 0.0
    assert result["integrated_score"] == 2.0
