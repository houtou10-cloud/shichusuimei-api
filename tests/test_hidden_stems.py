import pytest

from engine.hidden_stems import (
    build_hidden_stem_data,
    get_hidden_stems,
    get_main_hidden_stem,
)


def test_get_hidden_stems_single():
    assert get_hidden_stems("子") == ["癸"]
    assert get_hidden_stems("卯") == ["乙"]
    assert get_hidden_stems("酉") == ["辛"]


def test_get_hidden_stems_multiple():
    assert get_hidden_stems("丑") == [
        "己",
        "癸",
        "辛",
    ]

    assert get_hidden_stems("未") == [
        "己",
        "丁",
        "乙",
    ]

    assert get_hidden_stems("巳") == [
        "丙",
        "戊",
        "庚",
    ]

    assert get_hidden_stems("亥") == [
        "壬",
        "甲",
    ]


def test_get_main_hidden_stem():
    assert get_main_hidden_stem("子") == "癸"
    assert get_main_hidden_stem("丑") == "己"
    assert get_main_hidden_stem("未") == "己"
    assert get_main_hidden_stem("巳") == "丙"
    assert get_main_hidden_stem("亥") == "壬"


def test_build_hidden_stem_data():
    result = build_hidden_stem_data("未")

    assert result == {
        "branch": "未",
        "hidden_stems": [
            "己",
            "丁",
            "乙",
        ],
        "main_hidden_stem": "己",
    }


def test_hidden_stems_returns_copy():
    first = get_hidden_stems("未")
    first.append("甲")

    second = get_hidden_stems("未")

    assert second == [
        "己",
        "丁",
        "乙",
    ]


def test_invalid_branch():
    with pytest.raises(ValueError):
        get_hidden_stems("無")

    with pytest.raises(ValueError):
        get_main_hidden_stem("無")
