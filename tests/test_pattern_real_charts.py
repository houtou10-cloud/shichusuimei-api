"""
実命式を使った pattern_candidates / pattern_judgment v1 の回帰テスト。

目的:
- 既知の四柱が崩れていないこと
- 実命式で格局候補が返ること
- 月令主蔵干と格局候補が一致すること
- pattern_candidates と pattern_judgment が整合すること
- breaking / rescue factor の構造が壊れていないこと
- evidence が calculate_chart の各結果を保持すること
- 検証済み1985年命式の代表的な格局判定を固定すること

注意:
このファイルは「古典上の最終的な格局正解データセット」ではない。
現時点の pattern_judgment v1 の計算パイプラインを
実命式で回帰固定するためのテストである。

官殺混雑、食神制殺、傷官見官、財多身弱、
印綬の財破、偏印奪食、従格、化格などは
後続バージョンで検証項目を追加する。
"""

from types import SimpleNamespace

import pytest

from engine.chart import calculate_chart


def make_request(
    birth_date: str,
    birth_time: str | None,
    birth_place: str,
    gender: str,
):
    return SimpleNamespace(
        birth_date=birth_date,
        birth_time=birth_time,
        birth_place=birth_place,
        gender=gender,
    )


REAL_CHART_CASES = [
    {
        "id": "1984_hokkaido_female_early_hour",
        "birth_date": "1984-07-22",
        "birth_time": "04:15",
        "birth_place": "北海道",
        "gender": "female",
        "pillars": {
            "year": "甲子",
            "month": "辛未",
            "day": "乙巳",
            "hour": "戊寅",
        },
        "day_master": "乙",
        "expected_pattern": "偏財格",
        "expected_technical_pattern": (
            "indirect_wealth"
        ),
        "expected_month_branch": "未",
        "expected_main_hidden_stem": "己",
        "expected_ten_god": "偏財",
        "expected_exposed": True,
        "expected_exposure_positions": [
            "hour",
        ],
    },
    {
        "id": "1984_fukuoka_male_afternoon",
        "birth_date": "1984-07-22",
        "birth_time": "13:40",
        "birth_place": "福岡県",
        "gender": "male",
        "pillars": {
            "year": "甲子",
            "month": "辛未",
            "day": "乙巳",
            "hour": "癸未",
        },
        "day_master": "乙",
        "expected_pattern": "偏財格",
        "expected_technical_pattern": (
            "indirect_wealth"
        ),
        "expected_month_branch": "未",
        "expected_main_hidden_stem": "己",
        "expected_ten_god": "偏財",
        "expected_exposed": False,
        "expected_exposure_positions": [],
    },
    {
        "id": "1985_ishikawa_female_verified",
        "birth_date": "1985-07-17",
        "birth_time": "21:50",
        "birth_place": "石川県",
        "gender": "female",
        "pillars": {
            "year": "乙丑",
            "month": "癸未",
            "day": "乙巳",
            "hour": "丁亥",
        },
        "day_master": "乙",
        "expected_pattern": "偏財格",
        "expected_technical_pattern": (
            "indirect_wealth"
        ),
        "expected_month_branch": "未",
        "expected_main_hidden_stem": "己",
        "expected_ten_god": "偏財",
        "expected_exposed": False,
        "expected_exposure_positions": [],
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
        request
    )


# =========================================================
# Known pillar regression
# =========================================================


def test_real_pattern_chart_known_pillars(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    expected = real_chart_case[
        "pillars"
    ]

    assert (
        result["chart"]["year"][
            "pillar"
        ]
        == expected["year"]
    )

    assert (
        result["chart"]["month"][
            "pillar"
        ]
        == expected["month"]
    )

    assert (
        result["chart"]["day"][
            "pillar"
        ]
        == expected["day"]
    )

    assert (
        result["chart"]["hour"][
            "pillar"
        ]
        == expected["hour"]
    )

    assert (
        result["day_master"][
            "stem"
        ]
        == real_chart_case[
            "day_master"
        ]
    )


# =========================================================
# pattern_candidates structure
# =========================================================


def test_real_chart_contains_pattern_candidates(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    candidates = result[
        "pattern_candidates"
    ]

    assert isinstance(
        candidates,
        dict,
    )

    required_keys = {
        "has_candidate",
        "candidate_count",
        "primary_candidate",
        "candidates",
        "candidate_groups",
        "has_school_rule_candidate",
        "month_context",
        "day_master_stem",
        "overall_status",
        "method",
        "status",
        "notes",
    }

    assert required_keys.issubset(
        candidates.keys()
    )


def test_real_chart_pattern_candidates_metadata(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    candidates = result[
        "pattern_candidates"
    ]

    assert (
        candidates["method"]
        == "pattern_candidates_v1"
    )

    assert (
        candidates["status"]
        == "provisional_pattern_candidates"
    )

    assert isinstance(
        candidates["notes"],
        list,
    )

    assert (
        len(
            candidates["notes"]
        )
        >= 1
    )


def test_real_chart_has_expected_pattern_candidate(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    candidates = result[
        "pattern_candidates"
    ]

    assert (
        candidates[
            "has_candidate"
        ]
        is True
    )

    assert (
        candidates[
            "candidate_count"
        ]
        >= 1
    )

    primary = candidates[
        "primary_candidate"
    ]

    assert primary is not None

    assert (
        primary["pattern"]
        == real_chart_case[
            "expected_pattern"
        ]
    )

    assert (
        primary[
            "technical_pattern"
        ]
        == real_chart_case[
            "expected_technical_pattern"
        ]
    )

    assert (
        primary[
            "pattern_group"
        ]
        == "standard_pattern"
    )

    assert (
        primary["source"]
        == "month_main_hidden_stem"
    )


# =========================================================
# Month-command / candidate consistency
# =========================================================


def test_real_chart_pattern_candidate_matches_month_data(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    month = result[
        "chart"
    ][
        "month"
    ]

    primary = result[
        "pattern_candidates"
    ][
        "primary_candidate"
    ]

    assert (
        primary[
            "month_branch"
        ]
        == month[
            "branch"
        ]
    )

    assert (
        primary[
            "month_main_hidden_stem"
        ]
        == month[
            "main_hidden_stem"
        ]
    )

    assert (
        primary[
            "ten_god"
        ]
        == month[
            "main_hidden_stem_ten_god"
        ]
    )

    assert (
        primary[
            "month_branch"
        ]
        == real_chart_case[
            "expected_month_branch"
        ]
    )

    assert (
        primary[
            "month_main_hidden_stem"
        ]
        == real_chart_case[
            "expected_main_hidden_stem"
        ]
    )

    assert (
        primary[
            "ten_god"
        ]
        == real_chart_case[
            "expected_ten_god"
        ]
    )


def test_real_chart_pattern_candidate_exposure(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    primary = result[
        "pattern_candidates"
    ][
        "primary_candidate"
    ]

    assert (
        primary[
            "is_exposed"
        ]
        is real_chart_case[
            "expected_exposed"
        ]
    )

    assert (
        primary[
            "exposure_positions"
        ]
        == real_chart_case[
            "expected_exposure_positions"
        ]
    )


def test_real_chart_pattern_candidate_is_provisional(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    primary = result[
        "pattern_candidates"
    ][
        "primary_candidate"
    ]

    assert (
        primary[
            "is_provisional"
        ]
        is True
    )

    assert (
        primary[
            "candidate_status"
        ]
        == "provisional_candidate"
    )


# =========================================================
# pattern_judgment structure
# =========================================================


def test_real_chart_contains_pattern_judgment(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    judgment = result[
        "pattern_judgment"
    ]

    assert isinstance(
        judgment,
        dict,
    )

    required_keys = {
        "has_pattern_candidate",
        "has_pattern",
        "judgment_count",
        "primary_pattern",
        "technical_pattern",
        "primary_judgment",
        "judgments",
        "strong_count",
        "possible_count",
        "weakened_count",
        "school_rule_count",
        "overall_judgment",
        "confidence",
        "evidence",
        "method",
        "status",
        "notes",
    }

    assert required_keys.issubset(
        judgment.keys()
    )


def test_real_chart_pattern_judgment_metadata(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    judgment = result[
        "pattern_judgment"
    ]

    assert (
        judgment["method"]
        == "pattern_judgment_v2"
    )

    assert (
        judgment["status"]
        == "provisional_pattern_judgment_v2"
    )

    assert isinstance(
        judgment["notes"],
        list,
    )

    assert (
        len(
            judgment["notes"]
        )
        >= 1
    )


def test_real_chart_pattern_judgment_has_pattern(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    judgment = result[
        "pattern_judgment"
    ]

    assert (
        judgment[
            "has_pattern_candidate"
        ]
        is True
    )

    assert (
        judgment[
            "has_pattern"
        ]
        is True
    )

    assert (
        judgment[
            "judgment_count"
        ]
        >= 1
    )

    assert (
        judgment[
            "primary_judgment"
        ]
        is not None
    )


# =========================================================
# candidates / judgment consistency
# =========================================================


def test_real_chart_primary_judgment_matches_candidate(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    candidate = result[
        "pattern_candidates"
    ][
        "primary_candidate"
    ]

    judgment = result[
        "pattern_judgment"
    ]

    primary = judgment[
        "primary_judgment"
    ]

    assert (
        judgment[
            "primary_pattern"
        ]
        == candidate[
            "pattern"
        ]
    )

    assert (
        judgment[
            "technical_pattern"
        ]
        == candidate[
            "technical_pattern"
        ]
    )

    assert (
        primary[
            "pattern"
        ]
        == candidate[
            "pattern"
        ]
    )

    assert (
        primary[
            "technical_pattern"
        ]
        == candidate[
            "technical_pattern"
        ]
    )

    assert (
        primary[
            "candidate_confidence"
        ]
        == candidate[
            "confidence"
        ]
    )

    assert (
        primary[
            "candidate_status"
        ]
        == candidate[
            "candidate_status"
        ]
    )

    assert (
        primary[
            "is_exposed"
        ]
        is candidate[
            "is_exposed"
        ]
    )

    assert (
        primary[
            "exposure_positions"
        ]
        == candidate[
            "exposure_positions"
        ]
    )


# =========================================================
# Score / classification integrity
# =========================================================


def test_real_chart_pattern_score_formula(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    primary = result[
        "pattern_judgment"
    ][
        "primary_judgment"
    ]

    expected_raw = round(
        primary[
            "base_score"
        ]
        + primary[
            "exposure_adjustment"
        ]
        + primary[
            "school_rule_adjustment"
        ]
        + primary[
            "transformation_adjustment"
        ]
        + primary[
            "branch_adjustment"
        ]
        + primary[
            "special_rule_adjustment"
        ],
        2,
    )

    assert (
        primary[
            "raw_score"
        ]
        == expected_raw
    )

    expected_score = round(
        max(
            0.0,
            min(
                100.0,
                expected_raw,
            ),
        ),
        2,
    )

    assert (
        primary[
            "establishment_score"
        ]
        == expected_score
    )


def expected_establishment(
    primary,
):
    if primary[
        "requires_school_rule"
    ]:
        return (
            "requires_school_rule",
            "requires_school_rule",
        )

    score = primary[
        "establishment_score"
    ]

    if score >= 75.0:
        return (
            "strong",
            "provisional_established",
        )

    if score >= 55.0:
        return (
            "possible",
            "provisional_possible",
        )

    return (
        "weakened",
        "provisional_weakened",
    )


def test_real_chart_pattern_classification_matches_score(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    primary = result[
        "pattern_judgment"
    ][
        "primary_judgment"
    ]

    (
        expected_status,
        expected_final,
    ) = expected_establishment(
        primary
    )

    assert (
        primary[
            "establishment_status"
        ]
        == expected_status
    )

    assert (
        primary[
            "final_judgment"
        ]
        == expected_final
    )

    assert (
        result[
            "pattern_judgment"
        ][
            "overall_judgment"
        ]
        == expected_final
    )


def test_real_chart_pattern_confidence_is_valid(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    judgment = result[
        "pattern_judgment"
    ]

    primary = judgment[
        "primary_judgment"
    ]

    assert (
        primary["confidence"]
        in {
            "high",
            "medium",
            "low",
        }
    )

    assert (
        judgment["confidence"]
        == primary["confidence"]
    )


# =========================================================
# Breaking / rescue factors
# =========================================================


def test_real_chart_factor_counts_are_consistent(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    primary = result[
        "pattern_judgment"
    ][
        "primary_judgment"
    ]

    assert (
        primary[
            "breaking_factor_count"
        ]
        == len(
            primary[
                "breaking_factors"
            ]
        )
    )

    assert (
        primary[
            "rescue_factor_count"
        ]
        == len(
            primary[
                "rescue_factors"
            ]
        )
    )


def test_real_chart_exposure_factor_is_consistent(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    primary = result[
        "pattern_judgment"
    ][
        "primary_judgment"
    ]

    breaking_types = {
        factor[
            "type"
        ]
        for factor in primary[
            "breaking_factors"
        ]
    }

    rescue_types = {
        factor[
            "type"
        ]
        for factor in primary[
            "rescue_factors"
        ]
    }

    if primary[
        "is_exposed"
    ]:
        assert (
            "main_hidden_stem_not_exposed"
            not in breaking_types
        )

        assert (
            "main_hidden_stem_exposed"
            in rescue_types
        )

    else:
        assert (
            "main_hidden_stem_not_exposed"
            in breaking_types
        )

        assert (
            "main_hidden_stem_exposed"
            not in rescue_types
        )


def test_real_chart_balanced_strength_rescue_is_consistent(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    final_strength = result[
        "final_strength_judgment"
    ]

    primary = result[
        "pattern_judgment"
    ][
        "primary_judgment"
    ]

    rescue_types = {
        factor[
            "type"
        ]
        for factor in primary[
            "rescue_factors"
        ]
    }

    if (
        final_strength[
            "technical_label"
        ]
        == "balanced"
    ):
        assert (
            "balanced_day_master"
            in rescue_types
        )


# =========================================================
# Evidence integrity
# =========================================================


def test_real_chart_pattern_evidence_matches_results(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    evidence = result[
        "pattern_judgment"
    ][
        "evidence"
    ]

    assert (
        evidence[
            "pattern_candidates"
        ]
        == result[
            "pattern_candidates"
        ]
    )

    assert (
        evidence[
            "final_strength_judgment"
        ]
        == result[
            "final_strength_judgment"
        ]
    )

    assert (
        evidence[
            "stem_transformation_judgment"
        ]
        == result[
            "stem_transformation_judgment"
        ]
    )

    assert (
        evidence[
            "branch_relation_strength"
        ]
        == result[
            "branch_relation_strength"
        ]
    )


# =========================================================
# total_score must remain evidence-only in pattern v1
# =========================================================


def test_real_chart_branch_total_score_is_not_directly_applied(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    relation_strength = result[
        "branch_relation_strength"
    ]

    primary = result[
        "pattern_judgment"
    ][
        "primary_judgment"
    ]

    if (
        isinstance(
            relation_strength,
            dict,
        )
        and "total_score"
        in relation_strength
        and not any(
            isinstance(
                relation_strength.get(
                    key
                ),
                (int, float),
            )
            for key in (
                "strength_adjustment",
                "day_master_adjustment",
                "adjustment",
            )
        )
    ):
        assert (
            primary[
                "branch_adjustment"
            ]
            == 0.0
        )


# =========================================================
# Verified 1985 regression
# 乙丑 / 癸未 / 乙巳 / 丁亥
# =========================================================


def make_verified_request():
    return make_request(
        birth_date="1985-07-17",
        birth_time="21:50",
        birth_place="石川県",
        gender="female",
    )


def test_verified_1985_pattern_candidate():
    result = calculate_chart(
        make_verified_request()
    )

    candidate = result[
        "pattern_candidates"
    ][
        "primary_candidate"
    ]

    assert (
        candidate["pattern"]
        == "偏財格"
    )

    assert (
        candidate[
            "technical_pattern"
        ]
        == "indirect_wealth"
    )

    assert (
        candidate[
            "month_branch"
        ]
        == "未"
    )

    assert (
        candidate[
            "month_main_hidden_stem"
        ]
        == "己"
    )

    assert (
        candidate[
            "ten_god"
        ]
        == "偏財"
    )

    assert (
        candidate[
            "is_exposed"
        ]
        is False
    )

    assert (
        candidate[
            "exposure_positions"
        ]
        == []
    )

    assert (
        candidate[
            "confidence"
        ]
        == "medium"
    )


def test_verified_1985_pattern_judgment():
    result = calculate_chart(
        make_verified_request()
    )

    judgment = result[
        "pattern_judgment"
    ]

    primary = judgment[
        "primary_judgment"
    ]

    assert (
        judgment[
            "primary_pattern"
        ]
        == "偏財格"
    )

    assert (
        judgment[
            "technical_pattern"
        ]
        == "indirect_wealth"
    )

    assert (
        primary[
            "base_score"
        ]
        == 60.0
    )

    assert (
        primary[
            "exposure_adjustment"
        ]
        == 0.0
    )

    assert (
        primary[
            "branch_adjustment"
        ]
        == 0.0
    )

    assert (
        primary[
            "establishment_score"
        ]
        == 60.0
    )

    assert (
        primary[
            "establishment_status"
        ]
        == "possible"
    )

    assert (
        primary[
            "final_judgment"
        ]
        == "provisional_possible"
    )

    assert (
        judgment[
            "overall_judgment"
        ]
        == "provisional_possible"
    )

    assert (
        judgment[
            "confidence"
        ]
        == "medium"
    )


def test_verified_1985_not_exposed_is_breaking_factor():
    result = calculate_chart(
        make_verified_request()
    )

    primary = result[
        "pattern_judgment"
    ][
        "primary_judgment"
    ]

    breaking_types = {
        factor[
            "type"
        ]
        for factor in primary[
            "breaking_factors"
        ]
    }

    assert (
        "main_hidden_stem_not_exposed"
        in breaking_types
    )


def test_verified_1985_balanced_rescue_when_applicable():
    result = calculate_chart(
        make_verified_request()
    )

    final_strength = result[
        "final_strength_judgment"
    ]

    primary = result[
        "pattern_judgment"
    ][
        "primary_judgment"
    ]

    rescue_types = {
        factor[
            "type"
        ]
        for factor in primary[
            "rescue_factors"
        ]
    }

    if (
        final_strength[
            "technical_label"
        ]
        == "balanced"
    ):
        assert (
            "balanced_day_master"
            in rescue_types
        )


def test_verified_1985_pattern_metadata():
    result = calculate_chart(
        make_verified_request()
    )

    candidates = result[
        "pattern_candidates"
    ]

    judgment = result[
        "pattern_judgment"
    ]

    assert (
        candidates["method"]
        == "pattern_candidates_v1"
    )

    assert (
        candidates["status"]
        == "provisional_pattern_candidates"
    )

    assert (
        judgment["method"]
        == "pattern_judgment_v2"
    )

    assert (
        judgment["status"]
        == "provisional_pattern_judgment_v2"
    )
