"""
tests/test_month.py

月柱計算エンジン v3 の回帰テスト。

検証対象:
- 月支
- 月干
- 月柱
- 五虎遁
- 12節すべての境界
- 節入り1秒前
- 節入りちょうど
- 節入り1秒後
- naive datetime
- aware datetime
- 既知ケース
- 不正入力

採用ルール:
- 月境界は実際の節入り時刻
- solar_terms_v3 を使用
- 節入り時刻ちょうどから新しい月
- 月干は五虎遁
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from engine.month import (
    MONTH_BRANCH_ORDER,
    MONTH_METHOD,
    MONTH_STATUS,
    TIGER_MONTH_STEM_START,
    calculate_month_branch,
    calculate_month_pillar,
    calculate_month_pillar_data,
    calculate_month_stem,
    get_month_pillar_metadata,
)
from engine.solar_terms import (
    SOLAR_TERMS,
    get_solar_term_datetime,
)


JST = ZoneInfo(
    "Asia/Tokyo"
)


# =========================================================
# Constants
# =========================================================


def test_month_method():
    assert (
        MONTH_METHOD
        == "astronomical_solar_terms_v3"
    )


def test_month_status():
    assert (
        MONTH_STATUS
        == "astronomical"
    )


def test_month_branch_order():
    assert MONTH_BRANCH_ORDER == [
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
        "子",
        "丑",
    ]


def test_tiger_month_stem_start():
    assert TIGER_MONTH_STEM_START == {
        "甲": 2,
        "己": 2,
        "乙": 4,
        "庚": 4,
        "丙": 6,
        "辛": 6,
        "丁": 8,
        "壬": 8,
        "戊": 0,
        "癸": 0,
    }


# =========================================================
# Five Tiger Escape
# =========================================================


@pytest.mark.parametrize(
    "year_stem,expected",
    [
        ("甲", "丙"),
        ("己", "丙"),
        ("乙", "戊"),
        ("庚", "戊"),
        ("丙", "庚"),
        ("辛", "庚"),
        ("丁", "壬"),
        ("壬", "壬"),
        ("戊", "甲"),
        ("癸", "甲"),
    ],
)
def test_tiger_month_stem(
    year_stem,
    expected,
):
    assert (
        calculate_month_stem(
            year_stem,
            "寅",
        )
        == expected
    )


@pytest.mark.parametrize(
    "year_stem,month_branch,expected",
    [
        ("甲", "寅", "丙"),
        ("甲", "卯", "丁"),
        ("甲", "辰", "戊"),
        ("甲", "巳", "己"),
        ("甲", "午", "庚"),
        ("甲", "未", "辛"),
        ("甲", "申", "壬"),
        ("甲", "酉", "癸"),
        ("甲", "戌", "甲"),
        ("甲", "亥", "乙"),
        ("甲", "子", "丙"),
        ("甲", "丑", "丁"),
    ],
)
def test_month_stem_full_cycle_for_jia_year(
    year_stem,
    month_branch,
    expected,
):
    assert (
        calculate_month_stem(
            year_stem,
            month_branch,
        )
        == expected
    )


# =========================================================
# Known month branches
# =========================================================


@pytest.mark.parametrize(
    "target,expected",
    [
        (
            datetime(
                1984,
                7,
                10,
                12,
                0,
            ),
            "未",
        ),
        (
            datetime(
                1984,
                7,
                22,
                4,
                15,
            ),
            "未",
        ),
        (
            datetime(
                1985,
                7,
                17,
                21,
                50,
            ),
            "未",
        ),
        (
            datetime(
                2026,
                8,
                10,
                12,
                0,
            ),
            "申",
        ),
    ],
)
def test_known_month_branches(
    target,
    expected,
):
    assert (
        calculate_month_branch(
            target
        )
        == expected
    )


# =========================================================
# Known month pillars
# =========================================================


@pytest.mark.parametrize(
    "target,year_stem,expected",
    [
        (
            datetime(
                1984,
                7,
                10,
                12,
                0,
            ),
            "甲",
            "辛未",
        ),
        (
            datetime(
                1984,
                7,
                22,
                4,
                15,
            ),
            "甲",
            "辛未",
        ),
        (
            datetime(
                1985,
                7,
                17,
                21,
                50,
            ),
            "乙",
            "癸未",
        ),
    ],
)
def test_known_month_pillars(
    target,
    year_stem,
    expected,
):
    assert (
        calculate_month_pillar(
            target,
            year_stem,
        )
        == expected
    )


# =========================================================
# Solar-term boundaries
# =========================================================


@pytest.mark.parametrize(
    "term_name,new_branch",
    [
        ("立春", "寅"),
        ("啓蟄", "卯"),
        ("清明", "辰"),
        ("立夏", "巳"),
        ("芒種", "午"),
        ("小暑", "未"),
        ("立秋", "申"),
        ("白露", "酉"),
        ("寒露", "戌"),
        ("立冬", "亥"),
        ("大雪", "子"),
        ("小寒", "丑"),
    ],
)
def test_month_branch_at_solar_term(
    term_name,
    new_branch,
):
    term = get_solar_term_datetime(
        2026,
        term_name,
    )

    assert (
        calculate_month_branch(
            term
        )
        == new_branch
    )


@pytest.mark.parametrize(
    "term_name,new_branch",
    [
        ("立春", "寅"),
        ("啓蟄", "卯"),
        ("清明", "辰"),
        ("立夏", "巳"),
        ("芒種", "午"),
        ("小暑", "未"),
        ("立秋", "申"),
        ("白露", "酉"),
        ("寒露", "戌"),
        ("立冬", "亥"),
        ("大雪", "子"),
        ("小寒", "丑"),
    ],
)
def test_month_branch_after_solar_term(
    term_name,
    new_branch,
):
    term = get_solar_term_datetime(
        2026,
        term_name,
    )

    after = (
        term
        + timedelta(
            seconds=1
        )
    )

    assert (
        calculate_month_branch(
            after
        )
        == new_branch
    )


# =========================================================
# Previous branches
# =========================================================


PREVIOUS_BRANCH = {
    "立春": "丑",
    "啓蟄": "寅",
    "清明": "卯",
    "立夏": "辰",
    "芒種": "巳",
    "小暑": "午",
    "立秋": "未",
    "白露": "申",
    "寒露": "酉",
    "立冬": "戌",
    "大雪": "亥",
    "小寒": "子",
}


@pytest.mark.parametrize(
    "term_name,new_branch",
    [
        ("立春", "寅"),
        ("啓蟄", "卯"),
        ("清明", "辰"),
        ("立夏", "巳"),
        ("芒種", "午"),
        ("小暑", "未"),
        ("立秋", "申"),
        ("白露", "酉"),
        ("寒露", "戌"),
        ("立冬", "亥"),
        ("大雪", "子"),
        ("小寒", "丑"),
    ],
)
def test_month_branch_before_solar_term(
    term_name,
    new_branch,
):
    term = get_solar_term_datetime(
        2026,
        term_name,
    )

    before = (
        term
        - timedelta(
            seconds=1
        )
    )

    assert (
        calculate_month_branch(
            before
        )
        == PREVIOUS_BRANCH[
            term_name
        ]
    )


# =========================================================
# All 12 solar terms defined
# =========================================================


def test_all_twelve_month_boundary_terms_exist():
    names = {
        item[
            "name"
        ]
        for item
        in SOLAR_TERMS
    }

    assert names == {
        "小寒",
        "立春",
        "啓蟄",
        "清明",
        "立夏",
        "芒種",
        "小暑",
        "立秋",
        "白露",
        "寒露",
        "立冬",
        "大雪",
    }


def test_all_solar_terms_have_month_branch():
    for item in SOLAR_TERMS:
        assert (
            item[
                "month_branch"
            ]
            in MONTH_BRANCH_ORDER
        )


# =========================================================
# Boundary pillar
# =========================================================


def test_lichun_changes_month_pillar():
    lichun = get_solar_term_datetime(
        2026,
        "立春",
    )

    before = (
        lichun
        - timedelta(
            seconds=1
        )
    )

    at = lichun

    before_pillar = (
        calculate_month_pillar(
            before,
            "丙",
        )
    )

    at_pillar = (
        calculate_month_pillar(
            at,
            "丙",
        )
    )

    assert before_pillar == "辛丑"
    assert at_pillar == "庚寅"


def test_xiaoshu_changes_month_pillar():
    xiaoshu = get_solar_term_datetime(
        2026,
        "小暑",
    )

    before = (
        xiaoshu
        - timedelta(
            seconds=1
        )
    )

    at = xiaoshu

    before_pillar = (
        calculate_month_pillar(
            before,
            "丙",
        )
    )

    at_pillar = (
        calculate_month_pillar(
            at,
            "丙",
        )
    )

    assert before_pillar == "甲午"
    assert at_pillar == "乙未"


# =========================================================
# Timezone-aware datetime
# =========================================================


def test_month_branch_accepts_jst_aware():
    target = datetime(
        1985,
        7,
        17,
        21,
        50,
        tzinfo=JST,
    )

    assert (
        calculate_month_branch(
            target
        )
        == "未"
    )


def test_month_pillar_accepts_jst_aware():
    target = datetime(
        1985,
        7,
        17,
        21,
        50,
        tzinfo=JST,
    )

    assert (
        calculate_month_pillar(
            target,
            "乙",
        )
        == "癸未"
    )


def test_naive_and_jst_aware_same_local_time():
    naive = datetime(
        1985,
        7,
        17,
        21,
        50,
    )

    aware = datetime(
        1985,
        7,
        17,
        21,
        50,
        tzinfo=JST,
    )

    assert (
        calculate_month_branch(
            naive
        )
        == calculate_month_branch(
            aware
        )
    )


# =========================================================
# Detailed result
# =========================================================


def test_month_pillar_data():
    result = (
        calculate_month_pillar_data(
            datetime(
                1985,
                7,
                17,
                21,
                50,
            ),
            "乙",
        )
    )

    assert result[
        "ganzhi"
    ] == "癸未"

    assert result[
        "stem"
    ] == "癸"

    assert result[
        "branch"
    ] == "未"

    assert result[
        "year_stem"
    ] == "乙"

    assert result[
        "method"
    ] == (
        "astronomical_solar_terms_v3"
    )

    assert result[
        "status"
    ] == "astronomical"

    assert result[
        "boundary"
    ] == (
        "astronomical_solar_term"
    )

    assert result[
        "solar_term_source"
    ] == "solar_terms_v3"

    assert result[
        "true_solar_time"
    ] is False


# =========================================================
# Metadata
# =========================================================


def test_month_metadata():
    result = (
        get_month_pillar_metadata()
    )

    assert result[
        "method"
    ] == (
        "astronomical_solar_terms_v3"
    )

    assert result[
        "status"
    ] == "astronomical"

    assert result[
        "boundary"
    ] == (
        "astronomical_solar_term"
    )

    assert result[
        "solar_term_source"
    ] == "solar_terms_v3"

    assert result[
        "true_solar_time"
    ] is False

    assert result[
        "month_branch_order"
    ] == MONTH_BRANCH_ORDER


# =========================================================
# Invalid year stem
# =========================================================


@pytest.mark.parametrize(
    "year_stem",
    [
        "",
        "子",
        "A",
        "甲子",
        None,
    ],
)
def test_month_stem_invalid_year_stem(
    year_stem,
):
    with pytest.raises(
        ValueError
    ):
        calculate_month_stem(
            year_stem,
            "寅",
        )


@pytest.mark.parametrize(
    "year_stem",
    [
        "",
        "子",
        "A",
        "甲子",
        None,
    ],
)
def test_month_pillar_invalid_year_stem(
    year_stem,
):
    with pytest.raises(
        ValueError
    ):
        calculate_month_pillar(
            datetime(
                2026,
                8,
                10,
                12,
                0,
            ),
            year_stem,
        )


# =========================================================
# Invalid month branch
# =========================================================


@pytest.mark.parametrize(
    "month_branch",
    [
        "",
        "甲",
        "A",
        "寅卯",
        None,
    ],
)
def test_month_stem_invalid_month_branch(
    month_branch,
):
    with pytest.raises(
        ValueError
    ):
        calculate_month_stem(
            "甲",
            month_branch,
        )


# =========================================================
# Invalid datetime
# =========================================================


@pytest.mark.parametrize(
    "invalid_value",
    [
        "2026-08-10",
        20260810,
        0,
        1.5,
        None,
        [],
        {},
    ],
)
def test_month_branch_invalid_datetime(
    invalid_value,
):
    with pytest.raises(
        TypeError
    ):
        calculate_month_branch(
            invalid_value
        )


@pytest.mark.parametrize(
    "invalid_value",
    [
        "2026-08-10",
        20260810,
        None,
    ],
)
def test_month_pillar_invalid_datetime(
    invalid_value,
):
    with pytest.raises(
        TypeError
    ):
        calculate_month_pillar(
            invalid_value,
            "甲",
        )
