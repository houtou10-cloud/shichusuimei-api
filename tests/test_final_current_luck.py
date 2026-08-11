"""
tests/test_final_current_luck.py

current_luck_v1 最終回帰テスト。

検証対象:
- datetime 正規化
- 小数年齢
- 満年齢
- 大運区間判定
- 現在大運検索
- 次大運検索
- 大運表示データ
- 大運進行率
- 起運前
- 大運中
- 大運切替境界
- 最終大運
- 生成済み大運終了後
- 前大運 / 現在大運 / 次大運
- timezone-aware / naive
- calculate_current_luck
- get_current_luck_pillar
- 不正入力
- luck_pillars_v2 との統合

重要ルール:
    start_age <= age < end_age

終了年齢を排他的にすることで、
大運切替点で二重判定しない。
"""

from copy import deepcopy
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

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

from engine.luck_pillars import (
    calculate_luck_pillars,
)


JST = ZoneInfo("Asia/Tokyo")


# ============================================================
# Helpers
# ============================================================


def make_pillar(
    index,
    ganzhi,
    stem,
    branch,
    start_age,
    end_age,
):
    return {
        "index": index,
        "ganzhi": ganzhi,
        "stem": stem,
        "branch": branch,
        "start_age": start_age,
        "end_age": end_age,
    }


def make_simple_luck_pillars():
    """
    テスト専用の単純な大運。

    第1大運:
        2 <= age < 12

    第2大運:
        12 <= age < 22

    第3大運:
        22 <= age < 32
    """

    return {
        "method": "luck_pillars_v2",
        "status": (
            "provisional_luck_pillars_v2"
        ),
        "pillars": [
            make_pillar(
                1,
                "壬申",
                "壬",
                "申",
                2.0,
                12.0,
            ),
            make_pillar(
                2,
                "癸酉",
                "癸",
                "酉",
                12.0,
                22.0,
            ),
            make_pillar(
                3,
                "甲戌",
                "甲",
                "戌",
                22.0,
                32.0,
            ),
        ],
    }


def datetime_at_age(
    birth_datetime,
    age,
):
    """
    current_luck.py の小数年齢計算と
    同じ DAYS_PER_YEAR を使って
    指定年齢相当の日時を作る。
    """

    return (
        birth_datetime
        + timedelta(
            days=(
                age
                * DAYS_PER_YEAR
            )
        )
    )


def make_real_luck_pillars(
    count=10,
):
    """
    luck_pillars_v2 と統合するための
    回帰用データ。

    甲年男性なので順行。
    月柱 辛未。

    外部節入りを6日後に固定するため、
    三日一年法で2歳起運。
    """

    return calculate_luck_pillars(
        year_stem="甲",
        month_ganzhi="辛未",
        day_master_stem="乙",
        gender="male",
        birth_datetime=datetime(
            1984,
            7,
            22,
            4,
            15,
        ),
        target_term_datetime=datetime(
            1984,
            7,
            28,
            4,
            15,
        ),
        count=count,
    )


# ============================================================
# Constants
# ============================================================


def test_days_per_year():
    assert DAYS_PER_YEAR == 365.2425


def test_supported_luck_methods():
    assert "luck_pillars_v1" in (
        SUPPORTED_LUCK_METHODS
    )

    assert "luck_pillars_v2" in (
        SUPPORTED_LUCK_METHODS
    )


# ============================================================
# normalize_datetime_pair
# ============================================================


def test_normalize_naive_pair():
    first = datetime(
        2000,
        1,
        1,
        12,
        0,
    )

    second = datetime(
        2000,
        1,
        2,
        12,
        0,
    )

    result_first, result_second = (
        normalize_datetime_pair(
            first,
            second,
        )
    )

    assert result_first == first
    assert result_second == second

    assert result_first.tzinfo is None
    assert result_second.tzinfo is None


def test_normalize_aware_pair():
    first = datetime(
        2000,
        1,
        1,
        12,
        0,
        tzinfo=JST,
    )

    second = datetime(
        2000,
        1,
        2,
        12,
        0,
        tzinfo=JST,
    )

    result_first, result_second = (
        normalize_datetime_pair(
            first,
            second,
        )
    )

    assert result_first == first
    assert result_second == second

    assert result_first.tzinfo is not None
    assert result_second.tzinfo is not None


def test_normalize_mixed_pair_removes_timezone():
    first = datetime(
        2000,
        1,
        1,
        12,
        0,
        tzinfo=JST,
    )

    second = datetime(
        2000,
        1,
        2,
        12,
        0,
    )

    result_first, result_second = (
        normalize_datetime_pair(
            first,
            second,
        )
    )

    assert result_first.tzinfo is None
    assert result_second.tzinfo is None

    assert result_first == datetime(
        2000,
        1,
        1,
        12,
        0,
    )

    assert result_second == datetime(
        2000,
        1,
        2,
        12,
        0,
    )


