"""
tests/test_solar_terms.py

solar_terms_v3 統合テスト。

対象:
    engine.solar_terms

目的
----
固定月日方式だった solar_terms_v2 から、

    Skyfield
        ↓
    太陽黄経
        ↓
    実際の節入り日時
        ↓
    月支判定
        ↓
    大運対象節入り

へ移行した solar_terms_v3 を検証する。

重要
----
v3 では節入り日時を固定値として扱わない。

したがって、

    立春 = 2月4日00:00
    小暑 = 7月7日00:00
    立秋 = 8月8日00:00

のような旧暫定値を assert しない。

代わりに、

1. 節入り日時が妥当な暦日範囲に入る
2. 12節が正しい順番で取得できる
3. 節入り直前・ちょうど・直後で月境界が正しく切り替わる
4. forward / backward の大運対象節入りが正しい
5. 距離計算が実際の節入り時刻と整合する
6. メタデータが v3 を示す

ことを検証する。
"""

from datetime import datetime, timedelta

import pytest

from engine.solar_terms import (
    MONTH_BRANCHES,
    SOLAR_TERM_METHOD,
    SOLAR_TERM_NAMES,
    SOLAR_TERM_STATUS,
    SOLAR_TERMS,
    SolarTerm,
    build_solar_term,
    get_current_solar_term,
    get_distance_to_next_term_days,
    get_distance_to_previous_term_days,
    get_luck_pillar_target_datetime,
    get_luck_pillar_target_term,
    get_month_branch_by_datetime,
    get_month_number_by_datetime,
    get_next_solar_term,
    get_next_term,
    get_previous_solar_term,
    get_previous_term,
    get_solar_term_by_month,
    get_solar_term_datetime,
    get_solar_term_definition,
    get_solar_term_position,
    get_solar_terms_metadata,
    get_surrounding_solar_terms,
    get_target_term_for_luck_pillars,
    get_year_solar_terms,
    get_year_solar_terms_dict,
    solar_term_to_dict,
)


# =========================================================
# Constants
# =========================================================


EXPECTED_TERM_NAMES = [
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
]


EXPECTED_LONGITUDES = {
    "小寒": 285.0,
    "立春": 315.0,
    "啓蟄": 345.0,
    "清明": 15.0,
    "立夏": 45.0,
    "芒種": 75.0,
    "小暑": 105.0,
    "立秋": 135.0,
    "白露": 165.0,
    "寒露": 195.0,
    "立冬": 225.0,
    "大雪": 255.0,
}


EXPECTED_MONTH_BRANCHES = {
    "小寒": "丑",
    "立春": "寅",
    "啓蟄": "卯",
    "清明": "辰",
    "立夏": "巳",
    "芒種": "午",
    "小暑": "未",
    "立秋": "申",
    "白露": "酉",
    "寒露": "戌",
    "立冬": "亥",
    "大雪": "子",
}


EXPECTED_MONTH_NUMBERS = {
    "立春": 1,
    "啓蟄": 2,
    "清明": 3,
    "立夏": 4,
    "芒種": 5,
    "小暑": 6,
    "立秋": 7,
    "白露": 8,
    "寒露": 9,
    "立冬": 10,
    "大雪": 11,
    "小寒": 12,
}


# =========================================================
# Constants
# =========================================================


def test_solar_term_method():
    assert (
        SOLAR_TERM_METHOD
        == "skyfield_solar_longitude_v3"
    )


def test_solar_term_status():
    assert (
        SOLAR_TERM_STATUS
        == "astronomical"
    )


def test_solar_term_count():
    assert len(
        SOLAR_TERMS
    ) == 12


def test_solar_term_names():
    assert (
        SOLAR_TERM_NAMES
        == EXPECTED_TERM_NAMES
    )


