"""Frozen section 26 renderer and PDF v2 tests."""

from copy import deepcopy
from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

import pytest

import tests.test_ai_reading_v2_e2e as e2e
import engine.reading_pdf_v2 as pdf_v2
import engine.reading_renderer_v2 as renderer_v2
from engine.reading_pdf_v2 import (
    READING_PDF_V2_TEMPLATE_VERSION,
    ReadingPdfV2DependencyError,
    ReadingPdfV2Error,
    ReadingPdfV2GenerationError,
    ReadingPdfV2ValidationError,
    render_reading_product_v2_pdf_bytes,
    render_reading_product_v2_pdf_bytes_async,
    write_reading_product_v2_pdf,
    write_reading_product_v2_pdf_async,
)
from engine.reading_product_v2 import build_reading_product_v2
from engine.reading_quality_v2 import evaluate_ai_reading_quality_v2
from engine.reading_renderer_v2 import render_reading_product_v2_html


class Assessor:
    method = "pdf_v2_test_assessor"
    version = "v1"

    def assess(self, ai_reading, reading_context, judgment_metadata):
        return {"status": "completed", "findings": []}


def _product(case="gc03"):
    chart = (e2e.gc03_chart if case == "gc03" else e2e.gc10_chart).__wrapped__()
    artifacts = e2e._generate_pipeline(chart)
    report = evaluate_ai_reading_quality_v2(
        artifacts.reading, artifacts.reading_context, artifacts.judgment_metadata,
        semantic_assessor=Assessor(),
    )
    return build_reading_product_v2(
        chart, artifacts.reading_context, artifacts.reading, report,
        generated_at=datetime(2026, 1, 1, tzinfo=ZoneInfo("Asia/Tokyo")),
    )


def _product_with_prose(text):
    chart = e2e.gc03_chart.__wrapped__()
    artifacts = e2e._generate_pipeline(chart)
    reading = deepcopy(artifacts.reading)
    section = next(
        item for item in reading["sections"]
        if item["section_id"] == "core_personality"
    )
    section["summary"]["text"] = text
    report = evaluate_ai_reading_quality_v2(
        reading, artifacts.reading_context, artifacts.judgment_metadata,
        semantic_assessor=Assessor(),
    )
    assert report.decision == "pass"
    return build_reading_product_v2(
        chart, artifacts.reading_context, reading, report,
        generated_at=datetime(2026, 1, 1, tzinfo=ZoneInfo("Asia/Tokyo")),
    )


class Page:
    def __init__(self, data=b"%PDF-fake-v2"):
        self.data = data
        self.html = None

    async def set_content(self, html, **kwargs):
        self.html = html

    async def pdf(self, **kwargs):
        return self.data


class Browser:
    def __init__(self, page):
        self.page = page

    async def new_page(self):
        return self.page

    async def close(self):
        return None


class Chromium:
    def __init__(self, browser):
        self.browser = browser

    async def launch(self):
        return self.browser


class Manager:
    def __init__(self, page):
        self.playwright = type("PW", (), {"chromium": Chromium(Browser(page))})()

    async def __aenter__(self):
        return self.playwright

    async def __aexit__(self, *args):
        return None


class FailingManager:
    async def __aenter__(self):
        raise PermissionError("cannot start driver")

    async def __aexit__(self, *args):
        return None


def _install_backend(monkeypatch, data=b"%PDF-fake-v2"):
    page = Page(data)
    monkeypatch.setattr(pdf_v2, "_load_playwright", lambda: lambda: Manager(page))
    return page


def test_renderer_is_deterministic_product_only_and_has_exact_identity():
    product = _product()
    first = render_reading_product_v2_html(product)
    second = render_reading_product_v2_html(product)
    assert first == second
    assert first.startswith("<!DOCTYPE html>")
    assert f'content="{READING_PDF_V2_TEMPLATE_VERSION}"' in first
    headings = ["表紙", "基本情報", "命式", "日主", "五行", "月令・通根", "身強身弱",
                "干支関係", "格局", "用神", "本質・性格", "仕事・適職", "金運",
                "恋愛・人間関係", "健康傾向", "現在大運", "現在歳運", "今後の流れ",
                "長期大運", "総合アドバイス", "注意事項・免責"]
    positions = [first.index(f">{heading}<") for heading in headings]
    assert positions == sorted(positions)


