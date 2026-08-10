"""
tests/test_api.py

FastAPI 統合テスト。

対象:
    POST /api/v1/chart

目的
----
実際のAPI経路で、

    main.py
      ↓
    api.routes
      ↓
    calculate_chart()
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

まで返ることを確認する。

注意
----
APIでは現時点で target_datetime を
リクエストから指定できない。

そのため、年によって変わる
annual_luck.ganzhi の固定値は
このテストでは原則として断定しない。

代わりに、

    annual_luck
    integrated_luck

同士の内部整合性を確認する。
"""

from fastapi.testclient import TestClient

from main import app


client = TestClient(
    app
)


# =========================================================
# Test data
# =========================================================


VERIFIED_REQUEST = {
    "birth_date": "1985-07-17",
    "birth_time": "21:50",
    "birth_place": "石川県",
    "gender": "female",
}


EXPECTED_PILLARS = {
    "year": "乙丑",
    "month": "癸未",
    "day": "丁巳",
    "hour": "丁亥",
}


# =========================================================
# Root
# =========================================================


def test_root_api():
    response = client.get(
        "/"
    )

    assert (
        response.status_code
        == 200
    )

    data = response.json()

    assert data[
        "status"
    ] == "ok"

    assert (
        data[
            "message"
        ]
        == (
            "Shichusuimei API "
            "is running."
        )
    )


# =========================================================
# Basic chart endpoint
# =========================================================


def test_chart_api_status_200():
    response = client.post(
        "/api/v1/chart",
        json=VERIFIED_REQUEST,
    )

    assert (
        response.status_code
        == 200
    )


def test_chart_api_success_true():
    response = client.post(
        "/api/v1/chart",
        json=VERIFIED_REQUEST,
    )

    data = response.json()

    assert (
        data[
            "success"
        ]
        is True
    )


def test_chart_api_result_exists():
    response = client.post(
        "/api/v1/chart",
        json=VERIFIED_REQUEST,
    )

    data = response.json()

    assert "result" in data

    assert isinstance(
        data[
            "result"
        ],
        dict,
    )


# =========================================================
# Known pillar regression
# =========================================================


def test_chart_api_known_pillars():
    response = client.post(
        "/api/v1/chart",
        json=VERIFIED_REQUEST,
    )

    result = response.json()[
        "result"
    ]

    chart = result[
        "chart"
    ]

    assert (
        chart[
            "year"
        ][
            "pillar"
        ]
        == EXPECTED_PILLARS[
            "year"
        ]
    )

    assert (
        chart[
            "month"
        ][
            "pillar"
        ]
        == EXPECTED_PILLARS[
            "month"
        ]
    )

    assert (
        chart[
            "day"
        ][
            "pillar"
        ]
        == EXPECTED_PILLARS[
            "day"
        ]
    )

    assert (
        chart[
            "hour"
        ][
            "pillar"
        ]
        == EXPECTED_PILLARS[
            "hour"
        ]
    )


def test_chart_api_day_master():
    response = client.post(
        "/api/v1/chart",
        json=VERIFIED_REQUEST,
    )

    result = response.json()[
        "result"
    ]

    assert (
        result[
            "day_master"
        ][
            "stem"
        ]
        == "丁"
    )


# =========================================================
# Pipeline versions
# =========================================================


def test_chart_api_useful_gods_v3():
    response = client.post(
        "/api/v1/chart",
        json=VERIFIED_REQUEST,
    )

    result = response.json()[
        "result"
    ]

    assert (
        result[
            "useful_gods"
        ][
            "method"
        ]
        == "useful_gods_v3"
    )


def test_chart_api_luck_pillars_v2():
    response = client.post(
        "/api/v1/chart",
        json=VERIFIED_REQUEST,
    )

    result = response.json()[
        "result"
    ]

    assert (
        result[
            "luck_pillars"
        ][
            "method"
        ]
        == "luck_pillars_v2"
    )


