"""
格局判定で使用する特殊ルール群。

pattern_judgment_v2 から利用することを想定した、
副作用のない判定モジュールです。

v1 対象:
- 官殺混雑
- 食神制殺
- 傷官見官
- 財多身弱
- 印綬の財破
- 偏印奪食

重要:
このモジュールは「格局そのもの」を確定しません。
命式中の十神構成と身強身弱情報から、
格局判定に影響する特殊条件を検出して返します。

また、流派差が大きい条件を機械的に断定しないため、
結果には provisional / requires_school_rule を含めます。
"""

from __future__ import annotations

from collections import Counter
from typing import Any


SPECIAL_RULE_METHOD = (
    "pattern_special_rules_v1"
)

SPECIAL_RULE_STATUS = (
    "provisional_pattern_special_rules"
)


TEN_GODS = {
    "比肩",
    "劫財",
    "食神",
    "傷官",
    "偏財",
    "正財",
    "偏官",
    "正官",
    "偏印",
    "印綬",
}


OFFICER_GODS = {
    "正官",
    "偏官",
}

WEALTH_GODS = {
    "正財",
    "偏財",
}

RESOURCE_GODS = {
    "印綬",
    "偏印",
}

OUTPUT_GODS = {
    "食神",
    "傷官",
}


def _is_number(
    value: Any,
) -> bool:
    """
    boolを数値として扱わない数値判定。
    """
    return (
        isinstance(
            value,
            (int, float),
        )
        and not isinstance(
            value,
            bool,
        )
    )


def _safe_number(
    value: Any,
    default: float = 0.0,
) -> float:
    """
    数値ならfloat化し、それ以外はdefault。
    """
    if _is_number(
        value
    ):
        return float(
            value
        )

    return float(
        default
    )


def _normalize_ten_god(
    value: Any,
) -> str | None:
    """
    十神名を検証して返す。
    """
    if (
        isinstance(
            value,
            str,
        )
        and value in TEN_GODS
    ):
        return value

    return None


def _extract_pillars(
    chart_data: dict,
) -> dict:
    """
    chart_data から四柱辞書を取得する。

    calculate_chart() の chart 部分でも、
    calculate_four_pillars() の戻り値でも
    利用できるようにする。
    """
    if not isinstance(
        chart_data,
        dict,
    ):
        raise TypeError(
            "chart_dataはdict型で指定してください。"
        )

    nested_chart = chart_data.get(
        "chart"
    )

    if isinstance(
        nested_chart,
        dict,
    ):
        source = nested_chart
    else:
        source = chart_data

    result = {}

    for position in (
        "year",
        "month",
        "day",
        "hour",
    ):
        pillar = source.get(
            position
        )

        if isinstance(
            pillar,
            dict,
        ):
            result[
                position
            ] = pillar

    return result


def _append_occurrence(
    occurrences: list[dict],
    *,
    ten_god: Any,
    position: str,
    source: str,
    stem: Any = None,
) -> None:
    """
    有効な十神だけを occurrence に追加する。
    """
    normalized = (
        _normalize_ten_god(
            ten_god
        )
    )

    if normalized is None:
        return

    occurrences.append(
        {
            "ten_god": normalized,
            "position": position,
            "source": source,
            "stem": (
                stem
                if isinstance(
                    stem,
                    str,
                )
                else None
            ),
        }
    )


