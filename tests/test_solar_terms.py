"""
tests/test_solar_terms.py

engine/solar_terms.py の単体テスト。

検証対象
--------
- 12節の定義
- 節名・月からの定義取得
- 節入り日時
- SolarTerm生成
- 年間12節
- dict変換
- 前年・当年・翌年を含む検索範囲
- 直前の節入り
- 直後の節入り
- inclusive境界
- 大運用対象節入り
- 現在の節月
- 月支
- 月番号
- 前節・次節までの日数
- 年跨ぎ
- 1984年7月10日の小暑 / 立秋
- metadata
- compatibility alias

重要
----
現行 engine/solar_terms.py は
fixed_solar_terms_v2 による暫定節入りです。

本テストは「現在の固定節入り仕様」を
回帰テストとして固定します。

将来 Skyfield 等へ移行した場合は、
固定日時そのものではなく、
API契約・前後関係・境界判定を中心に
テストを更新してください。
"""

from datetime import datetime

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


def test_solar_term_method():
    assert (
        SOLAR_TERM_METHOD
        == "fixed_solar_terms_v2"
    )


def test_solar_term_status():
    assert (
        SOLAR_TERM_STATUS
        == "provisional"
    )


def test_solar_terms_count():
    assert len(
        SOLAR_TERMS
    ) == 12


