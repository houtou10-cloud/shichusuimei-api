"""
天干五合の化神が、
命式内の地支に通根しているかを
評価するモジュール。

v1では以下を行います。

- 化神五行を受け取る
- 各地支の蔵干を確認する
- 化神と同じ五行の蔵干があるかを判定する
- 根の位置と数を集計する

この結果だけで、
天干五合の「化成立」を
確定するものではありません。
"""


STEM_ELEMENT = {
    "甲": "木",
    "乙": "木",
    "丙": "火",
    "丁": "火",
    "戊": "土",
    "己": "土",
    "庚": "金",
    "辛": "金",
    "壬": "水",
    "癸": "水",
}


VALID_ELEMENTS = {
    "木",
    "火",
    "土",
    "金",
    "水",
}


PILLAR_POSITIONS = (
    "year",
    "month",
    "day",
    "hour",
)


POSITION_WEIGHTS = {
    "year": 0.8,
    "month": 1.5,
    "day": 1.2,
    "hour": 1.0,
}


HIDDEN_STEM_WEIGHTS = {
    1: 1.0,
    2: 0.5,
    3: 0.3,
}


def get_stem_element(
    stem: str,
) -> str:
    """
    天干の五行を返します。
    """
    if stem not in STEM_ELEMENT:
        raise ValueError(
            f"不正な天干です: {stem}"
        )

    return STEM_ELEMENT[
        stem
    ]


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


def find_element_roots_in_pillar(
    position: str,
    pillar_data: dict,
    target_element: str,
) -> list[dict]:
    """
    1つの地支について、
    対象五行に該当する蔵干を探します。
    """
    if target_element not in VALID_ELEMENTS:
        raise ValueError(
            f"不正な五行です: {target_element}"
        )

    hidden_stems = pillar_data.get(
        "hidden_stems",
        [],
    )

    if not isinstance(
        hidden_stems,
        list,
    ):
        raise TypeError(
            "hidden_stemsはlist型で指定してください。"
        )

    branch = pillar_data.get(
        "branch"
    )

    roots: list[dict] = []

    for index, stem in enumerate(
        hidden_stems,
        start=1,
    ):
        stem_element = (
            get_stem_element(
                stem
            )
        )

        if stem_element != target_element:
            continue

        hidden_stem_weight = (
            HIDDEN_STEM_WEIGHTS.get(
                index,
                0.0,
            )
        )

        position_weight = (
            POSITION_WEIGHTS[
                position
            ]
        )

        root_score = round(
            hidden_stem_weight
            * position_weight,
            2,
        )

        roots.append(
            {
                "position": position,
                "branch": branch,
                "stem": stem,
                "element": stem_element,
                "hidden_stem_rank": index,
                "hidden_stem_weight": (
                    hidden_stem_weight
                ),
                "position_weight": (
                    position_weight
                ),
                "root_score": root_score,
            }
        )

    return roots


def evaluate_transformation_root(
    result_element: str,
    chart_data: dict,
) -> dict:
    """
    化神五行が命式内で
    通根しているかを評価します。

    v1では、
    各地支のhidden_stemsを調べ、
    化神と同じ五行の蔵干を
    根として扱います。
    """
    if result_element not in VALID_ELEMENTS:
        raise ValueError(
            f"不正な五行です: {result_element}"
        )

    if not isinstance(
        chart_data,
        dict,
    ):
        raise TypeError(
            "chart_dataはdict型で指定してください。"
        )

    available_positions = (
        get_available_positions(
            chart_data
        )
    )

    roots: list[dict] = []

    for position in available_positions:
        pillar_data = chart_data[
            position
        ]

        pillar_roots = (
            find_element_roots_in_pillar(
                position,
                pillar_data,
                result_element,
            )
        )

        roots.extend(
            pillar_roots
        )

    root_count = len(
        roots
    )

    root_positions = list(
        dict.fromkeys(
            root["position"]
            for root in roots
        )
    )

    total_root_score = round(
        sum(
            root["root_score"]
            for root in roots
        ),
        2,
    )

    month_root_score = round(
        sum(
            root["root_score"]
            for root in roots
            if (
                root["position"]
                == "month"
            )
        ),
        2,
    )

    has_root = root_count > 0

    has_month_root = (
        month_root_score > 0
    )

    if (
        has_month_root
        and total_root_score >= 1.0
    ):
        root_strength = "strong"

    elif has_root:
        root_strength = "present"

    else:
        root_strength = "none"

    return {
        "result_element": result_element,
        "has_root": has_root,
        "has_month_root": (
            has_month_root
        ),
        "root_count": root_count,
        "root_positions": (
            root_positions
        ),
        "total_root_score": (
            total_root_score
        ),
        "month_root_score": (
            month_root_score
        ),
        "root_strength": (
            root_strength
        ),
        "roots": roots,
        "method": (
            "transformation_root_v1"
        ),
        "status": (
            "provisional_transformation_root"
        ),
        "notes": [
            (
                "化神五行と同じ五行を持つ"
                "蔵干を通根候補として"
                "評価しています。"
            ),
            (
                "月支の根は他の柱より"
                "高い位置重みで評価しています。"
            ),
            (
                "現在のroot_scoreは"
                "暫定的な重みです。"
            ),
            (
                "通根が存在しても、"
                "それだけで化成立とは"
                "判定しません。"
            ),
            (
                "今後、月令・透干・妨害・"
                "争合などと統合して"
                "最終判定を行います。"
            ),
        ],
    }


