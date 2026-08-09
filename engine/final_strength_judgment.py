"""
身強身弱の最終統合判定モジュール v2。

重要な設計変更:
weighted_strength_judgment["final_score"] には、
既存ロジックで五行・通根・月令がすでに反映されている。

そのためv2では、通根と月令を再加算しない。
これにより二重計上を防ぐ。

v2で最終スコアへ追加するのは原則として、

- 地支関係による「明示的な」身強身弱補正
- 干合化候補による限定的な補正

のみ。

weighted_root_strength と integrated_month_strength は
最終スコアの再計算には使わず、
判定根拠・confidence・監査用 evidence として保持する。

また、branch_relation_strength の total_score は、
地支関係全体の強弱を示す値であって、
日主の強弱への方向を直接示すとは限らない。
したがって total_score は自動加算しない。
"""


MIN_SCORE = 0.0
MAX_SCORE = 100.0


STRENGTH_THRESHOLDS = (
    (70.0, "very_strong", "極身強"),
    (58.0, "strong", "身強"),
    (43.0, "balanced", "中和"),
    (30.0, "weak", "身弱"),
    (0.0, "very_weak", "極身弱"),
)


TRANSFORMATION_ADJUSTMENTS = {
    "strong_candidate": 3.0,
    "possible": 1.5,
    "weak": 0.5,
    "unsupported": 0.0,
}


VALID_CONFLICT_SEVERITIES = {
    "none",
    "low",
    "medium",
    "high",
}


def clamp_score(score: float) -> float:
    """スコアを0〜100へ制限する。"""
    if not isinstance(score, (int, float)):
        raise TypeError(
            "scoreは数値で指定してください。"
        )

    return round(
        max(
            MIN_SCORE,
            min(MAX_SCORE, float(score)),
        ),
        2,
    )


def safe_number(
    value,
    default: float = 0.0,
) -> float:
    """数値を安全にfloatへ変換する。"""
    if value is None:
        return float(default)

    if not isinstance(value, (int, float)):
        raise TypeError(
            "数値項目はintまたは"
            "float型で指定してください。"
        )

    return float(value)


def extract_base_score(
    weighted_strength_judgment: dict,
) -> float:
    """
    既存のweighted身強身弱判定から
    最終基礎スコアを取得する。

    v2では final_score を最優先する。
    final_score は既に通根・月令を含む前提。
    """
    if not isinstance(
        weighted_strength_judgment,
        dict,
    ):
        raise TypeError(
            "weighted_strength_judgmentは"
            "dict型で指定してください。"
        )

    candidate_keys = (
        "final_score",
        "score",
        "strength_score",
        "support_score",
        "support_ratio",
    )

    for key in candidate_keys:
        value = weighted_strength_judgment.get(key)

        if isinstance(value, (int, float)):
            return clamp_score(value)

    raise ValueError(
        "weighted_strength_judgmentから"
        "基礎スコアを取得できません。"
    )


def extract_root_evidence(
    weighted_root_strength: dict | None,
) -> dict:
    """
    通根情報を監査用evidenceとして保持する。

    v2ではこの値をfinal_scoreへ再加算しない。
    """
    if weighted_root_strength is None:
        return {
            "available": False,
            "applied_to_final_score": False,
            "reason": "not_available",
            "data": None,
        }

    if not isinstance(weighted_root_strength, dict):
        raise TypeError(
            "weighted_root_strengthは"
            "dict型またはNoneで指定してください。"
        )

    return {
        "available": True,
        "applied_to_final_score": False,
        "reason": (
            "already_reflected_in_"
            "weighted_strength_judgment"
        ),
        "data": weighted_root_strength,
    }


def extract_month_evidence(
    integrated_month_strength: dict | None,
) -> dict:
    """
    月令・季節情報を監査用evidenceとして保持する。

    v2ではこの値をfinal_scoreへ再加算しない。
    """
    if integrated_month_strength is None:
        return {
            "available": False,
            "applied_to_final_score": False,
            "reason": "not_available",
            "data": None,
        }

    if not isinstance(
        integrated_month_strength,
        dict,
    ):
        raise TypeError(
            "integrated_month_strengthは"
            "dict型またはNoneで指定してください。"
        )

    return {
        "available": True,
        "applied_to_final_score": False,
        "reason": (
            "already_reflected_in_"
            "weighted_strength_judgment"
        ),
        "data": integrated_month_strength,
    }


def calculate_root_adjustment(
    weighted_root_strength: dict | None,
) -> float:
    """
    v2互換関数。

    通根はweighted_strength_judgmentに
    既に反映済みなので常に0.0を返す。
    """
    extract_root_evidence(
        weighted_root_strength
    )
    return 0.0


def calculate_month_adjustment(
    integrated_month_strength: dict | None,
) -> float:
    """
    v2互換関数。

    月令・季節旺衰はweighted_strength_judgmentに
    既に反映済みなので常に0.0を返す。
    """
    extract_month_evidence(
        integrated_month_strength
    )
    return 0.0


