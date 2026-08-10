from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from engine.annual_luck import (
    calculate_annual_luck_for_datetime,
)
from engine.chart import calculate_chart


JST = ZoneInfo("Asia/Tokyo")


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


def make_verified_request():
    """
    統合テストで使用する共通リクエストを返します。
    """
    return make_request(
        birth_date="1985-07-17",
        birth_time="21:50",
        birth_place="石川県",
        gender="female",
    )


def test_chart_1984_early_hour():
    request = make_request(
        birth_date="1984-07-22",
        birth_time="04:15",
        birth_place="北海道",
        gender="female",
    )

    result = calculate_chart(request)

    assert result["chart"]["year"]["pillar"] == "甲子"
    assert result["chart"]["month"]["pillar"] == "辛未"
    assert result["chart"]["day"]["pillar"] == "乙巳"
    assert result["chart"]["hour"]["pillar"] == "戊寅"
    assert result["day_master"]["stem"] == "乙"


def test_chart_1984_afternoon():
    request = make_request(
        birth_date="1984-07-22",
        birth_time="13:40",
        birth_place="福岡県",
        gender="male",
    )

    result = calculate_chart(request)

    assert result["chart"]["year"]["pillar"] == "甲子"
    assert result["chart"]["month"]["pillar"] == "辛未"
    assert result["chart"]["day"]["pillar"] == "乙巳"
    assert result["chart"]["hour"]["pillar"] == "癸未"


def test_chart_1985():
    request = make_verified_request()

    result = calculate_chart(request)

    assert result["chart"]["year"]["pillar"] == "乙丑"
    assert result["chart"]["month"]["pillar"] == "癸未"
    assert result["chart"]["day"]["pillar"] == "乙巳"
    assert result["chart"]["hour"]["pillar"] == "丁亥"


def test_chart_without_birth_time():
    request = make_request(
        birth_date="1984-07-22",
        birth_time=None,
        birth_place="東京都",
        gender="male",
    )

    result = calculate_chart(request)

    assert result["chart"]["year"]["pillar"] == "甲子"
    assert result["chart"]["month"]["pillar"] == "辛未"
    assert result["chart"]["day"]["pillar"] == "乙巳"
    assert result["chart"]["hour"] is None

    assert any(
        "出生時間が不明" in warning
        for warning in result["warnings"]
    )


def test_chart_contains_hidden_stems_and_ten_gods():
    request = make_verified_request()

    result = calculate_chart(request)
    chart = result["chart"]

    assert chart["year"]["stem_ten_god"] == "比肩"
    assert chart["year"]["hidden_stems"] == [
        "己",
        "癸",
        "辛",
    ]
    assert chart["year"]["main_hidden_stem"] == "己"
    assert (
        chart["year"]["main_hidden_stem_ten_god"]
        == "偏財"
    )

    assert chart["month"]["stem_ten_god"] == "偏印"
    assert chart["month"]["hidden_stems"] == [
        "己",
        "丁",
        "乙",
    ]
    assert chart["month"]["main_hidden_stem"] == "己"
    assert (
        chart["month"]["main_hidden_stem_ten_god"]
        == "偏財"
    )

    assert chart["day"]["stem_ten_god"] is None
    assert chart["day"]["hidden_stems"] == [
        "丙",
        "戊",
        "庚",
    ]
    assert chart["day"]["main_hidden_stem"] == "丙"
    assert (
        chart["day"]["main_hidden_stem_ten_god"]
        == "傷官"
    )

    assert chart["hour"]["stem_ten_god"] == "食神"
    assert chart["hour"]["hidden_stems"] == [
        "壬",
        "甲",
    ]
    assert chart["hour"]["main_hidden_stem"] == "壬"
    assert (
        chart["hour"]["main_hidden_stem_ten_god"]
        == "印綬"
    )


def test_chart_contains_twelve_stages():
    request = make_verified_request()

    result = calculate_chart(request)
    chart = result["chart"]

    assert chart["year"]["twelve_stage"] == "衰"
    assert chart["month"]["twelve_stage"] == "養"
    assert chart["day"]["twelve_stage"] == "沐浴"
    assert chart["hour"]["twelve_stage"] == "死"


def test_chart_contains_five_elements():
    request = make_verified_request()

    result = calculate_chart(request)
    five_elements = result["five_elements"]

    assert five_elements["counts"] == {
        "木": 4,
        "火": 4,
        "土": 5,
        "金": 2,
        "水": 4,
    }

    assert five_elements["percentages"] == {
        "木": 21.05,
        "火": 21.05,
        "土": 26.32,
        "金": 10.53,
        "水": 21.05,
    }

    assert five_elements["total"] == 19

    assert (
        five_elements["method"]
        == "simple_count_v1"
    )


def test_chart_contains_weighted_five_elements():
    request = make_verified_request()

    result = calculate_chart(request)
    weighted = result["weighted_five_elements"]

    assert weighted["scores"] == {
        "木": 2.4,
        "火": 1.9,
        "土": 1.5,
        "金": 0.2,
        "水": 2.0,
    }

    assert weighted["percentages"] == {
        "木": 30.0,
        "火": 23.75,
        "土": 18.75,
        "金": 2.5,
        "水": 25.0,
    }

    assert weighted["total"] == 8.0

    assert (
        weighted["method"]
        == "weighted_hidden_stems_v1"
    )


def test_chart_contains_day_master_balance():
    request = make_verified_request()

    result = calculate_chart(request)
    balance = result["day_master_balance"]

    assert balance["day_stem"] == "乙"
    assert balance["day_element"] == "木"

    assert balance["supporting_elements"] == [
        "木",
        "水",
    ]

    assert balance["draining_elements"] == [
        "火",
        "土",
        "金",
    ]

    assert balance["supporting_score"] == 8
    assert balance["draining_score"] == 11
    assert balance["supporting_ratio"] == 42.11
    assert balance["draining_ratio"] == 57.89

    assert (
        balance["method"]
        == "simple_element_relation_v1"
    )

    assert (
        balance["status"]
        == "classification_only"
    )


def test_chart_contains_weighted_day_master_balance():
    request = make_verified_request()

    result = calculate_chart(request)

    balance = result[
        "weighted_day_master_balance"
    ]

    assert balance["day_stem"] == "乙"
    assert balance["day_element"] == "木"

    assert balance["supporting_elements"] == [
        "木",
        "水",
    ]

    assert balance["draining_elements"] == [
        "火",
        "土",
        "金",
    ]

    assert balance["supporting_score"] == 4.4
    assert balance["draining_score"] == 3.6
    assert balance["supporting_ratio"] == 55.0
    assert balance["draining_ratio"] == 45.0

    assert (
        balance["method"]
        == "weighted_element_relation_v1"
    )

    assert (
        balance["status"]
        == "provisional_weighted_classification"
    )


def test_chart_contains_root_strength():
    request = make_verified_request()

    result = calculate_chart(request)
    root_strength = result["root_strength"]

    assert root_strength["day_stem"] == "乙"
    assert root_strength["day_element"] == "木"
    assert root_strength["has_root"] is True
    assert root_strength["root_count"] == 2

    assert root_strength["root_positions"] == [
        "month",
        "hour",
    ]

    assert root_strength["roots"] == [
        {
            "position": "month",
            "branch": "未",
            "root_stems": ["乙"],
            "root_count": 1,
        },
        {
            "position": "hour",
            "branch": "亥",
            "root_stems": ["甲"],
            "root_count": 1,
        },
    ]

    assert (
        root_strength["method"]
        == "hidden_stem_root_v1"
    )

    assert (
        root_strength["status"]
        == "simple_root_detection"
    )


def test_chart_contains_weighted_root_strength():
    request = make_verified_request()

    result = calculate_chart(request)

    weighted_root = result[
        "weighted_root_strength"
    ]

    assert weighted_root["day_stem"] == "乙"
    assert weighted_root["day_element"] == "木"
    assert weighted_root["has_root"] is True
    assert weighted_root["root_count"] == 2

    assert (
        weighted_root["total_root_score"]
        == 0.45
    )

    assert weighted_root["root_positions"] == [
        "month",
        "hour",
    ]

    assert weighted_root["roots"] == [
        {
            "position": "month",
            "branch": "未",
            "stem": "乙",
            "hidden_stem_rank": 3,
            "position_weight": 1.5,
            "hidden_stem_weight": 0.1,
            "root_score": 0.15,
        },
        {
            "position": "hour",
            "branch": "亥",
            "stem": "甲",
            "hidden_stem_rank": 2,
            "position_weight": 1.0,
            "hidden_stem_weight": 0.3,
            "root_score": 0.3,
        },
    ]

    assert (
        weighted_root["method"]
        == "weighted_root_strength_v1"
    )

    assert (
        weighted_root["status"]
        == "provisional_weighted_roots"
    )


def test_chart_contains_month_command():
    request = make_verified_request()

    result = calculate_chart(request)
    month_command = result["month_command"]

    assert month_command["day_stem"] == "乙"
    assert month_command["day_element"] == "木"
    assert month_command["month_branch"] == "未"
    assert month_command["month_element"] == "土"

    assert (
        month_command["relationship"]
        == "wealth"
    )

    assert (
        month_command["relationship_label"]
        == "財星"
    )

    assert month_command["effect"] == "draining"

    assert (
        month_command["supports_day_master"]
        is False
    )

    assert (
        month_command["method"]
        == "month_branch_element_v1"
    )

    assert (
        month_command["status"]
        == "provisional_month_command"
    )


def test_chart_contains_seasonal_strength():
    request = make_verified_request()

    result = calculate_chart(request)

    seasonal_strength = result[
        "seasonal_strength"
    ]

    assert seasonal_strength["day_stem"] == "乙"
    assert seasonal_strength["day_element"] == "木"
    assert seasonal_strength["month_branch"] == "未"
    assert seasonal_strength["state"] == "囚"
    assert seasonal_strength["score"] == -6.0

    assert (
        seasonal_strength["method"]
        == "seasonal_state_v1"
    )

    assert (
        seasonal_strength["status"]
        == "provisional_seasonal_strength"
    )


def test_chart_contains_strength_judgment():
    request = make_verified_request()

    result = calculate_chart(request)
    judgment = result["strength_judgment"]

    assert (
        judgment["label"]
        == "中和～やや身弱寄り"
    )

    assert judgment["final_score"] == 45.11

    assert (
        judgment["base_supporting_ratio"]
        == 42.11
    )

    assert judgment["adjustments"] == {
        "root_bonus": 6.0,
        "month_root_bonus": 5.0,
        "month_command_adjustment": -8.0,
    }

    assert (
        judgment["method"]
        == "provisional_strength_v1"
    )

    assert (
        judgment["status"]
        == "provisional_judgment"
    )


def test_chart_contains_weighted_strength_judgment():
    request = make_verified_request()

    result = calculate_chart(request)

    judgment = result[
        "weighted_strength_judgment"
    ]

    assert (
        judgment["label"]
        == "やや身強寄り"
    )

    # V3:
    # 55.0 + 4.5 - 9.2 = 50.3
    assert judgment["final_score"] == 50.3

    assert (
        judgment["base_supporting_ratio"]
        == 55.0
    )

    assert judgment["adjustments"] == {
        "weighted_root_bonus": 4.5,
        "integrated_month_adjustment": -9.2,
    }

    assert (
        judgment["evidence"][
            "total_root_score"
        ]
        == 0.45
    )

    assert (
        judgment["evidence"][
            "integrated_month_score"
        ]
        == -9.2
    )

    assert (
        judgment["evidence"][
            "seasonal_state"
        ]
        == "囚"
    )

    assert (
        judgment["evidence"][
            "seasonal_score"
        ]
        == -6.0
    )

    assert (
        judgment["evidence"][
            "month_supporting_ratio"
        ]
        == 10.0
    )

    assert (
        judgment["evidence"][
            "month_draining_ratio"
        ]
        == 90.0
    )

    assert (
        judgment["evidence"][
            "hidden_stem_balance"
        ]
        == -0.8
    )

    assert (
        judgment["evidence"][
            "hidden_stem_adjustment"
        ]
        == -3.2
    )

    assert (
        judgment["method"]
        == "weighted_provisional_strength_v3"
    )

    assert (
        judgment["status"]
        == "provisional_weighted_judgment"
    )