def evaluate_transformation_roots(
    stem_transformations: dict,
    chart_data: dict,
) -> dict:
    """
    stem_transformations内の
    各化神候補について、
    通根状況をまとめて評価します。
    """
    if not isinstance(
        stem_transformations,
        dict,
    ):
        raise TypeError(
            "stem_transformationsはdict型で指定してください。"
        )

    if not isinstance(
        chart_data,
        dict,
    ):
        raise TypeError(
            "chart_dataはdict型で指定してください。"
        )

    transformations = (
        stem_transformations.get(
            "transformations",
            [],
        )
    )

    if not isinstance(
        transformations,
        list,
    ):
        raise TypeError(
            "transformationsはlist型で指定してください。"
        )

    results: list[dict] = []

    for transformation in transformations:
        result_element = (
            transformation.get(
                "result_element"
            )
        )

        if result_element is None:
            raise ValueError(
                "transformationにresult_elementが必要です。"
            )

        root_result = (
            evaluate_transformation_root(
                result_element,
                chart_data,
            )
        )

        results.append(
            {
                "combination_name": (
                    transformation.get(
                        "combination_name"
                    )
                ),
                "result_element": (
                    result_element
                ),
                "transformation_status": (
                    transformation.get(
                        "transformation_status"
                    )
                ),
                "confidence": (
                    transformation.get(
                        "confidence"
                    )
                ),
                "root_evaluation": (
                    root_result
                ),
            }
        )

    rooted_count = sum(
        1
        for item in results
        if (
            item[
                "root_evaluation"
            ][
                "has_root"
            ]
        )
    )

    month_rooted_count = sum(
        1
        for item in results
        if (
            item[
                "root_evaluation"
            ][
                "has_month_root"
            ]
        )
    )

    if not results:
        overall_root_status = (
            "not_applicable"
        )

    elif (
        rooted_count
        == len(results)
    ):
        overall_root_status = (
            "rooted"
        )

    elif rooted_count > 0:
        overall_root_status = (
            "mixed"
        )

    else:
        overall_root_status = (
            "unrooted"
        )

    return {
        "has_transformation_candidate": (
            bool(results)
        ),
        "transformation_count": (
            len(results)
        ),
        "rooted_count": (
            rooted_count
        ),
        "month_rooted_count": (
            month_rooted_count
        ),
        "overall_root_status": (
            overall_root_status
        ),
        "results": results,
        "method": (
            "transformation_roots_v1"
        ),
        "status": (
            "provisional_transformation_roots"
        ),
        "notes": [
            (
                "干合の化神候補について、"
                "命式内の通根状況を"
                "評価しています。"
            ),
            (
                "hidden_stemsに化神五行が"
                "存在する場合を"
                "根として扱います。"
            ),
            (
                "月支の通根は"
                "別途集計しています。"
            ),
            (
                "本結果だけでは"
                "化の成立を確定しません。"
            ),
        ],
    }
