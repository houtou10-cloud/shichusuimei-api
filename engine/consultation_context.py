"""
engine/consultation_context.py

四柱推命鑑定書 v1.1
相談内容をAI鑑定へ安全に渡すための
consultation_context生成レイヤー。

目的
----
顧客から受け取った、

- 現在のお悩み
- 理想の未来

をそのまま命式計算ロジックへ混ぜず、

    命式 = 事実
    相談 = 焦点
    AI   = 説明

という責務分離を維持したまま、
AI鑑定で利用できる構造へ変換する。

重要
----
このモジュールは、

- 四柱を再計算しない
- 日主を変更しない
- 身強身弱を変更しない
- 格局を変更しない
- 用神を変更しない
- 大運・歳運を変更しない
- 顧客の希望に合わせて占術結果を書き換えない
- 「転職したい」から「転職すべき」と結論づけない
- 「結婚したい」から「結婚できる」と断定しない

相談内容は、
「鑑定書のどこを重点的に説明するか」
を決める情報としてのみ使用する。

Version
-------
consultation_context_v1
"""

from __future__ import annotations

import re

from copy import deepcopy
from typing import (
    Any,
    Dict,
    Mapping,
    Optional,
    Sequence,
)


# ============================================================
# Metadata
# ============================================================


CONSULTATION_CONTEXT_VERSION = (
    "consultation_context_v1"
)


CONSULTATION_CONTEXT_METHOD = (
    "consultation_context_v1"
)


CONSULTATION_CONTEXT_STATUS = (
    "ready_for_ai_reading"
)


# ============================================================
# Limits
# ============================================================


MAX_CONCERN_CHARS = 2000

MAX_DESIRED_FUTURE_CHARS = 2000

MAX_COMBINED_CHARS = 3500


# ============================================================
# Section keys
# ============================================================


READING_SECTION_KEYS = (
    "core_personality",
    "career",
    "wealth",
    "relationships",
    "health",
    "current_luck",
    "future_flow",
    "advice",
)


# ============================================================
# Focus categories
# ============================================================


FOCUS_CATEGORIES = (
    "career",
    "wealth",
    "relationships",
    "health",
    "current_luck",
    "future_flow",
    "self_understanding",
    "general",
)


# ============================================================
# Keyword rules
# ============================================================


CAREER_KEYWORDS = (
    "仕事",
    "転職",
    "就職",
    "退職",
    "会社",
    "職場",
    "上司",
    "部下",
    "適職",
    "天職",
    "キャリア",
    "副業",
    "独立",
    "起業",
    "事業",
    "働く",
    "働き方",
    "昇進",
    "昇格",
    "異動",
    "会社員",
    "フリーランス",
)


WEALTH_KEYWORDS = (
    "お金",
    "収入",
    "年収",
    "給料",
    "給与",
    "金運",
    "資産",
    "貯金",
    "貯蓄",
    "投資",
    "副収入",
    "利益",
    "稼ぐ",
    "稼ぎ",
    "経済",
    "経済的",
    "生活費",
    "借金",
    "ローン",
)


RELATIONSHIP_KEYWORDS = (
    "恋愛",
    "結婚",
    "離婚",
    "復縁",
    "彼氏",
    "彼女",
    "夫",
    "妻",
    "配偶者",
    "婚活",
    "恋人",
    "好きな人",
    "片思い",
    "人間関係",
    "友人",
    "友達",
    "家族",
    "親",
    "子供",
    "子ども",
    "パートナー",
)


HEALTH_KEYWORDS = (
    "健康",
    "体調",
    "病気",
    "病",
    "疲れ",
    "疲労",
    "ストレス",
    "睡眠",
    "不眠",
    "体力",
    "メンタル",
    "精神",
    "心身",
)


CURRENT_LUCK_KEYWORDS = (
    "今",
    "現在",
    "最近",
    "今年",
    "運勢",
    "運気",
    "現状",
    "タイミング",
    "時期",
)