def test_solar_term_names():
    assert SOLAR_TERM_NAMES == [
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


def test_solar_terms_months_are_unique():
    months = [
        term[
            "month"
        ]
        for term in SOLAR_TERMS
    ]

    assert sorted(
        months
    ) == list(
        range(
            1,
            13,
        )
    )


def test_solar_terms_names_are_unique():
    names = [
        term[
            "name"
        ]
        for term in SOLAR_TERMS
    ]

    assert len(
        names
    ) == len(
        set(
            names
        )
    )


# =========================================================
# Definition helpers
# =========================================================


def test_get_solar_term_definition_risshun():
    result = (
        get_solar_term_definition(
            "立春"
        )
    )

    assert result[
        "month"
    ] == 2

    assert result[
        "day"
    ] == 4

    assert result[
        "month_branch"
    ] == "寅"

    assert result[
        "month_number"
    ] == 1


def test_get_solar_term_definition_shosho():
    result = (
        get_solar_term_definition(
            "小暑"
        )
    )

    assert result[
        "month"
    ] == 7

    assert result[
        "day"
    ] == 7

    assert result[
        "month_branch"
    ] == "未"

    assert result[
        "month_number"
    ] == 6


def test_get_solar_term_definition_returns_copy():
    result = (
        get_solar_term_definition(
            "立春"
        )
    )

    result[
        "day"
    ] = 99

    original = (
        get_solar_term_definition(
            "立春"
        )
    )

    assert original[
        "day"
    ] == 4


def test_get_solar_term_definition_unknown():
    with pytest.raises(
        ValueError
    ):
        get_solar_term_definition(
            "不存在"
        )


@pytest.mark.parametrize(
    (
        "month",
        "expected_name",
        "expected_branch",
    ),
    [
        (1, "小寒", "丑"),
        (2, "立春", "寅"),
        (3, "啓蟄", "卯"),
        (4, "清明", "辰"),
        (5, "立夏", "巳"),
        (6, "芒種", "午"),
        (7, "小暑", "未"),
        (8, "立秋", "申"),
        (9, "白露", "酉"),
        (10, "寒露", "戌"),
        (11, "立冬", "亥"),
        (12, "大雪", "子"),
    ],
)
def test_get_solar_term_by_month(
    month,
    expected_name,
    expected_branch,
):
    result = (
        get_solar_term_by_month(
            month
        )
    )

    assert result[
        "name"
    ] == expected_name

    assert result[
        "month_branch"
    ] == expected_branch


def test_get_solar_term_by_month_type_error():
    with pytest.raises(
        TypeError
    ):
        get_solar_term_by_month(
            "7"
        )


@pytest.mark.parametrize(
    "month",
    [
        0,
        13,
        -1,
    ],
)
def test_get_solar_term_by_month_value_error(
    month,
):
    with pytest.raises(
        ValueError
    ):
        get_solar_term_by_month(
            month
        )


# =========================================================
# Solar-term datetime
# =========================================================


def test_get_solar_term_datetime():
    result = (
        get_solar_term_datetime(
            1984,
            "小暑",
        )
    )

    assert result == datetime(
        1984,
        7,
        7,
        0,
        0,
    )


def test_get_solar_term_datetime_risshun():
    result = (
        get_solar_term_datetime(
            1984,
            "立春",
        )
    )

    assert result == datetime(
        1984,
        2,
        4,
        0,
        0,
    )


def test_get_solar_term_datetime_year_type_error():
    with pytest.raises(
        TypeError
    ):
        get_solar_term_datetime(
            "1984",
            "立春",
        )


def test_get_solar_term_datetime_year_value_error():
    with pytest.raises(
        ValueError
    ):
        get_solar_term_datetime(
            0,
            "立春",
        )


def test_get_solar_term_datetime_unknown_term():
    with pytest.raises(
        ValueError
    ):
        get_solar_term_datetime(
            1984,
            "不存在",
        )


# =========================================================
# SolarTerm
# =========================================================


def test_build_solar_term():
    result = build_solar_term(
        1984,
        "立秋",
    )

    assert isinstance(
        result,
        SolarTerm,
    )

    assert result.name == "立秋"

    assert result.datetime == datetime(
        1984,
        8,
        8,
        0,
        0,
    )

    assert (
        result.month_branch
        == "申"
    )

    assert (
        result.month_number
        == 7
    )

    assert (
        result.method
        == "fixed_solar_terms_v2"
    )

    assert (
        result.status
        == "provisional"
    )


def test_solar_term_to_dict():
    term = build_solar_term(
        1984,
        "小暑",
    )

    result = solar_term_to_dict(
        term
    )

    assert result == {
        "name": "小暑",
        "datetime": (
            "1984-07-07T00:00:00"
        ),
        "month_branch": "未",
        "month_number": 6,
        "method": (
            "fixed_solar_terms_v2"
        ),
        "status": "provisional",
    }


def test_solar_term_to_dict_type_error():
    with pytest.raises(
        TypeError
    ):
        solar_term_to_dict(
            {}
        )


# =========================================================
# Year terms
# =========================================================


def test_get_year_solar_terms_count():
    result = get_year_solar_terms(
        1984
    )

    assert len(
        result
    ) == 12


def test_get_year_solar_terms_order():
    result = get_year_solar_terms(
        1984
    )

    assert [
        term.name
        for term in result
    ] == [
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


def test_get_year_solar_terms_datetimes_sorted():
    result = get_year_solar_terms(
        1984
    )

    datetimes = [
        term.datetime
        for term in result
    ]

    assert datetimes == sorted(
        datetimes
    )


def test_get_year_solar_terms_dict():
    result = (
        get_year_solar_terms_dict(
            1984
        )
    )

    assert len(
        result
    ) == 12

    assert result[0][
        "name"
    ] == "小寒"

    assert result[-1][
        "name"
    ] == "大雪"

    assert isinstance(
        result[0][
            "datetime"
        ],
        str,
    )


# =========================================================
# Surrounding terms
# =========================================================


def test_get_surrounding_solar_terms():
    target = datetime(
        1984,
        7,
        10,
        22,
        45,
    )

    result = (
        get_surrounding_solar_terms(
            target
        )
    )

    assert len(
        result
    ) == 36

    years = {
        term.datetime.year
        for term in result
    }

    assert years == {
        1983,
        1984,
        1985,
    }


def test_get_surrounding_solar_terms_sorted():
    result = (
        get_surrounding_solar_terms(
            datetime(
                1984,
                7,
                10,
            )
        )
    )

    datetimes = [
        term.datetime
        for term in result
    ]

    assert datetimes == sorted(
        datetimes
    )


def test_get_surrounding_solar_terms_type_error():
    with pytest.raises(
        TypeError
    ):
        get_surrounding_solar_terms(
            "1984-07-10"
        )


# =========================================================
# Previous / next solar term
# =========================================================


def test_previous_solar_term_1984_07_10():
    target = datetime(
        1984,
        7,
        10,
        22,
        45,
    )

    result = (
        get_previous_solar_term(
            target
        )
    )

    assert result.name == "小暑"

    assert result.datetime == datetime(
        1984,
        7,
        7,
        0,
        0,
    )


def test_next_solar_term_1984_07_10():
    target = datetime(
        1984,
        7,
        10,
        22,
        45,
    )

    result = (
        get_next_solar_term(
            target
        )
    )

    assert result.name == "立秋"

    assert result.datetime == datetime(
        1984,
        8,
        8,
        0,
        0,
    )


def test_previous_term_boundary_exclusive():
    target = datetime(
        1984,
        7,
        7,
        0,
        0,
    )

    result = (
        get_previous_solar_term(
            target,
            inclusive=False,
        )
    )

    assert result.name == "芒種"


def test_previous_term_boundary_inclusive():
    target = datetime(
        1984,
        7,
        7,
        0,
        0,
    )

    result = (
        get_previous_solar_term(
            target,
            inclusive=True,
        )
    )

    assert result.name == "小暑"


def test_next_term_boundary_exclusive():
    target = datetime(
        1984,
        7,
        7,
        0,
        0,
    )

    result = (
        get_next_solar_term(
            target,
            inclusive=False,
        )
    )

    assert result.name == "立秋"


def test_next_term_boundary_inclusive():
    target = datetime(
        1984,
        7,
        7,
        0,
        0,
    )

    result = (
        get_next_solar_term(
            target,
            inclusive=True,
        )
    )

    assert result.name == "小暑"


def test_previous_solar_term_type_error():
    with pytest.raises(
        TypeError
    ):
        get_previous_solar_term(
            "1984-07-10"
        )


def test_next_solar_term_type_error():
    with pytest.raises(
        TypeError
    ):
        get_next_solar_term(
            "1984-07-10"
        )


# =========================================================
# Year boundary
# =========================================================


def test_previous_term_early_january_crosses_year():
    target = datetime(
        1984,
        1,
        2,
        12,
        0,
    )

    result = (
        get_previous_solar_term(
            target
        )
    )

    assert result.name == "大雪"

    assert result.datetime == datetime(
        1983,
        12,
        7,
        0,
        0,
    )


def test_next_term_late_december_crosses_year():
    target = datetime(
        1984,
        12,
        20,
        12,
        0,
    )

    result = (
        get_next_solar_term(
            target
        )
    )

    assert result.name == "小寒"

    assert result.datetime == datetime(
        1985,
        1,
        6,
        0,
        0,
    )


def test_current_term_early_january_is_previous_year_daxue():
    target = datetime(
        1984,
        1,
        2,
        12,
        0,
    )

    result = (
        get_current_solar_term(
            target
        )
    )

    assert result.name == "大雪"

    assert (
        result.month_branch
        == "子"
    )

    assert (
        result.month_number
        == 11
    )


# =========================================================
# Luck-pillar target term
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

    assert result.name == "立秋"

    assert result.datetime == datetime(
        1984,
        8,
        8,
        0,
        0,
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

    assert result.name == "小暑"

    assert result.datetime == datetime(
        1984,
        7,
        7,
        0,
        0,
    )


def test_luck_pillar_target_datetime_forward():
    birth = datetime(
        1984,
        7,
        10,
        22,
        45,
    )

    result = (
        get_luck_pillar_target_datetime(
            birth,
            "forward",
        )
    )

    assert result == datetime(
        1984,
        8,
        8,
        0,
        0,
    )


def test_luck_pillar_target_datetime_backward():
    birth = datetime(
        1984,
        7,
        10,
        22,
        45,
    )

    result = (
        get_luck_pillar_target_datetime(
            birth,
            "backward",
        )
    )

    assert result == datetime(
        1984,
        7,
        7,
        0,
        0,
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
            "sideways",
        )


def test_luck_pillar_target_birth_type_error():
    with pytest.raises(
        TypeError
    ):
        get_luck_pillar_target_term(
            "1984-07-10",
            "forward",
        )


# =========================================================
# Boundary behavior for luck pillar target
# =========================================================


def test_luck_pillar_target_exact_term_forward_uses_next():
    birth = datetime(
        1984,
        7,
        7,
        0,
        0,
    )

    result = (
        get_luck_pillar_target_term(
            birth,
            "forward",
        )
    )

    assert result.name == "立秋"


def test_luck_pillar_target_exact_term_backward_uses_previous():
    birth = datetime(
        1984,
        7,
        7,
        0,
        0,
    )

    result = (
        get_luck_pillar_target_term(
            birth,
            "backward",
        )
    )

    assert result.name == "芒種"


# =========================================================
# Current solar month
# =========================================================


def test_current_solar_term_before_shosho():
    target = datetime(
        1984,
        7,
        6,
        23,
        59,
    )

    result = (
        get_current_solar_term(
            target
        )
    )

    assert result.name == "芒種"

    assert (
        result.month_branch
        == "午"
    )

    assert (
        result.month_number
        == 5
    )


def test_current_solar_term_at_shosho():
    target = datetime(
        1984,
        7,
        7,
        0,
        0,
    )

    result = (
        get_current_solar_term(
            target
        )
    )

    assert result.name == "小暑"

    assert (
        result.month_branch
        == "未"
    )

    assert (
        result.month_number
        == 6
    )


def test_current_solar_term_after_shosho():
    target = datetime(
        1984,
        7,
        10,
        22,
        45,
    )

    result = (
        get_current_solar_term(
            target
        )
    )

    assert result.name == "小暑"


@pytest.mark.parametrize(
    (
        "target",
        "expected_branch",
    ),
    [
        (
            datetime(
                1984,
                2,
                4,
                0,
                0,
            ),
            "寅",
        ),
        (
            datetime(
                1984,
                3,
                6,
                0,
                0,
            ),
            "卯",
        ),
        (
            datetime(
                1984,
                7,
                10,
                22,
                45,
            ),
            "未",
        ),
        (
            datetime(
                1984,
                12,
                7,
                0,
                0,
            ),
            "子",
        ),
    ],
)
def test_get_month_branch_by_datetime(
    target,
    expected_branch,
):
    assert (
        get_month_branch_by_datetime(
            target
        )
        == expected_branch
    )


@pytest.mark.parametrize(
    (
        "target",
        "expected_number",
    ),
    [
        (
            datetime(
                1984,
                2,
                4,
            ),
            1,
        ),
        (
            datetime(
                1984,
                3,
                6,
            ),
            2,
        ),
        (
            datetime(
                1984,
                7,
                10,
            ),
            6,
        ),
        (
            datetime(
                1984,
                12,
                7,
            ),
            11,
        ),
        (
            datetime(
                1985,
                1,
                6,
            ),
            12,
        ),
    ],
)
def test_get_month_number_by_datetime(
    target,
    expected_number,
):
    assert (
        get_month_number_by_datetime(
            target
        )
        == expected_number
    )


# =========================================================
# Distance helpers
# =========================================================


def test_distance_to_previous_term_days():
    target = datetime(
        1984,
        7,
        10,
        0,
        0,
    )

    result = (
        get_distance_to_previous_term_days(
            target
        )
    )

    assert result == pytest.approx(
        3.0
    )


def test_distance_to_next_term_days():
    target = datetime(
        1984,
        7,
        10,
        0,
        0,
    )

    result = (
        get_distance_to_next_term_days(
            target
        )
    )

    assert result == pytest.approx(
        29.0
    )


def test_distance_to_previous_term_days_fractional():
    target = datetime(
        1984,
        7,
        10,
        12,
        0,
    )

    result = (
        get_distance_to_previous_term_days(
            target
        )
    )

    assert result == pytest.approx(
        3.5
    )


def test_distance_to_next_term_days_fractional():
    target = datetime(
        1984,
        7,
        10,
        12,
        0,
    )

    result = (
        get_distance_to_next_term_days(
            target
        )
    )

    assert result == pytest.approx(
        28.5
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
        == "fixed_solar_terms_v2"
    )

    assert (
        result[
            "status"
        ]
        == "provisional"
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
        == "fixed_day_time"
    )

    assert (
        result[
            "timezone"
        ]
        == "naive_local_datetime"
    )

    assert (
        "luck_pillar_target_term"
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


# =========================================================
# Compatibility aliases
# =========================================================


def test_previous_term_alias():
    target = datetime(
        1984,
        7,
        10,
        22,
        45,
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
        22,
        45,
    )

    assert (
        get_next_term(
            target
        )
        == get_next_solar_term(
            target
        )
    )


def test_target_term_for_luck_pillars_alias_forward():
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
            "forward",
        )
        == get_luck_pillar_target_term(
            birth,
            "forward",
        )
    )


def test_target_term_for_luck_pillars_alias_backward():
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
            "backward",
        )
        == get_luck_pillar_target_term(
            birth,
            "backward",
        )
    )


