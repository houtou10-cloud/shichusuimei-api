"""
scripts/generate_customer_reading.py

四柱推命鑑定書 v1.2
本番顧客向け・相談内容連動・品質ゲート統合PDF生成スクリプト。
出生時刻不明（三柱モード）に対応。
品質ゲート不通過時のAuto-Repairに対応。

処理フロー
----------
顧客入力
    ↓
intake.json
    ↓
calculate_chart()
    ↓
reading_context.json
    ↓
build_consultation_context()
    ↓
consultation_context.json
    ↓
generate_reading(
    reading_context,
    consultation_context=...
)
    ↓
ai_reading.json
    ↓
reading_quality_v1
    ↓
valid=False の場合のみ Auto-Repair（最大2回）
    ↓
品質ゲート再検査
    ↓
quality_report.json / repair_history.json
    ↓
build_reading_product()
    ↓
product.json
    ↓
write_reading_product_pdf()
    ↓
四柱推命鑑定書_<お名前>様.pdf
    ↓
summary.json

設計原則
--------
命式 = 事実
相談 = 焦点
AI   = 説明

相談内容によって、

- 四柱
- 日主
- 身強身弱
- 格局
- 用神
- 大運
- 歳運

などの計算済み占術情報を
変更・再計算・創作しない。

注意
----
このスクリプトは実際にOpenAI APIを呼ぶ。

必要:
    OPENAI_API_KEY

任意:
    OPENAI_READING_MODEL

またPDF生成にはPlaywright Chromiumが必要。

    pip install playwright
    python -m playwright install chromium

実行例
------
PowerShell:

    $env:PYTHONPATH="."
    python .\\scripts\\generate_customer_reading.py

Version
-------
generate_customer_reading_v1_2
"""

from __future__ import annotations

import inspect
import json
import os
import re
import sys

from copy import deepcopy
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, Mapping


from engine.chart import (
    calculate_chart,
)

from engine.consultation_context import (
    build_consultation_context,
    validate_consultation_context,
)

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

from engine.reading_decade_luck import (
    generate_decade_luck_reading,
)

from engine.reading_product import (
    ReadingProduct,
    build_reading_product,
)

from engine.reading_pdf import (
    get_reading_pdf_metadata,
    write_reading_product_pdf,
)

from engine.reading_quality import (
    ReadingQualityError,
    ReadingQualityReport,
    validate_customer_facing_reading,
)

from engine.reading_repair import (
    ReadingRepairResult,
    repair_reading,
)


# ============================================================
# Script metadata
# ============================================================


SCRIPT_VERSION = (
    "generate_customer_reading_v1_2"
)


# ============================================================
# Product configuration
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

MAX_OUTPUT_TOKENS = 12000

REASONING_EFFORT = "minimal"

STORE = False

AUTO_REPAIR_ENABLED = True

MAX_REPAIR_ATTEMPTS = 2

REPAIR_MAX_OUTPUT_TOKENS = 8000

REPAIR_REASONING_EFFORT = "minimal"

REPAIR_STORE = False

# valid=True のwarningでも、
# 占術上の事実整合性に関わるものは
# Auto-Repair対象とする。
# valid=True のwarningは、
# quality_reportへ記録するが、
# v1.1ではPDF生成停止条件にはしない。
#
# 占術上の事実整合性に関する高度な
# warning判定・自動修復はv1.2で扱う。
AUTO_REPAIR_WARNING_CODES = frozenset()
PRODUCT_TITLE = "四柱推命鑑定書"

DOCUMENT_TITLE = "四柱推命鑑定書"

BRAND_NAME = "四柱推命 八雲"

BIRTH_COUNTRY_TYPE_JAPAN = "japan"
BIRTH_COUNTRY_TYPE_OVERSEAS = "overseas"


class OverseasBirthUnsupportedError(RuntimeError):
    """海外出生の命式計算を安全に停止するための例外。"""



# ============================================================
# Output
# ============================================================


OUTPUT_ROOT = (
    Path("output")
    / "customers"
)


PDF_FILENAME_PREFIX = (
    "四柱推命鑑定書_"
)

PDF_FILENAME_SUFFIX = (
    "様.pdf"
)

INTAKE_FILENAME = (
    "intake.json"
)

READING_CONTEXT_FILENAME = (
    "reading_context.json"
)

CONSULTATION_CONTEXT_FILENAME = (
    "consultation_context.json"
)

AI_READING_FILENAME = (
    "ai_reading.json"
)

DECADE_LUCK_AI_FILENAME = (
    "decade_luck_ai.json"
)

QUALITY_REPORT_FILENAME = (
    "quality_report.json"
)

REPAIR_HISTORY_FILENAME = (
    "repair_history.json"
)

PRODUCT_FILENAME = (
    "product.json"
)

SUMMARY_FILENAME = (
    "summary.json"
)


# ============================================================
# PDF filename
# ============================================================


def build_customer_pdf_filename(
    customer_name: str,
) -> str:
    """
    顧客名入りPDFファイル名を生成する。

    例:
        田中浩二
        -> 四柱推命鑑定書_田中浩二様.pdf

    Windowsで使用できない文字は除去する。
    """

    if not isinstance(
        customer_name,
        str,
    ):
        raise TypeError(
            "customer_nameは文字列で"
            "指定してください。"
        )

    normalized = (
        customer_name.strip()
    )

    if not normalized:
        raise ValueError(
            "customer_nameが空です。"
        )

    # Windows予約文字と制御文字を除去。
    normalized = re.sub(
        r'[<>:"/\\|?*\x00-\x1f]',
        "",
        normalized,
    )

    # 末尾のドット・空白はWindowsで不安定。
    normalized = (
        normalized.rstrip(
            ". "
        )
    )

    if not normalized:
        raise ValueError(
            "PDFファイル名に使用できる"
            "customer_nameがありません。"
        )

    return (
        PDF_FILENAME_PREFIX
        + normalized
        + PDF_FILENAME_SUFFIX
    )


# ============================================================
# Generic helpers
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


def _optional_string(
    value: Any,
    name: str,
) -> str:

    if value is None:
        return ""

    if not isinstance(
        value,
        str,
    ):
        raise TypeError(
            f"{name}は文字列である必要があります。"
        )

    return value.strip()


def save_json(
    path: Path,
    data: Any,
) -> Path:

    if not isinstance(
        path,
        Path,
    ):
        path = Path(
            path
        )

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


def _json_safe_copy(
    value: Any,
) -> Any:
    """
    JSON round-trip可能なdeepcopyを作る。
    """

    return json.loads(
        json.dumps(
            value,
            ensure_ascii=False,
            default=str,
        )
    )


# ============================================================
# Input normalization
# ============================================================


