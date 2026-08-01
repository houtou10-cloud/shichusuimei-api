from engine.constants import (
    BRANCH_ELEMENTS,
    STEM_ELEMENTS,
)


FIVE_ELEMENTS = [
    "木",
    "火",
    "土",
    "金",
    "水",
]


def empty_element_counts() -> dict[str, int]:
    """
    五行をすべて0で初期化した辞書を返します。
    """
    return {
        element: 0
        for element in FIVE_ELEMENTS
    }


def get_stem_element(stem: str) -> str:
    """
    天干の五行を返します。
    """
    if stem not in STEM_ELEMENTS:
        raise ValueError(
            f"不正な天干です: {stem}"
        )

    return STEM_ELEMENTS[stem]["element"]


def get_branch_element(branch: str) -> str:
    """

    地支の五行を返します。

    地支の本来の五行を返します。

    """
    if branch not in BRANCH_ELEMENTS:
        raise ValueError(
            f"不正な地支です: {branch}"
        )

    return BRANCH_ELEMENTS[branch]


def count_pillar_elements(
    pillar_data: dict,
) -> dict[str, int]:
    """
    1柱に含まれる五行を単純集計します。

    集計対象：
    ・天干
    ・地支
    ・すべての蔵干
    """
    counts = empty_element_counts()

    stem = pillar_data["stem"]
    branch = pillar_data["branch"]
    hidden_stems = pillar_data["hidden_stems"]

    counts[get_stem_element(stem)] += 1
    counts[get_branch_element(branch)] += 1

    for hidden_stem in hidden_stems:
        counts[get_stem_element(hidden_stem)] += 1

    return counts


def calculate_five_elements(
    chart: dict,
) -> dict:
    """
    年柱・月柱・日柱・時柱に含まれる五行を
    単純集計します。
    """
    counts = empty_element_counts()

    for position in [
        "year",
        "month",
        "day",
        "hour",
    ]:
        pillar_data = chart.get(position)

        if pillar_data is None:
            continue

        pillar_counts = count_pillar_elements(
            pillar_data
        )

        for element in FIVE_ELEMENTS:
            counts[element] += pillar_counts[element]

    total = sum(counts.values())

    percentages = {
        element: (
            round(
                counts[element] / total * 100,
                2,
            )
            if total
            else 0.0
        )
        for element in FIVE_ELEMENTS
    }

    return {
        "method": "simple_count_v1",
        "counts": counts,
        "percentages": percentages,
        "total": total,
        "notes": [
            "天干・地支・蔵干を各1点として単純集計しています。",
            "月令、季節、通根、蔵干比率は未反映です。",
        ],
    }
