"""
格局用神判定モジュール v1。

目的:
pattern_judgment_v2 の格局判定を受け取り、
格局を維持・補強する観点から用神候補を返す。

このモジュールは扶抑用神・調候用神とは独立した
「格局用神」レイヤーとして扱う。

v1で扱う標準格局:
- 正官格
- 偏官格（七殺格）
- 正財格
- 偏財格
- 印綬格
- 偏印格
- 食神格
- 傷官格

特殊月令格:
- 建禄格
- 羊刃格

注意:
- 建禄格・羊刃格には流派差がある。
- 従格・化格は本モジュールでは確定しない。
- v1は「格局から見た五行候補」を返す。
- 最終用神は扶抑・調候・格局・将来の通関等を
  統合する上位モジュールで判定する。
"""


from engine.constants import (
    STEM_ELEMENTS,
)


# =========================================================
# Constants
# =========================================================


ELEMENTS = (
    "木",
    "火",
    "土",
    "金",
    "水",
)


GENERATES = {
    "木": "火",
    "火": "土",
    "土": "金",
    "金": "水",
    "水": "木",
}


CONTROLS = {
    "木": "土",
    "火": "金",
    "土": "水",
    "金": "木",
    "水": "火",
}


GENERATED_BY = {
    generated: generator
    for generator, generated
    in GENERATES.items()
}


CONTROLLED_BY = {
    controlled: controller
    for controller, controlled
    in CONTROLS.items()
}


VALID_TECHNICAL_PATTERNS = {
    "direct_officer",
    "seven_killings",
    "direct_wealth",
    "indirect_wealth",
    "direct_resource",
    "indirect_resource",
    "eating_god",
    "hurting_officer",
    "jianlu",
    "yangren",
}


PATTERN_JAPANESE = {
    "direct_officer": "正官格",
    "seven_killings": "偏官格",
    "direct_wealth": "正財格",
    "indirect_wealth": "偏財格",
    "direct_resource": "印綬格",
    "indirect_resource": "偏印格",
    "eating_god": "食神格",
    "hurting_officer": "傷官格",
    "jianlu": "建禄格",
    "yangren": "羊刃格",
}


# 格局用神の基本ルール。
#
# role は説明用の技術ラベル。
# weight は格局観点での優先度。
#
# element の具体値は日主五行から動的に計算する。
PATTERN_RULES = {
    "direct_officer": (
        {
            "relation": "resource",
            "role": "protect_officer",
            "weight": 3.0,
        },
        {
            "relation": "wealth",
            "role": "generate_officer",
            "weight": 2.0,
        },
    ),
    "seven_killings": (
        {
            "relation": "output",
            "role": "control_killings",
            "weight": 3.0,
        },
        {
            "relation": "resource",
            "role": "transform_killings",
            "weight": 2.5,
        },
    ),
    "direct_wealth": (
        {
            "relation": "output",
            "role": "generate_wealth",
            "weight": 3.0,
        },
        {
            "relation": "officer",
            "role": "protect_wealth",
            "weight": 2.0,
        },
    ),
    "indirect_wealth": (
        {
            "relation": "output",
            "role": "generate_wealth",
            "weight": 3.0,
        },
        {
            "relation": "officer",
            "role": "protect_wealth",
            "weight": 2.0,
        },
    ),
    "direct_resource": (
        {
            "relation": "officer",
            "role": "generate_resource",
            "weight": 3.0,
        },
        {
            "relation": "peer",
            "role": "support_day_master",
            "weight": 1.5,
        },
    ),
    "indirect_resource": (
        {
            "relation": "wealth",
            "role": "control_excess_resource",
            "weight": 3.0,
        },
        {
            "relation": "officer",
            "role": "generate_resource",
            "weight": 1.5,
        },
    ),
    "eating_god": (
        {
            "relation": "wealth",
            "role": "receive_output",
            "weight": 3.0,
        },
        {
            "relation": "output",
            "role": "strengthen_output",
            "weight": 1.5,
        },
    ),
    "hurting_officer": (
        {
            "relation": "wealth",
            "role": "receive_output",
            "weight": 3.0,
        },
        {
            "relation": "resource",
            "role": "moderate_hurting_officer",
            "weight": 2.5,
        },
    ),
    "jianlu": (
        {
            "relation": "output",
            "role": "drain_strong_day_master",
            "weight": 3.0,
        },
        {
            "relation": "wealth",
            "role": "use_day_master_strength",
            "weight": 2.5,
        },
        {
            "relation": "officer",
            "role": "restrain_day_master",
            "weight": 2.0,
        },
    ),
    "yangren": (
        {
            "relation": "officer",
            "role": "restrain_yangren",
            "weight": 3.0,
        },
        {
            "relation": "output",
            "role": "drain_yangren",
            "weight": 2.0,
        },
        {
            "relation": "wealth",
            "role": "use_day_master_strength",
            "weight": 1.5,
        },
    ),
}