def calculate_branch_adjustment(
    branch_relations: dict | None,
) -> float:
    """
    地支関係による追加補正。

    v2では日主強弱への方向が明示された値だけを使う。
    total_score は自動利用しない。

    対応キー:
    - strength_adjustment
    - day_master_adjustment
    - adjustment

    最大±6点。
    """
    if branch_relations is None:
        return 0.0

    if not isinstance(branch_relations, dict):
        raise TypeError(
            "branch_relationsは"
            "dict型またはNoneで指定してください。"
        )

    for key in (
        "strength_adjustment",
        "day_master_adjustment",
        "adjustment",
    ):
        value = branch_relations.get(key)

        if isinstance(value, (int, float)):
            return round(
                max(
                    -6.0,
                    min(6.0, float(value)),
                ),
                2,
            )

    return 0.0


def extract_branch_evidence(
    branch_relations: dict | None,
) -> dict:
    """
    地支関係のevidenceを作る。

    total_scoreしか存在しない場合は、
    情報として保持するが最終スコアには使わない。
    """
    if branch_relations is None:
        return {
            "available": False,
            "applied_to_final_score": False,
            "adjustment": 0.0,
            "total_score": None,
            "reason": "not_available",
            "data": None,
        }

    if not isinstance(branch_relations, dict):
        raise TypeError(
            "branch_relationsは"
            "dict型またはNoneで指定してください。"
        )

    adjustment = calculate_branch_adjustment(
        branch_relations
    )

    has_explicit_adjustment = any(
        isinstance(
            branch_relations.get(key),
            (int, float),
        )
        for key in (
            "strength_adjustment",
            "day_master_adjustment",
            "adjustment",
        )
    )

    return {
        "available": True,
        "applied_to_final_score": (
            has_explicit_adjustment
        ),
        "adjustment": adjustment,
        "total_score": branch_relations.get(
            "total_score"
        ),
        "reason": (
            "explicit_day_master_adjustment"
            if has_explicit_adjustment
            else
            "no_explicit_day_master_adjustment"
        ),
        "data": branch_relations,
    }


def calculate_transformation_adjustment(
    stem_transformation_judgment: dict | None,
) -> float:
    """
    干合化候補による限定的な追加補正。

    strong_candidate: 3.0
    possible: 1.5
    weak: 0.5
    unsupported: 0.0

    conflict severity:
    none   -> 100%
    low    -> 80%
    medium -> 50%
    high   -> 25%

    複数候補があっても最大5点。
    """
    if stem_transformation_judgment is None:
        return 0.0

    if not isinstance(
        stem_transformation_judgment,
        dict,
    ):
        raise TypeError(
            "stem_transformation_judgmentは"
            "dict型またはNoneで指定してください。"
        )

    judgments = stem_transformation_judgment.get(
        "judgments",
        [],
    )

    if not isinstance(judgments, list):
        raise TypeError(
            "stem_transformation_judgmentの"
            "judgmentsはlist型で指定してください。"
        )

    adjustment = 0.0

    severity_multiplier = {
        "none": 1.0,
        "low": 0.8,
        "medium": 0.5,
        "high": 0.25,
    }

    for judgment in judgments:
        if not isinstance(judgment, dict):
            raise TypeError(
                "transformation judgmentは"
                "dict型で指定してください。"
            )

        judgment_level = judgment.get(
            "judgment"
        )

        base_adjustment = (
            TRANSFORMATION_ADJUSTMENTS.get(
                judgment_level,
                0.0,
            )
        )

        conflict_severity = judgment.get(
            "conflict_severity",
            "none",
        )

        if conflict_severity not in (
            VALID_CONFLICT_SEVERITIES
        ):
            raise ValueError(
                "不正なconflict_severityです: "
                f"{conflict_severity}"
            )

        adjustment += (
            base_adjustment
            * severity_multiplier[
                conflict_severity
            ]
        )

    return round(
        max(
            -5.0,
            min(5.0, adjustment),
        ),
        2,
    )


def classify_final_strength(
    final_score: float,
) -> dict:
    """最終スコアから身強身弱を分類する。"""
    score = clamp_score(final_score)

    for (
        threshold,
        technical_label,
        label,
    ) in STRENGTH_THRESHOLDS:
        if score >= threshold:
            return {
                "technical_label": (
                    technical_label
                ),
                "label": label,
            }

    return {
        "technical_label": "very_weak",
        "label": "極身弱",
    }


def calculate_confidence(
    weighted_root_strength: dict | None,
    integrated_month_strength: dict | None,
    branch_relations: dict | None,
    stem_transformation_judgment: dict | None,
) -> str:
    """
    利用可能な根拠数からconfidenceを算出する。

    root/monthは再加算しないが、
    判定根拠として存在するためconfidenceには使う。
    """
    available_count = 0

    for value in (
        weighted_root_strength,
        integrated_month_strength,
        branch_relations,
        stem_transformation_judgment,
    ):
        if value is not None:
            available_count += 1

    if available_count >= 4:
        return "high"

    if available_count >= 2:
        return "medium"

    return "low"


