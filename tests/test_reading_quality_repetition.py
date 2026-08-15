"""
tests/test_reading_quality_repetition.py

販売版 v1 に向けた文章重複Qualityテスト。

目的
----
AI鑑定書で起こりやすい「同じ意味の繰り返し」を、
顧客向けPDFへ出す前に検出できるようにする。

主な対象
--------
1. 同一セクションの summary と detail の過度な重複
2. 同一セクション内での同一文・同一フレーズ反復
3. 複数セクションをまたぐ定型フレーズの使い回し
4. 複数セクションをまたぐ同じ助言の使い回し
5. future_flow の5年総括と yearly の過度な重複
6. yearly 各年どうしの文章使い回し
7. 自然なキーワード共有は誤検出しない
8. 重複問題は原則 warning とし、単独ではPDF生成を止めない
9. 入力データを変更しない

設計方針
--------
この品質ゲートは文章を書き換えない。
問題を検出し、QualityIssue として報告するだけとする。

また、四柱推命の計算結果そのものは変更・再計算しない。
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


SUMMARY_DETAIL_REPETITION = (
    "summary_detail_repetition"
)

WITHIN_SECTION_REPETITION = (
    "within_section_text_repetition"
)

CROSS_SECTION_PHRASE_REPETITION = (
    "cross_section_phrase_repetition"
)

FUTURE_FLOW_REPETITION = (
    "future_flow_yearly_repetition"
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
                "条件を整えながら、"
                "次の流れへ備える期間です。"
            ),
            "detail": (
                "大きく広げるより、"
                "契約や役割を確認し、"
                "今後につながる準備を"
                "進めることが大切です。"
            ),
            "advice": [
                (
                    "判断を一度に決めず、"
                    "段階的に進めましょう。"
                ),
            ],
        },
        {
            "year": 2027,
            "title": "基盤を整える年",
            "summary": (
                "新しい環境の仕組みを"
                "整えやすい一年です。"
            ),
            "detail": (
                "評価基準や役割分担を"
                "明確にすることで、"
                "翌年以降の伸びにつながります。"
            ),
            "advice": [
                (
                    "続けられる仕組みを"
                    "先に作ってください。"
                ),
            ],
        },
        {
            "year": 2028,
            "title": "評価が広がる年",
            "summary": (
                "外部からの評価を"
                "得やすい流れです。"
            ),
            "detail": (
                "これまでの成果を見える形にし、"
                "役割や報酬の交渉へ"
                "つなげると活かしやすい時期です。"
            ),
            "advice": [
                (
                    "実績を整理して、"
                    "評価につながる形で示しましょう。"
                ),
            ],
        },
        {
            "year": 2029,
            "title": "専門性を深める年",
            "summary": (
                "得意分野を絞ることで"
                "強みが伝わりやすくなります。"
            ),
            "detail": (
                "前年に得た評価を土台に、"
                "専門領域を明確にして"
                "価値を深めることが重要です。"
            ),
            "advice": [
                (
                    "看板となる分野を決め、"
                    "実績を体系化しましょう。"
                ),
            ],
        },
        {
            "year": 2030,
            "title": "選択と集中の年",
            "summary": (
                "広げたものを整理し、"
                "重要な領域へ集中する一年です。"
            ),
            "detail": (
                "仕事量だけを増やさず、"
                "収益性や負荷を比較しながら"
                "残す領域を選ぶことが鍵です。"
            ),
            "advice": [
                (
                    "長期的に残したい仕事へ"
                    "資源を集中してください。"
                ),
            ],
        },
    ]


def make_reading():
    return {
        "summary": (
            "命式と現在の流れを踏まえ、"
            "仕事・金運・今後5年間を"
            "実践的に整理します。"
        ),
        "sections": {
            "core_personality": {
                "title": "本質・性格",
                "summary": (
                    "責任感が強く、"
                    "物事を着実に進めるタイプです。"
                ),
                "detail": (
                    "自分で考えて動く力があります。"
                    "一方で、抱え込みすぎると"
                    "判断が重くなりやすいため、"
                    "周囲との役割分担が役立ちます。"
                ),
                "evidence": [
                    (
                        "命式全体の構成から"
                        "読み取れる傾向です。"
                    ),
                ],
                "advice": [
                    (
                        "自分だけで完結させず、"
                        "必要な場面では周囲へ"
                        "役割を渡してください。"
                    ),
                ],
            },
            "career": {
                "title": "仕事・適職",
                "summary": (
                    "変化への対応力を活かし、"
                    "責任ある役割で"
                    "力を発揮しやすい傾向です。"
                ),
                "detail": (
                    "仕組みを整えながら"
                    "成果を出す仕事と相性があります。"
                    "転職では仕事内容だけでなく、"
                    "裁量や評価基準も比較すると"
                    "判断しやすくなります。"
                ),
                "evidence": [
                    (
                        "格局と用神の組み合わせから"
                        "仕事上の活かし方を見ています。"
                    ),
                ],
                "advice": [
                    (
                        "仕事内容・裁量・評価基準を"
                        "分けて比較してください。"
                    ),
                ],
            },
            "wealth": {
                "title": "金運",
                "summary": (
                    "収入の大きさだけでなく、"
                    "安定性とのバランスが"
                    "重要になります。"
                ),
                "detail": (
                    "条件の透明性が高いほど、"
                    "安心して力を発揮しやすくなります。"
                    "固定収入と上振れ余地を分けて"
                    "検討すると現実的です。"
                ),
                "evidence": [
                    (
                        "用神と現在の運勢を"
                        "収入設計へ置き換えて見ています。"
                    ),
                ],
                "advice": [
                    (
                        "最低限必要な収入と、"
                        "上振れを狙う部分を"
                        "分けて考えてください。"
                    ),
                ],
            },
            "future_flow": {
                "title": "これから5年間の運勢",
                "summary": (
                    "5年間は、準備から基盤整備、"
                    "評価拡大、専門性の深化、"
                    "選択と集中へ進む流れです。"
                ),
                "detail": (
                    "最初から一気に広げるより、"
                    "段階を踏んで土台を整え、"
                    "その後に評価と専門性を"
                    "伸ばしていく流れとして"
                    "捉えると活かしやすくなります。"
                ),
                "evidence": [
                    (
                        "各年の大運と歳運を"
                        "組み合わせて見ています。"
                    ),
                ],
                "advice": [
                    (
                        "年ごとの違いに合わせて、"
                        "行動の強弱を変えてください。"
                    ),
                ],
                "yearly": make_yearly(),
            },
            "advice": {
                "title": "総合アドバイス",
                "summary": (
                    "結論を一択にせず、"
                    "複数案を比較しながら"
                    "段階的に進めるのが適しています。"
                ),
                "detail": (
                    "仕事・収入・時期の三つを"
                    "別々に確認すると、"
                    "不安を具体的な判断材料へ"
                    "変えやすくなります。"
                ),
                "evidence": [
                    (
                        "命式と5年間の流れを"
                        "総合して整理しています。"
                    ),
                ],
                "advice": [
                    (
                        "選択肢を複数残しながら、"
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


def test_natural_reading_has_no_new_repetition_warning():
    reading = make_reading()

    report = validate(
        reading
    )

    assert (
        SUMMARY_DETAIL_REPETITION
        not in codes(report)
    )

    assert (
        WITHIN_SECTION_REPETITION
        not in codes(report)
    )

    assert (
        CROSS_SECTION_PHRASE_REPETITION
        not in codes(report)
    )

    assert (
        FUTURE_FLOW_REPETITION
        not in codes(report)
    )


# ============================================================
# 2. summary / detail repetition
# ============================================================


def test_detects_exact_summary_detail_repetition():
    reading = make_reading()

    repeated = (
        "転職では条件を比較しながら、"
        "段階的に判断することが大切です。"
    )

    reading[
        "sections"
    ][
        "career"
    ][
        "summary"
    ] = repeated

    reading[
        "sections"
    ][
        "career"
    ][
        "detail"
    ] = repeated

    report = validate(
        reading
    )

    assert (
        SUMMARY_DETAIL_REPETITION
        in codes(report)
    )


def test_detects_summary_embedded_almost_entirely_in_detail():
    reading = make_reading()

    summary = (
        "収入の下振れを抑えるため、"
        "条件を明文化して"
        "段階的に判断することが大切です。"
    )

    reading[
        "sections"
    ][
        "wealth"
    ][
        "summary"
    ] = summary

    reading[
        "sections"
    ][
        "wealth"
    ][
        "detail"
    ] = (
        summary
        + "そのうえで、"
        "上振れ余地を比較してください。"
    )

    report = validate(
        reading
    )

    assert (
        SUMMARY_DETAIL_REPETITION
        in codes(report)
    )


def test_keyword_overlap_alone_is_not_summary_detail_repetition():
    reading = make_reading()

    reading[
        "sections"
    ][
        "career"
    ][
        "summary"
    ] = (
        "転職では裁量のある環境が"
        "候補になります。"
    )

    reading[
        "sections"
    ][
        "career"
    ][
        "detail"
    ] = (
        "転職先を比較するときは、"
        "仕事内容だけではなく"
        "評価制度やチーム構成も"
        "確認してください。"
    )

    report = validate(
        reading
    )

    assert (
        SUMMARY_DETAIL_REPETITION
        not in codes(report)
    )


# ============================================================
# 3. Within-section repetition
# ============================================================


def test_detects_same_sentence_repeated_in_one_section():
    reading = make_reading()

    sentence = (
        "評価基準を先に確認してください。"
    )

    reading[
        "sections"
    ][
        "career"
    ][
        "detail"
    ] = (
        sentence
        + "仕事内容を整理してください。"
        + sentence
    )

    report = validate(
        reading
    )

    assert (
        WITHIN_SECTION_REPETITION
        in codes(report)
    )


def test_detects_detail_and_advice_copy_inside_same_section():
    reading = make_reading()

    repeated = (
        "条件を文書で確認してから"
        "最終判断してください。"
    )

    reading[
        "sections"
    ][
        "career"
    ][
        "detail"
    ] = repeated

    reading[
        "sections"
    ][
        "career"
    ][
        "advice"
    ] = [
        repeated,
    ]

    report = validate(
        reading
    )

    assert (
        WITHIN_SECTION_REPETITION
        in codes(report)
    )


def test_short_natural_word_repetition_is_not_flagged():
    reading = make_reading()

    reading[
        "sections"
    ][
        "career"
    ][
        "detail"
    ] = (
        "条件を確認し、"
        "仕事内容を比較してください。"
    )

    reading[
        "sections"
    ][
        "career"
    ][
        "advice"
    ] = [
        (
            "条件だけでなく、"
            "働く人との相性も"
            "確認してください。"
        ),
    ]

    report = validate(
        reading
    )

    assert (
        WITHIN_SECTION_REPETITION
        not in codes(report)
    )


# ============================================================
# 4. Cross-section phrase repetition
# ============================================================


def test_detects_same_long_phrase_across_multiple_sections():
    reading = make_reading()

    repeated = (
        "条件を明文化してから"
        "段階的に進めてください。"
    )

    for section_name in (
        "career",
        "wealth",
        "advice",
    ):
        reading[
            "sections"
        ][
            section_name
        ][
            "detail"
        ] = repeated

    report = validate(
        reading
    )

    assert (
        CROSS_SECTION_PHRASE_REPETITION
        in codes(report)
    )


def test_same_phrase_in_only_two_sections_is_tolerated():
    reading = make_reading()

    repeated = (
        "条件を明文化してから"
        "段階的に進めてください。"
    )

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
        ] = repeated

    report = validate(
        reading
    )

    assert (
        CROSS_SECTION_PHRASE_REPETITION
        not in codes(report)
    )


def test_common_domain_words_do_not_trigger_cross_section_phrase_warning():
    reading = make_reading()

    reading[
        "sections"
    ][
        "career"
    ][
        "detail"
    ] = (
        "仕事では評価基準を"
        "確認してください。"
    )

    reading[
        "sections"
    ][
        "wealth"
    ][
        "detail"
    ] = (
        "収入では評価制度と"
        "報酬条件を比較してください。"
    )

    reading[
        "sections"
    ][
        "advice"
    ][
        "detail"
    ] = (
        "最終判断では複数条件を"
        "比較してください。"
    )

    report = validate(
        reading
    )

    assert (
        CROSS_SECTION_PHRASE_REPETITION
        not in codes(report)
    )


# ============================================================
# 5. Existing cross-section advice concept check
# ============================================================


def test_existing_advice_concept_repetition_still_works():
    reading = make_reading()

    for section_name in (
        "core_personality",
        "career",
        "wealth",
        "future_flow",
    ):
        reading[
            "sections"
        ][
            section_name
        ][
            "advice"
        ] = [
            (
                "抱え込みを避け、"
                "周囲へ役割を渡してください。"
            ),
        ]

    report = validate(
        reading
    )

    assert (
        "cross_section_advice_repetition"
        in codes(report)
    )


# ============================================================
# 6. future_flow summary / yearly repetition
# ============================================================


def test_detects_future_flow_summary_copied_into_yearly():
    reading = make_reading()

    repeated = (
        "準備から基盤整備、"
        "評価拡大、専門性の深化、"
        "選択と集中へ進む流れです。"
    )

    reading[
        "sections"
    ][
        "future_flow"
    ][
        "summary"
    ] = repeated

    reading[
        "sections"
    ][
        "future_flow"
    ][
        "yearly"
    ][0][
        "detail"
    ] = repeated

    report = validate(
        reading
    )

    assert (
        FUTURE_FLOW_REPETITION
        in codes(report)
    )


def test_detects_same_yearly_detail_reused_for_multiple_years():
    reading = make_reading()

    repeated = (
        "条件を整えながら、"
        "実績を可視化して"
        "次の機会へ備える一年です。"
    )

    for index in (
        0,
        1,
        2,
    ):
        reading[
            "sections"
        ][
            "future_flow"
        ][
            "yearly"
        ][index][
            "detail"
        ] = repeated

    report = validate(
        reading
    )

    assert (
        FUTURE_FLOW_REPETITION
        in codes(report)
    )


def test_two_years_may_share_a_short_theme_without_warning():
    reading = make_reading()

    reading[
        "sections"
    ][
        "future_flow"
    ][
        "yearly"
    ][2][
        "summary"
    ] = (
        "評価が広がりやすい一年です。"
    )

    reading[
        "sections"
    ][
        "future_flow"
    ][
        "yearly"
    ][3][
        "summary"
    ] = (
        "評価を専門性へ"
        "つなげる一年です。"
    )

    report = validate(
        reading
    )

    assert (
        FUTURE_FLOW_REPETITION
        not in codes(report)
    )


def test_yearly_titles_are_not_treated_as_repetitive_body_text():
    reading = make_reading()

    for item in reading[
        "sections"
    ][
        "future_flow"
    ][
        "yearly"
    ]:
        item[
            "title"
        ] = "流れを整える年"

    report = validate(
        reading
    )

    assert (
        FUTURE_FLOW_REPETITION
        not in codes(report)
    )


# ============================================================
# 7. Severity contract
# ============================================================


def test_summary_detail_repetition_is_warning():
    reading = make_reading()

    repeated = (
        "選択肢を比較しながら"
        "段階的に判断してください。"
    )

    reading[
        "sections"
    ][
        "career"
    ][
        "summary"
    ] = repeated

    reading[
        "sections"
    ][
        "career"
    ][
        "detail"
    ] = repeated

    report = validate(
        reading
    )

    issue = next(
        issue
        for issue in report.issues
        if issue.code
        == SUMMARY_DETAIL_REPETITION
    )

    assert (
        issue_severity(
            issue
        )
        == "warning"
    )


def test_repetition_warning_alone_does_not_fail_quality_gate():
    reading = make_reading()

    repeated = (
        "選択肢を比較しながら"
        "段階的に判断してください。"
    )

    reading[
        "sections"
    ][
        "career"
    ][
        "summary"
    ] = repeated

    reading[
        "sections"
    ][
        "career"
    ][
        "detail"
    ] = repeated

    report = validate(
        reading
    )

    assert (
        SUMMARY_DETAIL_REPETITION
        in codes(report)
    )

    assert (
        report.valid
        is True
    )


# ============================================================
# 8. Issue path contract
# ============================================================


def test_summary_detail_issue_points_to_affected_section():
    reading = make_reading()

    repeated = (
        "収入条件を整理してから"
        "判断してください。"
    )

    reading[
        "sections"
    ][
        "wealth"
    ][
        "summary"
    ] = repeated

    reading[
        "sections"
    ][
        "wealth"
    ][
        "detail"
    ] = repeated

    report = validate(
        reading
    )

    issue = next(
        issue
        for issue in report.issues
        if issue.code
        == SUMMARY_DETAIL_REPETITION
    )

    assert (
        issue.path
        == "sections.wealth"
    )


def test_future_flow_issue_points_to_future_flow():
    reading = make_reading()

    repeated = (
        "段階的に土台を整え、"
        "その後に評価を広げます。"
    )

    reading[
        "sections"
    ][
        "future_flow"
    ][
        "detail"
    ] = repeated

    reading[
        "sections"
    ][
        "future_flow"
    ][
        "yearly"
    ][0][
        "detail"
    ] = repeated

    report = validate(
        reading
    )

    issue = next(
        issue
        for issue in report.issues
        if issue.code
        == FUTURE_FLOW_REPETITION
    )

    assert (
        issue.path
        == "sections.future_flow"
    )


# ============================================================
# 9. Immutability
# ============================================================


def test_repetition_validation_does_not_mutate_reading():
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


def test_repetition_validation_does_not_rewrite_duplicate_text():
    reading = make_reading()

    repeated = (
        "条件を比較してから"
        "判断してください。"
    )

    reading[
        "sections"
    ][
        "career"
    ][
        "summary"
    ] = repeated

    reading[
        "sections"
    ][
        "career"
    ][
        "detail"
    ] = repeated

    validate(
        reading
    )

    assert (
        reading[
            "sections"
        ][
            "career"
        ][
            "summary"
        ]
        == repeated
    )

    assert (
        reading[
            "sections"
        ][
            "career"
        ][
            "detail"
        ]
        == repeated
    )
