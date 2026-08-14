"""
tests/test_reading_quality_customer_value.py

四柱推命鑑定書・顧客価値品質ゲート（non-live）

目的:
- 同じ助言の章横断反復を抑える
- 五行を毎回同じ現代語へ固定変換しない
- 相談テーマの章を十分に深くする
- 総合鑑定を各章の単なる繰り返しにしない
- 健康で占術から具体的医療・生活習慣へ飛躍しすぎない
- evidence を「計算済み事実 → 解釈」の流れにする

OpenAI APIは呼ばない。
Playwrightも起動しない。
"""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

import pytest

from engine.chart import calculate_chart
from engine.reading_context import build_reading_context
from engine.reading_generator import build_generation_payload
from engine.reading_prompt import build_section_prompt


ALL_SECTIONS = (
    "core_personality",
    "career",
    "wealth",
    "relationships",
    "health",
    "current_luck",
    "future_flow",
    "advice",
)

CUSTOMER_VALUE_VERSION = "reading_quality_customer_value_v1"

REPEATED_CONCEPTS = (
    "見える化",
    "可視化",
    "仕組み化",
    "標準化",
    "再現性",
    "情報収集",
    "人脈",
    "学習",
    "段階的",
    "チェックリスト",
)

ELEMENT_TRANSLATIONS = {
    "金": ("仕組み化", "ルール", "品質", "精度", "基準"),
    "水": ("情報", "情報収集", "ネットワーク", "人脈"),
    "木": ("学習", "企画", "成長"),
    "土": ("安定", "運用", "段取り", "標準化"),
    "火": ("表現", "行動力", "自己主張", "勢い"),
}

HEALTH_OVERREACH_TERMS = (
    "夜更かし",
    "有酸素",
    "換気",
    "深呼吸",
    "サプリ",
    "服薬",
    "血圧",
    "血糖",
    "治療",
)


@pytest.fixture
def verified_request():
    return SimpleNamespace(
        birth_date="1985-07-17",
        birth_time="21:50",
        birth_place="石川県",
        gender="female",
    )


@pytest.fixture
def reading_context(verified_request):
    chart = calculate_chart(verified_request)
    return build_reading_context(chart)


@pytest.fixture
def generation_payload(reading_context):
    return build_generation_payload(
        reading_context,
        model="gpt-5",
        sections=ALL_SECTIONS,
        output_format="json",
        max_output_tokens=8000,
        reasoning_effort="minimal",
        store=False,
    )


def _system_prompt(payload: Mapping[str, Any]) -> str:
    value = payload["payload"]["instructions"]
    assert isinstance(value, str)
    assert value.strip()
    return value


def _user_prompt(payload: Mapping[str, Any]) -> str:
    value = payload["payload"]["input"][0]["content"]
    assert isinstance(value, str)
    assert value.strip()
    return value


def _section_texts(
    ai_reading: Mapping[str, Any],
) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}

    sections = ai_reading.get("sections", {})
    if not isinstance(sections, Mapping):
        return result

    for section_name, section in sections.items():
        if not isinstance(section, Mapping):
            continue

        texts: list[str] = []

        for field in ("summary", "detail"):
            value = section.get(field)
            if isinstance(value, str) and value.strip():
                texts.append(value.strip())

        for field in ("evidence", "advice"):
            value = section.get(field, [])
            if (
                isinstance(value, Sequence)
                and not isinstance(value, (str, bytes, bytearray))
            ):
                texts.extend(
                    item.strip()
                    for item in value
                    if isinstance(item, str) and item.strip()
                )

        result[str(section_name)] = texts

    return result


def find_overrepeated_concepts(
    ai_reading: Mapping[str, Any],
    *,
    max_sections: int = 3,
) -> dict[str, int]:
    sections = _section_texts(ai_reading)
    counter: Counter[str] = Counter()

    for texts in sections.values():
        combined = " ".join(texts)
        for concept in REPEATED_CONCEPTS:
            if concept in combined:
                counter[concept] += 1

    return {
        key: value
        for key, value in counter.items()
        if value > max_sections
    }