FUTURE_FLOW_KEYWORDS = (
    "未来",
    "将来",
    "今後",
    "これから",
    "数年後",
    "来年",
    "先",
    "方向性",
    "どうなる",
    "見通し",
)


SELF_UNDERSTANDING_KEYWORDS = (
    "自分",
    "性格",
    "長所",
    "短所",
    "強み",
    "弱み",
    "才能",
    "能力",
    "向いて",
    "適性",
    "本質",
    "自信",
    "生き方",
    "人生",
)


CATEGORY_KEYWORDS = {
    "career": (
        CAREER_KEYWORDS
    ),

    "wealth": (
        WEALTH_KEYWORDS
    ),

    "relationships": (
        RELATIONSHIP_KEYWORDS
    ),

    "health": (
        HEALTH_KEYWORDS
    ),

    "current_luck": (
        CURRENT_LUCK_KEYWORDS
    ),

    "future_flow": (
        FUTURE_FLOW_KEYWORDS
    ),

    "self_understanding": (
        SELF_UNDERSTANDING_KEYWORDS
    ),
}


# ============================================================
# Section mapping
# ============================================================


CATEGORY_SECTION_MAP = {
    "career": (
        "career",
        "current_luck",
        "future_flow",
        "advice",
    ),

    "wealth": (
        "wealth",
        "current_luck",
        "future_flow",
        "advice",
    ),

    "relationships": (
        "relationships",
        "current_luck",
        "future_flow",
        "advice",
    ),

    "health": (
        "health",
        "current_luck",
        "advice",
    ),

    "current_luck": (
        "current_luck",
        "future_flow",
        "advice",
    ),

    "future_flow": (
        "future_flow",
        "current_luck",
        "advice",
    ),

    # v1.1:
    # 自己理解そのものから
    # relationships を自動的に重点化しない。
    "self_understanding": (
        "core_personality",
        "career",
        "advice",
    ),

    "general": (
        "core_personality",
        "career",
        "wealth",
        "relationships",
        "current_luck",
        "future_flow",
        "advice",
    ),
}


# ============================================================
# Safety markers
# ============================================================


MEDICAL_DECISION_MARKERS = (
    "診断して",
    "病名",
    "治る",
    "完治",
    "余命",
    "薬",
    "治療",
    "手術",
)


# 日本語では、
#
#   投資すべき
#   投資をすべき
#   投資するべき
#
# など複数の自然な表記があるため、
# v1では代表的な表記揺れを明示的に検出する。
FINANCIAL_DECISION_MARKERS = (
    "絶対儲かる",
    "必ず儲かる",
    "確実に儲かる",

    "投資すべき",
    "投資をすべき",
    "投資するべき",
    "投資した方が",

    "買うべき",
    "購入すべき",
    "購入するべき",

    "売るべき",
    "売却すべき",
    "売却するべき",

    "株を買",
    "株を売",

    "仮想通貨を買",
    "仮想通貨を売",

    "必ず稼",
    "確実に稼",
)


CERTAINTY_MARKERS = (
    "絶対",
    "必ず",
    "確実",
    "100%",
    "１００％",
    "断言",
    "確定",
)


# ============================================================
# Generic helpers
# ============================================================


def _require_string_or_none(
    value: Any,
    name: str,
) -> Optional[str]:

    if value is None:
        return None

    if not isinstance(
        value,
        str,
    ):
        raise TypeError(
            f"{name}は文字列または"
            "Noneである必要があります。"
        )

    return value


def _normalize_whitespace(
    value: str,
) -> str:

    value = value.replace(
        "\u3000",
        " ",
    )

    value = value.replace(
        "\r\n",
        "\n",
    )

    value = value.replace(
        "\r",
        "\n",
    )

    value = re.sub(
        r"[ \t]+",
        " ",
        value,
    )

    value = re.sub(
        r"\n{3,}",
        "\n\n",
        value,
    )

    return value.strip()


