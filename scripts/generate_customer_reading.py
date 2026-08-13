"""
scripts/generate_customer_reading.py

四柱推命鑑定書 v1.0.0
顧客1名分の本番鑑定書を対話形式で生成するCLIスクリプト。

処理フロー
----------
顧客情報入力
    ↓
入力値検証
    ↓
calculate_chart()
    ↓
build_reading_context()
    ↓
generate_reading()
    ↓
build_reading_product()
    ↓
商品JSON保存
    ↓
AI鑑定JSON保存
    ↓
四柱推命鑑定書PDF生成
    ↓
顧客別フォルダ保存

出力例
------
output/customers/20260813_001/
    intake.json
    chart.json
    reading_context.json
    ai_reading.json
    product.json
    四柱推命鑑定書.pdf
    summary.json

重要
----
このスクリプトは実際にOpenAI APIを呼びます。

必要環境変数:
    OPENAI_API_KEY

必要環境:
    Playwright
    Chromium

初回のみ:
    pip install playwright
    python -m playwright install chromium

PowerShell実行例:
    $env:PYTHONPATH="."
    python .\\scripts\\generate_customer_reading.py

Version
-------
generate_customer_reading_v1
"""

from __future__ import annotations

import json
import os
import re
import sys

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping


from engine.chart import (
    calculate_chart,
)

from engine.reading_context import (
    build_reading_context,
)

from engine.reading_generator import (
    OPENAI_API_KEY_ENV,
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
# Version
# ============================================================


SCRIPT_VERSION = (
    "generate_customer_reading_v1"
)


# ============================================================
# Product configuration
# ============================================================


PRODUCT_TITLE = (
    "四柱推命鑑定書"
)


DOCUMENT_TITLE = (
    "四柱推命鑑定書"
)


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


LANGUAGE = "ja"

TONE = "professional_warm"

OUTPUT_FORMAT = "json"

MAX_OUTPUT_TOKENS = 8000

REASONING_EFFORT = "minimal"

STORE = False


# ============================================================
# Output configuration
# ============================================================


CUSTOMER_OUTPUT_ROOT = (
    Path("output")
    / "customers"
)


# ============================================================
# Gender
# ============================================================


GENDER_ALIASES = {
    "male": "male",
    "m": "male",
    "男": "male",
    "男性": "male",

    "female": "female",
    "f": "female",
    "女": "female",
    "女性": "female",
}


GENDER_LABELS = {
    "male": "男性",
    "female": "女性",
}


# ============================================================
# Customer input model
# ============================================================


@dataclass(
    frozen=True
)
class CustomerInput:

    customer_name: str

    birth_date: str

    birth_time: str

    birth_place: str

    gender: str

    concern: str

    desired_future: str

    @property
    def gender_label(
        self,
    ) -> str:

        return (
            GENDER_LABELS[
                self.gender
            ]
        )


# ============================================================
# Generic helpers
# ============================================================


def require_mapping(
    value: Any,
    name: str,
) -> Mapping[str, Any]:

    if not isinstance(
        value,
        Mapping,
    ):
        raise TypeError(
            f"{name}はmappingで"
            "ある必要があります。"
        )

    return value


def require_non_empty_string(
    value: Any,
    name: str,
) -> str:

    if not isinstance(
        value,
        str,
    ):
        raise TypeError(
            f"{name}は文字列で"
            "ある必要があります。"
        )

    value = value.strip()

    if not value:

        raise ValueError(
            f"{name}が空です。"
        )

    return value


def save_json(
    path: Path,
    value: Any,
) -> None:

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )


# ============================================================
# Input
# ============================================================


def prompt_required(
    label: str,
) -> str:

    while True:

        value = input(
            f"{label}: "
        ).strip()

        if value:
            return value

        print(
            "空欄にはできません。"
        )


def prompt_optional(
    label: str,
) -> str:

    return input(
        f"{label}: "
    ).strip()


# ============================================================
# Input validation
# ============================================================


def normalize_birth_date(
    value: str,
) -> str:

    value = (
        require_non_empty_string(
            value,
            "生年月日",
        )
    )

    candidates = (
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y.%m.%d",
    )

    parsed = None

    for pattern in candidates:

        try:

            parsed = (
                datetime.strptime(
                    value,
                    pattern,
                )
            )

            break

        except ValueError:
            continue

    if parsed is None:

        raise ValueError(
            "生年月日は "
            "YYYY-MM-DD 形式で"
            "入力してください。"
        )

    if (
        parsed.date()
        > datetime.now().date()
    ):

        raise ValueError(
            "未来の日付は"
            "生年月日に指定できません。"
        )

    return (
        parsed.strftime(
            "%Y-%m-%d"
        )
    )


