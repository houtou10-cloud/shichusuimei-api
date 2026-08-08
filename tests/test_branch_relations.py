from engine.branch_relations import (
    find_branch_clashes,
    find_branch_combinations,
    find_branch_punishments,
    find_branch_trines,
    get_branch_trine_info,
    is_branch_clash,
    is_branch_combination,
    is_branch_trine,
)


def test_branch_clash_pairs():
    assert is_branch_clash(
        "子",
        "午",
    ) is True

    assert is_branch_clash(
        "午",
        "子",
    ) is True

    assert is_branch_clash(
        "丑",
        "未",
    ) is True

    assert is_branch_clash(
        "寅",
        "申",
    ) is True

    assert is_branch_clash(
        "卯",
        "酉",
    ) is True

    assert is_branch_clash(
        "辰",
        "戌",
    ) is True

    assert is_branch_clash(
        "巳",
        "亥",
    ) is True


def test_non_clash_pair():
    assert is_branch_clash(
        "子",
        "丑",
    ) is False


def test_branch_combination_pairs():
    assert is_branch_combination(
        "子",
        "丑",
    ) is True

    assert is_branch_combination(
        "丑",
        "子",
    ) is True

    assert is_branch_combination(
        "寅",
        "亥",
    ) is True

    assert is_branch_combination(
        "卯",
        "戌",
    ) is True

    assert is_branch_combination(
        "辰",
        "酉",
    ) is True

    assert is_branch_combination(
        "巳",
        "申",
    ) is True

    assert is_branch_combination(
        "午",
        "未",
    ) is True


def test_non_combination_pair():
    assert is_branch_combination(
        "子",
        "午",
    ) is False


def test_branch_trine_water():
    assert is_branch_trine(
        "申",
        "子",
        "辰",
    ) is True

    info = get_branch_trine_info(
        "申",
        "子",
        "辰",
    )

    assert info == {
        "name": "申子辰",
        "element": "水",
    }


def test_branch_trine_wood():
    assert is_branch_trine(
        "亥",
        "卯",
        "未",
    ) is True

    info = get_branch_trine_info(
        "亥",
        "卯",
        "未",
    )

    assert info == {
        "name": "亥卯未",
        "element": "木",
    }


def test_branch_trine_fire():
    assert is_branch_trine(
        "寅",
        "午",
        "戌",
    ) is True

    info = get_branch_trine_info(
        "寅",
        "午",
        "戌",
    )

    assert info == {
        "name": "寅午戌",
        "element": "火",
    }


def test_branch_trine_metal():
    assert is_branch_trine(
        "巳",
        "酉",
        "丑",
    ) is True

    info = get_branch_trine_info(
        "巳",
        "酉",
        "丑",
    )

    assert info == {
        "name": "巳酉丑",
        "element": "金",
    }


def test_branch_trine_order_does_not_matter():
    assert is_branch_trine(
        "辰",
        "申",
        "子",
    ) is True

    assert is_branch_trine(
        "未",
        "亥",
        "卯",
    ) is True

    assert is_branch_trine(
        "戌",
        "午",
        "寅",
    ) is True

    assert is_branch_trine(
        "丑",
        "巳",
        "酉",
    ) is True


def test_non_trine_group():
    assert is_branch_trine(
        "子",
        "丑",
        "寅",
    ) is False

    assert (
        get_branch_trine_info(
            "子",
            "丑",
            "寅",
        )
        is None
    )


def test_find_branch_clashes():
    chart_data = {
        "year": {
            "branch": "丑",
        },
        "month": {
            "branch": "未",
        },
        "day": {
            "branch": "巳",
        },
        "hour": {
            "branch": "亥",
        },
    }

    result = find_branch_clashes(
        chart_data
    )

    assert result["has_clash"] is True
    assert result["clash_count"] == 2

    assert result["clashes"] == [
        {
            "position_a": "year",
            "branch_a": "丑",
            "position_b": "month",
            "branch_b": "未",
            "relation": "冲",
        },
        {
            "position_a": "day",
            "branch_a": "巳",
            "position_b": "hour",
            "branch_b": "亥",
            "relation": "冲",
        },
    ]

    assert (
        result["method"]
        == "branch_clash_v1"
    )

    assert (
        result["status"]
        == "detected_branch_clashes"
    )


