"""既存のゴールデン鑑定例を、従来（engine_v1）と本どおり（book_kiso）で比べる研究用スクリプト。

使い方: python scripts/compare_book_mode_goldens.py
本番の既定の計算は変更しない。結果は docs/book_mode_golden_comparison.json に書く。
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.models import ChartRequest  # noqa: E402
from engine.chart import calculate_chart  # noqa: E402
from engine.pillars import RULE_SET_BOOK  # noqa: E402

TARGET_DATETIME = datetime(2026, 1, 1, 12, 0)
POSITIONS = ("year", "month", "day", "hour")


def _golden_inputs() -> list[tuple[str, dict]]:
    found: dict[tuple, tuple[str, dict]] = {}
    for path in sorted((ROOT / "tests" / "golden").rglob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        candidates = []
        if isinstance(data, dict):
            for key in ("input", "request", "birth_input"):
                if isinstance(data.get(key), dict):
                    candidates.append(data[key])
        for item in candidates:
            if "birth_date" in item and "birth_place" in item and "gender" in item:
                key = (item["birth_date"], item.get("birth_time"), item["birth_place"], item["gender"])
                found.setdefault(key, (path.stem, item))
    return list(found.values())


def _summary(chart: dict) -> dict:
    pillars = chart["chart"]
    return {
        "pillars": {p: (pillars[p]["pillar"] if pillars.get(p) else None) for p in POSITIONS},
        "main_hidden_stems": {p: (pillars[p]["main_hidden_stem"] if pillars.get(p) else None) for p in POSITIONS},
        "strength": chart["final_strength_judgment"].get("label"),
        "strength_score": chart["final_strength_judgment"].get("final_score"),
        "primary_pattern": chart["pattern_judgment"].get("primary_pattern"),
        "primary_useful_element": chart["useful_gods"].get("primary_useful_element"),
        "final_useful_elements": chart["useful_gods"].get("final_useful_elements"),
    }


def main() -> dict:
    rows = []
    for name, item in _golden_inputs():
        req = ChartRequest(
            birth_date=item["birth_date"],
            birth_time=item.get("birth_time"),
            birth_place=item["birth_place"],
            gender=item["gender"],
        )
        engine = _summary(calculate_chart(req, target_datetime=TARGET_DATETIME))
        book = _summary(calculate_chart(req, target_datetime=TARGET_DATETIME, rule_set=RULE_SET_BOOK))
        changed = sorted(k for k in engine if engine[k] != book[k])
        rows.append({"case": name, "input": item, "changed": changed, "engine_v1": engine, "book_kiso": book})
    result = {
        "target_datetime": TARGET_DATETIME.isoformat(),
        "case_count": len(rows),
        "changed_case_count": sum(1 for r in rows if r["changed"]),
        "cases": rows,
    }
    out = ROOT / "docs" / "book_mode_golden_comparison.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    summary = main()
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"cases={summary['case_count']} changed={summary['changed_case_count']}")
    for row in summary["cases"]:
        print(row["case"], row["changed"] or "変化なし")