def test_current_luck_calculation_and_ai_prose_keep_separate_product_authorities():
    product = _product()
    before = product.to_dict()
    html = render_reading_product_v2_html(product)
    current_luck = before["reading_context"]["luck"]["current_luck"]
    current_pillar = current_luck["current_pillar"]
    progress = current_luck["progress"]
    current_section = next(
        section
        for section in before["ai_reading"]["sections"]
        if section["section_id"] == "current_luck"
    )

    for expected in (
        current_pillar["ganzhi"],
        current_pillar["stem_ten_god"],
        f'{current_pillar["start_age"]:.1f}',
        f'{current_pillar["end_age"]:.1f}',
        f'{current_luck["exact_age"]:.1f}',
        f'{progress["progress_percent"]:.1f}',
        f'{current_luck["years_until_next_luck"]:.1f}',
    ):
        assert expected in html
    assert current_section["summary"]["text"] in html
    assert current_section["detail"]["text"] in html
    assert "has_current_luck" not in html
    assert "current_pillar" not in html
    assert product.to_dict() == before


def test_existing_annual_and_long_term_luck_snapshots_remain_visible():
    product = _product()
    value = product.to_dict()
    html = render_reading_product_v2_html(product)

    annual = value["reading_context"]["luck"]["annual_luck"]
    for field in ("year", "ganzhi", "stem", "branch", "stem_ten_god", "twelve_stage"):
        assert str(annual[field]) in html
    long_term = value["reading_context"]["luck"]["luck_pillars"]
    assert long_term["direction_japanese"] in html
    assert f'{long_term["start_age"]:.1f}' in html
    for pillar in long_term["pillars"]:
        for field in ("ganzhi", "stem_ten_god"):
            assert str(pillar[field]) in html
        assert f'{pillar["start_age"]:.1f}' in html
        assert f'{pillar["end_age"]:.1f}' in html
    assert "stem_useful_relation" not in html
    assert "branch_useful_relation" not in html


def test_warning_uncertainty_and_unknown_hour_use_final_ai_catalog_only():
    product = _product("gc10")
    value = product.to_dict()
    html = render_reading_product_v2_html(product)
    for entry in value["ai_reading"]["warnings"]:
        assert entry["value"] in html
        assert entry["warning_id"] not in html
    for entry in value["ai_reading"]["uncertainty"]:
        assert entry["value"]["message"] in html
        assert entry["uncertainty_id"] not in html
    assert "出生時刻不明" in html
    assert "source_contract" not in html
    assert "source_path" not in html
    assert value["ai_reading"]["disclaimer"] in html


@pytest.mark.parametrize("case", ["gc03", "gc10"])
def test_customer_html_has_no_raw_structure_or_internal_field_leak(case):
    html = render_reading_product_v2_html(_product(case))
    forbidden = (
        "has_current_luck", "exact_age", "current_pillar",
        "stem_useful_relation", "branch_useful_relation", "warning_id",
        "uncertainty_id", "source_contract", "source_path",
        "technical_pattern", "technical_label",
    )
    assert all(token not in html for token in forbidden)
    assert "<pre" not in html
    assert "&quot;birth_date&quot;" not in html
    assert "&quot;pillars&quot;" not in html
    assert "{'" not in html and "['" not in html


def test_relation_presenter_supports_pair_trine_and_punishment_owner_shapes():
    relations = {
        "clashes": {"clashes": [{
            "position_a": "year", "branch_a": "子",
            "position_b": "month", "branch_b": "午", "relation": "冲",
        }]},
        "combinations": {"combinations": []},
        "trines": {"trines": [{
            "position_a": "year", "branch_a": "申",
            "position_b": "month", "branch_b": "子",
            "position_c": "day", "branch_c": "辰",
            "relation": "三合", "trine_name": "申子辰", "element": "水",
        }]},
        "punishments": {"punishments": [{
            "positions": ["year", "month", "day"],
            "branches": ["寅", "巳", "申"],
            "relation": "刑", "punishment_type": "三刑", "punishment_name": "寅巳申",
        }]},
        "harms": {"harms": []},
        "breaks": {"breaks": []},
    }
    html = renderer_v2._render_relations({"relations": relations})
    for expected in (
        "六冲", "年柱「子」", "月柱「午」", "三合", "申子辰", "水",
        "刑", "年柱「寅」", "月柱「巳」", "日柱「申」", "三刑", "寅巳申",
    ):
        assert expected in html
    assert "position_a" not in html
    assert "punishment_type" not in html


