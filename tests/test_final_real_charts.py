"""
tests/test_final_real_charts.py

四柱推命エンジン v1.0 完成前の最終E2E回帰テスト。

目的:
    実命式を入口にして、

    四柱
    -> 蔵干 / 通変星 / 十二運
    -> 身強身弱
    -> 格局
    -> 用神
    -> 大運
    -> 現在大運
    -> 歳運
    -> 大運×歳運統合

    までのパイプライン全体が、
    互いに矛盾せず接続されていることを確認する。

方針:
- 既に検証済みの3命式を使う。
- target_datetime は固定し、テストを再現可能にする。
- 占術上まだ暫定のスコア値そのものを過剰固定しない。
- 一方で、既知の四柱・格局・バージョン・evidence整合性は固定する。
"""

from datetime import datetime, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from engine.chart import calculate_chart
from engine.integrated_luck import calculate_integrated_luck
from engine.solar_terms import get_solar_term_datetime


JST = ZoneInfo("Asia/Tokyo")

TARGET_DATETIME = datetime(
    2026,
    8,
    10,
    15,
    36,
)


REAL_CHART_CASES = [
    {
        "id": "1984_hokkaido_female_early_hour", "birth_date": "1984-07-22", "birth_time": "04:15", "birth_place": "北海道", "gender": "female",
        "pillars": {"year": "甲子", "month": "辛未", "day": "丁巳", "hour": "壬寅"}, "day_master": "丁",
        "pattern": "食神格", "technical_pattern": "eating_god",
        "candidate_pattern": "羊刃格", "candidate_technical_pattern": "yangren",
    },
    {
        "id": "1984_fukuoka_male_afternoon", "birth_date": "1984-07-22", "birth_time": "13:40", "birth_place": "福岡県", "gender": "male",
        "pillars": {"year": "甲子", "month": "辛未", "day": "丁巳", "hour": "丁未"}, "day_master": "丁",
        "pattern": "食神格", "technical_pattern": "eating_god",
        "candidate_pattern": "羊刃格", "candidate_technical_pattern": "yangren",
    },
    {
        "id": "1985_ishikawa_female_verified", "birth_date": "1985-07-17", "birth_time": "21:50", "birth_place": "石川県", "gender": "female",
        "pillars": {"year": "乙丑", "month": "癸未", "day": "丁巳", "hour": "辛亥"}, "day_master": "丁",
        "pattern": "偏印格", "technical_pattern": "indirect_resource",
        "candidate_pattern": "偏印格", "candidate_technical_pattern": "indirect_resource",
    },
]


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


def calculate_real_chart(case):
    request = make_request(
        birth_date=case["birth_date"],
        birth_time=case["birth_time"],
        birth_place=case["birth_place"],
        gender=case["gender"],
    )

    return calculate_chart(
        request,
        target_datetime=TARGET_DATETIME,
    )


@pytest.fixture(
    params=REAL_CHART_CASES,
    ids=[case["id"] for case in REAL_CHART_CASES],
)
def real_chart_case(request):
    return request.param


@pytest.fixture
def real_chart_result(real_chart_case):
    return calculate_real_chart(real_chart_case)


# ============================================================
# 1. Known pillars
# ============================================================


def test_final_real_chart_four_pillars(
    real_chart_case,
    real_chart_result,
):
    expected = real_chart_case["pillars"]
    chart = real_chart_result["chart"]

    assert chart["year"]["pillar"] == expected["year"]
    assert chart["month"]["pillar"] == expected["month"]
    assert chart["day"]["pillar"] == expected["day"]
    assert chart["hour"]["pillar"] == expected["hour"]


def test_final_real_chart_day_master(
    real_chart_case,
    real_chart_result,
):
    assert (
        real_chart_result["day_master"]["stem"]
        == real_chart_case["day_master"]
    )


def test_final_real_chart_day_master_matches_day_pillar(
    real_chart_result,
):
    assert (
        real_chart_result["day_master"]["stem"]
        == real_chart_result["chart"]["day"]["stem"]
    )


# ============================================================
# 2. Pillar internal consistency
# ============================================================


