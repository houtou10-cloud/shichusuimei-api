import pytest

from engine.pattern_candidates import (
    build_jianlu_candidate,
    build_standard_pattern_candidate,
    build_yangren_candidate,
    candidate_priority,
    count_candidate_groups,
    determine_primary_candidate,
    evaluate_pattern_candidates,
    find_exposure_positions,
    validate_chart_data,
    validate_day_master_stem,
)


def make_pillar(
    pillar="甲子",
    stem="甲",
    branch="子",
    stem_ten_god="劫財",
    hidden_stems=None,
    main_hidden_stem="癸",
    main_hidden_stem_ten_god="偏印",
):
    if hidden_stems is None:
        hidden_stems = [
            "癸",
        ]

    return {
        "pillar": pillar,
        "stem": stem,
        "branch": branch,
        "stem_ten_god": stem_ten_god,
        "hidden_stems": hidden_stems,
        "main_hidden_stem": (
            main_hidden_stem
        ),
        "main_hidden_stem_ten_god": (
            main_hidden_stem_ten_god
        ),
        "hidden_stem_ten_gods": [
            {
                "stem": hidden_stem,
                "ten_god": None,
            }
            for hidden_stem in hidden_stems
        ],
        "twelve_stage": "仮",
    }


def make_chart(
    day_stem="乙",
    month_branch="未",
    month_stem="癸",
    month_hidden_stems=None,
    month_main_hidden_stem="己",
    month_main_hidden_stem_ten_god="偏財",
    year_stem="甲",
    hour_stem="丁",
):
    if month_hidden_stems is None:
        month_hidden_stems = [
            "己",
            "丁",
            "乙",
        ]

    return {
        "year": make_pillar(
            pillar=f"{year_stem}子",
            stem=year_stem,
            branch="子",
            stem_ten_god="劫財",
            hidden_stems=[
                "癸",
            ],
            main_hidden_stem="癸",
            main_hidden_stem_ten_god="偏印",
        ),
        "month": make_pillar(
            pillar=f"{month_stem}{month_branch}",
            stem=month_stem,
            branch=month_branch,
            stem_ten_god="偏印",
            hidden_stems=month_hidden_stems,
            main_hidden_stem=month_main_hidden_stem,
            main_hidden_stem_ten_god=(
                month_main_hidden_stem_ten_god
            ),
        ),
        "day": make_pillar(
            pillar=f"{day_stem}巳",
            stem=day_stem,
            branch="巳",
            stem_ten_god=None,
            hidden_stems=[
                "丙",
                "戊",
                "庚",
            ],
            main_hidden_stem="丙",
            main_hidden_stem_ten_god="傷官",
        ),
        "hour": make_pillar(
            pillar=f"{hour_stem}亥",
            stem=hour_stem,
            branch="亥",
            stem_ten_god="食神",
            hidden_stems=[
                "壬",
                "甲",
            ],
            main_hidden_stem="壬",
            main_hidden_stem_ten_god="印綬",
        ),
    }


# =========================================================
# validation
# =========================================================


def test_validate_day_master_stem():
    validate_day_master_stem(
        "乙"
    )


def test_validate_day_master_stem_invalid_type():
    with pytest.raises(
        TypeError,
        match=(
            "day_master_stemは"
            "str型"
        ),
    ):
        validate_day_master_stem(
            123
        )


def test_validate_day_master_stem_invalid_value():
    with pytest.raises(
        ValueError,
        match=(
            "不正なday_master_stem"
        ),
    ):
        validate_day_master_stem(
            "A"
        )


def test_validate_chart_data():
    validate_chart_data(
        make_chart()
    )


def test_validate_chart_data_invalid_type():
    with pytest.raises(
        TypeError,
        match=(
            "chart_dataはdict型"
        ),
    ):
        validate_chart_data(
            []
        )


@pytest.mark.parametrize(
    "position",
    [
        "year",
        "month",
        "day",
    ],
)
def test_validate_chart_data_missing_required_position(
    position,
):
    chart = make_chart()

    chart.pop(
        position
    )

    with pytest.raises(
        ValueError,
        match=(
            f"chart_dataに{position}"
        ),
    ):
        validate_chart_data(
            chart
        )