def normalize_birth_date(
    value: str,
) -> str:

    value = _require_non_empty_string(
        value,
        "生年月日",
    )

    if not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}",
        value,
    ):
        raise ValueError(
            "生年月日はYYYY-MM-DD形式で"
            "入力してください。"
        )

    try:
        parsed = datetime.strptime(
            value,
            "%Y-%m-%d",
        )
    except ValueError as exc:
        raise ValueError(
            "生年月日はYYYY-MM-DD形式で"
            "入力してください。"
        ) from exc

    return parsed.strftime(
        "%Y-%m-%d"
    )


def normalize_birth_time(
    value: Any,
) -> str | None:
    """
    出生時刻をHH:MM形式へ正規化する。

    内部表現としてNoneは
    「出生時刻不明」として正式に許可する。

    空文字は正規化関数へ直接渡された場合は
    不正入力としてValueErrorにする。
    CLIの空欄入力はprompt_customer_input()側で
    Noneへ変換してから本関数へ渡す。
    """

    if value is None:
        return None

    if not isinstance(
        value,
        str,
    ):
        raise TypeError(
            "出生時刻はHH:MM形式の文字列、"
            "またはNoneで指定してください。"
        )

    value = value.strip()

    if not value:
        raise ValueError(
            "出生時刻が空です。"
            "不明の場合はNoneを指定してください。"
        )

    try:
        parsed = datetime.strptime(
            value,
            "%H:%M",
        )
    except ValueError as exc:
        raise ValueError(
            "出生時刻はHH:MM形式で"
            "入力してください。"
        ) from exc

    return parsed.strftime(
        "%H:%M"
    )


def normalize_gender(
    value: str,
) -> str:

    value = _require_non_empty_string(
        value,
        "性別",
    )

    normalized = (
        value.strip()
        .lower()
    )

    male_values = {
        "男性",
        "男",
        "male",
        "m",
    }

    female_values = {
        "女性",
        "女",
        "female",
        "f",
    }

    if normalized in male_values:
        return "male"

    if normalized in female_values:
        return "female"

    raise ValueError(
        "性別は男性/女性"
        "またはmale/femaleで"
        "入力してください。"
    )


def normalize_name(
    value: str,
) -> str:

    value = _require_non_empty_string(
        value,
        "お名前",
    )

    if len(
        value
    ) > 100:
        raise ValueError(
            "お名前が長すぎます。"
        )

    return value


def normalize_birth_country_type(
    value: Any,
) -> str:
    """出生国区分を japan / overseas に正規化する。"""

    if value is None:
        return BIRTH_COUNTRY_TYPE_JAPAN

    if not isinstance(value, str):
        raise TypeError(
            "出生国区分は文字列である必要があります。"
        )

    normalized = value.strip().lower()

    if not normalized:
        return BIRTH_COUNTRY_TYPE_JAPAN

    if normalized in {"1", "日本", "国内", "japan", "jp"}:
        return BIRTH_COUNTRY_TYPE_JAPAN

    if normalized in {"2", "日本以外", "海外", "overseas", "foreign"}:
        return BIRTH_COUNTRY_TYPE_OVERSEAS

    raise ValueError(
        "出生国区分は1（日本）または2（日本以外）で入力してください。"
    )


def normalize_birth_country(
    value: Any,
    *,
    country_type: str,
) -> str:
    country_type = normalize_birth_country_type(country_type)

    if country_type == BIRTH_COUNTRY_TYPE_JAPAN:
        return "日本"

    country = _require_non_empty_string(value, "出生国")
    if len(country) > 100:
        raise ValueError("出生国が長すぎます。")
    return country


def normalize_birth_city(
    value: Any,
    *,
    country_type: str,
) -> str:
    country_type = normalize_birth_country_type(country_type)

    if country_type == BIRTH_COUNTRY_TYPE_JAPAN:
        return ""

    city = _require_non_empty_string(value, "出生都市")
    if len(city) > 200:
        raise ValueError("出生都市が長すぎます。")
    return city


def normalize_birth_place(
    value: str,
) -> str:

    value = _require_non_empty_string(
        value,
        "出生地",
    )

    if len(
        value
    ) > 200:
        raise ValueError(
            "出生地が長すぎます。"
        )

    return value


# ============================================================
# Customer ID
# ============================================================


def create_customer_id(
    now: datetime | None = None,
) -> str:

    if now is None:
        now = datetime.now()

    return now.strftime(
        "%Y%m%d_%H%M%S"
    )


def create_customer_dir(
    customer_id: str,
) -> Path:

    customer_id = (
        _require_non_empty_string(
            customer_id,
            "customer_id",
        )
    )

    if not re.fullmatch(
        r"[0-9]{8}_[0-9]{6}",
        customer_id,
    ):
        raise ValueError(
            "customer_idの形式が不正です。"
        )

    directory = (
        OUTPUT_ROOT
        / customer_id
    )

    directory.mkdir(
        parents=True,
        exist_ok=False,
    )

    return directory


# ============================================================
# CLI input
# ============================================================


def prompt_customer_input() -> Dict[str, Any]:

    print()
    print("=" * 72)
    print("四柱推命鑑定書｜顧客情報入力")
    print("=" * 72)
    print()

    name = normalize_name(input("お名前: "))
    birth_date = normalize_birth_date(input("生年月日 YYYY-MM-DD: "))
    birth_time_input = input(
        "出生時刻 HH:MM "
        "（不明の場合はEnter）: "
    ).strip()

    birth_time = normalize_birth_time(
        birth_time_input
        if birth_time_input
        else None
    )

    print()
    print("出生国を選択してください")
    print("1. 日本")
    print("2. 日本以外")

    birth_country_type = normalize_birth_country_type(
        input("選択 1/2: ")
    )

    if birth_country_type == BIRTH_COUNTRY_TYPE_JAPAN:
        birth_country = "日本"
        birth_city = ""
        birth_place = normalize_birth_place(
            input("出生地（都道府県）: ")
        )
    else:
        birth_country = normalize_birth_country(
            input("出生国: "),
            country_type=birth_country_type,
        )
        birth_city = normalize_birth_city(
            input("出生都市: "),
            country_type=birth_country_type,
        )
        birth_place = f"{birth_country} {birth_city}".strip()

    gender = normalize_gender(input("性別 男性/女性: "))
    concern = _optional_string(input("現在のお悩み: "), "現在のお悩み")
    desired_future = _optional_string(input("理想の未来: "), "理想の未来")

    return {
        "name": name,
        "birth_date": birth_date,
        "birth_time": birth_time,
        "birth_country_type": birth_country_type,
        "birth_country": birth_country,
        "birth_city": birth_city,
        "birth_place": birth_place,
        "gender": gender,
        "concern": concern,
        "desired_future": desired_future,
    }


# ============================================================
# Chart helpers
# ============================================================