def test_find_branch_combinations():
    chart_data = {
        "year": {
            "branch": "子",
        },
        "month": {
            "branch": "丑",
        },
        "day": {
            "branch": "午",
        },
        "hour": {
            "branch": "未",
        },
    }

    result = find_branch_combinations(
        chart_data
    )

    assert result["has_combination"] is True
    assert result["combination_count"] == 2

    assert result["combinations"] == [
        {
            "position_a": "year",
            "branch_a": "子",
            "position_b": "month",
            "branch_b": "丑",
            "relation": "六合",
        },
        {
            "position_a": "day",
            "branch_a": "午",
            "position_b": "hour",
            "branch_b": "未",
            "relation": "六合",
        },
    ]

    assert (
        result["method"]
        == "branch_combination_v1"
    )

    assert (
        result["status"]
        == "detected_branch_combinations"
    )


def test_find_branch_trines():
    chart_data = {
        "year": {
            "branch": "申",
        },
        "month": {
            "branch": "子",
        },
        "day": {
            "branch": "辰",
        },
        "hour": {
            "branch": "午",
        },
    }

    result = find_branch_trines(
        chart_data
    )

    assert result["has_trine"] is True
    assert result["trine_count"] == 1

    assert result["trines"] == [
        {
            "position_a": "year",
            "branch_a": "申",
            "position_b": "month",
            "branch_b": "子",
            "position_c": "day",
            "branch_c": "辰",
            "relation": "三合",
            "trine_name": "申子辰",
            "element": "水",
        },
    ]

    assert (
        result["method"]
        == "branch_trine_v1"
    )

    assert (
        result["status"]
        == "detected_branch_trines"
    )


def test_find_wood_branch_trine():
    chart_data = {
        "year": {
            "branch": "亥",
        },
        "month": {
            "branch": "卯",
        },
        "day": {
            "branch": "未",
        },
        "hour": {
            "branch": "子",
        },
    }

    result = find_branch_trines(
        chart_data
    )

    assert result["has_trine"] is True
    assert result["trine_count"] == 1

    assert result["trines"][0] == {
        "position_a": "year",
        "branch_a": "亥",
        "position_b": "month",
        "branch_b": "卯",
        "position_c": "day",
        "branch_c": "未",
        "relation": "三合",
        "trine_name": "亥卯未",
        "element": "木",
    }


def test_chart_without_branch_clash():
    chart_data = {
        "year": {
            "branch": "子",
        },
        "month": {
            "branch": "丑",
        },
        "day": {
            "branch": "寅",
        },
        "hour": {
            "branch": "卯",
        },
    }

    result = find_branch_clashes(
        chart_data
    )

    assert result["has_clash"] is False
    assert result["clash_count"] == 0
    assert result["clashes"] == []


