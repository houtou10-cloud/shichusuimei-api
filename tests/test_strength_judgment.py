import pytest

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


def test_weak_case():
    day_master_balance = {
        "supporting_score": 5,
        "draining_score": 15,
        "supporting_ratio": 25.0,
    }

    root_strength = {
        "root_count": 0,
        "root_positions": [],
    }

    month_command = {
        "effect": "controlling",
        "relationship": "officer",
    }

    result = calculate_provisional_strength(
        day_master_balance,
        root_strength,
        month_command,
    )

    assert result["label"] == "かなり身弱寄り"
    assert result["final_score"] == 15.0


def test_weighted_provisional_strength():
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

    result = (
        calculate_weighted_provisional_strength(
            weighted_day_master_balance,
            weighted_root_strength,
            month_command,
        )
    )

    # 55 + 4.5 - 8 = 51.5
    assert result["final_score"] == 51.5

    assert (
        result["label"]
        == "やや身強寄り"
    )

    assert result["adjustments"] == {
        "weighted_root_bonus": 4.5,
        "month_command_adjustment": -8.0,
    }

    assert (
        result["evidence"][
            "total_root_score"
        ]
        == 0.45
    )

    assert (
        result["method"]
        == "weighted_provisional_strength_v1"
    )

    assert (
        result["status"]
        == "provisional_weighted_judgment"
    )