def evaluate_final_strength_judgment(
    weighted_strength_judgment: dict,
    weighted_root_strength: dict | None = None,
    integrated_month_strength: dict | None = None,
    branch_relations: dict | None = None,
    stem_transformation_judgment: dict | None = None,
) -> dict:
    """
    身強身弱の最終統合判定 v2。

    base_score:
        weighted_strength_judgmentのfinal_score。
        五行・通根・月令を既に含む。

    final_score:
        base_score
        + branch_adjustment
        + transformation_adjustment

    root/monthは二重計上しない。
    """
    base_score = extract_base_score(
        weighted_strength_judgment
    )

    root_evidence = extract_root_evidence(
        weighted_root_strength
    )

    month_evidence = extract_month_evidence(
        integrated_month_strength
    )

    branch_evidence = extract_branch_evidence(
        branch_relations
    )

    root_adjustment = 0.0
    month_adjustment = 0.0

    branch_adjustment = branch_evidence[
        "adjustment"
    ]

    transformation_adjustment = (
        calculate_transformation_adjustment(
            stem_transformation_judgment
        )
    )

    adjustment_total = round(
        branch_adjustment
        + transformation_adjustment,
        2,
    )

    raw_final_score = round(
        base_score
        + adjustment_total,
        2,
    )

    final_score = clamp_score(
        raw_final_score
    )

    classification = classify_final_strength(
        final_score
    )

    confidence = calculate_confidence(
        weighted_root_strength,
        integrated_month_strength,
        branch_relations,
        stem_transformation_judgment,
    )

    return {
        "base_score": base_score,
        "root_adjustment": (
            root_adjustment
        ),
        "month_adjustment": (
            month_adjustment
        ),
        "branch_adjustment": (
            branch_adjustment
        ),
        "transformation_adjustment": (
            transformation_adjustment
        ),
        "adjustment_total": (
            adjustment_total
        ),
        "raw_final_score": (
            raw_final_score
        ),
        "final_score": final_score,
        "technical_label": (
            classification[
                "technical_label"
            ]
        ),
        "label": classification["label"],
        "confidence": confidence,
        "components": {
            "base": {
                "score": base_score,
                "contains": [
                    "weighted_five_elements",
                    "weighted_root_strength",
                    "integrated_month_strength",
                ],
            },
            "root": {
                "adjustment": 0.0,
                "available": (
                    root_evidence[
                        "available"
                    ]
                ),
                "applied_to_final_score": False,
                "reason": (
                    root_evidence["reason"]
                ),
            },
            "month": {
                "adjustment": 0.0,
                "available": (
                    month_evidence[
                        "available"
                    ]
                ),
                "applied_to_final_score": False,
                "reason": (
                    month_evidence["reason"]
                ),
            },
            "branch_relations": {
                "adjustment": (
                    branch_adjustment
                ),
                "available": (
                    branch_evidence[
                        "available"
                    ]
                ),
                "applied_to_final_score": (
                    branch_evidence[
                        "applied_to_final_score"
                    ]
                ),
                "total_score": (
                    branch_evidence[
                        "total_score"
                    ]
                ),
                "reason": (
                    branch_evidence["reason"]
                ),
            },
            "stem_transformation": {
                "adjustment": (
                    transformation_adjustment
                ),
                "available": (
                    stem_transformation_judgment
                    is not None
                ),
                "applied_to_final_score": (
                    transformation_adjustment
                    != 0.0
                ),
            },
        },
        "evidence": {
            "weighted_strength_judgment": (
                weighted_strength_judgment
            ),
            "weighted_root_strength": (
                weighted_root_strength
            ),
            "integrated_month_strength": (
                integrated_month_strength
            ),
            "branch_relations": (
                branch_relations
            ),
            "stem_transformation_judgment": (
                stem_transformation_judgment
            ),
        },
        "double_count_prevention": {
            "root_reapplied": False,
            "month_reapplied": False,
            "reason": (
                "root_and_month_are_already_"
                "included_in_weighted_"
                "strength_judgment"
            ),
        },
        "method": (
            "final_strength_judgment_v2"
        ),
        "status": (
            "provisional_final_strength_"
            "judgment_v2"
        ),
        "notes": [
            (
                "weighted_strength_judgmentの"
                "final_scoreを基礎値として使用します。"
            ),
            (
                "通根と月令は基礎値に既に"
                "反映されているため再加算しません。"
            ),
            (
                "地支関係は日主強弱への方向が"
                "明示された補正値だけを加算します。"
            ),
            (
                "branch_relation_strengthの"
                "total_score単独では日主強弱への"
                "方向を断定できないため"
                "自動加算しません。"
            ),
            (
                "干合化は完全成立を断定せず、"
                "判定確度と競合severityに応じた"
                "限定補正として扱います。"
            ),
            (
                "用神・忌神および格局判定は"
                "このモジュールには含みません。"
            ),
        ],
    }
