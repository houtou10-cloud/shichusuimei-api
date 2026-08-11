"""
格局候補抽出モジュール v1。

目的:
月支・月支主蔵干・通変星・透干情報から、
格局の「候補」を抽出する。

この段階では格局を確定しない。
最終的な格局成立判定は、後続の
pattern_judgment.py で行う。

既存のpillarデータ構造:

{
    "pillar": "癸未",
    "stem": "癸",
    "branch": "未",
    "stem_ten_god": "...",
    "hidden_stems": ["己", "丁", "乙"],
    "main_hidden_stem": "己",
    "main_hidden_stem_ten_god": "偏財",
    "hidden_stem_ten_gods": [
        {
            "stem": "己",
            "ten_god": "偏財",
        },
        ...
    ],
    "twelve_stage": "...",
}

v1で扱う候補:

- 正官格
- 偏官格
- 正財格
- 偏財格
- 印綬格
- 偏印格
- 食神格
- 傷官格
- 建禄格
- 羊刃格

注意:
建禄格・羊刃格は流派差がある。
特に陰干の羊刃を月劫格として扱う流派、
戊日午月を羊刃格としない流派などがある。

そのため、v1では「候補」として検出するだけで、
最終成立を確定しない。
"""


# =========================================================
# Constants
# =========================================================


STANDARD_PATTERN_BY_TEN_GOD = {
    "正官": {
        "pattern": "正官格",
        "technical_pattern": (
            "direct_officer"
        ),
    },
    "偏官": {
        "pattern": "偏官格",
        "technical_pattern": (
            "seven_killings"
        ),
    },
    "正財": {
        "pattern": "正財格",
        "technical_pattern": (
            "direct_wealth"
        ),
    },
    "偏財": {
        "pattern": "偏財格",
        "technical_pattern": (
            "indirect_wealth"
        ),
    },
    "印綬": {
        "pattern": "印綬格",
        "technical_pattern": (
            "direct_resource"
        ),
    },
    "正印": {
        "pattern": "印綬格",
        "technical_pattern": (
            "direct_resource"
        ),
    },
    "偏印": {
        "pattern": "偏印格",
        "technical_pattern": (
            "indirect_resource"
        ),
    },
    "食神": {
        "pattern": "食神格",
        "technical_pattern": (
            "eating_god"
        ),
    },
    "傷官": {
        "pattern": "傷官格",
        "technical_pattern": (
            "hurting_officer"
        ),
    },
}


# 日干に対する禄の月支。
#
# v1では候補抽出専用。
# 最終的な建禄格成立条件は
# pattern_judgment側で判定する。
JIANLU_BRANCH_BY_DAY_STEM = {
    "甲": "寅",
    "乙": "卯",
    "丙": "巳",
    "丁": "午",
    "戊": "巳",
    "己": "午",
    "庚": "申",
    "辛": "酉",
    "壬": "亥",
    "癸": "子",
}


# 日干に対する羊刃候補支。
#
# 羊刃の扱いには流派差があるため、
# v1ではあくまで候補検出に使用する。
YANGREN_BRANCH_BY_DAY_STEM = {
    "甲": "卯",
    "乙": "辰",
    "丙": "午",
    "丁": "未",
    "戊": "午",
    "己": "未",
    "庚": "酉",
    "辛": "戌",
    "壬": "子",
    "癸": "丑",
}


VALID_POSITIONS = {
    "year",
    "month",
    "day",
    "hour",
}


VALID_DAY_STEMS = set(
    JIANLU_BRANCH_BY_DAY_STEM
)


# =========================================================
# Validation
# =========================================================


def validate_day_master_stem(
    day_master_stem: str,
) -> None:
    if not isinstance(
        day_master_stem,
        str,
    ):
        raise TypeError(
            "day_master_stemは"
            "str型で指定してください。"
        )

    if day_master_stem not in VALID_DAY_STEMS:
        raise ValueError(
            "不正なday_master_stemです: "
            f"{day_master_stem}"
        )