def test_chart_api_current_luck_v1():
    response = client.post(
        "/api/v1/chart",
        json=VERIFIED_REQUEST,
    )

    result = response.json()[
        "result"
    ]

    assert (
        result[
            "current_luck"
        ][
            "method"
        ]
        == "current_luck_v1"
    )


def test_chart_api_annual_luck_v1():
    response = client.post(
        "/api/v1/chart",
        json=VERIFIED_REQUEST,
    )

    result = response.json()[
        "result"
    ]

    assert (
        result[
            "annual_luck"
        ][
            "method"
        ]
        == "annual_luck_v1"
    )


def test_chart_api_integrated_luck_v1():
    response = client.post(
        "/api/v1/chart",
        json=VERIFIED_REQUEST,
    )

    result = response.json()[
        "result"
    ]

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
            "provisional_"
            "integrated_luck_v1"
        )
    )


# =========================================================
# Annual luck structure
# =========================================================


def test_chart_api_annual_luck_required_keys():
    response = client.post(
        "/api/v1/chart",
        json=VERIFIED_REQUEST,
    )

    annual = response.json()[
        "result"
    ][
        "annual_luck"
    ]

    required_keys = {
        "year",
        "ganzhi",
        "stem",
        "branch",
        "stem_element",
        "branch_element",
        "day_master_stem",
        "stem_ten_god",
        "twelve_stage",
        "stem_useful_relation",
        "branch_useful_relation",
        "current_luck_relation",
        "method",
        "status",
    }

    assert required_keys.issubset(
        annual.keys()
    )


def test_chart_api_annual_luck_matches_day_master():
    response = client.post(
        "/api/v1/chart",
        json=VERIFIED_REQUEST,
    )

    result = response.json()[
        "result"
    ]

    assert (
        result[
            "annual_luck"
        ][
            "day_master_stem"
        ]
        == result[
            "day_master"
        ][
            "stem"
        ]
    )


# =========================================================
# Integrated luck structure
# =========================================================


