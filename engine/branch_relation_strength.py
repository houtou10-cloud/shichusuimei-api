"""
地支関係の影響度を統合評価するモジュール。

現在は以下の地支関係を対象とします。

- 六冲
- 六合
- 三合
- 刑
- 六害
- 六破

v1では各関係に暫定的な重みを与え、
命式内の地支関係の強さを数値化します。

このスコアは現時点では、
身強・身弱判定へ直接反映しません。
"""


BRANCH_RELATION_WEIGHTS = {
    "clash": -2.0,
    "combination": 1.5,
    "trine": 2.5,
    "punishment": -1.5,
    "harm": -1.0,
    "break": -0.5,
}


def _get_relation_count(
    relation_data: dict | None,
    count_key: str,
) -> int:
    """
    地支関係データから件数を安全に取得します。
    """
    if relation_data is None:
        return 0

    value = relation_data.get(
        count_key,
        0,
    )

    if not isinstance(value, int):
        raise TypeError(
            f"{count_key}はint型で指定してください。"
        )

    if value < 0:
        raise ValueError(
            f"{count_key}は0以上で指定してください。"
        )

    return value


def calculate_branch_relation_strength(
    branch_clashes: dict | None,
    branch_combinations: dict | None,
    branch_trines: dict | None,
    branch_punishments: dict | None,
    branch_harms: dict | None,
    branch_breaks: dict | None,
) -> dict:
    """
    各地支関係の検出結果を統合し、
    暫定的な関係強度スコアを算出します。

    正の値:
        合・三合などの結合関係が優勢。

    負の値:
        冲・刑・害・破などの
        不安定化関係が優勢。

    0:
        関係がない、
        または正負が相殺している状態。

    注意:
        このスコアは地支関係そのものの
        強さを表す暫定値です。

        日主を扶助するか、
        日主を弱めるかまでは
        v1では判定しません。
    """
    clash_count = _get_relation_count(
        branch_clashes,
        "clash_count",
    )

    combination_count = _get_relation_count(
        branch_combinations,
        "combination_count",
    )

    trine_count = _get_relation_count(
        branch_trines,
        "trine_count",
    )

    punishment_count = _get_relation_count(
        branch_punishments,
        "punishment_count",
    )

    harm_count = _get_relation_count(
        branch_harms,
        "harm_count",
    )

    break_count = _get_relation_count(
        branch_breaks,
        "break_count",
    )

    clash_score = (
        clash_count
        * BRANCH_RELATION_WEIGHTS[
            "clash"
        ]
    )

    combination_score = (
        combination_count
        * BRANCH_RELATION_WEIGHTS[
            "combination"
        ]
    )

    trine_score = (
        trine_count
        * BRANCH_RELATION_WEIGHTS[
            "trine"
        ]
    )

    punishment_score = (
        punishment_count
        * BRANCH_RELATION_WEIGHTS[
            "punishment"
        ]
    )

    harm_score = (
        harm_count
        * BRANCH_RELATION_WEIGHTS[
            "harm"
        ]
    )

    break_score = (
        break_count
        * BRANCH_RELATION_WEIGHTS[
            "break"
        ]
    )

    total_score = round(
        clash_score
        + combination_score
        + trine_score
        + punishment_score
        + harm_score
        + break_score,
        2,
    )

    positive_score = round(
        combination_score
        + trine_score,
        2,
    )

    negative_score = round(
        abs(
            clash_score
            + punishment_score
            + harm_score
            + break_score
        ),
        2,
    )

    total_relation_count = (
        clash_count
        + combination_count
        + trine_count
        + punishment_count
        + harm_count
        + break_count
    )

    if total_score > 0:
        balance = "positive"
    elif total_score < 0:
        balance = "negative"
    else:
        balance = "neutral"

    details = {
        "clash": {
            "count": clash_count,
            "weight": (
                BRANCH_RELATION_WEIGHTS[
                    "clash"
                ]
            ),
            "score": clash_score,
        },
        "combination": {
            "count": combination_count,
            "weight": (
                BRANCH_RELATION_WEIGHTS[
                    "combination"
                ]
            ),
            "score": combination_score,
        },
        "trine": {
            "count": trine_count,
            "weight": (
                BRANCH_RELATION_WEIGHTS[
                    "trine"
                ]
            ),
            "score": trine_score,
        },
        "punishment": {
            "count": punishment_count,
            "weight": (
                BRANCH_RELATION_WEIGHTS[
                    "punishment"
                ]
            ),
            "score": punishment_score,
        },
        "harm": {
            "count": harm_count,
            "weight": (
                BRANCH_RELATION_WEIGHTS[
                    "harm"
                ]
            ),
            "score": harm_score,
        },
        "break": {
            "count": break_count,
            "weight": (
                BRANCH_RELATION_WEIGHTS[
                    "break"
                ]
            ),
            "score": break_score,
        },
    }

    return {
        "total_relation_count": (
            total_relation_count
        ),
        "positive_score": (
            positive_score
        ),
        "negative_score": (
            negative_score
        ),
        "total_score": total_score,
        "balance": balance,
        "details": details,
        "weights": (
            BRANCH_RELATION_WEIGHTS.copy()
        ),
        "method": (
            "branch_relation_strength_v1"
        ),
        "status": (
            "provisional_branch_relation_strength"
        ),
        "notes": [
            (
                "六冲・六合・三合・刑・六害・六破を"
                "暫定重みで統合しています。"
            ),
            (
                "現在のスコアは地支関係の強度を"
                "表す暫定値です。"
            ),
            (
                "日主への扶助・剋泄耗の方向は"
                "まだ評価していません。"
            ),
            (
                "身強・身弱の最終判定には"
                "まだ直接反映していません。"
            ),
        ],
    }
