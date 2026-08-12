"""
scripts/generate_sample_product_pdf.py

四柱推命AI鑑定の商品PDFを、
実命式 + 実OpenAI API + Chromiumで生成する
最終商品品質確認スクリプト。

処理フロー
----------
出生情報
    ↓
calculate_chart()
    ↓
build_reading_context()
    ↓
generate_reading()
    ↓
build_reading_product()
    ↓
write_reading_product_pdf()
    ↓
販売用PDF

固定サンプル
------------
生年月日: 1985-07-17
出生時刻: 21:50
出生地: 石川県
性別: female

外部照合済み期待値:
    年柱: 乙丑
    月柱: 癸未
    日柱: 丁巳
    時柱: 辛亥
    日主: 丁

評価日時:
    2026-08-10 15:36

期待歳運:
    丙午

必要環境
--------
OPENAI_API_KEY

必要パッケージ
--------------
pip install playwright
python -m playwright install chromium

実行例
------
PowerShell:

    $env:PYTHONPATH="."
    python .\\scripts\\generate_sample_product_pdf.py

モデル指定:

    $env:OPENAI_READING_MODEL="gpt-5"
    python .\\scripts\\generate_sample_product_pdf.py

注意
----
このスクリプトは実際にOpenAI APIを呼ぶため、
API料金が発生する。

Version
-------
generate_sample_product_pdf_v1
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

from engine.chart import calculate_chart
from engine.reading_context import (
    build_reading_context,
)
from engine.reading_generator import (
    OPENAI_API_KEY_ENV,
    OPENAI_READING_MODEL_ENV,
    ReadingGenerationResult,
    generate_reading,
    get_default_model,
    has_openai_api_key,
)
from engine.reading_pdf import (
    READING_PDF_METHOD,
    READING_PDF_VERSION,
    get_reading_pdf_metadata,
    write_reading_product_pdf,
)
from engine.reading_product import (
    ReadingProduct,
    build_reading_product,
)


# ============================================================
# Script metadata
# ============================================================


SCRIPT_VERSION = (
    "generate_sample_product_pdf_v1"
)


# ============================================================
# Fixed sample
# ============================================================


SAMPLE_BIRTH_DATE = "1985-07-17"
SAMPLE_BIRTH_TIME = "21:50"
SAMPLE_BIRTH_PLACE = "石川県"
SAMPLE_GENDER = "female"


TARGET_DATETIME = datetime(
    2026,
    8,
    10,
    15,
    36,
)


EXPECTED_PILLARS = {
    "year": "乙丑",
    "month": "癸未",
    "day": "丁巳",
    "hour": "辛亥",
}

EXPECTED_DAY_MASTER = "丁"

EXPECTED_ANNUAL_GANZHI = "丙午"


# ============================================================
# Generation configuration
# ============================================================


SECTIONS = (
    "core_personality",
    "career",
    "wealth",
    "relationships",
    "health",
    "current_luck",
    "future_flow",
    "advice",
)

OUTPUT_FORMAT = "json"

LANGUAGE = "ja"

TONE = "professional_warm"

MAX_OUTPUT_TOKENS = 8000

REASONING_EFFORT = "minimal"

STORE = False

PRODUCT_TITLE = "四柱推命 AI鑑定書"

DOCUMENT_TITLE = (
    "四柱推命 AI鑑定書｜商品品質サンプル"
)


# ============================================================
# Output paths
# ============================================================


OUTPUT_DIR = (
    Path("output")
    / "product_pdf"
)

PDF_OUTPUT_PATH = (
    OUTPUT_DIR
    / "sample_product_1985-07-17_2150.pdf"
)

PRODUCT_JSON_OUTPUT_PATH = (
    OUTPUT_DIR
    / "sample_product_1985-07-17_2150.json"
)

READING_JSON_OUTPUT_PATH = (
    OUTPUT_DIR
    / "sample_ai_reading_1985-07-17_2150.json"
)


# ============================================================
# Generic validation helpers
# ============================================================


def _require_mapping(
    value: Any,
    name: str,
) -> Mapping[str, Any]:

    if not isinstance(
        value,
        Mapping,
    ):
        raise TypeError(
            f"{name}はdict型である必要があります。"
        )

    return value


def _require_non_empty_string(
    value: Any,
    name: str,
) -> str:

    if not isinstance(
        value,
        str,
    ):
        raise TypeError(
            f"{name}は文字列である必要があります。"
        )

    value = value.strip()

    if not value:
        raise ValueError(
            f"{name}が空です。"
        )

    return value


def _require_sequence(
    value: Any,
    name: str,
) -> Sequence[Any]:

    if not isinstance(
        value,
        (list, tuple),
    ):
        raise TypeError(
            f"{name}は配列である必要があります。"
        )

    return value


# ============================================================
# Environment
# ============================================================


def validate_environment() -> str:
    """
    OpenAI API環境を検証し、
    実際に利用するモデル名を返す。
    """

    if not has_openai_api_key():
        raise RuntimeError(
            f"{OPENAI_API_KEY_ENV} "
            "が設定されていません。"
        )

    model = _require_non_empty_string(
        get_default_model(),
        "OpenAI model",
    )

    return model


# ============================================================
# Request
# ============================================================


def build_sample_request() -> SimpleNamespace:
    """
    calculate_chart()へ渡す固定request。
    """

    return SimpleNamespace(
        birth_date=SAMPLE_BIRTH_DATE,
        birth_time=SAMPLE_BIRTH_TIME,
        birth_place=SAMPLE_BIRTH_PLACE,
        gender=SAMPLE_GENDER,
    )


# ============================================================
# Chart validation
# ============================================================


def validate_chart(
    chart_result: Mapping[str, Any],
) -> None:

    chart_result = _require_mapping(
        chart_result,
        "chart_result",
    )

    chart = _require_mapping(
        chart_result.get("chart"),
        "chart_result.chart",
    )

    for position, expected in (
        EXPECTED_PILLARS.items()
    ):

        pillar_data = _require_mapping(
            chart.get(position),
            f"chart_result.chart.{position}",
        )

        actual = _require_non_empty_string(
            pillar_data.get("pillar"),
            f"{position}.pillar",
        )

        if actual != expected:
            raise RuntimeError(
                f"{position}柱が期待値と不一致です。"
                f" expected={expected},"
                f" actual={actual}"
            )

    day_master = _require_mapping(
        chart_result.get("day_master"),
        "chart_result.day_master",
    )

    actual_day_master = (
        _require_non_empty_string(
            day_master.get("stem"),
            "day_master.stem",
        )
    )

    if (
        actual_day_master
        != EXPECTED_DAY_MASTER
    ):
        raise RuntimeError(
            "日主が期待値と不一致です。"
            f" expected={EXPECTED_DAY_MASTER},"
            f" actual={actual_day_master}"
        )


# ============================================================
# Reading context validation
# ============================================================


def validate_reading_context(
    reading_context: Mapping[
        str,
        Any,
    ],
) -> None:

    reading_context = _require_mapping(
        reading_context,
        "reading_context",
    )

    natal_chart = _require_mapping(
        reading_context.get(
            "natal_chart"
        ),
        "reading_context.natal_chart",
    )

    pillars = _require_mapping(
        natal_chart.get(
            "pillars"
        ),
        (
            "reading_context."
            "natal_chart.pillars"
        ),
    )

    for position, expected in (
        EXPECTED_PILLARS.items()
    ):

        pillar = _require_mapping(
            pillars.get(position),
            (
                "reading_context."
                f"pillars.{position}"
            ),
        )

        actual = _require_non_empty_string(
            pillar.get("pillar"),
            (
                "reading_context."
                f"{position}.pillar"
            ),
        )

        if actual != expected:
            raise RuntimeError(
                "reading_contextで"
                f"{position}柱が変化しています。"
                f" expected={expected},"
                f" actual={actual}"
            )

    day_master = _require_mapping(
        reading_context.get(
            "day_master"
        ),
        "reading_context.day_master",
    )

    actual_day_master = (
        _require_non_empty_string(
            day_master.get("stem"),
            (
                "reading_context."
                "day_master.stem"
            ),
        )
    )

    if (
        actual_day_master
        != EXPECTED_DAY_MASTER
    ):
        raise RuntimeError(
            "reading_contextで"
            "日主が変化しています。"
        )

    luck = _require_mapping(
        reading_context.get("luck"),
        "reading_context.luck",
    )

    annual_luck = _require_mapping(
        luck.get("annual_luck"),
        (
            "reading_context."
            "luck.annual_luck"
        ),
    )

    annual_ganzhi = (
        _require_non_empty_string(
            annual_luck.get("ganzhi"),
            "annual_luck.ganzhi",
        )
    )

    if (
        annual_ganzhi
        != EXPECTED_ANNUAL_GANZHI
    ):
        raise RuntimeError(
            "歳運が期待値と不一致です。"
            f" expected="
            f"{EXPECTED_ANNUAL_GANZHI},"
            f" actual={annual_ganzhi}"
        )

    status = _require_non_empty_string(
        reading_context.get("status"),
        "reading_context.status",
    )

    if (
        status
        != "ready_for_ai_reading"
    ):
        raise RuntimeError(
            "reading_contextが"
            "AI鑑定可能状態ではありません。"
            f" status={status}"
        )


# ============================================================
# AI generation validation
# ============================================================


def validate_generation_result(
    result: ReadingGenerationResult,
) -> None:

    if not isinstance(
        result,
        ReadingGenerationResult,
    ):
        raise TypeError(
            "resultはReadingGenerationResult"
            "である必要があります。"
        )

    if (
        result.output_format
        != "json"
    ):
        raise RuntimeError(
            "商品PDF生成には"
            "JSON形式の鑑定結果が必要です。"
        )

    if (
        result.status
        != "completed"
    ):
        raise RuntimeError(
            "AI鑑定生成がcompletedではありません。"
            f" status={result.status}"
        )

    if (
        result.response_status
        not in (
            None,
            "completed",
        )
    ):
        raise RuntimeError(
            "OpenAI responseが"
            "completedではありません。"
            f" response_status="
            f"{result.response_status}"
        )

    if not isinstance(
        result.parsed,
        Mapping,
    ):
        raise RuntimeError(
            "AI鑑定JSONが"
            "parseされていません。"
        )

    parsed = result.parsed

    _require_non_empty_string(
        parsed.get("summary"),
        "reading.summary",
    )

    _require_non_empty_string(
        parsed.get("disclaimer"),
        "reading.disclaimer",
    )

    parsed_sections = (
        _require_mapping(
            parsed.get("sections"),
            "reading.sections",
        )
    )

    if (
        set(parsed_sections.keys())
        != set(SECTIONS)
    ):
        raise RuntimeError(
            "AI鑑定のセクション構成が"
            "期待値と一致しません。"
        )

    for section_key in SECTIONS:

        section = _require_mapping(
            parsed_sections.get(
                section_key
            ),
            (
                "reading.sections."
                f"{section_key}"
            ),
        )

        for key in (
            "title",
            "summary",
            "detail",
        ):
            _require_non_empty_string(
                section.get(key),
                (
                    f"{section_key}."
                    f"{key}"
                ),
            )

        evidence = _require_sequence(
            section.get("evidence"),
            (
                f"{section_key}."
                "evidence"
            ),
        )

        advice = _require_sequence(
            section.get("advice"),
            (
                f"{section_key}."
                "advice"
            ),
        )

        if not evidence:
            raise RuntimeError(
                f"{section_key}.evidence"
                "が空です。"
            )

        if not advice:
            raise RuntimeError(
                f"{section_key}.advice"
                "が空です。"
            )


# ============================================================
# Product validation
# ============================================================


def validate_product(
    product: ReadingProduct,
) -> None:

    if not isinstance(
        product,
        ReadingProduct,
    ):
        raise TypeError(
            "productはReadingProduct"
            "である必要があります。"
        )

    if (
        product.status
        != "ready"
    ):
        raise RuntimeError(
            "ReadingProductが"
            "readyではありません。"
            f" status={product.status}"
        )

    subject = _require_mapping(
        product.subject,
        "product.subject",
    )

    if (
        subject.get("birth_date")
        != SAMPLE_BIRTH_DATE
    ):
        raise RuntimeError(
            "商品データの生年月日が"
            "変化しています。"
        )

    if (
        subject.get("birth_time")
        != SAMPLE_BIRTH_TIME
    ):
        raise RuntimeError(
            "商品データの出生時刻が"
            "変化しています。"
        )

    if (
        subject.get("birth_place")
        != SAMPLE_BIRTH_PLACE
    ):
        raise RuntimeError(
            "商品データの出生地が"
            "変化しています。"
        )

    chart_summary = (
        _require_mapping(
            product.chart_summary,
            "product.chart_summary",
        )
    )

    sequence = (
        chart_summary.get(
            "pillar_sequence"
        )
    )

    expected_sequence = list(
        EXPECTED_PILLARS.values()
    )

    if (
        sequence
        != expected_sequence
    ):
        raise RuntimeError(
            "商品データの四柱が"
            "期待値と一致しません。"
            f" expected={expected_sequence},"
            f" actual={sequence}"
        )

    day_master = _require_mapping(
        chart_summary.get(
            "day_master"
        ),
        (
            "product.chart_summary."
            "day_master"
        ),
    )

    if (
        day_master.get("stem")
        != EXPECTED_DAY_MASTER
    ):
        raise RuntimeError(
            "商品データの日主が"
            "変化しています。"
        )

    annual_luck = _require_mapping(
        chart_summary.get(
            "annual_luck"
        ),
        (
            "product.chart_summary."
            "annual_luck"
        ),
    )

    if (
        annual_luck.get("ganzhi")
        != EXPECTED_ANNUAL_GANZHI
    ):
        raise RuntimeError(
            "商品データの歳運が"
            "変化しています。"
        )

    if (
        len(product.sections)
        != len(SECTIONS)
    ):
        raise RuntimeError(
            "商品データが"
            "8セクションではありません。"
        )

    actual_section_keys = tuple(
        section.get("key")
        for section
        in product.sections
    )

    if (
        actual_section_keys
        != SECTIONS
    ):
        raise RuntimeError(
            "商品セクション順序が"
            "期待値と一致しません。"
            f" actual={actual_section_keys}"
        )

    _require_non_empty_string(
        product.summary,
        "product.summary",
    )

    _require_non_empty_string(
        product.disclaimer,
        "product.disclaimer",
    )


# ============================================================
# Security
# ============================================================


def validate_product_security(
    product: ReadingProduct,
) -> None:

    api_key = os.getenv(
        OPENAI_API_KEY_ENV,
        "",
    ).strip()

    product_json = json.dumps(
        product.to_dict(),
        ensure_ascii=False,
        default=str,
    )

    if (
        api_key
        and api_key in product_json
    ):
        raise RuntimeError(
            "商品データに"
            "OPENAI_API_KEYが"
            "露出しています。"
        )

    forbidden_keys = (
        '"api_key"',
        '"system_prompt"',
        '"user_prompt"',
    )

    for marker in forbidden_keys:
        if (
            marker
            in product_json
        ):
            raise RuntimeError(
                "商品データに"
                "非公開フィールドが"
                "含まれています: "
                f"{marker}"
            )


# ============================================================
# JSON save
# ============================================================


def save_json(
    path: Path,
    data: Any,
) -> Path:

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    return path


# ============================================================
# PDF validation
# ============================================================


def validate_pdf_file(
    pdf_path: Path,
) -> None:
    """
    最終生成PDFの最低限の
   ファイル品質を確認する。
    """

    if not pdf_path.exists():
        raise RuntimeError(
            "PDFファイルが"
            "生成されませんでした。"
        )

    if not pdf_path.is_file():
        raise RuntimeError(
            "PDF出力先が"
            "ファイルではありません。"
        )

    file_size = (
        pdf_path.stat().st_size
    )

    if file_size <= 0:
        raise RuntimeError(
            "生成されたPDFが空です。"
        )

    with pdf_path.open(
        "rb"
    ) as file:
        header = file.read(5)

    if header != b"%PDF-":
        raise RuntimeError(
            "生成ファイルが"
            "PDF形式ではありません。"
        )

    api_key = os.getenv(
        OPENAI_API_KEY_ENV,
        "",
    ).strip()

    if api_key:
        raw_data = (
            pdf_path.read_bytes()
        )

        api_key_bytes = (
            api_key.encode(
                "utf-8"
            )
        )

        if (
            api_key_bytes
            in raw_data
        ):
            raise RuntimeError(
                "生成PDFに"
                "OPENAI_API_KEYが"
                "露出しています。"
            )


# ============================================================
# Diagnostics
# ============================================================


def print_configuration(
    model: str,
) -> None:

    print(
        "# 四柱推命AI鑑定 "
        "商品PDFサンプル生成"
    )

    print()

    print(
        f"script_version: "
        f"{SCRIPT_VERSION}"
    )

    print(
        f"pdf_version: "
        f"{READING_PDF_VERSION}"
    )

    print(
        f"pdf_method: "
        f"{READING_PDF_METHOD}"
    )

    print(
        f"model: {model}"
    )

    print(
        f"{OPENAI_READING_MODEL_ENV}: "
        f"{os.getenv(OPENAI_READING_MODEL_ENV)!r}"
    )

    print(
        f"birth: "
        f"{SAMPLE_BIRTH_DATE} "
        f"{SAMPLE_BIRTH_TIME}"
    )

    print(
        f"birth_place: "
        f"{SAMPLE_BIRTH_PLACE}"
    )

    print(
        f"target_datetime: "
        f"{TARGET_DATETIME.isoformat()}"
    )

    print(
        f"sections: "
        f"{len(SECTIONS)}"
    )

    print(
        f"max_output_tokens: "
        f"{MAX_OUTPUT_TOKENS}"
    )

    print(
        f"reasoning_effort: "
        f"{REASONING_EFFORT}"
    )

    print(
        f"store: {STORE}"
    )

    print()


# ============================================================
# Main
# ============================================================


def main() -> int:

    try:

        # ----------------------------------------------------
        # 0. Environment
        # ----------------------------------------------------

        model = validate_environment()

        print_configuration(
            model
        )

        # ----------------------------------------------------
        # 1. Chart
        # ----------------------------------------------------

        print(
            "1. 命式計算"
        )

        request = (
            build_sample_request()
        )

        chart_result = (
            calculate_chart(
                request,
                target_datetime=(
                    TARGET_DATETIME
                ),
            )
        )

        validate_chart(
            chart_result
        )

        chart = (
            chart_result[
                "chart"
            ]
        )

        print(
            "   OK: "
            f"{chart['year']['pillar']} / "
            f"{chart['month']['pillar']} / "
            f"{chart['day']['pillar']} / "
            f"{chart['hour']['pillar']}"
        )

        print()

        # ----------------------------------------------------
        # 2. Reading context
        # ----------------------------------------------------

        print(
            "2. reading_context生成"
        )

        reading_context = (
            build_reading_context(
                chart_result
            )
        )

        validate_reading_context(
            reading_context
        )

        print(
            "   OK"
        )

        print()

        # ----------------------------------------------------
        # 3. OpenAI reading
        # ----------------------------------------------------

        print(
            "3. OpenAIで"
            "8セクション鑑定生成"
        )

        generation_result = (
            generate_reading(
                reading_context,
                model=model,
                sections=SECTIONS,
                language=LANGUAGE,
                tone=TONE,
                output_format=(
                    OUTPUT_FORMAT
                ),
                max_output_tokens=(
                    MAX_OUTPUT_TOKENS
                ),
                reasoning_effort=(
                    REASONING_EFFORT
                ),
                store=STORE,
            )
        )

        validate_generation_result(
            generation_result
        )

        print(
            "   OK"
        )

        print(
            "   response_status: "
            f"{generation_result.response_status}"
        )

        print(
            "   response_id: "
            f"{generation_result.response_id}"
        )

        print()

        # ----------------------------------------------------
        # 4. ReadingProduct
        # ----------------------------------------------------

        print(
            "4. ReadingProduct生成"
        )

        product = (
            build_reading_product(
                reading_context,
                generation_result,
                title=PRODUCT_TITLE,
                sections=SECTIONS,
            )
        )

        validate_product(
            product
        )

        validate_product_security(
            product
        )

        print(
            "   OK"
        )

        print()

        # ----------------------------------------------------
        # 5. JSON save
        # ----------------------------------------------------

        print(
            "5. 商品JSON保存"
        )

        save_json(
            PRODUCT_JSON_OUTPUT_PATH,
            product.to_dict(),
        )

        if (
            generation_result.parsed
            is None
        ):
            raise RuntimeError(
                "generation_result.parsed"
                "がありません。"
            )

        save_json(
            READING_JSON_OUTPUT_PATH,
            generation_result.parsed,
        )

        print(
            "   OK"
        )

        print()

        # ----------------------------------------------------
        # 6. PDF
        # ----------------------------------------------------

        print(
            "6. 商品PDF生成"
        )

        pdf_path = (
            write_reading_product_pdf(
                product,
                PDF_OUTPUT_PATH,
                document_title=(
                    DOCUMENT_TITLE
                ),
            )
        )

        validate_pdf_file(
            pdf_path
        )

        print(
            "   OK"
        )

        print(
            "   size: "
            f"{pdf_path.stat().st_size:,} bytes"
        )

        print()

        # ----------------------------------------------------
        # 7. PDF metadata
        # ----------------------------------------------------

        print(
            "7. PDF metadata確認"
        )

        pdf_metadata = (
            get_reading_pdf_metadata()
        )

        if (
            pdf_metadata.get(
                "version"
            )
            != READING_PDF_VERSION
        ):
            raise RuntimeError(
                "PDF versionが"
                "期待値と一致しません。"
            )

        if (
            pdf_metadata.get(
                "recalculates_astrology"
            )
            is not False
        ):
            raise RuntimeError(
                "PDF層が占術再計算を"
                "行う設定になっています。"
            )

        if (
            pdf_metadata.get(
                "rewrites_ai_reading"
            )
            is not False
        ):
            raise RuntimeError(
                "PDF層がAI鑑定文を"
                "書き換える設定になっています。"
            )

        if (
            pdf_metadata.get(
                "exposes_api_key"
            )
            is not False
        ):
            raise RuntimeError(
                "PDF層のAPIキー"
                "非露出保証が不正です。"
            )

        print(
            "   OK"
        )

        print()

        # ----------------------------------------------------
        # Complete
        # ----------------------------------------------------

        print(
            "生成完了"
        )

        print(
            "PDF: "
            f"{pdf_path.resolve()}"
        )

        print(
            "Product JSON: "
            f"{PRODUCT_JSON_OUTPUT_PATH.resolve()}"
        )

        print(
            "AI Reading JSON: "
            f"{READING_JSON_OUTPUT_PATH.resolve()}"
        )

        print(
            "response_status: "
            f"{generation_result.response_status}"
        )

        print(
            "response_id: "
            f"{generation_result.response_id}"
        )

        print(
            "usage: "
            f"{generation_result.usage}"
        )

        print(
            "pdf_version: "
            f"{READING_PDF_VERSION}"
        )

        print(
            "pdf_method: "
            f"{READING_PDF_METHOD}"
        )

        print(
            "pdf_size: "
            f"{pdf_path.stat().st_size:,} bytes"
        )

        return 0

    except Exception as exc:

        print(
            "",
            file=sys.stderr,
        )

        print(
            "生成失敗",
            file=sys.stderr,
        )

        print(
            f"{type(exc).__name__}: "
            f"{exc}",
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