@pytest.mark.parametrize(
    "position",
    ["year", "month", "day", "hour"],
)
def test_final_real_chart_pillar_matches_stem_branch(
    real_chart_result,
    position,
):
    pillar = real_chart_result["chart"][position]

    assert pillar["pillar"] == (
        pillar["stem"] + pillar["branch"]
    )


@pytest.mark.parametrize(
    "position",
    ["year", "month", "day", "hour"],
)
def test_final_real_chart_hidden_stems_exist(
    real_chart_result,
    position,
):
    pillar = real_chart_result["chart"][position]

    assert isinstance(pillar["hidden_stems"], list)
    assert pillar["hidden_stems"]
    assert (
        pillar["main_hidden_stem"]
        in pillar["hidden_stems"]
    )


@pytest.mark.parametrize(
    "position",
    ["year", "month", "day", "hour"],
)
def test_final_real_chart_twelve_stage_exists(
    real_chart_result,
    position,
):
    stage = real_chart_result["chart"][position][
        "twelve_stage"
    ]

    assert isinstance(stage, str)
    assert stage


# ============================================================
# 3. Final strength judgment
# ============================================================


def test_final_real_chart_contains_final_strength(
    real_chart_result,
):
    judgment = real_chart_result[
        "final_strength_judgment"
    ]

    required = {
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

    assert isinstance(judgment, dict)
    assert required.issubset(judgment.keys())


def test_final_real_chart_strength_metadata(
    real_chart_result,
):
    judgment = real_chart_result[
        "final_strength_judgment"
    ]

    assert (
        judgment["method"]
        == "final_strength_judgment_v2"
    )
    assert (
        judgment["status"]
        == "provisional_final_strength_judgment_v2"
    )


def test_final_real_chart_strength_score_range(
    real_chart_result,
):
    score = real_chart_result[
        "final_strength_judgment"
    ]["final_score"]

    assert 0.0 <= score <= 100.0


def test_final_real_chart_strength_label_valid(
    real_chart_result,
):
    technical_label = real_chart_result[
        "final_strength_judgment"
    ]["technical_label"]

    assert technical_label in {
        "very_strong",
        "strong",
        "balanced",
        "weak",
        "very_weak",
    }


def test_final_real_chart_strength_confidence_valid(
    real_chart_result,
):
    confidence = real_chart_result[
        "final_strength_judgment"
    ]["confidence"]

    assert confidence in {
        "high",
        "medium",
        "low",
    }


def test_final_real_chart_no_root_double_count(
    real_chart_result,
):
    judgment = real_chart_result[
        "final_strength_judgment"
    ]

    assert judgment["root_adjustment"] == 0.0
    assert (
        judgment["double_count_prevention"][
            "root_reapplied"
        ]
        is False
    )


def test_final_real_chart_no_month_double_count(
    real_chart_result,
):
    judgment = real_chart_result[
        "final_strength_judgment"
    ]

    assert judgment["month_adjustment"] == 0.0
    assert (
        judgment["double_count_prevention"][
            "month_reapplied"
        ]
        is False
    )


def test_final_real_chart_strength_evidence_matches_pipeline(
    real_chart_result,
):
    evidence = real_chart_result[
        "final_strength_judgment"
    ]["evidence"]

    assert (
        evidence["weighted_strength_judgment"]
        == real_chart_result[
            "weighted_strength_judgment"
        ]
    )
    assert (
        evidence["weighted_root_strength"]
        == real_chart_result["weighted_root_strength"]
    )
    assert (
        evidence["integrated_month_strength"]
        == real_chart_result[
            "integrated_month_strength"
        ]
    )
    assert (
        evidence["branch_relations"]
        == real_chart_result[
            "branch_relation_strength"
        ]
    )
    assert (
        evidence["stem_transformation_judgment"]
        == real_chart_result[
            "stem_transformation_judgment"
        ]
    )


# ============================================================
# 4. Pattern
# ============================================================


def test_final_real_chart_pattern_judgment(
    real_chart_case,
    real_chart_result,
):
    judgment = real_chart_result[
        "pattern_judgment"
    ]

    assert (
        judgment["primary_pattern"]
        == real_chart_case["pattern"]
    )
    assert (
        judgment["technical_pattern"]
        == real_chart_case["technical_pattern"]
    )


def test_final_real_chart_pattern_metadata(
    real_chart_result,
):
    judgment = real_chart_result[
        "pattern_judgment"
    ]

    assert judgment["method"] == "pattern_judgment_v2"
    assert (
        judgment["status"]
        == "provisional_pattern_judgment_v2"
    )


def test_final_real_chart_pattern_candidate_consistency(real_chart_case, real_chart_result):
    candidate = real_chart_result["pattern_candidates"]["primary_candidate"]
    judgment = real_chart_result["pattern_judgment"]
    assert candidate["pattern"] == real_chart_case["candidate_pattern"]
    assert candidate["technical_pattern"] == real_chart_case["candidate_technical_pattern"]
    assert judgment["primary_pattern"] == real_chart_case["pattern"]
    assert judgment["technical_pattern"] == real_chart_case["technical_pattern"]
    # 候補抽出と成立判定は別レイヤーのため、常に同一とは限らない。

# ============================================================
# 5. Useful gods
# ============================================================


def test_final_real_chart_useful_gods_v3(
    real_chart_result,
):
    useful = real_chart_result["useful_gods"]

    assert useful["method"] == "useful_gods_v3"
    assert (
        useful["status"]
        == "provisional_useful_gods_v3"
    )


def test_final_real_chart_useful_gods_day_master_consistency(
    real_chart_result,
):
    useful = real_chart_result["useful_gods"]

    assert (
        useful["day_master_stem"]
        == real_chart_result["day_master"]["stem"]
    )


def test_final_real_chart_useful_gods_primary_matches_final_list(
    real_chart_result,
):
    useful = real_chart_result["useful_gods"]
    final_elements = useful["final_useful_elements"]

    if final_elements:
        assert (
            useful["primary_useful_element"]
            == final_elements[0]
        )
        assert useful["has_useful_candidate"] is True


def test_final_real_chart_useful_gods_candidate_priority(
    real_chart_result,
):
    candidates = real_chart_result[
        "useful_gods"
    ]["final_candidates"]

    priorities = [
        candidate["priority"]
        for candidate in candidates
    ]

    assert priorities == list(
        range(1, len(candidates) + 1)
    )


def test_final_real_chart_pattern_useful_evidence(
    real_chart_result,
):
    evidence = real_chart_result[
        "pattern_useful_gods"
    ]["evidence"]

    assert (
        evidence["pattern_judgment"]
        == real_chart_result["pattern_judgment"]
    )
    assert (
        evidence["weighted_five_elements"]
        == real_chart_result[
            "weighted_five_elements"
        ]
    )


# ============================================================
# 6. Luck pillars
# ============================================================


def test_final_real_chart_luck_pillars_v2(
    real_chart_result,
):
    luck = real_chart_result["luck_pillars"]

    assert luck["method"] == "luck_pillars_v2"
    assert (
        luck["status"]
        == "provisional_luck_pillars_v2"
    )
    assert luck["pillar_count"] == len(luck["pillars"])


def test_final_real_chart_luck_has_ten_pillars(
    real_chart_result,
):
    luck = real_chart_result["luck_pillars"]

    assert luck["pillar_count"] == 10
    assert len(luck["pillars"]) == 10


def test_final_real_chart_luck_pillar_indices_contiguous(
    real_chart_result,
):
    pillars = real_chart_result[
        "luck_pillars"
    ]["pillars"]

    assert [
        pillar["index"]
        for pillar in pillars
    ] == list(range(1, 11))


def test_final_real_chart_luck_age_ranges_connect(
    real_chart_result,
):
    pillars = real_chart_result[
        "luck_pillars"
    ]["pillars"]

    for current, nxt in zip(
        pillars,
        pillars[1:],
    ):
        assert (
            current["end_age"]
            == nxt["start_age"]
        )


def test_final_real_chart_luck_does_not_receive_current_flags(
    real_chart_result,
):
    for pillar in real_chart_result[
        "luck_pillars"
    ]["pillars"]:
        assert "is_current" not in pillar
        assert "is_previous" not in pillar
        assert "is_next" not in pillar


# ============================================================
# 7. Current luck
# ============================================================


def test_final_real_chart_current_luck_v1(
    real_chart_result,
):
    current = real_chart_result["current_luck"]

    assert current["method"] == "current_luck_v1"
    assert current["status"] in {
        "current_luck_resolved",
        "before_first_luck",
        "after_last_luck",
    }


def test_final_real_chart_current_luck_exists_for_2026(
    real_chart_result,
):
    current = real_chart_result["current_luck"]

    assert current["has_current_luck"] is True
    assert isinstance(
        current["current_luck_pillar"],
        dict,
    )


def test_final_real_chart_current_luck_pillar_belongs_to_luck_pillars(
    real_chart_result,
):
    current = real_chart_result[
        "current_luck"
    ]["current_luck_pillar"]

    luck_pillars = real_chart_result[
        "luck_pillars"
    ]["pillars"]

    assert current["ganzhi"] in {
        pillar["ganzhi"]
        for pillar in luck_pillars
    }


def test_final_real_chart_current_luck_progress_range(
    real_chart_result,
):
    progress = real_chart_result[
        "current_luck"
    ]["progress"]

    assert (
        0.0
        <= progress["progress_percent"]
        <= 100.0
    )


# ============================================================
# 8. Annual luck
# ============================================================


def test_final_real_chart_annual_luck_v1(
    real_chart_result,
):
    annual = real_chart_result["annual_luck"]
    assert annual["method"] == "annual_luck_v1"


def test_final_real_chart_2026_annual_luck(
    real_chart_result,
):
    annual = real_chart_result["annual_luck"]

    assert annual["year"] == 2026
    assert annual["ganzhi"] == "丙午"
    assert annual["stem"] == "丙"
    assert annual["branch"] == "午"


def test_final_real_chart_2026_annual_ten_god(
    real_chart_result,
):
    """
    現在の正式日柱基準では3命式とも日主は丁。
    2026年の天干は丙なので、丁日主に対する丙は劫財。
    """
    assert (
        real_chart_result["annual_luck"]["stem_ten_god"]
        == "劫財"
    )


def test_final_real_chart_2026_annual_twelve_stage(
    real_chart_result,
):
    """
    現在の正式日柱基準では3命式とも日主は丁。
    2026年の地支は午なので、丁×午の十二運は建禄。
    """
    assert (
        real_chart_result["annual_luck"]["twelve_stage"]
        == "建禄"
    )


def test_final_real_chart_annual_day_master_consistency(
    real_chart_result,
):
    annual = real_chart_result["annual_luck"]

    assert (
        annual["day_master_stem"]
        == real_chart_result["day_master"]["stem"]
    )


# ============================================================
# 9. Integrated luck
# ============================================================


def test_final_real_chart_integrated_luck_v1(
    real_chart_result,
):
    integrated = real_chart_result[
        "integrated_luck"
    ]

    assert integrated["method"] == "integrated_luck_v1"
    assert (
        integrated["status"]
        == "provisional_integrated_luck_v1"
    )


def test_final_real_chart_integrated_current_ganzhi_consistency(
    real_chart_result,
):
    assert (
        real_chart_result[
            "integrated_luck"
        ]["current_luck_ganzhi"]
        == real_chart_result[
            "current_luck"
        ]["current_luck_pillar"]["ganzhi"]
    )


def test_final_real_chart_integrated_annual_ganzhi_consistency(
    real_chart_result,
):
    assert (
        real_chart_result[
            "integrated_luck"
        ]["annual_luck_ganzhi"]
        == real_chart_result[
            "annual_luck"
        ]["ganzhi"]
    )


def test_final_real_chart_integrated_current_elements_consistency(
    real_chart_result,
):
    current_pillar = real_chart_result[
        "current_luck"
    ]["current_luck_pillar"]

    elements = real_chart_result[
        "integrated_luck"
    ]["current_luck_elements"]

    assert (
        elements["stem"]
        == current_pillar["stem_element"]
    )
    assert (
        elements["branch"]
        == current_pillar["branch_element"]
    )


def test_final_real_chart_integrated_annual_elements_consistency(
    real_chart_result,
):
    annual = real_chart_result["annual_luck"]
    elements = real_chart_result[
        "integrated_luck"
    ]["annual_luck_elements"]

    assert elements["stem"] == annual["stem_element"]
    assert elements["branch"] == annual["branch_element"]


def test_final_real_chart_integrated_score_sum(
    real_chart_result,
):
    integrated = real_chart_result[
        "integrated_luck"
    ]
    score = integrated["score"]

    expected = (
        score["element_interaction_score"]
        + score["current_luck_useful_score"]
        + score["annual_luck_useful_score"]
    )

    assert score["total_score"] == expected
    assert integrated["overall_score"] == score["total_score"]


def test_final_real_chart_integrated_level_valid(
    real_chart_result,
):
    assert (
        real_chart_result[
            "integrated_luck"
        ]["overall_level"]
        in {
            "very_supportive",
            "supportive",
            "mixed",
            "challenging",
            "very_challenging",
        }
    )


def test_final_real_chart_integrated_confidence_valid(
    real_chart_result,
):
    confidence = real_chart_result[
        "integrated_luck"
    ]["confidence"]

    assert confidence["level"] in {
        "high",
        "medium",
        "low",
    }
    assert (
        0
        <= confidence["available_sources"]
        <= confidence["total_sources"]
    )


def test_final_real_chart_integrated_matches_direct_engine(
    real_chart_result,
):
    expected = calculate_integrated_luck(
        current_luck=real_chart_result[
            "current_luck"
        ],
        annual_luck=real_chart_result[
            "annual_luck"
        ],
        useful_gods=real_chart_result[
            "useful_gods"
        ],
    )

    assert (
        real_chart_result["integrated_luck"]
        == expected
    )


# ============================================================
# 10. Evidence chain
# ============================================================


def test_final_real_chart_integrated_evidence_consistency(
    real_chart_result,
):
    integrated = real_chart_result[
        "integrated_luck"
    ]
    evidence = integrated["evidence"]

    assert (
        evidence["current_luck_ganzhi"]
        == integrated["current_luck_ganzhi"]
    )
    assert (
        evidence["annual_luck_ganzhi"]
        == integrated["annual_luck_ganzhi"]
    )
    assert evidence["score"] == integrated["score"]


def test_final_real_chart_annual_evidence_consistency(
    real_chart_result,
):
    annual = real_chart_result["annual_luck"]
    evidence = annual["evidence"]

    assert evidence["ganzhi"] == annual["ganzhi"]
    assert (
        evidence["day_master_stem"]
        == annual["day_master_stem"]
    )
    assert (
        evidence["stem_ten_god"]
        == annual["stem_ten_god"]
    )
    assert (
        evidence["twelve_stage"]
        == annual["twelve_stage"]
    )


# ============================================================
# 11. Reasoning / notes
# ============================================================


def test_final_real_chart_reasoning_layers_exist(
    real_chart_result,
):
    annual_reasoning = real_chart_result[
        "annual_luck"
    ]["reasoning"]
    integrated_reasoning = real_chart_result[
        "integrated_luck"
    ]["reasoning"]

    assert isinstance(annual_reasoning, list)
    assert annual_reasoning
    assert isinstance(integrated_reasoning, list)
    assert integrated_reasoning


def test_final_real_chart_notes_exist(
    real_chart_result,
):
    for key in [
        "final_strength_judgment",
        "pattern_judgment",
        "useful_gods",
        "luck_pillars",
        "current_luck",
        "annual_luck",
        "integrated_luck",
    ]:
        notes = real_chart_result[key]["notes"]

        assert isinstance(notes, list)
        assert notes


# ============================================================
# 12. Fixed target reproducibility
# ============================================================


def test_final_real_chart_fixed_target_reproducible(
    real_chart_case,
):
    first = calculate_real_chart(real_chart_case)
    second = calculate_real_chart(real_chart_case)

    for key in [
        "chart",
        "final_strength_judgment",
        "useful_gods",
        "luck_pillars",
        "current_luck",
        "annual_luck",
        "integrated_luck",
    ]:
        assert first[key] == second[key]


# ============================================================
# 13. JST-aware regression
# ============================================================


def test_final_verified_chart_accepts_jst_aware_target():
    request = make_request(
        birth_date="1985-07-17",
        birth_time="21:50",
        birth_place="石川県",
        gender="female",
    )

    target = datetime(
        2026,
        8,
        10,
        15,
        36,
        tzinfo=JST,
    )

    result = calculate_chart(
        request,
        target_datetime=target,
    )

    assert result["annual_luck"]["ganzhi"] == "丙午"
    assert result["current_luck"]["method"] == "current_luck_v1"
    assert result["integrated_luck"]["method"] == "integrated_luck_v1"


# ============================================================
# 14. Lichun boundary regression
# ============================================================


def test_final_verified_chart_before_lichun_uses_previous_year():
    """
    天文学的に求めた2026年立春の1秒前は、
    まだ2025年の歳運（乙巳）として扱う。
    """
    request = make_request(
        birth_date="1985-07-17",
        birth_time="21:50",
        birth_place="石川県",
        gender="female",
    )

    lichun = get_solar_term_datetime(
        2026,
        "立春",
    )

    result = calculate_chart(
        request,
        target_datetime=(
            lichun - timedelta(seconds=1)
        ),
    )

    assert result["annual_luck"]["effective_year"] == 2025
    assert result["annual_luck"]["ganzhi"] == "乙巳"
    assert (
        result["integrated_luck"]["annual_luck_ganzhi"]
        == "乙巳"
    )


def test_final_verified_chart_at_lichun_uses_new_year():
    """
    天文学的な立春時刻ちょうどから、
    2026年の歳運（丙午）として扱う。
    """
    request = make_request(
        birth_date="1985-07-17",
        birth_time="21:50",
        birth_place="石川県",
        gender="female",
    )

    lichun = get_solar_term_datetime(
        2026,
        "立春",
    )

    result = calculate_chart(
        request,
        target_datetime=lichun,
    )

    assert result["annual_luck"]["effective_year"] == 2026
    assert result["annual_luck"]["ganzhi"] == "丙午"
    assert (
        result["integrated_luck"]["annual_luck_ganzhi"]
        == "丙午"
    )


def test_final_verified_chart_after_lichun_uses_new_year():
    """
    天文学的に求めた2026年立春の1秒後も、
    2026年の歳運（丙午）として扱う。
    """
    request = make_request(
        birth_date="1985-07-17",
        birth_time="21:50",
        birth_place="石川県",
        gender="female",
    )

    lichun = get_solar_term_datetime(
        2026,
        "立春",
    )

    result = calculate_chart(
        request,
        target_datetime=(
            lichun + timedelta(seconds=1)
        ),
    )

    assert result["annual_luck"]["effective_year"] == 2026
    assert result["annual_luck"]["ganzhi"] == "丙午"


# ============================================================
# 15. Final representative E2E regression
# ============================================================


def test_final_verified_1985_end_to_end():
    request = make_request(
        birth_date="1985-07-17",
        birth_time="21:50",
        birth_place="石川県",
        gender="female",
    )

    result = calculate_chart(
        request,
        target_datetime=TARGET_DATETIME,
    )

    assert result["chart"]["year"]["pillar"] == "乙丑"
    assert result["chart"]["month"]["pillar"] == "癸未"
    assert result["chart"]["day"]["pillar"] == "丁巳"
    assert result["chart"]["hour"]["pillar"] == "辛亥"
    assert result["day_master"]["stem"] == "丁"

    assert (
        result["final_strength_judgment"]["method"]
        == "final_strength_judgment_v2"
    )
    assert result["pattern_judgment"]["primary_pattern"] == "偏印格"
    assert (
        result["pattern_judgment"]["technical_pattern"]
        == "indirect_resource"
    )
    assert result["useful_gods"]["method"] == "useful_gods_v3"
    assert result["luck_pillars"]["method"] == "luck_pillars_v2"
    assert result["current_luck"]["method"] == "current_luck_v1"
    assert result["annual_luck"]["ganzhi"] == "丙午"
    assert result["annual_luck"]["stem_ten_god"] == "劫財"
    assert result["integrated_luck"]["method"] == "integrated_luck_v1"
    assert result["integrated_luck"]["annual_luck_ganzhi"] == "丙午"