def _normalize_optional_text(
    value: Any,
    *,
    name: str,
    max_chars: int,
) -> str:

    value = _require_string_or_none(
        value,
        name,
    )

    if value is None:
        return ""

    value = _normalize_whitespace(
        value
    )

    if len(
        value
    ) > max_chars:

        raise ValueError(
            f"{name}は"
            f"{max_chars}文字以内で"
            "入力してください。"
        )

    return value


def _contains_any(
    text: str,
    keywords: Sequence[str],
) -> bool:

    return any(
        keyword in text
        for keyword
        in keywords
    )


def _count_keyword_hits(
    text: str,
    keywords: Sequence[str],
) -> int:

    return sum(
        text.count(
            keyword
        )
        for keyword
        in keywords
    )


# ============================================================
# Input validation
# ============================================================


def validate_consultation_input(
    *,
    concern: Any = "",
    desired_future: Any = "",
) -> Dict[str, Any]:

    normalized_concern = (
        _normalize_optional_text(
            concern,
            name="concern",
            max_chars=(
                MAX_CONCERN_CHARS
            ),
        )
    )

    normalized_desired_future = (
        _normalize_optional_text(
            desired_future,
            name="desired_future",
            max_chars=(
                MAX_DESIRED_FUTURE_CHARS
            ),
        )
    )

    combined_length = (
        len(
            normalized_concern
        )
        + len(
            normalized_desired_future
        )
    )

    if (
        combined_length
        > MAX_COMBINED_CHARS
    ):

        raise ValueError(
            "concern と desired_future の"
            "合計文字数が上限を"
            "超えています。 "
            f"上限={MAX_COMBINED_CHARS}"
        )

    has_input = bool(
        normalized_concern
        or normalized_desired_future
    )

    return {
        "valid": True,

        "has_input": (
            has_input
        ),

        "concern_length": (
            len(
                normalized_concern
            )
        ),

        "desired_future_length": (
            len(
                normalized_desired_future
            )
        ),

        "combined_length": (
            combined_length
        ),

        "max_concern_chars": (
            MAX_CONCERN_CHARS
        ),

        "max_desired_future_chars": (
            MAX_DESIRED_FUTURE_CHARS
        ),

        "max_combined_chars": (
            MAX_COMBINED_CHARS
        ),
    }


# ============================================================
# Category analysis
# ============================================================


def analyze_consultation_categories(
    *,
    concern: str,
    desired_future: str,
) -> Dict[str, Any]:

    combined = "\n".join(
        item
        for item
        in (
            concern,
            desired_future,
        )
        if item
    )

    scores: Dict[
        str,
        int,
    ] = {}

    for (
        category,
        keywords,
    ) in CATEGORY_KEYWORDS.items():

        scores[
            category
        ] = (
            _count_keyword_hits(
                combined,
                keywords,
            )
        )

    detected = [
        category
        for (
            category,
            score,
        )
        in scores.items()
        if score > 0
    ]

    detected.sort(
        key=lambda category: (
            -scores[
                category
            ],
            FOCUS_CATEGORIES.index(
                category
            ),
        )
    )

    if detected:

        primary_focus = (
            detected[0]
        )

    else:

        primary_focus = (
            "general"
        )

    secondary_focus = [
        category
        for category
        in detected[
            1:
        ]
    ]

    return {
        "primary_focus": (
            primary_focus
        ),

        "secondary_focus": (
            secondary_focus
        ),

        "detected_categories": (
            detected
        ),

        "category_scores": (
            scores
        ),

        "method": (
            "keyword_focus_v1"
        ),
    }


# ============================================================
# Relevant sections
# ============================================================