@pytest.mark.parametrize(
    "position",
    [
        "year",
        "month",
        "day",
    ],
)
def test_validate_chart_data_invalid_required_pillar_type(
    position,
):
    chart = make_chart()

    chart[
        position
    ] = []

    with pytest.raises(
        TypeError,
        match=(
            f"{position}柱はdict型"
        ),
    ):
        validate_chart_data(
            chart
        )


def test_validate_chart_data_hour_none_allowed():
    chart = make_chart()

    chart["hour"] = None

    validate_chart_data(
        chart
    )


def test_validate_chart_data_invalid_hour_type():
    chart = make_chart()

    chart["hour"] = []

    with pytest.raises(
        TypeError,
        match=(
            "hour柱はdict型または"
            "None"
        ),
    ):
        validate_chart_data(
            chart
        )


@pytest.mark.parametrize(
    "key",
    [
        "stem",
        "branch",
        "hidden_stems",
        "main_hidden_stem",
        "main_hidden_stem_ten_god",
    ],
)
def test_validate_chart_data_missing_month_key(
    key,
):
    chart = make_chart()

    chart["month"].pop(
        key
    )

    with pytest.raises(
        ValueError,
        match=(
            f"month柱に{key}"
        ),
    ):
        validate_chart_data(
            chart
        )


def test_validate_chart_data_invalid_hidden_stems_type():
    chart = make_chart()

    chart[
        "month"
    ][
        "hidden_stems"
    ] = {}

    with pytest.raises(
        TypeError,
        match=(
            "month.hidden_stemsは"
            "list型"
        ),
    ):
        validate_chart_data(
            chart
        )


def test_validate_chart_data_invalid_main_hidden_stem_type():
    chart = make_chart()

    chart[
        "month"
    ][
        "main_hidden_stem"
    ] = 123

    with pytest.raises(
        TypeError,
        match=(
            "month.main_hidden_stemは"
            "str型"
        ),
    ):
        validate_chart_data(
            chart
        )


def test_validate_chart_data_invalid_main_hidden_stem_ten_god_type():
    chart = make_chart()

    chart[
        "month"
    ][
        "main_hidden_stem_ten_god"
    ] = None

    with pytest.raises(
        TypeError,
        match=(
            "month.main_hidden_stem_ten_godは"
            "str型"
        ),
    ):
        validate_chart_data(
            chart
        )


# =========================================================
# exposure
# =========================================================


def test_find_exposure_positions_year():
    chart = make_chart(
        month_main_hidden_stem="甲",
        year_stem="甲",
    )

    result = (
        find_exposure_positions(
            "甲",
            chart,
        )
    )

    assert result == [
        "year",
    ]


def test_find_exposure_positions_month():
    chart = make_chart(
        month_stem="己",
        month_main_hidden_stem="己",
    )

    result = (
        find_exposure_positions(
            "己",
            chart,
        )
    )

    assert result == [
        "month",
    ]


def test_find_exposure_positions_hour():
    chart = make_chart(
        hour_stem="己",
        month_main_hidden_stem="己",
    )

    result = (
        find_exposure_positions(
            "己",
            chart,
        )
    )

    assert result == [
        "hour",
    ]


def test_find_exposure_positions_multiple():
    chart = make_chart(
        year_stem="己",
        month_stem="己",
        hour_stem="己",
        month_main_hidden_stem="己",
    )

    result = (
        find_exposure_positions(
            "己",
            chart,
        )
    )

    assert result == [
        "year",
        "month",
        "hour",
    ]


def test_find_exposure_positions_none():
    chart = make_chart(
        year_stem="甲",
        month_stem="癸",
        hour_stem="丁",
        month_main_hidden_stem="己",
    )

    result = (
        find_exposure_positions(
            "己",
            chart,
        )
    )

    assert result == []


def test_find_exposure_positions_day_stem_is_not_counted():
    chart = make_chart(
        day_stem="乙",
        year_stem="甲",
        month_stem="癸",
        hour_stem="丁",
        month_main_hidden_stem="乙",
    )

    result = (
        find_exposure_positions(
            "乙",
            chart,
        )
    )

    assert result == []


def test_find_exposure_positions_hour_none():
    chart = make_chart(
        month_main_hidden_stem="己",
    )

    chart["hour"] = None

    result = (
        find_exposure_positions(
            "己",
            chart,
        )
    )

    assert result == []