def validate_chart_data(
    chart_data: dict,
) -> None:
    if not isinstance(
        chart_data,
        dict,
    ):
        raise TypeError(
            "chart_dataはdict型で"
            "指定してください。"
        )

    for position in (
        "year",
        "month",
        "day",
    ):
        if position not in chart_data:
            raise ValueError(
                "chart_dataに"
                f"{position}が必要です。"
            )

        pillar = chart_data[
            position
        ]

        if not isinstance(
            pillar,
            dict,
        ):
            raise TypeError(
                f"{position}柱は"
                "dict型で指定してください。"
            )

    hour = chart_data.get(
        "hour"
    )

    if (
        hour is not None
        and not isinstance(
            hour,
            dict,
        )
    ):
        raise TypeError(
            "hour柱はdict型または"
            "Noneで指定してください。"
        )

    month = chart_data[
        "month"
    ]

    required_month_keys = (
        "stem",
        "branch",
        "hidden_stems",
        "main_hidden_stem",
        "main_hidden_stem_ten_god",
    )

    for key in required_month_keys:
        if key not in month:
            raise ValueError(
                "month柱に"
                f"{key}が必要です。"
            )

    if not isinstance(
        month[
            "hidden_stems"
        ],
        list,
    ):
        raise TypeError(
            "month.hidden_stemsは"
            "list型で指定してください。"
        )

    if not isinstance(
        month[
            "main_hidden_stem"
        ],
        str,
    ):
        raise TypeError(
            "month.main_hidden_stemは"
            "str型で指定してください。"
        )

    if not isinstance(
        month[
            "main_hidden_stem_ten_god"
        ],
        str,
    ):
        raise TypeError(
            "month.main_hidden_stem_ten_godは"
            "str型で指定してください。"
        )


# =========================================================
# Exposure
# =========================================================


def find_exposure_positions(
    target_stem: str,
    chart_data: dict,
) -> list[str]:
    """
    指定した蔵干が、
    年干・月干・時干に透出している位置を返す。

    日干は日主そのものなので、
    月令蔵干の「透干」判定には使用しない。
    """
    if not isinstance(
        target_stem,
        str,
    ):
        raise TypeError(
            "target_stemはstr型で"
            "指定してください。"
        )

    validate_chart_data(
        chart_data
    )

    positions: list[str] = []

    for position in (
        "year",
        "month",
        "hour",
    ):
        pillar = chart_data.get(
            position
        )

        if pillar is None:
            continue

        stem = pillar.get(
            "stem"
        )

        if stem == target_stem:
            positions.append(
                position
            )

    return positions


# =========================================================
# Standard patterns
# =========================================================


def build_standard_pattern_candidate(
    chart_data: dict,
) -> dict | None:
    """
    月支主蔵干の通変星から
    普通格候補を1件抽出する。

    比肩・劫財の場合は、
    普通格候補をここでは作らない。
    """
    validate_chart_data(
        chart_data
    )

    month = chart_data[
        "month"
    ]

    month_branch = month[
        "branch"
    ]

    main_hidden_stem = month[
        "main_hidden_stem"
    ]

    ten_god = month[
        "main_hidden_stem_ten_god"
    ]

    pattern_rule = (
        STANDARD_PATTERN_BY_TEN_GOD.get(
            ten_god
        )
    )

    if pattern_rule is None:
        return None

    exposure_positions = (
        find_exposure_positions(
            main_hidden_stem,
            chart_data,
        )
    )

    is_exposed = bool(
        exposure_positions
    )

    confidence = (
        "high"
        if is_exposed
        else "medium"
    )

    return {
        "pattern": (
            pattern_rule[
                "pattern"
            ]
        ),
        "technical_pattern": (
            pattern_rule[
                "technical_pattern"
            ]
        ),
        "pattern_group": (
            "standard_pattern"
        ),
        "source": (
            "month_main_hidden_stem"
        ),
        "month_branch": (
            month_branch
        ),
        "month_main_hidden_stem": (
            main_hidden_stem
        ),
        "ten_god": (
            ten_god
        ),
        "is_exposed": (
            is_exposed
        ),
        "exposure_positions": (
            exposure_positions
        ),
        "confidence": (
            confidence
        ),
        "candidate_status": (
            "provisional_candidate"
        ),
        "is_provisional": True,
        "notes": [
            (
                "月支主蔵干の通変星から"
                "抽出した普通格候補です。"
            ),
            (
                "透干している場合は"
                "候補confidenceを高くしています。"
            ),
            (
                "格局成立・破格・救応は"
                "この段階では判定していません。"
            ),
        ],
    }


# =========================================================
# Jianlu
# =========================================================