def build_relevant_sections(
    category_analysis: Mapping[
        str,
        Any,
    ],
) -> Dict[str, Any]:

    if not isinstance(
        category_analysis,
        Mapping,
    ):
        raise TypeError(
            "category_analysisは"
            "mappingである必要があります。"
        )

    primary_focus = (
        category_analysis.get(
            "primary_focus",
            "general",
        )
    )

    if (
        primary_focus
        not in CATEGORY_SECTION_MAP
    ):

        primary_focus = (
            "general"
        )

    priority_sections = list(
        CATEGORY_SECTION_MAP[
            primary_focus
        ]
    )

    detected_categories = (
        category_analysis.get(
            "detected_categories",
            [],
        )
    )

    if not isinstance(
        detected_categories,
        (list, tuple),
    ):

        detected_categories = []

    relevant = []

    for section in priority_sections:

        if (
            section
            not in relevant
        ):

            relevant.append(
                section
            )

    for category in detected_categories:

        sections = (
            CATEGORY_SECTION_MAP.get(
                category,
                (),
            )
        )

        for section in sections:

            if (
                section
                not in relevant
            ):

                relevant.append(
                    section
                )

    # 8セクションの正式順序へ並べ直す
    ordered = [
        section
        for section
        in READING_SECTION_KEYS
        if section
        in relevant
    ]

    return {
        "primary_focus": (
            primary_focus
        ),

        "priority_sections": (
            priority_sections
        ),

        "relevant_sections": (
            ordered
        ),
    }


# ============================================================
# Safety analysis
# ============================================================


def analyze_consultation_safety(
    *,
    concern: str,
    desired_future: str,
) -> Dict[str, Any]:

    combined = "\n".join(
        item
        for item
        in (
            concern,
            desired_future,
        )
        if item
    )

    medical = (
        _contains_any(
            combined,
            MEDICAL_DECISION_MARKERS,
        )
    )

    financial = (
        _contains_any(
            combined,
            FINANCIAL_DECISION_MARKERS,
        )
    )

    certainty = (
        _contains_any(
            combined,
            CERTAINTY_MARKERS,
        )
    )

    warnings = []

    if medical:

        warnings.append(
            "医療・診断に関する相談が"
            "含まれる可能性があります。"
            "鑑定では医学的診断や"
            "治療判断を行わないでください。"
        )

    if financial:

        warnings.append(
            "投資・金銭判断に関する相談が"
            "含まれる可能性があります。"
            "鑑定では利益保証や"
            "具体的な投資判断を"
            "断定しないでください。"
        )

    if certainty:

        warnings.append(
            "確実性を求める表現が"
            "含まれる可能性があります。"
            "未来・結果を確定的に"
            "断言しないでください。"
        )

    return {
        "medical_decision_caution": (
            medical
        ),

        "financial_decision_caution": (
            financial
        ),

        "certainty_caution": (
            certainty
        ),

        "warnings": (
            warnings
        ),

        "requires_cautious_language": (
            bool(
                medical
                or financial
                or certainty
            )
        ),
    }


# ============================================================
# AI usage policy
# ============================================================


def build_ai_usage_policy(
) -> Dict[str, Any]:

    return {
        "consultation_role": (
            "focus_only"
        ),

        "astrology_is_source_of_facts": (
            True
        ),

        "consultation_may_change_astrology": (
            False
        ),

        "consultation_may_change_pillars": (
            False
        ),

        "consultation_may_change_day_master": (
            False
        ),

        "consultation_may_change_strength": (
            False
        ),

        "consultation_may_change_pattern": (
            False
        ),

        "consultation_may_change_useful_gods": (
            False
        ),

        "consultation_may_change_luck": (
            False
        ),

        "customer_desire_is_not_evidence": (
            True
        ),

        "customer_concern_is_not_evidence": (
            True
        ),

        "must_not_confirm_customer_assumption": (
            True
        ),

        "must_not_guarantee_future": (
            True
        ),

        "must_not_make_medical_diagnosis": (
            True
        ),

        "must_not_guarantee_financial_result": (
            True
        ),

        "must_explain_with_chart_evidence": (
            True
        ),
    }


