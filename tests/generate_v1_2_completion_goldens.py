"""Deterministically regenerate v1.2 machine Golden candidates.

Human approval and visual-review facts are deliberately outside this generator.
The generator refuses to touch a non-pending review slot, so a reviewed artifact
cannot be silently overwritten or carried forward across changed machine content.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import tests.test_ai_reading_v2_e2e as e2e
from engine.consultation_context import build_consultation_context
from engine.reading_product_v2 import build_reading_product_v2
from engine.reading_quality_v2 import evaluate_ai_reading_quality_v2
from engine.reading_renderer_v2 import render_reading_product_v2_html
from engine.reading_pdf_v2 import write_reading_product_v2_pdf


ROOT = Path("tests/golden/v1_2")
TARGET_DATETIME = "2026-08-10T15:36:00+09:00"
GENERATED_AT = datetime(2026, 1, 1, tzinfo=ZoneInfo("Asia/Tokyo"))


class GoldenAssessor:
    method = "golden_semantic_assessor_v1"
    version = "v1"

    def assess(self, ai_reading, reading_context, judgment_metadata):
        return {"status": "completed", "findings": []}


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def _read_existing_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise RuntimeError("existing Golden review artifact is unreadable") from None
    if not isinstance(value, dict):
        raise RuntimeError("existing Golden review artifact is invalid")
    return value


def _assert_embedded_review_pending(path: Path) -> None:
    value = _read_existing_json(path)
    review = value.get("human_review", {})
    if not isinstance(review, dict) or review:
        raise RuntimeError(
            "human-reviewed Golden cannot be overwritten by machine generation"
        )


def _assert_visual_review_pending(path: Path) -> None:
    if _read_existing_json(path):
        raise RuntimeError(
            "human visual review cannot be overwritten by machine generation"
        )


def _mutate_gc03(payload, request):
    current = next(item for item in request["trusted_catalogs"]["luck_value_sources"]
                   if item["section_id"] == "current_luck" and item["source_component"] == "current_luck")
    current_value = e2e._resolve_context_path(request["model_input"]["reading_context"], current["context_path"])
    current_number = e2e._first_plain_number(current_value)
    payload["sections"][5]["summary"] = e2e._block(
        text=f"信頼された現在運の値は{e2e._numeric_text(current_number)}です。",
        claim_type="luck_astrology", components=[current["source_component"]],
    )
    year = request["trusted_attachments"]["future_flow_years"][0]
    future = next(item for item in request["trusted_catalogs"]["luck_value_sources"]
                  if item["section_id"] == "future_flow" and item["year"] == year
                  and item["source_component"] == "integrated_luck")
    future_value = e2e._resolve_context_path(request["model_input"]["reading_context"], future["context_path"])
    future_number = e2e._first_plain_number(future_value)
    payload["future_flow_yearly"][0]["summary"] = e2e._block(
        text=f"{year}年の信頼された値は{e2e._numeric_text(future_number)}です。",
        claim_type="luck_astrology", components=[future["source_component"]],
    )


def _mutate_gc10(payload, request):
    payload["summary"]["text"] = "出生時刻不明のため、既知の三柱だけを用いて説明します。"


def build_cases():
    consultation = build_consultation_context(
        concern="仕事について相談したい", desired_future="落ち着いて働きたい",
    )
    definitions = (
        ("GC03", "GC03_1984_fukuoka_male_afternoon", e2e.gc03_chart.__wrapped__(), consultation, _mutate_gc03),
        ("GC10", "GC10_1985_ishikawa_female_unknown_birth_time", e2e.gc10_chart.__wrapped__(), None, _mutate_gc10),
    )
    cases = []
    for case_id, family, chart, consultation_context, mutate in definitions:
        artifacts = e2e._generate_pipeline(
            chart, consultation_context=consultation_context, mutate_payload=mutate,
        )
        report = evaluate_ai_reading_quality_v2(
            artifacts.reading, artifacts.reading_context, artifacts.judgment_metadata,
            semantic_assessor=GoldenAssessor(),
        )
        assert report.decision == "pass"
        product = build_reading_product_v2(
            chart, artifacts.reading_context, artifacts.reading, report,
            generated_at=GENERATED_AT,
        )
        cases.append((case_id, family, consultation_context, artifacts, report, product))
    return cases


def _manifest(category: str, entries: list[tuple[str, Path]], directory: Path) -> dict:
    files = []
    for artifact_id, path in sorted(entries):
        data = path.read_bytes()
        files.append({
            "artifact_id": artifact_id,
            "path": path.relative_to(directory).as_posix(),
            "size": len(data),
            "sha256": sha256(data).hexdigest(),
        })
    return {
        "schema_version": "golden_artifact_manifest_v2",
        "version": "golden_artifact_v2",
        "artifact_type": category,
        "file_count": len(files),
        "files": files,
    }


def generate() -> None:
    ai_dir = ROOT / "ai_reading_v2"
    product_dir = ROOT / "reading_product_v2"
    pdf_dir = ROOT / "pdf_v2"
    families = (
        "GC03_1984_fukuoka_male_afternoon",
        "GC10_1985_ishikawa_female_unknown_birth_time",
    )
    for family in families:
        _assert_embedded_review_pending(ai_dir / f"{family}_ai_reading_v2.json")
        _assert_embedded_review_pending(
            product_dir / f"{family}_reading_product_v2.json"
        )
        _assert_visual_review_pending(pdf_dir / f"{family}_visual_review.json")
    cases = build_cases()
    ai_entries = []
    product_entries = []
    pdf_entries = []
    for case_id, family, consultation, artifacts, report, product in cases:
        rc_name = f"{family}_consultation_reading_context_v2.json" if case_id == "GC03" else f"{family}_reading_context_v2.json"
        if case_id == "GC03":
            _write_json(ROOT / "reading_context" / rc_name, artifacts.reading_context)
        ai_path = ai_dir / f"{family}_ai_reading_v2.json"
        ai_golden = {
            "schema_version": "ai_reading_v2_golden_v1",
            "version": "ai_reading_v2_golden_v1",
            "case_id": case_id,
            "source_references": {
                "chart_fixture_id": family,
                "reading_context_fixture": f"tests/golden/v1_2/reading_context/{rc_name}",
                "target_datetime": TARGET_DATETIME,
                "consultation_context": deepcopy(consultation),
            },
            "provider_model": "test-model",
            "provider_response": artifacts.payload,
            "ai_reading": artifacts.reading,
            "quality_report": report.to_dict(),
            "human_review": {},
        }
        _write_json(ai_path, ai_golden)
        ai_entries.append((f"{case_id}:ai_reading_v2", ai_path))
        product_path = product_dir / f"{family}_reading_product_v2.json"
        product_golden = {
            "schema_version": "reading_product_v2_golden_v1",
            "version": "reading_product_v2_golden_v1",
            "case_id": case_id,
            "source_ai_reading_golden": f"tests/golden/v1_2/ai_reading_v2/{ai_path.name}",
            "generated_at": GENERATED_AT.isoformat(timespec="seconds"),
            "reading_product": product.to_dict(),
            "human_review": {},
        }
        _write_json(product_path, product_golden)
        product_entries.append((f"{case_id}:reading_product_v2", product_path))
        html_path = pdf_dir / f"{family}.html"
        html_path.parent.mkdir(parents=True, exist_ok=True)
        html_path.write_text(render_reading_product_v2_html(product), encoding="utf-8")
        pdf_path = pdf_dir / f"{family}.pdf"
        write_reading_product_v2_pdf(product, pdf_path)
        review_path = pdf_dir / f"{family}_visual_review.json"
        _write_json(review_path, {})
        pdf_entries.extend((
            (f"{case_id}:html", html_path), (f"{case_id}:pdf", pdf_path),
            (f"{case_id}:visual_review", review_path),
        ))
    _write_json(ai_dir / "manifest.json", _manifest("ai_reading_v2", ai_entries, ai_dir))
    _write_json(product_dir / "manifest.json", _manifest("reading_product_v2", product_entries, product_dir))
    _write_json(pdf_dir / "manifest.json", _manifest("pdf_v2", pdf_entries, pdf_dir))
    rc_dir = ROOT / "reading_context"
    rc_files = sorted(rc_dir.glob("*.json"))
    rc_files = [path for path in rc_files if path.name != "manifest.json"]
    _write_json(rc_dir / "manifest.json", {
        "baseline": "Yakumo Engine v1.2", "file_count": len(rc_files),
        "files": [{"name": path.name, "size": len(path.read_bytes()), "sha256": sha256(path.read_bytes()).hexdigest()} for path in rc_files],
    })
    root_manifest_path = ROOT / "manifest.json"
    root_manifest = json.loads(root_manifest_path.read_text(encoding="utf-8"))
    retained = [entry for entry in root_manifest["files"] if not entry["path"].startswith("reading_context/")]
    context_entries = [{
        "path": f"reading_context/{path.name}",
        "size": len(path.read_bytes()),
        "sha256": sha256(path.read_bytes()).hexdigest(),
    } for path in rc_files]
    root_files = sorted(retained + context_entries, key=lambda entry: entry["path"])
    _write_json(root_manifest_path, {
        "baseline": root_manifest["baseline"], "file_count": len(root_files), "files": root_files,
    })


if __name__ == "__main__":
    generate()