def collect_ten_god_occurrences(
    chart_data: dict,
    *,
    include_hidden_stems: bool = True,
    include_day_stem: bool = False,
) -> list[dict]:
    """
    命式から十神の出現情報を収集する。

    デフォルト:
    - 年月時の天干通変星を含む
    - 四支の蔵干通変星を含む
    - 日干自身は含めない

    同じ十神が複数箇所に存在する場合は
    それぞれ別 occurrence として保持する。
    """
    pillars = _extract_pillars(
        chart_data
    )

    occurrences: list[dict] = []

    for position in (
        "year",
        "month",
        "day",
        "hour",
    ):
        pillar = pillars.get(
            position
        )

        if not isinstance(
            pillar,
            dict,
        ):
            continue

        stem_ten_god = pillar.get(
            "stem_ten_god"
        )

        if (
            position != "day"
            or include_day_stem
        ):
            _append_occurrence(
                occurrences,
                ten_god=stem_ten_god,
                position=position,
                source="heavenly_stem",
                stem=pillar.get(
                    "stem"
                ),
            )

        if not include_hidden_stems:
            continue

        hidden_data = pillar.get(
            "hidden_stem_ten_gods"
        )

        if isinstance(
            hidden_data,
            list,
        ):
            for item in hidden_data:
                if not isinstance(
                    item,
                    dict,
                ):
                    continue

                _append_occurrence(
                    occurrences,
                    ten_god=item.get(
                        "ten_god"
                    ),
                    position=position,
                    source="hidden_stem",
                    stem=item.get(
                        "stem"
                    ),
                )

    return occurrences


def count_ten_gods(
    occurrences: list[dict],
) -> dict[str, int]:
    """
    occurrence一覧から十神数を集計する。
    """
    if not isinstance(
        occurrences,
        list,
    ):
        raise TypeError(
            "occurrencesはlist型で指定してください。"
        )

    counter: Counter[str] = Counter()

    for item in occurrences:
        if not isinstance(
            item,
            dict,
        ):
            raise TypeError(
                "occurrenceはdict型で指定してください。"
            )

        ten_god = _normalize_ten_god(
            item.get(
                "ten_god"
            )
        )

        if ten_god is not None:
            counter[
                ten_god
            ] += 1

    return {
        ten_god: counter.get(
            ten_god,
            0,
        )
        for ten_god in sorted(
            TEN_GODS
        )
    }


def _visible_count(
    occurrences: list[dict],
    ten_god: str,
) -> int:
    """
    天干に透出している指定十神の数。
    """
    return sum(
        1
        for item in occurrences
        if (
            item.get(
                "ten_god"
            )
            == ten_god
            and item.get(
                "source"
            )
            == "heavenly_stem"
        )
    )


def _total_count(
    occurrences: list[dict],
    ten_god: str,
) -> int:
    """
    天干・蔵干を含む指定十神の総数。
    """
    return sum(
        1
        for item in occurrences
        if (
            item.get(
                "ten_god"
            )
            == ten_god
        )
    )


def _has_any(
    occurrences: list[dict],
    ten_gods: set[str],
) -> bool:
    return any(
        item.get(
            "ten_god"
        )
        in ten_gods
        for item in occurrences
    )


def _positions_for(
    occurrences: list[dict],
    ten_god: str,
) -> list[dict]:
    return [
        dict(
            item
        )
        for item in occurrences
        if (
            item.get(
                "ten_god"
            )
            == ten_god
        )
    ]


def _extract_strength_label(
    final_strength_judgment: dict | None,
) -> str | None:
    """
    final_strength_judgment から
    technical_label を取得する。
    """
    if final_strength_judgment is None:
        return None

    if not isinstance(
        final_strength_judgment,
        dict,
    ):
        raise TypeError(
            "final_strength_judgmentは"
            "dict型またはNoneで指定してください。"
        )

    label = final_strength_judgment.get(
        "technical_label"
    )

    if isinstance(
        label,
        str,
    ):
        return label

    return None


def _extract_strength_score(
    final_strength_judgment: dict | None,
) -> float | None:
    if final_strength_judgment is None:
        return None

    if not isinstance(
        final_strength_judgment,
        dict,
    ):
        raise TypeError(
            "final_strength_judgmentは"
            "dict型またはNoneで指定してください。"
        )

    value = final_strength_judgment.get(
        "final_score"
    )

    if _is_number(
        value
    ):
        return float(
            value
        )

    return None


