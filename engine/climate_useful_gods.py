"""
engine/climate_useful_gods.py

調候用神候補判定エンジン v1。

目的
----
四柱推命における「調候」の観点を、
扶抑用神とは独立したレイヤーとして評価する。

v1では主に月支から季節傾向を判定し、
命式が寒・熱・燥・湿のどちらへ傾きやすいかを
説明可能な形で返す。

重要
----
このモジュールは「最終用神」を断定しない。

調候は本来、
- 日干
- 月令
- 月支
- 天干透出
- 蔵干
- 五行力量
- 寒暖燥湿
などを総合して判断する必要がある。

そのため v1 では、
月支を中心とした季節調整候補を返し、
後続の useful_gods_v2 で扶抑用神などと
統合するための evidence を提供する。

後続版で追加予定
----------------
- 日干別の調候優先表
- 十二月令別の詳細ルール
- 天干透出による候補強化
- 蔵干存在による候補補正
- weighted_five_elements による不足補正
- 寒暖燥湿スコア
- 調候用神の力量判定
"""

from __future__ import annotations

from typing import Any


CLIMATE_USEFUL_GODS_METHOD = (
    "climate_useful_gods_v1"
)

CLIMATE_USEFUL_GODS_STATUS = (
    "provisional_climate_useful_gods"
)


ELEMENTS = (
    "木",
    "火",
    "土",
    "金",
    "水",
)


STEMS = (
    "甲",
    "乙",
    "丙",
    "丁",
    "戊",
    "己",
    "庚",
    "辛",
    "壬",
    "癸",
)


