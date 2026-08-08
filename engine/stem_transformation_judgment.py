"""
天干五合の化について、
月令・通根・透干を統合して
暫定的な総合判定を行うモジュール。

現在利用する情報:

1. 月令による化神の支持
2. 化神の通根
3. 化神の透干
4. 干合参加者以外からの外部透干

重要:
v1では争合・妬合・妨害条件などを
まだ評価していません。

そのため、
「化が成立した(transformed)」とは断定せず、

- strong_candidate
- possible
- weak
- unsupported
- not_applicable

という候補評価を返します。
"""


MONTH_SUPPORT_SCORES = {
    "strong": 4.0,
    "supportive": 2.0,
    "weak": 0.0,
}


ROOT_STRENGTH_SCORES = {
    "strong": 3.0,
    "present": 1.5,
    "none": 0.0,
}


EXPOSURE_STRENGTH_SCORES = {
    "strong": 2.0,
    "participant_only": 0.5,
    "none": 0.0,
}


def get_month_support_score(
    support_level: str,
) -> float:
    """
    月令による化神支持を
    総合判定用スコアへ変換します。
    """
    if (
        support_level
        not in MONTH_SUPPORT_SCORES
    ):
        raise ValueError(
            "不正なmonth support levelです: "
            f"{support_level}"
        )

    return MONTH_SUPPORT_SCORES[
        support_level
    ]


def get_root_strength_score(
    root_strength: str,
) -> float:
    """
    化神の通根強度を
    総合判定用スコアへ変換します。
    """
    if (
        root_strength
        not in ROOT_STRENGTH_SCORES
    ):
        raise ValueError(
            "不正なroot strengthです: "
            f"{root_strength}"
        )

    return ROOT_STRENGTH_SCORES[
        root_strength
    ]


def get_exposure_strength_score(
    exposure_strength: str,
) -> float:
    """
    化神の透干状態を
    総合判定用スコアへ変換します。
    """
    if (
        exposure_strength
        not in EXPOSURE_STRENGTH_SCORES
    ):
        raise ValueError(
            "不正なexposure strengthです: "
            f"{exposure_strength}"
        )

    return EXPOSURE_STRENGTH_SCORES[
        exposure_strength
    ]


def find_result_by_combination(
    results: list,
    combination_name: str,
) -> dict | None:
    """
    resultsからcombination_nameが一致する
    最初のデータを返します。
    """
    for item in results:
        if (
            item.get(
                "combination_name"
            )
            == combination_name
        ):
            return item

    return None


def classify_judgment(
    total_score: float,
    month_support_level: str,
    has_root: bool,
    has_external_exposure: bool,
) -> str:
    """
    総合スコアと主要条件から、
    化の候補レベルを判定します。

    v1では「transformed」は返しません。
    """

    # 月令の支持が強く、
    # 通根があり、
    # 外部透干もある場合は
    # 強い化候補として扱います。
    if (
        month_support_level == "strong"
        and has_root
        and has_external_exposure
        and total_score >= 8.0
    ):
        return "strong_candidate"

    # 月令がstrongまたはsupportiveで、
    # 通根も存在する場合。
    if (
        month_support_level
        in {
            "strong",
            "supportive",
        }
        and has_root
        and total_score >= 5.0
    ):
        return "possible"

    # 月令支持はあるが、
    # 通根・外部透干などが弱いケース。
    if (
        month_support_level
        in {
            "strong",
            "supportive",
        }
        and total_score >= 2.0
    ):
        return "weak"

    return "unsupported"


