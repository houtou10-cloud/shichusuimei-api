from engine.weighted_root_strength import (
    calculate_weighted_roots,
)


def test_verified_weighted_roots():
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

    result = calculate_weighted_roots(
        "乙",
        chart,
    )

    assert result["has_root"] is True
    assert result["root_count"] == 2
    assert result["total_root_score"] == 0.45

    assert result["root_positions"] == [
        "month",
        "hour",
    ]

    assert result["roots"] == [
        {
            "position": "month",
            "branch": "未",
            "stem": "乙",
            "hidden_stem_rank": 3,
            "position_weight": 1.5,
            "hidden_stem_weight": 0.1,
            "root_score": 0.15,
        },
        {
            "position": "hour",
            "branch": "亥",
            "stem": "甲",
            "hidden_stem_rank": 2,
            "position_weight": 1.0,
            "hidden_stem_weight": 0.3,
            "root_score": 0.3,
        },
    ]


def test_no_weighted_roots():
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

    result = calculate_weighted_roots(
        "乙",
        chart,
    )

    assert result["has_root"] is False
    assert result["root_count"] == 0
    assert result["total_root_score"] == 0.0
    assert result["roots"] == []
