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


EXPECTED_TWELVE_STAGE_MATRIX = {
    "甲": {"子":"沐浴","丑":"冠帯","寅":"建禄","卯":"帝旺","辰":"衰","巳":"病","午":"死","未":"墓","申":"絶","酉":"胎","戌":"養","亥":"長生"},
    "乙": {"子":"病","丑":"衰","寅":"帝旺","卯":"建禄","辰":"冠帯","巳":"沐浴","午":"長生","未":"養","申":"胎","酉":"絶","戌":"墓","亥":"死"},
    "丙": {"子":"胎","丑":"養","寅":"長生","卯":"沐浴","辰":"冠帯","巳":"建禄","午":"帝旺","未":"衰","申":"病","酉":"死","戌":"墓","亥":"絶"},
    "丁": {"子":"絶","丑":"墓","寅":"死","卯":"病","辰":"衰","巳":"帝旺","午":"建禄","未":"冠帯","申":"沐浴","酉":"長生","戌":"養","亥":"胎"},
    "戊": {"子":"胎","丑":"養","寅":"長生","卯":"沐浴","辰":"冠帯","巳":"建禄","午":"帝旺","未":"衰","申":"病","酉":"死","戌":"墓","亥":"絶"},
    "己": {"子":"絶","丑":"墓","寅":"死","卯":"病","辰":"衰","巳":"帝旺","午":"建禄","未":"冠帯","申":"沐浴","酉":"長生","戌":"養","亥":"胎"},
    "庚": {"子":"死","丑":"墓","寅":"絶","卯":"胎","辰":"養","巳":"長生","午":"沐浴","未":"冠帯","申":"建禄","酉":"帝旺","戌":"衰","亥":"病"},
    "辛": {"子":"長生","丑":"養","寅":"胎","卯":"絶","辰":"墓","巳":"死","午":"病","未":"衰","申":"帝旺","酉":"建禄","戌":"冠帯","亥":"沐浴"},
    "壬": {"子":"帝旺","丑":"衰","寅":"病","卯":"死","辰":"墓","巳":"絶","午":"胎","未":"養","申":"長生","酉":"沐浴","戌":"冠帯","亥":"建禄"},
    "癸": {"子":"建禄","丑":"冠帯","寅":"沐浴","卯":"長生","辰":"養","巳":"胎","午":"絶","未":"墓","申":"死","酉":"病","戌":"衰","亥":"帝旺"},
}


def test_twelve_stage_full_rule_matrix():
    checked = 0

    for stem, expected_by_branch in EXPECTED_TWELVE_STAGE_MATRIX.items():
        for branch, expected_stage in expected_by_branch.items():
            assert calculate_twelve_stage(
                stem,
                branch,
            ) == expected_stage
            checked += 1

    assert checked == 120