def normalize_birth_time(
    value: str,
) -> str:

    value = (
        require_non_empty_string(
            value,
            "出生時刻",
        )
    )

    candidates = (
        "%H:%M",
        "%H:%M:%S",
    )

    parsed = None

    for pattern in candidates:

        try:

            parsed = (
                datetime.strptime(
                    value,
                    pattern,
                )
            )

            break

        except ValueError:
            continue

    if parsed is None:

        raise ValueError(
            "出生時刻は "
            "HH:MM 形式で"
            "入力してください。"
        )

    return (
        parsed.strftime(
            "%H:%M"
        )
    )


def normalize_gender(
    value: str,
) -> str:

    value = (
        require_non_empty_string(
            value,
            "性別",
        )
    )

    normalized = (
        GENDER_ALIASES.get(
            value.lower()
        )
    )

    if normalized is None:

        normalized = (
            GENDER_ALIASES.get(
                value
            )
        )

    if normalized is None:

        raise ValueError(
            "性別は "
            "男性 / 女性 "
            "のいずれかを"
            "入力してください。"
        )

    return normalized


def sanitize_customer_name(
    value: str,
) -> str:

    value = value.strip()

    # Windowsで使えない文字を除去
    value = re.sub(
        r'[\\/:*?"<>|]',
        "_",
        value,
    )

    # 改行や制御文字を除去
    value = re.sub(
        r"[\r\n\t]+",
        " ",
        value,
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    ).strip()

    if not value:

        return "customer"

    return value[:40]


# ============================================================
# Interactive customer intake
# ============================================================


def collect_customer_input(
) -> CustomerInput:

    print()
    print(
        "=" * 72
    )

    print(
        "四柱推命鑑定書"
    )

    print(
        "顧客情報入力"
    )

    print(
        "=" * 72
    )

    print()

    customer_name = (
        prompt_required(
            "お名前"
        )
    )

    birth_date = (
        normalize_birth_date(
            prompt_required(
                "生年月日 YYYY-MM-DD"
            )
        )
    )

    birth_time = (
        normalize_birth_time(
            prompt_required(
                "出生時刻 HH:MM"
            )
        )
    )

    birth_place = (
        prompt_required(
            "出生地"
        )
    )

    gender = (
        normalize_gender(
            prompt_required(
                "性別 男性/女性"
            )
        )
    )

    concern = (
        prompt_optional(
            "現在のお悩み"
        )
    )

    desired_future = (
        prompt_optional(
            "理想の未来"
        )
    )

    return CustomerInput(
        customer_name=(
            customer_name
        ),
        birth_date=(
            birth_date
        ),
        birth_time=(
            birth_time
        ),
        birth_place=(
            birth_place
        ),
        gender=gender,
        concern=concern,
        desired_future=(
            desired_future
        ),
    )


# ============================================================
# Confirmation
# ============================================================


def confirm_customer_input(
    customer: CustomerInput,
) -> bool:

    print()
    print(
        "=" * 72
    )

    print(
        "入力内容確認"
    )

    print(
        "=" * 72
    )

    print(
        f"お名前      : "
        f"{customer.customer_name}"
    )

    print(
        f"生年月日    : "
        f"{customer.birth_date}"
    )

    print(
        f"出生時刻    : "
        f"{customer.birth_time}"
    )

    print(
        f"出生地      : "
        f"{customer.birth_place}"
    )

    print(
        f"性別        : "
        f"{customer.gender_label}"
    )

    print(
        f"現在のお悩み: "
        f"{customer.concern or '未入力'}"
    )

    print(
        f"理想の未来  : "
        f"{customer.desired_future or '未入力'}"
    )

    print()

    while True:

        answer = input(
            "この内容で鑑定しますか？ "
            "[y/n]: "
        ).strip().lower()

        if answer in (
            "y",
            "yes",
        ):
            return True

        if answer in (
            "n",
            "no",
        ):
            return False

        print(
            "y または n を"
            "入力してください。"
        )


# ============================================================
# Environment validation
# ============================================================


def validate_environment(
) -> str:

    if not has_openai_api_key():

        raise RuntimeError(
            f"{OPENAI_API_KEY_ENV} "
            "が設定されていません。"
        )

    model = (
        get_default_model()
    )

    model = (
        require_non_empty_string(
            model,
            "OpenAI model",
        )
    )

    return model


