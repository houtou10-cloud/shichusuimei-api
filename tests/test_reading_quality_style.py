"""
tests/test_reading_quality_style.py

販売版 v1 に向けた
「AIっぽい定型表現」Qualityテスト。

目的
----
内容そのものが正しくても、

- 「〜と示されています」
- 「〜と読みます」
- 「〜が鍵です」
- 「〜ことが重要です」
- 「〜と考えられます」

のような同じ定型表現が鑑定書全体で
何度も続くと、文章が機械的に見えやすい。

本テストでは、意味内容ではなく
「同じ説明の型の使い回し」をwarningとして検出する。

確認項目
--------
1. 同じAI的定型句を多数章で繰り返した場合に検出する
2. 「示されています」「と読みます」等を個別に検出する
3. 同じ結論フレーズ「〜が鍵です」の使い回しを検出する
4. 同じ説明語尾が過剰に連続する場合に検出する
5. future_flow.yearly も文体検査対象にする
6. 5年運で各年の文章が自然に変化していれば誤検出しない
7. 「〜してください」「〜しましょう」など一般的な丁寧語だけでは警告しない
8. 四柱推命上必要な「傾向です」「流れです」の自然な共有は許容する
9. 2章程度の同じ定型句は許容する
10. style問題はwarningであり、それ単独では品質ゲートをfailさせない
11. 入力AI鑑定JSONを書き換えない

重要
----
このQuality層は文章を書き換えない。
命式・大運・歳運等も再計算しない。
問題をQualityIssueとして報告するだけである。
"""

from __future__ import annotations

from copy import deepcopy

from engine.reading_quality import (
    issue_severity,
    validate_customer_facing_reading,
)


# ============================================================
# Expected issue codes
# ============================================================


FORMULAIC_PHRASE_OVERUSE = (
    "formulaic_phrase_overuse"
)

SENTENCE_ENDING_OVERUSE = (
    "sentence_ending_overuse"
)

FUTURE_FLOW_STYLE_REPETITION = (
    "future_flow_style_repetition"
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
                "大きく動くより、"
                "条件を整える時間です。"
            ),
            "detail": (
                "契約や役割を確認し、"
                "次の選択へ備えることで"
                "不確実性を抑えやすくなります。"
            ),
            "advice": [
                (
                    "結論を急がず、"
                    "小さく試してから"
                    "判断してください。"
                ),
            ],
        },
        {
            "year": 2027,
            "title": "基盤を作る年",
            "summary": (
                "新しい環境の土台を"
                "整えやすい一年です。"
            ),
            "detail": (
                "役割分担や評価基準を"
                "明確にしておくと、"
                "翌年以降に動きやすくなります。"
            ),
            "advice": [
                (
                    "仕組みを先に作り、"
                    "無理なく続けられる形へ"
                    "整えてください。"
                ),
            ],
        },
        {
            "year": 2028,
            "title": "評価が広がる年",
            "summary": (
                "積み上げた成果が"
                "外へ伝わりやすくなります。"
            ),
            "detail": (
                "実績を見える形にまとめ、"
                "役割や報酬の交渉へ"
                "つなげる余地が生まれます。"
            ),
            "advice": [
                (
                    "成果を整理して、"
                    "相手に伝わる形で"
                    "提示しましょう。"
                ),
            ],
        },
        {
            "year": 2029,
            "title": "専門性を深める年",
            "summary": (
                "広げるより、"
                "得意分野を明確にすることで"
                "価値が伝わりやすくなります。"
            ),
            "detail": (
                "前年までの評価を土台に、"
                "自分の看板となる領域を"
                "育てていく時期です。"
            ),
            "advice": [
                (
                    "強みを一つ選び、"
                    "事例や実績を"
                    "体系化しましょう。"
                ),
            ],
        },
        {
            "year": 2030,
            "title": "選択と集中の年",
            "summary": (
                "広げた仕事を整理し、"
                "残すものを選ぶ段階です。"
            ),
            "detail": (
                "収益性や負荷を比べながら、"
                "長く育てたい領域へ"
                "力を集中させるとよいでしょう。"
            ),
            "advice": [
                (
                    "量を追いすぎず、"
                    "長期的に価値が残る仕事を"
                    "優先してください。"
                ),
            ],
        },
    ]


