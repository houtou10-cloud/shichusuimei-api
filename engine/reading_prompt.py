"""
engine/reading_prompt.py

AI鑑定文生成用プロンプト構築モジュール。\nconsultation_context_v1 の任意連動に対応。

目的
----
engine.reading_context が生成した reading_context_v1 を受け取り、
AIへ渡す system prompt / user prompt / messages を安定して生成する。

このモジュールは占術計算を行わない。
四柱・日主・身強身弱・格局・用神・大運・歳運・統合運は、
reading_context に含まれる既存計算結果を事実として扱う。

設計方針
--------
1. 占術計算を再実行しない。
2. reading_context の事実を勝手に変更しない。
3. 欠損情報を推測で補わない。
4. 「計算結果」と「文章上の解釈」を分離する。
5. 医療・法律・投資などの高リスク領域では断定を避ける。
6. 将来を確定的に予言しない。
7. JSON出力と通常文章出力の両方に対応する。
8. セクション単位の鑑定にも対応する。
9. GPT API / Chat Completions系へ渡しやすい messages 形式を返す。
10. プロンプト生成は決定論的に行う。

主な公開API
------------
- validate_reading_context()
- build_system_prompt()
- build_user_prompt()
- build_messages()
- build_section_prompt()
- build_json_output_schema()
- build_reading_request()
- calculate_reading_prompt()
- prepare_ai_messages()

注意
----
このモジュールはAIを呼び出さない。
AI実行は別レイヤーで行う。
"""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from engine.consultation_context import (
    build_compact_consultation_context,
    validate_consultation_context,
)


# ============================================================
# Constants
# ============================================================


READING_PROMPT_VERSION = "reading_prompt_v1"
READING_PROMPT_METHOD = "reading_prompt_v1"
READING_PROMPT_STATUS = "ready_for_ai_generation"

SUPPORTED_OUTPUT_FORMATS = (
    "text",
    "json",
)

SUPPORTED_LANGUAGES = (
    "ja",
    "ja-JP",
)

DEFAULT_LANGUAGE = "ja"

DEFAULT_TONE = "professional_warm"

SUPPORTED_TONES = (
    "professional_warm",
    "gentle",
    "concise",
    "detailed",
)

DEFAULT_READING_SECTIONS = (
    "core_personality",
    "career",
    "wealth",
    "relationships",
    "health",
    "current_luck",
    "future_flow",
    "advice",
)

SECTION_TITLES_JA = {
    "core_personality": "本質・性格",
    "career": "仕事・適職",
    "wealth": "金運",
    "relationships": "恋愛・人間関係",
    "health": "健康傾向",
    "current_luck": "現在の運勢",
    "future_flow": "今後の流れ",
    "advice": "総合アドバイス",
}

DEFAULT_SECTION_ORDER = DEFAULT_READING_SECTIONS

DEFAULT_MIN_SECTION_CHARS = 180
DEFAULT_MAX_SECTION_CHARS = 700

DEFAULT_MIN_SUMMARY_CHARS = 120
DEFAULT_MAX_SUMMARY_CHARS = 400


# ============================================================
# Generic helpers
# ============================================================


def _require_mapping(
    value: Any,
    name: str,
) -> Mapping[str, Any]:
    """
    Mapping型であることを検証する。
    """

    if not isinstance(
        value,
        Mapping,
    ):
        raise TypeError(
            f"{name}はdict型で指定してください。"
        )

    return value


def _require_bool(
    value: Any,
    name: str,
) -> bool:
    """
    bool型を検証する。
    """

    if not isinstance(
        value,
        bool,
    ):
        raise TypeError(
            f"{name}はbool型で指定してください。"
        )

    return value


def _require_positive_int(
    value: Any,
    name: str,
) -> int:
    """
    正の整数を検証する。
    """

    if (
        not isinstance(
            value,
            int,
        )
        or isinstance(
            value,
            bool,
        )
    ):
        raise TypeError(
            f"{name}は整数で指定してください。"
        )

    if value <= 0:
        raise ValueError(
            f"{name}は1以上で指定してください。"
        )

    return value


def _non_empty_string(
    value: Any,
    name: str,
) -> str:
    """
    空でない文字列を検証する。
    """

    if not isinstance(
        value,
        str,
    ):
        raise TypeError(
            f"{name}は文字列で指定してください。"
        )

    stripped = value.strip()

    if not stripped:
        raise ValueError(
            f"{name}は空文字にできません。"
        )

    return stripped


def _safe_dict(
    value: Any,
) -> Dict[str, Any]:
    """
    Mappingならdeepcopyしたdictを返す。
    """

    if not isinstance(
        value,
        Mapping,
    ):
        return {}

    return deepcopy(
        dict(value)
    )


def _safe_list(
    value: Any,
) -> List[Any]:
    """
    list/tupleならdeepcopyしたlistを返す。
    """

    if isinstance(
        value,
        list,
    ):
        return deepcopy(value)

    if isinstance(
        value,
        tuple,
    ):
        return deepcopy(
            list(value)
        )

    return []


def _compact_json(
    value: Any,
) -> str:
    """
    日本語をエスケープせず、安定したJSON文字列へ変換する。
    """

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
    )


def _pretty_json(
    value: Any,
) -> str:
    """
    AIが読みやすい整形済みJSON文字列へ変換する。
    """

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
    )