def _is_weak_day_master(
    final_strength_judgment: dict | None,
) -> bool:
    """
    身弱系ラベルを判定。

    ラベル名称が将来多少変わっても
    scoreが低い場合は補助判定する。
    """
    label = _extract_strength_label(
        final_strength_judgment
    )

    if label in {
        "weak",
        "very_weak",
        "extremely_weak",
    }:
        return True

    score = _extract_strength_score(
        final_strength_judgment
    )

    if (
        score is not None
        and score < 45.0
    ):
        return True

    return False


def _make_rule_result(
    *,
    rule: str,
    technical_rule: str,
    detected: bool,
    confidence: str,
    severity: str,
    effect: str,
    score_adjustment: float,
    evidence: dict,
    requires_school_rule: bool = False,
    note: str,
) -> dict:
    """
    特殊ルール共通の戻り値。
    """
    adjustment = max(
        -15.0,
        min(
            15.0,
            _safe_number(
                score_adjustment
            ),
        ),
    )

    return {
        "rule": rule,
        "technical_rule": technical_rule,
        "detected": bool(
            detected
        ),
        "confidence": confidence,
        "severity": severity,
        "effect": effect,
        "score_adjustment": round(
            adjustment,
            2,
        ),
        "requires_school_rule": bool(
            requires_school_rule
        ),
        "evidence": evidence,
        "note": note,
    }


# =========================================================
# 官殺混雑
# =========================================================


def detect_mixed_officer_killing(
    occurrences: list[dict],
) -> dict:
    """
    官殺混雑を検出する。

    v1:
    - 正官と偏官が両方存在 → detected
    - 両方が天干に透出 → confidence high
    - 片方のみ透出 → medium
    - 両方とも蔵干のみ → low

    格局への影響は一律破格とはせず、
    暫定的な減点要因として返す。
    """
    if not isinstance(
        occurrences,
        list,
    ):
        raise TypeError(
            "occurrencesはlist型で指定してください。"
        )

    direct_count = _total_count(
        occurrences,
        "正官",
    )
    seven_count = _total_count(
        occurrences,
        "偏官",
    )

    direct_visible = _visible_count(
        occurrences,
        "正官",
    )
    seven_visible = _visible_count(
        occurrences,
        "偏官",
    )

    detected = (
        direct_count > 0
        and seven_count > 0
    )

    if not detected:
        confidence = "high"
        severity = "none"
        adjustment = 0.0
    elif (
        direct_visible > 0
        and seven_visible > 0
    ):
        confidence = "high"
        severity = "high"
        adjustment = -10.0
    elif (
        direct_visible > 0
        or seven_visible > 0
    ):
        confidence = "medium"
        severity = "medium"
        adjustment = -7.0
    else:
        confidence = "low"
        severity = "low"
        adjustment = -4.0

    return _make_rule_result(
        rule="官殺混雑",
        technical_rule=(
            "mixed_officer_killing"
        ),
        detected=detected,
        confidence=confidence,
        severity=severity,
        effect=(
            "breaking"
            if detected
            else "neutral"
        ),
        score_adjustment=adjustment,
        evidence={
            "direct_officer_count": (
                direct_count
            ),
            "seven_killings_count": (
                seven_count
            ),
            "direct_officer_visible_count": (
                direct_visible
            ),
            "seven_killings_visible_count": (
                seven_visible
            ),
            "direct_officer_positions": (
                _positions_for(
                    occurrences,
                    "正官",
                )
            ),
            "seven_killings_positions": (
                _positions_for(
                    occurrences,
                    "偏官",
                )
            ),
        },
        note=(
            "正官と偏官の併存を検出します。"
            "v1では一律に破格とはせず、"
            "格局判定上の競合要因として扱います。"
        ),
    )


# =========================================================
# 食神制殺
# =========================================================


