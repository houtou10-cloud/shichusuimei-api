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

    # 1985-07-17 21:50 石川県の正式命式は
    # 乙丑 / 癸未 / 丁巳 / 辛亥、日主は丁。
    # 月支「未」の蔵干は己・丁・乙で、
    # 乙が年干に透干するため偏印格を
    # primary_candidate とする。
    assert (
        pattern_candidates[
            "candidate_count"
        ]
        == 2
    )

    primary = pattern_candidates[
        "primary_candidate"
    ]

    assert primary is not None

    assert (
        primary["pattern"]
        == "偏印格"
    )

    assert (
        primary["technical_pattern"]
        == "indirect_resource"
    )

    assert (
        primary["pattern_group"]
        == "standard_pattern"
    )

    assert (
        primary["source"]
        == "month_exposed_hidden_stem"
    )

    assert (
        primary["selection_rule"]
        == "exposed_month_hidden_stem_priority_v1"
    )

    assert primary["month_branch"] == "未"
    assert primary["month_main_hidden_stem"] == "己"
    assert primary["selected_hidden_stem"] == "乙"
    assert primary["selected_hidden_stem_rank"] == 3
    assert primary["selected_is_main_hidden_stem"] is False
    assert primary["ten_god"] == "偏印"
    assert primary["is_exposed"] is True
    assert primary["exposure_positions"] == ["year"]
    assert primary["confidence"] == "high"
    assert primary["candidate_status"] == "provisional_candidate"
    assert primary["is_provisional"] is True

    assert (
        pattern_candidates[
            "candidate_groups"
        ]
        == {
            "standard_pattern": 1,
            "special_month_pattern": 1,
        }
    )

    assert (
        pattern_candidates[
            "has_school_rule_candidate"
        ]
        is True
    )

    month_context = pattern_candidates[
        "month_context"
    ]

    assert month_context["month_stem"] == "癸"
    assert month_context["month_branch"] == "未"
    assert month_context["hidden_stems"] == [
        "己",
        "丁",
        "乙",
    ]
    assert month_context["main_hidden_stem"] == "己"
    assert (
        month_context[
            "main_hidden_stem_ten_god"
        ]
        == "食神"
    )

    sources = month_context[
        "standard_pattern_sources"
    ]

    assert [
        source["stem"]
        for source in sources
    ] == ["己", "丁", "乙"]

    assert sources[0]["ten_god"] == "食神"
    assert sources[0]["is_exposed"] is False
    assert sources[1]["ten_god"] == "比肩"
    assert sources[1]["is_standard_pattern"] is False
    assert sources[2]["ten_god"] == "偏印"
    assert sources[2]["is_exposed"] is True
    assert sources[2]["exposure_positions"] == ["year"]

    assert (
        pattern_candidates[
            "day_master_stem"
        ]
        == "丁"
    )

    assert (
        pattern_candidates[
            "overall_status"
        ]
        == "candidate_with_school_rule"
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

    assert len(
        pattern_candidates[
            "notes"
        ]
    ) >= 1

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
        primary["month_branch"]
        == month["branch"]
    )

    assert (
        primary["month_main_hidden_stem"]
        == month["main_hidden_stem"]
    )

    # 透干蔵干優先ルールでは、primary.ten_god は
    # 月支主蔵干の十神と一致する必要はない。
    # 実際に選択された蔵干とその十神が
    # 月柱データ内で整合していることを確認する。
    assert (
        primary["selected_hidden_stem"]
        in month["hidden_stems"]
    )

    selected_data = next(
        item
        for item in month[
            "hidden_stem_ten_gods"
        ]
        if item["stem"]
        == primary[
            "selected_hidden_stem"
        ]
    )

    assert (
        primary["ten_god"]
        == selected_data["ten_god"]
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

    candidates = result[
        "pattern_candidates"
    ]

    assert isinstance(
        judgment,
        dict,
    )

    assert judgment["has_pattern_candidate"] is True
    assert judgment["has_pattern"] is True
    assert judgment["judgment_count"] >= 1

    primary_candidate = candidates[
        "primary_candidate"
    ]
    primary = judgment[
        "primary_judgment"
    ]

    assert primary is not None

    # pattern_judgment は pattern_candidates の
    # primary_candidate と同じ格局を主判定に用いる。
    assert (
        judgment["primary_pattern"]
        == primary_candidate["pattern"]
        == "偏印格"
    )

    assert (
        judgment["technical_pattern"]
        == primary_candidate[
            "technical_pattern"
        ]
        == "indirect_resource"
    )

    assert (
        primary["pattern"]
        == "偏印格"
    )

    assert (
        primary["technical_pattern"]
        == "indirect_resource"
    )

    assert primary["is_exposed"] is True
    assert primary["exposure_positions"] == ["year"]

    assert isinstance(
        primary["establishment_score"],
        (int, float),
    )
    assert 0.0 <= primary["establishment_score"] <= 100.0

    assert isinstance(
        primary["establishment_status"],
        str,
    )
    assert isinstance(
        primary["final_judgment"],
        str,
    )

    assert (
        judgment["judgment_count"]
        == len(judgment["judgments"])
    )

    assert (
        judgment["strong_count"]
        + judgment["possible_count"]
        + judgment["weakened_count"]
        + judgment["school_rule_count"]
        == judgment["judgment_count"]
    )

    assert isinstance(
        judgment["overall_judgment"],
        str,
    )
    assert isinstance(
        judgment["confidence"],
        str,
    )

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

    assert len(judgment["notes"]) >= 1

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
        factor["type"]
        for factor in primary[
            "breaking_factors"
        ]
    }

    # 現在のprimaryは年干へ透干した乙を根拠にする
    # 偏印格なので、「主蔵干が非透干」を破格要因として
    # 要求してはいけない。
    assert (
        "main_hidden_stem_not_exposed"
        not in breaking_types
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