# ============================================================
# Customer ID / directory
# ============================================================


def build_customer_id(
) -> str:

    now = datetime.now()

    prefix = (
        now.strftime(
            "%Y%m%d_%H%M%S"
        )
    )

    candidate = prefix

    counter = 1

    while (
        CUSTOMER_OUTPUT_ROOT
        / candidate
    ).exists():

        candidate = (
            f"{prefix}_{counter:02d}"
        )

        counter += 1

    return candidate


def create_customer_directory(
    customer_id: str,
) -> Path:

    path = (
        CUSTOMER_OUTPUT_ROOT
        / customer_id
    )

    path.mkdir(
        parents=True,
        exist_ok=False,
    )

    return path


# ============================================================
# Intake JSON
# ============================================================


def build_intake_data(
    customer_id: str,
    customer: CustomerInput,
) -> dict[str, Any]:

    return {
        "customer_id": (
            customer_id
        ),

        "customer_name": (
            customer.customer_name
        ),

        "birth_date": (
            customer.birth_date
        ),

        "birth_time": (
            customer.birth_time
        ),

        "birth_place": (
            customer.birth_place
        ),

        "gender": (
            customer.gender
        ),

        "gender_label": (
            customer.gender_label
        ),

        "concern": (
            customer.concern
        ),

        "desired_future": (
            customer.desired_future
        ),

        "created_at": (
            datetime.now()
            .isoformat(
                timespec="seconds"
            )
        ),

        # v1では相談情報は保存のみ。
        # AI鑑定プロンプトへの統合は
        # consultation-aware reading v2で実装する。
        "consultation_input_used_for_ai": (
            False
        ),

        "schema": (
            "customer_intake_v1"
        ),
    }


# ============================================================
# Chart request
# ============================================================


def build_chart_request(
    customer: CustomerInput,
):

    return SimpleNamespace(
        birth_date=(
            customer.birth_date
        ),
        birth_time=(
            customer.birth_time
        ),
        birth_place=(
            customer.birth_place
        ),
        gender=(
            customer.gender
        ),
    )


# ============================================================
# Chart validation
# ============================================================


def validate_chart_result(
    result: Mapping[
        str,
        Any,
    ],
) -> None:

    result = (
        require_mapping(
            result,
            "chart_result",
        )
    )

    chart = (
        require_mapping(
            result.get(
                "chart"
            ),
            "chart_result.chart",
        )
    )

    for position in (
        "year",
        "month",
        "day",
        "hour",
    ):

        pillar = chart.get(
            position
        )

        if pillar is None:

            raise RuntimeError(
                f"{position}柱が"
                "生成されていません。"
            )

        pillar = (
            require_mapping(
                pillar,
                (
                    f"chart."
                    f"{position}"
                ),
            )
        )

        require_non_empty_string(
            pillar.get(
                "pillar"
            ),
            (
                f"chart."
                f"{position}."
                "pillar"
            ),
        )

    day_master = (
        require_mapping(
            result.get(
                "day_master"
            ),
            "day_master",
        )
    )

    require_non_empty_string(
        day_master.get(
            "stem"
        ),
        "day_master.stem",
    )


# ============================================================
# Context validation
# ============================================================


def validate_reading_context(
    context: Mapping[
        str,
        Any,
    ],
) -> None:

    context = (
        require_mapping(
            context,
            "reading_context",
        )
    )

    if (
        context.get(
            "status"
        )
        != "ready_for_ai_reading"
    ):

        raise RuntimeError(
            "reading_contextが"
            "ready_for_ai_reading"
            "ではありません。"
        )


# ============================================================
# AI generation validation
# ============================================================


