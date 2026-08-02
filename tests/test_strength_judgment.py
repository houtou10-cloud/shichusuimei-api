from engine.strength_judgment import (
    calculate_provisional_strength,
    calculate_weighted_provisional_strength,
    clamp_score,
    get_strength_label,
)


def test_clamp_score():
    assert clamp_score(50) == 50
    assert clamp_score(-10) == 0
    assert clamp_score(120) == 100


def test_strength_labels():
    assert get_strength_label(
        65
    ) == "身強寄り"

    assert get_strength_label(
        55
    ) == "やや身強寄り"

    assert get_strength_label(
        47
    ) == "中和～やや身弱寄り"

    assert get_strength_label(
        42
    ) == "身弱寄り"

    assert get_strength_label(
        35
    ) == "かなり身弱寄り"


def test_verified_chart_strength():
    day_master_balance = {
        "supporting_score": 8,
        "draining_score": 11,
        "supporting_ratio": 42.11,
    }

    root_strength = {
        "root_count": 2,
        "root_positions": [
            "month",
            "hour",
        ],
    }

    month_command = {
        "effect": "draining",
        "relationship": "wealth",
    }

    result = calculate_provisional_strength(
        day_master_balance,
        root_strength,
        month_command,
    )

    # 42.11 + 6 + 5 - 8 = 45.11
    assert result["final_score"] == 45.11

    assert (
        result["label"]
        == "中和～やや身弱寄り"
    )

    assert result["adjustments"] == {
        "root_bonus": 6.0,
        "month_root_bonus": 5.0,
        "month_command_adjustment": -8.0,
    }

    assert (
        result["method"]
        == "provisional_strength_v1"
    )

    assert (
        result["status"]
        == "provisional_judgment"
    )


def test_strong_supporting_case():
    day_master_balance = {
        "supporting_score": 14,
        "draining_score": 6,
        "supporting_ratio": 70.0,
    }

    root_strength = {
        "root_count": 2,
        "root_positions": [
            "month",
            "day",
        ],
    }

    month_command = {
        "effect": "supporting",
        "relationship": "resource",
    }

    result = calculate_provisional_strength(
        day_master_balance,
        root_strength,
        month_command,
    )

    assert result["label"] == "身強寄り"
    assert result["final_score"] == 93.0


def test_weighted_verified_chart_strength():
    weighted_day_master_balance = {
        "supporting_score": 4.4,
        "draining_score": 3.6,
        "supporting_ratio": 55.0,
    }

    weighted_root_strength = {
        "root_count": 2,
        "root_positions": [
            "month",
            "hour",
        ],
        "total_root_score": 0.45,
    }

    month_command = {
        "effect": "draining",
        "relationship": "wealth",
    }

    seasonal_strength = {
        "state": "囚",
        "score": -6.0,
    }

    result = calculate_weighted_provisional_strength(
        weighted_day_master_balance,
        weighted_root_strength,
        month_command,
        seasonal_strength,
    )

    # 55.0 + 4.5 - 6.0 = 53.5
    assert result["label"] == "やや身強寄り"
    assert result["final_score"] == 53.5

    assert result["adjustments"] == {
        "weighted_root_bonus": 4.5,
        "seasonal_adjustment": -6.0,
    }

    assert result["evidence"][
        "seasonal_state"
    ] == "囚"

    assert result["evidence"][
        "seasonal_score"
    ] == -6.0

    assert (
        result["method"]
        == "weighted_provisional_strength_v2"
    )

    assert (
        result["status"]
        == "provisional_weighted_judgment"
    )


def test_weighted_strength_with_prosperous_season():
    weighted_day_master_balance = {
        "supporting_score": 4.4,
        "draining_score": 3.6,
        "supporting_ratio": 55.0,
    }

    weighted_root_strength = {
        "root_count": 2,
        "root_positions": [
            "month",
            "hour",
        ],
        "total_root_score": 0.45,
    }

    month_command = {
        "effect": "supporting",
        "relationship": "companion",
    }

    seasonal_strength = {
        "state": "旺",
        "score": 12.0,
    }

    result = calculate_weighted_provisional_strength(
        weighted_day_master_balance,
        weighted_root_strength,
        month_command,
        seasonal_strength,
    )

    # 55.0 + 4.5 + 12.0 = 71.5
    assert result["final_score"] == 71.5
    assert result["label"] == "身強寄り"
    assert (
        result["adjustments"]["seasonal_adjustment"]
        == 12.0
    )


def test_weighted_strength_with_dead_season():
    weighted_day_master_balance = {
        "supporting_score": 4.4,
        "draining_score": 3.6,
        "supporting_ratio": 55.0,
    }

    weighted_root_strength = {
        "root_count": 2,
        "root_positions": [
            "month",
            "hour",
        ],
        "total_root_score": 0.45,
    }

    month_command = {
        "effect": "controlling",
        "relationship": "officer",
    }

    seasonal_strength = {
        "state": "死",
        "score": -10.0,
    }

    result = calculate_weighted_provisional_strength(
        weighted_day_master_balance,
        weighted_root_strength,
        month_command,
        seasonal_strength,
    )

    # 55.0 + 4.5 - 10.0 = 49.5
    assert result["final_score"] == 49.5

    assert (
        result["label"]
        == "中和～やや身弱寄り"
    )
