"""
格局成立判定エンジン v1。

pattern_candidates.py が抽出した「格局候補」を受け取り、
既存エンジンの次の情報を統合して暫定的な成立度を判定する。

- 格局候補
- final_strength_judgment
- 月令主蔵干の透干
- stem_transformation_judgment
- branch_relation_strength
- 流派差フラグ

重要:
v1は「古典上の格局理論を完全実装した最終版」ではない。
候補抽出と最終格局の間に、説明可能な判定レイヤーを置くことが目的。

特に以下は後続バージョンで拡張する。

- 官殺混雑
- 食神制殺
- 傷官見官
- 財多身弱
- 印綬の財破
- 偏印奪食
- 建禄格・羊刃格の詳細成立条件
- 従格・化格などの特殊格
- 地支の刑冲合害による月令損傷の詳細評価
"""


# =========================================================
# Constants
# =========================================================


VALID_ESTABLISHMENT_STATUS = {
    "not_applicable",
    "possible",
    "strong",
    "weakened",
    "requires_school_rule",
}


VALID_FINAL_JUDGMENTS = {
    "not_applicable",
    "provisional_established",
    "provisional_possible",
    "provisional_weakened",
    "requires_school_rule",
}


STANDARD_PATTERN_TECHNICAL_NAMES = {
    "direct_officer",
    "seven_killings",
    "direct_wealth",
    "indirect_wealth",
    "direct_resource",
    "indirect_resource",
    "eating_god",
    "hurting_officer",
}


SPECIAL_PATTERN_TECHNICAL_NAMES = {
    "jianlu",
    "yangren",
}


# =========================================================
# Basic helpers
# =========================================================


def clamp_score(
    value: float,
    minimum: float = 0.0,
    maximum: float = 100.0,
) -> float:
    if not isinstance(
        value,
        (int, float),
    ):
        raise TypeError(
            "valueは数値で指定してください。"
        )

    return round(
        max(
            minimum,
            min(
                maximum,
                float(value),
            ),
        ),
        2,
    )


def confidence_from_score(
    score: float,
) -> str:
    if not isinstance(
        score,
        (int, float),
    ):
        raise TypeError(
            "scoreは数値で指定してください。"
        )

    if score >= 75.0:
        return "high"

    if score >= 50.0:
        return "medium"

    return "low"


# =========================================================
# Validation
# =========================================================


def validate_pattern_candidates(
    pattern_candidates: dict,
) -> None:
    if not isinstance(
        pattern_candidates,
        dict,
    ):
        raise TypeError(
            "pattern_candidatesは"
            "dict型で指定してください。"
        )

    required_keys = {
        "has_candidate",
        "candidate_count",
        "primary_candidate",
        "candidates",
    }

    missing = (
        required_keys
        - set(
            pattern_candidates.keys()
        )
    )

    if missing:
        raise ValueError(
            "pattern_candidatesに"
            "必要なキーがありません: "
            f"{sorted(missing)}"
        )

    if not isinstance(
        pattern_candidates[
            "has_candidate"
        ],
        bool,
    ):
        raise TypeError(
            "has_candidateはbool型で"
            "指定してください。"
        )

    if not isinstance(
        pattern_candidates[
            "candidate_count"
        ],
        int,
    ):
        raise TypeError(
            "candidate_countはint型で"
            "指定してください。"
        )

    if not isinstance(
        pattern_candidates[
            "candidates"
        ],
        list,
    ):
        raise TypeError(
            "candidatesはlist型で"
            "指定してください。"
        )

    primary = pattern_candidates[
        "primary_candidate"
    ]

    if (
        primary is not None
        and not isinstance(
            primary,
            dict,
        )
    ):
        raise TypeError(
            "primary_candidateは"
            "dict型またはNoneで"
            "指定してください。"
        )


# =========================================================
# Evidence extraction
# =========================================================


