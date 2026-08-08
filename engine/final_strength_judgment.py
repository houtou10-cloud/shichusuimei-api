"""
身強身弱の最終統合判定モジュール。

既存エンジンで計算された、

- 基礎支持率
- 通根
- 月令・季節旺衰
- 地支関係
- 天干五合・化判定

を統合し、
最終的な身強身弱を判定します。

重要:
このモジュールは各計算ロジックを
再実装するものではありません。

既存モジュールの結果を受け取り、
最終判定へ統合するレイヤーです。

v1では干合化について、
五行そのものを完全変換せず、
限定的な補正として扱います。
"""


# =========================================================
# Constants
# =========================================================


MIN_SCORE = 0.0
MAX_SCORE = 100.0


STRENGTH_THRESHOLDS = (
    (
        70.0,
        "very_strong",
        "極身強",
    ),
    (
        58.0,
        "strong",
        "身強",
    ),
    (
        43.0,
        "balanced",
        "中和",
    ),
    (
        30.0,
        "weak",
        "身弱",
    ),
    (
        0.0,
        "very_weak",
        "極身弱",
    ),
)


TRANSFORMATION_ADJUSTMENTS = {
    "strong_candidate": 3.0,
    "possible": 1.5,
    "weak": 0.5,
    "unsupported": 0.0,
}


CONFIDENCE_LEVELS = {
    "high",
    "medium",
    "low",
}


# =========================================================
# Utility
# =========================================================


def clamp_score(
    score: float,
) -> float:
    """
    スコアを0〜100へ制限します。
    """
    if not isinstance(
        score,
        (int, float),
    ):
        raise TypeError(
            "scoreは数値で指定してください。"
        )

    return round(
        max(
            MIN_SCORE,
            min(
                MAX_SCORE,
                float(score),
            ),
        ),
        2,
    )


def safe_number(
    value,
    default: float = 0.0,
) -> float:
    """
    数値を安全にfloatへ変換します。

    Noneの場合はdefaultを返します。
    """
    if value is None:
        return float(
            default
        )

    if not isinstance(
        value,
        (int, float),
    ):
        raise TypeError(
            "数値項目はintまたは"
            "float型で指定してください。"
        )

    return float(
        value
    )


# =========================================================
# Base score
# =========================================================


