"""
tests/test_useful_gods_v3_real_cases.py

useful_gods_v3 の代表ケース回帰テスト。

注意:
このファイルの「real_cases」は、
十干すべてを実運用に近い条件で通す
代表ケース・回帰ケースという意味です。
生年月日から命式を再計算する実命式テストは
tests/test_pattern_real_charts.py が担当します。
"""

import pytest

from engine.useful_gods import (
    ELEMENTS,
    STEM_TO_ELEMENT,
    evaluate_useful_gods_v3,
)


GENERATES = {
    "木": "火",
    "火": "土",
    "土": "金",
    "金": "水",
    "水": "木",
}

GENERATED_BY = {
    generated: generator
    for generator, generated
    in GENERATES.items()
}

CONTROLS = {
    "木": "土",
    "火": "金",
    "土": "水",
    "金": "木",
    "水": "火",
}

CONTROLLED_BY = {
    controlled: controller
    for controller, controlled
    in CONTROLS.items()
}


STEM_CASES = (
    ("甲", "木", "水", "火", "土", "金"),
    ("乙", "木", "水", "火", "土", "金"),
    ("丙", "火", "木", "土", "金", "水"),
    ("丁", "火", "木", "土", "金", "水"),
    ("戊", "土", "火", "金", "水", "木"),
    ("己", "土", "火", "金", "水", "木"),
    ("庚", "金", "土", "水", "木", "火"),
    ("辛", "金", "土", "水", "木", "火"),
    ("壬", "水", "金", "木", "火", "土"),
    ("癸", "水", "金", "木", "火", "土"),
)


def make_weighted():
    return {
        "scores": {
            "木": 20.0,
            "火": 20.0,
            "土": 20.0,
            "金": 20.0,
            "水": 20.0,
        },
        "method": "weighted_five_elements_v1",
    }


def make_strength(
    label="weak",
    confidence="high",
):
    if label in {
        "strong",
        "very_strong",
        "extremely_strong",
    }:
        score = 65.0
    elif label in {
        "weak",
        "very_weak",
        "extremely_weak",
    }:
        score = 35.0
    else:
        score = 50.0

    return {
        "technical_label": label,
        "final_score": score,
        "confidence": confidence,
        "method": "final_strength_judgment_v2",
    }


def make_pattern(
    confidence="high",
):
    return {
        "primary_pattern": "偏財格",
        "technical_pattern": "indirect_wealth",
        "overall_judgment": "provisional_possible",
        "confidence": confidence,
        "method": "pattern_judgment_v2",
        "status": "provisional_pattern_judgment_v2",
    }


def make_climate(
    stem,
    elements,
    confidence="high",
):
    elements = list(elements)
    primary = elements[0] if elements else None

    return {
        "has_climate_candidate": primary is not None,
        "primary_climate_element": primary,
        "secondary_climate_elements": elements[1:],
        "climate_elements": elements,
        "climate_candidates": [],
        "day_master_stem": stem,
        "day_master_element": STEM_TO_ELEMENT[stem],
        "month_branch": "未",
        "season": "summer",
        "season_japanese": "夏",
        "temperature_label": "hot",
        "moisture_label": "slightly_dry",
        "heat_score": 1.15,
        "moisture_score": -0.4,
        "climate_needs": ["cooling"] if elements else [],
        "climate_element_scores": {
            element: 0.0
            for element in ELEMENTS
        },
        "confidence": confidence,
        "reasoning": ["representative climate fixture"],
        "evidence": {
            "season_source": "month_branch",
        },
        "method": "climate_useful_gods_v1",
        "status": "provisional_climate_useful_gods",
        "notes": ["representative climate fixture"],
    }


def make_pattern_useful(
    stem,
    elements,
    confidence="high",
):
    elements = list(elements)
    primary = elements[0] if elements else None

    candidates = [
        {
            "element": element,
            "priority": priority,
            "integrated_score": float(
                len(elements) - priority + 1
            ),
        }
        for priority, element
        in enumerate(elements, start=1)
    ]

    return {
        "has_pattern_useful_candidate": primary is not None,
        "primary_pattern_element": primary,
        "secondary_pattern_elements": elements[1:],
        "pattern_elements": elements,
        "pattern_candidates": candidates,
        "day_master_stem": stem,
        "day_master_element": STEM_TO_ELEMENT[stem],
        "primary_pattern": "偏財格",
        "technical_pattern": "indirect_wealth",
        "pattern_overall_judgment": "provisional_possible",
        "pattern_confidence": confidence,
        "supported_pattern": True,
        "element_relations": {},
        "confidence": confidence,
        "reasoning": ["representative pattern fixture"],
        "evidence": {},
        "method": "pattern_useful_gods_v1",
        "status": "provisional_pattern_useful_gods",
        "notes": ["representative pattern fixture"],
    }


