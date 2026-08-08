import pytest

from engine.stem_combination_conflict_types import (
    classify_duplicate_combination,
    classify_position_conflict,
    count_severity,
    determine_overall_severity,
    evaluate_stem_combination_conflict_types,
    normalize_combination_names,
    validate_conflict_data,
)


def make_position_conflict(
    position="year",
    stem="甲",
    combination_count=2,
    combination_names=None,
    partner_positions=None,
):
    if combination_names is None:
        combination_names = [
            "甲己",
            "甲己",
        ]

    if partner_positions is None:
        partner_positions = [
            "month",
            "day",
        ]

    return {
        "position": position,
        "stem": stem,
        "combination_count": (
            combination_count
        ),
        "combination_names": (
            combination_names
        ),
        "partner_positions": (
            partner_positions
        ),
        "conflict_type": (
            "competing_combination"
        ),
    }


def make_duplicate_conflict(
    combination_name="甲己",
    combination_count=2,
):
    return {
        "combination_name": (
            combination_name
        ),
        "combination_count": (
            combination_count
        ),
        "pairs": [
            {
                "position_a": "year",
                "stem_a": "甲",
                "position_b": "month",
                "stem_b": "己",
            },
            {
                "position_a": "year",
                "stem_a": "甲",
                "position_b": "day",
                "stem_b": "己",
            },
        ],
        "conflict_type": (
            "duplicated_combination"
        ),
    }


def make_conflict_data(
    position_conflicts=None,
    duplicate_combinations=None,
):
    if position_conflicts is None:
        position_conflicts = []

    if duplicate_combinations is None:
        duplicate_combinations = []

    return {
        "has_stem_combination": (
            bool(
                position_conflicts
                or duplicate_combinations
            )
        ),
        "combination_count": 0,
        "has_conflict": (
            bool(
                position_conflicts
                or duplicate_combinations
            )
        ),
        "conflict_count": (
            len(position_conflicts)
            + len(
                duplicate_combinations
            )
        ),
        "position_conflict_count": (
            len(position_conflicts)
        ),
        "duplicate_combination_count": (
            len(
                duplicate_combinations
            )
        ),
        "position_conflicts": (
            position_conflicts
        ),
        "duplicate_combinations": (
            duplicate_combinations
        ),
        "overall_status": (
            "conflicted"
            if (
                position_conflicts
                or duplicate_combinations
            )
            else "not_applicable"
        ),
    }


# =========================================================
# validate_conflict_data
# =========================================================


def test_validate_conflict_data():
    data = make_conflict_data()

    validate_conflict_data(
        data
    )


def test_validate_conflict_data_invalid_type():
    with pytest.raises(
        TypeError,
        match=(
            "stem_combination_conflictsは"
            "dict型"
        ),
    ):
        validate_conflict_data(
            []
        )


def test_validate_position_conflicts_type():
    with pytest.raises(
        TypeError,
        match=(
            "position_conflictsは"
            "list型"
        ),
    ):
        validate_conflict_data(
            {
                "position_conflicts": {},
                "duplicate_combinations": [],
            }
        )


def test_validate_duplicate_combinations_type():
    with pytest.raises(
        TypeError,
        match=(
            "duplicate_combinationsは"
            "list型"
        ),
    ):
        validate_conflict_data(
            {
                "position_conflicts": [],
                "duplicate_combinations": {},
            }
        )


# =========================================================
# normalize_combination_names
# =========================================================


def test_normalize_combination_names():
    result = normalize_combination_names(
        [
            "甲己",
            None,
            "甲己",
        ]
    )

    assert result == [
        "甲己",
        "甲己",
    ]


def test_normalize_combination_names_invalid_type():
    with pytest.raises(
        TypeError,
        match=(
            "combination_namesは"
            "list型"
        ),
    ):
        normalize_combination_names(
            "甲己"
        )


def test_normalize_combination_name_invalid_item():
    with pytest.raises(
        TypeError,
        match=(
            "combination_nameは"
            "str型"
        ),
    ):
        normalize_combination_names(
            [
                "甲己",
                123,
            ]
        )


# =========================================================
# classify_position_conflict
# =========================================================


def test_classify_position_conflict_as_competing_same():
    conflict = (
        make_position_conflict(
            combination_names=[
                "甲己",
                "甲己",
            ]
        )
    )

    result = (
        classify_position_conflict(
            conflict
        )
    )

    assert (
        result["source_type"]
        == "position_conflict"
    )

    assert (
        result["position"]
        == "year"
    )

    assert (
        result["stem"]
        == "甲"
    )

    assert (
        result[
            "combination_count"
        ]
        == 2
    )

    assert (
        result[
            "combination_names"
        ]
        == [
            "甲己",
            "甲己",
        ]
    )

    assert (
        result[
            "partner_positions"
        ]
        == [
            "month",
            "day",
        ]
    )

    assert (
        result["conflict_type"]
        == "争合候補"
    )

    assert (
        result["technical_type"]
        == "competing_same_combination"
    )

    assert (
        result["severity"]
        == "medium"
    )

    assert (
        result["is_provisional"]
        is True
    )


