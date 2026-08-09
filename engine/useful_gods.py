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
]