def test_normalize_mixed_pair_reverse():
    first = datetime(
        2000,
        1,
        1,
        12,
        0,
    )

    second = datetime(
        2000,
        1,
        2,
        12,
        0,
        tzinfo=JST,
    )

    result_first, result_second = (
        normalize_datetime_pair(
            first,
            second,
        )
    )

    assert result_first.tzinfo is None
    assert result_second.tzinfo is None


@pytest.mark.parametrize(
    "first,second",
    [
        (
            "2000-01-01",
            datetime(
                2000,
                1,
                2,
            ),
        ),
        (
            datetime(
                2000,
                1,
                1,
            ),
            "2000-01-02",
        ),
    ],
)
def test_normalize_invalid_datetime(
    first,
    second,
):
    with pytest.raises(TypeError):
        normalize_datetime_pair(
            first,
            second,
        )


# ============================================================
# calculate_exact_age
# ============================================================


def test_exact_age_at_birth():
    birth = datetime(
        2000,
        1,
        1,
    )

    assert (
        calculate_exact_age(
            birth,
            birth,
        )
        == 0.0
    )


def test_exact_age_one_engine_year():
    birth = datetime(
        2000,
        1,
        1,
    )

    target = (
        birth
        + timedelta(
            days=DAYS_PER_YEAR
        )
    )

    assert (
        calculate_exact_age(
            birth,
            target,
        )
        == pytest.approx(
            1.0,
            abs=1e-6,
        )
    )


def test_exact_age_two_engine_years():
    birth = datetime(
        2000,
        1,
        1,
    )

    target = datetime_at_age(
        birth,
        2.0,
    )

    assert (
        calculate_exact_age(
            birth,
            target,
        )
        == pytest.approx(
            2.0,
            abs=1e-6,
        )
    )


def test_exact_age_fractional():
    birth = datetime(
        2000,
        1,
        1,
    )

    target = datetime_at_age(
        birth,
        10.5,
    )

    assert (
        calculate_exact_age(
            birth,
            target,
        )
        == pytest.approx(
            10.5,
            abs=1e-6,
        )
    )


def test_exact_age_mixed_timezone():
    birth = datetime(
        2000,
        1,
        1,
        tzinfo=JST,
    )

    target = datetime(
        2000,
        1,
        2,
    )

    result = calculate_exact_age(
        birth,
        target,
    )

    expected = (
        1.0
        / DAYS_PER_YEAR
    )

    assert result == pytest.approx(
        expected,
        abs=1e-6,
    )


def test_exact_age_before_birth():
    birth = datetime(
        2000,
        1,
        2,
    )

    target = datetime(
        2000,
        1,
        1,
    )

    with pytest.raises(ValueError):
        calculate_exact_age(
            birth,
            target,
        )


def test_exact_age_invalid_birth():
    with pytest.raises(TypeError):
        calculate_exact_age(
            "2000-01-01",
            datetime(
                2000,
                1,
                2,
            ),
        )


def test_exact_age_invalid_target():
    with pytest.raises(TypeError):
        calculate_exact_age(
            datetime(
                2000,
                1,
                1,
            ),
            "2000-01-02",
        )


# ============================================================
# calculate_calendar_age
# ============================================================


def test_calendar_age_at_birth():
    birth = datetime(
        2000,
        7,
        10,
        12,
        0,
    )

    assert (
        calculate_calendar_age(
            birth,
            birth,
        )
        == 0
    )


def test_calendar_age_before_birthday():
    birth = datetime(
        2000,
        7,
        10,
        12,
        0,
    )

    target = datetime(
        2020,
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
        == 19
    )


def test_calendar_age_exact_birthday():
    birth = datetime(
        2000,
        7,
        10,
        12,
        0,
    )

    target = datetime(
        2020,
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
        == 20
    )


def test_calendar_age_after_birthday():
    birth = datetime(
        2000,
        7,
        10,
        12,
        0,
    )

    target = datetime(
        2020,
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
        == 20
    )