def _normalize_sections(
    sections: Optional[
        Sequence[str]
    ],
) -> Tuple[str, ...]:
    """
    鑑定セクションを正規化する。
    """

    if sections is None:
        return tuple(
            DEFAULT_READING_SECTIONS
        )

    if isinstance(
        sections,
        str,
    ):
        raise TypeError(
            "sectionsは文字列ではなく"
            "文字列の配列で指定してください。"
        )

    if not isinstance(
        sections,
        Sequence,
    ):
        raise TypeError(
            "sectionsは配列で指定してください。"
        )

    normalized = []

    for section in sections:
        if not isinstance(
            section,
            str,
        ):
            raise TypeError(
                "sectionsの各要素は文字列で指定してください。"
            )

        section = section.strip()

        if not section:
            raise ValueError(
                "sectionsに空文字は指定できません。"
            )

        if section not in DEFAULT_READING_SECTIONS:
            raise ValueError(
                f"未対応の鑑定セクションです: {section}"
            )

        if section not in normalized:
            normalized.append(
                section
            )

    if not normalized:
        raise ValueError(
            "sectionsには1件以上指定してください。"
        )

    return tuple(
        normalized
    )


# ============================================================
# Validation
# ============================================================


def validate_reading_context(
    reading_context: Mapping[
        str,
        Any,
    ],
) -> Dict[str, Any]:
    """
    reading_context_v1 の最低限構造を検証する。
    """

    reading_context = _require_mapping(
        reading_context,
        "reading_context",
    )

    required_top_level = (
        "schema_version",
        "subject",
        "natal_chart",
        "day_master",
        "five_elements",
        "strength",
        "pattern",
        "useful_gods",
        "luck",
        "reading_sections",
        "source_metadata",
        "method",
        "status",
    )

    missing = [
        key
        for key
        in required_top_level
        if key not in reading_context
    ]

    if missing:
        raise ValueError(
            "reading_contextに必要なキーがありません: "
            + ", ".join(missing)
        )

    schema_version = (
        reading_context.get(
            "schema_version"
        )
    )

    if schema_version != (
        "reading_context_v1"
    ):
        raise ValueError(
            "未対応のreading_context schemaです: "
            f"{schema_version}"
        )

    natal_chart = _require_mapping(
        reading_context[
            "natal_chart"
        ],
        "reading_context['natal_chart']",
    )

    pillars = _require_mapping(
        natal_chart.get(
            "pillars"
        ),
        "reading_context['natal_chart']['pillars']",
    )

    missing_pillars = [
        key
        for key
        in (
            "year",
            "month",
            "day",
            "hour",
        )
        if key not in pillars
    ]

    if missing_pillars:
        raise ValueError(
            "natal_chartに必要な四柱がありません: "
            + ", ".join(
                missing_pillars
            )
        )

    luck = _require_mapping(
        reading_context[
            "luck"
        ],
        "reading_context['luck']",
    )

    missing_luck = [
        key
        for key
        in (
            "luck_pillars",
            "current_luck",
            "annual_luck",
            "integrated_luck",
        )
        if key not in luck
    ]

    if missing_luck:
        raise ValueError(
            "luckに必要なキーがありません: "
            + ", ".join(
                missing_luck
            )
        )

    return {
        "valid": True,
        "schema_version": (
            schema_version
        ),
        "missing_top_level_keys": [],
        "missing_pillars": [],
        "missing_luck_keys": [],
    }


# ============================================================
# Reading facts extraction
# ============================================================


