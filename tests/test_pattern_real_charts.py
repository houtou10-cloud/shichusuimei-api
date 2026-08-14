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


# 現在採用している日柱基準
# 1984-07-10 = 乙巳、日界は00:00。
# この基準に合わせ、1984-07-22 および 1985-07-17 の
# 日柱・日主・時柱・格局期待値を同期する。
REAL_CHART_CASES = [
    {
        "id": "1984_hokkaido_female_early_hour",
        "birth_date": "1984-07-22",
        "birth_time": "04:15",
        "birth_place": "北海道",
        "gender": "female",
        "pillars": {"year": "甲子", "month": "辛未", "day": "丁巳", "hour": "壬寅"},
        "day_master": "丁",
        "expected_candidate_pattern": "羊刃格",
        "expected_candidate_technical_pattern": "yangren",
        "expected_candidate_status": "requires_school_rule",
        "expected_judgment_pattern": "食神格",
        "expected_judgment_technical_pattern": "eating_god",
        "expected_month_branch": "未",
        "expected_main_hidden_stem": "己",
        "expected_ten_god": "食神",
        "expected_exposed": False,
        "expected_exposure_positions": [],
    },
    {
        "id": "1984_fukuoka_male_afternoon",
        "birth_date": "1984-07-22",
        "birth_time": "13:40",
        "birth_place": "福岡県",
        "gender": "male",
        "pillars": {"year": "甲子", "month": "辛未", "day": "丁巳", "hour": "丁未"},
        "day_master": "丁",
        "expected_candidate_pattern": "羊刃格",
        "expected_candidate_technical_pattern": "yangren",
        "expected_candidate_status": "requires_school_rule",
        "expected_judgment_pattern": "食神格",
        "expected_judgment_technical_pattern": "eating_god",
        "expected_month_branch": "未",
        "expected_main_hidden_stem": "己",
        "expected_ten_god": "食神",
        "expected_exposed": False,
        "expected_exposure_positions": [],
    },
    {
        "id": "1985_ishikawa_female_verified",
        "birth_date": "1985-07-17",
        "birth_time": "21:50",
        "birth_place": "石川県",
        "gender": "female",
        "pillars": {"year": "乙丑", "month": "癸未", "day": "丁巳", "hour": "辛亥"},
        "day_master": "丁",
        "expected_candidate_pattern": "偏印格",
        "expected_candidate_technical_pattern": "indirect_resource",
        "expected_candidate_status": "provisional_candidate",
        "expected_judgment_pattern": "偏印格",
        "expected_judgment_technical_pattern": "indirect_resource",
        "expected_month_branch": "未",
        "expected_main_hidden_stem": "己",
        "expected_ten_god": "偏印",
        "expected_exposed": True,
        "expected_exposure_positions": ["year"],
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


def test_real_chart_has_expected_pattern_candidate(real_chart_case):
    result = calculate_real_chart(real_chart_case)
    primary = result["pattern_candidates"]["primary_candidate"]
    assert primary is not None
    assert primary["pattern"] == real_chart_case["expected_candidate_pattern"]
    assert primary["technical_pattern"] == real_chart_case["expected_candidate_technical_pattern"]
    if primary["pattern_group"] == "standard_pattern":
        assert primary["source"] in {"month_main_hidden_stem", "month_exposed_hidden_stem"}
    else:
        assert primary["pattern_group"] == "special_month_pattern"
        assert primary["source"] == "day_stem_month_branch"

# =========================================================
# Month-command / candidate consistency
# =========================================================


def test_real_chart_pattern_candidate_matches_month_data(real_chart_case):
    result = calculate_real_chart(real_chart_case)
    month = result["chart"]["month"]
    primary = result["pattern_candidates"]["primary_candidate"]
    assert primary["month_branch"] == month["branch"] == real_chart_case["expected_month_branch"]
    assert primary["month_main_hidden_stem"] == month["main_hidden_stem"] == real_chart_case["expected_main_hidden_stem"]
    if primary["pattern_group"] == "standard_pattern":
        assert primary["ten_god"] == real_chart_case["expected_ten_god"]
        if primary.get("selected_hidden_stem") == month["main_hidden_stem"]:
            assert primary["ten_god"] == month["main_hidden_stem_ten_god"]
    else:
        assert primary["technical_pattern"] == "yangren"

def test_real_chart_pattern_candidate_exposure(real_chart_case):
    result = calculate_real_chart(real_chart_case)
    primary = result["pattern_candidates"]["primary_candidate"]
    assert primary["is_exposed"] is real_chart_case["expected_exposed"]
    assert primary["exposure_positions"] == real_chart_case["expected_exposure_positions"]

def test_real_chart_pattern_candidate_is_provisional(real_chart_case):
    result = calculate_real_chart(real_chart_case)
    primary = result["pattern_candidates"]["primary_candidate"]
    assert primary["is_provisional"] is True
    assert primary["candidate_status"] == real_chart_case["expected_candidate_status"]

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


def test_real_chart_primary_judgment_matches_candidate(real_chart_case):
    result = calculate_real_chart(real_chart_case)
    candidate = result["pattern_candidates"]["primary_candidate"]
    judgment = result["pattern_judgment"]
    primary = judgment["primary_judgment"]
    assert candidate["pattern"] == real_chart_case["expected_candidate_pattern"]
    assert judgment["primary_pattern"] == real_chart_case["expected_judgment_pattern"]
    assert judgment["technical_pattern"] == real_chart_case["expected_judgment_technical_pattern"]
    assert primary["pattern"] == judgment["primary_pattern"]
    assert primary["technical_pattern"] == judgment["technical_pattern"]
    # 候補抽出と成立判定は別段階。羊刃格候補が流派依存の場合、
    # pattern_judgment が普通格を主判定に採用しても整合的である。
    if candidate["pattern"] == primary["pattern"]:
        assert primary["candidate_status"] == candidate["candidate_status"]

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


def test_real_chart_exposure_factor_is_consistent(real_chart_case):
    result = calculate_real_chart(real_chart_case)
    primary = result["pattern_judgment"]["primary_judgment"]
    breaking_types = {factor["type"] for factor in primary["breaking_factors"]}
    rescue_types = {factor["type"] for factor in primary["rescue_factors"]}
    if primary["is_exposed"]:
        assert "main_hidden_stem_not_exposed" not in breaking_types
        assert "selected_month_hidden_stem_not_exposed" not in breaking_types
        expected_rescue = (
            "selected_month_hidden_stem_exposed"
            if primary.get("source_candidate", {}).get("selected_is_main_hidden_stem") is False
            else "main_hidden_stem_exposed"
        )
        assert expected_rescue in rescue_types
    elif primary["technical_pattern"] in {"direct_officer","seven_killings","direct_wealth","indirect_wealth","direct_resource","indirect_resource","eating_god","hurting_officer"}:
        assert ({"main_hidden_stem_not_exposed", "selected_month_hidden_stem_not_exposed"} & breaking_types)

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
# 乙丑 / 癸未 / 丁巳 / 辛亥
# =========================================================


def make_verified_request():
    return make_request(
        birth_date="1985-07-17",
        birth_time="21:50",
        birth_place="石川県",
        gender="female",
    )


def test_verified_1985_pattern_candidate():
    result = calculate_chart(make_verified_request())
    candidate = result["pattern_candidates"]["primary_candidate"]
    assert candidate["pattern"] == "偏印格"
    assert candidate["technical_pattern"] == "indirect_resource"
    assert candidate["month_branch"] == "未"
    assert candidate["month_main_hidden_stem"] == "己"
    assert candidate["selected_hidden_stem"] == "乙"
    assert candidate["selected_hidden_stem_rank"] == 3
    assert candidate["selected_is_main_hidden_stem"] is False
    assert candidate["ten_god"] == "偏印"
    assert candidate["source"] == "month_exposed_hidden_stem"
    assert candidate["is_exposed"] is True
    assert candidate["exposure_positions"] == ["year"]
    assert candidate["confidence"] == "high"

def test_verified_1985_pattern_judgment():
    result = calculate_chart(make_verified_request())
    judgment = result["pattern_judgment"]
    primary = judgment["primary_judgment"]
    assert judgment["primary_pattern"] == "偏印格"
    assert judgment["technical_pattern"] == "indirect_resource"
    assert primary["pattern"] == "偏印格"
    assert primary["technical_pattern"] == "indirect_resource"
    assert primary["is_exposed"] is True
    assert primary["exposure_positions"] == ["year"]
    assert isinstance(primary["establishment_score"], (int, float))
    assert 0.0 <= primary["establishment_score"] <= 100.0
    assert primary["establishment_status"] in {"strong", "possible", "weakened", "requires_school_rule"}

def test_verified_1985_not_exposed_is_breaking_factor():
    result = calculate_chart(make_verified_request())
    primary = result["pattern_judgment"]["primary_judgment"]
    breaking_types = {factor["type"] for factor in primary["breaking_factors"]}
    rescue_types = {factor["type"] for factor in primary["rescue_factors"]}
    assert "main_hidden_stem_not_exposed" not in breaking_types
    assert "selected_month_hidden_stem_not_exposed" not in breaking_types
    assert "selected_month_hidden_stem_exposed" in rescue_types

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


# =========================================================
# pattern_special_rules real-chart regression
# =========================================================


def test_real_chart_contains_pattern_special_rules(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    special_rules = result[
        "pattern_special_rules"
    ]

    assert isinstance(
        special_rules,
        dict,
    )

    required_keys = {
        "has_special_rule",
        "rule_count",
        "detected_rule_count",
        "breaking_rule_count",
        "rescue_rule_count",
        "school_rule_count",
        "overall_status",
        "total_score_adjustment",
        "rules",
        "detected_rules",
        "breaking_rules",
        "rescue_rules",
        "school_rule_items",
        "ten_god_counts",
        "ten_god_occurrences",
        "strength_evidence",
        "method",
        "status",
        "notes",
    }

    assert required_keys.issubset(
        special_rules.keys()
    )


def test_real_chart_pattern_special_rules_metadata(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    special_rules = result[
        "pattern_special_rules"
    ]

    assert (
        special_rules["method"]
        == "pattern_special_rules_v1"
    )

    assert (
        special_rules["status"]
        == "provisional_pattern_special_rules"
    )

    assert (
        special_rules["rule_count"]
        == 6
    )

    assert (
        len(
            special_rules["rules"]
        )
        == 6
    )

    assert isinstance(
        special_rules["notes"],
        list,
    )

    assert (
        len(
            special_rules["notes"]
        )
        >= 1
    )


def test_real_chart_pattern_special_rule_counts_are_consistent(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    special_rules = result[
        "pattern_special_rules"
    ]

    assert (
        special_rules[
            "detected_rule_count"
        ]
        == len(
            special_rules[
                "detected_rules"
            ]
        )
    )

    assert (
        special_rules[
            "breaking_rule_count"
        ]
        == len(
            special_rules[
                "breaking_rules"
            ]
        )
    )

    assert (
        special_rules[
            "rescue_rule_count"
        ]
        == len(
            special_rules[
                "rescue_rules"
            ]
        )
    )

    assert (
        special_rules[
            "school_rule_count"
        ]
        == len(
            special_rules[
                "school_rule_items"
            ]
        )
    )


def test_real_chart_pattern_special_rules_strength_evidence(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    special_rules = result[
        "pattern_special_rules"
    ]

    final_strength = result[
        "final_strength_judgment"
    ]

    evidence = special_rules[
        "strength_evidence"
    ]

    assert (
        evidence[
            "technical_label"
        ]
        == final_strength.get(
            "technical_label"
        )
    )

    assert (
        evidence[
            "final_score"
        ]
        == final_strength.get(
            "final_score"
        )
    )

    assert isinstance(
        evidence[
            "is_weak_day_master"
        ],
        bool,
    )


def test_real_chart_pattern_special_rules_ten_god_counts(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    special_rules = result[
        "pattern_special_rules"
    ]

    counts = special_rules[
        "ten_god_counts"
    ]

    assert isinstance(
        counts,
        dict,
    )

    expected_ten_gods = {
        "比肩",
        "劫財",
        "食神",
        "傷官",
        "偏財",
        "正財",
        "偏官",
        "正官",
        "偏印",
        "印綬",
    }

    assert (
        set(
            counts.keys()
        )
        == expected_ten_gods
    )

    assert all(
        isinstance(
            value,
            int,
        )
        and value >= 0
        for value in counts.values()
    )


def test_real_chart_pattern_special_rule_lists_have_valid_structure(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    special_rules = result[
        "pattern_special_rules"
    ]

    for rule in special_rules[
        "rules"
    ]:
        assert isinstance(
            rule,
            dict,
        )

        assert {
            "rule",
            "technical_rule",
            "detected",
            "confidence",
            "severity",
            "effect",
            "score_adjustment",
            "requires_school_rule",
            "evidence",
            "note",
        }.issubset(
            rule.keys()
        )

        assert isinstance(
            rule["detected"],
            bool,
        )

        assert rule[
            "effect"
        ] in {
            "breaking",
            "rescue",
            "neutral",
        }


def test_real_chart_pattern_special_rules_total_adjustment_is_bounded(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    adjustment = result[
        "pattern_special_rules"
    ][
        "total_score_adjustment"
    ]

    assert isinstance(
        adjustment,
        (int, float),
    )

    assert (
        -20.0
        <= adjustment
        <= 20.0
    )


def test_real_chart_pattern_judgment_receives_special_rules(
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
            "pattern_special_rules"
        ]
        == result[
            "pattern_special_rules"
        ]
    )


def test_real_chart_primary_judgment_special_rule_fields(
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
        "special_rule_adjustment"
        in primary
    )

    assert (
        "applied_special_rule_count"
        in primary
    )

    assert (
        "applied_special_rules"
        in primary
    )

    assert isinstance(
        primary[
            "special_rule_adjustment"
        ],
        (int, float),
    )

    assert (
        primary[
            "applied_special_rule_count"
        ]
        == len(
            primary[
                "applied_special_rules"
            ]
        )
    )

    assert (
        -15.0
        <= primary[
            "special_rule_adjustment"
        ]
        <= 15.0
    )


def test_verified_1985_pattern_special_rules_metadata():
    result = calculate_chart(
        make_verified_request()
    )

    special_rules = result[
        "pattern_special_rules"
    ]

    assert (
        special_rules["method"]
        == "pattern_special_rules_v1"
    )

    assert (
        special_rules["status"]
        == "provisional_pattern_special_rules"
    )

    assert (
        special_rules["rule_count"]
        == 6
    )


def test_verified_1985_pattern_judgment_special_rules_evidence():
    result = calculate_chart(
        make_verified_request()
    )

    assert (
        result[
            "pattern_judgment"
        ][
            "evidence"
        ][
            "pattern_special_rules"
        ]
        == result[
            "pattern_special_rules"
        ]
    )

# =========================================================
# climate_useful_gods_v1 / pattern_useful_gods_v1 / useful_gods_v3
# real-chart regression
# =========================================================


def test_real_chart_contains_climate_useful_gods(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    climate = result[
        "climate_useful_gods"
    ]

    assert isinstance(
        climate,
        dict,
    )

    required_keys = {
        "has_climate_candidate",
        "primary_climate_element",
        "secondary_climate_elements",
        "climate_elements",
        "climate_candidates",
        "day_master_stem",
        "day_master_element",
        "month_branch",
        "season",
        "season_japanese",
        "temperature_label",
        "moisture_label",
        "heat_score",
        "moisture_score",
        "climate_needs",
        "climate_element_scores",
        "confidence",
        "reasoning",
        "evidence",
        "method",
        "status",
        "notes",
    }

    assert required_keys.issubset(
        climate.keys()
    )


def test_real_chart_climate_useful_gods_metadata(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    climate = result[
        "climate_useful_gods"
    ]

    assert (
        climate[
            "method"
        ]
        == "climate_useful_gods_v1"
    )

    assert (
        climate[
            "status"
        ]
        == "provisional_climate_useful_gods"
    )

    assert (
        climate[
            "confidence"
        ]
        in {
            "high",
            "medium",
            "low",
        }
    )


def test_real_chart_climate_matches_chart(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    climate = result[
        "climate_useful_gods"
    ]

    assert (
        climate[
            "day_master_stem"
        ]
        == result[
            "day_master"
        ][
            "stem"
        ]
    )

    assert (
        climate[
            "month_branch"
        ]
        == result[
            "chart"
        ][
            "month"
        ][
            "branch"
        ]
    )


def test_real_chart_climate_candidate_consistency(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    climate = result[
        "climate_useful_gods"
    ]

    elements = climate[
        "climate_elements"
    ]

    assert isinstance(
        elements,
        list,
    )

    assert (
        len(
            climate[
                "climate_candidates"
            ]
        )
        == len(
            elements
        )
    )

    if elements:
        assert (
            climate[
                "has_climate_candidate"
            ]
            is True
        )

        assert (
            climate[
                "primary_climate_element"
            ]
            == elements[0]
        )

        assert (
            climate[
                "secondary_climate_elements"
            ]
            == elements[1:]
        )
    else:
        assert (
            climate[
                "has_climate_candidate"
            ]
            is False
        )

        assert (
            climate[
                "primary_climate_element"
            ]
            is None
        )

        assert (
            climate[
                "secondary_climate_elements"
            ]
            == []
        )


def test_real_chart_climate_candidate_priorities(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    climate = result[
        "climate_useful_gods"
    ]

    for index, candidate in enumerate(
        climate[
            "climate_candidates"
        ],
        start=1,
    ):
        assert (
            candidate[
                "priority"
            ]
            == index
        )

        assert (
            candidate[
                "element"
            ]
            == climate[
                "climate_elements"
            ][
                index - 1
            ]
        )


def test_real_chart_contains_useful_gods_v3(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    useful_gods = result[
        "useful_gods"
    ]

    assert isinstance(
        useful_gods,
        dict,
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

    assert required_keys.issubset(
        useful_gods.keys()
    )


def test_real_chart_useful_gods_v3_metadata(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    useful_gods = result[
        "useful_gods"
    ]

    assert (
        useful_gods[
            "method"
        ]
        == "useful_gods_v3"
    )

    assert (
        useful_gods[
            "status"
        ]
        == "provisional_useful_gods_v3"
    )

    assert (
        useful_gods[
            "confidence"
        ]
        in {
            "high",
            "medium",
            "low",
        }
    )


def test_real_chart_useful_gods_v3_matches_day_master(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    useful_gods = result[
        "useful_gods"
    ]

    assert (
        useful_gods[
            "day_master_stem"
        ]
        == result[
            "day_master"
        ][
            "stem"
        ]
    )

    assert (
        useful_gods[
            "day_master_element"
        ]
        in {
            "木",
            "火",
            "土",
            "金",
            "水",
        }
    )


def test_real_chart_useful_gods_v3_evidence_matches_results(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    evidence = result[
        "useful_gods"
    ][
        "evidence"
    ]

    assert (
        evidence[
            "weighted_five_elements"
        ]
        == result[
            "weighted_five_elements"
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
            "pattern_judgment"
        ]
        == result[
            "pattern_judgment"
        ]
    )

    assert (
        evidence[
            "climate_useful_gods"
        ]
        == result[
            "climate_useful_gods"
        ]
    )

    assert (
        evidence[
            "pattern_useful_gods"
        ]
        == result[
            "pattern_useful_gods"
        ]
    )

    assert (
        evidence[
            "v2_baseline"
        ]
        == result[
            "useful_gods"
        ][
            "v2_baseline"
        ]
    )

    assert (
        evidence[
            "support_balance"
        ]
        == result[
            "useful_gods"
        ][
            "support_balance"
        ]
    )


def test_real_chart_useful_gods_v3_support_balance_is_v1(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    support = result[
        "useful_gods"
    ][
        "support_balance"
    ]

    assert (
        support[
            "method"
        ]
        == "useful_gods_v1"
    )

    assert (
        support[
            "status"
        ]
        == "provisional_useful_gods"
    )

    assert (
        support[
            "day_master_stem"
        ]
        == result[
            "day_master"
        ][
            "stem"
        ]
    )


def test_real_chart_useful_gods_v3_strength_summary_matches(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    summary = result[
        "useful_gods"
    ][
        "support_balance"
    ][
        "evidence"
    ][
        "strength_summary"
    ]

    strength = result[
        "final_strength_judgment"
    ]

    assert (
        summary[
            "technical_label"
        ]
        == strength.get(
            "technical_label"
        )
    )

    assert (
        summary[
            "final_score"
        ]
        == strength.get(
            "final_score"
        )
    )

    assert (
        summary[
            "confidence"
        ]
        == strength.get(
            "confidence"
        )
    )


def test_real_chart_useful_gods_v3_pattern_summary_matches(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    summary = result[
        "useful_gods"
    ][
        "support_balance"
    ][
        "evidence"
    ][
        "pattern_summary"
    ]

    judgment = result[
        "pattern_judgment"
    ]

    assert (
        summary[
            "available"
        ]
        is True
    )

    assert (
        summary[
            "primary_pattern"
        ]
        == judgment.get(
            "primary_pattern"
        )
    )

    assert (
        summary[
            "technical_pattern"
        ]
        == judgment.get(
            "technical_pattern"
        )
    )

    assert (
        summary[
            "overall_judgment"
        ]
        == judgment.get(
            "overall_judgment"
        )
    )

    assert (
        summary[
            "confidence"
        ]
        == judgment.get(
            "confidence"
        )
    )


def test_real_chart_useful_gods_v3_climate_matches_top_level(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    assert (
        result[
            "useful_gods"
        ][
            "climate"
        ]
        == result[
            "climate_useful_gods"
        ]
    )


def test_real_chart_useful_gods_v3_primary_matches_final(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    useful_gods = result[
        "useful_gods"
    ]

    final_elements = useful_gods[
        "final_useful_elements"
    ]

    assert isinstance(
        final_elements,
        list,
    )

    if final_elements:
        assert (
            useful_gods[
                "has_useful_candidate"
            ]
            is True
        )

        assert (
            useful_gods[
                "primary_useful_element"
            ]
            == final_elements[0]
        )

        assert (
            useful_gods[
                "secondary_useful_elements"
            ]
            == final_elements[1:]
        )
    else:
        assert (
            useful_gods[
                "has_useful_candidate"
            ]
            is False
        )

        assert (
            useful_gods[
                "primary_useful_element"
            ]
            is None
        )

        assert (
            useful_gods[
                "secondary_useful_elements"
            ]
            == []
        )


def test_real_chart_useful_gods_v3_final_candidate_priorities(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    useful_gods = result[
        "useful_gods"
    ]

    candidates = useful_gods[
        "final_candidates"
    ]

    elements = useful_gods[
        "final_useful_elements"
    ]

    assert (
        len(
            candidates
        )
        == len(
            elements
        )
    )

    for index, candidate in enumerate(
        candidates,
        start=1,
    ):
        assert (
            candidate[
                "priority"
            ]
            == index
        )

        assert (
            candidate[
                "element"
            ]
            == elements[
                index - 1
            ]
        )

        assert (
            candidate[
                "integrated_score"
            ]
            == useful_gods[
                "integrated_element_scores"
            ][
                candidate[
                    "element"
                ]
            ]
        )


def test_real_chart_useful_gods_v3_integrated_scores(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    scores = result[
        "useful_gods"
    ][
        "integrated_element_scores"
    ]

    assert set(
        scores.keys()
    ) == {
        "木",
        "火",
        "土",
        "金",
        "水",
    }

    for value in scores.values():
        assert isinstance(
            value,
            (int, float),
        )

        assert not isinstance(
            value,
            bool,
        )


def test_real_chart_useful_gods_v3_support_element_scores_match(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    support = result[
        "useful_gods"
    ][
        "support_balance"
    ]

    weighted = result[
        "weighted_five_elements"
    ]

    expected_scores = {
        element: float(
            weighted[
                "scores"
            ][
                element
            ]
        )
        for element in (
            "木",
            "火",
            "土",
            "金",
            "水",
        )
    }

    assert (
        support[
            "element_scores"
        ]
        == expected_scores
    )


def test_real_chart_useful_gods_v3_support_primary_consistency(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    support = result[
        "useful_gods"
    ][
        "support_balance"
    ]

    favorable = support[
        "favorable_elements"
    ]

    assert isinstance(
        favorable,
        list,
    )

    assert (
        len(
            favorable
        )
        >= 1
    )

    assert (
        support[
            "primary_useful_element"
        ]
        == favorable[0]
    )

    assert (
        support[
            "secondary_favorable_elements"
        ]
        == favorable[1:]
    )


def test_real_chart_useful_gods_v3_support_unfavorable_consistency(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    support = result[
        "useful_gods"
    ][
        "support_balance"
    ]

    unfavorable = support[
        "unfavorable_elements"
    ]

    assert isinstance(
        unfavorable,
        list,
    )

    if unfavorable:
        assert (
            support[
                "primary_unfavorable_element"
            ]
            == unfavorable[0]
        )
    else:
        assert (
            support[
                "primary_unfavorable_element"
            ]
            is None
        )


def test_real_chart_useful_gods_v3_support_candidate_priorities(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    support = result[
        "useful_gods"
    ][
        "support_balance"
    ]

    candidates = support[
        "useful_candidates"
    ]

    assert (
        len(
            candidates
        )
        == len(
            support[
                "favorable_elements"
            ]
        )
    )

    for index, candidate in enumerate(
        candidates,
        start=1,
    ):
        assert (
            candidate[
                "priority"
            ]
            == index
        )

        assert (
            candidate[
                "element"
            ]
            == support[
                "favorable_elements"
            ][
                index - 1
            ]
        )

        assert (
            candidate[
                "category"
            ]
            == "favorable"
        )


def test_real_chart_useful_gods_v3_support_groups_are_disjoint(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    support = result[
        "useful_gods"
    ][
        "support_balance"
    ]

    favorable = set(
        support[
            "favorable_elements"
        ]
    )

    unfavorable = set(
        support[
            "unfavorable_elements"
        ]
    )

    neutral = set(
        support[
            "neutral_elements"
        ]
    )

    assert favorable.isdisjoint(
        unfavorable
    )

    assert favorable.isdisjoint(
        neutral
    )

    assert unfavorable.isdisjoint(
        neutral
    )


def test_real_chart_useful_gods_v3_agreement_structure(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    agreement = result[
        "useful_gods"
    ][
        "agreement"
    ]

    required_keys = {
        "agreement_level",
        "has_triple_agreement",
        "has_double_agreement",
        "has_conflict",
        "triple_agreement_elements",
        "double_agreement_elements",
        "single_source_elements",
        "conflicted_elements",
        "by_element",
        "support_primary_element",
        "climate_primary_element",
        "pattern_primary_element",
    }

    assert required_keys.issubset(
        agreement.keys()
    )

    assert (
        agreement[
            "agreement_level"
        ]
        in {
            "triple_agreement",
            "double_agreement",
            "single_source_only",
            "no_candidate",
        }
    )


def test_real_chart_useful_gods_v3_agreement_references_sources(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    useful_gods = result[
        "useful_gods"
    ]

    agreement = useful_gods[
        "agreement"
    ]

    support = useful_gods[
        "support_balance"
    ]

    climate = useful_gods[
        "climate"
    ]

    pattern = useful_gods[
        "pattern"
    ]

    assert (
        agreement[
            "support_primary_element"
        ]
        == support.get(
            "primary_useful_element"
        )
    )

    assert (
        agreement[
            "climate_primary_element"
        ]
        == climate.get(
            "primary_climate_element"
        )
    )

    assert (
        agreement[
            "pattern_primary_element"
        ]
        == pattern.get(
            "primary_pattern_element"
        )
    )


def test_real_chart_useful_gods_v3_pattern_matches_top_level(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    assert (
        result[
            "useful_gods"
        ][
            "pattern"
        ]
        == result[
            "pattern_useful_gods"
        ]
    )


def test_real_chart_useful_gods_v3_preserves_v2_baseline(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    useful_gods = result[
        "useful_gods"
    ]

    baseline = useful_gods[
        "v2_baseline"
    ]

    assert (
        baseline[
            "method"
        ]
        == "useful_gods_v2"
    )

    assert (
        baseline[
            "status"
        ]
        == "provisional_useful_gods_v2"
    )

    assert (
        baseline[
            "support_balance"
        ]
        == useful_gods[
            "support_balance"
        ]
    )

    assert (
        baseline[
            "climate"
        ]
        == useful_gods[
            "climate"
        ]
    )


def test_real_chart_useful_gods_v3_reasoning_and_notes(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    useful_gods = result[
        "useful_gods"
    ]

    assert isinstance(
        useful_gods[
            "reasoning"
        ],
        list,
    )

    assert (
        len(
            useful_gods[
                "reasoning"
            ]
        )
        >= 1
    )

    assert isinstance(
        useful_gods[
            "notes"
        ],
        list,
    )

    assert (
        len(
            useful_gods[
                "notes"
            ]
        )
        >= 1
    )


def test_verified_1985_climate_useful_gods_metadata():
    result = calculate_chart(
        make_verified_request()
    )

    climate = result[
        "climate_useful_gods"
    ]

    assert (
        climate[
            "method"
        ]
        == "climate_useful_gods_v1"
    )

    assert (
        climate[
            "status"
        ]
        == "provisional_climate_useful_gods"
    )

    assert (
        climate[
            "day_master_stem"
        ]
        == "丁"
    )

    assert (
        climate[
            "day_master_element"
        ]
        == "火"
    )

    assert (
        climate[
            "month_branch"
        ]
        == "未"
    )

    assert (
        climate[
            "season"
        ]
        == "summer"
    )

    assert (
        climate[
            "primary_climate_element"
        ]
        == "水"
    )


def test_verified_1985_useful_gods_v3_metadata():
    result = calculate_chart(
        make_verified_request()
    )

    useful_gods = result[
        "useful_gods"
    ]

    assert (
        useful_gods[
            "method"
        ]
        == "useful_gods_v3"
    )

    assert (
        useful_gods[
            "status"
        ]
        == "provisional_useful_gods_v3"
    )

    assert (
        useful_gods[
            "day_master_stem"
        ]
        == "丁"
    )

    assert (
        useful_gods[
            "day_master_element"
        ]
        == "火"
    )

    assert (
        useful_gods[
            "climate"
        ]
        == result[
            "climate_useful_gods"
        ]
    )


def test_verified_1985_useful_gods_v3_evidence_integrity():
    result = calculate_chart(
        make_verified_request()
    )

    evidence = result[
        "useful_gods"
    ][
        "evidence"
    ]

    assert (
        evidence[
            "weighted_five_elements"
        ]
        == result[
            "weighted_five_elements"
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
            "pattern_judgment"
        ]
        == result[
            "pattern_judgment"
        ]
    )

    assert (
        evidence[
            "climate_useful_gods"
        ]
        == result[
            "climate_useful_gods"
        ]
    )

    assert (
        evidence[
            "support_balance"
        ]
        == result[
            "useful_gods"
        ][
            "support_balance"
        ]
    )


def test_verified_1985_useful_gods_v3_climate_is_water():
    result = calculate_chart(
        make_verified_request()
    )

    useful_gods = result[
        "useful_gods"
    ]

    assert (
        useful_gods[
            "climate"
        ][
            "month_branch"
        ]
        == "未"
    )

    assert (
        useful_gods[
            "climate"
        ][
            "primary_climate_element"
        ]
        == "水"
    )

# =========================================================
# pattern_useful_gods_v1 real-chart regression
# =========================================================


def test_real_chart_contains_pattern_useful_gods(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    pattern_useful = result[
        "pattern_useful_gods"
    ]

    assert isinstance(
        pattern_useful,
        dict,
    )

    required_keys = {
        "has_pattern_useful_candidate",
        "primary_pattern_element",
        "secondary_pattern_elements",
        "pattern_elements",
        "pattern_candidates",
        "day_master_stem",
        "day_master_element",
        "primary_pattern",
        "technical_pattern",
        "pattern_overall_judgment",
        "pattern_confidence",
        "supported_pattern",
        "element_relations",
        "confidence",
        "reasoning",
        "evidence",
        "method",
        "status",
        "notes",
    }

    assert required_keys.issubset(
        pattern_useful.keys()
    )


def test_real_chart_pattern_useful_gods_metadata(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    pattern_useful = result[
        "pattern_useful_gods"
    ]

    assert (
        pattern_useful[
            "method"
        ]
        == "pattern_useful_gods_v1"
    )

    assert (
        pattern_useful[
            "status"
        ]
        == "provisional_pattern_useful_gods"
    )

    assert (
        pattern_useful[
            "confidence"
        ]
        in {
            "high",
            "medium",
            "low",
        }
    )


def test_real_chart_pattern_useful_gods_matches_day_master(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    pattern_useful = result[
        "pattern_useful_gods"
    ]

    assert (
        pattern_useful[
            "day_master_stem"
        ]
        == result[
            "day_master"
        ][
            "stem"
        ]
    )

    assert (
        pattern_useful[
            "day_master_element"
        ]
        in {
            "木",
            "火",
            "土",
            "金",
            "水",
        }
    )


def test_real_chart_pattern_useful_gods_matches_pattern_judgment(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    pattern_useful = result[
        "pattern_useful_gods"
    ]

    judgment = result[
        "pattern_judgment"
    ]

    assert (
        pattern_useful[
            "primary_pattern"
        ]
        == judgment.get(
            "primary_pattern"
        )
    )

    assert (
        pattern_useful[
            "technical_pattern"
        ]
        == judgment.get(
            "technical_pattern"
        )
    )

    assert (
        pattern_useful[
            "pattern_overall_judgment"
        ]
        == judgment.get(
            "overall_judgment"
        )
    )

    assert (
        pattern_useful[
            "pattern_confidence"
        ]
        == judgment.get(
            "confidence"
        )
    )


def test_real_chart_pattern_useful_gods_candidate_consistency(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    pattern_useful = result[
        "pattern_useful_gods"
    ]

    elements = pattern_useful[
        "pattern_elements"
    ]

    candidates = pattern_useful[
        "pattern_candidates"
    ]

    assert isinstance(
        elements,
        list,
    )

    assert isinstance(
        candidates,
        list,
    )

    assert (
        len(
            candidates
        )
        == len(
            elements
        )
    )

    if elements:
        assert (
            pattern_useful[
                "has_pattern_useful_candidate"
            ]
            is True
        )

        assert (
            pattern_useful[
                "primary_pattern_element"
            ]
            == elements[0]
        )

        assert (
            pattern_useful[
                "secondary_pattern_elements"
            ]
            == elements[1:]
        )
    else:
        assert (
            pattern_useful[
                "has_pattern_useful_candidate"
            ]
            is False
        )

        assert (
            pattern_useful[
                "primary_pattern_element"
            ]
            is None
        )

        assert (
            pattern_useful[
                "secondary_pattern_elements"
            ]
            == []
        )


def test_real_chart_pattern_useful_gods_candidate_priorities(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    pattern_useful = result[
        "pattern_useful_gods"
    ]

    for index, candidate in enumerate(
        pattern_useful[
            "pattern_candidates"
        ],
        start=1,
    ):
        assert (
            candidate[
                "priority"
            ]
            == index
        )

        assert (
            candidate[
                "element"
            ]
            == pattern_useful[
                "pattern_elements"
            ][
                index - 1
            ]
        )


def test_real_chart_pattern_useful_gods_evidence_matches(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    evidence = result[
        "pattern_useful_gods"
    ][
        "evidence"
    ]

    assert (
        evidence[
            "pattern_judgment"
        ]
        == result[
            "pattern_judgment"
        ]
    )

    assert (
        evidence[
            "weighted_five_elements"
        ]
        == result[
            "weighted_five_elements"
        ]
    )

    assert (
        evidence[
            "pattern_info"
        ][
            "technical_pattern"
        ]
        == result[
            "pattern_judgment"
        ].get(
            "technical_pattern"
        )
    )

    assert isinstance(
        evidence[
            "raw_candidates"
        ],
        list,
    )


def test_real_chart_pattern_useful_gods_reasoning_and_notes(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    pattern_useful = result[
        "pattern_useful_gods"
    ]

    assert isinstance(
        pattern_useful[
            "reasoning"
        ],
        list,
    )

    assert isinstance(
        pattern_useful[
            "notes"
        ],
        list,
    )

    assert (
        len(
            pattern_useful[
                "notes"
            ]
        )
        >= 1
    )


def test_verified_1985_pattern_useful_gods_metadata():
    result = calculate_chart(
        make_verified_request()
    )

    pattern_useful = result[
        "pattern_useful_gods"
    ]

    assert (
        pattern_useful[
            "method"
        ]
        == "pattern_useful_gods_v1"
    )

    assert (
        pattern_useful[
            "status"
        ]
        == "provisional_pattern_useful_gods"
    )

    assert (
        pattern_useful[
            "day_master_stem"
        ]
        == "丁"
    )

    assert (
        pattern_useful[
            "day_master_element"
        ]
        == "火"
    )


def test_verified_1985_pattern_useful_gods_pattern_matches():
    result = calculate_chart(make_verified_request())
    pattern_useful = result["pattern_useful_gods"]
    assert pattern_useful["primary_pattern"] == "偏印格"
    assert pattern_useful["technical_pattern"] == "indirect_resource"
    assert pattern_useful["pattern_overall_judgment"] == result["pattern_judgment"]["overall_judgment"]
    assert pattern_useful["pattern_confidence"] == result["pattern_judgment"]["confidence"]

def test_verified_1985_pattern_useful_gods_elements():
    result = calculate_chart(make_verified_request())
    pattern_useful = result["pattern_useful_gods"]
    assert pattern_useful["supported_pattern"] is True
    assert pattern_useful["pattern_elements"] == ["金", "水"]
    assert pattern_useful["primary_pattern_element"] == "金"
    assert pattern_useful["secondary_pattern_elements"] == ["水"]

def test_verified_1985_pattern_useful_gods_candidate_roles():
    result = calculate_chart(make_verified_request())
    candidates = result["pattern_useful_gods"]["pattern_candidates"]
    assert len(candidates) == 2
    assert candidates[0]["element"] == "金"
    assert candidates[0]["relations"] == ["wealth"]
    assert candidates[0]["roles"] == ["control_excess_resource"]
    assert candidates[0]["priority"] == 1
    assert candidates[1]["element"] == "水"
    assert candidates[1]["relations"] == ["officer"]
    assert candidates[1]["roles"] == ["generate_resource"]
    assert candidates[1]["priority"] == 2

def test_verified_1985_pattern_useful_gods_evidence_integrity():
    result = calculate_chart(make_verified_request())
    pattern_useful = result["pattern_useful_gods"]
    evidence = pattern_useful["evidence"]
    assert evidence["pattern_judgment"] == result["pattern_judgment"]
    assert evidence["weighted_five_elements"] == result["weighted_five_elements"]
    assert evidence["pattern_info"]["technical_pattern"] == "indirect_resource"