# =========================================================
# Regression: 1984/07/10 22:45
# =========================================================


def test_regression_1984_07_10_2245_current_month():
    birth = datetime(
        1984,
        7,
        10,
        22,
        45,
    )

    current = (
        get_current_solar_term(
            birth
        )
    )

    assert current.name == "小暑"

    assert (
        current.month_branch
        == "未"
    )

    assert (
        current.month_number
        == 6
    )


def test_regression_1984_07_10_2245_previous_next():
    birth = datetime(
        1984,
        7,
        10,
        22,
        45,
    )

    previous = (
        get_previous_solar_term(
            birth
        )
    )

    next_term = (
        get_next_solar_term(
            birth
        )
    )

    assert previous.name == "小暑"

    assert next_term.name == "立秋"

    assert (
        previous.datetime
        < birth
        < next_term.datetime
    )


def test_regression_1984_07_10_2245_luck_targets():
    birth = datetime(
        1984,
        7,
        10,
        22,
        45,
    )

    forward = (
        get_luck_pillar_target_term(
            birth,
            "forward",
        )
    )

    backward = (
        get_luck_pillar_target_term(
            birth,
            "backward",
        )
    )

    assert forward.name == "立秋"

    assert backward.name == "小暑"


# =========================================================
# Structural consistency
# =========================================================


def test_all_solar_terms_have_required_keys():
    required_keys = {
        "name",
        "month",
        "day",
        "hour",
        "minute",
        "month_branch",
        "month_number",
    }

    for term in SOLAR_TERMS:
        assert required_keys.issubset(
            term.keys()
        )


def test_all_month_numbers_are_1_to_12():
    numbers = [
        term[
            "month_number"
        ]
        for term in SOLAR_TERMS
    ]

    assert sorted(
        numbers
    ) == list(
        range(
            1,
            13,
        )
    )


def test_all_month_branches_are_unique():
    branches = [
        term[
            "month_branch"
        ]
        for term in SOLAR_TERMS
    ]

    assert len(
        branches
    ) == 12

    assert len(
        set(
            branches
        )
    ) == 12


def test_month_number_to_branch_mapping():
    mapping = {
        term[
            "month_number"
        ]: term[
            "month_branch"
        ]
        for term in SOLAR_TERMS
    }

    assert mapping == {
        1: "寅",
        2: "卯",
        3: "辰",
        4: "巳",
        5: "午",
        6: "未",
        7: "申",
        8: "酉",
        9: "戌",
        10: "亥",
        11: "子",
        12: "丑",
    }
