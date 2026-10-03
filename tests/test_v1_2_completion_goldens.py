"""Verification for frozen section 30 AI/Product/PDF v2 artifacts."""

from hashlib import sha256
import json
from pathlib import Path, PurePosixPath

import pytest

from engine.reading_renderer_v2 import render_reading_product_v2_html
import tests.generate_v1_2_completion_goldens as golden_generator
from tests.generate_v1_2_completion_goldens import ROOT, build_cases


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_human_review_or_pending(review: dict, scope: str) -> None:
    if not review:
        assert review == {}
        return
    assert tuple(review) == ("status", "reviewer", "reviewed_at", "scope", "notes")
    assert review["status"] == "approved"
    assert type(review["reviewer"]) is str and review["reviewer"].strip()
    assert review["scope"] == scope
    assert type(review["notes"]) is list


@pytest.mark.parametrize(
    ("directory", "artifact_type", "count"),
    [
        ("ai_reading_v2", "ai_reading_v2", 2),
        ("reading_product_v2", "reading_product_v2", 2),
        ("pdf_v2", "pdf_v2", 6),
    ],
)
def test_manifest_integrity(directory, artifact_type, count):
    root = ROOT / directory
    manifest = _load(root / "manifest.json")
    assert tuple(manifest) == (
        "schema_version", "version", "artifact_type", "file_count", "files",
    )
    assert manifest["artifact_type"] == artifact_type
    assert manifest["file_count"] == count == len(manifest["files"])
    assert [item["artifact_id"] for item in manifest["files"]] == sorted(
        item["artifact_id"] for item in manifest["files"]
    )
    for item in manifest["files"]:
        assert tuple(item) == ("artifact_id", "path", "size", "sha256")
        relative = PurePosixPath(item["path"])
        assert not relative.is_absolute() and ".." not in relative.parts and "\\" not in item["path"]
        data = (root / item["path"]).read_bytes()
        assert len(data) == item["size"] > 0
        assert sha256(data).hexdigest() == item["sha256"]


def test_ai_product_and_html_goldens_regenerate_from_public_pipeline():
    for case_id, family, consultation, artifacts, report, product in build_cases():
        ai = _load(ROOT / "ai_reading_v2" / f"{family}_ai_reading_v2.json")
        assert tuple(ai) == (
            "schema_version", "version", "case_id", "source_references", "provider_model",
            "provider_response", "ai_reading", "quality_report", "human_review",
        )
        assert ai["case_id"] == case_id
        assert ai["provider_model"] == "test-model"
        assert ai["provider_response"] == artifacts.payload
        assert ai["ai_reading"] == artifacts.reading
        assert ai["quality_report"] == report.to_dict()
        assert ai["quality_report"]["semantic_assessment"] == {
            "status": "completed", "method": "golden_semantic_assessor_v1",
            "version": "v1",
        }
        _assert_human_review_or_pending(
            ai["human_review"],
            "ai_reading_v2_prose_and_contract",
        )
        product_golden = _load(ROOT / "reading_product_v2" / f"{family}_reading_product_v2.json")
        assert tuple(product_golden) == (
            "schema_version", "version", "case_id", "source_ai_reading_golden",
            "generated_at", "reading_product", "human_review",
        )
        assert product_golden["reading_product"] == product.to_dict()
        _assert_human_review_or_pending(
            product_golden["human_review"],
            "reading_product_v2_contract_and_content",
        )
        html = (ROOT / "pdf_v2" / f"{family}.html").read_text(encoding="utf-8")
        assert html == render_reading_product_v2_html(product)


def test_gc03_and_gc10_required_coverage():
    gc03 = _load(ROOT / "ai_reading_v2" / "GC03_1984_fukuoka_male_afternoon_ai_reading_v2.json")
    gc10 = _load(ROOT / "ai_reading_v2" / "GC10_1985_ishikawa_female_unknown_birth_time_ai_reading_v2.json")
    assert gc03["source_references"]["consultation_context"] is not None
    assert gc03["ai_reading"]["consultation_answer"] is not None
    assert gc03["quality_report"]["decision"] == "pass"
    assert gc10["ai_reading"]["warnings"]
    assert gc10["ai_reading"]["uncertainty"]
    assert gc10["ai_reading"]["summary"]["text"] == "出生時刻不明のため、既知の三柱だけを用いて説明します。"
    assert gc10["quality_report"]["decision"] == "pass"


def test_reference_pdf_candidates_and_visual_review_gate():
    for case_id, family in (
        ("GC03", "GC03_1984_fukuoka_male_afternoon"),
        ("GC10", "GC10_1985_ishikawa_female_unknown_birth_time"),
    ):
        assert (ROOT / "pdf_v2" / f"{family}.pdf").read_bytes().startswith(b"%PDF")
        review = _load(ROOT / "pdf_v2" / f"{family}_visual_review.json")
        if not review:
            assert review == {}
            continue
        assert tuple(review) == (
            "schema_version", "version", "case_id", "status", "reviewer", "reviewed_at", "checks",
        )
        assert review["case_id"] == case_id and review["status"] == "approved"
        assert tuple(review["checks"]) == (
            "mandatory_sections", "no_clipping", "no_overlap", "no_mojibake",
            "warnings_uncertainty", "unknown_hour_notice", "disclaimer",
            "future_yearly", "consultation_answer",
        )
        assert all(value in ("pass", "not_applicable") for value in review["checks"].values())


def test_machine_generator_never_creates_or_overwrites_human_approval(tmp_path):
    missing = tmp_path / "missing.json"
    golden_generator._assert_embedded_review_pending(missing)
    golden_generator._assert_visual_review_pending(missing)

    embedded = tmp_path / "embedded.json"
    supplied = {
        "status": "approved",
        "reviewer": "human-reviewer",
        "reviewed_at": "2026-09-27T12:00:00+09:00",
        "scope": "ai_reading_v2_prose_and_contract",
        "notes": ["human supplied"],
    }
    embedded.write_text(
        json.dumps({"human_review": supplied}, ensure_ascii=False),
        encoding="utf-8",
    )
    embedded_bytes = embedded.read_bytes()
    with pytest.raises(RuntimeError, match="cannot be overwritten"):
        golden_generator._assert_embedded_review_pending(embedded)
    assert embedded.read_bytes() == embedded_bytes

    visual = tmp_path / "visual_review.json"
    original = json.dumps(
        {
            "schema_version": "pdf_v2_visual_review_v1",
            "version": "pdf_v2_visual_review_v1",
            "case_id": "GC03",
            "status": "approved",
            "reviewer": "human-reviewer",
            "reviewed_at": "2026-09-27T12:00:00+09:00",
            "checks": {},
        },
        ensure_ascii=False,
    ).encode("utf-8")
    visual.write_bytes(original)
    with pytest.raises(RuntimeError, match="cannot be overwritten"):
        golden_generator._assert_visual_review_pending(visual)
    assert visual.read_bytes() == original

    pending = tmp_path / "pending_visual_review.json"
    pending.write_text("{}\n", encoding="utf-8")
    golden_generator._assert_visual_review_pending(pending)
    assert _load(pending) == {}


def test_current_repository_review_records_are_explicitly_pending():
    for directory, suffix in (
        ("ai_reading_v2", "_ai_reading_v2.json"),
        ("reading_product_v2", "_reading_product_v2.json"),
    ):
        for path in sorted((ROOT / directory).glob(f"GC*{suffix}")):
            assert _load(path)["human_review"] == {}
    for path in sorted((ROOT / "pdf_v2").glob("GC*_visual_review.json")):
        assert _load(path) == {}
