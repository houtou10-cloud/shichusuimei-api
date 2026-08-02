def clamp_score(
    score: float,
    minimum: float = 0.0,
    maximum: float = 100.0,
) -> float:
    """
    スコアを指定範囲内に収めます。
    """
    return max(
        minimum,
        min(score, maximum),
    )


def get_strength_label(
    final_score: float,
) -> str:
    """
    暫定スコアから身強身弱の傾向を返します。

    60点以上：身強寄り
    50点以上：やや身強寄り
    45点以上：中和～やや身弱寄り
    40点以上：身弱寄り
    40点未満：かなり身弱寄り
    """
    if final_score >= 60:
        return "身強寄り"

    if final_score >= 50:
        return "やや身強寄り"

    if final_score >= 45:
        return "中和～やや身弱寄り"

    if final_score >= 40:
        return "身弱寄り"

    return "かなり身弱寄り"


def calculate_provisional_strength(
    day_master_balance: dict,
    root_strength: dict,
    month_command: dict,
) -> dict:
    """
    単純五行比率・通根本数・月支との関係から、
    暫定的な身強身弱傾向を計算します。

    この関数は比較用の従来版です。
    季節補正は反映しません。
    """
    base_score = float(
        day_master_balance[
            "supporting_ratio"
        ]
    )

    root_count = int(
        root_strength.get(
            "root_count",
            0,
        )
    )

    root_positions = root_strength.get(
        "root_positions",
        [],
    )

    root_bonus = min(
        root_count * 3.0,
        9.0,
    )

    month_root_bonus = (
        5.0
        if "month" in root_positions
        else 0.0
    )

    month_effect = month_command.get(
        "effect"
    )

    if month_effect == "supporting":
        month_adjustment = 12.0
    elif month_effect == "draining":
        month_adjustment = -8.0
    elif month_effect == "controlling":
        month_adjustment = -10.0
    else:
        month_adjustment = 0.0

    raw_score = (
        base_score
        + root_bonus
        + month_root_bonus
        + month_adjustment
    )

    final_score = round(
        clamp_score(raw_score),
        2,
    )

    return {
        "label": get_strength_label(
            final_score
        ),
        "final_score": final_score,
        "base_supporting_ratio": base_score,
        "adjustments": {
            "root_bonus": root_bonus,
            "month_root_bonus": (
                month_root_bonus
            ),
            "month_command_adjustment": (
                month_adjustment
            ),
        },
        "evidence": {
            "supporting_score": (
                day_master_balance[
                    "supporting_score"
                ]
            ),
            "draining_score": (
                day_master_balance[
                    "draining_score"
                ]
            ),
            "root_count": root_count,
            "root_positions": root_positions,
            "month_effect": month_effect,
            "month_relationship": (
                month_command.get(
                    "relationship"
                )
            ),
        },
        "method": (
            "provisional_strength_v1"
        ),
        "status": (
            "provisional_judgment"
        ),
        "notes": [
            "単純五行比率・通根本数・月支関係を使った暫定判定です。",
            "蔵干の重みと通根の実効強度は未反映です。",
            "季節旺衰、合・冲・刑・害、格局は未反映です。",
            "比較用の従来版として残しています。",
        ],
    }


def calculate_weighted_provisional_strength(
    weighted_day_master_balance: dict,
    weighted_root_strength: dict,
    month_command: dict,
    seasonal_strength: dict,
) -> dict:
    """
    重み付き五行比率・重み付き通根・季節旺衰から、
    暫定的な身強身弱傾向を計算します。

    月支関係補正と季節補正の二重評価を避けるため、
    最終スコアには季節補正だけを使用します。
    """
    base_score = float(
        weighted_day_master_balance[
            "supporting_ratio"
        ]
    )

    total_root_score = float(
        weighted_root_strength.get(
            "total_root_score",
            0.0,
        )
    )

    weighted_root_bonus = round(
        total_root_score * 10.0,
        2,
    )

    seasonal_adjustment = float(
        seasonal_strength.get(
            "score",
            0.0,
        )
    )

    month_effect = month_command.get(
        "effect"
    )

    seasonal_state = seasonal_strength.get(
        "state"
    )

    raw_score = (
        base_score
        + weighted_root_bonus
        + seasonal_adjustment
    )

    final_score = round(
        clamp_score(raw_score),
        2,
    )

    return {
        "label": get_strength_label(
            final_score
        ),
        "final_score": final_score,
        "base_supporting_ratio": base_score,
        "adjustments": {
            "weighted_root_bonus": (
                weighted_root_bonus
            ),
            "seasonal_adjustment": (
                seasonal_adjustment
            ),
        },
        "evidence": {
            "supporting_score": (
                weighted_day_master_balance[
                    "supporting_score"
                ]
            ),
            "draining_score": (
                weighted_day_master_balance[
                    "draining_score"
                ]
            ),
            "total_root_score": (
                total_root_score
            ),
            "root_count": (
                weighted_root_strength.get(
                    "root_count",
                    0,
                )
            ),
            "root_positions": (
                weighted_root_strength.get(
                    "root_positions",
                    [],
                )
            ),
            "month_effect": month_effect,
            "month_relationship": (
                month_command.get(
                    "relationship"
                )
            ),
            "seasonal_state": (
                seasonal_state
            ),
            "seasonal_score": (
                seasonal_adjustment
            ),
        },
        "method": (
            "weighted_provisional_strength_v2"
        ),
        "status": (
            "provisional_weighted_judgment"
        ),
        "notes": [
            "重み付き五行比率と重み付き通根を使用しています。",
            "通根加点は重み付き通根スコアの10倍です。",
            "月支関係補正との二重評価を避け、季節補正を採用しています。",
            "土用期間、節入り直後、合・冲・刑・害は未反映です。",
            "この結果を最終的な身強身弱判定として断定しません。",
        ],
    }