def find_fixed_element_translation_overuse(
    ai_reading: Mapping[str, Any],
    *,
    max_sections: int = 3,
) -> dict[str, dict[str, int]]:
    sections = _section_texts(ai_reading)
    result: dict[str, dict[str, int]] = {}

    for element, translations in ELEMENT_TRANSLATIONS.items():
        counts: Counter[str] = Counter()

        for texts in sections.values():
            combined = " ".join(texts)

            if element not in combined:
                continue

            for word in translations:
                if word in combined:
                    counts[word] += 1

        over = {
            word: count
            for word, count in counts.items()
            if count > max_sections
        }

        if over:
            result[element] = over

    return result


def find_health_overreach_terms(
    ai_reading: Mapping[str, Any],
) -> tuple[str, ...]:
    sections = ai_reading.get("sections", {})
    if not isinstance(sections, Mapping):
        return ()

    health = sections.get("health", {})
    if not isinstance(health, Mapping):
        return ()

    texts: list[str] = []

    for field in ("summary", "detail"):
        value = health.get(field)
        if isinstance(value, str):
            texts.append(value)

    for field in ("evidence", "advice"):
        value = health.get(field, [])
        if (
            isinstance(value, Sequence)
            and not isinstance(value, (str, bytes, bytearray))
        ):
            texts.extend(
                item
                for item in value
                if isinstance(item, str)
            )

    combined = " ".join(texts)

    return tuple(
        term
        for term in HEALTH_OVERREACH_TERMS
        if term in combined
    )


def evidence_has_fact_to_meaning_flow(text: str) -> bool:
    if not isinstance(text, str) or not text.strip():
        return False

    fact_markers = (
        "日主",
        "格局",
        "身強",
        "身弱",
        "五行",
        "用神",
        "大運",
        "年運",
        "歳運",
        "通変星",
        "命式",
    )

    meaning_markers = (
        "ため",
        "ので",
        "から",
        "と読み",
        "と解釈",
        "傾向",
        "表れ",
        "つなが",
        "示され",
    )

    return (
        any(marker in text for marker in fact_markers)
        and any(marker in text for marker in meaning_markers)
    )


def section_length(
    ai_reading: Mapping[str, Any],
    section_name: str,
) -> int:
    texts = _section_texts(ai_reading).get(section_name, [])
    return sum(len(text) for text in texts)