def build_prompt_facts(
    reading_context: Mapping[
        str,
        Any,
    ],
) -> Dict[str, Any]:
    """
    AIへ渡す主要事実を抽出する。

    reading_context全体を投げるのではなく、
    鑑定文章に必要なデータを整理する。
    """

    reading_context = _require_mapping(
        reading_context,
        "reading_context",
    )

    subject = _safe_dict(
        reading_context.get(
            "subject"
        )
    )

    natal_chart = _safe_dict(
        reading_context.get(
            "natal_chart"
        )
    )

    day_master = _safe_dict(
        reading_context.get(
            "day_master"
        )
    )

    five_elements = _safe_dict(
        reading_context.get(
            "five_elements"
        )
    )

    strength = _safe_dict(
        reading_context.get(
            "strength"
        )
    )

    pattern = _safe_dict(
        reading_context.get(
            "pattern"
        )
    )

    useful_gods = _safe_dict(
        reading_context.get(
            "useful_gods"
        )
    )

    luck = _safe_dict(
        reading_context.get(
            "luck"
        )
    )

    luck_pillars = _safe_dict(
        luck.get(
            "luck_pillars"
        )
    )

    current_luck = _safe_dict(
        luck.get(
            "current_luck"
        )
    )

    annual_luck = _safe_dict(
        luck.get(
            "annual_luck"
        )
    )

    integrated_luck = (
        _safe_dict(
            luck.get(
                "integrated_luck"
            )
        )
    )

    return {
        "subject": {
            "birth_date": subject.get(
                "birth_date"
            ),
            "birth_time": subject.get(
                "birth_time"
            ),
            "birth_place": subject.get(
                "birth_place"
            ),
            "gender": subject.get(
                "gender"
            ),
            "timezone": subject.get(
                "timezone"
            ),
        },
        "natal_chart": {
            "pillar_sequence": _safe_list(
                natal_chart.get(
                    "pillar_sequence"
                )
            ),
            "pillars": _safe_dict(
                natal_chart.get(
                    "pillars"
                )
            ),
        },
        "day_master": day_master,
        "five_elements": five_elements,
        "strength": {
            "technical_label": strength.get(
                "technical_label"
            ),
            "label": strength.get(
                "label"
            ),
            "final_score": strength.get(
                "final_score"
            ),
            "confidence": strength.get(
                "confidence"
            ),
        },
        "pattern": {
            "primary_pattern": pattern.get(
                "primary_pattern"
            ),
            "technical_pattern": pattern.get(
                "technical_pattern"
            ),
            "overall_judgment": pattern.get(
                "overall_judgment"
            ),
            "confidence": pattern.get(
                "confidence"
            ),
        },
        "useful_gods": {
            "primary_useful_element": (
                useful_gods.get(
                    "primary_useful_element"
                )
            ),
            "secondary_useful_elements": (
                _safe_list(
                    useful_gods.get(
                        "secondary_useful_elements"
                    )
                )
            ),
            "final_useful_elements": (
                _safe_list(
                    useful_gods.get(
                        "final_useful_elements"
                    )
                )
            ),
            "unfavorable_elements": (
                _safe_list(
                    useful_gods.get(
                        "unfavorable_elements"
                    )
                )
            ),
            "strength_class": useful_gods.get(
                "strength_class"
            ),
            "confidence": useful_gods.get(
                "confidence"
            ),
            "agreement_level": useful_gods.get(
                "agreement_level"
            ),
        },
        "luck": {
            "luck_pillars": {
                "direction": (
                    luck_pillars.get(
                        "direction"
                    )
                ),
                "direction_japanese": (
                    luck_pillars.get(
                        "direction_japanese"
                    )
                ),
                "start_age": (
                    luck_pillars.get(
                        "start_age"
                    )
                ),
                "pillars": _safe_list(
                    luck_pillars.get(
                        "pillars"
                    )
                ),
            },
            "current_luck": {
                "has_current_luck": (
                    current_luck.get(
                        "has_current_luck"
                    )
                ),
                "phase": (
                    current_luck.get(
                        "phase"
                    )
                ),
                "exact_age": (
                    current_luck.get(
                        "exact_age"
                    )
                ),
                "calendar_age": (
                    current_luck.get(
                        "calendar_age"
                    )
                ),
                "current_pillar": (
                    current_luck.get(
                        "current_pillar"
                    )
                ),
                "previous_pillar": (
                    current_luck.get(
                        "previous_pillar"
                    )
                ),
                "next_pillar": (
                    current_luck.get(
                        "next_pillar"
                    )
                ),
                "progress": (
                    current_luck.get(
                        "progress"
                    )
                ),
                "years_until_next_luck": (
                    current_luck.get(
                        "years_until_next_luck"
                    )
                ),
            },
            "annual_luck": {
                "year": (
                    annual_luck.get(
                        "year"
                    )
                ),
                "effective_year": (
                    annual_luck.get(
                        "effective_year"
                    )
                ),
                "ganzhi": (
                    annual_luck.get(
                        "ganzhi"
                    )
                ),
                "stem_element": (
                    annual_luck.get(
                        "stem_element"
                    )
                ),
                "branch_element": (
                    annual_luck.get(
                        "branch_element"
                    )
                ),
                "stem_ten_god": (
                    annual_luck.get(
                        "stem_ten_god"
                    )
                ),
                "twelve_stage": (
                    annual_luck.get(
                        "twelve_stage"
                    )
                ),
                "stem_useful_relation": (
                    annual_luck.get(
                        "stem_useful_relation"
                    )
                ),
                "branch_useful_relation": (
                    annual_luck.get(
                        "branch_useful_relation"
                    )
                ),
                "current_luck_relation": (
                    annual_luck.get(
                        "current_luck_relation"
                    )
                ),
            },
            "integrated_luck": {
                "current_luck_ganzhi": (
                    integrated_luck.get(
                        "current_luck_ganzhi"
                    )
                ),
                "annual_luck_ganzhi": (
                    integrated_luck.get(
                        "annual_luck_ganzhi"
                    )
                ),
                "agreement_level": (
                    integrated_luck.get(
                        "agreement_level"
                    )
                ),
                "overall_score": (
                    integrated_luck.get(
                        "overall_score"
                    )
                ),
                "overall_level": (
                    integrated_luck.get(
                        "overall_level"
                    )
                ),
                "confidence": (
                    integrated_luck.get(
                        "confidence"
                    )
                ),
                "annual_ten_god": (
                    integrated_luck.get(
                        "annual_ten_god"
                    )
                ),
                "annual_twelve_stage": (
                    integrated_luck.get(
                        "annual_twelve_stage"
                    )
                ),
                "element_interactions": (
                    integrated_luck.get(
                        "element_interactions"
                    )
                ),
                "current_luck_useful": (
                    integrated_luck.get(
                        "current_luck_useful"
                    )
                ),
                "annual_luck_useful": (
                    integrated_luck.get(
                        "annual_luck_useful"
                    )
                ),
            },
        },
    }


# ============================================================
# Section instructions
# ============================================================


def get_section_instruction(
    reading_context: Mapping[
        str,
        Any,
    ],
    section: str,
) -> Dict[str, Any]:
    """
    reading_context側で定義された
    セクションinstructionを取得する。
    """

    reading_context = _require_mapping(
        reading_context,
        "reading_context",
    )

    section = _non_empty_string(
        section,
        "section",
    )

    if section not in (
        DEFAULT_READING_SECTIONS
    ):
        raise ValueError(
            f"未対応の鑑定セクションです: {section}"
        )

    sections = _safe_dict(
        reading_context.get(
            "reading_sections"
        )
    )

    raw_section = _safe_dict(
        sections.get(
            section
        )
    )

    return {
        "section": section,
        "title": (
            SECTION_TITLES_JA[
                section
            ]
        ),
        "focus": _safe_list(
            raw_section.get(
                "focus"
            )
        ),
        "instruction": (
            raw_section.get(
                "instruction"
            )
        ),
    }


def build_selected_section_instructions(
    reading_context: Mapping[
        str,
        Any,
    ],
    sections: Optional[
        Sequence[str]
    ] = None,
) -> List[Dict[str, Any]]:
    """
    選択された鑑定セクションのinstructionを返す。
    """

    normalized = (
        _normalize_sections(
            sections
        )
    )

    return [
        get_section_instruction(
            reading_context,
            section,
        )
        for section
        in normalized
    ]



# ============================================================
# Consultation context
# ============================================================


