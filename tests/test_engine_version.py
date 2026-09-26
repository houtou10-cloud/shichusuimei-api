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


def test_reading_context_v2_preserves_engine_metadata():
    from datetime import datetime
    from types import SimpleNamespace

    from engine.chart import calculate_chart
    from engine.reading_context_v2 import build_reading_context_v2

    request = SimpleNamespace(
        birth_date="1985-07-17",
        birth_time="21:50",
        birth_place="石川県",
        gender="female",
    )

    chart_result = calculate_chart(
        request,
        target_datetime=datetime(2026, 8, 10, 15, 36),
    )

    context = build_reading_context_v2(chart_result)

    assert context["engine_version"] == "1.2"
    assert context["source_metadata"]["engine"] == {
        "source_path": "engine_metadata",
        "method": None,
        "version": "1.2",
        "status": "development",
    }


def test_reading_context_v2_accepts_legacy_chart_without_engine_metadata():
    from datetime import datetime
    from types import SimpleNamespace

    from engine.chart import calculate_chart
    from engine.reading_context_v2 import build_reading_context_v2

    request = SimpleNamespace(
        birth_date="1985-07-17",
        birth_time="21:50",
        birth_place="石川県",
        gender="female",
    )

    chart_result = calculate_chart(
        request,
        target_datetime=datetime(2026, 8, 10, 15, 36),
    )

    chart_result.pop("engine_metadata")

    context = build_reading_context_v2(chart_result)

    assert context["engine_version"] is None
    assert context["source_metadata"]["engine"] == {
        "source_path": None,
        "method": None,
        "version": None,
        "status": None,
    }
