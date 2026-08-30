"""Dedicated tests for the opt-in Reading Context v2 projection."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from types import SimpleNamespace
from typing import Any, Mapping

import pytest

import engine.reading_context_v2 as reading_context_v2_module
from engine.chart import calculate_chart
from engine.consultation_context import build_consultation_context
from engine.reading_context import READING_SECTION_KEYS, build_reading_context
from engine.reading_context_v2 import (
    READING_CONTEXT_V2_EVIDENCE_SOURCES,
    READING_CONTEXT_V2_FACT_CODES,
    READING_CONTEXT_V2_METHOD,
    READING_CONTEXT_V2_SCHEMA_VERSION,
    READING_CONTEXT_V2_STATUS,
    READING_CONTEXT_V2_TOP_LEVEL_FIELDS,
    READING_CONTEXT_V2_VERSION,
    build_reading_context_v2,
    validate_reading_context_v2,
)


TARGET_DATETIME = datetime(2026, 8, 10, 15, 36)


def _request(*, birth_time: str | None) -> SimpleNamespace:
    return SimpleNamespace(
        birth_date="1985-07-17",
        birth_time=birth_time,
        birth_place="石川県",
        gender="female",
    )


def _resolve_path(value: Mapping[str, Any], path: str) -> Any:
    current: Any = value
    for part in path.split("."):
        current = current[part]
    return current


@pytest.fixture(scope="module")
def four_pillar_chart() -> dict[str, Any]:
    return calculate_chart(
        _request(birth_time="21:50"),
        target_datetime=TARGET_DATETIME,
    )


@pytest.fixture(scope="module")
def three_pillar_chart() -> dict[str, Any]:
    return calculate_chart(
        _request(birth_time=None),
        target_datetime=TARGET_DATETIME,
    )


@pytest.fixture(scope="module")
def four_pillar_v1(four_pillar_chart) -> dict[str, Any]:
    return build_reading_context(four_pillar_chart)


@pytest.fixture(scope="module")
def four_pillar_v2(four_pillar_chart) -> dict[str, Any]:
    return build_reading_context_v2(four_pillar_chart)


@pytest.fixture(scope="module")
def three_pillar_v2(three_pillar_chart) -> dict[str, Any]:
    return build_reading_context_v2(three_pillar_chart)


def test_four_pillar_builder_returns_valid_context(four_pillar_v2):
    assert four_pillar_v2["validation"] == {
        "valid": True,
        "errors": [],
        "missing_required_fields": [],
        "unknown_fields": [],
    }


def test_three_pillar_builder_returns_valid_context(three_pillar_v2):
    assert three_pillar_v2["validation"]["valid"] is True
    assert three_pillar_v2["birth_time_status"]["calculation_scope"] == (
        "three_pillars"
    )


def test_exact_required_top_level_fields(four_pillar_v2):
    assert tuple(four_pillar_v2) == READING_CONTEXT_V2_TOP_LEVEL_FIELDS
    assert len(four_pillar_v2) == 26


def test_fixed_schema_method_version_status(four_pillar_v2):
    assert four_pillar_v2["schema_version"] == READING_CONTEXT_V2_SCHEMA_VERSION
    assert four_pillar_v2["method"] == READING_CONTEXT_V2_METHOD
    assert four_pillar_v2["version"] == READING_CONTEXT_V2_VERSION
    assert four_pillar_v2["status"] == READING_CONTEXT_V2_STATUS
    assert four_pillar_v2["version"] == "reading_context_v2"


def test_null_and_empty_rules_for_absent_sources(four_pillar_chart):
    source = deepcopy(four_pillar_chart)
    source["input"].pop("timezone", None)
    source.pop("engine_metadata", None)
    source.pop("warnings", None)
    source.pop("uncertainty", None)
    for key in (
        "month_command",
        "weighted_month_command",
        "seasonal_strength",
        "integrated_month_strength",
        "root_strength",
        "weighted_root_strength",
        "branch_clashes",
        "branch_combinations",
        "branch_trines",
        "branch_punishments",
        "branch_harms",
        "branch_breaks",
        "branch_relation_strength",
    ):
        source.pop(key, None)

    context = build_reading_context_v2(source)

    assert context["engine_version"] is None
    assert context["subject"]["timezone"] is None
    assert context["month_command"] is None
    assert context["roots"] is None
    assert context["relations"] is None
    assert context["warnings"] == []
    assert context["uncertainty"] == []


def test_chart_mapping_preserves_v1_shared_values(
    four_pillar_v1,
    four_pillar_v2,
):
    assert four_pillar_v2["chart"] == four_pillar_v1["natal_chart"]


def test_unknown_hour_is_null(three_pillar_v2):
    assert three_pillar_v2["chart"]["pillars"]["hour"] is None


def test_unknown_pillar_sequence_hour_is_null(three_pillar_v2):
    assert three_pillar_v2["chart"]["pillar_sequence"][3] is None
    assert len(three_pillar_v2["chart"]["pillar_sequence"]) == 4


def test_fact_codes_are_allowlisted(four_pillar_v2):
    codes = [fact["code"] for fact in four_pillar_v2["facts"]]
    assert len(codes) == len(set(codes))
    assert set(codes).issubset(READING_CONTEXT_V2_FACT_CODES)


def test_fact_values_equal_context_path_values(four_pillar_v2):
    for fact in four_pillar_v2["facts"]:
        assert fact["context_path"] == fact["code"]
        assert fact["value"] == _resolve_path(
            four_pillar_v2,
            fact["context_path"],
        )


def test_interpretation_hints_are_exact_v1_projection(
    four_pillar_v1,
    four_pillar_v2,
):
    hints = four_pillar_v2["interpretation_hints"]
    assert [hint["section"] for hint in hints] == list(READING_SECTION_KEYS)
    for hint in hints:
        source = four_pillar_v1["reading_sections"][hint["section"]]
        assert hint["focus"] == source["focus"]
        assert hint["instruction"] == source["instruction"]


def test_consultation_absent_is_null(four_pillar_chart):
    context = build_reading_context_v2(four_pillar_chart)
    assert context["consultation"] is None


def test_empty_consultation_is_null(four_pillar_chart):
    consultation = build_consultation_context()
    context = build_reading_context_v2(
        four_pillar_chart,
        consultation_context=consultation,
    )
    assert consultation["has_consultation"] is False
    assert context["consultation"] is None


def test_consultation_present_is_exact_deep_copy(four_pillar_chart):
    consultation = build_consultation_context(
        concern="仕事について相談したい",
        desired_future="落ち着いて働きたい",
    )
    context = build_reading_context_v2(
        four_pillar_chart,
        consultation_context=consultation,
    )
    assert context["consultation"] == consultation
    assert context["consultation"] is not consultation


def test_warnings_are_exact_ordered_deep_copy(
    three_pillar_chart,
    three_pillar_v2,
):
    assert three_pillar_v2["warnings"] == three_pillar_chart["warnings"]
    assert three_pillar_v2["warnings"] is not three_pillar_chart["warnings"]


def test_uncertainty_is_exact_ordered_deep_copy(
    three_pillar_chart,
    three_pillar_v2,
):
    assert three_pillar_v2["uncertainty"] == three_pillar_chart["uncertainty"]
    assert three_pillar_v2["uncertainty"] is not three_pillar_chart["uncertainty"]


def test_source_version_is_null_when_source_has_no_version(four_pillar_v2):
    metadata = four_pillar_v2["source_metadata"]
    assert metadata["engine"]["version"] == "1.2"
    for key in (
        "five_elements",
        "roots",
        "strength",
        "relations",
        "pattern",
        "useful_gods",
        "luck_pillars",
        "current_luck",
        "annual_luck",
        "integrated_luck",
    ):
        assert metadata[key]["version"] is None
    for component in metadata["month_command"]["components"].values():
        assert component["version"] is None


def test_month_command_aggregate_metadata_is_null(four_pillar_v2):
    month = four_pillar_v2["source_metadata"]["month_command"]
    for key in ("source_path", "method", "version", "status"):
        assert month[key] is None


def test_month_command_component_metadata(four_pillar_v2):
    components = four_pillar_v2["source_metadata"]["month_command"][
        "components"
    ]
    assert tuple(components) == ("basic", "weighted", "seasonal", "integrated")
    assert components["basic"]["source_path"] == "month_command"
    assert components["basic"]["method"] == "month_branch_element_v1"
    assert components["weighted"]["method"] == "weighted_month_command_v1"
    assert components["seasonal"]["method"] == "seasonal_state_v1"
    assert components["integrated"]["method"] == (
        "integrated_month_strength_v1"
    )


def test_evidence_has_only_five_approved_categories(four_pillar_v2):
    expected = [category for category, _ in READING_CONTEXT_V2_EVIDENCE_SOURCES]
    assert [item["category"] for item in four_pillar_v2["evidence"]] == expected
    assert len(four_pillar_v2["evidence"]) == 5


def test_evidence_summary_is_null_and_full_tree_is_not_copied(four_pillar_v2):
    for item in four_pillar_v2["evidence"]:
        assert item["summary"] is None
        assert set(item) == {"category", "available", "source_path", "summary"}


def test_evidence_availability_comes_only_from_source(four_pillar_chart):
    source = deepcopy(four_pillar_chart)
    source["annual_luck"].pop("evidence")
    context = build_reading_context_v2(source)
    evidence = {item["category"]: item for item in context["evidence"]}
    assert evidence["annual_luck"]["available"] is False
    assert evidence["annual_luck"]["summary"] is None
    assert evidence["strength"]["available"] is True


def test_notes_are_exact_v1_deep_copy(four_pillar_v1, four_pillar_v2):
    assert four_pillar_v2["notes"] == four_pillar_v1["notes"]
    assert four_pillar_v2["notes"] is not four_pillar_v1["notes"]


def test_validator_non_mapping_raises_type_error():
    with pytest.raises(TypeError):
        validate_reading_context_v2([])  # type: ignore[arg-type]


def test_validator_unknown_field_returns_invalid_report(four_pillar_v2):
    context = deepcopy(four_pillar_v2)
    context["unsupported"] = True
    report = validate_reading_context_v2(context)
    assert report["valid"] is False
    assert report["unknown_fields"] == ["unsupported"]


def test_validator_missing_field_returns_invalid_report(four_pillar_v2):
    context = deepcopy(four_pillar_v2)
    context.pop("facts")
    report = validate_reading_context_v2(context)
    assert report["valid"] is False
    assert report["missing_required_fields"] == ["facts"]


def test_validator_bad_type_returns_invalid_report(four_pillar_v2):
    context = deepcopy(four_pillar_v2)
    context["warnings"] = "not-an-array"
    report = validate_reading_context_v2(context)
    assert report["valid"] is False
    assert "type:warnings:array" in report["errors"]


def test_validator_bad_hour_structure_returns_invalid_report(
    four_pillar_v2,
):
    context = deepcopy(four_pillar_v2)
    context["chart"]["pillars"]["hour"] = None
    context["chart"]["pillar_sequence"][3] = None
    report = validate_reading_context_v2(context)
    assert report["valid"] is False
    assert "hour_rule:known_requires_hour" in report["errors"]


def test_builder_invalid_final_context_raises_value_error(
    four_pillar_chart,
    monkeypatch,
):
    invalid_report = {
        "valid": False,
        "errors": ["forced_invalid"],
        "missing_required_fields": [],
        "unknown_fields": [],
    }
    monkeypatch.setattr(
        reading_context_v2_module,
        "validate_reading_context_v2",
        lambda context: deepcopy(invalid_report),
    )
    with pytest.raises(ValueError, match="forced_invalid"):
        reading_context_v2_module.build_reading_context_v2(four_pillar_chart)


def test_builder_does_not_mutate_chart_source(four_pillar_chart):
    before = deepcopy(four_pillar_chart)
    build_reading_context_v2(four_pillar_chart)
    assert four_pillar_chart == before


def test_v1_context_is_unchanged_before_and_after_v2_build(four_pillar_chart):
    before = build_reading_context(four_pillar_chart)
    build_reading_context_v2(four_pillar_chart)
    after = build_reading_context(four_pillar_chart)
    assert after == before