def evaluate_single_transformation_judgment(
    transformation: dict,
    root_result: dict,
    exposure_result: dict,
) -> dict:
    """
    1件の干合について、
    月令・通根・透干を統合して
    暫定総合判定を行います。
    """
    if not isinstance(
        transformation,
        dict,
    ):
        raise TypeError(
            "transformationはdict型で指定してください。"
        )

    if not isinstance(
        root_result,
        dict,
    ):
        raise TypeError(
            "root_resultはdict型で指定してください。"
        )

    if not isinstance(
        exposure_result,
        dict,
    ):
        raise TypeError(
            "exposure_resultはdict型で指定してください。"
        )

    combination_name = (
        transformation.get(
            "combination_name"
        )
    )

    if combination_name is None:
        raise ValueError(
            "transformationに"
            "combination_nameが必要です。"
        )

    result_element = (
        transformation.get(
            "result_element"
        )
    )

    if result_element is None:
        raise ValueError(
            "transformationに"
            "result_elementが必要です。"
        )

    month_support = (
        transformation.get(
            "month_support"
        )
    )

    if not isinstance(
        month_support,
        dict,
    ):
        raise ValueError(
            "transformationに"
            "month_supportが必要です。"
        )

    month_support_level = (
        month_support.get(
            "support_level"
        )
    )

    if month_support_level is None:
        raise ValueError(
            "month_supportに"
            "support_levelが必要です。"
        )

    root_evaluation = (
        root_result.get(
            "root_evaluation"
        )
    )

    if not isinstance(
        root_evaluation,
        dict,
    ):
        raise ValueError(
            "root_resultに"
            "root_evaluationが必要です。"
        )

    exposure_evaluation = (
        exposure_result.get(
            "exposure_evaluation"
        )
    )

    if not isinstance(
        exposure_evaluation,
        dict,
    ):
        raise ValueError(
            "exposure_resultに"
            "exposure_evaluationが必要です。"
        )

    root_strength = (
        root_evaluation.get(
            "root_strength"
        )
    )

    if root_strength is None:
        raise ValueError(
            "root_evaluationに"
            "root_strengthが必要です。"
        )

    exposure_strength = (
        exposure_evaluation.get(
            "exposure_strength"
        )
    )

    if exposure_strength is None:
        raise ValueError(
            "exposure_evaluationに"
            "exposure_strengthが必要です。"
        )

    has_root = bool(
        root_evaluation.get(
            "has_root",
            False,
        )
    )

    has_month_root = bool(
        root_evaluation.get(
            "has_month_root",
            False,
        )
    )

    has_exposure = bool(
        exposure_evaluation.get(
            "has_exposure",
            False,
        )
    )

    has_external_exposure = bool(
        exposure_evaluation.get(
            "has_external_exposure",
            False,
        )
    )

    month_score = (
        get_month_support_score(
            month_support_level
        )
    )

    root_score = (
        get_root_strength_score(
            root_strength
        )
    )

    exposure_score = (
        get_exposure_strength_score(
            exposure_strength
        )
    )

    total_score = round(
        month_score
        + root_score
        + exposure_score,
        2,
    )

    judgment = classify_judgment(
        total_score,
        month_support_level,
        has_root,
        has_external_exposure,
    )

    if judgment == "strong_candidate":
        confidence = "high"

    elif judgment == "possible":
        confidence = "medium"

    elif judgment == "weak":
        confidence = "low"

    else:
        confidence = "very_low"

    supporting_factors: list[str] = []
    limiting_factors: list[str] = []

    if (
        month_support_level
        == "strong"
    ):
        supporting_factors.append(
            "strong_month_support"
        )

    elif (
        month_support_level
        == "supportive"
    ):
        supporting_factors.append(
            "supportive_month"
        )

    else:
        limiting_factors.append(
            "weak_month_support"
        )

    if has_root:
        supporting_factors.append(
            "has_transformation_root"
        )
    else:
        limiting_factors.append(
            "no_transformation_root"
        )

    if has_month_root:
        supporting_factors.append(
            "has_month_root"
        )

    if has_external_exposure:
        supporting_factors.append(
            "has_external_exposure"
        )

    elif has_exposure:
        supporting_factors.append(
            "participant_exposure_only"
        )

        limiting_factors.append(
            "no_external_exposure"
        )

    else:
        limiting_factors.append(
            "no_transformation_exposure"
        )

    return {
        "combination_name": (
            combination_name
        ),
        "result_element": (
            result_element
        ),
        "position_a": (
            transformation.get(
                "position_a"
            )
        ),
        "position_b": (
            transformation.get(
                "position_b"
            )
        ),
        "month_support_level": (
            month_support_level
        ),
        "month_support_score": (
            month_score
        ),
        "root_strength": (
            root_strength
        ),
        "root_score": (
            root_score
        ),
        "has_root": (
            has_root
        ),
        "has_month_root": (
            has_month_root
        ),
        "exposure_strength": (
            exposure_strength
        ),
        "exposure_score": (
            exposure_score
        ),
        "has_exposure": (
            has_exposure
        ),
        "has_external_exposure": (
            has_external_exposure
        ),
        "total_score": (
            total_score
        ),
        "judgment": (
            judgment
        ),
        "confidence": (
            confidence
        ),
        "supporting_factors": (
            supporting_factors
        ),
        "limiting_factors": (
            limiting_factors
        ),
    }