def extract_final_strength_evidence(
    final_strength_judgment: dict | None,
) -> dict:
    if final_strength_judgment is None:
        return {
            "available": False,
            "final_score": None,
            "technical_label": None,
            "label": None,
            "confidence": None,
        }

    if not isinstance(
        final_strength_judgment,
        dict,
    ):
        raise TypeError(
            "final_strength_judgmentは"
            "dict型またはNoneで"
            "指定してください。"
        )

    return {
        "available": True,
        "final_score": (
            final_strength_judgment.get(
                "final_score"
            )
        ),
        "technical_label": (
            final_strength_judgment.get(
                "technical_label"
            )
        ),
        "label": (
            final_strength_judgment.get(
                "label"
            )
        ),
        "confidence": (
            final_strength_judgment.get(
                "confidence"
            )
        ),
    }


def extract_transformation_evidence(
    stem_transformation_judgment: dict | None,
) -> dict:
    if stem_transformation_judgment is None:
        return {
            "available": False,
            "has_candidate": False,
            "conflicted_count": 0,
            "overall_judgment": None,
        }

    if not isinstance(
        stem_transformation_judgment,
        dict,
    ):
        raise TypeError(
            "stem_transformation_judgmentは"
            "dict型またはNoneで"
            "指定してください。"
        )

    conflicted_count = (
        stem_transformation_judgment.get(
            "conflicted_judgment_count",
            0,
        )
    )

    if not isinstance(
        conflicted_count,
        int,
    ):
        conflicted_count = 0

    return {
        "available": True,
        "has_candidate": bool(
            stem_transformation_judgment.get(
                "has_transformation_candidate",
                False,
            )
        ),
        "conflicted_count": (
            conflicted_count
        ),
        "overall_judgment": (
            stem_transformation_judgment.get(
                "overall_judgment"
            )
        ),
    }


def extract_branch_evidence(
    branch_relation_strength: dict | None,
) -> dict:
    if branch_relation_strength is None:
        return {
            "available": False,
            "adjustment": 0.0,
            "total_score": None,
        }

    if not isinstance(
        branch_relation_strength,
        dict,
    ):
        raise TypeError(
            "branch_relation_strengthは"
            "dict型またはNoneで"
            "指定してください。"
        )

    adjustment = 0.0

    for key in (
        "strength_adjustment",
        "day_master_adjustment",
        "adjustment",
    ):
        value = (
            branch_relation_strength.get(
                key
            )
        )

        if isinstance(
            value,
            (int, float),
        ):
            adjustment = float(
                value
            )
            break

    return {
        "available": True,
        "adjustment": (
            adjustment
        ),
        "total_score": (
            branch_relation_strength.get(
                "total_score"
            )
        ),
    }


# =========================================================
# Candidate scoring
# =========================================================


def base_candidate_score(
    candidate: dict,
) -> float:
    if not isinstance(
        candidate,
        dict,
    ):
        raise TypeError(
            "candidateはdict型で"
            "指定してください。"
        )

    confidence = candidate.get(
        "confidence"
    )

    if confidence == "high":
        return 70.0

    if confidence == "medium":
        return 60.0

    if confidence == "low":
        return 50.0

    return 55.0


def exposure_adjustment(
    candidate: dict,
) -> float:
    if not isinstance(
        candidate,
        dict,
    ):
        raise TypeError(
            "candidateはdict型で"
            "指定してください。"
        )

    technical_pattern = (
        candidate.get(
            "technical_pattern"
        )
    )

    if (
        technical_pattern
        not in STANDARD_PATTERN_TECHNICAL_NAMES
    ):
        return 0.0

    if candidate.get(
        "is_exposed",
        False,
    ):
        return 10.0

    return 0.0


def school_rule_adjustment(
    candidate: dict,
) -> float:
    if not isinstance(
        candidate,
        dict,
    ):
        raise TypeError(
            "candidateはdict型で"
            "指定してください。"
        )

    if candidate.get(
        "requires_school_rule",
        False,
    ):
        return -15.0

    return 0.0


