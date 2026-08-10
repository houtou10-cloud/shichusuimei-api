from types import SimpleNamespace

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
    assert result["chart"]["day"]["pillar"] == "丁巳"
    assert result["chart"]["hour"]["pillar"] == "壬寅"
    assert result["day_master"]["stem"] == "丁"


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
    assert result["chart"]["day"]["pillar"] == "丁巳"
    assert result["chart"]["hour"]["pillar"] == "丁未"


def test_chart_1985():
    request = make_verified_request()

    result = calculate_chart(request)

    assert result["chart"]["year"]["pillar"] == "乙丑"
    assert result["chart"]["month"]["pillar"] == "癸未"
    assert result["chart"]["day"]["pillar"] == "丁巳"
    assert result["chart"]["hour"]["pillar"] == "辛亥"


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
    assert result["chart"]["day"]["pillar"] == "丁巳"
    assert result["chart"]["hour"] is None

    assert any(
        "出生時間が不明" in warning
        for warning in result["warnings"]
    )



def test_chart_contains_hidden_stems_and_ten_gods():
    request = make_verified_request()
    result = calculate_chart(request)
    chart = result["chart"]

    # 蔵干そのものは地支に依存するため固定確認する。
    assert chart["year"]["hidden_stems"] == ["己", "癸", "辛"]
    assert chart["month"]["hidden_stems"] == ["己", "丁", "乙"]
    assert chart["day"]["hidden_stems"] == ["丙", "戊", "庚"]
    assert chart["hour"]["hidden_stems"] == ["壬", "甲"]

    assert chart["year"]["main_hidden_stem"] == "己"
    assert chart["month"]["main_hidden_stem"] == "己"
    assert chart["day"]["main_hidden_stem"] == "丙"
    assert chart["hour"]["main_hidden_stem"] == "壬"

    # 日柱は本人なので stem_ten_god は None。
    assert chart["day"]["stem_ten_god"] is None

    # 丁日主へ切り替わった現在の回帰基準。
    assert result["day_master"]["stem"] == "丁"

    # 通変星は必ず文字列として計算されていることを確認。
    for position in ("year", "month", "hour"):
        assert isinstance(chart[position]["stem_ten_god"], str)

    for position in ("year", "month", "day", "hour"):
        assert isinstance(
            chart[position]["main_hidden_stem_ten_god"],
            str,
        )


def test_chart_contains_twelve_stages():
    request = make_verified_request()
    result = calculate_chart(request)
    chart = result["chart"]

    valid_stages = {
        "長生", "沐浴", "冠帯", "建禄",
        "帝旺", "衰", "病", "死",
        "墓", "絶", "胎", "養",
    }

    for position in ("year", "month", "day", "hour"):
        assert chart[position]["twelve_stage"] in valid_stages

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

    # 最新の日柱基準（丁日主）での実出力。
    assert weighted["scores"] == {
        "木": 1.4,
        "火": 1.9,
        "土": 1.5,
        "金": 1.2,
        "水": 2.0,
    }

    assert round(sum(weighted["scores"].values()), 2) == weighted["total"]
    assert round(sum(weighted["percentages"].values()), 2) == 100.0
    assert weighted["method"] == "weighted_hidden_stems_v1"


def test_chart_contains_day_master_balance():
    request = make_verified_request()
    result = calculate_chart(request)
    balance = result["day_master_balance"]

    assert balance["day_stem"] == "丁"
    assert balance["day_element"] == "火"

    assert balance["day_stem"] == result["day_master"]["stem"]
    assert balance["supporting_score"] + balance["draining_score"] > 0
    assert round(
        balance["supporting_ratio"] + balance["draining_ratio"],
        2,
    ) == 100.0

    assert balance["method"] == "simple_element_relation_v1"
    assert balance["status"] == "classification_only"


