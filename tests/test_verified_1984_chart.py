"""
tests/test_verified_1984_chart.py

1984年7月10日 22:45
愛知県
男性

実物の四柱推命鑑定書を基準にした
ゴールデンチャート回帰テスト。

目的
----
この命式を、八雲四柱推命エンジンの
基準命式 No.1 として固定する。

最重要ゴールデンデータ
----------------------
年柱：甲子
月柱：辛未
日柱：乙巳
時柱：丁亥

日主：乙

天干通変星
------------
年干 甲：劫財
月干 辛：偏官
日干 乙：日主
時干 丁：食神

鑑定書に記載された参考値
--------------------------
自我の強弱：中和
格局：食神格

五行力量：
木 26
火 18
土 28
金 14
水 14

大運：
0歳   辛未
9歳   壬申
19歳  癸酉
29歳  甲戌
39歳  乙亥
49歳  丙子
59歳  丁丑
69歳  戊寅
79歳  己卯
89歳  庚辰

注意
----
格局・五行力量・用神などは、
現在の八雲エンジンと鑑定書で
計算方式がまだ完全一致していない。

そのため、四柱・日主・通変星など
暦計算の基礎部分は通常テストとして固定し、
高度判定は段階的に一致させる。
"""

from datetime import datetime

import pytest

from api.models import ChartRequest
from engine.chart import calculate_chart


# =========================================================
# Golden data
# =========================================================


BIRTH_DATE = "1984-07-10"
BIRTH_TIME = "22:45"
BIRTH_PLACE = "愛知県"
GENDER = "male"


EXPECTED_PILLARS = {
    "year": "甲子",
    "month": "辛未",
    "day": "乙巳",
    "hour": "丁亥",
}


EXPECTED_STEMS = {
    "year": "甲",
    "month": "辛",
    "day": "乙",
    "hour": "丁",
}


EXPECTED_BRANCHES = {
    "year": "子",
    "month": "未",
    "day": "巳",
    "hour": "亥",
}


EXPECTED_STEM_TEN_GODS = {
    "year": "劫財",
    "month": "偏官",
    "day": None,
    "hour": "食神",
}


EXPECTED_DAY_MASTER = "乙"


EXPECTED_FIVE_ELEMENTS = {
    "木": 26,
    "火": 18,
    "土": 28,
    "金": 14,
    "水": 14,
}


EXPECTED_STRENGTH = "中和"


EXPECTED_PATTERN = "食神格"


EXPECTED_LUCK_SEQUENCE = [
    "壬申",
    "癸酉",
    "甲戌",
    "乙亥",
    "丙子",
    "丁丑",
    "戊寅",
    "己卯",
    "庚辰",
]


EXPECTED_DOCUMENT_LUCK_TABLE = [
    {
        "age": 0,
        "ganzhi": "辛未",
    },
    {
        "age": 9,
        "ganzhi": "壬申",
    },
    {
        "age": 19,
        "ganzhi": "癸酉",
    },
    {
        "age": 29,
        "ganzhi": "甲戌",
    },
    {
        "age": 39,
        "ganzhi": "乙亥",
    },
    {
        "age": 49,
        "ganzhi": "丙子",
    },
    {
        "age": 59,
        "ganzhi": "丁丑",
    },
    {
        "age": 69,
        "ganzhi": "戊寅",
    },
    {
        "age": 79,
        "ganzhi": "己卯",
    },
    {
        "age": 89,
        "ganzhi": "庚辰",
    },
]


# =========================================================
# Helpers
# =========================================================


def make_request() -> ChartRequest:
    """
    基準命式用のリクエストを生成する。
    """

    return ChartRequest(
        birth_date=BIRTH_DATE,
        birth_time=BIRTH_TIME,
        birth_place=BIRTH_PLACE,
        gender=GENDER,
    )


def calculate_verified_chart():
    """
    基準命式を計算する。
    """

    request = make_request()

    return calculate_chart(
        request
    )


