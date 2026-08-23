@'
"""
Yakumo Engine version metadata.

Engine version is independent from individual
calculation method/schema versions.
"""

from __future__ import annotations

from typing import Any


ENGINE_NAME = "Yakumo Engine"
ENGINE_VERSION = "1.2"
RULE_VERSION = "1.2"
ENGINE_STATUS = "development"


def get_engine_metadata() -> dict[str, Any]:
    """Return top-level Yakumo Engine metadata."""
    return {
        "engine_name": ENGINE_NAME,
        "engine_version": ENGINE_VERSION,
        "rule_version": RULE_VERSION,
        "status": ENGINE_STATUS,
    }
'@ | Set-Content engine\version.py -Encoding UTF8
