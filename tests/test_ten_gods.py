import pytest

from engine.ten_gods import (
    calculate_ten_god,
    get_element,
    get_element_relationship,
    get_yin_yang,
)


def test_stem_element():
    assert get_element("甲") == "木"
    assert get_element("丁") == "火"
    assert get_element("己") == "土"
    assert get_element("辛") == "金"
    assert get_element("癸") == "水"


def test_stem_yin_yang():
    assert get_yin_yang("甲") == "陽"
    assert get_yin_yang("乙") == "陰"
    assert get_yin_yang("壬") == "陽"
    assert get_yin_yang("癸") == "陰"


def test_element_relationship_for_yi_wood():
    assert get_element_relationship(
        "乙",
        "甲",
    ) == "same"

    assert get_element_relationship(
        "乙",
        "丁",
    ) == "output"

    assert get_element_relationship(
        "乙",
        "己",
    ) == "wealth"

    assert get_element_relationship(
        "乙",
        "辛",
    ) == "officer"

    assert get_element_relationship(
        "乙",
        "癸",
    ) == "resource"


def test_all_ten_gods_for_yi_day_master():
    expected = {
        "甲": "劫財",
        "乙": "比肩",
        "丙": "傷官",
        "丁": "食神",
        "戊": "正財",
        "己": "偏財",
        "庚": "正官",
        "辛": "偏官",
        "壬": "印綬",
        "癸": "偏印",
    }

    for target_stem, ten_god in expected.items():
        assert calculate_ten_god(
            "乙",
            target_stem,
        ) == ten_god


def test_verified_chart_ten_gods():
    # 1985年7月17日
    # 年柱：乙丑
    assert calculate_ten_god(
        "乙",
        "乙",
    ) == "比肩"

    assert calculate_ten_god(
        "乙",
        "己",
    ) == "偏財"

    # 月柱：癸未
    assert calculate_ten_god(
        "乙",
        "癸",
    ) == "偏印"

    # 日柱：乙巳
    assert calculate_ten_god(
        "乙",
        "丙",
    ) == "傷官"

    # 時柱：丁亥
    assert calculate_ten_god(
        "乙",
        "丁",
    ) == "食神"

    assert calculate_ten_god(
        "乙",
        "壬",
    ) == "印綬"


def test_invalid_stem():
    with pytest.raises(ValueError):
        calculate_ten_god(
            "乙",
            "無",
        )

    with pytest.raises(ValueError):
        calculate_ten_god(
            "無",
            "甲",
        )
