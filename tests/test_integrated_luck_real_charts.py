"""
tests/test_integrated_luck_real_charts.py

integrated_luck_v1 の実命式回帰テスト。

目的
----
既存の検証用3命式を使い、

    四柱
      ↓
    useful_gods_v3
      ↓
    luck_pillars_v2
      ↓
    current_luck_v1
      ↓
    annual_luck_v1
      ↓
    integrated_luck_v1

という計算パイプラインが、
実命式でも整合していることを確認する。

注意
----
このテストは「古典上の運勢の最終正解」を
固定するものではない。

integrated_luck_v1 の
計算パイプライン・データ整合性・
既存機能との接続を回帰固定するためのテストである。
"""

from datetime import datetime
from types import SimpleNamespace

import pytest

from engine.chart import calculate_chart
from engine.integrated_luck import (
    calculate_integrated_luck,
)


# =========================================================
# Fixed target datetime
# =========================================================


TARGET_DATETIME = datetime(
    2026,
    8,
    10,
    15,
    36,
)


# =========================================================
# Request helper
# =========================================================


def make_request(
    birth_date: str,
    birth_time: str | None,
    birth_place: str,
    gender: str,
):
    """
    calculate_chart() に渡す
    既存テスト互換のrequestを作る。
    """

    return SimpleNamespace(
        birth_date=birth_date,
        birth_time=birth_time,
        birth_place=birth_place,
        gender=gender,
    )


# =========================================================
# Real chart cases
# =========================================================


REAL_CHART_CASES = [
    {
        "id": (
            "1984_hokkaido_"
            "female_early_hour"
        ),
        "birth_date": "1984-07-22",
        "birth_time": "04:15",
        "birth_place": "北海道",
        "gender": "female",
        "pillars": {
            "year": "甲子",
            "month": "辛未",
            "day": "丁巳",
            "hour": "壬寅",
        },
        "day_master": "丁",
    },
    {
        "id": (
            "1984_fukuoka_"
            "male_afternoon"
        ),
        "birth_date": "1984-07-22",
        "birth_time": "13:40",
        "birth_place": "福岡県",
        "gender": "male",
        "pillars": {
            "year": "甲子",
            "month": "辛未",
            "day": "丁巳",
            "hour": "丁未",
        },
        "day_master": "丁",
    },
    {
        "id": (
            "1985_ishikawa_"
            "female_verified"
        ),
        "birth_date": "1985-07-17",
        "birth_time": "21:50",
        "birth_place": "石川県",
        "gender": "female",
        "pillars": {
            "year": "乙丑",
            "month": "癸未",
            "day": "丁巳",
            "hour": "辛亥",
        },
        "day_master": "丁",
    },
]


@pytest.fixture(
    params=REAL_CHART_CASES,
    ids=[
        case["id"]
        for case in REAL_CHART_CASES
    ],
)
def real_chart_case(request):
    return request.param


def calculate_real_chart(case):
    """
    固定評価日時で実命式を計算する。
    """

    request = make_request(
        birth_date=case[
            "birth_date"
        ],
        birth_time=case[
            "birth_time"
        ],
        birth_place=case[
            "birth_place"
        ],
        gender=case[
            "gender"
        ],
    )

    return calculate_chart(
        request,
        target_datetime=TARGET_DATETIME,
    )


# =========================================================
# Known pillar regression
# =========================================================


def test_real_chart_known_pillars(
    real_chart_case,
):
    """
    integrated_luck追加によって
    既知の四柱が変化していないことを確認する。
    """

    result = calculate_real_chart(
        real_chart_case
    )

    expected = real_chart_case[
        "pillars"
    ]

    assert (
        result[
            "chart"
        ][
            "year"
        ][
            "pillar"
        ]
        == expected[
            "year"
        ]
    )

    assert (
        result[
            "chart"
        ][
            "month"
        ][
            "pillar"
        ]
        == expected[
            "month"
        ]
    )

    assert (
        result[
            "chart"
        ][
            "day"
        ][
            "pillar"
        ]
        == expected[
            "day"
        ]
    )

    assert (
        result[
            "chart"
        ][
            "hour"
        ][
            "pillar"
        ]
        == expected[
            "hour"
        ]
    )