# =========================================================
# Validation
# =========================================================


def validate_day_master_stem(
    day_master_stem: str,
) -> None:
    """
    日干を検証します。
    """
    if not isinstance(
        day_master_stem,
        str,
    ):
        raise TypeError(
            "day_master_stemはstr型で指定してください。"
        )

    if day_master_stem not in STEM_ELEMENTS:
        raise ValueError(
            f"不正な日干です: {day_master_stem}"
        )


def validate_pattern_judgment(
    pattern_judgment: dict,
) -> None:
    """
    pattern_judgmentを検証します。
    """
    if not isinstance(
        pattern_judgment,
        dict,
    ):
        raise TypeError(
            "pattern_judgmentはdict型で指定してください。"
        )


def validate_weighted_five_elements(
    weighted_five_elements: dict | None,
) -> None:
    """
    weighted_five_elementsを検証します。
    """
    if weighted_five_elements is None:
        return

    if not isinstance(
        weighted_five_elements,
        dict,
    ):
        raise TypeError(
            "weighted_five_elementsはdict型またはNoneで指定してください。"
        )

    scores = weighted_five_elements.get(
        "scores"
    )

    if scores is None:
        return

    if not isinstance(
        scores,
        dict,
    ):
        raise TypeError(
            "weighted_five_elements['scores']はdict型で指定してください。"
        )


# =========================================================
# Element relations
# =========================================================


def get_day_master_element(
    day_master_stem: str,
) -> str:
    """
    日干の五行を返します。
    """
    validate_day_master_stem(
        day_master_stem
    )

    return STEM_ELEMENTS[
        day_master_stem
    ][
        "element"
    ]


