from engine.branch_relations import (
    find_branch_clashes,
    is_branch_clash,
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


def test_without_birth_time():
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