@pytest.fixture
def clean_ai_reading():
    return {
        "summary": (
            "現職での役割調整と外部市場の確認を並行し、"
            "条件が整った段階で次の選択肢を判断する流れです。"
        ),
        "sections": {
            "core_personality": {
                "summary": "丁の性質から、繊細な観察と表現力を活かしやすい傾向です。",
                "detail": "食神格のため、考えたことを人に伝わる形へ整える力が出やすいです。",
                "evidence": [
                    "日主が丁であるため、周囲への細かな配慮として表れやすいと読みます。",
                    "格局が食神格であるため、発想を外へ表現する力につながりやすいと解釈します。",
                ],
                "advice": ["強みが発揮された場面を振り返り、共通点を言葉にしましょう。"],
            },
            "career": {
                "summary": "現職継続と転職準備を並行し、役割と条件を比較する進め方が現実的です。",
                "detail": (
                    "食神格の表現力を活かせる役割を現職で試しつつ、"
                    "外部求人との違いも確認すると判断材料が増えます。"
                ),
                "evidence": [
                    "格局が食神格であるため、企画や提案で強みが表れやすいと読みます。",
                    "現在の大運に水の働きがあるため、外部情報へ触れることが判断材料につながると解釈します。",
                ],
                "advice": [
                    "現職で変えられる条件と、転職でしか変えにくい条件を分けて比較しましょう。",
                    "収入・仕事内容・裁量・生活への影響を現実データで確認しましょう。",
                ],
            },
            "wealth": {
                "summary": "収入面では、短期の勢いより継続できる収支構造の確認が重要です。",
                "detail": "転職や副業では、占術だけでなく手取りや固定費も一緒に確認してください。",
                "evidence": [
                    "現在の大運と年運に異なる働きがあるため、機会と慎重さが併存する流れと読みます。"
                ],
                "advice": ["選択肢ごとの収支を比較し、生活を維持できる条件を確認しましょう。"],
            },
            "relationships": {
                "summary": "人間関係では、相手に合わせすぎず自分の意図も伝えることが大切です。",
                "detail": "中和の判定から、状況へ適応しやすい一方で周囲の影響にも注意が必要です。",
                "evidence": [
                    "身強身弱が中和であるため、状況に合わせる柔軟性として表れやすいと読みます。"
                ],
                "advice": ["重要な場面では、自分の希望も言葉にして共有しましょう。"],
            },
            "health": {
                "summary": "健康面は五行上の偏りを生活全体を見直す参考程度に捉えてください。",
                "detail": "これは医学的診断ではなく、実際の体調は医療専門家の判断を優先してください。",
                "evidence": [
                    "五行バランスに偏りがあるため、生活全体のバランスを見る参考として読みます。"
                ],
                "advice": ["体調に気になる点がある場合は医療専門家へ相談してください。"],
            },
            "current_luck": {
                "summary": "現在は動きやすさと慎重さが同時に求められる流れです。",
                "detail": "大運と年運の働きが一方向ではないため、勢いだけで結論を出さない方が安定します。",
                "evidence": [
                    "現在の大運と年運に異なる五行が働くため、追い風と注意点が併存すると読みます。"
                ],
                "advice": ["重要な判断では情報を確認してから決めましょう。"],
            },
            "future_flow": {
                "summary": "今後は経験を整理し、自分なりの専門性へまとめることがテーマです。",
                "detail": "次の大運では現在とは異なる働きが加わるため、今の経験を次の役割へつなげる準備が重要です。",
                "evidence": [
                    "次期大運の干支構成が変化するため、現在の経験を整理して次へつなげる時期と読みます。"
                ],
                "advice": ["今後も使える経験と、今の環境だけで通用する経験を分けて整理しましょう。"],
            },
            "advice": {
                "summary": "転職か継続かを今すぐ一択にせず、比較材料を増やして判断するのが現実的です。",
                "detail": "命式上の傾向と現実条件を分け、現職改善と外部確認を並行してください。",
                "evidence": [
                    "食神格と現在の運勢を合わせると、価値を外へ示しながら選択肢を広げる方向が活かしやすいと読みます。"
                ],
                "advice": ["現職に残る場合と転職する場合のメリット・負担を比較して決めましょう。"],
            },
        },
        "disclaimer": (
            "本鑑定は医学的診断や投資判断を行うものではなく、"
            "将来の結果を保証するものでもありません。"
        ),
    }


# ---------------------------------------------------------------------------
# Prompt contract
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("phrase", ("繰り返", "重複"))
def test_system_prompt_requires_repetition_control(
    generation_payload,
    phrase,
):
    assert phrase in _system_prompt(generation_payload)


@pytest.mark.parametrize("phrase", ("同じ五行", "各セクション", "文脈"))
def test_system_prompt_keeps_contextual_element_translation(
    generation_payload,
    phrase,
):
    assert phrase in _system_prompt(generation_payload)


@pytest.mark.parametrize("phrase", ("固定", "機械的"))
def test_system_prompt_rejects_fixed_element_translation(
    generation_payload,
    phrase,
):
    assert phrase in _system_prompt(generation_payload)


@pytest.mark.parametrize("phrase", ("相談", "直接", "選択肢", "現実的"))
def test_system_prompt_requires_direct_consultation_answer(
    generation_payload,
    phrase,
):
    assert phrase in _system_prompt(generation_payload)


