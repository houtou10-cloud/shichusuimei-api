from engine.weighted_month_command import (
    calculate_weighted_month_command,
)


def test_wood_day_master_in_wei_month():
    month_pillar = {
        "branch": "未",
        "hidden_stems": [
            "己",
            "丁",
            "乙",
        ],
    }

    result = (
        calculate_weighted_month_command(
            "乙",
            month_pillar,
        )
    )

    assert result["day_element"] == "木"
    assert result["month_branch"] == "未"

    assert result["supporting_score"] == 0.1
    assert result["draining_score"] == 0.9

    assert result["supporting_ratio"] == 10.0
    assert result["draining_ratio"] == 90.0

    assert result["details"] == [
        {
            "stem": "己",
            "element": "土",
            "weight": 0.6,
            "supports_day_master": False,
        },
        {
            "stem": "丁",
            "element": "火",
            "weight": 0.3,
            "supports_day_master": False,
        },
        {
            "stem": "乙",
            "element": "木",
            "weight": 0.1,
            "supports_day_master": True,
        },
    ]

    assert (
        result["method"]
        == "weighted_month_command_v1"
    )

    assert (
        result["status"]
        == "provisional_weighted_month_command"
    )


def test_water_day_master_in_hai_month():
    month_pillar = {
        "branch": "亥",
        "hidden_stems": [
            "壬",
            "甲",
        ],
    }

    result = (
        calculate_weighted_month_command(
            "癸",
            month_pillar,
        )
    )

    assert result["supporting_score"] == 0.7
    assert result["draining_score"] == 0.3
    assert result["supporting_ratio"] == 70.0
    assert result["draining_ratio"] == 30.0
