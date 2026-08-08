from engine.stem_combinations import (
    find_stem_combinations,
    get_stem_combination_info,
    is_stem_combination,
)


def test_stem_combination_pairs():
    assert is_stem_combination(
        "甲",
        "己",
    ) is True

    assert is_stem_combination(
        "己",
        "甲",
    ) is True

    assert is_stem_combination(
        "乙",
        "庚",
    ) is True

    assert is_stem_combination(
        "丙",
        "辛",
    ) is True

    assert is_stem_combination(
        "丁",
        "壬",
    ) is True

    assert is_stem_combination(
        "戊",
        "癸",
    ) is True


def test_non_stem_combination_pair():
    assert is_stem_combination(
        "甲",
        "乙",
    ) is False

    assert is_stem_combination(
        "丙",
        "丁",
    ) is False


def test_get_ko_ki_combination_info():
    info = get_stem_combination_info(
        "甲",
        "己",
    )

    assert info == {
        "name": "甲己",
        "element": "土",
    }


def test_get_otsu_kou_combination_info():
    info = get_stem_combination_info(
        "乙",
        "庚",
    )

    assert info == {
        "name": "乙庚",
        "element": "金",
    }


def test_get_hei_shin_combination_info():
    info = get_stem_combination_info(
        "丙",
        "辛",
    )

    assert info == {
        "name": "丙辛",
        "element": "水",
    }


def test_get_tei_jin_combination_info():
    info = get_stem_combination_info(
        "丁",
        "壬",
    )

    assert info == {
        "name": "丁壬",
        "element": "木",
    }


def test_get_bo_ki_combination_info():
    info = get_stem_combination_info(
        "戊",
        "癸",
    )

    assert info == {
        "name": "戊癸",
        "element": "火",
    }


def test_get_non_combination_info():
    info = get_stem_combination_info(
        "甲",
        "乙",
    )

    assert info is None


def test_find_single_stem_combination():
    chart_data = {
        "year": {
            "stem": "甲",
        },
        "month": {
            "stem": "己",
        },
        "day": {
            "stem": "乙",
        },
        "hour": {
            "stem": "丙",
        },
    }

    result = find_stem_combinations(
        chart_data
    )

    assert (
        result["has_combination"]
        is True
    )

    assert (
        result["combination_count"]
        == 1
    )

    assert result["combinations"] == [
        {
            "position_a": "year",
            "stem_a": "甲",
            "position_b": "month",
            "stem_b": "己",
            "relation": "干合",
            "combination_name": "甲己",
            "result_element": "土",
            "transformation_status": (
                "not_evaluated"
            ),
        },
    ]

    assert (
        result["method"]
        == "stem_combination_v1"
    )

    assert (
        result["status"]
        == "detected_stem_combinations"
    )


def test_find_multiple_stem_combinations():
    chart_data = {
        "year": {
            "stem": "甲",
        },
        "month": {
            "stem": "己",
        },
        "day": {
            "stem": "丁",
        },
        "hour": {
            "stem": "壬",
        },
    }

    result = find_stem_combinations(
        chart_data
    )

    assert (
        result["has_combination"]
        is True
    )

    assert (
        result["combination_count"]
        == 2
    )

    assert result["combinations"] == [
        {
            "position_a": "year",
            "stem_a": "甲",
            "position_b": "month",
            "stem_b": "己",
            "relation": "干合",
            "combination_name": "甲己",
            "result_element": "土",
            "transformation_status": (
                "not_evaluated"
            ),
        },
        {
            "position_a": "day",
            "stem_a": "丁",
            "position_b": "hour",
            "stem_b": "壬",
            "relation": "干合",
            "combination_name": "丁壬",
            "result_element": "木",
            "transformation_status": (
                "not_evaluated"
            ),
        },
    ]


def test_chart_without_stem_combination():
    chart_data = {
        "year": {
            "stem": "甲",
        },
        "month": {
            "stem": "乙",
        },
        "day": {
            "stem": "丙",
        },
        "hour": {
            "stem": "丁",
        },
    }

    result = find_stem_combinations(
        chart_data
    )

    assert (
        result["has_combination"]
        is False
    )

    assert (
        result["combination_count"]
        == 0
    )

    assert (
        result["combinations"]
        == []
    )


def test_without_birth_time():
    chart_data = {
        "year": {
            "stem": "乙",
        },
        "month": {
            "stem": "庚",
        },
        "day": {
            "stem": "丙",
        },
        "hour": None,
    }

    result = find_stem_combinations(
        chart_data
    )

    assert (
        result["has_combination"]
        is True
    )

    assert (
        result["combination_count"]
        == 1
    )

    assert result["combinations"] == [
        {
            "position_a": "year",
            "stem_a": "乙",
            "position_b": "month",
            "stem_b": "庚",
            "relation": "干合",
            "combination_name": "乙庚",
            "result_element": "金",
            "transformation_status": (
                "not_evaluated"
            ),
        },
    ]


def test_combination_order_does_not_matter():
    chart_data = {
        "year": {
            "stem": "己",
        },
        "month": {
            "stem": "甲",
        },
        "day": {
            "stem": "丙",
        },
        "hour": {
            "stem": "丁",
        },
    }

    result = find_stem_combinations(
        chart_data
    )

    assert (
        result["has_combination"]
        is True
    )

    assert (
        result["combination_count"]
        == 1
    )

    assert (
        result["combinations"][0][
            "combination_name"
        ]
        == "甲己"
    )

    assert (
        result["combinations"][0][
            "result_element"
        ]
        == "土"
    )


def test_all_five_stem_combinations_individually():
    test_cases = [
        (
            "甲",
            "己",
            "甲己",
            "土",
        ),
        (
            "乙",
            "庚",
            "乙庚",
            "金",
        ),
        (
            "丙",
            "辛",
            "丙辛",
            "水",
        ),
        (
            "丁",
            "壬",
            "丁壬",
            "木",
        ),
        (
            "戊",
            "癸",
            "戊癸",
            "火",
        ),
    ]

    for (
        stem_a,
        stem_b,
        expected_name,
        expected_element,
    ) in test_cases:
        chart_data = {
            "year": {
                "stem": stem_a,
            },
            "month": {
                "stem": stem_b,
            },
            "day": {
                "stem": "甲",
            },
            "hour": None,
        }

        result = find_stem_combinations(
            chart_data
        )

        matching = [
            item
            for item in result[
                "combinations"
            ]
            if (
                item[
                    "combination_name"
                ]
                == expected_name
            )
        ]

        assert len(
            matching
        ) >= 1

        assert (
            matching[0][
                "result_element"
            ]
            == expected_element
        )


def test_result_contains_notes():
    chart_data = {
        "year": {
            "stem": "甲",
        },
        "month": {
            "stem": "己",
        },
        "day": {
            "stem": "乙",
        },
        "hour": None,
    }

    result = find_stem_combinations(
        chart_data
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
