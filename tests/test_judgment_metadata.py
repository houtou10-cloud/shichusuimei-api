"""Contract tests for the opt-in Common Judgment Metadata adapter."""

from copy import deepcopy
from datetime import datetime
from types import SimpleNamespace
from typing import Any

import pytest

import engine.judgment_metadata as judgment_metadata_module
from engine.chart import calculate_chart
from engine.judgment_metadata import (
    COMMON_JUDGMENT_COMPONENT_FIELDS,
    COMMON_JUDGMENT_COMPONENT_KEYS,
    COMMON_JUDGMENT_METADATA_SCHEMA_VERSION,
    COMMON_JUDGMENT_MONTH_COMMAND_COMPONENT_KEYS,
    COMMON_JUDGMENT_SOURCE_REGISTRY,
    COMMON_JUDGMENT_STATUS_MAPPING,
    build_common_judgment_metadata,
    validate_common_judgment_metadata,
)
from engine.reading_context import build_reading_context
from engine.reading_context_v2 import build_reading_context_v2


TARGET_DATETIME = datetime(2026, 8, 10, 15, 36)

EXPECTED_SOURCE_REGISTRY = {
    "five_elements": "weighted_five_elements",
    "month_command": {
        "basic": "month_command",
        "weighted": "weighted_month_command",
        "seasonal": "seasonal_strength",
        "integrated": "integrated_month_strength",
    },
    "roots": "weighted_root_strength",
    "strength": "final_strength_judgment",
    "relations": "branch_relation_strength",
    "pattern": "pattern_judgment",
    "useful_gods": "useful_gods",
    "luck_pillars": "luck_pillars",
    "current_luck": "current_luck",
    "annual_luck": "annual_luck",
    "integrated_luck": "integrated_luck",
}

EXPECTED_STATUS_MAPPING = {
    "provisional_weights": "provisional",
    "provisional_month_command": "provisional",
    "provisional_weighted_month_command": "provisional",
    "provisional_seasonal_strength": "provisional",
    "provisional_integrated_month_strength": "provisional",
    "provisional_weighted_roots": "provisional",
    "provisional_branch_relation_strength": "provisional",
    "provisional_pattern_judgment_v2": "provisional",
    "provisional_useful_gods_v3": "provisional",
    "provisional_luck_pillars_v2": "provisional",
    "provisional_annual_luck_v1": "provisional",
    "provisional_integrated_luck_v1": "provisional",
}

UNCERTAINTY = {
    "code": "fixture_uncertainty",
    "category": "rule_uncertainty",
    "status": "uncertain",
    "severity": "warning",
    "scope": ["strength"],
    "message": "fixture uncertainty",
}


def _record(
    method: str,
    status: str,
    *,
    version: str | None = None,
) -> dict[str, Any]:
    return {
        "method": method,
        "version": version,
        "status": status,
    }


def _full_chart_source() -> dict[str, Any]:
    source = {
        "weighted_five_elements": _record(
            "weighted_hidden_stems_v1",
            "provisional_weights",
        ),
        "month_command": _record(
            "month_command_v1",
            "provisional_month_command",
        ),
        "weighted_month_command": _record(
            "weighted_month_command_v1",
            "provisional_weighted_month_command",
        ),
        "seasonal_strength": _record(
            "seasonal_strength_v1",
            "provisional_seasonal_strength",
        ),
        "integrated_month_strength": _record(
            "integrated_month_strength_v1",
            "provisional_integrated_month_strength",
        ),
        "weighted_root_strength": _record(
            "weighted_root_strength_v1",
            "provisional_weighted_roots",
        ),
        "final_strength_judgment": _record(
            "final_strength_judgment_v2",
            "provisional",
            version="strength_contract_v2",
        ),
        "branch_relation_strength": _record(
            "branch_relation_strength_v1",
            "provisional_branch_relation_strength",
        ),
        "pattern_judgment": _record(
            "pattern_judgment_v2",
            "provisional_pattern_judgment_v2",
        ),
        "useful_gods": _record(
            "useful_gods_v3",
            "provisional_useful_gods_v3",
        ),
        "luck_pillars": _record(
            "luck_pillars_v2",
            "provisional_luck_pillars_v2",
        ),
        "current_luck": _record(
            "current_luck_v1",
            "current_luck_resolved",
        ),
        "annual_luck": _record(
            "annual_luck_v1",
            "provisional_annual_luck_v1",
        ),
        "integrated_luck": _record(
            "integrated_luck_v1",
            "provisional_integrated_luck_v1",
        ),
    }
    source["final_strength_judgment"].update(
        {
            "evidence": {"raw_score": 12.05},
            "warnings": ["source warning", "source warning"],
            "uncertainty": [deepcopy(UNCERTAINTY)],
            "notes": ["must not become a warning"],
            "golden_file": "must-not-be-projected.json",
            "approval": {"confirmed": True},
            "sha256": "must-not-be-projected",
        }
    )
    return source


