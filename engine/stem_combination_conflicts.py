"""
天干五合の競合状態を検出するモジュール。

主な対象:

- 同一の柱位置が複数の干合候補へ参加している
- 同一の天干が複数の相手と干合候補になっている

v1では、
競合状態を検出して情報化するだけです。

争合・妬合などの最終的な占術判断は、
後段の総合判定モジュールで扱います。
"""


PILLAR_POSITIONS = (
    "year",
    "month",
    "day",
    "hour",
)


def validate_stem_combinations(
    stem_combinations: dict,
) -> list[dict]:
    """
    stem_combinationsから
    combinations一覧を安全に取得します。
    """
    if not isinstance(
        stem_combinations,
        dict,
    ):
        raise TypeError(
            "stem_combinationsはdict型で指定してください。"
        )

    combinations = (
        stem_combinations.get(
            "combinations",
            [],
        )
    )

    if not isinstance(
        combinations,
        list,
    ):
        raise TypeError(
            "combinationsはlist型で指定してください。"
        )

    return combinations


def get_combination_positions(
    combination: dict,
) -> tuple[str | None, str | None]:
    """
    1件の干合候補から、
    参加している2つの柱位置を返します。
    """
    if not isinstance(
        combination,
        dict,
    ):
        raise TypeError(
            "combinationはdict型で指定してください。"
        )

    position_a = (
        combination.get(
            "position_a"
        )
    )

    position_b = (
        combination.get(
            "position_b"
        )
    )

    return (
        position_a,
        position_b,
    )


def build_position_usage(
    combinations: list[dict],
) -> dict[str, list[dict]]:
    """
    各柱位置が、
    どの干合候補に参加しているかを
    集計します。
    """
    usage: dict[str, list[dict]] = {
        position: []
        for position in PILLAR_POSITIONS
    }

    for combination in combinations:
        if not isinstance(
            combination,
            dict,
        ):
            raise TypeError(
                "combinationはdict型で指定してください。"
            )

        position_a = (
            combination.get(
                "position_a"
            )
        )

        position_b = (
            combination.get(
                "position_b"
            )
        )

        if position_a is not None:
            if (
                position_a
                not in PILLAR_POSITIONS
            ):
                raise ValueError(
                    "不正なpositionです: "
                    f"{position_a}"
                )

            usage[
                position_a
            ].append(
                combination
            )

        if position_b is not None:
            if (
                position_b
                not in PILLAR_POSITIONS
            ):
                raise ValueError(
                    "不正なpositionです: "
                    f"{position_b}"
                )

            usage[
                position_b
            ].append(
                combination
            )

    return usage


def find_position_conflicts(
    combinations: list[dict],
    chart_data: dict | None = None,
) -> list[dict]:
    """
    同一の柱位置が複数の干合候補に
    参加している状態を検出します。
    """
    usage = build_position_usage(
        combinations
    )

    conflicts: list[dict] = []

    for position in PILLAR_POSITIONS:
        related = usage[
            position
        ]

        if len(
            related
        ) <= 1:
            continue

        stem = None

        if (
            isinstance(
                chart_data,
                dict,
            )
            and isinstance(
                chart_data.get(
                    position
                ),
                dict,
            )
        ):
            stem = chart_data[
                position
            ].get(
                "stem"
            )

        combination_names = [
            item.get(
                "combination_name"
            )
            for item in related
        ]

        partner_positions: list[str] = []

        for item in related:
            position_a = (
                item.get(
                    "position_a"
                )
            )

            position_b = (
                item.get(
                    "position_b"
                )
            )

            if (
                position_a
                == position
                and position_b
                is not None
            ):
                partner_positions.append(
                    position_b
                )

            elif (
                position_b
                == position
                and position_a
                is not None
            ):
                partner_positions.append(
                    position_a
                )

        conflicts.append(
            {
                "position": position,
                "stem": stem,
                "combination_count": (
                    len(
                        related
                    )
                ),
                "combination_names": (
                    combination_names
                ),
                "partner_positions": (
                    partner_positions
                ),
                "conflict_type": (
                    "competing_combination"
                ),
            }
        )

    return conflicts


