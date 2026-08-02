def calculate_integrated_month_strength(
    seasonal_strength: dict,
    weighted_month_command: dict,
) -> dict:
    """
    季節状態と月支蔵干構成を統合し、
    月令の補正値を算出します。

    季節補正を主評価とし、
    月支蔵干の支援率との差を小さく補助評価します。
    """
    seasonal_score = float(
        seasonal_strength.get(
            "score",
            0.0,
        )
    )

    supporting_ratio = float(
        weighted_month_command.get(
            "supporting_ratio",
            0.0,
        )
    )

    draining_ratio = float(
        weighted_month_command.get(
            "draining_ratio",
            0.0,
        )
    )

    # 月支蔵干の偏りを-1.0～1.0へ変換
    hidden_stem_balance = round(
        (
            supporting_ratio
            - draining_ratio
        )
        / 100,
        2,
    )

    # 蔵干構成は補助評価として最大±4点
    hidden_stem_adjustment = round(
        hidden_stem_balance * 4.0,
        2,
    )

    integrated_score = round(
        seasonal_score
        + hidden_stem_adjustment,
        2,
    )

    return {
        "seasonal_state": (
            seasonal_strength.get(
                "state"
            )
        ),
        "seasonal_score": seasonal_score,
        "supporting_ratio": supporting_ratio,
        "draining_ratio": draining_ratio,
        "hidden_stem_balance": (
            hidden_stem_balance
        ),
        "hidden_stem_adjustment": (
            hidden_stem_adjustment
        ),
        "integrated_score": (
            integrated_score
        ),
        "method": (
            "integrated_month_strength_v1"
        ),
        "status": (
            "provisional_integrated_month_strength"
        ),
        "notes": [
            "季節補正を主評価として使用しています。",
            "月支蔵干構成は補助評価として最大±4点です。",
            "土用期間と節入り後の日数は未反映です。",
            "流派差を含むため暫定評価です。",
        ],
    }
