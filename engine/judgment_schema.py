"""Shared judgment schema vocabulary for Yakumo Engine v1.2."""

from __future__ import annotations

from typing import Any


VALID_JUDGMENT_STATUSES = {
    "resolved",
    "provisional",
    "uncertain",
    "unsupported",
}

VALID_CONFIDENCE_LEVELS = {
    "high",
    "medium",
    "low",
}

VALID_SEVERITIES = {
    "error",
    "warning",
    "info",
}


def validate_judgment_status(status: str) -> str:
    if status not in VALID_JUDGMENT_STATUSES:
        raise ValueError(
            f"invalid judgment status: {status}"
        )
    return status


def validate_confidence_level(level: str) -> str:
    if level not in VALID_CONFIDENCE_LEVELS:
        raise ValueError(
            f"invalid confidence level: {level}"
        )
    return level


def validate_severity(severity: str) -> str:
    if severity not in VALID_SEVERITIES:
        raise ValueError(
            f"invalid severity: {severity}"
        )
    return severity


def build_confidence(
    level: str,
    ratio: float | None = None,
) -> dict[str, Any]:
    validate_confidence_level(level)

    if (
        ratio is not None
        and not 0.0 <= ratio <= 1.0
    ):
        raise ValueError(
            "confidence ratio must be between 0.0 and 1.0"
        )

    return {
        "level": level,
        "ratio": ratio,
    }


VALID_UNCERTAINTY_CATEGORIES = {
    "input_uncertainty",
    "boundary_uncertainty",
    "calculation_uncertainty",
    "rule_uncertainty",
    "timing_uncertainty",
    "unsupported_condition",
}


def build_uncertainty(
    *,
    code: str,
    category: str,
    status: str = "uncertain",
    severity: str = "warning",
    scope: list[str] | None = None,
    message: str | None = None,
) -> dict[str, Any]:
    if category not in VALID_UNCERTAINTY_CATEGORIES:
        raise ValueError(
            f"invalid uncertainty category: {category}"
        )

    validate_judgment_status(status)
    validate_severity(severity)

    return {
        "code": code,
        "category": category,
        "status": status,
        "severity": severity,
        "scope": list(scope or []),
        "message": message,
    }
