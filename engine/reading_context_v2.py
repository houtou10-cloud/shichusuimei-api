"""Reading Context v2 projection and schema validation.

This module is intentionally isolated from ``engine.reading_context``.
It projects existing chart results and the immutable v1 reading context into
the frozen v2 schema.  It never recalculates astrology.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Mapping

from engine.consultation_context import validate_consultation_context
from engine.reading_context import READING_SECTION_KEYS, build_reading_context


READING_CONTEXT_V2_SCHEMA_VERSION = "reading_context_v2"
READING_CONTEXT_V2_METHOD = "reading_context_v2"
READING_CONTEXT_V2_VERSION = "reading_context_v2"
READING_CONTEXT_V2_STATUS = "ready_for_ai_reading"

READING_CONTEXT_V2_TOP_LEVEL_FIELDS = (
    "schema_version",
    "engine_version",
    "subject",
    "chart",
    "birth_time_status",
    "day_master",
    "five_elements",
    "month_command",
    "roots",
    "strength",
    "relations",
    "pattern",
    "useful_gods",
    "luck",
    "consultation",
    "facts",
    "interpretation_hints",
    "warnings",
    "uncertainty",
    "source_metadata",
    "evidence",
    "validation",
    "method",
    "version",
    "status",
    "notes",
)

READING_CONTEXT_V2_FACT_CODES = (
    "chart.pillar_sequence",
    "day_master.stem",
    "day_master.element",
    "five_elements.weighted_scores",
    "strength.final_score",
    "strength.technical_label",
    "strength.label",
    "strength.confidence",
    "pattern.primary_pattern",
    "useful_gods.primary_useful_element",
)

READING_CONTEXT_V2_EVIDENCE_SOURCES = (
    ("strength", "final_strength_judgment.evidence"),
    ("pattern", "pattern_judgment.evidence"),
    ("useful_gods", "useful_gods.evidence"),
    ("annual_luck", "annual_luck.evidence"),
    ("integrated_luck", "integrated_luck.evidence"),
)

PILLAR_FIELDS = (
    "position",
    "pillar",
    "stem",
    "branch",
    "stem_ten_god",
    "twelve_stage",
    "hidden_stems",
    "main_hidden_stem",
    "main_hidden_stem_ten_god",
)

METADATA_FIELDS = (
    "source_path",
    "method",
    "version",
    "status",
)

MONTH_COMPONENTS = (
    "basic",
    "weighted",
    "seasonal",
    "integrated",
)

SOURCE_METADATA_FIELDS = (
    "engine",
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

_MISSING = object()


def _mapping_copy(value: Any) -> Dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    return deepcopy(dict(value))


def _list_copy_or_empty(value: Any) -> list[Any]:
    if not isinstance(value, list):
        return []
    return deepcopy(value)


def _resolve_path(value: Any, path: str) -> Any:
    current = value
    for part in path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return _MISSING
        current = current[part]
    return current


def _first_source_path(
    value: Mapping[str, Any],
    paths: tuple[str, ...],
) -> str | None:
    for path in paths:
        if _resolve_path(value, path) is not _MISSING:
            return path
    return None


def _project_subject(chart_result: Mapping[str, Any]) -> Dict[str, Any]:
    source = chart_result.get("input")
    data = source if isinstance(source, Mapping) else {}
    return {
        "birth_date": deepcopy(data.get("birth_date")),
        "birth_time": deepcopy(data.get("birth_time")),
        "birth_place": deepcopy(data.get("birth_place")),
        "gender": deepcopy(data.get("gender")),
        "timezone": deepcopy(data.get("timezone")),
    }


def _project_chart(
    v1_context: Mapping[str, Any],
    birth_time_status: Mapping[str, Any],
) -> Dict[str, Any]:
    natal = v1_context.get("natal_chart")
    natal_data = natal if isinstance(natal, Mapping) else {}
    source_pillars = natal_data.get("pillars")
    source_pillars = (
        source_pillars if isinstance(source_pillars, Mapping) else {}
    )
    known = birth_time_status.get("known") is True

    pillars: Dict[str, Any] = {}
    for position in ("year", "month", "day"):
        pillars[position] = _mapping_copy(source_pillars.get(position))
    pillars["hour"] = (
        _mapping_copy(source_pillars.get("hour")) if known else None
    )

    source_sequence = natal_data.get("pillar_sequence")
    sequence = (
        deepcopy(source_sequence) if isinstance(source_sequence, list) else []
    )
    if len(sequence) == 4 and not known:
        sequence[3] = None

    return {
        "pillars": pillars,
        "pillar_sequence": sequence,
    }


def _project_component_group(
    chart_result: Mapping[str, Any],
    sources: tuple[tuple[str, str], ...],
) -> Dict[str, Any] | None:
    projected = {
        output_key: _mapping_copy(chart_result.get(source_key))
        for output_key, source_key in sources
    }
    if not any(value is not None for value in projected.values()):
        return None
    return projected


def _project_consultation(
    consultation_context: Mapping[str, Any] | None,
) -> Dict[str, Any] | None:
    if consultation_context is None:
        return None
    if not isinstance(consultation_context, Mapping):
        raise TypeError("consultation_context must be a Mapping or None")
    validate_consultation_context(consultation_context)
    if consultation_context.get("has_consultation") is not True:
        return None
    return deepcopy(dict(consultation_context))


def _project_interpretation_hints(
    v1_context: Mapping[str, Any],
) -> list[Dict[str, Any]]:
    sections = v1_context.get("reading_sections")
    sections = sections if isinstance(sections, Mapping) else {}
    result: list[Dict[str, Any]] = []
    for section in READING_SECTION_KEYS:
        source = sections.get(section)
        if not isinstance(source, Mapping):
            continue
        result.append(
            {
                "section": section,
                "focus": deepcopy(source.get("focus")),
                "instruction": deepcopy(source.get("instruction")),
            }
        )
    return result


def _metadata(
    source_path: str,
    source: Any,
) -> Dict[str, Any]:
    if not isinstance(source, Mapping):
        return {
            "source_path": None,
            "method": None,
            "version": None,
            "status": None,
        }
    return {
        "source_path": source_path,
        "method": deepcopy(source.get("method")),
        "version": deepcopy(source.get("version")),
        "status": deepcopy(source.get("status")),
    }


def _project_source_metadata(
    chart_result: Mapping[str, Any],
) -> Dict[str, Any]:
    engine_source = chart_result.get("engine_metadata")
    if isinstance(engine_source, Mapping):
        engine = {
            "source_path": "engine_metadata",
            "method": None,
            "version": deepcopy(engine_source.get("engine_version")),
            "status": deepcopy(engine_source.get("status")),
        }
    else:
        engine = {
            "source_path": None,
            "method": None,
            "version": None,
            "status": None,
        }

    month_sources = {
        "basic": "month_command",
        "weighted": "weighted_month_command",
        "seasonal": "seasonal_strength",
        "integrated": "integrated_month_strength",
    }
    month_metadata = {
        "source_path": None,
        "method": None,
        "version": None,
        "status": None,
        "components": {
            key: _metadata(path, chart_result.get(path))
            for key, path in month_sources.items()
        },
    }

    return {
        "engine": engine,
        "five_elements": _metadata(
            "weighted_five_elements",
            chart_result.get("weighted_five_elements"),
        ),
        "month_command": month_metadata,
        "roots": _metadata(
            "weighted_root_strength",
            chart_result.get("weighted_root_strength"),
        ),
        "strength": _metadata(
            "final_strength_judgment",
            chart_result.get("final_strength_judgment"),
        ),
        "relations": _metadata(
            "branch_relation_strength",
            chart_result.get("branch_relation_strength"),
        ),
        "pattern": _metadata(
            "pattern_judgment",
            chart_result.get("pattern_judgment"),
        ),
        "useful_gods": _metadata(
            "useful_gods",
            chart_result.get("useful_gods"),
        ),
        "luck_pillars": _metadata(
            "luck_pillars",
            chart_result.get("luck_pillars"),
        ),
        "current_luck": _metadata(
            "current_luck",
            chart_result.get("current_luck"),
        ),
        "annual_luck": _metadata(
            "annual_luck",
            chart_result.get("annual_luck"),
        ),
        "integrated_luck": _metadata(
            "integrated_luck",
            chart_result.get("integrated_luck"),
        ),
    }


def _project_evidence(
    chart_result: Mapping[str, Any],
) -> list[Dict[str, Any]]:
    result: list[Dict[str, Any]] = []
    for category, source_path in READING_CONTEXT_V2_EVIDENCE_SOURCES:
        evidence = _resolve_path(chart_result, source_path)
        result.append(
            {
                "category": category,
                "available": evidence is not _MISSING and evidence is not None,
                "source_path": source_path,
                "summary": None,
            }
        )
    return result


def _project_facts(
    context: Mapping[str, Any],
    chart_result: Mapping[str, Any],
) -> list[Dict[str, Any]]:
    source_paths: Dict[str, str | None] = {
        "chart.pillar_sequence": "chart" if isinstance(
            chart_result.get("chart"), Mapping
        ) else None,
        "day_master.stem": _first_source_path(
            chart_result,
            (
                "day_master.stem",
                "day_master.day_master_stem",
                "chart.day.stem",
            ),
        ),
        "day_master.element": _first_source_path(
            chart_result,
            (
                "day_master.element",
                "day_master.day_master_element",
            ),
        ),
        "five_elements.weighted_scores": _first_source_path(
            chart_result,
            ("weighted_five_elements.scores",),
        ),
        "strength.final_score": _first_source_path(
            chart_result,
            ("final_strength_judgment.final_score",),
        ),
        "strength.technical_label": _first_source_path(
            chart_result,
            ("final_strength_judgment.technical_label",),
        ),
        "strength.label": _first_source_path(
            chart_result,
            ("final_strength_judgment.label",),
        ),
        "strength.confidence": _first_source_path(
            chart_result,
            ("final_strength_judgment.confidence",),
        ),
        "pattern.primary_pattern": _first_source_path(
            chart_result,
            ("pattern_judgment.primary_pattern",),
        ),
        "useful_gods.primary_useful_element": _first_source_path(
            chart_result,
            ("useful_gods.primary_useful_element",),
        ),
    }

    confidence_paths = {
        "strength.final_score": "final_strength_judgment.confidence",
        "strength.technical_label": "final_strength_judgment.confidence",
        "strength.label": "final_strength_judgment.confidence",
        "strength.confidence": "final_strength_judgment.confidence",
        "pattern.primary_pattern": "pattern_judgment.confidence",
        "useful_gods.primary_useful_element": "useful_gods.confidence",
    }

    result: list[Dict[str, Any]] = []
    for code in READING_CONTEXT_V2_FACT_CODES:
        value = _resolve_path(context, code)
        source_path = source_paths[code]
        if value is _MISSING or value is None or source_path is None:
            continue
        confidence_path = confidence_paths.get(code)
        confidence = (
            _resolve_path(chart_result, confidence_path)
            if confidence_path is not None
            else None
        )
        if confidence is _MISSING:
            confidence = None
        result.append(
            {
                "code": code,
                "category": code.split(".", 1)[0],
                "value": deepcopy(value),
                "context_path": code,
                "source_path": source_path,
                "confidence": deepcopy(confidence),
            }
        )
    return result


def _new_validation_report() -> Dict[str, Any]:
    return {
        "valid": True,
        "errors": [],
        "missing_required_fields": [],
        "unknown_fields": [],
    }


def _add_error(report: Dict[str, Any], message: str) -> None:
    if message not in report["errors"]:
        report["errors"].append(message)


def _add_missing(report: Dict[str, Any], path: str) -> None:
    if path not in report["missing_required_fields"]:
        report["missing_required_fields"].append(path)
    _add_error(report, f"missing_required_field:{path}")


def _add_unknown(report: Dict[str, Any], path: str) -> None:
    if path not in report["unknown_fields"]:
        report["unknown_fields"].append(path)
    _add_error(report, f"unknown_field:{path}")


def _validate_keys(
    value: Mapping[str, Any],
    required: tuple[str, ...],
    allowed: tuple[str, ...],
    prefix: str,
    report: Dict[str, Any],
) -> None:
    for key in required:
        if key not in value:
            _add_missing(report, f"{prefix}.{key}" if prefix else key)
    for key in sorted(set(value) - set(allowed)):
        _add_unknown(report, f"{prefix}.{key}" if prefix else key)


def _validate_metadata_entry(
    value: Any,
    path: str,
    report: Dict[str, Any],
) -> None:
    if not isinstance(value, Mapping):
        _add_error(report, f"type:{path}:object")
        return
    _validate_keys(value, METADATA_FIELDS, METADATA_FIELDS, path, report)
    for field in METADATA_FIELDS:
        item = value.get(field)
        if item is not None and not isinstance(item, str):
            _add_error(report, f"type:{path}.{field}:string_or_null")


def validate_reading_context_v2(
    context: Mapping[str, Any],
) -> Dict[str, Any]:
    """Validate the frozen v2 projection schema without recalculation."""
    if not isinstance(context, Mapping):
        raise TypeError("reading_context_v2 must be a Mapping")

    report = _new_validation_report()

    fixed_values = {
        "schema_version": READING_CONTEXT_V2_SCHEMA_VERSION,
        "method": READING_CONTEXT_V2_METHOD,
        "version": READING_CONTEXT_V2_VERSION,
        "status": READING_CONTEXT_V2_STATUS,
    }
    for key, expected in fixed_values.items():
        if context.get(key) != expected:
            _add_error(report, f"fixed_value:{key}:{expected}")

    _validate_keys(
        context,
        READING_CONTEXT_V2_TOP_LEVEL_FIELDS,
        READING_CONTEXT_V2_TOP_LEVEL_FIELDS,
        "",
        report,
    )

    string_fields = ("schema_version", "method", "version", "status")
    for key in string_fields:
        if key in context and not isinstance(context[key], str):
            _add_error(report, f"type:{key}:string")
    if context.get("engine_version") is not None and not isinstance(
        context.get("engine_version"), str
    ):
        _add_error(report, "type:engine_version:string_or_null")

    object_fields = (
        "subject",
        "chart",
        "birth_time_status",
        "luck",
        "source_metadata",
        "validation",
    )
    for key in object_fields:
        if key in context and not isinstance(context[key], Mapping):
            _add_error(report, f"type:{key}:object")
    nullable_object_fields = (
        "day_master",
        "five_elements",
        "month_command",
        "roots",
        "strength",
        "relations",
        "pattern",
        "useful_gods",
        "consultation",
    )
    for key in nullable_object_fields:
        if key in context and context[key] is not None and not isinstance(
            context[key], Mapping
        ):
            _add_error(report, f"type:{key}:object_or_null")
    array_fields = (
        "facts",
        "interpretation_hints",
        "warnings",
        "uncertainty",
        "evidence",
        "notes",
    )
    for key in array_fields:
        if key in context and not isinstance(context[key], list):
            _add_error(report, f"type:{key}:array")

    subject = context.get("subject")
    subject_fields = (
        "birth_date",
        "birth_time",
        "birth_place",
        "gender",
        "timezone",
    )
    if isinstance(subject, Mapping):
        _validate_keys(subject, subject_fields, subject_fields, "subject", report)
        for key in subject_fields:
            value = subject.get(key)
            if value is not None and not isinstance(value, str):
                _add_error(report, f"type:subject.{key}:string_or_null")

    chart = context.get("chart")
    birth_status = context.get("birth_time_status")
    if isinstance(chart, Mapping):
        _validate_keys(
            chart,
            ("pillars", "pillar_sequence"),
            ("pillars", "pillar_sequence"),
            "chart",
            report,
        )
        pillars = chart.get("pillars")
        sequence = chart.get("pillar_sequence")
        if not isinstance(pillars, Mapping):
            _add_error(report, "type:chart.pillars:object")
        else:
            positions = ("year", "month", "day", "hour")
            _validate_keys(pillars, positions, positions, "chart.pillars", report)
            for index, position in enumerate(positions):
                pillar = pillars.get(position)
                if pillar is None and position == "hour":
                    continue
                if not isinstance(pillar, Mapping):
                    _add_error(report, f"type:chart.pillars.{position}:object")
                    continue
                _validate_keys(
                    pillar,
                    PILLAR_FIELDS,
                    PILLAR_FIELDS,
                    f"chart.pillars.{position}",
                    report,
                )
                for key in PILLAR_FIELDS:
                    item = pillar.get(key)
                    if key == "hidden_stems":
                        if not isinstance(item, list):
                            _add_error(
                                report,
                                f"type:chart.pillars.{position}.{key}:array",
                            )
                    elif item is not None and not isinstance(item, str):
                        _add_error(
                            report,
                            f"type:chart.pillars.{position}.{key}:string_or_null",
                        )
                if isinstance(sequence, list) and len(sequence) == 4:
                    if sequence[index] != pillar.get("pillar"):
                        _add_error(
                            report,
                            f"pillar_sequence_mismatch:{position}",
                        )
        if not isinstance(sequence, list):
            _add_error(report, "type:chart.pillar_sequence:array")
        elif len(sequence) != 4:
            _add_error(report, "length:chart.pillar_sequence:4")

        if isinstance(birth_status, Mapping) and isinstance(pillars, Mapping):
            known = birth_status.get("known")
            if not isinstance(known, bool):
                _add_error(report, "type:birth_time_status.known:boolean")
            elif known:
                if not isinstance(pillars.get("hour"), Mapping):
                    _add_error(report, "hour_rule:known_requires_hour")
                if isinstance(sequence, list) and len(sequence) == 4:
                    if sequence[3] is None:
                        _add_error(report, "hour_rule:known_sequence_requires_hour")
                if birth_status.get("calculation_scope") != "four_pillars":
                    _add_error(report, "hour_rule:known_scope_four_pillars")
            else:
                if pillars.get("hour") is not None:
                    _add_error(report, "hour_rule:unknown_hour_must_be_null")
                if isinstance(sequence, list) and len(sequence) == 4:
                    if sequence[3] is not None:
                        _add_error(report, "hour_rule:unknown_sequence_must_be_null")
                if birth_status.get("calculation_scope") != "three_pillars":
                    _add_error(report, "hour_rule:unknown_scope_three_pillars")

    for field, component_fields in (
        ("month_command", MONTH_COMPONENTS),
        ("roots", ("basic", "weighted")),
        (
            "relations",
            (
                "clashes",
                "combinations",
                "trines",
                "punishments",
                "harms",
                "breaks",
                "strength",
            ),
        ),
    ):
        value = context.get(field)
        if isinstance(value, Mapping):
            _validate_keys(value, component_fields, component_fields, field, report)
            for component in component_fields:
                item = value.get(component)
                if item is not None and not isinstance(item, Mapping):
                    _add_error(
                        report,
                        f"type:{field}.{component}:object_or_null",
                    )

    hints = context.get("interpretation_hints")
    if isinstance(hints, list):
        hint_sections: list[str] = []
        hint_fields = ("section", "focus", "instruction")
        for index, hint in enumerate(hints):
            path = f"interpretation_hints.{index}"
            if not isinstance(hint, Mapping):
                _add_error(report, f"type:{path}:object")
                continue
            _validate_keys(hint, hint_fields, hint_fields, path, report)
            section = hint.get("section")
            if not isinstance(section, str):
                _add_error(report, f"type:{path}.section:string")
            else:
                hint_sections.append(section)
                if section not in READING_SECTION_KEYS:
                    _add_error(report, f"unsupported_section:{section}")
            focus = hint.get("focus")
            if not isinstance(focus, list) or not all(
                isinstance(item, str) for item in focus
            ):
                _add_error(report, f"type:{path}.focus:array_of_string")
            if not isinstance(hint.get("instruction"), str):
                _add_error(report, f"type:{path}.instruction:string")
        if tuple(hint_sections) != tuple(READING_SECTION_KEYS):
            _add_error(report, "interpretation_hints:section_order_or_membership")

    uncertainty = context.get("uncertainty")
    if isinstance(uncertainty, list) and not all(
        isinstance(item, Mapping) for item in uncertainty
    ):
        _add_error(report, "type:uncertainty:array_of_object")
    notes = context.get("notes")
    if isinstance(notes, list) and not all(isinstance(item, str) for item in notes):
        _add_error(report, "type:notes:array_of_string")

    source_metadata = context.get("source_metadata")
    if isinstance(source_metadata, Mapping):
        _validate_keys(
            source_metadata,
            SOURCE_METADATA_FIELDS,
            SOURCE_METADATA_FIELDS,
            "source_metadata",
            report,
        )
        for key in SOURCE_METADATA_FIELDS:
            entry = source_metadata.get(key)
            if key != "month_command":
                _validate_metadata_entry(
                    entry,
                    f"source_metadata.{key}",
                    report,
                )
                continue
            path = "source_metadata.month_command"
            if not isinstance(entry, Mapping):
                _add_error(report, f"type:{path}:object")
                continue
            month_fields = METADATA_FIELDS + ("components",)
            _validate_keys(entry, month_fields, month_fields, path, report)
            for field in METADATA_FIELDS:
                if entry.get(field) is not None:
                    _add_error(report, f"month_aggregate_must_be_null:{field}")
            components = entry.get("components")
            if not isinstance(components, Mapping):
                _add_error(report, f"type:{path}.components:object")
                continue
            _validate_keys(
                components,
                MONTH_COMPONENTS,
                MONTH_COMPONENTS,
                f"{path}.components",
                report,
            )
            for component in MONTH_COMPONENTS:
                _validate_metadata_entry(
                    components.get(component),
                    f"{path}.components.{component}",
                    report,
                )

    facts = context.get("facts")
    if isinstance(facts, list):
        seen_codes: set[str] = set()
        fact_fields = (
            "code",
            "category",
            "value",
            "context_path",
            "source_path",
            "confidence",
        )
        for index, fact in enumerate(facts):
            path = f"facts.{index}"
            if not isinstance(fact, Mapping):
                _add_error(report, f"type:{path}:object")
                continue
            _validate_keys(fact, fact_fields, fact_fields, path, report)
            code = fact.get("code")
            if not isinstance(code, str):
                _add_error(report, f"type:{path}.code:string")
                continue
            if code not in READING_CONTEXT_V2_FACT_CODES:
                _add_error(report, f"unsupported_fact_code:{code}")
            if code in seen_codes:
                _add_error(report, f"duplicate_fact_code:{code}")
            seen_codes.add(code)
            if fact.get("context_path") != code:
                _add_error(report, f"fact_context_path:{code}")
            resolved = _resolve_path(context, code)
            if resolved is _MISSING or fact.get("value") != resolved:
                _add_error(report, f"fact_value_mismatch:{code}")
            if not isinstance(fact.get("category"), str):
                _add_error(report, f"type:{path}.category:string")
            if not isinstance(fact.get("source_path"), str):
                _add_error(report, f"type:{path}.source_path:string")
            confidence = fact.get("confidence")
            if confidence is not None and not isinstance(confidence, str):
                _add_error(report, f"type:{path}.confidence:string_or_null")

    evidence = context.get("evidence")
    if isinstance(evidence, list):
        expected_categories = tuple(
            category for category, _ in READING_CONTEXT_V2_EVIDENCE_SOURCES
        )
        seen_categories: list[str] = []
        evidence_fields = ("category", "available", "source_path", "summary")
        for index, item in enumerate(evidence):
            path = f"evidence.{index}"
            if not isinstance(item, Mapping):
                _add_error(report, f"type:{path}:object")
                continue
            _validate_keys(item, evidence_fields, evidence_fields, path, report)
            category = item.get("category")
            if not isinstance(category, str):
                _add_error(report, f"type:{path}.category:string")
            else:
                seen_categories.append(category)
                if category not in expected_categories:
                    _add_error(report, f"unsupported_evidence_category:{category}")
            if not isinstance(item.get("available"), bool):
                _add_error(report, f"type:{path}.available:boolean")
            source_path = item.get("source_path")
            if source_path is not None and not isinstance(source_path, str):
                _add_error(report, f"type:{path}.source_path:string_or_null")
            if item.get("summary") is not None:
                _add_error(report, f"evidence_summary_must_be_null:{category}")
        if tuple(seen_categories) != expected_categories:
            _add_error(report, "evidence:category_order_or_membership")

    validation = context.get("validation")
    validation_fields = (
        "valid",
        "errors",
        "missing_required_fields",
        "unknown_fields",
    )
    if isinstance(validation, Mapping):
        _validate_keys(
            validation,
            validation_fields,
            validation_fields,
            "validation",
            report,
        )
        if not isinstance(validation.get("valid"), bool):
            _add_error(report, "type:validation.valid:boolean")
        for key in ("errors", "missing_required_fields", "unknown_fields"):
            value = validation.get(key)
            if not isinstance(value, list) or not all(
                isinstance(item, str) for item in value
            ):
                _add_error(report, f"type:validation.{key}:array_of_string")

    report["valid"] = not report["errors"]
    return report


def build_reading_context_v2(
    chart_result: Mapping[str, Any],
    *,
    consultation_context: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    """Project existing chart/v1 context data into Reading Context v2."""
    if not isinstance(chart_result, Mapping):
        raise TypeError("chart_result must be a Mapping")

    v1_context = build_reading_context(chart_result)
    birth_time_status = v1_context.get("birth_time_status")
    if not isinstance(birth_time_status, Mapping):
        birth_time_status = {}

    engine_metadata = chart_result.get("engine_metadata")
    engine_version = (
        deepcopy(engine_metadata.get("engine_version"))
        if isinstance(engine_metadata, Mapping)
        else None
    )

    context: Dict[str, Any] = {
        "schema_version": READING_CONTEXT_V2_SCHEMA_VERSION,
        "engine_version": engine_version,
        "subject": _project_subject(chart_result),
        "chart": _project_chart(v1_context, birth_time_status),
        "birth_time_status": deepcopy(dict(birth_time_status)),
        "day_master": _mapping_copy(v1_context.get("day_master")),
        "five_elements": _mapping_copy(v1_context.get("five_elements")),
        "month_command": _project_component_group(
            chart_result,
            (
                ("basic", "month_command"),
                ("weighted", "weighted_month_command"),
                ("seasonal", "seasonal_strength"),
                ("integrated", "integrated_month_strength"),
            ),
        ),
        "roots": _project_component_group(
            chart_result,
            (
                ("basic", "root_strength"),
                ("weighted", "weighted_root_strength"),
            ),
        ),
        "strength": _mapping_copy(v1_context.get("strength")),
        "relations": _project_component_group(
            chart_result,
            (
                ("clashes", "branch_clashes"),
                ("combinations", "branch_combinations"),
                ("trines", "branch_trines"),
                ("punishments", "branch_punishments"),
                ("harms", "branch_harms"),
                ("breaks", "branch_breaks"),
                ("strength", "branch_relation_strength"),
            ),
        ),
        "pattern": _mapping_copy(v1_context.get("pattern")),
        "useful_gods": _mapping_copy(v1_context.get("useful_gods")),
        "luck": deepcopy(v1_context.get("luck")),
        "consultation": _project_consultation(consultation_context),
        "facts": [],
        "interpretation_hints": _project_interpretation_hints(v1_context),
        "warnings": _list_copy_or_empty(chart_result.get("warnings")),
        "uncertainty": _list_copy_or_empty(chart_result.get("uncertainty")),
        "source_metadata": _project_source_metadata(chart_result),
        "evidence": _project_evidence(chart_result),
        "validation": {
            "valid": False,
            "errors": [],
            "missing_required_fields": [],
            "unknown_fields": [],
        },
        "method": READING_CONTEXT_V2_METHOD,
        "version": READING_CONTEXT_V2_VERSION,
        "status": READING_CONTEXT_V2_STATUS,
        "notes": _list_copy_or_empty(v1_context.get("notes")),
    }

    context["facts"] = _project_facts(context, chart_result)

    validation = validate_reading_context_v2(context)
    if validation["valid"] is not True:
        raise ValueError(f"invalid reading_context_v2: {validation['errors']}")
    context["validation"] = validation

    final_validation = validate_reading_context_v2(context)
    if final_validation["valid"] is not True:
        raise ValueError(
            f"invalid final reading_context_v2: {final_validation['errors']}"
        )
    context["validation"] = final_validation
    return context


__all__ = [
    "READING_CONTEXT_V2_SCHEMA_VERSION",
    "READING_CONTEXT_V2_METHOD",
    "READING_CONTEXT_V2_VERSION",
    "READING_CONTEXT_V2_STATUS",
    "READING_CONTEXT_V2_TOP_LEVEL_FIELDS",
    "READING_CONTEXT_V2_FACT_CODES",
    "READING_CONTEXT_V2_EVIDENCE_SOURCES",
    "build_reading_context_v2",
    "validate_reading_context_v2",
]
