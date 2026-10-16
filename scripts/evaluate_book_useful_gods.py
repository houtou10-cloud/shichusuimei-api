"""応用編の例題で、用神の第一候補が本の用神と合うかを測る研究用スクリプト。

使い方: python scripts/evaluate_book_useful_gods.py
刻は2時間の時間帯の代表時刻に置き換える（子刻は命式の時柱に合う方を選ぶ）。
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

STEM_ELEMENT = {"甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土", "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水"}
KOKU_TIME = {"丑": "02:00", "寅": "04:00", "卯": "06:00", "辰": "08:00", "巳": "10:00", "午": "12:00",
             "未": "14:00", "申": "16:00", "酉": "18:00", "戌": "20:00", "亥": "22:00"}
TARGET = datetime(2026, 1, 1, 12, 0)
POSITIONS = ("year", "month", "day", "hour")


def _chart(example: dict, time: str, rule_set: str | None) -> dict:
    req = ChartRequest(birth_date=example["birth_date"], birth_time=time, birth_place="東京都", gender="male")
    return calculate_chart(req, target_datetime=TARGET, rule_set=rule_set)


def _pillars(chart: dict) -> list[str]:
    return [chart["chart"][p]["pillar"] for p in POSITIONS]


def evaluate(rule_set: str | None) -> dict:
    data = json.loads((ROOT / "tests/fixtures/book_examples/oyo_useful_gods.json").read_text(encoding="utf-8"))
    rows = []
    for ex in data["examples"]:
        if ex["koku"] == "子":
            candidates = [_chart(ex, t, rule_set) for t in ("00:30", "23:30")]
            chart = next((c for c in candidates if _pillars(c) == ex["book_pillars"]), candidates[0])
        else:
            chart = _chart(ex, KOKU_TIME[ex["koku"]], rule_set)
        book_elements = [STEM_ELEMENT[s] for s in ex["useful_stems"]]
        ug = chart["useful_gods"]
        primary = ug.get("primary_useful_element")
        rows.append({
            "source": ex["source"],
            "pillars_match": _pillars(chart) == ex["book_pillars"],
            "book_first": book_elements[0],
            "book_set": sorted(set(book_elements)),
            "primary": primary,
            "final": ug.get("final_useful_elements"),
            "top1_in_book_set": primary in book_elements,
            "top1_is_book_first": primary == book_elements[0],
            "strength": chart["final_strength_judgment"].get("label"),
            "pattern": chart["pattern_judgment"].get("primary_pattern"),
        })
    valid = [r for r in rows if r["pillars_match"]]
    return {
        "rule_set": rule_set or "engine_v1",
        "examples": len(rows),
        "pillars_match": len(valid),
        "top1_in_book_set": sum(r["top1_in_book_set"] for r in valid),
        "top1_is_book_first": sum(r["top1_is_book_first"] for r in valid),
        "rows": rows,
    }


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    results = [evaluate(None), evaluate("book_kiso")]
    for r in results:
        print(f"{r['rule_set']}: 命式一致 {r['pillars_match']}/{r['examples']}  第一候補が本の用神に含まれる {r['top1_in_book_set']}  本の第一用神と一致 {r['top1_is_book_first']}")
    (ROOT / "docs/book_useful_god_evaluation.json").write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
