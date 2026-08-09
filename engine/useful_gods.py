"""
用神・喜神・忌神候補判定エンジン v1。

目的:
- final_strength_judgment の身強身弱を主軸にする
- weighted_five_elements の五行量を補助情報として使う
- pattern_judgment_v2 を evidence として保持する
- 扶抑法を中心に「候補」を返す
- 調候・通関・格局用神はまだ断定しない

重要:
この v1 は用神を古典上の最終確定として断定するものではない。
扶抑法による候補選定を説明可能な形で返すための
暫定エンジンである。

後続版で追加予定:
- 調候用神
- 通関用神
- 格局用神
- 化格・従格専用ルール
- 月令・季節旺衰を直接使った優先順位補正
- 天干透出・通根による用神力量評価
"""

from __future__ import annotations

from typing import Any


USEFUL_GODS_METHOD = (
    "useful_gods_v1"
)

USEFUL_GODS_STATUS = (
    "provisional_useful_gods"
)


ELEMENTS = (
    "木",
    "火",
    "土",
    "金",
    "水",
)


STEM_TO_ELEMENT = {
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


GENERATES = {
    "木": "火",
    "火": "土",
    "土": "金",
    "金": "水",
    "水": "木",
}


GENERATED_BY = {
    value: key
    for key, value in GENERATES.items()
}


CONTROLS = {
    "木": "土",
    "火": "金",
    "土": "水",
    "金": "木",
    "水": "火",
}


CONTROLLED_BY = {
    value: key
    for key, value in CONTROLS.items()
}


STRONG_LABELS = {
    "strong",
    "very_strong",
    "extremely_strong",
}


WEAK_LABELS = {
    "weak",
    "very_weak",
    "extremely_weak",
}


BALANCED_LABELS = {
    "balanced",
    "neutral",
}


def _is_number(
    value: Any,
) -> bool:
    return (
        isinstance(
            value,
            (int, float),
        )
        and not isinstance(
            value,
            bool,
        )
    )


def _validate_element(
    element: str,
) -> None:
    if element not in ELEMENTS:
        raise ValueError(
            f"不正な五行です: {element}"
        )


def get_day_master_element(
    day_master_stem: str,
) -> str:
    """
    日干から日主五行を返す。
    """
    if not isinstance(
        day_master_stem,
        str,
    ):
        raise TypeError(
            "day_master_stemはstr型で"
            "指定してください。"
        )

    if (
        day_master_stem
        not in STEM_TO_ELEMENT
    ):
        raise ValueError(
            "不正な日干です: "
            f"{day_master_stem}"
        )

    return STEM_TO_ELEMENT[
        day_master_stem
    ]


def get_element_relations(
    day_element: str,
) -> dict:
    """
    日主五行から扶抑関係を返す。

    self:
        日主と同じ五行
    resource:
        日主を生じる五行
    output:
        日主が生じる五行
    wealth:
        日主が剋す五行
    officer:
        日主を剋す五行
    """
    _validate_element(
        day_element
    )

    return {
        "self": day_element,
        "resource": GENERATED_BY[
            day_element
        ],
        "output": GENERATES[
            day_element
        ],
        "wealth": CONTROLS[
            day_element
        ],
        "officer": CONTROLLED_BY[
            day_element
        ],
    }


def validate_weighted_five_elements(
    weighted_five_elements: dict,
) -> None:
    """
    weighted_five_elements の最低限の構造を検証。
    """
    if not isinstance(
        weighted_five_elements,
        dict,
    ):
        raise TypeError(
            "weighted_five_elementsは"
            "dict型で指定してください。"
        )

    scores = weighted_five_elements.get(
        "scores"
    )

    if not isinstance(
        scores,
        dict,
    ):
        raise ValueError(
            "weighted_five_elementsに"
            "scoresがありません。"
        )

    for element in ELEMENTS:
        value = scores.get(
            element
        )

        if not _is_number(
            value
        ):
            raise ValueError(
                "weighted_five_elementsの"
                f"scores[{element}]は"
                "数値で指定してください。"
            )


def extract_element_scores(
    weighted_five_elements: dict,
) -> dict[str, float]:
    """
    五行スコアをfloatで正規化して返す。
    """
    validate_weighted_five_elements(
        weighted_five_elements
    )

    scores = weighted_five_elements[
        "scores"
    ]

    return {
        element: float(
            scores[element]
        )
        for element in ELEMENTS
    }


def extract_strength_evidence(
    final_strength_judgment: dict,
) -> dict:
    """
    final_strength_judgment から
    用神判定に必要な情報を抽出する。
    """
    if not isinstance(
        final_strength_judgment,
        dict,
    ):
        raise TypeError(
            "final_strength_judgmentは"
            "dict型で指定してください。"
        )

    label = final_strength_judgment.get(
        "technical_label"
    )

    score = final_strength_judgment.get(
        "final_score"
    )

    confidence = (
        final_strength_judgment.get(
            "confidence"
        )
    )

    if (
        label is not None
        and not isinstance(
            label,
            str,
        )
    ):
        raise TypeError(
            "technical_labelはstr型または"
            "Noneで指定してください。"
        )

    if (
        score is not None
        and not _is_number(
            score
        )
    ):
        raise TypeError(
            "final_scoreは数値または"
            "Noneで指定してください。"
        )

    return {
        "technical_label": label,
        "final_score": (
            float(score)
            if _is_number(score)
            else None
        ),
        "confidence": confidence,
    }


def classify_strength_for_useful_gods(
    final_strength_judgment: dict,
) -> str:
    """
    用神候補選定用に身強身弱を
    strong / weak / balanced に正規化する。

    technical_labelを優先し、
    不明な場合のみfinal_scoreを補助利用する。
    """
    evidence = (
        extract_strength_evidence(
            final_strength_judgment
        )
    )

    label = evidence[
        "technical_label"
    ]

    if label in STRONG_LABELS:
        return "strong"

    if label in WEAK_LABELS:
        return "weak"

    if label in BALANCED_LABELS:
        return "balanced"

    score = evidence[
        "final_score"
    ]

    if score is None:
        return "balanced"

    if score >= 55.0:
        return "strong"

    if score < 45.0:
        return "weak"

    return "balanced"


def rank_elements_by_score(
    elements: list[str],
    element_scores: dict[str, float],
    *,
    ascending: bool = True,
) -> list[str]:
    """
    指定五行を五行量で順位づけする。

    ascending=True:
        少ない五行を優先
    """
    if not isinstance(
        elements,
        list,
    ):
        raise TypeError(
            "elementsはlist型で"
            "指定してください。"
        )

    for element in elements:
        _validate_element(
            element
        )

    return sorted(
        elements,
        key=lambda element: (
            element_scores[
                element
            ],
            ELEMENTS.index(
                element
            ),
        ),
        reverse=not ascending,
    )


def build_fuyoku_candidates(
    day_element: str,
    strength_class: str,
    element_scores: dict[str, float],
) -> dict:
    """
    扶抑法による候補グループを作る。

    weak:
        日主を助ける印星・比劫を喜ぶ。
        日主をさらに漏洩・消耗・剋する
        食傷・財・官殺を忌む。

    strong:
        日主の力を泄・消耗・剋する
        食傷・財・官殺を喜ぶ。
        印星・比劫を忌む。

    balanced:
        一律の扶抑用神を断定せず、
        五行量が少ない側から候補を提示する。
        忌神は空とする。
    """
    _validate_element(
        day_element
    )

    if strength_class not in {
        "strong",
        "weak",
        "balanced",
    }:
        raise ValueError(
            "不正なstrength_classです: "
            f"{strength_class}"
        )

    relations = (
        get_element_relations(
            day_element
        )
    )

    if strength_class == "weak":
        favorable = [
            relations["resource"],
            relations["self"],
        ]

        unfavorable = [
            relations["output"],
            relations["wealth"],
            relations["officer"],
        ]

        favorable = (
            rank_elements_by_score(
                favorable,
                element_scores,
                ascending=True,
            )
        )

        unfavorable = (
            rank_elements_by_score(
                unfavorable,
                element_scores,
                ascending=False,
            )
        )

        return {
            "favorable_elements": favorable,
            "unfavorable_elements": unfavorable,
            "neutral_elements": [],
            "selection_basis": (
                "weak_day_master_support"
            ),
        }

    if strength_class == "strong":
        favorable = [
            relations["output"],
            relations["wealth"],
            relations["officer"],
        ]

        unfavorable = [
            relations["resource"],
            relations["self"],
        ]

        favorable = (
            rank_elements_by_score(
                favorable,
                element_scores,
                ascending=True,
            )
        )

        unfavorable = (
            rank_elements_by_score(
                unfavorable,
                element_scores,
                ascending=False,
            )
        )

        return {
            "favorable_elements": favorable,
            "unfavorable_elements": unfavorable,
            "neutral_elements": [],
            "selection_basis": (
                "strong_day_master_drain"
            ),
        }

    ranked_all = (
        rank_elements_by_score(
            list(
                ELEMENTS
            ),
            element_scores,
            ascending=True,
        )
    )

    return {
        "favorable_elements": (
            ranked_all[:2]
        ),
        "unfavorable_elements": [],
        "neutral_elements": (
            ranked_all[2:]
        ),
        "selection_basis": (
            "balanced_day_master_scarcity"
        ),
    }


def calculate_element_role(
    element: str,
    relations: dict,
) -> str:
    """
    五行が日主に対してどの役割か返す。
    """
    _validate_element(
        element
    )

    for role, related_element in (
        relations.items()
    ):
        if related_element == element:
            return role

    raise ValueError(
        f"五行役割を特定できません: {element}"
    )


def build_candidate_details(
    elements: list[str],
    *,
    category: str,
    element_scores: dict[str, float],
    relations: dict,
) -> list[dict]:
    """
    用神候補等の説明用詳細を作る。
    """
    result: list[dict] = []

    for index, element in enumerate(
        elements,
        start=1,
    ):
        result.append(
            {
                "element": element,
                "priority": index,
                "category": category,
                "day_master_relation": (
                    calculate_element_role(
                        element,
                        relations,
                    )
                ),
                "weighted_score": round(
                    element_scores[
                        element
                    ],
                    4,
                ),
            }
        )

    return result


def determine_confidence(
    strength_class: str,
    final_strength_judgment: dict,
    pattern_judgment: dict | None,
) -> str:
    """
    v1の用神候補信頼度。

    balanced は扶抑だけでは決めにくいため
    原則 medium 以下にする。
    """
    strength_evidence = (
        extract_strength_evidence(
            final_strength_judgment
        )
    )

    strength_confidence = (
        strength_evidence.get(
            "confidence"
        )
    )

    if strength_class == "balanced":
        if strength_confidence == "low":
            return "low"

        return "medium"

    if pattern_judgment is None:
        if strength_confidence == "high":
            return "medium"

        return "low"

    if not isinstance(
        pattern_judgment,
        dict,
    ):
        raise TypeError(
            "pattern_judgmentはdict型または"
            "Noneで指定してください。"
        )

    pattern_confidence = (
        pattern_judgment.get(
            "confidence"
        )
    )

    if (
        strength_confidence == "high"
        and pattern_confidence in {
            "high",
            "medium",
        }
    ):
        return "high"

    if (
        strength_confidence in {
            "high",
            "medium",
        }
    ):
        return "medium"

    return "low"


def build_pattern_evidence(
    pattern_judgment: dict | None,
) -> dict:
    """
    pattern_judgment_v2 の主要情報を
    evidence向けに抜き出す。

    v1では格局による用神の直接変更はしない。
    """
    if pattern_judgment is None:
        return {
            "available": False,
            "primary_pattern": None,
            "technical_pattern": None,
            "overall_judgment": None,
            "confidence": None,
        }

    if not isinstance(
        pattern_judgment,
        dict,
    ):
        raise TypeError(
            "pattern_judgmentはdict型または"
            "Noneで指定してください。"
        )

    return {
        "available": True,
        "primary_pattern": (
            pattern_judgment.get(
                "primary_pattern"
            )
        ),
        "technical_pattern": (
            pattern_judgment.get(
                "technical_pattern"
            )
        ),
        "overall_judgment": (
            pattern_judgment.get(
                "overall_judgment"
            )
        ),
        "confidence": (
            pattern_judgment.get(
                "confidence"
            )
        ),
    }


def evaluate_useful_gods(
    day_master_stem: str,
    weighted_five_elements: dict,
    final_strength_judgment: dict,
    pattern_judgment: dict | None = None,
) -> dict:
    """
    扶抑法を中心に用神・喜神・忌神候補を返す。

    Parameters
    ----------
    day_master_stem:
        日干。例: "乙"

    weighted_five_elements:
        weighted_five_elements.py の戻り値。
        scoresキーを利用する。

    final_strength_judgment:
        final_strength_judgment.py の戻り値。

    pattern_judgment:
        pattern_judgment_v2 の戻り値。
        v1では evidence と信頼度補助に利用し、
        用神候補を直接変更しない。
    """
    day_element = (
        get_day_master_element(
            day_master_stem
        )
    )

    element_scores = (
        extract_element_scores(
            weighted_five_elements
        )
    )

    strength_evidence = (
        extract_strength_evidence(
            final_strength_judgment
        )
    )

    strength_class = (
        classify_strength_for_useful_gods(
            final_strength_judgment
        )
    )

    relations = (
        get_element_relations(
            day_element
        )
    )

    candidates = (
        build_fuyoku_candidates(
            day_element,
            strength_class,
            element_scores,
        )
    )

    favorable_elements = (
        candidates[
            "favorable_elements"
        ]
    )

    unfavorable_elements = (
        candidates[
            "unfavorable_elements"
        ]
    )

    neutral_elements = (
        candidates[
            "neutral_elements"
        ]
    )

    primary_useful_element = (
        favorable_elements[0]
        if favorable_elements
        else None
    )

    secondary_favorable_elements = (
        favorable_elements[1:]
    )

    primary_unfavorable_element = (
        unfavorable_elements[0]
        if unfavorable_elements
        else None
    )

    confidence = (
        determine_confidence(
            strength_class,
            final_strength_judgment,
            pattern_judgment,
        )
    )

    pattern_evidence = (
        build_pattern_evidence(
            pattern_judgment
        )
    )

    useful_candidates = (
        build_candidate_details(
            favorable_elements,
            category="favorable",
            element_scores=element_scores,
            relations=relations,
        )
    )

    unfavorable_candidates = (
        build_candidate_details(
            unfavorable_elements,
            category="unfavorable",
            element_scores=element_scores,
            relations=relations,
        )
    )

    neutral_candidates = (
        build_candidate_details(
            neutral_elements,
            category="neutral",
            element_scores=element_scores,
            relations=relations,
        )
    )

    if strength_class == "weak":
        reasoning = [
            (
                "日主を身弱系と判定したため、"
                "扶抑法では日主を生じる五行と"
                "同類五行を優先候補とします。"
            ),
            (
                "候補内ではweighted_five_elementsの"
                "スコアが少ない五行を優先しています。"
            ),
        ]
    elif strength_class == "strong":
        reasoning = [
            (
                "日主を身強系と判定したため、"
                "扶抑法では泄・財・官殺に相当する"
                "五行を優先候補とします。"
            ),
            (
                "候補内ではweighted_five_elementsの"
                "スコアが少ない五行を優先しています。"
            ),
        ]
    else:
        reasoning = [
            (
                "日主が中和域のため、扶抑法だけでは"
                "唯一の用神を強く断定しません。"
            ),
            (
                "v1では五行量の少ない五行を"
                "暫定候補として提示します。"
            ),
        ]

    return {
        "has_useful_candidate": (
            primary_useful_element
            is not None
        ),
        "primary_useful_element": (
            primary_useful_element
        ),
        "secondary_favorable_elements": (
            secondary_favorable_elements
        ),
        "favorable_elements": (
            favorable_elements
        ),
        "primary_unfavorable_element": (
            primary_unfavorable_element
        ),
        "unfavorable_elements": (
            unfavorable_elements
        ),
        "neutral_elements": (
            neutral_elements
        ),
        "useful_candidates": (
            useful_candidates
        ),
        "unfavorable_candidates": (
            unfavorable_candidates
        ),
        "neutral_candidates": (
            neutral_candidates
        ),
        "day_master_stem": (
            day_master_stem
        ),
        "day_master_element": (
            day_element
        ),
        "strength_class": (
            strength_class
        ),
        "selection_basis": (
            candidates[
                "selection_basis"
            ]
        ),
        "confidence": (
            confidence
        ),
        "relations": relations,
        "element_scores": (
            element_scores
        ),
        "reasoning": reasoning,
        "evidence": {
            "weighted_five_elements": (
                weighted_five_elements
            ),
            "final_strength_judgment": (
                final_strength_judgment
            ),
            "strength_summary": (
                strength_evidence
            ),
            "pattern_judgment": (
                pattern_judgment
            ),
            "pattern_summary": (
                pattern_evidence
            ),
        },
        "method": USEFUL_GODS_METHOD,
        "status": USEFUL_GODS_STATUS,
        "notes": [
            (
                "v1は扶抑法を中心とした"
                "用神候補判定です。"
            ),
            (
                "primary_useful_elementは"
                "古典上の最終確定用神ではなく、"
                "現時点の優先候補です。"
            ),
            (
                "調候用神・通関用神・格局用神は"
                "後続バージョンで別レイヤーとして"
                "評価します。"
            ),
            (
                "pattern_judgment_v2はv1では"
                "証拠情報と信頼度補助に利用し、"
                "候補五行を直接変更しません。"
            ),
            (
                "weighted_five_elementsのスコアは"
                "候補内の優先順位付けに利用します。"
            ),
        ],
    }


# =========================================================
# useful_gods_v2 integration
# =========================================================


USEFUL_GODS_V2_METHOD = (
    "useful_gods_v2"
)

USEFUL_GODS_V2_STATUS = (
    "provisional_useful_gods_v2"
)


SUPPORT_FAVORABLE_WEIGHTS = (
    3.0,
    2.0,
    1.0,
)

SUPPORT_UNFAVORABLE_WEIGHTS = (
    -2.5,
    -1.5,
    -1.0,
)

CLIMATE_WEIGHTS = (
    3.0,
    1.5,
    1.0,
)

AGREEMENT_BONUS = 2.0


def validate_climate_useful_gods_result(
    climate_useful_gods: dict,
) -> None:
    """
    climate_useful_gods_v1 の最低限の構造を検証する。
    """
    if not isinstance(
        climate_useful_gods,
        dict,
    ):
        raise TypeError(
            "climate_useful_godsは"
            "dict型で指定してください。"
        )

    climate_elements = (
        climate_useful_gods.get(
            "climate_elements"
        )
    )

    if not isinstance(
        climate_elements,
        list,
    ):
        raise ValueError(
            "climate_useful_godsに"
            "climate_elementsがありません。"
        )

    for element in climate_elements:
        _validate_element(
            element
        )

    primary = (
        climate_useful_gods.get(
            "primary_climate_element"
        )
    )

    if (
        primary is not None
        and primary not in ELEMENTS
    ):
        raise ValueError(
            "不正なprimary_climate_elementです: "
            f"{primary}"
        )


def build_support_balance_scores(
    support_balance: dict,
) -> dict[str, float]:
    """
    useful_gods_v1 の扶抑結果を
    統合用スコアへ変換する。

    favorable:
        優先順位順に +3 / +2 / +1

    unfavorable:
        優先順位順に -2.5 / -1.5 / -1

    neutral:
        0
    """
    if not isinstance(
        support_balance,
        dict,
    ):
        raise TypeError(
            "support_balanceはdict型で"
            "指定してください。"
        )

    scores = {
        element: 0.0
        for element in ELEMENTS
    }

    favorable = support_balance.get(
        "favorable_elements",
        [],
    )

    unfavorable = support_balance.get(
        "unfavorable_elements",
        [],
    )

    if not isinstance(
        favorable,
        list,
    ):
        raise TypeError(
            "favorable_elementsはlist型で"
            "指定してください。"
        )

    if not isinstance(
        unfavorable,
        list,
    ):
        raise TypeError(
            "unfavorable_elementsはlist型で"
            "指定してください。"
        )

    for index, element in enumerate(
        favorable
    ):
        _validate_element(
            element
        )

        weight = (
            SUPPORT_FAVORABLE_WEIGHTS[
                min(
                    index,
                    len(
                        SUPPORT_FAVORABLE_WEIGHTS
                    )
                    - 1,
                )
            ]
        )

        scores[
            element
        ] += weight

    for index, element in enumerate(
        unfavorable
    ):
        _validate_element(
            element
        )

        weight = (
            SUPPORT_UNFAVORABLE_WEIGHTS[
                min(
                    index,
                    len(
                        SUPPORT_UNFAVORABLE_WEIGHTS
                    )
                    - 1,
                )
            ]
        )

        scores[
            element
        ] += weight

    return {
        element: round(
            score,
            2,
        )
        for element, score
        in scores.items()
    }


def build_climate_integration_scores(
    climate_useful_gods: dict,
) -> dict[str, float]:
    """
    climate_useful_gods_v1 の候補順位を
    useful_gods_v2 統合用スコアへ変換する。
    """
    validate_climate_useful_gods_result(
        climate_useful_gods
    )

    scores = {
        element: 0.0
        for element in ELEMENTS
    }

    climate_elements = (
        climate_useful_gods[
            "climate_elements"
        ]
    )

    for index, element in enumerate(
        climate_elements
    ):
        weight = (
            CLIMATE_WEIGHTS[
                min(
                    index,
                    len(
                        CLIMATE_WEIGHTS
                    )
                    - 1,
                )
            ]
        )

        scores[
            element
        ] += weight

    return {
        element: round(
            score,
            2,
        )
        for element, score
        in scores.items()
    }


def evaluate_useful_gods_agreement(
    support_balance: dict,
    climate_useful_gods: dict,
) -> dict:
    """
    扶抑用神と調候用神の一致・競合を評価する。

    agreed_elements:
        扶抑で favorable かつ
        調候でも候補となる五行。

    conflicted_elements:
        扶抑で unfavorable だが
        調候では候補となる五行。
    """
    if not isinstance(
        support_balance,
        dict,
    ):
        raise TypeError(
            "support_balanceはdict型で"
            "指定してください。"
        )

    validate_climate_useful_gods_result(
        climate_useful_gods
    )

    favorable = support_balance.get(
        "favorable_elements",
        [],
    )

    unfavorable = support_balance.get(
        "unfavorable_elements",
        [],
    )

    climate_elements = (
        climate_useful_gods[
            "climate_elements"
        ]
    )

    favorable_set = set(
        favorable
    )

    unfavorable_set = set(
        unfavorable
    )

    climate_set = set(
        climate_elements
    )

    agreed_elements = [
        element
        for element in ELEMENTS
        if (
            element
            in favorable_set
            and element
            in climate_set
        )
    ]

    conflicted_elements = [
        element
        for element in ELEMENTS
        if (
            element
            in unfavorable_set
            and element
            in climate_set
        )
    ]

    if agreed_elements:
        agreement_level = (
            "strong_agreement"
            if (
                support_balance.get(
                    "primary_useful_element"
                )
                == climate_useful_gods.get(
                    "primary_climate_element"
                )
            )
            else "partial_agreement"
        )
    elif conflicted_elements:
        agreement_level = "conflict"
    elif climate_elements:
        agreement_level = "independent"
    else:
        agreement_level = (
            "support_balance_only"
        )

    return {
        "has_agreement": bool(
            agreed_elements
        ),
        "has_conflict": bool(
            conflicted_elements
        ),
        "agreement_level": (
            agreement_level
        ),
        "agreed_elements": (
            agreed_elements
        ),
        "conflicted_elements": (
            conflicted_elements
        ),
        "support_primary_element": (
            support_balance.get(
                "primary_useful_element"
            )
        ),
        "climate_primary_element": (
            climate_useful_gods.get(
                "primary_climate_element"
            )
        ),
    }


def build_integrated_element_scores(
    support_balance: dict,
    climate_useful_gods: dict,
    agreement: dict,
) -> dict[str, float]:
    """
    扶抑・調候・一致ボーナスを統合する。
    """
    support_scores = (
        build_support_balance_scores(
            support_balance
        )
    )

    climate_scores = (
        build_climate_integration_scores(
            climate_useful_gods
        )
    )

    agreed_elements = set(
        agreement.get(
            "agreed_elements",
            [],
        )
    )

    scores: dict[str, float] = {}

    for element in ELEMENTS:
        score = (
            support_scores[element]
            + climate_scores[element]
        )

        if element in agreed_elements:
            score += AGREEMENT_BONUS

        scores[element] = round(
            score,
            2,
        )

    return scores


def rank_integrated_useful_elements(
    integrated_scores: dict[str, float],
) -> list[str]:
    """
    統合スコアが正の五行を
    高い順に用神候補として返す。
    """
    if not isinstance(
        integrated_scores,
        dict,
    ):
        raise TypeError(
            "integrated_scoresはdict型で"
            "指定してください。"
        )

    candidates: list[str] = []

    for element in ELEMENTS:
        score = integrated_scores.get(
            element
        )

        if not _is_number(
            score
        ):
            raise ValueError(
                "integrated_scoresの"
                f"{element}は数値で"
                "指定してください。"
            )

        if float(
            score
        ) > 0.0:
            candidates.append(
                element
            )

    return sorted(
        candidates,
        key=lambda element: (
            -float(
                integrated_scores[
                    element
                ]
            ),
            ELEMENTS.index(
                element
            ),
        ),
    )


def build_integrated_candidate_details(
    ranked_elements: list[str],
    integrated_scores: dict[str, float],
    support_balance: dict,
    climate_useful_gods: dict,
    agreement: dict,
) -> list[dict]:
    """
    useful_gods_v2 最終候補の詳細を作る。
    """
    if not isinstance(
        ranked_elements,
        list,
    ):
        raise TypeError(
            "ranked_elementsはlist型で"
            "指定してください。"
        )

    support_scores = (
        build_support_balance_scores(
            support_balance
        )
    )

    climate_scores = (
        build_climate_integration_scores(
            climate_useful_gods
        )
    )

    agreed = set(
        agreement.get(
            "agreed_elements",
            [],
        )
    )

    conflicted = set(
        agreement.get(
            "conflicted_elements",
            [],
        )
    )

    result: list[dict] = []

    for priority, element in enumerate(
        ranked_elements,
        start=1,
    ):
        result.append(
            {
                "element": element,
                "priority": priority,
                "integrated_score": (
                    integrated_scores[
                        element
                    ]
                ),
                "support_balance_score": (
                    support_scores[
                        element
                    ]
                ),
                "climate_score": (
                    climate_scores[
                        element
                    ]
                ),
                "agreement_bonus": (
                    AGREEMENT_BONUS
                    if element in agreed
                    else 0.0
                ),
                "is_agreed": (
                    element in agreed
                ),
                "is_conflicted": (
                    element in conflicted
                ),
            }
        )

    return result


def determine_useful_gods_v2_confidence(
    support_balance: dict,
    climate_useful_gods: dict,
    agreement: dict,
) -> str:
    """
    扶抑・調候の一致状況から
    v2の信頼度を決める。
    """
    support_confidence = (
        support_balance.get(
            "confidence"
        )
    )

    climate_confidence = (
        climate_useful_gods.get(
            "confidence"
        )
    )

    level = agreement.get(
        "agreement_level"
    )

    if level == "strong_agreement":
        if (
            support_confidence
            in {"high", "medium"}
            and climate_confidence
            in {"high", "medium"}
        ):
            return "high"

        return "medium"

    if level == "partial_agreement":
        return "medium"

    if level == "conflict":
        return "low"

    if level == "independent":
        if (
            support_confidence == "high"
            and climate_confidence == "high"
        ):
            return "medium"

        return "low"

    if support_confidence == "high":
        return "medium"

    return "low"


def build_useful_gods_v2_reasoning(
    support_balance: dict,
    climate_useful_gods: dict,
    agreement: dict,
    final_elements: list[str],
) -> list[str]:
    """
    統合判定の説明文。
    """
    reasoning: list[str] = []

    support_primary = (
        support_balance.get(
            "primary_useful_element"
        )
    )

    climate_primary = (
        climate_useful_gods.get(
            "primary_climate_element"
        )
    )

    if support_primary is not None:
        reasoning.append(
            "扶抑法の第一候補は"
            f"{support_primary}です。"
        )

    if climate_primary is not None:
        reasoning.append(
            "調候法の第一候補は"
            f"{climate_primary}です。"
        )
    else:
        reasoning.append(
            "調候法では強い第一候補を"
            "検出していません。"
        )

    level = agreement.get(
        "agreement_level"
    )

    if level == "strong_agreement":
        reasoning.append(
            "扶抑と調候の第一候補が一致するため、"
            "統合判定では強い一致として扱います。"
        )

    elif level == "partial_agreement":
        reasoning.append(
            "扶抑候補と調候候補に共通五行があるため、"
            "統合判定で一致ボーナスを加えます。"
        )

    elif level == "conflict":
        reasoning.append(
            "調候候補の一部が扶抑上の忌神候補と"
            "競合するため、信頼度を抑えます。"
        )

    elif level == "independent":
        reasoning.append(
            "扶抑と調候の候補は一致していませんが、"
            "直接の忌神競合も検出していません。"
        )

    else:
        reasoning.append(
            "調候上の強い候補がないため、"
            "扶抑結果を中心に統合します。"
        )

    if final_elements:
        reasoning.append(
            "統合スコアでは"
            f"{final_elements[0]}を"
            "第一候補とします。"
        )

    return reasoning


def evaluate_useful_gods_v2(
    day_master_stem: str,
    weighted_five_elements: dict,
    final_strength_judgment: dict,
    pattern_judgment: dict | None,
    climate_useful_gods: dict,
) -> dict:
    """
    扶抑用神 v1 と調候用神 v1 を統合する
    useful_gods_v2。

    既存 evaluate_useful_gods() は
    後方互換のため v1 のまま保持する。
    chart.py を v2 接続する際は
    この関数を使用する。
    """
    validate_climate_useful_gods_result(
        climate_useful_gods
    )

    support_balance = evaluate_useful_gods(
        day_master_stem,
        weighted_five_elements,
        final_strength_judgment,
        pattern_judgment,
    )

    climate_day_stem = (
        climate_useful_gods.get(
            "day_master_stem"
        )
    )

    if (
        climate_day_stem is not None
        and climate_day_stem
        != day_master_stem
    ):
        raise ValueError(
            "扶抑判定と調候判定の"
            "day_master_stemが一致しません。"
        )

    agreement = (
        evaluate_useful_gods_agreement(
            support_balance,
            climate_useful_gods,
        )
    )

    integrated_scores = (
        build_integrated_element_scores(
            support_balance,
            climate_useful_gods,
            agreement,
        )
    )

    final_elements = (
        rank_integrated_useful_elements(
            integrated_scores
        )
    )

    primary_useful_element = (
        final_elements[0]
        if final_elements
        else None
    )

    secondary_useful_elements = (
        final_elements[1:]
    )

    final_candidates = (
        build_integrated_candidate_details(
            final_elements,
            integrated_scores,
            support_balance,
            climate_useful_gods,
            agreement,
        )
    )

    confidence = (
        determine_useful_gods_v2_confidence(
            support_balance,
            climate_useful_gods,
            agreement,
        )
    )

    reasoning = (
        build_useful_gods_v2_reasoning(
            support_balance,
            climate_useful_gods,
            agreement,
            final_elements,
        )
    )

    return {
        "has_useful_candidate": (
            primary_useful_element
            is not None
        ),
        "primary_useful_element": (
            primary_useful_element
        ),
        "secondary_useful_elements": (
            secondary_useful_elements
        ),
        "final_useful_elements": (
            final_elements
        ),
        "final_candidates": (
            final_candidates
        ),
        "integrated_element_scores": (
            integrated_scores
        ),
        "support_balance": (
            support_balance
        ),
        "climate": (
            climate_useful_gods
        ),
        "agreement": (
            agreement
        ),
        "day_master_stem": (
            day_master_stem
        ),
        "day_master_element": (
            support_balance[
                "day_master_element"
            ]
        ),
        "strength_class": (
            support_balance[
                "strength_class"
            ]
        ),
        "confidence": (
            confidence
        ),
        "reasoning": (
            reasoning
        ),
        "evidence": {
            "weighted_five_elements": (
                weighted_five_elements
            ),
            "final_strength_judgment": (
                final_strength_judgment
            ),
            "pattern_judgment": (
                pattern_judgment
            ),
            "support_balance": (
                support_balance
            ),
            "climate_useful_gods": (
                climate_useful_gods
            ),
        },
        "method": (
            USEFUL_GODS_V2_METHOD
        ),
        "status": (
            USEFUL_GODS_V2_STATUS
        ),
        "notes": [
            (
                "v2は扶抑用神v1と"
                "調候用神v1を統合した"
                "暫定判定です。"
            ),
            (
                "扶抑と調候が同じ五行を支持する場合、"
                "一致ボーナスを加えます。"
            ),
            (
                "調候候補が扶抑上の忌神候補と"
                "重なる場合は競合として保持し、"
                "信頼度を抑えます。"
            ),
            (
                "通関用神・格局用神・"
                "日干別詳細調候表は"
                "後続バージョンで統合します。"
            ),
            (
                "primary_useful_elementは"
                "古典上の最終確定用神ではなく、"
                "現在の統合ルールによる第一候補です。"
            ),
        ],
    }


__all__ = [
    "USEFUL_GODS_METHOD",
    "USEFUL_GODS_STATUS",
    "ELEMENTS",
    "STEM_TO_ELEMENT",
    "GENERATES",
    "GENERATED_BY",
    "CONTROLS",
    "CONTROLLED_BY",
    "get_day_master_element",
    "get_element_relations",
    "validate_weighted_five_elements",
    "extract_element_scores",
    "extract_strength_evidence",
    "classify_strength_for_useful_gods",
    "rank_elements_by_score",
    "build_fuyoku_candidates",
    "calculate_element_role",
    "build_candidate_details",
    "determine_confidence",
    "build_pattern_evidence",
    "evaluate_useful_gods",
    "USEFUL_GODS_V2_METHOD",
    "USEFUL_GODS_V2_STATUS",
    "SUPPORT_FAVORABLE_WEIGHTS",
    "SUPPORT_UNFAVORABLE_WEIGHTS",
    "CLIMATE_WEIGHTS",
    "AGREEMENT_BONUS",
    "validate_climate_useful_gods_result",
    "build_support_balance_scores",
    "build_climate_integration_scores",
    "evaluate_useful_gods_agreement",
    "build_integrated_element_scores",
    "rank_integrated_useful_elements",
    "build_integrated_candidate_details",
    "determine_useful_gods_v2_confidence",
    "build_useful_gods_v2_reasoning",
    "evaluate_useful_gods_v2",
]