def test_chart_api_integrated_luck_required_keys():
    response = client.post(
        "/api/v1/chart",
        json=VERIFIED_REQUEST,
    )

    integrated = response.json()[
        "result"
    ][
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
# Cross-layer consistency
# =========================================================


def test_chart_api_integrated_annual_ganzhi_matches():
    response = client.post(
        "/api/v1/chart",
        json=VERIFIED_REQUEST,
    )

    result = response.json()[
        "result"
    ]

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


def test_chart_api_integrated_current_ganzhi_matches():
    response = client.post(
        "/api/v1/chart",
        json=VERIFIED_REQUEST,
    )

    result = response.json()[
        "result"
    ]

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


def test_chart_api_integrated_ten_god_matches():
    response = client.post(
        "/api/v1/chart",
        json=VERIFIED_REQUEST,
    )

    result = response.json()[
        "result"
    ]

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


def test_chart_api_integrated_twelve_stage_matches():
    response = client.post(
        "/api/v1/chart",
        json=VERIFIED_REQUEST,
    )

    result = response.json()[
        "result"
    ]

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
# Element consistency
# =========================================================


def test_chart_api_integrated_annual_elements_match():
    response = client.post(
        "/api/v1/chart",
        json=VERIFIED_REQUEST,
    )

    result = response.json()[
        "result"
    ]

    annual = result[
        "annual_luck"
    ]

    integrated = result[
        "integrated_luck"
    ]

    assert (
        integrated[
            "annual_luck_elements"
        ][
            "stem"
        ]
        == annual[
            "stem_element"
        ]
    )

    assert (
        integrated[
            "annual_luck_elements"
        ][
            "branch"
        ]
        == annual[
            "branch_element"
        ]
    )


def test_chart_api_element_interaction_score():
    response = client.post(
        "/api/v1/chart",
        json=VERIFIED_REQUEST,
    )

    interactions = response.json()[
        "result"
    ][
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
# Score consistency
# =========================================================


def test_chart_api_integrated_score_consistency():
    response = client.post(
        "/api/v1/chart",
        json=VERIFIED_REQUEST,
    )

    integrated = response.json()[
        "result"
    ][
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


def test_chart_api_integrated_level_valid():
    response = client.post(
        "/api/v1/chart",
        json=VERIFIED_REQUEST,
    )

    level = response.json()[
        "result"
    ][
        "integrated_luck"
    ][
        "overall_level"
    ]

    assert level in {
        "very_supportive",
        "supportive",
        "mixed",
        "challenging",
        "very_challenging",
    }


# =========================================================
# Confidence
# =========================================================


def test_chart_api_integrated_confidence():
    response = client.post(
        "/api/v1/chart",
        json=VERIFIED_REQUEST,
    )

    confidence = response.json()[
        "result"
    ][
        "integrated_luck"
    ][
        "confidence"
    ]

    assert {
        "available_sources",
        "total_sources",
        "ratio",
        "level",
    }.issubset(
        confidence.keys()
    )

    assert (
        confidence[
            "total_sources"
        ]
        == 3
    )

    assert (
        confidence[
            "level"
        ]
        == "high"
    )


# =========================================================
# Evidence
# =========================================================


def test_chart_api_integrated_evidence_consistency():
    response = client.post(
        "/api/v1/chart",
        json=VERIFIED_REQUEST,
    )

    integrated = response.json()[
        "result"
    ][
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
# Reasoning
# =========================================================


def test_chart_api_integrated_reasoning_exists():
    response = client.post(
        "/api/v1/chart",
        json=VERIFIED_REQUEST,
    )

    integrated = response.json()[
        "result"
    ][
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


# =========================================================
# API validation
# =========================================================


def test_chart_api_missing_birth_date():
    payload = dict(
        VERIFIED_REQUEST
    )

    payload.pop(
        "birth_date"
    )

    response = client.post(
        "/api/v1/chart",
        json=payload,
    )

    assert (
        response.status_code
        == 422
    )


def test_chart_api_missing_birth_place():
    payload = dict(
        VERIFIED_REQUEST
    )

    payload.pop(
        "birth_place"
    )

    response = client.post(
        "/api/v1/chart",
        json=payload,
    )

    assert (
        response.status_code
        == 422
    )


def test_chart_api_missing_gender():
    payload = dict(
        VERIFIED_REQUEST
    )

    payload.pop(
        "gender"
    )

    response = client.post(
        "/api/v1/chart",
        json=payload,
    )

    assert (
        response.status_code
        == 422
    )


def test_chart_api_birth_time_optional():
    payload = dict(
        VERIFIED_REQUEST
    )

    payload[
        "birth_time"
    ] = None

    response = client.post(
        "/api/v1/chart",
        json=payload,
    )

    assert (
        response.status_code
        == 200
    )

    data = response.json()

    assert (
        data[
            "success"
        ]
        is True
    )


# =========================================================
# Reproducibility within same run
# =========================================================


def test_chart_api_repeated_request_core_consistency():
    """
    API側では target_datetime を
    外から固定できないため、
    annual_luck全体の完全一致は要求しない。

    一方、出生命式そのものは
    同じ入力なら一致する。
    """

    first = client.post(
        "/api/v1/chart",
        json=VERIFIED_REQUEST,
    )

    second = client.post(
        "/api/v1/chart",
        json=VERIFIED_REQUEST,
    )

    assert (
        first.status_code
        == 200
    )

    assert (
        second.status_code
        == 200
    )

    first_result = first.json()[
        "result"
    ]

    second_result = second.json()[
        "result"
    ]

    assert (
        first_result[
            "chart"
        ]
        == second_result[
            "chart"
        ]
    )

    assert (
        first_result[
            "day_master"
        ]
        == second_result[
            "day_master"
        ]
    )

    assert (
        first_result[
            "useful_gods"
        ][
            "method"
        ]
        == second_result[
            "useful_gods"
        ][
            "method"
        ]
        == "useful_gods_v3"
    )
