from engine.day_master_strength import (
    get_day_master_element,
)
from engine.five_elements import (
    get_stem_element,
)
from engine.hidden_stem_weights import (
    get_hidden_stem_weights,
)


def calculate_weighted_month_command(
    day_stem: str,
    month_pillar: dict,
) -> dict:
    """
    月支の蔵干構成を使い、
    日主を支える割合と弱める割合を計算します。
    """
    day_element = get_day_master_element(
        day_stem
    )

    hidden_stems = month_pillar[
        "hidden_stems"
    ]

    weighted_hidden_stems = (
        get_hidden_stem_weights(
            hidden_stems
        )
    )

    supporting_score = 0.0
    draining_score = 0.0
    details: list[dict] = []

    supporting_elements = {
        day_element,
    }

    resource_elements = {
        "木": "水",
        "火": "木",
        "土": "火",
        "金": "土",
        "水": "金",
    }

    supporting_elements.add(
        resource_elements[day_element]
    )

    for item in weighted_hidden_stems:
        stem = item["stem"]
        weight = float(item["weight"])

        element = get_stem_element(
            stem
        )

        supports_day_master = (
            element in supporting_elements
        )

        if supports_day_master:
            supporting_score += weight
        else:
            draining_score += weight

        details.append(
            {
                "stem": stem,
                "element": element,
                "weight": weight,
                "supports_day_master": (
                    supports_day_master
                ),
            }
        )

    supporting_score = round(
        supporting_score,
        2,
    )

    draining_score = round(
        draining_score,
        2,
    )

    total = round(
        supporting_score + draining_score,
        2,
    )

    supporting_ratio = (
        round(
            supporting_score / total * 100,
            2,
        )
        if total
        else 0.0
    )

    draining_ratio = (
        round(
            draining_score / total * 100,
            2,
        )
        if total
        else 0.0
    )

    return {
        "day_stem": day_stem,
        "day_element": day_element,
        "month_branch": month_pillar[
            "branch"
        ],
        "supporting_score": (
            supporting_score
        ),
        "draining_score": (
            draining_score
        ),
        "supporting_ratio": (
            supporting_ratio
        ),
        "draining_ratio": (
            draining_ratio
        ),
        "details": details,
        "method": (
            "weighted_month_command_v1"
        ),
        "status": (
            "provisional_weighted_month_command"
        ),
        "notes": [
            "月支蔵干の比率を使って評価しています。",
            "日主と同じ五行・日主を生じる五行を支援側としています。",
            "土用期間と節入り後の日数は未反映です。",
        ],
    }