def test_calendar_age_before_birth():
    with pytest.raises(ValueError):
        calculate_calendar_age(
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


# ============================================================
# is_age_in_luck_pillar
# ============================================================


@pytest.fixture
def first_pillar():
    return make_pillar(
        1,
        "壬申",
        "壬",
        "申",
        2.0,
        12.0,
    )


def test_age_before_pillar(
    first_pillar,
):
    assert (
        is_age_in_luck_pillar(
            1.999,
            first_pillar,
        )
        is False
    )


def test_age_at_start_is_inside(
    first_pillar,
):
    assert (
        is_age_in_luck_pillar(
            2.0,
            first_pillar,
        )
        is True
    )


def test_age_middle_is_inside(
    first_pillar,
):
    assert (
        is_age_in_luck_pillar(
            7.0,
            first_pillar,
        )
        is True
    )


def test_age_just_before_end_is_inside(
    first_pillar,
):
    assert (
        is_age_in_luck_pillar(
            11.999999,
            first_pillar,
        )
        is True
    )


def test_age_at_end_is_outside(
    first_pillar,
):
    assert (
        is_age_in_luck_pillar(
            12.0,
            first_pillar,
        )
        is False
    )


def test_age_after_end_is_outside(
    first_pillar,
):
    assert (
        is_age_in_luck_pillar(
            12.1,
            first_pillar,
        )
        is False
    )


@pytest.mark.parametrize(
    "age",
    [
        "2",
        None,
        True,
        False,
    ],
)
def test_is_age_in_luck_pillar_invalid_age(
    age,
    first_pillar,
):
    with pytest.raises(TypeError):
        is_age_in_luck_pillar(
            age,
            first_pillar,
        )


def test_invalid_start_age_type():
    pillar = make_pillar(
        1,
        "壬申",
        "壬",
        "申",
        "2",
        12.0,
    )

    with pytest.raises(TypeError):
        is_age_in_luck_pillar(
            5.0,
            pillar,
        )


def test_invalid_end_age_type():
    pillar = make_pillar(
        1,
        "壬申",
        "壬",
        "申",
        2.0,
        "12",
    )

    with pytest.raises(TypeError):
        is_age_in_luck_pillar(
            5.0,
            pillar,
        )


def test_negative_start_age():
    pillar = make_pillar(
        1,
        "壬申",
        "壬",
        "申",
        -1.0,
        10.0,
    )

    with pytest.raises(ValueError):
        is_age_in_luck_pillar(
            5.0,
            pillar,
        )


def test_end_age_equal_start_age():
    pillar = make_pillar(
        1,
        "壬申",
        "壬",
        "申",
        2.0,
        2.0,
    )

    with pytest.raises(ValueError):
        is_age_in_luck_pillar(
            2.0,
            pillar,
        )


# ============================================================
# find_current_luck_index
# ============================================================


def test_find_current_before_first():
    pillars = (
        make_simple_luck_pillars()[
            "pillars"
        ]
    )

    assert (
        find_current_luck_index(
            1.0,
            pillars,
        )
        is None
    )


def test_find_current_first():
    pillars = (
        make_simple_luck_pillars()[
            "pillars"
        ]
    )

    assert (
        find_current_luck_index(
            5.0,
            pillars,
        )
        == 0
    )


def test_find_current_second():
    pillars = (
        make_simple_luck_pillars()[
            "pillars"
        ]
    )

    assert (
        find_current_luck_index(
            15.0,
            pillars,
        )
        == 1
    )


def test_find_current_third():
    pillars = (
        make_simple_luck_pillars()[
            "pillars"
        ]
    )

    assert (
        find_current_luck_index(
            25.0,
            pillars,
        )
        == 2
    )


def test_find_current_after_last():
    pillars = (
        make_simple_luck_pillars()[
            "pillars"
        ]
    )

    assert (
        find_current_luck_index(
            32.0,
            pillars,
        )
        is None
    )


def test_find_current_boundary_moves_next():
    pillars = (
        make_simple_luck_pillars()[
            "pillars"
        ]
    )

    assert (
        find_current_luck_index(
            12.0,
            pillars,
        )
        == 1
    )


def test_find_current_invalid_pillars():
    with pytest.raises(TypeError):
        find_current_luck_index(
            5.0,
            {},
        )


# ============================================================
# find_next_luck_index
# ============================================================


def test_find_next_before_first():
    pillars = (
        make_simple_luck_pillars()[
            "pillars"
        ]
    )

    assert (
        find_next_luck_index(
            1.0,
            pillars,
        )
        == 0
    )


def test_find_next_during_first():
    pillars = (
        make_simple_luck_pillars()[
            "pillars"
        ]
    )

    assert (
        find_next_luck_index(
            5.0,
            pillars,
        )
        == 1
    )


def test_find_next_at_second_start():
    pillars = (
        make_simple_luck_pillars()[
            "pillars"
        ]
    )

    assert (
        find_next_luck_index(
            12.0,
            pillars,
        )
        == 2
    )


def test_find_next_after_last():
    pillars = (
        make_simple_luck_pillars()[
            "pillars"
        ]
    )

    assert (
        find_next_luck_index(
            40.0,
            pillars,
        )
        is None
    )


@pytest.mark.parametrize(
    "age",
    [
        None,
        "5",
        True,
        False,
    ],
)
def test_find_next_invalid_age(
    age,
):
    with pytest.raises(TypeError):
        find_next_luck_index(
            age,
            make_simple_luck_pillars()[
                "pillars"
            ],
        )


def test_find_next_invalid_pillars():
    with pytest.raises(TypeError):
        find_next_luck_index(
            5.0,
            {},
        )


# ============================================================
# build_luck_pillar_view
# ============================================================


def test_build_current_view():
    original = make_pillar(
        1,
        "壬申",
        "壬",
        "申",
        2.0,
        12.0,
    )

    result = build_luck_pillar_view(
        original,
        is_current=True,
    )

    assert result[
        "is_current"
    ] is True

    assert result[
        "is_previous"
    ] is False

    assert result[
        "is_next"
    ] is False


def test_build_previous_view():
    result = build_luck_pillar_view(
        make_pillar(
            1,
            "壬申",
            "壬",
            "申",
            2.0,
            12.0,
        ),
        is_previous=True,
    )

    assert result[
        "is_previous"
    ] is True


def test_build_next_view():
    result = build_luck_pillar_view(
        make_pillar(
            2,
            "癸酉",
            "癸",
            "酉",
            12.0,
            22.0,
        ),
        is_next=True,
    )

    assert result[
        "is_next"
    ] is True


def test_build_view_does_not_mutate_original():
    original = make_pillar(
        1,
        "壬申",
        "壬",
        "申",
        2.0,
        12.0,
    )

    snapshot = deepcopy(
        original
    )

    result = build_luck_pillar_view(
        original,
        is_current=True,
    )

    assert original == snapshot
    assert result is not original

    assert (
        "is_current"
        not in original
    )


def test_build_view_none():
    assert (
        build_luck_pillar_view(
            None
        )
        is None
    )


def test_build_view_invalid():
    with pytest.raises(TypeError):
        build_luck_pillar_view(
            "pillar"
        )


# ============================================================
# calculate_luck_progress
# ============================================================


def test_progress_at_start():
    pillar = make_pillar(
        1,
        "壬申",
        "壬",
        "申",
        2.0,
        12.0,
    )

    result = calculate_luck_progress(
        2.0,
        pillar,
    )

    assert result[
        "duration_years"
    ] == 10.0

    assert result[
        "elapsed_years"
    ] == 0.0

    assert result[
        "remaining_years"
    ] == 10.0

    assert result[
        "progress_ratio"
    ] == 0.0

    assert result[
        "progress_percent"
    ] == 0.0


def test_progress_middle():
    pillar = make_pillar(
        1,
        "壬申",
        "壬",
        "申",
        2.0,
        12.0,
    )

    result = calculate_luck_progress(
        7.0,
        pillar,
    )

    assert result[
        "elapsed_years"
    ] == 5.0

    assert result[
        "remaining_years"
    ] == 5.0

    assert result[
        "progress_ratio"
    ] == 0.5

    assert result[
        "progress_percent"
    ] == 50.0


def test_progress_near_end():
    pillar = make_pillar(
        1,
        "壬申",
        "壬",
        "申",
        2.0,
        12.0,
    )

    result = calculate_luck_progress(
        11.0,
        pillar,
    )

    assert result[
        "elapsed_years"
    ] == 9.0

    assert result[
        "remaining_years"
    ] == 1.0

    assert result[
        "progress_percent"
    ] == 90.0


def test_progress_before_start_is_clamped():
    pillar = make_pillar(
        1,
        "壬申",
        "壬",
        "申",
        2.0,
        12.0,
    )

    result = calculate_luck_progress(
        1.0,
        pillar,
    )

    assert result[
        "elapsed_years"
    ] == 0.0

    assert result[
        "progress_ratio"
    ] == 0.0

    assert result[
        "progress_percent"
    ] == 0.0


def test_progress_after_end_is_clamped():
    pillar = make_pillar(
        1,
        "壬申",
        "壬",
        "申",
        2.0,
        12.0,
    )

    result = calculate_luck_progress(
        20.0,
        pillar,
    )

    assert result[
        "remaining_years"
    ] == 0.0

    assert result[
        "progress_ratio"
    ] == 1.0

    assert result[
        "progress_percent"
    ] == 100.0


@pytest.mark.parametrize(
    "age",
    [
        None,
        "5",
        True,
        False,
    ],
)
def test_progress_invalid_age(
    age,
):
    with pytest.raises(TypeError):
        calculate_luck_progress(
            age,
            make_pillar(
                1,
                "壬申",
                "壬",
                "申",
                2.0,
                12.0,
            ),
        )


def test_progress_invalid_pillar():
    with pytest.raises(TypeError):
        calculate_luck_progress(
            5.0,
            "pillar",
        )


# ============================================================
# evaluate_current_luck - before first
# ============================================================


def test_before_first_luck():
    birth = datetime(
        2000,
        1,
        1,
    )

    target = datetime_at_age(
        birth,
        1.0,
    )

    result = evaluate_current_luck(
        birth_datetime=birth,
        target_datetime=target,
        luck_pillars=(
            make_simple_luck_pillars()
        ),
    )

    assert result[
        "has_current_luck"
    ] is False

    assert result[
        "phase"
    ] == "before_first_luck"

    assert result[
        "status"
    ] == "before_first_luck"

    assert result[
        "current_luck_pillar"
    ] is None

    assert result[
        "previous_luck_pillar"
    ] is None

    assert result[
        "next_luck_pillar"
    ]["ganzhi"] == "壬申"

    assert result[
        "next_luck_pillar"
    ]["is_next"] is True

    assert result[
        "progress"
    ] is None

    assert result[
        "years_until_next_luck"
    ] == pytest.approx(
        1.0,
        abs=1e-6,
    )


def test_before_first_method():
    birth = datetime(
        2000,
        1,
        1,
    )

    result = evaluate_current_luck(
        birth_datetime=birth,
        target_datetime=(
            datetime_at_age(
                birth,
                1.0,
            )
        ),
        luck_pillars=(
            make_simple_luck_pillars()
        ),
    )

    assert result[
        "method"
    ] == "current_luck_v1"


# ============================================================
# evaluate_current_luck - first pillar
# ============================================================


def test_first_luck_at_exact_start():
    birth = datetime(
        2000,
        1,
        1,
    )

    target = datetime_at_age(
        birth,
        2.0,
    )

    result = evaluate_current_luck(
        birth_datetime=birth,
        target_datetime=target,
        luck_pillars=(
            make_simple_luck_pillars()
        ),
    )

    assert result[
        "has_current_luck"
    ] is True

    assert result[
        "phase"
    ] == "in_luck_pillar"

    assert result[
        "status"
    ] == "current_luck_resolved"

    assert result[
        "current_luck_pillar"
    ]["ganzhi"] == "壬申"

    assert result[
        "current_luck_pillar"
    ]["is_current"] is True

    assert result[
        "previous_luck_pillar"
    ] is None

    assert result[
        "next_luck_pillar"
    ]["ganzhi"] == "癸酉"

    assert result[
        "progress"
    ]["progress_percent"] == 0.0


def test_first_luck_middle():
    birth = datetime(
        2000,
        1,
        1,
    )

    target = datetime_at_age(
        birth,
        7.0,
    )

    result = evaluate_current_luck(
        birth_datetime=birth,
        target_datetime=target,
        luck_pillars=(
            make_simple_luck_pillars()
        ),
    )

    assert result[
        "current_luck_pillar"
    ]["ganzhi"] == "壬申"

    assert result[
        "progress"
    ]["progress_percent"] == 50.0

    assert result[
        "years_until_next_luck"
    ] == 5.0


# ============================================================
# Boundary
# ============================================================


def test_boundary_exactly_moves_to_second():
    birth = datetime(
        2000,
        1,
        1,
    )

    target = datetime_at_age(
        birth,
        12.0,
    )

    result = evaluate_current_luck(
        birth_datetime=birth,
        target_datetime=target,
        luck_pillars=(
            make_simple_luck_pillars()
        ),
    )

    assert result[
        "current_luck_pillar"
    ]["ganzhi"] == "癸酉"

    assert result[
        "previous_luck_pillar"
    ]["ganzhi"] == "壬申"

    assert result[
        "next_luck_pillar"
    ]["ganzhi"] == "甲戌"

    assert result[
        "progress"
    ]["progress_percent"] == 0.0


def test_boundary_has_only_one_current_pillar():
    pillars = (
        make_simple_luck_pillars()[
            "pillars"
        ]
    )

    age = 12.0

    matches = [
        pillar
        for pillar in pillars
        if is_age_in_luck_pillar(
            age,
            pillar,
        )
    ]

    assert len(matches) == 1

    assert matches[0][
        "ganzhi"
    ] == "癸酉"


# ============================================================
# Middle pillar
# ============================================================


def test_second_luck_has_previous_and_next():
    birth = datetime(
        2000,
        1,
        1,
    )

    target = datetime_at_age(
        birth,
        17.0,
    )

    result = evaluate_current_luck(
        birth_datetime=birth,
        target_datetime=target,
        luck_pillars=(
            make_simple_luck_pillars()
        ),
    )

    assert result[
        "previous_luck_pillar"
    ]["ganzhi"] == "壬申"

    assert result[
        "previous_luck_pillar"
    ]["is_previous"] is True

    assert result[
        "current_luck_pillar"
    ]["ganzhi"] == "癸酉"

    assert result[
        "current_luck_pillar"
    ]["is_current"] is True

    assert result[
        "next_luck_pillar"
    ]["ganzhi"] == "甲戌"

    assert result[
        "next_luck_pillar"
    ]["is_next"] is True


# ============================================================
# Last pillar
# ============================================================


def test_last_luck_has_no_next():
    birth = datetime(
        2000,
        1,
        1,
    )

    target = datetime_at_age(
        birth,
        25.0,
    )

    result = evaluate_current_luck(
        birth_datetime=birth,
        target_datetime=target,
        luck_pillars=(
            make_simple_luck_pillars()
        ),
    )

    assert result[
        "has_current_luck"
    ] is True

    assert result[
        "current_luck_pillar"
    ]["ganzhi"] == "甲戌"

    assert result[
        "previous_luck_pillar"
    ]["ganzhi"] == "癸酉"

    assert result[
        "next_luck_pillar"
    ] is None


# ============================================================
# After last pillar
# ============================================================


def test_after_last_luck():
    birth = datetime(
        2000,
        1,
        1,
    )

    target = datetime_at_age(
        birth,
        32.0,
    )

    result = evaluate_current_luck(
        birth_datetime=birth,
        target_datetime=target,
        luck_pillars=(
            make_simple_luck_pillars()
        ),
    )

    assert result[
        "has_current_luck"
    ] is False

    assert result[
        "phase"
    ] == "after_last_luck"

    assert result[
        "status"
    ] == "after_last_luck"

    assert result[
        "current_luck_pillar"
    ] is None

    assert result[
        "previous_luck_pillar"
    ]["ganzhi"] == "甲戌"

    assert result[
        "previous_luck_pillar"
    ]["is_previous"] is True

    assert result[
        "next_luck_pillar"
    ] is None

    assert result[
        "progress"
    ] is None

    assert result[
        "years_until_next_luck"
    ] is None


# ============================================================
# Input immutability
# ============================================================


def test_evaluate_does_not_mutate_luck_pillars():
    luck = make_simple_luck_pillars()

    snapshot = deepcopy(
        luck
    )

    birth = datetime(
        2000,
        1,
        1,
    )

    evaluate_current_luck(
        birth_datetime=birth,
        target_datetime=(
            datetime_at_age(
                birth,
                17.0,
            )
        ),
        luck_pillars=luck,
    )

    assert luck == snapshot


# ============================================================
# Alias
# ============================================================


def test_calculate_current_luck_alias():
    birth = datetime(
        2000,
        1,
        1,
    )

    target = datetime_at_age(
        birth,
        17.0,
    )

    luck = make_simple_luck_pillars()

    direct = evaluate_current_luck(
        birth_datetime=birth,
        target_datetime=target,
        luck_pillars=luck,
    )

    alias = calculate_current_luck(
        birth_datetime=birth,
        target_datetime=target,
        luck_pillars=luck,
    )

    assert alias == direct


# ============================================================
# get_current_luck_pillar
# ============================================================


def test_get_current_luck_pillar():
    birth = datetime(
        2000,
        1,
        1,
    )

    result = get_current_luck_pillar(
        birth_datetime=birth,
        target_datetime=(
            datetime_at_age(
                birth,
                17.0,
            )
        ),
        luck_pillars=(
            make_simple_luck_pillars()
        ),
    )

    assert result[
        "ganzhi"
    ] == "癸酉"

    assert result[
        "is_current"
    ] is True


def test_get_current_luck_before_first():
    birth = datetime(
        2000,
        1,
        1,
    )

    result = get_current_luck_pillar(
        birth_datetime=birth,
        target_datetime=(
            datetime_at_age(
                birth,
                1.0,
            )
        ),
        luck_pillars=(
            make_simple_luck_pillars()
        ),
    )

    assert result is None


def test_get_current_luck_after_last():
    birth = datetime(
        2000,
        1,
        1,
    )

    result = get_current_luck_pillar(
        birth_datetime=birth,
        target_datetime=(
            datetime_at_age(
                birth,
                40.0,
            )
        ),
        luck_pillars=(
            make_simple_luck_pillars()
        ),
    )

    assert result is None


# ============================================================
# Validation - luck_pillars
# ============================================================


def test_invalid_luck_pillars_type():
    with pytest.raises(TypeError):
        evaluate_current_luck(
            birth_datetime=datetime(
                2000,
                1,
                1,
            ),
            target_datetime=datetime(
                2010,
                1,
                1,
            ),
            luck_pillars=[],
        )


def test_missing_pillars_key():
    with pytest.raises(ValueError):
        evaluate_current_luck(
            birth_datetime=datetime(
                2000,
                1,
                1,
            ),
            target_datetime=datetime(
                2010,
                1,
                1,
            ),
            luck_pillars={},
        )


def test_pillars_not_list():
    with pytest.raises(TypeError):
        evaluate_current_luck(
            birth_datetime=datetime(
                2000,
                1,
                1,
            ),
            target_datetime=datetime(
                2010,
                1,
                1,
            ),
            luck_pillars={
                "pillars": {},
            },
        )


def test_empty_pillars():
    with pytest.raises(ValueError):
        evaluate_current_luck(
            birth_datetime=datetime(
                2000,
                1,
                1,
            ),
            target_datetime=datetime(
                2010,
                1,
                1,
            ),
            luck_pillars={
                "pillars": [],
            },
        )


def test_pillar_not_dict():
    with pytest.raises(TypeError):
        evaluate_current_luck(
            birth_datetime=datetime(
                2000,
                1,
                1,
            ),
            target_datetime=datetime(
                2010,
                1,
                1,
            ),
            luck_pillars={
                "pillars": [
                    "壬申",
                ],
            },
        )


@pytest.mark.parametrize(
    "missing_key",
    [
        "index",
        "ganzhi",
        "stem",
        "branch",
        "start_age",
        "end_age",
    ],
)
def test_missing_required_pillar_key(
    missing_key,
):
    pillar = make_pillar(
        1,
        "壬申",
        "壬",
        "申",
        2.0,
        12.0,
    )

    del pillar[
        missing_key
    ]

    with pytest.raises(ValueError):
        evaluate_current_luck(
            birth_datetime=datetime(
                2000,
                1,
                1,
            ),
            target_datetime=datetime(
                2010,
                1,
                1,
            ),
            luck_pillars={
                "pillars": [
                    pillar,
                ],
            },
        )


# ============================================================
# Validation - datetime
# ============================================================


def test_evaluate_invalid_birth_datetime():
    with pytest.raises(TypeError):
        evaluate_current_luck(
            birth_datetime="2000-01-01",
            target_datetime=datetime(
                2010,
                1,
                1,
            ),
            luck_pillars=(
                make_simple_luck_pillars()
            ),
        )


def test_evaluate_invalid_target_datetime():
    with pytest.raises(TypeError):
        evaluate_current_luck(
            birth_datetime=datetime(
                2000,
                1,
                1,
            ),
            target_datetime="2010-01-01",
            luck_pillars=(
                make_simple_luck_pillars()
            ),
        )


def test_evaluate_target_before_birth():
    with pytest.raises(ValueError):
        evaluate_current_luck(
            birth_datetime=datetime(
                2000,
                1,
                2,
            ),
            target_datetime=datetime(
                2000,
                1,
                1,
            ),
            luck_pillars=(
                make_simple_luck_pillars()
            ),
        )


# ============================================================
# Timezone regression
# ============================================================


def test_evaluate_aware_datetimes():
    birth = datetime(
        2000,
        1,
        1,
        tzinfo=JST,
    )

    target = datetime_at_age(
        birth,
        17.0,
    )

    result = evaluate_current_luck(
        birth_datetime=birth,
        target_datetime=target,
        luck_pillars=(
            make_simple_luck_pillars()
        ),
    )

    assert result[
        "has_current_luck"
    ] is True

    assert result[
        "current_luck_pillar"
    ]["ganzhi"] == "癸酉"


def test_evaluate_birth_aware_target_naive():
    birth = datetime(
        2000,
        1,
        1,
        tzinfo=JST,
    )

    naive_birth = birth.replace(
        tzinfo=None
    )

    target = datetime_at_age(
        naive_birth,
        17.0,
    )

    result = evaluate_current_luck(
        birth_datetime=birth,
        target_datetime=target,
        luck_pillars=(
            make_simple_luck_pillars()
        ),
    )

    assert result[
        "has_current_luck"
    ] is True

    assert result[
        "current_luck_pillar"
    ]["ganzhi"] == "癸酉"


def test_evaluate_birth_naive_target_aware():
    birth = datetime(
        2000,
        1,
        1,
    )

    target_naive = datetime_at_age(
        birth,
        17.0,
    )

    target = target_naive.replace(
        tzinfo=JST
    )

    result = evaluate_current_luck(
        birth_datetime=birth,
        target_datetime=target,
        luck_pillars=(
            make_simple_luck_pillars()
        ),
    )

    assert result[
        "has_current_luck"
    ] is True

    assert result[
        "current_luck_pillar"
    ]["ganzhi"] == "癸酉"


# ============================================================
# luck_pillars_v2 integration
# ============================================================


def test_real_luck_pillars_first_ganzhi():
    luck = make_real_luck_pillars(
        count=5
    )

    assert luck[
        "pillars"
    ][0][
        "ganzhi"
    ] == "壬申"


def test_real_luck_pillars_start_age():
    luck = make_real_luck_pillars(
        count=5
    )

    assert luck[
        "pillars"
    ][0][
        "start_age"
    ] == 2.0


def test_real_luck_before_first():
    birth = datetime(
        1984,
        7,
        22,
        4,
        15,
    )

    luck = make_real_luck_pillars(
        count=5
    )

    target = datetime_at_age(
        birth,
        1.0,
    )

    result = evaluate_current_luck(
        birth_datetime=birth,
        target_datetime=target,
        luck_pillars=luck,
    )

    assert result[
        "phase"
    ] == "before_first_luck"

    assert result[
        "next_luck_pillar"
    ]["ganzhi"] == "壬申"


def test_real_luck_first_pillar():
    birth = datetime(
        1984,
        7,
        22,
        4,
        15,
    )

    luck = make_real_luck_pillars(
        count=5
    )

    target = datetime_at_age(
        birth,
        5.0,
    )

    result = evaluate_current_luck(
        birth_datetime=birth,
        target_datetime=target,
        luck_pillars=luck,
    )

    assert result[
        "phase"
    ] == "in_luck_pillar"

    assert result[
        "current_luck_pillar"
    ]["ganzhi"] == "壬申"


def test_real_luck_second_pillar():
    birth = datetime(
        1984,
        7,
        22,
        4,
        15,
    )

    luck = make_real_luck_pillars(
        count=5
    )

    target = datetime_at_age(
        birth,
        15.0,
    )

    result = evaluate_current_luck(
        birth_datetime=birth,
        target_datetime=target,
        luck_pillars=luck,
    )

    assert result[
        "current_luck_pillar"
    ]["ganzhi"] == "癸酉"

    assert result[
        "previous_luck_pillar"
    ]["ganzhi"] == "壬申"

    assert result[
        "next_luck_pillar"
    ]["ganzhi"] == "甲戌"


def test_real_luck_boundary():
    birth = datetime(
        1984,
        7,
        22,
        4,
        15,
    )

    luck = make_real_luck_pillars(
        count=5
    )

    target = datetime_at_age(
        birth,
        12.0,
    )

    result = evaluate_current_luck(
        birth_datetime=birth,
        target_datetime=target,
        luck_pillars=luck,
    )

    assert result[
        "current_luck_pillar"
    ]["ganzhi"] == "癸酉"


# ============================================================
# Output structure
# ============================================================


def test_result_required_keys():
    birth = datetime(
        2000,
        1,
        1,
    )

    result = evaluate_current_luck(
        birth_datetime=birth,
        target_datetime=(
            datetime_at_age(
                birth,
                17.0,
            )
        ),
        luck_pillars=(
            make_simple_luck_pillars()
        ),
    )

    required = {
        "has_current_luck",
        "phase",
        "exact_age",
        "calendar_age",
        "current_luck_pillar",
        "previous_luck_pillar",
        "next_luck_pillar",
        "progress",
        "years_until_next_luck",
        "method",
        "status",
        "notes",
    }

    assert required.issubset(
        result.keys()
    )


def test_current_result_notes():
    birth = datetime(
        2000,
        1,
        1,
    )

    result = evaluate_current_luck(
        birth_datetime=birth,
        target_datetime=(
            datetime_at_age(
                birth,
                17.0,
            )
        ),
        luck_pillars=(
            make_simple_luck_pillars()
        ),
    )

    assert isinstance(
        result[
            "notes"
        ],
        list,
    )

    assert result[
        "notes"
    ]


def test_exact_age_is_float():
    birth = datetime(
        2000,
        1,
        1,
    )

    result = evaluate_current_luck(
        birth_datetime=birth,
        target_datetime=(
            datetime_at_age(
                birth,
                17.0,
            )
        ),
        luck_pillars=(
            make_simple_luck_pillars()
        ),
    )

    assert isinstance(
        result[
            "exact_age"
        ],
        float,
    )


def test_calendar_age_is_int():
    birth = datetime(
        2000,
        1,
        1,
    )

    result = evaluate_current_luck(
        birth_datetime=birth,
        target_datetime=(
            datetime_at_age(
                birth,
                17.0,
            )
        ),
        luck_pillars=(
            make_simple_luck_pillars()
        ),
    )

    assert isinstance(
        result[
            "calendar_age"
        ],
        int,
    )


# ============================================================
# Determinism
# ============================================================


def test_evaluate_is_deterministic():
    birth = datetime(
        2000,
        1,
        1,
    )

    target = datetime_at_age(
        birth,
        17.0,
    )

    luck = make_simple_luck_pillars()

    first = evaluate_current_luck(
        birth_datetime=birth,
        target_datetime=target,
        luck_pillars=luck,
    )

    second = evaluate_current_luck(
        birth_datetime=birth,
        target_datetime=target,
        luck_pillars=luck,
    )

    assert first == second


# ============================================================
# Final regression
# ============================================================


def test_final_current_luck_regression():
    """
    current_luck_v1 の最終代表ケース。

    2歳起運、
    12歳で第2大運へ切替。

    17歳時点では
    第2大運「癸酉」の途中。
    """

    birth = datetime(
        2000,
        1,
        1,
    )

    target = datetime_at_age(
        birth,
        17.0,
    )

    result = evaluate_current_luck(
        birth_datetime=birth,
        target_datetime=target,
        luck_pillars=(
            make_simple_luck_pillars()
        ),
    )

    assert result[
        "has_current_luck"
    ] is True

    assert result[
        "phase"
    ] == "in_luck_pillar"

    assert result[
        "current_luck_pillar"
    ]["ganzhi"] == "癸酉"

    assert result[
        "previous_luck_pillar"
    ]["ganzhi"] == "壬申"

    assert result[
        "next_luck_pillar"
    ]["ganzhi"] == "甲戌"

    assert result[
        "progress"
    ]["progress_percent"] == 50.0

    assert result[
        "years_until_next_luck"
    ] == 5.0

    assert result[
        "method"
    ] == "current_luck_v1"

    assert result[
        "status"
    ] == "current_luck_resolved"
