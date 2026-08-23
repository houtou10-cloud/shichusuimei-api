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
