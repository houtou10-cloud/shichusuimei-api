"""
tests/test_current_luck.py

engine/current_luck.py の単体テスト。

検証対象
--------
- exact age
- calendar age
- timezone-aware / naive 混在
- 起運前
- 現在大運
- 大運切替境界
- 最終大運
- 大運範囲終了後
- previous / current / next
- 進行率
- 10年間隔
- alias
- 元データ非破壊
"""

from datetime import datetime, timezone

import pytest

from engine.current_luck import (
    DAYS_PER_YEAR,
    SUPPORTED_LUCK_METHODS,
    build_luck_pillar_view,
    calculate_calendar_age,
    calculate_current_luck,
    calculate_exact_age,
    calculate_luck_progress,
    evaluate_current_luck,
    find_current_luck_index,
    find_next_luck_index,
    get_current_luck_pillar,
    is_age_in_luck_pillar,
    normalize_datetime_pair,
)


# =========================================================
# Fixtures
# =========================================================


def make_luck_pillar(
    index,
    ganzhi,
    start_age,
    end_age,
):
    return {
        "index": index,
        "ganzhi": ganzhi,
        "stem": ganzhi[0],
        "branch": ganzhi[1],
        "start_age": start_age,
        "end_age": end_age,
    }


def make_luck_pillars():
    return {
        "pillars": [
            make_luck_pillar(
                1,
                "甲申",
                5.0,
                15.0,
            ),
            make_luck_pillar(
                2,
                "乙酉",
                15.0,
                25.0,
            ),
            make_luck_pillar(
                3,
                "丙戌",
                25.0,
                35.0,
            ),
            make_luck_pillar(
                4,
                "丁亥",
                35.0,
                45.0,
            ),
            make_luck_pillar(
                5,
                "戊子",
                45.0,
                55.0,
            ),
        ],
        "method": "luck_pillars_v2",
        "status": "provisional_luck_pillars_v2",
    }


def make_birth_datetime():
    return datetime(
        2000,
        1,
        1,
        0,
        0,
    )


# =========================================================
# Constants
# =========================================================


def test_days_per_year():
    assert (
        DAYS_PER_YEAR
        == 365.2425
    )


def test_supported_luck_methods():
    assert (
        "luck_pillars_v1"
        in SUPPORTED_LUCK_METHODS
    )

    assert (
        "luck_pillars_v2"
        in SUPPORTED_LUCK_METHODS
    )


# =========================================================
# normalize_datetime_pair
# =========================================================


def test_normalize_datetime_pair_naive():
    first = datetime(
        2000,
        1,
        1,
    )

    second = datetime(
        2020,
        1,
        1,
    )

    result_first, result_second = (
        normalize_datetime_pair(
            first,
            second,
        )
    )

    assert result_first == first
    assert result_second == second


def test_normalize_datetime_pair_aware():
    first = datetime(
        2000,
        1,
        1,
        tzinfo=timezone.utc,
    )

    second = datetime(
        2020,
        1,
        1,
        tzinfo=timezone.utc,
    )

    result_first, result_second = (
        normalize_datetime_pair(
            first,
            second,
        )
    )

    assert (
        result_first.tzinfo
        is not None
    )

    assert (
        result_second.tzinfo
        is not None
    )


def test_normalize_datetime_pair_mixed_removes_tzinfo():
    first = datetime(
        2000,
        1,
        1,
        tzinfo=timezone.utc,
    )

    second = datetime(
        2020,
        1,
        1,
    )

    result_first, result_second = (
        normalize_datetime_pair(
            first,
            second,
        )
    )

    assert (
        result_first.tzinfo
        is None
    )

    assert (
        result_second.tzinfo
        is None
    )


def test_normalize_datetime_pair_invalid_first():
    with pytest.raises(
        TypeError
    ):
        normalize_datetime_pair(
            "2000-01-01",
            datetime(
                2020,
                1,
                1,
            ),
        )


# =========================================================
# Exact age
# =========================================================


def test_calculate_exact_age_zero():
    birth = make_birth_datetime()

    assert (
        calculate_exact_age(
            birth,
            birth,
        )
        == 0.0
    )