def make_reading():
    return {
        "summary": (
            "命式と現在の流れを踏まえ、"
            "仕事・金運・今後の方向性を"
            "実践的に整理します。"
        ),
        "sections": {
            "core_personality": {
                "title": "本質・性格",
                "summary": (
                    "責任感があり、"
                    "着実に積み上げる力を"
                    "持っています。"
                ),
                "detail": (
                    "自分で考えて動ける一方、"
                    "抱え込みすぎると"
                    "判断が重くなりやすいため、"
                    "適度に周囲へ頼る余白も"
                    "大切になります。"
                ),
                "evidence": [
                    (
                        "日主と命式全体の構成から、"
                        "粘り強さと自己完結力の"
                        "両方が見て取れます。"
                    ),
                ],
                "advice": [
                    (
                        "重要な仕事ほど、"
                        "一人で抱えず"
                        "役割を分けてください。"
                    ),
                ],
            },
            "career": {
                "title": "仕事・適職",
                "summary": (
                    "責任ある役割や、"
                    "改善を求められる環境で"
                    "持ち味を活かしやすいタイプです。"
                ),
                "detail": (
                    "仕事内容だけでなく、"
                    "裁量や評価基準まで比較すると、"
                    "転職先との相性を"
                    "判断しやすくなります。"
                ),
                "evidence": [
                    (
                        "格局と用神の組み合わせを、"
                        "仕事での役割や"
                        "環境選びに置き換えています。"
                    ),
                ],
                "advice": [
                    (
                        "候補先は、"
                        "仕事内容・裁量・評価制度の"
                        "三つに分けて比較してください。"
                    ),
                ],
            },
            "wealth": {
                "title": "金運",
                "summary": (
                    "収入額だけでなく、"
                    "安定性とのバランスを"
                    "考えることが大切です。"
                ),
                "detail": (
                    "最低限必要な収入を守りながら、"
                    "成果に応じた上振れ余地を"
                    "別枠で考えると"
                    "現実的な設計になります。"
                ),
                "evidence": [
                    (
                        "用神と現在の運勢を、"
                        "収入の安定性と"
                        "伸びしろの両面から見ています。"
                    ),
                ],
                "advice": [
                    (
                        "固定収入と変動収入を"
                        "分けて考え、"
                        "下振れ幅を確認してください。"
                    ),
                ],
            },
            "relationships": {
                "title": "恋愛・人間関係",
                "summary": (
                    "相手を支える力がありますが、"
                    "自分の基準を"
                    "強く求めすぎないことも大切です。"
                ),
                "detail": (
                    "役割や期待を先に共有すると、"
                    "無用な抱え込みや"
                    "すれ違いを減らしやすくなります。"
                ),
                "evidence": [
                    (
                        "命式に見られる責任感を、"
                        "対人関係での距離感として"
                        "解釈しています。"
                    ),
                ],
                "advice": [
                    (
                        "相手のやり方にも余白を残し、"
                        "期待を言葉で"
                        "共有してみてください。"
                    ),
                ],
            },
            "health": {
                "title": "健康傾向",
                "summary": (
                    "無理を続けるより、"
                    "生活全体のリズムを"
                    "整える意識が役立ちます。"
                ),
                "detail": (
                    "四柱推命は医学的診断ではありません。"
                    "忙しい時ほど休息と活動の"
                    "切り替えを意識する程度の"
                    "一般的な参考にとどめてください。"
                ),
                "evidence": [
                    (
                        "五行の偏りは、"
                        "生活バランスを見直す"
                        "参考情報として扱っています。"
                    ),
                ],
                "advice": [
                    (
                        "具体的な不調がある場合は、"
                        "自己判断せず"
                        "医療専門家へ相談してください。"
                    ),
                ],
            },
            "current_luck": {
                "title": "現在の運勢",
                "summary": (
                    "今は拡大より、"
                    "準備と条件整理を"
                    "優先しやすい時期です。"
                ),
                "detail": (
                    "すぐに一択へ絞るより、"
                    "選択肢を残しながら"
                    "比較する方が"
                    "現在の流れに合っています。"
                ),
                "evidence": [
                    (
                        "現在大運と歳運を組み合わせ、"
                        "攻めと守りのバランスを"
                        "確認しています。"
                    ),
                ],
                "advice": [
                    (
                        "契約条件や撤退基準を"
                        "先に確認してから"
                        "動いてください。"
                    ),
                ],
            },
            "future_flow": {
                "title": "これから5年間の運勢",
                "summary": (
                    "準備から基盤づくり、"
                    "評価拡大、専門性の深化、"
                    "選択と集中へ進む流れです。"
                ),
                "detail": (
                    "最初から一気に広げるのではなく、"
                    "段階を踏んで土台を作ることで、"
                    "後半の追い風を"
                    "活かしやすくなります。"
                ),
                "evidence": [
                    (
                        "5年分の大運と歳運を"
                        "年ごとに比較して"
                        "全体の変化を整理しています。"
                    ),
                ],
                "advice": [
                    (
                        "年ごとの違いに合わせて、"
                        "行動量を"
                        "調整してください。"
                    ),
                ],
                "yearly": make_yearly(),
            },
            "advice": {
                "title": "総合アドバイス",
                "summary": (
                    "一択に決めるより、"
                    "複数案を比較しながら"
                    "段階的に進める方法が合います。"
                ),
                "detail": (
                    "仕事・収入・時期を"
                    "別々に確認すると、"
                    "漠然とした不安を"
                    "具体的な判断材料へ変えられます。"
                ),
                "evidence": [
                    (
                        "命式・現在運・5年運を"
                        "相談内容に沿って"
                        "総合しています。"
                    ),
                ],
                "advice": [
                    (
                        "候補を複数残したまま、"
                        "条件を比較して"
                        "最終判断してください。"
                    ),
                ],
            },
        },
        "disclaimer": (
            "本鑑定は将来を断定または"
            "保証するものではありません。"
            "健康・医療に関する内容は"
            "医学的な診断ではありません。"
            "投資・金融・金銭に関する"
            "最終判断は、必要に応じて"
            "専門家へご相談ください。"
        ),
    }