def get_chart(result):
    """
    result["chart"] を安全に取得する。
    """

    assert isinstance(
        result,
        dict,
    )

    assert "chart" in result

    chart = result[
        "chart"
    ]

    assert isinstance(
        chart,
        dict,
    )

    return chart


# =========================================================
# Request / integration
# =========================================================


def test_verified_1984_chart_returns_dict():
    result = (
        calculate_verified_chart()
    )

    assert isinstance(
        result,
        dict,
    )


def test_verified_1984_chart_has_chart():
    result = (
        calculate_verified_chart()
    )

    assert "chart" in result


def test_verified_1984_chart_has_four_pillars():
    result = (
        calculate_verified_chart()
    )

    chart = get_chart(
        result
    )

    assert {
        "year",
        "month",
        "day",
        "hour",
    }.issubset(
        chart.keys()
    )


# =========================================================
# Four pillars
# =========================================================


@pytest.mark.parametrize(
    (
        "position",
        "expected",
    ),
    EXPECTED_PILLARS.items(),
)
def test_verified_1984_pillars(
    position,
    expected,
):
    """
    鑑定書の四柱を絶対基準として固定する。
    """

    result = (
        calculate_verified_chart()
    )

    chart = get_chart(
        result
    )

    assert (
        chart[
            position
        ][
            "pillar"
        ]
        == expected
    )


def test_verified_1984_year_pillar():
    result = (
        calculate_verified_chart()
    )

    assert (
        result[
            "chart"
        ][
            "year"
        ][
            "pillar"
        ]
        == "甲子"
    )


def test_verified_1984_month_pillar():
    result = (
        calculate_verified_chart()
    )

    assert (
        result[
            "chart"
        ][
            "month"
        ][
            "pillar"
        ]
        == "辛未"
    )


def test_verified_1984_day_pillar():
    """
    最重要回帰テスト。

    1984年7月10日は乙巳日。
    """

    result = (
        calculate_verified_chart()
    )

    assert (
        result[
            "chart"
        ][
            "day"
        ][
            "pillar"
        ]
        == "乙巳"
    )


def test_verified_1984_hour_pillar():
    """
    乙日・亥時なので丁亥。
    """

    result = (
        calculate_verified_chart()
    )

    assert (
        result[
            "chart"
        ][
            "hour"
        ][
            "pillar"
        ]
        == "丁亥"
    )


# =========================================================
# Stem / branch
# =========================================================


@pytest.mark.parametrize(
    (
        "position",
        "expected_stem",
    ),
    EXPECTED_STEMS.items(),
)
def test_verified_1984_stems(
    position,
    expected_stem,
):
    result = (
        calculate_verified_chart()
    )

    chart = get_chart(
        result
    )

    assert (
        chart[
            position
        ][
            "stem"
        ]
        == expected_stem
    )


@pytest.mark.parametrize(
    (
        "position",
        "expected_branch",
    ),
    EXPECTED_BRANCHES.items(),
)
def test_verified_1984_branches(
    position,
    expected_branch,
):
    result = (
        calculate_verified_chart()
    )

    chart = get_chart(
        result
    )

    assert (
        chart[
            position
        ][
            "branch"
        ]
        == expected_branch
    )


# =========================================================
# Day master
# =========================================================


def test_verified_1984_day_master_is_otsu():
    """
    日主は乙木。
    """

    result = (
        calculate_verified_chart()
    )

    chart = get_chart(
        result
    )

    assert (
        chart[
            "day"
        ][
            "stem"
        ]
        == EXPECTED_DAY_MASTER
    )


# =========================================================
# Heavenly-stem ten gods
# =========================================================


@pytest.mark.parametrize(
    (
        "position",
        "expected",
    ),
    EXPECTED_STEM_TEN_GODS.items(),
)
def test_verified_1984_stem_ten_gods(
    position,
    expected,
):
    """
    鑑定書記載の天干通変星を確認する。

    乙日主：
        甲 = 劫財
        辛 = 偏官
        乙 = 日主
        丁 = 食神
    """

    result = (
        calculate_verified_chart()
    )

    chart = get_chart(
        result
    )

    assert (
        chart[
            position
        ][
            "stem_ten_god"
        ]
        == expected
    )