@pytest.fixture
def chart_source() -> dict[str, Any]:
    return _full_chart_source()


@pytest.fixture
def metadata(chart_source) -> dict[str, Any]:
    return build_common_judgment_metadata(chart_source)


def _component(metadata: dict[str, Any], key: str) -> dict[str, Any]:
    return metadata["components"][key]


def _request() -> SimpleNamespace:
    return SimpleNamespace(
        birth_date="1985-07-17",
        birth_time="21:50",
        birth_place="石川県",
        gender="female",
    )


def test_valid_full_projection_and_exact_envelope(metadata):
    assert validate_common_judgment_metadata(metadata) == {
        "valid": True,
        "errors": [],
        "missing_required_fields": [],
        "unknown_fields": [],
    }
    assert tuple(metadata) == ("schema_version", "components")
    assert metadata["schema_version"] == COMMON_JUDGMENT_METADATA_SCHEMA_VERSION
    assert metadata["schema_version"] == "common_judgment_metadata_v1"


def test_source_registry_and_registered_components_are_exact(metadata):
    assert COMMON_JUDGMENT_SOURCE_REGISTRY == EXPECTED_SOURCE_REGISTRY
    assert tuple(metadata["components"]) == COMMON_JUDGMENT_COMPONENT_KEYS
    assert set(metadata["components"]) == set(EXPECTED_SOURCE_REGISTRY)
    assert tuple(metadata["components"]["month_command"]["components"]) == (
        COMMON_JUDGMENT_MONTH_COMMAND_COMPONENT_KEYS
    )


def test_component_records_have_exact_fields(metadata):
    for key, record in metadata["components"].items():
        if key == "month_command":
            assert tuple(record) == COMMON_JUDGMENT_COMPONENT_FIELDS + (
                "components",
            )
            for nested in record["components"].values():
                assert tuple(nested) == COMMON_JUDGMENT_COMPONENT_FIELDS
        else:
            assert tuple(record) == COMMON_JUDGMENT_COMPONENT_FIELDS


def test_missing_source_uses_nullable_projection(chart_source):
    chart_source.pop("annual_luck")
    record = _component(build_common_judgment_metadata(chart_source), "annual_luck")
    assert record == {
        "source_path": None,
        "method": None,
        "version": None,
        "status": None,
        "component_status": None,
        "evidence": None,
        "warnings": [],
        "uncertainty": [],
    }


def test_method_and_explicit_version_are_exact_projections(metadata):
    strength = _component(metadata, "strength")
    assert strength["method"] == "final_strength_judgment_v2"
    assert strength["version"] == "strength_contract_v2"


def test_missing_version_remains_null_without_method_suffix_inference(metadata):
    five_elements = _component(metadata, "five_elements")
    assert five_elements["method"] == "weighted_hidden_stems_v1"
    assert five_elements["version"] is None


def test_canonical_status_projects_directly(metadata):
    strength = _component(metadata, "strength")
    assert strength["status"] == "provisional"
    assert strength["component_status"] is None


def test_explicit_status_mapping_registry_is_exact(metadata):
    assert COMMON_JUDGMENT_STATUS_MAPPING == EXPECTED_STATUS_MAPPING
    record = _component(metadata, "five_elements")
    assert record["status"] == "provisional"
    assert record["component_status"] == "provisional_weights"


