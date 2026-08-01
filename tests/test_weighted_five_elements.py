from engine.weighted_five_elements import (
    calculate_weighted_five_elements,
    calculate_weighted_pillar_elements,
)


def test_weighted_single_pillar():
    pillar = {
        "stem": "乙",
        "branch": "丑",
        "hidden_stems": [
            "己",
            "癸",
            "辛",
        ],
    }

    result = (
        calculate_weighted_pillar_elements(
            pillar
        )
    )

    assert result == {
        "木": 1.0,
        "火": 0.0,
        "土": 0.6,
        "金": 0.1,
        "水": 0.3,
    }


def test_verified_weighted_chart():
    chart = {
        "year": {
            "stem": "乙",
            "branch": "丑",
            "hidden_stems": [
                "己",
                "癸",
                "辛",
            ],
        },
        "month": {
            "stem": "癸",
            "branch": "未",
            "hidden_stems": [
                "己",
                "丁",
                "乙",
            ],
        },
        "day": {
            "stem": "乙",
            "branch": "巳",
            "hidden_stems": [
                "丙",
                "戊",
                "庚",
            ],
        },
        "hour": {
            "stem": "丁",
            "branch": "亥",
            "hidden_stems": [
                "壬",
                "甲",
            ],
        },
    }

    result = (
        calculate_weighted_five_elements(
            chart
        )
    )

    assert result["scores"] == {
        "木": 2.4,
        "火": 1.9,
        "土": 1.5,
        "金": 0.2,
        "水": 2.0,
    }

    assert result["percentages"] == {
        "木": 30.0,
        "火": 23.75,
        "土": 18.75,
        "金": 2.5,
        "水": 25.0,
    }

    assert result["total"] == 8.0
    assert (
        result["method"]
        == "weighted_hidden_stems_v1"
    )