def detect_food_god_controls_killing(
    occurrences: list[dict],
) -> dict:
    """
    食神制殺の候補を検出する。

    v1:
    - 偏官あり
    - 食神あり
    で候補成立。

    両者が天干に見える場合を強く評価する。
    """
    if not isinstance(
        occurrences,
        list,
    ):
        raise TypeError(
            "occurrencesはlist型で指定してください。"
        )

    killing_count = _total_count(
        occurrences,
        "偏官",
    )
    food_count = _total_count(
        occurrences,
        "食神",
    )

    killing_visible = _visible_count(
        occurrences,
        "偏官",
    )
    food_visible = _visible_count(
        occurrences,
        "食神",
    )

    detected = (
        killing_count > 0
        and food_count > 0
    )

    if not detected:
        confidence = "high"
        severity = "none"
        adjustment = 0.0
    elif (
        killing_visible > 0
        and food_visible > 0
    ):
        confidence = "high"
        severity = "high"
        adjustment = 10.0
    elif (
        killing_visible > 0
        or food_visible > 0
    ):
        confidence = "medium"
        severity = "medium"
        adjustment = 7.0
    else:
        confidence = "low"
        severity = "low"
        adjustment = 4.0

    return _make_rule_result(
        rule="食神制殺",
        technical_rule=(
            "food_god_controls_killing"
        ),
        detected=detected,
        confidence=confidence,
        severity=severity,
        effect=(
            "rescue"
            if detected
            else "neutral"
        ),
        score_adjustment=adjustment,
        evidence={
            "seven_killings_count": (
                killing_count
            ),
            "food_god_count": (
                food_count
            ),
            "seven_killings_visible_count": (
                killing_visible
            ),
            "food_god_visible_count": (
                food_visible
            ),
            "seven_killings_positions": (
                _positions_for(
                    occurrences,
                    "偏官",
                )
            ),
            "food_god_positions": (
                _positions_for(
                    occurrences,
                    "食神",
                )
            ),
        },
        note=(
            "偏官と食神の併存を"
            "食神制殺候補として検出します。"
            "制化の強弱・距離・根・月令は"
            "後続版で精密化します。"
        ),
    )


# =========================================================
# 傷官見官
# =========================================================


def detect_hurting_officer_meets_officer(
    occurrences: list[dict],
) -> dict:
    """
    傷官見官を検出する。

    v1:
    - 傷官あり
    - 正官あり
    で候補成立。
    """
    if not isinstance(
        occurrences,
        list,
    ):
        raise TypeError(
            "occurrencesはlist型で指定してください。"
        )

    hurting_count = _total_count(
        occurrences,
        "傷官",
    )
    officer_count = _total_count(
        occurrences,
        "正官",
    )

    hurting_visible = _visible_count(
        occurrences,
        "傷官",
    )
    officer_visible = _visible_count(
        occurrences,
        "正官",
    )

    detected = (
        hurting_count > 0
        and officer_count > 0
    )

    if not detected:
        confidence = "high"
        severity = "none"
        adjustment = 0.0
    elif (
        hurting_visible > 0
        and officer_visible > 0
    ):
        confidence = "high"
        severity = "high"
        adjustment = -10.0
    elif (
        hurting_visible > 0
        or officer_visible > 0
    ):
        confidence = "medium"
        severity = "medium"
        adjustment = -7.0
    else:
        confidence = "low"
        severity = "low"
        adjustment = -4.0

    return _make_rule_result(
        rule="傷官見官",
        technical_rule=(
            "hurting_officer_meets_officer"
        ),
        detected=detected,
        confidence=confidence,
        severity=severity,
        effect=(
            "breaking"
            if detected
            else "neutral"
        ),
        score_adjustment=adjustment,
        evidence={
            "hurting_officer_count": (
                hurting_count
            ),
            "direct_officer_count": (
                officer_count
            ),
            "hurting_officer_visible_count": (
                hurting_visible
            ),
            "direct_officer_visible_count": (
                officer_visible
            ),
            "hurting_officer_positions": (
                _positions_for(
                    occurrences,
                    "傷官",
                )
            ),
            "direct_officer_positions": (
                _positions_for(
                    occurrences,
                    "正官",
                )
            ),
        },
        note=(
            "傷官と正官の併存を検出します。"
            "印による制傷などの救済条件は"
            "後続版でさらに精密化します。"
        ),
    )


