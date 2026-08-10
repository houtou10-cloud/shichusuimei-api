def determine_primary_judgment(
    judgments: list[dict],
    preferred_candidate: dict | None = None,
) -> dict | None:
    """
    複数の格局成立判定から、
    primary_judgment を選択する。

    選択順序:
    1. establishment_status
    2. establishment_score
    3. pattern_candidates 側の preferred_candidate

    preferred_candidate は絶対指定ではなく、
    成立状態と成立スコアが同等の場合の
    タイブレークとしてのみ利用する。

    これにより、
    requires_school_rule=True の建禄格・羊刃格が、
    より成立度の高い普通格を無条件に上書きすることを防ぐ。
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
        """
        primary選択用の比較キー。

        judgment_priority() が返す
        establishment_status と
        establishment_score を最優先する。

        preferred_candidate との一致は
        最後のタイブレークとしてのみ使う。
        """
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