def transformation_adjustment(
    candidate: dict,
    stem_transformation_judgment: dict | None,
) -> float:
    if not isinstance(
        candidate,
        dict,
    ):
        raise TypeError(
            "candidateはdict型で"
            "指定してください。"
        )

    evidence = (
        extract_transformation_evidence(
            stem_transformation_judgment
        )
    )

    if not evidence[
        "available"
    ]:
        return 0.0

    if (
        evidence[
            "conflicted_count"
        ]
        > 0
    ):
        return -5.0

    return 0.0


def branch_adjustment(
    branch_relation_strength: dict | None,
) -> float:
    evidence = (
        extract_branch_evidence(
            branch_relation_strength
        )
    )

    if not evidence[
        "available"
    ]:
        return 0.0

    # branch_relation_strengthの
    # 明示的な日主補正値のみを利用する。
    # total_scoreは意味が異なる可能性があるため
    # 格局成立度へ直接加算しない。
    adjustment = evidence[
        "adjustment"
    ]

    if adjustment > 5.0:
        return 5.0

    if adjustment < -5.0:
        return -5.0

    return round(
        adjustment,
        2,
    )


# =========================================================
# Factors
# =========================================================


def collect_breaking_factors(
    candidate: dict,
    stem_transformation_judgment: dict | None = None,
    branch_relation_strength: dict | None = None,
) -> list[dict]:
    if not isinstance(
        candidate,
        dict,
    ):
        raise TypeError(
            "candidateはdict型で"
            "指定してください。"
        )

    factors: list[dict] = []

    if (
        candidate.get(
            "technical_pattern"
        )
        in STANDARD_PATTERN_TECHNICAL_NAMES
        and not candidate.get(
            "is_exposed",
            False,
        )
    ):
        factors.append(
            {
                "type": (
                    "main_hidden_stem_not_exposed"
                ),
                "severity": "low",
                "description": (
                    "月支主蔵干が天干へ"
                    "透出していません。"
                ),
            }
        )

    transformation = (
        extract_transformation_evidence(
            stem_transformation_judgment
        )
    )

    if (
        transformation[
            "conflicted_count"
        ]
        > 0
    ):
        factors.append(
            {
                "type": (
                    "stem_transformation_conflict"
                ),
                "severity": "medium",
                "description": (
                    "干合化判定に競合要因があります。"
                ),
            }
        )

    branches = (
        extract_branch_evidence(
            branch_relation_strength
        )
    )

    if (
        branches[
            "adjustment"
        ]
        < 0.0
    ):
        factors.append(
            {
                "type": (
                    "negative_branch_adjustment"
                ),
                "severity": (
                    "medium"
                    if branches[
                        "adjustment"
                    ] <= -3.0
                    else "low"
                ),
                "description": (
                    "地支関係に命式強度を"
                    "弱める明示的補正があります。"
                ),
                "value": (
                    branches[
                        "adjustment"
                    ]
                ),
            }
        )

    if candidate.get(
        "requires_school_rule",
        False,
    ):
        factors.append(
            {
                "type": (
                    "school_rule_dependency"
                ),
                "severity": "medium",
                "description": (
                    "この格局候補は流派差の"
                    "影響を受けます。"
                ),
            }
        )

    return factors


def collect_rescue_factors(
    candidate: dict,
    final_strength_judgment: dict | None = None,
    branch_relation_strength: dict | None = None,
) -> list[dict]:
    if not isinstance(
        candidate,
        dict,
    ):
        raise TypeError(
            "candidateはdict型で"
            "指定してください。"
        )

    factors: list[dict] = []

    if candidate.get(
        "is_exposed",
        False,
    ):
        factors.append(
            {
                "type": (
                    "main_hidden_stem_exposed"
                ),
                "strength": "medium",
                "description": (
                    "月支主蔵干が天干へ"
                    "透出しています。"
                ),
            }
        )

    strength = (
        extract_final_strength_evidence(
            final_strength_judgment
        )
    )

    if (
        strength["available"]
        and strength[
            "technical_label"
        ]
        == "balanced"
    ):
        factors.append(
            {
                "type": (
                    "balanced_day_master"
                ),
                "strength": "low",
                "description": (
                    "日主強度が中和域です。"
                ),
            }
        )

    branches = (
        extract_branch_evidence(
            branch_relation_strength
        )
    )

    if (
        branches[
            "adjustment"
        ]
        > 0.0
    ):
        factors.append(
            {
                "type": (
                    "positive_branch_adjustment"
                ),
                "strength": (
                    "medium"
                    if branches[
                        "adjustment"
                    ] >= 3.0
                    else "low"
                ),
                "description": (
                    "地支関係に命式強度を"
                    "支える明示的補正があります。"
                ),
                "value": (
                    branches[
                        "adjustment"
                    ]
                ),
            }
        )

    return factors