def build_chart_request(
    intake: Mapping[
        str,
        Any,
    ],
) -> SimpleNamespace:

    intake = _require_mapping(
        intake,
        "intake",
    )

    country_type = normalize_birth_country_type(
        intake.get("birth_country_type", BIRTH_COUNTRY_TYPE_JAPAN)
    )

    if country_type != BIRTH_COUNTRY_TYPE_JAPAN:
        raise OverseasBirthUnsupportedError(
            "海外出生は現在のv1.0では命式計算に対応していません。"
        )

    return SimpleNamespace(
        birth_date=(
            intake[
                "birth_date"
            ]
        ),
        birth_time=(
            intake[
                "birth_time"
            ]
        ),
        birth_place=(
            intake[
                "birth_place"
            ]
        ),
        gender=(
            intake[
                "gender"
            ]
        ),
    )


def extract_pillars(
    chart_result: Mapping[
        str,
        Any,
    ],
) -> Dict[str, str | None]:
    """
    chart_resultから表示・summary用の柱文字列を抽出する。

    年柱・月柱・日柱は常に必須。
    時柱は出生時刻不明時のみNoneを許可する。
    """

    chart_result = _require_mapping(
        chart_result,
        "chart_result",
    )

    chart = chart_result.get(
        "chart"
    )

    chart = _require_mapping(
        chart,
        "chart_result.chart",
    )

    result: Dict[
        str,
        str | None,
    ] = {}

    for position in (
        "year",
        "month",
        "day",
    ):
        pillar_data = chart.get(
            position
        )

        pillar_data = _require_mapping(
            pillar_data,
            f"chart.{position}",
        )

        pillar = pillar_data.get(
            "pillar"
        )

        result[
            position
        ] = _require_non_empty_string(
            pillar,
            f"{position}柱",
        )

    hour_data = chart.get(
        "hour"
    )

    if hour_data is None:
        birth_time_status = chart_result.get(
            "birth_time_status",
            {},
        )

        if isinstance(
            birth_time_status,
            Mapping,
        ):
            birth_time_known = (
                birth_time_status.get(
                    "known"
                )
            )

            if birth_time_known is True:
                raise RuntimeError(
                    "出生時刻ありの命式で"
                    "時柱が欠落しています。"
                )

        result["hour"] = None

    else:
        hour_data = _require_mapping(
            hour_data,
            "chart.hour",
        )

        result[
            "hour"
        ] = _require_non_empty_string(
            hour_data.get(
                "pillar"
            ),
            "hour柱",
        )

    return result


def extract_day_master(
    reading_context: Mapping[
        str,
        Any,
    ],
) -> str:

    reading_context = (
        _require_mapping(
            reading_context,
            "reading_context",
        )
    )

    day_master = (
        reading_context.get(
            "day_master"
        )
    )

    day_master = _require_mapping(
        day_master,
        "reading_context.day_master",
    )

    return _require_non_empty_string(
        day_master.get(
            "stem"
        ),
        "日主",
    )


def format_pillars_for_display(
    pillars: Mapping[
        str,
        Any,
    ],
) -> str:
    """
    命式をコンソール表示用の文字列へ変換する。

    出生時刻不明なら時柱位置を
    「出生時刻不明」と表示する。
    """

    pillars = _require_mapping(
        pillars,
        "pillars",
    )

    year = _require_non_empty_string(
        pillars.get("year"),
        "年柱",
    )
    month = _require_non_empty_string(
        pillars.get("month"),
        "月柱",
    )
    day = _require_non_empty_string(
        pillars.get("day"),
        "日柱",
    )

    hour_raw = pillars.get(
        "hour"
    )

    if hour_raw is None:
        hour = "出生時刻不明"
    else:
        hour = _require_non_empty_string(
            hour_raw,
            "時柱",
        )

    return (
        f"{year} / "
        f"{month} / "
        f"{day} / "
        f"{hour}"
    )


# ============================================================
# Validation
# ============================================================


def validate_generation_result(
    result: ReadingGenerationResult,
) -> None:

    if not isinstance(
        result,
        ReadingGenerationResult,
    ):
        raise TypeError(
            "generation_resultが"
            "ReadingGenerationResultではありません。"
        )

    if (
        result.output_format
        != "json"
    ):
        raise RuntimeError(
            "商品生成ではJSON鑑定が必要です。"
        )

    if (
        result.parsed
        is None
    ):
        raise RuntimeError(
            "AI鑑定JSONが取得できませんでした。"
        )

    if (
        result.response_status
        not in (
            None,
            "completed",
        )
    ):
        raise RuntimeError(
            "OpenAI responseがcompletedではありません。 "
            f"status={result.response_status}"
        )

    if (
        result.status
        != "completed"
    ):
        raise RuntimeError(
            "鑑定生成がcompletedではありません。 "
            f"status={result.status}"
        )


def get_auto_repair_issue_codes(
    report: ReadingQualityReport,
) -> tuple[str, ...]:
    """
    valid=Trueでも修復すべき
    重要warning codeを返す。
    """

    if not isinstance(
        report,
        ReadingQualityReport,
    ):
        raise TypeError(
            "quality_reportが"
            "ReadingQualityReportではありません。"
        )

    result: list[str] = []

    for issue in report.issues:
        if (
            issue.code
            in AUTO_REPAIR_WARNING_CODES
            and issue.code
            not in result
        ):
            result.append(
                issue.code
            )

    return tuple(
        result
    )


def should_auto_repair(
    report: ReadingQualityReport,
) -> bool:
    """
    Auto-Repair開始・継続条件。

    - errorがある
    - valid=Trueでも重要warningがある
    """

    if not isinstance(
        report,
        ReadingQualityReport,
    ):
        raise TypeError(
            "quality_reportが"
            "ReadingQualityReportではありません。"
        )

    if not report.valid:
        return True

    return bool(
        get_auto_repair_issue_codes(
            report
        )
    )


def ensure_no_required_repair_issues(
    report: ReadingQualityReport,
) -> None:
    """
    PDF生成前の最終防波堤。

    valid=Trueでも重要warningが
    残っていれば停止する。
    """

    if not isinstance(
        report,
        ReadingQualityReport,
    ):
        raise TypeError(
            "quality_reportが"
            "ReadingQualityReportではありません。"
        )

    codes = (
        get_auto_repair_issue_codes(
            report
        )
    )

    if not codes:
        return

    raise ReadingQualityError(
        "顧客向け鑑定文章に"
        "Auto-Repair必須の品質問題が"
        "残っています。 "
        "codes="
        + ", ".join(
            codes
        )
    )


