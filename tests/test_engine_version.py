"""Tests for Yakumo Engine top-level version metadata."""

from engine.version import (
    ENGINE_NAME,
    ENGINE_STATUS,
    ENGINE_VERSION,
    RULE_VERSION,
    get_engine_metadata,
)


def test_engine_version_constants():
    assert ENGINE_NAME == "Yakumo Engine"
    assert ENGINE_VERSION == "1.2"
    assert RULE_VERSION == "1.2"
    assert ENGINE_STATUS == "development"


def test_engine_metadata_contract():
    assert get_engine_metadata() == {
        "engine_name": "Yakumo Engine",
        "engine_version": "1.2",
        "rule_version": "1.2",
        "status": "development",
    }


def test_calculate_chart_exposes_engine_metadata():
    from datetime import datetime
    from types import SimpleNamespace

    from engine.chart import calculate_chart

    request = SimpleNamespace(
        birth_date="1985-07-17",
        birth_time="21:50",
        birth_place="石川県",
        gender="female",
    )

    result = calculate_chart(
        request,
        target_datetime=datetime(2026, 8, 10, 15, 36),
    )

    assert result["engine_metadata"] == {
        "engine_name": "Yakumo Engine",
        "engine_version": "1.2",
        "rule_version": "1.2",
        "status": "development",
    }
