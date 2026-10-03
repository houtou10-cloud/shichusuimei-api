"""PASS-only PDF v2 output APIs for ReadingProductV2."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from engine.reading_product_v2 import ReadingProductV2


READING_PDF_V2_TEMPLATE_VERSION = "reading_pdf_template_v2"
READING_PDF_V2_VERSION = "reading_pdf_v2"
READING_PDF_V2_METHOD = "html_to_pdf_playwright_chromium_v2"
READING_PDF_V2_STATUS = "ready"


class ReadingPdfV2Error(Exception):
    pass


class ReadingPdfV2ValidationError(ReadingPdfV2Error):
    pass


class ReadingPdfV2DependencyError(ReadingPdfV2Error):
    pass


class ReadingPdfV2GenerationError(ReadingPdfV2Error):
    pass


def _validate_options(
    product: Any,
    *,
    document_title: Any,
    page_format: Any,
    print_background: Any,
    prefer_css_page_size: Any,
    timeout_ms: Any,
) -> str:
    if not isinstance(product, ReadingProductV2):
        raise ReadingPdfV2ValidationError("product must be ReadingProductV2")
    try:
        ReadingProductV2(product.to_dict())
    except Exception:
        raise ReadingPdfV2ValidationError("product invariant is invalid") from None
    if document_title is None:
        title = "八雲式四柱推命 鑑定書"
    elif type(document_title) is str and document_title.strip():
        title = document_title
    else:
        raise ReadingPdfV2ValidationError("document_title is invalid")
    if page_format != "A4":
        raise ReadingPdfV2ValidationError("page_format must be A4")
    if type(print_background) is not bool or type(prefer_css_page_size) is not bool:
        raise ReadingPdfV2ValidationError("PDF boolean options are invalid")
    if type(timeout_ms) is not int or timeout_ms <= 0:
        raise ReadingPdfV2ValidationError("timeout_ms must be a positive integer")
    return title


def _load_playwright():
    try:
        from playwright.async_api import async_playwright
    except Exception:
        return None
    return async_playwright


async def render_reading_product_v2_pdf_bytes_async(
    product: ReadingProductV2,
    *,
    document_title: str | None = None,
    page_format: str = "A4",
    print_background: bool = True,
    prefer_css_page_size: bool = True,
    timeout_ms: int = 30000,
) -> bytes:
    title = _validate_options(
        product, document_title=document_title, page_format=page_format,
        print_background=print_background, prefer_css_page_size=prefer_css_page_size,
        timeout_ms=timeout_ms,
    )
    from engine.reading_renderer_v2 import render_reading_product_v2_html

    html = render_reading_product_v2_html(product, document_title=title, include_css=True)
    loader = _load_playwright()
    if loader is None:
        raise ReadingPdfV2DependencyError("Playwright is unavailable")
    manager = None
    browser = None
    try:
        manager = loader()
        playwright = await manager.__aenter__()
    except Exception:
        manager = None
        raise ReadingPdfV2DependencyError("Playwright is unavailable") from None
    try:
        try:
            browser = await playwright.chromium.launch()
        except Exception:
            raise ReadingPdfV2DependencyError("Chromium is unavailable") from None
        page = await browser.new_page()
        await page.set_content(html, wait_until="networkidle", timeout=timeout_ms)
        data = await page.pdf(
            format=page_format,
            print_background=print_background,
            prefer_css_page_size=prefer_css_page_size,
        )
    except ReadingPdfV2Error:
        raise
    except Exception:
        raise ReadingPdfV2GenerationError("PDF generation failed") from None
    finally:
        if browser is not None:
            try:
                await browser.close()
            except Exception:
                pass
        if manager is not None:
            try:
                await manager.__aexit__(None, None, None)
            except Exception:
                pass
    if type(data) is not bytes or not data or not data.startswith(b"%PDF"):
        raise ReadingPdfV2GenerationError("PDF backend returned invalid data")
    return bytes(data)


def _run_sync(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    coro.close()
    raise ReadingPdfV2GenerationError("use the async PDF API inside a running event loop")


def render_reading_product_v2_pdf_bytes(
    product: ReadingProductV2,
    *,
    document_title: str | None = None,
    page_format: str = "A4",
    print_background: bool = True,
    prefer_css_page_size: bool = True,
    timeout_ms: int = 30000,
) -> bytes:
    return _run_sync(render_reading_product_v2_pdf_bytes_async(
        product, document_title=document_title, page_format=page_format,
        print_background=print_background, prefer_css_page_size=prefer_css_page_size,
        timeout_ms=timeout_ms,
    ))


def _pdf_path(value: str | Path) -> Path:
    if not isinstance(value, (str, Path)):
        raise ReadingPdfV2ValidationError("output_path is invalid")
    path = Path(value)
    if path.suffix.lower() != ".pdf":
        raise ReadingPdfV2ValidationError("output_path must use .pdf")
    return path


async def write_reading_product_v2_pdf_async(
    product: ReadingProductV2,
    output_path: str | Path,
    *,
    document_title: str | None = None,
    page_format: str = "A4",
    print_background: bool = True,
    prefer_css_page_size: bool = True,
    timeout_ms: int = 30000,
) -> Path:
    path = _pdf_path(output_path)
    data = await render_reading_product_v2_pdf_bytes_async(
        product, document_title=document_title, page_format=page_format,
        print_background=print_background, prefer_css_page_size=prefer_css_page_size,
        timeout_ms=timeout_ms,
    )
    try:
        if path.parent.exists() and not path.parent.is_dir():
            raise OSError
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        if not path.is_file() or path.stat().st_size <= 0 or not path.read_bytes().startswith(b"%PDF"):
            raise OSError
    except Exception:
        raise ReadingPdfV2GenerationError("PDF file write failed") from None
    return path


def write_reading_product_v2_pdf(
    product: ReadingProductV2,
    output_path: str | Path,
    *,
    document_title: str | None = None,
    page_format: str = "A4",
    print_background: bool = True,
    prefer_css_page_size: bool = True,
    timeout_ms: int = 30000,
) -> Path:
    return _run_sync(write_reading_product_v2_pdf_async(
        product, output_path, document_title=document_title, page_format=page_format,
        print_background=print_background, prefer_css_page_size=prefer_css_page_size,
        timeout_ms=timeout_ms,
    ))


__all__ = [
    "READING_PDF_V2_TEMPLATE_VERSION", "READING_PDF_V2_VERSION",
    "READING_PDF_V2_METHOD", "READING_PDF_V2_STATUS", "ReadingPdfV2Error",
    "ReadingPdfV2ValidationError", "ReadingPdfV2DependencyError",
    "ReadingPdfV2GenerationError", "write_reading_product_v2_pdf_async",
    "write_reading_product_v2_pdf", "render_reading_product_v2_pdf_bytes_async",
    "render_reading_product_v2_pdf_bytes",
]