def test_unknown_detection_status_is_component_status_only(chart_source):
    chart_source["branch_relation_strength"]["status"] = "relations_detected"
    record = _component(build_common_judgment_metadata(chart_source), "relations")
    assert record["status"] is None
    assert record["component_status"] == "relations_detected"


def test_current_luck_resolved_is_not_mapped_to_resolved(metadata):
    record = _component(metadata, "current_luck")
    assert "current_luck_resolved" not in COMMON_JUDGMENT_STATUS_MAPPING
    assert record["status"] is None
    assert record["component_status"] == "current_luck_resolved"


def test_evidence_is_exact_deep_copy_without_provenance_or_verification(
    chart_source,
    metadata,
):
    source = chart_source["final_strength_judgment"]
    evidence = _component(metadata, "strength")["evidence"]
    assert evidence == source["evidence"]
    assert evidence is not source["evidence"]
    assert "source_path" not in evidence
    assert "method" not in evidence
    assert "version" not in evidence
    assert "status" not in evidence
    assert "golden_file" not in evidence
    assert "approval" not in evidence
    assert "sha256" not in evidence


def test_warnings_are_exact_deep_copy_and_notes_are_not_promoted(
    chart_source,
    metadata,
):
    source = chart_source["final_strength_judgment"]
    warnings = _component(metadata, "strength")["warnings"]
    assert warnings == source["warnings"]
    assert warnings is not source["warnings"]
    assert warnings == ["source warning", "source warning"]
    assert source["notes"][0] not in warnings


def test_uncertainty_is_exact_deep_copy(chart_source, metadata):
    source = chart_source["final_strength_judgment"]
    uncertainty = _component(metadata, "strength")["uncertainty"]
    assert uncertainty == source["uncertainty"]
    assert uncertainty is not source["uncertainty"]
    assert uncertainty[0] is not source["uncertainty"][0]


def test_builder_does_not_mutate_source(chart_source):
    before = deepcopy(chart_source)
    build_common_judgment_metadata(chart_source)
    assert chart_source == before


def test_output_mutation_does_not_mutate_source(chart_source):
    metadata = build_common_judgment_metadata(chart_source)
    _component(metadata, "strength")["evidence"]["raw_score"] = 99
    _component(metadata, "strength")["warnings"].append("new")
    _component(metadata, "strength")["uncertainty"][0]["scope"].append("luck")
    assert chart_source["final_strength_judgment"]["evidence"] == {
        "raw_score": 12.05
    }
    assert chart_source["final_strength_judgment"]["warnings"] == [
        "source warning",
        "source warning",
    ]
    assert chart_source["final_strength_judgment"]["uncertainty"][0][
        "scope"
    ] == ["strength"]


def test_validator_non_mapping_raises_type_error():
    with pytest.raises(TypeError):
        validate_common_judgment_metadata([])  # type: ignore[arg-type]


def test_validator_rejects_unknown_top_level_field(metadata):
    metadata["unexpected"] = True
    report = validate_common_judgment_metadata(metadata)
    assert report["valid"] is False
    assert report["unknown_fields"] == ["unexpected"]


def test_validator_rejects_unknown_component_and_component_field(metadata):
    metadata["components"]["unexpected"] = {}
    _component(metadata, "strength")["unexpected"] = True
    report = validate_common_judgment_metadata(metadata)
    assert report["valid"] is False
    assert report["unknown_fields"] == [
        "components.unexpected",
        "components.strength.unexpected",
    ]


def test_validator_rejects_invalid_status(metadata):
    _component(metadata, "strength")["status"] = "final"
    report = validate_common_judgment_metadata(metadata)
    assert report["valid"] is False
    assert "value:components.strength.status" in report["errors"]


def test_validator_rejects_invalid_warnings(metadata):
    _component(metadata, "strength")["warnings"] = ["valid", 1]
    report = validate_common_judgment_metadata(metadata)
    assert report["valid"] is False
    assert "type:components.strength.warnings:array_of_string" in report["errors"]


@pytest.mark.parametrize(
    "field,value,error",
    [
        ("category", "not-a-category", "value"),
        ("severity", "critical", "value"),
        ("scope", "strength", "type"),
    ],
)
def test_validator_rejects_invalid_uncertainty(metadata, field, value, error):
    _component(metadata, "strength")["uncertainty"][0][field] = value
    report = validate_common_judgment_metadata(metadata)
    assert report["valid"] is False
    expected = f"{error}:components.strength.uncertainty[0].{field}"
    assert any(item.startswith(expected) for item in report["errors"])


