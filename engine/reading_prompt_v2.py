"""Trusted AI Reading v2 request construction.

This module consumes validated Reading Context v2 and Common Judgment
Metadata v1 objects.  It builds prompt-time catalogs, attachments, messages,
and a strict model-output schema without recalculating astrology.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from copy import deepcopy
import json
from typing import Any

from engine.judgment_metadata import (
    COMMON_JUDGMENT_COMPONENT_KEYS,
    COMMON_JUDGMENT_METADATA_SCHEMA_VERSION,
    COMMON_JUDGMENT_MONTH_COMMAND_COMPONENT_KEYS,
    COMMON_JUDGMENT_SOURCE_REGISTRY,
    validate_common_judgment_metadata,
)
from engine.judgment_schema import (
    VALID_JUDGMENT_STATUSES,
    VALID_SEVERITIES,
    VALID_UNCERTAINTY_CATEGORIES,
)
from engine.reading_context_v2 import validate_reading_context_v2


AI_READING_REQUEST_V2_SCHEMA_VERSION = "ai_reading_request_v2"
AI_READING_REQUEST_V2_VERSION = "ai_reading_request_v2"
AI_READING_REQUEST_V2_METHOD = "reading_prompt_v2"
AI_READING_REQUEST_V2_STATUS = "ready_for_ai_generation"

AI_READING_V2_SUPPORTED_LANGUAGES = ("ja",)
AI_READING_V2_SUPPORTED_TONES = ("professional_warm",)
AI_READING_V2_LONG_TERM_LUCK_COUNT = 5
AI_READING_V2_CLAIM_TYPES = (
    "practical",
    "astrology",
    "luck_astrology",
)

AI_READING_V2_SECTION_SLOTS = (
    ("core_personality", "本質・性格"),
    ("career", "仕事・適職"),
    ("wealth", "金運"),
    ("relationships", "恋愛・人間関係"),
    ("health", "健康傾向"),
    ("current_luck", "現在の運勢"),
    ("future_flow", "今後の流れ"),
    ("advice", "総合アドバイス"),
)

AI_READING_V2_DISCLAIMER = (
    "本鑑定は八雲式四柱推命エンジンの計算結果に基づく参考情報です。"
    "将来の出来事を保証するものではなく、医療・法律・投資その他の"
    "専門的判断を代替するものではありません。重要な意思決定は、"
    "必要に応じて適切な専門家へご相談ください。"
)

AI_READING_V2_SYSTEM_PROMPT = (
    "あなたは八雲式四柱推命エンジンのAI Reading v2文章化レイヤーです。"
    "出力言語は日本語、toneはprofessional_warmとし、model_output_schemaに"
    "厳密に一致するJSONだけを返してください。\n"
    "sectionsは提示された順序どおりのexactly 8 positional slotsとし、"
    "section ID、title、yearその他のtrusted fieldを返さないでください。\n"
    "占術上の主張は、提示されたfacts、source components、および許可された"
    "luck crosswalkだけを根拠とし、referenceを新規作成してはいけません。\n"
    "warningとuncertaintyは提示されたcatalog IDからだけ選択し、新規作成、"
    "変更、正規化、重複排除をしてはいけません。\n"
    "出生時間不明の場合はknown_pillars_onlyを守り、時柱または時柱由来の"
    "解釈を推定せず、strength confidenceを強化せず、estimated timingと"
    "applicable uncertaintyを保持し、internal_reference_timeを出生時刻として"
    "扱わないでください。\n"
    "四柱、蔵干、通変星、十二運、五行score、身強身弱、干支関係、格局、"
    "用神、大運、歳運、current luck、integrated luckを再計算、再判定、"
    "再分類してはいけません。\n"
    "missing hour、true solar time、timezone correction、location correctionを"
    "推定してはいけません。\n"
    "consultationは説明の優先順位とpractical contextにだけ使用し、占術結果を"
    "生成または変更してはいけません。\n"
    "すべてのgrounded_text_blockでclaim_typeを宣言し、意図するtextと一致"
    "させてください。practicalに占術またはluckの主張を含めず、astrologyは"
    "factでgroundし、luck_astrologyは許可されたlocationとluck crosswalkで"
    "groundしてください。占術またはluckの主張をpracticalとして偽装しては"
    "いけません。\n"
    "claim_typeごとのreference ruleを厳守してください。practicalでは"
    "source_fact_codesとsource_componentsをともにempty arrayとします。"
    "astrologyではsource_fact_codesを1件以上選び、luck_pillars、current_luck、"
    "annual_luck、integrated_luckをsource_componentsに含めません。luck_astrologyでは"
    "対応するlocationのluck_value_sourcesに存在する有効なluck componentを"
    "source_componentsに1件以上選んでください。\n"
    "claim_typeのlocation ruleを厳守してください。top-level summaryと"
    "consultation_answerはpracticalまたはastrologyだけを許可します。"
    "core_personality、career、wealth、relationships、health、adviceのsummary、detail、"
    "advice[]はpracticalまたはastrologyだけを許可し、evidence[]とinterpretation[]は"
    "astrologyだけを許可します。current_luckとfuture_flowのsummary、detail、"
    "advice[]は3種すべてを許可し、evidence[]とinterpretation[]はastrologyまたは"
    "luck_astrologyだけを許可します。future_flow_yearlyの各summaryとdetailは"
    "3種すべてを許可します。\n"
    "luck_astrologyはcurrent_luck、future_flow、future_flow_yearlyだけで使用します。"
    "current_luckではluck_value_sourcesのcurrent_luck entryとexact matchするluck_pillars、"
    "current_luck、annual_luck、integrated_luckのみを選びます。future_flowのnon-yearly"
    " blockではcurrent_luck、annual_luck、integrated_luckのみを選び、選択した"
    "componentについてluck_value_sourcesに存在する全future_flow year entryをtrusted orderで"
    "一括して使用し、subset yearを指定しません。"
    "future_flow_yearlyでは、その位置のyear/indexにexact matchするcurrent_luck、"
    "annual_luck、integrated_luckのみを選んでください。year、index、context_pathは"
    "trusted fieldであり、model payloadに返してはいけません。\n"
    "顧客向けtextではsupportive、mixed、balanced、integrated score、統合評価、"
    "統合スコア、統合比較、混合、favorable factorなどの"
    "内部評価labelやvalueをそのまま出力せず、その意味を一般の顧客が理解できる"
    "自然な日本語で説明してください。内部metadataの値は変更しません。\n"
    "consultationまたはtrusted factsに明示されていない職種、業界、専門業務、役職を"
    "推定してはいけません。KPI、SLA、WBS、PM/Ops、品質ゲート、監査ログ、"
    "ダッシュボード、要件定義書、CS起点、A/Bテストなどの専門用語は、入力情報に"
    "具体的な根拠がある場合にだけ使用し、一般の相談者にも理解できる日本語を優先して"
    "ください。「仕組み化」を根拠なくこれらの専門用語へ展開してはいけません。\n"
    "職種、活動、場面などの具体例は、trusted factsまたはconsultationに本人の事実として"
    "示されていない限り、『たとえば』『一例として』『こうした分野では』など、例示で"
    "あることを明示してください。例示を相談者本人の経歴、現在の仕事、予定、希望として"
    "断定してはいけません。\n"
    "文章上の役割が異なる内容を1つのgrounded_text_blockへ混在させないでください。"
    "evidence[]は提示されたfactまたはluckの根拠、interpretation[]はその根拠から読める"
    "傾向と現実生活での意味、advice[]は助言または明示された具体例として役割を分けます。"
    "practicalな助言・具体例だけを述べるblockはclaim_typeをpracticalとしてreferenceを"
    "emptyにし、占術またはluckの主張を含めるblockは対応するclaim_typeと有効なreferenceを"
    "使用してください。summaryとdetailを含む各blockも、宣言した単一のclaim_typeとtextの"
    "意味を一致させてください。\n"
    "鑑定文はsection全体として、四柱推命上の根拠、そこから読める傾向、日常・仕事・"
    "人間関係など現実生活での現れ方、必要に応じた具体例、実行可能な助言が自然に"
    "つながるようにし、同じ内容を反復しないでください。"
    "落ち着いた丁寧な語り口で、押し付けや過度な断定を避け、一般の30〜60代が理解できる"
    "表現を使い、神秘主義やAI・コンサル資料のような文体へ寄せないでください。\n"
    "healthでは病名の診断、特定疾患の予測、特定臓器についての医学的断定、医療行為の"
    "代替、具体的な治療法や健康法の断定をしてはいけません。命式から直接導けない"
    "デジタル断食や朝型生活などの具体策を作らず、休息、生活リズム、無理を重ねないこと、"
    "自分の状態の確認、必要に応じた専門家への相談という一般的な生活助言に留めてください。\n"
    "返してよいのはmodel-owned payloadだけです。section_id、title、year、"
    "disclaimer、catalog、source contract、engine_version、schema_version、"
    "version、method、status、validationを返してはいけません。\n"
    "source_fact_codes、source_components、warning IDs、uncertainty IDsは"
    "提示されたallowed valuesからだけ選択し、strict JSONとして返してください。"
)

AI_READING_V2_SYSTEM_PROMPT += (
    " long_term_luck はtrusted_attachmentsのlong_term_luck_pillarsの順序をそのまま使い、"
    "各要素をtitle/theme/career/wealth/relationships/caution/adviceとして生成してください。"
    "これらの本文は対応するluck_pillarsだけでgroundし、pillarの干支・年齢・通変星・五行を計算・変更しないでください。"
)

AI_READING_V2_SYSTEM_PROMPT += (
    " For relationships evidence and interpretation grounded in the trusted branch-relation facts, "
    "use astrology with source_components containing exactly relations; relationships is a section name, "
    "not a source component. Do not mix another component into that block unless its text is explicitly "
    "grounded in that component's trusted facts. Use the existing fact code chart.pillar_sequence "
    "as the fact reference for that branch-relation grounding; do not invent a relation fact code. "
    "The interpretation must state an astrology observation from the branch-relation facts and then "
    "give its astrology interpretation. Do not put generic advice or action proposals in interpretation; "
    "put practical actions in advice."
)

AI_READING_V2_SYSTEM_PROMPT += (
    " Customer-facing prose must not expose internal labels such as 統合評価、統合運評価、"
    "統合スコア、内部評価; describe the combined flow naturally in ordinary Japanese instead."
)

AI_READING_V2_SYSTEM_PROMPT += (
    " For each future_flow_yearly item, provide title, theme, career, wealth, relationships, "
    "caution, and 2-4 advice blocks in addition to summary and detail. Keep the supplied year "
    "order and ground luck claims only in the matching yearly luck crosswalk; do not calculate "
    "years or invent fact codes. Distinguish the year's concrete actions from long-term luck themes."
)

AI_READING_V2_USER_PROMPT_PREFIX = (
    "以下のmodel_inputだけを使用し、model_output_schemaに厳密に一致するJSONを"
    "生成してください。\n"
    "model_input="
)

AI_READING_REQUEST_V2_FIELDS = (
    "schema_version",
    "version",
    "method",
    "status",
    "language",
    "tone",
    "source_contracts",
    "trusted_catalogs",
    "trusted_attachments",
    "model_input",
    "messages",
    "model_output_schema",
    "validation",
)

_VALIDATION_FIELDS = (
    "valid",
    "errors",
    "missing_required_fields",
    "unknown_fields",
)
_UNCERTAINTY_FIELDS = (
    "code",
    "category",
    "status",
    "severity",
    "scope",
    "message",
)
_TOP_LEVEL_LUCK_COMPONENTS = (
    "luck_pillars",
    "current_luck",
    "annual_luck",
    "integrated_luck",
)
_FUTURE_LUCK_COMPONENTS = (
    "current_luck",
    "annual_luck",
    "integrated_luck",
)

_INTERNAL_INTEGRATED_LUCK_KEYS = frozenset(
    {
        "overall_score",
        "overall_level",
        "agreement_level",
        "score",
        "confidence",
        "reasoning",
    }
)


def _strip_internal_integrated_luck(value: Any) -> Any:
    """Remove internal evaluation labels from the customer-facing model input only."""
    if isinstance(value, Mapping):
        return {
            key: _strip_internal_integrated_luck(item)
            for key, item in value.items()
            if key not in _INTERNAL_INTEGRATED_LUCK_KEYS
        }
    if isinstance(value, (list, tuple)):
        return [_strip_internal_integrated_luck(item) for item in value]
    return deepcopy(value)


def _customer_prompt_reading_context(reading_context: Mapping[str, Any]) -> dict[str, Any]:
    projected = deepcopy(dict(reading_context))
    luck = projected.get("luck")
    if isinstance(luck, Mapping):
        if "integrated_luck" in luck:
            luck["integrated_luck"] = _strip_internal_integrated_luck(
                luck["integrated_luck"]
            )
        yearly = luck.get("five_year_luck")
        if isinstance(yearly, list):
            for entry in yearly:
                if isinstance(entry, Mapping) and "integrated_luck" in entry:
                    entry["integrated_luck"] = _strip_internal_integrated_luck(
                        entry["integrated_luck"]
                    )
    return projected


def _customer_prompt_judgment_metadata(judgment_metadata: Mapping[str, Any]) -> dict[str, Any]:
    projected = deepcopy(dict(judgment_metadata))
    components = projected.get("components")
    if isinstance(components, Mapping) and isinstance(components.get("integrated_luck"), Mapping):
        components["integrated_luck"]["evidence"] = _strip_internal_integrated_luck(
            components["integrated_luck"].get("evidence")
        )
    return projected


def _build_long_term_luck_pillars(
    reading_context: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Select current and following four owner-calculated luck pillars."""
    luck = reading_context["luck"]
    pillars = luck["luck_pillars"]["pillars"]
    current = luck.get("current_luck")
    current_index = current.get("current_pillar", {}).get("index") if isinstance(current, Mapping) else None
    start = next(
        (position for position, pillar in enumerate(pillars)
         if pillar.get("index") == current_index),
        0,
    )
    selected = pillars[start:start + AI_READING_V2_LONG_TERM_LUCK_COUNT]
    return [deepcopy(dict(pillar)) for pillar in selected]