def test_chart_contains_weighted_month_command():
    request = make_verified_request()

    result = calculate_chart(request)

    weighted_month_command = result[
        "weighted_month_command"
    ]

    assert weighted_month_command[
        "day_stem"
    ] == "乙"

    assert weighted_month_command[
        "day_element"
    ] == "木"

    assert weighted_month_command[
        "month_branch"
    ] == "未"

    assert weighted_month_command[
        "supporting_score"
    ] == 0.1

    assert weighted_month_command[
        "draining_score"
    ] == 0.9

    assert weighted_month_command[
        "supporting_ratio"
    ] == 10.0

    assert weighted_month_command[
        "draining_ratio"
    ] == 90.0

    assert weighted_month_command["details"] == [
        {
            "stem": "己",
            "element": "土",
            "weight": 0.6,
            "supports_day_master": False,
        },
        {
            "stem": "丁",
            "element": "火",
            "weight": 0.3,
            "supports_day_master": False,
        },
        {
            "stem": "乙",
            "element": "木",
            "weight": 0.1,
            "supports_day_master": True,
        },
    ]

    assert (
        weighted_month_command["method"]
        == "weighted_month_command_v1"
    )

    assert (
        weighted_month_command["status"]
        == "provisional_weighted_month_command"
    )


def test_chart_contains_integrated_month_strength():
    request = make_verified_request()

    result = calculate_chart(request)

    integrated = result[
        "integrated_month_strength"
    ]

    assert (
        integrated["seasonal_state"]
        == "囚"
    )

    assert integrated["seasonal_score"] == -6.0

    assert (
        integrated["supporting_ratio"]
        == 10.0
    )

    assert (
        integrated["draining_ratio"]
        == 90.0
    )

    assert (
        integrated["hidden_stem_balance"]
        == -0.8
    )

    assert (
        integrated["hidden_stem_adjustment"]
        == -3.2
    )

    assert (
        integrated["integrated_score"]
        == -9.2
    )

    assert (
        integrated["method"]
        == "integrated_month_strength_v1"
    )

    assert (
        integrated["status"]
        == "provisional_integrated_month_strength"
    )
def test_chart_contains_branch_clashes():
    request = make_verified_request()

    result = calculate_chart(request)

    branch_clashes = result[
        "branch_clashes"
    ]

    assert (
        branch_clashes["has_clash"]
        is True
    )

    assert (
        branch_clashes["clash_count"]
        == 2
    )

    assert branch_clashes["clashes"] == [
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
        branch_clashes["method"]
        == "branch_clash_v1"
    )

    assert (
        branch_clashes["status"]
        == "detected_branch_clashes"
    )


def test_chart_contains_branch_combinations():
    request = make_verified_request()

    result = calculate_chart(request)

    branch_combinations = result[
        "branch_combinations"
    ]

    assert (
        branch_combinations["has_combination"]
        is False
    )

    assert (
        branch_combinations["combination_count"]
        == 0
    )

    assert (
        branch_combinations["combinations"]
        == []
    )

    assert (
        branch_combinations["method"]
        == "branch_combination_v1"
    )

    assert (
        branch_combinations["status"]
        == "detected_branch_combinations"
    )


def test_chart_contains_branch_trines():
    request = make_verified_request()

    result = calculate_chart(request)

    branch_trines = result[
        "branch_trines"
    ]

    assert (
        branch_trines["has_trine"]
        is False
    )

    assert (
        branch_trines["trine_count"]
        == 0
    )

    assert (
        branch_trines["trines"]
        == []
    )

    assert (
        branch_trines["method"]
        == "branch_trine_v1"
    )

    assert (
        branch_trines["status"]
        == "detected_branch_trines"
    )


def test_chart_contains_branch_punishments():
    request = make_verified_request()

    result = calculate_chart(request)

    branch_punishments = result[
        "branch_punishments"
    ]

    assert (
        branch_punishments["has_punishment"]
        is False
    )

    assert (
        branch_punishments["punishment_count"]
        == 0
    )

    assert (
        branch_punishments["punishments"]
        == []
    )

    assert (
        branch_punishments["method"]
        == "branch_punishment_v1"
    )

    assert (
        branch_punishments["status"]
        == "detected_branch_punishments"
    )


def test_chart_contains_branch_harms():
    request = make_verified_request()

    result = calculate_chart(request)

    branch_harms = result[
        "branch_harms"
    ]

    assert branch_harms["has_harm"] is False
    assert branch_harms["harm_count"] == 0
    assert branch_harms["harms"] == []

    assert (
        branch_harms["method"]
        == "branch_harm_v1"
    )

    assert (
        branch_harms["status"]
        == "detected_branch_harms"
    )

def test_chart_contains_branch_breaks():
    request = make_verified_request()

    result = calculate_chart(request)

    branch_breaks = result[
        "branch_breaks"
    ]

    assert (
        branch_breaks["has_break"]
        is False
    )

    assert (
        branch_breaks["break_count"]
        == 0
    )

    assert (
        branch_breaks["breaks"]
        == []
    )

    assert (
        branch_breaks["method"]
        == "branch_break_v1"
    )

    assert (
        branch_breaks["status"]
        == "detected_branch_breaks"
    )


def test_chart_contains_branch_relation_strength():
    """
    calculate_chart() の結果に
    地支関係の総合強度が含まれることを確認します。
    """
    request = make_verified_request()

    result = calculate_chart(request)

    relation_strength = result[
        "branch_relation_strength"
    ]

    # 検証命式:
    # 年支 丑 / 月支 未 / 日支 巳 / 時支 亥
    #
    # 冲:
    # 丑-未
    # 巳-亥
    #
    # その他:
    # 六合 0
    # 三合 0
    # 刑   0
    # 害   0
    # 破   0
    assert (
        relation_strength["total_relation_count"]
        == 2
    )

    assert (
        relation_strength["positive_score"]
        == 0.0
    )

    assert (
        relation_strength["negative_score"]
        == 4.0
    )

    assert (
        relation_strength["total_score"]
        == -4.0
    )

    assert (
        relation_strength["balance"]
        == "negative"
    )

    assert relation_strength["details"]["clash"] == {
        "count": 2,
        "weight": -2.0,
        "score": -4.0,
    }

    assert (
        relation_strength["details"]["combination"]
        == {
            "count": 0,
            "weight": 1.5,
            "score": 0.0,
        }
    )

    assert relation_strength["details"]["trine"] == {
        "count": 0,
        "weight": 2.5,
        "score": 0.0,
    }

    assert (
        relation_strength["details"]["punishment"]
        == {
            "count": 0,
            "weight": -1.5,
            "score": 0.0,
        }
    )

    assert relation_strength["details"]["harm"] == {
        "count": 0,
        "weight": -1.0,
        "score": 0.0,
    }

    assert relation_strength["details"]["break"] == {
        "count": 0,
        "weight": -0.5,
        "score": 0.0,
    }

    assert relation_strength["weights"] == {
        "clash": -2.0,
        "combination": 1.5,
        "trine": 2.5,
        "punishment": -1.5,
        "harm": -1.0,
        "break": -0.5,
    }

    assert (
        relation_strength["method"]
        == "branch_relation_strength_v1"
    )

    assert (
        relation_strength["status"]
        == "provisional_branch_relation_strength"
    )

    assert isinstance(
        relation_strength["notes"],
        list,
    )

    assert len(
        relation_strength["notes"]
    ) >= 1
    def test_chart_contains_stem_combinations():
        request = make_verified_request()
    
        result = calculate_chart(request)
    
        stem_combinations = result[
            "stem_combinations"
        ]
    
        assert (
            stem_combinations["has_combination"]
            is False
        )
    
        assert (
            stem_combinations["combination_count"]
            == 0
        )
    
        assert (
            stem_combinations["combinations"]
            == []
        )
    
        assert (
            stem_combinations["method"]
            == "stem_combination_v1"
        )
    
        assert (
            stem_combinations["status"]
            == "detected_stem_combinations"
        )
    
        assert isinstance(
            stem_combinations["notes"],
            list,
        )
    
        assert len(
            stem_combinations["notes"]
        ) >= 1
def test_chart_contains_stem_transformations():
        request = make_verified_request()
    
        result = calculate_chart(request)
    
        stem_transformations = result[
            "stem_transformations"
        ]
    
        assert (
            stem_transformations[
                "has_stem_combination"
            ]
            is False
        )
    
        assert (
            stem_transformations[
                "transformation_count"
            ]
            == 0
        )
    
        assert (
            stem_transformations[
                "possible_count"
            ]
            == 0
        )
    
        assert (
            stem_transformations[
                "unsupported_count"
            ]
            == 0
        )
    
        assert (
            stem_transformations[
                "overall_status"
            ]
            == "not_applicable"
        )
    
        assert (
            stem_transformations[
                "transformations"
            ]
            == []
        )
    
        assert (
            stem_transformations[
                "method"
            ]
            == "stem_transformation_v1"
        )
    
        assert (
            stem_transformations[
                "status"
            ]
            == "provisional_stem_transformation"
        )
    
        assert isinstance(
            stem_transformations["notes"],
            list,
        )
    
        assert (
            len(
                stem_transformations["notes"]
            )
            >= 1
        )
def test_chart_contains_transformation_roots():
        request = make_verified_request()
    
        result = calculate_chart(request)
    
        transformation_roots = result[
            "transformation_roots"
        ]
    
        assert (
            transformation_roots[
                "has_transformation_candidate"
            ]
            is False
        )
    
        assert (
            transformation_roots[
                "transformation_count"
            ]
            == 0
        )
    
        assert (
            transformation_roots[
                "rooted_count"
            ]
            == 0
        )
    
        assert (
            transformation_roots[
                "month_rooted_count"
            ]
            == 0
        )
    
        assert (
            transformation_roots[
                "overall_root_status"
            ]
            == "not_applicable"
        )
    
        assert (
            transformation_roots[
                "results"
            ]
            == []
        )
    
        assert (
            transformation_roots[
                "method"
            ]
            == "transformation_roots_v1"
        )
    
        assert (
            transformation_roots[
                "status"
            ]
            == "provisional_transformation_roots"
        )
    
        assert isinstance(
            transformation_roots["notes"],
            list,
        )
    
        assert (
            len(
                transformation_roots["notes"]
            )
            >= 1
        )
def test_chart_contains_transformation_exposures():
        request = make_verified_request()
    
        result = calculate_chart(request)
    
        transformation_exposures = result[
            "transformation_exposures"
        ]
    
        assert (
            transformation_exposures[
                "has_transformation_candidate"
            ]
            is False
        )
    
        assert (
            transformation_exposures[
                "transformation_count"
            ]
            == 0
        )
    
        assert (
            transformation_exposures[
                "exposed_count"
            ]
            == 0
        )
    
        assert (
            transformation_exposures[
                "external_exposed_count"
            ]
            == 0
        )
    
        assert (
            transformation_exposures[
                "overall_exposure_status"
            ]
            == "not_applicable"
        )
    
        assert (
            transformation_exposures[
                "results"
            ]
            == []
        )
    
        assert (
            transformation_exposures[
                "method"
            ]
            == "transformation_exposures_v1"
        )
    
        assert (
            transformation_exposures[
                "status"
            ]
            == "provisional_transformation_exposures"
        )
    
        assert isinstance(
            transformation_exposures["notes"],
            list,
        )
    
        assert (
            len(
                transformation_exposures["notes"]
            )
            >= 1
        )
