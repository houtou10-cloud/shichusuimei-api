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
# Luck Pillars Integration Tests
# ============================================================


def test_chart_contains_luck_pillars():
    """
    calculate_chart() の結果に
    大運計算結果が含まれることを確認します。
    """
    request = make_verified_request()

    result = calculate_chart(request)

    assert "luck_pillars" in result

    luck_pillars = result["luck_pillars"]

    assert isinstance(
        luck_pillars,
        dict,
    )


def test_chart_luck_pillars_required_keys():
    """
    luck_pillars が統合結果として必要な
    基本キーを持つことを確認します。
    """
    request = make_verified_request()

    result = calculate_chart(request)

    luck_pillars = result[
        "luck_pillars"
    ]

    required_keys = {
        "direction",
        "direction_label",
        "start_age",
        "start_age_detail",
        "pillars",
        "method",
        "status",
        "notes",
    }

    assert required_keys.issubset(
        luck_pillars.keys()
    )


def test_chart_luck_pillars_v2_metadata():
    """
    chart 統合後も luck_pillars_v2 の
    metadata が維持されることを確認します。
    """
    request = make_verified_request()

    result = calculate_chart(request)

    luck_pillars = result[
        "luck_pillars"
    ]

    assert (
        luck_pillars["method"]
        == "luck_pillars_v2"
    )

    assert isinstance(
        luck_pillars["status"],
        str,
    )

    assert isinstance(
        luck_pillars["notes"],
        list,
    )


def test_chart_luck_pillars_direction_exists():
    """
    大運の順行・逆行が
    正しく統合されていることを確認します。
    """
    request = make_verified_request()

    result = calculate_chart(request)

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
        "direction_label"
    ] in {
        "順行",
        "逆行",
    }


def test_chart_luck_pillars_direction_label_consistency():
    """
    direction と direction_label の
    対応が一致することを確認します。
    """
    request = make_verified_request()

    result = calculate_chart(request)

    luck_pillars = result[
        "luck_pillars"
    ]

    direction = luck_pillars[
        "direction"
    ]

    direction_label = luck_pillars[
        "direction_label"
    ]

    expected = {
        "forward": "順行",
        "backward": "逆行",
    }

    assert (
        direction_label
        == expected[direction]
    )


def test_chart_luck_pillars_start_age_exists():
    """
    起運年齢が存在し、
    数値として扱えることを確認します。
    """
    request = make_verified_request()

    result = calculate_chart(request)

    luck_pillars = result[
        "luck_pillars"
    ]

    start_age = luck_pillars[
        "start_age"
    ]

    assert isinstance(
        start_age,
        (int, float),
    )

    assert start_age >= 0


def test_chart_luck_pillars_start_age_is_reasonable():
    """
    起運年齢が現実的な範囲に
    収まっていることを確認します。

    四柱推命の起運計算として、
    異常値を検出するための
    integration guard です。
    """
    request = make_verified_request()

    result = calculate_chart(request)

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


def test_chart_luck_pillars_start_age_detail_exists():
    """
    起運計算の詳細情報が
    保存されていることを確認します。
    """
    request = make_verified_request()

    result = calculate_chart(request)

    detail = result[
        "luck_pillars"
    ][
        "start_age_detail"
    ]

    assert isinstance(
        detail,
        dict,
    )

    assert len(detail) >= 1


def test_chart_luck_pillars_has_multiple_pillars():
    """
    大運が複数期間生成されることを
    確認します。
    """
    request = make_verified_request()

    result = calculate_chart(request)

    pillars = result[
        "luck_pillars"
    ][
        "pillars"
    ]

    assert isinstance(
        pillars,
        list,
    )

    assert len(pillars) >= 8


def test_chart_luck_pillars_generates_ten_periods():
    """
    現在の実装方針では
    大運10本を生成することを確認します。
    """
    request = make_verified_request()

    result = calculate_chart(request)

    pillars = result[
        "luck_pillars"
    ][
        "pillars"
    ]

    assert len(pillars) == 10


def test_chart_luck_pillars_each_item_is_dict():
    """
    各大運が辞書形式で
    格納されていることを確認します。
    """
    request = make_verified_request()

    result = calculate_chart(request)

    pillars = result[
        "luck_pillars"
    ][
        "pillars"
    ]

    assert all(
        isinstance(
            pillar,
            dict,
        )
        for pillar in pillars
    )


def test_chart_luck_pillars_each_item_has_pillar():
    """
    各大運に干支が存在することを
    確認します。
    """
    request = make_verified_request()

    result = calculate_chart(request)

    pillars = result[
        "luck_pillars"
    ][
        "pillars"
    ]

    for pillar in pillars:
        assert "pillar" in pillar

        assert isinstance(
            pillar["pillar"],
            str,
        )

        assert len(
            pillar["pillar"]
        ) == 2


