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
    五行比率・通根・月令を使って、
    暫定的な身強身弱傾向を計算します。

    計算方法：
    ・日主を助ける五行の比率を基礎点とする
    ・通根1件につき3点加算、最大9点
    ・月支に通根していれば5点加算
    ・月令が日主を助ける場合は12点加算
    ・月令が日主を消耗させる場合は8点減算
    ・月令が日主を剋す場合は10点減算
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

    label = get_strength_label(
        final_score
    )

    return {
        "label": label,
        "final_score": final_score,
        "base_supporting_ratio": (
            base_score
        ),
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
            "root_positions": (
                root_positions
            ),
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
            "五行比率・通根・月令を使った暫定判定です。",
            "蔵干の本気・中気・余気の重みは未反映です。",
            "季節旺衰、合・冲・刑・害、格局は未反映です。",
            "この結果を最終的な身強身弱判定として断定しません。",
        ],
    }