def evaluate_case(
    stem,
    strength_label,
    climate_elements,
    pattern_elements,
    confidence="high",
):
    return evaluate_useful_gods_v3(
        stem,
        make_weighted(),
        make_strength(
            label=strength_label,
            confidence=confidence,
        ),
        make_pattern(
            confidence=confidence,
        ),
        make_climate(
            stem,
            climate_elements,
            confidence=confidence,
        ),
        make_pattern_useful(
            stem,
            pattern_elements,
            confidence=confidence,
        ),
    )


@pytest.mark.parametrize(
    (
        "stem",
        "day_master_element",
        "resource",
        "output",
        "wealth",
        "officer",
    ),
    STEM_CASES,
)
def test_stem_case_relations_are_consistent(
    stem,
    day_master_element,
    resource,
    output,
    wealth,
    officer,
):
    assert STEM_TO_ELEMENT[stem] == day_master_element
    assert GENERATED_BY[day_master_element] == resource
    assert GENERATES[day_master_element] == output
    assert CONTROLS[day_master_element] == wealth
    assert CONTROLLED_BY[day_master_element] == officer


@pytest.mark.parametrize(
    (
        "stem",
        "day_master_element",
        "resource",
        "output",
        "wealth",
        "officer",
    ),
    STEM_CASES,
)
def test_ten_stems_triple_agreement(
    stem,
    day_master_element,
    resource,
    output,
    wealth,
    officer,
):
    result = evaluate_case(
        stem,
        "weak",
        [resource],
        [resource],
        "high",
    )

    agreement = result["agreement"]

    assert result["method"] == "useful_gods_v3"
    assert result["status"] == "provisional_useful_gods_v3"
    assert result["day_master_stem"] == stem
    assert result["day_master_element"] == day_master_element

    assert agreement["agreement_level"] == "triple_agreement"
    assert agreement["has_triple_agreement"] is True
    assert resource in agreement["triple_agreement_elements"]
    assert agreement["by_element"][resource]["source_count"] == 3
    assert agreement["by_element"][resource]["sources"] == [
        "support_balance",
        "climate",
        "pattern",
    ]

    assert result["primary_useful_element"] == resource
    assert result["final_useful_elements"][0] == resource
    assert result["confidence"] == "high"


@pytest.mark.parametrize(
    (
        "stem",
        "day_master_element",
        "resource",
        "output",
        "wealth",
        "officer",
    ),
    STEM_CASES,
)
def test_ten_stems_double_agreement(
    stem,
    day_master_element,
    resource,
    output,
    wealth,
    officer,
):
    result = evaluate_case(
        stem,
        "weak",
        [resource],
        [output],
        "medium",
    )

    agreement = result["agreement"]

    assert agreement["agreement_level"] == "double_agreement"
    assert agreement["has_triple_agreement"] is False
    assert agreement["has_double_agreement"] is True
    assert resource in agreement["double_agreement_elements"]
    assert agreement["by_element"][resource]["source_count"] == 2
    assert set(
        agreement["by_element"][resource]["sources"]
    ) == {
        "support_balance",
        "climate",
    }


@pytest.mark.parametrize(
    (
        "stem",
        "day_master_element",
        "resource",
        "output",
        "wealth",
        "officer",
    ),
    STEM_CASES,
)
def test_ten_stems_support_conflict(
    stem,
    day_master_element,
    resource,
    output,
    wealth,
    officer,
):
    result = evaluate_case(
        stem,
        "strong",
        [resource],
        [resource],
        "high",
    )

    support = result["support_balance"]
    agreement = result["agreement"]

    assert resource in support["unfavorable_elements"]
    assert agreement["has_conflict"] is True
    assert resource in agreement["conflicted_elements"]
    assert (
        agreement["by_element"][resource]["is_support_conflict"]
        is True
    )


@pytest.mark.parametrize(
    (
        "stem",
        "day_master_element",
        "resource",
        "output",
        "wealth",
        "officer",
    ),
    STEM_CASES,
)
def test_ten_stems_final_result_consistency(
    stem,
    day_master_element,
    resource,
    output,
    wealth,
    officer,
):
    result = evaluate_case(
        stem,
        "weak",
        [resource],
        [resource, output],
    )

    final_elements = result["final_useful_elements"]
    final_candidates = result["final_candidates"]

    assert final_elements
    assert result["has_useful_candidate"] is True
    assert result["primary_useful_element"] == final_elements[0]
    assert result["secondary_useful_elements"] == final_elements[1:]
    assert len(final_candidates) == len(final_elements)

    for index, candidate in enumerate(
        final_candidates,
        start=1,
    ):
        assert candidate["priority"] == index
        assert candidate["element"] == final_elements[index - 1]
        assert (
            candidate["integrated_score"]
            == result["integrated_element_scores"][
                candidate["element"]
            ]
        )


@pytest.mark.parametrize(
    (
        "stem",
        "day_master_element",
        "resource",
        "output",
        "wealth",
        "officer",
    ),
    STEM_CASES,
)
def test_ten_stems_all_scores_numeric(
    stem,
    day_master_element,
    resource,
    output,
    wealth,
    officer,
):
    result = evaluate_case(
        stem,
        "weak",
        [resource],
        [output],
    )

    scores = result["integrated_element_scores"]

    assert set(scores.keys()) == set(ELEMENTS)

    for value in scores.values():
        assert isinstance(value, (int, float))
        assert not isinstance(value, bool)