def validate_quality_report(
    report: ReadingQualityReport,
) -> None:
    """
    顧客向け品質レポートを検証する。

    report.valid が False の場合は、
    ReadingQualityError を送出して
    ReadingProduct / PDF 生成へ進ませない。

    品質判定そのものは
    engine.reading_quality が担当する。
    この関数は既に生成済みの report を
    本番パイプライン用にエラー化するだけ。
    """

    if not isinstance(
        report,
        ReadingQualityReport,
    ):
        raise TypeError(
            "quality_reportが"
            "ReadingQualityReportではありません。"
        )

    if report.valid:
        return

    lines = [
        (
            "顧客向け鑑定文章が品質ゲートを"
            "通過しませんでした。"
        ),
        f"issue_count={report.issue_count}",
    ]

    for issue in report.issues:
        matched = (
            f" matched={issue.matched!r}"
            if issue.matched is not None
            else ""
        )

        lines.append(
            f"- [{issue.code}] "
            f"{issue.path}: "
            f"{issue.message}"
            f"{matched}"
        )

    raise ReadingQualityError(
        "\n".join(lines)
    )



def build_repaired_generation_result(
    original: ReadingGenerationResult,
    repair_result: ReadingRepairResult,
) -> ReadingGenerationResult:
    """
    Auto-Repair後のJSONをReadingProduct工程へ渡すため、
    新しいReadingGenerationResultを生成する。

    ReadingGenerationResultはfrozen dataclassのため、
    元resultを直接書き換えない。

    response_id / usage は初回生成の情報を維持する。
    Repair API側の情報はrepair_history.jsonへ保存する。
    """

    if not isinstance(
        original,
        ReadingGenerationResult,
    ):
        raise TypeError(
            "originalがReadingGenerationResultではありません。"
        )

    if not isinstance(
        repair_result,
        ReadingRepairResult,
    ):
        raise TypeError(
            "repair_resultがReadingRepairResultではありません。"
        )

    repaired = _require_mapping(
        repair_result.repaired,
        "repair_result.repaired",
    )

    repaired_copy = _json_safe_copy(
        repaired
    )

    return ReadingGenerationResult(
        output_format=original.output_format,
        model=original.model,
        text=json.dumps(
            repaired_copy,
            ensure_ascii=False,
        ),
        parsed=repaired_copy,
        response_id=original.response_id,
        response_status=original.response_status,
        usage=deepcopy(
            original.usage
        ),
        sections=tuple(
            original.sections
        ),
        method=original.method,
        status=original.status,
    )


def build_repair_history(
    *,
    initial_quality_report: ReadingQualityReport,
    attempts: list[Dict[str, Any]],
    final_quality_report: ReadingQualityReport,
) -> Dict[str, Any]:
    """
    Auto-Repair履歴を保存用dictへ変換する。
    """

    if not isinstance(
        initial_quality_report,
        ReadingQualityReport,
    ):
        raise TypeError(
            "initial_quality_reportが"
            "ReadingQualityReportではありません。"
        )

    if not isinstance(
        final_quality_report,
        ReadingQualityReport,
    ):
        raise TypeError(
            "final_quality_reportが"
            "ReadingQualityReportではありません。"
        )

    return {
        "enabled": AUTO_REPAIR_ENABLED,
        "max_attempts": MAX_REPAIR_ATTEMPTS,
        "attempt_count": len(
            attempts
        ),
        "repaired": bool(
            attempts
        ),
        "initial_quality": (
            initial_quality_report.to_dict()
        ),
        "attempts": deepcopy(
            attempts
        ),
        "final_quality": (
            final_quality_report.to_dict()
        ),
        "final_valid": (
            final_quality_report.valid
        ),
    }


def validate_product(
    product: ReadingProduct,
) -> None:

    if not isinstance(
        product,
        ReadingProduct,
    ):
        raise TypeError(
            "productがReadingProductではありません。"
        )

    if (
        product.title
        != PRODUCT_TITLE
    ):
        raise RuntimeError(
            "商品タイトルが不正です。"
        )

    if len(
        product.sections
    ) != len(
        SECTIONS
    ):
        raise RuntimeError(
            "鑑定セクション数が"
            "8ではありません。"
        )


def validate_pdf(
    pdf_path: Path,
) -> int:

    if not pdf_path.exists():
        raise RuntimeError(
            "PDFファイルが生成されていません。"
        )

    data = (
        pdf_path.read_bytes()
    )

    if not data:
        raise RuntimeError(
            "PDFファイルが空です。"
        )

    if not data.startswith(
        b"%PDF"
    ):
        raise RuntimeError(
            "生成ファイルがPDF形式ではありません。"
        )

    return len(
        data
    )


# ============================================================
# Security
# ============================================================


def validate_output_security(
    *,
    product_data: Mapping[
        str,
        Any,
    ],
    consultation_context: Mapping[
        str,
        Any,
    ],
    reading_context: Mapping[
        str,
        Any,
    ],
) -> None:
    """
    保存対象JSONにAPIキーや
    prompt内部フィールドが混入していないことを確認する。

    顧客相談文そのものは、
    consultation_context.jsonへ保存するため
    セキュリティ違反とは扱わない。
    """

    serialized = json.dumps(
        {
            "product": (
                product_data
            ),
            "consultation_context": (
                consultation_context
            ),
            "reading_context": (
                reading_context
            ),
        },
        ensure_ascii=False,
        default=str,
    )

    api_key = os.getenv(
        OPENAI_API_KEY_ENV,
        "",
    ).strip()

    if (
        api_key
        and api_key
        in serialized
    ):
        raise RuntimeError(
            "保存対象JSONに"
            "OPENAI_API_KEYが含まれています。"
        )

    forbidden_markers = (
        '"api_key"',
        '"system_prompt"',
        '"user_prompt"',
    )

    lower = (
        serialized.lower()
    )

    for marker in forbidden_markers:
        if marker.lower() in lower:
            raise RuntimeError(
                "保存対象JSONに"
                "非公開フィールドが含まれています: "
                f"{marker}"
            )


# ============================================================
# Summary
# ============================================================