# =========================================================
# Consistency
# =========================================================


def test_verified_1984_pillar_matches_stem_branch():
    """
    pillar文字列とstem/branchが一致すること。
    """

    result = (
        calculate_verified_chart()
    )

    chart = get_chart(
        result
    )

    for position in (
        "year",
        "month",
        "day",
        "hour",
    ):
        pillar = (
            chart[
                position
            ][
                "pillar"
            ]
        )

        stem = (
            chart[
                position
            ][
                "stem"
            ]
        )

        branch = (
            chart[
                position
            ][
                "branch"
            ]
        )

        assert (
            pillar
            == stem + branch
        )


def test_verified_1984_day_master_drives_ten_gods():
    """
    日主が乙であることを前提に、
    天干通変星の整合性を確認する。
    """

    result = (
        calculate_verified_chart()
    )

    chart = get_chart(
        result
    )

    assert (
        chart[
            "day"
        ][
            "stem"
        ]
        == "乙"
    )

    assert (
        chart[
            "year"
        ][
            "stem_ten_god"
        ]
        == "劫財"
    )

    assert (
        chart[
            "month"
        ][
            "stem_ten_god"
        ]
        == "偏官"
    )

    assert (
        chart[
            "hour"
        ][
            "stem_ten_god"
        ]
        == "食神"
    )


# =========================================================
# Luck pillars
# =========================================================


def test_verified_1984_has_luck_pillars():
    result = (
        calculate_verified_chart()
    )

    assert (
        "luck_pillars"
        in result
    )

    assert isinstance(
        result[
            "luck_pillars"
        ],
        dict,
    )


def test_verified_1984_luck_direction_forward():
    """
    甲年男性は順行。
    """

    result = (
        calculate_verified_chart()
    )

    luck = result[
        "luck_pillars"
    ]

    assert (
        luck[
            "direction"
        ]
        == "forward"
    )


def test_verified_1984_luck_direction_japanese():
    result = (
        calculate_verified_chart()
    )

    luck = result[
        "luck_pillars"
    ]

    assert (
        luck[
            "direction_japanese"
        ]
        == "順行"
    )


def test_verified_1984_luck_sequence():
    """
    月柱辛未から順行。

    大運：
        壬申
        癸酉
        甲戌
        乙亥
        丙子
        丁丑
        戊寅
        己卯
        庚辰
    """

    result = (
        calculate_verified_chart()
    )

    luck = result[
        "luck_pillars"
    ]

    pillars = luck[
        "pillars"
    ]

    actual = [
        item[
            "ganzhi"
        ]
        for item in pillars[
            :len(
                EXPECTED_LUCK_SEQUENCE
            )
        ]
    ]

    assert (
        actual
        == EXPECTED_LUCK_SEQUENCE
    )


def test_verified_1984_luck_has_at_least_nine_pillars():
    result = (
        calculate_verified_chart()
    )

    pillars = (
        result[
            "luck_pillars"
        ][
            "pillars"
        ]
    )

    assert (
        len(
            pillars
        )
        >= 9
    )


# =========================================================
# Golden-document metadata
#
# 以下は鑑定書の値をコード上にも記録する。
# 現在の八雲エンジンと計算法が異なる項目は
# まだ通常CIの合否条件にはしない。
# =========================================================


def test_verified_1984_document_five_elements_total_is_100():
    """
    鑑定書の五行力量。

        木26
        火18
        土28
        金14
        水14

    合計100。
    """

    assert (
        sum(
            EXPECTED_FIVE_ELEMENTS.values()
        )
        == 100
    )


