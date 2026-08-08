from engine.branch_relations import (
    find_branch_clashes,
    find_branch_combinations,
    is_branch_clash,
    is_branch_combination,
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