def validate(
    reading,
):
    return validate_customer_facing_reading(
        reading
    )


def codes(
    report,
):
    return {
        issue.code
        for issue in report.issues
    }


# ============================================================
# 1. Baseline
# ============================================================


def test_natural_reading_has_no_style_warning():
    reading = make_reading()

    report = validate(
        reading
    )

    assert (
        FORMULAIC_PHRASE_OVERUSE
        not in codes(report)
    )

    assert (
        SENTENCE_ENDING_OVERUSE
        not in codes(report)
    )

    assert (
        FUTURE_FLOW_STYLE_REPETITION
        not in codes(report)
    )


# ============================================================
# 2. Formulaic phrases
# ============================================================


def test_detects_shimesareteimasu_overuse():
    reading = make_reading()

    for section_name in (
        "core_personality",
        "career",
        "wealth",
        "relationships",
    ):
        reading[
            "sections"
        ][
            section_name
        ][
            "evidence"
        ] = [
            (
                "この傾向が命式に"
                "示されています。"
            ),
        ]

    report = validate(
        reading
    )

    assert (
        FORMULAIC_PHRASE_OVERUSE
        in codes(report)
    )


def test_detects_to_yomimasu_overuse():
    reading = make_reading()

    for section_name in (
        "career",
        "wealth",
        "current_luck",
        "advice",
    ):
        reading[
            "sections"
        ][
            section_name
        ][
            "detail"
        ] = (
            f"{section_name}について、"
            "慎重に進める時期と読みます。"
        )

    report = validate(
        reading
    )

    assert (
        FORMULAIC_PHRASE_OVERUSE
        in codes(report)
    )


def test_detects_kagi_desu_overuse():
    reading = make_reading()

    for section_name in (
        "career",
        "wealth",
        "current_luck",
        "advice",
    ):
        reading[
            "sections"
        ][
            section_name
        ][
            "detail"
        ] = (
            f"{section_name}では、"
            "条件を整えることが鍵です。"
        )

    report = validate(
        reading
    )

    assert (
        FORMULAIC_PHRASE_OVERUSE
        in codes(report)
    )


