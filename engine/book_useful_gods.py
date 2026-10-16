"""本どおりモードの用神（よい五行）。

応用編p.210は、調候表を「参考にして」命式に必要な五行を考えるよう述べている。
応用編p.211〜263の例題51件（命式が一致した47件）では、調候表の一番手の五行が
本の用神に含まれる例が45件、本の第一用神と一致する例が39件あった
（scripts/evaluate_book_useful_gods.py）。このため、調候表の並び（大字→小字）を
用神の候補順とする。従来の点数の仕組みの結果は engine_v1_useful_gods に残す。

大字のない調候表のマスは一番手が本から決まらないため confidence を下げる。
"""

from __future__ import annotations

from typing import Any


def book_useful_gods(engine_useful_gods: dict[str, Any], book_climate: dict[str, Any]) -> dict[str, Any]:
    elements = list(book_climate.get("climate_elements") or [])
    if not elements:
        return engine_useful_gods
    engine_candidates = {
        c.get("element"): c for c in engine_useful_gods.get("final_candidates") or [] if isinstance(c, dict)
    }
    candidates = []
    for index, element in enumerate(elements):
        base = dict(engine_candidates.get(element, {"element": element}))
        base.update({"element": element, "priority": index + 1, "book_source": "oyo_p210_chokou_table"})
        candidates.append(base)
    has_major = bool(book_climate.get("book_has_major_stem", True))
    result = dict(engine_useful_gods)
    result.update(
        {
            "book_method": "book_oyo_p210_chokou_order",
            "has_useful_candidate": True,
            "primary_useful_element": elements[0],
            "secondary_useful_elements": elements[1:],
            "final_useful_elements": elements,
            "final_candidates": candidates,
            "confidence": "medium" if not has_major else engine_useful_gods.get("confidence", "high"),
            "book_chokou_stems": book_climate.get("book_chokou_stems"),
            "engine_v1_useful_gods": {
                "primary_useful_element": engine_useful_gods.get("primary_useful_element"),
                "final_useful_elements": engine_useful_gods.get("final_useful_elements"),
            },
        }
    )
    return result
