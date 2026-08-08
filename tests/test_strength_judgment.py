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

    integrated_month_strength = {
        "seasonal_state": "囚",
        "seasonal_score": -6.0,
        "supporting_ratio": 10.0,
        "draining_ratio": 90.0,
        "hidden_stem_balance": -0.8,
        "hidden_stem_adjustment": -3.2,
        "integrated_score": -9.2,
    }

    result = calculate_weighted_provisional_strength(
        weighted_day_master_balance,
        weighted_root_strength,
        month_command,
        integrated_month_strength,
    )

    # 55.0 + 4.5 - 9.2 = 50.3
    assert result["label"] == "やや身強寄り"
    assert result["final_score"] == 50.3
    assert result["base_supporting_ratio"] == 55.0

    assert result["adjustments"] == {
        "weighted_root_bonus": 4.5,
        "integrated_month_adjustment": -9.2,
    }

    assert (
        result["evidence"][
            "total_root_score"
        ]
        == 0.45
    )

    assert (
        result["evidence"][
            "integrated_month_score"
        ]
        == -9.2
    )

    assert (
        result["evidence"][
            "seasonal_state"
        ]
        == "囚"
    )

    assert (
        result["evidence"][
            "seasonal_score"
        ]
        == -6.0
    )

    assert (
        result["evidence"][
            "month_supporting_ratio"
        ]
        == 10.0
    )

    assert (
        result["evidence"][
            "month_draining_ratio"
        ]
        == 90.0
    )

    assert (
        result["evidence"][
            "hidden_stem_balance"
        ]
        == -0.8
    )

    assert (
        result["evidence"][
            "hidden_stem_adjustment"
        ]
        == -3.2
    )

    assert (
        result["method"]
        == "weighted_provisional_strength_v3"
    )

    assert (
        result["status"]
        == "provisional_weighted_judgment"
    )


def test_weighted_strength_with_strong_month():
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

    integrated_month_strength = {
        "seasonal_state": "旺",
        "seasonal_score": 12.0,
        "supporting_ratio": 80.0,
        "draining_ratio": 20.0,
        "hidden_stem_balance": 0.6,
        "hidden_stem_adjustment": 2.4,
        "integrated_score": 14.4,
    }

    result = calculate_weighted_provisional_strength(
        weighted_day_master_balance,
        weighted_root_strength,
        month_command,
        integrated_month_strength,
    )

    # 55.0 + 4.5 + 14.4 = 73.9
    assert result["final_score"] == 73.9
    assert result["label"] == "身強寄り"

    assert result["adjustments"] == {
        "weighted_root_bonus": 4.5,
        "integrated_month_adjustment": 14.4,
    }

    assert (
        result["method"]
        == "weighted_provisional_strength_v3"
    )


def test_weighted_strength_with_weak_month():
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

    integrated_month_strength = {
        "seasonal_state": "死",
        "seasonal_score": -10.0,
        "supporting_ratio": 20.0,
        "draining_ratio": 80.0,
        "hidden_stem_balance": -0.6,
        "hidden_stem_adjustment": -2.4,
        "integrated_score": -12.4,
    }

    result = calculate_weighted_provisional_strength(
        weighted_day_master_balance,
        weighted_root_strength,
        month_command,
        integrated_month_strength,
    )

    # 55.0 + 4.5 - 12.4 = 47.1
    assert result["final_score"] == 47.1

    assert (
        result["label"]
        == "中和～やや身弱寄り"
    )

    assert result["adjustments"] == {
        "weighted_root_bonus": 4.5,
        "integrated_month_adjustment": -12.4,
    }

    assert (
        result["method"]
        == "weighted_provisional_strength_v3"
    )


def test_weighted_strength_with_neutral_month():
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
        "effect": "neutral",
        "relationship": "neutral",
    }

    integrated_month_strength = {
        "seasonal_state": "休",
        "seasonal_score": 2.0,
        "supporting_ratio": 50.0,
        "draining_ratio": 50.0,
        "hidden_stem_balance": 0.0,
        "hidden_stem_adjustment": 0.0,
        "integrated_score": 2.0,
    }

    result = calculate_weighted_provisional_strength(
        weighted_day_master_balance,
        weighted_root_strength,
        month_command,
        integrated_month_strength,
    )

    # 55.0 + 4.5 + 2.0 = 61.5
    assert result["final_score"] == 61.5
    assert result["label"] == "身強寄り"

    assert result["adjustments"] == {
        "weighted_root_bonus": 4.5,
        "integrated_month_adjustment": 2.0,
    }

    assert (
        result["method"]
        == "weighted_provisional_strength_v3"
    )


def test_weighted_strength_clamps_to_100():
    weighted_day_master_balance = {
        "supporting_score": 9.0,
        "draining_score": 1.0,
        "supporting_ratio": 90.0,
    }

    weighted_root_strength = {
        "root_count": 3,
        "root_positions": [
            "year",
            "month",
            "hour",
        ],
        "total_root_score": 1.5,
    }

    month_command = {
        "effect": "supporting",
        "relationship": "companion",
    }

    integrated_month_strength = {
        "seasonal_state": "旺",
        "seasonal_score": 12.0,
        "supporting_ratio": 100.0,
        "draining_ratio": 0.0,
        "hidden_stem_balance": 1.0,
        "hidden_stem_adjustment": 4.0,
        "integrated_score": 16.0,
    }

    result = calculate_weighted_provisional_strength(
        weighted_day_master_balance,
        weighted_root_strength,
        month_command,
        integrated_month_strength,
    )

    # 90 + 15 + 16 = 121 → 100へ制限
    assert result["final_score"] == 100.0
    assert result["label"] == "身強寄り"


def test_weighted_strength_clamps_to_zero():
    weighted_day_master_balance = {
        "supporting_score": 0.5,
        "draining_score": 9.5,
        "supporting_ratio": 5.0,
    }

    weighted_root_strength = {
        "root_count": 0,
        "root_positions": [],
        "total_root_score": 0.0,
    }

    month_command = {
        "effect": "controlling",
        "relationship": "officer",
    }

    integrated_month_strength = {
        "seasonal_state": "死",
        "seasonal_score": -10.0,
        "supporting_ratio": 0.0,
        "draining_ratio": 100.0,
        "hidden_stem_balance": -1.0,
        "hidden_stem_adjustment": -4.0,
        "integrated_score": -14.0,
    }

    result = calculate_weighted_provisional_strength(
        weighted_day_master_balance,
        weighted_root_strength,
        month_command,
        integrated_month_strength,
    )

    # 5 + 0 - 14 = -9 → 0へ制限
    assert result["final_score"] == 0.0

    assert (
        result["label"]
        == "かなり身弱寄り"
    )