def _normalize_consultation_context(
    consultation_context: Optional[
        Mapping[str, Any]
    ],
) -> Optional[Dict[str, Any]]:
    """
    consultation_context_v1 を検証し、
    promptへ渡すcompact版へ変換する。

    None の場合は相談内容連動を無効にし、
    従来の reading_prompt_v1 と同じ出力を維持する。

    この関数は占術計算を行わない。
    """

    if consultation_context is None:
        return None

    consultation_context = _require_mapping(
        consultation_context,
        "consultation_context",
    )

    validate_consultation_context(
        consultation_context
    )

    compact = (
        build_compact_consultation_context(
            consultation_context
        )
    )

    if (
        compact.get(
            "recalculates_astrology"
        )
        is not False
    ):
        raise ValueError(
            "consultation_contextは"
            "占術を再計算してはいけません。"
        )

    if (
        compact.get(
            "rewrites_chart_facts"
        )
        is not False
    ):
        raise ValueError(
            "consultation_contextは"
            "命式事実を書き換えてはいけません。"
        )

    return deepcopy(
        compact
    )


def build_consultation_prompt_block(
    consultation_context: Optional[
        Mapping[str, Any]
    ],
) -> str:
    """
    consultation_context_v1 を
    AI向け相談情報ブロックへ変換する。

    相談内容は鑑定の「焦点」であり、
    四柱推命上の「根拠」ではないことを
    prompt内で明示する。

    consultation_context が None、
    または相談入力が空の場合は空文字を返す。
    """

    compact = (
        _normalize_consultation_context(
            consultation_context
        )
    )

    if compact is None:
        return ""

    if not compact.get(
        "has_consultation"
    ):
        return ""

    concern = (
        compact.get(
            "concern",
            "",
        )
        or ""
    )

    desired_future = (
        compact.get(
            "desired_future",
            "",
        )
        or ""
    )

    primary_focus = (
        compact.get(
            "primary_focus",
            "general",
        )
        or "general"
    )

    secondary_focus = (
        compact.get(
            "secondary_focus",
            [],
        )
    )

    priority_sections = (
        compact.get(
            "priority_sections",
            [],
        )
    )

    relevant_sections = (
        compact.get(
            "relevant_sections",
            [],
        )
    )

    safety = (
        compact.get(
            "safety",
            {},
        )
    )

    instructions = (
        compact.get(
            "instructions",
            [],
        )
    )

    if not isinstance(
        secondary_focus,
        list,
    ):
        secondary_focus = []

    if not isinstance(
        priority_sections,
        list,
    ):
        priority_sections = []

    if not isinstance(
        relevant_sections,
        list,
    ):
        relevant_sections = []

    if not isinstance(
        safety,
        Mapping,
    ):
        safety = {}

    if not isinstance(
        instructions,
        list,
    ):
        instructions = []

    consultation_payload = {
        "concern": concern,
        "desired_future": (
            desired_future
        ),
        "primary_focus": (
            primary_focus
        ),
        "secondary_focus": (
            secondary_focus
        ),
        "priority_sections": (
            priority_sections
        ),
        "relevant_sections": (
            relevant_sections
        ),
        "safety": {
            "medical_decision_caution": (
                bool(
                    safety.get(
                        "medical_decision_caution",
                        False,
                    )
                )
            ),
            "financial_decision_caution": (
                bool(
                    safety.get(
                        "financial_decision_caution",
                        False,
                    )
                )
            ),
            "certainty_caution": (
                bool(
                    safety.get(
                        "certainty_caution",
                        False,
                    )
                )
            ),
            "requires_cautious_language": (
                bool(
                    safety.get(
                        "requires_cautious_language",
                        False,
                    )
                )
            ),
        },
    }

    instruction_lines = [
        f"- {item.strip()}"
        for item
        in instructions
        if (
            isinstance(
                item,
                str,
            )
            and item.strip()
        )
    ]

    instruction_text = "\n".join(
        instruction_lines
    )

    if not instruction_text:
        instruction_text = (
            "- 相談内容は鑑定の"
            "焦点づけにのみ使用してください。"
        )

    return f"""
【相談内容】
以下は相談者本人が入力した相談情報です。

この情報は、
「どのテーマを重点的に説明するか」
を決めるためにのみ使用してください。

相談内容そのものは、
四柱推命上の計算結果・根拠ではありません。

相談者の希望や悩みに合わせて、
命式・日主・身強身弱・格局・用神・
大運・歳運・通変星・十二運などを
変更、再計算、創作しないでください。

相談情報:
{_pretty_json(consultation_payload)}

【相談内容の使用ルール】
{instruction_text}

【相談連動鑑定の絶対条件】
- 命式の計算済み事実を最優先してください。
- 相談者の希望そのものを占術上の根拠にしないでください。
- 相談者が望む結論へ迎合しないでください。
- 相談内容と計算結果が一致しない場合、計算結果を変更しないでください。
- 相談に直接関係するセクションでは、一般論だけで終わらせず、相談者の迷いに接続して説明してください。
- 相談に直接関係するセクションでは、可能な限り「相談者の問い → 計算済み事実 → 解釈 → 複数の選択肢 → 今できる行動」の順で説明してください。
- 「転職すべき」「結婚できる」「必ず儲かる」など、未来や意思決定を確定的に断言しないでください。
- 現実的な選択肢、注意点、活かし方を示してください。
- 現職継続・転職・副業など複数の選択肢が考えられる相談では、入力情報の範囲で比較し、根拠のない一択に誘導しないでください。
- 相談者が入力していない職業・役職・雇用形態・事業形態を勝手に補ってはいけません。
- 根拠のない具体的な回数・頻度・期間・金額・数値目標を助言として作らないでください。
""".strip()


# ============================================================
# System prompt
# ============================================================