def test_chart_contains_weighted_day_master_balance():
    request = make_verified_request()
    result = calculate_chart(request)
    balance = result["weighted_day_master_balance"]

    assert balance["day_stem"] == "丁"
    assert balance["day_element"] == "火"
    assert balance["day_stem"] == result["day_master"]["stem"]

    assert round(
        balance["supporting_score"] + balance["draining_score"],
        2,
    ) == result["weighted_five_elements"]["total"]

    assert round(
        balance["supporting_ratio"] + balance["draining_ratio"],
        2,
    ) == 100.0

    assert balance["method"] == "weighted_element_relation_v1"
    assert (
        balance["status"]
        == "provisional_weighted_classification"
    )


def test_chart_contains_root_strength():
    request = make_verified_request()
    result = calculate_chart(request)
    root_strength = result["root_strength"]

    assert root_strength["day_stem"] == "丁"
    assert root_strength["day_element"] == "火"
    assert root_strength["day_stem"] == result["day_master"]["stem"]

    assert isinstance(root_strength["has_root"], bool)
    assert root_strength["root_count"] == len(root_strength["roots"])
    assert root_strength["root_count"] == len(root_strength["root_positions"])

    assert root_strength["method"] == "hidden_stem_root_v1"
    assert root_strength["status"] == "simple_root_detection"


def test_chart_contains_weighted_root_strength():
    request = make_verified_request()
    result = calculate_chart(request)
    weighted_root = result["weighted_root_strength"]

    assert weighted_root["day_stem"] == "丁"
    assert weighted_root["day_element"] == "火"
    assert weighted_root["day_stem"] == result["day_master"]["stem"]

    assert isinstance(weighted_root["has_root"], bool)
    assert weighted_root["root_count"] == len(weighted_root["roots"])
    assert weighted_root["root_count"] == len(weighted_root["root_positions"])
    assert weighted_root["total_root_score"] >= 0.0

    assert weighted_root["method"] == "weighted_root_strength_v1"
    assert weighted_root["status"] == "provisional_weighted_roots"


def test_chart_contains_month_command():
    request = make_verified_request()
    result = calculate_chart(request)
    month_command = result["month_command"]

    assert month_command["day_stem"] == "丁"
    assert month_command["day_element"] == "火"
    assert month_command["month_branch"] == "未"
    assert month_command["month_element"] == "土"

    assert month_command["day_stem"] == result["day_master"]["stem"]
    assert isinstance(month_command["relationship"], str)
    assert isinstance(month_command["relationship_label"], str)
    assert month_command["effect"] in {"supporting", "draining", "neutral"}
    assert isinstance(month_command["supports_day_master"], bool)

    assert month_command["method"] == "month_branch_element_v1"
    assert month_command["status"] == "provisional_month_command"


def test_chart_contains_seasonal_strength():
    request = make_verified_request()
    result = calculate_chart(request)
    seasonal_strength = result["seasonal_strength"]

    assert seasonal_strength["day_stem"] == "丁"
    assert seasonal_strength["day_element"] == "火"
    assert seasonal_strength["month_branch"] == "未"
    assert seasonal_strength["state"] == "休"
    assert isinstance(seasonal_strength["score"], (int, float))

    assert seasonal_strength["method"] == "seasonal_state_v1"
    assert (
        seasonal_strength["status"]
        == "provisional_seasonal_strength"
    )


def test_chart_contains_strength_judgment():
    request = make_verified_request()
    result = calculate_chart(request)
    judgment = result["strength_judgment"]

    assert judgment["label"] == "かなり身弱寄り"
    assert 0.0 <= judgment["final_score"] <= 100.0
    assert 0.0 <= judgment["base_supporting_ratio"] <= 100.0

    assert isinstance(judgment["adjustments"], dict)
    assert "root_bonus" in judgment["adjustments"]
    assert "month_root_bonus" in judgment["adjustments"]
    assert "month_command_adjustment" in judgment["adjustments"]

    assert judgment["method"] == "provisional_strength_v1"
    assert judgment["status"] == "provisional_judgment"


