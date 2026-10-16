"""本番エンジンと『四柱推命 基礎』の手順の食い違いを数える研究用スクリプト。

使い方: python scripts/compare_book_vs_engine.py [件数]
本番エンジンは呼び出すだけで変更しない。
"""

from __future__ import annotations

import json
import random
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.pillars import calculate_four_pillars  # noqa: E402
from scripts.book_method_rules import (  # noqa: E402
    book_hidden_stems_for_chart,
    book_hour_pillar,
    in_summer_time,
)


def main(samples: int = 4000, seed: int = 20261016) -> dict:
    rng = random.Random(seed)
    start = datetime(1930, 1, 1)
    span_minutes = int((datetime(2030, 1, 1) - start).total_seconds() // 60)
    counts: Counter[str] = Counter()
    by_position: Counter[str] = Counter()
    for _ in range(samples):
        birth = start + timedelta(minutes=rng.randrange(span_minutes))
        engine = calculate_four_pillars(birth)
        counts["total"] += 1
        book_hour = book_hour_pillar(engine["day"]["stem"], birth)
        if book_hour.status == "hold":
            counts["hour_hold"] += 1
        elif book_hour.value != engine["hour"]["pillar"]:
            counts["hour_diff"] += 1
            if birth.hour == 23:
                counts["hour_diff_late_zi"] += 1
            elif in_summer_time(birth):
                counts["hour_diff_summer_time"] += 1
            else:
                counts["hour_diff_exact_boundary"] += 1
        branches = {p: engine[p]["branch"] for p in ("year", "month", "day", "hour")}
        book_stems = book_hidden_stems_for_chart(birth, branches)
        any_diff = False
        for position, result in book_stems.items():
            if result.value != engine[position]["main_hidden_stem"]:
                by_position[position] += 1
                any_diff = True
        if any_diff:
            counts["hidden_stem_any_diff"] += 1
        if book_stems["month"].value != engine["month"]["main_hidden_stem"]:
            counts["month_hidden_stem_diff"] += 1
    total = counts["total"]
    summary = {
        "samples": total,
        "range": "1930-01-01〜2029-12-31（分単位の一様乱数、seed=%d）" % seed,
        "hour_pillar_diff_rate": round(counts["hour_diff"] / total, 4),
        "hour_pillar_diff_breakdown": {
            "late_zi_23h": counts["hour_diff_late_zi"],
            "summer_time": counts["hour_diff_summer_time"],
            "exact_boundary": counts["hour_diff_exact_boundary"],
        },
        "hour_pillar_hold": counts["hour_hold"],
        "hidden_stem_any_position_diff_rate": round(counts["hidden_stem_any_diff"] / total, 4),
        "month_hidden_stem_diff_rate": round(counts["month_hidden_stem_diff"] / total, 4),
        "hidden_stem_diff_by_position": dict(by_position),
    }
    return summary


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 4000
    print(json.dumps(main(n), ensure_ascii=False, indent=2))