# =========================================================
# Classification
# =========================================================


def classify_establishment(
    candidate: dict,
    score: float,
) -> dict:
    if not isinstance(
        candidate,
        dict,
    ):
        raise TypeError(
            "candidateはdict型で"
            "指定してください。"
        )

    if not isinstance(
        score,
        (int, float),
    ):
        raise TypeError(
            "scoreは数値で指定してください。"
        )

    if candidate.get(
        "requires_school_rule",
        False,
    ):
        return {
            "establishment_status": (
                "requires_school_rule"
            ),
            "final_judgment": (
                "requires_school_rule"
            ),
        }

    if score >= 75.0:
        return {
            "establishment_status": (
                "strong"
            ),
            "final_judgment": (
                "provisional_established"
            ),
        }

    if score >= 55.0:
        return {
            "establishment_status": (
                "possible"
            ),
            "final_judgment": (
                "provisional_possible"
            ),
        }

    return {
        "establishment_status": (
            "weakened"
        ),
        "final_judgment": (
            "provisional_weakened"
        ),
    }


# =========================================================
# Single candidate judgment
# =========================================================


def judge_pattern_candidate(
    candidate: dict,
    final_strength_judgment: dict | None = None,
    stem_transformation_judgment: dict | None = None,
    branch_relation_strength: dict | None = None,
    pattern_special_rules: dict | None = None,
) -> dict:
    if not isinstance(
        candidate,
        dict,
    ):
        raise TypeError(
            "candidateはdict型で"
            "指定してください。"
        )

    base_score = (
        base_candidate_score(
            candidate
        )
    )

    exposed_adjustment = (
        exposure_adjustment(
            candidate
        )
    )

    school_adjustment = (
        school_rule_adjustment(
            candidate
        )
    )

    transform_adjustment = (
        transformation_adjustment(
            candidate,
            stem_transformation_judgment,
        )
    )

    relation_adjustment = (
        branch_adjustment(
            branch_relation_strength
        )
    )

    raw_score = round(
        base_score
        + exposed_adjustment
        + school_adjustment
        + transform_adjustment
        + relation_adjustment,
        2,
    )

    establishment_score = (
        clamp_score(
            raw_score
        )
    )

    classification = (
        classify_establishment(
            candidate,
            establishment_score,
        )
    )

    breaking_factors = (
        collect_breaking_factors(
            candidate,
            stem_transformation_judgment,
            branch_relation_strength,
        )
    )

    rescue_factors = (
        collect_rescue_factors(
            candidate,
            final_strength_judgment,
            branch_relation_strength,
        )
    )

    return {
        "pattern": candidate.get(
            "pattern"
        ),
        "technical_pattern": (
            candidate.get(
                "technical_pattern"
            )
        ),
        "pattern_group": (
            candidate.get(
                "pattern_group"
            )
        ),
        "candidate_confidence": (
            candidate.get(
                "confidence"
            )
        ),
        "candidate_status": (
            candidate.get(
                "candidate_status"
            )
        ),
        "is_exposed": bool(
            candidate.get(
                "is_exposed",
                False,
            )
        ),
        "exposure_positions": list(
            candidate.get(
                "exposure_positions",
                [],
            )
        ),
        "requires_school_rule": bool(
            candidate.get(
                "requires_school_rule",
                False,
            )
        ),
        "base_score": (
            base_score
        ),
        "exposure_adjustment": (
            exposed_adjustment
        ),
        "school_rule_adjustment": (
            school_adjustment
        ),
        "transformation_adjustment": (
            transform_adjustment
        ),
        "branch_adjustment": (
            relation_adjustment
        ),
        "raw_score": (
            raw_score
        ),
        "establishment_score": (
            establishment_score
        ),
        "establishment_status": (
            classification[
                "establishment_status"
            ]
        ),
        "breaking_factors": (
            breaking_factors
        ),
        "breaking_factor_count": len(
            breaking_factors
        ),
        "rescue_factors": (
            rescue_factors
        ),
        "rescue_factor_count": len(
            rescue_factors
        ),
        "final_judgment": (
            classification[
                "final_judgment"
            ]
        ),
        "confidence": (
            confidence_from_score(
                establishment_score
            )
        ),
        "source_candidate": (
            candidate
        ),
    }