def test_detects_koto_ga_juyo_overuse():
    reading = make_reading()

    for section_name in (
        "core_personality",
        "career",
        "wealth",
        "relationships",
    ):
        reading[
            "sections"
        ][
            section_name
        ][
            "summary"
        ] = (
            f"{section_name}では、"
            "バランスを取ることが重要です。"
        )

    report = validate(
        reading
    )

    assert (
        FORMULAIC_PHRASE_OVERUSE
        in codes(report)
    )


def test_detects_to_kangaeraremasu_overuse():
    reading = make_reading()

    for section_name in (
        "career",
        "wealth",
        "current_luck",
        "future_flow",
    ):
        reading[
            "sections"
        ][
            section_name
        ][
            "evidence"
        ] = [
            (
                f"{section_name}では、"
                "この要素が影響すると"
                "考えられます。"
            ),
        ]

    report = validate(
        reading
    )

    assert (
        FORMULAIC_PHRASE_OVERUSE
        in codes(report)
    )


# ============================================================
# 3. Tolerance
# ============================================================


def test_same_formulaic_phrase_in_two_sections_is_tolerated():
    reading = make_reading()

    for section_name in (
        "career",
        "wealth",
    ):
        reading[
            "sections"
        ][
            section_name
        ][
            "detail"
        ] = (
            f"{section_name}では、"
            "条件を整えることが鍵です。"
        )

    report = validate(
        reading
    )

    assert (
        FORMULAIC_PHRASE_OVERUSE
        not in codes(report)
    )


def test_polite_kudasai_endings_alone_are_not_formulaic_warning():
    reading = make_reading()

    for section_name in (
        "core_personality",
        "career",
        "wealth",
        "relationships",
        "current_luck",
        "advice",
    ):
        reading[
            "sections"
        ][
            section_name
        ][
            "advice"
        ] = [
            (
                f"{section_name}の状況に合わせて"
                "判断してください。"
            ),
        ]

    report = validate(
        reading
    )

    assert (
        FORMULAIC_PHRASE_OVERUSE
        not in codes(report)
    )


def test_shimashou_endings_alone_are_not_formulaic_warning():
    reading = make_reading()

    for section_name in (
        "core_personality",
        "career",
        "wealth",
        "relationships",
    ):
        reading[
            "sections"
        ][
            section_name
        ][
            "advice"
        ] = [
            (
                f"{section_name}では"
                "無理のない方法を選びましょう。"
            ),
        ]

    report = validate(
        reading
    )

    assert (
        FORMULAIC_PHRASE_OVERUSE
        not in codes(report)
    )


# ============================================================
# 4. Sentence-ending overuse
# ============================================================


def test_detects_same_explanatory_ending_across_many_sections():
    reading = make_reading()

    endings = {
        "core_personality": (
            "自分の基準を持つことが"
            "持ち味だといえます。"
        ),
        "career": (
            "責任ある仕事に向くと"
            "いえます。"
        ),
        "wealth": (
            "安定性を重視する方が"
            "よいといえます。"
        ),
        "relationships": (
            "役割共有が助けになると"
            "いえます。"
        ),
        "current_luck": (
            "準備を優先する時期だと"
            "いえます。"
        ),
    }

    for section_name, value in (
        endings.items()
    ):
        reading[
            "sections"
        ][
            section_name
        ][
            "detail"
        ] = value

    report = validate(
        reading
    )

    assert (
        SENTENCE_ENDING_OVERUSE
        in codes(report)
    )


def test_detects_desho_overuse_across_many_sections():
    reading = make_reading()

    for section_name in (
        "core_personality",
        "career",
        "wealth",
        "relationships",
        "health",
        "current_luck",
        "advice",
    ):
        reading[
            "sections"
        ][
            section_name
        ][
            "summary"
        ] = (
            f"{section_name}では、"
            "落ち着いた判断が"
            "役立つでしょう。"
        )

    report = validate(
        reading
    )

    assert (
        SENTENCE_ENDING_OVERUSE
        in codes(report)
    )


