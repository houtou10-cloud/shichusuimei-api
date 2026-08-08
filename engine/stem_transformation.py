"""
天干五合の「化」の成立可能性を評価するモジュール。

対象となる天干五合:

甲・己 → 土
乙・庚 → 金
丙・辛 → 水
丁・壬 → 木
戊・癸 → 火

重要:
天干が五合していても、
必ず化するわけではありません。

v1では主に月支と化神五行との関係から、
化の成立可能性を暫定評価します。

通根・透干・妨害・争合・妬合などは
今後のバージョンで追加します。
"""


BRANCH_ELEMENT = {
    "寅": "木",
    "卯": "木",
    "辰": "土",
    "巳": "火",
    "午": "火",
    "未": "土",
    "申": "金",
    "酉": "金",
    "戌": "土",
    "亥": "水",
    "子": "水",
    "丑": "土",
}


ELEMENT_GENERATES = {
    "木": "火",
    "火": "土",
    "土": "金",
    "金": "水",
    "水": "木",
}


VALID_ELEMENTS = {
    "木",
    "火",
    "土",
    "金",
    "水",
}


def get_month_branch_element(
    month_branch: str,
) -> str:
    """
    月支の代表五行を返します。

    v1では月支の本気に相当する
    代表五行のみを使用します。
    """
    if month_branch not in BRANCH_ELEMENT:
        raise ValueError(
            f"不正な月支です: {month_branch}"
        )

    return BRANCH_ELEMENT[
        month_branch
    ]


def evaluate_month_support(
    result_element: str,
    month_branch: str,
) -> dict:
    """
    化神五行が月支から
    どの程度支持されるかを評価します。

    v1の判定:

    strong:
        月支の代表五行と化神が同じ。

    supportive:
        月支の五行が化神を生じる。

    weak:
        上記以外。
    """
    if result_element not in VALID_ELEMENTS:
        raise ValueError(
            f"不正な五行です: {result_element}"
        )

    month_element = (
        get_month_branch_element(
            month_branch
        )
    )

    if month_element == result_element:
        support_level = "strong"
        support_score = 2.0

    elif (
        ELEMENT_GENERATES[
            month_element
        ]
        == result_element
    ):
        support_level = "supportive"
        support_score = 1.0

    else:
        support_level = "weak"
        support_score = 0.0

    return {
        "month_branch": month_branch,
        "month_element": month_element,
        "result_element": result_element,
        "support_level": support_level,
        "support_score": support_score,
    }


def evaluate_single_transformation(
    combination: dict,
    month_branch: str,
) -> dict:
    """
    1件の干合について、
    化の成立可能性を暫定評価します。
    """
    result_element = combination.get(
        "result_element"
    )

    if result_element is None:
        raise ValueError(
            "combinationにresult_elementが必要です。"
        )

    month_support = (
        evaluate_month_support(
            result_element,
            month_branch,
        )
    )

    support_level = (
        month_support[
            "support_level"
        ]
    )

    if support_level == "strong":
        transformation_status = (
            "possible"
        )

        confidence = "high"

    elif support_level == "supportive":
        transformation_status = (
            "possible"
        )

        confidence = "medium"

    else:
        transformation_status = (
            "unsupported"
        )

        confidence = "low"

    return {
        "position_a": combination.get(
            "position_a"
        ),
        "stem_a": combination.get(
            "stem_a"
        ),
        "position_b": combination.get(
            "position_b"
        ),
        "stem_b": combination.get(
            "stem_b"
        ),
        "combination_name": (
            combination.get(
                "combination_name"
            )
        ),
        "result_element": (
            result_element
        ),
        "transformation_status": (
            transformation_status
        ),
        "confidence": confidence,
        "month_support": month_support,
    }


def evaluate_stem_transformations(
    stem_combinations: dict,
    chart_data: dict,
) -> dict:
    """
    命式内で検出された天干五合について、
    化の成立可能性を評価します。

    v1では月支の代表五行との関係を
    主な判断材料とします。
    """
    if not isinstance(
        stem_combinations,
        dict,
    ):
        raise TypeError(
            "stem_combinationsはdict型で指定してください。"
        )

    if not isinstance(
        chart_data,
        dict,
    ):
        raise TypeError(
            "chart_dataはdict型で指定してください。"
        )

    month_pillar = chart_data.get(
        "month"
    )

    if not isinstance(
        month_pillar,
        dict,
    ):
        raise ValueError(
            "chart_dataにmonth柱が必要です。"
        )

    month_branch = month_pillar.get(
        "branch"
    )

    if month_branch is None:
        raise ValueError(
            "month柱にbranchが必要です。"
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

    transformations: list[dict] = []

    for combination in combinations:
        transformations.append(
            evaluate_single_transformation(
                combination,
                month_branch,
            )
        )

    possible_count = sum(
        1
        for item in transformations
        if (
            item[
                "transformation_status"
            ]
            == "possible"
        )
    )

    unsupported_count = sum(
        1
        for item in transformations
        if (
            item[
                "transformation_status"
            ]
            == "unsupported"
        )
    )

    if not transformations:
        overall_status = (
            "not_applicable"
        )

    elif (
        possible_count
        == len(transformations)
    ):
        overall_status = (
            "possible"
        )

    elif possible_count > 0:
        overall_status = (
            "mixed"
        )

    else:
        overall_status = (
            "unsupported"
        )

    return {
        "has_stem_combination": bool(
            transformations
        ),
        "transformation_count": len(
            transformations
        ),
        "possible_count": (
            possible_count
        ),
        "unsupported_count": (
            unsupported_count
        ),
        "overall_status": (
            overall_status
        ),
        "transformations": (
            transformations
        ),
        "method": (
            "stem_transformation_v1"
        ),
        "status": (
            "provisional_stem_transformation"
        ),
        "notes": [
            (
                "天干五合の化の成立可能性を"
                "暫定評価しています。"
            ),
            (
                "v1では月支の代表五行と"
                "化神五行との関係を"
                "主な判断材料としています。"
            ),
            (
                "possibleは化の成立確定を"
                "意味するものではありません。"
            ),
            (
                "通根・透干・争合・妬合・"
                "周囲の五行による妨害条件は"
                "まだ評価していません。"
            ),
            (
                "身強・身弱や五行量への"
                "直接補正はまだ行っていません。"
            ),
        ],
    }