# =========================================================
# Primary selection
# =========================================================


def judgment_priority(
    judgment: dict,
) -> tuple:
    if not isinstance(
        judgment,
        dict,
    ):
        raise TypeError(
            "judgmentはdict型で"
            "指定してください。"
        )

    status_priority = {
        "strong": 4,
        "possible": 3,
        "requires_school_rule": 2,
        "weakened": 1,
        "not_applicable": 0,
    }

    return (
        status_priority.get(
            judgment.get(
                "establishment_status"
            ),
            0,
        ),
        float(
            judgment.get(
                "establishment_score",
                0.0,
            )
        ),
    )


def determine_primary_judgment(
    judgments: list[dict],
    preferred_candidate: dict | None = None,
) -> dict | None:
    """
    複数の格局成立判定からprimary_judgmentを選択する。

    優先順位:
    1. establishment_status
    2. establishment_score
    3. preferred_candidateとの一致

    preferred_candidateは絶対指定ではなく、
    成立状態と成立スコアが同等の場合の
    タイブレークとしてのみ利用する。
    """
    if not isinstance(
        judgments,
        list,
    ):
        raise TypeError(
            "judgmentsはlist型で"
            "指定してください。"
        )

    if not judgments:
        return None

    for judgment in judgments:
        if not isinstance(
            judgment,
            dict,
        ):
            raise TypeError(
                "judgmentはdict型で"
                "指定してください。"
            )

    preferred_pattern = None

    if isinstance(
        preferred_candidate,
        dict,
    ):
        preferred_pattern = (
            preferred_candidate.get(
                "technical_pattern"
            )
        )

    def primary_priority(
        judgment: dict,
    ) -> tuple:
        base_priority = (
            judgment_priority(
                judgment
            )
        )

        preferred_bonus = (
            1
            if (
                preferred_pattern is not None
                and judgment.get(
                    "technical_pattern"
                )
                == preferred_pattern
            )
            else 0
        )

        return (
            base_priority[0],
            base_priority[1],
            preferred_bonus,
        )

    return max(
        judgments,
        key=primary_priority,
    )

# =========================================================
# Main evaluator
# =========================================================


