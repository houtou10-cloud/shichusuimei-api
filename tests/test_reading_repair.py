"""
tests/test_reading_repair_five_year_luck.py

reading_repair の five_year_luck / future_flow.yearly 回帰テスト。

目的
----
5年運対応後のAI鑑定JSONをAuto-Repairへ渡したときに、

1. future_flow.yearly の5件構造を維持する
2. yearly 自体を削除できない
3. yearly の件数を増減できない
4. yearly 各要素の必須構造を変更できない
5. 文章だけの修正は許可する
6. five_year_luck を変更禁止の計算済み事実として保護する
7. Repair指示に5年運・yearly維持ルールを含める

ことを固定する。

注意
----
このテストは5年運を再計算しない。
reading_repair の責務は、既存の計算済み事実と
AI鑑定JSONの構造を壊さず文章品質だけを修復することである。
"""

from __future__ import annotations

from copy import deepcopy

import pytest

from engine.reading_repair import (
    ReadingRepairValidationError,
    build_protected_facts,
    build_repair_instructions,
    validate_same_json_structure,
)


# ============================================================
# Helpers
# ============================================================


def make_yearly():
    return [
        {
            "year": 2026,
            "title": "ここから年末まで",
            "summary": (
                "現在年の残り期間の流れです。"
            ),
            "detail": (
                "鑑定日時点から年末までの"
                "流れを説明します。"
            ),
            "advice": [
                "優先順位を整える。",
            ],
        },
        {
            "year": 2027,
            "title": "基盤を整える年",
            "summary": (
                "次の展開へ備える一年です。"
            ),
            "detail": (
                "足元を固めながら"
                "選択肢を広げます。"
            ),
            "advice": [
                "継続できる形を選ぶ。",
            ],
        },
        {
            "year": 2028,
            "title": "動きが強まる年",
            "summary": (
                "変化を活かしやすい一年です。"
            ),
            "detail": (
                "状況を見ながら"
                "行動範囲を広げます。"
            ),
            "advice": [
                "機会を見極めて動く。",
            ],
        },
        {
            "year": 2029,
            "title": "形にしていく年",
            "summary": (
                "積み重ねを成果へ"
                "つなげる一年です。"
            ),
            "detail": (
                "広げすぎず、"
                "重要なものを形にします。"
            ),
            "advice": [
                "成果を整理して残す。",
            ],
        },
        {
            "year": 2030,
            "title": "次の段階へ向かう年",
            "summary": (
                "5年間の経験を"
                "次へつなぐ一年です。"
            ),
            "detail": (
                "これまでを振り返り、"
                "次の方向を選びます。"
            ),
            "advice": [
                "次の長期目標を考える。",
            ],
        },
    ]


def make_five_year_ai_reading():
    return {
        "summary": (
            "現在から5年間の流れを"
            "年ごとに整理します。"
        ),
        "sections": {
            "future_flow": {
                "title": (
                    "これから5年間の運勢"
                ),
                "summary": (
                    "5年間全体の流れです。"
                ),
                "detail": (
                    "年ごとの違いを踏まえ、"
                    "長期的な流れを説明します。"
                ),
                "evidence": [
                    (
                        "各年の大運・歳運・"
                        "統合運を参照しています。"
                    ),
                ],
                "advice": [
                    (
                        "年ごとの流れに合わせて"
                        "行動を調整してください。"
                    ),
                ],
                "yearly": make_yearly(),
            },
        },
        "disclaimer": (
            "本鑑定は将来を確定的に"
            "予言するものではありません。"
        ),
    }


def make_five_year_reading_context():
    five_year_luck = [
        {
            "year": 2026,
            "target_datetime": (
                "2026-08-15T10:30:00"
            ),
            "current_luck": {
                "current_pillar": {
                    "ganzhi": "丁亥",
                },
            },
            "annual_luck": {
                "effective_year": 2026,
                "ganzhi": "丙午",
            },
            "integrated_luck": {
                "annual_luck_ganzhi": "丙午",
            },
        },
        {
            "year": 2027,
            "target_datetime": (
                "2027-07-01T12:00:00"
            ),
            "current_luck": {
                "current_pillar": {
                    "ganzhi": "丁亥",
                },
            },
            "annual_luck": {
                "effective_year": 2027,
                "ganzhi": "丁未",
            },
            "integrated_luck": {
                "annual_luck_ganzhi": "丁未",
            },
        },
        {
            "year": 2028,
            "target_datetime": (
                "2028-07-01T12:00:00"
            ),
            "current_luck": {
                "current_pillar": {
                    "ganzhi": "丁亥",
                },
            },
            "annual_luck": {
                "effective_year": 2028,
                "ganzhi": "戊申",
            },
            "integrated_luck": {
                "annual_luck_ganzhi": "戊申",
            },
        },
        {
            "year": 2029,
            "target_datetime": (
                "2029-07-01T12:00:00"
            ),
            "current_luck": {
                "current_pillar": {
                    "ganzhi": "丁亥",
                },
            },
            "annual_luck": {
                "effective_year": 2029,
                "ganzhi": "己酉",
            },
            "integrated_luck": {
                "annual_luck_ganzhi": "己酉",
            },
        },
        {
            "year": 2030,
            "target_datetime": (
                "2030-07-01T12:00:00"
            ),
            "current_luck": {
                "current_pillar": {
                    "ganzhi": "丁亥",
                },
            },
            "annual_luck": {
                "effective_year": 2030,
                "ganzhi": "庚戌",
            },
            "integrated_luck": {
                "annual_luck_ganzhi": "庚戌",
            },
        },
    ]

    return {
        "chart": {
            "year": {
                "stem": "乙",
                "branch": "丑",
            },
            "month": {
                "stem": "癸",
                "branch": "未",
            },
            "day": {
                "stem": "丁",
                "branch": "巳",
            },
            "hour": {
                "stem": "辛",
                "branch": "亥",
            },
        },
        "day_master": {
            "stem": "丁",
            "element": "火",
        },
        "final_strength_judgment": {
            "label": "中和",
            "final_score": 50.0,
        },
        "pattern_judgment": {
            "pattern": "食神格",
        },
        "useful_gods": {
            "primary": "金",
        },
        "luck_pillars": {
            "status": "calculated",
        },
        "current_luck": {
            "status": "available",
        },
        "annual_luck": {
            "status": "available",
        },
        "integrated_luck": {
            "status": "available",
        },
        # 現行 reading_context では luck 配下に存在するケースもあるため、
        # top-level と nested の両方を用意して保護抽出の互換性を確認する。
        "five_year_luck": deepcopy(
            five_year_luck
        ),
        "luck": {
            "five_year_luck": deepcopy(
                five_year_luck
            ),
        },
        "birth_time_status": {
            "known": True,
        },
    }