@pytest.mark.parametrize("case", ["gc03", "gc10"])
def test_structured_customer_facts_are_preserved_in_readable_form(case):
    product = _product(case)
    value = product.to_dict()
    rc = value["reading_context"]
    ai = value["ai_reading"]
    html = render_reading_product_v2_html(product)

    subject = rc["subject"]
    for field in ("birth_date", "birth_place"):
        assert subject[field] in html
    if subject["birth_time"] is None:
        assert "出生時刻不明" in html
        assert ">不明<" in html
    else:
        assert subject["birth_time"] in html
    for pillar in rc["chart"]["pillars"].values():
        if pillar is not None:
            for field in ("stem", "branch", "twelve_stage"):
                assert pillar[field] in html
    assert rc["strength"]["label"] in html
    assert str(rc["strength"]["final_score"]) in html
    assert rc["pattern"]["primary_pattern"] in html
    assert rc["useful_gods"]["primary_useful_element"] in html
    for element in rc["useful_gods"]["final_useful_elements"]:
        assert element in html
    current = rc["luck"]["current_luck"]
    assert current["current_pillar"]["ganzhi"] in html
    assert f'{current["progress"]["progress_percent"]:.1f}' in html
    annual = rc["luck"]["annual_luck"]
    assert annual["ganzhi"] in html
    future = next(section for section in ai["sections"] if section["section_id"] == "future_flow")
    for yearly in future["yearly"]:
        assert f'{yearly["year"]}年' in html
        assert yearly["summary"]["text"] in html
        assert yearly["detail"]["text"] in html
    for pillar in rc["luck"]["luck_pillars"]["pillars"]:
        assert pillar["ganzhi"] in html
    if ai["consultation_answer"] is not None:
        assert ai["consultation_answer"]["text"] in html
    assert ai["disclaimer"] in html


def test_realistic_long_japanese_prose_is_exactly_preserved_escaped_and_pdf_safe(monkeypatch):
    prose = (
        "これは表示確認用の文章です。複数の文と日本語の句読点を含みます。"
        "長い文章でも段落内で自然に折り返され、内容そのものは変更されません。"
        "HTML安全性の確認として <script>alert(\"x\")</script> & '引用' を含めます。"
        "これは占術上の判断ではなく、純粋な表示試験用テキストです。"
    ) * 4
    product = _product_with_prose(prose)
    before = product.to_dict()
    html = render_reading_product_v2_html(product)
    assert prose not in html
    assert escape(prose) in html
    assert "<script>alert" not in html
    assert "white-space:pre-wrap" in html
    assert "overflow-wrap:anywhere" in html
    page = _install_backend(monkeypatch)
    assert render_reading_product_v2_pdf_bytes(product).startswith(b"%PDF")
    assert escape(prose) in page.html
    assert product.to_dict() == before


def test_pdf_exception_hierarchy_is_exact():
    assert issubclass(ReadingPdfV2ValidationError, ReadingPdfV2Error)
    assert issubclass(ReadingPdfV2DependencyError, ReadingPdfV2Error)
    assert issubclass(ReadingPdfV2GenerationError, ReadingPdfV2Error)


def test_sync_bytes_and_path_apis(monkeypatch, tmp_path):
    _install_backend(monkeypatch)
    product = _product()
    assert render_reading_product_v2_pdf_bytes(product).startswith(b"%PDF")
    path = write_reading_product_v2_pdf(product, tmp_path / "reading.pdf")
    assert path.is_file() and path.read_bytes().startswith(b"%PDF")


@pytest.mark.asyncio
async def test_async_bytes_and_path_apis(monkeypatch, tmp_path):
    _install_backend(monkeypatch)
    product = _product()
    assert (await render_reading_product_v2_pdf_bytes_async(product)).startswith(b"%PDF")
    path = await write_reading_product_v2_pdf_async(product, tmp_path / "nested" / "reading.pdf")
    assert path.is_file()


@pytest.mark.asyncio
async def test_sync_api_rejected_inside_running_loop():
    with pytest.raises(ReadingPdfV2GenerationError):
        render_reading_product_v2_pdf_bytes(_product())


@pytest.mark.parametrize("option,value", [("page_format", "Letter"), ("print_background", 1), ("timeout_ms", True)])
def test_invalid_options_fail_before_dependency(monkeypatch, option, value):
    monkeypatch.setattr(pdf_v2, "_load_playwright", lambda: (_ for _ in ()).throw(AssertionError()))
    with pytest.raises(ReadingPdfV2ValidationError):
        render_reading_product_v2_pdf_bytes(_product(), **{option: value})


def test_dependency_and_invalid_backend_are_typed(monkeypatch):
    monkeypatch.setattr(pdf_v2, "_load_playwright", lambda: None)
    with pytest.raises(ReadingPdfV2DependencyError):
        render_reading_product_v2_pdf_bytes(_product())
    _install_backend(monkeypatch, b"not-pdf")
    with pytest.raises(ReadingPdfV2GenerationError):
        render_reading_product_v2_pdf_bytes(_product())


def test_playwright_driver_start_failure_is_dependency_error(monkeypatch):
    monkeypatch.setattr(pdf_v2, "_load_playwright", lambda: lambda: FailingManager())
    with pytest.raises(ReadingPdfV2DependencyError):
        render_reading_product_v2_pdf_bytes(_product())


def test_renderer_rejects_non_product():
    with pytest.raises(ReadingPdfV2ValidationError):
        render_reading_product_v2_html({})
