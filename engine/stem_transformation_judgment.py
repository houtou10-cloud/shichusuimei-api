"""
天干五合の化について、
月令・通根・透干・干合競合を統合して
暫定的な総合判定を行うモジュール。

現在利用する情報:

1. 月令による化神の支持
2. 化神の通根
3. 化神の透干
4. 干合参加者以外からの外部透干
5. 同一柱が複数の干合候補に参加する競合

重要:
v2でも争合・妬合・妨害条件の
占術的な最終判定までは行いません。

競合が検出された干合候補は、
評価を1段階抑制します。

判定:

- strong_candidate
- possible
- weak
- unsupported
- not_applicable
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


JUDGMENT_DOWNGRADE = {
    "strong_candidate": "possible",
    "possible": "weak",
    "weak": "unsupported",
    "unsupported": "unsupported",
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

    v2では既存APIとの互換性維持のため残します。
    複数の同名干合がある場合は、
    positionによる照合を優先する
    find_result_for_transformation()を使用します。
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


def find_result_for_transformation(
    results: list,
    transformation: dict,
) -> dict | None:
    """
    transformationに対応する評価結果を探します。

    combination_nameに加えて、
    position_a / position_b が結果側に存在する場合は
    位置も照合します。

    既存のroot/exposure結果が位置情報を
    持たない場合はcombination_nameで照合します。
    """
    combination_name = transformation.get(
        "combination_name"
    )

    position_a = transformation.get(
        "position_a"
    )

    position_b = transformation.get(
        "position_b"
    )

    name_matches = [
        item
        for item in results
        if (
            item.get(
                "combination_name"
            )
            == combination_name
        )
    ]

    if not name_matches:
        return None

    for item in name_matches:
        item_position_a = item.get(
            "position_a"
        )
        item_position_b = item.get(
            "position_b"
        )

        if (
            item_position_a is None
            and item_position_b is None
        ):
            continue

        if (
            item_position_a == position_a
            and item_position_b == position_b
        ):
            return item

        if (
            item_position_a == position_b
            and item_position_b == position_a
        ):
            return item

    return name_matches[0]


def classify_judgment(
    total_score: float,
    month_support_level: str,
    has_root: bool,
    has_external_exposure: bool,
) -> str:
    """
    総合スコアと主要条件から、
    化の候補レベルを判定します。

    この段階では競合情報を反映しません。
    競合による抑制は
    apply_conflict_adjustment()で行います。
    """
    if (
        month_support_level == "strong"
        and has_root
        and has_external_exposure
        and total_score >= 8.0
    ):
        return "strong_candidate"

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


def get_conflicted_positions(
    stem_combination_conflicts: dict | None,
) -> set[str]:
    """
    競合評価から、
    competing_combinationが検出された
    柱位置を集合で返します。

    Noneの場合は競合なしとして扱います。
    """
    if stem_combination_conflicts is None:
        return set()

    if not isinstance(
        stem_combination_conflicts,
        dict,
    ):
        raise TypeError(
            "stem_combination_conflictsは"
            "dict型またはNoneで指定してください。"
        )

    position_conflicts = (
        stem_combination_conflicts.get(
            "position_conflicts",
            [],
        )
    )

    if not isinstance(
        position_conflicts,
        list,
    ):
        raise TypeError(
            "position_conflictsはlist型で指定してください。"
        )

    positions: set[str] = set()

    for conflict in position_conflicts:
        if not isinstance(
            conflict,
            dict,
        ):
            raise TypeError(
                "position_conflictはdict型で指定してください。"
            )

        position = conflict.get(
            "position"
        )

        if position is not None:
            positions.add(
                position
            )

    return positions


def get_transformation_conflict_info(
    transformation: dict,
    stem_combination_conflicts: dict | None,
) -> dict:
    """
    1件の干合候補が、
    検出済みの競合位置に関係しているかを
    判定します。

    全体に競合が存在するだけでは減点せず、
    position_a / position_b のどちらかが
    実際に競合位置である場合だけ
    この干合候補をconflictedとします。
    """
    if not isinstance(
        transformation,
        dict,
    ):
        raise TypeError(
            "transformationはdict型で指定してください。"
        )

    conflicted_positions = (
        get_conflicted_positions(
            stem_combination_conflicts
        )
    )

    position_a = transformation.get(
        "position_a"
    )

    position_b = transformation.get(
        "position_b"
    )

    matched_positions = [
        position
        for position in (
            position_a,
            position_b,
        )
        if (
            position is not None
            and position
            in conflicted_positions
        )
    ]

    has_conflict = bool(
        matched_positions
    )

    return {
        "has_conflict": has_conflict,
        "conflicted_positions": (
            matched_positions
        ),
        "adjustment_steps": (
            -1 if has_conflict else 0
        ),
        "reason": (
            "competing_combination"
            if has_conflict
            else None
        ),
    }


def apply_conflict_adjustment(
    judgment: str,
    has_conflict: bool,
) -> str:
    """
    競合がある干合候補の判定を
    1段階抑制します。

    strong_candidate -> possible
    possible         -> weak
    weak             -> unsupported
    unsupported      -> unsupported
    """
    if judgment not in JUDGMENT_DOWNGRADE:
        raise ValueError(
            "不正なjudgmentです: "
            f"{judgment}"
        )

    if not has_conflict:
        return judgment

    return JUDGMENT_DOWNGRADE[
        judgment
    ]


def evaluate_single_transformation_judgment(
    transformation: dict,
    root_result: dict,
    exposure_result: dict,
    conflict_info: dict | None = None,
) -> dict:
    """
    1件の干合について、
    月令・通根・透干・競合を統合して
    暫定総合判定を行います。

    conflict_infoを省略した場合は
    競合なしとして扱うため、
    v1の呼び出し方とも互換性があります。
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

    if (
        conflict_info is not None
        and not isinstance(
            conflict_info,
            dict,
        )
    ):
        raise TypeError(
            "conflict_infoはdict型またはNoneで指定してください。"
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

    base_judgment = classify_judgment(
        total_score,
        month_support_level,
        has_root,
        has_external_exposure,
    )

    if conflict_info is None:
        conflict_info = {
            "has_conflict": False,
            "conflicted_positions": [],
            "adjustment_steps": 0,
            "reason": None,
        }

    has_conflict = bool(
        conflict_info.get(
            "has_conflict",
            False,
        )
    )

    judgment = apply_conflict_adjustment(
        base_judgment,
        has_conflict,
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

    if has_conflict:
        limiting_factors.append(
            "competing_combination"
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
        "base_judgment": (
            base_judgment
        ),
        "has_conflict": (
            has_conflict
        ),
        "conflict_info": (
            conflict_info
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
    stem_combination_conflicts: dict | None = None,
) -> dict:
    """
    全ての干合候補について、
    月令・通根・透干・競合を統合した
    暫定総合判定を行います。

    第4引数は任意です。
    省略した場合は競合なしとして扱うため、
    既存コードとの互換性を保ちます。
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

    if (
        stem_combination_conflicts is not None
        and not isinstance(
            stem_combination_conflicts,
            dict,
        )
    ):
        raise TypeError(
            "stem_combination_conflictsは"
            "dict型またはNoneで指定してください。"
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
        if not isinstance(
            transformation,
            dict,
        ):
            raise TypeError(
                "transformationはdict型で指定してください。"
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

        root_result = (
            find_result_for_transformation(
                root_results,
                transformation,
            )
        )

        if root_result is None:
            raise ValueError(
                "対応する通根評価が"
                "見つかりません: "
                f"{combination_name}"
            )

        exposure_result = (
            find_result_for_transformation(
                exposure_results,
                transformation,
            )
        )

        if exposure_result is None:
            raise ValueError(
                "対応する透干評価が"
                "見つかりません: "
                f"{combination_name}"
            )

        conflict_info = (
            get_transformation_conflict_info(
                transformation,
                stem_combination_conflicts,
            )
        )

        judgment = (
            evaluate_single_transformation_judgment(
                transformation,
                root_result,
                exposure_result,
                conflict_info,
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

    conflicted_judgment_count = sum(
        1
        for item in judgments
        if item[
            "has_conflict"
        ]
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
        "conflicted_judgment_count": (
            conflicted_judgment_count
        ),
        "overall_judgment": (
            overall_judgment
        ),
        "judgments": (
            judgments
        ),
        "method": (
            "stem_transformation_judgment_v2"
        ),
        "status": (
            "provisional_stem_transformation_judgment"
        ),
        "notes": [
            (
                "天干五合の化について、"
                "月令・通根・透干・干合競合を"
                "統合して暫定評価しています。"
            ),
            (
                "競合する柱位置を含む干合候補は"
                "判定を1段階抑制しています。"
            ),
            (
                "strong_candidateでも"
                "化成立を確定したものではありません。"
            ),
            (
                "争合・妬合の詳細分類や"
                "その他の妨害条件は"
                "まだ評価していません。"
            ),
            (
                "現段階では五行量や"
                "身強身弱への変換補正を"
                "行っていません。"
            ),
        ],
    }