def validate_generation(
    generation: ReadingGenerationResult,
) -> None:

    if not isinstance(
        generation,
        ReadingGenerationResult,
    ):

        raise TypeError(
            "generationが"
            "ReadingGenerationResult"
            "ではありません。"
        )

    if (
        generation.status
        != "completed"
    ):

        raise RuntimeError(
            "AI鑑定生成が"
            "completedではありません。 "
            f"status="
            f"{generation.status}"
        )

    if (
        generation.response_status
        not in (
            None,
            "completed",
        )
    ):

        raise RuntimeError(
            "OpenAI responseが"
            "completedではありません。 "
            f"response_status="
            f"{generation.response_status}"
        )

    parsed = (
        require_mapping(
            generation.parsed,
            "generation.parsed",
        )
    )

    require_non_empty_string(
        parsed.get(
            "summary"
        ),
        "AI summary",
    )

    sections = (
        require_mapping(
            parsed.get(
                "sections"
            ),
            "AI sections",
        )
    )

    if (
        tuple(
            sections.keys()
        )
        != SECTIONS
    ):

        raise RuntimeError(
            "AI鑑定の"
            "8セクション構成が"
            "一致しません。"
        )

    require_non_empty_string(
        parsed.get(
            "disclaimer"
        ),
        "AI disclaimer",
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
            "productが"
            "ReadingProduct"
            "ではありません。"
        )

    if (
        product.status
        != "ready"
    ):

        raise RuntimeError(
            "ReadingProductが"
            "readyではありません。 "
            f"status="
            f"{product.status}"
        )

    if (
        len(
            product.sections
        )
        != len(
            SECTIONS
        )
    ):

        raise RuntimeError(
            "ReadingProductが"
            "8セクションでは"
            "ありません。"
        )


# ============================================================
# PDF validation
# ============================================================


def validate_pdf(
    path: Path,
) -> int:

    if not path.exists():

        raise RuntimeError(
            "PDFファイルが"
            "生成されていません。"
        )

    if not path.is_file():

        raise RuntimeError(
            "PDF出力先が"
            "ファイルではありません。"
        )

    if (
        path.suffix.lower()
        != ".pdf"
    ):

        raise RuntimeError(
            "PDF拡張子が"
            "不正です。"
        )

    size = (
        path.stat()
        .st_size
    )

    if (
        size
        < 10_000
    ):

        raise RuntimeError(
            "生成PDFのサイズが"
            "小さすぎます。 "
            f"size={size}"
        )

    data = (
        path.read_bytes()
    )

    if not data.startswith(
        b"%PDF-"
    ):

        raise RuntimeError(
            "生成ファイルが"
            "PDFではありません。"
        )

    return size


# ============================================================
# Security validation
# ============================================================


def validate_no_api_key_exposure(
    *values: Any,
) -> None:

    api_key = (
        os.getenv(
            OPENAI_API_KEY_ENV,
            "",
        )
        .strip()
    )

    if not api_key:
        return

    for index, value in enumerate(
        values,
        start=1,
    ):

        if isinstance(
            value,
            bytes,
        ):

            if (
                api_key.encode(
                    "utf-8"
                )
                in value
            ):

                raise RuntimeError(
                    "APIキーが"
                    "生成物に"
                    "露出しています。 "
                    f"target={index}"
                )

            continue

        serialized = (
            json.dumps(
                value,
                ensure_ascii=False,
                default=str,
            )
        )

        if (
            api_key
            in serialized
        ):

            raise RuntimeError(
                "APIキーが"
                "生成物に"
                "露出しています。 "
                f"target={index}"
            )


# ============================================================
# Display chart
# ============================================================


def print_chart_summary(
    chart_result: Mapping[
        str,
        Any,
    ],
) -> None:

    chart = (
        chart_result[
            "chart"
        ]
    )

    pillars = []

    for position in (
        "year",
        "month",
        "day",
        "hour",
    ):

        pillars.append(
            chart[
                position
            ][
                "pillar"
            ]
        )

    day_master = (
        chart_result[
            "day_master"
        ][
            "stem"
        ]
    )

    print(
        "   "
        + " / ".join(
            pillars
        )
    )

    print(
        f"   日主: "
        f"{day_master}"
    )


# ============================================================
# PDF metadata validation
# ============================================================


def validate_pdf_metadata(
) -> dict[str, Any]:

    metadata = (
        get_reading_pdf_metadata()
    )

    if (
        metadata.get(
            "version"
        )
        != READING_PDF_VERSION
    ):

        raise RuntimeError(
            "PDF versionが"
            "一致しません。"
        )

    if (
        metadata.get(
            "method"
        )
        != READING_PDF_METHOD
    ):

        raise RuntimeError(
            "PDF methodが"
            "一致しません。"
        )

    if (
        metadata.get(
            "recalculates_astrology"
        )
        is not False
    ):

        raise RuntimeError(
            "PDF層が占術を"
            "再計算しています。"
        )

    if (
        metadata.get(
            "rewrites_ai_reading"
        )
        is not False
    ):

        raise RuntimeError(
            "PDF層がAI鑑定文を"
            "書き換えています。"
        )

    if (
        metadata.get(
            "exposes_api_key"
        )
        is not False
    ):

        raise RuntimeError(
            "PDF層のAPIキー"
            "非露出設定が"
            "不正です。"
        )

    return metadata