def test_classify_position_conflict_as_multiple():
    conflict = (
        make_position_conflict(
            combination_names=[
                "甲己",
                "乙庚",
            ]
        )
    )

    result = (
        classify_position_conflict(
            conflict
        )
    )

    assert (
        result["conflict_type"]
        == "複合競合"
    )

    assert (
        result["technical_type"]
        == "competing_multiple_combinations"
    )

    assert (
        result["severity"]
        == "high"
    )


def test_classify_position_conflict_as_unclassified():
    conflict = (
        make_position_conflict(
            combination_count=1,
            combination_names=[
                "甲己",
            ],
            partner_positions=[
                "month",
            ],
        )
    )

    result = (
        classify_position_conflict(
            conflict
        )
    )

    assert (
        result["conflict_type"]
        == "未分類競合"
    )

    assert (
        result["technical_type"]
        == "unclassified_position_conflict"
    )

    assert (
        result["severity"]
        == "low"
    )


def test_classify_position_conflict_invalid_type():
    with pytest.raises(
        TypeError,
        match="conflictはdict型",
    ):
        classify_position_conflict(
            []
        )


def test_classify_position_conflict_invalid_position():
    conflict = (
        make_position_conflict(
            position="invalid"
        )
    )

    with pytest.raises(
        ValueError,
        match="不正なpositionです",
    ):
        classify_position_conflict(
            conflict
        )


def test_classify_position_conflict_invalid_partner_positions():
    conflict = (
        make_position_conflict()
    )

    conflict[
        "partner_positions"
    ] = {}

    with pytest.raises(
        TypeError,
        match=(
            "partner_positionsは"
            "list型"
        ),
    ):
        classify_position_conflict(
            conflict
        )


# =========================================================
# classify_duplicate_combination
# =========================================================


def test_classify_duplicate_combination():
    conflict = (
        make_duplicate_conflict()
    )

    result = (
        classify_duplicate_combination(
            conflict
        )
    )

    assert (
        result["source_type"]
        == "duplicate_combination"
    )

    assert (
        result["combination_name"]
        == "甲己"
    )

    assert (
        result[
            "combination_count"
        ]
        == 2
    )

    assert (
        result["conflict_type"]
        == "重複干合候補"
    )

    assert (
        result["technical_type"]
        == "duplicated_combination"
    )

    assert (
        result["severity"]
        == "low"
    )

    assert (
        result["is_provisional"]
        is True
    )

    assert (
        len(
            result["pairs"]
        )
        == 2
    )


def test_classify_duplicate_combination_invalid_type():
    with pytest.raises(
        TypeError,
        match="conflictはdict型",
    ):
        classify_duplicate_combination(
            []
        )


def test_classify_duplicate_combination_invalid_pairs():
    conflict = (
        make_duplicate_conflict()
    )

    conflict["pairs"] = {}

    with pytest.raises(
        TypeError,
        match="pairsはlist型",
    ):
        classify_duplicate_combination(
            conflict
        )


# =========================================================
# severity
# =========================================================


def test_count_severity():
    conflicts = [
        {
            "severity": "high",
        },
        {
            "severity": "medium",
        },
        {
            "severity": "medium",
        },
        {
            "severity": "low",
        },
    ]

    result = count_severity(
        conflicts
    )

    assert result == {
        "high": 1,
        "medium": 2,
        "low": 1,
    }


def test_count_severity_ignores_unknown():
    conflicts = [
        {
            "severity": "unknown",
        },
    ]

    result = count_severity(
        conflicts
    )

    assert result == {
        "high": 0,
        "medium": 0,
        "low": 0,
    }


def test_determine_overall_severity_high():
    result = (
        determine_overall_severity(
            {
                "high": 1,
                "medium": 2,
                "low": 3,
            }
        )
    )

    assert result == "high"


def test_determine_overall_severity_medium():
    result = (
        determine_overall_severity(
            {
                "high": 0,
                "medium": 1,
                "low": 3,
            }
        )
    )

    assert result == "medium"


def test_determine_overall_severity_low():
    result = (
        determine_overall_severity(
            {
                "high": 0,
                "medium": 0,
                "low": 1,
            }
        )
    )

    assert result == "low"


def test_determine_overall_severity_none():
    result = (
        determine_overall_severity(
            {
                "high": 0,
                "medium": 0,
                "low": 0,
            }
        )
    )

    assert result == "none"


# =========================================================
# evaluate
# =========================================================


