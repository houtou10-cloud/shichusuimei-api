from engine.five_elements import (
    FIVE_ELEMENTS,
    get_stem_element,
)
from engine.hidden_stem_weights import (
    get_hidden_stem_weights,
)


PILLAR_POSITIONS = [
    "year",
    "month",
    "day",
    "hour",
]


def empty_weighted_scores() -> dict[str, float]:
    """
    五行スコアを0.0で初期化します。
    """
    return {
        element: 0.0
        for element in FIVE_ELEMENTS
    }


def calculate_weighted_pillar_elements(
    pillar_data: dict,
) -> dict[str, float]:
    """
    1柱の五行を重み付きで集計します。

    ・天干：1.0点
    ・地支：蔵干全体で合計1.0点

    地支自体は別に加算せず、
    蔵干によって地支の五行構成を表現します。
    """
    scores = empty_weighted_scores()

    stem = pillar_data["stem"]
    hidden_stems = pillar_data[
        "hidden_stems"
    ]

    stem_element = get_stem_element(
        stem
    )

    scores[stem_element] += 1.0

    weighted_hidden_stems = (
        get_hidden_stem_weights(
            hidden_stems
        )
    )

    for item in weighted_hidden_stems:
        hidden_element = get_stem_element(
            item["stem"]
        )

        scores[hidden_element] += item[
            "weight"
        ]

    return scores


def calculate_weighted_five_elements(
    chart: dict,
) -> dict:
    """
    四柱の五行を重み付きで集計します。

    4つの天干で合計4点、
    4つの地支で合計4点となるため、
    出生時間がある場合の総点は8点です。
    """
    scores = empty_weighted_scores()

    pillar_details: dict = {}

    for position in PILLAR_POSITIONS:
        pillar_data = chart.get(position)

        if pillar_data is None:
            continue

        pillar_scores = (
            calculate_weighted_pillar_elements(
                pillar_data
            )
        )

        pillar_details[position] = (
            pillar_scores
        )

        for element in FIVE_ELEMENTS:
            scores[element] += (
                pillar_scores[element]
            )

    rounded_scores = {
        element: round(
            scores[element],
            2,
        )
        for element in FIVE_ELEMENTS
    }

    total = round(
        sum(rounded_scores.values()),
        2,
    )

    percentages = {
        element: (
            round(
                rounded_scores[element]
                / total
                * 100,
                2,
            )
            if total
            else 0.0
        )
        for element in FIVE_ELEMENTS
    }

    return {
        "method": (
            "weighted_hidden_stems_v1"
        ),
        "scores": rounded_scores,
        "percentages": percentages,
        "total": total,
        "pillar_details": (
            pillar_details
        ),
        "status": "provisional_weights",
        "notes": [
            "天干を各1.0点として集計しています。",
            "各地支は蔵干全体で合計1.0点として集計しています。",
            "蔵干比率は暫定値であり、流派に応じた調整が必要です。",
            "月令と季節旺衰はまだ反映していません。",
        ],
    }
