"""
tests/test_final_luck_pillars.py

大運計算エンジン luck_pillars_v2 の最終回帰テスト。

検証対象:
- 六十干支の分解・移動
- 順行 / 逆行
- 対象節入りの外部指定 / 自動取得
- 三日一年法による起運年齢
- 年齢表示
- 大運開始日時の概算
- 十神
- 五行関係
- useful_gods_v3 との関係
- 大運干支列
- 1本の大運データ
- calculate_luck_pillars
- evaluate_luck_pillars 互換API
- 不正入力
- 既知の順行 / 逆行ケース

方針:
天文節入りそのものの精度は solar_terms 側で検証済みとし、
ここでは大運エンジンの責務を固定する。
外部指定の節入り日時を使うテストを中心にすることで、
大運ロジックを天文計算から独立して検証する。
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from engine.luck_pillars import (
    BRANCH_TO_ELEMENT,
    CONTROLLED_BY,
    CONTROLS,
    EARTHLY_BRANCHES,
    ELEMENTS,
    GENERATED_BY,
    GENERATES,
    HEAVENLY_STEMS,
    SEXAGENARY_CYCLE,
    STEM_TO_ELEMENT,
    STEM_TO_YIN_YANG,
    age_to_year_month_day,
    build_luck_pillar_data,
    calculate_luck_pillars,
    calculate_start_age,
    calculate_term_distance_days,
    determine_luck_direction,
    estimate_start_datetime,
    evaluate_element_against_useful_gods,
    evaluate_luck_pillars,
    generate_luck_ganzhi,
    get_element_relation,
    get_sexagenary_index,
    get_ten_god_for_stem,
    resolve_target_term,
    shift_ganzhi,
    split_ganzhi,
)


JST = ZoneInfo("Asia/Tokyo")


# ============================================================
# Helpers
# ============================================================


def make_useful_gods():
    return {
        "primary_useful_element": "火",
        "final_useful_elements": [
            "火",
            "土",
            "金",
        ],
        "support_balance": {
            "unfavorable_elements": [
                "水",
                "木",
            ],
        },
        "method": "useful_gods_v3",
    }


def make_external_forward_result(
    *,
    count=10,
    useful_gods=None,
):
    """
    甲年男性 = 順行。

    birth:
        1984-07-22 04:15

    target:
        1984-07-28 04:15

    差:
        6日

    三日一年法:
        6 / 3 = 2歳起運

    月柱:
        辛未

    順行第1大運:
        壬申
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
        useful_gods=useful_gods,
    )


def make_external_backward_result(
    *,
    count=10,
    useful_gods=None,
):
    """
    甲年女性 = 逆行。

    birth:
        1984-07-22 04:15

    target:
        1984-07-16 04:15

    差:
        6日

    三日一年法:
        2歳起運

    月柱:
        辛未

    逆行第1大運:
        庚午
    """

    return calculate_luck_pillars(
        year_stem="甲",
        month_ganzhi="辛未",
        day_master_stem="乙",
        gender="female",
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
            16,
            4,
            15,
        ),
        count=count,
        useful_gods=useful_gods,
    )


# ============================================================
# Constants
# ============================================================


