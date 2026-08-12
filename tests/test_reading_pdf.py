"""
tests/test_reading_pdf.py

engine/reading_pdf.py の非LIVE品質テスト。

目的
----
ReadingProduct
    ↓
reading_renderer.py
    ↓
HTML
    ↓
reading_pdf.py
    ↓
PDF

というPDF商品化レイヤーについて、
OpenAI APIを呼ばず、Chromium実起動も原則行わずに
契約・安全性・同期/非同期API・依存関係処理を検証する。

主な検証内容
------------
1. 定数・metadata
2. ReadingProduct以外を拒否
3. .pdf以外の出力先を拒否
4. timeout / page_format等の入力検証
5. rendererの完全HTMLをそのまま利用
6. APIキー・内部promptの混入を拒否
7. write_reading_product_pdf_async() の接続
8. write_reading_product_pdf() の同期ラッパー
9. PDF bytes API
10. 実行中event loopで同期APIを拒否
11. dependency error
12. 生成ファイル不存在 / 空ファイルの検出
13. PDF magic header確認
14. 占術再計算・AI文章再生成をしないmetadata
15. 最終品質ゲート

このテストは非LIVE。
OpenAI API料金は発生しない。

Playwright本体やChromiumが未導入でも、
大半のテストはmockにより実行可能。

Version
-------
reading_pdf_test_v1
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

import pytest

import engine.reading_pdf as reading_pdf_module
from engine.reading_pdf import (
    DEFAULT_PAGE_FORMAT,
    DEFAULT_PREFER_CSS_PAGE_SIZE,
    DEFAULT_PRINT_BACKGROUND,
    DEFAULT_TIMEOUT_MS,
    READING_PDF_METHOD,
    READING_PDF_STATUS,
    READING_PDF_VERSION,
    ReadingPdfDependencyError,
    ReadingPdfGenerationError,
    ReadingPdfValidationError,
    build_reading_pdf_html,
    get_reading_pdf_metadata,
    render_reading_product_pdf_bytes,
    render_reading_product_pdf_bytes_async,
    write_reading_product_pdf,
    write_reading_product_pdf_async,
)
from engine.reading_product import ReadingProduct


# ============================================================
# Fixtures
# ============================================================


def _make_section(
    key: str,
    title: str,
) -> dict[str, Any]:
    return {
        "key": key,
        "title": title,
        "summary": (
            f"{title}の要約です。"
        ),
        "detail": (
            f"{title}の詳細本文です。"
        ),
        "evidence": [
            f"{title}の根拠1",
            f"{title}の根拠2",
        ],
        "advice": [
            f"{title}の助言1",
            f"{title}の助言2",
        ],
    }


@pytest.fixture
def sample_product() -> ReadingProduct:
    sections = (
        _make_section(
            "core_personality",
            "本質・性格",
        ),
        _make_section(
            "career",
            "仕事・適職",
        ),
        _make_section(
            "wealth",
            "金運",
        ),
        _make_section(
            "relationships",
            "恋愛・人間関係",
        ),
        _make_section(
            "health",
            "健康傾向",
        ),
        _make_section(
            "current_luck",
            "現在の運勢",
        ),
        _make_section(
            "future_flow",
            "今後の流れ",
        ),
        _make_section(
            "advice",
            "開運アドバイス",
        ),
    )

    return ReadingProduct(
        title="四柱推命 AI鑑定書",

        subject={
            "birth_date": "1985-07-17",
            "birth_time": "21:50",
            "birth_place": "石川県",
            "gender": "female",
            "timezone": "Asia/Tokyo",
        },

        chart_summary={
            "pillar_sequence": [
                "乙丑",
                "癸未",
                "丁巳",
                "辛亥",
            ],

            "pillars": {
                "year": {
                    "position": "year",
                    "pillar": "乙丑",
                    "stem": "乙",
                    "branch": "丑",
                    "stem_ten_god": "偏印",
                    "twelve_stage": "墓",
                    "main_hidden_stem": "己",
                    "main_hidden_stem_ten_god": (
                        "食神"
                    ),
                },
                "month": {
                    "position": "month",
                    "pillar": "癸未",
                    "stem": "癸",
                    "branch": "未",
                    "stem_ten_god": "偏官",
                    "twelve_stage": "冠帯",
                    "main_hidden_stem": "己",
                    "main_hidden_stem_ten_god": (
                        "食神"
                    ),
                },
                "day": {
                    "position": "day",
                    "pillar": "丁巳",
                    "stem": "丁",
                    "branch": "巳",
                    "stem_ten_god": "日主",
                    "twelve_stage": "帝旺",
                    "main_hidden_stem": "丙",
                    "main_hidden_stem_ten_god": (
                        "劫財"
                    ),
                },
                "hour": {
                    "position": "hour",
                    "pillar": "辛亥",
                    "stem": "辛",
                    "branch": "亥",
                    "stem_ten_god": "偏財",
                    "twelve_stage": "胎",
                    "main_hidden_stem": "壬",
                    "main_hidden_stem_ten_god": (
                        "正官"
                    ),
                },
            },

            "day_master": {
                "stem": "丁",
                "element": "火",
                "yin_yang": "陰",
                "day_pillar": "丁巳",
            },

            "five_elements": {
                "weighted_scores": {
                    "木": 18.0,
                    "火": 23.0,
                    "土": 20.0,
                    "金": 14.0,
                    "水": 25.0,
                },
                "strongest_element": "水",
                "weakest_element": "金",
            },

            "strength": {
                "label": "中和",
                "technical_label": "balanced",
                "final_score": 50.0,
            },

            "pattern": {
                "primary_pattern": "食神格",
                "technical_pattern": "食神格",
                "overall_judgment": "成立",
            },

            "useful_gods": {
                "primary_useful_element": "金",
                "secondary_useful_elements": [
                    "水",
                    "木",
                    "土",
                ],
                "unfavorable_elements": [
                    "火",
                ],
            },

            "current_luck": {
                "ganzhi": "丁亥",
                "stem_ten_god": "比肩",
                "start_age": 37,
                "end_age": 47,
            },

            "annual_luck": {
                "year": 2026,
                "ganzhi": "丙午",
                "stem_ten_god": "劫財",
                "twelve_stage": "建禄",
            },
        },

        sections=sections,

        summary=(
            "丁日主と食神格を活かし、"
            "仕組み化を加えると安定しやすい命式です。"
        ),

        disclaimer=(
            "本鑑定は傾向を示すものであり、"
            "将来を確定的に断定するものではありません。"
            "医学・医療上の判断は専門家へご相談ください。"
        ),

        generation={
            "model": "gpt-5",
            "response_id": "resp_test_pdf_001",
            "response_status": "completed",
            "usage": {
                "input_tokens": 100,
                "output_tokens": 200,
                "total_tokens": 300,
            },
            "sections": [
                section[
                    "key"
                ]
                for section
                in sections
            ],
            "method": (
                "openai_responses_api_v1"
            ),
            "status": "completed",
        },

        metadata={
            "created_at": (
                "2026-08-12T00:00:00+00:00"
            ),
            "reading_context_schema": (
                "reading_context_v1"
            ),
            "reading_context_method": (
                "reading_context_v1"
            ),
            "reading_context_status": (
                "ready_for_ai_reading"
            ),
            "source_metadata": {},
            "product_version": (
                "reading_product_v1"
            ),
            "recalculates_astrology": False,
            "rewrites_ai_reading": False,
        },
    )


# ============================================================
# Constants
# ============================================================


def test_pdf_version():
    assert (
        READING_PDF_VERSION
        == "reading_pdf_v1"
    )


def test_pdf_method():
    assert (
        READING_PDF_METHOD
        == (
            "html_to_pdf_playwright_chromium_v1"
        )
    )


def test_pdf_status():
    assert (
        READING_PDF_STATUS
        == "ready"
    )


def test_default_page_format():
    assert (
        DEFAULT_PAGE_FORMAT
        == "A4"
    )


def test_default_print_background():
    assert (
        DEFAULT_PRINT_BACKGROUND
        is True
    )


def test_default_prefer_css_page_size():
    assert (
        DEFAULT_PREFER_CSS_PAGE_SIZE
        is True
    )


def test_default_timeout_positive():
    assert isinstance(
        DEFAULT_TIMEOUT_MS,
        int,
    )
    assert (
        DEFAULT_TIMEOUT_MS
        > 0
    )


# ============================================================
# Metadata
# ============================================================


def test_pdf_metadata_contract():
    metadata = (
        get_reading_pdf_metadata()
    )

    assert (
        metadata[
            "version"
        ]
        == READING_PDF_VERSION
    )

    assert (
        metadata[
            "method"
        ]
        == READING_PDF_METHOD
    )

    assert (
        metadata[
            "status"
        ]
        == READING_PDF_STATUS
    )

    assert (
        metadata[
            "input_type"
        ]
        == "ReadingProduct"
    )

    assert (
        metadata[
            "intermediate_type"
        ]
        == "html_document"
    )

    assert (
        metadata[
            "backend"
        ]
        == "playwright_chromium"
    )

    assert (
        metadata[
            "uses_reading_renderer"
        ]
        is True
    )

    assert (
        metadata[
            "recalculates_astrology"
        ]
        is False
    )

    assert (
        metadata[
            "rewrites_ai_reading"
        ]
        is False
    )

    assert (
        metadata[
            "exposes_generation_metadata"
        ]
        is False
    )

    assert (
        metadata[
            "exposes_api_key"
        ]
        is False
    )

    assert (
        metadata[
            "async_supported"
        ]
        is True
    )


# ============================================================
# Input validation
# ============================================================


@pytest.mark.parametrize(
    "bad_value",
    (
        None,
        {},
        [],
        "product",
        123,
    ),
)
def test_build_pdf_html_rejects_non_product(
    bad_value,
):
    with pytest.raises(
        TypeError
    ):
        build_reading_pdf_html(
            bad_value
        )


@pytest.mark.parametrize(
    "bad_path",
    (
        "reading.html",
        "reading.txt",
        "reading.json",
        "reading",
    ),
)
def test_write_pdf_rejects_non_pdf_path(
    sample_product,
    bad_path,
):
    with pytest.raises(
        ValueError
    ):
        write_reading_product_pdf(
            sample_product,
            bad_path,
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad_path",
    (
        "reading.html",
        "reading.txt",
        "reading.json",
        "reading",
    ),
)
async def test_write_pdf_async_rejects_non_pdf_path(
    sample_product,
    bad_path,
):
    with pytest.raises(
        ValueError
    ):
        await (
            write_reading_product_pdf_async(
                sample_product,
                bad_path,
            )
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad_timeout",
    (
        0,
        -1,
        -100,
    ),
)
async def test_async_rejects_non_positive_timeout(
    sample_product,
    tmp_path,
    bad_timeout,
):
    with pytest.raises(
        ValueError
    ):
        await (
            write_reading_product_pdf_async(
                sample_product,
                tmp_path / "a.pdf",
                timeout_ms=bad_timeout,
            )
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad_timeout",
    (
        1.5,
        "30000",
        True,
        None,
    ),
)
async def test_async_rejects_non_int_timeout(
    sample_product,
    tmp_path,
    bad_timeout,
):
    with pytest.raises(
        TypeError
    ):
        await (
            write_reading_product_pdf_async(
                sample_product,
                tmp_path / "a.pdf",
                timeout_ms=bad_timeout,
            )
        )


@pytest.mark.asyncio
async def test_async_rejects_blank_page_format(
    sample_product,
    tmp_path,
):
    with pytest.raises(
        ValueError
    ):
        await (
            write_reading_product_pdf_async(
                sample_product,
                tmp_path / "a.pdf",
                page_format="   ",
            )
        )


@pytest.mark.asyncio
async def test_async_rejects_non_string_page_format(
    sample_product,
    tmp_path,
):
    with pytest.raises(
        TypeError
    ):
        await (
            write_reading_product_pdf_async(
                sample_product,
                tmp_path / "a.pdf",
                page_format=123,
            )
        )


@pytest.mark.asyncio
async def test_async_rejects_non_bool_print_background(
    sample_product,
    tmp_path,
):
    with pytest.raises(
        TypeError
    ):
        await (
            write_reading_product_pdf_async(
                sample_product,
                tmp_path / "a.pdf",
                print_background="yes",
            )
        )


@pytest.mark.asyncio
async def test_async_rejects_non_bool_prefer_css_page_size(
    sample_product,
    tmp_path,
):
    with pytest.raises(
        TypeError
    ):
        await (
            write_reading_product_pdf_async(
                sample_product,
                tmp_path / "a.pdf",
                prefer_css_page_size="yes",
            )
        )


# ============================================================
# HTML building
# ============================================================


def test_build_pdf_html_returns_full_document(
    sample_product,
):
    result = (
        build_reading_pdf_html(
            sample_product
        )
    )

    assert isinstance(
        result,
        str,
    )

    assert result.startswith(
        "<!DOCTYPE html>"
    )

    assert (
        '<html lang="ja">'
        in result
    )


def test_build_pdf_html_contains_chart(
    sample_product,
):
    result = (
        build_reading_pdf_html(
            sample_product
        )
    )

    for pillar in (
        "乙丑",
        "癸未",
        "丁巳",
        "辛亥",
    ):
        assert (
            pillar
            in result
        )


def test_build_pdf_html_contains_sections(
    sample_product,
):
    result = (
        build_reading_pdf_html(
            sample_product
        )
    )

    for title in (
        "本質・性格",
        "仕事・適職",
        "金運",
        "恋愛・人間関係",
        "健康傾向",
        "現在の運勢",
        "今後の流れ",
        "開運アドバイス",
    ):
        assert (
            title
            in result
        )


def test_build_pdf_html_contains_print_css(
    sample_product,
):
    result = (
        build_reading_pdf_html(
            sample_product
        )
    )

    assert (
        "@page"
        in result
    )

    assert (
        "size: A4"
        in result
    )

    assert (
        "@media print"
        in result
    )


def test_build_pdf_html_custom_document_title(
    sample_product,
):
    result = (
        build_reading_pdf_html(
            sample_product,
            document_title=(
                "八雲 四柱推命鑑定書"
            ),
        )
    )

    assert (
        "<title>八雲 四柱推命鑑定書</title>"
        in result
    )


def test_build_pdf_html_blank_document_title_falls_back(
    sample_product,
):
    result = (
        build_reading_pdf_html(
            sample_product,
            document_title="   ",
        )
    )

    assert (
        "<title>四柱推命 AI鑑定書</title>"
        in result
    )


def test_build_pdf_html_rejects_non_string_document_title(
    sample_product,
):
    with pytest.raises(
        TypeError
    ):
        build_reading_pdf_html(
            sample_product,
            document_title=123,
        )


# ============================================================
# Security
# ============================================================


def test_build_pdf_html_does_not_expose_generation_metadata(
    sample_product,
):
    result = (
        build_reading_pdf_html(
            sample_product
        )
    )

    assert (
        "resp_test_pdf_001"
        not in result
    )

    assert (
        "openai_responses_api_v1"
        not in result
    )


def test_security_rejects_actual_api_key(
    sample_product,
    monkeypatch,
):
    monkeypatch.setenv(
        "OPENAI_API_KEY",
        "sk-test-secret-value",
    )

    def fake_renderer(
        product,
        **kwargs,
    ):
        return (
            "<!DOCTYPE html>"
            "<html><body>"
            "sk-test-secret-value"
            "</body></html>"
        )

    monkeypatch.setattr(
        reading_pdf_module,
        "render_reading_product_html",
        fake_renderer,
    )

    with pytest.raises(
        ReadingPdfValidationError
    ):
        build_reading_pdf_html(
            sample_product
        )


@pytest.mark.parametrize(
    "marker",
    (
        '"api_key"',
        "'api_key'",
        '"system_prompt"',
        "'system_prompt'",
        '"user_prompt"',
        "'user_prompt'",
    ),
)
def test_security_rejects_private_markers(
    sample_product,
    monkeypatch,
    marker,
):
    def fake_renderer(
        product,
        **kwargs,
    ):
        return (
            "<!DOCTYPE html>"
            "<html><body>"
            f"{marker}"
            "</body></html>"
        )

    monkeypatch.setattr(
        reading_pdf_module,
        "render_reading_product_html",
        fake_renderer,
    )

    with pytest.raises(
        ReadingPdfValidationError
    ):
        build_reading_pdf_html(
            sample_product
        )


def test_build_pdf_html_rejects_non_full_html(
    sample_product,
    monkeypatch,
):
    def fake_renderer(
        product,
        **kwargs,
    ):
        return (
            "<html><body>"
            "fragment"
            "</body></html>"
        )

    monkeypatch.setattr(
        reading_pdf_module,
        "render_reading_product_html",
        fake_renderer,
    )

    with pytest.raises(
        ReadingPdfGenerationError
    ):
        build_reading_pdf_html(
            sample_product
        )


def test_build_pdf_html_rejects_non_string_renderer_result(
    sample_product,
    monkeypatch,
):
    def fake_renderer(
        product,
        **kwargs,
    ):
        return None

    monkeypatch.setattr(
        reading_pdf_module,
        "render_reading_product_html",
        fake_renderer,
    )

    with pytest.raises(
        ReadingPdfGenerationError
    ):
        build_reading_pdf_html(
            sample_product
        )


# ============================================================
# Dependency loader
# ============================================================


def test_load_playwright_dependency_error(
    monkeypatch,
):
    real_import = __import__

    def fake_import(
        name,
        globals=None,
        locals=None,
        fromlist=(),
        level=0,
    ):
        if (
            name
            == "playwright.async_api"
        ):
            raise ImportError(
                "playwright not installed"
            )

        return real_import(
            name,
            globals,
            locals,
            fromlist,
            level,
        )

    monkeypatch.setattr(
        "builtins.__import__",
        fake_import,
    )

    with pytest.raises(
        ReadingPdfDependencyError
    ):
        reading_pdf_module._load_playwright()


# ============================================================
# Async write API
# ============================================================


@pytest.mark.asyncio
async def test_async_write_calls_core_renderer(
    sample_product,
    tmp_path,
    monkeypatch,
):
    captured = {}

    async def fake_render(
        html_document,
        output_path,
        *,
        page_format,
        print_background,
        prefer_css_page_size,
        timeout_ms,
    ):
        captured[
            "html_document"
        ] = html_document
        captured[
            "output_path"
        ] = output_path
        captured[
            "page_format"
        ] = page_format
        captured[
            "print_background"
        ] = print_background
        captured[
            "prefer_css_page_size"
        ] = prefer_css_page_size
        captured[
            "timeout_ms"
        ] = timeout_ms

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_path.write_bytes(
            b"%PDF-1.7\nfake"
        )

        return output_path

    monkeypatch.setattr(
        reading_pdf_module,
        "_render_html_to_pdf_async",
        fake_render,
    )

    output = (
        tmp_path
        / "reading.pdf"
    )

    result = await (
        write_reading_product_pdf_async(
            sample_product,
            output,
            page_format="A4",
            print_background=True,
            prefer_css_page_size=True,
            timeout_ms=12345,
        )
    )

    assert (
        result
        == output
    )

    assert (
        captured[
            "output_path"
        ]
        == output
    )

    assert (
        captured[
            "page_format"
        ]
        == "A4"
    )

    assert (
        captured[
            "print_background"
        ]
        is True
    )

    assert (
        captured[
            "prefer_css_page_size"
        ]
        is True
    )

    assert (
        captured[
            "timeout_ms"
        ]
        == 12345
    )

    assert (
        "<!DOCTYPE html>"
        in captured[
            "html_document"
        ]
    )


@pytest.mark.asyncio
async def test_async_write_passes_custom_document_title(
    sample_product,
    tmp_path,
    monkeypatch,
):
    captured = {}

    async def fake_render(
        html_document,
        output_path,
        **kwargs,
    ):
        captured[
            "html_document"
        ] = html_document

        output_path.write_bytes(
            b"%PDF-1.7\nfake"
        )

        return output_path

    monkeypatch.setattr(
        reading_pdf_module,
        "_render_html_to_pdf_async",
        fake_render,
    )

    await (
        write_reading_product_pdf_async(
            sample_product,
            tmp_path / "reading.pdf",
            document_title=(
                "カスタムPDFタイトル"
            ),
        )
    )

    assert (
        "<title>カスタムPDFタイトル</title>"
        in captured[
            "html_document"
        ]
    )


# ============================================================
# Sync write API
# ============================================================


def test_sync_write_uses_async_api(
    sample_product,
    tmp_path,
    monkeypatch,
):
    output = (
        tmp_path
        / "reading.pdf"
    )

    async def fake_async(
        product,
        output_path,
        **kwargs,
    ):
        output_path = Path(
            output_path
        )

        output_path.write_bytes(
            b"%PDF-1.7\nsync-fake"
        )

        return output_path

    monkeypatch.setattr(
        reading_pdf_module,
        "write_reading_product_pdf_async",
        fake_async,
    )

    result = (
        write_reading_product_pdf(
            sample_product,
            output,
        )
    )

    assert (
        result
        == output
    )

    assert output.exists()


@pytest.mark.asyncio
async def test_sync_write_rejected_inside_running_loop(
    sample_product,
    tmp_path,
):
    with pytest.raises(
        ReadingPdfGenerationError
    ):
        write_reading_product_pdf(
            sample_product,
            tmp_path / "reading.pdf",
        )


# ============================================================
# PDF bytes API
# ============================================================


@pytest.mark.asyncio
async def test_pdf_bytes_async(
    sample_product,
    monkeypatch,
):
    async def fake_write(
        product,
        output_path,
        **kwargs,
    ):
        output_path = Path(
            output_path
        )

        output_path.write_bytes(
            b"%PDF-1.7\nbytes-test"
        )

        return output_path

    monkeypatch.setattr(
        reading_pdf_module,
        "write_reading_product_pdf_async",
        fake_write,
    )

    data = await (
        render_reading_product_pdf_bytes_async(
            sample_product
        )
    )

    assert isinstance(
        data,
        bytes,
    )

    assert data.startswith(
        b"%PDF"
    )


def test_pdf_bytes_sync(
    sample_product,
    monkeypatch,
):
    async def fake_bytes_async(
        product,
        **kwargs,
    ):
        return (
            b"%PDF-1.7\nsync-bytes"
        )

    monkeypatch.setattr(
        reading_pdf_module,
        "render_reading_product_pdf_bytes_async",
        fake_bytes_async,
    )

    data = (
        render_reading_product_pdf_bytes(
            sample_product
        )
    )

    assert isinstance(
        data,
        bytes,
    )

    assert data.startswith(
        b"%PDF"
    )


@pytest.mark.asyncio
async def test_pdf_bytes_async_rejects_empty_data(
    sample_product,
    monkeypatch,
):
    async def fake_write(
        product,
        output_path,
        **kwargs,
    ):
        output_path = Path(
            output_path
        )

        output_path.write_bytes(
            b""
        )

        return output_path

    monkeypatch.setattr(
        reading_pdf_module,
        "write_reading_product_pdf_async",
        fake_write,
    )

    with pytest.raises(
        ReadingPdfGenerationError
    ):
        await (
            render_reading_product_pdf_bytes_async(
                sample_product
            )
        )


@pytest.mark.asyncio
async def test_pdf_bytes_async_rejects_non_pdf_data(
    sample_product,
    monkeypatch,
):
    async def fake_write(
        product,
        output_path,
        **kwargs,
    ):
        output_path = Path(
            output_path
        )

        output_path.write_bytes(
            b"NOT A PDF"
        )

        return output_path

    monkeypatch.setattr(
        reading_pdf_module,
        "write_reading_product_pdf_async",
        fake_write,
    )

    with pytest.raises(
        ReadingPdfGenerationError
    ):
        await (
            render_reading_product_pdf_bytes_async(
                sample_product
            )
        )


@pytest.mark.asyncio
async def test_sync_bytes_rejected_inside_running_loop(
    sample_product,
):
    with pytest.raises(
        ReadingPdfGenerationError
    ):
        render_reading_product_pdf_bytes(
            sample_product
        )


# ============================================================
# Core renderer validation
# ============================================================


@pytest.mark.asyncio
async def test_core_renderer_detects_missing_file(
    monkeypatch,
    tmp_path,
):
    """
    Playwright contextをfake化して、
    page.pdf()が何も作らないケースを確認。
    """

    class FakePage:
        def set_default_timeout(
            self,
            value,
        ):
            return None

        async def set_content(
            self,
            *args,
            **kwargs,
        ):
            return None

        async def evaluate(
            self,
            *args,
            **kwargs,
        ):
            return None

        async def emulate_media(
            self,
            *args,
            **kwargs,
        ):
            return None

        async def pdf(
            self,
            *args,
            **kwargs,
        ):
            return None

    class FakeBrowser:
        async def new_page(
            self,
        ):
            return FakePage()

        async def close(
            self,
        ):
            return None

    class FakeChromium:
        async def launch(
            self,
            **kwargs,
        ):
            return FakeBrowser()

    class FakePlaywright:
        def __init__(
            self,
        ):
            self.chromium = (
                FakeChromium()
            )

    class FakeContextManager:
        async def __aenter__(
            self,
        ):
            return FakePlaywright()

        async def __aexit__(
            self,
            exc_type,
            exc,
            tb,
        ):
            return False

    def fake_async_playwright():
        return FakeContextManager()

    monkeypatch.setattr(
        reading_pdf_module,
        "_load_playwright",
        lambda: (
            fake_async_playwright
        ),
    )

    with pytest.raises(
        ReadingPdfGenerationError
    ):
        await (
            reading_pdf_module
            ._render_html_to_pdf_async(
                "<!DOCTYPE html>"
                "<html></html>",
                tmp_path
                / "missing.pdf",
                page_format="A4",
                print_background=True,
                prefer_css_page_size=True,
                timeout_ms=1000,
            )
        )


@pytest.mark.asyncio
async def test_core_renderer_detects_empty_file(
    monkeypatch,
    tmp_path,
):
    class FakePage:
        def set_default_timeout(
            self,
            value,
        ):
            return None

        async def set_content(
            self,
            *args,
            **kwargs,
        ):
            return None

        async def evaluate(
            self,
            *args,
            **kwargs,
        ):
            return None

        async def emulate_media(
            self,
            *args,
            **kwargs,
        ):
            return None

        async def pdf(
            self,
            *,
            path,
            **kwargs,
        ):
            Path(
                path
            ).write_bytes(
                b""
            )

    class FakeBrowser:
        async def new_page(
            self,
        ):
            return FakePage()

        async def close(
            self,
        ):
            return None

    class FakeChromium:
        async def launch(
            self,
            **kwargs,
        ):
            return FakeBrowser()

    class FakePlaywright:
        def __init__(
            self,
        ):
            self.chromium = (
                FakeChromium()
            )

    class FakeContextManager:
        async def __aenter__(
            self,
        ):
            return FakePlaywright()

        async def __aexit__(
            self,
            exc_type,
            exc,
            tb,
        ):
            return False

    def fake_async_playwright():
        return FakeContextManager()

    monkeypatch.setattr(
        reading_pdf_module,
        "_load_playwright",
        lambda: (
            fake_async_playwright
        ),
    )

    with pytest.raises(
        ReadingPdfGenerationError
    ):
        await (
            reading_pdf_module
            ._render_html_to_pdf_async(
                "<!DOCTYPE html>"
                "<html></html>",
                tmp_path
                / "empty.pdf",
                page_format="A4",
                print_background=True,
                prefer_css_page_size=True,
                timeout_ms=1000,
            )
        )


@pytest.mark.asyncio
async def test_core_renderer_success(
    monkeypatch,
    tmp_path,
):
    captured = {}

    class FakePage:
        def set_default_timeout(
            self,
            value,
        ):
            captured[
                "timeout"
            ] = value

        async def set_content(
            self,
            html_document,
            **kwargs,
        ):
            captured[
                "html"
            ] = html_document
            captured[
                "set_content_kwargs"
            ] = kwargs

        async def evaluate(
            self,
            script,
        ):
            captured[
                "font_wait"
            ] = True

        async def emulate_media(
            self,
            **kwargs,
        ):
            captured[
                "media"
            ] = kwargs

        async def pdf(
            self,
            *,
            path,
            **kwargs,
        ):
            captured[
                "pdf_kwargs"
            ] = kwargs

            Path(
                path
            ).write_bytes(
                b"%PDF-1.7\ncore-success"
            )

    class FakeBrowser:
        async def new_page(
            self,
        ):
            return FakePage()

        async def close(
            self,
        ):
            captured[
                "closed"
            ] = True

    class FakeChromium:
        async def launch(
            self,
            **kwargs,
        ):
            captured[
                "launch"
            ] = kwargs

            return FakeBrowser()

    class FakePlaywright:
        def __init__(
            self,
        ):
            self.chromium = (
                FakeChromium()
            )

    class FakeContextManager:
        async def __aenter__(
            self,
        ):
            return FakePlaywright()

        async def __aexit__(
            self,
            exc_type,
            exc,
            tb,
        ):
            return False

    def fake_async_playwright():
        return FakeContextManager()

    monkeypatch.setattr(
        reading_pdf_module,
        "_load_playwright",
        lambda: (
            fake_async_playwright
        ),
    )

    output = (
        tmp_path
        / "success.pdf"
    )

    result = await (
        reading_pdf_module
        ._render_html_to_pdf_async(
            "<!DOCTYPE html>"
            "<html></html>",
            output,
            page_format="A4",
            print_background=True,
            prefer_css_page_size=True,
            timeout_ms=4321,
        )
    )

    assert (
        result
        == output
    )

    assert output.exists()

    assert (
        output.read_bytes()
        .startswith(
            b"%PDF"
        )
    )

    assert (
        captured[
            "launch"
        ][
            "headless"
        ]
        is True
    )

    assert (
        captured[
            "timeout"
        ]
        == 4321
    )

    assert (
        captured[
            "media"
        ][
            "media"
        ]
        == "print"
    )

    assert (
        captured[
            "pdf_kwargs"
        ][
            "format"
        ]
        == "A4"
    )

    assert (
        captured[
            "pdf_kwargs"
        ][
            "print_background"
        ]
        is True
    )

    assert (
        captured[
            "pdf_kwargs"
        ][
            "prefer_css_page_size"
        ]
        is True
    )

    assert (
        captured[
            "closed"
        ]
        is True
    )


@pytest.mark.asyncio
async def test_core_renderer_wraps_browser_launch_error(
    monkeypatch,
    tmp_path,
):
    class FakeChromium:
        async def launch(
            self,
            **kwargs,
        ):
            raise RuntimeError(
                "chromium missing"
            )

    class FakePlaywright:
        def __init__(
            self,
        ):
            self.chromium = (
                FakeChromium()
            )

    class FakeContextManager:
        async def __aenter__(
            self,
        ):
            return FakePlaywright()

        async def __aexit__(
            self,
            exc_type,
            exc,
            tb,
        ):
            return False

    def fake_async_playwright():
        return FakeContextManager()

    monkeypatch.setattr(
        reading_pdf_module,
        "_load_playwright",
        lambda: (
            fake_async_playwright
        ),
    )

    with pytest.raises(
        ReadingPdfDependencyError
    ):
        await (
            reading_pdf_module
            ._render_html_to_pdf_async(
                "<!DOCTYPE html>"
                "<html></html>",
                tmp_path
                / "reading.pdf",
                page_format="A4",
                print_background=True,
                prefer_css_page_size=True,
                timeout_ms=1000,
            )
        )


# ============================================================
# Source immutability
# ============================================================


def test_build_pdf_html_does_not_mutate_product(
    sample_product,
):
    before_subject = dict(
        sample_product.subject
    )

    before_sequence = list(
        sample_product.chart_summary[
            "pillar_sequence"
        ]
    )

    before_summary = (
        sample_product.summary
    )

    build_reading_pdf_html(
        sample_product
    )

    assert (
        sample_product.subject
        == before_subject
    )

    assert (
        sample_product.chart_summary[
            "pillar_sequence"
        ]
        == before_sequence
    )

    assert (
        sample_product.summary
        == before_summary
    )


# ============================================================
# Final gate
# ============================================================


def test_reading_pdf_v1_final_gate(
    sample_product,
    tmp_path,
    monkeypatch,
):
    """
    reading_pdf_v1 最終品質ゲート。

    Chromium実起動はmockしつつ、
    Product -> HTML -> PDF file
    の公開同期APIまで確認する。
    """

    async def fake_render(
        html_document,
        output_path,
        *,
        page_format,
        print_background,
        prefer_css_page_size,
        timeout_ms,
    ):
        assert (
            "<!DOCTYPE html>"
            in html_document
        )

        assert (
            "乙丑"
            in html_document
        )

        assert (
            "癸未"
            in html_document
        )

        assert (
            "丁巳"
            in html_document
        )

        assert (
            "辛亥"
            in html_document
        )

        assert (
            "本質・性格"
            in html_document
        )

        assert (
            "開運アドバイス"
            in html_document
        )

        assert (
            "@media print"
            in html_document
        )

        assert (
            page_format
            == "A4"
        )

        assert (
            print_background
            is True
        )

        assert (
            prefer_css_page_size
            is True
        )

        assert (
            timeout_ms
            == DEFAULT_TIMEOUT_MS
        )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_path.write_bytes(
            b"%PDF-1.7\nfinal-gate"
        )

        return output_path

    monkeypatch.setattr(
        reading_pdf_module,
        "_render_html_to_pdf_async",
        fake_render,
    )

    output = (
        tmp_path
        / "final.pdf"
    )

    result = (
        write_reading_product_pdf(
            sample_product,
            output,
        )
    )

    assert (
        result
        == output
    )

    assert output.exists()

    assert (
        output.stat().st_size
        > 0
    )

    assert (
        output.read_bytes()
        .startswith(
            b"%PDF"
        )
    )

    metadata = (
        get_reading_pdf_metadata()
    )

    assert (
        metadata[
            "version"
        ]
        == "reading_pdf_v1"
    )

    assert (
        metadata[
            "status"
        ]
        == "ready"
    )

    assert (
        metadata[
            "uses_reading_renderer"
        ]
        is True
    )

    assert (
        metadata[
            "recalculates_astrology"
        ]
        is False
    )

    assert (
        metadata[
            "rewrites_ai_reading"
        ]
        is False
    )

    assert (
        metadata[
            "exposes_api_key"
        ]
        is False
    )