def build_system_prompt(
    *,
    language: str = DEFAULT_LANGUAGE,
    tone: str = DEFAULT_TONE,
    output_format: str = "text",
) -> str:
    """
    AI鑑定用system promptを生成する。
    """

    language = _non_empty_string(
        language,
        "language",
    )

    tone = _non_empty_string(
        tone,
        "tone",
    )

    output_format = (
        _non_empty_string(
            output_format,
            "output_format",
        )
    )

    if language not in (
        SUPPORTED_LANGUAGES
    ):
        raise ValueError(
            f"未対応のlanguageです: {language}"
        )

    if tone not in SUPPORTED_TONES:
        raise ValueError(
            f"未対応のtoneです: {tone}"
        )

    if output_format not in (
        SUPPORTED_OUTPUT_FORMATS
    ):
        raise ValueError(
            "output_formatはtextまたはjsonで指定してください。"
        )

    tone_text = {
        "professional_warm": (
            "専門性を保ちながら、"
            "親しみやすく落ち着いた日本語"
        ),
        "gentle": (
            "柔らかく安心感のある日本語"
        ),
        "concise": (
            "簡潔で要点を絞った日本語"
        ),
        "detailed": (
            "丁寧で十分な説明を含む日本語"
        ),
    }[
        tone
    ]

    format_rule = (
        "通常の日本語文章として出力してください。"
        if output_format == "text"
        else (
            "指定されたJSON構造に従い、"
            "JSON以外の文字を出力しないでください。"
        )
    )

    return f"""
あなたは四柱推命の鑑定文章を作成する専門AIです。

あなたの役割は「計算」ではありません。
入力された計算済みデータを、読みやすく誠実な鑑定文章へ変換することです。

【最重要ルール】

1. 四柱・日主・身強身弱・格局・用神・大運・歳運・統合運を再計算しないでください。
2. 入力された計算結果を事実として扱ってください。
3. 入力データと異なる日主・格局・用神・干支・通変星・十二運を新たに作らないでください。
4. 入力に存在しない情報を推測で補わないでください。
5. 不明値やnullは、必要に応じて「判断材料が不足している」と表現してください。
6. 計算結果と文章上の解釈を区別してください。
7. 単一の要素だけで人物像を決めつけないでください。
8. 吉凶を絶対視しないでください。
9. 将来について確定的に断定しないでください。「必ず起こる」「確実に成功する」などの表現を避けてください。
10. 運勢は傾向・流れ・活かし方として表現してください。
11. 読み手を不必要に怖がらせる表現を避けてください。
12. 悪い時期も「何を避けるか」「どう活かすか」を併記してください。
13. 良い時期も過度な楽観を煽らず、活かす条件を示してください。

【健康】

健康については医学的診断を行わないでください。
病名・発症・寿命を断定しないでください。
五行上の偏りや生活習慣上の注意傾向として表現してください。
必要な場合は医療専門家への相談を妨げない表現にしてください。

【金運・投資】

金運は占術上の傾向として説明してください。
具体的な金融商品の売買、必勝法、利益保証として表現しないでください。
重要な金融判断は現実の収支・リスク・専門情報を併用する前提で書いてください。

【仕事】

適職は「向いている可能性が高い領域」「能力を活かしやすい働き方」として示してください。
特定職業への転職を絶対的に勧めないでください。

【恋愛・人間関係】

相手の人格や未来の出来事を断定しないでください。
本人の傾向、関係構築の特徴、注意点として説明してください。

【文章品質】

- {tone_text}で書いてください。
- 専門用語は必要に応じて簡潔に説明してください。
- 同じ説明を繰り返さないでください。
- 読み手が行動に移せる具体性を持たせてください。
- 「あなたは絶対に〜」のような決めつけを避けてください。
- 計算データの羅列だけで終わらせず、意味を説明してください。

【商品品質の追加ルール】

- reading_context や consultation_context に根拠のない具体的な回数・頻度・期間・金額・件数・数値目標を作らないでください。
- 「週3回」「3か月」「5回」「毎月○円」などの具体的な回数や数値は、入力データに根拠がある場合を除き、事実のように提示しないでください。
- 根拠のない具体化で文章をもっともらしく見せないでください。
- 入力されていない職業、勤務先、役職、雇用形態、事業形態、年収、収入状況、家族構成、既婚・未婚、病歴などを事実として扱わず、暗黙に仮定しないでください。
- 相談者の職業や事業形態が入力されていない場合は、一般化した選択肢として説明し、特定の職業・会社員・経営者・自営業などと決めつけないでください。
- JSONの evidence は、内部キーや英語ラベルをそのまま並べるだけでなく、顧客が理解できる自然な日本語で記述してください。
- evidence には、可能な限り「どの計算済み事実が、どの解釈につながるか」が分かる表現を使ってください。
- 同じ五行でも、日主・五行バランス・用神・大運・歳運・格局など、どの文脈で現れているかによって意味や働き方が異なります。各セクションの目的と計算上の文脈に応じて意味を説明してください。
- 同じ五行をすべて同じ意味に固定せず、その五行がどの計算項目に現れているかを区別して説明してください。
- 五行を「水＝情報」「木＝成長」のような一語だけに固定し、すべてのセクションで機械的に繰り返さないでください。
- 相談内容に関連するセクションでは、相談者の問いを明示的に取り上げたうえで、計算済み事実 → 解釈 → 選択肢 → 実践的な行動の順で説明してください。
- 相談内容に直接関係しないセクションへ、無理に相談テーマを持ち込まないでください。
- 根拠のない具体的な回数・件数・期間・金額・数値目標を、四柱推命上の必然であるかのように表現しないでください。

【免責事項の品質】

JSON出力の disclaimer は、次の条件を必ず満たしてください。
- 「医学的診断」という表現を明示的に含めてください。
- 「投資助言」または「金融判断」に関する注意を含めてください。
- 将来を断定的に保証しないことを明記してください。
- 重要な判断では、必要に応じて「専門家」の意見や現実の情報も併用する旨を含めてください。
- disclaimer は短すぎず、顧客向けの自然な日本語にしてください。

【出力】

{format_rule}
""".strip()