# ============================================================
# Instructions for AI
# ============================================================


def build_consultation_instructions(
    *,
    has_input: bool,
    primary_focus: str,
    relevant_sections: Sequence[str],
    safety: Mapping[
        str,
        Any,
    ],
) -> list[str]:

    instructions = [
        (
            "相談内容は鑑定の焦点づけにのみ使用し、"
            "命式・日主・身強身弱・格局・用神・"
            "大運・歳運などの計算済み事実を"
            "変更しないこと。"
        ),

        (
            "相談者の希望や前提を、"
            "四柱推命上の根拠として"
            "扱わないこと。"
        ),

        (
            "鑑定上の主張は可能な限り、"
            "reading_context内の計算済みデータに"
            "根拠を置くこと。"
        ),

        (
            "相談者が望む結論へ迎合せず、"
            "命式上の傾向と現実的な選択肢を"
            "分けて説明すること。"
        ),

        (
            "未来・成功・結婚・転職・収入などを"
            "確定的に断言しないこと。"
        ),
    ]

    if has_input:

        instructions.append(
            (
                "相談内容に直接関係するセクションでは、"
                "一般論だけで終わらず、"
                "相談者が現在どこに迷っているかを"
                "踏まえて説明すること。"
            )
        )

        instructions.append(
            (
                f"今回の主な相談焦点は"
                f"「{primary_focus}」。"
                "ただしこの分類自体を"
                "鑑定書本文へ機械的に"
                "表示する必要はない。"
            )
        )

        if relevant_sections:

            joined = ", ".join(
                relevant_sections
            )

            instructions.append(
                (
                    "特に重点を置く候補セクション: "
                    f"{joined}"
                )
            )

    if (
        safety.get(
            "medical_decision_caution"
        )
    ):

        instructions.append(
            (
                "健康相談では医学的診断、"
                "疾患の確定、治療方針の判断を"
                "行わないこと。"
            )
        )

    if (
        safety.get(
            "financial_decision_caution"
        )
    ):

        instructions.append(
            (
                "金銭・投資相談では、"
                "購入・売却・投資実行を"
                "断定的に指示せず、"
                "利益を保証しないこと。"
            )
        )

    if (
        safety.get(
            "certainty_caution"
        )
    ):

        instructions.append(
            (
                "相談者が確実な答えを"
                "求めている場合でも、"
                "断定表現へ合わせないこと。"
            )
        )

    return instructions


# ============================================================
# Build context
# ============================================================


