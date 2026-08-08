BRANCH_CLASH_PAIRS = {
    frozenset(("子", "午")),
    frozenset(("丑", "未")),
    frozenset(("寅", "申")),
    frozenset(("卯", "酉")),
    frozenset(("辰", "戌")),
    frozenset(("巳", "亥")),
}


PILLAR_POSITIONS = (
    "year",
    "month",
    "day",
    "hour",
)


def is_branch_clash(
    branch_a: str,
    branch_b: str,
) -> bool:
    """
    2つの地支が六冲の関係にあるかを判定します。
    """
    pair = frozenset(
        (
            branch_a,
            branch_b,
        )
    )

    return pair in BRANCH_CLASH_PAIRS


def find_branch_clashes(
    chart_data: dict,
) -> dict:
    """
    命式内の地支同士から六冲を検出します。

    出生時間不明でhourがNoneの場合は、
    時柱を判定対象から除外します。
    """
    available_positions = [
        position
        for position in PILLAR_POSITIONS
        if chart_data.get(position) is not None
    ]

    clashes: list[dict] = []

    for index_a in range(
        len(available_positions)
    ):
        for index_b in range(
            index_a + 1,
            len(available_positions),
        ):
            position_a = (
                available_positions[index_a]
            )

            position_b = (
                available_positions[index_b]
            )

            pillar_a = chart_data[position_a]
            pillar_b = chart_data[position_b]

            branch_a = pillar_a["branch"]
            branch_b = pillar_b["branch"]

            if not is_branch_clash(
                branch_a,
                branch_b,
            ):
                continue

            clashes.append(
                {
                    "position_a": position_a,
                    "branch_a": branch_a,
                    "position_b": position_b,
                    "branch_b": branch_b,
                    "relation": "冲",
                }
            )

    return {
        "has_clash": bool(clashes),
        "clash_count": len(clashes),
        "clashes": clashes,
        "method": "branch_clash_v1",
        "status": "detected_branch_clashes",
        "notes": [
            "命式内の地支同士から六冲を検出しています。",
            "現在は六冲の有無のみを判定しています。",
            "冲による五行・通根への影響度は未反映です。",
        ],
    }