def test_find_exposure_positions_invalid_target_type():
    with pytest.raises(
        TypeError,
        match=(
            "target_stemはstr型"
        ),
    ):
        find_exposure_positions(
            123,
            make_chart(),
        )


# =========================================================
# standard pattern candidates
# =========================================================


@pytest.mark.parametrize(
    (
        "ten_god",
        "pattern",
        "technical_pattern",
    ),
    [
        (
            "正官",
            "正官格",
            "direct_officer",
        ),
        (
            "偏官",
            "偏官格",
            "seven_killings",
        ),
        (
            "正財",
            "正財格",
            "direct_wealth",
        ),
        (
            "偏財",
            "偏財格",
            "indirect_wealth",
        ),
        (
            "印綬",
            "印綬格",
            "direct_resource",
        ),
        (
            "正印",
            "印綬格",
            "direct_resource",
        ),
        (
            "偏印",
            "偏印格",
            "indirect_resource",
        ),
        (
            "食神",
            "食神格",
            "eating_god",
        ),
        (
            "傷官",
            "傷官格",
            "hurting_officer",
        ),
    ],
)
def test_build_standard_pattern_candidate(
    ten_god,
    pattern,
    technical_pattern,
):
    chart = make_chart(
        month_main_hidden_stem_ten_god=(
            ten_god
        ),
    )

    result = (
        build_standard_pattern_candidate(
            chart
        )
    )

    assert (
        result["pattern"]
        == pattern
    )

    assert (
        result["technical_pattern"]
        == technical_pattern
    )

    assert (
        result["pattern_group"]
        == "standard_pattern"
    )

    assert (
        result["source"]
        == "month_main_hidden_stem"
    )

    assert (
        result["candidate_status"]
        == "provisional_candidate"
    )

    assert (
        result["is_provisional"]
        is True
    )


@pytest.mark.parametrize(
    "ten_god",
    [
        "比肩",
        "劫財",
        "不明",
    ],
)
def test_build_standard_pattern_candidate_none(
    ten_god,
):
    chart = make_chart(
        month_main_hidden_stem_ten_god=(
            ten_god
        ),
    )

    result = (
        build_standard_pattern_candidate(
            chart
        )
    )

    assert result is None


def test_standard_pattern_exposed_high_confidence():
    chart = make_chart(
        month_stem="己",
        month_main_hidden_stem="己",
        month_main_hidden_stem_ten_god="偏財",
    )

    result = (
        build_standard_pattern_candidate(
            chart
        )
    )

    assert (
        result["is_exposed"]
        is True
    )

    assert (
        result["exposure_positions"]
        == [
            "month",
        ]
    )

    assert (
        result["confidence"]
        == "high"
    )


def test_standard_pattern_not_exposed_medium_confidence():
    chart = make_chart(
        year_stem="甲",
        month_stem="癸",
        hour_stem="丁",
        month_main_hidden_stem="己",
        month_main_hidden_stem_ten_god="偏財",
    )

    result = (
        build_standard_pattern_candidate(
            chart
        )
    )

    assert (
        result["is_exposed"]
        is False
    )

    assert (
        result["exposure_positions"]
        == []
    )

    assert (
        result["confidence"]
        == "medium"
    )


# =========================================================
# jianlu candidate
# =========================================================


@pytest.mark.parametrize(
    (
        "day_stem",
        "month_branch",
    ),
    [
        ("甲", "寅"),
        ("乙", "卯"),
        ("丙", "巳"),
        ("丁", "午"),
        ("戊", "巳"),
        ("己", "午"),
        ("庚", "申"),
        ("辛", "酉"),
        ("壬", "亥"),
        ("癸", "子"),
    ],
)
def test_build_jianlu_candidate(
    day_stem,
    month_branch,
):
    chart = make_chart(
        day_stem=day_stem,
        month_branch=month_branch,
        month_hidden_stems=[
            day_stem,
        ],
        month_main_hidden_stem=(
            day_stem
        ),
        month_main_hidden_stem_ten_god="比肩",
    )

    result = (
        build_jianlu_candidate(
            day_stem,
            chart,
        )
    )

    assert (
        result["pattern"]
        == "建禄格"
    )

    assert (
        result["technical_pattern"]
        == "jianlu"
    )

    assert (
        result["pattern_group"]
        == "special_month_pattern"
    )

    assert (
        result["month_branch"]
        == month_branch
    )

    assert (
        result["expected_branch"]
        == month_branch
    )

    assert (
        result["confidence"]
        == "high"
    )

    assert (
        result["is_provisional"]
        is True
    )