def test_calculate_exact_age_one_year():
    birth = datetime(
        2000,
        1,
        1,
    )

    target = (
        birth
        + pytest.importorskip(
            "datetime"
        )
        if False
        else None
    )

    target = datetime(
        2000,
        12,
        31,
        5,
        49,
        7,
    )

    age = calculate_exact_age(
        birth,
        target,
    )

    assert age == pytest.approx(
        1.0,
        abs=0.001,
    )


def test_calculate_exact_age_target_before_birth():
    with pytest.raises(
        ValueError
    ):
        calculate_exact_age(
            datetime(
                2000,
                1,
                2,
            ),
            datetime(
                2000,
                1,
                1,
            ),
        )


# =========================================================
# Calendar age
# =========================================================


def test_calculate_calendar_age_on_birthday():
    birth = datetime(
        2000,
        7,
        10,
        12,
        0,
    )

    target = datetime(
        2025,
        7,
        10,
        12,
        0,
    )

    assert (
        calculate_calendar_age(
            birth,
            target,
        )
        == 25
    )


def test_calculate_calendar_age_before_birthday():
    birth = datetime(
        2000,
        7,
        10,
        12,
        0,
    )

    target = datetime(
        2025,
        7,
        10,
        11,
        59,
    )

    assert (
        calculate_calendar_age(
            birth,
            target,
        )
        == 24
    )


def test_calculate_calendar_age_after_birthday():
    birth = datetime(
        2000,
        7,
        10,
        12,
        0,
    )

    target = datetime(
        2025,
        7,
        11,
        0,
        0,
    )

    assert (
        calculate_calendar_age(
            birth,
            target,
        )
        == 25
    )


# =========================================================
# is_age_in_luck_pillar
# =========================================================


def test_age_at_start_is_inside():
    pillar = make_luck_pillar(
        1,
        "甲申",
        5.0,
        15.0,
    )

    assert (
        is_age_in_luck_pillar(
            5.0,
            pillar,
        )
        is True
    )


def test_age_before_start_is_outside():
    pillar = make_luck_pillar(
        1,
        "甲申",
        5.0,
        15.0,
    )

    assert (
        is_age_in_luck_pillar(
            4.999,
            pillar,
        )
        is False
    )


def test_age_before_end_is_inside():
    pillar = make_luck_pillar(
        1,
        "甲申",
        5.0,
        15.0,
    )

    assert (
        is_age_in_luck_pillar(
            14.999,
            pillar,
        )
        is True
    )


def test_age_at_end_is_outside():
    pillar = make_luck_pillar(
        1,
        "甲申",
        5.0,
        15.0,
    )

    assert (
        is_age_in_luck_pillar(
            15.0,
            pillar,
        )
        is False
    )


# =========================================================
# Current / next index
# =========================================================


def test_find_current_luck_index():
    pillars = make_luck_pillars()[
        "pillars"
    ]

    assert (
        find_current_luck_index(
            27.0,
            pillars,
        )
        == 2
    )


def test_find_current_luck_index_before_first():
    pillars = make_luck_pillars()[
        "pillars"
    ]

    assert (
        find_current_luck_index(
            4.0,
            pillars,
        )
        is None
    )


def test_find_current_luck_index_boundary_moves_to_next():
    pillars = make_luck_pillars()[
        "pillars"
    ]

    assert (
        find_current_luck_index(
            15.0,
            pillars,
        )
        == 1
    )


def test_find_next_luck_index_before_first():
    pillars = make_luck_pillars()[
        "pillars"
    ]

    assert (
        find_next_luck_index(
            2.0,
            pillars,
        )
        == 0
    )


def test_find_next_luck_index_inside_period():
    pillars = make_luck_pillars()[
        "pillars"
    ]

    assert (
        find_next_luck_index(
            27.0,
            pillars,
        )
        == 3
    )


def test_find_next_luck_index_after_last():
    pillars = make_luck_pillars()[
        "pillars"
    ]

    assert (
        find_next_luck_index(
            60.0,
            pillars,
        )
        is None
    )


