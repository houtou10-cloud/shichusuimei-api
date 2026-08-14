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

from engine.ten_gods import (
    calculate_ten_god,
)




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


def get_day_master_stem_from_chart(
    chart_data: dict,
) -> str:
    """
    chart_dataの日柱から日主天干を取得する。
    """
    validate_chart_data(
        chart_data
    )

    day = chart_data[
        "day"
    ]

    day_master_stem = day.get(
        "stem"
    )

    validate_day_master_stem(
        day_master_stem
    )

    return day_master_stem


def build_month_hidden_stem_sources(
    chart_data: dict,
) -> list[dict]:
    """
    月支の全蔵干について、
    通変星・普通格対応・透干状況を整理する。

    重要:
    - 日干そのものは透干位置に含めない。
    - 比肩・劫財などSTANDARD_PATTERN_BY_TEN_GODに
      対応しない十神は、普通格候補にはしない。
    - hidden_stemsの並び順は既存エンジンの順位を保持する。
    """
    validate_chart_data(
        chart_data
    )

    month = chart_data[
        "month"
    ]

    day_master_stem = (
        get_day_master_stem_from_chart(
            chart_data
        )
    )

    hidden_stems = list(
        month[
            "hidden_stems"
        ]
    )

    main_hidden_stem = month[
        "main_hidden_stem"
    ]

    # 既存pillarデータに通変星一覧があれば利用する。
    # テスト用fixtureなどでNoneの場合はcalculate_ten_godで補う。
    supplied_ten_gods = {}

    raw_hidden_ten_gods = (
        month.get(
            "hidden_stem_ten_gods",
            [],
        )
    )

    if isinstance(
        raw_hidden_ten_gods,
        list,
    ):
        for item in raw_hidden_ten_gods:
            if not isinstance(
                item,
                dict,
            ):
                continue

            stem = item.get(
                "stem"
            )
            ten_god = item.get(
                "ten_god"
            )

            if (
                isinstance(
                    stem,
                    str,
                )
                and isinstance(
                    ten_god,
                    str,
                )
            ):
                supplied_ten_gods[
                    stem
                ] = ten_god

    sources: list[dict] = []

    for index, hidden_stem in enumerate(
        hidden_stems
    ):
        ten_god = supplied_ten_gods.get(
            hidden_stem
        )

        if ten_god is None:
            ten_god = calculate_ten_god(
                day_master_stem,
                hidden_stem,
            )

        pattern_rule = (
            STANDARD_PATTERN_BY_TEN_GOD.get(
                ten_god
            )
        )

        exposure_positions = (
            find_exposure_positions(
                hidden_stem,
                chart_data,
            )
        )

        sources.append(
            {
                "stem": hidden_stem,
                "rank": index + 1,
                "ten_god": ten_god,
                "pattern_rule": (
                    pattern_rule
                ),
                "is_standard_pattern": (
                    pattern_rule
                    is not None
                ),
                "is_main_hidden_stem": (
                    hidden_stem
                    == main_hidden_stem
                ),
                "is_exposed": bool(
                    exposure_positions
                ),
                "exposure_positions": (
                    exposure_positions
                ),
            }
        )

    return sources