def test_build_jianlu_candidate_none():
    chart = make_chart(
        day_stem="乙",
        month_branch="未",
    )

    result = (
        build_jianlu_candidate(
            "乙",
            chart,
        )
    )

    assert result is None


# =========================================================
# yangren candidate
# =========================================================


@pytest.mark.parametrize(
    (
        "day_stem",
        "month_branch",
    ),
    [
        ("甲", "卯"),
        ("丙", "午"),
        ("戊", "午"),
        ("庚", "酉"),
        ("壬", "子"),
    ],
)
def test_build_yangren_candidate_yang_stem(
    day_stem,
    month_branch,
):
    chart = make_chart(
        day_stem=day_stem,
        month_branch=month_branch,
        month_hidden_stems=[
            day_stem,
        ],
        month_main_hidden_stem=(
            day_stem
        ),
        month_main_hidden_stem_ten_god="劫財",
    )

    result = (
        build_yangren_candidate(
            day_stem,
            chart,
        )
    )

    assert (
        result["pattern"]
        == "羊刃格"
    )

    assert (
        result["technical_pattern"]
        == "yangren"
    )

    assert (
        result["requires_school_rule"]
        is False
    )

    assert (
        result["confidence"]
        == "high"
    )

    assert (
        result["candidate_status"]
        == "provisional_candidate"
    )


@pytest.mark.parametrize(
    (
        "day_stem",
        "month_branch",
    ),
    [
        ("乙", "辰"),
        ("丁", "未"),
        ("己", "未"),
        ("辛", "戌"),
        ("癸", "丑"),
    ],
)
def test_build_yangren_candidate_yin_stem_requires_school_rule(
    day_stem,
    month_branch,
):
    chart = make_chart(
        day_stem=day_stem,
        month_branch=month_branch,
        month_hidden_stems=[
            day_stem,
        ],
        month_main_hidden_stem=(
            day_stem
        ),
        month_main_hidden_stem_ten_god="劫財",
    )

    result = (
        build_yangren_candidate(
            day_stem,
            chart,
        )
    )

    assert (
        result["pattern"]
        == "羊刃格"
    )

    assert (
        result["requires_school_rule"]
        is True
    )

    assert (
        result["confidence"]
        == "medium"
    )

    assert (
        result["candidate_status"]
        == "requires_school_rule"
    )


def test_build_yangren_candidate_none():
    chart = make_chart(
        day_stem="乙",
        month_branch="未",
    )

    result = (
        build_yangren_candidate(
            "乙",
            chart,
        )
    )

    assert result is None


# =========================================================
# candidate helpers
# =========================================================


def make_candidate(
    technical_pattern,
    pattern_group,
    is_exposed=False,
):
    return {
        "technical_pattern": (
            technical_pattern
        ),
        "pattern_group": (
            pattern_group
        ),
        "is_exposed": (
            is_exposed
        ),
    }


def test_candidate_priority_jianlu():
    result = candidate_priority(
        make_candidate(
            "jianlu",
            "special_month_pattern",
        )
    )

    assert result == 300


def test_candidate_priority_yangren():
    result = candidate_priority(
        make_candidate(
            "yangren",
            "special_month_pattern",
        )
    )

    assert result == 290


def test_candidate_priority_standard_exposed():
    result = candidate_priority(
        make_candidate(
            "indirect_wealth",
            "standard_pattern",
            is_exposed=True,
        )
    )

    assert result == 220


def test_candidate_priority_standard_not_exposed():
    result = candidate_priority(
        make_candidate(
            "indirect_wealth",
            "standard_pattern",
            is_exposed=False,
        )
    )

    assert result == 200


def test_candidate_priority_unknown():
    result = candidate_priority(
        make_candidate(
            "unknown",
            "unknown",
        )
    )

    assert result == 0


def test_candidate_priority_invalid_type():
    with pytest.raises(
        TypeError,
        match=(
            "candidateはdict型"
        ),
    ):
        candidate_priority(
            []
        )