# =========================================================
# build_luck_pillar_view
# =========================================================


def test_build_luck_pillar_view_current():
    original = make_luck_pillar(
        1,
        "甲申",
        5.0,
        15.0,
    )

    result = build_luck_pillar_view(
        original,
        is_current=True,
    )

    assert (
        result[
            "is_current"
        ]
        is True
    )

    assert (
        result[
            "is_previous"
        ]
        is False
    )

    assert (
        result[
            "is_next"
        ]
        is False
    )


def test_build_luck_pillar_view_does_not_mutate_original():
    original = make_luck_pillar(
        1,
        "甲申",
        5.0,
        15.0,
    )

    build_luck_pillar_view(
        original,
        is_current=True,
    )

    assert (
        "is_current"
        not in original
    )


def test_build_luck_pillar_view_none():
    assert (
        build_luck_pillar_view(
            None
        )
        is None
    )


# =========================================================
# Progress
# =========================================================


def test_calculate_luck_progress_start():
    pillar = make_luck_pillar(
        1,
        "甲申",
        5.0,
        15.0,
    )

    result = calculate_luck_progress(
        5.0,
        pillar,
    )

    assert (
        result[
            "progress_percent"
        ]
        == 0.0
    )

    assert (
        result[
            "remaining_years"
        ]
        == 10.0
    )


def test_calculate_luck_progress_middle():
    pillar = make_luck_pillar(
        1,
        "甲申",
        5.0,
        15.0,
    )

    result = calculate_luck_progress(
        10.0,
        pillar,
    )

    assert (
        result[
            "progress_percent"
        ]
        == 50.0
    )

    assert (
        result[
            "elapsed_years"
        ]
        == 5.0
    )

    assert (
        result[
            "remaining_years"
        ]
        == 5.0
    )


def test_calculate_luck_progress_near_end():
    pillar = make_luck_pillar(
        1,
        "甲申",
        5.0,
        15.0,
    )

    result = calculate_luck_progress(
        14.0,
        pillar,
    )

    assert (
        result[
            "progress_percent"
        ]
        == 90.0
    )


# =========================================================
# Main evaluator: before first luck
# =========================================================


def test_evaluate_current_luck_before_first():
    birth = make_birth_datetime()

    target = datetime(
        2002,
        1,
        1,
    )

    result = evaluate_current_luck(
        birth_datetime=birth,
        target_datetime=target,
        luck_pillars=make_luck_pillars(),
    )

    assert (
        result[
            "has_current_luck"
        ]
        is False
    )

    assert (
        result[
            "phase"
        ]
        == "before_first_luck"
    )

    assert (
        result[
            "current_luck_pillar"
        ]
        is None
    )

    assert (
        result[
            "previous_luck_pillar"
        ]
        is None
    )

    assert (
        result[
            "next_luck_pillar"
        ][
            "ganzhi"
        ]
        == "甲申"
    )

    assert (
        result[
            "next_luck_pillar"
        ][
            "is_next"
        ]
        is True
    )


# =========================================================
# Main evaluator: current luck
# =========================================================


def test_evaluate_current_luck_middle():
    birth = make_birth_datetime()

    target = datetime(
        2027,
        1,
        1,
    )

    result = evaluate_current_luck(
        birth_datetime=birth,
        target_datetime=target,
        luck_pillars=make_luck_pillars(),
    )

    assert (
        result[
            "has_current_luck"
        ]
        is True
    )

    assert (
        result[
            "phase"
        ]
        == "in_luck_pillar"
    )

    assert (
        result[
            "current_luck_pillar"
        ][
            "ganzhi"
        ]
        == "丙戌"
    )

    assert (
        result[
            "previous_luck_pillar"
        ][
            "ganzhi"
        ]
        == "乙酉"
    )

    assert (
        result[
            "next_luck_pillar"
        ][
            "ganzhi"
        ]
        == "丁亥"
    )