def test_chart_contains_stem_transformation_judgment():
        request = make_verified_request()
    
        result = calculate_chart(request)
    
        judgment = result[
            "stem_transformation_judgment"
        ]
    
        assert (
            judgment[
                "has_transformation_candidate"
            ]
            is False
        )
    
        assert (
            judgment["judgment_count"]
            == 0
        )
    
        assert (
            judgment[
                "strong_candidate_count"
            ]
            == 0
        )
    
        assert (
            judgment["possible_count"]
            == 0
        )
    
        assert (
            judgment["weak_count"]
            == 0
        )
    
        assert (
            judgment["unsupported_count"]
            == 0
        )

        assert (
            judgment[
                "conflicted_judgment_count"
            ]
            == 0
        )

        assert (
            judgment[
                "high_conflict_count"
            ]
            == 0
        )

        assert (
            judgment[
                "medium_conflict_count"
            ]
            == 0
        )

        assert (
            judgment[
                "low_conflict_count"
            ]
            == 0
        )
    
        assert (
            judgment["overall_judgment"]
            == "not_applicable"
        )
    
        assert (
            judgment["judgments"]
            == []
        )
    
        assert (
            judgment["method"]
            == "stem_transformation_judgment_v3"
        )
    
        assert (
            judgment["status"]
            == "provisional_stem_transformation_judgment"
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
def test_chart_contains_stem_combination_conflicts():
        request = make_verified_request()
    
        result = calculate_chart(request)
    
        conflicts = result[
            "stem_combination_conflicts"
        ]
    
        assert (
            conflicts[
                "has_stem_combination"
            ]
            is False
        )
    
        assert (
            conflicts[
                "combination_count"
            ]
            == 0
        )
    
        assert (
            conflicts[
                "has_conflict"
            ]
            is False
        )
    
        assert (
            conflicts[
                "conflict_count"
            ]
            == 0
        )
    
        assert (
            conflicts[
                "position_conflict_count"
            ]
            == 0
        )
    
        assert (
            conflicts[
                "duplicate_combination_count"
            ]
            == 0
        )
    
        assert (
            conflicts[
                "position_conflicts"
            ]
            == []
        )
    
        assert (
            conflicts[
                "duplicate_combinations"
            ]
            == []
        )
    
        assert (
            conflicts[
                "overall_status"
            ]
            == "not_applicable"
        )
    
        assert (
            conflicts[
                "method"
            ]
            == "stem_combination_conflict_v1"
        )
    
        assert (
            conflicts[
                "status"
            ]
            == "detected_stem_combination_conflicts"
        )
    
        assert isinstance(
            conflicts["notes"],
            list,
        )
    
        assert len(
            conflicts["notes"]
        ) >= 1


def test_chart_contains_stem_combination_conflict_types():
    request = make_verified_request()

    result = calculate_chart(request)

    conflict_types = result[
        "stem_combination_conflict_types"
    ]

    assert (
        conflict_types[
            "has_typed_conflict"
        ]
        is False
    )

    assert (
        conflict_types[
            "typed_conflict_count"
        ]
        == 0
    )

    assert (
        conflict_types[
            "position_conflict_count"
        ]
        == 0
    )

    assert (
        conflict_types[
            "duplicate_conflict_count"
        ]
        == 0
    )

    assert (
        conflict_types[
            "争合_candidate_count"
        ]
        == 0
    )

    assert (
        conflict_types[
            "multiple_conflict_count"
        ]
        == 0
    )

    assert (
        conflict_types[
            "unclassified_count"
        ]
        == 0
    )

    assert (
        conflict_types[
            "severity_counts"
        ]
        == {
            "high": 0,
            "medium": 0,
            "low": 0,
        }
    )

    assert (
        conflict_types[
            "overall_severity"
        ]
        == "none"
    )

    assert (
        conflict_types[
            "position_conflicts"
        ]
        == []
    )

    assert (
        conflict_types[
            "duplicate_conflicts"
        ]
        == []
    )

    assert (
        conflict_types[
            "conflicts"
        ]
        == []
    )

    assert (
        conflict_types[
            "overall_status"
        ]
        == "not_applicable"
    )

    assert (
        conflict_types[
            "method"
        ]
        == "stem_combination_conflict_types_v1"
    )

    assert (
        conflict_types[
            "status"
        ]
        == "provisional_conflict_typing"
    )

    assert isinstance(
        conflict_types["notes"],
        list,
    )

    assert (
        len(
            conflict_types["notes"]
        )
        >= 1
    )


def test_chart_contains_final_strength_judgment():
    request = make_verified_request()

    result = calculate_chart(request)

    judgment = result[
        "final_strength_judgment"
    ]

    assert isinstance(
        judgment["base_score"],
        float,
    )

    assert isinstance(
        judgment["root_adjustment"],
        float,
    )

    assert isinstance(
        judgment["month_adjustment"],
        float,
    )

    assert isinstance(
        judgment["branch_adjustment"],
        float,
    )

    assert isinstance(
        judgment[
            "transformation_adjustment"
        ],
        float,
    )

    assert isinstance(
        judgment["adjustment_total"],
        float,
    )

    assert isinstance(
        judgment["raw_final_score"],
        float,
    )

    assert isinstance(
        judgment["final_score"],
        float,
    )

    assert (
        0.0
        <= judgment["final_score"]
        <= 100.0
    )

    assert judgment[
        "technical_label"
    ] in {
        "very_strong",
        "strong",
        "balanced",
        "weak",
        "very_weak",
    }

    assert judgment["label"] in {
        "極身強",
        "身強",
        "中和",
        "身弱",
        "極身弱",
    }

    assert judgment["confidence"] in {
        "high",
        "medium",
        "low",
    }

    assert isinstance(
        judgment["components"],
        dict,
    )

    assert (
        judgment["components"][
            "base"
        ]["score"]
        == judgment["base_score"]
    )

    assert (
        judgment["components"][
            "root"
        ]["adjustment"]
        == judgment["root_adjustment"]
    )

    assert (
        judgment["components"][
            "month"
        ]["adjustment"]
        == judgment["month_adjustment"]
    )

    assert (
        judgment["components"][
            "branch_relations"
        ]["adjustment"]
        == judgment["branch_adjustment"]
    )

    assert (
        judgment["components"][
            "stem_transformation"
        ]["adjustment"]
        == judgment[
            "transformation_adjustment"
        ]
    )

    assert (
        judgment["method"]
        == "final_strength_judgment_v2"
    )

    assert (
        judgment["status"]
        == "provisional_final_strength_judgment_v2"
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


def test_chart_contains_pattern_candidates():
    request = make_verified_request()

    result = calculate_chart(
        request
    )

    pattern_candidates = result[
        "pattern_candidates"
    ]

    assert isinstance(
        pattern_candidates,
        dict,
    )

    assert (
        pattern_candidates[
            "has_candidate"
        ]
        is True
    )

    assert (
        pattern_candidates[
            "candidate_count"
        ]
        >= 1
    )

    assert (
        pattern_candidates[
            "primary_candidate"
        ]
        is not None
    )

    assert (
        pattern_candidates[
            "primary_candidate"
        ][
            "pattern"
        ]
        == "偏財格"
    )

    assert (
        pattern_candidates[
            "primary_candidate"
        ][
            "technical_pattern"
        ]
        == "indirect_wealth"
    )

    assert (
        pattern_candidates[
            "primary_candidate"
        ][
            "pattern_group"
        ]
        == "standard_pattern"
    )

    assert (
        pattern_candidates[
            "primary_candidate"
        ][
            "source"
        ]
        == "month_main_hidden_stem"
    )

    assert (
        pattern_candidates[
            "primary_candidate"
        ][
            "month_branch"
        ]
        == "未"
    )

    assert (
        pattern_candidates[
            "primary_candidate"
        ][
            "month_main_hidden_stem"
        ]
        == "己"
    )

    assert (
        pattern_candidates[
            "primary_candidate"
        ][
            "ten_god"
        ]
        == "偏財"
    )

    assert (
        pattern_candidates[
            "primary_candidate"
        ][
            "is_exposed"
        ]
        is False
    )

    assert (
        pattern_candidates[
            "primary_candidate"
        ][
            "exposure_positions"
        ]
        == []
    )

    assert (
        pattern_candidates[
            "primary_candidate"
        ][
            "confidence"
        ]
        == "medium"
    )

    assert (
        pattern_candidates[
            "candidate_groups"
        ]
        == {
            "standard_pattern": 1,
            "special_month_pattern": 0,
        }
    )

    assert (
        pattern_candidates[
            "has_school_rule_candidate"
        ]
        is False
    )

    assert (
        pattern_candidates[
            "month_context"
        ][
            "month_stem"
        ]
        == "癸"
    )

    assert (
        pattern_candidates[
            "month_context"
        ][
            "month_branch"
        ]
        == "未"
    )

    assert (
        pattern_candidates[
            "month_context"
        ][
            "hidden_stems"
        ]
        == [
            "己",
            "丁",
            "乙",
        ]
    )

    assert (
        pattern_candidates[
            "month_context"
        ][
            "main_hidden_stem"
        ]
        == "己"
    )

    assert (
        pattern_candidates[
            "month_context"
        ][
            "main_hidden_stem_ten_god"
        ]
        == "偏財"
    )

    assert (
        pattern_candidates[
            "day_master_stem"
        ]
        == "乙"
    )

    assert (
        pattern_candidates[
            "overall_status"
        ]
        == "candidate_detected"
    )

    assert (
        pattern_candidates[
            "method"
        ]
        == "pattern_candidates_v1"
    )

    assert (
        pattern_candidates[
            "status"
        ]
        == "provisional_pattern_candidates"
    )

    assert isinstance(
        pattern_candidates[
            "notes"
        ],
        list,
    )

    assert (
        len(
            pattern_candidates[
                "notes"
            ]
        )
        >= 1
    )


def test_chart_pattern_candidate_matches_month_data():
    request = make_verified_request()

    result = calculate_chart(
        request
    )

    month = result[
        "chart"
    ][
        "month"
    ]

    pattern_candidates = result[
        "pattern_candidates"
    ]

    primary = pattern_candidates[
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


def test_chart_pattern_candidates_are_provisional():
    request = make_verified_request()

    result = calculate_chart(
        request
    )

    pattern_candidates = result[
        "pattern_candidates"
    ]

    assert (
        pattern_candidates[
            "primary_candidate"
        ][
            "is_provisional"
        ]
        is True
    )

    assert (
        pattern_candidates[
            "primary_candidate"
        ][
            "candidate_status"
        ]
        == "provisional_candidate"
    )




def test_chart_contains_pattern_judgment():
    request = make_verified_request()

    result = calculate_chart(
        request
    )

    judgment = result[
        "pattern_judgment"
    ]

    assert isinstance(
        judgment,
        dict,
    )

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
        judgment[
            "primary_judgment"
        ]
        is not None
    )

    assert (
        judgment[
            "primary_judgment"
        ][
            "pattern"
        ]
        == "偏財格"
    )

    assert (
        judgment[
            "primary_judgment"
        ][
            "technical_pattern"
        ]
        == "indirect_wealth"
    )

    assert (
        judgment[
            "primary_judgment"
        ][
            "is_exposed"
        ]
        is False
    )

    assert (
        judgment[
            "primary_judgment"
        ][
            "establishment_score"
        ]
        == 60.0
    )

    assert (
        judgment[
            "primary_judgment"
        ][
            "establishment_status"
        ]
        == "possible"
    )

    assert (
        judgment[
            "primary_judgment"
        ][
            "final_judgment"
        ]
        == "provisional_possible"
    )

    assert (
        judgment[
            "strong_count"
        ]
        == 0
    )

    assert (
        judgment[
            "possible_count"
        ]
        == 1
    )

    assert (
        judgment[
            "weakened_count"
        ]
        == 0
    )

    assert (
        judgment[
            "school_rule_count"
        ]
        == 0
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

    assert (
        judgment[
            "method"
        ]
        == "pattern_judgment_v2"
    )

    assert (
        judgment[
            "status"
        ]
        == "provisional_pattern_judgment_v2"
    )

    assert isinstance(
        judgment[
            "notes"
        ],
        list,
    )

    assert (
        len(
            judgment[
                "notes"
            ]
        )
        >= 1
    )


def test_chart_pattern_judgment_breaking_factors():
    request = make_verified_request()

    result = calculate_chart(
        request
    )

    judgment = result[
        "pattern_judgment"
    ]

    primary = judgment[
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


def test_chart_pattern_judgment_rescue_factors():
    request = make_verified_request()

    result = calculate_chart(
        request
    )

    judgment = result[
        "pattern_judgment"
    ]

    primary = judgment[
        "primary_judgment"
    ]

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

    rescue_types = {
        factor[
            "type"
        ]
        for factor in primary[
            "rescue_factors"
        ]
    }

    final_strength = result[
        "final_strength_judgment"
    ]

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


def test_chart_pattern_judgment_evidence_matches_results():
    request = make_verified_request()

    result = calculate_chart(
        request
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


def test_chart_pattern_judgment_matches_pattern_candidates():
    request = make_verified_request()

    result = calculate_chart(
        request
    )

    candidates = result[
        "pattern_candidates"
    ]

    judgment = result[
        "pattern_judgment"
    ]

    assert (
        judgment[
            "primary_pattern"
        ]
        == candidates[
            "primary_candidate"
        ][
            "pattern"
        ]
    )

    assert (
        judgment[
            "technical_pattern"
        ]
        == candidates[
            "primary_candidate"
        ][
            "technical_pattern"
        ]
    )


def test_chart_contains_pattern_special_rules():
    request = make_verified_request()

    result = calculate_chart(
        request
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

    assert (
        special_rules[
            "rule_count"
        ]
        == 6
    )

    assert (
        special_rules[
            "method"
        ]
        == "pattern_special_rules_v1"
    )

    assert (
        special_rules[
            "status"
        ]
        == "provisional_pattern_special_rules"
    )

    assert isinstance(
        special_rules[
            "rules"
        ],
        list,
    )

    assert (
        len(
            special_rules[
                "rules"
            ]
        )
        == 6
    )

    assert isinstance(
        special_rules[
            "detected_rules"
        ],
        list,
    )

    assert isinstance(
        special_rules[
            "breaking_rules"
        ],
        list,
    )

    assert isinstance(
        special_rules[
            "rescue_rules"
        ],
        list,
    )

    assert isinstance(
        special_rules[
            "school_rule_items"
        ],
        list,
    )

    assert isinstance(
        special_rules[
            "ten_god_counts"
        ],
        dict,
    )

    assert isinstance(
        special_rules[
            "ten_god_occurrences"
        ],
        list,
    )

    assert isinstance(
        special_rules[
            "strength_evidence"
        ],
        dict,
    )

    assert isinstance(
        special_rules[
            "notes"
        ],
        list,
    )

    assert (
        len(
            special_rules[
                "notes"
            ]
        )
        >= 1
    )


def test_chart_pattern_special_rule_counts_are_consistent():
    request = make_verified_request()

    result = calculate_chart(
        request
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


def test_chart_pattern_special_rules_match_strength():
    request = make_verified_request()

    result = calculate_chart(
        request
    )

    special_rules = result[
        "pattern_special_rules"
    ]

    strength = result[
        "final_strength_judgment"
    ]

    evidence = special_rules[
        "strength_evidence"
    ]

    assert (
        evidence[
            "technical_label"
        ]
        == strength.get(
            "technical_label"
        )
    )

    assert (
        evidence[
            "final_score"
        ]
        == strength.get(
            "final_score"
        )
    )


def test_chart_pattern_judgment_receives_special_rules():
    request = make_verified_request()

    result = calculate_chart(
        request
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


def test_chart_pattern_special_rules_and_judgment_are_v2_compatible():
    request = make_verified_request()

    result = calculate_chart(
        request
    )

    special_rules = result[
        "pattern_special_rules"
    ]

    judgment = result[
        "pattern_judgment"
    ]

    assert (
        special_rules[
            "method"
        ]
        == "pattern_special_rules_v1"
    )

    assert (
        judgment[
            "method"
        ]
        == "pattern_judgment_v2"
    )

    assert (
        judgment[
            "status"
        ]
        == "provisional_pattern_judgment_v2"
    )

    primary = judgment[
        "primary_judgment"
    ]

    assert primary is not None

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

    assert isinstance(
        primary[
            "special_rule_adjustment"
        ],
        (int, float),
    )

# =========================================================
# climate_useful_gods_v1 / pattern_useful_gods_v1 / useful_gods_v3 integration
# =========================================================


def test_chart_contains_climate_useful_gods():
    request = make_verified_request()

    result = calculate_chart(
        request
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


def test_chart_climate_useful_gods_metadata():
    request = make_verified_request()

    result = calculate_chart(
        request
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


def test_chart_climate_useful_gods_matches_chart():
    request = make_verified_request()

    result = calculate_chart(
        request
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
            "day_master_stem"
        ]
        == "乙"
    )

    assert (
        climate[
            "day_master_element"
        ]
        == "木"
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

    assert (
        climate[
            "month_branch"
        ]
        == "未"
    )


def test_chart_climate_useful_gods_verified_1985_values():
    request = make_verified_request()

    result = calculate_chart(
        request
    )

    climate = result[
        "climate_useful_gods"
    ]

    assert (
        climate[
            "season"
        ]
        == "summer"
    )

    assert (
        climate[
            "season_japanese"
        ]
        == "夏"
    )

    assert (
        climate[
            "heat_score"
        ]
        == 1.15
    )

    assert (
        climate[
            "moisture_score"
        ]
        == -0.4
    )

    assert (
        climate[
            "climate_needs"
        ]
        == [
            "cooling",
        ]
    )

    assert (
        climate[
            "primary_climate_element"
        ]
        == "水"
    )

    assert (
        climate[
            "climate_elements"
        ]
        == [
            "水",
        ]
    )


def test_chart_climate_useful_gods_candidate_consistency():
    request = make_verified_request()

    result = calculate_chart(
        request
    )

    climate = result[
        "climate_useful_gods"
    ]

    elements = climate[
        "climate_elements"
    ]

    candidates = climate[
        "climate_candidates"
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


def test_chart_climate_useful_gods_candidate_priorities():
    request = make_verified_request()

    result = calculate_chart(
        request
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


def test_chart_contains_useful_gods_v3():
    request = make_verified_request()

    result = calculate_chart(
        request
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


def test_chart_useful_gods_v3_metadata():
    request = make_verified_request()

    result = calculate_chart(
        request
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


def test_chart_useful_gods_v3_matches_day_master():
    request = make_verified_request()

    result = calculate_chart(
        request
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
            "day_master_stem"
        ]
        == "乙"
    )

    assert (
        useful_gods[
            "day_master_element"
        ]
        == "木"
    )


def test_chart_useful_gods_v3_evidence_matches_results():
    request = make_verified_request()

    result = calculate_chart(
        request
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


def test_chart_useful_gods_v3_support_balance_metadata():
    request = make_verified_request()

    result = calculate_chart(
        request
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


def test_chart_useful_gods_v3_strength_summary_matches_final_strength():
    request = make_verified_request()

    result = calculate_chart(
        request
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


def test_chart_useful_gods_v3_pattern_summary_matches_pattern_judgment():
    request = make_verified_request()

    result = calculate_chart(
        request
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


def test_chart_useful_gods_v3_climate_matches_top_level():
    request = make_verified_request()

    result = calculate_chart(
        request
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


def test_chart_useful_gods_v3_primary_matches_final_elements():
    request = make_verified_request()

    result = calculate_chart(
        request
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


def test_chart_useful_gods_v3_final_candidate_priorities():
    request = make_verified_request()

    result = calculate_chart(
        request
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


def test_chart_useful_gods_v3_integrated_scores():
    request = make_verified_request()

    result = calculate_chart(
        request
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


def test_chart_useful_gods_v3_support_element_scores_match_weighted():
    request = make_verified_request()

    result = calculate_chart(
        request
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


def test_chart_useful_gods_v3_support_primary_consistency():
    request = make_verified_request()

    result = calculate_chart(
        request
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


def test_chart_useful_gods_v3_support_unfavorable_consistency():
    request = make_verified_request()

    result = calculate_chart(
        request
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


def test_chart_useful_gods_v3_support_candidate_priorities():
    request = make_verified_request()

    result = calculate_chart(
        request
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


def test_chart_useful_gods_v3_support_lists_are_disjoint():
    request = make_verified_request()

    result = calculate_chart(
        request
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


def test_chart_useful_gods_v3_agreement_structure():
    request = make_verified_request()

    result = calculate_chart(
        request
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


def test_chart_useful_gods_v3_agreement_matches_sources():
    request = make_verified_request()

    result = calculate_chart(
        request
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


def test_chart_useful_gods_v3_pattern_matches_top_level():
    request = make_verified_request()

    result = calculate_chart(
        request
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


def test_chart_useful_gods_v3_preserves_v2_baseline():
    request = make_verified_request()

    result = calculate_chart(
        request
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


def test_chart_useful_gods_v3_reasoning_and_notes_exist():
    request = make_verified_request()

    result = calculate_chart(
        request
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

# =========================================================
# pattern_useful_gods_v1 integration
# =========================================================


def test_chart_contains_pattern_useful_gods():
    request = make_verified_request()

    result = calculate_chart(
        request
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


def test_chart_pattern_useful_gods_metadata():
    request = make_verified_request()

    result = calculate_chart(
        request
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


def test_chart_pattern_useful_gods_matches_day_master():
    request = make_verified_request()

    result = calculate_chart(
        request
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
            "day_master_stem"
        ]
        == "乙"
    )

    assert (
        pattern_useful[
            "day_master_element"
        ]
        == "木"
    )


def test_chart_pattern_useful_gods_matches_pattern_judgment():
    request = make_verified_request()

    result = calculate_chart(
        request
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
        == judgment[
            "primary_pattern"
        ]
    )

    assert (
        pattern_useful[
            "technical_pattern"
        ]
        == judgment[
            "technical_pattern"
        ]
    )

    assert (
        pattern_useful[
            "pattern_overall_judgment"
        ]
        == judgment[
            "overall_judgment"
        ]
    )

    assert (
        pattern_useful[
            "pattern_confidence"
        ]
        == judgment[
            "confidence"
        ]
    )


def test_chart_pattern_useful_gods_verified_1985_values():
    request = make_verified_request()

    result = calculate_chart(
        request
    )

    pattern_useful = result[
        "pattern_useful_gods"
    ]

    assert (
        pattern_useful[
            "primary_pattern"
        ]
        == "偏財格"
    )

    assert (
        pattern_useful[
            "technical_pattern"
        ]
        == "indirect_wealth"
    )

    assert (
        pattern_useful[
            "supported_pattern"
        ]
        is True
    )

    assert (
        pattern_useful[
            "pattern_elements"
        ]
        == [
            "火",
            "金",
        ]
    )

    assert (
        pattern_useful[
            "primary_pattern_element"
        ]
        == "火"
    )

    assert (
        pattern_useful[
            "secondary_pattern_elements"
        ]
        == [
            "金",
        ]
    )


def test_chart_pattern_useful_gods_candidate_consistency():
    request = make_verified_request()

    result = calculate_chart(
        request
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


def test_chart_pattern_useful_gods_candidate_priorities():
    request = make_verified_request()

    result = calculate_chart(
        request
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


def test_chart_pattern_useful_gods_evidence_matches_results():
    request = make_verified_request()

    result = calculate_chart(
        request
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
        ][
            "technical_pattern"
        ]
    )

    assert isinstance(
        evidence[
            "raw_candidates"
        ],
        list,
    )


def test_chart_pattern_useful_gods_candidate_roles_verified_1985():
    request = make_verified_request()

    result = calculate_chart(
        request
    )

    candidates = result[
        "pattern_useful_gods"
    ][
        "pattern_candidates"
    ]

    assert len(
        candidates
    ) == 2

    assert (
        candidates[0][
            "element"
        ]
        == "火"
    )

    assert (
        candidates[0][
            "relations"
        ]
        == [
            "output",
        ]
    )

    assert (
        candidates[0][
            "roles"
        ]
        == [
            "generate_wealth",
        ]
    )

    assert (
        candidates[1][
            "element"
        ]
        == "金"
    )

    assert (
        candidates[1][
            "relations"
        ]
        == [
            "officer",
        ]
    )

    assert (
        candidates[1][
            "roles"
        ]
        == [
            "protect_wealth",
        ]
    )


def test_chart_pattern_useful_gods_reasoning_and_notes_exist():
    request = make_verified_request()

    result = calculate_chart(
        request
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

    assert (
        len(
            pattern_useful[
                "reasoning"
            ]
        )
        >= 1
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

# ============================================================
# Luck Pillars v2 Integration Tests
# ============================================================


def test_chart_contains_luck_pillars():
    """
    calculate_chart() の結果に
    大運計算結果が含まれることを確認します。
    """
    request = make_verified_request()

    result = calculate_chart(
        request
    )

    assert "luck_pillars" in result

    luck_pillars = result[
        "luck_pillars"
    ]

    assert isinstance(
        luck_pillars,
        dict,
    )


def test_chart_luck_pillars_required_keys():
    """
    luck_pillars_v2 の主要キーが
    chart 統合後も存在することを確認します。
    """
    request = make_verified_request()

    result = calculate_chart(
        request
    )

    luck_pillars = result[
        "luck_pillars"
    ]

    required_keys = {
        "direction",
        "direction_japanese",
        "year_stem",
        "year_stem_yin_yang",
        "gender",
        "month_ganzhi",
        "day_master_stem",
        "day_master_element",
        "birth_datetime",
        "target_term_datetime",
        "target_term_name",
        "target_term_month",
        "target_term_branch",
        "target_term_source",
        "term_distance_days",
        "start_age",
        "start_age_detail",
        "pillars",
        "pillar_count",
        "calculation_rules",
        "method",
        "status",
        "notes",
    }

    assert required_keys.issubset(
        luck_pillars.keys()
    )


def test_chart_luck_pillars_v2_metadata():
    """
    luck_pillars_v2 の method / status を確認します。
    """
    request = make_verified_request()

    result = calculate_chart(
        request
    )

    luck_pillars = result[
        "luck_pillars"
    ]

    assert (
        luck_pillars[
            "method"
        ]
        == "luck_pillars_v2"
    )

    assert (
        luck_pillars[
            "status"
        ]
        == "provisional_luck_pillars_v2"
    )

    assert isinstance(
        luck_pillars[
            "notes"
        ],
        list,
    )

    assert (
        len(
            luck_pillars[
                "notes"
            ]
        )
        >= 1
    )


def test_chart_luck_pillars_direction_exists():
    """
    direction と direction_japanese が
    正常な値であることを確認します。
    """
    request = make_verified_request()

    result = calculate_chart(
        request
    )

    luck_pillars = result[
        "luck_pillars"
    ]

    assert luck_pillars[
        "direction"
    ] in {
        "forward",
        "backward",
    }

    assert luck_pillars[
        "direction_japanese"
    ] in {
        "順行",
        "逆行",
    }


def test_chart_luck_pillars_direction_japanese_consistency():
    """
    direction と日本語表示の対応を確認します。
    """
    request = make_verified_request()

    result = calculate_chart(
        request
    )

    luck_pillars = result[
        "luck_pillars"
    ]

    expected = {
        "forward": "順行",
        "backward": "逆行",
    }

    assert (
        luck_pillars[
            "direction_japanese"
        ]
        == expected[
            luck_pillars[
                "direction"
            ]
        ]
    )


def test_chart_luck_pillars_verified_1985_direction():
    """
    検証命式:
    1985年 乙年・女性。

    陰年女性なので順行になることを確認します。
    """
    request = make_verified_request()

    result = calculate_chart(
        request
    )

    luck_pillars = result[
        "luck_pillars"
    ]

    assert (
        luck_pillars[
            "year_stem"
        ]
        == "乙"
    )

    assert (
        luck_pillars[
            "year_stem_yin_yang"
        ]
        == "陰"
    )

    assert (
        luck_pillars[
            "gender"
        ]
        == "female"
    )

    assert (
        luck_pillars[
            "direction"
        ]
        == "forward"
    )

    assert (
        luck_pillars[
            "direction_japanese"
        ]
        == "順行"
    )


def test_chart_luck_pillars_chart_identity_consistency():
    """
    大運計算へ渡した年干・月柱・日主が
    chart 本体と一致することを確認します。
    """
    request = make_verified_request()

    result = calculate_chart(
        request
    )

    luck_pillars = result[
        "luck_pillars"
    ]

    assert (
        luck_pillars[
            "year_stem"
        ]
        == result[
            "chart"
        ][
            "year"
        ][
            "stem"
        ]
    )

    assert (
        luck_pillars[
            "month_ganzhi"
        ]
        == result[
            "chart"
        ][
            "month"
        ][
            "pillar"
        ]
    )

    assert (
        luck_pillars[
            "day_master_stem"
        ]
        == result[
            "day_master"
        ][
            "stem"
        ]
    )

    assert (
        luck_pillars[
            "day_master_element"
        ]
        == "木"
    )


def test_chart_luck_pillars_uses_solar_terms_v2():
    """
    chart からの通常計算では
    solar_terms_v2 により対象節が
    自動選択されることを確認します。
    """
    request = make_verified_request()

    result = calculate_chart(
        request
    )

    luck_pillars = result[
        "luck_pillars"
    ]

    assert (
        luck_pillars[
            "target_term_source"
        ]
        == "solar_terms_v2"
    )

    assert (
        luck_pillars[
            "calculation_rules"
        ][
            "term_datetime_source"
        ]
        == "solar_terms_v2"
    )


def test_chart_luck_pillars_verified_1985_target_term():
    """
    1985-07-17 21:50 は順行なので、
    固定節入り仕様の solar_terms_v2 では
    次節の立秋を対象にすることを確認します。
    """
    request = make_verified_request()

    result = calculate_chart(
        request
    )

    luck_pillars = result[
        "luck_pillars"
    ]

    assert (
        luck_pillars[
            "target_term_name"
        ]
        == "立秋"
    )

    assert (
        luck_pillars[
            "target_term_month"
        ]
        == 8
    )

    assert (
        luck_pillars[
            "target_term_branch"
        ]
        == "申"
    )

    assert (
        luck_pillars[
            "target_term_datetime"
        ]
        == "1985-08-08T00:00:00"
    )


def test_chart_luck_pillars_start_age_exists():
    """
    起運年齢が数値で存在することを確認します。
    """
    request = make_verified_request()

    result = calculate_chart(
        request
    )

    start_age = result[
        "luck_pillars"
    ][
        "start_age"
    ]

    assert isinstance(
        start_age,
        (int, float),
    )

    assert not isinstance(
        start_age,
        bool,
    )

    assert start_age >= 0.0


def test_chart_luck_pillars_start_age_is_reasonable():
    """
    起運年齢が大きく逸脱していないことを
    integration guard として確認します。
    """
    request = make_verified_request()

    result = calculate_chart(
        request
    )

    start_age = result[
        "luck_pillars"
    ][
        "start_age"
    ]

    assert (
        0.0
        <= start_age
        <= 12.0
    )


def test_chart_luck_pillars_start_age_matches_term_distance():
    """
    三日一年法:
        start_age = term_distance_days / 3

    が chart 統合後も成立することを確認します。
    """
    request = make_verified_request()

    result = calculate_chart(
        request
    )

    luck_pillars = result[
        "luck_pillars"
    ]

    expected = round(
        luck_pillars[
            "term_distance_days"
        ]
        / 3.0,
        6,
    )

    assert (
        luck_pillars[
            "start_age"
        ]
        == expected
    )


def test_chart_luck_pillars_start_age_detail():
    """
    起運年齢の年・月・日表示が
    保持されていることを確認します。
    """
    request = make_verified_request()

    result = calculate_chart(
        request
    )

    detail = result[
        "luck_pillars"
    ][
        "start_age_detail"
    ]

    required_keys = {
        "years",
        "months",
        "days",
    }

    assert required_keys.issubset(
        detail.keys()
    )

    assert all(
        isinstance(
            detail[key],
            int,
        )
        for key in required_keys
    )


def test_chart_luck_pillars_generates_ten_periods():
    """
    デフォルトで大運10本が生成されることを
    確認します。
    """
    request = make_verified_request()

    result = calculate_chart(
        request
    )

    luck_pillars = result[
        "luck_pillars"
    ]

    assert (
        luck_pillars[
            "pillar_count"
        ]
        == 10
    )

    assert (
        len(
            luck_pillars[
                "pillars"
            ]
        )
        == 10
    )


def test_chart_luck_pillars_each_item_required_keys():
    """
    各大運データの主要キーを確認します。
    """
    request = make_verified_request()

    result = calculate_chart(
        request
    )

    pillars = result[
        "luck_pillars"
    ][
        "pillars"
    ]

    required_keys = {
        "index",
        "ganzhi",
        "stem",
        "branch",
        "stem_element",
        "branch_element",
        "stem_yin_yang",
        "stem_ten_god",
        "start_age",
        "end_age",
        "start_age_detail",
        "end_age_detail",
        "start_datetime",
        "end_datetime",
        "stem_useful_relation",
        "branch_useful_relation",
    }

    for pillar in pillars:
        assert required_keys.issubset(
            pillar.keys()
        )


def test_chart_luck_pillars_each_item_has_ganzhi():
    """
    各大運に2文字の干支があることを確認します。
    """
    request = make_verified_request()

    result = calculate_chart(
        request
    )

    pillars = result[
        "luck_pillars"
    ][
        "pillars"
    ]

    for pillar in pillars:
        assert isinstance(
            pillar[
                "ganzhi"
            ],
            str,
        )

        assert (
            len(
                pillar[
                    "ganzhi"
                ]
            )
            == 2
        )


def test_chart_luck_pillars_ganzhi_matches_stem_branch():
    """
    ganzhi == stem + branch を確認します。
    """
    request = make_verified_request()

    result = calculate_chart(
        request
    )

    pillars = result[
        "luck_pillars"
    ][
        "pillars"
    ]

    for pillar in pillars:
        assert (
            pillar[
                "ganzhi"
            ]
            == (
                pillar[
                    "stem"
                ]
                + pillar[
                    "branch"
                ]
            )
        )


def test_chart_luck_pillars_indexes_are_sequential():
    """
    index が1～10で連続することを確認します。
    """
    request = make_verified_request()

    result = calculate_chart(
        request
    )

    pillars = result[
        "luck_pillars"
    ][
        "pillars"
    ]

    assert [
        pillar[
            "index"
        ]
        for pillar in pillars
    ] == list(
        range(
            1,
            11,
        )
    )


def test_chart_luck_pillars_age_ranges_are_ordered():
    """
    大運の年齢範囲が
    時系列順であることを確認します。
    """
    request = make_verified_request()

    result = calculate_chart(
        request
    )

    pillars = result[
        "luck_pillars"
    ][
        "pillars"
    ]

    for pillar in pillars:
        assert (
            pillar[
                "start_age"
            ]
            < pillar[
                "end_age"
            ]
        )

    for previous, current in zip(
        pillars,
        pillars[1:],
    ):
        assert (
            previous[
                "start_age"
            ]
            < current[
                "start_age"
            ]
        )


def test_chart_luck_pillars_are_ten_year_intervals():
    """
    各大運が10年区切りであることを確認します。
    """
    request = make_verified_request()

    result = calculate_chart(
        request
    )

    pillars = result[
        "luck_pillars"
    ][
        "pillars"
    ]

    for pillar in pillars:
        assert (
            round(
                pillar[
                    "end_age"
                ]
                - pillar[
                    "start_age"
                ],
                6,
            )
            == 10.0
        )

    for previous, current in zip(
        pillars,
        pillars[1:],
    ):
        assert (
            round(
                current[
                    "start_age"
                ]
                - previous[
                    "start_age"
                ],
                6,
            )
            == 10.0
        )


def test_chart_luck_pillars_first_period_matches_start_age():
    """
    第1大運の開始年齢が
    luck_pillars.start_age と一致することを確認します。
    """
    request = make_verified_request()

    result = calculate_chart(
        request
    )

    luck_pillars = result[
        "luck_pillars"
    ]

    first = luck_pillars[
        "pillars"
    ][0]

    assert (
        first[
            "start_age"
        ]
        == luck_pillars[
            "start_age"
        ]
    )


def test_chart_luck_pillars_verified_1985_first_ganzhi():
    """
    癸未月・順行の第1大運が
    甲申になることを確認します。
    """
    request = make_verified_request()

    result = calculate_chart(
        request
    )

    first = result[
        "luck_pillars"
    ][
        "pillars"
    ][0]

    assert (
        first[
            "ganzhi"
        ]
        == "甲申"
    )

    assert (
        first[
            "stem"
        ]
        == "甲"
    )

    assert (
        first[
            "branch"
        ]
        == "申"
    )


def test_chart_luck_pillars_verified_1985_first_ten_god():
    """
    乙日主に対する第1大運甲の通変星が
    劫財であることを確認します。
    """
    request = make_verified_request()

    result = calculate_chart(
        request
    )

    first = result[
        "luck_pillars"
    ][
        "pillars"
    ][0]

    assert (
        first[
            "stem_ten_god"
        ]
        == "劫財"
    )


def test_chart_luck_pillars_elements_exist():
    """
    各大運の天干・地支五行が
    五行集合内にあることを確認します。
    """
    request = make_verified_request()

    result = calculate_chart(
        request
    )

    pillars = result[
        "luck_pillars"
    ][
        "pillars"
    ]

    elements = {
        "木",
        "火",
        "土",
        "金",
        "水",
    }

    for pillar in pillars:
        assert (
            pillar[
                "stem_element"
            ]
            in elements
        )

        assert (
            pillar[
                "branch_element"
            ]
            in elements
        )


def test_chart_luck_pillars_useful_gods_relations_exist():
    """
    useful_gods_v3 との関係判定が
    各大運へ統合されていることを確認します。
    """
    request = make_verified_request()

    result = calculate_chart(
        request
    )

    pillars = result[
        "luck_pillars"
    ][
        "pillars"
    ]

    relation_keys = {
        "is_useful",
        "is_primary_useful",
        "priority",
        "relationship",
    }

    for pillar in pillars:
        assert relation_keys.issubset(
            pillar[
                "stem_useful_relation"
            ].keys()
        )

        assert relation_keys.issubset(
            pillar[
                "branch_useful_relation"
            ].keys()
        )


def test_chart_luck_pillars_useful_relation_labels():
    """
    用神関係ラベルが想定集合内にあることを確認します。
    """
    request = make_verified_request()

    result = calculate_chart(
        request
    )

    pillars = result[
        "luck_pillars"
    ][
        "pillars"
    ]

    valid_relationships = {
        "unknown",
        "primary_useful",
        "secondary_useful",
        "support_unfavorable",
        "neutral",
    }

    for pillar in pillars:
        assert (
            pillar[
                "stem_useful_relation"
            ][
                "relationship"
            ]
            in valid_relationships
        )

        assert (
            pillar[
                "branch_useful_relation"
            ][
                "relationship"
            ]
            in valid_relationships
        )


def test_chart_luck_pillars_calculation_rules():
    """
    大運計算ルールのmetadataを確認します。
    """
    request = make_verified_request()

    result = calculate_chart(
        request
    )

    rules = result[
        "luck_pillars"
    ][
        "calculation_rules"
    ]

    assert (
        rules[
            "direction_rule"
        ]
        == "陽男陰女順行・陰男陽女逆行"
    )

    assert (
        rules[
            "start_age_rule"
        ]
        == "三日一年法"
    )

    assert (
        rules[
            "month_pillar_rule"
        ]
        == "月柱の次干支から第1大運"
    )

    assert (
        rules[
            "pillar_duration_years"
        ]
        == 10
    )


def test_chart_luck_pillars_no_duplicate_ganzhi():
    """
    最初の10大運に同じ干支が
    重複しないことを確認します。
    """
    request = make_verified_request()

    result = calculate_chart(
        request
    )

    pillars = result[
        "luck_pillars"
    ][
        "pillars"
    ]

    ganzhi_list = [
        pillar[
            "ganzhi"
        ]
        for pillar in pillars
    ]

    assert (
        len(
            ganzhi_list
        )
        == len(
            set(
                ganzhi_list
            )
        )
    )


def test_chart_luck_pillars_start_and_end_datetime_exist():
    """
    各大運に概算開始・終了日時が
    ISO文字列として存在することを確認します。
    """
    request = make_verified_request()

    result = calculate_chart(
        request
    )

    pillars = result[
        "luck_pillars"
    ][
        "pillars"
    ]

    for pillar in pillars:
        assert isinstance(
            pillar[
                "start_datetime"
            ],
            str,
        )

        assert isinstance(
            pillar[
                "end_datetime"
            ],
            str,
        )

        assert (
            "T"
            in pillar[
                "start_datetime"
            ]
        )

        assert (
            "T"
            in pillar[
                "end_datetime"
            ]
        )

# ============================================================
# Current Luck v1 Integration Tests
# ============================================================


CURRENT_LUCK_TARGET_DATETIME = datetime(
    2026,
    8,
    10,
    15,
    36,
)


def calculate_verified_chart_with_current_luck():
    """
    current_luck_v1 の chart 統合テストで使用する
    固定日時つき検証結果を返します。

    datetime.now() に依存させず、
    テストの再現性を維持します。
    """
    request = make_verified_request()

    return calculate_chart(
        request,
        target_datetime=(
            CURRENT_LUCK_TARGET_DATETIME
        ),
    )


def test_chart_contains_current_luck():
    """
    calculate_chart() の戻り値に
    current_luck が含まれることを確認します。
    """
    result = (
        calculate_verified_chart_with_current_luck()
    )

    assert "current_luck" in result

    assert isinstance(
        result[
            "current_luck"
        ],
        dict,
    )


def test_chart_current_luck_required_keys():
    """
    current_luck_v1 の主要キーが
    chart 統合後も存在することを確認します。
    """
    result = (
        calculate_verified_chart_with_current_luck()
    )

    current_luck = result[
        "current_luck"
    ]

    required_keys = {
        "has_current_luck",
        "phase",
        "exact_age",
        "calendar_age",
        "current_luck_pillar",
        "previous_luck_pillar",
        "next_luck_pillar",
        "progress",
        "years_until_next_luck",
        "method",
        "status",
        "notes",
    }

    assert required_keys.issubset(
        current_luck.keys()
    )


def test_chart_current_luck_v1_metadata():
    """
    current_luck_v1 の method / status を確認します。
    """
    result = (
        calculate_verified_chart_with_current_luck()
    )

    current_luck = result[
        "current_luck"
    ]

    assert (
        current_luck[
            "method"
        ]
        == "current_luck_v1"
    )

    assert (
        current_luck[
            "status"
        ]
        in {
            "current_luck_resolved",
            "before_first_luck",
            "after_last_luck",
        }
    )

    assert isinstance(
        current_luck[
            "notes"
        ],
        list,
    )

    assert (
        len(
            current_luck[
                "notes"
            ]
        )
        >= 1
    )


def test_chart_current_luck_fixed_target_is_reproducible():
    """
    同じ target_datetime を指定した場合、
    current_luck の結果が再現されることを確認します。
    """
    request = make_verified_request()

    first = calculate_chart(
        request,
        target_datetime=(
            CURRENT_LUCK_TARGET_DATETIME
        ),
    )

    second = calculate_chart(
        request,
        target_datetime=(
            CURRENT_LUCK_TARGET_DATETIME
        ),
    )

    assert (
        first[
            "current_luck"
        ]
        == second[
            "current_luck"
        ]
    )


def test_chart_current_luck_age_fields_exist():
    """
    exact_age / calendar_age が
    正常な型と範囲であることを確認します。
    """
    result = (
        calculate_verified_chart_with_current_luck()
    )

    current_luck = result[
        "current_luck"
    ]

    assert isinstance(
        current_luck[
            "exact_age"
        ],
        (int, float),
    )

    assert not isinstance(
        current_luck[
            "exact_age"
        ],
        bool,
    )

    assert (
        current_luck[
            "exact_age"
        ]
        >= 0.0
    )

    assert isinstance(
        current_luck[
            "calendar_age"
        ],
        int,
    )

    assert not isinstance(
        current_luck[
            "calendar_age"
        ],
        bool,
    )

    assert (
        current_luck[
            "calendar_age"
        ]
        >= 0
    )


def test_chart_current_luck_verified_calendar_age():
    """
    1985-07-17 生まれを
    2026-08-10 時点で判定すると
    満41歳であることを確認します。
    """
    result = (
        calculate_verified_chart_with_current_luck()
    )

    assert (
        result[
            "current_luck"
        ][
            "calendar_age"
        ]
        == 41
    )


def test_chart_current_luck_exact_age_is_consistent():
    """
    exact_age が満年齢以上かつ、
    次の誕生日までの範囲にあることを確認します。
    """
    result = (
        calculate_verified_chart_with_current_luck()
    )

    current_luck = result[
        "current_luck"
    ]

    exact_age = current_luck[
        "exact_age"
    ]

    calendar_age = current_luck[
        "calendar_age"
    ]

    assert (
        calendar_age
        <= exact_age
        < calendar_age + 1.1
    )


def test_chart_current_luck_phase_is_valid():
    """
    phase が current_luck_v1 の
    想定集合内にあることを確認します。
    """
    result = (
        calculate_verified_chart_with_current_luck()
    )

    assert (
        result[
            "current_luck"
        ][
            "phase"
        ]
        in {
            "before_first_luck",
            "in_luck_pillar",
            "after_last_luck",
        }
    )


def test_chart_current_luck_verified_is_in_luck():
    """
    2026年時点では生成済み大運範囲内にあるため、
    現在大運が取得できることを確認します。
    """
    result = (
        calculate_verified_chart_with_current_luck()
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

    assert (
        current_luck[
            "phase"
        ]
        == "in_luck_pillar"
    )

    assert (
        current_luck[
            "current_luck_pillar"
        ]
        is not None
    )


def test_chart_current_luck_pillar_required_keys():
    """
    現在大運に必要な主要キーを確認します。
    """
    result = (
        calculate_verified_chart_with_current_luck()
    )

    current_pillar = result[
        "current_luck"
    ][
        "current_luck_pillar"
    ]

    required_keys = {
        "index",
        "ganzhi",
        "stem",
        "branch",
        "start_age",
        "end_age",
        "is_current",
        "is_previous",
        "is_next",
    }

    assert required_keys.issubset(
        current_pillar.keys()
    )


def test_chart_current_luck_current_flag():
    """
    current_luck_pillar のフラグを確認します。
    """
    result = (
        calculate_verified_chart_with_current_luck()
    )

    current_pillar = result[
        "current_luck"
    ][
        "current_luck_pillar"
    ]

    assert (
        current_pillar[
            "is_current"
        ]
        is True
    )

    assert (
        current_pillar[
            "is_previous"
        ]
        is False
    )

    assert (
        current_pillar[
            "is_next"
        ]
        is False
    )


def test_chart_current_luck_matches_luck_pillars():
    """
    current_luck_pillar が
    luck_pillars 内の同一 index の大運と一致することを
    確認します。
    """
    result = (
        calculate_verified_chart_with_current_luck()
    )

    current_pillar = result[
        "current_luck"
    ][
        "current_luck_pillar"
    ]

    index = current_pillar[
        "index"
    ]

    source_pillar = result[
        "luck_pillars"
    ][
        "pillars"
    ][
        index - 1
    ]

    for key in {
        "index",
        "ganzhi",
        "stem",
        "branch",
        "start_age",
        "end_age",
    }:
        assert (
            current_pillar[
                key
            ]
            == source_pillar[
                key
            ]
        )


def test_chart_current_luck_ganzhi_matches_stem_branch():
    """
    現在大運の ganzhi == stem + branch を確認します。
    """
    result = (
        calculate_verified_chart_with_current_luck()
    )

    current_pillar = result[
        "current_luck"
    ][
        "current_luck_pillar"
    ]

    assert (
        current_pillar[
            "ganzhi"
        ]
        == (
            current_pillar[
                "stem"
            ]
            + current_pillar[
                "branch"
            ]
        )
    )


def test_chart_current_luck_age_inside_current_period():
    """
    exact_age が現在大運の
    start_age <= age < end_age
    を満たすことを確認します。
    """
    result = (
        calculate_verified_chart_with_current_luck()
    )

    current_luck = result[
        "current_luck"
    ]

    age = current_luck[
        "exact_age"
    ]

    pillar = current_luck[
        "current_luck_pillar"
    ]

    assert (
        pillar[
            "start_age"
        ]
        <= age
        < pillar[
            "end_age"
        ]
    )


def test_chart_current_luck_previous_consistency():
    """
    previous_luck_pillar がある場合、
    現在大運の1つ前であることを確認します。
    """
    result = (
        calculate_verified_chart_with_current_luck()
    )

    current_luck = result[
        "current_luck"
    ]

    current_pillar = current_luck[
        "current_luck_pillar"
    ]

    previous_pillar = current_luck[
        "previous_luck_pillar"
    ]

    if current_pillar[
        "index"
    ] == 1:
        assert previous_pillar is None
    else:
        assert previous_pillar is not None

        assert (
            previous_pillar[
                "index"
            ]
            == current_pillar[
                "index"
            ]
            - 1
        )

        assert (
            previous_pillar[
                "is_previous"
            ]
            is True
        )

        assert (
            previous_pillar[
                "is_current"
            ]
            is False
        )


def test_chart_current_luck_next_consistency():
    """
    next_luck_pillar がある場合、
    現在大運の1つ後であることを確認します。
    """
    result = (
        calculate_verified_chart_with_current_luck()
    )

    current_luck = result[
        "current_luck"
    ]

    current_pillar = current_luck[
        "current_luck_pillar"
    ]

    next_pillar = current_luck[
        "next_luck_pillar"
    ]

    pillar_count = result[
        "luck_pillars"
    ][
        "pillar_count"
    ]

    if current_pillar[
        "index"
    ] == pillar_count:
        assert next_pillar is None
    else:
        assert next_pillar is not None

        assert (
            next_pillar[
                "index"
            ]
            == current_pillar[
                "index"
            ]
            + 1
        )

        assert (
            next_pillar[
                "is_next"
            ]
            is True
        )

        assert (
            next_pillar[
                "is_current"
            ]
            is False
        )


def test_chart_current_luck_progress_exists():
    """
    現在大運がある場合に progress が
    辞書として返ることを確認します。
    """
    result = (
        calculate_verified_chart_with_current_luck()
    )

    progress = result[
        "current_luck"
    ][
        "progress"
    ]

    assert isinstance(
        progress,
        dict,
    )

    required_keys = {
        "start_age",
        "end_age",
        "duration_years",
        "elapsed_years",
        "remaining_years",
        "progress_ratio",
        "progress_percent",
    }

    assert required_keys.issubset(
        progress.keys()
    )


def test_chart_current_luck_progress_range():
    """
    進行率が0～100%の範囲に収まることを確認します。
    """
    result = (
        calculate_verified_chart_with_current_luck()
    )

    progress = result[
        "current_luck"
    ][
        "progress"
    ]

    assert (
        0.0
        <= progress[
            "progress_ratio"
        ]
        <= 1.0
    )

    assert (
        0.0
        <= progress[
            "progress_percent"
        ]
        <= 100.0
    )


def test_chart_current_luck_progress_matches_period():
    """
    progress の開始・終了年齢が
    current_luck_pillar と一致することを確認します。
    """
    result = (
        calculate_verified_chart_with_current_luck()
    )

    current_luck = result[
        "current_luck"
    ]

    progress = current_luck[
        "progress"
    ]

    pillar = current_luck[
        "current_luck_pillar"
    ]

    assert (
        progress[
            "start_age"
        ]
        == pillar[
            "start_age"
        ]
    )

    assert (
        progress[
            "end_age"
        ]
        == pillar[
            "end_age"
        ]
    )

    assert (
        progress[
            "duration_years"
        ]
        == 10.0
    )


def test_chart_current_luck_remaining_matches_years_until_next():
    """
    現在大運中では progress.remaining_years と
    years_until_next_luck が一致することを確認します。
    """
    result = (
        calculate_verified_chart_with_current_luck()
    )

    current_luck = result[
        "current_luck"
    ]

    assert (
        current_luck[
            "years_until_next_luck"
        ]
        == current_luck[
            "progress"
        ][
            "remaining_years"
        ]
    )


def test_chart_current_luck_does_not_mutate_luck_pillars():
    """
    current_luck 用の is_current 等のフラグが、
    元の luck_pillars データへ混入しないことを確認します。
    """
    result = (
        calculate_verified_chart_with_current_luck()
    )

    for pillar in result[
        "luck_pillars"
    ][
        "pillars"
    ]:
        assert (
            "is_current"
            not in pillar
        )

        assert (
            "is_previous"
            not in pillar
        )

        assert (
            "is_next"
            not in pillar
        )


def test_chart_current_luck_target_datetime_accepts_jst_aware():
    """
    JST aware datetime を指定しても
    current_luck を計算できることを確認します。
    """
    request = make_verified_request()

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

    assert (
        result[
            "current_luck"
        ][
            "method"
        ]
        == "current_luck_v1"
    )


def test_chart_current_luck_target_datetime_invalid_type():
    """
    target_datetime が datetime 以外なら
    TypeError になることを確認します。
    """
    request = make_verified_request()

    with pytest.raises(
        TypeError
    ):
        calculate_chart(
            request,
            target_datetime=(
                "2026-08-10 15:36"
            ),
        )


def test_chart_current_luck_default_target_works():
    """
    target_datetime=None の通常API経路でも
    current_luck が生成されることを確認します。

    現在時刻依存なので具体的な大運番号は固定しません。
    """
    request = make_verified_request()

    result = calculate_chart(
        request
    )

    assert (
        "current_luck"
        in result
    )

    assert (
        result[
            "current_luck"
        ][
            "method"
        ]
        == "current_luck_v1"
    )


def test_chart_current_luck_verified_chart_is_preserved():
    """
    current_luck 統合後も、
    既存の検証命式が変わらないことを確認します。
    """
    result = (
        calculate_verified_chart_with_current_luck()
    )

    assert (
        result[
            "chart"
        ][
            "year"
        ][
            "pillar"
        ]
        == "乙丑"
    )

    assert (
        result[
            "chart"
        ][
            "month"
        ][
            "pillar"
        ]
        == "癸未"
    )

    assert (
        result[
            "chart"
        ][
            "day"
        ][
            "pillar"
        ]
        == "乙巳"
    )

    assert (
        result[
            "chart"
        ][
            "hour"
        ][
            "pillar"
        ]
        == "丁亥"
    )


def test_chart_current_luck_preserves_useful_gods_v3():
    """
    current_luck 統合後も
    useful_gods_v3 が維持されることを確認します。
    """
    result = (
        calculate_verified_chart_with_current_luck()
    )

    assert (
        result[
            "useful_gods"
        ][
            "method"
        ]
        == "useful_gods_v3"
    )


def test_chart_current_luck_preserves_luck_pillars_v2():
    """
    current_luck 統合後も
    luck_pillars_v2 が維持されることを確認します。
    """
    result = (
        calculate_verified_chart_with_current_luck()
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
            "luck_pillars"
        ][
            "pillar_count"
        ]
        == 10
    )

# ============================================================
# Annual Luck v1 Integration Tests
# ============================================================


def test_chart_contains_annual_luck():
    """
    calculate_chart() の戻り値に
    annual_luck が含まれることを確認します。
    """
    result = (
        calculate_verified_chart_with_current_luck()
    )

    assert "annual_luck" in result

    assert isinstance(
        result[
            "annual_luck"
        ],
        dict,
    )


def test_chart_annual_luck_required_keys():
    """
    annual_luck_v1 の主要キーが
    chart 統合後も存在することを確認します。
    """
    result = (
        calculate_verified_chart_with_current_luck()
    )

    annual_luck = result[
        "annual_luck"
    ]

    required_keys = {
        "year",
        "ganzhi",
        "stem",
        "branch",
        "stem_element",
        "stem_yin_yang",
        "branch_element",
        "day_master_stem",
        "day_master_element",
        "stem_ten_god",
        "twelve_stage",
        "hidden_stems",
        "main_hidden_stem",
        "main_hidden_stem_ten_god",
        "main_hidden_stem_element",
        "hidden_stem_ten_gods",
        "stem_useful_relation",
        "branch_useful_relation",
        "current_luck_relation",
        "reasoning",
        "evidence",
        "method",
        "status",
        "notes",
        "target_datetime",
        "calendar_year",
        "effective_year",
        "year_boundary_applied",
        "year_boundary_rule",
    }

    assert required_keys.issubset(
        annual_luck.keys()
    )


def test_chart_annual_luck_v1_metadata():
    """
    annual_luck_v1 の method / status を確認します。
    """
    result = (
        calculate_verified_chart_with_current_luck()
    )

    annual_luck = result[
        "annual_luck"
    ]

    assert (
        annual_luck[
            "method"
        ]
        == "annual_luck_v1"
    )

    assert (
        annual_luck[
            "status"
        ]
        == "provisional_annual_luck_v1"
    )

    assert isinstance(
        annual_luck[
            "notes"
        ],
        list,
    )

    assert (
        len(
            annual_luck[
                "notes"
            ]
        )
        >= 1
    )


def test_chart_annual_luck_verified_2026_ganzhi():
    """
    固定 target_datetime が 2026-08-10 のため、
    歳運が丙午になることを確認します。
    """
    result = (
        calculate_verified_chart_with_current_luck()
    )

    annual_luck = result[
        "annual_luck"
    ]

    assert (
        annual_luck[
            "calendar_year"
        ]
        == 2026
    )

    assert (
        annual_luck[
            "effective_year"
        ]
        == 2026
    )

    assert (
        annual_luck[
            "year"
        ]
        == 2026
    )

    assert (
        annual_luck[
            "ganzhi"
        ]
        == "丙午"
    )

    assert (
        annual_luck[
            "stem"
        ]
        == "丙"
    )

    assert (
        annual_luck[
            "branch"
        ]
        == "午"
    )


def test_chart_annual_luck_verified_2026_elements():
    """
    丙・午ともに火であることを確認します。
    """
    result = (
        calculate_verified_chart_with_current_luck()
    )

    annual_luck = result[
        "annual_luck"
    ]

    assert (
        annual_luck[
            "stem_element"
        ]
        == "火"
    )

    assert (
        annual_luck[
            "branch_element"
        ]
        == "火"
    )

    assert (
        annual_luck[
            "stem_yin_yang"
        ]
        == "陽"
    )


def test_chart_annual_luck_matches_day_master():
    """
    annual_luck の日主情報が
    chart 本体と一致することを確認します。
    """
    result = (
        calculate_verified_chart_with_current_luck()
    )

    annual_luck = result[
        "annual_luck"
    ]

    assert (
        annual_luck[
            "day_master_stem"
        ]
        == result[
            "day_master"
        ][
            "stem"
        ]
    )

    assert (
        annual_luck[
            "day_master_stem"
        ]
        == "乙"
    )

    assert (
        annual_luck[
            "day_master_element"
        ]
        == "木"
    )


def test_chart_annual_luck_verified_2026_ten_god():
    """
    乙日主に対する2026年の丙は
    傷官になることを確認します。
    """
    result = (
        calculate_verified_chart_with_current_luck()
    )

    assert (
        result[
            "annual_luck"
        ][
            "stem_ten_god"
        ]
        == "傷官"
    )


def test_chart_annual_luck_verified_2026_twelve_stage():
    """
    乙日主 × 午 = 長生を確認します。
    """
    result = (
        calculate_verified_chart_with_current_luck()
    )

    assert (
        result[
            "annual_luck"
        ][
            "twelve_stage"
        ]
        == "長生"
    )


def test_chart_annual_luck_hidden_stems_exist():
    """
    歳運地支の蔵干情報が
    chart 統合後も保持されることを確認します。
    """
    result = (
        calculate_verified_chart_with_current_luck()
    )

    annual_luck = result[
        "annual_luck"
    ]

    assert isinstance(
        annual_luck[
            "hidden_stems"
        ],
        list,
    )

    assert (
        len(
            annual_luck[
                "hidden_stems"
            ]
        )
        >= 1
    )

    assert (
        annual_luck[
            "main_hidden_stem"
        ]
        in annual_luck[
            "hidden_stems"
        ]
    )


def test_chart_annual_luck_hidden_stem_ten_gods_consistent():
    """
    蔵干数と蔵干通変星データ数が
    一致することを確認します。
    """
    result = (
        calculate_verified_chart_with_current_luck()
    )

    annual_luck = result[
        "annual_luck"
    ]

    assert (
        len(
            annual_luck[
                "hidden_stem_ten_gods"
            ]
        )
        == len(
            annual_luck[
                "hidden_stems"
            ]
        )
    )

    for item in annual_luck[
        "hidden_stem_ten_gods"
    ]:
        assert {
            "stem",
            "ten_god",
            "element",
            "yin_yang",
        }.issubset(
            item.keys()
        )


def test_chart_annual_luck_uses_same_target_datetime():
    """
    current_luck と annual_luck が
    同じ固定基準日時から計算されることを確認します。
    """
    result = (
        calculate_verified_chart_with_current_luck()
    )

    annual_luck = result[
        "annual_luck"
    ]

    assert (
        annual_luck[
            "target_datetime"
        ]
        == (
            CURRENT_LUCK_TARGET_DATETIME
            .isoformat()
        )
    )


def test_chart_annual_luck_year_boundary_metadata():
    """
    歳運の立春境界metadataを確認します。
    """
    result = (
        calculate_verified_chart_with_current_luck()
    )

    annual_luck = result[
        "annual_luck"
    ]

    assert (
        annual_luck[
            "year_boundary_applied"
        ]
        is True
    )

    assert (
        annual_luck[
            "year_boundary_rule"
        ]
        == "暫定：立春2月4日00:00"
    )


def test_chart_annual_luck_useful_relations_exist():
    """
    useful_gods_v3 との関係評価が
    歳運へ統合されていることを確認します。
    """
    result = (
        calculate_verified_chart_with_current_luck()
    )

    annual_luck = result[
        "annual_luck"
    ]

    relation_keys = {
        "is_useful",
        "is_primary_useful",
        "is_unfavorable",
        "priority",
        "relationship",
    }

    assert relation_keys.issubset(
        annual_luck[
            "stem_useful_relation"
        ].keys()
    )

    assert relation_keys.issubset(
        annual_luck[
            "branch_useful_relation"
        ].keys()
    )


def test_chart_annual_luck_current_luck_relation_exists():
    """
    current_luck_v1 との関係評価が
    annual_luck に含まれることを確認します。
    """
    result = (
        calculate_verified_chart_with_current_luck()
    )

    relation = result[
        "annual_luck"
    ][
        "current_luck_relation"
    ]

    required_keys = {
        "has_current_luck",
        "current_luck_ganzhi",
        "current_luck_stem_element",
        "current_luck_branch_element",
        "stem_element_relation",
        "branch_element_relation",
        "status",
    }

    assert required_keys.issubset(
        relation.keys()
    )

    assert (
        relation[
            "has_current_luck"
        ]
        is True
    )

    assert (
        relation[
            "status"
        ]
        == "evaluated"
    )


def test_chart_annual_luck_current_luck_ganzhi_matches():
    """
    annual_luck 側に記録された現在大運干支が、
    current_luck 本体と一致することを確認します。
    """
    result = (
        calculate_verified_chart_with_current_luck()
    )

    annual_relation = result[
        "annual_luck"
    ][
        "current_luck_relation"
    ]

    current_pillar = result[
        "current_luck"
    ][
        "current_luck_pillar"
    ]

    assert (
        annual_relation[
            "current_luck_ganzhi"
        ]
        == current_pillar[
            "ganzhi"
        ]
    )

    assert (
        annual_relation[
            "current_luck_index"
        ]
        == current_pillar[
            "index"
        ]
    )


def test_chart_annual_luck_evidence_consistency():
    """
    evidence が上位の歳運結果と
    一致することを確認します。
    """
    result = (
        calculate_verified_chart_with_current_luck()
    )

    annual_luck = result[
        "annual_luck"
    ]

    evidence = annual_luck[
        "evidence"
    ]

    assert (
        evidence[
            "year"
        ]
        == annual_luck[
            "year"
        ]
    )

    assert (
        evidence[
            "ganzhi"
        ]
        == annual_luck[
            "ganzhi"
        ]
    )

    assert (
        evidence[
            "day_master_stem"
        ]
        == annual_luck[
            "day_master_stem"
        ]
    )

    assert (
        evidence[
            "stem_ten_god"
        ]
        == annual_luck[
            "stem_ten_god"
        ]
    )

    assert (
        evidence[
            "twelve_stage"
        ]
        == annual_luck[
            "twelve_stage"
        ]
    )


def test_chart_annual_luck_reasoning_exists():
    """
    AI鑑定前段階の reasoning が
    保持されていることを確認します。
    """
    result = (
        calculate_verified_chart_with_current_luck()
    )

    reasoning = result[
        "annual_luck"
    ][
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
        >= 5
    )

    joined = "".join(
        reasoning
    )

    assert "2026" in joined
    assert "丙午" in joined
    assert "傷官" in joined
    assert "長生" in joined


def test_chart_annual_luck_matches_direct_engine_call():
    """
    chart.py で生成した annual_luck と、
    annual_luck エンジンを同条件で直接呼んだ結果が
    完全一致することを確認します。
    """
    result = (
        calculate_verified_chart_with_current_luck()
    )

    expected = (
        calculate_annual_luck_for_datetime(
            target_datetime=(
                CURRENT_LUCK_TARGET_DATETIME
            ),
            day_master_stem=result[
                "day_master"
            ][
                "stem"
            ],
            useful_gods=result[
                "useful_gods"
            ],
            current_luck=result[
                "current_luck"
            ],
        )
    )

    assert (
        result[
            "annual_luck"
        ]
        == expected
    )


def test_chart_annual_luck_fixed_target_is_reproducible():
    """
    同じ target_datetime なら
    annual_luck の結果が完全一致することを確認します。
    """
    request = make_verified_request()

    first = calculate_chart(
        request,
        target_datetime=(
            CURRENT_LUCK_TARGET_DATETIME
        ),
    )

    second = calculate_chart(
        request,
        target_datetime=(
            CURRENT_LUCK_TARGET_DATETIME
        ),
    )

    assert (
        first[
            "annual_luck"
        ]
        == second[
            "annual_luck"
        ]
    )


def test_chart_annual_luck_before_lichun():
    """
    2026-02-03 23:59 は暫定立春前なので、
    2025年乙巳として扱うことを確認します。
    """
    request = make_verified_request()

    result = calculate_chart(
        request,
        target_datetime=datetime(
            2026,
            2,
            3,
            23,
            59,
        ),
    )

    annual_luck = result[
        "annual_luck"
    ]

    assert (
        annual_luck[
            "calendar_year"
        ]
        == 2026
    )

    assert (
        annual_luck[
            "effective_year"
        ]
        == 2025
    )

    assert (
        annual_luck[
            "year"
        ]
        == 2025
    )

    assert (
        annual_luck[
            "ganzhi"
        ]
        == "乙巳"
    )


def test_chart_annual_luck_at_lichun():
    """
    2026-02-04 00:00 は暫定立春境界なので、
    2026年丙午へ切り替わることを確認します。
    """
    request = make_verified_request()

    result = calculate_chart(
        request,
        target_datetime=datetime(
            2026,
            2,
            4,
            0,
            0,
        ),
    )

    annual_luck = result[
        "annual_luck"
    ]

    assert (
        annual_luck[
            "effective_year"
        ]
        == 2026
    )

    assert (
        annual_luck[
            "ganzhi"
        ]
        == "丙午"
    )


def test_chart_annual_luck_accepts_jst_aware_target():
    """
    JST aware datetime でも
    annual_luck が計算できることを確認します。
    """
    request = make_verified_request()

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

    annual_luck = result[
        "annual_luck"
    ]

    assert (
        annual_luck[
            "ganzhi"
        ]
        == "丙午"
    )

    assert (
        annual_luck[
            "method"
        ]
        == "annual_luck_v1"
    )


def test_chart_annual_luck_preserves_verified_chart():
    """
    annual_luck 統合後も既存検証命式が
    変化しないことを確認します。
    """
    result = (
        calculate_verified_chart_with_current_luck()
    )

    assert (
        result[
            "chart"
        ][
            "year"
        ][
            "pillar"
        ]
        == "乙丑"
    )

    assert (
        result[
            "chart"
        ][
            "month"
        ][
            "pillar"
        ]
        == "癸未"
    )

    assert (
        result[
            "chart"
        ][
            "day"
        ][
            "pillar"
        ]
        == "乙巳"
    )

    assert (
        result[
            "chart"
        ][
            "hour"
        ][
            "pillar"
        ]
        == "丁亥"
    )


def test_chart_annual_luck_preserves_useful_gods_v3():
    """
    annual_luck 統合後も useful_gods_v3 が
    維持されることを確認します。
    """
    result = (
        calculate_verified_chart_with_current_luck()
    )

    assert (
        result[
            "useful_gods"
        ][
            "method"
        ]
        == "useful_gods_v3"
    )


def test_chart_annual_luck_preserves_luck_pillars_v2():
    """
    annual_luck 統合後も luck_pillars_v2 が
    維持されることを確認します。
    """
    result = (
        calculate_verified_chart_with_current_luck()
    )

    assert (
        result[
            "luck_pillars"
        ][
            "method"
        ]
        == "luck_pillars_v2"
    )


def test_chart_annual_luck_preserves_current_luck_v1():
    """
    annual_luck 統合後も current_luck_v1 が
    維持されることを確認します。
    """
    result = (
        calculate_verified_chart_with_current_luck()
    )

    assert (
        result[
            "current_luck"
        ][
            "method"
        ]
        == "current_luck_v1"
    )
