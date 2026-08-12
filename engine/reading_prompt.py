"""
engine/reading_prompt.py

AI鑑定文生成用プロンプト構築モジュール。

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


def _require_mapping(
    value: Any,
    name: str,
) -> Mapping[str, Any]:
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


def validate_reading_context(
    reading_context: Mapping[
        str,
        Any,
    ],
) -> Dict[str, Any]:
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


def build_prompt_facts(
    reading_context: Mapping[
        str,
        Any,
    ],
) -> Dict[str, Any]:
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
    integrated_luck = _safe_dict(
        luck.get(
            "integrated_luck"
        )
    )

    return {
        "subject": {
            "birth_date": subject.get("birth_date"),
            "birth_time": subject.get("birth_time"),
            "birth_place": subject.get("birth_place"),
            "gender": subject.get("gender"),
            "timezone": subject.get("timezone"),
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
            "primary_useful_element": useful_gods.get(
                "primary_useful_element"
            ),
            "secondary_useful_elements": _safe_list(
                useful_gods.get(
                    "secondary_useful_elements"
                )
            ),
            "final_useful_elements": _safe_list(
                useful_gods.get(
                    "final_useful_elements"
                )
            ),
            "unfavorable_elements": _safe_list(
                useful_gods.get(
                    "unfavorable_elements"
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
                "direction": luck_pillars.get(
                    "direction"
                ),
                "direction_japanese": luck_pillars.get(
                    "direction_japanese"
                ),
                "start_age": luck_pillars.get(
                    "start_age"
                ),
                "pillars": _safe_list(
                    luck_pillars.get(
                        "pillars"
                    )
                ),
            },
            "current_luck": {
                "has_current_luck": current_luck.get(
                    "has_current_luck"
                ),
                "phase": current_luck.get(
                    "phase"
                ),
                "exact_age": current_luck.get(
                    "exact_age"
                ),
                "calendar_age": current_luck.get(
                    "calendar_age"
                ),
                "current_pillar": current_luck.get(
                    "current_pillar"
                ),
                "previous_pillar": current_luck.get(
                    "previous_pillar"
                ),
                "next_pillar": current_luck.get(
                    "next_pillar"
                ),
                "progress": current_luck.get(
                    "progress"
                ),
                "years_until_next_luck": current_luck.get(
                    "years_until_next_luck"
                ),
            },
            "annual_luck": {
                "year": annual_luck.get(
                    "year"
                ),
                "effective_year": annual_luck.get(
                    "effective_year"
                ),
                "ganzhi": annual_luck.get(
                    "ganzhi"
                ),
                "stem_element": annual_luck.get(
                    "stem_element"
                ),
                "branch_element": annual_luck.get(
                    "branch_element"
                ),
                "stem_ten_god": annual_luck.get(
                    "stem_ten_god"
                ),
                "twelve_stage": annual_luck.get(
                    "twelve_stage"
                ),
                "stem_useful_relation": annual_luck.get(
                    "stem_useful_relation"
                ),
                "branch_useful_relation": annual_luck.get(
                    "branch_useful_relation"
                ),
                "current_luck_relation": annual_luck.get(
                    "current_luck_relation"
                ),
            },
            "integrated_luck": {
                "current_luck_ganzhi": integrated_luck.get(
                    "current_luck_ganzhi"
                ),
                "annual_luck_ganzhi": integrated_luck.get(
                    "annual_luck_ganzhi"
                ),
                "agreement_level": integrated_luck.get(
                    "agreement_level"
                ),
                "overall_score": integrated_luck.get(
                    "overall_score"
                ),
                "overall_level": integrated_luck.get(
                    "overall_level"
                ),
                "confidence": integrated_luck.get(
                    "confidence"
                ),
                "annual_ten_god": integrated_luck.get(
                    "annual_ten_god"
                ),
                "annual_twelve_stage": integrated_luck.get(
                    "annual_twelve_stage"
                ),
                "element_interactions": integrated_luck.get(
                    "element_interactions"
                ),
                "current_luck_useful": integrated_luck.get(
                    "current_luck_useful"
                ),
                "annual_luck_useful": integrated_luck.get(
                    "annual_luck_useful"
                ),
            },
        },
    }


def get_section_instruction(
    reading_context: Mapping[
        str,
        Any,
    ],
    section: str,
) -> Dict[str, Any]:
    reading_context = _require_mapping(
        reading_context,
        "reading_context",
    )

    section = _non_empty_string(
        section,
        "section",
    )

    if section not in DEFAULT_READING_SECTIONS:
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
        "title": SECTION_TITLES_JA[
            section
        ],
        "focus": _safe_list(
            raw_section.get(
                "focus"
            )
        ),
        "instruction": raw_section.get(
            "instruction"
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
    normalized = _normalize_sections(
        sections
    )

    return [
        get_section_instruction(
            reading_context,
            section,
        )
        for section in normalized
    ]


def build_system_prompt(
    *,
    language: str = DEFAULT_LANGUAGE,
    tone: str = DEFAULT_TONE,
    output_format: str = "text",
) -> str:
    language = _non_empty_string(
        language,
        "language",
    )
    tone = _non_empty_string(
        tone,
        "tone",
    )
    output_format = _non_empty_string(
        output_format,
        "output_format",
    )

    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(
            f"未対応のlanguageです: {language}"
        )

    if tone not in SUPPORTED_TONES:
        raise ValueError(
            f"未対応のtoneです: {tone}"
        )

    if output_format not in SUPPORTED_OUTPUT_FORMATS:
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
9. 将来を確定的に予言しないでください。
10. 将来について「必ず起こる」「確実に成功する」などの断定を避けてください。
11. 運勢は傾向・流れ・活かし方として表現してください。
12. 読み手を不必要に怖がらせる表現を避けてください。
13. 悪い時期も「何を避けるか」「どう活かすか」を併記してください。
14. 良い時期も過度な楽観を煽らず、活かす条件を示してください。

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

【商品品質の文章設計】

- {tone_text}で書いてください。
- 鑑定全体を、項目ごとの説明の寄せ集めではなく、一人の人物を多面的に読み解く一貫した鑑定として構成してください。
- 命式全体から中心となる人物テーマを捉え、各セクションでは同じテーマを単純反復せず、その領域固有の意味へ展開してください。
- 入力に存在しない人生経験、職歴、家族構成、過去の出来事、将来の出来事を創作してはいけません。
- 日主・格局・身強身弱・五行・用神・大運・歳運を、すべてのセクションで機械的に繰り返さないでください。
- 同じ計算根拠を複数セクションで参照する場合も、同じ説明文を繰り返さず、そのセクションの問いに合わせて意味を翻訳してください。
- 専門用語は必要な場合だけ使い、初見の読者にも意味が伝わる自然な日本語を添えてください。
- technical_label、overall_score、overall_level、confidence、agreement_level、mixed、useful、secondary_useful 等の内部キー名・英語ラベル・実装上の表現を、顧客向けの summary / detail / advice にそのまま露出させないでください。
- evidence は入力データに基づく根拠を簡潔に示して構いませんが、内部パスの羅列だけにせず、人が読んで意味を理解できる表現を優先してください。
- 第一用神 primary_useful_element と補助用神 secondary_useful_elements を明確に区別してください。第一用神を中心的な調整方向、補助用神を状況に応じて助けになる要素として扱ってください。
- final_useful_elements に複数の五行が含まれていても、すべてを同格の「用神」として並べないでください。
- 用神を万能な吉要素、幸運保証、単純なラッキー要素として扱わないでください。
- 「〜タイプです」「〜傾向があります」「〜しやすいです」の連発を避け、文章表現に変化を持たせてください。
- 誰にでも当てはまりやすい一般論より、入力された命式要素の組み合わせから説明できる内容を優先してください。
- 根拠から導けない具体的職業、出来事、成功時期、結婚時期、病気、収入額などを作らないでください。
- 長所だけを並べず、強み・扱いにくさ・活かし方をセットで説明してください。
- 読み手を持ち上げるだけの文章にも、不安を煽る文章にもせず、現実的で前向きな鑑定にしてください。
- 計算データを羅列して終わらせず、「それが本人にとって何を意味するか」を人間の言葉へ翻訳してください。
- 読み手が「自分の場合、次に何を意識すればよいか」まで理解できる具体性を持たせてください。
- 命式・大運・歳運などの入力データから直接導けない具体的な回数・頻度・件数・割合・金額・期限を、四柱推命上の必然として新たに設定しないでください。
- 具体策が必要な場合は、「定期的に」「少数に絞る」「一定期間試す」「一度時間を置く」など、占術上の根拠を超えない中立的な表現を優先してください。
- subject / reading_context に職業・役職・事業形態・家族構成・恋愛状況・資産状況などが存在しない場合、それらを暗黙に仮定しないでください。
- 職業情報がない場合は、「顧客」「売上」「料金表」「契約」「上長」「KPI」「サブスク」「案件獲得」など特定の会社員・経営者・事業者像を前提とする語を必要以上に使わず、「仕事」「役割」「成果」「判断」「日常の選択」など中立的な語へ置き換えてください。
- 同じ五行でも、各セクションの役割に応じて意味を自然に翻訳してください。たとえば金を、仕事では「整理・判断・品質」、金運では「管理・選別」、人間関係では「境界線・意思表示」、現在運では「優先順位・取捨選択」のように文脈に合わせて扱い、すべての章を同じ「ルール化」の説明にしないでください。
- evidence は計算済み事実だけを使い、顧客が読める自然な日本語へ翻訳してください。内部パス、内部キー、英語ラベル、実装上の表現をそのまま列挙せず、「日柱：丁巳」「格局：食神格」「身強・身弱：中和」のような形式を優先してください。

【セクション別の役割】

- 本質・性格:
  人物像、思考・感情・行動の特徴、自然に発揮される強み、負荷がかかった時に出やすい課題を中心に書いてください。
  仕事や金運の話へ広げすぎないでください。

- 仕事・適職:
  職業名の羅列ではなく、能力が活きる役割、仕事の進め方、環境、成果の出し方を中心に書いてください。
  特定職種を挙げる場合は、入力根拠から自然に導ける例示に留めてください。

- 金運:
  金額や儲けを予言せず、価値を生む方法、収入との結びつき、管理・守り方、判断上の注意を中心に書いてください。
  投資成果を保証しないでください。

- 恋愛・人間関係:
  相手の人物像や未来を予言せず、本人の距離感、関係構築、伝え方、境界線、対人上の強みと注意点を中心に書いてください。

- 健康傾向:
  五行から病名、臓器異常、発症、寿命を推測・断定しないでください。
  心身の負荷を減らす一般的な生活習慣、休息、生活リズムなどの範囲で助言してください。

- 現在の運勢:
  大運・歳運・統合運を用いて、現在のテーマ、追い風、注意点を整理してください。
  最後に「今は何を優先し、何を急がない方がよいか」が伝わる内容にしてください。

- 今後の流れ:
  大運を順番に羅列するだけでなく、人生のテーマや力の使い方がどのように移り変わる可能性があるかを時間軸で説明してください。
  遠い未来ほど断定度を下げてください。

- 総合アドバイス:
  他セクションの要約を繰り返すだけにしないでください。
  鑑定全体を統合し、今から優先して取り組める行動へ落とし込んでください。

【出力】

{format_rule}
""".strip()


