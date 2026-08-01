import pytest

from engine.hidden_stem_weights import (
    get_hidden_stem_weights,
)


def test_single_hidden_stem():
    result = get_hidden_stem_weights(
        ["癸"]
    )

    assert result == [
        {
            "stem": "癸",
            "weight": 1.0,
            "rank": 1,
        }
    ]


def test_two_hidden_stems():
    result = get_hidden_stem_weights(
        [
            "壬",
            "甲",
        ]
    )

    assert result == [
        {
            "stem": "壬",
            "weight": 0.7,
            "rank": 1,
        },
        {
            "stem": "甲",
            "weight": 0.3,
            "rank": 2,
        },
    ]


def test_three_hidden_stems():
    result = get_hidden_stem_weights(
        [
            "己",
            "癸",
            "辛",
        ]
    )

    assert result == [
        {
            "stem": "己",
            "weight": 0.6,
            "rank": 1,
        },
        {
            "stem": "癸",
            "weight": 0.3,
            "rank": 2,
        },
        {
            "stem": "辛",
            "weight": 0.1,
            "rank": 3,
        },
    ]


def test_weights_total_one():
    for hidden_stems in [
        ["癸"],
        ["壬", "甲"],
        ["己", "癸", "辛"],
    ]:
        result = get_hidden_stem_weights(
            hidden_stems
        )

        total = sum(
            item["weight"]
            for item in result
        )

        assert round(total, 10) == 1.0


def test_invalid_hidden_stems():
    with pytest.raises(TypeError):
        get_hidden_stem_weights(
            "己"
        )

    with pytest.raises(ValueError):
        get_hidden_stem_weights(
            []
        )

    with pytest.raises(ValueError):
        get_hidden_stem_weights(
            [
                "甲",
                "乙",
                "丙",
                "丁",
            ]
        )
