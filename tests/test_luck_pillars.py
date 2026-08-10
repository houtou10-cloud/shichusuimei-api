"""
tests/test_luck_pillars.py

engine/luck_pillars.py の単体テスト。

検証対象
--------
- 六十干支
- 干支分割
- 順行・逆行
- 三日一年法
- 年齢表示
- 開始日時概算
- 五行関係
- 通変星
- useful_gods_v3 との関係
- 大運干支生成
- 1本の大運データ
- calculate_luck_pillars()
- evaluate_luck_pillars()
- 1984年甲子年の順逆
- 辛未月からの順行・逆行
"""

from datetime import datetime

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
    shift_ganzhi,
    split_ganzhi,
)


# =========================================================
# Fixtures
# =========================================================


def make_useful_gods():
    return {
        "primary_useful_element": "水",
        "final_useful_elements": [
            "水",
            "木",
            "火",
        ],
        "support_balance": {
            "unfavorable_elements": [
                "土",
                "金",
            ],
        },
        "method": "useful_gods_v3",
    }


# =========================================================
# Constants
# =========================================================


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


def test_stem_to_element():
    assert STEM_TO_ELEMENT["甲"] == "木"
    assert STEM_TO_ELEMENT["丁"] == "火"
    assert STEM_TO_ELEMENT["己"] == "土"
    assert STEM_TO_ELEMENT["辛"] == "金"
    assert STEM_TO_ELEMENT["癸"] == "水"


def test_stem_to_yin_yang():
    assert STEM_TO_YIN_YANG["甲"] == "陽"
    assert STEM_TO_YIN_YANG["乙"] == "陰"
    assert STEM_TO_YIN_YANG["庚"] == "陽"
    assert STEM_TO_YIN_YANG["辛"] == "陰"


def test_branch_to_element():
    assert BRANCH_TO_ELEMENT["子"] == "水"
    assert BRANCH_TO_ELEMENT["寅"] == "木"
    assert BRANCH_TO_ELEMENT["巳"] == "火"
    assert BRANCH_TO_ELEMENT["申"] == "金"
    assert BRANCH_TO_ELEMENT["未"] == "土"


def test_sexagenary_cycle_length():
    assert len(
        SEXAGENARY_CYCLE
    ) == 60


def test_sexagenary_cycle_edges():
    assert SEXAGENARY_CYCLE[0] == "甲子"
    assert SEXAGENARY_CYCLE[-1] == "癸亥"


# =========================================================
# Ganzhi helpers
# =========================================================


@pytest.mark.parametrize(
    (
        "ganzhi",
        "expected_stem",
        "expected_branch",
    ),
    [
        ("甲子", "甲", "子"),
        ("辛未", "辛", "未"),
        ("癸亥", "癸", "亥"),
    ],
)
def test_split_ganzhi(
    ganzhi,
    expected_stem,
    expected_branch,
):
    stem, branch = split_ganzhi(
        ganzhi
    )

    assert stem == expected_stem
    assert branch == expected_branch


def test_split_ganzhi_invalid_type():
    with pytest.raises(
        ValueError
    ):
        split_ganzhi(
            123
        )


def test_split_ganzhi_invalid_length():
    with pytest.raises(
        ValueError
    ):
        split_ganzhi(
            "甲"
        )


def test_split_ganzhi_invalid_stem():
    with pytest.raises(
        ValueError
    ):
        split_ganzhi(
            "A子"
        )


def test_split_ganzhi_invalid_branch():
    with pytest.raises(
        ValueError
    ):
        split_ganzhi(
            "甲A"
        )


def test_get_sexagenary_index():
    assert (
        get_sexagenary_index(
            "甲子"
        )
        == 0
    )

    assert (
        get_sexagenary_index(
            "辛未"
        )
        == SEXAGENARY_CYCLE.index(
            "辛未"
        )
    )


def test_get_sexagenary_index_invalid():
    with pytest.raises(
        ValueError
    ):
        get_sexagenary_index(
            "甲丑"
        )


def test_shift_ganzhi_forward():
    assert (
        shift_ganzhi(
            "辛未",
            1,
        )
        == "壬申"
    )


def test_shift_ganzhi_backward():
    assert (
        shift_ganzhi(
            "辛未",
            -1,
        )
        == "庚午"
    )