def test_current_luck_flags():
    birth = make_birth_datetime()

    target = datetime(
        2027,
        1,
        1,
    )

    result = evaluate_current_luck(
        birth_datetime=birth,
        target_datetime=target,
        luck_pillars=make_luck_pillars(),
    )

    assert (
        result[
            "current_luck_pillar"
        ][
            "is_current"
        ]
        is True
    )

    assert (
        result[
            "previous_luck_pillar"
        ][
            "is_previous"
        ]
        is True
    )

    assert (
        result[
            "next_luck_pillar"
        ][
            "is_next"
        ]
        is True
    )


# =========================================================
# Exact boundary
# =========================================================


def test_exact_age_boundary_moves_to_next_pillar():
    pillars = make_luck_pillars()[
        "pillars"
    ]

    assert (
        find_current_luck_index(
            35.0,
            pillars,
        )
        == 3
    )


def test_exact_age_boundary_not_previous_pillar():
    pillars = make_luck_pillars()[
        "pillars"
    ]

    assert (
        is_age_in_luck_pillar(
            35.0,
            pillars[2],
        )
        is False
    )

    assert (
        is_age_in_luck_pillar(
            35.0,
            pillars[3],
        )
        is True
    )


# =========================================================
# Last luck
# =========================================================


def test_evaluate_last_luck_has_no_next():
    birth = make_birth_datetime()

    target = datetime(
        2050,
        1,
        1,
    )

    result = evaluate_current_luck(
        birth_datetime=birth,
        target_datetime=target,
        luck_pillars=make_luck_pillars(),
    )

    assert (
        result[
            "has_current_luck"
        ]
        is True
    )

    assert (
        result[
            "current_luck_pillar"
        ][
            "ganzhi"
        ]
        == "戊子"
    )

    assert (
        result[
            "next_luck_pillar"
        ]
        is None
    )


# =========================================================
# After last luck
# =========================================================


def test_evaluate_after_last_luck():
    birth = make_birth_datetime()

    target = datetime(
        2070,
        1,
        1,
    )

    result = evaluate_current_luck(
        birth_datetime=birth,
        target_datetime=target,
        luck_pillars=make_luck_pillars(),
    )

    assert (
        result[
            "has_current_luck"
        ]
        is False
    )

    assert (
        result[
            "phase"
        ]
        == "after_last_luck"
    )

    assert (
        result[
            "current_luck_pillar"
        ]
        is None
    )

    assert (
        result[
            "previous_luck_pillar"
        ][
            "ganzhi"
        ]
        == "戊子"
    )

    assert (
        result[
            "next_luck_pillar"
        ]
        is None
    )


# =========================================================
# Metadata
# =========================================================


def test_current_luck_metadata():
    result = evaluate_current_luck(
        birth_datetime=make_birth_datetime(),
        target_datetime=datetime(
            2027,
            1,
            1,
        ),
        luck_pillars=make_luck_pillars(),
    )

    assert (
        result[
            "method"
        ]
        == "current_luck_v1"
    )

    assert (
        result[
            "status"
        ]
        == "current_luck_resolved"
    )

    assert isinstance(
        result[
            "notes"
        ],
        list,
    )

    assert (
        len(
            result[
                "notes"
            ]
        )
        >= 1
    )


def test_current_luck_progress_exists():
    result = evaluate_current_luck(
        birth_datetime=make_birth_datetime(),
        target_datetime=datetime(
            2027,
            1,
            1,
        ),
        luck_pillars=make_luck_pillars(),
    )

    assert isinstance(
        result[
            "progress"
        ],
        dict,
    )

    assert (
        0.0
        <= result[
            "progress"
        ][
            "progress_percent"
        ]
        <= 100.0
    )


# =========================================================
# Alias
# =========================================================


def test_calculate_current_luck_alias():
    kwargs = {
        "birth_datetime": (
            make_birth_datetime()
        ),
        "target_datetime": datetime(
            2027,
            1,
            1,
        ),
        "luck_pillars": (
            make_luck_pillars()
        ),
    }

    assert (
        calculate_current_luck(
            **kwargs
        )
        == evaluate_current_luck(
            **kwargs
        )
    )


