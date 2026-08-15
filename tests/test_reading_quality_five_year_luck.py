"""
tests/test_reading_quality_five_year_luck.py

reading_quality の
future_flow.yearly / five_year_luck 対応テスト。

目的
----
5年運対応後のAI鑑定JSONについて、

1. future_flow.yearly の5年分を顧客向け文章として収集する
2. yearly の title / summary / detail / advice を品質検査対象にする
3. yearly 内の内部キー漏洩を検出する
4. yearly 内の過度な断定表現を検出する
5. yearly 内の根拠のない具体的数値を検出する
6. yearly を future_flow という1セクションとして扱う
7. 既存のセクション品質検査を壊さない
8. 入力AI鑑定JSONを変更しない

ことを固定する。

注意
----
five_year_luck は計算済み事実であり、
reading_quality は5年運そのものを再計算しない。

このテストの責務は、
future_flow.yearly に生成された顧客向け文章を
既存の品質ゲートへ正しく流すことである。
"""

from __future__ import annotations

from copy import deepcopy

import pytest

from engine.reading_quality import (
    find_internal_key_leaks,
    find_overconfident_claims,
    find_unsupported_numeric_claims,
    iter_customer_facing_texts,
    validate_customer_facing_reading,
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
                "足元を整えながら、"
                "次の流れへ備える期間です。"
            ),
            "detail": (
                "現在地を確認し、"
                "優先順位を整理しながら"
                "進むことが大切です。"
            ),
            "advice": [
                (
                    "今年残りの期間は、"
                    "無理に広げすぎず"
                    "重要なことへ集中しましょう。"
                ),
            ],
        },
        {
            "year": 2027,
            "title": "基盤を整える年",
            "summary": (
                "今後につながる基盤を"
                "整えやすい一年です。"
            ),
            "detail": (
                "目先の結果だけでなく、"
                "継続できる形を作ることが"
                "重要になります。"
            ),
            "advice": [
                (
                    "長く続けられる方法を"
                    "選ぶことを意識しましょう。"
                ),
            ],
        },
        {
            "year": 2028,
            "title": "動きが強まる年",
            "summary": (
                "これまで整えてきたものを"
                "動かしやすい一年です。"
            ),
            "detail": (
                "状況を見極めながら、"
                "必要な場面では"
                "一歩前へ出ることが"
                "活かし方になります。"
            ),
            "advice": [
                (
                    "機会を選びながら、"
                    "行動範囲を広げてみましょう。"
                ),
            ],
        },
        {
            "year": 2029,
            "title": "形にしていく年",
            "summary": (
                "積み重ねてきたことを"
                "形へつなげやすい一年です。"
            ),
            "detail": (
                "広げることだけを考えず、"
                "重要なものを選んで"
                "完成度を高める視点が"
                "役立ちます。"
            ),
            "advice": [
                (
                    "成果として残したいものを"
                    "明確にしてみましょう。"
                ),
            ],
        },
        {
            "year": 2030,
            "title": "次の段階へ向かう年",
            "summary": (
                "5年間の経験を整理して、"
                "次の方向へつなげる一年です。"
            ),
            "detail": (
                "ここまでの流れを振り返り、"
                "残すものと変えるものを"
                "見極めることが重要です。"
            ),
            "advice": [
                (
                    "次の長期的な目標を"
                    "考えてみましょう。"
                ),
            ],
        },
    ]


def make_ai_reading():
    return {
        "summary": (
            "命式と現在の運勢を踏まえ、"
            "これからの方向性を整理します。"
        ),
        "sections": {
            "core_personality": {
                "title": "あなたの本質",
                "summary": (
                    "自分の感覚を大切にしながら"
                    "進む傾向があります。"
                ),
                "detail": (
                    "周囲に合わせるだけでなく、"
                    "自分なりの基準を持つことが"
                    "強みにつながります。"
                ),
                "evidence": [
                    (
                        "命式全体の構成から"
                        "読み取れる傾向です。"
                    ),
                ],
                "advice": [
                    (
                        "自分が納得できる基準を"
                        "大切にしてください。"
                    ),
                ],
            },
            "future_flow": {
                "title": "これから5年間の運勢",
                "summary": (
                    "5年間は一方向ではなく、"
                    "段階的に流れが変化します。"
                ),
                "detail": (
                    "足元を整える時期から、"
                    "動き、形にし、"
                    "次の段階へ向かう流れとして"
                    "見ることができます。"
                ),
                "evidence": [
                    (
                        "各年の大運と歳運を"
                        "組み合わせて見ています。"
                    ),
                ],
                "advice": [
                    (
                        "年ごとの違いを意識して、"
                        "行動の強弱を調整してください。"
                    ),
                ],
                "yearly": make_yearly(),
            },
        },
        "disclaimer": (
            "本鑑定は将来を断定または保証するものではありません。"
            "健康・医療に関する内容は医学的な診断ではありません。"
            "投資・金融・金銭に関する最終判断は、"
            "必要に応じて専門家へご相談ください。"
        ),
    }