# =========================================================
# 財多身弱
# =========================================================


def detect_wealth_many_body_weak(
    occurrences: list[dict],
    final_strength_judgment: dict | None,
) -> dict:
    """
    財多身弱候補を検出する。

    v1:
    - 財星が複数
    - 日主が身弱系
    で候補成立。

    財の「多」の定義は流派差があるため、
    requires_school_rule=True とする。
    """
    if not isinstance(
        occurrences,
        list,
    ):
        raise TypeError(
            "occurrencesはlist型で指定してください。"
        )

    direct_wealth = _total_count(
        occurrences,
        "正財",
    )
    indirect_wealth = _total_count(
        occurrences,
        "偏財",
    )

    wealth_count = (
        direct_wealth
        + indirect_wealth
    )

    is_weak = _is_weak_day_master(
        final_strength_judgment
    )

    detected = (
        wealth_count >= 2
        and is_weak
    )

    return _make_rule_result(
        rule="財多身弱",
        technical_rule=(
            "wealth_many_body_weak"
        ),
        detected=detected,
        confidence=(
            "medium"
            if detected
            else "high"
        ),
        severity=(
            "medium"
            if detected
            else "none"
        ),
        effect=(
            "breaking"
            if detected
            else "neutral"
        ),
        score_adjustment=(
            -8.0
            if detected
            else 0.0
        ),
        evidence={
            "direct_wealth_count": (
                direct_wealth
            ),
            "indirect_wealth_count": (
                indirect_wealth
            ),
            "wealth_count": wealth_count,
            "is_weak_day_master": (
                is_weak
            ),
            "strength_label": (
                _extract_strength_label(
                    final_strength_judgment
                )
            ),
            "strength_score": (
                _extract_strength_score(
                    final_strength_judgment
                )
            ),
        },
        requires_school_rule=detected,
        note=(
            "財星の多さと身弱を組み合わせた"
            "暫定判定です。"
            "財星の力量・月令・通根まで含む"
            "厳密な財多判定は後続版で行います。"
        ),
    )


# =========================================================
# 印綬の財破
# =========================================================


def detect_wealth_breaks_resource(
    occurrences: list[dict],
) -> dict:
    """
    印綬の財破候補を検出する。

    v1:
    - 印綬あり
    - 正財または偏財あり
    で候補成立。

    財が印を実際に破れる力量かどうかは
    後続版で精密化する。
    """
    if not isinstance(
        occurrences,
        list,
    ):
        raise TypeError(
            "occurrencesはlist型で指定してください。"
        )

    resource_count = _total_count(
        occurrences,
        "印綬",
    )

    direct_wealth = _total_count(
        occurrences,
        "正財",
    )

    indirect_wealth = _total_count(
        occurrences,
        "偏財",
    )

    wealth_count = (
        direct_wealth
        + indirect_wealth
    )

    resource_visible = _visible_count(
        occurrences,
        "印綬",
    )

    wealth_visible = (
        _visible_count(
            occurrences,
            "正財",
        )
        + _visible_count(
            occurrences,
            "偏財",
        )
    )

    detected = (
        resource_count > 0
        and wealth_count > 0
    )

    if not detected:
        confidence = "high"
        severity = "none"
        adjustment = 0.0
    elif (
        resource_visible > 0
        and wealth_visible > 0
    ):
        confidence = "high"
        severity = "high"
        adjustment = -9.0
    elif (
        resource_visible > 0
        or wealth_visible > 0
    ):
        confidence = "medium"
        severity = "medium"
        adjustment = -6.0
    else:
        confidence = "low"
        severity = "low"
        adjustment = -3.0

    return _make_rule_result(
        rule="印綬の財破",
        technical_rule=(
            "wealth_breaks_resource"
        ),
        detected=detected,
        confidence=confidence,
        severity=severity,
        effect=(
            "breaking"
            if detected
            else "neutral"
        ),
        score_adjustment=adjustment,
        evidence={
            "proper_resource_count": (
                resource_count
            ),
            "direct_wealth_count": (
                direct_wealth
            ),
            "indirect_wealth_count": (
                indirect_wealth
            ),
            "wealth_count": wealth_count,
            "proper_resource_visible_count": (
                resource_visible
            ),
            "wealth_visible_count": (
                wealth_visible
            ),
        },
        note=(
            "印綬と財星の併存を"
            "財破印候補として検出します。"
            "実際の破格成立には力量比較が必要です。"
        ),
    )