def test_chart_contains_weighted_strength_judgment():
    request = make_verified_request()
    result = calculate_chart(request)
    judgment = result["weighted_strength_judgment"]

    # 最新CIで確認済みの丁日主基準スコア。
    assert judgment["final_score"] == 54.75
    assert 0.0 <= judgment["base_supporting_ratio"] <= 100.0

    assert isinstance(judgment["adjustments"], dict)
    assert "weighted_root_bonus" in judgment["adjustments"]
    assert "integrated_month_adjustment" in judgment["adjustments"]

    evidence = judgment["evidence"]
    assert evidence["seasonal_state"] == "休"
    assert isinstance(evidence["seasonal_score"], (int, float))
    assert round(
        evidence["month_supporting_ratio"]
        + evidence["month_draining_ratio"],
        2,
    ) == 100.0

    assert judgment["method"] == "weighted_provisional_strength_v3"
    assert judgment["status"] == "provisional_weighted_judgment"


def test_chart_contains_weighted_month_command():
    request = make_verified_request()
    result = calculate_chart(request)
    weighted_month_command = result["weighted_month_command"]

    assert weighted_month_command["day_stem"] == "丁"
    assert weighted_month_command["day_element"] == "火"
    assert weighted_month_command["month_branch"] == "未"

    assert round(
        weighted_month_command["supporting_ratio"]
        + weighted_month_command["draining_ratio"],
        2,
    ) == 100.0

    assert round(
        weighted_month_command["supporting_score"]
        + weighted_month_command["draining_score"],
        2,
    ) == 1.0

    assert isinstance(weighted_month_command["details"], list)
    assert len(weighted_month_command["details"]) >= 1

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
    integrated = result["integrated_month_strength"]

    assert integrated["seasonal_state"] == "休"
    assert isinstance(integrated["seasonal_score"], (int, float))

    assert round(
        integrated["supporting_ratio"]
        + integrated["draining_ratio"],
        2,
    ) == 100.0

    assert isinstance(integrated["hidden_stem_balance"], (int, float))
    assert isinstance(integrated["hidden_stem_adjustment"], (int, float))
    assert isinstance(integrated["integrated_score"], (int, float))

    assert integrated["method"] == "integrated_month_strength_v1"
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
    result = calculate_chart(request)
    pattern_candidates = result["pattern_candidates"]

    assert isinstance(pattern_candidates, dict)
    assert pattern_candidates["has_candidate"] is True
    assert pattern_candidates["candidate_count"] >= 1
    assert pattern_candidates["primary_candidate"] is not None

    primary = pattern_candidates["primary_candidate"]

    assert primary["pattern"] == "食神格"
    assert primary["technical_pattern"] == "eating_god"
    assert primary["pattern_group"] == "standard_pattern"
    assert primary["source"] == "month_main_hidden_stem"
    assert primary["month_branch"] == "未"
    assert primary["month_main_hidden_stem"] == "己"
    assert primary["ten_god"] == "食神"

    assert pattern_candidates["day_master_stem"] == "丁"
    assert pattern_candidates["day_master_stem"] == result["day_master"]["stem"]

    assert pattern_candidates["overall_status"] == "candidate_detected"
    assert pattern_candidates["method"] == "pattern_candidates_v1"
    assert pattern_candidates["status"] == "provisional_pattern_candidates"
    assert isinstance(pattern_candidates["notes"], list)

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
    result = calculate_chart(request)
    judgment = result["pattern_judgment"]

    assert isinstance(judgment, dict)
    assert judgment["has_pattern_candidate"] is True
    assert judgment["has_pattern"] is True
    assert judgment["judgment_count"] >= 1

    assert judgment["primary_pattern"] == "食神格"
    assert judgment["technical_pattern"] == "eating_god"
    assert judgment["primary_judgment"] is not None

    primary = judgment["primary_judgment"]
    assert primary["pattern"] == "食神格"
    assert primary["technical_pattern"] == "eating_god"
    assert primary["establishment_status"] in {
        "strong",
        "possible",
        "weakened",
        "requires_school_rule",
    }
    assert isinstance(primary["establishment_score"], (int, float))

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

