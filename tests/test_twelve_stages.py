import pytest

from engine.twelve_stages import (
    calculate_twelve_stage,
)


def test_verified_stages_for_yi_day_master():
    assert calculate_twelve_stage(
        "乙",
        "丑",
    ) == "衰"

    assert calculate_twelve_stage(
        "乙",
        "未",
    ) == "養"

    assert calculate_twelve_stage(
        "乙",
        "巳",
    ) == "沐浴"

    assert calculate_twelve_stage(
        "乙",
        "亥",
    ) == "死"


def test_full_cycle_for_yi_day_master():
    expected = {
        "子": "病",
        "丑": "衰",
        "寅": "帝旺",
        "卯": "建禄",
        "辰": "冠帯",
        "巳": "沐浴",
        "午": "長生",
        "未": "養",
        "申": "胎",
        "酉": "絶",
        "戌": "墓",
        "亥": "死",
    }

    for branch, stage in expected.items():
        assert calculate_twelve_stage(
            "乙",
            branch,
        ) == stage


def test_all_stems_have_all_branches():
    stems = [
        "甲",
        "乙",
        "丙",
        "丁",
        "戊",
        "己",
        "庚",
        "辛",
        "壬",
        "癸",
    ]

    branches = [
        "子",
        "丑",
        "寅",
        "卯",
        "辰",
        "巳",
        "午",
        "未",
        "申",
        "酉",
        "戌",
        "亥",
    ]

    for stem in stems:
        results = [
            calculate_twelve_stage(
                stem,
                branch,
            )
            for branch in branches
        ]

        assert len(results) == 12
        assert len(set(results)) == 12


def test_invalid_values():
    with pytest.raises(ValueError):
        calculate_twelve_stage(
            "無",
            "子",
        )

    with pytest.raises(ValueError):
        calculate_twelve_stage(
            "乙",
            "無",
        )