# =========================================================
# 偏印奪食
# =========================================================


def detect_indirect_resource_robs_food(
    occurrences: list[dict],
) -> dict:
    """
    偏印奪食候補を検出する。

    v1:
    - 偏印あり
    - 食神あり
    で候補成立。
    """
    if not isinstance(
        occurrences,
        list,
    ):
        raise TypeError(
            "occurrencesはlist型で指定してください。"
        )

    indirect_resource = _total_count(
        occurrences,
        "偏印",
    )

    food_count = _total_count(
        occurrences,
        "食神",
    )

    resource_visible = _visible_count(
        occurrences,
        "偏印",
    )

    food_visible = _visible_count(
        occurrences,
        "食神",
    )

    detected = (
        indirect_resource > 0
        and food_count > 0
    )

    if not detected:
        confidence = "high"
        severity = "none"
        adjustment = 0.0
    elif (
        resource_visible > 0
        and food_visible > 0
    ):
        confidence = "high"
        severity = "high"
        adjustment = -9.0
    elif (
        resource_visible > 0
        or food_visible > 0
    ):
        confidence = "medium"
        severity = "medium"
        adjustment = -6.0
    else:
        confidence = "low"
        severity = "low"
        adjustment = -3.0

    return _make_rule_result(
        rule="偏印奪食",
        technical_rule=(
            "indirect_resource_robs_food"
        ),
        detected=detected,
        confidence=confidence,
        severity=severity,
        effect=(
            "breaking"
            if detected
            else "neutral"
        ),
        score_adjustment=adjustment,
        evidence={
            "indirect_resource_count": (
                indirect_resource
            ),
            "food_god_count": (
                food_count
            ),
            "indirect_resource_visible_count": (
                resource_visible
            ),
            "food_god_visible_count": (
                food_visible
            ),
        },
        note=(
            "偏印と食神の併存を"
            "偏印奪食候補として検出します。"
            "力量・位置・救済条件は"
            "後続版で精密化します。"
        ),
    )


# =========================================================
# Aggregate evaluation
# =========================================================