def _new_validation_report() -> dict[str, Any]:
    return {
        "valid": True,
        "errors": [],
        "missing_required_fields": [],
        "unknown_fields": [],
    }


def _append_once(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


def _add_error(report: dict[str, Any], value: str) -> None:
    _append_once(report["errors"], value)


def _add_missing(report: dict[str, Any], value: str) -> None:
    _append_once(report["missing_required_fields"], value)
    _add_error(report, f"missing_required_field:{value}")


def _add_unknown(report: dict[str, Any], value: str) -> None:
    _append_once(report["unknown_fields"], value)
    _add_error(report, f"unknown_field:{value}")


def _merge_owner_report(
    report: dict[str, Any],
    owner_report: Mapping[str, Any],
    prefix: str,
) -> None:
    for value in owner_report.get("errors", []):
        _add_error(report, f"{prefix}:{value}")
    for value in owner_report.get("missing_required_fields", []):
        _append_once(report["missing_required_fields"], f"{prefix}.{value}")
    for value in owner_report.get("unknown_fields", []):
        _append_once(report["unknown_fields"], f"{prefix}.{value}")


def _validate_uncertainty_entry(
    value: Any,
    path: str,
    report: dict[str, Any],
) -> None:
    if not isinstance(value, Mapping):
        _add_error(report, f"type:{path}:object")
        return

    for field in _UNCERTAINTY_FIELDS:
        if field not in value:
            _add_missing(report, f"{path}.{field}")
    for field in sorted(set(value) - set(_UNCERTAINTY_FIELDS)):
        _add_unknown(report, f"{path}.{field}")

    if "code" in value and not isinstance(value["code"], str):
        _add_error(report, f"type:{path}.code:string")
    category = value.get("category")
    if "category" in value:
        if not isinstance(category, str):
            _add_error(report, f"type:{path}.category:string")
        elif category not in VALID_UNCERTAINTY_CATEGORIES:
            _add_error(report, f"value:{path}.category")
    status = value.get("status")
    if "status" in value:
        if not isinstance(status, str):
            _add_error(report, f"type:{path}.status:string")
        elif status not in VALID_JUDGMENT_STATUSES:
            _add_error(report, f"value:{path}.status")
    severity = value.get("severity")
    if "severity" in value:
        if not isinstance(severity, str):
            _add_error(report, f"type:{path}.severity:string")
        elif severity not in VALID_SEVERITIES:
            _add_error(report, f"value:{path}.severity")
    if "scope" in value:
        scope = value["scope"]
        if not isinstance(scope, list) or any(
            not isinstance(item, str) for item in scope
        ):
            _add_error(report, f"type:{path}.scope:array_of_string")
    if "message" in value:
        message = value["message"]
        if message is not None and not isinstance(message, str):
            _add_error(report, f"type:{path}.message:string_or_null")


def _iter_component_records(
    metadata: Mapping[str, Any],
) -> Iterator[tuple[str, str, Mapping[str, Any]]]:
    components = metadata["components"]
    for key in COMMON_JUDGMENT_COMPONENT_KEYS:
        if key != "month_command":
            yield key, f"components.{key}", components[key]
            continue
        nested = components[key]["components"]
        for nested_key in COMMON_JUDGMENT_MONTH_COMMAND_COMPONENT_KEYS:
            yield (
                f"month_command.{nested_key}",
                f"components.month_command.components.{nested_key}",
                nested[nested_key],
            )


def _registered_source_path(component: str) -> str:
    if not component.startswith("month_command."):
        return COMMON_JUDGMENT_SOURCE_REGISTRY[component]
    nested_key = component.split(".", 1)[1]
    return COMMON_JUDGMENT_SOURCE_REGISTRY["month_command"][nested_key]


def _validate_component_compatibility(
    metadata: Mapping[str, Any],
    report: dict[str, Any],
) -> None:
    for component, path, record in _iter_component_records(metadata):
        expected = _registered_source_path(component)
        source_path = record.get("source_path")
        if source_path is not None and source_path != expected:
            _add_error(report, f"value:{path}.source_path:{expected}")
        if source_path is not None and not isinstance(record.get("method"), str):
            _add_error(report, f"required:{path}.method:present_source")


def validate_ai_reading_prompt_inputs_v2(
    reading_context: Mapping[str, Any],
    judgment_metadata: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate prompt prerequisites without calculation or completion."""
    if not isinstance(reading_context, Mapping):
        raise TypeError("reading_context must be a Mapping")
    if not isinstance(judgment_metadata, Mapping):
        raise TypeError("judgment_metadata must be a Mapping")

    report = _new_validation_report()
    context_report = validate_reading_context_v2(reading_context)
    metadata_report = validate_common_judgment_metadata(judgment_metadata)
    if not context_report["valid"]:
        _merge_owner_report(report, context_report, "reading_context")
    if not metadata_report["valid"]:
        _merge_owner_report(report, metadata_report, "judgment_metadata")
    if not context_report["valid"] or not metadata_report["valid"]:
        report["valid"] = False
        return report

    warnings = reading_context.get("warnings")
    if not isinstance(warnings, list) or any(
        not isinstance(item, str) for item in warnings
    ):
        _add_error(report, "type:reading_context.warnings:array_of_string")

    uncertainty = reading_context.get("uncertainty")
    if not isinstance(uncertainty, list):
        _add_error(report, "type:reading_context.uncertainty:array")
    else:
        for index, entry in enumerate(uncertainty):
            _validate_uncertainty_entry(
                entry,
                f"reading_context.uncertainty[{index}]",
                report,
            )

    engine_version = reading_context.get("engine_version")
    if engine_version is not None and not isinstance(engine_version, str):
        _add_error(report, "type:reading_context.engine_version:string_or_null")

    luck = reading_context.get("luck")
    if not isinstance(luck, Mapping):
        _add_error(report, "type:reading_context.luck:object")
    else:
        for component in _TOP_LEVEL_LUCK_COMPONENTS:
            path = f"reading_context.luck.{component}"
            if component not in luck:
                _add_missing(report, path)
                continue
            value = luck[component]
            if value is not None and not isinstance(value, Mapping):
                _add_error(report, f"type:{path}:object_or_null")

        if "five_year_luck" not in luck:
            _add_missing(report, "reading_context.luck.five_year_luck")
        five_year_luck = luck.get("five_year_luck")
        if not isinstance(five_year_luck, list):
            _add_error(
                report,
                "type:reading_context.luck.five_year_luck:array",
            )
        else:
            seen_years: set[int] = set()
            for index, entry in enumerate(five_year_luck):
                base = f"reading_context.luck.five_year_luck[{index}]"
                if not isinstance(entry, Mapping):
                    _add_error(report, f"type:{base}:object")
                    continue
                if "year" not in entry:
                    _add_missing(report, f"{base}.year")
                year = entry.get("year")
                if not isinstance(year, int) or isinstance(year, bool):
                    _add_error(report, f"type:{base}.year:integer")
                elif year in seen_years:
                    _add_error(report, f"duplicate_year:{year}")
                else:
                    seen_years.add(year)
                for component in _FUTURE_LUCK_COMPONENTS:
                    path = f"{base}.{component}"
                    if component not in entry:
                        _add_missing(report, path)
                        continue
                    value = entry[component]
                    if value is not None and not isinstance(value, Mapping):
                        _add_error(report, f"type:{path}:object_or_null")

    _validate_component_compatibility(judgment_metadata, report)
    report["valid"] = not any(
        (
            report["errors"],
            report["missing_required_fields"],
            report["unknown_fields"],
        )
    )
    return report


def _section_slots() -> list[dict[str, str]]:
    return [
        {"section_id": section_id, "title": title}
        for section_id, title in AI_READING_V2_SECTION_SLOTS
    ]


def _available_components(
    metadata: Mapping[str, Any],
) -> list[str]:
    result: list[str] = []
    for component, _, record in _iter_component_records(metadata):
        if record["source_path"] is not None:
            result.append(component)
    return result


def _warning_catalog_entry(
    warning_id: str,
    source_contract: str,
    source_path: str,
    value: str,
) -> dict[str, Any]:
    return {
        "warning_id": warning_id,
        "source_contract": source_contract,
        "source_path": source_path,
        "value": deepcopy(value),
    }


def _uncertainty_catalog_entry(
    uncertainty_id: str,
    source_contract: str,
    source_path: str,
    value: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "uncertainty_id": uncertainty_id,
        "source_contract": source_contract,
        "source_path": source_path,
        "value": deepcopy(dict(value)),
    }


def _build_notice_catalogs(
    reading_context: Mapping[str, Any],
    judgment_metadata: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    warnings: list[dict[str, Any]] = []
    uncertainty: list[dict[str, Any]] = []

    for index, value in enumerate(reading_context["warnings"]):
        warnings.append(
            _warning_catalog_entry(
                f"warning_{len(warnings) + 1:04d}",
                "reading_context_v2",
                f"warnings[{index}]",
                value,
            )
        )
    for index, value in enumerate(reading_context["uncertainty"]):
        uncertainty.append(
            _uncertainty_catalog_entry(
                f"uncertainty_{len(uncertainty) + 1:04d}",
                "reading_context_v2",
                f"uncertainty[{index}]",
                value,
            )
        )

    for _, path, record in _iter_component_records(judgment_metadata):
        for index, value in enumerate(record["warnings"]):
            warnings.append(
                _warning_catalog_entry(
                    f"warning_{len(warnings) + 1:04d}",
                    "common_judgment_metadata_v1",
                    f"{path}.warnings[{index}]",
                    value,
                )
            )
        for index, value in enumerate(record["uncertainty"]):
            uncertainty.append(
                _uncertainty_catalog_entry(
                    f"uncertainty_{len(uncertainty) + 1:04d}",
                    "common_judgment_metadata_v1",
                    f"{path}.uncertainty[{index}]",
                    value,
                )
            )
    return warnings, uncertainty


def _component_available(
    metadata: Mapping[str, Any],
    component: str,
) -> bool:
    record = metadata["components"][component]
    source_path = record["source_path"]
    return (
        source_path is not None
        and source_path == COMMON_JUDGMENT_SOURCE_REGISTRY[component]
        and isinstance(record["method"], str)
    )


def _build_luck_value_sources(
    reading_context: Mapping[str, Any],
    judgment_metadata: Mapping[str, Any],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    luck = reading_context["luck"]

    for component in _TOP_LEVEL_LUCK_COMPONENTS:
        if not _component_available(judgment_metadata, component):
            continue
        if luck[component] is None:
            continue
        result.append(
            {
                "section_id": "current_luck",
                "year": None,
                "source_component": component,
                "context_path": f"luck.{component}",
            }
        )

    for index, entry in enumerate(luck["five_year_luck"]):
        for component in _FUTURE_LUCK_COMPONENTS:
            if not _component_available(judgment_metadata, component):
                continue
            if entry[component] is None:
                continue
            result.append(
                {
                    "section_id": "future_flow",
                    "year": entry["year"],
                    "source_component": component,
                    "context_path": (
                        f"luck.five_year_luck[{index}].{component}"
                    ),
                }
            )
    if _component_available(judgment_metadata, "luck_pillars"):
        for position, pillar in enumerate(_build_long_term_luck_pillars(reading_context)):
            result.append(
                {
                    "section_id": "long_term_luck",
                    "year": pillar["index"],
                    "source_component": "luck_pillars",
                    "context_path": f"luck.luck_pillars.pillars[{position}]",
                }
            )
    return result


def _build_trusted_catalogs(
    reading_context: Mapping[str, Any],
    judgment_metadata: Mapping[str, Any],
) -> dict[str, Any]:
    warnings, uncertainty = _build_notice_catalogs(
        reading_context,
        judgment_metadata,
    )
    return {
        "fact_codes": [fact["code"] for fact in reading_context["facts"]],
        "source_components": _available_components(judgment_metadata),
        "warnings": warnings,
        "uncertainty": uncertainty,
        "luck_value_sources": _build_luck_value_sources(
            reading_context,
            judgment_metadata,
        ),
    }


def _dynamic_string_array_schema(values: list[str]) -> dict[str, Any]:
    if values:
        return {
            "type": "array",
            "items": {"type": "string", "enum": deepcopy(values)},
            "uniqueItems": True,
        }
    return {
        "type": "array",
        "items": {"type": "string"},
        "minItems": 0,
        "maxItems": 0,
        "uniqueItems": True,
    }


def _available_claim_types(
    trusted_catalogs: Mapping[str, Any],
) -> list[str]:
    available = [AI_READING_V2_CLAIM_TYPES[0]]
    if trusted_catalogs["fact_codes"]:
        available.append(AI_READING_V2_CLAIM_TYPES[1])
    if trusted_catalogs["luck_value_sources"]:
        available.append(AI_READING_V2_CLAIM_TYPES[2])
    return available


def _build_model_output_schema(
    trusted_catalogs: Mapping[str, Any],
    *,
    future_year_count: int,
    consultation_present: bool,
    long_term_luck_count: int,
) -> dict[str, Any]:
    warning_ids = [entry["warning_id"] for entry in trusted_catalogs["warnings"]]
    uncertainty_ids = [
        entry["uncertainty_id"]
        for entry in trusted_catalogs["uncertainty"]
    ]
    definitions = {
        "fact_code_array": _dynamic_string_array_schema(
            trusted_catalogs["fact_codes"]
        ),
        "source_component_array": _dynamic_string_array_schema(
            trusted_catalogs["source_components"]
        ),
        "warning_id_array": _dynamic_string_array_schema(warning_ids),
        "uncertainty_id_array": _dynamic_string_array_schema(uncertainty_ids),
        "grounded_text_block": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "claim_type": {
                    "type": "string",
                    "enum": _available_claim_types(trusted_catalogs),
                },
                "source_fact_codes": {"$ref": "#/$defs/fact_code_array"},
                "source_components": {
                    "$ref": "#/$defs/source_component_array"
                },
                "warnings": {"$ref": "#/$defs/warning_id_array"},
                "uncertainty": {"$ref": "#/$defs/uncertainty_id_array"},
            },
            "required": [
                "text",
                "claim_type",
                "source_fact_codes",
                "source_components",
                "warnings",
                "uncertainty",
            ],
            "additionalProperties": False,
        },
        "model_section_payload": {
            "type": "object",
            "properties": {
                "facts": {"$ref": "#/$defs/fact_code_array"},
                "summary": {"$ref": "#/$defs/grounded_text_block"},
                "detail": {"$ref": "#/$defs/grounded_text_block"},
                "evidence": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/grounded_text_block"},
                },
                "interpretation": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/grounded_text_block"},
                },
                "advice": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/grounded_text_block"},
                },
                "warnings": {"$ref": "#/$defs/warning_id_array"},
                "uncertainty": {"$ref": "#/$defs/uncertainty_id_array"},
            },
            "required": [
                "facts",
                "summary",
                "detail",
                "evidence",
                "interpretation",
                "advice",
                "warnings",
                "uncertainty",
            ],
            "additionalProperties": False,
        },
        "model_year_payload": {
            "type": "object",
            "properties": {
                "title": {"$ref": "#/$defs/grounded_text_block"},
                "theme": {"$ref": "#/$defs/grounded_text_block"},
                "career": {"$ref": "#/$defs/grounded_text_block"},
                "wealth": {"$ref": "#/$defs/grounded_text_block"},
                "relationships": {"$ref": "#/$defs/grounded_text_block"},
                "caution": {"$ref": "#/$defs/grounded_text_block"},
                "advice": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/grounded_text_block"},
                    "minItems": 2,
                    "maxItems": 4,
                },
                "summary": {"$ref": "#/$defs/grounded_text_block"},
                "detail": {"$ref": "#/$defs/grounded_text_block"},
            },
            # The detail fields are additive: legacy deterministic fixtures remain
            # valid, while production prompts request and render them when present.
            "required": ["summary", "detail"],
            "additionalProperties": False,
        },
        "long_term_luck_payload": {
            "type": "object",
            "properties": {
                field: {"$ref": "#/$defs/grounded_text_block"}
                for field in (
                    "title", "theme", "career", "wealth",
                    "relationships", "caution",
                )
            } | {
                "advice": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/grounded_text_block"},
                    "minItems": 2,
                    "maxItems": 4,
                }
            },
            "required": [
                "title", "theme", "career", "wealth",
                "relationships", "caution", "advice",
            ],
            "additionalProperties": False,
        },
    }
    consultation_schema = (
        {"$ref": "#/$defs/grounded_text_block"}
        if consultation_present
        else {"type": "null"}
    )
    return {
        "$defs": definitions,
        "type": "object",
        "properties": {
            "summary": {"$ref": "#/$defs/grounded_text_block"},
            "sections": {
                "type": "array",
                "items": {"$ref": "#/$defs/model_section_payload"},
                "minItems": 8,
                "maxItems": 8,
            },
            "future_flow_yearly": {
                "type": "array",
                "items": {"$ref": "#/$defs/model_year_payload"},
                "minItems": future_year_count,
                "maxItems": future_year_count,
            },
            "long_term_luck": {
                "type": "array",
                "items": {"$ref": "#/$defs/long_term_luck_payload"},
                "minItems": long_term_luck_count,
                "maxItems": long_term_luck_count,
            },
            "consultation_answer": consultation_schema,
        },
        "required": [
            "summary",
            "sections",
            "future_flow_yearly",
            "long_term_luck",
            "consultation_answer",
        ],
        "additionalProperties": False,
    }


def build_ai_reading_request_v2(
    reading_context: Mapping[str, Any],
    judgment_metadata: Mapping[str, Any],
    *,
    sections: None = None,
    language: str = "ja",
    tone: str = "professional_warm",
) -> dict[str, Any]:
    """Build the trusted internal request for AI Reading v2 generation."""
    if sections is not None:
        raise ValueError("sections must be None for AI Reading v2")
    if language not in AI_READING_V2_SUPPORTED_LANGUAGES:
        raise ValueError("language must be 'ja' for AI Reading v2")
    if tone not in AI_READING_V2_SUPPORTED_TONES:
        raise ValueError("unsupported AI Reading v2 tone")

    validation = validate_ai_reading_prompt_inputs_v2(
        reading_context,
        judgment_metadata,
    )
    if not validation["valid"]:
        raise ValueError(f"invalid AI Reading v2 prompt inputs: {validation}")

    trusted_catalogs = _build_trusted_catalogs(
        reading_context,
        judgment_metadata,
    )
    section_slots = _section_slots()
    future_flow_years = [
        entry["year"] for entry in reading_context["luck"]["five_year_luck"]
    ]
    consultation_present = reading_context["consultation"] is not None
    long_term_luck_pillars = (
        _build_long_term_luck_pillars(reading_context)
        if _component_available(judgment_metadata, "luck_pillars")
        else []
    )
    trusted_attachments = {
        "final_schema_version": "ai_reading_v2",
        "final_version": "ai_reading_v2",
        "final_method": "openai_responses_api_v2",
        "final_status": "completed",
        "engine_version": deepcopy(reading_context["engine_version"]),
        "sections": deepcopy(section_slots),
        "future_flow_years": deepcopy(future_flow_years),
        "long_term_luck_pillars": long_term_luck_pillars,
        "consultation_present": consultation_present,
        "disclaimer": AI_READING_V2_DISCLAIMER,
    }
    model_input = {
        "reading_context": _customer_prompt_reading_context(reading_context),
        "judgment_metadata": _customer_prompt_judgment_metadata(judgment_metadata),
        "trusted_catalogs": deepcopy(trusted_catalogs),
        "section_slots": deepcopy(section_slots),
        "future_flow_years": deepcopy(future_flow_years),
        "long_term_luck_pillars": deepcopy(long_term_luck_pillars),
    }
    user_content = AI_READING_V2_USER_PROMPT_PREFIX + json.dumps(
        model_input,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=False,
        allow_nan=False,
    )
    messages = [
        {"role": "system", "content": AI_READING_V2_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
    model_output_schema = _build_model_output_schema(
        trusted_catalogs,
        future_year_count=len(future_flow_years),
        consultation_present=consultation_present,
        long_term_luck_count=len(trusted_attachments["long_term_luck_pillars"]),
    )

    return {
        "schema_version": AI_READING_REQUEST_V2_SCHEMA_VERSION,
        "version": AI_READING_REQUEST_V2_VERSION,
        "method": AI_READING_REQUEST_V2_METHOD,
        "status": AI_READING_REQUEST_V2_STATUS,
        "language": language,
        "tone": tone,
        "source_contracts": {
            "reading_context": {
                "schema_version": reading_context["schema_version"],
                "method": reading_context["method"],
                "version": reading_context["version"],
                "status": reading_context["status"],
            },
            "judgment_metadata": {
                "schema_version": judgment_metadata["schema_version"],
            },
        },
        "trusted_catalogs": trusted_catalogs,
        "trusted_attachments": trusted_attachments,
        "model_input": model_input,
        "messages": messages,
        "model_output_schema": model_output_schema,
        "validation": deepcopy(validation),
    }


__all__ = [
    "AI_READING_REQUEST_V2_FIELDS",
    "AI_READING_REQUEST_V2_METHOD",
    "AI_READING_REQUEST_V2_SCHEMA_VERSION",
    "AI_READING_REQUEST_V2_STATUS",
    "AI_READING_REQUEST_V2_VERSION",
    "AI_READING_V2_CLAIM_TYPES",
    "AI_READING_V2_LONG_TERM_LUCK_COUNT",
    "AI_READING_V2_DISCLAIMER",
    "AI_READING_V2_SECTION_SLOTS",
    "AI_READING_V2_SUPPORTED_LANGUAGES",
    "AI_READING_V2_SUPPORTED_TONES",
    "AI_READING_V2_SYSTEM_PROMPT",
    "AI_READING_V2_USER_PROMPT_PREFIX",
    "build_ai_reading_request_v2",
    "validate_ai_reading_prompt_inputs_v2",
]