# ============================================================
# Structural protection
# ============================================================


def test_five_year_structure_accepts_text_only_changes():
    original = make_five_year_ai_reading()
    repaired = deepcopy(
        original
    )

    repaired[
        "sections"
    ][
        "future_flow"
    ][
        "summary"
    ] = (
        "5年間を通じて、"
        "段階的に流れが変化します。"
    )

    repaired[
        "sections"
    ][
        "future_flow"
    ][
        "yearly"
    ][0][
        "detail"
    ] = (
        "ここから年末までは、"
        "現在地を確認しながら進みます。"
    )

    validate_same_json_structure(
        original,
        repaired,
    )


def test_five_year_structure_rejects_missing_yearly():
    original = make_five_year_ai_reading()
    repaired = deepcopy(
        original
    )

    del repaired[
        "sections"
    ][
        "future_flow"
    ][
        "yearly"
    ]

    with pytest.raises(
        ReadingRepairValidationError
    ):
        validate_same_json_structure(
            original,
            repaired,
        )


def test_five_year_structure_rejects_six_years():
    original = make_five_year_ai_reading()
    repaired = deepcopy(
        original
    )

    extra = deepcopy(
        repaired[
            "sections"
        ][
            "future_flow"
        ][
            "yearly"
        ][-1]
    )
    extra["year"] = 2031

    repaired[
        "sections"
    ][
        "future_flow"
    ][
        "yearly"
    ].append(
        extra
    )

    with pytest.raises(
        ReadingRepairValidationError
    ):
        validate_same_json_structure(
            original,
            repaired,
        )


def test_five_year_structure_rejects_four_years():
    original = make_five_year_ai_reading()
    repaired = deepcopy(
        original
    )

    repaired[
        "sections"
    ][
        "future_flow"
    ][
        "yearly"
    ].pop()

    with pytest.raises(
        ReadingRepairValidationError
    ):
        validate_same_json_structure(
            original,
            repaired,
        )


def test_five_year_structure_rejects_missing_nested_key():
    original = make_five_year_ai_reading()
    repaired = deepcopy(
        original
    )

    del repaired[
        "sections"
    ][
        "future_flow"
    ][
        "yearly"
    ][2][
        "advice"
    ]

    with pytest.raises(
        ReadingRepairValidationError
    ):
        validate_same_json_structure(
            original,
            repaired,
        )


def test_five_year_structure_rejects_year_type_change():
    original = make_five_year_ai_reading()
    repaired = deepcopy(
        original
    )

    repaired[
        "sections"
    ][
        "future_flow"
    ][
        "yearly"
    ][0][
        "year"
    ] = "2026"

    with pytest.raises(
        ReadingRepairValidationError
    ):
        validate_same_json_structure(
            original,
            repaired,
        )


# ============================================================
# Protected facts
# ============================================================


def test_build_protected_facts_contains_five_year_luck():
    reading_context = (
        make_five_year_reading_context()
    )

    protected = build_protected_facts(
        reading_context
    )

    assert (
        "five_year_luck"
        in protected
    )

    assert [
        item["year"]
        for item in protected[
            "five_year_luck"
        ]
    ] == [
        2026,
        2027,
        2028,
        2029,
        2030,
    ]


def test_protected_five_year_luck_is_independent_copy():
    reading_context = (
        make_five_year_reading_context()
    )

    protected = build_protected_facts(
        reading_context
    )

    protected[
        "five_year_luck"
    ][0][
        "year"
    ] = 9999

    assert (
        reading_context[
            "five_year_luck"
        ][0][
            "year"
        ]
        == 2026
    )


# ============================================================
# Repair instructions
# ============================================================


@pytest.mark.parametrize(
    "required_text",
    (
        "five_year_luck",
        "yearly",
        "5年間",
    ),
)
def test_repair_instructions_contains_five_year_policy(
    required_text,
):
    instructions = (
        build_repair_instructions()
    )

    assert required_text in instructions


def test_repair_instructions_protects_yearly_structure():
    instructions = (
        build_repair_instructions()
    )

    assert (
        "5件"
        in instructions
        or "5年"
        in instructions
    )

    assert (
        "構造"
        in instructions
    )


# ============================================================
# Regression / immutability
# ============================================================


def test_validate_structure_does_not_mutate_original():
    original = make_five_year_ai_reading()
    repaired = deepcopy(
        original
    )

    before = deepcopy(
        original
    )

    validate_same_json_structure(
        original,
        repaired,
    )

    assert original == before


def test_protected_facts_does_not_mutate_reading_context():
    reading_context = (
        make_five_year_reading_context()
    )

    before = deepcopy(
        reading_context
    )

    build_protected_facts(
        reading_context
    )

    assert (
        reading_context
        == before
    )
