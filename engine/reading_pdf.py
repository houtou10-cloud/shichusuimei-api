"""
engine/reading_pdf.py

四柱推命 AI鑑定 PDF出力レイヤー v1

目的
----
ReadingProduct
    ↓
reading_renderer_v1
    ↓
商品用HTML
    ↓
reading_pdf_v1
    ↓
商品用PDF

設計原則
--------
- 命式を再計算しない
- AI鑑定文を書き換えない
- ReadingProduct を唯一の入力データとする
- HTMLは engine.reading_renderer の出力を利用する
- APIキーや内部生成情報をPDFへ表示しない
- PDF生成処理と占術ロジックを分離する
- Windows / Linux(Render等) の両方を想定する

PDFバックエンド
---------------
Playwright / Chromium を使用する。

理由:
- reading_renderer.py のHTML/CSSをそのまま利用できる
- @page / @media print / break-* を活かせる
- 日本語HTMLのレンダリング品質が比較的安定する
- ブラウザ表示とPDF表示の差を小さくできる

必要パッケージ:
    pip install playwright
    python -m playwright install chromium

Version
-------
reading_pdf_v1
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, Union

from engine.reading_product import ReadingProduct
from engine.reading_renderer import (
    render_reading_product_html,
)


READING_PDF_VERSION = "reading_pdf_v1"

READING_PDF_METHOD = (
    "html_to_pdf_playwright_chromium_v1"
)

READING_PDF_STATUS = "ready"

DEFAULT_PAGE_FORMAT = "A4"

DEFAULT_PRINT_BACKGROUND = True

DEFAULT_PREFER_CSS_PAGE_SIZE = True

DEFAULT_DISPLAY_HEADER_FOOTER = False

DEFAULT_WAIT_UNTIL = "load"

DEFAULT_TIMEOUT_MS = 30_000

DEFAULT_MARGIN = {
    "top": "0mm",
    "right": "0mm",
    "bottom": "0mm",
    "left": "0mm",
}


# ============================================================
# Exceptions
# ============================================================


class ReadingPdfError(Exception):
    """reading_pdf.py の基底例外。"""


class ReadingPdfValidationError(
    ReadingPdfError
):
    """PDF生成入力が不正。"""


class ReadingPdfDependencyError(
    ReadingPdfError
):
    """PDF生成依存関係が利用できない。"""


class ReadingPdfGenerationError(
    ReadingPdfError
):
    """PDF生成に失敗した。"""


# ============================================================
# Validation
# ============================================================


def _require_product(
    product: Any,
) -> ReadingProduct:
    if not isinstance(
        product,
        ReadingProduct,
    ):
        raise TypeError(
            "productはReadingProductで"
            "指定してください。"
        )

    return product


def _require_pdf_path(
    output_path: Union[
        str,
        Path,
    ],
) -> Path:
    path = Path(output_path)

    if (
        path.suffix.lower()
        != ".pdf"
    ):
        raise ValueError(
            "output_pathは.pdfで"
            "指定してください。"
        )

    return path


def _require_positive_int(
    value: Any,
    name: str,
) -> int:
    if isinstance(
        value,
        bool,
    ) or not isinstance(
        value,
        int,
    ):
        raise TypeError(
            f"{name}は整数で"
            "指定してください。"
        )

    if value <= 0:
        raise ValueError(
            f"{name}は1以上で"
            "指定してください。"
        )

    return value


def _normalize_document_title(
    product: ReadingProduct,
    document_title: Optional[str],
) -> str:
    if document_title is not None:
        if not isinstance(
            document_title,
            str,
        ):
            raise TypeError(
                "document_titleは文字列または"
                "Noneで指定してください。"
            )

        title = document_title.strip()

        if title:
            return title

    product_title = getattr(
        product,
        "title",
        "",
    )

    if isinstance(
        product_title,
        str,
    ):
        product_title = (
            product_title.strip()
        )

        if product_title:
            return product_title

    return "四柱推命鑑定書"


# ============================================================
# Dependency
# ============================================================


def _load_playwright():
    """
    Playwrightを遅延importする。

    reading_pdf.py をimportしただけでは
    Playwright必須にしない。
    """

    try:
        from playwright.async_api import (
            async_playwright,
        )
    except ImportError as exc:
        raise ReadingPdfDependencyError(
            "PDF生成にはPlaywrightが"
            "必要です。"
            " `pip install playwright` を実行し、"
            "続けて"
            " `python -m playwright install chromium`"
            " を実行してください。"
        ) from exc

    return async_playwright


# ============================================================
# Security
# ============================================================


def _validate_html_security(
    html_document: str,
) -> None:
    """
    PDF化前HTMLへ秘密情報が
    混入していないか最低限確認する。
    """

    if not isinstance(
        html_document,
        str,
    ):
        raise TypeError(
            "html_documentは文字列で"
            "指定してください。"
        )

    api_key = os.getenv(
        "OPENAI_API_KEY",
        "",
    ).strip()

    if (
        api_key
        and api_key in html_document
    ):
        raise ReadingPdfValidationError(
            "PDF化対象HTMLに"
            "OPENAI_API_KEYが"
            "含まれています。"
        )

    forbidden_markers = (
        '"api_key"',
        "'api_key'",
        '"system_prompt"',
        "'system_prompt'",
        '"user_prompt"',
        "'user_prompt'",
    )

    lower_html = (
        html_document.lower()
    )

    for marker in forbidden_markers:
        if (
            marker.lower()
            in lower_html
        ):
            raise ReadingPdfValidationError(
                "PDF化対象HTMLに"
                "非公開フィールドが"
                "含まれています: "
                f"{marker}"
            )


# ============================================================
# HTML
# ============================================================


def build_reading_pdf_html(
    product: ReadingProduct,
    *,
    document_title: Optional[
        str
    ] = None,
) -> str:
    """
    PDF生成用HTMLを作成する。

    rendererの完全HTMLをそのまま利用し、
    鑑定内容を再構築しない。
    """

    product = _require_product(
        product
    )

    title = (
        _normalize_document_title(
            product,
            document_title,
        )
    )

    html_document = (
        render_reading_product_html(
            product,
            include_css=True,
            document_title=title,
        )
    )

    if not isinstance(
        html_document,
        str,
    ):
        raise ReadingPdfGenerationError(
            "HTML rendererが文字列を"
            "返しませんでした。"
        )

    if (
        "<!DOCTYPE html>"
        not in html_document
    ):
        raise ReadingPdfGenerationError(
            "PDF化対象が完全なHTML文書"
            "ではありません。"
        )

    _validate_html_security(
        html_document
    )

    return html_document


# ============================================================
# PDF core
# ============================================================


async def _render_html_to_pdf_async(
    html_document: str,
    output_path: Path,
    *,
    page_format: str,
    print_background: bool,
    prefer_css_page_size: bool,
    timeout_ms: int,
) -> Path:
    async_playwright = (
        _load_playwright()
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        async with (
            async_playwright()
            as playwright
        ):
            try:
                browser = (
                    await playwright.chromium.launch(
                        headless=True
                    )
                )
            except Exception as exc:
                raise ReadingPdfDependencyError(
                    "Chromiumを起動できません。"
                    " Playwright本体だけでなく"
                    "Chromiumのインストールも"
                    "確認してください。"
                    " `python -m playwright install chromium`"
                ) from exc

            try:
                page = await browser.new_page()

                page.set_default_timeout(
                    timeout_ms
                )

                await page.set_content(
                    html_document,
                    wait_until=(
                        DEFAULT_WAIT_UNTIL
                    ),
                    timeout=timeout_ms,
                )

                # Webフォント等が存在する場合にも
                # 可能な範囲でフォント読み込みを待つ。
                try:
                    await page.evaluate(
                        """async () => {
                            if (
                                document.fonts
                                && document.fonts.ready
                            ) {
                                await document.fonts.ready;
                            }
                        }"""
                    )
                except Exception:
                    # document.fonts未対応などは
                    # PDF生成自体を止めない。
                    pass

                await page.emulate_media(
                    media="print"
                )

                await page.pdf(
                    path=str(
                        output_path
                    ),
                    format=page_format,
                    print_background=(
                        print_background
                    ),
                    prefer_css_page_size=(
                        prefer_css_page_size
                    ),
                    display_header_footer=(
                        DEFAULT_DISPLAY_HEADER_FOOTER
                    ),
                    margin=DEFAULT_MARGIN,
                )

            finally:
                await browser.close()

    except (
        ReadingPdfDependencyError,
        ReadingPdfValidationError,
    ):
        raise

    except Exception as exc:
        raise ReadingPdfGenerationError(
            "HTMLからPDFへの変換に"
            "失敗しました。"
        ) from exc

    if not output_path.exists():
        raise ReadingPdfGenerationError(
            "PDFファイルが"
            "生成されませんでした。"
        )

    if (
        output_path.stat().st_size
        <= 0
    ):
        raise ReadingPdfGenerationError(
            "生成されたPDFが空です。"
        )

    return output_path


def _run_async(
    coroutine: Any,
) -> Any:
    """
    通常の同期Pythonコードから
    async PDF処理を実行する。

    既にevent loopが動作している環境では
    明示的にasync APIの利用を促す。
    """

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(
            coroutine
        )

    # coroutineを生成済みなので、
    # warning回避のためclose可能なら閉じる。
    close = getattr(
        coroutine,
        "close",
        None,
    )

    if callable(close):
        close()

    raise ReadingPdfGenerationError(
        "実行中のasyncio event loop内から"
        "同期PDF APIは使用できません。"
        " `await write_reading_product_pdf_async(...)`"
        " を使用してください。"
    )


# ============================================================
# Public async API
# ============================================================


async def write_reading_product_pdf_async(
    product: ReadingProduct,
    output_path: Union[
        str,
        Path,
    ],
    *,
    document_title: Optional[
        str
    ] = None,
    page_format: str = (
        DEFAULT_PAGE_FORMAT
    ),
    print_background: bool = (
        DEFAULT_PRINT_BACKGROUND
    ),
    prefer_css_page_size: bool = (
        DEFAULT_PREFER_CSS_PAGE_SIZE
    ),
    timeout_ms: int = (
        DEFAULT_TIMEOUT_MS
    ),
) -> Path:
    """
    ReadingProductを商品用PDFへ保存する
    async API。
    """

    product = _require_product(
        product
    )

    path = _require_pdf_path(
        output_path
    )

    timeout_ms = (
        _require_positive_int(
            timeout_ms,
            "timeout_ms",
        )
    )

    if not isinstance(
        page_format,
        str,
    ):
        raise TypeError(
            "page_formatは文字列で"
            "指定してください。"
        )

    page_format = (
        page_format.strip()
    )

    if not page_format:
        raise ValueError(
            "page_formatが空です。"
        )

    if not isinstance(
        print_background,
        bool,
    ):
        raise TypeError(
            "print_backgroundはboolで"
            "指定してください。"
        )

    if not isinstance(
        prefer_css_page_size,
        bool,
    ):
        raise TypeError(
            "prefer_css_page_sizeはboolで"
            "指定してください。"
        )

    html_document = (
        build_reading_pdf_html(
            product,
            document_title=(
                document_title
            ),
        )
    )

    return await (
        _render_html_to_pdf_async(
            html_document,
            path,
            page_format=(
                page_format
            ),
            print_background=(
                print_background
            ),
            prefer_css_page_size=(
                prefer_css_page_size
            ),
            timeout_ms=(
                timeout_ms
            ),
        )
    )


# ============================================================
# Public sync API
# ============================================================


def write_reading_product_pdf(
    product: ReadingProduct,
    output_path: Union[
        str,
        Path,
    ],
    *,
    document_title: Optional[
        str
    ] = None,
    page_format: str = (
        DEFAULT_PAGE_FORMAT
    ),
    print_background: bool = (
        DEFAULT_PRINT_BACKGROUND
    ),
    prefer_css_page_size: bool = (
        DEFAULT_PREFER_CSS_PAGE_SIZE
    ),
    timeout_ms: int = (
        DEFAULT_TIMEOUT_MS
    ),
) -> Path:
    """
    ReadingProductを商品用PDFへ保存する
    同期API。

    CLI / scripts / 通常のFastAPI外処理向け。
    """

    product = _require_product(
        product
    )

    path = _require_pdf_path(
        output_path
    )

    coroutine = (
        write_reading_product_pdf_async(
            product,
            path,
            document_title=(
                document_title
            ),
            page_format=(
                page_format
            ),
            print_background=(
                print_background
            ),
            prefer_css_page_size=(
                prefer_css_page_size
            ),
            timeout_ms=(
                timeout_ms
            ),
        )
    )

    return _run_async(
        coroutine
    )


# ============================================================
# Bytes API
# ============================================================


async def render_reading_product_pdf_bytes_async(
    product: ReadingProduct,
    *,
    document_title: Optional[
        str
    ] = None,
    page_format: str = (
        DEFAULT_PAGE_FORMAT
    ),
    print_background: bool = (
        DEFAULT_PRINT_BACKGROUND
    ),
    prefer_css_page_size: bool = (
        DEFAULT_PREFER_CSS_PAGE_SIZE
    ),
    timeout_ms: int = (
        DEFAULT_TIMEOUT_MS
    ),
) -> bytes:
    """
    ReadingProductをPDF bytesへ変換する。

    APIレスポンスやストレージ保存向け。
    """

    product = _require_product(
        product
    )

    with tempfile.TemporaryDirectory(
        prefix="reading_pdf_"
    ) as temp_dir:
        temp_path = (
            Path(temp_dir)
            / "reading.pdf"
        )

        await (
            write_reading_product_pdf_async(
                product,
                temp_path,
                document_title=(
                    document_title
                ),
                page_format=(
                    page_format
                ),
                print_background=(
                    print_background
                ),
                prefer_css_page_size=(
                    prefer_css_page_size
                ),
                timeout_ms=(
                    timeout_ms
                ),
            )
        )

        data = temp_path.read_bytes()

    if not data:
        raise ReadingPdfGenerationError(
            "生成PDF bytesが空です。"
        )

    if not data.startswith(
        b"%PDF"
    ):
        raise ReadingPdfGenerationError(
            "生成データがPDF形式では"
            "ありません。"
        )

    return data


def render_reading_product_pdf_bytes(
    product: ReadingProduct,
    *,
    document_title: Optional[
        str
    ] = None,
    page_format: str = (
        DEFAULT_PAGE_FORMAT
    ),
    print_background: bool = (
        DEFAULT_PRINT_BACKGROUND
    ),
    prefer_css_page_size: bool = (
        DEFAULT_PREFER_CSS_PAGE_SIZE
    ),
    timeout_ms: int = (
        DEFAULT_TIMEOUT_MS
    ),
) -> bytes:
    """
    ReadingProductをPDF bytesへ変換する
    同期API。
    """

    product = _require_product(
        product
    )

    coroutine = (
        render_reading_product_pdf_bytes_async(
            product,
            document_title=(
                document_title
            ),
            page_format=(
                page_format
            ),
            print_background=(
                print_background
            ),
            prefer_css_page_size=(
                prefer_css_page_size
            ),
            timeout_ms=(
                timeout_ms
            ),
        )
    )

    return _run_async(
        coroutine
    )


# ============================================================
# Metadata
# ============================================================


def get_reading_pdf_metadata(
) -> Dict[str, Any]:
    return {
        "version": (
            READING_PDF_VERSION
        ),
        "method": (
            READING_PDF_METHOD
        ),
        "status": (
            READING_PDF_STATUS
        ),
        "input_type": (
            "ReadingProduct"
        ),
        "intermediate_type": (
            "html_document"
        ),
        "output_types": [
            "pdf_file",
            "pdf_bytes",
        ],
        "backend": (
            "playwright_chromium"
        ),
        "page_format": (
            DEFAULT_PAGE_FORMAT
        ),
        "print_background": (
            DEFAULT_PRINT_BACKGROUND
        ),
        "prefer_css_page_size": (
            DEFAULT_PREFER_CSS_PAGE_SIZE
        ),
        "uses_reading_renderer": True,
        "recalculates_astrology": False,
        "rewrites_ai_reading": False,
        "exposes_generation_metadata": False,
        "exposes_api_key": False,
        "async_supported": True,
    }


__all__ = [
    "READING_PDF_VERSION",
    "READING_PDF_METHOD",
    "READING_PDF_STATUS",
    "DEFAULT_PAGE_FORMAT",
    "DEFAULT_PRINT_BACKGROUND",
    "DEFAULT_PREFER_CSS_PAGE_SIZE",
    "DEFAULT_TIMEOUT_MS",
    "ReadingPdfError",
    "ReadingPdfValidationError",
    "ReadingPdfDependencyError",
    "ReadingPdfGenerationError",
    "build_reading_pdf_html",
    "write_reading_product_pdf",
    "write_reading_product_pdf_async",
    "render_reading_product_pdf_bytes",
    "render_reading_product_pdf_bytes_async",
    "get_reading_pdf_metadata",
]