BRANCHES = (
    "子",
    "丑",
    "寅",
    "卯",
    "辰",
    "巳",
    "午",
    "未",
    "申",
    "酉",
    "戌",
    "亥",
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


# 月支を季節へ分類する。
#
# 四季土用の辰・未・戌・丑は、
# 単純に一季節へ完全固定できないが、
# v1では実装を安定させるため
# 季節遷移を含む代表分類を採用する。
MONTH_BRANCH_TO_SEASON = {
    "寅": "spring",
    "卯": "spring",
    "辰": "spring",
    "巳": "summer",
    "午": "summer",
    "未": "summer",
    "申": "autumn",
    "酉": "autumn",
    "戌": "autumn",
    "亥": "winter",
    "子": "winter",
    "丑": "winter",
}


SEASON_JAPANESE = {
    "spring": "春",
    "summer": "夏",
    "autumn": "秋",
    "winter": "冬",
}


# v1の季節気候モデル。
#
# heat:
#   正なら熱傾向
#   負なら寒傾向
#
# moisture:
#   正なら湿傾向
#   負なら燥傾向
#
# これは古典の最終判定ではなく、
# 調候レイヤーの説明用指標。
SEASON_CLIMATE_PROFILE = {
    "spring": {
        "heat": 0.0,
        "moisture": 0.5,
        "temperature_label": (
            "moderate"
        ),
        "moisture_label": (
            "slightly_moist"
        ),
    },
    "summer": {
        "heat": 1.0,
        "moisture": -0.25,
        "temperature_label": (
            "hot"
        ),
        "moisture_label": (
            "slightly_dry"
        ),
    },
    "autumn": {
        "heat": -0.25,
        "moisture": -1.0,
        "temperature_label": (
            "slightly_cool"
        ),
        "moisture_label": (
            "dry"
        ),
    },
    "winter": {
        "heat": -1.0,
        "moisture": 0.75,
        "temperature_label": (
            "cold"
        ),
        "moisture_label": (
            "moist"
        ),
    },
}


# 月支ごとの追加補正。
#
# 季節末の土支は季節そのものだけでは
# 表現しにくいため、v1でも最低限の
# 補正を持たせる。
MONTH_BRANCH_CLIMATE_ADJUSTMENT = {
    "子": {
        "heat": -0.25,
        "moisture": 0.25,
    },
    "丑": {
        "heat": -0.10,
        "moisture": 0.20,
    },
    "寅": {
        "heat": -0.10,
        "moisture": 0.10,
    },
    "卯": {
        "heat": 0.00,
        "moisture": 0.10,
    },
    "辰": {
        "heat": 0.10,
        "moisture": 0.25,
    },
    "巳": {
        "heat": 0.20,
        "moisture": -0.10,
    },
    "午": {
        "heat": 0.30,
        "moisture": -0.20,
    },
    "未": {
        "heat": 0.15,
        "moisture": -0.15,
    },
    "申": {
        "heat": 0.00,
        "moisture": -0.15,
    },
    "酉": {
        "heat": -0.10,
        "moisture": -0.25,
    },
    "戌": {
        "heat": -0.10,
        "moisture": -0.30,
    },
    "亥": {
        "heat": -0.20,
        "moisture": 0.20,
    },
}


# 気候調整に使う五行。
#
# 火:
#   寒を温める
#
# 水:
#   熱を冷ます・乾燥を潤す
#
# 木:
#   v1では乾燥時の補助候補。
#
# 土・金:
#   v1では気候調整の主役として
#   自動選定しない。
CLIMATE_FUNCTIONS = {
    "火": {
        "warms": True,
        "cools": False,
        "moistens": False,
        "dries": True,
    },
    "水": {
        "warms": False,
        "cools": True,
        "moistens": True,
        "dries": False,
    },
    "木": {
        "warms": False,
        "cools": False,
        "moistens": True,
        "dries": False,
    },
    "土": {
        "warms": False,
        "cools": False,
        "moistens": False,
        "dries": True,
    },
    "金": {
        "warms": False,
        "cools": False,
        "moistens": False,
        "dries": False,
    },
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


def validate_day_master_stem(
    day_master_stem: str,
) -> None:
    """
    日干を検証する。
    """
    if not isinstance(
        day_master_stem,
        str,
    ):
        raise TypeError(
            "day_master_stemはstr型で"
            "指定してください。"
        )

    if day_master_stem not in STEMS:
        raise ValueError(
            "不正な日干です: "
            f"{day_master_stem}"
        )


def validate_month_branch(
    month_branch: str,
) -> None:
    """
    月支を検証する。
    """
    if not isinstance(
        month_branch,
        str,
    ):
        raise TypeError(
            "month_branchはstr型で"
            "指定してください。"
        )

    if month_branch not in BRANCHES:
        raise ValueError(
            "不正な月支です: "
            f"{month_branch}"
        )


def get_day_master_element(
    day_master_stem: str,
) -> str:
    """
    日干から五行を返す。
    """
    validate_day_master_stem(
        day_master_stem
    )

    return STEM_TO_ELEMENT[
        day_master_stem
    ]


def get_season(
    month_branch: str,
) -> str:
    """
    月支から季節を返す。
    """
    validate_month_branch(
        month_branch
    )

    return MONTH_BRANCH_TO_SEASON[
        month_branch
    ]


def get_season_japanese(
    season: str,
) -> str:
    """
    season technical label を
    日本語表記へ変換する。
    """
    if season not in SEASON_JAPANESE:
        raise ValueError(
            "不正なseasonです: "
            f"{season}"
        )

    return SEASON_JAPANESE[
        season
    ]


def calculate_climate_profile(
    month_branch: str,
) -> dict:
    """
    月支から寒暖燥湿の暫定プロファイルを返す。
    """
    season = get_season(
        month_branch
    )

    base = SEASON_CLIMATE_PROFILE[
        season
    ]

    adjustment = (
        MONTH_BRANCH_CLIMATE_ADJUSTMENT[
            month_branch
        ]
    )

    heat_score = round(
        float(base["heat"])
        + float(
            adjustment["heat"]
        ),
        4,
    )

    moisture_score = round(
        float(base["moisture"])
        + float(
            adjustment[
                "moisture"
            ]
        ),
        4,
    )

    if heat_score <= -0.75:
        temperature_label = "cold"
    elif heat_score < -0.20:
        temperature_label = (
            "slightly_cool"
        )
    elif heat_score <= 0.20:
        temperature_label = (
            "moderate"
        )
    elif heat_score < 0.75:
        temperature_label = (
            "slightly_hot"
        )
    else:
        temperature_label = "hot"

    if moisture_score <= -0.75:
        moisture_label = "dry"
    elif moisture_score < -0.20:
        moisture_label = (
            "slightly_dry"
        )
    elif moisture_score <= 0.20:
        moisture_label = (
            "moderate"
        )
    elif moisture_score < 0.75:
        moisture_label = (
            "slightly_moist"
        )
    else:
        moisture_label = "moist"

    return {
        "season": season,
        "season_japanese": (
            get_season_japanese(
                season
            )
        ),
        "month_branch": (
            month_branch
        ),
        "heat_score": (
            heat_score
        ),
        "moisture_score": (
            moisture_score
        ),
        "temperature_label": (
            temperature_label
        ),
        "moisture_label": (
            moisture_label
        ),
        "base_profile": {
            "heat": float(
                base["heat"]
            ),
            "moisture": float(
                base["moisture"]
            ),
        },
        "branch_adjustment": {
            "heat": float(
                adjustment["heat"]
            ),
            "moisture": float(
                adjustment[
                    "moisture"
                ]
            ),
        },
    }


def determine_climate_needs(
    climate_profile: dict,
) -> list[str]:
    """
    気候プロファイルから必要な調整を返す。

    戻り値:
        warming
        cooling
        moistening
        drying

    v1では極端でない場合、
    無理に調整要求を作らない。
    """
    if not isinstance(
        climate_profile,
        dict,
    ):
        raise TypeError(
            "climate_profileはdict型で"
            "指定してください。"
        )

    heat_score = climate_profile.get(
        "heat_score"
    )

    moisture_score = (
        climate_profile.get(
            "moisture_score"
        )
    )

    if not _is_number(
        heat_score
    ):
        raise ValueError(
            "climate_profileのheat_scoreは"
            "数値で指定してください。"
        )

    if not _is_number(
        moisture_score
    ):
        raise ValueError(
            "climate_profileの"
            "moisture_scoreは"
            "数値で指定してください。"
        )

    needs: list[str] = []

    if heat_score <= -0.50:
        needs.append(
            "warming"
        )
    elif heat_score >= 0.50:
        needs.append(
            "cooling"
        )

    if moisture_score <= -0.50:
        needs.append(
            "moistening"
        )
    elif moisture_score >= 0.75:
        needs.append(
            "drying"
        )

    return needs


def build_climate_element_scores(
    climate_needs: list[str],
) -> dict[str, float]:
    """
    調候上の必要性から五行候補スコアを作る。

    このスコアは五行力量ではなく、
    「気候調整にどれだけ適合するか」を表す。
    """
    if not isinstance(
        climate_needs,
        list,
    ):
        raise TypeError(
            "climate_needsはlist型で"
            "指定してください。"
        )

    valid_needs = {
        "warming",
        "cooling",
        "moistening",
        "drying",
    }

    for need in climate_needs:
        if need not in valid_needs:
            raise ValueError(
                "不正なclimate needです: "
                f"{need}"
            )

    scores = {
        element: 0.0
        for element in ELEMENTS
    }

    for need in climate_needs:
        if need == "warming":
            scores["火"] += 2.0

        elif need == "cooling":
            scores["水"] += 2.0

        elif need == "moistening":
            scores["水"] += 1.5
            scores["木"] += 0.5

        elif need == "drying":
            scores["火"] += 1.0
            scores["土"] += 0.5

    return {
        element: round(
            score,
            4,
        )
        for element, score
        in scores.items()
    }


def rank_climate_elements(
    climate_element_scores: dict[
        str,
        float
    ],
) -> list[str]:
    """
    調候適合スコアが高い順に五行を返す。

    0点の五行は候補から除外する。
    同点時は ELEMENTS の順序で安定化する。
    """
    if not isinstance(
        climate_element_scores,
        dict,
    ):
        raise TypeError(
            "climate_element_scoresは"
            "dict型で指定してください。"
        )

    candidates: list[str] = []

    for element in ELEMENTS:
        score = (
            climate_element_scores.get(
                element
            )
        )

        if not _is_number(
            score
        ):
            raise ValueError(
                "climate_element_scoresの"
                f"{element}は数値で"
                "指定してください。"
            )

        if float(score) > 0.0:
            candidates.append(
                element
            )

    return sorted(
        candidates,
        key=lambda element: (
            -float(
                climate_element_scores[
                    element
                ]
            ),
            ELEMENTS.index(
                element
            ),
        ),
    )


def build_climate_candidate_details(
    ranked_elements: list[str],
    climate_element_scores: dict[
        str,
        float
    ],
    climate_needs: list[str],
) -> list[dict]:
    """
    調候候補の説明用詳細を作る。
    """
    if not isinstance(
        ranked_elements,
        list,
    ):
        raise TypeError(
            "ranked_elementsはlist型で"
            "指定してください。"
        )

    result: list[dict] = []

    for priority, element in enumerate(
        ranked_elements,
        start=1,
    ):
        functions = (
            CLIMATE_FUNCTIONS[
                element
            ]
        )

        matched_needs: list[str] = []

        if (
            "warming"
            in climate_needs
            and functions[
                "warms"
            ]
        ):
            matched_needs.append(
                "warming"
            )

        if (
            "cooling"
            in climate_needs
            and functions[
                "cools"
            ]
        ):
            matched_needs.append(
                "cooling"
            )

        if (
            "moistening"
            in climate_needs
            and functions[
                "moistens"
            ]
        ):
            matched_needs.append(
                "moistening"
            )

        if (
            "drying"
            in climate_needs
            and functions[
                "dries"
            ]
        ):
            matched_needs.append(
                "drying"
            )

        result.append(
            {
                "element": element,
                "priority": priority,
                "climate_score": float(
                    climate_element_scores[
                        element
                    ]
                ),
                "matched_needs": (
                    matched_needs
                ),
                "functions": dict(
                    functions
                ),
            }
        )

    return result


def determine_climate_confidence(
    climate_profile: dict,
    climate_needs: list[str],
) -> str:
    """
    v1の調候候補信頼度。

    季節的偏りが明確なほど高くする。
    """
    heat_score = abs(
        float(
            climate_profile[
                "heat_score"
            ]
        )
    )

    moisture_score = abs(
        float(
            climate_profile[
                "moisture_score"
            ]
        )
    )

    strongest = max(
        heat_score,
        moisture_score,
    )

    if not climate_needs:
        return "low"

    if strongest >= 1.0:
        return "high"

    if strongest >= 0.5:
        return "medium"

    return "low"


def build_climate_reasoning(
    climate_profile: dict,
    climate_needs: list[str],
    ranked_elements: list[str],
) -> list[str]:
    """
    説明文を生成する。
    """
    reasoning: list[str] = []

    season_japanese = (
        climate_profile[
            "season_japanese"
        ]
    )

    month_branch = (
        climate_profile[
            "month_branch"
        ]
    )

    reasoning.append(
        f"月支は{month_branch}で、"
        f"v1では{season_japanese}の"
        "季節傾向として評価します。"
    )

    temperature_label = (
        climate_profile[
            "temperature_label"
        ]
    )

    moisture_label = (
        climate_profile[
            "moisture_label"
        ]
    )

    reasoning.append(
        "寒暖評価は"
        f"{temperature_label}、"
        "燥湿評価は"
        f"{moisture_label}です。"
    )

    if not climate_needs:
        reasoning.append(
            "v1の閾値では強い調候要求を"
            "検出していないため、"
            "調候だけで特定五行を"
            "強く推奨しません。"
        )

        return reasoning

    need_labels = {
        "warming": "温める",
        "cooling": "冷ます",
        "moistening": "潤す",
        "drying": "乾かす",
    }

    readable_needs = [
        need_labels[need]
        for need in climate_needs
    ]

    reasoning.append(
        "調候上は"
        + "・".join(
            readable_needs
        )
        + "方向の調整を候補とします。"
    )

    if ranked_elements:
        reasoning.append(
            "その調整機能から、"
            f"{ranked_elements[0]}を"
            "第一候補として評価します。"
        )

    return reasoning


def evaluate_climate_useful_gods(
    day_master_stem: str,
    month_branch: str,
) -> dict:
    """
    調候用神候補を評価する。

    Parameters
    ----------
    day_master_stem:
        日干。
        v1では主にメタデータとして保持する。
        後続版の日干別調候表で利用予定。

    month_branch:
        月支。
        v1の季節・寒暖燥湿判定の中心。

    Returns
    -------
    dict
        調候用神候補と根拠。
    """
    validate_day_master_stem(
        day_master_stem
    )

    validate_month_branch(
        month_branch
    )

    day_master_element = (
        get_day_master_element(
            day_master_stem
        )
    )

    climate_profile = (
        calculate_climate_profile(
            month_branch
        )
    )

    climate_needs = (
        determine_climate_needs(
            climate_profile
        )
    )

    climate_element_scores = (
        build_climate_element_scores(
            climate_needs
        )
    )

    ranked_elements = (
        rank_climate_elements(
            climate_element_scores
        )
    )

    primary_climate_element = (
        ranked_elements[0]
        if ranked_elements
        else None
    )

    secondary_climate_elements = (
        ranked_elements[1:]
    )

    candidate_details = (
        build_climate_candidate_details(
            ranked_elements,
            climate_element_scores,
            climate_needs,
        )
    )

    confidence = (
        determine_climate_confidence(
            climate_profile,
            climate_needs,
        )
    )

    reasoning = (
        build_climate_reasoning(
            climate_profile,
            climate_needs,
            ranked_elements,
        )
    )

    return {
        "has_climate_candidate": (
            primary_climate_element
            is not None
        ),
        "primary_climate_element": (
            primary_climate_element
        ),
        "secondary_climate_elements": (
            secondary_climate_elements
        ),
        "climate_elements": (
            ranked_elements
        ),
        "climate_candidates": (
            candidate_details
        ),
        "day_master_stem": (
            day_master_stem
        ),
        "day_master_element": (
            day_master_element
        ),
        "month_branch": (
            month_branch
        ),
        "season": (
            climate_profile[
                "season"
            ]
        ),
        "season_japanese": (
            climate_profile[
                "season_japanese"
            ]
        ),
        "temperature_label": (
            climate_profile[
                "temperature_label"
            ]
        ),
        "moisture_label": (
            climate_profile[
                "moisture_label"
            ]
        ),
        "heat_score": (
            climate_profile[
                "heat_score"
            ]
        ),
        "moisture_score": (
            climate_profile[
                "moisture_score"
            ]
        ),
        "climate_needs": (
            climate_needs
        ),
        "climate_element_scores": (
            climate_element_scores
        ),
        "confidence": (
            confidence
        ),
        "reasoning": (
            reasoning
        ),
        "evidence": {
            "climate_profile": (
                climate_profile
            ),
            "season_source": (
                "month_branch"
            ),
            "day_master_usage": (
                "metadata_only_in_v1"
            ),
        },
        "method": (
            CLIMATE_USEFUL_GODS_METHOD
        ),
        "status": (
            CLIMATE_USEFUL_GODS_STATUS
        ),
        "notes": [
            (
                "v1は月支を中心とした"
                "季節調候候補判定です。"
            ),
            (
                "primary_climate_elementは"
                "最終用神ではなく、"
                "調候観点の第一候補です。"
            ),
            (
                "日干別の詳細な調候優先表は"
                "後続バージョンで実装します。"
            ),
            (
                "扶抑用神とは独立して評価し、"
                "useful_gods_v2で統合する"
                "前提のレイヤーです。"
            ),
            (
                "辰・未・戌・丑などの土用月は"
                "季節遷移を含むため、"
                "v1では簡略化した補正を"
                "使用しています。"
            ),
        ],
    }


__all__ = [
    "CLIMATE_USEFUL_GODS_METHOD",
    "CLIMATE_USEFUL_GODS_STATUS",
    "ELEMENTS",
    "STEMS",
    "BRANCHES",
    "STEM_TO_ELEMENT",
    "MONTH_BRANCH_TO_SEASON",
    "SEASON_JAPANESE",
    "SEASON_CLIMATE_PROFILE",
    "MONTH_BRANCH_CLIMATE_ADJUSTMENT",
    "CLIMATE_FUNCTIONS",
    "validate_day_master_stem",
    "validate_month_branch",
    "get_day_master_element",
    "get_season",
    "get_season_japanese",
    "calculate_climate_profile",
    "determine_climate_needs",
    "build_climate_element_scores",
    "rank_climate_elements",
    "build_climate_candidate_details",
    "determine_climate_confidence",
    "build_climate_reasoning",
    "evaluate_climate_useful_gods",
]