def extract_base_score(
    weighted_strength_judgment: dict,
) -> float:
    """
    既存の身強身弱判定から
    基礎スコアを取得します。

    複数のキー名へ対応し、
    既存APIとの互換性を持たせます。
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
        "score",
        "strength_score",
        "final_score",
        "support_score",
        "support_ratio",
    )

    for key in candidate_keys:
        value = (
            weighted_strength_judgment.get(
                key
            )
        )

        if isinstance(
            value,
            (int, float),
        ):
            return clamp_score(
                float(value)
            )

    raise ValueError(
        "weighted_strength_judgmentから"
        "基礎スコアを取得できません。"
    )


# =========================================================
# Root adjustment
# =========================================================


def calculate_root_adjustment(
    weighted_root_strength: dict | None,
) -> float:
    """
    通根による補正値を計算します。

    v1では既存結果を尊重しつつ、
    最大±8点程度に制限します。
    """
    if weighted_root_strength is None:
        return 0.0

    if not isinstance(
        weighted_root_strength,
        dict,
    ):
        raise TypeError(
            "weighted_root_strengthは"
            "dict型またはNoneで指定してください。"
        )

    if isinstance(
        weighted_root_strength.get(
            "adjustment"
        ),
        (int, float),
    ):
        adjustment = float(
            weighted_root_strength[
                "adjustment"
            ]
        )

        return round(
            max(
                -8.0,
                min(
                    8.0,
                    adjustment,
                ),
            ),
            2,
        )

    root_strength = (
        weighted_root_strength.get(
            "root_strength"
        )
        or weighted_root_strength.get(
            "strength"
        )
        or weighted_root_strength.get(
            "level"
        )
    )

    mapping = {
        "very_strong": 8.0,
        "strong": 6.0,
        "medium": 3.0,
        "moderate": 3.0,
        "weak": 1.0,
        "none": -3.0,
    }

    if root_strength in mapping:
        return mapping[
            root_strength
        ]

    has_root = (
        weighted_root_strength.get(
            "has_root"
        )
    )

    if has_root is True:
        return 3.0

    if has_root is False:
        return -3.0

    return 0.0


# =========================================================
# Month / seasonal adjustment
# =========================================================


def calculate_month_adjustment(
    integrated_month_strength: dict | None,
) -> float:
    """
    月令・季節旺衰による補正。

    月令は身強身弱判定で重要なので、
    通根より大きめの補正幅を許容します。
    """
    if integrated_month_strength is None:
        return 0.0

    if not isinstance(
        integrated_month_strength,
        dict,
    ):
        raise TypeError(
            "integrated_month_strengthは"
            "dict型またはNoneで指定してください。"
        )

    for key in (
        "adjustment",
        "month_adjustment",
        "seasonal_adjustment",
    ):
        value = (
            integrated_month_strength.get(
                key
            )
        )

        if isinstance(
            value,
            (int, float),
        ):
            return round(
                max(
                    -15.0,
                    min(
                        15.0,
                        float(value),
                    ),
                ),
                2,
            )

    level = (
        integrated_month_strength.get(
            "strength"
        )
        or integrated_month_strength.get(
            "level"
        )
        or integrated_month_strength.get(
            "month_strength"
        )
    )

    mapping = {
        "very_strong": 12.0,
        "strong": 9.0,
        "supportive": 5.0,
        "neutral": 0.0,
        "weak": -6.0,
        "very_weak": -10.0,
    }

    return mapping.get(
        level,
        0.0,
    )


# =========================================================
# Branch relation adjustment
# =========================================================


def calculate_branch_adjustment(
    branch_relations: dict | None,
) -> float:
    """
    地支関係による補正。

    v1では地支関係を補助要素として扱い、
    過大評価しないよう最大±6点に制限します。
    """
    if branch_relations is None:
        return 0.0

    if not isinstance(
        branch_relations,
        dict,
    ):
        raise TypeError(
            "branch_relationsは"
            "dict型またはNoneで指定してください。"
        )

    for key in (
        "strength_adjustment",
        "adjustment",
        "total_adjustment",
    ):
        value = (
            branch_relations.get(
                key
            )
        )

        if isinstance(
            value,
            (int, float),
        ):
            return round(
                max(
                    -6.0,
                    min(
                        6.0,
                        float(value),
                    ),
                ),
                2,
            )

    return 0.0


# =========================================================
# Transformation adjustment
# =========================================================


def calculate_transformation_adjustment(
    stem_transformation_judgment: dict | None,
) -> float:
    """
    干合化候補による補正。

    v1では化を完全成立として扱わず、
    限定的な補正に留めます。

    複数候補がある場合も
    最大±5点以内に制限します。
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

    judgments = (
        stem_transformation_judgment.get(
            "judgments",
            [],
        )
    )

    if not isinstance(
        judgments,
        list,
    ):
        raise TypeError(
            "stem_transformation_judgmentの"
            "judgmentsはlist型で指定してください。"
        )

    adjustment = 0.0

    for judgment in judgments:
        if not isinstance(
            judgment,
            dict,
        ):
            raise TypeError(
                "transformation judgmentは"
                "dict型で指定してください。"
            )

        judgment_level = (
            judgment.get(
                "judgment"
            )
        )

        base_adjustment = (
            TRANSFORMATION_ADJUSTMENTS.get(
                judgment_level,
                0.0,
            )
        )

        conflict_severity = (
            judgment.get(
                "conflict_severity",
                "none",
            )
        )

        if conflict_severity == "high":
            base_adjustment *= 0.25

        elif conflict_severity == "medium":
            base_adjustment *= 0.5

        elif conflict_severity == "low":
            base_adjustment *= 0.8

        adjustment += (
            base_adjustment
        )

    return round(
        max(
            -5.0,
            min(
                5.0,
                adjustment,
            ),
        ),
        2,
    )


# =========================================================
# Classification
# =========================================================