# ============================================================
# Output schema
# ============================================================


def build_json_output_schema(
    sections: Optional[
        Sequence[str]
    ] = None,
) -> Dict[str, Any]:
    """
    JSON形式鑑定の期待構造を返す。
    """

    normalized = (
        _normalize_sections(
            sections
        )
    )

    section_properties = {}

    for section in normalized:
        section_properties[
            section
        ] = {
            "type": "object",
            "required": [
                "title",
                "summary",
                "detail",
                "evidence",
                "advice",
            ],
            "properties": {
                "title": {
                    "type": "string",
                },
                "summary": {
                    "type": "string",
                },
                "detail": {
                    "type": "string",
                },
                "evidence": {
                    "type": "array",
                    "items": {
                        "type": "string",
                    },
                },
                "advice": {
                    "type": "array",
                    "items": {
                        "type": "string",
                    },
                },
            },
        }

    return {
        "type": "object",
        "required": [
            "summary",
            "sections",
            "disclaimer",
        ],
        "properties": {
            "summary": {
                "type": "string",
            },
            "sections": {
                "type": "object",
                "required": list(
                    normalized
                ),
                "properties": (
                    section_properties
                ),
            },
            "disclaimer": {
                "type": "string",
            },
        },
    }


# ============================================================
# User prompt
# ============================================================


def build_user_prompt(
    reading_context: Mapping[
        str,
        Any,
    ],
    *,
    consultation_context: Optional[
        Mapping[str, Any]
    ] = None,
    sections: Optional[
        Sequence[str]
    ] = None,
    output_format: str = "text",
    min_section_chars: int = (
        DEFAULT_MIN_SECTION_CHARS
    ),
    max_section_chars: int = (
        DEFAULT_MAX_SECTION_CHARS
    ),
    include_raw_facts: bool = True,
) -> str:
    """
    reading_contextからuser promptを生成する。
    """

    reading_context = _require_mapping(
        reading_context,
        "reading_context",
    )

    validate_reading_context(
        reading_context
    )

    normalized_sections = (
        _normalize_sections(
            sections
        )
    )

    output_format = (
        _non_empty_string(
            output_format,
            "output_format",
        )
    )

    if output_format not in (
        SUPPORTED_OUTPUT_FORMATS
    ):
        raise ValueError(
            "output_formatはtextまたはjsonで指定してください。"
        )

    min_section_chars = (
        _require_positive_int(
            min_section_chars,
            "min_section_chars",
        )
    )

    max_section_chars = (
        _require_positive_int(
            max_section_chars,
            "max_section_chars",
        )
    )

    if (
        max_section_chars
        < min_section_chars
    ):
        raise ValueError(
            "max_section_charsは"
            "min_section_chars以上にしてください。"
        )

    include_raw_facts = _require_bool(
        include_raw_facts,
        "include_raw_facts",
    )

    instructions = (
        build_selected_section_instructions(
            reading_context,
            normalized_sections,
        )
    )

    facts = build_prompt_facts(
        reading_context
    )

    consultation_block = (
        build_consultation_prompt_block(
            consultation_context
        )
    )

    section_lines = []

    for index, item in enumerate(
        instructions,
        start=1,
    ):
        focus = "、".join(
            item["focus"]
        )

        section_lines.append(
            (
                f"{index}. "
                f"{item['title']} "
                f"({item['section']})\n"
                f"   参照領域: {focus}\n"
                f"   指示: {item['instruction']}"
            )
        )

    section_text = "\n\n".join(
        section_lines
    )

    if output_format == "json":
        schema = (
            build_json_output_schema(
                normalized_sections
            )
        )

        output_instruction = f"""
【出力形式】
JSONのみを返してください。
Markdownコードフェンスは付けないでください。

各 section の evidence は、顧客向けの自然な日本語で書いてください。
内部キーや英語ラベルをそのまま並べるだけにしないでください。

disclaimer には必ず、
- 医学的診断ではないこと
- 投資助言または金融判断を保証するものではないこと
- 将来を断定的に保証しないこと
- 重要な判断では必要に応じて専門家の意見や現実の情報も併用すること
を含めてください。

JSON Schema:
{_pretty_json(schema)}
""".strip()

    else:
        title_lines = [
            (
                f"- {SECTION_TITLES_JA[section]}"
            )
            for section
            in normalized_sections
        ]

        output_instruction = f"""
【出力形式】
最初に全体要約を書き、その後、次の順番で見出しを付けてください。

{chr(10).join(title_lines)}

各セクションは目安として
{min_section_chars}〜{max_section_chars}文字程度で書いてください。

各セクションでは、
「根拠となる計算結果 → 解釈 → 実践的な助言」
の順序を意識してください。
""".strip()

    raw_facts_block = ""

    if include_raw_facts:
        raw_facts_block = f"""
【計算済みデータ】
以下は既に計算済みの事実です。
再計算・修正・置換をしないでください。

{_pretty_json(facts)}
""".strip()

    return f"""
以下のreading_contextを基に四柱推命鑑定文を作成してください。

【絶対条件】

- 入力された計算結果を変更しないこと。
- 日主を再判定しないこと。
- 身強身弱を再判定しないこと。
- 格局を再判定しないこと。
- 用神を再選定しないこと。
- 大運を再計算しないこと。
- 歳運を再計算しないこと。
- 通変星を再計算しないこと。
- 十二運を再計算しないこと。
- 入力値と矛盾する干支を生成しないこと。
- 情報がない場合は推測で埋めないこと。

【鑑定対象セクション】

{section_text}

{consultation_block}

{output_instruction}

{raw_facts_block}

【文章上の注意】

1. 命式の特徴と現在の運勢を混同しないでください。
2. 生来の特徴は natal_chart / day_master / strength / pattern を中心に説明してください。
3. 現在の運勢は current_luck / annual_luck / integrated_luck を中心に説明してください。
4. useful_gods は「活かしやすい方向性」として扱ってください。
5. integrated_luck の overall_score は絶対的な吉凶値として扱わないでください。
6. confidence が低い場合は、断定度を下げてください。
7. 健康については医学的診断を行わないでください。
8. 金運については投資利益を保証しないでください。
9. 将来は確定的な未来ではなく、流れ・可能性として説明してください。
10. 読み手が実行できる具体的な行動提案を含めてください。
11. 根拠のない具体的な回数・頻度・期間・金額・数値目標を作らないでください。
12. 入力されていない職業・勤務先・役職・雇用形態・事業形態・収入状況などを事実として仮定しないでください。
13. JSONの evidence は、内部キーや英語ラベルだけで終わらせず、顧客が理解できる自然な日本語で書いてください。
14. evidence は、計算済み事実と解釈のつながりが分かる形にしてください。
15. 同じ五行でも、日主・五行バランス・用神・大運・歳運・格局などの文脈によって意味が異なることを意識してください。
16. 同じ五行を各セクションで同じ一語に固定して機械的に繰り返さないでください。
17. 相談に関係するセクションでは、相談者の具体的な問いに直接触れてください。
18. 相談に関係するセクションでは「計算済み事実 → 解釈 → 複数の選択肢 → 現実的な行動」の流れを意識してください。
19. 相談に関係しないセクションへ相談テーマを無理に持ち込まないでください。
20. 根拠のない具体化で文章をもっともらしく見せないでください。
""".strip()