def test_present_source_without_method_is_rejected_by_validator(metadata):
    _component(metadata, "strength")["method"] = None
    report = validate_common_judgment_metadata(metadata)
    assert report["valid"] is False
    assert "required:components.strength.method:present_source" in report["errors"]


def test_present_source_without_method_is_rejected_by_builder(chart_source):
    chart_source["final_strength_judgment"].pop("method")
    with pytest.raises(ValueError, match="present_source"):
        build_common_judgment_metadata(chart_source)


def test_month_command_nested_structure_and_aggregate_contract(metadata):
    month_command = _component(metadata, "month_command")
    assert {
        key: month_command[key] for key in COMMON_JUDGMENT_COMPONENT_FIELDS
    } == {
        "source_path": None,
        "method": None,
        "version": None,
        "status": None,
        "component_status": None,
        "evidence": None,
        "warnings": [],
        "uncertainty": [],
    }
    assert {
        key: record["source_path"]
        for key, record in month_command["components"].items()
    } == EXPECTED_SOURCE_REGISTRY["month_command"]


def test_validator_rejects_original_month_command_aggregate_loophole(metadata):
    month_command = _component(metadata, "month_command")
    month_command["source_path"] = ""
    month_command["method"] = "fabricated"

    report = validate_common_judgment_metadata(metadata)

    assert report["valid"] is False
    assert "value:components.month_command.source_path:aggregate_null" in (
        report["errors"]
    )
    assert "value:components.month_command.method:aggregate_null" in (
        report["errors"]
    )


@pytest.mark.parametrize(
    "field,value,expected_suffix",
    [
        ("source_path", "month_command", "aggregate_null"),
        ("method", "fabricated", "aggregate_null"),
        ("version", "v1", "aggregate_null"),
        ("status", "provisional", "aggregate_null"),
        ("component_status", "anything", "aggregate_null"),
        ("evidence", {}, "aggregate_null"),
        ("warnings", ["warning"], "aggregate_empty"),
        ("uncertainty", [deepcopy(UNCERTAINTY)], "aggregate_empty"),
    ],
)
def test_validator_requires_fixed_month_command_aggregate_fields(
    metadata,
    field,
    value,
    expected_suffix,
):
    _component(metadata, "month_command")[field] = value

    report = validate_common_judgment_metadata(metadata)

    assert report["valid"] is False
    assert (
        f"value:components.month_command.{field}:{expected_suffix}"
        in report["errors"]
    )


def test_validator_rejects_invalid_month_command_structure(metadata):
    month_command = _component(metadata, "month_command")
    month_command["source_path"] = "month_command"
    month_command["components"].pop("seasonal")
    report = validate_common_judgment_metadata(metadata)
    assert report["valid"] is False
    assert "components.month_command.components.seasonal" in (
        report["missing_required_fields"]
    )
    assert "value:components.month_command.source_path:aggregate_null" in (
        report["errors"]
    )


def test_builder_raises_if_final_validation_is_invalid(chart_source, monkeypatch):
    invalid_report = {
        "valid": False,
        "errors": ["forced_invalid"],
        "missing_required_fields": [],
        "unknown_fields": [],
    }
    monkeypatch.setattr(
        judgment_metadata_module,
        "validate_common_judgment_metadata",
        lambda value: deepcopy(invalid_report),
    )
    with pytest.raises(ValueError, match="forced_invalid"):
        judgment_metadata_module.build_common_judgment_metadata(chart_source)


def test_reading_context_v1_and_v2_outputs_are_unchanged_by_adapter():
    chart_result = calculate_chart(_request(), target_datetime=TARGET_DATETIME)
    v1_before = build_reading_context(chart_result)
    v2_before = build_reading_context_v2(chart_result)
    chart_before = deepcopy(chart_result)

    build_common_judgment_metadata(chart_result)

    assert chart_result == chart_before
    assert build_reading_context(chart_result) == v1_before
    assert build_reading_context_v2(chart_result) == v2_before