def evaluate_pattern_judgment(
    pattern_candidates: dict,
    final_strength_judgment: dict | None = None,
    stem_transformation_judgment: dict | None = None,
    branch_relation_strength: dict | None = None,
    pattern_special_rules: dict | None = None,
) -> dict:
    """
    格局候補を暫定的な成立判定へ変換する。

    pattern_candidatesのprimary_candidateを尊重しつつ、
    全候補についてjudgmentを生成する。
    """
    validate_pattern_candidates(
        pattern_candidates
    )

    if not pattern_candidates[
        "has_candidate"
    ]:
        return {
            "has_pattern_candidate": False,
            "has_pattern": False,
            "judgment_count": 0,
            "primary_pattern": None,
            "technical_pattern": None,
            "primary_judgment": None,
            "judgments": [],
            "strong_count": 0,
            "possible_count": 0,
            "weakened_count": 0,
            "school_rule_count": 0,
            "overall_judgment": (
                "not_applicable"
            ),
            "confidence": "low",
            "evidence": {
                "pattern_candidates": (
                    pattern_candidates
                ),
                "final_strength_judgment": (
                    final_strength_judgment
                ),
                "stem_transformation_judgment": (
                    stem_transformation_judgment
                ),
                "branch_relation_strength": (
                    branch_relation_strength
                ),
                "pattern_special_rules": (
                    pattern_special_rules
                ),
            },
            "method": (
                "pattern_judgment_v1"
            ),
            "status": (
                "provisional_pattern_judgment"
            ),
            "notes": [
                (
                    "格局候補がないため"
                    "成立判定は行っていません。"
                ),
            ],
        }

    judgments = [
        judge_pattern_candidate(
            candidate,
            final_strength_judgment,
            stem_transformation_judgment,
            branch_relation_strength,
            pattern_special_rules,
        )
        for candidate in pattern_candidates[
            "candidates"
        ]
    ]

    primary_judgment = (
        determine_primary_judgment(
            judgments,
            pattern_candidates.get(
                "primary_candidate"
            ),
        )
    )

    strong_count = sum(
        1
        for judgment in judgments
        if judgment[
            "establishment_status"
        ]
        == "strong"
    )

    possible_count = sum(
        1
        for judgment in judgments
        if judgment[
            "establishment_status"
        ]
        == "possible"
    )

    weakened_count = sum(
        1
        for judgment in judgments
        if judgment[
            "establishment_status"
        ]
        == "weakened"
    )

    school_rule_count = sum(
        1
        for judgment in judgments
        if judgment[
            "establishment_status"
        ]
        == "requires_school_rule"
    )

    overall_judgment = (
        primary_judgment[
            "final_judgment"
        ]
        if primary_judgment
        else "not_applicable"
    )

    confidence = (
        primary_judgment[
            "confidence"
        ]
        if primary_judgment
        else "low"
    )

    # v1では候補が存在し、
    # primary judgmentが生成された場合に
    # has_pattern=Trueとする。
    #
    # ただしこれは「古典上の最終確定」ではなく
    # 暫定格局判定が存在する、という意味。
    has_pattern = (
        primary_judgment is not None
    )

    return {
        "has_pattern_candidate": True,
        "has_pattern": (
            has_pattern
        ),
        "judgment_count": len(
            judgments
        ),
        "primary_pattern": (
            primary_judgment[
                "pattern"
            ]
            if primary_judgment
            else None
        ),
        "technical_pattern": (
            primary_judgment[
                "technical_pattern"
            ]
            if primary_judgment
            else None
        ),
        "primary_judgment": (
            primary_judgment
        ),
        "judgments": (
            judgments
        ),
        "strong_count": (
            strong_count
        ),
        "possible_count": (
            possible_count
        ),
        "weakened_count": (
            weakened_count
        ),
        "school_rule_count": (
            school_rule_count
        ),
        "overall_judgment": (
            overall_judgment
        ),
        "confidence": (
            confidence
        ),
        "evidence": {
            "pattern_candidates": (
                pattern_candidates
            ),
            "final_strength_judgment": (
                final_strength_judgment
            ),
            "stem_transformation_judgment": (
                stem_transformation_judgment
            ),
            "branch_relation_strength": (
                branch_relation_strength
            ),
            "pattern_special_rules": (
                pattern_special_rules
            ),
        },
        "method": (
            "pattern_judgment_v1"
        ),
        "status": (
            "provisional_pattern_judgment"
        ),
        "notes": [
            (
                "pattern_candidatesで抽出した"
                "候補を基礎に判定しています。"
            ),
            (
                "普通格では月支主蔵干の"
                "透干を成立度の補助情報として"
                "評価しています。"
            ),
            (
                "地支関係は明示的な"
                "strength_adjustment等のみを"
                "利用し、total_scoreは"
                "直接加算していません。"
            ),
            (
                "干合化の競合は"
                "成立度を弱める要因として"
                "限定的に反映しています。"
            ),
            (
                "建禄格・羊刃格などの"
                "流派差は確定せず"
                "フラグとして保持します。"
            ),
            (
                "官殺混雑・食神制殺・"
                "傷官見官・財多身弱などは"
                "後続バージョンで実装します。"
            ),
        ],
    }
