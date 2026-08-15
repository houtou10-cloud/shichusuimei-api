"""
tests/test_reading_quality_useful_gods.py

販売版 v1 に向けた
「用神」と「補助用神」の役割表現整合性テスト。

背景
----
reading_context の useful_gods では、

    primary_useful_element
    secondary_useful_elements
    final_useful_elements

を区別して保持している。

たとえば、

    primary_useful_element = "土"
    secondary_useful_elements = ["水", "火", "金"]
    final_useful_elements = ["土", "水", "火", "金"]

の場合、

    「用神は土」
    「用神の土を中心に、水・火・金が補助する」

は正しい。

一方、

    「用神に土・水・火・金が揃う」
    「用神は土・水・火・金です」

のように primary と secondary を
すべて同格の「用神」と表現すると、
計算済み事実との役割関係が崩れる。

本テストでは、この混同を
顧客向けQuality warningとして検出する。

設計方針
--------
- 占術計算は変更しない。
- reading_context の計算済み値を正とする。
- 顧客向け文章だけを検査する。
- 問題箇所は leaf path で返す。
  Auto-Repair が該当文章だけを
  部分修復できるようにする。
- 本issue単独ではPDF生成を止めない。
"""

from __future__ import annotations

from copy import deepcopy

from engine.reading_quality import (
    issue_severity,
    validate_customer_facing_reading,
)


# ============================================================
# Expected issue code
# ============================================================


USEFUL_GODS_ROLE_CONFUSION = (
    "useful_gods_role_confusion"
)


# ============================================================
# Helpers
# ============================================================


def make_reading_context(
    *,
    primary="土",
    secondary=None,
    final=None,
):
    if secondary is None:
        secondary = [
            "水",
            "火",
            "金",
        ]

    if final is None:
        final = [
            primary,
            *secondary,
        ]

    return {
        "useful_gods": {
            "primary_useful_element": (
                primary
            ),
            "secondary_useful_elements": (
                list(
                    secondary
                )
            ),
            "final_useful_elements": (
                list(
                    final
                )
            ),
            "unfavorable_elements": [],
            "strength_class": "balanced",
            "confidence": 0.8,
            "agreement_level": "high",
        },
    }


def make_yearly():
    return [
        {
            "year": 2026,
            "title": "ここから年末まで",
            "summary": (
                "発信と検証を進めながら、"
                "反応の良い方向を"
                "見極める期間です。"
            ),
            "detail": (
                "一度に広げず、"
                "小さな試行を重ねて"
                "手応えを確認してください。"
            ),
            "advice": [
                (
                    "反応の良い企画を"
                    "一つ選んでください。"
                ),
            ],
        },
        {
            "year": 2027,
            "title": "基盤を固める年",
            "summary": (
                "収支や契約などの"
                "土台を整えやすい一年です。"
            ),
            "detail": (
                "価格や提供条件を整理し、"
                "継続しやすい仕組みへ"
                "整えることが役立ちます。"
            ),
            "advice": [
                (
                    "価格と作業時間を"
                    "記録してください。"
                ),
            ],
        },
        {
            "year": 2028,
            "title": "安定収益を育てる年",
            "summary": (
                "継続的な売上を"
                "意識しやすい一年です。"
            ),
            "detail": (
                "成果が出た方法を"
                "再利用できる形にすると、"
                "負担を抑えやすくなります。"
            ),
            "advice": [
                (
                    "継続販売できる形を"
                    "検討しましょう。"
                ),
            ],
        },
        {
            "year": 2029,
            "title": "選択肢が広がる年",
            "summary": (
                "新しい顧客や案件との"
                "接点が増えやすい時期です。"
            ),
            "detail": (
                "数だけを追わず、"
                "利益と負荷のバランスを"
                "確認することが大切です。"
            ),
            "advice": [
                (
                    "採算の良い案件を"
                    "優先してください。"
                ),
            ],
        },
        {
            "year": 2030,
            "title": "守りを整える年",
            "summary": (
                "広げたものを整理して、"
                "安定運用へ移す時期です。"
            ),
            "detail": (
                "契約や品質基準を見直し、"
                "長く続けるための"
                "仕組みを整えてください。"
            ),
            "advice": [
                (
                    "不要な負担を"
                    "減らしていきましょう。"
                ),
            ],
        },
    ]