def evaluate_pattern_special_rules(
    chart_data: dict,
    final_strength_judgment: dict | None = None,
) -> dict:
    """
    格局特殊ルールを一括評価する。

    戻り値は pattern_judgment_v2 から
    そのまま evidence として利用できる構造。
    """
    if not isinstance(
        chart_data,
        dict,
    ):
        raise TypeError(
            "chart_dataはdict型で指定してください。"
        )

    if (
        final_strength_judgment is not None
        and not isinstance(
            final_strength_judgment,
            dict,
        )
    ):
        raise TypeError(
            "final_strength_judgmentは"
            "dict型またはNoneで指定してください。"
        )

    occurrences = (
        collect_ten_god_occurrences(
            chart_data
        )
    )

    counts = count_ten_gods(
        occurrences
    )

    rules = [
        detect_mixed_officer_killing(
            occurrences
        ),
        detect_food_god_controls_killing(
            occurrences
        ),
        detect_hurting_officer_meets_officer(
            occurrences
        ),
        detect_wealth_many_body_weak(
            occurrences,
            final_strength_judgment,
        ),
        detect_wealth_breaks_resource(
            occurrences
        ),
        detect_indirect_resource_robs_food(
            occurrences
        ),
    ]

    detected_rules = [
        rule
        for rule in rules
        if rule[
            "detected"
        ]
    ]

    breaking_rules = [
        rule
        for rule in detected_rules
        if rule[
            "effect"
        ]
        == "breaking"
    ]

    rescue_rules = [
        rule
        for rule in detected_rules
        if rule[
            "effect"
        ]
        == "rescue"
    ]

    school_rule_items = [
        rule
        for rule in detected_rules
        if rule[
            "requires_school_rule"
        ]
    ]

    total_adjustment = round(
        sum(
            _safe_number(
                rule[
                    "score_adjustment"
                ]
            )
            for rule in detected_rules
        ),
        2,
    )

    # 特殊ルールだけで格局全体を過剰に動かさない。
    total_adjustment = max(
        -20.0,
        min(
            20.0,
            total_adjustment,
        ),
    )

    if not detected_rules:
        overall_status = (
            "no_special_rule_detected"
        )
    elif (
        breaking_rules
        and rescue_rules
    ):
        overall_status = (
            "mixed_special_rules"
        )
    elif breaking_rules:
        overall_status = (
            "breaking_rules_detected"
        )
    else:
        overall_status = (
            "rescue_rules_detected"
        )

    return {
        "has_special_rule": bool(
            detected_rules
        ),
        "rule_count": len(
            rules
        ),
        "detected_rule_count": len(
            detected_rules
        ),
        "breaking_rule_count": len(
            breaking_rules
        ),
        "rescue_rule_count": len(
            rescue_rules
        ),
        "school_rule_count": len(
            school_rule_items
        ),
        "overall_status": (
            overall_status
        ),
        "total_score_adjustment": round(
            total_adjustment,
            2,
        ),
        "rules": rules,
        "detected_rules": (
            detected_rules
        ),
        "breaking_rules": (
            breaking_rules
        ),
        "rescue_rules": (
            rescue_rules
        ),
        "school_rule_items": (
            school_rule_items
        ),
        "ten_god_counts": counts,
        "ten_god_occurrences": (
            occurrences
        ),
        "strength_evidence": {
            "technical_label": (
                _extract_strength_label(
                    final_strength_judgment
                )
            ),
            "final_score": (
                _extract_strength_score(
                    final_strength_judgment
                )
            ),
            "is_weak_day_master": (
                _is_weak_day_master(
                    final_strength_judgment
                )
            ),
        },
        "method": SPECIAL_RULE_METHOD,
        "status": SPECIAL_RULE_STATUS,
        "notes": [
            (
                "特殊ルールv1は十神の併存・透干と"
                "身強身弱を中心にした暫定判定です。"
            ),
            (
                "月令・通根・距離・力量・合化・"
                "救済条件の完全評価は後続版で"
                "段階的に追加します。"
            ),
            (
                "検出された特殊ルールだけで"
                "格局を自動確定しません。"
            ),
        ],
    }


__all__ = [
    "SPECIAL_RULE_METHOD",
    "SPECIAL_RULE_STATUS",
    "TEN_GODS",
    "OFFICER_GODS",
    "WEALTH_GODS",
    "RESOURCE_GODS",
    "OUTPUT_GODS",
    "collect_ten_god_occurrences",
    "count_ten_gods",
    "detect_mixed_officer_killing",
    "detect_food_god_controls_killing",
    "detect_hurting_officer_meets_officer",
    "detect_wealth_many_body_weak",
    "detect_wealth_breaks_resource",
    "detect_indirect_resource_robs_food",
    "evaluate_pattern_special_rules",
]