def test_real_chart_day_master(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    assert (
        result[
            "day_master"
        ][
            "stem"
        ]
        == real_chart_case[
            "day_master"
        ]
    )


# =========================================================
# Pipeline versions
# =========================================================


def test_real_chart_useful_gods_v3(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    assert (
        result[
            "useful_gods"
        ][
            "method"
        ]
        == "useful_gods_v3"
    )


def test_real_chart_luck_pillars_v2(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    assert (
        result[
            "luck_pillars"
        ][
            "method"
        ]
        == "luck_pillars_v2"
    )


def test_real_chart_current_luck_v1(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    assert (
        result[
            "current_luck"
        ][
            "method"
        ]
        == "current_luck_v1"
    )


def test_real_chart_annual_luck_v1(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    assert (
        result[
            "annual_luck"
        ][
            "method"
        ]
        == "annual_luck_v1"
    )


def test_real_chart_integrated_luck_v1(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    assert (
        result[
            "integrated_luck"
        ][
            "method"
        ]
        == "integrated_luck_v1"
    )

    assert (
        result[
            "integrated_luck"
        ][
            "status"
        ]
        == (
            "provisional_integrated_luck_v1"
        )
    )


# =========================================================
# Integrated luck structure
# =========================================================


def test_real_chart_integrated_luck_required_keys(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    integrated = result[
        "integrated_luck"
    ]

    required_keys = {
        "current_luck_ganzhi",
        "annual_luck_ganzhi",
        "current_luck_elements",
        "annual_luck_elements",
        "element_interactions",
        "current_luck_useful",
        "annual_luck_useful",
        "useful_gods_agreement",
        "annual_ten_god",
        "annual_twelve_stage",
        "score",
        "overall_score",
        "overall_level",
        "confidence",
        "reasoning",
        "evidence",
        "method",
        "status",
        "notes",
    }

    assert required_keys.issubset(
        integrated.keys()
    )


# =========================================================
# Current luck consistency
# =========================================================


def test_real_chart_current_luck_exists(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    current_luck = result[
        "current_luck"
    ]

    assert (
        current_luck[
            "has_current_luck"
        ]
        is True
    )

    assert isinstance(
        current_luck[
            "current_luck_pillar"
        ],
        dict,
    )


def test_real_chart_integrated_current_ganzhi_matches(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    current_pillar = result[
        "current_luck"
    ][
        "current_luck_pillar"
    ]

    assert (
        result[
            "integrated_luck"
        ][
            "current_luck_ganzhi"
        ]
        == current_pillar[
            "ganzhi"
        ]
    )


def test_real_chart_integrated_current_elements_match(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    current_pillar = result[
        "current_luck"
    ][
        "current_luck_pillar"
    ]

    elements = result[
        "integrated_luck"
    ][
        "current_luck_elements"
    ]

    assert (
        elements[
            "stem"
        ]
        == current_pillar[
            "stem_element"
        ]
    )

    assert (
        elements[
            "branch"
        ]
        == current_pillar[
            "branch_element"
        ]
    )


# =========================================================
# Annual luck consistency
# =========================================================


def test_real_chart_2026_annual_luck_is_bingwu(
    real_chart_case,
):
    """
    3命式とも評価年は2026年なので
    歳運干支は丙午。
    """

    result = calculate_real_chart(
        real_chart_case
    )

    assert (
        result[
            "annual_luck"
        ][
            "year"
        ]
        == 2026
    )

    assert (
        result[
            "annual_luck"
        ][
            "ganzhi"
        ]
        == "丙午"
    )

    assert (
        result[
            "integrated_luck"
        ][
            "annual_luck_ganzhi"
        ]
        == "丙午"
    )


def test_real_chart_integrated_annual_ganzhi_matches(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    assert (
        result[
            "integrated_luck"
        ][
            "annual_luck_ganzhi"
        ]
        == result[
            "annual_luck"
        ][
            "ganzhi"
        ]
    )


def test_real_chart_integrated_annual_elements_match(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    annual = result[
        "annual_luck"
    ]

    elements = result[
        "integrated_luck"
    ][
        "annual_luck_elements"
    ]

    assert (
        elements[
            "stem"
        ]
        == annual[
            "stem_element"
        ]
    )

    assert (
        elements[
            "branch"
        ]
        == annual[
            "branch_element"
        ]
    )


# =========================================================
# Ten god / twelve stage
# =========================================================


def test_real_chart_2026_ten_god_is_gouzai(
    real_chart_case,
):
    """
    3命式の日主はいずれも丁。

    丁日主に対する2026年丙は
    劫財。
    """

    result = calculate_real_chart(
        real_chart_case
    )

    assert (
        result[
            "annual_luck"
        ][
            "stem_ten_god"
        ]
        == "劫財"
    )

    assert (
        result[
            "integrated_luck"
        ][
            "annual_ten_god"
        ]
        == "劫財"
    )


def test_real_chart_2026_twelve_stage_is_kenroku(
    real_chart_case,
):
    """
    3命式の日主はいずれも丁。

    丁 × 午 = 建禄。
    """

    result = calculate_real_chart(
        real_chart_case
    )

    assert (
        result[
            "annual_luck"
        ][
            "twelve_stage"
        ]
        == "建禄"
    )

    assert (
        result[
            "integrated_luck"
        ][
            "annual_twelve_stage"
        ]
        == "建禄"
    )


def test_real_chart_integrated_ten_god_matches_annual(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    assert (
        result[
            "integrated_luck"
        ][
            "annual_ten_god"
        ]
        == result[
            "annual_luck"
        ][
            "stem_ten_god"
        ]
    )


def test_real_chart_integrated_twelve_stage_matches_annual(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    assert (
        result[
            "integrated_luck"
        ][
            "annual_twelve_stage"
        ]
        == result[
            "annual_luck"
        ][
            "twelve_stage"
        ]
    )


# =========================================================
# Element interaction
# =========================================================


def test_real_chart_element_interactions_structure(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    interactions = result[
        "integrated_luck"
    ][
        "element_interactions"
    ]

    required_keys = {
        "current_luck_elements",
        "annual_luck_elements",
        "stem_relation",
        "branch_relation",
        "score",
    }

    assert required_keys.issubset(
        interactions.keys()
    )

    for relation_key in {
        "stem_relation",
        "branch_relation",
    }:
        relation = interactions[
            relation_key
        ]

        assert {
            "source_element",
            "target_element",
            "relationship",
            "score",
        }.issubset(
            relation.keys()
        )


def test_real_chart_element_interaction_score_consistency(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    interactions = result[
        "integrated_luck"
    ][
        "element_interactions"
    ]

    expected = (
        interactions[
            "stem_relation"
        ][
            "score"
        ]
        + interactions[
            "branch_relation"
        ][
            "score"
        ]
    )

    assert (
        interactions[
            "score"
        ]
        == expected
    )


# =========================================================
# Useful gods integration
# =========================================================


def test_real_chart_integrated_useful_structures(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    integrated = result[
        "integrated_luck"
    ]

    for key in {
        "current_luck_useful",
        "annual_luck_useful",
    }:
        useful = integrated[
            key
        ]

        assert {
            "stem_element",
            "branch_element",
            "stem_relation",
            "branch_relation",
            "stem_score",
            "branch_score",
            "score",
        }.issubset(
            useful.keys()
        )


def test_real_chart_annual_useful_matches_annual_luck(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    integrated = result[
        "integrated_luck"
    ]

    annual = result[
        "annual_luck"
    ]

    assert (
        integrated[
            "annual_luck_useful"
        ][
            "stem_relation"
        ]
        == annual[
            "stem_useful_relation"
        ]
    )

    assert (
        integrated[
            "annual_luck_useful"
        ][
            "branch_relation"
        ]
        == annual[
            "branch_useful_relation"
        ]
    )


# =========================================================
# Agreement
# =========================================================


def test_real_chart_useful_gods_agreement_structure(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    agreement = result[
        "integrated_luck"
    ][
        "useful_gods_agreement"
    ]

    required_keys = {
        "agreement_level",
        "useful_count",
        "unfavorable_count",
        "known_count",
        "has_useful_alignment",
        "has_unfavorable_alignment",
        "has_mixed_signal",
    }

    assert required_keys.issubset(
        agreement.keys()
    )


def test_real_chart_useful_gods_agreement_counts(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    agreement = result[
        "integrated_luck"
    ][
        "useful_gods_agreement"
    ]

    assert (
        0
        <= agreement[
            "known_count"
        ]
        <= 4
    )

    assert (
        0
        <= agreement[
            "useful_count"
        ]
        <= 4
    )

    assert (
        0
        <= agreement[
            "unfavorable_count"
        ]
        <= 4
    )

    assert (
        agreement[
            "useful_count"
        ]
        + agreement[
            "unfavorable_count"
        ]
        <= agreement[
            "known_count"
        ]
    )


# =========================================================
# Score
# =========================================================


def test_real_chart_integrated_score_structure(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    score = result[
        "integrated_luck"
    ][
        "score"
    ]

    required_keys = {
        "element_interaction_score",
        "current_luck_useful_score",
        "annual_luck_useful_score",
        "total_score",
    }

    assert required_keys.issubset(
        score.keys()
    )


def test_real_chart_integrated_score_sum(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    integrated = result[
        "integrated_luck"
    ]

    score = integrated[
        "score"
    ]

    expected = (
        score[
            "element_interaction_score"
        ]
        + score[
            "current_luck_useful_score"
        ]
        + score[
            "annual_luck_useful_score"
        ]
    )

    assert (
        score[
            "total_score"
        ]
        == expected
    )

    assert (
        integrated[
            "overall_score"
        ]
        == score[
            "total_score"
        ]
    )


def test_real_chart_integrated_level_valid(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    assert (
        result[
            "integrated_luck"
        ][
            "overall_level"
        ]
        in {
            "very_supportive",
            "supportive",
            "mixed",
            "challenging",
            "very_challenging",
        }
    )


# =========================================================
# Confidence
# =========================================================


def test_real_chart_integrated_confidence_high(
    real_chart_case,
):
    """
    chart統合では、

    - current_luck
    - annual_luck
    - useful_gods

    の3ソースが揃うためhigh。
    """

    result = calculate_real_chart(
        real_chart_case
    )

    confidence = result[
        "integrated_luck"
    ][
        "confidence"
    ]

    assert (
        confidence[
            "available_sources"
        ]
        == 3
    )

    assert (
        confidence[
            "total_sources"
        ]
        == 3
    )

    assert (
        confidence[
            "ratio"
        ]
        == 1.0
    )

    assert (
        confidence[
            "level"
        ]
        == "high"
    )


# =========================================================
# Reasoning
# =========================================================


def test_real_chart_integrated_reasoning_exists(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    integrated = result[
        "integrated_luck"
    ]

    reasoning = integrated[
        "reasoning"
    ]

    assert isinstance(
        reasoning,
        list,
    )

    assert (
        len(
            reasoning
        )
        >= 1
    )

    joined = "".join(
        reasoning
    )

    assert (
        integrated[
            "current_luck_ganzhi"
        ]
        in joined
    )

    assert "丙午" in joined
    assert "劫財" in joined
    assert "建禄" in joined


# =========================================================
# Evidence
# =========================================================


def test_real_chart_integrated_evidence_structure(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    evidence = result[
        "integrated_luck"
    ][
        "evidence"
    ]

    required_keys = {
        "current_luck_ganzhi",
        "annual_luck_ganzhi",
        "element_interactions",
        "current_luck_useful",
        "annual_luck_useful",
        "useful_gods_agreement",
        "annual_ten_god",
        "annual_twelve_stage",
        "score",
    }

    assert required_keys.issubset(
        evidence.keys()
    )


def test_real_chart_integrated_evidence_consistency(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    integrated = result[
        "integrated_luck"
    ]

    evidence = integrated[
        "evidence"
    ]

    assert (
        evidence[
            "current_luck_ganzhi"
        ]
        == integrated[
            "current_luck_ganzhi"
        ]
    )

    assert (
        evidence[
            "annual_luck_ganzhi"
        ]
        == integrated[
            "annual_luck_ganzhi"
        ]
    )

    assert (
        evidence[
            "annual_ten_god"
        ]
        == integrated[
            "annual_ten_god"
        ]
    )

    assert (
        evidence[
            "annual_twelve_stage"
        ]
        == integrated[
            "annual_twelve_stage"
        ]
    )

    assert (
        evidence[
            "score"
        ]
        == integrated[
            "score"
        ]
    )


# =========================================================
# Direct engine equivalence
# =========================================================


def test_real_chart_integrated_matches_direct_engine(
    real_chart_case,
):
    """
    chart.py 経由の結果と、
    integrated_luckエンジンを直接呼んだ結果が
    完全一致することを確認する。
    """

    result = calculate_real_chart(
        real_chart_case
    )

    expected = (
        calculate_integrated_luck(
            current_luck=result[
                "current_luck"
            ],
            annual_luck=result[
                "annual_luck"
            ],
            useful_gods=result[
                "useful_gods"
            ],
        )
    )

    assert (
        result[
            "integrated_luck"
        ]
        == expected
    )


# =========================================================
# Reproducibility
# =========================================================


def test_real_chart_integrated_is_reproducible(
    real_chart_case,
):
    first = calculate_real_chart(
        real_chart_case
    )

    second = calculate_real_chart(
        real_chart_case
    )

    assert (
        first[
            "integrated_luck"
        ]
        == second[
            "integrated_luck"
        ]
    )


# =========================================================
# Cross-case regression
# =========================================================


def test_all_real_charts_integrated_luck_can_be_calculated():
    """
    3命式を一括で計算して、
    すべてintegrated_luck_v1まで
    到達できることを確認する。
    """

    results = [
        calculate_real_chart(
            case
        )
        for case in REAL_CHART_CASES
    ]

    assert len(
        results
    ) == 3

    for result in results:
        integrated = result[
            "integrated_luck"
        ]

        assert isinstance(
            integrated,
            dict,
        )

        assert (
            integrated[
                "method"
            ]
            == "integrated_luck_v1"
        )

        assert (
            integrated[
                "annual_luck_ganzhi"
            ]
            == "丙午"
        )

        assert (
            integrated[
                "annual_ten_god"
            ]
            == "劫財"
        )

        assert (
            integrated[
                "annual_twelve_stage"
            ]
            == "建禄"
        )


def test_all_real_charts_preserve_day_master_hinoto():
    """
    3命式はいずれも丁日主であることを
    回帰固定する。
    """

    for case in REAL_CHART_CASES:
        result = calculate_real_chart(
            case
        )

        assert (
            result[
                "day_master"
            ][
                "stem"
            ]
            == "丁"
        )


def test_all_real_charts_preserve_pipeline_versions():
    """
    integrated_luck追加後も、
    既存パイプラインの世代を維持する。
    """

    for case in REAL_CHART_CASES:
        result = calculate_real_chart(
            case
        )

        assert (
            result[
                "useful_gods"
            ][
                "method"
            ]
            == "useful_gods_v3"
        )

        assert (
            result[
                "luck_pillars"
            ][
                "method"
            ]
            == "luck_pillars_v2"
        )

        assert (
            result[
                "current_luck"
            ][
                "method"
            ]
            == "current_luck_v1"
        )

        assert (
            result[
                "annual_luck"
            ][
                "method"
            ]
            == "annual_luck_v1"
        )

        assert (
            result[
                "integrated_luck"
            ][
                "method"
            ]
            == "integrated_luck_v1"
        )