# ============================================================
# Section-only prompt
# ============================================================


def build_section_prompt(
    reading_context: Mapping[
        str,
        Any,
    ],
    section: str,
    *,
    consultation_context: Optional[
        Mapping[str, Any]
    ] = None,
    output_format: str = "text",
    min_chars: int = (
        DEFAULT_MIN_SECTION_CHARS
    ),
    max_chars: int = (
        DEFAULT_MAX_SECTION_CHARS
    ),
) -> str:
    """
    1セクションのみの鑑定promptを生成する。
    """

    section = _non_empty_string(
        section,
        "section",
    )

    return build_user_prompt(
        reading_context,
        consultation_context=(
            consultation_context
        ),
        sections=(
            section,
        ),
        output_format=output_format,
        min_section_chars=min_chars,
        max_section_chars=max_chars,
    )


# ============================================================
# Messages
# ============================================================


def build_messages(
    reading_context: Mapping[
        str,
        Any,
    ],
    *,
    consultation_context: Optional[
        Mapping[str, Any]
    ] = None,
    sections: Optional[
        Sequence[str]
    ] = None,
    language: str = DEFAULT_LANGUAGE,
    tone: str = DEFAULT_TONE,
    output_format: str = "text",
    min_section_chars: int = (
        DEFAULT_MIN_SECTION_CHARS
    ),
    max_section_chars: int = (
        DEFAULT_MAX_SECTION_CHARS
    ),
    include_raw_facts: bool = True,
) -> List[Dict[str, str]]:
    """
    GPT APIへ渡しやすいmessages形式を生成する。
    """

    system_prompt = (
        build_system_prompt(
            language=language,
            tone=tone,
            output_format=output_format,
        )
    )

    user_prompt = build_user_prompt(
        reading_context,
        consultation_context=(
            consultation_context
        ),
        sections=sections,
        output_format=output_format,
        min_section_chars=(
            min_section_chars
        ),
        max_section_chars=(
            max_section_chars
        ),
        include_raw_facts=(
            include_raw_facts
        ),
    )

    return [
        {
            "role": "system",
            "content": system_prompt,
        },
        {
            "role": "user",
            "content": user_prompt,
        },
    ]


# ============================================================
# Reading request
# ============================================================


def build_reading_request(
    reading_context: Mapping[
        str,
        Any,
    ],
    *,
    consultation_context: Optional[
        Mapping[str, Any]
    ] = None,
    sections: Optional[
        Sequence[str]
    ] = None,
    language: str = DEFAULT_LANGUAGE,
    tone: str = DEFAULT_TONE,
    output_format: str = "text",
    min_section_chars: int = (
        DEFAULT_MIN_SECTION_CHARS
    ),
    max_section_chars: int = (
        DEFAULT_MAX_SECTION_CHARS
    ),
    include_raw_facts: bool = True,
) -> Dict[str, Any]:
    """
    AI実行層へ渡す標準request構造を生成する。
    """

    validation = (
        validate_reading_context(
            reading_context
        )
    )

    normalized_sections = (
        _normalize_sections(
            sections
        )
    )

    messages = build_messages(
        reading_context,
        consultation_context=(
            consultation_context
        ),
        sections=normalized_sections,
        language=language,
        tone=tone,
        output_format=output_format,
        min_section_chars=(
            min_section_chars
        ),
        max_section_chars=(
            max_section_chars
        ),
        include_raw_facts=(
            include_raw_facts
        ),
    )

    result = {
        "version": (
            READING_PROMPT_VERSION
        ),
        "sections": list(
            normalized_sections
        ),
        "language": language,
        "tone": tone,
        "output_format": (
            output_format
        ),
        "messages": messages,
        "validation": validation,
        "method": (
            READING_PROMPT_METHOD
        ),
        "status": (
            READING_PROMPT_STATUS
        ),
    }

    if output_format == "json":
        result[
            "output_schema"
        ] = build_json_output_schema(
            normalized_sections
        )

    else:
        result[
            "output_schema"
        ] = None

    return result


# ============================================================
# Compact request for external AI layer
# ============================================================