def build_summary(
    *,
    customer_id: str,
    intake: Mapping[
        str,
        Any,
    ],
    pillars: Mapping[
        str,
        Any,
    ],
    day_master: str,
    consultation_context: Mapping[
        str,
        Any,
    ],
    generation_result: ReadingGenerationResult,
    pdf_path: Path,
    pdf_size: int,
    model: str,
    quality_report: ReadingQualityReport | None = None,
    birth_time_status: Mapping[str, Any] | None = None,
    repair_history: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:

    focus = (
        consultation_context.get(
            "focus",
            {}
        )
    )

    safety = (
        consultation_context.get(
            "safety",
            {}
        )
    )

    return {
        "script_version": (
            SCRIPT_VERSION
        ),

        "customer_id": (
            customer_id
        ),

        "customer_name": (
            intake.get(
                "name"
            )
        ),

        "birth": {
            "birth_date": (
                intake.get(
                    "birth_date"
                )
            ),
            "birth_time": (
                intake.get(
                    "birth_time"
                )
            ),
            "birth_country_type": intake.get(
                "birth_country_type", BIRTH_COUNTRY_TYPE_JAPAN
            ),
            "birth_country": intake.get("birth_country", "日本"),
            "birth_city": intake.get("birth_city", ""),
            "birth_place": (
                intake.get(
                    "birth_place"
                )
            ),
            "gender": (
                intake.get(
                    "gender"
                )
            ),
        },

        "birth_time_status": (
            _json_safe_copy(
                birth_time_status
            )
            if isinstance(
                birth_time_status,
                Mapping,
            )
            else None
        ),

        "pillars": {
            "year": (
                pillars[
                    "year"
                ]
            ),
            "month": (
                pillars[
                    "month"
                ]
            ),
            "day": (
                pillars[
                    "day"
                ]
            ),
            "hour": (
                pillars[
                    "hour"
                ]
            ),
        },

        "day_master": (
            day_master
        ),

        "consultation": {
            "has_consultation": (
                consultation_context.get(
                    "has_consultation"
                )
            ),
            "primary_focus": (
                focus.get(
                    "primary"
                )
            ),
            "secondary_focus": (
                deepcopy(
                    focus.get(
                        "secondary",
                        [],
                    )
                )
            ),
            "requires_cautious_language": (
                safety.get(
                    "requires_cautious_language",
                    False,
                )
            ),
        },

        "generation": {
            "model": (
                model
            ),
            "response_status": (
                generation_result.response_status
            ),
            "response_id": (
                generation_result.response_id
            ),
            "usage": deepcopy(
                generation_result.usage
            ),
            "method": (
                generation_result.method
            ),
            "status": (
                generation_result.status
            ),
        },

        "quality": (
            quality_report.to_dict()
            if isinstance(
                quality_report,
                ReadingQualityReport,
            )
            else None
        ),

        "repair": (
            _json_safe_copy(
                repair_history
            )
            if isinstance(
                repair_history,
                Mapping,
            )
            else None
        ),

        "pdf": {
            "path": str(
                pdf_path
            ),
            "size_bytes": (
                pdf_size
            ),
        },

        "created_at": (
            datetime.now()
            .astimezone()
            .isoformat()
        ),

        "status": (
            "completed"
        ),
    }


# ============================================================
# Environment
# ============================================================


def validate_environment() -> str:

    if not has_openai_api_key():
        raise RuntimeError(
            "OPENAI_API_KEY が設定されていません。"
        )

    model = get_default_model()

    return _require_non_empty_string(
        model,
        "OpenAI model",
    )


# ============================================================
# Main generation
# ============================================================


def generate_customer_reading(
    intake: Mapping[
        str,
        Any,
    ],
) -> Dict[str, Any]:

    intake = _require_mapping(
        intake,
        "intake",
    )

    # 外部から関数として呼ばれた場合も
    # 最低限正規化する。
    normalized_intake = {
        "name": normalize_name(
            intake.get(
                "name"
            )
        ),
        "birth_date": (
            normalize_birth_date(
                intake.get(
                    "birth_date"
                )
            )
        ),
        "birth_time": (
            normalize_birth_time(
                (
                    None
                    if (
                        isinstance(
                            intake.get(
                                "birth_time"
                            ),
                            str,
                        )
                        and not intake.get(
                            "birth_time"
                        ).strip()
                    )
                    else intake.get(
                        "birth_time"
                    )
                )
            )
        ),
        "birth_country_type": normalize_birth_country_type(
            intake.get("birth_country_type", BIRTH_COUNTRY_TYPE_JAPAN)
        ),
        "birth_country": "",
        "birth_city": "",
        "birth_place": "",
        "gender": normalize_gender(
            intake.get(
                "gender"
            )
        ),
        "concern": (
            _optional_string(
                intake.get(
                    "concern",
                    "",
                ),
                "concern",
            )
        ),
        "desired_future": (
            _optional_string(
                intake.get(
                    "desired_future",
                    "",
                ),
                "desired_future",
            )
        ),
    }

    country_type = normalized_intake["birth_country_type"]

    normalized_intake["birth_country"] = normalize_birth_country(
        intake.get("birth_country", "日本"),
        country_type=country_type,
    )
    normalized_intake["birth_city"] = normalize_birth_city(
        intake.get("birth_city", ""),
        country_type=country_type,
    )

    if country_type == BIRTH_COUNTRY_TYPE_JAPAN:
        normalized_intake["birth_place"] = normalize_birth_place(
            intake.get("birth_place")
        )
    else:
        normalized_intake["birth_place"] = (
            f"{normalized_intake['birth_country']} "
            f"{normalized_intake['birth_city']}"
        ).strip()

    generation_started_at = (
        datetime.now()
    )

    customer_id = (
        create_customer_id(
            generation_started_at
        )
    )

    customer_dir = (
        create_customer_dir(
            customer_id
        )
    )

    intake_path = (
        customer_dir
        / INTAKE_FILENAME
    )

    reading_context_path = (
        customer_dir
        / READING_CONTEXT_FILENAME
    )

    consultation_context_path = (
        customer_dir
        / CONSULTATION_CONTEXT_FILENAME
    )

    ai_reading_path = (
        customer_dir
        / AI_READING_FILENAME
    )

    decade_luck_ai_path = (
        customer_dir
        / DECADE_LUCK_AI_FILENAME
    )

    quality_report_path = (
        customer_dir
        / QUALITY_REPORT_FILENAME
    )

    repair_history_path = (
        customer_dir
        / REPAIR_HISTORY_FILENAME
    )

    product_path = (
        customer_dir
        / PRODUCT_FILENAME
    )

    pdf_filename = (
        build_customer_pdf_filename(
            normalized_intake[
                "name"
            ]
        )
    )

    pdf_path = (
        customer_dir
        / pdf_filename
    )

    summary_path = (
        customer_dir
        / SUMMARY_FILENAME
    )

    # --------------------------------------------------------
    # 0. Intake
    # --------------------------------------------------------

    print(
        "0. 顧客情報保存"
    )

    intake_record = {
        "customer_id": (
            customer_id
        ),
        "name": (
            normalized_intake[
                "name"
            ]
        ),
        "birth_date": (
            normalized_intake[
                "birth_date"
            ]
        ),
        "birth_time": (
            normalized_intake[
                "birth_time"
            ]
        ),
        "birth_country_type": normalized_intake["birth_country_type"],
        "birth_country": normalized_intake["birth_country"],
        "birth_city": normalized_intake["birth_city"],
        "birth_place": (
            normalized_intake[
                "birth_place"
            ]
        ),
        "gender": (
            normalized_intake[
                "gender"
            ]
        ),
        "concern": (
            normalized_intake[
                "concern"
            ]
        ),
        "desired_future": (
            normalized_intake[
                "desired_future"
            ]
        ),
        "created_at": (
            generation_started_at
            .astimezone()
            .isoformat()
        ),
        "schema_version": (
            "customer_intake_v1"
        ),
    }

    save_json(
        intake_path,
        intake_record,
    )

    print(
        "   OK"
    )
    print()

    if normalized_intake["birth_country_type"] == BIRTH_COUNTRY_TYPE_OVERSEAS:
        print("=" * 72)
        print("海外出生のため命式計算を停止しました")
        print("=" * 72)
        print()
        print("海外出生は現在のv1.0では命式計算に対応していません。")
        print("誤ったタイムゾーン・サマータイム・時刻補正による")
        print("命式生成を防ぐため、処理を停止しました。")
        print()
        print("顧客情報はintake.jsonへ保存済みです:")
        print(f"  {intake_path.resolve()}")
        raise OverseasBirthUnsupportedError(
            "海外出生は現在のv1.0では命式計算に対応していません。"
        )

    model = validate_environment()

    # --------------------------------------------------------
    # 1. Chart
    # --------------------------------------------------------

    print(
        "1. 命式計算"
    )

    request = build_chart_request(
        normalized_intake
    )

    chart_result = calculate_chart(
        request,
        target_datetime=(
            generation_started_at
        ),
    )

    pillars = extract_pillars(
        chart_result
    )

    print(
        "   "
        + format_pillars_for_display(
            pillars
        )
    )

    birth_time_status = (
        chart_result.get(
            "birth_time_status",
            {},
        )
    )

    if (
        isinstance(
            birth_time_status,
            Mapping,
        )
        and birth_time_status.get(
            "known"
        )
        is False
    ):
        print(
            "   ※ 出生時刻不明のため、"
            "時柱なしの三柱モードで鑑定します。"
        )
        print(
            "   ※ 大運開始時期・現在大運の境界は"
            "推定扱いです。"
        )

    # --------------------------------------------------------
    # 2. Reading context
    # --------------------------------------------------------

    print()
    print(
        "2. reading_context生成"
    )

    reading_context = (
        build_reading_context(
            chart_result
        )
    )

    reading_context = _require_mapping(
        reading_context,
        "reading_context",
    )

    day_master = (
        extract_day_master(
            reading_context
        )
    )

    save_json(
        reading_context_path,
        _json_safe_copy(
            reading_context
        ),
    )

    print(
        f"   日主: {day_master}"
    )

    print(
        "   OK"
    )

    # --------------------------------------------------------
    # 3. Consultation context
    # --------------------------------------------------------

    print()
    print(
        "3. consultation_context生成"
    )

    consultation_context = (
        build_consultation_context(
            concern=(
                normalized_intake[
                    "concern"
                ]
            ),
            desired_future=(
                normalized_intake[
                    "desired_future"
                ]
            ),
        )
    )

    consultation_validation = (
        validate_consultation_context(
            consultation_context
        )
    )

    if (
        consultation_validation.get(
            "valid"
        )
        is not True
    ):
        raise RuntimeError(
            "consultation_contextが"
            "validではありません。"
        )

    save_json(
        consultation_context_path,
        consultation_context,
    )

    primary_focus = (
        consultation_context[
            "focus"
        ][
            "primary"
        ]
    )

    print(
        "   primary_focus: "
        f"{primary_focus}"
    )

    print(
        "   OK"
    )

    # --------------------------------------------------------
    # 4. OpenAI
    # --------------------------------------------------------

    print()
    print(
        "4. OpenAIで8セクション相談連動鑑定生成"
    )

    generation_result = (
        generate_reading(
            reading_context,
            consultation_context=(
                consultation_context
            ),
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

    if (
        generation_result.parsed
        is None
    ):
        raise RuntimeError(
            "AI Reading JSONがありません。"
        )

    save_json(
        ai_reading_path,
        generation_result.parsed,
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

    # --------------------------------------------------------
    # 4.5. Customer-facing quality gate
    # --------------------------------------------------------

    print()
    print(
        "4.5. 顧客向け品質ゲート"
    )

    initial_quality_report = (
        validate_customer_facing_reading(
            generation_result.parsed,
            reading_context=(
                reading_context
            ),
            consultation_context=(
                consultation_context
            ),
        )
    )

    quality_report = (
        initial_quality_report
    )

    print(
        "   valid: "
        f"{quality_report.valid}"
    )

    print(
        "   issues: "
        f"{quality_report.issue_count}"
    )

    repair_attempts: list[
        Dict[str, Any]
    ] = []

    final_generation_result = (
        generation_result
    )

    # --------------------------------------------------------
    # 4.6. Auto-Repair
    # --------------------------------------------------------

    if (
        AUTO_REPAIR_ENABLED
        and should_auto_repair(
            quality_report
        )
    ):
        print()
        print(
            "4.6. Auto-Repair"
        )

        for attempt_number in range(
            1,
            MAX_REPAIR_ATTEMPTS + 1,
        ):
            print(
                "   attempt: "
                f"{attempt_number}"
            )

            repair_result = (
                repair_reading(
                    final_generation_result.parsed,
                    quality_report,
                    reading_context=(
                        reading_context
                    ),
                    consultation_context=(
                        consultation_context
                    ),
                    model=model,
                    max_output_tokens=(
                        REPAIR_MAX_OUTPUT_TOKENS
                    ),
                    reasoning_effort=(
                        REPAIR_REASONING_EFFORT
                    ),
                    store=REPAIR_STORE,
                )
            )

            repaired_generation_result = (
                build_repaired_generation_result(
                    final_generation_result,
                    repair_result,
                )
            )

            if (
                repaired_generation_result.parsed
                is None
            ):
                raise RuntimeError(
                    "Auto-Repair後の"
                    "AI Reading JSONがありません。"
                )

            repaired_quality_report = (
                validate_customer_facing_reading(
                    repaired_generation_result.parsed,
                    reading_context=(
                        reading_context
                    ),
                    consultation_context=(
                        consultation_context
                    ),
                )
            )

            repair_attempts.append(
                {
                    "attempt": (
                        attempt_number
                    ),
                    "repair": (
                        repair_result.to_dict()
                    ),
                    "quality_before": (
                        quality_report.to_dict()
                    ),
                    "quality_after": (
                        repaired_quality_report.to_dict()
                    ),
                }
            )

            final_generation_result = (
                repaired_generation_result
            )

            quality_report = (
                repaired_quality_report
            )

            print(
                "   response_status: "
                f"{repair_result.response_status}"
            )

            print(
                "   response_id: "
                f"{repair_result.response_id}"
            )

            print(
                "   changed: "
                f"{repair_result.changed}"
            )

            print(
                "   valid_after_repair: "
                f"{quality_report.valid}"
            )

            print(
                "   issues_after_repair: "
                f"{quality_report.issue_count}"
            )

            if not should_auto_repair(
                quality_report
            ):
                print(
                    "   OK"
                )
                break

    # --------------------------------------------------------
    # 4.7. Final quality gate
    # --------------------------------------------------------

    print()
    print(
        "4.7. 最終品質ゲート"
    )

    repair_history = (
        build_repair_history(
            initial_quality_report=(
                initial_quality_report
            ),
            attempts=(
                repair_attempts
            ),
            final_quality_report=(
                quality_report
            ),
        )
    )

    save_json(
        repair_history_path,
        repair_history,
    )

    save_json(
        quality_report_path,
        quality_report.to_dict(),
    )

    if (
        final_generation_result.parsed
        is None
    ):
        raise RuntimeError(
            "最終AI Reading JSONがありません。"
        )

    # ai_reading.json は
    # Product / PDFへ実際に使用する最終版を保存する。
    save_json(
        ai_reading_path,
        final_generation_result.parsed,
    )

    print(
        "   valid: "
        f"{quality_report.valid}"
    )

    print(
        "   issues: "
        f"{quality_report.issue_count}"
    )

    print(
        "   repair_attempts: "
        f"{len(repair_attempts)}"
    )

    validate_quality_report(
        quality_report
    )

    ensure_no_required_repair_issues(
        quality_report
    )

    print(
        "   OK"
    )

    # 以降は必ず最終採用版を使う。
    generation_result = (
        final_generation_result
    )

    # --------------------------------------------------------
    # 4.8. 大運AI鑑定
    # --------------------------------------------------------
    #
    # 本番ReadingProductが decade_luck 対応済みの場合のみ
    # 大運AI鑑定を生成する。
    #
    # 既存テストのfake build_reading_productが
    # decade_luck未対応の場合はAPI呼び出しを行わない。
    # --------------------------------------------------------

    try:
        product_signature = inspect.signature(
            build_reading_product
        )
        product_parameters = (
            product_signature.parameters
        )
        supports_decade_luck = (
            "decade_luck"
            in product_parameters
            or any(
                parameter.kind
                == inspect.Parameter.VAR_KEYWORD
                for parameter
                in product_parameters.values()
            )
        )
    except (
        TypeError,
        ValueError,
    ):
        supports_decade_luck = True

    decade_luck_result = None
    decade_luck_data: Dict[
        str,
        Any,
    ] = {}

    if supports_decade_luck:
        print()
        print(
            "4.8. 大運AI鑑定生成"
        )

        decade_luck_result = (
            generate_decade_luck_reading(
                reading_context,
                consultation_context=(
                    consultation_context
                ),
                model=model,
                reasoning_effort=(
                    REASONING_EFFORT
                ),
                store=STORE,
            )
        )

        decade_luck_data = (
            decade_luck_result.to_dict()
        )

        if not isinstance(
            decade_luck_data,
            Mapping,
        ):
            raise RuntimeError(
                "大運AI鑑定結果が"
                "Mappingではありません。"
            )

        decade_luck_data = dict(
            decade_luck_data
        )

        decade_periods = (
            decade_luck_data.get(
                "periods",
                []
            )
        )

        if not isinstance(
            decade_periods,
            list,
        ):
            raise RuntimeError(
                "大運AI鑑定periodsが"
                "listではありません。"
            )

        save_json(
            decade_luck_ai_path,
            decade_luck_data,
        )

        print(
            "   OK"
        )
        print(
            "   response_status: "
            f"{decade_luck_result.response_status}"
        )
        print(
            "   response_id: "
            f"{decade_luck_result.response_id}"
        )
        print(
            "   periods: "
            f"{len(decade_periods)}"
        )

    # --------------------------------------------------------
    # 5. ReadingProduct
    # --------------------------------------------------------

    print()
    print(
        "5. ReadingProduct生成"
    )

    product_kwargs: Dict[
        str,
        Any,
    ] = {
        "title": PRODUCT_TITLE,
        "sections": SECTIONS,
        "customer_name": (
            normalized_intake[
                "name"
            ]
        ),
        "reading_datetime": (
            generation_started_at
        ),
        "brand_name": BRAND_NAME,
    }

    if supports_decade_luck:
        product_kwargs[
            "decade_luck"
        ] = decade_luck_data

    product = (
        build_reading_product(
            reading_context,
            generation_result,
            **product_kwargs,
        )
    )

    validate_product(
        product
    )

    product_data = (
        product.to_dict()
    )

    save_json(
        product_path,
        product_data,
    )

    print(
        "   OK"
    )

    # --------------------------------------------------------
    # 6. Security
    # --------------------------------------------------------

    print()
    print(
        "6. セキュリティ確認"
    )

    validate_output_security(
        product_data=(
            product_data
        ),
        consultation_context=(
            consultation_context
        ),
        reading_context=(
            reading_context
        ),
    )

    print(
        "   OK"
    )

    # --------------------------------------------------------
    # 7. PDF
    # --------------------------------------------------------

    print()
    print(
        "7. 四柱推命鑑定書PDF生成"
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

    if (
        generated_pdf_path
        != pdf_path
    ):
        raise RuntimeError(
            "PDF出力パスが期待値と異なります。"
        )

    pdf_size = validate_pdf(
        pdf_path
    )

    print(
        "   OK"
    )

    print(
        "   size: "
        f"{pdf_size:,} bytes"
    )

    # --------------------------------------------------------
    # 8. PDF metadata
    # --------------------------------------------------------

    print()
    print(
        "8. PDF metadata確認"
    )

    pdf_metadata = (
        get_reading_pdf_metadata()
    )

    if not isinstance(
        pdf_metadata,
        Mapping,
    ):
        raise RuntimeError(
            "PDF metadataがdictではありません。"
        )

    if (
        pdf_metadata.get(
            "recalculates_astrology"
        )
        is not False
    ):
        raise RuntimeError(
            "PDF metadataの"
            "recalculates_astrologyが不正です。"
        )

    print(
        "   OK"
    )

    # --------------------------------------------------------
    # 9. Summary
    # --------------------------------------------------------

    summary = build_summary(
        customer_id=(
            customer_id
        ),
        intake=(
            normalized_intake
        ),
        pillars=pillars,
        day_master=(
            day_master
        ),
        consultation_context=(
            consultation_context
        ),
        generation_result=(
            generation_result
        ),
        pdf_path=pdf_path,
        pdf_size=(
            pdf_size
        ),
        model=model,
        quality_report=(
            quality_report
        ),
        birth_time_status=(
            chart_result.get(
                "birth_time_status"
            )
        ),
        repair_history=(
            repair_history
        ),
    )

    summary[
        "pdf_metadata"
    ] = _json_safe_copy(
        pdf_metadata
    )

    save_json(
        summary_path,
        summary,
    )

    return {
        "customer_id": (
            customer_id
        ),
        "customer_dir": (
            customer_dir
        ),
        "intake_path": (
            intake_path
        ),
        "reading_context_path": (
            reading_context_path
        ),
        "consultation_context_path": (
            consultation_context_path
        ),
        "ai_reading_path": (
            ai_reading_path
        ),
        "decade_luck_ai_path": (
            decade_luck_ai_path
        ),
        "quality_report_path": (
            quality_report_path
        ),
        "quality_report": (
            quality_report.to_dict()
        ),
        "repair_history_path": (
            repair_history_path
        ),
        "repair_history": (
            deepcopy(
                repair_history
            )
        ),
        "product_path": (
            product_path
        ),
        "pdf_path": (
            pdf_path
        ),
        "summary_path": (
            summary_path
        ),
        "pdf_size": (
            pdf_size
        ),
        "pillars": (
            pillars
        ),
        "day_master": (
            day_master
        ),
        "primary_focus": (
            primary_focus
        ),
        "response_status": (
            generation_result.response_status
        ),
        "response_id": (
            generation_result.response_id
        ),
        "usage": deepcopy(
            generation_result.usage
        ),
        "model": (
            model
        ),
        "birth_time_status": (
            _json_safe_copy(
                chart_result.get(
                    "birth_time_status",
                    {},
                )
            )
        ),
    }


# ============================================================
# Console output
# ============================================================


def print_completion(
    *,
    intake: Mapping[
        str,
        Any,
    ],
    result: Mapping[
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
        f"{result['customer_id']}"
    )

    print(
        "お名前: "
        f"{intake['name']}"
    )

    print(
        "相談焦点: "
        f"{result['primary_focus']}"
    )

    print()

    print(
        "命式:"
    )

    pillars = result[
        "pillars"
    ]

    print(
        "  "
        + format_pillars_for_display(
            pillars
        )
    )

    birth_time_status = result.get(
        "birth_time_status",
        {},
    )

    if (
        isinstance(
            birth_time_status,
            Mapping,
        )
        and birth_time_status.get(
            "known"
        )
        is False
    ):
        print(
            "  ※ 出生時刻不明："
            "年柱・月柱・日柱を中心に鑑定"
        )
        print(
            "  ※ 大運の開始・切替時期は推定"
        )

    print(
        "日主: "
        f"{result['day_master']}"
    )

    print()

    print(
        "PDF:"
    )

    print(
        "  "
        f"{result['pdf_path'].resolve()}"
    )

    print()

    print(
        "Product JSON:"
    )

    print(
        "  "
        f"{result['product_path'].resolve()}"
    )

    print()

    print(
        "AI Reading JSON:"
    )

    print(
        "  "
        f"{result['ai_reading_path'].resolve()}"
    )

    print()

    decade_luck_ai_path = (
        result.get(
            "decade_luck_ai_path"
        )
    )

    if (
        decade_luck_ai_path is not None
        and Path(
            decade_luck_ai_path
        ).exists()
    ):
        print(
            "Decade Luck AI JSON:"
        )
        print(
            "  "
            f"{Path(decade_luck_ai_path).resolve()}"
        )
        print()

    print(
        "Quality Report:"
    )

    print(
        "  "
        f"{result['quality_report_path'].resolve()}"
    )

    print(
        "  valid: "
        f"{result['quality_report']['valid']}"
    )

    print(
        "  issues: "
        f"{result['quality_report']['issue_count']}"
    )

    print()

    print(
        "Repair History:"
    )

    print(
        "  "
        f"{result['repair_history_path'].resolve()}"
    )

    print(
        "  attempts: "
        f"{result['repair_history']['attempt_count']}"
    )

    print(
        "  repaired: "
        f"{result['repair_history']['repaired']}"
    )

    print()

    print(
        "Reading Context:"
    )

    print(
        "  "
        f"{result['reading_context_path'].resolve()}"
    )

    print()

    print(
        "Consultation Context:"
    )

    print(
        "  "
        f"{result['consultation_context_path'].resolve()}"
    )

    print()

    print(
        "Intake:"
    )

    print(
        "  "
        f"{result['intake_path'].resolve()}"
    )

    print()

    print(
        "Summary:"
    )

    print(
        "  "
        f"{result['summary_path'].resolve()}"
    )

    print()

    print(
        "response_status: "
        f"{result['response_status']}"
    )

    print(
        "response_id: "
        f"{result['response_id']}"
    )

    print(
        "model: "
        f"{result['model']}"
    )

    print(
        "pdf_size: "
        f"{result['pdf_size']:,} bytes"
    )

    print(
        "quality_valid: "
        f"{result['quality_report']['valid']}"
    )

    print(
        "quality_issues: "
        f"{result['quality_report']['issue_count']}"
    )

    print(
        "repair_attempts: "
        f"{result['repair_history']['attempt_count']}"
    )

    print(
        "usage: "
        f"{result['usage']}"
    )


# ============================================================
# Main
# ============================================================


def main() -> int:

    print()
    print(
        "# 四柱推命鑑定書｜本番顧客生成"
    )

    print()

    print(
        f"script_version: {SCRIPT_VERSION}"
    )

    print(
        "consultation: enabled"
    )

    print(
        f"product_title: {PRODUCT_TITLE}"
    )

    print(
        f"output_root: {OUTPUT_ROOT.resolve()}"
    )

    print()

    if not has_openai_api_key():

        print(
            "=" * 72
        )

        print(
            "生成失敗"
        )

        print(
            "=" * 72
        )

        print(
            f"{OPENAI_API_KEY_ENV} が設定されていません。"
        )

        return 1

    configured_model = (
        os.getenv(
            OPENAI_READING_MODEL_ENV,
            "",
        ).strip()
    )

    if configured_model:

        print(
            "model: "
            f"{configured_model}"
        )

    else:

        print(
            "model: "
            f"{get_default_model()}"
        )

    print()

    try:

        intake = (
            prompt_customer_input()
        )

        print()

        result = (
            generate_customer_reading(
                intake
            )
        )

        print_completion(
            intake=intake,
            result=result,
        )

        return 0

    except KeyboardInterrupt:

        print()
        print(
            "処理を中止しました。"
        )

        return 130

    except Exception as exc:

        print()

        print(
            "=" * 72
        )

        print(
            "生成失敗"
        )

        print(
            "=" * 72
        )

        print(
            f"{type(exc).__name__}: {exc}"
        )

        return 1


if __name__ == "__main__":
    sys.exit(
        main()
    )