def test_determine_primary_candidate_empty():
    assert (
        determine_primary_candidate(
            []
        )
        is None
    )


def test_determine_primary_candidate_prefers_jianlu():
    standard = make_candidate(
        "indirect_wealth",
        "standard_pattern",
        is_exposed=True,
    )

    yangren = make_candidate(
        "yangren",
        "special_month_pattern",
    )

    jianlu = make_candidate(
        "jianlu",
        "special_month_pattern",
    )

    result = (
        determine_primary_candidate(
            [
                standard,
                yangren,
                jianlu,
            ]
        )
    )

    assert result is jianlu


def test_determine_primary_candidate_invalid_type():
    with pytest.raises(
        TypeError,
        match=(
            "candidatesはlist型"
        ),
    ):
        determine_primary_candidate(
            {}
        )


def test_determine_primary_candidate_invalid_item():
    with pytest.raises(
        TypeError,
        match=(
            "candidateはdict型"
        ),
    ):
        determine_primary_candidate(
            [
                [],
            ]
        )


def test_count_candidate_groups():
    result = (
        count_candidate_groups(
            [
                make_candidate(
                    "indirect_wealth",
                    "standard_pattern",
                ),
                make_candidate(
                    "jianlu",
                    "special_month_pattern",
                ),
                make_candidate(
                    "yangren",
                    "special_month_pattern",
                ),
            ]
        )
    )

    assert result == {
        "standard_pattern": 1,
        "special_month_pattern": 2,
    }


def test_count_candidate_groups_empty():
    result = (
        count_candidate_groups(
            []
        )
    )

    assert result == {
        "standard_pattern": 0,
        "special_month_pattern": 0,
    }


def test_count_candidate_groups_invalid_type():
    with pytest.raises(
        TypeError,
        match=(
            "candidatesはlist型"
        ),
    ):
        count_candidate_groups(
            {}
        )


def test_count_candidate_groups_invalid_item():
    with pytest.raises(
        TypeError,
        match=(
            "candidateはdict型"
        ),
    ):
        count_candidate_groups(
            [
                [],
            ]
        )


# =========================================================
# main evaluator
# =========================================================


def test_evaluate_pattern_candidates_standard_only():
    chart = make_chart(
        day_stem="乙",
        month_branch="未",
        month_main_hidden_stem="己",
        month_main_hidden_stem_ten_god="偏財",
    )

    result = (
        evaluate_pattern_candidates(
            chart,
            "乙",
        )
    )

    assert (
        result["has_candidate"]
        is True
    )

    assert (
        result["candidate_count"]
        == 1
    )

    assert (
        result["primary_candidate"][
            "pattern"
        ]
        == "偏財格"
    )

    assert (
        result["candidate_groups"]
        == {
            "standard_pattern": 1,
            "special_month_pattern": 0,
        }
    )

    assert (
        result[
            "has_school_rule_candidate"
        ]
        is False
    )

    assert (
        result["overall_status"]
        == "candidate_detected"
    )

    assert (
        result["method"]
        == "pattern_candidates_v1"
    )

    assert (
        result["status"]
        == "provisional_pattern_candidates"
    )


def test_evaluate_pattern_candidates_jianlu_only():
    chart = make_chart(
        day_stem="乙",
        month_branch="卯",
        month_hidden_stems=[
            "乙",
        ],
        month_main_hidden_stem="乙",
        month_main_hidden_stem_ten_god="比肩",
    )

    result = (
        evaluate_pattern_candidates(
            chart,
            "乙",
        )
    )

    assert (
        result["candidate_count"]
        == 1
    )

    assert (
        result["primary_candidate"][
            "pattern"
        ]
        == "建禄格"
    )

    assert (
        result["candidate_groups"]
        == {
            "standard_pattern": 0,
            "special_month_pattern": 1,
        }
    )


def test_evaluate_pattern_candidates_yangren_yin_stem():
    chart = make_chart(
        day_stem="乙",
        month_branch="辰",
        month_hidden_stems=[
            "乙",
        ],
        month_main_hidden_stem="乙",
        month_main_hidden_stem_ten_god="劫財",
    )

    result = (
        evaluate_pattern_candidates(
            chart,
            "乙",
        )
    )

    assert (
        result["candidate_count"]
        == 1
    )

    assert (
        result["primary_candidate"][
            "pattern"
        ]
        == "羊刃格"
    )

    assert (
        result[
            "has_school_rule_candidate"
        ]
        is True
    )

    assert (
        result["overall_status"]
        == "candidate_with_school_rule"
    )


