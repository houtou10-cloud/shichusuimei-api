from engine.constants import (
    STEM_ELEMENTS,
    STEMS,
)


PILLAR_POSITIONS = [
    "year",
    "month",
    "day",
    "hour",
]


def get_stem_element(
    stem: str,
) -> str:
    """
    天干の五行を返します。
    """
    if stem not in STEMS:
        raise ValueError(
            f"不正な天干です: {stem}"
        )

    return STEM_ELEMENTS[stem]["element"]


def find_roots(
    day_stem: str,
    chart: dict,
) -> dict:
    """
    日主と同じ五行を持つ蔵干を探し、
    通根状況を返します。

    現在は単純版です。
    蔵干の強弱、月令、余気・中気・本気の
    重み付けはまだ行いません。
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

        matching_stems = [
            hidden_stem
            for hidden_stem in hidden_stems
            if get_stem_element(
                hidden_stem
            ) == day_element
        ]

        if matching_stems:
            roots.append(
                {
                    "position": position,
                    "branch": branch,
                    "root_stems": matching_stems,
                    "root_count": len(
                        matching_stems
                    ),
                }
            )

    root_count = sum(
        root["root_count"]
        for root in roots
    )

    return {
        "day_stem": day_stem,
        "day_element": day_element,
        "has_root": root_count > 0,
        "root_count": root_count,
        "root_positions": [
            root["position"]
            for root in roots
        ],
        "roots": roots,
        "method": "hidden_stem_root_v1",
        "status": "simple_root_detection",
        "notes": [
            "地支の蔵干に日主と同じ五行があるかを判定しています。",
            "本気・中気・余気の重み付けは未反映です。",
            "月支の根を特別に強く評価する処理は未実装です。",
        ],
    }