def build_consultation_context(
    *,
    concern: Any = "",
    desired_future: Any = "",
) -> Dict[str, Any]:
    """
    顧客相談内容をAI鑑定向けに整理する。

    Parameters
    ----------
    concern:
        現在のお悩み。

    desired_future:
        理想の未来。

    Returns
    -------
    dict
        consultation_context_v1

    Notes
    -----
    この関数は占術計算を一切行わない。

    入力された相談内容は、
    AI鑑定の焦点・優先セクション・
    安全上の注意を決めるためだけに使用する。
    """

    normalized_concern = (
        _normalize_optional_text(
            concern,
            name="concern",
            max_chars=(
                MAX_CONCERN_CHARS
            ),
        )
    )

    normalized_desired_future = (
        _normalize_optional_text(
            desired_future,
            name="desired_future",
            max_chars=(
                MAX_DESIRED_FUTURE_CHARS
            ),
        )
    )

    validation = (
        validate_consultation_input(
            concern=(
                normalized_concern
            ),
            desired_future=(
                normalized_desired_future
            ),
        )
    )

    category_analysis = (
        analyze_consultation_categories(
            concern=(
                normalized_concern
            ),
            desired_future=(
                normalized_desired_future
            ),
        )
    )

    relevant_sections = (
        build_relevant_sections(
            category_analysis
        )
    )

    safety = (
        analyze_consultation_safety(
            concern=(
                normalized_concern
            ),
            desired_future=(
                normalized_desired_future
            ),
        )
    )

    ai_usage_policy = (
        build_ai_usage_policy()
    )

    instructions = (
        build_consultation_instructions(
            has_input=(
                validation[
                    "has_input"
                ]
            ),
            primary_focus=(
                category_analysis[
                    "primary_focus"
                ]
            ),
            relevant_sections=(
                relevant_sections[
                    "relevant_sections"
                ]
            ),
            safety=safety,
        )
    )

    return {
        "version": (
            CONSULTATION_CONTEXT_VERSION
        ),

        "input": {
            "concern": (
                normalized_concern
            ),

            "desired_future": (
                normalized_desired_future
            ),
        },

        "has_consultation": (
            validation[
                "has_input"
            ]
        ),

        "focus": {
            "primary": (
                category_analysis[
                    "primary_focus"
                ]
            ),

            "secondary": (
                deepcopy(
                    category_analysis[
                        "secondary_focus"
                    ]
                )
            ),

            "detected_categories": (
                deepcopy(
                    category_analysis[
                        "detected_categories"
                    ]
                )
            ),

            "category_scores": (
                deepcopy(
                    category_analysis[
                        "category_scores"
                    ]
                )
            ),

            "priority_sections": (
                deepcopy(
                    relevant_sections[
                        "priority_sections"
                    ]
                )
            ),

            "relevant_sections": (
                deepcopy(
                    relevant_sections[
                        "relevant_sections"
                    ]
                )
            ),
        },

        "safety": (
            deepcopy(
                safety
            )
        ),

        "ai_usage_policy": (
            deepcopy(
                ai_usage_policy
            )
        ),

        "instructions": (
            deepcopy(
                instructions
            )
        ),

        "validation": (
            deepcopy(
                validation
            )
        ),

        "source": {
            "concern_source": (
                "customer_input"
            ),

            "desired_future_source": (
                "customer_input"
            ),

            "astrology_source": (
                "reading_context"
            ),
        },

        "recalculates_astrology": (
            False
        ),

        "rewrites_chart_facts": (
            False
        ),

        "method": (
            CONSULTATION_CONTEXT_METHOD
        ),

        "status": (
            CONSULTATION_CONTEXT_STATUS
        ),
    }


# ============================================================
# Validation for generated context
# ============================================================