@pytest.mark.parametrize(
    (
        "stem",
        "day_master_element",
        "resource",
        "output",
        "wealth",
        "officer",
    ),
    STEM_CASES,
)
def test_ten_stems_evidence_integrity(
    stem,
    day_master_element,
    resource,
    output,
    wealth,
    officer,
):
    weighted = make_weighted()
    strength = make_strength(
        label="weak",
        confidence="high",
    )
    pattern = make_pattern(
        confidence="high",
    )
    climate = make_climate(
        stem,
        [resource],
        confidence="high",
    )
    pattern_useful = make_pattern_useful(
        stem,
        [resource, output],
        confidence="high",
    )

    result = evaluate_useful_gods_v3(
        stem,
        weighted,
        strength,
        pattern,
        climate,
        pattern_useful,
    )

    evidence = result["evidence"]

    assert evidence["weighted_five_elements"] == weighted
    assert evidence["final_strength_judgment"] == strength
    assert evidence["pattern_judgment"] == pattern
    assert evidence["climate_useful_gods"] == climate
    assert evidence["pattern_useful_gods"] == pattern_useful
    assert evidence["support_balance"] == result["support_balance"]
    assert evidence["v2_baseline"] == result["v2_baseline"]


@pytest.mark.parametrize(
    (
        "stem",
        "day_master_element",
        "resource",
        "output",
        "wealth",
        "officer",
    ),
    STEM_CASES,
)
def test_ten_stems_v2_baseline_preserved(
    stem,
    day_master_element,
    resource,
    output,
    wealth,
    officer,
):
    result = evaluate_case(
        stem,
        "weak",
        [resource],
        [resource],
    )

    baseline = result["v2_baseline"]

    assert baseline["method"] == "useful_gods_v2"
    assert baseline["status"] == "provisional_useful_gods_v2"
    assert baseline["support_balance"] == result["support_balance"]
    assert baseline["climate"] == result["climate"]


@pytest.mark.parametrize(
    (
        "yang_stem",
        "yin_stem",
        "resource",
    ),
    [
        ("甲", "乙", "水"),
        ("丙", "丁", "木"),
        ("戊", "己", "火"),
        ("庚", "辛", "土"),
        ("壬", "癸", "金"),
    ],
)
def test_yin_yang_pair_same_resource_result(
    yang_stem,
    yin_stem,
    resource,
):
    yang_result = evaluate_case(
        yang_stem,
        "weak",
        [resource],
        [resource],
    )

    yin_result = evaluate_case(
        yin_stem,
        "weak",
        [resource],
        [resource],
    )

    assert yang_result["primary_useful_element"] == resource
    assert yin_result["primary_useful_element"] == resource
    assert (
        yang_result["agreement"]["agreement_level"]
        == "triple_agreement"
    )
    assert (
        yin_result["agreement"]["agreement_level"]
        == "triple_agreement"
    )


@pytest.mark.parametrize(
    (
        "stem",
        "day_master_element",
        "resource",
        "output",
        "wealth",
        "officer",
    ),
    STEM_CASES,
)
def test_ten_stems_required_keys(
    stem,
    day_master_element,
    resource,
    output,
    wealth,
    officer,
):
    result = evaluate_case(
        stem,
        "weak",
        [resource],
        [resource],
    )

    required_keys = {
        "has_useful_candidate",
        "primary_useful_element",
        "secondary_useful_elements",
        "final_useful_elements",
        "final_candidates",
        "integrated_element_scores",
        "support_balance",
        "climate",
        "pattern",
        "v2_baseline",
        "agreement",
        "day_master_stem",
        "day_master_element",
        "strength_class",
        "confidence",
        "reasoning",
        "evidence",
        "method",
        "status",
        "notes",
    }

    assert required_keys.issubset(result.keys())


@pytest.mark.parametrize(
    (
        "stem",
        "day_master_element",
        "resource",
        "output",
        "wealth",
        "officer",
    ),
    STEM_CASES,
)
def test_ten_stems_reasoning_and_notes(
    stem,
    day_master_element,
    resource,
    output,
    wealth,
    officer,
):
    result = evaluate_case(
        stem,
        "weak",
        [resource],
        [resource],
    )

    assert isinstance(result["reasoning"], list)
    assert len(result["reasoning"]) >= 1
    assert isinstance(result["notes"], list)
    assert len(result["notes"]) >= 1


def test_all_ten_stems_are_covered_once():
    stems = [
        case[0]
        for case in STEM_CASES
    ]

    assert stems == [
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
    assert len(set(stems)) == 10


def test_all_five_elements_are_covered():
    assert {
        case[1]
        for case in STEM_CASES
    } == {
        "木",
        "火",
        "土",
        "金",
        "水",
    }


def test_all_resource_elements_are_covered():
    assert {
        case[2]
        for case in STEM_CASES
    } == {
        "木",
        "火",
        "土",
        "金",
        "水",
    }