def build_jianlu_candidate(
    day_master_stem: str,
    chart_data: dict,
) -> dict | None:
    """
    日干と月支から建禄格候補を抽出する。
    """
    validate_day_master_stem(
        day_master_stem
    )

    validate_chart_data(
        chart_data
    )

    month = chart_data[
        "month"
    ]

    month_branch = month[
        "branch"
    ]

    expected_branch = (
        JIANLU_BRANCH_BY_DAY_STEM[
            day_master_stem
        ]
    )

    if month_branch != expected_branch:
        return None

    main_hidden_stem = month[
        "main_hidden_stem"
    ]

    ten_god = month[
        "main_hidden_stem_ten_god"
    ]

    exposure_positions = (
        find_exposure_positions(
            main_hidden_stem,
            chart_data,
        )
    )

    return {
        "pattern": "建禄格",
        "technical_pattern": (
            "jianlu"
        ),
        "pattern_group": (
            "special_month_pattern"
        ),
        "source": (
            "day_stem_month_branch"
        ),
        "day_master_stem": (
            day_master_stem
        ),
        "month_branch": (
            month_branch
        ),
        "expected_branch": (
            expected_branch
        ),
        "month_main_hidden_stem": (
            main_hidden_stem
        ),
        "ten_god": (
            ten_god
        ),
        "is_exposed": bool(
            exposure_positions
        ),
        "exposure_positions": (
            exposure_positions
        ),
        "confidence": "high",
        "candidate_status": (
            "provisional_candidate"
        ),
        "is_provisional": True,
        "notes": [
            (
                "日干と月支の禄支一致から"
                "建禄格候補を抽出しています。"
            ),
            (
                "最終的な格局成立条件は"
                "pattern_judgmentで判定します。"
            ),
        ],
    }


# =========================================================
# Yangren
# =========================================================


def build_yangren_candidate(
    day_master_stem: str,
    chart_data: dict,
) -> dict | None:
    """
    日干と月支から羊刃格候補を抽出する。

    流派差が大きいため、
    最終確定は行わない。
    """
    validate_day_master_stem(
        day_master_stem
    )

    validate_chart_data(
        chart_data
    )

    month = chart_data[
        "month"
    ]

    month_branch = month[
        "branch"
    ]

    expected_branch = (
        YANGREN_BRANCH_BY_DAY_STEM[
            day_master_stem
        ]
    )

    if month_branch != expected_branch:
        return None

    main_hidden_stem = month[
        "main_hidden_stem"
    ]

    ten_god = month[
        "main_hidden_stem_ten_god"
    ]

    exposure_positions = (
        find_exposure_positions(
            main_hidden_stem,
            chart_data,
        )
    )

    yin_day_stems = {
        "乙",
        "丁",
        "己",
        "辛",
        "癸",
    }

    requires_school_rule = (
        day_master_stem
        in yin_day_stems
    )

    confidence = (
        "medium"
        if requires_school_rule
        else "high"
    )

    return {
        "pattern": "羊刃格",
        "technical_pattern": (
            "yangren"
        ),
        "pattern_group": (
            "special_month_pattern"
        ),
        "source": (
            "day_stem_month_branch"
        ),
        "day_master_stem": (
            day_master_stem
        ),
        "month_branch": (
            month_branch
        ),
        "expected_branch": (
            expected_branch
        ),
        "month_main_hidden_stem": (
            main_hidden_stem
        ),
        "ten_god": (
            ten_god
        ),
        "is_exposed": bool(
            exposure_positions
        ),
        "exposure_positions": (
            exposure_positions
        ),
        "requires_school_rule": (
            requires_school_rule
        ),
        "confidence": (
            confidence
        ),
        "candidate_status": (
            "requires_school_rule"
            if requires_school_rule
            else "provisional_candidate"
        ),
        "is_provisional": True,
        "notes": [
            (
                "日干と月支の羊刃候補支一致から"
                "羊刃格候補を抽出しています。"
            ),
            (
                "羊刃格には流派差があるため"
                "この段階では確定しません。"
            ),
            (
                "陰干の場合は月劫格として"
                "扱う流派があるため"
                "requires_school_ruleを立てています。"
            ),
        ],
    }


# =========================================================
# Candidate helpers
# =========================================================


def candidate_priority(
    candidate: dict,
) -> int:
    """
    primary_candidate選定用の優先順位。

    これは格局の優劣ではなく、
    候補抽出段階での代表候補選定規則。
    """
    if not isinstance(
        candidate,
        dict,
    ):
        raise TypeError(
            "candidateはdict型で"
            "指定してください。"
        )

    technical_pattern = (
        candidate.get(
            "technical_pattern"
        )
    )

    # 月令が比肩・劫財系の場合は、
    # 建禄・羊刃候補を優先候補として扱う。
    #
    # ただし、陰干の羊刃候補など
    # requires_school_rule=True の候補は
    # 流派依存性があるため、
    # 通常の普通格候補より無条件には優先しない。
    #
    # これにより、
    #
    #   standard_pattern
    #       ↓
    #   possible / strong
    #
    # と判定できる候補が存在する場合に、
    # 流派依存の羊刃候補が
    # primary_candidate を奪うことを防ぐ。
    if technical_pattern == "jianlu":
        return 300

    if technical_pattern == "yangren":
        if candidate.get(
            "requires_school_rule",
            False,
        ):
            return 190

        return 290

    if (
        candidate.get(
            "pattern_group"
        )
        == "standard_pattern"
    ):
        if candidate.get(
            "is_exposed"
        ):
            return 220

        return 200

    return 0