def test_desho_in_six_sections_is_tolerated():
    reading = make_reading()

    for section_name in (
        "career",
        "wealth",
        "relationships",
        "health",
        "future_flow",
        "advice",
    ):
        reading[
            "sections"
        ][
            section_name
        ][
            "summary"
        ] = (
            f"{section_name}では、"
            "状況を確認すると"
            "よいでしょう。"
        )

    report = validate(
        reading
    )

    assert (
        SENTENCE_ENDING_OVERUSE
        not in codes(report)
    )


def test_natural_mixed_sentence_endings_do_not_trigger():
    reading = make_reading()

    reading[
        "sections"
    ][
        "career"
    ][
        "detail"
    ] = (
        "裁量のある仕事と"
        "相性があります。"
    )

    reading[
        "sections"
    ][
        "wealth"
    ][
        "detail"
    ] = (
        "収入条件を"
        "比較するとよいでしょう。"
    )

    reading[
        "sections"
    ][
        "current_luck"
    ][
        "detail"
    ] = (
        "今は準備を優先する"
        "時期と見ています。"
    )

    reading[
        "sections"
    ][
        "advice"
    ][
        "detail"
    ] = (
        "複数の選択肢を"
        "残しておく方法が合います。"
    )

    report = validate(
        reading
    )

    assert (
        SENTENCE_ENDING_OVERUSE
        not in codes(report)
    )


# ============================================================
# 5. future_flow.yearly style
# ============================================================


def test_detects_same_formulaic_phrase_in_many_years():
    reading = make_reading()

    for index in (
        0,
        1,
        2,
        3,
    ):
        year = reading[
            "sections"
        ][
            "future_flow"
        ][
            "yearly"
        ][index][
            "year"
        ]

        reading[
            "sections"
        ][
            "future_flow"
        ][
            "yearly"
        ][index][
            "detail"
        ] = (
            f"{year}年は、"
            "条件を整えることが鍵です。"
        )

    report = validate(
        reading
    )

    assert (
        FUTURE_FLOW_STYLE_REPETITION
        in codes(report)
    )


def test_detects_same_yearly_sentence_ending_pattern():
    reading = make_reading()

    for index in (
        0,
        1,
        2,
        3,
    ):
        year = reading[
            "sections"
        ][
            "future_flow"
        ][
            "yearly"
        ][index][
            "year"
        ]

        reading[
            "sections"
        ][
            "future_flow"
        ][
            "yearly"
        ][index][
            "summary"
        ] = (
            f"{year}年は"
            "準備が役立つでしょう。"
        )

    report = validate(
        reading
    )

    assert (
        FUTURE_FLOW_STYLE_REPETITION
        in codes(report)
    )


def test_yearly_natural_variation_does_not_trigger_style_warning():
    reading = make_reading()

    report = validate(
        reading
    )

    assert (
        FUTURE_FLOW_STYLE_REPETITION
        not in codes(report)
    )


def test_two_years_may_share_same_style_without_warning():
    reading = make_reading()

    for index in (
        0,
        1,
    ):
        reading[
            "sections"
        ][
            "future_flow"
        ][
            "yearly"
        ][index][
            "detail"
        ] = (
            "条件を整えることが鍵です。"
        )

    report = validate(
        reading
    )

    assert (
        FUTURE_FLOW_STYLE_REPETITION
        not in codes(report)
    )


def test_yearly_polite_advice_endings_are_not_style_problem():
    reading = make_reading()

    for index, item in enumerate(
        reading[
            "sections"
        ][
            "future_flow"
        ][
            "yearly"
        ]
    ):
        item[
            "advice"
        ] = [
            (
                f"{index + 1}段階目として、"
                "状況を確認してください。"
            ),
        ]

    report = validate(
        reading
    )

    assert (
        FUTURE_FLOW_STYLE_REPETITION
        not in codes(report)
    )


# ============================================================
# 6. Required domain language tolerance
# ============================================================


