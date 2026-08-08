"""
天干五合の化について、
月令・通根・透干・競合severityを統合して
暫定的な総合判定を行うモジュール。

v3では、
競合の有無だけでなく、
stem_combination_conflict_types の
severity を反映します。

補正ルール:

- low    -> 判定維持
- medium -> 1段階抑制
- high   -> 2段階抑制

ただし、
無関係な柱位置の競合は
その干合候補へ影響させません。

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


JUDGMENT_LEVELS = [
    "unsupported",
    "weak",
    "possible",
    "strong_candidate",
]


SEVERITY_ADJUSTMENT_STEPS = {
    "none": 0,
    "low": 0,
    "medium": -1,
    "high": -2,
}


def get_month_support_score(
    support_level: str,
) -> float:
    if support_level not in MONTH_SUPPORT_SCORES:
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
    if root_strength not in ROOT_STRENGTH_SCORES:
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
            and position in conflicted_positions
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


def get_related_typed_conflicts(
    transformation: dict,
    stem_combination_conflict_types: dict | None,
) -> list[dict]:
    """
    transformationに関係する
    typed conflictのみを抽出します。

    position_conflictは
    position_a / position_b が一致する場合。

    duplicate_combinationは
    combination_name が一致する場合。
    """
    if stem_combination_conflict_types is None:
        return []

    if not isinstance(
        stem_combination_conflict_types,
        dict,
    ):
        raise TypeError(
            "stem_combination_conflict_typesは"
            "dict型またはNoneで指定してください。"
        )

    conflicts = (
        stem_combination_conflict_types.get(
            "conflicts",
            [],
        )
    )

    if not isinstance(
        conflicts,
        list,
    ):
        raise TypeError(
            "stem_combination_conflict_typesの"
            "conflictsはlist型で指定してください。"
        )

    position_a = transformation.get(
        "position_a"
    )

    position_b = transformation.get(
        "position_b"
    )

    combination_name = transformation.get(
        "combination_name"
    )

    related: list[dict] = []

    for conflict in conflicts:
        if not isinstance(
            conflict,
            dict,
        ):
            raise TypeError(
                "typed conflictはdict型で指定してください。"
            )

        source_type = conflict.get(
            "source_type"
        )

        if source_type == "position_conflict":
            position = conflict.get(
                "position"
            )

            if position in {
                position_a,
                position_b,
            }:
                related.append(
                    conflict
                )

        elif source_type == "duplicate_combination":
            if (
                conflict.get(
                    "combination_name"
                )
                == combination_name
            ):
                related.append(
                    conflict
                )

    return related


def get_max_conflict_severity(
    related_conflicts: list[dict],
) -> str:
    """
    関連する競合の最大severityを返します。
    """
    if not isinstance(
        related_conflicts,
        list,
    ):
        raise TypeError(
            "related_conflictsはlist型で指定してください。"
        )

    severity_rank = {
        "none": 0,
        "low": 1,
        "medium": 2,
        "high": 3,
    }

    max_severity = "none"
    max_rank = 0

    for conflict in related_conflicts:
        if not isinstance(
            conflict,
            dict,
        ):
            raise TypeError(
                "typed conflictはdict型で指定してください。"
            )

        severity = conflict.get(
            "severity",
            "none",
        )

        if severity not in severity_rank:
            raise ValueError(
                "不正なconflict severityです: "
                f"{severity}"
            )

        rank = severity_rank[
            severity
        ]

        if rank > max_rank:
            max_rank = rank
            max_severity = severity

    return max_severity


def get_severity_adjustment_steps(
    severity: str,
) -> int:
    if (
        severity
        not in SEVERITY_ADJUSTMENT_STEPS
    ):
        raise ValueError(
            "不正なconflict severityです: "
            f"{severity}"
        )

    return SEVERITY_ADJUSTMENT_STEPS[
        severity
    ]


def apply_judgment_adjustment_steps(
    judgment: str,
    adjustment_steps: int,
) -> str:
    """
    judgmentを指定段階だけ上下させます。

    今回は主に負数を使用します。
    下限はunsupported、
    上限はstrong_candidateです。
    """
    if judgment not in JUDGMENT_LEVELS:
        raise ValueError(
            "不正なjudgmentです: "
            f"{judgment}"
        )

    if not isinstance(
        adjustment_steps,
        int,
    ):
        raise TypeError(
            "adjustment_stepsはint型で指定してください。"
        )

    current_index = (
        JUDGMENT_LEVELS.index(
            judgment
        )
    )

    adjusted_index = (
        current_index
        + adjustment_steps
    )

    adjusted_index = max(
        0,
        min(
            adjusted_index,
            len(
                JUDGMENT_LEVELS
            )
            - 1,
        ),
    )

    return JUDGMENT_LEVELS[
        adjusted_index
    ]


def evaluate_single_transformation_judgment(
    transformation: dict,
    root_result: dict,
    exposure_result: dict,
    conflict_info: dict | None = None,
    related_typed_conflicts: list[dict] | None = None,
) -> dict:
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

    if (
        related_typed_conflicts is not None
        and not isinstance(
            related_typed_conflicts,
            list,
        )
    ):
        raise TypeError(
            "related_typed_conflictsは"
            "list型またはNoneで指定してください。"
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

    if related_typed_conflicts is None:
        related_typed_conflicts = []

    conflict_severity = (
        get_max_conflict_severity(
            related_typed_conflicts
        )
    )

    severity_adjustment_steps = (
        get_severity_adjustment_steps(
            conflict_severity
        )
    )

    # typed conflictが存在しない場合は、
    # v2互換のconflict_infoを利用します。
    if (
        conflict_severity == "none"
        and conflict_info.get(
            "has_conflict",
            False,
        )
    ):
        conflict_severity = "medium"
        severity_adjustment_steps = -1

    judgment = (
        apply_judgment_adjustment_steps(
            base_judgment,
            severity_adjustment_steps,
        )
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

    if conflict_severity == "low":
        limiting_factors.append(
            "low_conflict"
        )

    elif conflict_severity == "medium":
        limiting_factors.append(
            "medium_conflict"
        )

    elif conflict_severity == "high":
        limiting_factors.append(
            "high_conflict"
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
            conflict_severity
            != "none"
        ),
        "conflict_severity": (
            conflict_severity
        ),
        "conflict_adjustment_steps": (
            severity_adjustment_steps
        ),
        "conflict_info": (
            conflict_info
        ),
        "related_typed_conflicts": (
            related_typed_conflicts
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
    stem_combination_conflict_types: dict | None = None,
) -> dict:
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

    if (
        stem_combination_conflict_types is not None
        and not isinstance(
            stem_combination_conflict_types,
            dict,
        )
    ):
        raise TypeError(
            "stem_combination_conflict_typesは"
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

        related_typed_conflicts = (
            get_related_typed_conflicts(
                transformation,
                stem_combination_conflict_types,
            )
        )

        judgment = (
            evaluate_single_transformation_judgment(
                transformation,
                root_result,
                exposure_result,
                conflict_info,
                related_typed_conflicts,
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
        if (
            item[
                "conflict_severity"
            ]
            != "none"
        )
    )

    high_conflict_count = sum(
        1
        for item in judgments
        if (
            item[
                "conflict_severity"
            ]
            == "high"
        )
    )

    medium_conflict_count = sum(
        1
        for item in judgments
        if (
            item[
                "conflict_severity"
            ]
            == "medium"
        )
    )

    low_conflict_count = sum(
        1
        for item in judgments
        if (
            item[
                "conflict_severity"
            ]
            == "low"
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
        "conflicted_judgment_count": (
            conflicted_judgment_count
        ),
        "high_conflict_count": (
            high_conflict_count
        ),
        "medium_conflict_count": (
            medium_conflict_count
        ),
        "low_conflict_count": (
            low_conflict_count
        ),
        "overall_judgment": (
            overall_judgment
        ),
        "judgments": (
            judgments
        ),
        "method": (
            "stem_transformation_judgment_v3"
        ),
        "status": (
            "provisional_stem_transformation_judgment"
        ),
        "notes": [
            (
                "天干五合の化について、"
                "月令・通根・透干・競合severityを"
                "統合して暫定評価しています。"
            ),
            (
                "low競合は判定維持、"
                "mediumは1段階、"
                "highは2段階抑制します。"
            ),
            (
                "無関係な柱位置の競合は"
                "対象干合へ影響させません。"
            ),
            (
                "strong_candidateでも"
                "化成立を確定したものではありません。"
            ),
            (
                "争合・妬合の古典的な最終判定は"
                "まだ暫定段階です。"
            ),
        ],
    }