def evaluate_stem_transformation_judgment(
    stem_transformations: dict,
    transformation_roots: dict,
    transformation_exposures: dict,
) -> dict:
    """
    全ての干合候補について、
    月令・通根・透干を統合した
    暫定総合判定を行います。
    """
    if not isinstance(
        stem_transformations,
        dict,
    ):
        raise TypeError(
            "stem_transformationsはdict型で指定してください。"
        )

    if not isinstance(
        transformation_roots,
        dict,
    ):
        raise TypeError(
            "transformation_rootsはdict型で指定してください。"
        )

    if not isinstance(
        transformation_exposures,
        dict,
    ):
        raise TypeError(
            "transformation_exposuresはdict型で指定してください。"
        )

    transformations = (
        stem_transformations.get(
            "transformations",
            [],
        )
    )

    root_results = (
        transformation_roots.get(
            "results",
            [],
        )
    )

    exposure_results = (
        transformation_exposures.get(
            "results",
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

    if not isinstance(
        root_results,
        list,
    ):
        raise TypeError(
            "transformation_rootsの"
            "resultsはlist型で指定してください。"
        )

    if not isinstance(
        exposure_results,
        list,
    ):
        raise TypeError(
            "transformation_exposuresの"
            "resultsはlist型で指定してください。"
        )

    judgments: list[dict] = []

    for transformation in transformations:
        combination_name = (
            transformation.get(
                "combination_name"
            )
        )

        if combination_name is None:
            raise ValueError(
                "transformationに"
                "combination_nameが必要です。"
            )

        root_result = (
            find_result_by_combination(
                root_results,
                combination_name,
            )
        )

        if root_result is None:
            raise ValueError(
                "対応する通根評価が"
                "見つかりません: "
                f"{combination_name}"
            )

        exposure_result = (
            find_result_by_combination(
                exposure_results,
                combination_name,
            )
        )

        if exposure_result is None:
            raise ValueError(
                "対応する透干評価が"
                "見つかりません: "
                f"{combination_name}"
            )

        judgment = (
            evaluate_single_transformation_judgment(
                transformation,
                root_result,
                exposure_result,
            )
        )

        judgments.append(
            judgment
        )

    strong_candidate_count = sum(
        1
        for item in judgments
        if (
            item["judgment"]
            == "strong_candidate"
        )
    )

    possible_count = sum(
        1
        for item in judgments
        if (
            item["judgment"]
            == "possible"
        )
    )

    weak_count = sum(
        1
        for item in judgments
        if (
            item["judgment"]
            == "weak"
        )
    )

    unsupported_count = sum(
        1
        for item in judgments
        if (
            item["judgment"]
            == "unsupported"
        )
    )

    if not judgments:
        overall_judgment = (
            "not_applicable"
        )

    elif (
        strong_candidate_count
        == len(judgments)
    ):
        overall_judgment = (
            "strong_candidate"
        )

    elif (
        unsupported_count
        == len(judgments)
    ):
        overall_judgment = (
            "unsupported"
        )

    elif (
        possible_count
        == len(judgments)
    ):
        overall_judgment = (
            "possible"
        )

    elif (
        weak_count
        == len(judgments)
    ):
        overall_judgment = (
            "weak"
        )

    else:
        overall_judgment = (
            "mixed"
        )

    return {
        "has_transformation_candidate": (
            bool(judgments)
        ),
        "judgment_count": (
            len(judgments)
        ),
        "strong_candidate_count": (
            strong_candidate_count
        ),
        "possible_count": (
            possible_count
        ),
        "weak_count": (
            weak_count
        ),
        "unsupported_count": (
            unsupported_count
        ),
        "overall_judgment": (
            overall_judgment
        ),
        "judgments": (
            judgments
        ),
        "method": (
            "stem_transformation_judgment_v1"
        ),
        "status": (
            "provisional_stem_transformation_judgment"
        ),
        "notes": [
            (
                "天干五合の化について、"
                "月令・通根・透干を統合して"
                "暫定評価しています。"
            ),
            (
                "strong_candidateでも"
                "化成立を確定したものでは"
                "ありません。"
            ),
            (
                "争合・妬合・妨害条件などは"
                "まだ評価していません。"
            ),
            (
                "現段階では五行量や"
                "身強身弱への変換補正を"
                "行っていません。"
            ),
        ],
    }