def validate_consultation_context(
    context: Mapping[
        str,
        Any,
    ],
) -> Dict[str, Any]:

    if not isinstance(
        context,
        Mapping,
    ):

        raise TypeError(
            "consultation_contextは"
            "mappingである必要があります。"
        )

    required_keys = {
        "version",
        "input",
        "has_consultation",
        "focus",
        "safety",
        "ai_usage_policy",
        "instructions",
        "validation",
        "source",
        "recalculates_astrology",
        "rewrites_chart_facts",
        "method",
        "status",
    }

    missing_keys = sorted(
        required_keys
        - set(
            context.keys()
        )
    )

    if missing_keys:

        raise ValueError(
            "consultation_contextに"
            "必須キーがありません: "
            + ", ".join(
                missing_keys
            )
        )

    if (
        context.get(
            "version"
        )
        != CONSULTATION_CONTEXT_VERSION
    ):

        raise ValueError(
            "consultation_contextの"
            "versionが不正です。"
        )

    if (
        context.get(
            "method"
        )
        != CONSULTATION_CONTEXT_METHOD
    ):

        raise ValueError(
            "consultation_contextの"
            "methodが不正です。"
        )

    if (
        context.get(
            "status"
        )
        != CONSULTATION_CONTEXT_STATUS
    ):

        raise ValueError(
            "consultation_contextの"
            "statusが不正です。"
        )

    if (
        context.get(
            "recalculates_astrology"
        )
        is not False
    ):

        raise ValueError(
            "consultation_contextは"
            "占術を再計算しては"
            "いけません。"
        )

    if (
        context.get(
            "rewrites_chart_facts"
        )
        is not False
    ):

        raise ValueError(
            "consultation_contextは"
            "命式事実を書き換えては"
            "いけません。"
        )

    input_data = (
        context.get(
            "input"
        )
    )

    if not isinstance(
        input_data,
        Mapping,
    ):

        raise ValueError(
            "consultation_context.inputが"
            "mappingではありません。"
        )

    focus = (
        context.get(
            "focus"
        )
    )

    if not isinstance(
        focus,
        Mapping,
    ):

        raise ValueError(
            "consultation_context.focusが"
            "mappingではありません。"
        )

    primary = (
        focus.get(
            "primary"
        )
    )

    if (
        primary
        not in FOCUS_CATEGORIES
    ):

        raise ValueError(
            "consultation_context.focus.primaryが"
            "不正です。"
        )

    relevant_sections = (
        focus.get(
            "relevant_sections"
        )
    )

    if not isinstance(
        relevant_sections,
        (list, tuple),
    ):

        raise ValueError(
            "relevant_sectionsが"
            "配列ではありません。"
        )

    unknown_sections = [
        section
        for section
        in relevant_sections
        if (
            section
            not in READING_SECTION_KEYS
        )
    ]

    if unknown_sections:

        raise ValueError(
            "不明なreading sectionがあります: "
            + ", ".join(
                unknown_sections
            )
        )

    instructions = (
        context.get(
            "instructions"
        )
    )

    if not isinstance(
        instructions,
        (list, tuple),
    ):

        raise ValueError(
            "instructionsが"
            "配列ではありません。"
        )

    if not instructions:

        raise ValueError(
            "instructionsが空です。"
        )

    if not all(
        isinstance(
            item,
            str,
        )
        and item.strip()
        for item
        in instructions
    ):

        raise ValueError(
            "instructionsに"
            "不正な値があります。"
        )

    validation = (
        context.get(
            "validation"
        )
    )

    if not isinstance(
        validation,
        Mapping,
    ):

        raise ValueError(
            "validationが"
            "mappingではありません。"
        )

    if (
        validation.get(
            "valid"
        )
        is not True
    ):

        raise ValueError(
            "consultation_contextの"
            "validationが"
            "validではありません。"
        )

    return {
        "valid": True,

        "version": (
            context[
                "version"
            ]
        ),

        "method": (
            context[
                "method"
            ]
        ),

        "status": (
            context[
                "status"
            ]
        ),

        "has_consultation": (
            bool(
                context[
                    "has_consultation"
                ]
            )
        ),

        "primary_focus": (
            primary
        ),

        "relevant_sections": (
            list(
                relevant_sections
            )
        ),
    }


# ============================================================
# Compact context
# ============================================================


