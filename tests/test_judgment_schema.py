import pytest

from engine.judgment_schema import (
    VALID_CONFIDENCE_LEVELS,
    VALID_JUDGMENT_STATUSES,
    VALID_SEVERITIES,
    build_confidence,
    validate_confidence_level,
    validate_judgment_status,
    validate_severity,
)


def test_judgment_status_vocabulary():
    assert VALID_JUDGMENT_STATUSES == {
        "resolved",
        "provisional",
        "uncertain",
        "unsupported",
    }


def test_confidence_level_vocabulary():
    assert VALID_CONFIDENCE_LEVELS == {
        "high",
        "medium",
        "low",
    }


def test_severity_vocabulary():
    assert VALID_SEVERITIES == {
        "error",
        "warning",
        "info",
    }


def test_validators_accept_supported_values():
    assert validate_judgment_status("resolved") == "resolved"
    assert validate_confidence_level("medium") == "medium"
    assert validate_severity("warning") == "warning"


def test_validators_reject_unsupported_values():
    with pytest.raises(ValueError):
        validate_judgment_status("finished")

    with pytest.raises(ValueError):
        validate_confidence_level("very_high")

    with pytest.raises(ValueError):
        validate_severity("critical")


def test_build_confidence():
    assert build_confidence("medium", 0.75) == {
        "level": "medium",
        "ratio": 0.75,
    }


@pytest.mark.parametrize(
    "ratio",
    [-0.01, 1.01],
)
def test_build_confidence_rejects_out_of_range_ratio(ratio):
    with pytest.raises(ValueError):
        build_confidence("high", ratio)