def build_json_output_schema(
    sections: Optional[
        Sequence[str]
    ] = None,
) -> Dict[str, Any]:
    normalized = _normalize_sections(
        sections
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


def build_user_prompt(
    reading_context: Mapping[
        str,
        Any,
    ],
    *,
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
    reading_context = _require_mapping(
        reading_context,
        "reading_context",
    )

    validate_reading_context(
        reading_context
    )

    normalized_sections = _normalize_sections(
        sections
    )

    output_format = _non_empty_string(
        output_format,
        "output_format",
    )

    if output_format not in SUPPORTED_OUTPUT_FORMATS:
        raise ValueError(
            "output_formatはtextまたはjsonで指定してください。"
        )

    min_section_chars = _require_positive_int(
        min_section_chars,
        "min_section_chars",
    )

    max_section_chars = _require_positive_int(
        max_section_chars,
        "max_section_chars",
    )

    if max_section_chars < min_section_chars:
        raise ValueError(
            "max_section_charsは"
            "min_section_chars以上にしてください。"
        )

    include_raw_facts = _require_bool(
        include_raw_facts,
        "include_raw_facts",
    )

    instructions = build_selected_section_instructions(
        reading_context,
        normalized_sections,
    )

    facts = build_prompt_facts(
        reading_context
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
        schema = build_json_output_schema(
            normalized_sections
        )

        output_instruction = f"""
【出力形式】
JSONのみを返してください。
Markdownコードフェンスは付けないでください。

JSON Schema:
{_pretty_json(schema)}
""".strip()

    else:
        title_lines = [
            f"- {SECTION_TITLES_JA[section]}"
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

{output_instruction}

{raw_facts_block}

【文章上の注意】

1. 命式の特徴と現在の運勢を混同しないでください。
2. 生来の特徴は natal_chart / day_master / strength / pattern を中心に説明してください。
3. 現在の運勢は current_luck / annual_luck / integrated_luck を中心に説明してください。
4. useful_gods は命式を整える「活かしやすい方向性」として扱ってください。
5. primary_useful_element を中心的な調整方向、secondary_useful_elements を補助的な要素として区別してください。
6. final_useful_elements に複数要素があっても、すべてを同格の第一用神として説明しないでください。
7. integrated_luck の overall_score は絶対的な吉凶値として扱わないでください。
8. overall_level、mixed、agreement_level、confidence 等の内部ラベルを summary / detail / advice にそのまま出さず、自然な日本語へ翻訳してください。
9. confidence が低い場合は断定度を下げてください。ただし内部キー名そのものを顧客向け本文へ出す必要はありません。
10. 本質・仕事・金運・人間関係・健康・現在運・未来運・総合助言で、同じ説明を機械的に繰り返さないでください。
11. 各セクションには固有の役割を持たせ、同じ命式要素でもそのテーマに即した解釈へ変換してください。
12. 健康については医学的診断を行わず、五行だけから病名・臓器異常・発症・寿命を推測しないでください。
13. 金運については投資利益、収入増加、成功を保証しないでください。
14. 将来は確定的な未来ではなく、流れ・可能性・準備の方向として説明してください。
15. 入力にない職業、出来事、人物、時期、金額、過去の経験を創作しないでください。
16. advice は抽象的な精神論だけにせず、現実に実行できる行動へ落とし込んでください。
17. 全セクションを通して一貫した人物像を保ちつつ、文章の重複は避けてください。
18. summary はそのセクションの結論、detail は計算結果を人間の言葉へ翻訳した解釈、evidence は計算済み事実、advice は具体策として役割を分けてください。
19. evidence でも存在しない計算値を作らず、入力にある事実だけを使ってください。
20. JSON Schemaのキー、階層、必須フィールドを変更せず、指定されたセクションだけを返してください。
21. 入力に根拠のない具体的な回数・頻度・件数・割合・金額・期限を、四柱推命上の必然として新たに設定しないでください。
22. 「週1回」「月2件」「2〜3本」「四半期に1件」など、入力に根拠のない数値目標を独自に作らず、「定期的に」「少数に絞る」「一度時間を置く」など中立的に表現してください。
23. subject / reading_context に職業・役職・事業形態・家族構成・恋愛状況・資産状況が存在しない場合、それらを推測しないでください。
24. 職業情報がない場合、「顧客」「売上」「料金」「契約」「上長」「KPI」「サブスク」「案件獲得」等を前提にせず、一般的な仕事・役割・成果・判断として説明してください。
25. 同じ五行の象意を全セクションで同じ意味に固定せず、各セクションの役割に応じた自然な日本語へ翻訳してください。
26. evidence は入力に存在する計算済み事実のみを使い、内部キー名・内部パス・英語ラベルを可能な限り避けて、顧客が読める日本語の根拠として出力してください。
""".strip()


def build_section_prompt(
    reading_context: Mapping[
        str,
        Any,
    ],
    section: str,
    *,
    output_format: str = "text",
    min_chars: int = (
        DEFAULT_MIN_SECTION_CHARS
    ),
    max_chars: int = (
        DEFAULT_MAX_SECTION_CHARS
    ),
) -> str:
    section = _non_empty_string(
        section,
        "section",
    )

    return build_user_prompt(
        reading_context,
        sections=(
            section,
        ),
        output_format=output_format,
        min_section_chars=min_chars,
        max_section_chars=max_chars,
    )


def build_messages(
    reading_context: Mapping[
        str,
        Any,
    ],
    *,
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
    system_prompt = build_system_prompt(
        language=language,
        tone=tone,
        output_format=output_format,
    )

    user_prompt = build_user_prompt(
        reading_context,
        sections=sections,
        output_format=output_format,
        min_section_chars=min_section_chars,
        max_section_chars=max_section_chars,
        include_raw_facts=include_raw_facts,
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


def build_reading_request(
    reading_context: Mapping[
        str,
        Any,
    ],
    *,
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
    validation = validate_reading_context(
        reading_context
    )

    normalized_sections = _normalize_sections(
        sections
    )

    messages = build_messages(
        reading_context,
        sections=normalized_sections,
        language=language,
        tone=tone,
        output_format=output_format,
        min_section_chars=min_section_chars,
        max_section_chars=max_section_chars,
        include_raw_facts=include_raw_facts,
    )

    result = {
        "version": READING_PROMPT_VERSION,
        "sections": list(
            normalized_sections
        ),
        "language": language,
        "tone": tone,
        "output_format": output_format,
        "messages": messages,
        "validation": validation,
        "method": READING_PROMPT_METHOD,
        "status": READING_PROMPT_STATUS,
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


def build_compact_reading_request(
    reading_context: Mapping[
        str,
        Any,
    ],
    *,
    sections: Optional[
        Sequence[str]
    ] = None,
    output_format: str = "text",
) -> Dict[str, Any]:
    request = build_reading_request(
        reading_context,
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
        "output_format": request[
            "output_format"
        ],
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


def audit_prompt_request(
    request: Mapping[
        str,
        Any,
    ],
) -> Dict[str, Any]:
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


def calculate_reading_prompt(
    reading_context: Mapping[
        str,
        Any,
    ],
    *,
    sections: Optional[
        Sequence[str]
    ] = None,
    output_format: str = "text",
) -> Dict[str, Any]:
    return build_reading_request(
        reading_context,
        sections=sections,
        output_format=output_format,
    )


def prepare_ai_messages(
    reading_context: Mapping[
        str,
        Any,
    ],
    *,
    sections: Optional[
        Sequence[str]
    ] = None,
    output_format: str = "text",
) -> List[Dict[str, str]]:
    return build_messages(
        reading_context,
        sections=sections,
        output_format=output_format,
    )


def prepare_ai_reading_request(
    reading_context: Mapping[
        str,
        Any,
    ],
    *,
    sections: Optional[
        Sequence[str]
    ] = None,
    output_format: str = "text",
) -> Dict[str, Any]:
    return build_reading_request(
        reading_context,
        sections=sections,
        output_format=output_format,
    )


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