def select_standard_pattern_source(
    chart_data: dict,
) -> dict | None:
    """
    普通格の取格元となる月支蔵干を1件選ぶ。

    八雲採用ルール:
    1. 月支蔵干のうち普通格に対応するものを対象とする。
    2. 天干へ透出している蔵干があれば、それを優先する。
    3. 複数が透出している場合、
       主蔵干が透出していれば主蔵干を優先する。
    4. 主蔵干が透出していなければ、
       hidden_stemsの既存順位が高い透干蔵干を優先する。
    5. 普通格対応の透干蔵干がなければ、
       従来互換として主蔵干を使用する。
    6. 主蔵干が比肩・劫財など普通格対象外ならNoneを返す。

    この関数は格局成立を確定しない。
    後続pattern_judgmentへ渡す候補の取格元だけを選ぶ。
    """
    validate_chart_data(
        chart_data
    )

    month = chart_data[
        "month"
    ]

    main_hidden_stem = month[
        "main_hidden_stem"
    ]

    sources = (
        build_month_hidden_stem_sources(
            chart_data
        )
    )

    standard_sources = [
        source
        for source in sources
        if source[
            "is_standard_pattern"
        ]
    ]

    exposed_sources = [
        source
        for source in standard_sources
        if source[
            "is_exposed"
        ]
    ]

    if exposed_sources:
        exposed_main = next(
            (
                source
                for source
                in exposed_sources
                if source[
                    "is_main_hidden_stem"
                ]
            ),
            None,
        )

        if exposed_main is not None:
            return exposed_main

        return min(
            exposed_sources,
            key=lambda source: (
                source[
                    "rank"
                ]
            ),
        )

    main_source = next(
        (
            source
            for source in standard_sources
            if source[
                "stem"
            ]
            == main_hidden_stem
        ),
        None,
    )

    return main_source


def build_standard_pattern_candidate(
    chart_data: dict,
) -> dict | None:
    """
    月支蔵干の透干状況を考慮して
    普通格候補を1件抽出する。

    従来版:
        月支主蔵干だけから普通格を選択。

    現在版:
        月支全蔵干のうち普通格対象となる十神を確認し、
        透干している蔵干を優先して取格元を選ぶ。
        有効な透干がなければ主蔵干へフォールバックする。

    比肩・劫財は普通格候補をここでは作らない。
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

    source = (
        select_standard_pattern_source(
            chart_data
        )
    )

    if source is None:
        return None

    selected_hidden_stem = source[
        "stem"
    ]

    ten_god = source[
        "ten_god"
    ]

    pattern_rule = source[
        "pattern_rule"
    ]

    if pattern_rule is None:
        return None

    is_exposed = source[
        "is_exposed"
    ]

    exposure_positions = list(
        source[
            "exposure_positions"
        ]
    )

    selected_is_main = (
        source[
            "is_main_hidden_stem"
        ]
    )

    confidence = (
        "high"
        if is_exposed
        else "medium"
    )

    selection_source = (
        "month_main_hidden_stem"
        if selected_is_main
        else "month_exposed_hidden_stem"
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
            selection_source
        ),
        "selection_rule": (
            "exposed_month_hidden_stem_priority_v1"
        ),
        "month_branch": (
            month_branch
        ),
        # 既存互換用。
        # 月支本来の主蔵干は変更しない。
        "month_main_hidden_stem": (
            main_hidden_stem
        ),
        # 実際に今回の普通格候補の根拠として
        # 選択された月支蔵干。
        "selected_hidden_stem": (
            selected_hidden_stem
        ),
        "selected_hidden_stem_rank": (
            source[
                "rank"
            ]
        ),
        "selected_is_main_hidden_stem": (
            selected_is_main
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
                "月支全蔵干の通変星と"
                "透干状況を確認して"
                "普通格候補を抽出しています。"
            ),
            (
                "普通格に対応する月支蔵干が"
                "天干へ透出している場合は、"
                "非透干の主蔵干より優先します。"
            ),
            (
                "複数の普通格対象蔵干が"
                "透出している場合は、"
                "主蔵干、次いで既存蔵干順位を"
                "優先します。"
            ),
            (
                "有効な透干蔵干がない場合は"
                "従来互換として月支主蔵干を"
                "候補元にします。"
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

    # 月令が比肩・劫財系の場合は
    # 建禄・羊刃候補を優先する。
    if technical_pattern == "jianlu":
        return 300

    if technical_pattern == "yangren":
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
            "standard_pattern_sources": (
                build_month_hidden_stem_sources(
                    chart_data
                )
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
                "普通格では月支全蔵干の"
                "通変星と透干状況を確認し、"
                "有効な透干蔵干を優先して"
                "代表候補を抽出しています。"
            ),
            (
                "普通格対象の透干蔵干がない場合は、"
                "従来互換として月支主蔵干を"
                "候補元にしています。"
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
