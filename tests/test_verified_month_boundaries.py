"""
tests/test_verified_month_boundaries.py

四柱推命 月柱・節入り境界
ゴールデン回帰テスト v1

目的
----
engine/month.py と
engine/solar_terms.py の連携について、

・12節による月支切替
・節入り1秒前
・節入りちょうど
・節入り1秒後
・五虎遁による月干
・月柱全体
・立春で年干も切り替わるケース
・小寒の年跨ぎケース

を検証する。

重要
----
四柱推命の月柱は、
グレゴリオ暦の毎月1日ではなく、

小寒
立春
啓蟄
清明
立夏
芒種
小暑
立秋
白露
寒露
立冬
大雪

の12節の実際の節入り日時によって
切り替える。

境界ルール
----------
節入り1秒前:
    旧月

節入りちょうど:
    新月

節入り1秒後:
    新月

月干は五虎遁によって
年干と月支から決定する。

Version
-------
verified_month_boundaries_v1
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from engine.month import (
    calculate_month_branch,
    calculate_month_pillar,
    calculate_month_stem,
)

from engine.solar_terms import (
    get_current_solar_term,
    get_month_branch_by_datetime,
    get_month_number_by_datetime,
    get_solar_term_datetime,
)


# ============================================================
# Constants
# ============================================================


TEST_YEAR = 2026


# ============================================================
# 2026 month-boundary golden data
# ============================================================
#
# 2026年は立春から丙午年。
#
# 五虎遁:
#
# 丙辛歳首尋庚
#
# よって丙年の寅月は庚寅から始まる。
#
# ただし2026年1月の小寒時点では
# まだ立春前なので乙巳年。
#
# 乙年:
#
# 寅 戊寅
# 卯 己卯
# 辰 庚辰
# 巳 辛巳
# 午 壬午
# 未 癸未
# 申 甲申
# 酉 乙酉
# 戌 丙戌
# 亥 丁亥
# 子 戊子
# 丑 己丑
#
# 丙年:
#
# 寅 庚寅
# 卯 辛卯
# 辰 壬辰
# 巳 癸巳
# 午 甲午
# 未 乙未
# 申 丙申
# 酉 丁酉
# 戌 戊戌
# 亥 己亥
# 子 庚子
# 丑 辛丑
#
# ============================================================


MONTH_BOUNDARIES_2026 = [
    {
        "term": "小寒",
        "year_stem": "乙",
        "before_branch": "子",
        "after_branch": "丑",
        "before_pillar": "戊子",
        "after_pillar": "己丑",
        "month_number": 12,
    },
    {
        "term": "立春",
        "year_stem": "丙",
        "before_branch": "丑",
        "after_branch": "寅",
        # 立春直前は乙巳年の丑月。
        # 立春から丙午年の寅月。
        "before_pillar": "己丑",
        "after_pillar": "庚寅",
        "month_number": 1,
    },
    {
        "term": "啓蟄",
        "year_stem": "丙",
        "before_branch": "寅",
        "after_branch": "卯",
        "before_pillar": "庚寅",
        "after_pillar": "辛卯",
        "month_number": 2,
    },
    {
        "term": "清明",
        "year_stem": "丙",
        "before_branch": "卯",
        "after_branch": "辰",
        "before_pillar": "辛卯",
        "after_pillar": "壬辰",
        "month_number": 3,
    },
    {
        "term": "立夏",
        "year_stem": "丙",
        "before_branch": "辰",
        "after_branch": "巳",
        "before_pillar": "壬辰",
        "after_pillar": "癸巳",
        "month_number": 4,
    },
    {
        "term": "芒種",
        "year_stem": "丙",
        "before_branch": "巳",
        "after_branch": "午",
        "before_pillar": "癸巳",
        "after_pillar": "甲午",
        "month_number": 5,
    },
    {
        "term": "小暑",
        "year_stem": "丙",
        "before_branch": "午",
        "after_branch": "未",
        "before_pillar": "甲午",
        "after_pillar": "乙未",
        "month_number": 6,
    },
    {
        "term": "立秋",
        "year_stem": "丙",
        "before_branch": "未",
        "after_branch": "申",
        "before_pillar": "乙未",
        "after_pillar": "丙申",
        "month_number": 7,
    },
    {
        "term": "白露",
        "year_stem": "丙",
        "before_branch": "申",
        "after_branch": "酉",
        "before_pillar": "丙申",
        "after_pillar": "丁酉",
        "month_number": 8,
    },
    {
        "term": "寒露",
        "year_stem": "丙",
        "before_branch": "酉",
        "after_branch": "戌",
        "before_pillar": "丁酉",
        "after_pillar": "戊戌",
        "month_number": 9,
    },
    {
        "term": "立冬",
        "year_stem": "丙",
        "before_branch": "戌",
        "after_branch": "亥",
        "before_pillar": "戊戌",
        "after_pillar": "己亥",
        "month_number": 10,
    },
    {
        "term": "大雪",
        "year_stem": "丙",
        "before_branch": "亥",
        "after_branch": "子",
        "before_pillar": "己亥",
        "after_pillar": "庚子",
        "month_number": 11,
    },
]


# ============================================================
# Helper
# ============================================================


def get_boundary(
    term_name: str,
) -> datetime:
    """
    solar_termsエンジンから
    2026年の実際の節入り日時を取得する。
    """

    result = get_solar_term_datetime(
        TEST_YEAR,
        term_name,
    )

    assert isinstance(
        result,
        datetime,
    )

    return result


# ============================================================
# Solar-term availability
# ============================================================


@pytest.mark.parametrize(
    "case",
    MONTH_BOUNDARIES_2026,
)
def test_all_month_boundaries_exist(
    case,
):
    """
    12節すべてについて
    節入り日時を取得できる。
    """

    boundary = get_boundary(
        case["term"]
    )

    assert boundary.year == TEST_YEAR


# ============================================================
# Solar-term order
# ============================================================


def test_month_boundaries_are_chronological():
    """
    2026年の12節が
    時系列順になっていることを確認する。
    """

    boundaries = [
        get_boundary(case["term"])
        for case
        in MONTH_BOUNDARIES_2026
    ]

    assert boundaries == sorted(
        boundaries
    )


# ============================================================
# Month branch
# ============================================================


@pytest.mark.parametrize(
    "case",
    MONTH_BOUNDARIES_2026,
)
def test_month_branch_one_second_before_boundary(
    case,
):
    """
    節入り1秒前は旧月支。
    """

    boundary = get_boundary(
        case["term"]
    )

    target = (
        boundary
        - timedelta(seconds=1)
    )

    result = calculate_month_branch(
        target
    )

    assert result == case[
        "before_branch"
    ]


@pytest.mark.parametrize(
    "case",
    MONTH_BOUNDARIES_2026,
)
def test_month_branch_exact_boundary(
    case,
):
    """
    節入りちょうどから新月支。
    """

    boundary = get_boundary(
        case["term"]
    )

    result = calculate_month_branch(
        boundary
    )

    assert result == case[
        "after_branch"
    ]


@pytest.mark.parametrize(
    "case",
    MONTH_BOUNDARIES_2026,
)
def test_month_branch_one_second_after_boundary(
    case,
):
    """
    節入り1秒後も新月支。
    """

    boundary = get_boundary(
        case["term"]
    )

    target = (
        boundary
        + timedelta(seconds=1)
    )

    result = calculate_month_branch(
        target
    )

    assert result == case[
        "after_branch"
    ]


# ============================================================
# solar_terms -> month branch
# ============================================================


@pytest.mark.parametrize(
    "case",
    MONTH_BOUNDARIES_2026,
)
def test_solar_terms_month_branch_before(
    case,
):
    """
    solar_terms側でも
    1秒前は旧月支。
    """

    boundary = get_boundary(
        case["term"]
    )

    result = (
        get_month_branch_by_datetime(
            boundary
            - timedelta(seconds=1)
        )
    )

    assert result == case[
        "before_branch"
    ]


@pytest.mark.parametrize(
    "case",
    MONTH_BOUNDARIES_2026,
)
def test_solar_terms_month_branch_exact(
    case,
):
    """
    solar_terms側でも
    節入りちょうどから新月支。
    """

    boundary = get_boundary(
        case["term"]
    )

    result = (
        get_month_branch_by_datetime(
            boundary
        )
    )

    assert result == case[
        "after_branch"
    ]


@pytest.mark.parametrize(
    "case",
    MONTH_BOUNDARIES_2026,
)
def test_solar_terms_month_branch_after(
    case,
):
    """
    solar_terms側でも
    1秒後は新月支。
    """

    boundary = get_boundary(
        case["term"]
    )

    result = (
        get_month_branch_by_datetime(
            boundary
            + timedelta(seconds=1)
        )
    )

    assert result == case[
        "after_branch"
    ]


# ============================================================
# Current solar term
# ============================================================


@pytest.mark.parametrize(
    "case",
    MONTH_BOUNDARIES_2026,
)
def test_current_solar_term_exact_boundary(
    case,
):
    """
    節入りちょうどでは、
    新しい節そのものがcurrentになる。
    """

    boundary = get_boundary(
        case["term"]
    )

    result = get_current_solar_term(
        boundary
    )

    assert result.name == case["term"]

    assert (
        result.month_branch
        == case["after_branch"]
    )


# ============================================================
# Month number
# ============================================================


@pytest.mark.parametrize(
    "case",
    MONTH_BOUNDARIES_2026,
)
def test_month_number_exact_boundary(
    case,
):
    """
    節入りちょうどの月番号を確認する。

    寅 = 1
    卯 = 2
    ...
    子 = 11
    丑 = 12
    """

    boundary = get_boundary(
        case["term"]
    )

    result = (
        get_month_number_by_datetime(
            boundary
        )
    )

    assert result == case[
        "month_number"
    ]


# ============================================================
# Five Tigers
# ============================================================


@pytest.mark.parametrize(
    (
        "year_stem,"
        "month_branch,"
        "expected_stem"
    ),
    [
        ("丙", "寅", "庚"),
        ("丙", "卯", "辛"),
        ("丙", "辰", "壬"),
        ("丙", "巳", "癸"),
        ("丙", "午", "甲"),
        ("丙", "未", "乙"),
        ("丙", "申", "丙"),
        ("丙", "酉", "丁"),
        ("丙", "戌", "戊"),
        ("丙", "亥", "己"),
        ("丙", "子", "庚"),
        ("丙", "丑", "辛"),
    ],
)
def test_five_tigers_2026(
    year_stem,
    month_branch,
    expected_stem,
):
    """
    丙年の五虎遁を検証する。
    """

    result = calculate_month_stem(
        year_stem,
        month_branch,
    )

    assert result == expected_stem


# ============================================================
# Full month pillar
# ============================================================


@pytest.mark.parametrize(
    "case",
    MONTH_BOUNDARIES_2026,
)
def test_month_pillar_exact_boundary(
    case,
):
    """
    節入りちょうどの月柱を確認する。
    """

    boundary = get_boundary(
        case["term"]
    )

    result = calculate_month_pillar(
        boundary,
        case["year_stem"],
    )

    assert result == case[
        "after_pillar"
    ]


@pytest.mark.parametrize(
    "case",
    [
        case
        for case
        in MONTH_BOUNDARIES_2026
        if case["term"] != "立春"
    ],
)
def test_month_pillar_one_second_before_boundary(
    case,
):
    """
    立春以外について、
    節入り1秒前は旧月柱。

    同一年干の中での
    月柱切替を検証する。
    """

    boundary = get_boundary(
        case["term"]
    )

    result = calculate_month_pillar(
        (
            boundary
            - timedelta(seconds=1)
        ),
        case["year_stem"],
    )

    assert result == case[
        "before_pillar"
    ]


@pytest.mark.parametrize(
    "case",
    MONTH_BOUNDARIES_2026,
)
def test_month_pillar_one_second_after_boundary(
    case,
):
    """
    節入り1秒後は新月柱。
    """

    boundary = get_boundary(
        case["term"]
    )

    result = calculate_month_pillar(
        (
            boundary
            + timedelta(seconds=1)
        ),
        case["year_stem"],
    )

    assert result == case[
        "after_pillar"
    ]


# ============================================================
# Lichun special boundary
# ============================================================


def test_lichun_month_pillar_one_second_before():
    """
    立春は月だけでなく年も切り替わる。

    2026年立春直前:
        乙巳年
        己丑月
    """

    boundary = get_boundary(
        "立春"
    )

    result = calculate_month_pillar(
        (
            boundary
            - timedelta(seconds=1)
        ),
        "乙",
    )

    assert result == "己丑"


def test_lichun_month_pillar_exact():
    """
    2026年立春ちょうど:

        丙午年
        庚寅月
    """

    boundary = get_boundary(
        "立春"
    )

    result = calculate_month_pillar(
        boundary,
        "丙",
    )

    assert result == "庚寅"


def test_lichun_month_pillar_one_second_after():
    """
    2026年立春1秒後:

        丙午年
        庚寅月
    """

    boundary = get_boundary(
        "立春"
    )

    result = calculate_month_pillar(
        (
            boundary
            + timedelta(seconds=1)
        ),
        "丙",
    )

    assert result == "庚寅"


# ============================================================
# Xiaohan year-crossing
# ============================================================


def test_xiaohan_before_boundary():
    """
    2026年小寒直前は
    乙巳年の子月。

    月柱:
        戊子
    """

    boundary = get_boundary(
        "小寒"
    )

    result = calculate_month_pillar(
        (
            boundary
            - timedelta(seconds=1)
        ),
        "乙",
    )

    assert result == "戊子"


def test_xiaohan_exact_boundary():
    """
    2026年小寒ちょうどから
    乙巳年の丑月。

    月柱:
        己丑
    """

    boundary = get_boundary(
        "小寒"
    )

    result = calculate_month_pillar(
        boundary,
        "乙",
    )

    assert result == "己丑"


# ============================================================
# Regression:
# calendar month must NOT control pillar
# ============================================================


def test_calendar_month_start_does_not_change_month_branch():
    """
    3月1日になっただけでは
    卯月へ切り替わらない。

    立春後・啓蟄前なので
    寅月のまま。
    """

    keichitsu = get_boundary(
        "啓蟄"
    )

    target = datetime(
        2026,
        3,
        1,
        12,
        0,
        0,
    )

    assert target < keichitsu

    assert (
        calculate_month_branch(
            target
        )
        == "寅"
    )


def test_calendar_month_start_does_not_change_month_pillar():
    """
    2026年3月1日は、
    暦上は3月でも
    啓蟄前なので庚寅月。
    """

    target = datetime(
        2026,
        3,
        1,
        12,
        0,
        0,
    )

    result = calculate_month_pillar(
        target,
        "丙",
    )

    assert result == "庚寅"


# ============================================================
# Representative dates
# ============================================================


@pytest.mark.parametrize(
    (
        "target,"
        "year_stem,"
        "expected"
    ),
    [
        (
            datetime(
                2026,
                2,
                15,
                12,
                0,
            ),
            "丙",
            "庚寅",
        ),
        (
            datetime(
                2026,
                3,
                15,
                12,
                0,
            ),
            "丙",
            "辛卯",
        ),
        (
            datetime(
                2026,
                4,
                15,
                12,
                0,
            ),
            "丙",
            "壬辰",
        ),
        (
            datetime(
                2026,
                5,
                15,
                12,
                0,
            ),
            "丙",
            "癸巳",
        ),
        (
            datetime(
                2026,
                6,
                15,
                12,
                0,
            ),
            "丙",
            "甲午",
        ),
        (
            datetime(
                2026,
                7,
                15,
                12,
                0,
            ),
            "丙",
            "乙未",
        ),
        (
            datetime(
                2026,
                8,
                15,
                12,
                0,
            ),
            "丙",
            "丙申",
        ),
        (
            datetime(
                2026,
                9,
                15,
                12,
                0,
            ),
            "丙",
            "丁酉",
        ),
        (
            datetime(
                2026,
                10,
                15,
                12,
                0,
            ),
            "丙",
            "戊戌",
        ),
        (
            datetime(
                2026,
                11,
                15,
                12,
                0,
            ),
            "丙",
            "己亥",
        ),
        (
            datetime(
                2026,
                12,
                15,
                12,
                0,
            ),
            "丙",
            "庚子",
        ),
    ],
)
def test_representative_month_pillars(
    target,
    year_stem,
    expected,
):
    """
    各節月の中間付近でも
    月柱が正しいことを確認する。
    """

    result = calculate_month_pillar(
        target,
        year_stem,
    )

    assert result == expected


# ============================================================
# 1984 regression
# ============================================================


def test_verified_1984_july_month_pillar():
    """
    既存の検証命式。

    1984-07-22
    甲子年
    辛未月
    """

    result = calculate_month_pillar(
        datetime(
            1984,
            7,
            22,
            4,
            15,
        ),
        "甲",
    )

    assert result == "辛未"


def test_verified_1984_july_month_branch():
    """
    1984-07-22は未月。
    """

    result = calculate_month_branch(
        datetime(
            1984,
            7,
            22,
            4,
            15,
        )
    )

    assert result == "未"


# ============================================================
# 1985 regression
# ============================================================


def test_verified_1985_july_month_pillar():
    """
    既存の検証命式。

    1985-07-17
    乙丑年
    癸未月
    """

    result = calculate_month_pillar(
        datetime(
            1985,
            7,
            17,
            21,
            50,
        ),
        "乙",
    )

    assert result == "癸未"


def test_verified_1985_july_month_branch():
    """
    1985-07-17は未月。
    """

    result = calculate_month_branch(
        datetime(
            1985,
            7,
            17,
            21,
            50,
        )
    )

    assert result == "未"


# ============================================================
# Cross-module consistency
# ============================================================


@pytest.mark.parametrize(
    "case",
    MONTH_BOUNDARIES_2026,
)
def test_month_module_and_solar_terms_agree(
    case,
):
    """
    month.py と solar_terms.py が
    同じ月支を返すことを確認する。
    """

    boundary = get_boundary(
        case["term"]
    )

    for target in (
        boundary
        - timedelta(seconds=1),
        boundary,
        boundary
        + timedelta(seconds=1),
    ):
        assert (
            calculate_month_branch(
                target
            )
            ==
            get_month_branch_by_datetime(
                target
            )
        )


# ============================================================
# Exact-boundary invariant
# ============================================================


@pytest.mark.parametrize(
    "case",
    MONTH_BOUNDARIES_2026,
)
def test_exact_boundary_is_always_new_month(
    case,
):
    """
    全12節について、

    境界時刻そのもの =
    新しい月

    という不変条件を固定する。
    """

    boundary = get_boundary(
        case["term"]
    )

    current_term = (
        get_current_solar_term(
            boundary
        )
    )

    assert (
        current_term.name
        == case["term"]
    )

    assert (
        current_term.month_branch
        == case["after_branch"]
    )

    assert (
        calculate_month_branch(
            boundary
        )
        == case["after_branch"]
    )


# ============================================================
# One-second transition invariant
# ============================================================


@pytest.mark.parametrize(
    "case",
    MONTH_BOUNDARIES_2026,
)
def test_every_boundary_changes_exactly_at_term(
    case,
):
    """
    全12節について、

    1秒前 != 新月
    境界   == 新月
    1秒後 == 新月

    をまとめて確認する。
    """

    boundary = get_boundary(
        case["term"]
    )

    before = (
        calculate_month_branch(
            boundary
            - timedelta(seconds=1)
        )
    )

    exact = (
        calculate_month_branch(
            boundary
        )
    )

    after = (
        calculate_month_branch(
            boundary
            + timedelta(seconds=1)
        )
    )

    assert before == case[
        "before_branch"
    ]

    assert exact == case[
        "after_branch"
    ]

    assert after == case[
        "after_branch"
    ]

    assert before != exact

    assert exact == after