def test_verified_1984_document_luck_table():
    """
    鑑定書に記載された大運表を
    ゴールデンデータとして保持する。
    """

    assert (
        EXPECTED_DOCUMENT_LUCK_TABLE[
            0
        ]
        == {
            "age": 0,
            "ganzhi": "辛未",
        }
    )

    assert (
        EXPECTED_DOCUMENT_LUCK_TABLE[
            3
        ]
        == {
            "age": 29,
            "ganzhi": "甲戌",
        }
    )

    assert (
        EXPECTED_DOCUMENT_LUCK_TABLE[
            4
        ]
        == {
            "age": 39,
            "ganzhi": "乙亥",
        }
    )

    assert (
        EXPECTED_DOCUMENT_LUCK_TABLE[
            5
        ]
        == {
            "age": 49,
            "ganzhi": "丙子",
        }
    )

    assert (
        EXPECTED_DOCUMENT_LUCK_TABLE[
            -1
        ]
        == {
            "age": 89,
            "ganzhi": "庚辰",
        }
    )


# =========================================================
# Future contract: strength
# =========================================================


@pytest.mark.xfail(
    reason=(
        "鑑定書では中和。"
        "八雲エンジンの身強身弱ロジックを"
        "鑑定書方式へ精密化するまでの将来契約。"
    ),
    strict=False,
)
def test_verified_1984_future_strength_matches_document():
    """
    鑑定書：
        自我の強弱 = 中和
    """

    result = (
        calculate_verified_chart()
    )

    judgment = result[
        "final_strength_judgment"
    ]

    assert (
        judgment[
            "label"
        ]
        == EXPECTED_STRENGTH
    )


# =========================================================
# Future contract: pattern
# =========================================================


@pytest.mark.xfail(
    reason=(
        "鑑定書では食神格。"
        "現在の格局ロジックとは判定方式が異なるため、"
        "格局精密化フェーズで一致させる。"
    ),
    strict=False,
)
def test_verified_1984_future_pattern_matches_document():
    """
    鑑定書：
        格局 = 食神格
    """

    result = (
        calculate_verified_chart()
    )

    judgment = result[
        "pattern_judgment"
    ]

    assert (
        judgment[
            "primary_pattern"
        ]
        == EXPECTED_PATTERN
    )


# =========================================================
# Future contract: five-element quantities
# =========================================================


@pytest.mark.xfail(
    reason=(
        "鑑定書の五行力量26/18/28/14/14と"
        "現在の八雲エンジンでは算出方式が異なるため、"
        "五行力量ロジック精密化時の将来契約。"
    ),
    strict=False,
)
def test_verified_1984_future_five_elements_match_document():
    """
    鑑定書：

        木 = 26
        火 = 18
        土 = 28
        金 = 14
        水 = 14

    API内部の名称・構造が確定後、
    通常テストへ昇格させる。
    """

    result = (
        calculate_verified_chart()
    )

    # -----------------------------------------------------
    # 現行APIで five_elements が存在する場合を想定。
    #
    # API構造を変更した場合は、
    # 五行力量モジュール確定時にここを合わせる。
    # -----------------------------------------------------

    five_elements = result[
        "five_elements"
    ]

    actual = {
        "木": five_elements[
            "木"
        ],
        "火": five_elements[
            "火"
        ],
        "土": five_elements[
            "土"
        ],
        "金": five_elements[
            "金"
        ],
        "水": five_elements[
            "水"
        ],
    }

    assert (
        actual
        == EXPECTED_FIVE_ELEMENTS
    )


# =========================================================
# Final golden assertion
# =========================================================


def test_verified_1984_golden_chart():
    """
    このファイルで最重要のテスト。

    どれだけ後段ロジックを変更しても、
    基本命式

        甲子
        辛未
        乙巳
        丁亥

    は絶対に変更されてはいけない。
    """

    result = (
        calculate_verified_chart()
    )

    chart = get_chart(
        result
    )

    actual = {
        "year": (
            chart[
                "year"
            ][
                "pillar"
            ]
        ),
        "month": (
            chart[
                "month"
            ][
                "pillar"
            ]
        ),
        "day": (
            chart[
                "day"
            ][
                "pillar"
            ]
        ),
        "hour": (
            chart[
                "hour"
            ][
                "pillar"
            ]
        ),
    }

    assert (
        actual
        == EXPECTED_PILLARS
    )