def determine_primary_candidate(
    candidates: list[dict],
) -> dict | None:
    if not isinstance(
        candidates,
        list,
    ):
        raise TypeError(
            "candidatesはlist型で"
            "指定してください。"
        )

    if not candidates:
        return None

    for candidate in candidates:
        if not isinstance(
            candidate,
            dict,
        ):
            raise TypeError(
                "candidateはdict型で"
                "指定してください。"
            )

    sorted_candidates = sorted(
        candidates,
        key=candidate_priority,
        reverse=True,
    )

    return sorted_candidates[
        0
    ]


def count_candidate_groups(
    candidates: list[dict],
) -> dict:
    if not isinstance(
        candidates,
        list,
    ):
        raise TypeError(
            "candidatesはlist型で"
            "指定してください。"
        )

    result = {
        "standard_pattern": 0,
        "special_month_pattern": 0,
    }

    for candidate in candidates:
        if not isinstance(
            candidate,
            dict,
        ):
            raise TypeError(
                "candidateはdict型で"
                "指定してください。"
            )

        group = candidate.get(
            "pattern_group"
        )

        if group in result:
            result[group] += 1

    return result


# =========================================================
# Main evaluator
# =========================================================


def evaluate_pattern_candidates(
    chart_data: dict,
    day_master_stem: str,
) -> dict:
    """
    命式から格局候補を抽出する。

    v1では月令中心に候補を抽出し、
    格局を確定しない。
    """
    validate_chart_data(
        chart_data
    )

    validate_day_master_stem(
        day_master_stem
    )

    month = chart_data[
        "month"
    ]

    candidates: list[dict] = []

    standard_candidate = (
        build_standard_pattern_candidate(
            chart_data
        )
    )

    if standard_candidate is not None:
        candidates.append(
            standard_candidate
        )

    jianlu_candidate = (
        build_jianlu_candidate(
            day_master_stem,
            chart_data,
        )
    )

    if jianlu_candidate is not None:
        candidates.append(
            jianlu_candidate
        )

    yangren_candidate = (
        build_yangren_candidate(
            day_master_stem,
            chart_data,
        )
    )

    if yangren_candidate is not None:
        candidates.append(
            yangren_candidate
        )

    primary_candidate = (
        determine_primary_candidate(
            candidates
        )
    )

    candidate_groups = (
        count_candidate_groups(
            candidates
        )
    )

    has_school_rule_candidate = any(
        candidate.get(
            "requires_school_rule",
            False,
        )
        for candidate in candidates
    )

    if not candidates:
        overall_status = (
            "no_candidate"
        )

    elif has_school_rule_candidate:
        overall_status = (
            "candidate_with_school_rule"
        )

    else:
        overall_status = (
            "candidate_detected"
        )

    return {
        "has_candidate": bool(
            candidates
        ),
        "candidate_count": len(
            candidates
        ),
        "primary_candidate": (
            primary_candidate
        ),
        "candidates": (
            candidates
        ),
        "candidate_groups": (
            candidate_groups
        ),
        "has_school_rule_candidate": (
            has_school_rule_candidate
        ),
        "month_context": {
            "month_stem": (
                month["stem"]
            ),
            "month_branch": (
                month["branch"]
            ),
            "hidden_stems": list(
                month[
                    "hidden_stems"
                ]
            ),
            "main_hidden_stem": (
                month[
                    "main_hidden_stem"
                ]
            ),
            "main_hidden_stem_ten_god": (
                month[
                    "main_hidden_stem_ten_god"
                ]
            ),
        },
        "day_master_stem": (
            day_master_stem
        ),
        "overall_status": (
            overall_status
        ),
        "method": (
            "pattern_candidates_v1"
        ),
        "status": (
            "provisional_pattern_candidates"
        ),
        "notes": [
            (
                "月支主蔵干とその通変星を"
                "中心に格局候補を抽出しています。"
            ),
            (
                "普通格では月支主蔵干の"
                "透干状況も記録しています。"
            ),
            (
                "建禄格・羊刃格は"
                "日干と月支の関係から"
                "候補として抽出しています。"
            ),
            (
                "羊刃格には流派差があるため、"
                "この段階では成立を"
                "確定していません。"
            ),
            (
                "身強身弱・干合化・地支関係・"
                "破格・救応は後続の"
                "pattern_judgmentで統合します。"
            ),
        ],
    }
