from engine.five_elements import get_stem_element
from engine.hidden_stem_weights import (
    get_hidden_stem_weights,
)


POSITION_WEIGHTS = {
    "year": 0.8,
    "month": 1.5,
    "day": 1.3,
    "hour": 1.0,
}


PILLAR_POSITIONS = [
    "year",
    "month",
    "day",
    "hour",
]


def calculate_weighted_roots(
    day_stem: str,
    chart: dict,
) -> dict:
    """
    日主と同じ五行を持つ蔵干を探し、
    柱の位置と蔵干比率を使って
    通根の強さを計算します。
    """
    day_element = get_stem_element(
        day_stem
    )

    roots: list[dict] = []

    for position in PILLAR_POSITIONS:
        pillar_data = chart.get(position)

        if pillar_data is None:
            continue

        branch = pillar_data["branch"]
        hidden_stems = pillar_data.get(
            "hidden_stems",
            [],
        )

        weighted_hidden_stems = (
            get_hidden_stem_weights(
                hidden_stems
            )
        )

        position_weight = POSITION_WEIGHTS[
            position
        ]

        for hidden_stem_data in weighted_hidden_stems:
            hidden_stem = hidden_stem_data[
                "stem"
            ]

            hidden_element = get_stem_element(
                hidden_stem
            )

            if hidden_element != day_element:
                continue

            hidden_stem_weight = (
                hidden_stem_data["weight"]
            )

            root_score = round(
                position_weight
                * hidden_stem_weight,
                2,
            )

            roots.append(
                {
                    "position": position,
                    "branch": branch,
                    "stem": hidden_stem,
                    "hidden_stem_rank": (
                        hidden_stem_data["rank"]
                    ),
                    "position_weight": (
                        position_weight
                    ),
                    "hidden_stem_weight": (
                        hidden_stem_weight
                    ),
                    "root_score": root_score,
                }
            )

    total_root_score = round(
        sum(
            root["root_score"]
            for root in roots
        ),
        2,
    )

    return {
        "day_stem": day_stem,
        "day_element": day_element,
        "has_root": bool(roots),
        "root_count": len(roots),
        "total_root_score": total_root_score,
        "root_positions": [
            root["position"]
            for root in roots
        ],
        "roots": roots,
        "method": "weighted_root_strength_v1",
        "status": "provisional_weighted_roots",
        "notes": [
            "柱の位置と蔵干比率を使って通根を評価しています。",
            "位置別の重みは暫定値です。",
            "合・冲・刑・害による根の変化は未反映です。",
        ],
    }
