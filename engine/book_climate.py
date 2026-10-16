"""『四柱推命』応用編p.210の調候表による調候用神（本どおりモード）。

表は日干×月支ごとに必要な干を示す。各マスの先頭が大字（最も重視される干）、
続く干が小字（補助）。大字がなく四字すべてが小字のマスがあり、その場合は
一番手が本から決まらないため status="hold" とする。

原典の表は「参考にして」命式に必要な五行を考えるもの（p.210本文）。
engine/chart.py の rule_set="book_kiso" から使う。既定の計算には影響しない。
"""

from __future__ import annotations

from typing import Any

STEM_ELEMENT = {"甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土", "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水"}
_MONTHS = "寅卯辰巳午未申酉戌亥子丑"

# 応用編p.210（全120マスを原典画像と照合済み）。月の順は寅〜丑。
_TABLE = {
    "甲": ("丙癸", "庚丁己", "庚丁壬", "癸庚丁", "癸庚丁", "癸庚丁", "庚壬丁", "庚丙丁", "庚甲丁壬癸", "庚丙戊丁", "丁庚戊丙", "丁庚丙"),
    "乙": ("丙癸", "丙癸", "癸丙", "癸辛", "癸丙辛", "癸丙辛", "丙癸己", "丙丁癸", "丙癸辛", "丙戊", "丙", "丙"),
    "丙": ("壬", "壬己辛庚", "壬甲庚", "壬庚癸", "壬庚", "壬庚", "壬戊", "壬癸", "甲壬", "甲壬戊", "壬戊甲己", "壬甲"),
    "丁": ("甲庚", "庚甲", "甲庚", "甲庚", "壬庚癸", "甲庚壬", "甲庚丙戊", "甲庚丙戊", "甲庚", "甲庚", "甲庚", "甲庚"),
    "戊": ("丙甲癸", "丙甲癸", "甲丙癸", "甲丙癸", "壬丙甲", "癸丙甲", "丙甲癸", "丙癸", "甲癸丙", "丙甲", "丙甲", "丙甲"),
    "己": ("丙癸甲", "甲癸丙", "丙癸甲", "癸丙", "癸丙", "癸丙", "丙癸", "丙癸", "甲丙癸", "丙甲戊", "丙甲戊", "丙甲戊"),
    "庚": ("戊丙甲", "丁甲", "甲丁", "壬丙戊丁", "壬癸", "丁甲", "丁甲", "丁甲丙", "甲壬丁", "丁丙甲", "丁丙甲", "丙丁甲"),
    "辛": ("己壬庚", "壬甲己", "壬甲", "壬癸甲", "壬癸甲己", "壬庚甲", "壬甲", "壬甲", "壬甲", "壬丙", "丙壬甲戊", "丙壬甲戊"),
    "壬": ("庚丙戊", "戊辛庚", "甲庚", "壬庚癸辛", "癸庚辛", "辛甲癸", "戊丁", "甲庚", "甲丙", "戊丙庚", "戊丙", "丙丁甲"),
    "癸": ("辛丙", "庚辛", "丙辛甲", "辛壬庚", "庚壬癸辛", "庚壬癸辛", "丁甲", "辛丙", "辛壬癸甲", "庚丁戊辛", "丙辛", "丙丁"),
}

# 大字がなく、四字すべてが小字のマス（原典画像で確認）
_NO_MAJOR = {
    ("甲", "亥"), ("甲", "子"), ("丙", "卯"), ("丙", "子"), ("丁", "申"), ("丁", "酉"), ("庚", "巳"), ("辛", "午"),
    ("辛", "子"), ("辛", "丑"), ("壬", "巳"), ("癸", "午"), ("癸", "未"), ("癸", "戌"), ("癸", "亥"),
}


def chokou_stems(day_stem: str, month_branch: str) -> tuple[str, bool]:
    """(マスの干の並び, 大字があるか) を返す。"""
    cell = _TABLE[day_stem][_MONTHS.index(month_branch)]
    return cell, (day_stem, month_branch) not in _NO_MAJOR


def book_climate_useful_gods(engine_result: dict[str, Any], day_stem: str, month_branch: str) -> dict[str, Any]:
    """既存の climate_useful_gods と同じ主要キーで、調候表の結果を返す。"""
    stems, has_major = chokou_stems(day_stem, month_branch)
    elements: list[str] = []
    for stem in stems:
        element = STEM_ELEMENT[stem]
        if element not in elements:
            elements.append(element)
    candidates = [
        {
            "element": element,
            "priority": index + 1,
            "stems": [s for s in stems if STEM_ELEMENT[s] == element],
            "is_major": has_major and STEM_ELEMENT[stems[0]] == element,
            "climate_score": None,
        }
        for index, element in enumerate(elements)
    ]
    notes = []
    status = "ok"
    if not has_major:
        status = "hold"
        notes.append("調候表のこのマスは四字すべて小字で大字がなく、一番手が本から決まらない。並びは転記順")
    result = dict(engine_result)
    result.update(
        {
            "book_method": "book_oyo_p210_chokou_table",
            "has_climate_candidate": bool(elements),
            "primary_climate_element": elements[0] if elements else None,
            "secondary_climate_elements": elements[1:],
            "climate_elements": elements,
            "climate_candidates": candidates,
            "book_chokou_stems": stems,
            "book_has_major_stem": has_major,
            "book_status": status,
            "book_notes": notes,
        }
    )
    return result
