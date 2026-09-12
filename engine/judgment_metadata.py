"""Opt-in Common Judgment Metadata projection for Yakumo Engine v1.2."""

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from engine.judgment_schema import (
    VALID_JUDGMENT_STATUSES,
    VALID_SEVERITIES,
    VALID_UNCERTAINTY_CATEGORIES,
)


COMMON_JUDGMENT_METADATA_SCHEMA_VERSION = "common_judgment_metadata_v1"

COMMON_JUDGMENT_COMPONENT_FIELDS = (
    "source_path",
    "method",
    "version",
    "status",
    "component_status",
    "evidence",
    "warnings",
    "uncertainty",
)

COMMON_JUDGMENT_COMPONENT_KEYS = (
    "five_elements",
    "month_command",
    "roots",
    "strength",
    "relations",
    "pattern",
    "useful_gods",
    "luck_pillars",
    "current_luck",
    "annual_luck",
    "integrated_luck",
)

COMMON_JUDGMENT_MONTH_COMMAND_COMPONENT_KEYS = (
    "basic",
    "weighted",
    "seasonal",
    "integrated",
)

COMMON_JUDGMENT_SOURCE_REGISTRY = {
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

COMMON_JUDGMENT_STATUS_MAPPING = {
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

_ENVELOPE_FIELDS = ("schema_version", "components")
_MONTH_COMMAND_FIELDS = COMMON_JUDGMENT_COMPONENT_FIELDS + ("components",)
_UNCERTAINTY_FIELDS = (
    "code",
    "category",
    "status",
    "severity",
    "scope",
    "message",
)


def _empty_component_record() -> dict[str, Any]:
    return {
        "source_path": None,
        "method": None,
        "version": None,
        "status": None,
        "component_status": None,
        "evidence": None,
        "warnings": [],
        "uncertainty": [],
    }


def _project_status(raw_status: Any) -> tuple[Any, Any]:
    if raw_status is None:
        return None, None
    if isinstance(raw_status, str) and raw_status in VALID_JUDGMENT_STATUSES:
        return raw_status, None
    if isinstance(raw_status, str) and raw_status in COMMON_JUDGMENT_STATUS_MAPPING:
        return COMMON_JUDGMENT_STATUS_MAPPING[raw_status], raw_status
    return None, deepcopy(raw_status)


def _project_component_record(
    chart_result: Mapping[str, Any],
    source_path: str,
) -> dict[str, Any]:
    if source_path not in chart_result or chart_result[source_path] is None:
        return _empty_component_record()

    source = chart_result[source_path]
    if not isinstance(source, Mapping):
        raise ValueError(f"registered source must be a Mapping: {source_path}")

    status, component_status = _project_status(source.get("status"))
    return {
        "source_path": source_path,
        "method": deepcopy(source.get("method")),
        "version": deepcopy(source.get("version")),
        "status": status,
        "component_status": component_status,
        "evidence": deepcopy(source.get("evidence")),
        "warnings": deepcopy(source.get("warnings", [])),
        "uncertainty": deepcopy(source.get("uncertainty", [])),
    }


def _new_validation_report() -> dict[str, Any]:
    return {
        "valid": True,
        "errors": [],
        "missing_required_fields": [],
        "unknown_fields": [],
    }


def _append_once(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


def _add_error(report: dict[str, Any], value: str) -> None:
    _append_once(report["errors"], value)


def _add_missing(report: dict[str, Any], value: str) -> None:
    _append_once(report["missing_required_fields"], value)


def _add_unknown(report: dict[str, Any], value: str) -> None:
    _append_once(report["unknown_fields"], value)


def _validate_exact_keys(
    value: Mapping[str, Any],
    expected: tuple[str, ...],
    path: str,
    report: dict[str, Any],
) -> None:
    for key in expected:
        if key not in value:
            _add_missing(report, f"{path}.{key}" if path else key)
    for key in sorted(set(value) - set(expected)):
        _add_unknown(report, f"{path}.{key}" if path else key)


def _validate_uncertainty(
    value: Any,
    path: str,
    report: dict[str, Any],
) -> None:
    if not isinstance(value, list):
        _add_error(report, f"type:{path}:array")
        return

    for index, item in enumerate(value):
        item_path = f"{path}[{index}]"
        if not isinstance(item, Mapping):
            _add_error(report, f"type:{item_path}:object")
            continue
        _validate_exact_keys(item, _UNCERTAINTY_FIELDS, item_path, report)

        if "code" in item and not isinstance(item["code"], str):
            _add_error(report, f"type:{item_path}.code:string")
        if "category" in item:
            category = item["category"]
            if not isinstance(category, str):
                _add_error(report, f"type:{item_path}.category:string")
            elif category not in VALID_UNCERTAINTY_CATEGORIES:
                _add_error(report, f"value:{item_path}.category")
        if "status" in item:
            status = item["status"]
            if not isinstance(status, str):
                _add_error(report, f"type:{item_path}.status:string")
            elif status not in VALID_JUDGMENT_STATUSES:
                _add_error(report, f"value:{item_path}.status")
        if "severity" in item:
            severity = item["severity"]
            if not isinstance(severity, str):
                _add_error(report, f"type:{item_path}.severity:string")
            elif severity not in VALID_SEVERITIES:
                _add_error(report, f"value:{item_path}.severity")
        if "scope" in item:
            scope = item["scope"]
            if not isinstance(scope, list) or any(
                not isinstance(entry, str) for entry in scope
            ):
                _add_error(report, f"type:{item_path}.scope:array_of_string")
        if "message" in item and item["message"] is not None and not isinstance(
            item["message"], str
        ):
            _add_error(report, f"type:{item_path}.message:string_or_null")


def _validate_status_pair(
    status: Any,
    component_status: Any,
    path: str,
    report: dict[str, Any],
) -> None:
    if component_status is None:
        return
    if not isinstance(component_status, str):
        return

    if component_status in VALID_JUDGMENT_STATUSES:
        _add_error(report, f"value:{path}.component_status:canonical_status")
        return

    mapped = COMMON_JUDGMENT_STATUS_MAPPING.get(component_status)
    if mapped is None:
        if status is not None:
            _add_error(report, f"value:{path}.status:unmapped_component_status")
    elif status != mapped:
        _add_error(report, f"value:{path}.status:explicit_mapping")


def _validate_component_record(
    value: Any,
    *,
    path: str,
    expected_source_path: str,
    report: dict[str, Any],
) -> None:
    if not isinstance(value, Mapping):
        _add_error(report, f"type:{path}:object")
        return

    _validate_exact_keys(value, COMMON_JUDGMENT_COMPONENT_FIELDS, path, report)

    source_path = value.get("source_path")
    if source_path is not None and not isinstance(source_path, str):
        _add_error(report, f"type:{path}.source_path:string_or_null")
    elif source_path is not None and source_path != expected_source_path:
        _add_error(report, f"value:{path}.source_path:{expected_source_path}")

    method = value.get("method")
    if method is not None and not isinstance(method, str):
        _add_error(report, f"type:{path}.method:string_or_null")
    if source_path is not None and not isinstance(method, str):
        _add_error(report, f"required:{path}.method:present_source")

    version = value.get("version")
    if version is not None and not isinstance(version, str):
        _add_error(report, f"type:{path}.version:string_or_null")

    status = value.get("status")
    if status is not None and not isinstance(status, str):
        _add_error(report, f"type:{path}.status:string_or_null")
    elif status is not None and status not in VALID_JUDGMENT_STATUSES:
        _add_error(report, f"value:{path}.status")

    component_status = value.get("component_status")
    if component_status is not None and not isinstance(component_status, str):
        _add_error(report, f"type:{path}.component_status:string_or_null")
    _validate_status_pair(status, component_status, path, report)

    evidence = value.get("evidence")
    if evidence is not None and not isinstance(evidence, (Mapping, list)):
        _add_error(report, f"type:{path}.evidence:object_array_or_null")

    warnings = value.get("warnings")
    if not isinstance(warnings, list) or any(
        not isinstance(entry, str) for entry in warnings
    ):
        _add_error(report, f"type:{path}.warnings:array_of_string")

    _validate_uncertainty(value.get("uncertainty"), f"{path}.uncertainty", report)

    if source_path is None:
        nullable_fields = (
            "method",
            "version",
            "status",
            "component_status",
            "evidence",
        )
        for field in nullable_fields:
            if value.get(field) is not None:
                _add_error(report, f"value:{path}.{field}:missing_source")
        for field in ("warnings", "uncertainty"):
            if value.get(field) != []:
                _add_error(report, f"value:{path}.{field}:missing_source")


def _validate_month_command(
    value: Any,
    path: str,
    report: dict[str, Any],
) -> None:
    if not isinstance(value, Mapping):
        _add_error(report, f"type:{path}:object")
        return

    _validate_exact_keys(value, _MONTH_COMMAND_FIELDS, path, report)
    for field in (
        "source_path",
        "method",
        "version",
        "status",
        "component_status",
        "evidence",
    ):
        if value.get(field) is not None:
            _add_error(report, f"value:{path}.{field}:aggregate_null")
    for field in ("warnings", "uncertainty"):
        if value.get(field) != []:
            _add_error(report, f"value:{path}.{field}:aggregate_empty")

    nested = value.get("components")
    if not isinstance(nested, Mapping):
        _add_error(report, f"type:{path}.components:object")
        return
    _validate_exact_keys(
        nested,
        COMMON_JUDGMENT_MONTH_COMMAND_COMPONENT_KEYS,
        f"{path}.components",
        report,
    )
    registry = COMMON_JUDGMENT_SOURCE_REGISTRY["month_command"]
    for key in COMMON_JUDGMENT_MONTH_COMMAND_COMPONENT_KEYS:
        if key in nested:
            _validate_component_record(
                nested[key],
                path=f"{path}.components.{key}",
                expected_source_path=registry[key],
                report=report,
            )


def validate_common_judgment_metadata(
    metadata: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate the frozen metadata schema without astrology recalculation."""
    if not isinstance(metadata, Mapping):
        raise TypeError("common_judgment_metadata must be a Mapping")

    report = _new_validation_report()
    _validate_exact_keys(metadata, _ENVELOPE_FIELDS, "", report)

    if metadata.get("schema_version") != COMMON_JUDGMENT_METADATA_SCHEMA_VERSION:
        _add_error(
            report,
            "fixed_value:schema_version:common_judgment_metadata_v1",
        )

    components = metadata.get("components")
    if not isinstance(components, Mapping):
        _add_error(report, "type:components:object")
    else:
        _validate_exact_keys(
            components,
            COMMON_JUDGMENT_COMPONENT_KEYS,
            "components",
            report,
        )
        for key in COMMON_JUDGMENT_COMPONENT_KEYS:
            if key not in components:
                continue
            if key == "month_command":
                _validate_month_command(
                    components[key],
                    "components.month_command",
                    report,
                )
                continue
            source_path = COMMON_JUDGMENT_SOURCE_REGISTRY[key]
            _validate_component_record(
                components[key],
                path=f"components.{key}",
                expected_source_path=source_path,
                report=report,
            )

    report["valid"] = not any(
        (
            report["errors"],
            report["missing_required_fields"],
            report["unknown_fields"],
        )
    )
    return report


def build_common_judgment_metadata(
    chart_result: Mapping[str, Any],
) -> dict[str, Any]:
    """Project registered judgment metadata without changing raw chart output."""
    if not isinstance(chart_result, Mapping):
        raise TypeError("chart_result must be a Mapping")

    components: dict[str, Any] = {}
    for key in COMMON_JUDGMENT_COMPONENT_KEYS:
        registry_entry = COMMON_JUDGMENT_SOURCE_REGISTRY[key]
        if key == "month_command":
            aggregate = _empty_component_record()
            aggregate["components"] = {
                nested_key: _project_component_record(
                    chart_result,
                    registry_entry[nested_key],
                )
                for nested_key in COMMON_JUDGMENT_MONTH_COMMAND_COMPONENT_KEYS
            }
            components[key] = aggregate
        else:
            components[key] = _project_component_record(
                chart_result,
                registry_entry,
            )

    metadata = {
        "schema_version": COMMON_JUDGMENT_METADATA_SCHEMA_VERSION,
        "components": components,
    }
    validation = validate_common_judgment_metadata(metadata)
    if not validation["valid"]:
        raise ValueError(f"invalid common judgment metadata: {validation}")
    return metadata


__all__ = [
    "COMMON_JUDGMENT_COMPONENT_FIELDS",
    "COMMON_JUDGMENT_COMPONENT_KEYS",
    "COMMON_JUDGMENT_METADATA_SCHEMA_VERSION",
    "COMMON_JUDGMENT_MONTH_COMMAND_COMPONENT_KEYS",
    "COMMON_JUDGMENT_SOURCE_REGISTRY",
    "COMMON_JUDGMENT_STATUS_MAPPING",
    "build_common_judgment_metadata",
    "validate_common_judgment_metadata",
]