def test_chart_without_branch_combination():
    chart_data = {
        "year": {
            "branch": "子",
        },
        "month": {
            "branch": "午",
        },
        "day": {
            "branch": "寅",
        },
        "hour": {
            "branch": "申",
        },
    }

    result = find_branch_combinations(
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

    assert result["combinations"] == []


def test_chart_without_branch_trine():
    chart_data = {
        "year": {
            "branch": "子",
        },
        "month": {
            "branch": "丑",
        },
        "day": {
            "branch": "寅",
        },
        "hour": {
            "branch": "卯",
        },
    }

    result = find_branch_trines(
        chart_data
    )

    assert result["has_trine"] is False
    assert result["trine_count"] == 0
    assert result["trines"] == []


def test_without_birth_time_for_clash():
    chart_data = {
        "year": {
            "branch": "子",
        },
        "month": {
            "branch": "午",
        },
        "day": {
            "branch": "寅",
        },
        "hour": None,
    }

    result = find_branch_clashes(
        chart_data
    )

    assert result["has_clash"] is True
    assert result["clash_count"] == 1

    assert result["clashes"] == [
        {
            "position_a": "year",
            "branch_a": "子",
            "position_b": "month",
            "branch_b": "午",
            "relation": "冲",
        },
    ]


def test_without_birth_time_for_combination():
    chart_data = {
        "year": {
            "branch": "子",
        },
        "month": {
            "branch": "丑",
        },
        "day": {
            "branch": "寅",
        },
        "hour": None,
    }

    result = find_branch_combinations(
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
            "branch_a": "子",
            "position_b": "month",
            "branch_b": "丑",
            "relation": "六合",
        },
    ]


def test_without_birth_time_for_trine():
    chart_data = {
        "year": {
            "branch": "申",
        },
        "month": {
            "branch": "子",
        },
        "day": {
            "branch": "辰",
        },
        "hour": None,
    }

    result = find_branch_trines(
        chart_data
    )

    assert result["has_trine"] is True
    assert result["trine_count"] == 1

    assert result["trines"] == [
        {
            "position_a": "year",
            "branch_a": "申",
            "position_b": "month",
            "branch_b": "子",
            "position_c": "day",
            "branch_c": "辰",
            "relation": "三合",
            "trine_name": "申子辰",
            "element": "水",
        },
    ]


def test_tiger_snake_monkey_triple_punishment():
    chart_data = {
        "year": {
            "branch": "寅",
        },
        "month": {
            "branch": "巳",
        },
        "day": {
            "branch": "申",
        },
        "hour": {
            "branch": "子",
        },
    }

    result = find_branch_punishments(
        chart_data
    )

    assert (
        result["has_punishment"]
        is True
    )

    assert (
        result["punishment_count"]
        == 1
    )

    assert result["punishments"] == [
        {
            "positions": [
                "year",
                "month",
                "day",
            ],
            "branches": [
                "寅",
                "巳",
                "申",
            ],
            "relation": "刑",
            "punishment_type": "三刑",
            "punishment_name": "寅巳申",
        },
    ]


def test_ox_dog_goat_triple_punishment():
    chart_data = {
        "year": {
            "branch": "丑",
        },
        "month": {
            "branch": "戌",
        },
        "day": {
            "branch": "未",
        },
        "hour": {
            "branch": "子",
        },
    }

    result = find_branch_punishments(
        chart_data
    )

    assert (
        result["has_punishment"]
        is True
    )

    assert (
        result["punishment_count"]
        == 1
    )

    assert result["punishments"] == [
        {
            "positions": [
                "year",
                "month",
                "day",
            ],
            "branches": [
                "丑",
                "戌",
                "未",
            ],
            "relation": "刑",
            "punishment_type": "三刑",
            "punishment_name": "丑戌未",
        },
    ]


def test_rat_rabbit_mutual_punishment():
    chart_data = {
        "year": {
            "branch": "子",
        },
        "month": {
            "branch": "卯",
        },
        "day": {
            "branch": "寅",
        },
        "hour": {
            "branch": "巳",
        },
    }

    result = find_branch_punishments(
        chart_data
    )

    assert (
        result["has_punishment"]
        is True
    )

    assert (
        result["punishment_count"]
        == 1
    )

    assert result["punishments"] == [
        {
            "positions": [
                "year",
                "month",
            ],
            "branches": [
                "子",
                "卯",
            ],
            "relation": "刑",
            "punishment_type": "相刑",
            "punishment_name": "子卯",
        },
    ]


