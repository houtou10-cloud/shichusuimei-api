"""
Tests for engine.reading_quality.

Customer-facing AI reading quality gate のテスト。

目的:
- 内部評価ラベルを顧客向け文章へ出さない
- 内部キーを顧客向け文章へ出さない
- snake_case を顧客向け文章へ出さない
- JSON path を顧客向け文章へ出さない
- field=value を顧客向け文章へ出さない
- 根拠のない具体的数量助言を検出する
- reading_context に根拠がある数値は許容する
- 過度な断定表現を検出する
- disclaimer の最低限の安全性を確認する
- 内部JSON構造そのものは誤検出しない
- 検査によって入力データを変更しない
"""

from __future__ import annotations

from copy import deepcopy
import json

import pytest

from engine.reading_quality import (
    READING_QUALITY_METHOD,
    READING_QUALITY_STATUS,
    READING_QUALITY_VERSION,
    CustomerFacingText,
    QualityIssue,
    ReadingQualityError,
    ReadingQualityReport,
    ensure_customer_facing_reading_quality,
    find_internal_key_leaks,
    find_internal_label_leaks,
    find_overconfident_claims,
    find_unsupported_numeric_claims,
    iter_customer_facing_texts,
    quality_report_to_json,
    validate_customer_facing_reading,
    validate_disclaimer,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def valid_ai_reading():
    """
    顧客向け品質ゲートを通過する最小構成。
    """

    return {
        "summary": (
            "命式全体を見ると、行動力と慎重さの"
            "バランスを意識すると持ち味を"
            "活かしやすい傾向があります。"
        ),
        "sections": {
            "core_personality": {
                "title": "本質・性格",
                "summary": (
                    "日主の性質を軸に、自主性と"
                    "改善力を活かしやすい傾向です。"
                ),
                "detail": (
                    "物事を整理し、必要な部分を"
                    "磨き上げていく力があります。"
                ),
                "evidence": [
                    (
                        "日主の性質から、物事を整え"
                        "精度を高める力として読みます。"
                    ),
                    (
                        "身強身弱は中和と判定され、"
                        "環境との組み合わせが重要です。"
                    ),
                ],
                "advice": [
                    (
                        "結論を急ぎすぎず、周囲との"
                        "合意形成も意識してください。"
                    ),
                    (
                        "改善だけでなく、新しい学びや"
                        "関係づくりにも目を向けましょう。"
                    ),
                ],
            },
            "career": {
                "title": "仕事・適職",
                "summary": (
                    "現場判断と改善力を活かせる"
                    "環境と相性が良い傾向です。"
                ),
                "detail": (
                    "仕事では、裁量があり、課題を"
                    "整理して改善へつなげられる場で"
                    "強みを活かしやすいでしょう。"
                ),
                "evidence": [
                    (
                        "命式の主格と日主の組み合わせ"
                        "から、判断力と改善力を"
                        "活かしやすいと読みます。"
                    ),
                ],
                "advice": [
                    (
                        "現在の仕事で強みを活かせる"
                        "役割を整理し、小さく検証して"
                        "から次の判断へ進みましょう。"
                    ),
                ],
            },
            "wealth": {
                "title": "金運",
                "summary": (
                    "収益機会を活かしながら、"
                    "仕組みを整えることが大切です。"
                ),
                "detail": (
                    "短期的な機会だけを見るのではなく、"
                    "収支や継続性も確認すると"
                    "安定につながりやすいでしょう。"
                ),
                "evidence": [
                    (
                        "現在の運勢では収益機会を"
                        "活かしやすい要素があります。"
                    ),
                ],
                "advice": [
                    (
                        "収支や原価を確認し、"
                        "現実の数字も併用して"
                        "判断してください。"
                    ),
                ],
            },
            "relationships": {
                "title": "恋愛・人間関係",
                "summary": (
                    "意思決定の速さを活かしながら、"
                    "相手との対話を丁寧にすると"
                    "関係が安定しやすいでしょう。"
                ),
                "detail": (
                    "自分の考えを明確に持ちやすい一方、"
                    "相手のペースを確認することも"
                    "大切です。"
                ),
                "evidence": [
                    (
                        "命式上の自主性の強さから、"
                        "自分で判断して進みやすい"
                        "傾向として読みます。"
                    ),
                ],
                "advice": [
                    (
                        "結論だけでなく、背景や意図も"
                        "共有するよう意識しましょう。"
                    ),
                ],
            },
            "health": {
                "title": "健康傾向",
                "summary": (
                    "生活のリズムと休息を整えることを"
                    "意識するとよいでしょう。"
                ),
                "detail": (
                    "これは医学的診断ではなく、"
                    "五行上の偏りから見た"
                    "生活上の傾向です。"
                ),
                "evidence": [
                    (
                        "五行の偏りから、緊張と休息の"
                        "バランスを意識したい傾向です。"
                    ),
                ],
                "advice": [
                    (
                        "心身の不調が気になる場合は、"
                        "自己判断せず医療専門家へ"
                        "相談してください。"
                    ),
                ],
            },
            "current_luck": {
                "title": "現在の運勢",
                "summary": (
                    "追い風になる要素と慎重さが"
                    "必要な要素の両方があります。"
                ),
                "detail": (
                    "現在は機会を活かしながら、"
                    "拙速な判断を避けることが"
                    "重要な時期です。"
                ),
                "evidence": [
                    (
                        "大運と年運を総合すると、"
                        "機会を活かしつつ慎重に"
                        "進めたい流れと読みます。"
                    ),
                ],
                "advice": [
                    (
                        "小さく試し、結果を確認しながら"
                        "次の行動を決めてください。"
                    ),
                ],
            },
            "future_flow": {
                "title": "今後の流れ",
                "summary": (
                    "今後は継続性と安定した基盤づくりが"
                    "重要になりやすい流れです。"
                ),
                "detail": (
                    "現在得ている機会の中から、"
                    "再現性のあるものを選び、"
                    "仕組みへ移していくとよいでしょう。"
                ),
                "evidence": [
                    (
                        "次の大運では、継続性や"
                        "堅実な運用を重視する要素が"
                        "強まりやすいと読みます。"
                    ),
                ],
                "advice": [
                    (
                        "続けやすい条件を整理し、"
                        "再現性の高いものへ"
                        "資源を集中させましょう。"
                    ),
                ],
            },
            "advice": {
                "title": "総合アドバイス",
                "summary": (
                    "機会を試しながら、安定した"
                    "仕組みへつなげていくことが"
                    "重要です。"
                ),
                "detail": (
                    "一つの選択肢へ急いで決めるより、"
                    "現実の結果を確認しながら"
                    "段階的に判断するとよいでしょう。"
                ),
                "evidence": [
                    (
                        "現在と今後の運勢を総合すると、"
                        "機会と安定の両方を意識する"
                        "流れが示されています。"
                    ),
                ],
                "advice": [
                    (
                        "現実の収支や働き方も確認し、"
                        "占術だけで重要な判断を"
                        "決めないようにしてください。"
                    ),
                ],
            },
        },
        "disclaimer": (
            "本鑑定は四柱推命に基づく傾向の"
            "読み解きであり、医学的診断では"
            "ありません。投資や金融判断の"
            "保証を行うものでもなく、将来の"
            "出来事を断定的に約束するものでは"
            "ありません。重要な判断では必要に"
            "応じて専門家の意見や現実情報を"
            "併用してください。"
        ),
    }


@pytest.fixture
def reading_context():
    """
    数値根拠判定用の最小reading_context。
    """

    return {
        "schema_version": "reading_context_v1",
        "subject": {
            "birth_year": 1990,
        },
        "natal_chart": {
            "day_master": "庚",
            "strength": {
                "score": 51.95,
                "label": "中和",
            },
        },
        "luck": {
            "current_year": 2026,
            "current_da_un": {
                "start_age": 27,
                "end_age": 36,
            },
        },
        "reading_sections": {},
        "safety": {},
    }


@pytest.fixture
def consultation_context():
    return {
        "version": "consultation_context_v1",
        "input": {
            "concern": (
                "今の仕事を続けるか、副業や"
                "独立へ進むか悩んでいます。"
            ),
            "desired_future": (
                "安定した収入を得たいです。"
            ),
        },
        "has_consultation": True,
        "recalculates_astrology": False,
        "rewrites_chart_facts": False,
    }


# ============================================================================
# Identity
# ============================================================================


def test_quality_version():
    assert (
        READING_QUALITY_VERSION
        == "reading_quality_v1"
    )


def test_quality_method():
    assert (
        READING_QUALITY_METHOD
        == "customer_facing_quality_gate_v1"
    )


def test_quality_status():
    assert (
        READING_QUALITY_STATUS
        == "ready_for_customer_facing_validation"
    )


# ============================================================================
# Customer-facing extraction
# ============================================================================


def test_iter_customer_facing_texts_returns_tuple(
    valid_ai_reading,
):
    result = iter_customer_facing_texts(
        valid_ai_reading
    )

    assert isinstance(result, tuple)
    assert result


def test_iter_customer_facing_texts_contains_root_summary(
    valid_ai_reading,
):
    result = iter_customer_facing_texts(
        valid_ai_reading
    )

    assert any(
        item.path == "summary"
        for item in result
    )


def test_iter_customer_facing_texts_contains_disclaimer(
    valid_ai_reading,
):
    result = iter_customer_facing_texts(
        valid_ai_reading
    )

    assert any(
        item.path == "disclaimer"
        for item in result
    )


def test_iter_customer_facing_texts_contains_section_summary(
    valid_ai_reading,
):
    result = iter_customer_facing_texts(
        valid_ai_reading
    )

    assert any(
        item.path
        == "sections.career.summary"
        for item in result
    )


def test_iter_customer_facing_texts_contains_evidence_item(
    valid_ai_reading,
):
    result = iter_customer_facing_texts(
        valid_ai_reading
    )

    assert any(
        item.path
        == "sections.career.evidence[0]"
        for item in result
    )


def test_iter_customer_facing_texts_contains_advice_item(
    valid_ai_reading,
):
    result = iter_customer_facing_texts(
        valid_ai_reading
    )

    assert any(
        item.path
        == "sections.career.advice[0]"
        for item in result
    )


def test_customer_facing_text_dataclass():
    item = CustomerFacingText(
        path="summary",
        text="テスト",
        kind="summary",
    )

    assert item.path == "summary"
    assert item.text == "テスト"
    assert item.kind == "summary"


def test_internal_metadata_is_not_customer_facing(
    valid_ai_reading,
):
    reading = deepcopy(
        valid_ai_reading
    )

    reading["metadata"] = {
        "overall": "mixed",
        "current_luck": "positive",
        "schema_version": "internal_v1",
    }

    result = iter_customer_facing_texts(
        reading
    )

    assert all(
        not item.path.startswith("metadata")
        for item in result
    )


# ============================================================================
# Internal label leaks
# ============================================================================


@pytest.mark.parametrize(
    "label",
    (
        "mixed",
        "overall",
        "positive",
        "negative",
        "neutral",
    ),
)
def test_internal_label_leak_detected(
    valid_ai_reading,
    label,
):
    reading = deepcopy(
        valid_ai_reading
    )

    reading["sections"]["wealth"]["evidence"][
        0
    ] = (
        f"統合運は{label}と評価されています。"
    )

    issues = find_internal_label_leaks(
        reading
    )

    assert issues
    assert any(
        issue.code == "internal_label_leak"
        for issue in issues
    )

    assert any(
        issue.matched.lower() == label
        for issue in issues
        if issue.matched is not None
    )


def test_real_mixed_leak_pattern_detected(
    valid_ai_reading,
):
    reading = deepcopy(
        valid_ai_reading
    )

    reading["sections"]["wealth"]["evidence"][
        0
    ] = (
        "統合運は「mixed（混在）」ですが、"
        "偏財の働きは有効と評価されています。"
    )

    issues = find_internal_label_leaks(
        reading
    )

    assert any(
        issue.matched == "mixed"
        for issue in issues
    )


def test_real_overall_leak_pattern_detected(
    valid_ai_reading,
):
    reading = deepcopy(
        valid_ai_reading
    )

    reading["sections"]["current_luck"][
        "evidence"
    ][0] = (
        "統合運はoverallが混在と評価されつつ、"
        "活かし方次第で成果につながります。"
    )

    issues = find_internal_label_leaks(
        reading
    )

    assert any(
        issue.matched == "overall"
        for issue in issues
    )


def test_internal_label_in_metadata_is_allowed(
    valid_ai_reading,
):
    reading = deepcopy(
        valid_ai_reading
    )

    reading["metadata"] = {
        "overall": "mixed",
        "direction": "positive",
    }

    issues = find_internal_label_leaks(
        reading
    )

    assert issues == ()


def test_japanese_translation_of_mixed_is_allowed(
    valid_ai_reading,
):
    reading = deepcopy(
        valid_ai_reading
    )

    reading["sections"]["current_luck"][
        "summary"
    ] = (
        "追い風になる要素と慎重さが必要な"
        "要素の両方があります。"
    )

    issues = find_internal_label_leaks(
        reading
    )

    assert issues == ()


# ============================================================================
# Internal key leaks
# ============================================================================


@pytest.mark.parametrize(
    "text",
    (
        "overall_scoreを見ると安定しています。",
        "current_luckでは追い風です。",
        "useful_godsは水です。",
        "reading_contextを確認してください。",
        "integrated_luckの結果です。",
        "day_masterは庚です。",
        "schema_versionはv1です。",
    ),
)
def test_internal_field_leak_detected(
    valid_ai_reading,
    text,
):
    reading = deepcopy(
        valid_ai_reading
    )

    reading["sections"]["career"]["detail"] = (
        text
    )

    issues = find_internal_key_leaks(
        reading
    )

    assert issues


def test_snake_case_detected(
    valid_ai_reading,
):
    reading = deepcopy(
        valid_ai_reading
    )

    reading["sections"]["career"]["detail"] = (
        "overall_scoreを基準に判断します。"
    )

    issues = find_internal_key_leaks(
        reading
    )

    assert any(
        issue.code == "snake_case_leak"
        for issue in issues
    )


def test_json_path_detected(
    valid_ai_reading,
):
    reading = deepcopy(
        valid_ai_reading
    )

    reading["sections"]["career"]["detail"] = (
        "integrated_luck.overall_scoreを"
        "参照すると現在の流れが分かります。"
    )

    issues = find_internal_key_leaks(
        reading
    )

    assert any(
        issue.code == "json_path_leak"
        for issue in issues
    )


def test_field_assignment_detected(
    valid_ai_reading,
):
    reading = deepcopy(
        valid_ai_reading
    )

    reading["sections"]["career"]["detail"] = (
        "overall=mixedという評価です。"
    )

    issues = find_internal_key_leaks(
        reading
    )

    assert any(
        issue.code
        == "field_assignment_leak"
        for issue in issues
    )


def test_internal_keys_as_json_keys_are_allowed(
    valid_ai_reading,
):
    reading = deepcopy(
        valid_ai_reading
    )

    reading["internal"] = {
        "overall_score": 10,
        "current_luck": {
            "overall": "mixed",
        },
        "useful_gods": ["水"],
    }

    issues = find_internal_key_leaks(
        reading
    )

    assert issues == ()


# ============================================================================
# Overconfident claims
# ============================================================================


@pytest.mark.parametrize(
    "text",
    (
        "あなたは必ず成功します。",
        "この仕事なら確実に成功します。",
        "副業を始めれば絶対に稼げるでしょう。",
        "この投資なら必ず儲かるでしょう。",
        "来年は確実に結婚します。",
        "今年は必ず転職します。",
        "この時期に病気になります。",
        "来年に発症します。",
    ),
)
def test_overconfident_claim_detected(
    valid_ai_reading,
    text,
):
    reading = deepcopy(
        valid_ai_reading
    )

    reading["sections"]["advice"]["detail"] = (
        text
    )

    issues = find_overconfident_claims(
        reading
    )

    assert issues


@pytest.mark.parametrize(
    "text",
    (
        "成功につながりやすい傾向があります。",
        "収益機会を活かしやすい時期です。",
        "転職も選択肢の一つとして検討できます。",
        "結婚を断定するものではありません。",
        "健康面は医学的診断ではありません。",
    ),
)
def test_cautious_claim_is_allowed(
    valid_ai_reading,
    text,
):
    reading = deepcopy(
        valid_ai_reading
    )

    reading["sections"]["advice"]["detail"] = (
        text
    )

    issues = find_overconfident_claims(
        reading
    )

    assert issues == ()


# ============================================================================
# Unsupported numeric claims
# ============================================================================


def test_real_two_to_three_types_advice_detected(
    valid_ai_reading,
    reading_context,
    consultation_context,
):
    reading = deepcopy(
        valid_ai_reading
    )

    reading["sections"]["future_flow"][
        "advice"
    ][0] = (
        "チャネルや顧客層は2〜3種類に整理し、"
        "最も再現性の高い型へ"
        "資源を集中させてください。"
    )

    issues = find_unsupported_numeric_claims(
        reading,
        reading_context=reading_context,
        consultation_context=(
            consultation_context
        ),
    )

    assert issues
    assert any(
        issue.code
        == "unsupported_numeric_range"
        for issue in issues
    )


@pytest.mark.parametrize(
    "text",
    (
        "副業を3つ始めてください。",
        "毎週2回、新しい営業をしてください。",
        "顧客を5件獲得してください。",
        "候補を4種類に絞ってください。",
        "毎月3件の案件を取ってください。",
    ),
)
def test_unsupported_numeric_advice_detected(
    valid_ai_reading,
    reading_context,
    consultation_context,
    text,
):
    reading = deepcopy(
        valid_ai_reading
    )

    reading["sections"]["career"]["advice"][
        0
    ] = text

    issues = find_unsupported_numeric_claims(
        reading,
        reading_context=reading_context,
        consultation_context=(
            consultation_context
        ),
    )

    assert issues


def test_unsupported_money_target_detected(
    valid_ai_reading,
    reading_context,
    consultation_context,
):
    reading = deepcopy(
        valid_ai_reading
    )

    reading["sections"]["wealth"]["advice"][
        0
    ] = (
        "まず月30万円を目標にしてください。"
    )

    issues = find_unsupported_numeric_claims(
        reading,
        reading_context=reading_context,
        consultation_context=(
            consultation_context
        ),
    )

    assert any(
        issue.code
        == "unsupported_money_target"
        for issue in issues
    )


def test_unsupported_percent_target_detected(
    valid_ai_reading,
    reading_context,
    consultation_context,
):
    reading = deepcopy(
        valid_ai_reading
    )

    reading["sections"]["wealth"]["advice"][
        0
    ] = (
        "利益率20％を目標にしてください。"
    )

    issues = find_unsupported_numeric_claims(
        reading,
        reading_context=reading_context,
        consultation_context=(
            consultation_context
        ),
    )

    assert any(
        issue.code
        == "unsupported_percent_target"
        for issue in issues
    )


def test_grounded_numeric_count_is_allowed(
    valid_ai_reading,
    reading_context,
    consultation_context,
):
    context = deepcopy(
        reading_context
    )

    context["verified_value"] = {
        "recommended_count": 3,
    }

    reading = deepcopy(
        valid_ai_reading
    )

    reading["sections"]["career"]["advice"][
        0
    ] = (
        "計算済み情報に基づき3つを"
        "確認してください。"
    )

    issues = find_unsupported_numeric_claims(
        reading,
        reading_context=context,
        consultation_context=(
            consultation_context
        ),
    )

    assert issues == ()


def test_numeric_year_in_detail_is_not_flagged(
    valid_ai_reading,
    reading_context,
    consultation_context,
):
    reading = deepcopy(
        valid_ai_reading
    )

    reading["sections"]["current_luck"][
        "detail"
    ] = (
        "2026年の年運は、現在の流れを"
        "慎重に確認したい時期です。"
    )

    issues = find_unsupported_numeric_claims(
        reading,
        reading_context=reading_context,
        consultation_context=(
            consultation_context
        ),
    )

    assert issues == ()


def test_calculated_score_in_evidence_is_not_flagged(
    valid_ai_reading,
    reading_context,
    consultation_context,
):
    reading = deepcopy(
        valid_ai_reading
    )

    reading["sections"]["core_personality"][
        "evidence"
    ][0] = (
        "計算済みの身強身弱スコアは"
        "51.95です。"
    )

    issues = find_unsupported_numeric_claims(
        reading,
        reading_context=reading_context,
        consultation_context=(
            consultation_context
        ),
    )

    assert issues == ()


def test_non_numeric_advice_is_allowed(
    valid_ai_reading,
    reading_context,
    consultation_context,
):
    reading = deepcopy(
        valid_ai_reading
    )

    reading["sections"]["future_flow"][
        "advice"
    ][0] = (
        "チャネルや顧客層を整理し、"
        "再現性の高いものへ"
        "資源を集中させてください。"
    )

    issues = find_unsupported_numeric_claims(
        reading,
        reading_context=reading_context,
        consultation_context=(
            consultation_context
        ),
    )

    assert issues == ()


# ============================================================================
# Disclaimer
# ============================================================================


def test_valid_disclaimer_passes(
    valid_ai_reading,
):
    issues = validate_disclaimer(
        valid_ai_reading
    )

    assert issues == ()


def test_missing_disclaimer_detected(
    valid_ai_reading,
):
    reading = deepcopy(
        valid_ai_reading
    )

    reading.pop("disclaimer")

    issues = validate_disclaimer(
        reading
    )

    assert issues
    assert issues[0].code == "missing_disclaimer"


def test_blank_disclaimer_detected(
    valid_ai_reading,
):
    reading = deepcopy(
        valid_ai_reading
    )

    reading["disclaimer"] = "   "

    issues = validate_disclaimer(
        reading
    )

    assert issues
    assert issues[0].code == "missing_disclaimer"


def test_disclaimer_missing_medical_detected(
    valid_ai_reading,
):
    reading = deepcopy(
        valid_ai_reading
    )

    reading["disclaimer"] = (
        "本鑑定は投資や金融判断を保証する"
        "ものではありません。また将来を"
        "断定するものではありません。"
    )

    issues = validate_disclaimer(
        reading
    )

    assert any(
        issue.code
        == "disclaimer_missing_medical"
        for issue in issues
    )


def test_disclaimer_missing_financial_detected(
    valid_ai_reading,
):
    reading = deepcopy(
        valid_ai_reading
    )

    reading["disclaimer"] = (
        "本鑑定は医学的診断ではありません。"
        "また将来を断定するものでは"
        "ありません。"
    )

    issues = validate_disclaimer(
        reading
    )

    assert any(
        issue.code
        == "disclaimer_missing_financial"
        for issue in issues
    )


def test_disclaimer_missing_future_uncertainty_detected(
    valid_ai_reading,
):
    reading = deepcopy(
        valid_ai_reading
    )

    reading["disclaimer"] = (
        "本鑑定は医学的診断ではありません。"
        "投資や金融判断については"
        "専門家へ相談してください。"
    )

    issues = validate_disclaimer(
        reading
    )

    assert any(
        issue.code
        == "disclaimer_missing_future_uncertainty"
        for issue in issues
    )


# ============================================================================
# Full validation
# ============================================================================


def test_valid_reading_passes_full_validation(
    valid_ai_reading,
    reading_context,
    consultation_context,
):
    report = validate_customer_facing_reading(
        valid_ai_reading,
        reading_context=reading_context,
        consultation_context=(
            consultation_context
        ),
    )

    assert isinstance(
        report,
        ReadingQualityReport,
    )

    assert report.valid is True
    assert report.issue_count == 0
    assert report.issues == ()


def test_invalid_reading_fails_full_validation(
    valid_ai_reading,
    reading_context,
    consultation_context,
):
    reading = deepcopy(
        valid_ai_reading
    )

    reading["sections"]["wealth"]["evidence"][
        0
    ] = (
        "統合運はmixedです。"
    )

    report = validate_customer_facing_reading(
        reading,
        reading_context=reading_context,
        consultation_context=(
            consultation_context
        ),
    )

    assert report.valid is False
    assert report.issue_count >= 1


def test_multiple_problems_are_all_reported(
    valid_ai_reading,
    reading_context,
    consultation_context,
):
    reading = deepcopy(
        valid_ai_reading
    )

    reading["sections"]["wealth"]["evidence"][
        0
    ] = (
        "overall_scoreはmixedです。"
    )

    reading["sections"]["future_flow"][
        "advice"
    ][0] = (
        "顧客層を2〜3種類に"
        "絞ってください。"
    )

    reading["sections"]["advice"]["detail"] = (
        "この方法なら必ず成功します。"
    )

    report = validate_customer_facing_reading(
        reading,
        reading_context=reading_context,
        consultation_context=(
            consultation_context
        ),
    )

    assert report.valid is False

    codes = {
        issue.code
        for issue in report.issues
    }

    assert "internal_label_leak" in codes
    assert "snake_case_leak" in codes
    assert "unsupported_numeric_range" in codes
    assert "guaranteed_success" in codes


# ============================================================================
# Ensure helper
# ============================================================================


def test_ensure_valid_reading_returns_report(
    valid_ai_reading,
    reading_context,
    consultation_context,
):
    report = (
        ensure_customer_facing_reading_quality(
            valid_ai_reading,
            reading_context=reading_context,
            consultation_context=(
                consultation_context
            ),
        )
    )

    assert report.valid is True


def test_ensure_invalid_reading_raises(
    valid_ai_reading,
    reading_context,
    consultation_context,
):
    reading = deepcopy(
        valid_ai_reading
    )

    reading["sections"]["wealth"]["evidence"][
        0
    ] = (
        "統合運はmixedです。"
    )

    with pytest.raises(
        ReadingQualityError
    ):
        ensure_customer_facing_reading_quality(
            reading,
            reading_context=reading_context,
            consultation_context=(
                consultation_context
            ),
        )


def test_quality_error_contains_path(
    valid_ai_reading,
    reading_context,
    consultation_context,
):
    reading = deepcopy(
        valid_ai_reading
    )

    reading["sections"]["wealth"]["evidence"][
        0
    ] = (
        "統合運はmixedです。"
    )

    with pytest.raises(
        ReadingQualityError
    ) as exc_info:
        ensure_customer_facing_reading_quality(
            reading,
            reading_context=reading_context,
            consultation_context=(
                consultation_context
            ),
        )

    message = str(exc_info.value)

    assert (
        "sections.wealth.evidence[0]"
        in message
    )

    assert "mixed" in message


# ============================================================================
# Report model
# ============================================================================


def test_quality_issue_to_dict():
    issue = QualityIssue(
        code="test_code",
        message="テストメッセージ",
        path="summary",
        value="テスト本文",
        matched="test",
    )

    result = issue.to_dict()

    assert result == {
        "code": "test_code",
        "message": "テストメッセージ",
        "path": "summary",
        "value": "テスト本文",
        "matched": "test",
    }


def test_quality_report_issue_count():
    issue = QualityIssue(
        code="test_code",
        message="test",
        path="summary",
        value="test",
    )

    report = ReadingQualityReport(
        valid=False,
        issues=(issue,),
    )

    assert report.issue_count == 1


def test_quality_report_to_dict():
    report = ReadingQualityReport(
        valid=True,
    )

    result = report.to_dict()

    assert result["valid"] is True
    assert result["issue_count"] == 0

    assert (
        result["version"]
        == READING_QUALITY_VERSION
    )

    assert (
        result["method"]
        == READING_QUALITY_METHOD
    )

    assert (
        result["status"]
        == READING_QUALITY_STATUS
    )


def test_quality_report_json_serializable():
    report = ReadingQualityReport(
        valid=True,
    )

    serialized = json.dumps(
        report.to_dict(),
        ensure_ascii=False,
    )

    assert isinstance(serialized, str)


def test_quality_report_to_json():
    report = ReadingQualityReport(
        valid=True,
    )

    serialized = quality_report_to_json(
        report
    )

    parsed = json.loads(serialized)

    assert parsed["valid"] is True
    assert parsed["issue_count"] == 0


def test_quality_report_to_json_rejects_bad_type():
    with pytest.raises(TypeError):
        quality_report_to_json(
            {"valid": True}
        )


# ============================================================================
# Input validation
# ============================================================================


@pytest.mark.parametrize(
    "bad_value",
    (
        None,
        1,
        1.5,
        True,
        [],
        "reading",
    ),
)
def test_validate_rejects_non_mapping_ai_reading(
    bad_value,
):
    with pytest.raises(TypeError):
        validate_customer_facing_reading(
            bad_value
        )


@pytest.mark.parametrize(
    "bad_value",
    (
        1,
        1.5,
        True,
        [],
        "context",
    ),
)
def test_validate_rejects_bad_reading_context(
    valid_ai_reading,
    bad_value,
):
    with pytest.raises(TypeError):
        validate_customer_facing_reading(
            valid_ai_reading,
            reading_context=bad_value,
        )


@pytest.mark.parametrize(
    "bad_value",
    (
        1,
        1.5,
        True,
        [],
        "consultation",
    ),
)
def test_validate_rejects_bad_consultation_context(
    valid_ai_reading,
    bad_value,
):
    with pytest.raises(TypeError):
        validate_customer_facing_reading(
            valid_ai_reading,
            consultation_context=bad_value,
        )


def test_sections_non_mapping_rejected(
    valid_ai_reading,
):
    reading = deepcopy(
        valid_ai_reading
    )

    reading["sections"] = []

    with pytest.raises(TypeError):
        iter_customer_facing_texts(
            reading
        )


# ============================================================================
# Mutation protection
# ============================================================================


def test_validation_does_not_mutate_ai_reading(
    valid_ai_reading,
    reading_context,
    consultation_context,
):
    reading = deepcopy(
        valid_ai_reading
    )

    before = deepcopy(reading)

    validate_customer_facing_reading(
        reading,
        reading_context=reading_context,
        consultation_context=(
            consultation_context
        ),
    )

    assert reading == before


def test_validation_does_not_mutate_reading_context(
    valid_ai_reading,
    reading_context,
    consultation_context,
):
    context = deepcopy(
        reading_context
    )

    before = deepcopy(context)

    validate_customer_facing_reading(
        valid_ai_reading,
        reading_context=context,
        consultation_context=(
            consultation_context
        ),
    )

    assert context == before


def test_validation_does_not_mutate_consultation_context(
    valid_ai_reading,
    reading_context,
    consultation_context,
):
    consultation = deepcopy(
        consultation_context
    )

    before = deepcopy(
        consultation
    )

    validate_customer_facing_reading(
        valid_ai_reading,
        reading_context=reading_context,
        consultation_context=consultation,
    )

    assert consultation == before


# ============================================================================
# Regression: actual live failure patterns
# ============================================================================


def test_live_regression_mixed(
    valid_ai_reading,
    reading_context,
    consultation_context,
):
    reading = deepcopy(
        valid_ai_reading
    )

    reading["sections"]["wealth"]["evidence"] = [
        (
            "統合運は「mixed（混在）」ですが、"
            "偏財の働きは有効と評価されており、"
            "守りの設計で安定化が期待できます。"
        )
    ]

    report = validate_customer_facing_reading(
        reading,
        reading_context=reading_context,
        consultation_context=(
            consultation_context
        ),
    )

    assert report.valid is False

    assert any(
        issue.code == "internal_label_leak"
        and issue.matched == "mixed"
        for issue in report.issues
    )


def test_live_regression_overall(
    valid_ai_reading,
    reading_context,
    consultation_context,
):
    reading = deepcopy(
        valid_ai_reading
    )

    reading["sections"]["current_luck"][
        "evidence"
    ] = [
        (
            "統合運はoverallが混在と評価されつつ、"
            "偏財の有効性が示されており、"
            "活かし方次第で成果に結びやすいと"
            "解釈できます。"
        )
    ]

    report = validate_customer_facing_reading(
        reading,
        reading_context=reading_context,
        consultation_context=(
            consultation_context
        ),
    )

    assert report.valid is False

    assert any(
        issue.code == "internal_label_leak"
        and issue.matched == "overall"
        for issue in report.issues
    )


def test_live_regression_two_to_three_types(
    valid_ai_reading,
    reading_context,
    consultation_context,
):
    reading = deepcopy(
        valid_ai_reading
    )

    reading["sections"]["future_flow"][
        "advice"
    ] = [
        (
            "チャネルや顧客層は2〜3種類に整理し、"
            "最も再現性の高い型へ"
            "資源を集中させてください。"
        )
    ]

    report = validate_customer_facing_reading(
        reading,
        reading_context=reading_context,
        consultation_context=(
            consultation_context
        ),
    )

    assert report.valid is False

    assert any(
        issue.code
        == "unsupported_numeric_range"
        for issue in report.issues
    )


# ============================================================================
# Final gate
# ============================================================================


def test_reading_quality_v1_final_gate(
    valid_ai_reading,
    reading_context,
    consultation_context,
):
    """
    reading_quality_v1 の最終ゲート。

    正常な顧客向け鑑定が通過し、
    代表的な不正出力が検出されることを
    まとめて確認する。
    """

    valid_report = (
        validate_customer_facing_reading(
            valid_ai_reading,
            reading_context=reading_context,
            consultation_context=(
                consultation_context
            ),
        )
    )

    assert valid_report.valid is True
    assert valid_report.issue_count == 0

    invalid = deepcopy(
        valid_ai_reading
    )

    invalid["sections"]["wealth"]["evidence"][
        0
    ] = (
        "統合運はmixedです。"
    )

    invalid["sections"]["current_luck"][
        "detail"
    ] = (
        "overall_scoreを参照すると"
        "現在の流れが分かります。"
    )

    invalid["sections"]["future_flow"][
        "advice"
    ][0] = (
        "顧客層を2〜3種類に"
        "絞ってください。"
    )

    invalid["sections"]["advice"]["detail"] = (
        "この方法なら必ず成功します。"
    )

    invalid_report = (
        validate_customer_facing_reading(
            invalid,
            reading_context=reading_context,
            consultation_context=(
                consultation_context
            ),
        )
    )

    assert invalid_report.valid is False

    codes = {
        issue.code
        for issue in invalid_report.issues
    }

    assert "internal_label_leak" in codes
    assert "snake_case_leak" in codes
    assert "unsupported_numeric_range" in codes
    assert "guaranteed_success" in codes

    assert (
        invalid_report.version
        == "reading_quality_v1"
    )

    assert (
        invalid_report.method
        == "customer_facing_quality_gate_v1"
    )

    assert (
        invalid_report.status
        == "ready_for_customer_facing_validation"
    )