def find_duplicate_combination_names(
    combinations: list[dict],
) -> list[dict]:
    """
    同じcombination_nameが
    複数回出現している状態を検出します。

    例:
    甲・己・己 のような命式では、
    甲己という組み合わせ候補が
    複数生じる可能性があります。
    """
    grouped: dict[str, list[dict]] = {}

    for combination in combinations:
        if not isinstance(
            combination,
            dict,
        ):
            raise TypeError(
                "combinationはdict型で指定してください。"
            )

        combination_name = (
            combination.get(
                "combination_name"
            )
        )

        if combination_name is None:
            continue

        grouped.setdefault(
            combination_name,
            [],
        ).append(
            combination
        )

    duplicates: list[dict] = []

    for (
        combination_name,
        related,
    ) in grouped.items():
        if len(
            related
        ) <= 1:
            continue

        duplicates.append(
            {
                "combination_name": (
                    combination_name
                ),
                "combination_count": (
                    len(
                        related
                    )
                ),
                "pairs": [
                    {
                        "position_a": (
                            item.get(
                                "position_a"
                            )
                        ),
                        "stem_a": (
                            item.get(
                                "stem_a"
                            )
                        ),
                        "position_b": (
                            item.get(
                                "position_b"
                            )
                        ),
                        "stem_b": (
                            item.get(
                                "stem_b"
                            )
                        ),
                    }
                    for item in related
                ],
                "conflict_type": (
                    "duplicated_combination"
                ),
            }
        )

    return duplicates


def evaluate_stem_combination_conflicts(
    stem_combinations: dict,
    chart_data: dict | None = None,
) -> dict:
    """
    天干五合候補について、
    競合状態をまとめて評価します。

    v1では、

    - 同一positionの複数干合
    - 同一combination_nameの複数出現

    を検出します。
    """
    combinations = (
        validate_stem_combinations(
            stem_combinations
        )
    )

    if (
        chart_data is not None
        and not isinstance(
            chart_data,
            dict,
        )
    ):
        raise TypeError(
            "chart_dataはdict型またはNoneで指定してください。"
        )

    position_conflicts = (
        find_position_conflicts(
            combinations,
            chart_data,
        )
    )

    duplicate_combinations = (
        find_duplicate_combination_names(
            combinations
        )
    )

    conflict_count = (
        len(
            position_conflicts
        )
        + len(
            duplicate_combinations
        )
    )

    has_conflict = (
        conflict_count > 0
    )

    if not combinations:
        overall_status = (
            "not_applicable"
        )

    elif has_conflict:
        overall_status = (
            "conflicted"
        )

    else:
        overall_status = (
            "clear"
        )

    return {
        "has_stem_combination": bool(
            combinations
        ),
        "combination_count": len(
            combinations
        ),
        "has_conflict": (
            has_conflict
        ),
        "conflict_count": (
            conflict_count
        ),
        "position_conflict_count": (
            len(
                position_conflicts
            )
        ),
        "duplicate_combination_count": (
            len(
                duplicate_combinations
            )
        ),
        "position_conflicts": (
            position_conflicts
        ),
        "duplicate_combinations": (
            duplicate_combinations
        ),
        "overall_status": (
            overall_status
        ),
        "method": (
            "stem_combination_conflict_v1"
        ),
        "status": (
            "detected_stem_combination_conflicts"
        ),
        "notes": [
            (
                "同一の柱位置が複数の干合候補へ"
                "参加している状態を検出しています。"
            ),
            (
                "同じ干合名称が複数回現れる状態も"
                "重複候補として検出しています。"
            ),
            (
                "現在は競合状態の検出のみで、"
                "争合・妬合の最終的な成立判定は"
                "行っていません。"
            ),
            (
                "競合を理由に干合や化を"
                "自動的に不成立にはしていません。"
            ),
            (
                "後段の干合化総合判定で"
                "減点・制限要因として"
                "利用する予定です。"
            ),
        ],
    }