def test_evaluate_pattern_candidates_no_candidate():
    chart = make_chart(
        day_stem="乙",
        month_branch="未",
        month_main_hidden_stem="乙",
        month_main_hidden_stem_ten_god="比肩",
    )

    result = (
        evaluate_pattern_candidates(
            chart,
            "乙",
        )
    )

    assert (
        result["has_candidate"]
        is False
    )

    assert (
        result["candidate_count"]
        == 0
    )

    assert (
        result["primary_candidate"]
        is None
    )

    assert (
        result["candidates"]
        == []
    )

    assert (
        result["overall_status"]
        == "no_candidate"
    )


def test_evaluate_pattern_candidates_month_context():
    chart = make_chart(
        day_stem="乙",
        month_branch="未",
        month_stem="癸",
        month_hidden_stems=[
            "己",
            "丁",
            "乙",
        ],
        month_main_hidden_stem="己",
        month_main_hidden_stem_ten_god="偏財",
    )

    result = (
        evaluate_pattern_candidates(
            chart,
            "乙",
        )
    )

    assert (
        result["month_context"]
        == {
            "month_stem": "癸",
            "month_branch": "未",
            "hidden_stems": [
                "己",
                "丁",
                "乙",
            ],
            "main_hidden_stem": "己",
            "main_hidden_stem_ten_god": "偏財",
        }
    )

    assert (
        result["day_master_stem"]
        == "乙"
    )


def test_evaluate_pattern_candidates_notes():
    result = (
        evaluate_pattern_candidates(
            make_chart(),
            "乙",
        )
    )

    assert isinstance(
        result["notes"],
        list,
    )

    assert (
        len(
            result["notes"]
        )
        >= 1
    )


# =========================================================
# verified real chart style case
# 1985-07-17 21:50 石川県
# 乙丑 / 癸未 / 乙巳 / 丁亥
# =========================================================


def test_verified_1985_pattern_candidate():
    chart = {
        "year": make_pillar(
            pillar="乙丑",
            stem="乙",
            branch="丑",
            stem_ten_god="比肩",
            hidden_stems=[
                "己",
                "癸",
                "辛",
            ],
            main_hidden_stem="己",
            main_hidden_stem_ten_god="偏財",
        ),
        "month": make_pillar(
            pillar="癸未",
            stem="癸",
            branch="未",
            stem_ten_god="偏印",
            hidden_stems=[
                "己",
                "丁",
                "乙",
            ],
            main_hidden_stem="己",
            main_hidden_stem_ten_god="偏財",
        ),
        "day": make_pillar(
            pillar="乙巳",
            stem="乙",
            branch="巳",
            stem_ten_god=None,
            hidden_stems=[
                "丙",
                "戊",
                "庚",
            ],
            main_hidden_stem="丙",
            main_hidden_stem_ten_god="傷官",
        ),
        "hour": make_pillar(
            pillar="丁亥",
            stem="丁",
            branch="亥",
            stem_ten_god="食神",
            hidden_stems=[
                "壬",
                "甲",
            ],
            main_hidden_stem="壬",
            main_hidden_stem_ten_god="印綬",
        ),
    }

    result = (
        evaluate_pattern_candidates(
            chart,
            "乙",
        )
    )

    assert (
        result["has_candidate"]
        is True
    )

    assert (
        result["candidate_count"]
        == 1
    )

    assert (
        result["primary_candidate"][
            "pattern"
        ]
        == "偏財格"
    )

    assert (
        result["primary_candidate"][
            "technical_pattern"
        ]
        == "indirect_wealth"
    )

    assert (
        result["primary_candidate"][
            "month_branch"
        ]
        == "未"
    )

    assert (
        result["primary_candidate"][
            "month_main_hidden_stem"
        ]
        == "己"
    )

    assert (
        result["primary_candidate"][
            "ten_god"
        ]
        == "偏財"
    )

    assert (
        result["primary_candidate"][
            "is_exposed"
        ]
        is False
    )

    assert (
        result["primary_candidate"][
            "confidence"
        ]
        == "medium"
    )
