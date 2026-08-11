"""
scripts/generate_sample_reading.py

商品品質確認用の実鑑定サンプル生成スクリプト。
実命式 -> reading_context -> OpenAI -> 8セクションJSON -> Markdown保存。
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping

from engine.chart import calculate_chart
from engine.reading_context import build_reading_context
from engine.reading_generator import (
    OPENAI_API_KEY_ENV,
    OPENAI_READING_MODEL_ENV,
    ReadingGenerationResult,
    generate_reading,
    get_default_model,
    has_openai_api_key,
)

SCRIPT_VERSION = "generate_sample_reading_v1"

SAMPLE_BIRTH_DATE = "1985-07-17"
SAMPLE_BIRTH_TIME = "21:50"
SAMPLE_BIRTH_PLACE = "石川県"
SAMPLE_GENDER = "female"

TARGET_DATETIME = datetime(2026, 8, 10, 15, 36)

EXPECTED_PILLARS = {
    "year": "乙丑",
    "month": "癸未",
    "day": "丁巳",
    "hour": "辛亥",
}
EXPECTED_DAY_MASTER = "丁"
EXPECTED_ANNUAL_GANZHI = "丙午"

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

SECTION_LABELS = {
    "core_personality": "本質・性格",
    "career": "仕事・適職",
    "wealth": "金運",
    "relationships": "恋愛・人間関係",
    "health": "健康傾向",
    "current_luck": "現在の運勢",
    "future_flow": "今後の流れ",
    "advice": "開運アドバイス",
}

OUTPUT_FORMAT = "json"
MAX_OUTPUT_TOKENS = 8000
REASONING_EFFORT = "minimal"
STORE = False

OUTPUT_DIR = Path("output")
JSON_OUTPUT_PATH = OUTPUT_DIR / "sample_reading_1985-07-17_2150.json"
MARKDOWN_OUTPUT_PATH = OUTPUT_DIR / "sample_reading_1985-07-17_2150.md"


def _require_mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{name}はdict型である必要があります。")
    return value


def _require_non_empty_string(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name}は文字列である必要があります。")
    value = value.strip()
    if not value:
        raise ValueError(f"{name}が空です。")
    return value


def validate_environment() -> str:
    if not has_openai_api_key():
        raise RuntimeError(
            f"{OPENAI_API_KEY_ENV} が設定されていません。"
        )
    return _require_non_empty_string(
        get_default_model(),
        "OpenAI model",
    )


def build_sample_request() -> SimpleNamespace:
    return SimpleNamespace(
        birth_date=SAMPLE_BIRTH_DATE,
        birth_time=SAMPLE_BIRTH_TIME,
        birth_place=SAMPLE_BIRTH_PLACE,
        gender=SAMPLE_GENDER,
    )


def validate_verified_chart(chart_result: Mapping[str, Any]) -> None:
    chart = _require_mapping(chart_result["chart"], "chart")

    for position, expected in EXPECTED_PILLARS.items():
        actual = chart[position]["pillar"]
        if actual != expected:
            raise RuntimeError(
                f"{position}柱が不一致です: expected={expected}, actual={actual}"
            )

    actual_dm = chart_result["day_master"]["stem"]
    if actual_dm != EXPECTED_DAY_MASTER:
        raise RuntimeError(
            f"日主が不一致です: expected={EXPECTED_DAY_MASTER}, actual={actual_dm}"
        )


def validate_reading_context(context: Mapping[str, Any]) -> None:
    if context.get("status") != "ready_for_ai_reading":
        raise RuntimeError(
            f"reading_context statusが不正です: {context.get('status')!r}"
        )

    pillars = context["natal_chart"]["pillars"]

    for position, expected in EXPECTED_PILLARS.items():
        actual = pillars[position]["pillar"]
        if actual != expected:
            raise RuntimeError(
                f"context {position}柱が不一致です: expected={expected}, actual={actual}"
            )

    if context["day_master"]["stem"] != EXPECTED_DAY_MASTER:
        raise RuntimeError("reading_contextの日主が不一致です。")

    annual = context["luck"]["annual_luck"]["ganzhi"]
    if annual != EXPECTED_ANNUAL_GANZHI:
        raise RuntimeError(
            f"歳運が不一致です: expected={EXPECTED_ANNUAL_GANZHI}, actual={annual}"
        )

    missing = [
        section
        for section in SECTIONS
        if section not in context["reading_sections"]
    ]
    if missing:
        raise RuntimeError(
            "reading_contextにsectionが不足しています: "
            + ", ".join(missing)
        )


def validate_section(section_data: Any, section_name: str) -> None:
    section_data = _require_mapping(section_data, section_name)

    for key in ("title", "summary", "detail"):
        _require_non_empty_string(
            section_data.get(key),
            f"{section_name}.{key}",
        )

    for key in ("evidence", "advice"):
        values = section_data.get(key)
        if not isinstance(values, list):
            raise TypeError(f"{section_name}.{key}はlistではありません。")
        if not values:
            raise ValueError(f"{section_name}.{key}が空です。")
        for index, item in enumerate(values):
            _require_non_empty_string(
                item,
                f"{section_name}.{key}[{index}]",
            )


def validate_generation_result(result: ReadingGenerationResult) -> None:
    if not isinstance(result, ReadingGenerationResult):
        raise TypeError("ReadingGenerationResultではありません。")

    if result.status != "completed":
        raise RuntimeError(
            f"AI生成が未完了です: status={result.status!r}, "
            f"response_status={result.response_status!r}"
        )

    if result.output_format != "json":
        raise RuntimeError("output_formatがjsonではありません。")

    if result.sections != SECTIONS:
        raise RuntimeError(
            f"sectionsが不一致です: {result.sections!r}"
        )

    if not isinstance(result.parsed, dict):
        raise RuntimeError("parse済みJSONがありません。")

    reading = result.parsed
    for key in ("summary", "sections", "disclaimer"):
        if key not in reading:
            raise RuntimeError(f"鑑定JSONに{key}がありません。")

    _require_non_empty_string(reading["summary"], "summary")
    _require_non_empty_string(reading["disclaimer"], "disclaimer")

    sections = _require_mapping(reading["sections"], "sections")

    if set(sections.keys()) != set(SECTIONS):
        raise RuntimeError(
            f"8セクションが不一致です: {list(sections.keys())}"
        )

    for section_name in SECTIONS:
        validate_section(sections[section_name], section_name)


def build_markdown(
    model: str,
    result: ReadingGenerationResult,
) -> str:
    if result.parsed is None:
        raise RuntimeError("parsedがありません。")

    reading = result.parsed
    lines = [
        "# 四柱推命 AI鑑定サンプル",
        "",
        "## 基本情報",
        "",
        f"- 生年月日: {SAMPLE_BIRTH_DATE}",
        f"- 出生時刻: {SAMPLE_BIRTH_TIME}",
        f"- 出生地: {SAMPLE_BIRTH_PLACE}",
        f"- 性別: {SAMPLE_GENDER}",
        f"- 評価日時: {TARGET_DATETIME.isoformat()}",
        f"- 使用モデル: {model}",
        "",
        "## 命式",
        "",
        f"- 年柱: {EXPECTED_PILLARS['year']}",
        f"- 月柱: {EXPECTED_PILLARS['month']}",
        f"- 日柱: {EXPECTED_PILLARS['day']}",
        f"- 時柱: {EXPECTED_PILLARS['hour']}",
        f"- 日主: {EXPECTED_DAY_MASTER}",
        f"- 歳運: {EXPECTED_ANNUAL_GANZHI}",
        "",
        "## 総合鑑定",
        "",
        _require_non_empty_string(reading["summary"], "summary"),
        "",
    ]

    for section_name in SECTIONS:
        data = reading["sections"][section_name]
        lines.extend([
            f"## {SECTION_LABELS[section_name]}",
            "",
            f"### {_require_non_empty_string(data['title'], section_name + '.title')}",
            "",
            _require_non_empty_string(data["summary"], section_name + ".summary"),
            "",
            _require_non_empty_string(data["detail"], section_name + ".detail"),
            "",
            "### 根拠",
            "",
        ])

        for item in data["evidence"]:
            lines.append(f"- {item}")

        lines.extend(["", "### アドバイス", ""])

        for item in data["advice"]:
            lines.append(f"- {item}")

        lines.append("")

    lines.extend([
        "## 免責・注意事項",
        "",
        _require_non_empty_string(reading["disclaimer"], "disclaimer"),
        "",
        "---",
        "",
        f"Generated by {SCRIPT_VERSION}",
        "",
    ])

    return "\n".join(lines)


def build_json_document(
    model: str,
    chart_result: Mapping[str, Any],
    context: Mapping[str, Any],
    result: ReadingGenerationResult,
) -> dict[str, Any]:
    return {
        "document_version": SCRIPT_VERSION,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "subject": {
            "birth_date": SAMPLE_BIRTH_DATE,
            "birth_time": SAMPLE_BIRTH_TIME,
            "birth_place": SAMPLE_BIRTH_PLACE,
            "gender": SAMPLE_GENDER,
            "target_date_time": TARGET_DATETIME.isoformat(),
        },
        "verified": {
            "pillars": dict(EXPECTED_PILLARS),
            "day_master": EXPECTED_DAY_MASTER,
            "annual_ganzhi": EXPECTED_ANNUAL_GANZHI,
        },
        "generation": {
            "model": model,
            "response_id": result.response_id,
            "response_status": result.response_status,
            "usage": result.usage,
            "sections": list(result.sections),
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "reasoning_effort": REASONING_EFFORT,
            "store": STORE,
        },
        "engine_summary": {
            "chart_method": chart_result.get("method"),
            "reading_context_method": context.get("method"),
            "reading_context_status": context.get("status"),
        },
        "reading": result.parsed,
    }


def main() -> int:
    try:
        print("=" * 60)
        print("四柱推命AI鑑定 商品品質サンプル生成")
        print("=" * 60)

        model = validate_environment()
        print(f"model: {model}")
        print(
            f"{OPENAI_READING_MODEL_ENV}: "
            f"{os.getenv(OPENAI_READING_MODEL_ENV)!r}"
        )

        print("\n1. 命式計算")
        request = build_sample_request()
        chart_result = calculate_chart(
            request,
            target_datetime=TARGET_DATETIME,
        )
        validate_verified_chart(chart_result)
        print("   OK: 乙丑 / 癸未 / 丁巳 / 辛亥")

        print("\n2. reading_context生成")
        context = build_reading_context(chart_result)
        validate_reading_context(context)
        print("   OK")

        print("\n3. OpenAIで8セクション鑑定生成")
        result = generate_reading(
            context,
            model=model,
            sections=SECTIONS,
            output_format=OUTPUT_FORMAT,
            max_output_tokens=MAX_OUTPUT_TOKENS,
            reasoning_effort=REASONING_EFFORT,
            store=STORE,
        )
        validate_generation_result(result)
        print("   OK")

        print("\n4. ファイル保存")
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        document = build_json_document(
            model,
            chart_result,
            context,
            result,
        )
        JSON_OUTPUT_PATH.write_text(
            json.dumps(
                document,
                ensure_ascii=False,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )

        markdown = build_markdown(model, result)
        MARKDOWN_OUTPUT_PATH.write_text(
            markdown,
            encoding="utf-8",
        )

        print("   OK")
        print("\n生成完了")
        print(f"JSON: {JSON_OUTPUT_PATH.resolve()}")
        print(f"Markdown: {MARKDOWN_OUTPUT_PATH.resolve()}")
        print(f"response_status: {result.response_status}")
        print(f"response_id: {result.response_id}")
        print(f"usage: {result.usage}")

        return 0

    except KeyboardInterrupt:
        print("\n中断しました。", file=sys.stderr)
        return 130

    except Exception as exc:
        print("\n生成に失敗しました。", file=sys.stderr)
        print(
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