def test_career_prompt_requires_multiple_options(reading_context):
    prompt = build_section_prompt(
        reading_context,
        "career",
        output_format="json",
    )

    assert "選択肢" in prompt
    assert ("複数" in prompt or "一択" in prompt)


def test_career_prompt_requires_decision_criteria(reading_context):
    prompt = build_section_prompt(
        reading_context,
        "career",
        output_format="json",
    )

    assert (
        "判断基準" in prompt
        or "条件" in prompt
        or "比較" in prompt
    )


@pytest.mark.parametrize(
    "phrase",
    ("医学的診断", "推測", "入力"),
)
def test_health_prompt_keeps_medical_boundary(
    reading_context,
    phrase,
):
    prompt = build_section_prompt(
        reading_context,
        "health",
        output_format="json",
    )

    assert phrase in prompt


@pytest.mark.parametrize(
    "phrase",
    ("夜更かし", "有酸素", "換気", "深呼吸"),
)
def test_health_prompt_does_not_prescribe_specific_habits(
    reading_context,
    phrase,
):
    prompt = build_section_prompt(
        reading_context,
        "health",
        output_format="json",
    )

    assert phrase not in prompt


def test_system_prompt_requires_fact_to_meaning_evidence(
    generation_payload,
):
    prompt = _system_prompt(generation_payload)

    assert "計算済み事実" in prompt
    assert ("意味" in prompt or "解釈" in prompt)


def test_system_prompt_requires_section_role_separation(
    generation_payload,
):
    prompt = _system_prompt(generation_payload)

    assert (
        "セクションごと" in prompt
        or "各セクション" in prompt
        or "役割" in prompt
    )

    assert (
        "重複" in prompt
        or "繰り返" in prompt
        or "同じ説明" in prompt
    )


# ---------------------------------------------------------------------------
# Deterministic helpers
# ---------------------------------------------------------------------------


def test_clean_reading_has_no_overrepetition(clean_ai_reading):
    assert (
        find_overrepeated_concepts(
            clean_ai_reading
        )
        == {}
    )


def test_detects_repeated_advice_across_many_sections(
    clean_ai_reading,
):
    reading = deepcopy(clean_ai_reading)

    for section in (
        "career",
        "wealth",
        "current_luck",
        "future_flow",
        "advice",
    ):
        reading["sections"][section]["advice"] = [
            "成果の見える化を進めましょう。"
        ]

    result = find_overrepeated_concepts(reading)

    assert result["見える化"] == 5


def test_clean_reading_has_no_fixed_element_overuse(
    clean_ai_reading,
):
    assert (
        find_fixed_element_translation_overuse(
            clean_ai_reading
        )
        == {}
    )


def test_detects_fixed_element_translation_overuse(
    clean_ai_reading,
):
    reading = deepcopy(clean_ai_reading)

    for section in (
        "career",
        "wealth",
        "relationships",
        "current_luck",
        "future_flow",
    ):
        reading["sections"][section]["detail"] = (
            "用神の金は仕組み化を意味し、"
            "仕事では仕組み化を進めるとよいでしょう。"
        )

    result = find_fixed_element_translation_overuse(reading)

    assert result["金"]["仕組み化"] == 5


@pytest.mark.parametrize(
    "term",
    ("夜更かし", "有酸素", "換気", "深呼吸"),
)
def test_detects_health_overreach_term(
    clean_ai_reading,
    term,
):
    reading = deepcopy(clean_ai_reading)

    reading["sections"]["health"]["advice"] = [
        f"{term}を意識してください。"
    ]

    assert term in find_health_overreach_terms(reading)


@pytest.mark.parametrize(
    "text",
    (
        "日主が丁であるため、細かな配慮として表れやすいと読みます。",
        "格局が食神格であるため、表現力を活かしやすい傾向と解釈します。",
        "現在の大運に水の働きがあるため、外部情報を取り入れやすい流れと読みます。",
    ),
)
def test_good_evidence_has_fact_to_meaning_flow(text):
    assert evidence_has_fact_to_meaning_flow(text) is True