def test_heavenly_stems():
    assert HEAVENLY_STEMS == [
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


def test_earthly_branches():
    assert EARTHLY_BRANCHES == [
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


def test_elements():
    assert ELEMENTS == [
        "木",
        "火",
        "土",
        "金",
        "水",
    ]


def test_sexagenary_cycle_length():
    assert len(SEXAGENARY_CYCLE) == 60


def test_sexagenary_cycle_unique():
    assert (
        len(set(SEXAGENARY_CYCLE))
        == 60
    )


def test_sexagenary_cycle_starts_with_jiazi():
    assert SEXAGENARY_CYCLE[0] == "甲子"


def test_sexagenary_cycle_ends_with_guihai():
    assert SEXAGENARY_CYCLE[-1] == "癸亥"


def test_stem_element_mapping():
    assert STEM_TO_ELEMENT["甲"] == "木"
    assert STEM_TO_ELEMENT["乙"] == "木"
    assert STEM_TO_ELEMENT["丙"] == "火"
    assert STEM_TO_ELEMENT["辛"] == "金"
    assert STEM_TO_ELEMENT["壬"] == "水"


def test_branch_element_mapping():
    assert BRANCH_TO_ELEMENT["子"] == "水"
    assert BRANCH_TO_ELEMENT["寅"] == "木"
    assert BRANCH_TO_ELEMENT["午"] == "火"
    assert BRANCH_TO_ELEMENT["申"] == "金"
    assert BRANCH_TO_ELEMENT["辰"] == "土"


def test_stem_yin_yang_mapping():
    assert STEM_TO_YIN_YANG == {
        "甲": "陽",
        "乙": "陰",
        "丙": "陽",
        "丁": "陰",
        "戊": "陽",
        "己": "陰",
        "庚": "陽",
        "辛": "陰",
        "壬": "陽",
        "癸": "陰",
    }


def test_generation_inverse_mapping():
    for source, target in GENERATES.items():
        assert GENERATED_BY[target] == source


def test_control_inverse_mapping():
    for source, target in CONTROLS.items():
        assert CONTROLLED_BY[target] == source


# ============================================================
# Ganzhi helpers
# ============================================================


@pytest.mark.parametrize(
    "ganzhi,expected",
    [
        ("甲子", ("甲", "子")),
        ("辛未", ("辛", "未")),
        ("乙巳", ("乙", "巳")),
        ("癸亥", ("癸", "亥")),
    ],
)
def test_split_ganzhi(
    ganzhi,
    expected,
):
    assert split_ganzhi(ganzhi) == expected


@pytest.mark.parametrize(
    "value",
    [
        None,
        123,
        "",
        "甲",
        "甲子丑",
        "A子",
        "甲A",
    ],
)
def test_split_ganzhi_invalid(value):
    with pytest.raises(ValueError):
        split_ganzhi(value)


def test_get_sexagenary_index_jiazi():
    assert get_sexagenary_index("甲子") == 0


def test_get_sexagenary_index_guihai():
    assert get_sexagenary_index("癸亥") == 59


def test_get_sexagenary_index_invalid():
    with pytest.raises(ValueError):
        get_sexagenary_index("甲丑")


@pytest.mark.parametrize(
    "ganzhi,steps,expected",
    [
        ("甲子", 1, "乙丑"),
        ("甲子", -1, "癸亥"),
        ("癸亥", 1, "甲子"),
        ("辛未", 1, "壬申"),
        ("辛未", -1, "庚午"),
        ("甲子", 60, "甲子"),
        ("甲子", -60, "甲子"),
    ],
)
def test_shift_ganzhi(
    ganzhi,
    steps,
    expected,
):
    assert (
        shift_ganzhi(
            ganzhi,
            steps,
        )
        == expected
    )


# ============================================================
# Luck direction
# ============================================================


@pytest.mark.parametrize(
    "year_stem,gender,expected",
    [
        ("甲", "male", "forward"),
        ("甲", "男", "forward"),
        ("甲", "female", "backward"),
        ("甲", "女", "backward"),
        ("丙", "male", "forward"),
        ("戊", "male", "forward"),
        ("庚", "male", "forward"),
        ("壬", "male", "forward"),
        ("乙", "female", "forward"),
        ("丁", "female", "forward"),
        ("己", "female", "forward"),
        ("辛", "female", "forward"),
        ("癸", "female", "forward"),
        ("乙", "male", "backward"),
        ("丁", "male", "backward"),
        ("己", "male", "backward"),
        ("辛", "male", "backward"),
        ("癸", "male", "backward"),
        ("丙", "female", "backward"),
        ("戊", "female", "backward"),
        ("庚", "female", "backward"),
        ("壬", "female", "backward"),
    ],
)
def test_determine_luck_direction(
    year_stem,
    gender,
    expected,
):
    assert (
        determine_luck_direction(
            year_stem,
            gender,
        )
        == expected
    )


def test_determine_luck_direction_invalid_stem():
    with pytest.raises(ValueError):
        determine_luck_direction(
            "A",
            "male",
        )


def test_determine_luck_direction_invalid_gender():
    with pytest.raises(ValueError):
        determine_luck_direction(
            "甲",
            "unknown",
        )


# ============================================================
# Target solar term resolution
# ============================================================


def test_resolve_target_term_external():
    birth = datetime(
        1984,
        7,
        22,
        4,
        15,
    )

    target = datetime(
        1984,
        7,
        28,
        4,
        15,
    )

    result = resolve_target_term(
        birth_datetime=birth,
        direction="forward",
        target_term_datetime=target,
    )

    assert (
        result["target_term_datetime"]
        == target
    )

    assert (
        result["target_term_source"]
        == "external_input"
    )

    assert result[
        "target_term_name"
    ] is None

    assert result[
        "target_term_month"
    ] is None

    assert result[
        "target_term_branch"
    ] is None


def test_resolve_target_term_automatic_forward():
    result = resolve_target_term(
        birth_datetime=datetime(
            1984,
            7,
            22,
            4,
            15,
        ),
        direction="forward",
    )

    assert isinstance(
        result[
            "target_term_datetime"
        ],
        datetime,
    )

    assert isinstance(
        result[
            "target_term_name"
        ],
        str,
    )

    assert result[
        "target_term_month"
    ] in range(
        1,
        13,
    )

    assert result[
        "target_term_branch"
    ] in EARTHLY_BRANCHES

    assert (
        result[
            "target_term_source"
        ]
        == "solar_terms_v2"
    )

    assert (
        result[
            "target_term_datetime"
        ]
        > datetime(
            1984,
            7,
            22,
            4,
            15,
        )
    )


def test_resolve_target_term_automatic_backward():
    birth = datetime(
        1984,
        7,
        22,
        4,
        15,
    )

    result = resolve_target_term(
        birth_datetime=birth,
        direction="backward",
    )

    assert isinstance(
        result[
            "target_term_datetime"
        ],
        datetime,
    )

    assert (
        result[
            "target_term_datetime"
        ]
        < birth
    )


def test_resolve_target_term_invalid_direction():
    with pytest.raises(ValueError):
        resolve_target_term(
            birth_datetime=datetime(
                1984,
                7,
                22,
                4,
                15,
            ),
            direction="sideways",
        )


# ============================================================
# Term distance / start age
# ============================================================


@pytest.mark.parametrize(
    "days,expected",
    [
        (0, 0.0),
        (1, 1.0),
        (3, 3.0),
        (6, 6.0),
        (9, 9.0),
    ],
)
def test_calculate_term_distance_days(
    days,
    expected,
):
    birth = datetime(
        2000,
        1,
        1,
        0,
        0,
    )

    target = birth + timedelta(
        days=days
    )

    assert (
        calculate_term_distance_days(
            birth,
            target,
        )
        == expected
    )


def test_term_distance_absolute_backward():
    birth = datetime(
        2000,
        1,
        10,
    )

    target = datetime(
        2000,
        1,
        4,
    )

    assert (
        calculate_term_distance_days(
            birth,
            target,
        )
        == 6.0
    )


@pytest.mark.parametrize(
    "distance_days,expected_age",
    [
        (0, 0.0),
        (3, 1.0),
        (6, 2.0),
        (9, 3.0),
        (30, 10.0),
    ],
)
def test_calculate_start_age_three_days_one_year(
    distance_days,
    expected_age,
):
    birth = datetime(
        2000,
        1,
        1,
    )

    target = birth + timedelta(
        days=distance_days
    )

    assert (
        calculate_start_age(
            birth,
            target,
        )
        == expected_age
    )


def test_calculate_start_age_half_day():
    birth = datetime(
        2000,
        1,
        1,
        0,
        0,
    )

    target = datetime(
        2000,
        1,
        1,
        12,
        0,
    )

    assert (
        calculate_start_age(
            birth,
            target,
        )
        == pytest.approx(
            1 / 6,
            abs=1e-6,
        )
    )


def test_term_distance_jst_aware():
    birth = datetime(
        2000,
        1,
        1,
        tzinfo=JST,
    )

    target = datetime(
        2000,
        1,
        4,
        tzinfo=JST,
    )

    assert (
        calculate_term_distance_days(
            birth,
            target,
        )
        == 3.0
    )


@pytest.mark.parametrize(
    "bad_birth,bad_target",
    [
        (
            "2000-01-01",
            datetime(2000, 1, 4),
        ),
        (
            datetime(2000, 1, 1),
            "2000-01-04",
        ),
    ],
)
def test_term_distance_invalid_datetime(
    bad_birth,
    bad_target,
):
    with pytest.raises(TypeError):
        calculate_term_distance_days(
            bad_birth,
            bad_target,
        )


# ============================================================
# Age formatting
# ============================================================


@pytest.mark.parametrize(
    "age,expected",
    [
        (
            0.0,
            {
                "years": 0,
                "months": 0,
                "days": 0,
            },
        ),
        (
            1.0,
            {
                "years": 1,
                "months": 0,
                "days": 0,
            },
        ),
        (
            1.5,
            {
                "years": 1,
                "months": 6,
                "days": 0,
            },
        ),
        (
            2.25,
            {
                "years": 2,
                "months": 3,
                "days": 0,
            },
        ),
    ],
)
def test_age_to_year_month_day(
    age,
    expected,
):
    assert (
        age_to_year_month_day(age)
        == expected
    )


def test_age_to_year_month_day_negative():
    with pytest.raises(ValueError):
        age_to_year_month_day(
            -0.1
        )


# ============================================================
# Start datetime estimate
# ============================================================


def test_estimate_start_datetime_zero():
    birth = datetime(
        2000,
        1,
        1,
        12,
        0,
    )

    assert (
        estimate_start_datetime(
            birth,
            0.0,
        )
        == birth
    )


def test_estimate_start_datetime_two_years():
    birth = datetime(
        2000,
        1,
        1,
        0,
        0,
    )

    result = estimate_start_datetime(
        birth,
        2.0,
    )

    expected = (
        birth
        + timedelta(
            days=2.0 * 365.2425
        )
    )

    assert result == expected


def test_estimate_start_datetime_negative():
    with pytest.raises(ValueError):
        estimate_start_datetime(
            datetime(
                2000,
                1,
                1,
            ),
            -1.0,
        )


# ============================================================
# Element relations
# ============================================================


@pytest.mark.parametrize(
    "target,expected",
    [
        ("木", "same"),
        ("水", "resource"),
        ("火", "output"),
        ("土", "wealth"),
        ("金", "officer"),
    ],
)
def test_get_element_relation_for_wood(
    target,
    expected,
):
    assert (
        get_element_relation(
            "木",
            target,
        )
        == expected
    )


def test_get_element_relation_invalid_day_element():
    with pytest.raises(ValueError):
        get_element_relation(
            "空",
            "木",
        )


def test_get_element_relation_invalid_target():
    with pytest.raises(ValueError):
        get_element_relation(
            "木",
            "空",
        )


# ============================================================
# Ten Gods
# ============================================================


@pytest.mark.parametrize(
    "target_stem,expected",
    [
        ("乙", "比肩"),
        ("甲", "劫財"),
        ("癸", "偏印"),
        ("壬", "印綬"),
        ("丁", "食神"),
        ("丙", "傷官"),
        ("己", "偏財"),
        ("戊", "正財"),
        ("辛", "偏官"),
        ("庚", "正官"),
    ],
)
def test_ten_gods_for_otsu_day_master(
    target_stem,
    expected,
):
    assert (
        get_ten_god_for_stem(
            "乙",
            target_stem,
        )
        == expected
    )


def test_ten_god_invalid_day_stem():
    with pytest.raises(ValueError):
        get_ten_god_for_stem(
            "A",
            "甲",
        )


def test_ten_god_invalid_target_stem():
    with pytest.raises(ValueError):
        get_ten_god_for_stem(
            "乙",
            "A",
        )


# ============================================================
# Useful gods relationship
# ============================================================


def test_useful_relation_unknown_without_useful_gods():
    result = (
        evaluate_element_against_useful_gods(
            "火",
            None,
        )
    )

    assert result == {
        "is_useful": None,
        "is_primary_useful": None,
        "priority": None,
        "relationship": "unknown",
    }


def test_useful_relation_primary():
    result = (
        evaluate_element_against_useful_gods(
            "火",
            make_useful_gods(),
        )
    )

    assert result[
        "is_useful"
    ] is True

    assert result[
        "is_primary_useful"
    ] is True

    assert result[
        "priority"
    ] == 1

    assert result[
        "relationship"
    ] == "primary_useful"


def test_useful_relation_secondary():
    result = (
        evaluate_element_against_useful_gods(
            "土",
            make_useful_gods(),
        )
    )

    assert result[
        "is_useful"
    ] is True

    assert result[
        "is_primary_useful"
    ] is False

    assert result[
        "priority"
    ] == 2

    assert result[
        "relationship"
    ] == "secondary_useful"


def test_useful_relation_support_unfavorable():
    result = (
        evaluate_element_against_useful_gods(
            "水",
            make_useful_gods(),
        )
    )

    assert result[
        "is_useful"
    ] is False

    assert (
        result["relationship"]
        == "support_unfavorable"
    )


def test_useful_relation_neutral():
    useful = make_useful_gods()

    useful[
        "final_useful_elements"
    ] = [
        "火",
    ]

    useful[
        "support_balance"
    ][
        "unfavorable_elements"
    ] = [
        "水",
    ]

    result = (
        evaluate_element_against_useful_gods(
            "金",
            useful,
        )
    )

    assert result[
        "relationship"
    ] == "neutral"


def test_useful_relation_invalid_element():
    with pytest.raises(ValueError):
        evaluate_element_against_useful_gods(
            "空",
            make_useful_gods(),
        )


# ============================================================
# Luck Ganzhi generation
# ============================================================


def test_generate_forward_from_shinbi():
    result = generate_luck_ganzhi(
        "辛未",
        "forward",
        count=5,
    )

    assert result == [
        "壬申",
        "癸酉",
        "甲戌",
        "乙亥",
        "丙子",
    ]


def test_generate_backward_from_shinbi():
    result = generate_luck_ganzhi(
        "辛未",
        "backward",
        count=5,
    )

    assert result == [
        "庚午",
        "己巳",
        "戊辰",
        "丁卯",
        "丙寅",
    ]


def test_generate_does_not_include_month_pillar():
    result = generate_luck_ganzhi(
        "辛未",
        "forward",
        count=10,
    )

    assert "辛未" not in result


def test_generate_requested_count():
    result = generate_luck_ganzhi(
        "辛未",
        "forward",
        count=7,
    )

    assert len(result) == 7


def test_generate_unique_first_ten():
    result = generate_luck_ganzhi(
        "辛未",
        "forward",
        count=10,
    )

    assert len(result) == len(
        set(result)
    )


def test_generate_invalid_direction():
    with pytest.raises(ValueError):
        generate_luck_ganzhi(
            "辛未",
            "sideways",
        )


def test_generate_invalid_count_type():
    with pytest.raises(TypeError):
        generate_luck_ganzhi(
            "辛未",
            "forward",
            count=1.5,
        )


@pytest.mark.parametrize(
    "count",
    [
        0,
        -1,
    ],
)
def test_generate_invalid_count_value(
    count,
):
    with pytest.raises(ValueError):
        generate_luck_ganzhi(
            "辛未",
            "forward",
            count=count,
        )


# ============================================================
# Single pillar
# ============================================================


def test_build_luck_pillar_data_basic():
    result = build_luck_pillar_data(
        index=1,
        ganzhi="壬申",
        day_master_stem="乙",
        start_age=2.0,
        birth_datetime=datetime(
            1984,
            7,
            22,
            4,
            15,
        ),
    )

    assert result[
        "index"
    ] == 1

    assert result[
        "ganzhi"
    ] == "壬申"

    assert result[
        "stem"
    ] == "壬"

    assert result[
        "branch"
    ] == "申"

    assert result[
        "stem_element"
    ] == "水"

    assert result[
        "branch_element"
    ] == "金"

    assert result[
        "stem_yin_yang"
    ] == "陽"

    assert result[
        "stem_ten_god"
    ] == "印綬"

    assert result[
        "start_age"
    ] == 2.0

    assert result[
        "end_age"
    ] == 12.0

    assert isinstance(
        result[
            "start_datetime"
        ],
        str,
    )

    assert isinstance(
        result[
            "end_datetime"
        ],
        str,
    )


def test_build_second_luck_pillar_age_range():
    result = build_luck_pillar_data(
        index=2,
        ganzhi="癸酉",
        day_master_stem="乙",
        start_age=2.0,
    )

    assert result[
        "start_age"
    ] == 12.0

    assert result[
        "end_age"
    ] == 22.0

    assert result[
        "start_datetime"
    ] is None

    assert result[
        "end_datetime"
    ] is None


def test_build_luck_pillar_useful_relations():
    result = build_luck_pillar_data(
        index=1,
        ganzhi="丙午",
        day_master_stem="乙",
        start_age=2.0,
        useful_gods=make_useful_gods(),
    )

    assert (
        result[
            "stem_useful_relation"
        ][
            "relationship"
        ]
        == "primary_useful"
    )

    assert (
        result[
            "branch_useful_relation"
        ][
            "relationship"
        ]
        == "primary_useful"
    )


# ============================================================
# calculate_luck_pillars - forward
# ============================================================


def test_calculate_luck_pillars_forward_direction():
    result = (
        make_external_forward_result()
    )

    assert result[
        "direction"
    ] == "forward"

    assert result[
        "direction_japanese"
    ] == "順行"

    assert result[
        "gender"
    ] == "male"


def test_calculate_luck_pillars_forward_start_age():
    result = (
        make_external_forward_result()
    )

    assert result[
        "term_distance_days"
    ] == 6.0

    assert result[
        "start_age"
    ] == 2.0

    assert result[
        "start_age_detail"
    ] == {
        "years": 2,
        "months": 0,
        "days": 0,
    }


def test_calculate_luck_pillars_forward_sequence():
    result = (
        make_external_forward_result(
            count=5
        )
    )

    assert [
        item["ganzhi"]
        for item in result[
            "pillars"
        ]
    ] == [
        "壬申",
        "癸酉",
        "甲戌",
        "乙亥",
        "丙子",
    ]


def test_calculate_luck_pillars_forward_first_age():
    result = (
        make_external_forward_result()
    )

    first = result["pillars"][0]

    assert first[
        "start_age"
    ] == 2.0

    assert first[
        "end_age"
    ] == 12.0


def test_calculate_luck_pillars_ten_year_intervals():
    result = (
        make_external_forward_result(
            count=5
        )
    )

    pillars = result["pillars"]

    for previous, current in zip(
        pillars,
        pillars[1:],
    ):
        assert (
            current["start_age"]
            - previous["start_age"]
            == 10.0
        )

        assert (
            current["start_age"]
            == previous["end_age"]
        )


# ============================================================
# calculate_luck_pillars - backward
# ============================================================


def test_calculate_luck_pillars_backward_direction():
    result = (
        make_external_backward_result()
    )

    assert result[
        "direction"
    ] == "backward"

    assert result[
        "direction_japanese"
    ] == "逆行"

    assert result[
        "gender"
    ] == "female"


def test_calculate_luck_pillars_backward_sequence():
    result = (
        make_external_backward_result(
            count=5
        )
    )

    assert [
        item["ganzhi"]
        for item in result[
            "pillars"
        ]
    ] == [
        "庚午",
        "己巳",
        "戊辰",
        "丁卯",
        "丙寅",
    ]


def test_calculate_luck_pillars_backward_start_age():
    result = (
        make_external_backward_result()
    )

    assert result[
        "term_distance_days"
    ] == 6.0

    assert result[
        "start_age"
    ] == 2.0


# ============================================================
# Main result structure
# ============================================================


def test_calculate_luck_pillars_metadata():
    result = (
        make_external_forward_result()
    )

    assert result[
        "method"
    ] == "luck_pillars_v2"

    assert result[
        "status"
    ] == (
        "provisional_luck_pillars_v2"
    )


def test_calculate_luck_pillars_external_source():
    result = (
        make_external_forward_result()
    )

    assert (
        result[
            "target_term_source"
        ]
        == "external_input"
    )

    assert (
        result[
            "calculation_rules"
        ][
            "term_datetime_source"
        ]
        == "external_input"
    )


def test_calculate_luck_pillars_basic_identity():
    result = (
        make_external_forward_result()
    )

    assert result[
        "year_stem"
    ] == "甲"

    assert result[
        "year_stem_yin_yang"
    ] == "陽"

    assert result[
        "month_ganzhi"
    ] == "辛未"

    assert result[
        "day_master_stem"
    ] == "乙"

    assert result[
        "day_master_element"
    ] == "木"


def test_calculate_luck_pillars_pillar_count():
    result = (
        make_external_forward_result(
            count=7
        )
    )

    assert result[
        "pillar_count"
    ] == 7

    assert len(
        result[
            "pillars"
        ]
    ) == 7


def test_calculate_luck_pillars_datetime_strings():
    result = (
        make_external_forward_result(
            count=3
        )
    )

    for pillar in result[
        "pillars"
    ]:
        assert isinstance(
            pillar[
                "start_datetime"
            ],
            str,
        )

        assert isinstance(
            pillar[
                "end_datetime"
            ],
            str,
        )

        assert (
            "T"
            in pillar[
                "start_datetime"
            ]
        )

        assert (
            "T"
            in pillar[
                "end_datetime"
            ]
        )


def test_calculation_rules():
    result = (
        make_external_forward_result()
    )

    rules = result[
        "calculation_rules"
    ]

    assert rules[
        "direction_rule"
    ] == (
        "陽男陰女順行・陰男陽女逆行"
    )

    assert rules[
        "start_age_rule"
    ] == "三日一年法"

    assert rules[
        "month_pillar_rule"
    ] == (
        "月柱の次干支から第1大運"
    )

    assert rules[
        "pillar_duration_years"
    ] == 10


def test_result_notes_exist():
    result = (
        make_external_forward_result()
    )

    assert isinstance(
        result["notes"],
        list,
    )

    assert result["notes"]


# ============================================================
# useful_gods integration
# ============================================================


def test_calculate_luck_pillars_with_useful_gods():
    result = (
        make_external_forward_result(
            count=5,
            useful_gods=(
                make_useful_gods()
            ),
        )
    )

    for pillar in result[
        "pillars"
    ]:
        assert (
            pillar[
                "stem_useful_relation"
            ][
                "relationship"
            ]
            in {
                "primary_useful",
                "secondary_useful",
                "support_unfavorable",
                "neutral",
            }
        )

        assert (
            pillar[
                "branch_useful_relation"
            ][
                "relationship"
            ]
            in {
                "primary_useful",
                "secondary_useful",
                "support_unfavorable",
                "neutral",
            }
        )


# ============================================================
# Automatic solar-term integration
# ============================================================


def test_calculate_luck_pillars_auto_term_forward():
    result = calculate_luck_pillars(
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
        count=3,
    )

    assert (
        result[
            "target_term_source"
        ]
        == "solar_terms_v2"
    )

    assert result[
        "target_term_name"
    ] is not None

    assert result[
        "target_term_branch"
    ] in EARTHLY_BRANCHES

    assert result[
        "term_distance_days"
    ] >= 0.0

    assert result[
        "start_age"
    ] >= 0.0


def test_calculate_luck_pillars_auto_term_backward():
    result = calculate_luck_pillars(
        year_stem="甲",
        month_ganzhi="辛未",
        day_master_stem="乙",
        gender="female",
        birth_datetime=datetime(
            1984,
            7,
            22,
            4,
            15,
        ),
        count=3,
    )

    assert (
        result[
            "target_term_source"
        ]
        == "solar_terms_v2"
    )

    assert (
        datetime.fromisoformat(
            result[
                "target_term_datetime"
            ]
        )
        < datetime(
            1984,
            7,
            22,
            4,
            15,
        )
    )


# ============================================================
# Compatibility alias
# ============================================================


def test_evaluate_luck_pillars_alias():
    kwargs = {
        "year_stem": "甲",
        "month_ganzhi": "辛未",
        "day_master_stem": "乙",
        "gender": "male",
        "birth_datetime": datetime(
            1984,
            7,
            22,
            4,
            15,
        ),
        "target_term_datetime": (
            datetime(
                1984,
                7,
                28,
                4,
                15,
            )
        ),
        "count": 5,
        "useful_gods": (
            make_useful_gods()
        ),
    }

    direct = calculate_luck_pillars(
        **kwargs
    )

    alias = evaluate_luck_pillars(
        **kwargs
    )

    assert alias == direct


# ============================================================
# Gender normalization
# ============================================================


def test_japanese_male_normalized():
    result = calculate_luck_pillars(
        year_stem="甲",
        month_ganzhi="辛未",
        day_master_stem="乙",
        gender="男",
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
        count=1,
    )

    assert result[
        "gender"
    ] == "male"


def test_japanese_female_normalized():
    result = calculate_luck_pillars(
        year_stem="乙",
        month_ganzhi="辛未",
        day_master_stem="乙",
        gender="女",
        birth_datetime=datetime(
            1985,
            7,
            17,
            21,
            50,
        ),
        target_term_datetime=datetime(
            1985,
            7,
            23,
            21,
            50,
        ),
        count=1,
    )

    assert result[
        "gender"
    ] == "female"


# ============================================================
# Invalid main API input
# ============================================================


def test_calculate_luck_pillars_invalid_year_stem():
    with pytest.raises(ValueError):
        calculate_luck_pillars(
            year_stem="A",
            month_ganzhi="辛未",
            day_master_stem="乙",
            gender="male",
            birth_datetime=datetime(
                1984,
                7,
                22,
            ),
            target_term_datetime=datetime(
                1984,
                7,
                28,
            ),
        )


def test_calculate_luck_pillars_invalid_day_master():
    with pytest.raises(ValueError):
        calculate_luck_pillars(
            year_stem="甲",
            month_ganzhi="辛未",
            day_master_stem="A",
            gender="male",
            birth_datetime=datetime(
                1984,
                7,
                22,
            ),
            target_term_datetime=datetime(
                1984,
                7,
                28,
            ),
        )


def test_calculate_luck_pillars_invalid_month_ganzhi():
    with pytest.raises(ValueError):
        calculate_luck_pillars(
            year_stem="甲",
            month_ganzhi="辛",
            day_master_stem="乙",
            gender="male",
            birth_datetime=datetime(
                1984,
                7,
                22,
            ),
            target_term_datetime=datetime(
                1984,
                7,
                28,
            ),
        )


def test_calculate_luck_pillars_invalid_gender():
    with pytest.raises(ValueError):
        calculate_luck_pillars(
            year_stem="甲",
            month_ganzhi="辛未",
            day_master_stem="乙",
            gender="x",
            birth_datetime=datetime(
                1984,
                7,
                22,
            ),
            target_term_datetime=datetime(
                1984,
                7,
                28,
            ),
        )


def test_calculate_luck_pillars_invalid_birth_datetime():
    with pytest.raises(TypeError):
        calculate_luck_pillars(
            year_stem="甲",
            month_ganzhi="辛未",
            day_master_stem="乙",
            gender="male",
            birth_datetime="1984-07-22",
            target_term_datetime=datetime(
                1984,
                7,
                28,
            ),
        )


def test_calculate_luck_pillars_invalid_target_datetime():
    with pytest.raises(TypeError):
        calculate_luck_pillars(
            year_stem="甲",
            month_ganzhi="辛未",
            day_master_stem="乙",
            gender="male",
            birth_datetime=datetime(
                1984,
                7,
                22,
            ),
            target_term_datetime=(
                "1984-07-28"
            ),
        )


def test_calculate_luck_pillars_invalid_count_type():
    with pytest.raises(TypeError):
        calculate_luck_pillars(
            year_stem="甲",
            month_ganzhi="辛未",
            day_master_stem="乙",
            gender="male",
            birth_datetime=datetime(
                1984,
                7,
                22,
            ),
            target_term_datetime=datetime(
                1984,
                7,
                28,
            ),
            count=1.5,
        )


def test_calculate_luck_pillars_invalid_count_zero():
    with pytest.raises(ValueError):
        calculate_luck_pillars(
            year_stem="甲",
            month_ganzhi="辛未",
            day_master_stem="乙",
            gender="male",
            birth_datetime=datetime(
                1984,
                7,
                22,
            ),
            target_term_datetime=datetime(
                1984,
                7,
                28,
            ),
            count=0,
        )


# ============================================================
# Regression invariants
# ============================================================


def test_first_pillar_is_one_step_after_month_forward():
    result = (
        make_external_forward_result(
            count=1
        )
    )

    assert (
        result["pillars"][0][
            "ganzhi"
        ]
        == shift_ganzhi(
            "辛未",
            1,
        )
    )


def test_first_pillar_is_one_step_before_month_backward():
    result = (
        make_external_backward_result(
            count=1
        )
    )

    assert (
        result["pillars"][0][
            "ganzhi"
        ]
        == shift_ganzhi(
            "辛未",
            -1,
        )
    )


def test_all_pillars_have_required_keys():
    result = (
        make_external_forward_result(
            count=3,
            useful_gods=(
                make_useful_gods()
            ),
        )
    )

    required = {
        "index",
        "ganzhi",
        "stem",
        "branch",
        "stem_element",
        "branch_element",
        "stem_yin_yang",
        "stem_ten_god",
        "start_age",
        "end_age",
        "start_age_detail",
        "end_age_detail",
        "start_datetime",
        "end_datetime",
        "stem_useful_relation",
        "branch_useful_relation",
    }

    for pillar in result[
        "pillars"
    ]:
        assert required.issubset(
            pillar.keys()
        )


def test_pillar_indices_are_contiguous():
    result = (
        make_external_forward_result(
            count=10
        )
    )

    assert [
        pillar["index"]
        for pillar in result[
            "pillars"
        ]
    ] == list(
        range(
            1,
            11,
        )
    )


def test_pillar_ganzhi_are_unique_for_first_ten():
    result = (
        make_external_forward_result(
            count=10
        )
    )

    ganzhi = [
        pillar["ganzhi"]
        for pillar in result[
            "pillars"
        ]
    ]

    assert len(ganzhi) == len(
        set(ganzhi)
    )


def test_pillar_start_datetime_precedes_end_datetime():
    result = (
        make_external_forward_result(
            count=10
        )
    )

    for pillar in result[
        "pillars"
    ]:
        start = datetime.fromisoformat(
            pillar[
                "start_datetime"
            ]
        )

        end = datetime.fromisoformat(
            pillar[
                "end_datetime"
            ]
        )

        assert start < end


def test_each_pillar_end_equals_next_start_age():
    result = (
        make_external_forward_result(
            count=10
        )
    )

    pillars = result[
        "pillars"
    ]

    for current, nxt in zip(
        pillars,
        pillars[1:],
    ):
        assert (
            current[
                "end_age"
            ]
            == nxt[
                "start_age"
            ]
        )


def test_external_forward_is_deterministic():
    first = (
        make_external_forward_result()
    )

    second = (
        make_external_forward_result()
    )

    assert first == second


def test_external_backward_is_deterministic():
    first = (
        make_external_backward_result()
    )

    second = (
        make_external_backward_result()
    )

    assert first == second
