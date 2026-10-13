"""Generate a synthetic, provider-free customer-Web preview for staging QA.

The input is synthetic and not a source-text example.  Astrology calculation,
B evaluation, and customer rendering use the real implementation; only the
external-AI prose call is replaced by the existing deterministic fallback.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import os
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import api.fast_reading as fast_reading
from api.customer_pipeline import validate_customer_input
from api.customer_routes import _move_fast_back_link_to_header, _render_fast_result
from api.symbol_judgment_reference import FEATURE_FLAG_ENV


def generate_preview(output: Path) -> Path:
    original_flag = os.environ.get(FEATURE_FLAG_ENV)
    os.environ[FEATURE_FLAG_ENV] = "true"
    original_factory = fast_reading.create_customer_provider_client
    fast_reading.create_customer_provider_client = lambda: None
    try:
        customer_input = validate_customer_input({
            "birth_date": "1984-07-22",
            "birth_hour": "13",
            "birth_minute": "40",
            "birth_place": "福岡県",
            "gender": "male",
            "consultation": "合成入力によるステージング画面確認です。",
        })
        result = fast_reading.run_fast_reading(
            customer_input,
            reference_time=datetime(2026, 10, 13, 12, 0, tzinfo=ZoneInfo("Asia/Tokyo")),
        )
        document = _move_fast_back_link_to_header(_render_fast_result(result))
    finally:
        fast_reading.create_customer_provider_client = original_factory
        if original_flag is None:
            os.environ.pop(FEATURE_FLAG_ENV, None)
        else:
            os.environ[FEATURE_FLAG_ENV] = original_flag
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(document, encoding="utf-8")
    return output.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a synthetic B-reference customer-Web preview")
    parser.add_argument("--output", type=Path, required=True, help="Destination .html path")
    args = parser.parse_args()
    if args.output.suffix.lower() not in {".html", ".htm"}:
        parser.error("--output must use .html or .htm")
    print(generate_preview(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