def classify_final_strength(
    final_score: float,
) -> dict:
    """
    最終スコアから
    身強身弱ラベルを返します。
    """
    score = clamp_score(
        final_score
    )

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

    # 通常ここには到達しません。
    return {
        "technical_label": (
            "very_weak"
        ),
        "label": "極身弱",
    }


# =========================================================
# Confidence
# =========================================================


def calculate_confidence(
    weighted_root_strength: dict | None,
    integrated_month_strength: dict | None,
    branch_relations: dict | None,
    stem_transformation_judgment: dict | None,
) -> str:
    """
    最終判定のconfidenceを算出します。

    入力情報が多いほどconfidenceを上げます。
    """
    available_count = 0

    if weighted_root_strength is not None:
        available_count += 1

    if integrated_month_strength is not None:
        available_count += 1

    if branch_relations is not None:
        available_count += 1

    if (
        stem_transformation_judgment
        is not None
    ):
        available_count += 1

    if available_count >= 4:
        return "high"

    if available_count >= 2:
        return "medium"

    return "low"


# =========================================================
# Main evaluator
# =========================================================


def evaluate_final_strength_judgment(
    weighted_strength_judgment: dict,
    weighted_root_strength: dict | None = None,
    integrated_month_strength: dict | None = None,
    branch_relations: dict | None = None,
    stem_transformation_judgment: dict | None = None,
) -> dict:
    """
    身強身弱の最終統合判定を行います。
    """
    base_score = (
        extract_base_score(
            weighted_strength_judgment
        )
    )

    root_adjustment = (
        calculate_root_adjustment(
            weighted_root_strength
        )
    )

    month_adjustment = (
        calculate_month_adjustment(
            integrated_month_strength
        )
    )

    branch_adjustment = (
        calculate_branch_adjustment(
            branch_relations
        )
    )

    transformation_adjustment = (
        calculate_transformation_adjustment(
            stem_transformation_judgment
        )
    )

    raw_final_score = (
        base_score
        + root_adjustment
        + month_adjustment
        + branch_adjustment
        + transformation_adjustment
    )

    final_score = clamp_score(
        raw_final_score
    )

    classification = (
        classify_final_strength(
            final_score
        )
    )

    confidence = (
        calculate_confidence(
            weighted_root_strength,
            integrated_month_strength,
            branch_relations,
            stem_transformation_judgment,
        )
    )

    adjustment_total = round(
        root_adjustment
        + month_adjustment
        + branch_adjustment
        + transformation_adjustment,
        2,
    )

    return {
        "base_score": (
            base_score
        ),
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
        "raw_final_score": round(
            raw_final_score,
            2,
        ),
        "final_score": (
            final_score
        ),
        "technical_label": (
            classification[
                "technical_label"
            ]
        ),
        "label": (
            classification[
                "label"
            ]
        ),
        "confidence": (
            confidence
        ),
        "components": {
            "base": {
                "score": (
                    base_score
                ),
            },
            "root": {
                "adjustment": (
                    root_adjustment
                ),
                "available": (
                    weighted_root_strength
                    is not None
                ),
            },
            "month": {
                "adjustment": (
                    month_adjustment
                ),
                "available": (
                    integrated_month_strength
                    is not None
                ),
            },
            "branch_relations": {
                "adjustment": (
                    branch_adjustment
                ),
                "available": (
                    branch_relations
                    is not None
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
            },
        },
        "method": (
            "final_strength_judgment_v1"
        ),
        "status": (
            "provisional_final_strength_judgment"
        ),
        "notes": [
            (
                "既存の身強身弱判定を基礎として、"
                "通根・月令・地支関係・干合化を"
                "統合した最終判定です。"
            ),
            (
                "月令は身強身弱への影響が大きいため、"
                "他の補助要素より大きな補正幅を"
                "許容しています。"
            ),
            (
                "地支関係はv1では補助的な"
                "補正として扱っています。"
            ),
            (
                "干合化はまだ完全成立を"
                "断定せず、限定的な補正として"
                "反映しています。"
            ),
            (
                "用神・忌神および格局判定は"
                "このモジュールには含みません。"
            ),
        ],
    }
