"""Golden regressions for approved Reading Context v2 fixtures."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from engine.chart import calculate_chart
from engine.reading_context_v2 import (
    READING_CONTEXT_V2_EVIDENCE_SOURCES,
    READING_CONTEXT_V2_FACT_CODES,
    READING_CONTEXT_V2_TOP_LEVEL_FIELDS,
    build_reading_context_v2,
    validate_reading_context_v2,
)


TESTS_ROOT = Path(__file__).parent
GC03_APPROVAL_PATH = (
    TESTS_ROOT
    / "verification"
    / "extreme_fixtures"
    / "GC03_1984_fukuoka_male_afternoon_strength_v1.json"
)
V1_2_GOLDEN_ROOT = TESTS_ROOT / "golden" / "v1_2"
GC03_READING_CONTEXT_GOLDEN_PATH = (
    V1_2_GOLDEN_ROOT
    / "reading_context"
    / "GC03_1984_fukuoka_male_afternoon_reading_context_v2.json"
)
GC10_READING_CONTEXT_GOLDEN_PATH = (
    V1_2_GOLDEN_ROOT
    / "reading_context"
    / "GC10_1985_ishikawa_female_unknown_birth_time_reading_context_v2.json"
)
V1_2_ROOT_MANIFEST_PATH = V1_2_GOLDEN_ROOT / "manifest.json"
V1_2_READING_CONTEXT_MANIFEST_PATH = (
    V1_2_GOLDEN_ROOT / "reading_context" / "manifest.json"
)

TARGET_DATETIME = datetime(2026, 8, 10, 15, 36)
VALID_REPORT = {
    "valid": True,
    "errors": [],
    "missing_required_fields": [],
    "unknown_fields": [],
}
GC10_INPUT = {
    "birth_date": "1985-07-17",
    "birth_time": None,
    "birth_place": "石川県",
    "timezone": "Asia/Tokyo",
    "gender": "female",
}
GC10_APPROVED_PILLARS = {
    "year": "乙丑",
    "month": "癸未",
    "day": "丁巳",
    "hour": None,
}
GC10_CONFIDENCE_UNCERTAINTY = {
    "code": "birth_time_unknown_strength_confidence_reduced",
    "category": "input_uncertainty",
    "status": "uncertain",
    "severity": "warning",
    "scope": ["strength"],
    "message": (
        "出生時間が不明なため、身強身弱判定の"
        "confidence上限をmediumとして扱います。"
    ),
}
GC10_WARNINGS = [
    "出生時間が不明なため、時柱は計算していません。",
    (
        "出生時間が不明なため、五行・通根・身強身弱・格局・用神などは"
        "確認可能な年柱・月柱・日柱の範囲での評価です。"
    ),
    (
        "出生時間が不明なため、大運開始年齢・開始日時・"
        "現在大運の切り替わり時期には精度上の制限があります。"
    ),
]
GC10_TOP_LEVEL_UNCERTAINTY = [
    {
        "code": "birth_time_unknown",
        "category": "input_uncertainty",
        "status": "uncertain",
        "severity": "warning",
        "scope": [
            "hour_pillar",
            "five_elements",
            "root_strength",
            "strength",
            "pattern",
            "useful_gods",
            "luck_timing",
        ],
        "message": (
            "出生時間が不明なため、一部の判定は"
            "既知の三柱範囲または推定値です。"
        ),
    }
]


def _load_json(path: Path):
    with path.open(encoding="utf-8") as source_file:
        return json.load(source_file)


def _calculate_gc03_from_approval(approval):
    fixture = approval["fixture"]
    request = SimpleNamespace(
        birth_date=fixture["birth_date"],
        birth_time=fixture["birth_time"],
        birth_place=fixture["location"],
        gender=fixture["gender"],
    )
    return calculate_chart(request, target_datetime=TARGET_DATETIME)


def _calculate_gc10_unknown_time():
    request = SimpleNamespace(
        birth_date=GC10_INPUT["birth_date"],
        birth_time=GC10_INPUT["birth_time"],
        birth_place=GC10_INPUT["birth_place"],
        gender=GC10_INPUT["gender"],
    )
    return calculate_chart(request, target_datetime=TARGET_DATETIME)


def _resolve_path(value, path):
    current = value
    for part in path.split("."):
        current = current[part]
    return current


def test_gc03_reading_context_v2_golden_full_regression():
    approval = _load_json(GC03_APPROVAL_PATH)
    golden = _load_json(GC03_READING_CONTEXT_GOLDEN_PATH)

    fixture = approval["fixture"]
    verification = approval["verification_levels"]
    approved_strength = approval["independent_calculation"]

    assert approval["schema"] == "yakumo_extreme_fixture_approval_v1"
    assert fixture["fixture_id"] == "1984_fukuoka_male_afternoon_v2"
    assert fixture["fixture_role"] == "strong_side"
    assert fixture["calculation_scope"] == "four_pillars"
    assert fixture["four_pillars"] == {
        "year": "甲子",
        "month": "辛未",
        "day": "丁巳",
        "hour": "丁未",
    }
    assert verification["calendar_verified"]["confirmed"] is True
    assert verification["strength_verified"]["confirmed"] is True
    assert verification["golden_regression"]["confirmed"] is True

    assert tuple(golden) == (
        "schema",
        "golden_version",
        "fixture",
        "source_reference",
        "expected_reading_context",
    )
    assert golden["schema"] == "yakumo_reading_context_golden_v1"
    assert golden["golden_version"] == "v1_2"
    assert golden["fixture"] == {
        "fixture_id": fixture["fixture_id"],
        "fixture_role": fixture["fixture_role"],
        "calculation_scope": fixture["calculation_scope"],
        "input": {
            "birth_date": fixture["birth_date"],
            "birth_time": fixture["birth_time"],
            "birth_place": fixture["location"],
            "timezone": fixture["timezone"],
            "gender": fixture["gender"],
        },
        "approved_pillars": fixture["four_pillars"],
        "day_master": fixture["day_master"],
        "target_datetime": "2026-08-10T15:36:00",
        "consultation": None,
    }

    source_reference = golden["source_reference"]
    assert source_reference == {
        "approval_record": (
            "tests/verification/extreme_fixtures/"
            "GC03_1984_fukuoka_male_afternoon_strength_v1.json"
        ),
        "approval_schema": approval["schema"],
        "calendar_truth": "verification_levels.calendar_verified",
        "strength_truth": "verification_levels.strength_verified",
        "existing_v1_1_chart_golden": verification["golden_regression"][
            "golden_file"
        ],
        "existing_v1_1_chart_golden_is_v2_expected_truth_source": False,
        "projection_scope": "reading_context_v2_regression_baseline_only",
    }

    chart_result = _calculate_gc03_from_approval(approval)
    actual_pillars = {
        position: chart_result["chart"][position]["pillar"]
        for position in ("year", "month", "day", "hour")
    }
    assert actual_pillars == fixture["four_pillars"]
    assert chart_result["day_master"]["stem"] == fixture["day_master"]

    final_strength = chart_result["final_strength_judgment"]
    assert final_strength["final_score"] == approved_strength["scores"][
        "final_score"
    ]
    assert final_strength["technical_label"] == approved_strength[
        "classification"
    ]["technical_label"]
    assert final_strength["label"] == approved_strength["classification"][
        "label"
    ]

    actual_context = build_reading_context_v2(
        chart_result,
        consultation_context=None,
    )
    expected_context = golden["expected_reading_context"]

    assert tuple(expected_context) == READING_CONTEXT_V2_TOP_LEVEL_FIELDS
    assert len(expected_context) == 26
    assert expected_context["consultation"] is None
    assert expected_context["engine_version"] == "1.2"
    for field in (
        "validation",
        "warnings",
        "uncertainty",
        "source_metadata",
        "facts",
        "evidence",
        "interpretation_hints",
    ):
        assert field in expected_context

    assert validate_reading_context_v2(expected_context) == VALID_REPORT
    assert validate_reading_context_v2(actual_context) == VALID_REPORT
    assert expected_context == actual_context


def test_gc03_reading_context_v2_golden_manifest_integrity():
    root_manifest = _load_json(V1_2_ROOT_MANIFEST_PATH)
    category_manifest = _load_json(V1_2_READING_CONTEXT_MANIFEST_PATH)

    assert root_manifest["baseline"] == "Yakumo Engine v1.2"
    assert category_manifest["baseline"] == "Yakumo Engine v1.2"
    assert root_manifest["file_count"] == 3
    assert category_manifest["file_count"] == 2
    assert root_manifest["file_count"] == len(root_manifest["files"])
    assert category_manifest["file_count"] == len(category_manifest["files"])

    golden_name = GC03_READING_CONTEXT_GOLDEN_PATH.name
    root_path = f"reading_context/{golden_name}"
    root_entries = [
        entry for entry in root_manifest["files"] if entry["path"] == root_path
    ]
    category_entries = [
        entry
        for entry in category_manifest["files"]
        if entry["name"] == golden_name
    ]
    assert len(root_entries) == 1
    assert len(category_entries) == 1

    root_entry = root_entries[0]
    category_entry = category_entries[0]
    assert root_entry["path"] == f"reading_context/{category_entry['name']}"

    raw_bytes = GC03_READING_CONTEXT_GOLDEN_PATH.read_bytes()
    raw_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    assert root_entry["size"] == len(raw_bytes)
    assert category_entry["size"] == len(raw_bytes)
    assert root_entry["sha256"] == raw_sha256
    assert category_entry["sha256"] == raw_sha256
    assert root_entry["sha256"] == category_entry["sha256"]

    assert not raw_bytes.startswith(b"\xef\xbb\xbf")
    assert raw_bytes.endswith(b"\n")
    assert b"\r\n" not in raw_bytes
    golden = json.loads(raw_bytes.decode("utf-8"))
    serialized = (
        json.dumps(
            golden,
            ensure_ascii=False,
            indent=2,
            sort_keys=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    assert serialized == raw_bytes

    strength_entries = [
        entry
        for entry in root_manifest["files"]
        if entry["path"]
        == (
            "strength/"
            "GC13_Michael_Jordan_1963_brooklyn_male_afternoon_strength.json"
        )
    ]
    assert strength_entries == [
        {
            "path": (
                "strength/"
                "GC13_Michael_Jordan_1963_brooklyn_male_afternoon_strength.json"
            ),
            "size": 2768,
            "sha256": (
                "f5ccdadc41235a618a9124d767a5c872"
                "e26381869725b75b0ad615b6db4daa64"
            ),
        }
    ]


def test_gc10_three_pillar_reading_context_v2_golden_full_regression():
    golden = _load_json(GC10_READING_CONTEXT_GOLDEN_PATH)

    assert tuple(golden) == (
        "schema",
        "golden_version",
        "fixture",
        "source_reference",
        "expected_reading_context",
    )
    assert golden["schema"] == "yakumo_reading_context_golden_v1"
    assert golden["golden_version"] == "v1_2"
    assert golden["fixture"] == {
        "fixture_id": "GC10_unknown_birth_time_three_pillars",
        "fixture_role": "three_pillar_contract",
        "calculation_scope": "three_pillars",
        "input": GC10_INPUT,
        "approved_pillars": GC10_APPROVED_PILLARS,
        "day_master": "丁",
        "target_datetime": "2026-08-10T15:36:00",
        "consultation": None,
    }
    assert golden["source_reference"] == {
        "verified_calendar_fixture": "1985_ishikawa_female_verified_v2",
        "unknown_time_policy_test": "tests/test_unknown_birth_time.py",
        "existing_v1_1_chart_golden": (
            "tests/golden/v1_1/charts/"
            "GC10_unknown_birth_time_three_pillars.json"
        ),
        "existing_v1_1_chart_golden_is_v2_expected_truth_source": False,
        "projection_scope": "reading_context_v2_regression_baseline_only",
    }

    chart_result = _calculate_gc10_unknown_time()
    assert chart_result["input"] == GC10_INPUT
    assert chart_result["birth_time_status"]["known"] is False
    assert chart_result["birth_time_status"]["hour_pillar_available"] is False
    assert chart_result["birth_time_status"]["calculation_scope"] == (
        "three_pillars"
    )
    actual_pillars = {
        position: (
            None
            if chart_result["chart"].get(position) is None
            else chart_result["chart"][position]["pillar"]
        )
        for position in ("year", "month", "day", "hour")
    }
    assert actual_pillars == GC10_APPROVED_PILLARS
    assert chart_result["chart"]["hour"] is None
    assert chart_result["day_master"]["stem"] == "丁"

    final_strength = chart_result["final_strength_judgment"]
    assert final_strength["confidence"] == "medium"
    confidence_uncertainties = [
        item
        for item in final_strength["uncertainty"]
        if item.get("code") == GC10_CONFIDENCE_UNCERTAINTY["code"]
    ]
    assert confidence_uncertainties == [GC10_CONFIDENCE_UNCERTAINTY]
    assert chart_result["warnings"] == GC10_WARNINGS
    assert chart_result["uncertainty"] == GC10_TOP_LEVEL_UNCERTAINTY

    actual_context = build_reading_context_v2(
        chart_result,
        consultation_context=None,
    )
    expected_context = golden["expected_reading_context"]

    assert tuple(expected_context) == READING_CONTEXT_V2_TOP_LEVEL_FIELDS
    assert len(expected_context) == 26
    assert expected_context["consultation"] is None
    assert expected_context["chart"]["pillars"]["hour"] is None
    assert expected_context["chart"]["pillar_sequence"] == [
        "乙丑",
        "癸未",
        "丁巳",
        None,
    ]
    assert expected_context["strength"]["confidence"] == "medium"
    assert expected_context["warnings"] == chart_result["warnings"]
    assert expected_context["uncertainty"] == chart_result["uncertainty"]
    assert all(
        item.get("code") != GC10_CONFIDENCE_UNCERTAINTY["code"]
        for item in expected_context["uncertainty"]
    )

    fact_codes = [fact["code"] for fact in expected_context["facts"]]
    assert len(fact_codes) == len(set(fact_codes))
    assert set(fact_codes).issubset(READING_CONTEXT_V2_FACT_CODES)
    for fact in expected_context["facts"]:
        assert fact["value"] == _resolve_path(
            expected_context,
            fact["context_path"],
        )

    expected_categories = [
        category for category, _ in READING_CONTEXT_V2_EVIDENCE_SOURCES
    ]
    assert [
        item["category"] for item in expected_context["evidence"]
    ] == expected_categories
    assert len(expected_context["evidence"]) == 5
    assert all(
        item["summary"] is None for item in expected_context["evidence"]
    )

    assert validate_reading_context_v2(expected_context) == VALID_REPORT
    assert validate_reading_context_v2(actual_context) == VALID_REPORT
    assert expected_context == actual_context


def test_gc10_three_pillar_reading_context_v2_golden_manifest_integrity():
    root_manifest = _load_json(V1_2_ROOT_MANIFEST_PATH)
    category_manifest = _load_json(V1_2_READING_CONTEXT_MANIFEST_PATH)

    assert root_manifest["baseline"] == "Yakumo Engine v1.2"
    assert category_manifest["baseline"] == "Yakumo Engine v1.2"
    assert root_manifest["file_count"] == len(root_manifest["files"])
    assert category_manifest["file_count"] == len(category_manifest["files"])

    golden_name = GC10_READING_CONTEXT_GOLDEN_PATH.name
    root_path = f"reading_context/{golden_name}"
    root_entries = [
        entry for entry in root_manifest["files"] if entry["path"] == root_path
    ]
    category_entries = [
        entry
        for entry in category_manifest["files"]
        if entry["name"] == golden_name
    ]
    assert len(root_entries) == 1
    assert len(category_entries) == 1

    root_entry = root_entries[0]
    category_entry = category_entries[0]
    assert root_entry["path"] == f"reading_context/{category_entry['name']}"

    raw_bytes = GC10_READING_CONTEXT_GOLDEN_PATH.read_bytes()
    raw_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    assert root_entry["size"] == len(raw_bytes)
    assert category_entry["size"] == len(raw_bytes)
    assert root_entry["sha256"] == raw_sha256
    assert category_entry["sha256"] == raw_sha256
    assert root_entry["sha256"] == category_entry["sha256"]

    assert not raw_bytes.startswith(b"\xef\xbb\xbf")
    assert raw_bytes.endswith(b"\n")
    assert b"\r\n" not in raw_bytes
    golden = json.loads(raw_bytes.decode("utf-8"))
    serialized = (
        json.dumps(
            golden,
            ensure_ascii=False,
            indent=2,
            sort_keys=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    assert serialized == raw_bytes

    gc03_name = GC03_READING_CONTEXT_GOLDEN_PATH.name
    assert [
        entry
        for entry in category_manifest["files"]
        if entry["name"] == gc03_name
    ] == [
        {
            "name": gc03_name,
            "size": 90794,
            "sha256": (
                "43ac944b53923fb9bf04ea320472dbdf"
                "ec65962b7f1f20ed74f35613e1d7c4bd"
            ),
        }
    ]
    assert [
        entry
        for entry in root_manifest["files"]
        if entry["path"] == f"reading_context/{gc03_name}"
    ] == [
        {
            "path": f"reading_context/{gc03_name}",
            "size": 90794,
            "sha256": (
                "43ac944b53923fb9bf04ea320472dbdf"
                "ec65962b7f1f20ed74f35613e1d7c4bd"
            ),
        }
    ]
    assert [
        entry
        for entry in root_manifest["files"]
        if entry["path"]
        == (
            "strength/"
            "GC13_Michael_Jordan_1963_brooklyn_male_afternoon_strength.json"
        )
    ] == [
        {
            "path": (
                "strength/"
                "GC13_Michael_Jordan_1963_brooklyn_male_afternoon_strength.json"
            ),
            "size": 2768,
            "sha256": (
                "f5ccdadc41235a618a9124d767a5c872"
                "e26381869725b75b0ad615b6db4daa64"
            ),
        }
    ]