def make_reading():
    """
    既存Qualityルールに抵触しにくい
    顧客向け鑑定JSONの最小実用fixture。
    """

    return {
        "summary": (
            "命式と現在の流れを踏まえ、"
            "相談内容に沿って"
            "今後の方向性を整理します。"
        ),
        "sections": {
            "core_personality": {
                "title": "本質・性格",
                "summary": (
                    "柔軟に工夫しながら、"
                    "着実に改善していく"
                    "力があります。"
                ),
                "detail": (
                    "周囲の状況を見ながら"
                    "方法を調整できるため、"
                    "試行錯誤を重ねる場面で"
                    "持ち味を活かしやすいでしょう。"
                ),
                "evidence": [
                    (
                        "日主と命式全体の構成を"
                        "性格傾向として"
                        "整理しています。"
                    ),
                ],
                "advice": [
                    (
                        "一度に完成を目指さず、"
                        "改善を重ねてください。"
                    ),
                ],
            },
            "career": {
                "title": "仕事・適職",
                "summary": (
                    "企画と改善を組み合わせる"
                    "仕事と相性があります。"
                ),
                "detail": (
                    "仕事内容だけでなく、"
                    "裁量や評価基準も確認すると"
                    "環境との相性を"
                    "判断しやすくなります。"
                ),
                "evidence": [
                    (
                        "格局と五行のバランスを"
                        "仕事上の活かし方へ"
                        "置き換えています。"
                    ),
                ],
                "advice": [
                    (
                        "得意な工程を"
                        "一つ明確にしてください。"
                    ),
                ],
            },
            "wealth": {
                "title": "金運",
                "summary": (
                    "収入を増やすことと、"
                    "管理を整えることの"
                    "両方が重要になります。"
                ),
                "detail": (
                    "用神は土です。"
                    "水・火・金は補助として"
                    "活かすとバランスを"
                    "取りやすくなります。"
                ),
                "evidence": [
                    (
                        "用神と補助用神の"
                        "役割を区別して"
                        "金運へ反映しています。"
                    ),
                ],
                "advice": [
                    (
                        "収支を記録し、"
                        "利益が残る形を"
                        "確認してください。"
                    ),
                ],
            },
            "relationships": {
                "title": "恋愛・人間関係",
                "summary": (
                    "相手に合わせる力を"
                    "持っています。"
                ),
                "detail": (
                    "期待することを"
                    "先に共有すると、"
                    "すれ違いを"
                    "減らしやすくなります。"
                ),
                "evidence": [
                    (
                        "命式の対人傾向を"
                        "日常的な関係づくりへ"
                        "置き換えています。"
                    ),
                ],
                "advice": [
                    (
                        "役割と期待を"
                        "言葉にしてください。"
                    ),
                ],
            },
            "health": {
                "title": "健康傾向",
                "summary": (
                    "生活全体のバランスを"
                    "意識することが役立ちます。"
                ),
                "detail": (
                    "四柱推命は医学的診断ではありません。"
                    "休息や活動量を見直す"
                    "一般的な参考として"
                    "扱ってください。"
                ),
                "evidence": [
                    (
                        "五行の偏りは"
                        "生活習慣を考える"
                        "参考情報として扱います。"
                    ),
                ],
                "advice": [
                    (
                        "不調がある場合は"
                        "医療専門家へ"
                        "相談してください。"
                    ),
                ],
            },
            "current_luck": {
                "title": "現在の運勢",
                "summary": (
                    "今は試しながら"
                    "方向を絞る時期です。"
                ),
                "detail": (
                    "小さな行動で反応を確かめ、"
                    "成果が見えるものへ"
                    "力を寄せる方法が"
                    "現実的です。"
                ),
                "evidence": [
                    (
                        "現在大運と歳運を"
                        "組み合わせて"
                        "行動の強弱を見ています。"
                    ),
                ],
                "advice": [
                    (
                        "反応を記録して"
                        "次の判断に使ってください。"
                    ),
                ],
            },
            "future_flow": {
                "title": "これから5年間の運勢",
                "summary": (
                    "検証から基盤整備、"
                    "安定収益、拡張、"
                    "再整備へ進む流れです。"
                ),
                "detail": (
                    "年ごとのテーマを分けて、"
                    "その時期に必要な"
                    "課題へ集中すると"
                    "進めやすくなります。"
                ),
                "evidence": [
                    (
                        "5年分の大運と歳運を"
                        "比較して"
                        "全体の変化を見ています。"
                    ),
                ],
                "advice": [
                    (
                        "毎年の優先順位を"
                        "一つ決めてください。"
                    ),
                ],
                "yearly": make_yearly(),
            },
            "advice": {
                "title": "総合アドバイス",
                "summary": (
                    "小さく試し、"
                    "成果が出た方法を"
                    "仕組みにする進め方が合います。"
                ),
                "detail": (
                    "用神の土を中心に、"
                    "水・火・金を補助として"
                    "活かす考え方で、"
                    "収益と運用の両面を"
                    "整えていくとよいでしょう。"
                ),
                "evidence": [
                    (
                        "命式と現在運、"
                        "5年運を総合して"
                        "相談内容へ結びつけています。"
                    ),
                ],
                "advice": [
                    (
                        "利益と負荷を"
                        "定期的に振り返ってください。"
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
    reading_context=None,
):
    return validate_customer_facing_reading(
        reading,
        reading_context=(
            reading_context
        ),
    )


def codes(
    report,
):
    return {
        issue.code
        for issue in report.issues
    }


def useful_issues(
    report,
):
    return tuple(
        issue
        for issue in report.issues
        if issue.code
        == USEFUL_GODS_ROLE_CONFUSION
    )


# ============================================================
# 1. Baseline
# ============================================================


def test_natural_useful_gods_wording_has_no_warning():
    reading = make_reading()
    context = make_reading_context()

    report = validate(
        reading,
        context,
    )

    assert (
        USEFUL_GODS_ROLE_CONFUSION
        not in codes(report)
    )


def test_primary_and_secondary_explicit_wording_is_valid():
    reading = make_reading()
    context = make_reading_context()

    reading[
        "sections"
    ][
        "wealth"
    ][
        "detail"
    ] = (
        "用神は土で、"
        "補助は水・火・金です。"
    )

    report = validate(
        reading,
        context,
    )

    assert (
        USEFUL_GODS_ROLE_CONFUSION
        not in codes(report)
    )


def test_primary_centered_wording_is_valid():
    reading = make_reading()
    context = make_reading_context()

    reading[
        "sections"
    ][
        "wealth"
    ][
        "detail"
    ] = (
        "用神の土を中心に、"
        "水・火・金も補助として"
        "活かしていく考え方です。"
    )

    report = validate(
        reading,
        context,
    )

    assert (
        USEFUL_GODS_ROLE_CONFUSION
        not in codes(report)
    )


# ============================================================
# 2. Detect primary / secondary confusion
# ============================================================


def test_detects_all_final_elements_called_useful_gods():
    reading = make_reading()
    context = make_reading_context()

    reading[
        "sections"
    ][
        "wealth"
    ][
        "detail"
    ] = (
        "用神に土・水・火・金が"
        "そろっています。"
    )

    report = validate(
        reading,
        context,
    )

    assert (
        USEFUL_GODS_ROLE_CONFUSION
        in codes(report)
    )


def test_detects_useful_gods_are_all_elements_wording():
    reading = make_reading()
    context = make_reading_context()

    reading[
        "sections"
    ][
        "career"
    ][
        "detail"
    ] = (
        "この命式の用神は"
        "土・水・火・金です。"
    )

    report = validate(
        reading,
        context,
    )

    assert (
        USEFUL_GODS_ROLE_CONFUSION
        in codes(report)
    )


def test_detects_all_elements_as_same_rank_useful_gods():
    reading = make_reading()
    context = make_reading_context()

    reading[
        "sections"
    ][
        "advice"
    ][
        "detail"
    ] = (
        "用神として"
        "土・水・火・金を"
        "活かすことが重要です。"
    )

    report = validate(
        reading,
        context,
    )

    assert (
        USEFUL_GODS_ROLE_CONFUSION
        in codes(report)
    )


def test_detects_parenthetical_all_useful_elements():
    reading = make_reading()
    context = make_reading_context()

    reading[
        "sections"
    ][
        "current_luck"
    ][
        "detail"
    ] = (
        "用神（土・水・火・金）を"
        "意識して行動すると"
        "流れを活かしやすくなります。"
    )

    report = validate(
        reading,
        context,
    )

    assert (
        USEFUL_GODS_ROLE_CONFUSION
        in codes(report)
    )


def test_detects_secondary_only_element_called_primary_useful_god():
    reading = make_reading()
    context = make_reading_context()

    reading[
        "sections"
    ][
        "career"
    ][
        "detail"
    ] = (
        "この命式では"
        "水が用神です。"
    )

    report = validate(
        reading,
        context,
    )

    assert (
        USEFUL_GODS_ROLE_CONFUSION
        in codes(report)
    )


# ============================================================
# 3. Other primary elements
# ============================================================


def test_detector_is_not_hardcoded_to_earth():
    reading = make_reading()

    context = make_reading_context(
        primary="火",
        secondary=[
            "土",
            "木",
        ],
        final=[
            "火",
            "土",
            "木",
        ],
    )

    reading[
        "sections"
    ][
        "wealth"
    ][
        "detail"
    ] = (
        "用神は火・土・木です。"
    )

    report = validate(
        reading,
        context,
    )

    assert (
        USEFUL_GODS_ROLE_CONFUSION
        in codes(report)
    )


def test_other_primary_element_correct_wording_passes():
    reading = make_reading()

    context = make_reading_context(
        primary="火",
        secondary=[
            "土",
            "木",
        ],
        final=[
            "火",
            "土",
            "木",
        ],
    )

    reading[
        "sections"
    ][
        "wealth"
    ][
        "detail"
    ] = (
        "用神は火です。"
        "土と木は補助として"
        "活かします。"
    )

    report = validate(
        reading,
        context,
    )

    assert (
        USEFUL_GODS_ROLE_CONFUSION
        not in codes(report)
    )


# ============================================================
# 4. Primary only
# ============================================================


def test_primary_only_context_allows_single_useful_god():
    reading = make_reading()

    context = make_reading_context(
        primary="土",
        secondary=[],
        final=[
            "土",
        ],
    )

    reading[
        "sections"
    ][
        "wealth"
    ][
        "detail"
    ] = (
        "この命式の用神は土です。"
    )

    report = validate(
        reading,
        context,
    )

    assert (
        USEFUL_GODS_ROLE_CONFUSION
        not in codes(report)
    )


def test_primary_only_does_not_invent_secondary_confusion():
    reading = make_reading()

    context = make_reading_context(
        primary="土",
        secondary=[],
        final=[
            "土",
        ],
    )

    reading[
        "sections"
    ][
        "wealth"
    ][
        "detail"
    ] = (
        "土を中心に"
        "収益管理を整えると"
        "安定しやすくなります。"
    )

    report = validate(
        reading,
        context,
    )

    assert (
        USEFUL_GODS_ROLE_CONFUSION
        not in codes(report)
    )


# ============================================================
# 5. Missing / insufficient context
# ============================================================


def test_no_reading_context_skips_useful_gods_role_check():
    reading = make_reading()

    reading[
        "sections"
    ][
        "wealth"
    ][
        "detail"
    ] = (
        "用神は土・水・火・金です。"
    )

    report = validate(
        reading,
        None,
    )

    assert (
        USEFUL_GODS_ROLE_CONFUSION
        not in codes(report)
    )


def test_missing_useful_gods_context_skips_check():
    reading = make_reading()

    reading[
        "sections"
    ][
        "wealth"
    ][
        "detail"
    ] = (
        "用神は土・水・火・金です。"
    )

    report = validate(
        reading,
        {},
    )

    assert (
        USEFUL_GODS_ROLE_CONFUSION
        not in codes(report)
    )


def test_missing_primary_useful_element_skips_check():
    reading = make_reading()

    context = {
        "useful_gods": {
            "primary_useful_element": None,
            "secondary_useful_elements": [
                "水",
                "火",
            ],
            "final_useful_elements": [
                "水",
                "火",
            ],
        },
    }

    reading[
        "sections"
    ][
        "wealth"
    ][
        "detail"
    ] = (
        "用神は水・火です。"
    )

    report = validate(
        reading,
        context,
    )

    assert (
        USEFUL_GODS_ROLE_CONFUSION
        not in codes(report)
    )


# ============================================================
# 6. Issue path contract
# ============================================================


def test_issue_points_to_exact_customer_text_path():
    reading = make_reading()
    context = make_reading_context()

    reading[
        "sections"
    ][
        "wealth"
    ][
        "detail"
    ] = (
        "用神に土・水・火・金が"
        "そろっています。"
    )

    report = validate(
        reading,
        context,
    )

    issue = useful_issues(
        report
    )[0]

    assert (
        issue.path
        == "sections.wealth.detail"
    )


def test_issue_inside_evidence_points_to_exact_list_item():
    reading = make_reading()
    context = make_reading_context()

    reading[
        "sections"
    ][
        "career"
    ][
        "evidence"
    ] = [
        (
            "用神は土・水・火・金で、"
            "仕事全体を支える配置です。"
        ),
    ]

    report = validate(
        reading,
        context,
    )

    issue = useful_issues(
        report
    )[0]

    assert (
        issue.path
        == "sections.career.evidence[0]"
    )


def test_issue_inside_yearly_points_to_exact_yearly_path():
    reading = make_reading()
    context = make_reading_context()

    reading[
        "sections"
    ][
        "future_flow"
    ][
        "yearly"
    ][2][
        "detail"
    ] = (
        "2028年は"
        "用神の土・水・火・金が"
        "働きやすい年です。"
    )

    report = validate(
        reading,
        context,
    )

    issue = useful_issues(
        report
    )[0]

    assert (
        issue.path
        == (
            "sections.future_flow."
            "yearly[2].detail"
        )
    )


# ============================================================
# 7. Severity / gate contract
# ============================================================


def test_useful_gods_role_confusion_is_warning():
    reading = make_reading()
    context = make_reading_context()

    reading[
        "sections"
    ][
        "wealth"
    ][
        "detail"
    ] = (
        "用神は土・水・火・金です。"
    )

    report = validate(
        reading,
        context,
    )

    issue = useful_issues(
        report
    )[0]

    assert (
        issue_severity(
            issue
        )
        == "warning"
    )


def test_useful_gods_warning_alone_does_not_fail_gate():
    reading = make_reading()
    context = make_reading_context()

    reading[
        "sections"
    ][
        "wealth"
    ][
        "detail"
    ] = (
        "用神は土・水・火・金です。"
    )

    report = validate(
        reading,
        context,
    )

    assert (
        USEFUL_GODS_ROLE_CONFUSION
        in codes(report)
    )

    assert (
        report.valid
        is True
    )


# ============================================================
# 8. Multiple occurrences
# ============================================================


def test_detects_confusion_in_multiple_sections():
    reading = make_reading()
    context = make_reading_context()

    reading[
        "sections"
    ][
        "career"
    ][
        "detail"
    ] = (
        "用神は土・水・火・金です。"
    )

    reading[
        "sections"
    ][
        "wealth"
    ][
        "detail"
    ] = (
        "用神に土・水・火・金が"
        "そろっています。"
    )

    report = validate(
        reading,
        context,
    )

    issues = useful_issues(
        report
    )

    assert (
        len(issues)
        == 2
    )

    assert {
        issue.path
        for issue in issues
    } == {
        "sections.career.detail",
        "sections.wealth.detail",
    }


# ============================================================
# 9. Immutability
# ============================================================


def test_useful_gods_validation_does_not_mutate_reading():
    reading = make_reading()
    context = make_reading_context()

    reading[
        "sections"
    ][
        "wealth"
    ][
        "detail"
    ] = (
        "用神は土・水・火・金です。"
    )

    before = deepcopy(
        reading
    )

    validate(
        reading,
        context,
    )

    assert (
        reading
        == before
    )


def test_useful_gods_validation_does_not_mutate_context():
    reading = make_reading()
    context = make_reading_context()

    reading[
        "sections"
    ][
        "wealth"
    ][
        "detail"
    ] = (
        "用神は土・水・火・金です。"
    )

    before = deepcopy(
        context
    )

    validate(
        reading,
        context,
    )

    assert (
        context
        == before
    )