def build_compact_reading_request(
    reading_context: Mapping[
        str,
        Any,
    ],
    *,
    consultation_context: Optional[
        Mapping[str, Any]
    ] = None,
    sections: Optional[
        Sequence[str]
    ] = None,
    output_format: str = "text",
) -> Dict[str, Any]:
    """
    外部AI層向けの簡潔なrequestを生成する。
    """

    request = build_reading_request(
        reading_context,
        consultation_context=(
            consultation_context
        ),
        sections=sections,
        output_format=output_format,
    )

    return {
        "version": request[
            "version"
        ],
        "messages": deepcopy(
            request[
                "messages"
            ]
        ),
        "output_format": (
            request[
                "output_format"
            ]
        ),
        "output_schema": deepcopy(
            request[
                "output_schema"
            ]
        ),
        "method": request[
            "method"
        ],
        "status": request[
            "status"
        ],
    }


# ============================================================
# Prompt audit
# ============================================================


def audit_prompt_request(
    request: Mapping[
        str,
        Any,
    ],
) -> Dict[str, Any]:
    """
    生成済みreading requestの最低限整合性を確認する。
    """

    request = _require_mapping(
        request,
        "request",
    )

    messages = request.get(
        "messages"
    )

    if not isinstance(
        messages,
        list,
    ):
        raise TypeError(
            "request['messages']はlist型である必要があります。"
        )

    if len(messages) != 2:
        raise ValueError(
            "messagesはsystem/userの2件である必要があります。"
        )

    expected_roles = (
        "system",
        "user",
    )

    for index, role in enumerate(
        expected_roles
    ):
        message = messages[
            index
        ]

        if not isinstance(
            message,
            Mapping,
        ):
            raise TypeError(
                "messagesの各要素はdict型である必要があります。"
            )

        if message.get(
            "role"
        ) != role:
            raise ValueError(
                "messagesのrole順序が不正です。"
            )

        content = message.get(
            "content"
        )

        if (
            not isinstance(
                content,
                str,
            )
            or not content.strip()
        ):
            raise ValueError(
                "messagesのcontentが空です。"
            )

    system_text = messages[
        0
    ][
        "content"
    ]

    user_text = messages[
        1
    ][
        "content"
    ]

    required_system_phrases = (
        "再計算しない",
        "入力された計算結果",
        "医学的診断",
        "確定的",
    )

    missing_system_rules = [
        phrase
        for phrase
        in required_system_phrases
        if phrase not in system_text
    ]

    required_user_phrases = (
        "日主を再判定しない",
        "格局を再判定しない",
        "用神を再選定しない",
        "大運を再計算しない",
        "歳運を再計算しない",
    )

    missing_user_rules = [
        phrase
        for phrase
        in required_user_phrases
        if phrase not in user_text
    ]

    if (
        missing_system_rules
        or missing_user_rules
    ):
        raise ValueError(
            "プロンプトに必須ガードレールが不足しています。"
        )

    return {
        "valid": True,
        "message_count": 2,
        "system_rule_check": True,
        "user_rule_check": True,
        "method": "reading_prompt_audit_v1",
    }


# ============================================================
# Compatibility aliases
# ============================================================


def calculate_reading_prompt(
    reading_context: Mapping[
        str,
        Any,
    ],
    *,
    consultation_context: Optional[
        Mapping[str, Any]
    ] = None,
    sections: Optional[
        Sequence[str]
    ] = None,
    output_format: str = "text",
) -> Dict[str, Any]:
    """
    build_reading_request() の互換API。
    """

    return build_reading_request(
        reading_context,
        consultation_context=(
            consultation_context
        ),
        sections=sections,
        output_format=output_format,
    )


def prepare_ai_messages(
    reading_context: Mapping[
        str,
        Any,
    ],
    *,
    consultation_context: Optional[
        Mapping[str, Any]
    ] = None,
    sections: Optional[
        Sequence[str]
    ] = None,
    output_format: str = "text",
) -> List[Dict[str, str]]:
    """
    AI実行層向けmessages取得alias。
    """

    return build_messages(
        reading_context,
        consultation_context=(
            consultation_context
        ),
        sections=sections,
        output_format=output_format,
    )


def prepare_ai_reading_request(
    reading_context: Mapping[
        str,
        Any,
    ],
    *,
    consultation_context: Optional[
        Mapping[str, Any]
    ] = None,
    sections: Optional[
        Sequence[str]
    ] = None,
    output_format: str = "text",
) -> Dict[str, Any]:
    """
    AI実行層向けrequest取得alias。
    """

    return build_reading_request(
        reading_context,
        consultation_context=(
            consultation_context
        ),
        sections=sections,
        output_format=output_format,
    )


# ============================================================
# Public API
# ============================================================


__all__ = [
    "READING_PROMPT_VERSION",
    "READING_PROMPT_METHOD",
    "READING_PROMPT_STATUS",
    "SUPPORTED_OUTPUT_FORMATS",
    "SUPPORTED_LANGUAGES",
    "DEFAULT_LANGUAGE",
    "DEFAULT_TONE",
    "SUPPORTED_TONES",
    "DEFAULT_READING_SECTIONS",
    "SECTION_TITLES_JA",
    "DEFAULT_SECTION_ORDER",
    "DEFAULT_MIN_SECTION_CHARS",
    "DEFAULT_MAX_SECTION_CHARS",
    "DEFAULT_MIN_SUMMARY_CHARS",
    "DEFAULT_MAX_SUMMARY_CHARS",
    "validate_reading_context",
    "build_prompt_facts",
    "get_section_instruction",
    "build_selected_section_instructions",
    "build_consultation_prompt_block",
    "build_system_prompt",
    "build_json_output_schema",
    "build_user_prompt",
    "build_section_prompt",
    "build_messages",
    "build_reading_request",
    "build_compact_reading_request",
    "audit_prompt_request",
    "calculate_reading_prompt",
    "prepare_ai_messages",
    "prepare_ai_reading_request",
]
