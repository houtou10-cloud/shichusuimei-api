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


EXPECTED_TEN_GOD_MATRIX = {
    "甲": {"甲":"比肩","乙":"劫財","丙":"食神","丁":"傷官","戊":"偏財","己":"正財","庚":"偏官","辛":"正官","壬":"偏印","癸":"印綬"},
    "乙": {"甲":"劫財","乙":"比肩","丙":"傷官","丁":"食神","戊":"正財","己":"偏財","庚":"正官","辛":"偏官","壬":"印綬","癸":"偏印"},
    "丙": {"甲":"偏印","乙":"印綬","丙":"比肩","丁":"劫財","戊":"食神","己":"傷官","庚":"偏財","辛":"正財","壬":"偏官","癸":"正官"},
    "丁": {"甲":"印綬","乙":"偏印","丙":"劫財","丁":"比肩","戊":"傷官","己":"食神","庚":"正財","辛":"偏財","壬":"正官","癸":"偏官"},
    "戊": {"甲":"偏官","乙":"正官","丙":"偏印","丁":"印綬","戊":"比肩","己":"劫財","庚":"食神","辛":"傷官","壬":"偏財","癸":"正財"},
    "己": {"甲":"正官","乙":"偏官","丙":"印綬","丁":"偏印","戊":"劫財","己":"比肩","庚":"傷官","辛":"食神","壬":"正財","癸":"偏財"},
    "庚": {"甲":"偏財","乙":"正財","丙":"偏官","丁":"正官","戊":"偏印","己":"印綬","庚":"比肩","辛":"劫財","壬":"食神","癸":"傷官"},
    "辛": {"甲":"正財","乙":"偏財","丙":"正官","丁":"偏官","戊":"印綬","己":"偏印","庚":"劫財","辛":"比肩","壬":"傷官","癸":"食神"},
    "壬": {"甲":"食神","乙":"傷官","丙":"偏財","丁":"正財","戊":"偏官","己":"正官","庚":"偏印","辛":"印綬","壬":"比肩","癸":"劫財"},
    "癸": {"甲":"傷官","乙":"食神","丙":"正財","丁":"偏財","戊":"正官","己":"偏官","庚":"印綬","辛":"偏印","壬":"劫財","癸":"比肩"},
}


def test_ten_god_full_rule_matrix():
    checked = 0

    for day_stem, expected_by_target in EXPECTED_TEN_GOD_MATRIX.items():
        for target_stem, expected_ten_god in expected_by_target.items():
            assert calculate_ten_god(
                day_stem,
                target_stem,
            ) == expected_ten_god
            checked += 1

    assert checked == 100
