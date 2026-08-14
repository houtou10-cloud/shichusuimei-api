"""
tests/test_reading_consultation_quality.py

相談連動型AI鑑定の品質ゲート。

目的
----
consultation_context_v1 を reading_prompt_v1 に連携したとき、

1. 相談内容がAIプロンプトへ正しく渡る
2. 相談内容が命式上の根拠として扱われない
3. 顧客の希望に迎合しない
4. 命式・日主・身強身弱・格局・用神・運勢を再計算しない
5. 将来を確定的に断言しない
6. 相談テーマに応じた具体的説明を促す
7. 転職・金運・恋愛・健康などの主要相談へ対応する
8. consultation_context が無い場合の既存動作を壊さない

ことを固定する。

このテストは原則としてOpenAI APIを呼ばない。
prompt構築レイヤーの品質保証を目的とする。
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict

import pytest

from engine.consultation_context import (
    build_consultation_context,
)
from engine.reading_prompt import (
    DEFAULT_READING_SECTIONS,
    READING_PROMPT_METHOD,
    READING_PROMPT_STATUS,
    READING_PROMPT_VERSION,
    audit_prompt_request,
    build_compact_reading_request,
    build_consultation_prompt_block,
    build_messages,
    build_reading_request,
    build_section_prompt,
    build_system_prompt,
    build_user_prompt,
)


# ============================================================
# Test constants
# ============================================================


EXPECTED_SECTIONS = (
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
# Fixtures
# ============================================================


@pytest.fixture
def reading_context() -> Dict[str, Any]:
    """
    reading_prompt_v1 が要求する最低限の
    reading_context_v1 を構築する。

    実際の占術計算をこのテストでは行わない。
    prompt連携の品質確認に必要な固定値のみ使用する。
    """

    return {
        "schema_version": "reading_context_v1",
        "subject": {
            "birth_date": "1990-05-15",
            "birth_time": "14:30",
            "birth_place": "東京都",
            "gender": "male",
            "timezone": "Asia/Tokyo",
        },
        "natal_chart": {
            "pillar_sequence": [
                "庚午",
                "辛巳",
                "乙亥",
                "癸未",
            ],
            "pillars": {
                "year": {
                    "ganzhi": "庚午",
                },
                "month": {
                    "ganzhi": "辛巳",
                },
                "day": {
                    "ganzhi": "乙亥",
                },
                "hour": {
                    "ganzhi": "癸未",
                },
            },
        },
        "day_master": {
            "stem": "乙",
            "element": "木",
            "yin_yang": "陰",
        },
        "five_elements": {
            "wood": 2,
            "fire": 2,
            "earth": 1,
            "metal": 2,
            "water": 2,
        },
        "strength": {
            "technical_label": "balanced",
            "label": "中和",
            "final_score": 50.0,
            "confidence": "medium",
        },
        "pattern": {
            "primary_pattern": "正官格",
            "technical_pattern": "proper_officer",
            "overall_judgment": "成立",
            "confidence": "medium",
        },
        "useful_gods": {
            "primary_useful_element": "水",
            "secondary_useful_elements": [
                "木",
            ],
            "final_useful_elements": [
                "水",
                "木",
            ],
            "unfavorable_elements": [
                "金",
            ],
            "strength_class": "balanced",
            "confidence": "medium",
            "agreement_level": "medium",
        },
        "luck": {
            "luck_pillars": {
                "direction": "forward",
                "direction_japanese": "順行",
                "start_age": 5.0,
                "pillars": [
                    {
                        "ganzhi": "壬午",
                        "start_age": 5,
                    },
                    {
                        "ganzhi": "癸未",
                        "start_age": 15,
                    },
                    {
                        "ganzhi": "甲申",
                        "start_age": 25,
                    },
                    {
                        "ganzhi": "乙酉",
                        "start_age": 35,
                    },
                ],
            },
            "current_luck": {
                "has_current_luck": True,
                "phase": "middle",
                "exact_age": 36.0,
                "calendar_age": 36,
                "current_pillar": {
                    "ganzhi": "乙酉",
                },
                "previous_pillar": {
                    "ganzhi": "甲申",
                },
                "next_pillar": {
                    "ganzhi": "丙戌",
                },
                "progress": 0.1,
                "years_until_next_luck": 9.0,
            },
            "annual_luck": {
                "year": 2026,
                "effective_year": 2026,
                "ganzhi": "丙午",
                "stem_element": "火",
                "branch_element": "火",
                "stem_ten_god": "傷官",
                "twelve_stage": "長生",
                "stem_useful_relation": "neutral",
                "branch_useful_relation": "neutral",
                "current_luck_relation": "mixed",
            },
            "integrated_luck": {
                "current_luck_ganzhi": "乙酉",
                "annual_luck_ganzhi": "丙午",
                "agreement_level": "medium",
                "overall_score": 55.0,
                "overall_level": "moderate",
                "confidence": "medium",
                "annual_ten_god": "傷官",
                "annual_twelve_stage": "長生",
                "element_interactions": [],
                "current_luck_useful": "mixed",
                "annual_luck_useful": "neutral",
            },
        },
        "reading_sections": {
            "core_personality": {
                "focus": [
                    "day_master",
                    "strength",
                    "pattern",
                ],
                "instruction": (
                    "日主・身強身弱・格局を中心に、"
                    "本人の本質と強みを説明してください。"
                ),
            },
            "career": {
                "focus": [
                    "day_master",
                    "pattern",
                    "useful_gods",
                    "current_luck",
                ],
                "instruction": (
                    "仕事上の強み、働き方、"
                    "現在の仕事運を説明してください。"
                ),
            },
            "wealth": {
                "focus": [
                    "pattern",
                    "useful_gods",
                    "current_luck",
                    "annual_luck",
                ],
                "instruction": (
                    "金運の傾向と現実的な注意点を"
                    "説明してください。"
                ),
            },
            "relationships": {
                "focus": [
                    "day_master",
                    "pattern",
                ],
                "instruction": (
                    "恋愛・人間関係の傾向を"
                    "説明してください。"
                ),
            },
            "health": {
                "focus": [
                    "five_elements",
                    "strength",
                ],
                "instruction": (
                    "五行上の偏りを中心に、"
                    "健康傾向を非診断的に説明してください。"
                ),
            },
            "current_luck": {
                "focus": [
                    "current_luck",
                    "annual_luck",
                    "integrated_luck",
                ],
                "instruction": (
                    "現在の大運・歳運・統合運を"
                    "説明してください。"
                ),
            },
            "future_flow": {
                "focus": [
                    "current_luck",
                    "annual_luck",
                    "integrated_luck",
                ],
                "instruction": (
                    "今後の流れを断定せず、"
                    "可能性として説明してください。"
                ),
            },
            "advice": {
                "focus": [
                    "day_master",
                    "useful_gods",
                    "current_luck",
                    "integrated_luck",
                ],
                "instruction": (
                    "命式と現在の運勢を踏まえ、"
                    "実行可能な助言を提示してください。"
                ),
            },
        },
        "source_metadata": {
            "astrology_source": "calculated",
            "ai_recalculation": False,
        },
        "method": "reading_context_v1",
        "status": "ready_for_reading",
    }


@pytest.fixture
def career_consultation() -> Dict[str, Any]:
    return build_consultation_context(
        concern=(
            "今の仕事を続けるか転職するか悩んでいます。"
            "収入にも不安があります。"
        ),
        desired_future=(
            "自分の強みを活かして"
            "安定した収入を得たいです。"
        ),
    )


@pytest.fixture
def wealth_consultation() -> Dict[str, Any]:
    return build_consultation_context(
        concern=(
            "収入がなかなか増えず、"
            "今後のお金について不安があります。"
        ),
        desired_future=(
            "収入を安定させて、"
            "将来のお金の不安を減らしたいです。"
        ),
    )


@pytest.fixture
def relationship_consultation() -> Dict[str, Any]:
    return build_consultation_context(
        concern=(
            "恋愛がなかなかうまくいかず、"
            "良い関係を築けるか悩んでいます。"
        ),
        desired_future=(
            "自分に合う相手と"
            "安定した関係を築きたいです。"
        ),
    )


@pytest.fixture
def health_consultation() -> Dict[str, Any]:
    return build_consultation_context(
        concern=(
            "最近健康について不安を感じています。"
            "生活習慣も見直したいです。"
        ),
        desired_future=(
            "無理をせず健康的な生活を"
            "続けたいです。"
        ),
    )


@pytest.fixture
def self_understanding_consultation() -> Dict[str, Any]:
    return build_consultation_context(
        concern=(
            "自分の強みや向いていることが"
            "よく分かりません。"
        ),
        desired_future=(
            "自分の特徴を理解して、"
            "自分らしい選択をしたいです。"
        ),
    )


# ============================================================
# Basic identity
# ============================================================


def test_prompt_version_kept():
    assert (
        READING_PROMPT_VERSION
        == "reading_prompt_v1"
    )


def test_prompt_method_kept():
    assert (
        READING_PROMPT_METHOD
        == "reading_prompt_v1"
    )


def test_prompt_status_kept():
    assert (
        READING_PROMPT_STATUS
        == "ready_for_ai_generation"
    )


def test_default_sections_kept():
    assert tuple(
        DEFAULT_READING_SECTIONS
    ) == EXPECTED_SECTIONS


# ============================================================
# Consultation block
# ============================================================


def test_consultation_block_contains_concern(
    career_consultation,
):
    text = build_consultation_prompt_block(
        career_consultation
    )

    assert (
        "今の仕事を続けるか転職するか"
        in text
    )


def test_consultation_block_contains_desired_future(
    career_consultation,
):
    text = build_consultation_prompt_block(
        career_consultation
    )

    assert (
        "安定した収入"
        in text
    )


def test_consultation_block_marks_customer_input_as_non_astrology(
    career_consultation,
):
    text = build_consultation_prompt_block(
        career_consultation
    )

    assert (
        "四柱推命上の計算結果・根拠ではありません"
        in text
    )


def test_consultation_block_forbids_recalculation(
    career_consultation,
):
    text = build_consultation_prompt_block(
        career_consultation
    )

    assert "再計算" in text
    assert "変更" in text


def test_consultation_block_forbids_customer_pleasing(
    career_consultation,
):
    text = build_consultation_prompt_block(
        career_consultation
    )

    assert (
        "相談者が望む結論へ迎合しない"
        in text
    )


def test_consultation_block_requires_realistic_options(
    career_consultation,
):
    text = build_consultation_prompt_block(
        career_consultation
    )

    assert "現実的な選択肢" in text
    assert "注意点" in text
    assert "活かし方" in text


def test_consultation_block_forbids_future_certainty(
    career_consultation,
):
    text = build_consultation_prompt_block(
        career_consultation
    )

    assert "確定的" in text


def test_none_consultation_block_is_empty():
    assert (
        build_consultation_prompt_block(None)
        == ""
    )


# ============================================================
# System prompt guardrails
# ============================================================


def test_system_prompt_forbids_recalculation():
    text = build_system_prompt()

    assert "再計算しない" in text


def test_system_prompt_contains_certainty_guardrail():
    text = build_system_prompt()

    assert "確定的" in text
    assert "必ず起こる" in text
    assert "確実に成功する" in text


def test_system_prompt_contains_health_guardrail():
    text = build_system_prompt()

    assert "医学的診断" in text
    assert "病名" in text
    assert "寿命" in text


def test_system_prompt_contains_financial_guardrail():
    text = build_system_prompt()

    assert "利益保証" in text
    assert "金融判断" in text


def test_system_prompt_contains_career_guardrail():
    text = build_system_prompt()

    assert (
        "特定職業への転職を絶対的に勧めない"
        in text
    )


def test_system_prompt_contains_relationship_guardrail():
    text = build_system_prompt()

    assert (
        "相手の人格や未来の出来事を断定しない"
        in text
    )


# ============================================================
# Career consultation
# ============================================================


def test_career_consultation_detected(
    career_consultation,
):
    assert (
        career_consultation[
            "focus"
        ][
            "primary"
        ]
        == "career"
    )


def test_career_consultation_prioritizes_career(
    career_consultation,
):
    priority = career_consultation[
        "focus"
    ][
        "priority_sections"
    ]

    assert "career" in priority


def test_career_prompt_contains_customer_question(
    reading_context,
    career_consultation,
):
    text = build_user_prompt(
        reading_context,
        consultation_context=(
            career_consultation
        ),
    )

    assert "転職" in text
    assert "収入" in text


def test_career_prompt_contains_career_section(
    reading_context,
    career_consultation,
):
    text = build_user_prompt(
        reading_context,
        consultation_context=(
            career_consultation
        ),
    )

    assert "仕事・適職" in text


def test_career_prompt_does_not_force_job_change(
    reading_context,
    career_consultation,
):
    text = build_user_prompt(
        reading_context,
        consultation_context=(
            career_consultation
        ),
    )

    assert (
        "相談者が望む結論へ迎合しない"
        in text
    )

    assert (
        "未来や意思決定を確定的に断言しない"
        in text
    )


# ============================================================
# Wealth consultation
# ============================================================


def test_wealth_consultation_detected(
    wealth_consultation,
):
    detected = wealth_consultation[
        "focus"
    ][
        "detected_categories"
    ]

    assert "wealth" in detected


def test_wealth_prompt_contains_money_context(
    reading_context,
    wealth_consultation,
):
    text = build_user_prompt(
        reading_context,
        consultation_context=(
            wealth_consultation
        ),
    )

    assert (
        "お金"
        in text
        or "収入"
        in text
    )


def test_wealth_prompt_keeps_financial_safety(
    reading_context,
    wealth_consultation,
):
    messages = build_messages(
        reading_context,
        consultation_context=(
            wealth_consultation
        ),
    )

    system_text = messages[0][
        "content"
    ]

    assert "利益保証" in system_text
    assert "金融判断" in system_text


# ============================================================
# Relationship consultation
# ============================================================


def test_relationship_consultation_detected(
    relationship_consultation,
):
    detected = relationship_consultation[
        "focus"
    ][
        "detected_categories"
    ]

    assert "relationships" in detected


def test_relationship_prompt_contains_relationship_context(
    reading_context,
    relationship_consultation,
):
    text = build_user_prompt(
        reading_context,
        consultation_context=(
            relationship_consultation
        ),
    )

    assert "恋愛" in text
    assert "関係" in text


def test_relationship_prompt_keeps_non_certainty_rule(
    reading_context,
    relationship_consultation,
):
    messages = build_messages(
        reading_context,
        consultation_context=(
            relationship_consultation
        ),
    )

    system_text = messages[0][
        "content"
    ]

    assert (
        "相手の人格や未来の出来事を断定しない"
        in system_text
    )


# ============================================================
# Health consultation
# ============================================================


def test_health_consultation_detected(
    health_consultation,
):
    detected = health_consultation[
        "focus"
    ][
        "detected_categories"
    ]

    assert "health" in detected


def test_health_prompt_contains_health_context(
    reading_context,
    health_consultation,
):
    text = build_user_prompt(
        reading_context,
        consultation_context=(
            health_consultation
        ),
    )

    assert "健康" in text


def test_health_prompt_keeps_medical_guardrail(
    reading_context,
    health_consultation,
):
    messages = build_messages(
        reading_context,
        consultation_context=(
            health_consultation
        ),
    )

    system_text = messages[0][
        "content"
    ]

    assert "医学的診断" in system_text
    assert "病名" in system_text


# ============================================================
# Self understanding
# ============================================================


def test_self_understanding_detected(
    self_understanding_consultation,
):
    detected = (
        self_understanding_consultation[
            "focus"
        ][
            "detected_categories"
        ]
    )

    assert "self_understanding" in detected


def test_self_understanding_does_not_force_relationships(
    self_understanding_consultation,
):
    relevant = (
        self_understanding_consultation[
            "focus"
        ][
            "relevant_sections"
        ]
    )

    assert "relationships" not in relevant


# ============================================================
# Chart integrity
# ============================================================


def test_consultation_does_not_mutate_reading_context(
    reading_context,
    career_consultation,
):
    before = deepcopy(
        reading_context
    )

    build_user_prompt(
        reading_context,
        consultation_context=(
            career_consultation
        ),
    )

    assert reading_context == before


def test_consultation_does_not_mutate_consultation_context(
    reading_context,
    career_consultation,
):
    before = deepcopy(
        career_consultation
    )

    build_user_prompt(
        reading_context,
        consultation_context=(
            career_consultation
        ),
    )

    assert career_consultation == before


def test_prompt_preserves_day_master(
    reading_context,
    career_consultation,
):
    text = build_user_prompt(
        reading_context,
        consultation_context=(
            career_consultation
        ),
    )

    assert '"stem": "乙"' in text


def test_prompt_preserves_pillars(
    reading_context,
    career_consultation,
):
    text = build_user_prompt(
        reading_context,
        consultation_context=(
            career_consultation
        ),
    )

    for ganzhi in (
        "庚午",
        "辛巳",
        "乙亥",
        "癸未",
    ):
        assert ganzhi in text


def test_prompt_preserves_strength(
    reading_context,
    career_consultation,
):
    text = build_user_prompt(
        reading_context,
        consultation_context=(
            career_consultation
        ),
    )

    assert '"label": "中和"' in text


def test_prompt_preserves_pattern(
    reading_context,
    career_consultation,
):
    text = build_user_prompt(
        reading_context,
        consultation_context=(
            career_consultation
        ),
    )

    assert (
        '"primary_pattern": "正官格"'
        in text
    )


def test_prompt_preserves_useful_gods(
    reading_context,
    career_consultation,
):
    text = build_user_prompt(
        reading_context,
        consultation_context=(
            career_consultation
        ),
    )

    assert (
        '"primary_useful_element": "水"'
        in text
    )


def test_prompt_preserves_current_luck(
    reading_context,
    career_consultation,
):
    text = build_user_prompt(
        reading_context,
        consultation_context=(
            career_consultation
        ),
    )

    assert "乙酉" in text


def test_prompt_preserves_annual_luck(
    reading_context,
    career_consultation,
):
    text = build_user_prompt(
        reading_context,
        consultation_context=(
            career_consultation
        ),
    )

    assert "丙午" in text


# ============================================================
# Wrong customer assumptions
# ============================================================


def test_wrong_customer_day_master_assumption_does_not_replace_chart(
    reading_context,
):
    consultation = build_consultation_context(
        concern=(
            "私は日主が甲だと思っています。"
            "甲として仕事運を見てください。"
        ),
        desired_future=(
            "自分に合う仕事を知りたいです。"
        ),
    )

    text = build_user_prompt(
        reading_context,
        consultation_context=consultation,
    )

    # 顧客発言として甲は存在してよい。
    assert "日主が甲" in text

    # しかし計算済みデータの日主は乙のまま。
    assert '"stem": "乙"' in text

    # AIには再判定禁止が渡される。
    assert "日主を再判定しない" in text


def test_wrong_customer_pattern_assumption_does_not_replace_chart(
    reading_context,
):
    consultation = build_consultation_context(
        concern=(
            "自分は偏財格だと思います。"
            "偏財格として金運を見てください。"
        ),
        desired_future=(
            "収入を増やしたいです。"
        ),
    )

    text = build_user_prompt(
        reading_context,
        consultation_context=consultation,
    )

    assert "偏財格" in text

    assert (
        '"primary_pattern": "正官格"'
        in text
    )

    assert "格局を再判定しない" in text


# ============================================================
# Section-only consultation
# ============================================================


@pytest.mark.parametrize(
    "section",
    EXPECTED_SECTIONS,
)
def test_each_section_accepts_consultation(
    reading_context,
    career_consultation,
    section,
):
    text = build_section_prompt(
        reading_context,
        section,
        consultation_context=(
            career_consultation
        ),
    )

    assert isinstance(text, str)
    assert text.strip()

    assert (
        "今の仕事を続けるか転職するか"
        in text
    )


def test_career_section_only_contains_career_title(
    reading_context,
    career_consultation,
):
    text = build_section_prompt(
        reading_context,
        "career",
        consultation_context=(
            career_consultation
        ),
    )

    assert "仕事・適職" in text


# ============================================================
# Messages
# ============================================================


def test_messages_have_system_and_user(
    reading_context,
    career_consultation,
):
    messages = build_messages(
        reading_context,
        consultation_context=(
            career_consultation
        ),
    )

    assert len(messages) == 2

    assert (
        messages[0]["role"]
        == "system"
    )

    assert (
        messages[1]["role"]
        == "user"
    )


def test_consultation_is_not_in_system_message(
    reading_context,
    career_consultation,
):
    messages = build_messages(
        reading_context,
        consultation_context=(
            career_consultation
        ),
    )

    assert (
        "今の仕事を続けるか転職するか"
        not in messages[0]["content"]
    )


def test_consultation_is_in_user_message(
    reading_context,
    career_consultation,
):
    messages = build_messages(
        reading_context,
        consultation_context=(
            career_consultation
        ),
    )

    assert (
        "今の仕事を続けるか転職するか"
        in messages[1]["content"]
    )


# ============================================================
# Request
# ============================================================


def test_reading_request_accepts_consultation(
    reading_context,
    career_consultation,
):
    request = build_reading_request(
        reading_context,
        consultation_context=(
            career_consultation
        ),
        output_format="json",
    )

    assert (
        request["version"]
        == "reading_prompt_v1"
    )

    assert (
        request["method"]
        == "reading_prompt_v1"
    )

    assert (
        request["status"]
        == "ready_for_ai_generation"
    )


def test_reading_request_keeps_all_sections(
    reading_context,
    career_consultation,
):
    request = build_reading_request(
        reading_context,
        consultation_context=(
            career_consultation
        ),
        output_format="json",
    )

    assert tuple(
        request["sections"]
    ) == EXPECTED_SECTIONS


def test_reading_request_json_schema_exists(
    reading_context,
    career_consultation,
):
    request = build_reading_request(
        reading_context,
        consultation_context=(
            career_consultation
        ),
        output_format="json",
    )

    assert isinstance(
        request["output_schema"],
        dict,
    )


def test_compact_request_accepts_consultation(
    reading_context,
    career_consultation,
):
    request = (
        build_compact_reading_request(
            reading_context,
            consultation_context=(
                career_consultation
            ),
            output_format="json",
        )
    )

    assert (
        request["version"]
        == "reading_prompt_v1"
    )

    assert (
        request["status"]
        == "ready_for_ai_generation"
    )


# ============================================================
# Audit
# ============================================================


def test_request_passes_prompt_audit(
    reading_context,
    career_consultation,
):
    request = build_reading_request(
        reading_context,
        consultation_context=(
            career_consultation
        ),
    )

    result = audit_prompt_request(
        request
    )

    assert result["valid"] is True
    assert (
        result["system_rule_check"]
        is True
    )
    assert (
        result["user_rule_check"]
        is True
    )


# ============================================================
# Legacy compatibility
# ============================================================


def test_none_consultation_still_builds_prompt(
    reading_context,
):
    text = build_user_prompt(
        reading_context,
        consultation_context=None,
    )

    assert isinstance(text, str)
    assert text.strip()


def test_none_consultation_has_no_consultation_block(
    reading_context,
):
    text = build_user_prompt(
        reading_context,
        consultation_context=None,
    )

    assert "【相談内容】" not in text


def test_none_consultation_messages_work(
    reading_context,
):
    messages = build_messages(
        reading_context,
        consultation_context=None,
    )

    assert len(messages) == 2


def test_none_consultation_request_work(
    reading_context,
):
    request = build_reading_request(
        reading_context,
        consultation_context=None,
    )

    assert (
        request["status"]
        == "ready_for_ai_generation"
    )


# ============================================================
# Consultation quality invariants
# ============================================================


@pytest.mark.parametrize(
    "forbidden_recalculation",
    (
        "日主を再判定しない",
        "身強身弱を再判定しない",
        "格局を再判定しない",
        "用神を再選定しない",
        "大運を再計算しない",
        "歳運を再計算しない",
        "通変星を再計算しない",
        "十二運を再計算しない",
    ),
)
def test_consultation_prompt_keeps_astrology_guardrails(
    reading_context,
    career_consultation,
    forbidden_recalculation,
):
    text = build_user_prompt(
        reading_context,
        consultation_context=(
            career_consultation
        ),
    )

    assert forbidden_recalculation in text


def test_consultation_prompt_requires_chart_priority(
    reading_context,
    career_consultation,
):
    text = build_user_prompt(
        reading_context,
        consultation_context=(
            career_consultation
        ),
    )

    assert (
        "命式の計算済み事実を最優先"
        in text
    )


def test_consultation_prompt_says_desire_is_not_evidence(
    reading_context,
    career_consultation,
):
    text = build_user_prompt(
        reading_context,
        consultation_context=(
            career_consultation
        ),
    )

    assert (
        "相談者の希望そのものを占術上の根拠にしない"
        in text
    )


def test_consultation_prompt_requires_connection_to_actual_problem(
    reading_context,
    career_consultation,
):
    text = build_user_prompt(
        reading_context,
        consultation_context=(
            career_consultation
        ),
    )

    assert (
        "一般論だけで終わらせず"
        in text
    )

    assert (
        "相談者の迷いに接続して説明"
        in text
    )


def test_consultation_prompt_requires_actionable_advice(
    reading_context,
    career_consultation,
):
    text = build_user_prompt(
        reading_context,
        consultation_context=(
            career_consultation
        ),
    )

    assert (
        "実行できる具体的な行動提案"
        in text
    )


# ============================================================
# Mutation safety
# ============================================================


def test_build_messages_does_not_mutate_inputs(
    reading_context,
    career_consultation,
):
    reading_before = deepcopy(
        reading_context
    )

    consultation_before = deepcopy(
        career_consultation
    )

    build_messages(
        reading_context,
        consultation_context=(
            career_consultation
        ),
    )

    assert (
        reading_context
        == reading_before
    )

    assert (
        career_consultation
        == consultation_before
    )


def test_build_request_does_not_mutate_inputs(
    reading_context,
    career_consultation,
):
    reading_before = deepcopy(
        reading_context
    )

    consultation_before = deepcopy(
        career_consultation
    )

    build_reading_request(
        reading_context,
        consultation_context=(
            career_consultation
        ),
        output_format="json",
    )

    assert (
        reading_context
        == reading_before
    )

    assert (
        career_consultation
        == consultation_before
    )


# ============================================================
# Final gate
# ============================================================


def test_reading_consultation_quality_v1_final_gate(
    reading_context,
    career_consultation,
):
    """
    consultation連動品質の最終ゲート。

    このテストが通ることで、

    - reading_context_v1
    - consultation_context_v1
    - reading_prompt_v1

    の3レイヤーが最低限の品質条件を
   満たして連携していることを確認する。
    """

    request = build_reading_request(
        reading_context,
        consultation_context=(
            career_consultation
        ),
        output_format="json",
    )

    audit = audit_prompt_request(
        request
    )

    assert (
        request["version"]
        == "reading_prompt_v1"
    )

    assert (
        request["method"]
        == "reading_prompt_v1"
    )

    assert (
        request["status"]
        == "ready_for_ai_generation"
    )

    assert tuple(
        request["sections"]
    ) == EXPECTED_SECTIONS

    assert (
        request["output_format"]
        == "json"
    )

    assert isinstance(
        request["output_schema"],
        dict,
    )

    assert (
        audit["valid"]
        is True
    )

    system_text = (
        request["messages"][0][
            "content"
        ]
    )

    user_text = (
        request["messages"][1][
            "content"
        ]
    )

    assert "再計算しない" in system_text
    assert "確定的" in system_text
    assert "医学的診断" in system_text

    assert (
        "今の仕事を続けるか転職するか"
        in user_text
    )

    assert (
        "命式の計算済み事実を最優先"
        in user_text
    )

    assert (
        "相談者が望む結論へ迎合しない"
        in user_text
    )

    assert (
        "日主を再判定しない"
        in user_text
    )

    assert (
        "格局を再判定しない"
        in user_text
    )

    assert (
        "用神を再選定しない"
        in user_text
    )

    assert (
        '"stem": "乙"'
        in user_text
    )

    assert (
        '"primary_pattern": "正官格"'
        in user_text
    )

    assert (
        '"primary_useful_element": "水"'
        in user_text
    )