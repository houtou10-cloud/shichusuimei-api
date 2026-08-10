"""
実命式を使った final_strength_judgment v2 の回帰テスト。

目的:
- 既知の四柱が崩れていないこと
- final_strength_judgment が実命式で返ること
- 通根・月令を二重計上していないこと
- final_score の加算式が一貫していること
- 既知の検証命式について代表値を固定すること

注意:
このファイルは「占術上の正解データセット」そのものではない。
まずは既存の検証命式と計算パイプラインの回帰を固定する。
今後、外部の信頼できる鑑定基準と照合した命式を追加して、
身強身弱の精度検証用データセットへ拡張する。
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


# 日柱回帰基準:
# 1984-07-10 = 乙巳
# 1984-07-21 = 丙辰
# 1984-07-22 = 丁巳
# 1985-07-17 = 丁巳
# 日干変更に伴い時柱も再計算する。
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
            "day": "丁巳",
            "hour": "壬寅",
        },
        "day_master": "丁",
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
            "day": "丁巳",
            "hour": "丁未",
        },
        "day_master": "丁",
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


def test_real_chart_known_pillars(
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
# final_strength_judgment structure
# =========================================================


def test_real_chart_contains_final_strength_judgment(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    judgment = result[
        "final_strength_judgment"
    ]

    assert isinstance(
        judgment,
        dict,
    )

    required_keys = {
        "base_score",
        "root_adjustment",
        "month_adjustment",
        "branch_adjustment",
        "transformation_adjustment",
        "adjustment_total",
        "raw_final_score",
        "final_score",
        "technical_label",
        "label",
        "confidence",
        "components",
        "evidence",
        "double_count_prevention",
        "method",
        "status",
        "notes",
    }

    assert required_keys.issubset(
        judgment.keys()
    )


def test_real_chart_final_strength_metadata(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    judgment = result[
        "final_strength_judgment"
    ]

    assert (
        judgment["method"]
        == "final_strength_judgment_v2"
    )

    assert (
        judgment["status"]
        == (
            "provisional_final_strength_"
            "judgment_v2"
        )
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


# =========================================================
# Double count prevention
# =========================================================


def test_real_chart_root_is_not_reapplied(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    judgment = result[
        "final_strength_judgment"
    ]

    assert (
        judgment["root_adjustment"]
        == 0.0
    )

    assert (
        judgment["components"]["root"][
            "applied_to_final_score"
        ]
        is False
    )

    assert (
        judgment[
            "double_count_prevention"
        ][
            "root_reapplied"
        ]
        is False
    )


def test_real_chart_month_is_not_reapplied(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    judgment = result[
        "final_strength_judgment"
    ]

    assert (
        judgment["month_adjustment"]
        == 0.0
    )

    assert (
        judgment["components"]["month"][
            "applied_to_final_score"
        ]
        is False
    )

    assert (
        judgment[
            "double_count_prevention"
        ][
            "month_reapplied"
        ]
        is False
    )


def test_real_chart_double_count_reason(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    prevention = result[
        "final_strength_judgment"
    ][
        "double_count_prevention"
    ]

    assert (
        prevention["reason"]
        == (
            "root_and_month_are_already_"
            "included_in_weighted_"
            "strength_judgment"
        )
    )


# =========================================================
# Formula consistency
# =========================================================


def test_real_chart_adjustment_total_formula(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    judgment = result[
        "final_strength_judgment"
    ]

    expected = round(
        judgment[
            "branch_adjustment"
        ]
        + judgment[
            "transformation_adjustment"
        ],
        2,
    )

    assert (
        judgment["adjustment_total"]
        == expected
    )


def test_real_chart_raw_final_score_formula(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    judgment = result[
        "final_strength_judgment"
    ]

    expected = round(
        judgment["base_score"]
        + judgment[
            "adjustment_total"
        ],
        2,
    )

    assert (
        judgment["raw_final_score"]
        == expected
    )


def test_real_chart_final_score_is_clamped(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    judgment = result[
        "final_strength_judgment"
    ]

    expected = round(
        max(
            0.0,
            min(
                100.0,
                judgment[
                    "raw_final_score"
                ],
            ),
        ),
        2,
    )

    assert (
        judgment["final_score"]
        == expected
    )

    assert (
        0.0
        <= judgment["final_score"]
        <= 100.0
    )


# =========================================================
# Label consistency
# =========================================================


def expected_label_from_score(
    score: float,
):
    if score >= 70.0:
        return (
            "very_strong",
            "極身強",
        )

    if score >= 58.0:
        return (
            "strong",
            "身強",
        )

    if score >= 43.0:
        return (
            "balanced",
            "中和",
        )

    if score >= 30.0:
        return (
            "weak",
            "身弱",
        )

    return (
        "very_weak",
        "極身弱",
    )


def test_real_chart_label_matches_final_score(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    judgment = result[
        "final_strength_judgment"
    ]

    (
        expected_technical,
        expected_label,
    ) = expected_label_from_score(
        judgment["final_score"]
    )

    assert (
        judgment[
            "technical_label"
        ]
        == expected_technical
    )

    assert (
        judgment["label"]
        == expected_label
    )


def test_real_chart_confidence_is_valid(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    confidence = result[
        "final_strength_judgment"
    ][
        "confidence"
    ]

    assert confidence in {
        "high",
        "medium",
        "low",
    }


# =========================================================
# Evidence integrity
# =========================================================


def test_real_chart_evidence_matches_chart_results(
    real_chart_case,
):
    result = calculate_real_chart(
        real_chart_case
    )

    evidence = result[
        "final_strength_judgment"
    ][
        "evidence"
    ]

    assert (
        evidence[
            "weighted_strength_judgment"
        ]
        == result[
            "weighted_strength_judgment"
        ]
    )

    assert (
        evidence[
            "weighted_root_strength"
        ]
        == result[
            "weighted_root_strength"
        ]
    )

    assert (
        evidence[
            "integrated_month_strength"
        ]
        == result[
            "integrated_month_strength"
        ]
    )

    assert (
        evidence[
            "branch_relations"
        ]
        == result[
            "branch_relation_strength"
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


# =========================================================
# Verified real-chart regression
# =========================================================


def make_verified_request():
    return make_request(
        birth_date="1985-07-17",
        birth_time="21:50",
        birth_place="石川県",
        gender="female",
    )


def test_verified_1985_chart_pillars():
    result = calculate_chart(
        make_verified_request()
    )

    assert (
        result["chart"]["year"][
            "pillar"
        ]
        == "乙丑"
    )

    assert (
        result["chart"]["month"][
            "pillar"
        ]
        == "癸未"
    )

    assert (
        result["chart"]["day"][
            "pillar"
        ]
        == "丁巳"
    )

    assert (
        result["chart"]["hour"][
            "pillar"
        ]
        == "辛亥"
    )


def test_verified_1985_final_strength_no_double_count():
    result = calculate_chart(
        make_verified_request()
    )

    judgment = result[
        "final_strength_judgment"
    ]

    assert (
        judgment["root_adjustment"]
        == 0.0
    )

    assert (
        judgment["month_adjustment"]
        == 0.0
    )

    assert (
        judgment[
            "double_count_prevention"
        ][
            "root_reapplied"
        ]
        is False
    )

    assert (
        judgment[
            "double_count_prevention"
        ][
            "month_reapplied"
        ]
        is False
    )


def test_verified_1985_total_score_is_evidence_only():
    result = calculate_chart(
        make_verified_request()
    )

    relation_strength = result[
        "branch_relation_strength"
    ]

    judgment = result[
        "final_strength_judgment"
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
            judgment[
                "branch_adjustment"
            ]
            == 0.0
        )

        assert (
            judgment["components"][
                "branch_relations"
            ][
                "applied_to_final_score"
            ]
            is False
        )


def test_verified_1985_final_score_formula():
    result = calculate_chart(
        make_verified_request()
    )

    judgment = result[
        "final_strength_judgment"
    ]

    expected = round(
        judgment["base_score"]
        + judgment[
            "branch_adjustment"
        ]
        + judgment[
            "transformation_adjustment"
        ],
        2,
    )

    expected = round(
        max(
            0.0,
            min(
                100.0,
                expected,
            ),
        ),
        2,
    )

    assert (
        judgment["final_score"]
        == expected
    )
