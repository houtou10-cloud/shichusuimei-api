"""
engine/reading_context.py

AI鑑定文生成用コンテキスト整形モジュール。

目的
----
calculate_chart() が返す詳細な計算結果を、
AI鑑定文生成に必要な情報だけへ整理する。

このモジュールは占術計算を行わない。
既存エンジンの計算結果を読み取り、
文章生成層へ渡しやすい安定した構造へ変換する。

設計方針
--------
1. 元の chart_result を変更しない。
2. 占術上の再計算をしない。
3. evidence / notes の巨大な入れ子をそのままAIへ渡さない。
4. AIに必要な主要情報だけを抽出する。
5. 欠損値を安全に扱う。
6. v1.0以降の拡張を想定し、セクション単位で分離する。
7. AIが「事実」と「解釈」を混同しない構造にする。

主な出力
--------
{
    "schema_version": "reading_context_v1",
    "subject": {...},
    "natal_chart": {...},
    "day_master": {...},
    "five_elements": {...},
    "strength": {...},
    "pattern": {...},
    "useful_gods": {...},
    "luck": {
        "luck_pillars": {...},
        "current_luck": {...},
        "annual_luck": {...},
        "integrated_luck": {...},
    },
    "reading_sections": {...},
    "source_metadata": {...},
}

注意
----
このモジュールの出力はAI鑑定文生成の「入力データ」であり、
鑑定文そのものではない。
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Iterable, List, Mapping, Optional


# ============================================================
# Constants
# ============================================================


READING_CONTEXT_SCHEMA_VERSION = "reading_context_v1"
READING_CONTEXT_METHOD = "reading_context_v1"
READING_CONTEXT_STATUS = "ready_for_ai_reading"


PILLAR_POSITIONS = (
    "year",
    "month",
    "day",
    "hour",
)


READING_SECTION_KEYS = (
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
# Generic helpers
# ============================================================


def _require_mapping(
    value: Any,
    name: str,
) -> Mapping[str, Any]:
    """
    dict互換の値であることを検証する。
    """

    if not isinstance(
        value,
        Mapping,
    ):
        raise TypeError(
            f"{name}はdict型で指定してください。"
        )

    return value


def _safe_dict(
    value: Any,
) -> Dict[str, Any]:
    """
    Mappingならdeepcopyしたdictを返す。
    それ以外は空dict。
    """

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
    """
    list / tupleならdeepcopyしたlistを返す。
    それ以外は空list。
    """

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


def _non_empty_string(
    value: Any,
) -> Optional[str]:
    """
    空でない文字列ならその値を返す。
    """

    if not isinstance(
        value,
        str,
    ):
        return None

    stripped = value.strip()

    if not stripped:
        return None

    return stripped


def _first_present(
    mapping: Mapping[str, Any],
    keys: Iterable[str],
    default: Any = None,
) -> Any:
    """
    複数候補キーのうち、
    最初に存在する値を返す。
    """

    for key in keys:
        if key in mapping:
            return mapping[key]

    return default


def _extract_method_metadata(
    value: Any,
) -> Dict[str, Any]:
    """
    各計算モジュールのmethod/statusだけを抽出する。
    """

    if not isinstance(
        value,
        Mapping,
    ):
        return {
            "method": None,
            "status": None,
        }

    return {
        "method": value.get(
            "method"
        ),
        "status": value.get(
            "status"
        ),
    }


# ============================================================
# Birth time uncertainty
# ============================================================


def build_birth_time_context(
    chart_result: Mapping[str, Any],
) -> Dict[str, Any]:
    """出生時刻の既知・未知と鑑定上の利用範囲を整形する。"""
    chart_result = _require_mapping(chart_result, "chart_result")
    source = _safe_dict(chart_result.get("birth_time_status"))
    input_data = _safe_dict(chart_result.get("input"))

    if source:
        known = source.get("known")
        if not isinstance(known, bool):
            known = input_data.get("birth_time") is not None
    else:
        known = input_data.get("birth_time") is not None

    defaults = {
        "known": known,
        "hour_pillar_available": known,
        "calculation_scope": "four_pillars" if known else "three_pillars",
        "interpretation_scope": "full_chart" if known else "known_pillars_only",
        "five_elements_scope": "full_chart" if known else "known_pillars_only",
        "root_scope": "full_chart" if known else "known_pillars_only",
        "strength_scope": "full_chart" if known else "known_pillars_only",
        "pattern_scope": "full_chart" if known else "known_pillars_only",
        "useful_gods_scope": "full_chart" if known else "known_pillars_only",
        "relationship_scope": "full_chart" if known else "known_pillars_only",
        "luck_pillar_sequence_available": True,
        "luck_start_timing_precision": "normal" if known else "estimated",
        "current_luck_precision": "normal" if known else "estimated",
        "internal_reference_time_used": False if known else True,
        "internal_reference_time": None if known else "12:00",
        "is_provisional_due_to_unknown_birth_time": not known,
    }
    for key in tuple(defaults):
        if key in source:
            defaults[key] = deepcopy(source[key])

    defaults["reading_rule"] = (
        "通常の四柱として解釈できます。"
        if known
        else (
            "出生時刻不明のため、年柱・月柱・日柱の範囲で解釈します。"
            "時柱を推測せず、五行・身強身弱・格局・用神を命式全体の確定事項として断定しません。"
            "大運開始時期と現在大運の境界は推定扱いです。"
        )
    )
    return defaults


def _apply_birth_time_scope(
    context: Dict[str, Any],
    birth_time: Mapping[str, Any],
    *,
    scope_key: str,
) -> Dict[str, Any]:
    """既存計算値を変えず、AI向けの確度メタデータだけを付加する。"""
    result = deepcopy(context)
    known = bool(birth_time.get("known"))
    result["scope"] = birth_time.get(scope_key)
    result["is_complete_chart_evaluation"] = known
    result["provisional_due_to_unknown_birth_time"] = not known
    return result


# ============================================================
# Subject
# ============================================================


def build_subject_context(
    chart_result: Mapping[str, Any],
) -> Dict[str, Any]:
    """
    入力者の基本情報を整形する。
    """

    chart_result = _require_mapping(
        chart_result,
        "chart_result",
    )

    input_data = _safe_dict(
        chart_result.get(
            "input"
        )
    )

    return {
        "birth_date": input_data.get(
            "birth_date"
        ),
        "birth_time": input_data.get(
            "birth_time"
        ),
        "birth_place": input_data.get(
            "birth_place"
        ),
        "gender": input_data.get(
            "gender"
        ),
        "timezone": input_data.get(
            "timezone",
            "Asia/Tokyo",
        ),
    }


# ============================================================
# Natal chart
# ============================================================


def build_pillar_context(
    pillar: Any,
    position: str,
) -> Dict[str, Any]:
    """
    1柱分のAI鑑定用データを整形する。
    """

    data = _safe_dict(
        pillar
    )

    hidden_stems = _safe_list(
        data.get(
            "hidden_stems"
        )
    )

    return {
        "position": position,
        "pillar": _first_present(
            data,
            (
                "pillar",
                "ganzhi",
            ),
        ),
        "stem": data.get(
            "stem"
        ),
        "branch": data.get(
            "branch"
        ),
        "stem_ten_god": _first_present(
            data,
            (
                "stem_ten_god",
                "ten_god",
            ),
        ),
        "twelve_stage": data.get(
            "twelve_stage"
        ),
        "hidden_stems": hidden_stems,
        "main_hidden_stem": data.get(
            "main_hidden_stem"
        ),
        "main_hidden_stem_ten_god": _first_present(
            data,
            (
                "main_hidden_stem_ten_god",
                "hidden_stem_ten_god",
            ),
        ),
    }


def build_natal_chart_context(
    chart_result: Mapping[str, Any],
) -> Dict[str, Any]:
    """
    年・月・日・時の四柱を整形する。
    """

    chart_result = _require_mapping(
        chart_result,
        "chart_result",
    )

    chart = _safe_dict(
        chart_result.get(
            "chart"
        )
    )

    pillars = {}

    for position in PILLAR_POSITIONS:
        pillars[position] = (
            build_pillar_context(
                chart.get(
                    position
                ),
                position,
            )
        )

    return {
        "pillars": pillars,
        "pillar_sequence": [
            pillars[position][
                "pillar"
            ]
            for position
            in PILLAR_POSITIONS
        ],
    }


# ============================================================
# Day master
# ============================================================


def build_day_master_context(
    chart_result: Mapping[str, Any],
) -> Dict[str, Any]:
    """
    日主情報を整形する。
    """

    chart_result = _require_mapping(
        chart_result,
        "chart_result",
    )

    day_master = _safe_dict(
        chart_result.get(
            "day_master"
        )
    )

    day_pillar = (
        _safe_dict(
            _safe_dict(
                chart_result.get(
                    "chart"
                )
            ).get(
                "day"
            )
        )
    )

    stem = _first_present(
        day_master,
        (
            "stem",
            "day_master_stem",
        ),
        day_pillar.get(
            "stem"
        ),
    )

    return {
        "stem": stem,
        "element": _first_present(
            day_master,
            (
                "element",
                "day_master_element",
            ),
        ),
        "yin_yang": _first_present(
            day_master,
            (
                "yin_yang",
                "polarity",
            ),
        ),
        "day_pillar": _first_present(
            day_pillar,
            (
                "pillar",
                "ganzhi",
            ),
        ),
    }


# ============================================================
# Five elements
# ============================================================


def _extract_element_scores(
    data: Any,
) -> Dict[str, Any]:
    """
    五行スコアを可能な範囲で抽出する。
    """

    mapping = _safe_dict(
        data
    )

    scores = mapping.get(
        "scores"
    )

    if isinstance(
        scores,
        Mapping,
    ):
        return deepcopy(
            dict(scores)
        )

    result = {}

    for element in (
        "木",
        "火",
        "土",
        "金",
        "水",
    ):
        if element in mapping:
            result[element] = (
                mapping[element]
            )

    return result


def build_five_elements_context(
    chart_result: Mapping[str, Any],
) -> Dict[str, Any]:
    """
    五行情報を整形する。
    """

    chart_result = _require_mapping(
        chart_result,
        "chart_result",
    )

    five_elements = _safe_dict(
        chart_result.get(
            "five_elements"
        )
    )

    weighted = _safe_dict(
        chart_result.get(
            "weighted_five_elements"
        )
    )

    weighted_scores = (
        _extract_element_scores(
            weighted
        )
    )

    raw_scores = (
        _extract_element_scores(
            five_elements
        )
    )

    strongest = None
    weakest = None

    if weighted_scores:
        numeric_scores = {
            key: value
            for key, value
            in weighted_scores.items()
            if isinstance(
                value,
                (int, float),
            )
            and not isinstance(
                value,
                bool,
            )
        }

        if numeric_scores:
            strongest = max(
                numeric_scores,
                key=numeric_scores.get,
            )

            weakest = min(
                numeric_scores,
                key=numeric_scores.get,
            )

    return {
        "raw_scores": raw_scores,
        "weighted_scores": weighted_scores,
        "strongest_element": strongest,
        "weakest_element": weakest,
        "weighted_method": weighted.get(
            "method"
        ),
        "weighted_status": weighted.get(
            "status"
        ),
    }


# ============================================================
# Strength
# ============================================================


def build_strength_context(
    chart_result: Mapping[str, Any],
) -> Dict[str, Any]:
    """
    最終身強身弱判定をAI向けに簡潔化する。
    """

    chart_result = _require_mapping(
        chart_result,
        "chart_result",
    )

    strength = _safe_dict(
        chart_result.get(
            "final_strength_judgment"
        )
    )

    return {
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
        "adjustment_total": strength.get(
            "adjustment_total"
        ),
        "method": strength.get(
            "method"
        ),
        "status": strength.get(
            "status"
        ),
        "notes": _safe_list(
            strength.get(
                "notes"
            )
        ),
    }


# ============================================================
# Pattern
# ============================================================


def build_pattern_context(
    chart_result: Mapping[str, Any],
) -> Dict[str, Any]:
    """
    格局判定をAI向けに整形する。
    """

    chart_result = _require_mapping(
        chart_result,
        "chart_result",
    )

    pattern = _safe_dict(
        chart_result.get(
            "pattern_judgment"
        )
    )

    primary = _safe_dict(
        pattern.get(
            "primary_judgment"
        )
    )

    return {
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
        "establishment_score": _first_present(
            primary,
            (
                "establishment_score",
                "final_score",
            ),
        ),
        "establishment_status": primary.get(
            "establishment_status"
        ),
        "is_exposed": primary.get(
            "is_exposed"
        ),
        "breaking_factors": _safe_list(
            primary.get(
                "breaking_factors"
            )
        ),
        "rescue_factors": _safe_list(
            primary.get(
                "rescue_factors"
            )
        ),
        "method": pattern.get(
            "method"
        ),
        "status": pattern.get(
            "status"
        ),
    }


# ============================================================
# Useful gods
# ============================================================


def _compact_candidate(
    candidate: Any,
) -> Dict[str, Any]:
    """
    用神候補1件を簡潔化する。
    """

    data = _safe_dict(
        candidate
    )

    return {
        "element": data.get(
            "element"
        ),
        "priority": data.get(
            "priority"
        ),
        "integrated_score": data.get(
            "integrated_score"
        ),
        "source_count": data.get(
            "source_count"
        ),
        "is_triple_agreement": data.get(
            "is_triple_agreement"
        ),
        "is_double_agreement": data.get(
            "is_double_agreement"
        ),
        "is_conflicted": data.get(
            "is_conflicted"
        ),
    }


def build_useful_gods_context(
    chart_result: Mapping[str, Any],
) -> Dict[str, Any]:
    """
    用神v3の結果をAI向けに整形する。
    """

    chart_result = _require_mapping(
        chart_result,
        "chart_result",
    )

    useful = _safe_dict(
        chart_result.get(
            "useful_gods"
        )
    )

    support_balance = _safe_dict(
        useful.get(
            "support_balance"
        )
    )

    agreement = _safe_dict(
        useful.get(
            "agreement"
        )
    )

    candidates = [
        _compact_candidate(
            candidate
        )
        for candidate
        in _safe_list(
            useful.get(
                "final_candidates"
            )
        )
    ]

    return {
        "has_useful_candidate": useful.get(
            "has_useful_candidate"
        ),
        "primary_useful_element": useful.get(
            "primary_useful_element"
        ),
        "secondary_useful_elements": _safe_list(
            useful.get(
                "secondary_useful_elements"
            )
        ),
        "final_useful_elements": _safe_list(
            useful.get(
                "final_useful_elements"
            )
        ),
        "unfavorable_elements": _safe_list(
            support_balance.get(
                "unfavorable_elements"
            )
        ),
        "strength_class": useful.get(
            "strength_class"
        ),
        "confidence": useful.get(
            "confidence"
        ),
        "agreement_level": agreement.get(
            "agreement_level"
        ),
        "triple_agreement_elements": _safe_list(
            agreement.get(
                "triple_agreement_elements"
            )
        ),
        "double_agreement_elements": _safe_list(
            agreement.get(
                "double_agreement_elements"
            )
        ),
        "conflicted_elements": _safe_list(
            agreement.get(
                "conflicted_elements"
            )
        ),
        "candidates": candidates,
        "reasoning": _safe_list(
            useful.get(
                "reasoning"
            )
        ),
        "method": useful.get(
            "method"
        ),
        "status": useful.get(
            "status"
        ),
    }


# ============================================================
# Luck pillars
# ============================================================


def _compact_luck_pillar(
    pillar: Any,
) -> Dict[str, Any]:
    """
    大運1件をAI向けに簡潔化する。
    """

    data = _safe_dict(
        pillar
    )

    return {
        "index": data.get(
            "index"
        ),
        "ganzhi": _first_present(
            data,
            (
                "ganzhi",
                "pillar",
            ),
        ),
        "stem": data.get(
            "stem"
        ),
        "branch": data.get(
            "branch"
        ),
        "stem_element": data.get(
            "stem_element"
        ),
        "branch_element": data.get(
            "branch_element"
        ),
        "stem_ten_god": data.get(
            "stem_ten_god"
        ),
        "start_age": data.get(
            "start_age"
        ),
        "end_age": data.get(
            "end_age"
        ),
        "stem_useful_relation": _safe_dict(
            data.get(
                "stem_useful_relation"
            )
        ),
        "branch_useful_relation": _safe_dict(
            data.get(
                "branch_useful_relation"
            )
        ),
    }


def build_luck_pillars_context(
    chart_result: Mapping[str, Any],
) -> Dict[str, Any]:
    """
    大運一覧をAI向けに整形する。
    """

    chart_result = _require_mapping(
        chart_result,
        "chart_result",
    )

    luck = _safe_dict(
        chart_result.get(
            "luck_pillars"
        )
    )

    pillars = [
        _compact_luck_pillar(
            pillar
        )
        for pillar
        in _safe_list(
            luck.get(
                "pillars"
            )
        )
    ]

    return {
        "direction": luck.get(
            "direction"
        ),
        "direction_japanese": luck.get(
            "direction_japanese"
        ),
        "start_age": luck.get(
            "start_age"
        ),
        "start_age_detail": _safe_dict(
            luck.get(
                "start_age_detail"
            )
        ),
        "pillar_count": len(
            pillars
        ),
        "pillars": pillars,
        "method": luck.get(
            "method"
        ),
        "status": luck.get(
            "status"
        ),
    }


# ============================================================
# Current luck
# ============================================================


def build_current_luck_context(
    chart_result: Mapping[str, Any],
) -> Dict[str, Any]:
    """
    現在大運情報をAI向けに整形する。
    """

    chart_result = _require_mapping(
        chart_result,
        "chart_result",
    )

    current = _safe_dict(
        chart_result.get(
            "current_luck"
        )
    )

    current_pillar = (
        current.get(
            "current_luck_pillar"
        )
    )

    previous_pillar = (
        current.get(
            "previous_luck_pillar"
        )
    )

    next_pillar = (
        current.get(
            "next_luck_pillar"
        )
    )

    return {
        "has_current_luck": current.get(
            "has_current_luck"
        ),
        "phase": current.get(
            "phase"
        ),
        "exact_age": current.get(
            "exact_age"
        ),
        "calendar_age": current.get(
            "calendar_age"
        ),
        "current_pillar": (
            _compact_luck_pillar(
                current_pillar
            )
            if isinstance(
                current_pillar,
                Mapping,
            )
            else None
        ),
        "previous_pillar": (
            _compact_luck_pillar(
                previous_pillar
            )
            if isinstance(
                previous_pillar,
                Mapping,
            )
            else None
        ),
        "next_pillar": (
            _compact_luck_pillar(
                next_pillar
            )
            if isinstance(
                next_pillar,
                Mapping,
            )
            else None
        ),
        "progress": _safe_dict(
            current.get(
                "progress"
            )
        ),
        "years_until_next_luck": current.get(
            "years_until_next_luck"
        ),
        "method": current.get(
            "method"
        ),
        "status": current.get(
            "status"
        ),
    }


# ============================================================
# Annual luck
# ============================================================


def build_annual_luck_context(
    chart_result: Mapping[str, Any],
) -> Dict[str, Any]:
    """
    歳運情報をAI向けに整形する。
    """

    chart_result = _require_mapping(
        chart_result,
        "chart_result",
    )

    annual = _safe_dict(
        chart_result.get(
            "annual_luck"
        )
    )

    return {
        "year": annual.get(
            "year"
        ),
        "calendar_year": annual.get(
            "calendar_year"
        ),
        "effective_year": annual.get(
            "effective_year"
        ),
        "ganzhi": annual.get(
            "ganzhi"
        ),
        "stem": annual.get(
            "stem"
        ),
        "branch": annual.get(
            "branch"
        ),
        "stem_element": annual.get(
            "stem_element"
        ),
        "branch_element": annual.get(
            "branch_element"
        ),
        "stem_ten_god": annual.get(
            "stem_ten_god"
        ),
        "twelve_stage": annual.get(
            "twelve_stage"
        ),
        "stem_useful_relation": _safe_dict(
            annual.get(
                "stem_useful_relation"
            )
        ),
        "branch_useful_relation": _safe_dict(
            annual.get(
                "branch_useful_relation"
            )
        ),
        "current_luck_relation": _safe_dict(
            annual.get(
                "current_luck_relation"
            )
        ),
        "year_boundary_applied": annual.get(
            "year_boundary_applied"
        ),
        "year_boundary_rule": annual.get(
            "year_boundary_rule"
        ),
        "reasoning": _safe_list(
            annual.get(
                "reasoning"
            )
        ),
        "method": annual.get(
            "method"
        ),
        "status": annual.get(
            "status"
        ),
    }


# ============================================================
# Integrated luck
# ============================================================


def build_integrated_luck_context(
    chart_result: Mapping[str, Any],
) -> Dict[str, Any]:
    """
    大運×歳運の統合結果をAI向けに整形する。
    """

    chart_result = _require_mapping(
        chart_result,
        "chart_result",
    )

    integrated = _safe_dict(
        chart_result.get(
            "integrated_luck"
        )
    )

    confidence = _safe_dict(
        integrated.get(
            "confidence"
        )
    )

    agreement = _safe_dict(
        integrated.get(
            "useful_gods_agreement"
        )
    )

    score = _safe_dict(
        integrated.get(
            "score"
        )
    )

    element_interactions = _safe_dict(
        integrated.get(
            "element_interactions"
        )
    )

    return {
        "current_luck_ganzhi": integrated.get(
            "current_luck_ganzhi"
        ),
        "annual_luck_ganzhi": integrated.get(
            "annual_luck_ganzhi"
        ),
        "current_luck_elements": _safe_dict(
            integrated.get(
                "current_luck_elements"
            )
        ),
        "annual_luck_elements": _safe_dict(
            integrated.get(
                "annual_luck_elements"
            )
        ),
        "element_interactions": {
            "stem_relation": _safe_dict(
                element_interactions.get(
                    "stem_relation"
                )
            ),
            "branch_relation": _safe_dict(
                element_interactions.get(
                    "branch_relation"
                )
            ),
            "score": element_interactions.get(
                "score"
            ),
        },
        "current_luck_useful": _safe_dict(
            integrated.get(
                "current_luck_useful"
            )
        ),
        "annual_luck_useful": _safe_dict(
            integrated.get(
                "annual_luck_useful"
            )
        ),
        "agreement_level": agreement.get(
            "agreement_level"
        ),
        "score": score,
        "overall_score": integrated.get(
            "overall_score"
        ),
        "overall_level": integrated.get(
            "overall_level"
        ),
        "confidence": {
            "level": confidence.get(
                "level"
            ),
            "ratio": confidence.get(
                "ratio"
            ),
            "available_sources": confidence.get(
                "available_sources"
            ),
            "total_sources": confidence.get(
                "total_sources"
            ),
        },
        "annual_ten_god": integrated.get(
            "annual_ten_god"
        ),
        "annual_twelve_stage": integrated.get(
            "annual_twelve_stage"
        ),
        "reasoning": _safe_list(
            integrated.get(
                "reasoning"
            )
        ),
        "method": integrated.get(
            "method"
        ),
        "status": integrated.get(
            "status"
        ),
    }


# ============================================================
# Reading sections
# ============================================================


def build_reading_sections(
    context_parts: Mapping[str, Any],
) -> Dict[str, Any]:
    """
    AIが各鑑定テーマで参照すべき情報源を明示する。

    この段階では鑑定文を生成しない。
    各テーマに対する「参照データの案内」を作る。
    """

    context_parts = _require_mapping(
        context_parts,
        "context_parts",
    )

    return {
        "core_personality": {
            "focus": [
                "day_master",
                "strength",
                "pattern",
                "five_elements",
            ],
            "instruction": (
                "性格・価値観・行動傾向を、"
                "日主・身強身弱・格局・五行バランスから読む。"
            ),
        },
        "career": {
            "focus": [
                "pattern",
                "useful_gods",
                "day_master",
                "current_luck",
                "annual_luck",
            ],
            "instruction": (
                "仕事適性・働き方・現在の仕事運を、"
                "格局・用神・通変星・大運・歳運から読む。"
            ),
        },
        "wealth": {
            "focus": [
                "pattern",
                "useful_gods",
                "five_elements",
                "current_luck",
                "annual_luck",
                "integrated_luck",
            ],
            "instruction": (
                "金運・収入傾向・蓄財傾向を、"
                "命式構造と現在運を分けて読む。"
            ),
        },
        "relationships": {
            "focus": [
                "day_master",
                "pattern",
                "five_elements",
                "current_luck",
                "annual_luck",
            ],
            "instruction": (
                "対人・恋愛傾向を命式の性質として読み、"
                "現在運による変化と区別して説明する。"
            ),
        },
        "health": {
            "focus": [
                "five_elements",
                "strength",
                "useful_gods",
                "current_luck",
                "annual_luck",
            ],
            "instruction": (
                "健康は医学的診断を行わず、"
                "五行上の偏りや生活上の注意傾向として表現する。"
            ),
        },
        "current_luck": {
            "focus": [
                "current_luck",
                "annual_luck",
                "integrated_luck",
                "useful_gods",
            ],
            "instruction": (
                "現在の大運と歳運を分けて説明し、"
                "最後に統合運の意味を補足する。"
            ),
        },
        "future_flow": {
            "focus": [
                "luck_pillars",
                "current_luck",
                "annual_luck",
                "useful_gods",
            ],
            "instruction": (
                "現在大運の次の大運を中心に、"
                "長期的な変化の方向性を説明する。"
            ),
        },
        "advice": {
            "focus": [
                "useful_gods",
                "strength",
                "integrated_luck",
                "pattern",
            ],
            "instruction": (
                "断定的な未来予言ではなく、"
                "命式上活かしやすい方向と具体的な行動案を示す。"
            ),
        },
    }


# ============================================================
# Source metadata
# ============================================================


def build_source_metadata(
    chart_result: Mapping[str, Any],
) -> Dict[str, Any]:
    """
    どのエンジン結果から鑑定contextを作ったか記録する。
    """

    chart_result = _require_mapping(
        chart_result,
        "chart_result",
    )

    return {
        "strength": _extract_method_metadata(
            chart_result.get(
                "final_strength_judgment"
            )
        ),
        "pattern": _extract_method_metadata(
            chart_result.get(
                "pattern_judgment"
            )
        ),
        "useful_gods": _extract_method_metadata(
            chart_result.get(
                "useful_gods"
            )
        ),
        "luck_pillars": _extract_method_metadata(
            chart_result.get(
                "luck_pillars"
            )
        ),
        "current_luck": _extract_method_metadata(
            chart_result.get(
                "current_luck"
            )
        ),
        "annual_luck": _extract_method_metadata(
            chart_result.get(
                "annual_luck"
            )
        ),
        "integrated_luck": _extract_method_metadata(
            chart_result.get(
                "integrated_luck"
            )
        ),
    }


# ============================================================
# Validation
# ============================================================


def validate_chart_result_for_reading(
    chart_result: Mapping[str, Any],
) -> Dict[str, Any]:
    """
    AI鑑定context生成に必要な最低限の入力を検証する。

    後方互換ルール:
    ・birth_time_status が無い従来形式では四柱必須
    ・birth_time_status があり、known=False の場合のみ
      時柱なしを許可
    """

    chart_result = _require_mapping(
        chart_result,
        "chart_result",
    )

    required_top_level_keys = (
        "chart",
        "day_master",
        "final_strength_judgment",
        "pattern_judgment",
        "useful_gods",
        "luck_pillars",
        "current_luck",
        "annual_luck",
        "integrated_luck",
    )

    missing = [
        key
        for key in required_top_level_keys
        if key not in chart_result
    ]

    if missing:
        raise ValueError(
            "chart_resultに必要なキーがありません: "
            + ", ".join(missing)
        )

    chart = _require_mapping(
        chart_result["chart"],
        "chart_result['chart']",
    )

    # 年・月・日は常に必須。
    required_core_pillars = (
        "year",
        "month",
        "day",
    )

    missing_core_pillars = [
        position
        for position in required_core_pillars
        if position not in chart
        or chart.get(position) is None
    ]

    if missing_core_pillars:
        raise ValueError(
            "chartに必要な年柱・月柱・日柱がありません: "
            + ", ".join(
                missing_core_pillars
            )
        )

    birth_time_status_raw = chart_result.get(
        "birth_time_status"
    )

    # --------------------------------------------------------
    # 後方互換
    #
    # birth_time_status が無い旧形式では、
    # 従来どおり四柱すべてを必須とする。
    # --------------------------------------------------------
    if not isinstance(
        birth_time_status_raw,
        Mapping,
    ):
        if (
            "hour" not in chart
            or chart.get("hour") is None
        ):
            raise ValueError(
                "chartに必要な四柱がありません: hour"
            )

        return {
            "valid": True,
            "missing_top_level_keys": [],
            "missing_pillars": [],
            "hour_pillar_available": True,
            "birth_time_known": True,
        }

    # --------------------------------------------------------
    # 新形式
    # --------------------------------------------------------
    birth_time = build_birth_time_context(
        chart_result
    )

    hour_available = (
        chart.get("hour") is not None
    )

    # 出生時刻が分かっているなら時柱必須。
    if (
        birth_time["known"]
        and not hour_available
    ):
        raise ValueError(
            "出生時刻ありのchart_resultには"
            "時柱が必要です。"
        )

    # 出生時刻不明なら、時柱を確定値として保持しない。
    if (
        not birth_time["known"]
        and hour_available
    ):
        raise ValueError(
            "出生時刻不明のchart_resultでは"
            "時柱を確定値として保持できません。"
        )

    return {
        "valid": True,
        "missing_top_level_keys": [],
        "missing_pillars": [],
        "hour_pillar_available": (
            hour_available
        ),
        "birth_time_known": (
            birth_time["known"]
        ),
    }


# ============================================================
# Main builder
# ============================================================


def build_reading_context(
    chart_result: Mapping[str, Any],
    *,
    validate: bool = True,
) -> Dict[str, Any]:
    """
    calculate_chart() の結果から
    AI鑑定用contextを生成する。

    Parameters
    ----------
    chart_result:
        calculate_chart() の戻り値。

    validate:
        Trueの場合、必要な主要キーを事前検証する。

    Returns
    -------
    dict
        AI鑑定文生成に使用する安定したcontext。
    """

    chart_result = _require_mapping(
        chart_result,
        "chart_result",
    )

    if not isinstance(
        validate,
        bool,
    ):
        raise TypeError(
            "validateはbool型で指定してください。"
        )

    if validate:
        validation = (
            validate_chart_result_for_reading(
                chart_result
            )
        )
    else:
        validation = {
            "valid": None,
            "missing_top_level_keys": None,
            "missing_pillars": None,
        }

    birth_time = build_birth_time_context(
        chart_result
    )

    subject = build_subject_context(
        chart_result
    )

    natal_chart = (
        build_natal_chart_context(
            chart_result
        )
    )

    day_master = (
        build_day_master_context(
            chart_result
        )
    )

    five_elements = (
        build_five_elements_context(
            chart_result
        )
    )

    strength = build_strength_context(
        chart_result
    )

    pattern = build_pattern_context(
        chart_result
    )

    useful_gods = (
        build_useful_gods_context(
            chart_result
        )
    )

    luck_pillars = (
        build_luck_pillars_context(
            chart_result
        )
    )

    current_luck = (
        build_current_luck_context(
            chart_result
        )
    )

    annual_luck = (
        build_annual_luck_context(
            chart_result
        )
    )

    integrated_luck = (
        build_integrated_luck_context(
            chart_result
        )
    )

    five_elements = _apply_birth_time_scope(
        five_elements,
        birth_time,
        scope_key="five_elements_scope",
    )
    strength = _apply_birth_time_scope(
        strength,
        birth_time,
        scope_key="strength_scope",
    )
    pattern = _apply_birth_time_scope(
        pattern,
        birth_time,
        scope_key="pattern_scope",
    )
    useful_gods = _apply_birth_time_scope(
        useful_gods,
        birth_time,
        scope_key="useful_gods_scope",
    )

    luck_pillars["timing_precision"] = birth_time.get(
        "luck_start_timing_precision"
    )
    luck_pillars["timing_is_estimated"] = not birth_time["known"]
    current_luck["timing_precision"] = birth_time.get(
        "current_luck_precision"
    )
    current_luck["timing_is_estimated"] = not birth_time["known"]
    integrated_luck["timing_is_estimated"] = not birth_time["known"]

    context_parts = {
        "day_master": day_master,
        "five_elements": five_elements,
        "strength": strength,
        "pattern": pattern,
        "useful_gods": useful_gods,
        "luck_pillars": luck_pillars,
        "current_luck": current_luck,
        "annual_luck": annual_luck,
        "integrated_luck": integrated_luck,
    }

    reading_sections = (
        build_reading_sections(
            context_parts
        )
    )

    return {
        "schema_version": (
            READING_CONTEXT_SCHEMA_VERSION
        ),
        "subject": subject,
        "birth_time_status": birth_time,
        "natal_chart": natal_chart,
        "day_master": day_master,
        "five_elements": five_elements,
        "strength": strength,
        "pattern": pattern,
        "useful_gods": useful_gods,
        "luck": {
            "luck_pillars": (
                luck_pillars
            ),
            "current_luck": (
                current_luck
            ),
            "annual_luck": (
                annual_luck
            ),
            "integrated_luck": (
                integrated_luck
            ),
        },
        "reading_sections": (
            reading_sections
        ),
        "source_metadata": (
            build_source_metadata(
                chart_result
            )
        ),
        "validation": validation,
        "method": (
            READING_CONTEXT_METHOD
        ),
        "status": (
            READING_CONTEXT_STATUS
        ),
        "notes": [
            (
                "このcontextは既存の計算結果を"
                "AI鑑定文生成向けに整形したものです。"
            ),
            (
                "reading_context.py 自体では"
                "四柱・身強身弱・格局・用神・運勢を"
                "再計算しません。"
            ),
            (
                "AI鑑定では計算結果と文章上の解釈を"
                "明確に分けて扱ってください。"
            ),
            (
                "健康に関する文章は医学的診断として"
                "表現しないでください。"
            ),
            (
                "将来については確定的な予言ではなく、"
                "傾向・可能性・行動提案として表現してください。"
            ),
            (
                "出生時刻不明時は時柱を推測せず、三柱範囲の結果を"
                "命式全体の確定事項として断定しないでください。"
                if not birth_time["known"]
                else "出生時刻が確認できているため四柱範囲で整形しています。"
            ),
        ],
    }


# ============================================================
# Compatibility aliases
# ============================================================


def calculate_reading_context(
    chart_result: Mapping[str, Any],
    *,
    validate: bool = True,
) -> Dict[str, Any]:
    """
    build_reading_context() の互換API。
    """

    return build_reading_context(
        chart_result,
        validate=validate,
    )


def prepare_ai_reading_context(
    chart_result: Mapping[str, Any],
    *,
    validate: bool = True,
) -> Dict[str, Any]:
    """
    AI生成層から利用する意味的alias。
    """

    return build_reading_context(
        chart_result,
        validate=validate,
    )


# ============================================================
# Public API
# ============================================================


__all__ = [
    "READING_CONTEXT_SCHEMA_VERSION",
    "READING_CONTEXT_METHOD",
    "READING_CONTEXT_STATUS",
    "PILLAR_POSITIONS",
    "READING_SECTION_KEYS",
    "build_birth_time_context",
    "build_subject_context",
    "build_pillar_context",
    "build_natal_chart_context",
    "build_day_master_context",
    "build_five_elements_context",
    "build_strength_context",
    "build_pattern_context",
    "build_useful_gods_context",
    "build_luck_pillars_context",
    "build_current_luck_context",
    "build_annual_luck_context",
    "build_integrated_luck_context",
    "build_reading_sections",
    "build_source_metadata",
    "validate_chart_result_for_reading",
    "build_reading_context",
    "calculate_reading_context",
    "prepare_ai_reading_context",
]
