BRANCH_CLASH_PAIRS = {
    frozenset(("子", "午")),
    frozenset(("丑", "未")),
    frozenset(("寅", "申")),
    frozenset(("卯", "酉")),
    frozenset(("辰", "戌")),
    frozenset(("巳", "亥")),
}


BRANCH_COMBINATION_PAIRS = {
    frozenset(("子", "丑")),
    frozenset(("寅", "亥")),
    frozenset(("卯", "戌")),
    frozenset(("辰", "酉")),
    frozenset(("巳", "申")),
    frozenset(("午", "未")),
}


BRANCH_TRINE_GROUPS = {
    frozenset(("申", "子", "辰")): {
        "element": "水",
        "name": "申子辰",
    },
    frozenset(("亥", "卯", "未")): {
        "element": "木",
        "name": "亥卯未",
    },
    frozenset(("寅", "午", "戌")): {
        "element": "火",
        "name": "寅午戌",
    },
    frozenset(("巳", "酉", "丑")): {
        "element": "金",
        "name": "巳酉丑",
    },
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


def is_branch_combination(
    branch_a: str,
    branch_b: str,
) -> bool:
    """
    2つの地支が六合の関係にあるかを判定します。
    """
    pair = frozenset(
        (
            branch_a,
            branch_b,
        )
    )

    return pair in BRANCH_COMBINATION_PAIRS


def is_branch_trine(
    branch_a: str,
    branch_b: str,
    branch_c: str,
) -> bool:
    """
    3つの地支が三合の関係にあるかを判定します。
    """
    group = frozenset(
        (
            branch_a,
            branch_b,
            branch_c,
        )
    )

    return group in BRANCH_TRINE_GROUPS


def get_branch_trine_info(
    branch_a: str,
    branch_b: str,
    branch_c: str,
) -> dict | None:
    """
    3つの地支が三合を形成する場合、
    三合局の情報を返します。

    三合でない場合はNoneを返します。
    """
    group = frozenset(
        (
            branch_a,
            branch_b,
            branch_c,
        )
    )

    info = BRANCH_TRINE_GROUPS.get(
        group
    )

    if info is None:
        return None

    return {
        "name": info["name"],
        "element": info["element"],
    }


def get_available_positions(
    chart_data: dict,
) -> list[str]:
    """
    命式内で利用可能な柱位置を返します。

    出生時間不明でhourがNoneの場合は、
    時柱を除外します。
    """
    return [
        position
        for position in PILLAR_POSITIONS
        if chart_data.get(position) is not None
    ]


def find_branch_clashes(
    chart_data: dict,
) -> dict:
    """
    命式内の地支同士から六冲を検出します。

    出生時間不明でhourがNoneの場合は、
    時柱を判定対象から除外します。
    """
    available_positions = (
        get_available_positions(
            chart_data
        )
    )

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


def find_branch_combinations(
    chart_data: dict,
) -> dict:
    """
    命式内の地支同士から六合を検出します。

    出生時間不明でhourがNoneの場合は、
    時柱を判定対象から除外します。
    """
    available_positions = (
        get_available_positions(
            chart_data
        )
    )

    combinations: list[dict] = []

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

            if not is_branch_combination(
                branch_a,
                branch_b,
            ):
                continue

            combinations.append(
                {
                    "position_a": position_a,
                    "branch_a": branch_a,
                    "position_b": position_b,
                    "branch_b": branch_b,
                    "relation": "六合",
                }
            )

    return {
        "has_combination": bool(
            combinations
        ),
        "combination_count": len(
            combinations
        ),
        "combinations": combinations,
        "method": (
            "branch_combination_v1"
        ),
        "status": (
            "detected_branch_combinations"
        ),
        "notes": [
            "命式内の地支同士から六合を検出しています。",
            "現在は六合の有無のみを判定しています。",
            "六合による五行・通根への影響度は未反映です。",
        ],
    }


def find_branch_trines(
    chart_data: dict,
) -> dict:
    """
    命式内の地支から三合を検出します。

    三合四局：
    申・子・辰 → 水局
    亥・卯・未 → 木局
    寅・午・戌 → 火局
    巳・酉・丑 → 金局

    出生時間不明でhourがNoneの場合は、
    時柱を判定対象から除外します。
    """
    available_positions = (
        get_available_positions(
            chart_data
        )
    )

    trines: list[dict] = []

    position_count = len(
        available_positions
    )

    for index_a in range(
        position_count
    ):
        for index_b in range(
            index_a + 1,
            position_count,
        ):
            for index_c in range(
                index_b + 1,
                position_count,
            ):
                position_a = (
                    available_positions[index_a]
                )

                position_b = (
                    available_positions[index_b]
                )

                position_c = (
                    available_positions[index_c]
                )

                branch_a = chart_data[
                    position_a
                ]["branch"]

                branch_b = chart_data[
                    position_b
                ]["branch"]

                branch_c = chart_data[
                    position_c
                ]["branch"]

                trine_info = (
                    get_branch_trine_info(
                        branch_a,
                        branch_b,
                        branch_c,
                    )
                )

                if trine_info is None:
                    continue

                trines.append(
                    {
                        "position_a": position_a,
                        "branch_a": branch_a,
                        "position_b": position_b,
                        "branch_b": branch_b,
                        "position_c": position_c,
                        "branch_c": branch_c,
                        "relation": "三合",
                        "trine_name": (
                            trine_info["name"]
                        ),
                        "element": (
                            trine_info["element"]
                        ),
                    }
                )

    return {
        "has_trine": bool(trines),
        "trine_count": len(trines),
        "trines": trines,
        "method": "branch_trine_v1",
        "status": "detected_branch_trines",
        "notes": [
            "命式内の3つの地支から三合を検出しています。",
            "申子辰は水局として判定します。",
            "亥卯未は木局として判定します。",
            "寅午戌は火局として判定します。",
            "巳酉丑は金局として判定します。",
            "現在は完全な三合のみを判定しています。",
            "半会・拱合はまだ判定していません。",
            "三合による五行強弱への補正は未反映です。",
        ],
    }