@pytest.mark.parametrize(
    "text",
    (
        "日主は丁です。",
        "食神格です。",
        "水が強いです。",
        "仕組み化するとよいでしょう。",
        "",
    ),
)
def test_shallow_evidence_is_rejected(text):
    assert evidence_has_fact_to_meaning_flow(text) is False


def test_career_section_is_not_thinner_than_unrelated_sections(
    clean_ai_reading,
):
    career = section_length(
        clean_ai_reading,
        "career",
    )

    relationships = section_length(
        clean_ai_reading,
        "relationships",
    )

    health = section_length(
        clean_ai_reading,
        "health",
    )

    assert career >= max(
        relationships,
        health,
    )


# ---------------------------------------------------------------------------
# LIVE-PDF style regressions
# ---------------------------------------------------------------------------


def test_live_style_repetition_is_detected(clean_ai_reading):
    reading = deepcopy(clean_ai_reading)

    for section in (
        "core_personality",
        "career",
        "wealth",
        "current_luck",
        "future_flow",
        "advice",
    ):
        reading["sections"][section]["detail"] = (
            "成果の見える化と仕組み化を進め、"
            "再現性を高めることが重要です。"
        )

    result = find_overrepeated_concepts(reading)

    assert result["見える化"] == 6
    assert result["仕組み化"] == 6
    assert result["再現性"] == 6


def test_live_style_fixed_five_element_translation_is_detected(
    clean_ai_reading,
):
    reading = deepcopy(clean_ai_reading)

    template = (
        "金は仕組み化、水は情報収集、"
        "木は学習、土は安定運用として活かします。"
    )

    for section in (
        "career",
        "wealth",
        "relationships",
        "current_luck",
        "future_flow",
    ):
        reading["sections"][section]["detail"] = template

    result = find_fixed_element_translation_overuse(reading)

    assert result["金"]["仕組み化"] == 5
    assert result["水"]["情報収集"] == 5
    assert result["木"]["学習"] == 5
    assert result["土"]["安定"] == 5


def test_live_style_health_overreach_is_detected(
    clean_ai_reading,
):
    reading = deepcopy(clean_ai_reading)

    reading["sections"]["health"]["detail"] = (
        "水が強めなので夜更かしを避け、"
        "換気と軽い有酸素、深呼吸を意識してください。"
    )

    result = set(
        find_health_overreach_terms(reading)
    )

    assert {
        "夜更かし",
        "換気",
        "有酸素",
        "深呼吸",
    }.issubset(result)


# ---------------------------------------------------------------------------
# Final gate
# ---------------------------------------------------------------------------


def test_reading_quality_customer_value_v1_final_gate(
    generation_payload,
    reading_context,
    clean_ai_reading,
):
    system_prompt = _system_prompt(
        generation_payload
    )

    assert "相談" in system_prompt
    assert "計算済み事実" in system_prompt
    assert "同じ五行" in system_prompt
    assert "各セクション" in system_prompt

    career_prompt = build_section_prompt(
        reading_context,
        "career",
        output_format="json",
    )

    assert "選択肢" in career_prompt

    health_prompt = build_section_prompt(
        reading_context,
        "health",
        output_format="json",
    )

    assert "医学的診断" in health_prompt

    assert (
        find_overrepeated_concepts(
            clean_ai_reading
        )
        == {}
    )

    assert (
        find_fixed_element_translation_overuse(
            clean_ai_reading
        )
        == {}
    )

    assert (
        section_length(
            clean_ai_reading,
            "career",
        )
        >= section_length(
            clean_ai_reading,
            "health",
        )
    )

    assert (
        CUSTOMER_VALUE_VERSION
        == "reading_quality_customer_value_v1"
    )