def get_element_relations(
    day_master_element: str,
) -> dict:
    """
    日主五行から五行関係を返します。

    peer:
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
    if day_master_element not in ELEMENTS:
        raise ValueError(
            f"不正な五行です: {day_master_element}"
        )

    return {
        "peer": day_master_element,
        "resource": GENERATED_BY[
            day_master_element
        ],
        "output": GENERATES[
            day_master_element
        ],
        "wealth": CONTROLS[
            day_master_element
        ],
        "officer": CONTROLLED_BY[
            day_master_element
        ],
    }


# =========================================================
# Pattern extraction
# =========================================================


def extract_pattern_info(
    pattern_judgment: dict,
) -> dict:
    """
    pattern_judgment_v2から代表格局情報を抽出します。
    """
    validate_pattern_judgment(
        pattern_judgment
    )

    primary_pattern = pattern_judgment.get(
        "primary_pattern"
    )

    technical_pattern = pattern_judgment.get(
        "technical_pattern"
    )

    primary_judgment = pattern_judgment.get(
        "primary_judgment"
    )

    if not isinstance(
        primary_judgment,
        dict,
    ):
        primary_judgment = None

    overall_judgment = pattern_judgment.get(
        "overall_judgment",
        "not_applicable",
    )

    confidence = pattern_judgment.get(
        "confidence",
        "low",
    )

    has_pattern = bool(
        pattern_judgment.get(
            "has_pattern",
            False,
        )
    )

    return {
        "has_pattern": has_pattern,
        "primary_pattern": primary_pattern,
        "technical_pattern": technical_pattern,
        "primary_judgment": primary_judgment,
        "overall_judgment": overall_judgment,
        "confidence": confidence,
    }


def is_supported_pattern(
    technical_pattern: str | None,
) -> bool:
    """
    v1で格局用神判定に対応しているか返します。
    """
    return (
        technical_pattern
        in VALID_TECHNICAL_PATTERNS
    )


# =========================================================
# Rule helpers
# =========================================================


def relation_to_element(
    relation: str,
    element_relations: dict,
) -> str:
    """
    五行関係ラベルを具体的な五行へ変換します。
    """
    if relation not in element_relations:
        raise ValueError(
            f"不正な五行関係です: {relation}"
        )

    return element_relations[
        relation
    ]


def get_pattern_rules(
    technical_pattern: str,
) -> tuple[dict, ...]:
    """
    格局ごとの用神ルールを返します。
    """
    if technical_pattern not in PATTERN_RULES:
        return ()

    return PATTERN_RULES[
        technical_pattern
    ]


def get_element_score(
    element: str,
    weighted_five_elements: dict | None,
) -> float | None:
    """
    加重五行スコアを取得します。

    スコアが利用できない場合はNoneを返します。
    """
    if weighted_five_elements is None:
        return None

    scores = weighted_five_elements.get(
        "scores"
    )

    if not isinstance(
        scores,
        dict,
    ):
        return None

    value = scores.get(
        element
    )

    if not isinstance(
        value,
        (int, float),
    ) or isinstance(
        value,
        bool,
    ):
        return None

    return float(
        value
    )


def calculate_presence_adjustment(
    element_score: float | None,
) -> float:
    """
    五行量による小さな補正値を返します。

    格局用神の主目的は格局構造なので、
    五行量は順位を逆転させすぎない程度の
    補助情報としてのみ使用します。

    少ない五行ほど若干加点し、
    極端に多い五行は若干減点します。
    """
    if element_score is None:
        return 0.0

    if element_score <= 0.0:
        return 0.5

    if element_score < 1.0:
        return 0.3

    if element_score >= 4.0:
        return -0.3

    return 0.0


def build_pattern_candidate(
    element: str,
    relation: str,
    role: str,
    base_weight: float,
    weighted_five_elements: dict | None,
) -> dict:
    """
    格局用神候補を1件作成します。
    """
    element_score = get_element_score(
        element,
        weighted_five_elements,
    )

    presence_adjustment = (
        calculate_presence_adjustment(
            element_score
        )
    )

    score = round(
        base_weight
        + presence_adjustment,
        4,
    )

    return {
        "element": element,
        "relation": relation,
        "role": role,
        "base_weight": float(
            base_weight
        ),
        "element_score": element_score,
        "presence_adjustment": (
            presence_adjustment
        ),
        "score": score,
    }


def merge_pattern_candidates(
    candidates: list[dict],
) -> list[dict]:
    """
    同一五行候補を統合します。

    同一五行が複数の役割で候補になる場合は、
    最大scoreを主スコアとし、役割を保持します。
    """
    merged: dict[str, dict] = {}

    for candidate in candidates:
        element = candidate[
            "element"
        ]

        if element not in merged:
            merged[element] = {
                "element": element,
                "score": candidate[
                    "score"
                ],
                "roles": [
                    candidate[
                        "role"
                    ],
                ],
                "relations": [
                    candidate[
                        "relation"
                    ],
                ],
                "base_weights": [
                    candidate[
                        "base_weight"
                    ],
                ],
                "element_score": candidate[
                    "element_score"
                ],
                "presence_adjustment": (
                    candidate[
                        "presence_adjustment"
                    ]
                ),
            }
            continue

        current = merged[element]

        current[
            "score"
        ] = max(
            current[
                "score"
            ],
            candidate[
                "score"
            ],
        )

        if (
            candidate[
                "role"
            ]
            not in current[
                "roles"
            ]
        ):
            current[
                "roles"
            ].append(
                candidate[
                    "role"
                ]
            )

        if (
            candidate[
                "relation"
            ]
            not in current[
                "relations"
            ]
        ):
            current[
                "relations"
            ].append(
                candidate[
                    "relation"
                ]
            )

        current[
            "base_weights"
        ].append(
            candidate[
                "base_weight"
            ]
        )

    ordered = sorted(
        merged.values(),
        key=lambda item: (
            -item[
                "score"
            ],
            ELEMENTS.index(
                item[
                    "element"
                ]
            ),
        ),
    )

    for index, item in enumerate(
        ordered,
        start=1,
    ):
        item[
            "priority"
        ] = index

    return ordered


# =========================================================
# Confidence
# =========================================================


def calculate_pattern_useful_confidence(
    pattern_info: dict,
    candidates: list[dict],
) -> str:
    """
    格局用神判定のconfidenceを返します。
    """
    if not candidates:
        return "low"

    overall = pattern_info[
        "overall_judgment"
    ]

    source_confidence = pattern_info[
        "confidence"
    ]

    if (
        overall
        == "provisional_established"
        and source_confidence == "high"
    ):
        return "high"

    if overall in {
        "provisional_established",
        "provisional_possible",
    }:
        return "medium"

    return "low"


# =========================================================
# Reasoning
# =========================================================


ROLE_MESSAGES = {
    "protect_officer": (
        "正官を保護する印星側の五行を"
        "格局用神候補としました。"
    ),
    "generate_officer": (
        "官星を生じる財星側の五行を"
        "補助候補としました。"
    ),
    "control_killings": (
        "七殺を制する食傷側の五行を"
        "格局用神候補としました。"
    ),
    "transform_killings": (
        "七殺の力を印へ流す印星側の五行を"
        "補助候補としました。"
    ),
    "generate_wealth": (
        "財星を生じる食傷側の五行を"
        "格局用神候補としました。"
    ),
    "protect_wealth": (
        "財の働きを格局内で活用するため、"
        "官星側の五行を補助候補としました。"
    ),
    "generate_resource": (
        "印星を生じる官殺側の五行を"
        "格局用神候補としました。"
    ),
    "support_day_master": (
        "印格を受ける日主側の安定要素として"
        "比劫側の五行を補助候補としました。"
    ),
    "control_excess_resource": (
        "偏印の偏りを抑える財星側の五行を"
        "格局用神候補としました。"
    ),
    "receive_output": (
        "食傷の気を財へ流す財星側の五行を"
        "格局用神候補としました。"
    ),
    "strengthen_output": (
        "食神の働きを維持する食傷側の五行を"
        "補助候補としました。"
    ),
    "moderate_hurting_officer": (
        "傷官の過剰を調整する印星側の五行を"
        "補助候補としました。"
    ),
    "drain_strong_day_master": (
        "建禄・羊刃の強い日主を洩らす"
        "食傷側の五行を候補としました。"
    ),
    "use_day_master_strength": (
        "強い日主の力を財へ使う五行を"
        "候補としました。"
    ),
    "restrain_day_master": (
        "強い日主を官殺で制する五行を"
        "候補としました。"
    ),
    "restrain_yangren": (
        "羊刃の強さを官殺で制する五行を"
        "第一候補としました。"
    ),
    "drain_yangren": (
        "羊刃の強さを食傷へ洩らす五行を"
        "補助候補としました。"
    ),
}


def build_reasoning(
    pattern_info: dict,
    candidates: list[dict],
) -> list[str]:
    """
    判定理由を文章リストで返します。
    """
    reasoning: list[str] = []

    technical_pattern = pattern_info[
        "technical_pattern"
    ]

    pattern_name = pattern_info[
        "primary_pattern"
    ]

    if pattern_name is None:
        pattern_name = PATTERN_JAPANESE.get(
            technical_pattern
        )

    if pattern_name is not None:
        reasoning.append(
            f"代表格局を{pattern_name}として評価しました。"
        )

    for candidate in candidates:
        for role in candidate[
            "roles"
        ]:
            message = ROLE_MESSAGES.get(
                role
            )

            if (
                message is not None
                and message not in reasoning
            ):
                reasoning.append(
                    message
                )

    return reasoning


# =========================================================
# Main
# =========================================================


def evaluate_pattern_useful_gods(
    day_master_stem: str,
    pattern_judgment: dict,
    weighted_five_elements: dict | None = None,
) -> dict:
    """
    格局判定から格局用神候補を評価します。

    Parameters
    ----------
    day_master_stem:
        日干。

    pattern_judgment:
        evaluate_pattern_judgment() の戻り値を想定。

    weighted_five_elements:
        calculate_weighted_five_elements() の戻り値。
        任意。存在量による軽微な補正に使用する。

    Returns
    -------
    dict
        格局用神候補と判定根拠。
    """
    validate_day_master_stem(
        day_master_stem
    )

    validate_pattern_judgment(
        pattern_judgment
    )

    validate_weighted_five_elements(
        weighted_five_elements
    )

    day_master_element = (
        get_day_master_element(
            day_master_stem
        )
    )

    element_relations = (
        get_element_relations(
            day_master_element
        )
    )

    pattern_info = extract_pattern_info(
        pattern_judgment
    )

    technical_pattern = pattern_info[
        "technical_pattern"
    ]

    has_usable_pattern = (
        pattern_info[
            "has_pattern"
        ]
        and is_supported_pattern(
            technical_pattern
        )
    )

    raw_candidates: list[dict] = []

    if has_usable_pattern:
        rules = get_pattern_rules(
            technical_pattern
        )

        for rule in rules:
            relation = rule[
                "relation"
            ]

            element = relation_to_element(
                relation,
                element_relations,
            )

            raw_candidates.append(
                build_pattern_candidate(
                    element=element,
                    relation=relation,
                    role=rule[
                        "role"
                    ],
                    base_weight=rule[
                        "weight"
                    ],
                    weighted_five_elements=(
                        weighted_five_elements
                    ),
                )
            )

    candidates = merge_pattern_candidates(
        raw_candidates
    )

    pattern_elements = [
        candidate[
            "element"
        ]
        for candidate in candidates
    ]

    if pattern_elements:
        primary_pattern_element = (
            pattern_elements[0]
        )

        secondary_pattern_elements = (
            pattern_elements[1:]
        )
    else:
        primary_pattern_element = None
        secondary_pattern_elements = []

    confidence = (
        calculate_pattern_useful_confidence(
            pattern_info,
            candidates,
        )
    )

    reasoning = build_reasoning(
        pattern_info,
        candidates,
    )

    notes = [
        (
            "格局用神v1は扶抑用神・調候用神とは"
            "独立した補助判定です。"
        ),
        (
            "最終用神は複数の用神レイヤーを"
            "統合して決定する必要があります。"
        ),
        (
            "建禄格・羊刃格には流派差があるため、"
            "現段階では暫定判定です。"
        ),
        (
            "従格・化格・特殊格局の専用用神規則は"
            "後続バージョンで追加します。"
        ),
    ]

    if not pattern_info[
        "has_pattern"
    ]:
        notes.append(
            "有効な格局がないため、格局用神候補を返していません。"
        )

    elif not is_supported_pattern(
        technical_pattern
    ):
        notes.append(
            "現在の格局用神v1では未対応の格局です。"
        )

    return {
        "has_pattern_useful_candidate": bool(
            pattern_elements
        ),
        "primary_pattern_element": (
            primary_pattern_element
        ),
        "secondary_pattern_elements": (
            secondary_pattern_elements
        ),
        "pattern_elements": (
            pattern_elements
        ),
        "pattern_candidates": candidates,
        "day_master_stem": day_master_stem,
        "day_master_element": (
            day_master_element
        ),
        "primary_pattern": pattern_info[
            "primary_pattern"
        ],
        "technical_pattern": (
            technical_pattern
        ),
        "pattern_overall_judgment": (
            pattern_info[
                "overall_judgment"
            ]
        ),
        "pattern_confidence": (
            pattern_info[
                "confidence"
            ]
        ),
        "supported_pattern": (
            is_supported_pattern(
                technical_pattern
            )
        ),
        "element_relations": (
            element_relations
        ),
        "confidence": confidence,
        "reasoning": reasoning,
        "evidence": {
            "pattern_judgment": (
                pattern_judgment
            ),
            "weighted_five_elements": (
                weighted_five_elements
            ),
            "pattern_info": (
                pattern_info
            ),
            "raw_candidates": (
                raw_candidates
            ),
        },
        "method": (
            "pattern_useful_gods_v1"
        ),
        "status": (
            "provisional_pattern_useful_gods"
        ),
        "notes": notes,
    }
