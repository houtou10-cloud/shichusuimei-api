"""
engine/integrated_luck.py

四柱推命
大運 × 歳運 統合評価エンジン v1

目的
----
current_luck_v1 と annual_luck_v1 を統合し、

    現在大運
    ×
    歳運
    ×
    useful_gods_v3

の関係を構造化して評価する。

v1では以下を扱う。

1. 現在大運の干支
2. 歳運の干支
3. 大運天干 × 歳運天干の五行関係
4. 大運地支 × 歳運地支の五行関係
5. 歳運の用神適合
6. 現在大運の用神適合
7. 大運・歳運の用神一致
8. 歳運通変星
9. 歳運十二運
10. 統合スコア
11. 統合レベル
12. evidence
13. reasoning

重要
----
このバージョンでは、

    干合
    支合
    三合
    方合
    冲
    刑
    害
    破

などの干支関係はまだ最終スコアへ入れない。

これらは後続バージョンで追加する。

したがって integrated_luck_v1 は
「五行・用神を中心とした統合評価」であり、
最終的な吉凶断定ではない。

Version:
    integrated_luck_v1
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from engine.annual_luck import (
    evaluate_element_against_useful_gods,
    get_branch_element,
    get_element_relationship,
)
from engine.ten_gods import (
    get_element,
)


# =========================================================
# Constants
# =========================================================


INTEGRATED_LUCK_METHOD = (
    "integrated_luck_v1"
)


INTEGRATED_LUCK_STATUS = (
    "provisional_integrated_luck_v1"
)


FIVE_ELEMENTS = {
    "木",
    "火",
    "土",
    "金",
    "水",
}


RELATION_SCORE = {
    "same": 1.0,
    "generates": 2.0,
    "generated_by": 1.0,
    "controls": -1.0,
    "controlled_by": -2.0,
    "unknown": 0.0,
}


USEFUL_RELATION_SCORE = {
    "primary_useful": 3.0,
    "secondary_useful": 2.0,
    "neutral": 0.0,
    "support_unfavorable": -2.0,
    "unknown": 0.0,
}


# =========================================================
# Validation
# =========================================================


def _validate_dict(
    value: Any,
    name: str,
) -> None:
    """
    dict型を検証する。
    """

    if not isinstance(
        value,
        dict,
    ):
        raise TypeError(
            f"{name}はdict型で指定してください。"
        )


def _validate_optional_dict(
    value: Any,
    name: str,
) -> None:
    """
    None または dict を検証する。
    """

    if (
        value is not None
        and not isinstance(
            value,
            dict,
        )
    ):
        raise TypeError(
            f"{name}はdict型またはNoneで"
            "指定してください。"
        )


def _validate_element(
    element: Optional[str],
) -> bool:
    """
    五行として有効か確認する。

    戻り値:
        True:
            有効

        False:
            None または不正値
    """

    return (
        isinstance(
            element,
            str,
        )
        and element
        in FIVE_ELEMENTS
    )


# =========================================================
# Current luck helpers
# =========================================================


def get_current_luck_pillar(
    current_luck: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """
    current_luck_v1 から
    現在大運柱を取得する。

    現在大運が存在しない場合は None。
    """

    _validate_dict(
        current_luck,
        "current_luck",
    )

    if not current_luck.get(
        "has_current_luck"
    ):
        return None

    pillar = current_luck.get(
        "current_luck_pillar"
    )

    if not isinstance(
        pillar,
        dict,
    ):
        return None

    return pillar


def get_current_luck_ganzhi(
    current_luck: Dict[str, Any],
) -> Optional[str]:
    """
    現在大運干支を取得する。
    """

    pillar = get_current_luck_pillar(
        current_luck
    )

    if pillar is None:
        return None

    ganzhi = pillar.get(
        "ganzhi"
    )

    if isinstance(
        ganzhi,
        str,
    ):
        return ganzhi

    # compatibility
    pillar_value = pillar.get(
        "pillar"
    )

    if isinstance(
        pillar_value,
        str,
    ):
        return pillar_value

    return None


def get_current_luck_elements(
    current_luck: Dict[str, Any],
) -> Dict[str, Optional[str]]:
    """
    現在大運の天干・地支五行を取得する。

    stem_element / branch_element が
    current_luck_pillar に存在しない場合は、
    stem / branch から補完する。
    """

    pillar = get_current_luck_pillar(
        current_luck
    )

    if pillar is None:
        return {
            "stem": None,
            "branch": None,
        }

    stem_element = pillar.get(
        "stem_element"
    )

    branch_element = pillar.get(
        "branch_element"
    )

    if not _validate_element(
        stem_element
    ):
        stem = pillar.get(
            "stem"
        )

        if isinstance(
            stem,
            str,
        ):
            try:
                stem_element = (
                    get_element(
                        stem
                    )
                )
            except ValueError:
                stem_element = None

    if not _validate_element(
        branch_element
    ):
        branch = pillar.get(
            "branch"
        )

        if isinstance(
            branch,
            str,
        ):
            try:
                branch_element = (
                    get_branch_element(
                        branch
                    )
                )
            except ValueError:
                branch_element = None

    if not _validate_element(
        stem_element
    ):
        stem_element = None

    if not _validate_element(
        branch_element
    ):
        branch_element = None

    return {
        "stem": stem_element,
        "branch": branch_element,
    }


# =========================================================
# Annual luck helpers
# =========================================================


def get_annual_luck_elements(
    annual_luck: Dict[str, Any],
) -> Dict[str, Optional[str]]:
    """
    annual_luck_v1 から
    天干・地支五行を取得する。
    """

    _validate_dict(
        annual_luck,
        "annual_luck",
    )

    stem_element = annual_luck.get(
        "stem_element"
    )

    branch_element = annual_luck.get(
        "branch_element"
    )

    if not _validate_element(
        stem_element
    ):
        stem = annual_luck.get(
            "stem"
        )

        if isinstance(
            stem,
            str,
        ):
            try:
                stem_element = (
                    get_element(
                        stem
                    )
                )
            except ValueError:
                stem_element = None

    if not _validate_element(
        branch_element
    ):
        branch = annual_luck.get(
            "branch"
        )

        if isinstance(
            branch,
            str,
        ):
            try:
                branch_element = (
                    get_branch_element(
                        branch
                    )
                )
            except ValueError:
                branch_element = None

    if not _validate_element(
        stem_element
    ):
        stem_element = None

    if not _validate_element(
        branch_element
    ):
        branch_element = None

    return {
        "stem": stem_element,
        "branch": branch_element,
    }


# =========================================================
# Element interaction
# =========================================================


def evaluate_element_interaction(
    source_element: Optional[str],
    target_element: Optional[str],
) -> Dict[str, Any]:
    """
    2つの五行関係を評価する。

    source:
        現在大運

    target:
        歳運

    として使用する。

    例:
        大運木 -> 歳運火
            generates

        大運金 -> 歳運火
            controlled_by
    """

    if (
        not _validate_element(
            source_element
        )
        or not _validate_element(
            target_element
        )
    ):
        return {
            "source_element": (
                source_element
            ),
            "target_element": (
                target_element
            ),
            "relationship": "unknown",
            "score": 0.0,
        }

    relationship = (
        get_element_relationship(
            source_element,
            target_element,
        )
    )

    score = RELATION_SCORE.get(
        relationship,
        0.0,
    )

    return {
        "source_element": (
            source_element
        ),
        "target_element": (
            target_element
        ),
        "relationship": (
            relationship
        ),
        "score": float(
            score
        ),
    }


def build_element_interactions(
    current_luck: Dict[str, Any],
    annual_luck: Dict[str, Any],
) -> Dict[str, Any]:
    """
    現在大運と歳運の五行関係を構築する。
    """

    current_elements = (
        get_current_luck_elements(
            current_luck
        )
    )

    annual_elements = (
        get_annual_luck_elements(
            annual_luck
        )
    )

    stem_relation = (
        evaluate_element_interaction(
            current_elements[
                "stem"
            ],
            annual_elements[
                "stem"
            ],
        )
    )

    branch_relation = (
        evaluate_element_interaction(
            current_elements[
                "branch"
            ],
            annual_elements[
                "branch"
            ],
        )
    )

    total_score = (
        stem_relation[
            "score"
        ]
        + branch_relation[
            "score"
        ]
    )

    return {
        "current_luck_elements": (
            current_elements
        ),
        "annual_luck_elements": (
            annual_elements
        ),
        "stem_relation": (
            stem_relation
        ),
        "branch_relation": (
            branch_relation
        ),
        "score": float(
            total_score
        ),
    }


# =========================================================
# Useful gods helpers
# =========================================================


def score_useful_relation(
    relation: Optional[
        Dict[str, Any]
    ],
) -> float:
    """
    useful_gods relation を
    スコアへ変換する。
    """

    if not isinstance(
        relation,
        dict,
    ):
        return 0.0

    relationship = relation.get(
        "relationship",
        "unknown",
    )

    return float(
        USEFUL_RELATION_SCORE.get(
            relationship,
            0.0,
        )
    )


def evaluate_current_luck_useful_gods(
    current_luck: Dict[str, Any],
    useful_gods: Optional[
        Dict[str, Any]
    ],
) -> Dict[str, Any]:
    """
    現在大運の天干・地支五行を
    useful_gods_v3 と比較する。
    """

    elements = (
        get_current_luck_elements(
            current_luck
        )
    )

    stem_element = elements[
        "stem"
    ]

    branch_element = elements[
        "branch"
    ]

    if _validate_element(
        stem_element
    ):
        stem_relation = (
            evaluate_element_against_useful_gods(
                stem_element,
                useful_gods,
            )
        )
    else:
        stem_relation = {
            "is_useful": None,
            "is_primary_useful": None,
            "is_unfavorable": None,
            "priority": None,
            "relationship": "unknown",
        }

    if _validate_element(
        branch_element
    ):
        branch_relation = (
            evaluate_element_against_useful_gods(
                branch_element,
                useful_gods,
            )
        )
    else:
        branch_relation = {
            "is_useful": None,
            "is_primary_useful": None,
            "is_unfavorable": None,
            "priority": None,
            "relationship": "unknown",
        }

    stem_score = (
        score_useful_relation(
            stem_relation
        )
    )

    branch_score = (
        score_useful_relation(
            branch_relation
        )
    )

    return {
        "stem_element": (
            stem_element
        ),
        "branch_element": (
            branch_element
        ),
        "stem_relation": (
            stem_relation
        ),
        "branch_relation": (
            branch_relation
        ),
        "stem_score": (
            stem_score
        ),
        "branch_score": (
            branch_score
        ),
        "score": float(
            stem_score
            + branch_score
        ),
    }


def evaluate_annual_luck_useful_gods(
    annual_luck: Dict[str, Any],
    useful_gods: Optional[
        Dict[str, Any]
    ],
) -> Dict[str, Any]:
    """
    歳運と useful_gods_v3 の関係を評価する。

    annual_luck_v1 が既に持つ
    stem_useful_relation /
    branch_useful_relation
    を優先的に利用する。

    欠けている場合は五行から再計算する。
    """

    elements = (
        get_annual_luck_elements(
            annual_luck
        )
    )

    stem_relation = annual_luck.get(
        "stem_useful_relation"
    )

    branch_relation = annual_luck.get(
        "branch_useful_relation"
    )

    if not isinstance(
        stem_relation,
        dict,
    ):
        stem_element = elements[
            "stem"
        ]

        if _validate_element(
            stem_element
        ):
            stem_relation = (
                evaluate_element_against_useful_gods(
                    stem_element,
                    useful_gods,
                )
            )
        else:
            stem_relation = {
                "relationship": "unknown",
            }

    if not isinstance(
        branch_relation,
        dict,
    ):
        branch_element = elements[
            "branch"
        ]

        if _validate_element(
            branch_element
        ):
            branch_relation = (
                evaluate_element_against_useful_gods(
                    branch_element,
                    useful_gods,
                )
            )
        else:
            branch_relation = {
                "relationship": "unknown",
            }

    stem_score = (
        score_useful_relation(
            stem_relation
        )
    )

    branch_score = (
        score_useful_relation(
            branch_relation
        )
    )

    return {
        "stem_element": (
            elements[
                "stem"
            ]
        ),
        "branch_element": (
            elements[
                "branch"
            ]
        ),
        "stem_relation": (
            stem_relation
        ),
        "branch_relation": (
            branch_relation
        ),
        "stem_score": (
            stem_score
        ),
        "branch_score": (
            branch_score
        ),
        "score": float(
            stem_score
            + branch_score
        ),
    }


# =========================================================
# Agreement
# =========================================================


def _is_useful_relation(
    relation: Any,
) -> bool:
    """
    用神側の関係か判定する。
    """

    if not isinstance(
        relation,
        dict,
    ):
        return False

    return relation.get(
        "relationship"
    ) in {
        "primary_useful",
        "secondary_useful",
    }


def _is_unfavorable_relation(
    relation: Any,
) -> bool:
    """
    忌神側の関係か判定する。
    """

    if not isinstance(
        relation,
        dict,
    ):
        return False

    return (
        relation.get(
            "relationship"
        )
        == "support_unfavorable"
    )


def evaluate_useful_gods_agreement(
    current_useful: Dict[str, Any],
    annual_useful: Dict[str, Any],
) -> Dict[str, Any]:
    """
    現在大運と歳運が、
    用神面で同じ方向を向いているか判定する。

    v1では天干・地支の4ポイントを
    単純集計する。
    """

    current_relations = [
        current_useful.get(
            "stem_relation"
        ),
        current_useful.get(
            "branch_relation"
        ),
    ]

    annual_relations = [
        annual_useful.get(
            "stem_relation"
        ),
        annual_useful.get(
            "branch_relation"
        ),
    ]

    all_relations = (
        current_relations
        + annual_relations
    )

    useful_count = sum(
        1
        for relation
        in all_relations
        if _is_useful_relation(
            relation
        )
    )

    unfavorable_count = sum(
        1
        for relation
        in all_relations
        if _is_unfavorable_relation(
            relation
        )
    )

    known_count = sum(
        1
        for relation
        in all_relations
        if (
            isinstance(
                relation,
                dict,
            )
            and relation.get(
                "relationship"
            )
            != "unknown"
        )
    )

    if known_count == 0:
        agreement_level = (
            "unknown"
        )

    elif (
        useful_count >= 3
        and unfavorable_count == 0
    ):
        agreement_level = (
            "strong_useful_alignment"
        )

    elif (
        unfavorable_count >= 3
        and useful_count == 0
    ):
        agreement_level = (
            "strong_unfavorable_alignment"
        )

    elif (
        useful_count > 0
        and unfavorable_count > 0
    ):
        agreement_level = (
            "mixed"
        )

    elif useful_count > 0:
        agreement_level = (
            "useful_alignment"
        )

    elif unfavorable_count > 0:
        agreement_level = (
            "unfavorable_alignment"
        )

    else:
        agreement_level = (
            "neutral"
        )

    return {
        "agreement_level": (
            agreement_level
        ),
        "useful_count": (
            useful_count
        ),
        "unfavorable_count": (
            unfavorable_count
        ),
        "known_count": (
            known_count
        ),
        "has_useful_alignment": (
            useful_count > 0
        ),
        "has_unfavorable_alignment": (
            unfavorable_count > 0
        ),
        "has_mixed_signal": (
            useful_count > 0
            and unfavorable_count > 0
        ),
    }


# =========================================================
# Score
# =========================================================


def calculate_integrated_score(
    *,
    element_interactions: Dict[
        str,
        Any,
    ],
    current_useful: Dict[
        str,
        Any,
    ],
    annual_useful: Dict[
        str,
        Any,
    ],
) -> Dict[str, Any]:
    """
    v1統合スコアを計算する。

    配点
    ----
    大運×歳運 五行関係:
        stem + branch

    現在大運の用神適合:
        stem + branch

    歳運の用神適合:
        stem + branch

    注意
    ----
    このスコアは内部比較用。

    占断の絶対的な吉凶値ではない。
    """

    interaction_score = float(
        element_interactions.get(
            "score",
            0.0,
        )
    )

    current_useful_score = float(
        current_useful.get(
            "score",
            0.0,
        )
    )

    annual_useful_score = float(
        annual_useful.get(
            "score",
            0.0,
        )
    )

    total_score = (
        interaction_score
        + current_useful_score
        + annual_useful_score
    )

    return {
        "element_interaction_score": (
            interaction_score
        ),
        "current_luck_useful_score": (
            current_useful_score
        ),
        "annual_luck_useful_score": (
            annual_useful_score
        ),
        "total_score": float(
            total_score
        ),
    }


def classify_integrated_level(
    score: float,
) -> str:
    """
    統合スコアをレベル化する。

    v1暫定閾値。

        >= 8:
            very_supportive

        >= 4:
            supportive

        > -4:
            mixed

        > -8:
            challenging

        <= -8:
            very_challenging
    """

    if score >= 8.0:
        return "very_supportive"

    if score >= 4.0:
        return "supportive"

    if score > -4.0:
        return "mixed"

    if score > -8.0:
        return "challenging"

    return "very_challenging"


# =========================================================
# Confidence
# =========================================================


def calculate_integrated_confidence(
    *,
    current_luck: Dict[str, Any],
    annual_luck: Dict[str, Any],
    useful_gods: Optional[
        Dict[str, Any]
    ],
) -> Dict[str, Any]:
    """
    統合評価に利用できた情報量を示す。

    占断の正しさそのものではなく、
    入力データの充足度を表す。
    """

    available = 0
    total = 3

    if get_current_luck_pillar(
        current_luck
    ) is not None:
        available += 1

    if annual_luck.get(
        "ganzhi"
    ):
        available += 1

    if isinstance(
        useful_gods,
        dict,
    ):
        available += 1

    ratio = (
        available
        / total
    )

    if ratio == 1.0:
        level = "high"
    elif ratio >= (
        2 / 3
    ):
        level = "medium"
    else:
        level = "low"

    return {
        "available_sources": (
            available
        ),
        "total_sources": (
            total
        ),
        "ratio": float(
            ratio
        ),
        "level": level,
    }


# =========================================================
# Reasoning
# =========================================================


def build_integrated_luck_reasoning(
    *,
    current_luck_ganzhi: Optional[
        str
    ],
    annual_luck_ganzhi: Optional[
        str
    ],
    element_interactions: Dict[
        str,
        Any,
    ],
    agreement: Dict[
        str,
        Any,
    ],
    score_data: Dict[
        str,
        Any,
    ],
    overall_level: str,
    annual_ten_god: Optional[str],
    annual_twelve_stage: Optional[str],
) -> List[str]:
    """
    AI鑑定用の構造化reasoningを生成する。

    吉凶を断定しすぎず、
    計算根拠を文章化する。
    """

    reasoning: List[str] = []

    if current_luck_ganzhi:
        reasoning.append(
            (
                "現在大運は"
                f"{current_luck_ganzhi}です。"
            )
        )
    else:
        reasoning.append(
            "現在大運は特定されていません。"
        )

    if annual_luck_ganzhi:
        reasoning.append(
            (
                "対象歳運は"
                f"{annual_luck_ganzhi}です。"
            )
        )

    stem_relation = (
        element_interactions.get(
            "stem_relation",
            {},
        ).get(
            "relationship",
            "unknown",
        )
    )

    branch_relation = (
        element_interactions.get(
            "branch_relation",
            {},
        ).get(
            "relationship",
            "unknown",
        )
    )

    reasoning.append(
        (
            "大運天干と歳運天干の"
            "五行関係は"
            f"{stem_relation}です。"
        )
    )

    reasoning.append(
        (
            "大運地支と歳運地支の"
            "五行関係は"
            f"{branch_relation}です。"
        )
    )

    reasoning.append(
        (
            "大運・歳運を用神面から"
            "比較した結果は"
            f"{agreement.get('agreement_level')}です。"
        )
    )

    if annual_ten_god:
        reasoning.append(
            (
                "歳運天干の通変星は"
                f"{annual_ten_god}です。"
            )
        )

    if annual_twelve_stage:
        reasoning.append(
            (
                "歳運地支の十二運は"
                f"{annual_twelve_stage}です。"
            )
        )

    reasoning.append(
        (
            "v1統合スコアは"
            f"{score_data.get('total_score')}、"
            "統合レベルは"
            f"{overall_level}です。"
        )
    )

    reasoning.append(
        (
            "この統合評価は五行・用神を"
            "中心とした暫定評価であり、"
            "干合・支合・冲・刑・害などは"
            "まだ最終スコアへ含めていません。"
        )
    )

    return reasoning


# =========================================================
# Core
# =========================================================


def build_integrated_luck(
    *,
    current_luck: Dict[str, Any],
    annual_luck: Dict[str, Any],
    useful_gods: Optional[
        Dict[str, Any]
    ] = None,
) -> Dict[str, Any]:
    """
    現在大運・歳運・用神を統合評価する。
    """

    _validate_dict(
        current_luck,
        "current_luck",
    )

    _validate_dict(
        annual_luck,
        "annual_luck",
    )

    _validate_optional_dict(
        useful_gods,
        "useful_gods",
    )

    current_luck_ganzhi = (
        get_current_luck_ganzhi(
            current_luck
        )
    )

    annual_luck_ganzhi = (
        annual_luck.get(
            "ganzhi"
        )
    )

    element_interactions = (
        build_element_interactions(
            current_luck,
            annual_luck,
        )
    )

    current_useful = (
        evaluate_current_luck_useful_gods(
            current_luck,
            useful_gods,
        )
    )

    annual_useful = (
        evaluate_annual_luck_useful_gods(
            annual_luck,
            useful_gods,
        )
    )

    agreement = (
        evaluate_useful_gods_agreement(
            current_useful,
            annual_useful,
        )
    )

    score_data = (
        calculate_integrated_score(
            element_interactions=(
                element_interactions
            ),
            current_useful=(
                current_useful
            ),
            annual_useful=(
                annual_useful
            ),
        )
    )

    overall_score = (
        score_data[
            "total_score"
        ]
    )

    overall_level = (
        classify_integrated_level(
            overall_score
        )
    )

    confidence = (
        calculate_integrated_confidence(
            current_luck=(
                current_luck
            ),
            annual_luck=(
                annual_luck
            ),
            useful_gods=(
                useful_gods
            ),
        )
    )

    annual_ten_god = (
        annual_luck.get(
            "stem_ten_god"
        )
    )

    annual_twelve_stage = (
        annual_luck.get(
            "twelve_stage"
        )
    )

    reasoning = (
        build_integrated_luck_reasoning(
            current_luck_ganzhi=(
                current_luck_ganzhi
            ),
            annual_luck_ganzhi=(
                annual_luck_ganzhi
            ),
            element_interactions=(
                element_interactions
            ),
            agreement=(
                agreement
            ),
            score_data=(
                score_data
            ),
            overall_level=(
                overall_level
            ),
            annual_ten_god=(
                annual_ten_god
            ),
            annual_twelve_stage=(
                annual_twelve_stage
            ),
        )
    )

    evidence = {
        "current_luck_ganzhi": (
            current_luck_ganzhi
        ),
        "annual_luck_ganzhi": (
            annual_luck_ganzhi
        ),
        "element_interactions": (
            element_interactions
        ),
        "current_luck_useful": (
            current_useful
        ),
        "annual_luck_useful": (
            annual_useful
        ),
        "useful_gods_agreement": (
            agreement
        ),
        "annual_ten_god": (
            annual_ten_god
        ),
        "annual_twelve_stage": (
            annual_twelve_stage
        ),
        "score": (
            score_data
        ),
    }

    return {
        "current_luck_ganzhi": (
            current_luck_ganzhi
        ),
        "annual_luck_ganzhi": (
            annual_luck_ganzhi
        ),
        "current_luck_elements": (
            element_interactions[
                "current_luck_elements"
            ]
        ),
        "annual_luck_elements": (
            element_interactions[
                "annual_luck_elements"
            ]
        ),
        "element_interactions": (
            element_interactions
        ),
        "current_luck_useful": (
            current_useful
        ),
        "annual_luck_useful": (
            annual_useful
        ),
        "useful_gods_agreement": (
            agreement
        ),
        "annual_ten_god": (
            annual_ten_god
        ),
        "annual_twelve_stage": (
            annual_twelve_stage
        ),
        "score": (
            score_data
        ),
        "overall_score": (
            overall_score
        ),
        "overall_level": (
            overall_level
        ),
        "confidence": (
            confidence
        ),
        "reasoning": (
            reasoning
        ),
        "evidence": (
            evidence
        ),
        "method": (
            INTEGRATED_LUCK_METHOD
        ),
        "status": (
            INTEGRATED_LUCK_STATUS
        ),
        "notes": [
            (
                "integrated_luck_v1 は"
                "current_luck_v1 と "
                "annual_luck_v1 を統合した"
                "暫定評価です。"
            ),
            (
                "用神評価は useful_gods_v3 "
                "を利用します。"
            ),
            (
                "統合スコアは内部比較用であり、"
                "絶対的な吉凶値ではありません。"
            ),
            (
                "干合・支合・三合・方合・冲・"
                "刑・害・破はv1の統合スコアへ"
                "まだ含めていません。"
            ),
        ],
    }


# =========================================================
# Public API
# =========================================================


def calculate_integrated_luck(
    *,
    current_luck: Dict[str, Any],
    annual_luck: Dict[str, Any],
    useful_gods: Optional[
        Dict[str, Any]
    ] = None,
) -> Dict[str, Any]:
    """
    大運 × 歳運 × 用神の統合評価を返す。

    Parameters
    ----------
    current_luck:
        current_luck_v1

    annual_luck:
        annual_luck_v1

    useful_gods:
        useful_gods_v3

    Returns
    -------
    dict
        integrated_luck_v1
    """

    return build_integrated_luck(
        current_luck=(
            current_luck
        ),
        annual_luck=(
            annual_luck
        ),
        useful_gods=(
            useful_gods
        ),
    )


def evaluate_integrated_luck(
    *,
    current_luck: Dict[str, Any],
    annual_luck: Dict[str, Any],
    useful_gods: Optional[
        Dict[str, Any]
    ] = None,
) -> Dict[str, Any]:
    """
    calculate_integrated_luck()
    の互換alias。
    """

    return calculate_integrated_luck(
        current_luck=(
            current_luck
        ),
        annual_luck=(
            annual_luck
        ),
        useful_gods=(
            useful_gods
        ),
    )


# =========================================================
# Public exports
# =========================================================


__all__ = [
    "INTEGRATED_LUCK_METHOD",
    "INTEGRATED_LUCK_STATUS",
    "FIVE_ELEMENTS",
    "RELATION_SCORE",
    "USEFUL_RELATION_SCORE",
    "get_current_luck_pillar",
    "get_current_luck_ganzhi",
    "get_current_luck_elements",
    "get_annual_luck_elements",
    "evaluate_element_interaction",
    "build_element_interactions",
    "score_useful_relation",
    "evaluate_current_luck_useful_gods",
    "evaluate_annual_luck_useful_gods",
    "evaluate_useful_gods_agreement",
    "calculate_integrated_score",
    "classify_integrated_level",
    "calculate_integrated_confidence",
    "build_integrated_luck_reasoning",
    "build_integrated_luck",
    "calculate_integrated_luck",
    "evaluate_integrated_luck",
]