def test_shift_ganzhi_wrap_forward():
    assert (
        shift_ganzhi(
            "癸亥",
            1,
        )
        == "甲子"
    )


def test_shift_ganzhi_wrap_backward():
    assert (
        shift_ganzhi(
            "甲子",
            -1,
        )
        == "癸亥"
    )


# =========================================================
# Direction
# =========================================================


@pytest.mark.parametrize(
    (
        "year_stem",
        "gender",
        "expected",
    ),
    [
        ("甲", "male", "forward"),
        ("甲", "男", "forward"),
        ("甲", "female", "backward"),
        ("甲", "女", "backward"),
        ("乙", "male", "backward"),
        ("乙", "男", "backward"),
        ("乙", "female", "forward"),
        ("乙", "女", "forward"),
        ("庚", "male", "forward"),
        ("辛", "female", "forward"),
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
    with pytest.raises(
        ValueError
    ):
        determine_luck_direction(
            "A",
            "male",
        )


def test_determine_luck_direction_invalid_gender():
    with pytest.raises(
        ValueError
    ):
        determine_luck_direction(
            "甲",
            "unknown",
        )


def test_1984_jiazi_male_forward():
    assert (
        determine_luck_direction(
            "甲",
            "male",
        )
        == "forward"
    )


def test_1984_jiazi_female_backward():
    assert (
        determine_luck_direction(
            "甲",
            "female",
        )
        == "backward"
    )


# =========================================================
# Start age
# =========================================================


def test_calculate_term_distance_days_exact_three_days():
    birth = datetime(
        1984,
        7,
        10,
        0,
        0,
    )

    term = datetime(
        1984,
        7,
        13,
        0,
        0,
    )

    assert (
        calculate_term_distance_days(
            birth,
            term,
        )
        == 3.0
    )


def test_calculate_term_distance_days_absolute():
    birth = datetime(
        1984,
        7,
        10,
        0,
        0,
    )

    term = datetime(
        1984,
        7,
        7,
        0,
        0,
    )

    assert (
        calculate_term_distance_days(
            birth,
            term,
        )
        == 3.0
    )


def test_calculate_term_distance_days_birth_type_error():
    with pytest.raises(
        TypeError
    ):
        calculate_term_distance_days(
            "1984-07-10",
            datetime(
                1984,
                7,
                13,
            ),
        )


def test_calculate_term_distance_days_term_type_error():
    with pytest.raises(
        TypeError
    ):
        calculate_term_distance_days(
            datetime(
                1984,
                7,
                10,
            ),
            "1984-07-13",
        )


def test_calculate_start_age_three_days_is_one_year():
    birth = datetime(
        1984,
        7,
        10,
        0,
        0,
    )

    term = datetime(
        1984,
        7,
        13,
        0,
        0,
    )

    assert (
        calculate_start_age(
            birth,
            term,
        )
        == 1.0
    )


def test_calculate_start_age_six_days_is_two_years():
    birth = datetime(
        1984,
        7,
        10,
        0,
        0,
    )

    term = datetime(
        1984,
        7,
        16,
        0,
        0,
    )

    assert (
        calculate_start_age(
            birth,
            term,
        )
        == 2.0
    )


# =========================================================
# Age detail / datetime
# =========================================================


def test_age_to_year_month_day_zero():
    assert (
        age_to_year_month_day(
            0.0
        )
        == {
            "years": 0,
            "months": 0,
            "days": 0,
        }
    )


def test_age_to_year_month_day_one_and_half():
    assert (
        age_to_year_month_day(
            1.5
        )
        == {
            "years": 1,
            "months": 6,
            "days": 0,
        }
    )


def test_age_to_year_month_day_negative():
    with pytest.raises(
        ValueError
    ):
        age_to_year_month_day(
            -1.0
        )


def test_estimate_start_datetime_one_year():
    birth = datetime(
        2000,
        1,
        1,
        0,
        0,
    )

    result = estimate_start_datetime(
        birth,
        1.0,
    )

    assert result > birth

    delta_days = (
        result - birth
    ).total_seconds() / 86400.0

    assert delta_days == pytest.approx(
        365.2425
    )


# =========================================================
# Five-element relations
# =========================================================


@pytest.mark.parametrize(
    (
        "day_master_element",
        "target_element",
        "expected",
    ),
    [
        ("木", "木", "same"),
        ("木", "水", "resource"),
        ("木", "火", "output"),
        ("木", "土", "wealth"),
        ("木", "金", "officer"),
        ("火", "木", "resource"),
        ("土", "金", "output"),
        ("金", "木", "wealth"),
        ("水", "土", "officer"),
    ],
)
def test_get_element_relation(
    day_master_element,
    target_element,
    expected,
):
    assert (
        get_element_relation(
            day_master_element,
            target_element,
        )
        == expected
    )


def test_get_element_relation_invalid_day_master():
    with pytest.raises(
        ValueError
    ):
        get_element_relation(
            "空",
            "木",
        )


def test_get_element_relation_invalid_target():
    with pytest.raises(
        ValueError
    ):
        get_element_relation(
            "木",
            "空",
        )


# =========================================================
# Ten gods
# =========================================================


@pytest.mark.parametrize(
    (
        "day_master",
        "target",
        "expected",
    ),
    [
        ("甲", "甲", "比肩"),
        ("甲", "乙", "劫財"),
        ("甲", "壬", "偏印"),
        ("甲", "癸", "印綬"),
        ("甲", "丙", "食神"),
        ("甲", "丁", "傷官"),
        ("甲", "戊", "偏財"),
        ("甲", "己", "正財"),
        ("甲", "庚", "偏官"),
        ("甲", "辛", "正官"),
        ("乙", "乙", "比肩"),
        ("乙", "甲", "劫財"),
    ],
)
def test_get_ten_god_for_stem(
    day_master,
    target,
    expected,
):
    assert (
        get_ten_god_for_stem(
            day_master,
            target,
        )
        == expected
    )


def test_get_ten_god_invalid_day_master():
    with pytest.raises(
        ValueError
    ):
        get_ten_god_for_stem(
            "A",
            "甲",
        )


def test_get_ten_god_invalid_target():
    with pytest.raises(
        ValueError
    ):
        get_ten_god_for_stem(
            "甲",
            "A",
        )


# =========================================================
# Useful gods relation
# =========================================================


def test_element_against_useful_gods_without_data():
    result = (
        evaluate_element_against_useful_gods(
            "水",
            None,
        )
    )

    assert result == {
        "is_useful": None,
        "is_primary_useful": None,
        "priority": None,
        "relationship": "unknown",
    }


def test_element_against_useful_gods_primary():
    result = (
        evaluate_element_against_useful_gods(
            "水",
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


def test_element_against_useful_gods_secondary():
    result = (
        evaluate_element_against_useful_gods(
            "木",
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


def test_element_against_useful_gods_unfavorable():
    result = (
        evaluate_element_against_useful_gods(
            "金",
            make_useful_gods(),
        )
    )

    assert result[
        "is_useful"
    ] is False

    assert result[
        "relationship"
    ] == "support_unfavorable"


def test_element_against_useful_gods_neutral():
    useful = make_useful_gods()

    useful[
        "final_useful_elements"
    ] = [
        "水",
    ]

    useful[
        "support_balance"
    ][
        "unfavorable_elements"
    ] = [
        "金",
    ]

    result = (
        evaluate_element_against_useful_gods(
            "火",
            useful,
        )
    )

    assert result[
        "relationship"
    ] == "neutral"


def test_element_against_useful_gods_invalid():
    with pytest.raises(
        ValueError
    ):
        evaluate_element_against_useful_gods(
            "空",
            make_useful_gods(),
        )


# =========================================================
# Generate luck ganzhi
# =========================================================


def test_generate_luck_ganzhi_forward_from_xinwei():
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


def test_generate_luck_ganzhi_backward_from_xinwei():
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


def test_generate_luck_ganzhi_invalid_direction():
    with pytest.raises(
        ValueError
    ):
        generate_luck_ganzhi(
            "辛未",
            "sideways",
        )


def test_generate_luck_ganzhi_invalid_count_type():
    with pytest.raises(
        TypeError
    ):
        generate_luck_ganzhi(
            "辛未",
            "forward",
            count=1.5,
        )


def test_generate_luck_ganzhi_invalid_count_value():
    with pytest.raises(
        ValueError
    ):
        generate_luck_ganzhi(
            "辛未",
            "forward",
            count=0,
        )


def test_generate_luck_ganzhi_invalid_month_ganzhi():
    with pytest.raises(
        ValueError
    ):
        generate_luck_ganzhi(
            "甲丑",
            "forward",
        )


# =========================================================
# Single pillar
# =========================================================


def test_build_luck_pillar_data_basic():
    birth = datetime(
        1984,
        7,
        10,
        0,
        0,
    )

    result = build_luck_pillar_data(
        index=1,
        ganzhi="壬申",
        day_master_stem="乙",
        start_age=2.0,
        birth_datetime=birth,
        useful_gods=make_useful_gods(),
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
        "stem_ten_god"
    ] == "印綬"

    assert result[
        "start_age"
    ] == 2.0

    assert result[
        "end_age"
    ] == 12.0

    assert result[
        "start_datetime"
    ] is not None

    assert result[
        "end_datetime"
    ] is not None

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
        == "support_unfavorable"
    )


def test_build_luck_pillar_data_second_pillar_age():
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


def test_build_luck_pillar_data_without_birth_datetime():
    result = build_luck_pillar_data(
        index=1,
        ganzhi="壬申",
        day_master_stem="乙",
        start_age=2.0,
    )

    assert result[
        "start_datetime"
    ] is None

    assert result[
        "end_datetime"
    ] is None


# =========================================================
# Main API
# =========================================================


def test_calculate_luck_pillars_forward():
    birth = datetime(
        1984,
        7,
        10,
        0,
        0,
    )

    term = datetime(
        1984,
        7,
        16,
        0,
        0,
    )

    result = calculate_luck_pillars(
        year_stem="甲",
        month_ganzhi="辛未",
        day_master_stem="乙",
        gender="male",
        birth_datetime=birth,
        target_term_datetime=term,
        count=5,
        useful_gods=make_useful_gods(),
    )

    assert (
        result[
            "direction"
        ]
        == "forward"
    )

    assert (
        result[
            "direction_japanese"
        ]
        == "順行"
    )

    assert (
        result[
            "start_age"
        ]
        == 2.0
    )

    assert (
        result[
            "pillar_count"
        ]
        == 5
    )

    assert [
        pillar[
            "ganzhi"
        ]
        for pillar in result[
            "pillars"
        ]
    ] == [
        "壬申",
        "癸酉",
        "甲戌",
        "乙亥",
        "丙子",
    ]

    assert (
        result[
            "method"
        ]
        == "luck_pillars_v1"
    )

    assert (
        result[
            "status"
        ]
        == "provisional_luck_pillars_v1"
    )


def test_calculate_luck_pillars_backward():
    birth = datetime(
        1984,
        7,
        10,
        0,
        0,
    )

    term = datetime(
        1984,
        7,
        4,
        0,
        0,
    )

    result = calculate_luck_pillars(
        year_stem="甲",
        month_ganzhi="辛未",
        day_master_stem="乙",
        gender="female",
        birth_datetime=birth,
        target_term_datetime=term,
        count=5,
    )

    assert (
        result[
            "direction"
        ]
        == "backward"
    )

    assert (
        result[
            "direction_japanese"
        ]
        == "逆行"
    )

    assert [
        pillar[
            "ganzhi"
        ]
        for pillar in result[
            "pillars"
        ]
    ] == [
        "庚午",
        "己巳",
        "戊辰",
        "丁卯",
        "丙寅",
    ]


def test_calculate_luck_pillars_metadata():
    birth = datetime(
        1984,
        7,
        10,
        0,
        0,
    )

    term = datetime(
        1984,
        7,
        16,
        0,
        0,
    )

    result = calculate_luck_pillars(
        year_stem="甲",
        month_ganzhi="辛未",
        day_master_stem="乙",
        gender="男",
        birth_datetime=birth,
        target_term_datetime=term,
        count=1,
    )

    assert (
        result[
            "year_stem"
        ]
        == "甲"
    )

    assert (
        result[
            "year_stem_yin_yang"
        ]
        == "陽"
    )

    assert (
        result[
            "gender"
        ]
        == "male"
    )

    assert (
        result[
            "month_ganzhi"
        ]
        == "辛未"
    )

    assert (
        result[
            "day_master_stem"
        ]
        == "乙"
    )

    assert (
        result[
            "day_master_element"
        ]
        == "木"
    )

    assert (
        result[
            "term_distance_days"
        ]
        == 6.0
    )

    assert (
        result[
            "calculation_rules"
        ][
            "direction_rule"
        ]
        == "陽男陰女順行・陰男陽女逆行"
    )

    assert (
        result[
            "calculation_rules"
        ][
            "start_age_rule"
        ]
        == "三日一年法"
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


def test_calculate_luck_pillars_age_ranges():
    birth = datetime(
        1984,
        7,
        10,
        0,
        0,
    )

    term = datetime(
        1984,
        7,
        16,
        0,
        0,
    )

    result = calculate_luck_pillars(
        year_stem="甲",
        month_ganzhi="辛未",
        day_master_stem="乙",
        gender="male",
        birth_datetime=birth,
        target_term_datetime=term,
        count=3,
    )

    ages = [
        (
            pillar[
                "start_age"
            ],
            pillar[
                "end_age"
            ],
        )
        for pillar in result[
            "pillars"
        ]
    ]

    assert ages == [
        (2.0, 12.0),
        (12.0, 22.0),
        (22.0, 32.0),
    ]


def test_calculate_luck_pillars_invalid_year_stem():
    with pytest.raises(
        ValueError
    ):
        calculate_luck_pillars(
            year_stem="A",
            month_ganzhi="辛未",
            day_master_stem="乙",
            gender="male",
            birth_datetime=datetime(
                1984,
                7,
                10,
            ),
            target_term_datetime=datetime(
                1984,
                7,
                16,
            ),
        )


def test_calculate_luck_pillars_invalid_day_master():
    with pytest.raises(
        ValueError
    ):
        calculate_luck_pillars(
            year_stem="甲",
            month_ganzhi="辛未",
            day_master_stem="A",
            gender="male",
            birth_datetime=datetime(
                1984,
                7,
                10,
            ),
            target_term_datetime=datetime(
                1984,
                7,
                16,
            ),
        )


def test_calculate_luck_pillars_invalid_month_ganzhi():
    with pytest.raises(
        ValueError
    ):
        calculate_luck_pillars(
            year_stem="甲",
            month_ganzhi="甲丑",
            day_master_stem="乙",
            gender="male",
            birth_datetime=datetime(
                1984,
                7,
                10,
            ),
            target_term_datetime=datetime(
                1984,
                7,
                16,
            ),
        )


def test_calculate_luck_pillars_invalid_gender():
    with pytest.raises(
        ValueError
    ):
        calculate_luck_pillars(
            year_stem="甲",
            month_ganzhi="辛未",
            day_master_stem="乙",
            gender="x",
            birth_datetime=datetime(
                1984,
                7,
                10,
            ),
            target_term_datetime=datetime(
                1984,
                7,
                16,
            ),
        )


# =========================================================
# Alias
# =========================================================


def test_evaluate_luck_pillars_alias_matches_calculate():
    kwargs = {
        "year_stem": "甲",
        "month_ganzhi": "辛未",
        "day_master_stem": "乙",
        "gender": "male",
        "birth_datetime": datetime(
            1984,
            7,
            10,
            0,
            0,
        ),
        "target_term_datetime": datetime(
            1984,
            7,
            16,
            0,
            0,
        ),
        "count": 3,
        "useful_gods": (
            make_useful_gods()
        ),
    }

    assert (
        evaluate_luck_pillars(
            **kwargs
        )
        == calculate_luck_pillars(
            **kwargs
        )
    )


# =========================================================
# Relation tables sanity
# =========================================================


def test_generates_mapping():
    assert GENERATES == {
        "木": "火",
        "火": "土",
        "土": "金",
        "金": "水",
        "水": "木",
    }


def test_generated_by_mapping():
    assert GENERATED_BY == {
        "火": "木",
        "土": "火",
        "金": "土",
        "水": "金",
        "木": "水",
    }


def test_controls_mapping():
    assert CONTROLS == {
        "木": "土",
        "火": "金",
        "土": "水",
        "金": "木",
        "水": "火",
    }


def test_controlled_by_mapping():
    assert CONTROLLED_BY == {
        "土": "木",
        "金": "火",
        "水": "土",
        "木": "金",
        "火": "水",
    }