def test_evaluate_no_conflicts():
    result = (
        evaluate_stem_combination_conflict_types(
            make_conflict_data()
        )
    )

    assert (
        result[
            "has_typed_conflict"
        ]
        is False
    )

    assert (
        result[
            "typed_conflict_count"
        ]
        == 0
    )

    assert (
        result[
            "position_conflict_count"
        ]
        == 0
    )

    assert (
        result[
            "duplicate_conflict_count"
        ]
        == 0
    )

    assert (
        result[
            "争合_candidate_count"
        ]
        == 0
    )

    assert (
        result[
            "multiple_conflict_count"
        ]
        == 0
    )

    assert (
        result[
            "unclassified_count"
        ]
        == 0
    )

    assert (
        result["severity_counts"]
        == {
            "high": 0,
            "medium": 0,
            "low": 0,
        }
    )

    assert (
        result["overall_severity"]
        == "none"
    )

    assert (
        result["conflicts"]
        == []
    )

    assert (
        result["overall_status"]
        == "not_applicable"
    )

    assert (
        result["method"]
        == "stem_combination_conflict_types_v1"
    )

    assert (
        result["status"]
        == "provisional_conflict_typing"
    )


def test_evaluate_competing_same_combination():
    data = make_conflict_data(
        position_conflicts=[
            make_position_conflict(
                combination_names=[
                    "甲己",
                    "甲己",
                ]
            ),
        ],
    )

    result = (
        evaluate_stem_combination_conflict_types(
            data
        )
    )

    assert (
        result[
            "has_typed_conflict"
        ]
        is True
    )

    assert (
        result[
            "typed_conflict_count"
        ]
        == 1
    )

    assert (
        result[
            "争合_candidate_count"
        ]
        == 1
    )

    assert (
        result[
            "multiple_conflict_count"
        ]
        == 0
    )

    assert (
        result["overall_severity"]
        == "medium"
    )

    assert (
        result["overall_status"]
        == "classified"
    )


def test_evaluate_multiple_combination_conflict():
    data = make_conflict_data(
        position_conflicts=[
            make_position_conflict(
                combination_names=[
                    "甲己",
                    "乙庚",
                ]
            ),
        ],
    )

    result = (
        evaluate_stem_combination_conflict_types(
            data
        )
    )

    assert (
        result[
            "multiple_conflict_count"
        ]
        == 1
    )

    assert (
        result[
            "争合_candidate_count"
        ]
        == 0
    )

    assert (
        result["overall_severity"]
        == "high"
    )


def test_evaluate_duplicate_combination():
    data = make_conflict_data(
        duplicate_combinations=[
            make_duplicate_conflict(),
        ],
    )

    result = (
        evaluate_stem_combination_conflict_types(
            data
        )
    )

    assert (
        result[
            "typed_conflict_count"
        ]
        == 1
    )

    assert (
        result[
            "duplicate_conflict_count"
        ]
        == 1
    )

    assert (
        result["overall_severity"]
        == "low"
    )

    assert (
        result[
            "duplicate_conflicts"
        ][0][
            "conflict_type"
        ]
        == "重複干合候補"
    )


def test_evaluate_combined_conflicts():
    data = make_conflict_data(
        position_conflicts=[
            make_position_conflict(
                combination_names=[
                    "甲己",
                    "乙庚",
                ]
            ),
            make_position_conflict(
                position="month",
                stem="己",
                combination_names=[
                    "甲己",
                    "甲己",
                ],
            ),
        ],
        duplicate_combinations=[
            make_duplicate_conflict(),
        ],
    )

    result = (
        evaluate_stem_combination_conflict_types(
            data
        )
    )

    assert (
        result[
            "typed_conflict_count"
        ]
        == 3
    )

    assert (
        result[
            "position_conflict_count"
        ]
        == 2
    )

    assert (
        result[
            "duplicate_conflict_count"
        ]
        == 1
    )

    assert (
        result[
            "争合_candidate_count"
        ]
        == 1
    )

    assert (
        result[
            "multiple_conflict_count"
        ]
        == 1
    )

    assert (
        result["severity_counts"]
        == {
            "high": 1,
            "medium": 1,
            "low": 1,
        }
    )

    assert (
        result["overall_severity"]
        == "high"
    )

    assert (
        result["overall_status"]
        == "classified"
    )


def test_evaluate_unclassified_only():
    data = make_conflict_data(
        position_conflicts=[
            make_position_conflict(
                combination_count=1,
                combination_names=[
                    "甲己",
                ],
                partner_positions=[
                    "month",
                ],
            ),
        ],
    )

    result = (
        evaluate_stem_combination_conflict_types(
            data
        )
    )

    assert (
        result[
            "unclassified_count"
        ]
        == 1
    )

    assert (
        result["overall_severity"]
        == "low"
    )

    assert (
        result["overall_status"]
        == "partially_classified"
    )


def test_result_contains_notes():
    result = (
        evaluate_stem_combination_conflict_types(
            make_conflict_data()
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