def build_compact_consultation_context(
    consultation_context: Mapping[
        str,
        Any,
    ],
) -> Dict[str, Any]:
    """
    AI promptへ渡しやすい簡潔版を返す。

    内部のvalidation詳細や文字数上限などは除き、
    AIが鑑定文生成に必要な内容だけ残す。
    """

    validate_consultation_context(
        consultation_context
    )

    input_data = (
        consultation_context[
            "input"
        ]
    )

    focus = (
        consultation_context[
            "focus"
        ]
    )

    safety = (
        consultation_context[
            "safety"
        ]
    )

    return {
        "concern": (
            input_data.get(
                "concern",
                "",
            )
        ),

        "desired_future": (
            input_data.get(
                "desired_future",
                "",
            )
        ),

        "has_consultation": (
            consultation_context[
                "has_consultation"
            ]
        ),

        "primary_focus": (
            focus.get(
                "primary"
            )
        ),

        "secondary_focus": (
            deepcopy(
                focus.get(
                    "secondary",
                    [],
                )
            )
        ),

        "priority_sections": (
            deepcopy(
                focus.get(
                    "priority_sections",
                    [],
                )
            )
        ),

        "relevant_sections": (
            deepcopy(
                focus.get(
                    "relevant_sections",
                    [],
                )
            )
        ),

        "safety": {
            "medical_decision_caution": (
                safety.get(
                    "medical_decision_caution",
                    False,
                )
            ),

            "financial_decision_caution": (
                safety.get(
                    "financial_decision_caution",
                    False,
                )
            ),

            "certainty_caution": (
                safety.get(
                    "certainty_caution",
                    False,
                )
            ),

            "requires_cautious_language": (
                safety.get(
                    "requires_cautious_language",
                    False,
                )
            ),
        },

        "instructions": (
            deepcopy(
                consultation_context[
                    "instructions"
                ]
            )
        ),

        "recalculates_astrology": (
            False
        ),

        "rewrites_chart_facts": (
            False
        ),

        "method": (
            CONSULTATION_CONTEXT_METHOD
        ),

        "status": (
            CONSULTATION_CONTEXT_STATUS
        ),
    }


# ============================================================
# Convenience API
# ============================================================


def prepare_consultation_context(
    *,
    concern: Any = "",
    desired_future: Any = "",
) -> Dict[str, Any]:
    """
    build_consultation_context() の互換alias。
    """

    return build_consultation_context(
        concern=concern,
        desired_future=(
            desired_future
        ),
    )


def calculate_consultation_context(
    *,
    concern: Any = "",
    desired_future: Any = "",
) -> Dict[str, Any]:
    """
    API命名互換用alias。

    consultation_contextは占術計算ではないが、
    既存engineのcalculate_*命名との
    互換性確保のため提供する。
    """

    return build_consultation_context(
        concern=concern,
        desired_future=(
            desired_future
        ),
    )


# ============================================================
# Metadata
# ============================================================


def get_consultation_context_metadata(
) -> Dict[str, Any]:

    return {
        "version": (
            CONSULTATION_CONTEXT_VERSION
        ),

        "method": (
            CONSULTATION_CONTEXT_METHOD
        ),

        "status": (
            CONSULTATION_CONTEXT_STATUS
        ),

        "input_fields": [
            "concern",
            "desired_future",
        ],

        "focus_categories": list(
            FOCUS_CATEGORIES
        ),

        "reading_sections": list(
            READING_SECTION_KEYS
        ),

        "max_concern_chars": (
            MAX_CONCERN_CHARS
        ),

        "max_desired_future_chars": (
            MAX_DESIRED_FUTURE_CHARS
        ),

        "max_combined_chars": (
            MAX_COMBINED_CHARS
        ),

        "recalculates_astrology": (
            False
        ),

        "rewrites_chart_facts": (
            False
        ),

        "customer_concern_is_evidence": (
            False
        ),

        "customer_desire_is_evidence": (
            False
        ),

        "purpose": (
            "focus_ai_reading_without_"
            "changing_astrology"
        ),
    }


# ============================================================
# Public exports
# ============================================================


__all__ = [
    "CONSULTATION_CONTEXT_VERSION",
    "CONSULTATION_CONTEXT_METHOD",
    "CONSULTATION_CONTEXT_STATUS",
    "MAX_CONCERN_CHARS",
    "MAX_DESIRED_FUTURE_CHARS",
    "MAX_COMBINED_CHARS",
    "READING_SECTION_KEYS",
    "FOCUS_CATEGORIES",
    "validate_consultation_input",
    "analyze_consultation_categories",
    "build_relevant_sections",
    "analyze_consultation_safety",
    "build_ai_usage_policy",
    "build_consultation_instructions",
    "build_consultation_context",
    "validate_consultation_context",
    "build_compact_consultation_context",
    "prepare_consultation_context",
    "calculate_consultation_context",
    "get_consultation_context_metadata",
]