def test_chart_luck_pillars_each_item_has_stem_and_branch():
    """
    各大運の天干・地支が
    保存されていることを確認します。
    """
    request = make_verified_request()

    result = calculate_chart(request)

    pillars = result[
        "luck_pillars"
    ][
        "pillars"
    ]

    for pillar in pillars:
        assert "stem" in pillar
        assert "branch" in pillar

        assert isinstance(
            pillar["stem"],
            str,
        )

        assert isinstance(
            pillar["branch"],
            str,
        )

        assert len(
            pillar["stem"]
        ) == 1

        assert len(
            pillar["branch"]
        ) == 1


def test_chart_luck_pillars_pillar_matches_stem_branch():
    """
    pillar が stem + branch と
    一致することを確認します。
    """
    request = make_verified_request()

    result = calculate_chart(request)

    pillars = result[
        "luck_pillars"
    ][
        "pillars"
    ]

    for pillar in pillars:
        assert (
            pillar["pillar"]
            == (
                pillar["stem"]
                + pillar["branch"]
            )
        )


def test_chart_luck_pillars_each_item_has_index():
    """
    大運番号が連続していることを
    確認します。
    """
    request = make_verified_request()

    result = calculate_chart(request)

    pillars = result[
        "luck_pillars"
    ][
        "pillars"
    ]

    indexes = [
        pillar["index"]
        for pillar in pillars
    ]

    assert indexes == list(
        range(
            1,
            len(pillars) + 1,
        )
    )


def test_chart_luck_pillars_age_ranges_are_ordered():
    """
    大運の年齢範囲が
    時系列順になっていることを確認します。
    """
    request = make_verified_request()

    result = calculate_chart(request)

    pillars = result[
        "luck_pillars"
    ][
        "pillars"
    ]

    previous_start_age = None

    for pillar in pillars:
        assert "start_age" in pillar
        assert "end_age" in pillar

        start_age = pillar[
            "start_age"
        ]

        end_age = pillar[
            "end_age"
        ]

        assert (
            start_age
            <= end_age
        )

        if previous_start_age is not None:
            assert (
                start_age
                > previous_start_age
            )

        previous_start_age = start_age


def test_chart_luck_pillars_are_ten_year_intervals():
    """
    各大運の開始年齢が
    10年ずつ進むことを確認します。
    """
    request = make_verified_request()

    result = calculate_chart(request)

    pillars = result[
        "luck_pillars"
    ][
        "pillars"
    ]

    for previous, current in zip(
        pillars,
        pillars[1:],
    ):
        difference = (
            current["start_age"]
            - previous["start_age"]
        )

        assert round(
            difference,
            6,
        ) == 10.0


def test_chart_luck_pillars_day_master_consistency():
    """
    luck_pillars 内の日主情報がある場合、
    chart の日主と一致することを確認します。
    """
    request = make_verified_request()

    result = calculate_chart(request)

    luck_pillars = result[
        "luck_pillars"
    ]

    if "day_master_stem" in luck_pillars:
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


def test_chart_luck_pillars_month_pillar_consistency():
    """
    luck_pillars 内に基準月柱がある場合、
    chart の月柱と一致することを確認します。
    """
    request = make_verified_request()

    result = calculate_chart(request)

    luck_pillars = result[
        "luck_pillars"
    ]

    if "month_pillar" in luck_pillars:
        assert (
            luck_pillars[
                "month_pillar"
            ]
            == result[
                "chart"
            ][
                "month"
            ][
                "pillar"
            ]
        )


def test_chart_luck_pillars_verified_chart():
    """
    1985-07-17 21:50 石川県女性の
    検証命式で大運が正常に
    統合されることを確認します。
    """
    request = make_verified_request()

    result = calculate_chart(request)

    assert (
        result["chart"]["year"]["pillar"]
        == "乙丑"
    )

    assert (
        result["chart"]["month"]["pillar"]
        == "癸未"
    )

    assert (
        result["chart"]["day"]["pillar"]
        == "乙巳"
    )

    assert (
        result["chart"]["hour"]["pillar"]
        == "丁亥"
    )

    luck_pillars = result[
        "luck_pillars"
    ]

    assert (
        luck_pillars["method"]
        == "luck_pillars_v2"
    )

    assert len(
        luck_pillars["pillars"]
    ) == 10


def test_chart_luck_pillars_notes_exist():
    """
    大運計算に関する注記が
    最低1件存在することを確認します。
    """
    request = make_verified_request()

    result = calculate_chart(request)

    notes = result[
        "luck_pillars"
    ][
        "notes"
    ]

    assert isinstance(
        notes,
        list,
    )

    assert len(notes) >= 1


def test_chart_luck_pillars_no_duplicate_pillars():
    """
    10本の大運干支が
    不自然に重複していないことを確認します。
    """
    request = make_verified_request()

    result = calculate_chart(request)

    pillars = result[
        "luck_pillars"
    ][
        "pillars"
    ]

    pillar_names = [
        pillar["pillar"]
        for pillar in pillars
    ]

    assert (
        len(pillar_names)
        == len(set(pillar_names))
    )