# ============================================================
# Main generation
# ============================================================


def generate_customer_reading(
    customer: CustomerInput,
) -> dict[str, Any]:

    model = (
        validate_environment()
    )

    customer_id = (
        build_customer_id()
    )

    customer_dir = (
        create_customer_directory(
            customer_id
        )
    )

    intake_path = (
        customer_dir
        / "intake.json"
    )

    chart_path = (
        customer_dir
        / "chart.json"
    )

    context_path = (
        customer_dir
        / "reading_context.json"
    )

    ai_reading_path = (
        customer_dir
        / "ai_reading.json"
    )

    product_path = (
        customer_dir
        / "product.json"
    )

    pdf_path = (
        customer_dir
        / "四柱推命鑑定書.pdf"
    )

    summary_path = (
        customer_dir
        / "summary.json"
    )

    # --------------------------------------------------------
    # 0. Intake
    # --------------------------------------------------------

    print()
    print(
        "0. 顧客情報保存"
    )

    intake_data = (
        build_intake_data(
            customer_id,
            customer,
        )
    )

    save_json(
        intake_path,
        intake_data,
    )

    print(
        "   OK"
    )

    # --------------------------------------------------------
    # 1. Chart
    # --------------------------------------------------------

    print()
    print(
        "1. 命式計算"
    )

    request = (
        build_chart_request(
            customer
        )
    )

    target_datetime = (
        datetime.now()
    )

    chart_result = (
        calculate_chart(
            request,
            target_datetime=(
                target_datetime
            ),
        )
    )

    validate_chart_result(
        chart_result
    )

    save_json(
        chart_path,
        chart_result,
    )

    print_chart_summary(
        chart_result
    )

    print(
        "   OK"
    )

    # --------------------------------------------------------
    # 2. Reading context
    # --------------------------------------------------------

    print()
    print(
        "2. reading_context生成"
    )

    context = (
        build_reading_context(
            chart_result
        )
    )

    validate_reading_context(
        context
    )

    save_json(
        context_path,
        context,
    )

    print(
        "   OK"
    )

    # --------------------------------------------------------
    # 3. OpenAI
    # --------------------------------------------------------

    print()
    print(
        "3. OpenAIで"
        "8セクション鑑定生成"
    )

    generation = (
        generate_reading(
            context,
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

    validate_generation(
        generation
    )

    save_json(
        ai_reading_path,
        generation.parsed,
    )

    print(
        "   OK"
    )

    print(
        "   response_status: "
        f"{generation.response_status}"
    )

    print(
        "   response_id: "
        f"{generation.response_id}"
    )

    # --------------------------------------------------------
    # 4. ReadingProduct
    # --------------------------------------------------------

    print()
    print(
        "4. ReadingProduct生成"
    )

    product = (
        build_reading_product(
            context,
            generation,
            title=(
                PRODUCT_TITLE
            ),
            sections=(
                SECTIONS
            ),
        )
    )

    validate_product(
        product
    )

    product_dict = (
        product.to_dict()
    )

    save_json(
        product_path,
        product_dict,
    )

    print(
        "   OK"
    )

    # --------------------------------------------------------
    # 5. PDF
    # --------------------------------------------------------

    print()
    print(
        "5. 四柱推命鑑定書PDF生成"
    )

    generated_pdf_path = (
        write_reading_product_pdf(
            product,
            pdf_path,
            document_title=(
                DOCUMENT_TITLE
            ),
        )
    )

    pdf_size = (
        validate_pdf(
            generated_pdf_path
        )
    )

    print(
        "   OK"
    )

    print(
        f"   size: "
        f"{pdf_size:,} bytes"
    )

    # --------------------------------------------------------
    # 6. Security
    # --------------------------------------------------------

    print()
    print(
        "6. セキュリティ確認"
    )

    validate_no_api_key_exposure(
        intake_data,
        chart_result,
        context,
        generation.parsed,
        product_dict,
        generated_pdf_path
        .read_bytes(),
    )

    print(
        "   OK"
    )

    # --------------------------------------------------------
    # 7. PDF metadata
    # --------------------------------------------------------

    print()
    print(
        "7. PDF metadata確認"
    )

    pdf_metadata = (
        validate_pdf_metadata()
    )

    print(
        "   OK"
    )

    # --------------------------------------------------------
    # 8. Summary
    # --------------------------------------------------------

    summary = {
        "customer_id": (
            customer_id
        ),

        "customer_name": (
            customer.customer_name
        ),

        "script_version": (
            SCRIPT_VERSION
        ),

        "product_title": (
            PRODUCT_TITLE
        ),

        "model": (
            model
        ),

        "generated_at": (
            datetime.now()
            .isoformat(
                timespec="seconds"
            )
        ),

        "target_datetime": (
            target_datetime
            .isoformat(
                timespec="seconds"
            )
        ),

        "response_status": (
            generation
            .response_status
        ),

        "response_id": (
            generation
            .response_id
        ),

        "usage": (
            generation.usage
        ),

        "pdf_version": (
            pdf_metadata[
                "version"
            ]
        ),

        "pdf_method": (
            pdf_metadata[
                "method"
            ]
        ),

        "pdf_size": (
            pdf_size
        ),

        "files": {
            "intake": str(
                intake_path.resolve()
            ),

            "chart": str(
                chart_path.resolve()
            ),

            "reading_context": str(
                context_path.resolve()
            ),

            "ai_reading": str(
                ai_reading_path.resolve()
            ),

            "product": str(
                product_path.resolve()
            ),

            "pdf": str(
                generated_pdf_path
                .resolve()
            ),
        },

        "consultation_input_used_for_ai": (
            False
        ),

        "status": (
            "completed"
        ),
    }

    save_json(
        summary_path,
        summary,
    )

    return summary


# ============================================================
# Completion display
# ============================================================


def print_completion(
    summary: Mapping[
        str,
        Any,
    ],
) -> None:

    print()
    print(
        "=" * 72
    )

    print(
        "鑑定書生成完了"
    )

    print(
        "=" * 72
    )

    print()

    print(
        "顧客ID: "
        f"{summary['customer_id']}"
    )

    print(
        "お名前: "
        f"{summary['customer_name']}"
    )

    print()

    print(
        "PDF:"
    )

    print(
        f"  "
        f"{summary['files']['pdf']}"
    )

    print()

    print(
        "Product JSON:"
    )

    print(
        f"  "
        f"{summary['files']['product']}"
    )

    print()

    print(
        "AI Reading JSON:"
    )

    print(
        f"  "
        f"{summary['files']['ai_reading']}"
    )

    print()

    print(
        "Intake:"
    )

    print(
        f"  "
        f"{summary['files']['intake']}"
    )

    print()

    print(
        "response_status: "
        f"{summary['response_status']}"
    )

    print(
        "response_id: "
        f"{summary['response_id']}"
    )

    print(
        "pdf_size: "
        f"{summary['pdf_size']:,} bytes"
    )

    print()

    print(
        "STATUS: COMPLETED"
    )


# ============================================================
# Main
# ============================================================


def main() -> int:

    print()
    print(
        "# 四柱推命鑑定書"
    )

    print(
        "# 顧客本番生成 v1"
    )

    print()

    print(
        f"script_version: "
        f"{SCRIPT_VERSION}"
    )

    print(
        f"product_title: "
        f"{PRODUCT_TITLE}"
    )

    print()

    try:

        # ----------------------------------------------------
        # Environment check first.
        #
        # 顧客情報を入力してから
        # APIキーなしで失敗するのを避ける。
        # ----------------------------------------------------

        model = (
            validate_environment()
        )

        print(
            f"model: "
            f"{model}"
        )

        print(
            f"pdf_version: "
            f"{READING_PDF_VERSION}"
        )

        print(
            f"pdf_method: "
            f"{READING_PDF_METHOD}"
        )

        # ----------------------------------------------------
        # Customer intake
        # ----------------------------------------------------

        customer = (
            collect_customer_input()
        )

        confirmed = (
            confirm_customer_input(
                customer
            )
        )

        if not confirmed:

            print()
            print(
                "キャンセルしました。"
            )

            return 0

        # ----------------------------------------------------
        # Generation
        # ----------------------------------------------------

        summary = (
            generate_customer_reading(
                customer
            )
        )

        # ----------------------------------------------------
        # Complete
        # ----------------------------------------------------

        print_completion(
            summary
        )

        return 0

    except KeyboardInterrupt:

        print()
        print()
        print(
            "ユーザー操作により"
            "中断しました。"
        )

        return 130

    except Exception as exc:

        print()
        print(
            "=" * 72,
            file=sys.stderr,
        )

        print(
            "鑑定書生成失敗",
            file=sys.stderr,
        )

        print(
            "=" * 72,
            file=sys.stderr,
        )

        print(
            (
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":

    raise SystemExit(
        main()
    )