def test_month_branches():
    assert MONTH_BRANCHES == [
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


def test_all_terms_have_longitude():
    for term in SOLAR_TERMS:
        assert "longitude" in term

        assert (
            term["longitude"]
            == EXPECTED_LONGITUDES[
                term["name"]
            ]
        )


# =========================================================
# Definition helpers
# =========================================================


def test_get_solar_term_definition():
    result = (
        get_solar_term_definition(
            "小暑"
        )
    )

    assert result["name"] == "小暑"
    assert result["month"] == 7
    assert result["month_branch"] == "未"
    assert result["month_number"] == 6
    assert result["longitude"] == 105.0


def test_get_solar_term_definition_returns_copy():
    first = get_solar_term_definition(
        "立春"
    )

    second = get_solar_term_definition(
        "立春"
    )

    assert first == second
    assert first is not second


def test_get_solar_term_definition_invalid():
    with pytest.raises(
        ValueError
    ):
        get_solar_term_definition(
            "存在しない節"
        )


@pytest.mark.parametrize(
    (
        "month",
        "name",
    ),
    [
        (1, "小寒"),
        (2, "立春"),
        (3, "啓蟄"),
        (4, "清明"),
        (5, "立夏"),
        (6, "芒種"),
        (7, "小暑"),
        (8, "立秋"),
        (9, "白露"),
        (10, "寒露"),
        (11, "立冬"),
        (12, "大雪"),
    ],
)
def test_get_solar_term_by_month(
    month,
    name,
):
    result = (
        get_solar_term_by_month(
            month
        )
    )

    assert result[
        "name"
    ] == name


@pytest.mark.parametrize(
    "month",
    [
        0,
        13,
        -1,
    ],
)
def test_get_solar_term_by_month_invalid(
    month,
):
    with pytest.raises(
        ValueError
    ):
        get_solar_term_by_month(
            month
        )


def test_get_solar_term_by_month_type_error():
    with pytest.raises(
        TypeError
    ):
        get_solar_term_by_month(
            "7"
        )


# =========================================================
# Astronomical datetime
# =========================================================


def test_get_solar_term_datetime():
    result = (
        get_solar_term_datetime(
            1984,
            "小暑",
        )
    )

    assert isinstance(
        result,
        datetime,
    )

    # 小暑は通常7月6～8日付近。
    assert result.year == 1984
    assert result.month == 7
    assert 6 <= result.day <= 8


def test_get_solar_term_datetime_risshun():
    result = (
        get_solar_term_datetime(
            1984,
            "立春",
        )
    )

    assert isinstance(
        result,
        datetime,
    )

    assert result.year == 1984
    assert result.month == 2

    # 天文計算結果を固定時刻ではなく
    # 妥当な暦日範囲で検証する。
    assert 3 <= result.day <= 5


def test_solar_term_datetime_is_timezone_naive():
    result = (
        get_solar_term_datetime(
            1985,
            "立秋",
        )
    )

    assert (
        result.tzinfo
        is None
    )


def test_solar_term_datetime_reproducible():
    first = (
        get_solar_term_datetime(
            1985,
            "小暑",
        )
    )

    second = (
        get_solar_term_datetime(
            1985,
            "小暑",
        )
    )

    assert first == second


def test_solar_term_datetime_invalid_year():
    with pytest.raises(
        ValueError
    ):
        get_solar_term_datetime(
            0,
            "立春",
        )


def test_solar_term_datetime_invalid_term():
    with pytest.raises(
        ValueError
    ):
        get_solar_term_datetime(
            1984,
            "存在しない節",
        )


# =========================================================
# SolarTerm object
# =========================================================


def test_build_solar_term():
    term = build_solar_term(
        1984,
        "小暑",
    )

    assert isinstance(
        term,
        SolarTerm,
    )

    assert term.name == "小暑"
    assert term.month_branch == "未"
    assert term.month_number == 6
    assert term.longitude == 105.0

    assert (
        term.method
        == SOLAR_TERM_METHOD
    )

    assert (
        term.status
        == SOLAR_TERM_STATUS
    )


def test_build_solar_term_datetime_matches():
    term = build_solar_term(
        1984,
        "立秋",
    )

    expected = (
        get_solar_term_datetime(
            1984,
            "立秋",
        )
    )

    assert (
        term.datetime
        == expected
    )


# =========================================================
# Year terms
# =========================================================


def test_get_year_solar_terms():
    terms = get_year_solar_terms(
        1984
    )

    assert len(
        terms
    ) == 12

    assert [
        term.name
        for term in terms
    ] == EXPECTED_TERM_NAMES


def test_get_year_solar_terms_sorted():
    terms = get_year_solar_terms(
        1984
    )

    datetimes = [
        term.datetime
        for term in terms
    ]

    assert datetimes == sorted(
        datetimes
    )


def test_get_year_solar_terms_unique():
    terms = get_year_solar_terms(
        1984
    )

    assert len(
        {
            term.name
            for term in terms
        }
    ) == 12


def test_get_year_solar_terms_longitudes():
    terms = get_year_solar_terms(
        1984
    )

    for term in terms:
        assert (
            term.longitude
            == EXPECTED_LONGITUDES[
                term.name
            ]
        )


def test_get_year_solar_terms_dict():
    results = (
        get_year_solar_terms_dict(
            1984
        )
    )

    assert len(
        results
    ) == 12

    assert isinstance(
        results[0],
        dict,
    )

    assert {
        "name",
        "datetime",
        "month_branch",
        "month_number",
        "longitude",
        "method",
        "status",
    }.issubset(
        results[0].keys()
    )


# =========================================================
# Serialization
# =========================================================


def test_solar_term_to_dict():
    term = build_solar_term(
        1984,
        "立春",
    )

    result = solar_term_to_dict(
        term
    )

    assert result[
        "name"
    ] == "立春"

    assert result[
        "month_branch"
    ] == "寅"

    assert result[
        "month_number"
    ] == 1

    assert result[
        "longitude"
    ] == 315.0

    assert result[
        "datetime"
    ] == term.datetime.isoformat()

    assert result[
        "method"
    ] == SOLAR_TERM_METHOD

    assert result[
        "status"
    ] == SOLAR_TERM_STATUS


def test_solar_term_to_dict_type_error():
    with pytest.raises(
        TypeError
    ):
        solar_term_to_dict(
            {}
        )


# =========================================================
# Surrounding terms
# =========================================================


def test_get_surrounding_solar_terms():
    target = datetime(
        1984,
        7,
        10,
        12,
        0,
    )

    terms = (
        get_surrounding_solar_terms(
            target
        )
    )

    assert len(
        terms
    ) == 36

    assert terms == sorted(
        terms,
        key=lambda item: (
            item.datetime
        ),
    )


def test_surrounding_terms_include_previous_and_next_year():
    target = datetime(
        1984,
        1,
        1,
        0,
        0,
    )

    terms = (
        get_surrounding_solar_terms(
            target
        )
    )

    years = {
        term.datetime.year
        for term in terms
    }

    assert 1983 in years
    assert 1984 in years
    assert 1985 in years


# =========================================================
# Previous / next term
# =========================================================


def test_previous_solar_term():
    shosho = build_solar_term(
        1984,
        "小暑",
    )

    target = (
        shosho.datetime
        + timedelta(
            days=1
        )
    )

    result = (
        get_previous_solar_term(
            target
        )
    )

    assert (
        result.name
        == "小暑"
    )


def test_next_solar_term():
    shosho = build_solar_term(
        1984,
        "小暑",
    )

    target = (
        shosho.datetime
        + timedelta(
            days=1
        )
    )

    result = (
        get_next_solar_term(
            target
        )
    )

    assert (
        result.name
        == "立秋"
    )


def test_previous_solar_term_exact_default_excludes():
    shosho = build_solar_term(
        1984,
        "小暑",
    )

    result = (
        get_previous_solar_term(
            shosho.datetime,
            inclusive=False,
        )
    )

    assert (
        result.name
        == "芒種"
    )


def test_previous_solar_term_exact_inclusive():
    shosho = build_solar_term(
        1984,
        "小暑",
    )

    result = (
        get_previous_solar_term(
            shosho.datetime,
            inclusive=True,
        )
    )

    assert (
        result.name
        == "小暑"
    )


def test_next_solar_term_exact_default_excludes():
    shosho = build_solar_term(
        1984,
        "小暑",
    )

    result = (
        get_next_solar_term(
            shosho.datetime,
            inclusive=False,
        )
    )

    assert (
        result.name
        == "立秋"
    )


def test_next_solar_term_exact_inclusive():
    shosho = build_solar_term(
        1984,
        "小暑",
    )

    result = (
        get_next_solar_term(
            shosho.datetime,
            inclusive=True,
        )
    )

    assert (
        result.name
        == "小暑"
    )


# =========================================================
# Luck pillar target term
# =========================================================


def test_luck_pillar_target_forward_1984_07_10():
    birth = datetime(
        1984,
        7,
        10,
        22,
        45,
    )

    result = (
        get_luck_pillar_target_term(
            birth,
            "forward",
        )
    )

    assert (
        result.name
        == "立秋"
    )

    assert (
        result.datetime
        > birth
    )


def test_luck_pillar_target_backward_1984_07_10():
    birth = datetime(
        1984,
        7,
        10,
        22,
        45,
    )

    result = (
        get_luck_pillar_target_term(
            birth,
            "backward",
        )
    )

    assert (
        result.name
        == "小暑"
    )

    assert (
        result.datetime
        < birth
    )


def test_luck_pillar_target_datetime_forward():
    birth = datetime(
        1984,
        7,
        10,
        22,
        45,
    )

    term = (
        get_luck_pillar_target_term(
            birth,
            "forward",
        )
    )

    result = (
        get_luck_pillar_target_datetime(
            birth,
            "forward",
        )
    )

    assert result == term.datetime


def test_luck_pillar_target_datetime_backward():
    birth = datetime(
        1984,
        7,
        10,
        22,
        45,
    )

    term = (
        get_luck_pillar_target_term(
            birth,
            "backward",
        )
    )

    result = (
        get_luck_pillar_target_datetime(
            birth,
            "backward",
        )
    )

    assert result == term.datetime


def test_luck_pillar_target_exact_term_forward_uses_next():
    shosho = build_solar_term(
        1984,
        "小暑",
    )

    result = (
        get_luck_pillar_target_term(
            shosho.datetime,
            "forward",
        )
    )

    assert (
        result.name
        == "立秋"
    )


def test_luck_pillar_target_exact_term_backward_uses_previous():
    shosho = build_solar_term(
        1984,
        "小暑",
    )

    result = (
        get_luck_pillar_target_term(
            shosho.datetime,
            "backward",
        )
    )

    assert (
        result.name
        == "芒種"
    )


def test_luck_pillar_target_invalid_direction():
    with pytest.raises(
        ValueError
    ):
        get_luck_pillar_target_term(
            datetime(
                1984,
                7,
                10,
            ),
            "invalid",
        )


# =========================================================
# Current solar term
# =========================================================


def test_current_solar_term_after_shosho():
    shosho = build_solar_term(
        1984,
        "小暑",
    )

    target = (
        shosho.datetime
        + timedelta(
            seconds=1
        )
    )

    result = (
        get_current_solar_term(
            target
        )
    )

    assert (
        result.name
        == "小暑"
    )


def test_current_solar_term_at_shosho():
    shosho = build_solar_term(
        1984,
        "小暑",
    )

    result = (
        get_current_solar_term(
            shosho.datetime
        )
    )

    assert (
        result.name
        == "小暑"
    )


def test_current_solar_term_before_shosho():
    shosho = build_solar_term(
        1984,
        "小暑",
    )

    target = (
        shosho.datetime
        - timedelta(
            seconds=1
        )
    )

    result = (
        get_current_solar_term(
            target
        )
    )

    assert (
        result.name
        == "芒種"
    )


# =========================================================
# Month branch
# =========================================================


@pytest.mark.parametrize(
    (
        "term_name",
        "expected_branch",
    ),
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
def test_get_month_branch_at_term(
    term_name,
    expected_branch,
):
    term = build_solar_term(
        1984,
        term_name,
    )

    assert (
        get_month_branch_by_datetime(
            term.datetime
        )
        == expected_branch
    )


@pytest.mark.parametrize(
    (
        "term_name",
        "previous_branch",
    ),
    [
        ("立春", "丑"),
        ("啓蟄", "寅"),
        ("清明", "卯"),
        ("立夏", "辰"),
        ("芒種", "巳"),
        ("小暑", "午"),
        ("立秋", "未"),
        ("白露", "申"),
        ("寒露", "酉"),
        ("立冬", "戌"),
        ("大雪", "亥"),
        ("小寒", "子"),
    ],
)
def test_get_month_branch_one_second_before_term(
    term_name,
    previous_branch,
):
    term = build_solar_term(
        1984,
        term_name,
    )

    target = (
        term.datetime
        - timedelta(
            seconds=1
        )
    )

    assert (
        get_month_branch_by_datetime(
            target
        )
        == previous_branch
    )


# =========================================================
# Month number
# =========================================================


@pytest.mark.parametrize(
    (
        "term_name",
        "month_number",
    ),
    [
        ("立春", 1),
        ("啓蟄", 2),
        ("清明", 3),
        ("立夏", 4),
        ("芒種", 5),
        ("小暑", 6),
        ("立秋", 7),
        ("白露", 8),
        ("寒露", 9),
        ("立冬", 10),
        ("大雪", 11),
        ("小寒", 12),
    ],
)
def test_get_month_number_at_term(
    term_name,
    month_number,
):
    term = build_solar_term(
        1984,
        term_name,
    )

    assert (
        get_month_number_by_datetime(
            term.datetime
        )
        == month_number
    )


# =========================================================
# Boundary tests
# =========================================================


@pytest.mark.parametrize(
    "term_name",
    EXPECTED_TERM_NAMES,
)
def test_term_boundary_switches_exactly(
    term_name,
):
    term = build_solar_term(
        1984,
        term_name,
    )

    before = (
        term.datetime
        - timedelta(
            seconds=1
        )
    )

    exact = term.datetime

    after = (
        term.datetime
        + timedelta(
            seconds=1
        )
    )

    branch_before = (
        get_month_branch_by_datetime(
            before
        )
    )

    branch_exact = (
        get_month_branch_by_datetime(
            exact
        )
    )

    branch_after = (
        get_month_branch_by_datetime(
            after
        )
    )

    assert (
        branch_exact
        == term.month_branch
    )

    assert (
        branch_after
        == term.month_branch
    )

    assert (
        branch_before
        != term.month_branch
    )


# =========================================================
# Distance helpers
# =========================================================


def test_distance_to_previous_term_days():
    shosho = build_solar_term(
        1984,
        "小暑",
    )

    target = (
        shosho.datetime
        + timedelta(
            days=3
        )
    )

    result = (
        get_distance_to_previous_term_days(
            target
        )
    )

    assert result == pytest.approx(
        3.0,
        abs=1e-8,
    )


def test_distance_to_previous_term_days_fractional():
    shosho = build_solar_term(
        1984,
        "小暑",
    )

    target = (
        shosho.datetime
        + timedelta(
            days=3,
            hours=12,
        )
    )

    result = (
        get_distance_to_previous_term_days(
            target
        )
    )

    assert result == pytest.approx(
        3.5,
        abs=1e-8,
    )


def test_distance_to_next_term_days():
    shosho = build_solar_term(
        1984,
        "小暑",
    )

    risshu = build_solar_term(
        1984,
        "立秋",
    )

    target = (
        shosho.datetime
        + timedelta(
            days=3
        )
    )

    expected = (
        (
            risshu.datetime
            - target
        ).total_seconds()
        / 86400.0
    )

    result = (
        get_distance_to_next_term_days(
            target
        )
    )

    assert result == pytest.approx(
        expected,
        abs=1e-8,
    )


def test_distance_to_next_term_days_fractional():
    shosho = build_solar_term(
        1984,
        "小暑",
    )

    risshu = build_solar_term(
        1984,
        "立秋",
    )

    target = (
        shosho.datetime
        + timedelta(
            days=3,
            hours=12,
        )
    )

    expected = (
        (
            risshu.datetime
            - target
        ).total_seconds()
        / 86400.0
    )

    result = (
        get_distance_to_next_term_days(
            target
        )
    )

    assert result == pytest.approx(
        expected,
        abs=1e-8,
    )


# =========================================================
# Solar-term position
# =========================================================


def test_get_solar_term_position():
    shosho = build_solar_term(
        1984,
        "小暑",
    )

    target = (
        shosho.datetime
        + timedelta(
            days=5
        )
    )

    result = (
        get_solar_term_position(
            target
        )
    )

    assert (
        result[
            "current_term"
        ][
            "name"
        ]
        == "小暑"
    )

    assert (
        result[
            "next_term"
        ][
            "name"
        ]
        == "立秋"
    )

    assert (
        result[
            "days_from_current_term"
        ]
        == pytest.approx(
            5.0,
            abs=1e-8,
        )
    )

    assert (
        0.0
        <= result[
            "progress_ratio"
        ]
        <= 1.0
    )

    assert (
        result[
            "method"
        ]
        == SOLAR_TERM_METHOD
    )

    assert (
        result[
            "status"
        ]
        == SOLAR_TERM_STATUS
    )


def test_get_solar_term_position_just_after():
    shosho = build_solar_term(
        1984,
        "小暑",
    )

    target = (
        shosho.datetime
        + timedelta(
            hours=12
        )
    )

    result = (
        get_solar_term_position(
            target
        )
    )

    assert (
        result[
            "is_just_after_term"
        ]
        is True
    )


def test_get_solar_term_position_not_just_after():
    shosho = build_solar_term(
        1984,
        "小暑",
    )

    target = (
        shosho.datetime
        + timedelta(
            days=5
        )
    )

    result = (
        get_solar_term_position(
            target
        )
    )

    assert (
        result[
            "is_just_after_term"
        ]
        is False
    )


def test_solar_term_position_consistency():
    target = datetime(
        1985,
        7,
        17,
        21,
        50,
    )

    result = (
        get_solar_term_position(
            target
        )
    )

    total = (
        result[
            "days_from_current_term"
        ]
        + result[
            "days_to_next_term"
        ]
    )

    assert total == pytest.approx(
        result[
            "term_span_days"
        ],
        abs=1e-6,
    )


# =========================================================
# Compatibility aliases
# =========================================================


def test_previous_term_alias():
    target = datetime(
        1984,
        7,
        10,
        12,
        0,
    )

    assert (
        get_previous_term(
            target
        )
        == get_previous_solar_term(
            target
        )
    )


def test_next_term_alias():
    target = datetime(
        1984,
        7,
        10,
        12,
        0,
    )

    assert (
        get_next_term(
            target
        )
        == get_next_solar_term(
            target
        )
    )


@pytest.mark.parametrize(
    "direction",
    [
        "forward",
        "backward",
    ],
)
def test_target_term_for_luck_pillars_alias(
    direction,
):
    birth = datetime(
        1984,
        7,
        10,
        22,
        45,
    )

    assert (
        get_target_term_for_luck_pillars(
            birth,
            direction,
        )
        == get_luck_pillar_target_term(
            birth,
            direction,
        )
    )


# =========================================================
# Real-chart relevant regression
# =========================================================


def test_1985_verified_birth_is_in_shosho_month():
    """
    1985-07-17 21:50 は
    小暑後・立秋前なので未月。
    """

    birth = datetime(
        1985,
        7,
        17,
        21,
        50,
    )

    current = (
        get_current_solar_term(
            birth
        )
    )

    assert current.name == "小暑"
    assert current.month_branch == "未"
    assert current.month_number == 6


def test_1985_verified_forward_target_is_risshu():
    """
    乙年女性は大運順行。

    1985-07-17 出生から見た
    次節は立秋。
    """

    birth = datetime(
        1985,
        7,
        17,
        21,
        50,
    )

    result = (
        get_luck_pillar_target_term(
            birth,
            "forward",
        )
    )

    assert result.name == "立秋"
    assert result.month_branch == "申"
    assert result.datetime > birth


def test_1985_risshu_is_astronomical_not_fixed_midnight():
    """
    v2との差を保証する回帰テスト。

    旧仕様:
        1985-08-08 00:00

    v3:
        太陽黄経135°の実時刻。

    したがって旧固定値と一致してはいけない。
    """

    result = (
        get_solar_term_datetime(
            1985,
            "立秋",
        )
    )

    assert (
        result
        != datetime(
            1985,
            8,
            8,
            0,
            0,
        )
    )


def test_1984_shosho_is_astronomical_not_fixed_midnight():
    result = (
        get_solar_term_datetime(
            1984,
            "小暑",
        )
    )

    assert (
        result
        != datetime(
            1984,
            7,
            7,
            0,
            0,
        )
    )


# =========================================================
# Metadata
# =========================================================


def test_solar_terms_metadata():
    result = (
        get_solar_terms_metadata()
    )

    assert (
        result[
            "method"
        ]
        == "skyfield_solar_longitude_v3"
    )

    assert (
        result[
            "status"
        ]
        == "astronomical"
    )

    assert (
        result[
            "term_count"
        ]
        == 12
    )

    assert (
        result[
            "term_type"
        ]
        == "12_month_boundary_terms"
    )

    assert (
        result[
            "precision"
        ]
        == "astronomical_solar_longitude"
    )

    assert (
        result[
            "timezone"
        ]
        == "JST_naive_public_api"
    )

    assert (
        result[
            "ephemeris"
        ]
        == "JPL DE421"
    )

    assert isinstance(
        result[
            "supports"
        ],
        list,
    )

    assert (
        "month_boundary"
        in result[
            "supports"
        ]
    )

    assert (
        "previous_term"
        in result[
            "supports"
        ]
    )

    assert (
        "next_term"
        in result[
            "supports"
        ]
    )

    assert (
        "luck_pillar_target_term"
        in result[
            "supports"
        ]
    )

    assert (
        "solar_term_position"
        in result[
            "supports"
        ]
    )

    assert (
        "astronomical_longitude"
        in result[
            "supports"
        ]
    )

    assert isinstance(
        result[
            "limitations"
        ],
        list,
    )

    assert (
        len(
            result[
                "limitations"
            ]
        )
        >= 1
    )
