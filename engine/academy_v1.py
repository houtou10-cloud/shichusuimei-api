"""Deterministic projection of the existing chart engine for Academy lessons.

This module deliberately contains no astrology calculations.  It selects the
already-calculated, customer-safe values needed by the six Academy questions.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from engine.constants import STEMS, STEM_ELEMENTS
from engine.final_strength_judgment import STRENGTH_THRESHOLDS
from engine.pattern_candidates import STANDARD_PATTERN_BY_TEN_GOD
from engine.ten_gods import calculate_ten_god


ACADEMY_STEM_OPTIONS = tuple(STEMS)
ACADEMY_ELEMENT_OPTIONS = tuple(dict.fromkeys(STEM_ELEMENTS[stem]["element"] for stem in STEMS))
ACADEMY_STRENGTH_OPTIONS = tuple(item[2] for item in STRENGTH_THRESHOLDS)
ACADEMY_TEN_GOD_OPTIONS = tuple(
    dict.fromkeys(calculate_ten_god(day_stem, target_stem) for day_stem in STEMS for target_stem in STEMS)
)


def _text(value: object, fallback: str = "判定情報なし") -> str:
    return value if isinstance(value, str) and value else fallback


def build_academy_projection(chart: Mapping[str, object]) -> dict[str, object]:
    """Return only values appropriate for the student-facing answer review."""

    chart_data = chart.get("chart")
    if not isinstance(chart_data, Mapping):
        raise ValueError("chart output is missing chart data")
    month = chart_data.get("month")
    day = chart_data.get("day")
    if not isinstance(month, Mapping) or not isinstance(day, Mapping):
        raise ValueError("chart output is missing month/day data")

    hidden_stems = tuple(value for value in month.get("hidden_stems", ()) if isinstance(value, str))
    hidden_gods = tuple(
        item.get("ten_god")
        for item in month.get("hidden_stem_ten_gods", ())
        if isinstance(item, Mapping) and isinstance(item.get("ten_god"), str)
    )
    strength = chart.get("final_strength_judgment")
    pattern = chart.get("pattern_judgment")
    useful = chart.get("useful_gods")
    status = chart.get("birth_time_status")
    if not isinstance(strength, Mapping):
        strength = {}
    if not isinstance(pattern, Mapping):
        pattern = {}
    if not isinstance(useful, Mapping):
        useful = {}
    if not isinstance(status, Mapping):
        status = {}

    primary_judgment = pattern.get("primary_judgment")
    if not isinstance(primary_judgment, Mapping):
        primary_judgment = {}
    source_candidate = primary_judgment.get("source_candidate")
    if not isinstance(source_candidate, Mapping):
        source_candidate = {}
    pattern_evidence = {
        "month_branch": _text(source_candidate.get("month_branch"), _text(month.get("branch"))),
        "hidden_stems": hidden_stems,
        "selected_hidden_stem": _text(source_candidate.get("selected_hidden_stem")),
        "selected_ten_god": _text(source_candidate.get("ten_god")),
        "exposure_positions": tuple(
            value for value in source_candidate.get("exposure_positions", ()) if isinstance(value, str)
        ),
    }
    pillars = tuple(
        (position, item.get("pillar"))
        for position in ("year", "month", "day", "hour")
        if isinstance(item := chart_data.get(position), Mapping) and isinstance(item.get("pillar"), str)
    )
    return {
        "pillars": pillars,
        "day_master": _text(day.get("stem")),
        "month_branch": _text(month.get("branch")),
        "month_hidden_stems": hidden_stems,
        "month_hidden_stem_ten_gods": hidden_gods,
        "strength": _text(strength.get("label")),
        "pattern": _text(pattern.get("primary_pattern")),
        "useful_element": _text(useful.get("primary_useful_element")),
        "pattern_evidence": pattern_evidence,
        "unknown_birth_time": not bool(status.get("hour_pillar_available", False)),
    }


def grade_academy_answers(projection: Mapping[str, object], answers: Mapping[str, object]) -> tuple[bool, ...]:
    """Compare submitted values with a server-side projection; never trust client answers."""

    hidden_stems = tuple(projection["month_hidden_stems"])
    hidden_gods = tuple(projection["month_hidden_stem_ten_gods"])
    submitted_hidden = tuple(value for value in answers.get("q2", ()) if isinstance(value, str))
    submitted_gods = tuple(
        answers.get(f"q3_{index}") for index in range(len(hidden_gods))
    )
    return (
        answers.get("q1") == projection["day_master"],
        submitted_hidden == hidden_stems,
        submitted_gods == hidden_gods,
        answers.get("q4") == projection["strength"],
        answers.get("q5") == projection["pattern"],
        answers.get("q6") == projection["useful_element"],
    )


def pattern_options(projection: Mapping[str, object]) -> tuple[str, ...]:
    values = [
        value["pattern"]
        for value in STANDARD_PATTERN_BY_TEN_GOD.values()
        if isinstance(value, Mapping) and isinstance(value.get("pattern"), str)
    ]
    values.append(str(projection["pattern"]))
    return tuple(dict.fromkeys(values))


__all__ = [
    "ACADEMY_ELEMENT_OPTIONS",
    "ACADEMY_STEM_OPTIONS",
    "ACADEMY_STRENGTH_OPTIONS",
    "ACADEMY_TEN_GOD_OPTIONS",
    "build_academy_projection",
    "grade_academy_answers",
    "pattern_options",
]