def make_reading_context():
    five_year_luck = [
        {
            "year": 2026,
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
        "five_year_luck": deepcopy(
            five_year_luck
        ),
        "luck": {
            "five_year_luck": deepcopy(
                five_year_luck
            ),
        },
    }


# ============================================================
# 1. yearly text collection
# ============================================================


def test_iter_customer_facing_texts_collects_yearly():
    reading = make_ai_reading()

    texts = tuple(
        iter_customer_facing_texts(
            reading
        )
    )

    paths = {
        item.path
        for item in texts
    }

    assert (
        "sections.future_flow.yearly[0].title"
        in paths
    )

    assert (
        "sections.future_flow.yearly[0].summary"
        in paths
    )

    assert (
        "sections.future_flow.yearly[0].detail"
        in paths
    )

    assert (
        "sections.future_flow.yearly[0].advice[0]"
        in paths
    )


def test_iter_customer_facing_texts_collects_all_five_years():
    reading = make_ai_reading()

    texts = tuple(
        iter_customer_facing_texts(
            reading
        )
    )

    paths = {
        item.path
        for item in texts
    }

    for index in range(5):
        assert (
            f"sections.future_flow."
            f"yearly[{index}].title"
            in paths
        )

        assert (
            f"sections.future_flow."
            f"yearly[{index}].summary"
            in paths
        )

        assert (
            f"sections.future_flow."
            f"yearly[{index}].detail"
            in paths
        )

        assert (
            f"sections.future_flow."
            f"yearly[{index}].advice[0]"
            in paths
        )


def test_year_number_is_not_customer_facing_text():
    reading = make_ai_reading()

    texts = tuple(
        iter_customer_facing_texts(
            reading
        )
    )

    paths = {
        item.path
        for item in texts
    }

    for index in range(5):
        assert (
            f"sections.future_flow."
            f"yearly[{index}].year"
            not in paths
        )


# ============================================================
# 2. Path / kind contract
# ============================================================


def test_yearly_text_kinds_are_preserved():
    reading = make_ai_reading()

    texts = tuple(
        iter_customer_facing_texts(
            reading
        )
    )

    by_path = {
        item.path: item
        for item in texts
    }

    assert (
        by_path[
            "sections.future_flow."
            "yearly[0].title"
        ].kind
        == "title"
    )

    assert (
        by_path[
            "sections.future_flow."
            "yearly[0].summary"
        ].kind
        == "summary"
    )

    assert (
        by_path[
            "sections.future_flow."
            "yearly[0].detail"
        ].kind
        == "detail"
    )

    assert (
        by_path[
            "sections.future_flow."
            "yearly[0].advice[0]"
        ].kind
        == "advice"
    )


# ============================================================
# 3. Internal key leaks
# ============================================================


@pytest.mark.parametrize(
    "leaked_text",
    (
        (
            "five_year_luck を見ると"
            "流れが強まっています。"
        ),
        (
            "integrated_luck の結果では"
            "追い風があります。"
        ),
        (
            "current_luck を基準に"
            "判断しています。"
        ),
    ),
)
def test_internal_key_leak_inside_yearly_is_detected(
    leaked_text,
):
    reading = make_ai_reading()

    reading[
        "sections"
    ][
        "future_flow"
    ][
        "yearly"
    ][1][
        "detail"
    ] = leaked_text

    issues = find_internal_key_leaks(
        reading
    )

    assert issues

    assert any(
        issue.path
        == (
            "sections.future_flow."
            "yearly[1].detail"
        )
        for issue in issues
    )


# ============================================================
# 4. Overconfident claims
# ============================================================


@pytest.mark.parametrize(
    "claim",
    (
        "2028年は必ず成功します。",
        "この年は絶対に成功します。",
        "確実に達成できます。",
    ),
)
def test_overconfident_claim_inside_yearly_is_detected(
    claim,
):
    reading = make_ai_reading()

    reading[
        "sections"
    ][
        "future_flow"
    ][
        "yearly"
    ][2][
        "detail"
    ] = claim

    issues = find_overconfident_claims(
        reading
    )

    assert issues

    assert any(
        issue.path
        == (
            "sections.future_flow."
            "yearly[2].detail"
        )
        for issue in issues
    )


# ============================================================
# 5. Unsupported numeric claims
# ============================================================


def test_unsupported_numeric_advice_inside_yearly_is_detected():
    reading = make_ai_reading()
    context = make_reading_context()

    reading[
        "sections"
    ][
        "future_flow"
    ][
        "yearly"
    ][3][
        "advice"
    ] = [
        (
            "この年は新しい活動を"
            "17件始めてください。"
        ),
    ]

    issues = find_unsupported_numeric_claims(
        reading,
        reading_context=context,
    )

    assert issues

    assert any(
        issue.path
        == (
            "sections.future_flow."
            "yearly[3].advice[0]"
        )
        for issue in issues
    )


def test_grounded_year_number_does_not_fail_by_itself():
    reading = make_ai_reading()
    context = make_reading_context()

    reading[
        "sections"
    ][
        "future_flow"
    ][
        "yearly"
    ][1][
        "advice"
    ] = [
        (
            "2027年の流れを踏まえ、"
            "長期的な基盤を整えてください。"
        ),
    ]

    issues = find_unsupported_numeric_claims(
        reading,
        reading_context=context,
    )

    relevant = [
        issue
        for issue in issues
        if issue.path
        == (
            "sections.future_flow."
            "yearly[1].advice[0]"
        )
    ]

    assert relevant == []


# ============================================================
# 6. Full quality gate
# ============================================================


def test_valid_five_year_reading_passes_quality_gate():
    reading = make_ai_reading()
    context = make_reading_context()

    report = validate_customer_facing_reading(
        reading,
        reading_context=context,
    )

    assert report.valid is True


def test_invalid_yearly_text_fails_full_quality_gate():
    reading = make_ai_reading()
    context = make_reading_context()

    reading[
        "sections"
    ][
        "future_flow"
    ][
        "yearly"
    ][4][
        "detail"
    ] = (
        "five_year_luck の結果から、"
        "2030年は絶対に成功します。"
    )

    report = validate_customer_facing_reading(
        reading,
        reading_context=context,
    )

    assert report.valid is False

    assert any(
        issue.path
        == (
            "sections.future_flow."
            "yearly[4].detail"
        )
        for issue in report.issues
    )


# ============================================================
# 7. future_flow remains one section
# ============================================================


def test_yearly_paths_remain_under_future_flow_section():
    reading = make_ai_reading()

    texts = tuple(
        iter_customer_facing_texts(
            reading
        )
    )

    yearly_items = [
        item
        for item in texts
        if ".yearly[" in item.path
    ]

    assert yearly_items

    assert all(
        item.path.startswith(
            "sections.future_flow."
        )
        for item in yearly_items
    )


# ============================================================
# 8. Existing section behavior
# ============================================================


def test_existing_section_texts_are_still_collected():
    reading = make_ai_reading()

    texts = tuple(
        iter_customer_facing_texts(
            reading
        )
    )

    paths = {
        item.path
        for item in texts
    }

    assert (
        "sections.core_personality.title"
        in paths
    )

    assert (
        "sections.core_personality.summary"
        in paths
    )

    assert (
        "sections.core_personality.detail"
        in paths
    )

    assert (
        "sections.core_personality.evidence[0]"
        in paths
    )

    assert (
        "sections.core_personality.advice[0]"
        in paths
    )


# ============================================================
# 9. Immutability
# ============================================================


def test_iter_customer_facing_texts_does_not_mutate_input():
    reading = make_ai_reading()
    before = deepcopy(
        reading
    )

    tuple(
        iter_customer_facing_texts(
            reading
        )
    )

    assert reading == before


def test_quality_validation_does_not_mutate_input():
    reading = make_ai_reading()
    context = make_reading_context()

    reading_before = deepcopy(
        reading
    )
    context_before = deepcopy(
        context
    )

    validate_customer_facing_reading(
        reading,
        reading_context=context,
    )

    assert reading == reading_before
    assert context == context_before
