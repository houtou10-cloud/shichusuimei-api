"""Production-shape connection tests using saved results and synthetic records.

Synthetic records below are not source-text observations and do not extend fixtures.
"""

from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts.symbol_judgment_b_production_adapter import (
    ADAPTER_VERSION,
    DISPLAY_NAME,
    adapt_production_result,
    run_reference_evaluation,
)


GOLDEN = Path(__file__).parent / "golden" / "v1_1" / "charts" / "GC01_1985_ishikawa_female_verified.json"


def synthetic_production(pillars, *, primary="木", secondary=None, unfavorable=None,
                         great_luck="壬子", annual="癸亥"):
    secondary = ["火", "水"] if secondary is None else secondary
    unfavorable = ["土", "金"] if unfavorable is None else unfavorable
    return {
        "chart": {position: {"stem": ganzhi[0], "branch": ganzhi[1], "ganzhi": ganzhi}
                  for position, ganzhi in pillars.items()},
        "useful_gods": {
            "primary_useful_element": primary,
            "secondary_useful_elements": secondary,
            "support_balance": {"unfavorable_elements": unfavorable},
        },
        "current_luck": {
            "has_current_luck": great_luck is not None,
            "current_luck_pillar": None if great_luck is None else {
                "stem": great_luck[0], "branch": great_luck[1], "ganzhi": great_luck,
            },
        },
        "annual_luck": {"stem": annual[0], "branch": annual[1], "ganzhi": annual},
        "pattern_judgment": {"technical_pattern": "synthetic_standard_pattern_only"},
    }


NORMAL = synthetic_production(
    {"year": "甲辰", "month": "癸酉", "day": "丁亥", "hour": "乙巳"}
)


def test_saved_production_result_runs_end_to_end_without_mutation():
    source = json.loads(GOLDEN.read_text(encoding="utf-8"))
    before = deepcopy(source)
    result = run_reference_evaluation(source, enabled=True)
    assert result["status"] == "success"
    assert source == before == result["original_data"]
    adapted = result["adapter_result"]["input"]
    assert adapted["pillars"] == {"year": "乙丑", "month": "癸未", "day": "丁巳", "hour": "辛亥"}
    assert adapted["great_luck"] == "丁亥"
    assert adapted["annual"] == "丙午"
    assert result["display"]["display_name"] == DISPLAY_NAME
    assert result["display"]["items"]


def test_api_result_wrapper_is_supported_read_only():
    wrapped = {"result": deepcopy(NORMAL), "request_id": "synthetic"}
    before = deepcopy(wrapped)
    adapted = adapt_production_result(wrapped)
    assert adapted["status"] == "ok"
    assert adapted["input"]["pillars"]["day"] == "丁亥"
    assert wrapped == before


def test_adapter_never_uses_combined_ganzhi_to_guess_missing_stem_or_branch():
    missing_stem = deepcopy(NORMAL)
    del missing_stem["chart"]["year"]["stem"]
    missing_branch = deepcopy(NORMAL)
    del missing_branch["annual_luck"]["branch"]
    assert adapt_production_result(missing_stem)["reasons"] == ["chart_year_invalid_or_missing_stem"]
    assert adapt_production_result(missing_branch)["reasons"] == ["annual_luck_invalid_or_missing_branch"]


def test_adapter_holds_inconsistent_combined_ganzhi_and_missing_roles():
    mismatch = deepcopy(NORMAL)
    mismatch["current_luck"]["current_luck_pillar"]["ganzhi"] = "甲子"
    no_roles = deepcopy(NORMAL)
    del no_roles["useful_gods"]
    assert adapt_production_result(mismatch)["reasons"] == ["current_luck_pillar_ganzhi_mismatch"]
    assert adapt_production_result(no_roles)["reasons"] == ["missing_useful_gods"]


def test_adapter_holds_production_day_master_mismatch():
    mismatch = deepcopy(NORMAL)
    mismatch["day_master"] = {"stem": "甲"}
    assert adapt_production_result(mismatch)["reasons"] == ["day_master_mismatch"]


def test_standard_pattern_is_not_promoted_to_special_structure():
    adapted = adapt_production_result(NORMAL)
    assert "special_structure" not in adapted["input"]
    assert adapted["special_structure_source"] == "not_supplied"
    explicit = adapt_production_result(NORMAL, explicit_special_structure={"type": "従児格"})
    assert explicit["input"]["special_structure"] == {"type": "従児格"}
    assert explicit["special_structure_source"] == "explicit_caller_input"