def test_dragon_self_punishment():
    chart_data = {
        "year": {
            "branch": "辰",
        },
        "month": {
            "branch": "辰",
        },
        "day": {
            "branch": "寅",
        },
        "hour": {
            "branch": "巳",
        },
    }

    result = find_branch_punishments(
        chart_data
    )

    assert (
        result["has_punishment"]
        is True
    )

    assert (
        result["punishment_count"]
        == 1
    )

    assert result["punishments"] == [
        {
            "positions": [
                "year",
                "month",
            ],
            "branches": [
                "辰",
                "辰",
            ],
            "relation": "刑",
            "punishment_type": "自刑",
            "punishment_name": "辰辰",
        },
    ]


def test_horse_self_punishment():
    chart_data = {
        "year": {
            "branch": "午",
        },
        "month": {
            "branch": "午",
        },
        "day": {
            "branch": "寅",
        },
        "hour": {
            "branch": "巳",
        },
    }

    result = find_branch_punishments(
        chart_data
    )

    assert (
        result["has_punishment"]
        is True
    )

    assert (
        result["punishment_count"]
        == 1
    )

    assert (
        result["punishments"][0][
            "punishment_type"
        ]
        == "自刑"
    )

    assert (
        result["punishments"][0][
            "punishment_name"
        ]
        == "午午"
    )


def test_rooster_self_punishment():
    chart_data = {
        "year": {
            "branch": "酉",
        },
        "month": {
            "branch": "酉",
        },
        "day": {
            "branch": "寅",
        },
        "hour": {
            "branch": "巳",
        },
    }

    result = find_branch_punishments(
        chart_data
    )

    assert (
        result["has_punishment"]
        is True
    )

    assert (
        result["punishment_count"]
        == 1
    )

    assert (
        result["punishments"][0][
            "punishment_name"
        ]
        == "酉酉"
    )


def test_boar_self_punishment():
    chart_data = {
        "year": {
            "branch": "亥",
        },
        "month": {
            "branch": "亥",
        },
        "day": {
            "branch": "寅",
        },
        "hour": {
            "branch": "午",
        },
    }

    result = find_branch_punishments(
        chart_data
    )

    assert (
        result["has_punishment"]
        is True
    )

    assert (
        result["punishment_count"]
        == 1
    )

    assert (
        result["punishments"][0][
            "punishment_name"
        ]
        == "亥亥"
    )


def test_chart_without_branch_punishment():
    chart_data = {
        "year": {
            "branch": "子",
        },
        "month": {
            "branch": "丑",
        },
        "day": {
            "branch": "辰",
        },
        "hour": {
            "branch": "未",
        },
    }

    result = find_branch_punishments(
        chart_data
    )

    assert (
        result["has_punishment"]
        is False
    )

    assert (
        result["punishment_count"]
        == 0
    )

    assert result["punishments"] == []

    assert (
        result["method"]
        == "branch_punishment_v1"
    )

    assert (
        result["status"]
        == "detected_branch_punishments"
    )


def test_partial_triple_punishment_is_not_detected():
    chart_data = {
        "year": {
            "branch": "寅",
        },
        "month": {
            "branch": "巳",
        },
        "day": {
            "branch": "子",
        },
        "hour": {
            "branch": "丑",
        },
    }

    result = find_branch_punishments(
        chart_data
    )

    assert (
        result["has_punishment"]
        is False
    )

    assert (
        result["punishment_count"]
        == 0
    )


def test_without_birth_time_for_punishment():
    chart_data = {
        "year": {
            "branch": "子",
        },
        "month": {
            "branch": "卯",
        },
        "day": {
            "branch": "寅",
        },
        "hour": None,
    }

    result = find_branch_punishments(
        chart_data
    )

    assert (
        result["has_punishment"]
        is True
    )

    assert (
        result["punishment_count"]
        == 1
    )

    assert result["punishments"] == [
        {
            "positions": [
                "year",
                "month",
            ],
            "branches": [
                "子",
                "卯",
            ],
            "relation": "刑",
            "punishment_type": "相刑",
            "punishment_name": "子卯",
        },
    ]
