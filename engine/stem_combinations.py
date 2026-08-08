"""
天干五合を検出するモジュール。

現在は以下の五合を対象とします。

甲・己 → 土
乙・庚 → 金
丙・辛 → 水
丁・壬 → 木
戊・癸 → 火

v1では干合の成立候補を検出します。

実際に化するかどうかは、
月令・季節・周囲の五行・根などを
考慮する必要があるため、
このモジュールではまだ判定しません。
"""


STEM_COMBINATION_PAIRS = {
    frozenset(("甲", "己")): {
        "name": "甲己",
        "element": "土",
    },
    frozenset(("乙", "庚")): {
        "name": "乙庚",
        "element": "金",
    },
    frozenset(("丙", "辛")): {
        "name": "丙辛",
        "element": "水",
    },
    frozenset(("丁", "壬")): {
        "name": "丁壬",
        "element": "木",
    },
    frozenset(("戊", "癸")): {
        "name": "戊癸",
        "element": "火",
    },
}


PILLAR_POSITIONS = (
    "year",
    "month",
    "day",
    "hour",
)


def is_stem_combination(
    stem_a: str,
    stem_b: str,
) -> bool:
    """
    2つの天干が五合の関係にあるかを判定します。
    """
    pair = frozenset(
        (
            stem_a,
            stem_b,
        )
    )

    return pair in STEM_COMBINATION_PAIRS


def get_stem_combination_info(
    stem_a: str,
    stem_b: str,
) -> dict | None:
    """
    2つの天干が五合を形成する場合、
    干合情報を返します。

    五合でない場合はNoneを返します。
    """
    pair = frozenset(
        (
            stem_a,
            stem_b,
        )
    )

    info = STEM_COMBINATION_PAIRS.get(
        pair
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


def find_stem_combinations(
    chart_data: dict,
) -> dict:
    """
    命式内の天干同士から五合を検出します。

    出生時間不明でhourがNoneの場合は、
    時柱を判定対象から除外します。

    v1では干合の存在のみを検出します。

    実際に化するかどうかは
    まだ判定しません。
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

            pillar_a = chart_data[
                position_a
            ]

            pillar_b = chart_data[
                position_b
            ]

            stem_a = pillar_a["stem"]
            stem_b = pillar_b["stem"]

            info = (
                get_stem_combination_info(
                    stem_a,
                    stem_b,
                )
            )

            if info is None:
                continue

            combinations.append(
                {
                    "position_a": position_a,
                    "stem_a": stem_a,
                    "position_b": position_b,
                    "stem_b": stem_b,
                    "relation": "干合",
                    "combination_name": (
                        info["name"]
                    ),
                    "result_element": (
                        info["element"]
                    ),
                    "transformation_status": (
                        "not_evaluated"
                    ),
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
        "method": "stem_combination_v1",
        "status": (
            "detected_stem_combinations"
        ),
        "notes": [
            (
                "命式内の天干同士から"
                "天干五合を検出しています。"
            ),
            (
                "甲己は土、乙庚は金、"
                "丙辛は水、丁壬は木、"
                "戊癸は火の候補として扱います。"
            ),
            (
                "現在は干合の存在のみを"
                "判定しています。"
            ),
            (
                "月令・季節・通根などを考慮した"
                "化の成立判定は未実装です。"
            ),
            (
                "干合による五行・身強身弱への"
                "補正はまだ行っていません。"
            ),
        ],
    }