@pytest.mark.parametrize("name,source,expected_strength", [
    ("strong", synthetic_production(
        {"year": "甲寅", "month": "乙卯", "day": "甲寅", "hour": "癸亥"},
        primary="金", secondary=["火", "土"], unfavorable=["木", "水"],
    ), "strong"),
    ("weak", synthetic_production(
        {"year": "庚申", "month": "辛酉", "day": "甲戌", "hour": "戊辰"},
        primary="水", secondary=["木"], unfavorable=["火", "土", "金"],
    ), "weak"),
])
def test_synthetic_strength_shapes_run_through_full_boundary(name, source, expected_strength):
    result = run_reference_evaluation(source, enabled=True)
    assert result["status"] == "success", name
    assert result["model_result"]["analysis"]["day_master_strength"] == expected_strength
    assert result["display"]["items"]


def test_synthetic_transformation_and_explicit_special_are_separate_paths():
    transformation = synthetic_production(
        {"year": "甲辰", "month": "己未", "day": "戊戌", "hour": "丙辰"},
        primary="土", secondary=["火"], unfavorable=["木", "金", "水"],
    )
    transformed = run_reference_evaluation(transformation, enabled=True)
    assert transformed["model_result"]["transformations"]["established_count"] == 1
    assert transformed["adapter_result"]["special_structure_source"] == "not_supplied"

    special_source = synthetic_production(
        {"year": "丙午", "month": "丁巳", "day": "甲午", "hour": "丙午"},
        primary="水", secondary=["木"], unfavorable=["火", "土", "金"],
    )
    special = run_reference_evaluation(
        special_source, enabled=True, explicit_special_structure={"type": "従児格"}
    )
    assert special["model_result"]["special_structure"]["status"] == "established"
    assert special["model_result"]["element_roles"]["overrides_element_roles"] is True


def test_periods_and_display_contract_do_not_hide_hold_rows():
    result = run_reference_evaluation(NORMAL, enabled=True)
    combined = next(item for item in result["model_result"]["evaluations"]
                    if item["target_type"] == "great_luck_annual")
    displayed = next(item for item in result["display"]["items"]
                     if item.get("target_type") == "great_luck_annual")
    assert displayed["symbol"] == combined["symbol"]
    assert displayed["applied_rules"] == combined["applied_rule_ids"]
    assert displayed["assumptions"]
    assert "転職・投資" in result["display"]["notice"]
    assert result["display"]["model_version"] == "yakumo-b-research-v1"


def test_unclassified_production_roles_have_short_japanese_hold_reason():
    source = deepcopy(NORMAL)
    source["useful_gods"]["support_balance"]["unfavorable_elements"] = []
    result = run_reference_evaluation(source, enabled=True)
    held = next(item for item in result["display"]["items"]
                if item["target_type"] == "five_element" and item["target"] == "土")
    assert held["symbol"] is None
    assert held["display_symbol"] == "判定保留"
    assert held["reason"] == "本番データに対象五行の喜忌分類がないため判定を保留しました。"


def test_competing_combination_returns_global_hold_and_preserves_source():
    source = synthetic_production(
        {"year": "甲辰", "month": "己未", "day": "甲子", "hour": "戊辰"},
        primary="土", secondary=["火"], unfavorable=["木", "金", "水"],
    )
    before = deepcopy(source)
    result = run_reference_evaluation(source, enabled=True)
    assert result["status"] == "hold"
    assert source == before == result["original_data"]
    item = result["display"]["items"][0]
    assert item["symbol"] is None and item["display_symbol"] == "判定保留"
    assert item["applied_rules"] == ["B.TRANSFORM.001"]


def test_invalid_input_and_adapter_hold_never_become_symbols():
    invalid = run_reference_evaluation([], enabled=True)
    missing = deepcopy(NORMAL)
    del missing["annual_luck"]
    held = run_reference_evaluation(missing, enabled=True)
    for result in (invalid, held):
        assert result["status"] == "hold"
        assert result["display"]["items"][0]["symbol"] is None
        assert result["display"]["items"][0]["display_symbol"] == "判定保留"


def test_evaluator_exception_is_caught_without_losing_original_data():
    source = deepcopy(NORMAL)

    def broken(_value):
        raise RuntimeError("synthetic evaluator failure")

    result = run_reference_evaluation(source, enabled=True, evaluator=broken)
    assert result["status"] == "error"
    assert result["error"]["type"] == "RuntimeError"
    assert result["original_data"] == source
    assert result["display"]["items"][0]["symbol"] is None
    assert "RuntimeError" in result["display"]["items"][0]["reason"]


def test_disabled_feature_does_not_call_adapter_or_evaluator():
    called = False

    def must_not_run(_value):
        nonlocal called
        called = True
        raise AssertionError("disabled evaluator was called")

    source = {"not": "a production result"}
    result = run_reference_evaluation(source, enabled=False, evaluator=must_not_run)
    assert called is False
    assert result["status"] == "disabled"
    assert result["adapter_result"] is None
    assert result["original_data"] == source
    assert result["display"]["items"][0]["symbol"] is None
    assert result["display"]["items"][0]["reason"] == "研究機能が無効です。Bモデルは実行していません。"


def test_adapter_version_is_explicit():
    assert ADAPTER_VERSION == "b_production_readonly_adapter_v1"