def test_tendency_word_across_sections_is_not_style_warning():
    reading = make_reading()

    for section_name in (
        "core_personality",
        "career",
        "wealth",
        "relationships",
    ):
        reading[
            "sections"
        ][
            section_name
        ][
            "summary"
        ] = (
            f"{section_name}には"
            "このような傾向があります。"
        )

    report = validate(
        reading
    )

    assert (
        FORMULAIC_PHRASE_OVERUSE
        not in codes(report)
    )


def test_flow_word_across_luck_sections_is_not_style_warning():
    reading = make_reading()

    reading[
        "sections"
    ][
        "current_luck"
    ][
        "summary"
    ] = (
        "準備を優先しやすい流れです。"
    )

    reading[
        "sections"
    ][
        "future_flow"
    ][
        "summary"
    ] = (
        "段階的に広がっていく流れです。"
    )

    report = validate(
        reading
    )

    assert (
        FORMULAIC_PHRASE_OVERUSE
        not in codes(report)
    )


# ============================================================
# 7. Severity / gate contract
# ============================================================


def test_formulaic_phrase_issue_is_warning():
    reading = make_reading()

    for section_name in (
        "core_personality",
        "career",
        "wealth",
        "relationships",
    ):
        reading[
            "sections"
        ][
            section_name
        ][
            "evidence"
        ] = [
            (
                "この特徴が命式に"
                "示されています。"
            ),
        ]

    report = validate(
        reading
    )

    issue = next(
        issue
        for issue in report.issues
        if issue.code
        == FORMULAIC_PHRASE_OVERUSE
    )

    assert (
        issue_severity(
            issue
        )
        == "warning"
    )


def test_style_warning_alone_does_not_fail_quality_gate():
    reading = make_reading()

    for section_name in (
        "core_personality",
        "career",
        "wealth",
        "relationships",
    ):
        reading[
            "sections"
        ][
            section_name
        ][
            "evidence"
        ] = [
            (
                "この特徴が命式に"
                "示されています。"
            ),
        ]

    report = validate(
        reading
    )

    assert (
        FORMULAIC_PHRASE_OVERUSE
        in codes(report)
    )

    assert (
        report.valid
        is True
    )


# ============================================================
# 8. Issue paths
# ============================================================


def test_formulaic_phrase_issue_points_to_sections():
    reading = make_reading()

    for section_name in (
        "career",
        "wealth",
        "current_luck",
        "advice",
    ):
        reading[
            "sections"
        ][
            section_name
        ][
            "detail"
        ] = (
            f"{section_name}では、"
            "条件整理が鍵です。"
        )

    report = validate(
        reading
    )

    issue = next(
        issue
        for issue in report.issues
        if issue.code
        == FORMULAIC_PHRASE_OVERUSE
    )

    assert (
        issue.path
        == "sections"
    )


def test_future_flow_style_issue_points_to_future_flow():
    reading = make_reading()

    for index in (
        0,
        1,
        2,
        3,
    ):
        reading[
            "sections"
        ][
            "future_flow"
        ][
            "yearly"
        ][index][
            "detail"
        ] = (
            "条件を整えることが鍵です。"
        )

    report = validate(
        reading
    )

    issue = next(
        issue
        for issue in report.issues
        if issue.code
        == FUTURE_FLOW_STYLE_REPETITION
    )

    assert (
        issue.path
        == "sections.future_flow"
    )


# ============================================================
# 9. Immutability
# ============================================================


def test_style_validation_does_not_mutate_reading():
    reading = make_reading()

    before = deepcopy(
        reading
    )

    validate(
        reading
    )

    assert (
        reading
        == before
    )


def test_style_validation_does_not_rewrite_formulaic_text():
    reading = make_reading()

    repeated = (
        "条件を整えることが鍵です。"
    )

    for section_name in (
        "career",
        "wealth",
        "current_luck",
        "advice",
    ):
        reading[
            "sections"
        ][
            section_name
        ][
            "detail"
        ] = repeated

    validate(
        reading
    )

    for section_name in (
        "career",
        "wealth",
        "current_luck",
        "advice",
    ):
        assert (
            reading[
                "sections"
            ][
                section_name
            ][
                "detail"
            ]
            == repeated
        )