def test_get_current_luck_pillar_alias():
    result = get_current_luck_pillar(
        birth_datetime=(
            make_birth_datetime()
        ),
        target_datetime=datetime(
            2027,
            1,
            1,
        ),
        luck_pillars=(
            make_luck_pillars()
        ),
    )

    assert (
        result[
            "ganzhi"
        ]
        == "丙戌"
    )

    assert (
        result[
            "is_current"
        ]
        is True
    )


# =========================================================
# Validation
# =========================================================


def test_evaluate_current_luck_invalid_luck_pillars_type():
    with pytest.raises(
        TypeError
    ):
        evaluate_current_luck(
            birth_datetime=(
                make_birth_datetime()
            ),
            target_datetime=datetime(
                2027,
                1,
                1,
            ),
            luck_pillars=[],
        )


def test_evaluate_current_luck_missing_pillars():
    with pytest.raises(
        ValueError
    ):
        evaluate_current_luck(
            birth_datetime=(
                make_birth_datetime()
            ),
            target_datetime=datetime(
                2027,
                1,
                1,
            ),
            luck_pillars={},
        )


def test_evaluate_current_luck_empty_pillars():
    with pytest.raises(
        ValueError
    ):
        evaluate_current_luck(
            birth_datetime=(
                make_birth_datetime()
            ),
            target_datetime=datetime(
                2027,
                1,
                1,
            ),
            luck_pillars={
                "pillars": [],
            },
        )


def test_evaluate_current_luck_missing_required_pillar_key():
    luck = {
        "pillars": [
            {
                "index": 1,
                "ganzhi": "甲申",
            }
        ],
    }

    with pytest.raises(
        ValueError
    ):
        evaluate_current_luck(
            birth_datetime=(
                make_birth_datetime()
            ),
            target_datetime=datetime(
                2027,
                1,
                1,
            ),
            luck_pillars=luck,
        )


# =========================================================
# Ten-year interval regression
# =========================================================


def test_fixture_luck_pillars_are_ten_year_intervals():
    pillars = make_luck_pillars()[
        "pillars"
    ]

    for pillar in pillars:
        assert (
            pillar[
                "end_age"
            ]
            - pillar[
                "start_age"
            ]
            == 10.0
        )


def test_fixture_luck_pillars_are_contiguous():
    pillars = make_luck_pillars()[
        "pillars"
    ]

    for previous, current in zip(
        pillars,
        pillars[1:],
    ):
        assert (
            previous[
                "end_age"
            ]
            == current[
                "start_age"
            ]
        )


# =========================================================
# Real-style regression
# =========================================================


def test_1985_verified_style_current_luck():
    """
    実命式連携前の代表回帰ケース。

    1985-07-17 21:50 生まれとして、
    仮に第1大運が約7歳開始なら、
    2026年時点では第4大運付近になることを
    構造として確認する。

    正確な起運年齢そのものは
    luck_pillars_v2 / solar_terms_v2 側で検証する。
    """

    birth = datetime(
        1985,
        7,
        17,
        21,
        50,
    )

    luck = {
        "pillars": [
            make_luck_pillar(
                1,
                "甲申",
                7.0,
                17.0,
            ),
            make_luck_pillar(
                2,
                "乙酉",
                17.0,
                27.0,
            ),
            make_luck_pillar(
                3,
                "丙戌",
                27.0,
                37.0,
            ),
            make_luck_pillar(
                4,
                "丁亥",
                37.0,
                47.0,
            ),
            make_luck_pillar(
                5,
                "戊子",
                47.0,
                57.0,
            ),
        ],
        "method": (
            "luck_pillars_v2"
        ),
    }

    result = evaluate_current_luck(
        birth_datetime=birth,
        target_datetime=datetime(
            2026,
            8,
            10,
            15,
            24,
        ),
        luck_pillars=luck,
    )

    assert (
        result[
            "has_current_luck"
        ]
        is True
    )

    assert (
        result[
            "current_luck_pillar"
        ][
            "index"
        ]
        == 4
    )

    assert (
        result[
            "current_luck_pillar"
        ][
            "ganzhi"
        ]
        == "丁亥"
    )
