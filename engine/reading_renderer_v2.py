"""Deterministic customer-readable HTML renderer for ReadingProduct v2."""

from __future__ import annotations

from html import escape
from typing import Any

from engine.reading_pdf_v2 import (
    READING_PDF_V2_TEMPLATE_VERSION,
    ReadingPdfV2ValidationError,
)
from engine.reading_product_v2 import ReadingProductV2


READING_RENDERER_V2_VERSION = "reading_renderer_v2"
READING_RENDERER_V2_METHOD = "reading_renderer_v2"
READING_RENDERER_V2_STATUS = "ready"

_SECTION_TITLES = {
    "core_personality": "本質・性格",
    "career": "仕事・適職",
    "wealth": "金運",
    "relationships": "恋愛・人間関係",
    "health": "健康傾向",
    "current_luck": "現在大運",
    "future_flow": "今後の流れ",
    "advice": "総合アドバイス",
}

_CUSTOMER_SECTION_TITLES = {
    **_SECTION_TITLES,
    "health": "健康・生活",
}

_POSITION_LABELS = {
    "year": "年柱",
    "month": "月柱",
    "day": "日柱",
    "hour": "時柱",
}

_CONFIDENCE_LABELS = {
    "high": "高",
    "medium": "中",
    "low": "低",
}


def _dict(value: Any) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError("structured presentation source is invalid")
    return value


def _list(value: Any) -> list[Any]:
    if type(value) is not list:
        raise ValueError("structured presentation array is invalid")
    return value


def _text(value: Any, *, missing: str = "—") -> str:
    """Escape one primitive value; structured values are never stringified."""
    if value is None:
        return escape(missing)
    if type(value) is str:
        return escape(value)
    if type(value) in (int, float):
        return escape(str(value))
    raise ValueError("customer-visible value must be a primitive")


def _joined_text(values: Any, *, separator: str = "・", missing: str = "—") -> str:
    items = _list(values)
    if not items:
        return escape(missing)
    if any(type(item) is not str for item in items):
        raise ValueError("customer-visible list must contain strings")
    return separator.join(escape(item) for item in items)


def _yes_no(value: Any) -> str:
    if type(value) is not bool:
        raise ValueError("customer-visible boolean is invalid")
    return "あり" if value else "なし"


def _confidence(value: Any) -> str:
    if type(value) is not str or value not in _CONFIDENCE_LABELS:
        raise ValueError("confidence is invalid")
    return _CONFIDENCE_LABELS[value]


def _one_decimal(value: Any) -> str:
    """Format one already-calculated numeric value for customer display."""
    if type(value) not in (int, float):
        raise ValueError("customer-visible numeric value is invalid")
    return escape(f"{value:.1f}")


def _definition_rows(rows: list[tuple[str, str]], *, css_class: str = "facts") -> str:
    return (
        f'<dl class="{css_class}">'
        + "".join(
            f"<div><dt>{escape(label)}</dt><dd>{value}</dd></div>"
            for label, value in rows
        )
        + "</dl>"
    )


def _table(headers: list[str], rows: list[list[str]], *, css_class: str = "data-table") -> str:
    head = "".join(f"<th>{escape(header)}</th>" for header in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>"
        for row in rows
    )
    return (
        f'<div class="table-wrap"><table class="{css_class}">'
        f"<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>"
    )


def _paragraphs(values: Any, *, css_class: str = "fact-note") -> str:
    items = _list(values)
    if any(type(item) is not str for item in items):
        raise ValueError("paragraph list must contain strings")
    return "".join(f'<p class="{css_class}">{escape(item)}</p>' for item in items)


def _block(block: Any) -> str:
    item = _dict(block)
    text = item.get("text")
    if type(text) is not str:
        raise ValueError("AI reading text block is invalid")
    return f'<p class="reading-text">{escape(text)}</p>'


def _ai_section(section: dict[str, Any]) -> str:
    parts = [_block(section["summary"]), _block(section["detail"])]
    for field in ("evidence", "interpretation", "advice"):
        parts.extend(_block(value) for value in _list(section[field]))
    if section["section_id"] == "future_flow":
        for yearly_value in _list(section["yearly"]):
            yearly = _dict(yearly_value)
            parts.append(f'<h3 class="year-heading">{_text(yearly["year"])}年</h3>')
            parts.append(_block(yearly["summary"]))
            parts.append(_block(yearly["detail"]))
    if section["section_id"] == "future_flow":
        for yearly_value in _list(section["yearly"]):
            yearly = _dict(yearly_value)
            for field in ("title", "theme", "career", "wealth", "relationships", "caution"):
                if field in yearly:
                    parts.append(_block(yearly[field]))
            if isinstance(yearly.get("advice"), list):
                parts.extend(_block(value) for value in yearly["advice"])
    return "".join(parts)


def _customer_block_group(title: str, blocks: Any, css_class: str) -> str:
    values = _list(blocks)
    if not values:
        return ""
    return (
        f'<div class="reading-group {css_class}"><h3>{escape(title)}</h3>'
        + "".join(_block(value) for value in values)
        + "</div>"
    )


def _customer_ai_section(
    section: dict[str, Any],
    *,
    include_summary: bool = True,
) -> str:
    """Present every model-owned text block once under customer-facing labels."""

    parts: list[str] = []
    if include_summary:
        parts.append(
            '<div class="reading-group reading-lead"><h3>このテーマの要点</h3>'
            + _block(section["summary"])
            + "</div>"
        )
    parts.append(
        '<div class="reading-group"><h3>詳しい読み解き</h3>'
        + _block(section["detail"])
        + "</div>"
    )
    parts.append(
        _customer_block_group(
            "命式に表れていること", section["evidence"], "reading-evidence"
        )
    )
    parts.append(
        _customer_block_group(
            "日常に現れやすい傾向", section["interpretation"], "reading-interpretation"
        )
    )
    parts.append(
        _customer_block_group(
            "活かし方のヒント", section["advice"], "reading-advice"
        )
    )
    if section["section_id"] == "future_flow":
        yearly_parts = ['<div class="yearly-flow"><h3>年ごとの流れ</h3>']
        for yearly_value in _list(section["yearly"]):
            yearly = _dict(yearly_value)
            detail_parts = []
            for field, label in (("title", "この年のタイトル"), ("theme", "この年のテーマ"), ("career", "仕事・キャリア"), ("wealth", "金運・お金との向き合い方"), ("relationships", "人間関係"), ("caution", "注意したいこと")):
                if field in yearly:
                    detail_parts.append(f'<div class="year-detail"><h5>{escape(label)}</h5>{_block(yearly[field])}</div>')
            if isinstance(yearly.get("advice"), list):
                detail_parts.append('<div class="year-detail"><h5>この年を活かすポイント</h5>' + "".join(_block(item) for item in yearly["advice"]) + "</div>")
            yearly_parts.append(
                f'<div class="year-card"><h4>{_text(yearly["year"])}年</h4>'
                + "".join(detail_parts)
                + _block(yearly["summary"])
                + _block(yearly["detail"])
                + "</div>"
            )
        yearly_parts.append("</div>")
        parts.append("".join(yearly_parts))
    return "".join(parts)


def _section(title: str, body: str, section_id: str, *, css_class: str = "") -> str:
    class_attribute = f' class="{css_class}"' if css_class else ""
    return (
        f'<section id="{section_id}"{class_attribute}>'
        f"<h2>{escape(title)}</h2>{body}</section>"
    )


def _customer_cover(title: str) -> str:
    """Render a cover without exposing a redundant customer-visible heading."""

    return (
        '<section id="cover" class="cover customer-cover" aria-label="鑑定書表紙">'
        '<div class="cover-content"><p class="cover-kicker">八雲式 四柱推命</p>'
        f'<h1>{escape(title)}</h1>'
        '<p class="cover-subtitle">あなたの命式から読み解く、これからの道しるべ</p>'
        "</div></section>"
    )


def _render_basic_info(rc: dict[str, Any]) -> str:
    subject = _dict(rc["subject"])
    gender = subject["gender"]
    if gender == "male":
        gender_label = "男性"
    elif gender == "female":
        gender_label = "女性"
    else:
        gender_label = _text(gender)
    birth_time = (
        "出生時刻不明" if subject["birth_time"] is None else _text(subject["birth_time"])
    )
    return _definition_rows([
        ("生年月日", _text(subject["birth_date"])),
        ("出生時刻", birth_time),
        ("出生地", _text(subject["birth_place"])),
        ("性別", gender_label),
    ])


def _render_pillars(
    rc: dict[str, Any],
    engine_result: dict[str, Any],
) -> str:
    pillars = _dict(_dict(rc["chart"])["pillars"])
    engine_pillars = _dict(_dict(engine_result["chart"]))
    positions = ("year", "month", "day", "hour")
    entries: list[dict[str, Any] | None] = []
    engine_entries: list[dict[str, Any] | None] = []
    for position in positions:
        entry = pillars[position]
        entries.append(None if entry is None else _dict(entry))
        engine_entry = engine_pillars[position]
        engine_entries.append(None if engine_entry is None else _dict(engine_entry))

    def cells(field: str, *, list_value: bool = False, missing: str = "不明") -> list[str]:
        result: list[str] = []
        for entry in entries:
            if entry is None:
                result.append(escape(missing))
            elif list_value:
                result.append(_joined_text(entry[field], missing=missing))
            else:
                result.append(_text(entry[field], missing=missing))
        return result

    def hidden_ten_god_cells() -> list[str]:
        result: list[str] = []
        for entry, engine_entry in zip(entries, engine_entries):
            if entry is None:
                if engine_entry is not None:
                    raise ValueError("hour pillar sources are inconsistent")
                result.append(escape("不明"))
                continue
            if engine_entry is None:
                raise ValueError("pillar sources are inconsistent")
            hidden_stems = _list(entry["hidden_stems"])
            raw_ten_gods = _list(engine_entry["hidden_stem_ten_gods"])
            if len(hidden_stems) != len(raw_ten_gods):
                raise ValueError("hidden-stem sources are inconsistent")
            ten_gods: list[str] = []
            for stem, raw_ten_god in zip(hidden_stems, raw_ten_gods):
                ten_god = _dict(raw_ten_god)
                if ten_god.get("stem") != stem or type(ten_god.get("ten_god")) is not str:
                    raise ValueError("hidden-stem sources are inconsistent")
                ten_gods.append(ten_god["ten_god"])
            result.append(_joined_text(ten_gods))
        return result

    rows = [
        ["天干", *cells("stem")],
        ["地支", *cells("branch")],
        ["天干通変星", *cells("stem_ten_god", missing="—")],
        ["十二運", *cells("twelve_stage")],
        ["蔵干", *cells("hidden_stems", list_value=True)],
        ["蔵干通変星", *hidden_ten_god_cells()],
    ]
    return _table(["", "年柱", "月柱", "日柱", "時柱"], rows, css_class="pillar-table")


def _render_day_master(rc: dict[str, Any]) -> str:
    day_master = _dict(rc["day_master"])
    rows = [
        ("日主", _text(day_master["stem"])),
        ("日柱", _text(day_master["day_pillar"])),
    ]
    if day_master["element"] is not None:
        rows.append(("五行", _text(day_master["element"])))
    if day_master["yin_yang"] is not None:
        rows.append(("陰陽", _text(day_master["yin_yang"])))
    return _definition_rows(rows)


def _render_five_elements(rc: dict[str, Any]) -> str:
    five = _dict(rc["five_elements"])
    scores = _dict(five["weighted_scores"])
    rows = [[_text(element), _text(scores[element])] for element in ("木", "火", "土", "金", "水")]
    return _table(["五行", "算出値"], rows) + _definition_rows([
        ("最も強い五行", _text(five["strongest_element"])),
        ("最も弱い五行", _text(five["weakest_element"])),
    ], css_class="facts compact")


def _render_month_command_and_roots(rc: dict[str, Any]) -> str:
    command = _dict(rc["month_command"])
    basic = _dict(command["basic"])
    weighted = _dict(command["weighted"])
    seasonal = _dict(command["seasonal"])
    integrated = _dict(command["integrated"])
    roots = _dict(rc["roots"])
    root_basic = _dict(roots["basic"])
    root_weighted = _dict(roots["weighted"])
    month_body = '<h3>月令</h3>' + _definition_rows([
        ("月支", _text(basic["month_branch"])),
        ("月支の五行", _text(basic["month_element"])),
        ("日主との関係", _text(basic["relationship_label"])),
        ("季節状態", _text(seasonal["state"])),
        ("季節スコア", _text(seasonal["score"])),
        ("扶助割合", f'{_text(weighted["supporting_ratio"])}%'),
        ("消耗割合", f'{_text(weighted["draining_ratio"])}%'),
        ("月令総合スコア", _text(integrated["integrated_score"])),
    ])
    root_rows = []
    for root_value in _list(root_weighted["roots"]):
        root = _dict(root_value)
        position = root["position"]
        if position not in _POSITION_LABELS:
            raise ValueError("root position is invalid")
        root_rows.append([
            escape(_POSITION_LABELS[position]),
            _text(root["branch"]),
            _text(root["stem"]),
            _text(root["root_score"]),
        ])
    positions = _list(root_basic["root_positions"])
    if any(position not in _POSITION_LABELS for position in positions):
        raise ValueError("root positions are invalid")
    roots_body = '<h3>通根</h3>' + _definition_rows([
        ("通根", _yes_no(root_basic["has_root"])),
        ("通根数", _text(root_basic["root_count"])),
        ("通根位置", "・".join(escape(_POSITION_LABELS[position]) for position in positions) or "—"),
        ("通根総合スコア", _text(root_weighted["total_root_score"])),
    ])
    if root_rows:
        roots_body += _table(["位置", "地支", "根となる蔵干", "スコア"], root_rows)
    return month_body + roots_body


def _render_strength(rc: dict[str, Any]) -> str:
    strength = _dict(rc["strength"])
    return _definition_rows([
        ("判定", _text(strength["label"])),
        ("スコア", _text(strength["final_score"])),
        ("確度", _confidence(strength["confidence"])),
    ], css_class="facts highlight")


def _render_relations(rc: dict[str, Any]) -> str:
    relations = _dict(rc["relations"])
    pair_definitions = (
        ("clashes", "clashes", "六冲"),
        ("combinations", "combinations", "六合"),
        ("harms", "harms", "六害"),
        ("breaks", "breaks", "六破"),
    )
    items: list[str] = []
    for group_key, entries_key, label in pair_definitions:
        group = _dict(relations[group_key])
        for relation_value in _list(group[entries_key]):
            relation = _dict(relation_value)
            position_a = relation["position_a"]
            position_b = relation["position_b"]
            if position_a not in _POSITION_LABELS or position_b not in _POSITION_LABELS:
                raise ValueError("relation position is invalid")
            items.append(
                f'<li><strong>{escape(label)}</strong>：'
                f'{escape(_POSITION_LABELS[position_a])}「{_text(relation["branch_a"])}」― '
                f'{escape(_POSITION_LABELS[position_b])}「{_text(relation["branch_b"])}」'
                f'（{_text(relation["relation"])}）</li>'
            )

    trines = _dict(relations["trines"])
    for relation_value in _list(trines["trines"]):
        relation = _dict(relation_value)
        positions = [relation["position_a"], relation["position_b"], relation["position_c"]]
        if any(position not in _POSITION_LABELS for position in positions):
            raise ValueError("trine position is invalid")
        branches = [relation["branch_a"], relation["branch_b"], relation["branch_c"]]
        members = "・".join(
            f'{escape(_POSITION_LABELS[position])}「{_text(branch)}」'
            for position, branch in zip(positions, branches, strict=True)
        )
        items.append(
            f'<li><strong>三合</strong>：{members}'
            f'（{_text(relation["trine_name"])}・{_text(relation["element"])}）</li>'
        )

    punishments = _dict(relations["punishments"])
    for relation_value in _list(punishments["punishments"]):
        relation = _dict(relation_value)
        positions = _list(relation["positions"])
        branches = _list(relation["branches"])
        if len(positions) != len(branches) or any(
            position not in _POSITION_LABELS for position in positions
        ):
            raise ValueError("punishment positions are invalid")
        if any(type(branch) is not str for branch in branches):
            raise ValueError("punishment branches are invalid")
        members = "・".join(
            f'{escape(_POSITION_LABELS[position])}「{escape(branch)}」'
            for position, branch in zip(positions, branches, strict=True)
        )
        items.append(
            f'<li><strong>刑</strong>：{members}'
            f'（{_text(relation["punishment_type"])}・{_text(relation["punishment_name"])}）</li>'
        )
    if not items:
        return '<p class="empty-state">該当する干支関係はありません。</p>'
    return '<ul class="relation-list">' + "".join(items) + "</ul>"


def _factor_descriptions(values: Any, label: str) -> str:
    items = _list(values)
    if not items:
        return ""
    descriptions = []
    for value in items:
        item = _dict(value)
        if type(item.get("description")) is not str:
            raise ValueError("pattern factor description is invalid")
        descriptions.append(item["description"])
    return f'<h3>{escape(label)}</h3>' + _paragraphs(descriptions)


def _render_pattern(rc: dict[str, Any]) -> str:
    pattern = _dict(rc["pattern"])
    return _definition_rows([
        ("格局", _text(pattern["primary_pattern"])),
        ("成立スコア", _text(pattern["establishment_score"])),
        ("確度", _confidence(pattern["confidence"])),
    ], css_class="facts highlight") + _factor_descriptions(
        pattern["breaking_factors"], "注意要素"
    ) + _factor_descriptions(pattern["rescue_factors"], "補助要素")


def _render_useful_gods(rc: dict[str, Any]) -> str:
    useful = _dict(rc["useful_gods"])
    return _definition_rows([
        ("第一候補", _text(useful["primary_useful_element"])),
        ("その他の候補", _joined_text(useful["secondary_useful_elements"])),
        ("用神候補", _joined_text(useful["final_useful_elements"])),
        ("忌神側", _joined_text(useful["unfavorable_elements"])),
        ("確度", _confidence(useful["confidence"])),
    ], css_class="facts highlight")


def _render_current_luck(rc: dict[str, Any]) -> str:
    current = _dict(_dict(rc["luck"])["current_luck"])
    if current["has_current_luck"] is not True:
        return '<p class="empty-state">現在該当する大運はありません。</p>'
    pillar = _dict(current["current_pillar"])
    progress = _dict(current["progress"])
    return '<div class="calculated-facts"><h3>算出された現在大運</h3>' + _definition_rows([
        ("現在の大運", _text(pillar["ganzhi"])),
        ("通変星", _text(pillar["stem_ten_god"])),
        ("期間", f'約{_one_decimal(pillar["start_age"])}歳 ～ 約{_one_decimal(pillar["end_age"])}歳'),
        ("現在年齢", f'約{_one_decimal(current["exact_age"])}歳'),
        ("進行度", f'{_one_decimal(progress["progress_percent"])}%'),
        ("次の大運まで", f'約{_one_decimal(current["years_until_next_luck"])}年'),
    ], css_class="facts highlight") + "</div>"


def _render_annual_luck(rc: dict[str, Any]) -> str:
    annual = _dict(_dict(rc["luck"])["annual_luck"])
    return _definition_rows([
        ("対象年", f'{_text(annual["year"])}年'),
        ("歳運干支", _text(annual["ganzhi"])),
        ("天干", _text(annual["stem"])),
        ("地支", _text(annual["branch"])),
        ("通変星", _text(annual["stem_ten_god"])),
        ("十二運", _text(annual["twelve_stage"])),
    ], css_class="facts highlight")


def _render_long_term_luck(rc: dict[str, Any]) -> str:
    luck = _dict(_dict(rc["luck"])["luck_pillars"])
    rows = []
    for pillar_value in _list(luck["pillars"]):
        pillar = _dict(pillar_value)
        rows.append([
            f'約{_one_decimal(pillar["start_age"])}歳 ～ 約{_one_decimal(pillar["end_age"])}歳',
            _text(pillar["ganzhi"]),
            _text(pillar["stem_ten_god"]),
            _text(pillar["stem_element"]),
            _text(pillar["branch_element"]),
        ])
    return _definition_rows([
        ("大運の進行", _text(luck["direction_japanese"])),
        ("大運開始年齢", f'約{_one_decimal(luck["start_age"])}歳'),
    ]) + _table(["期間", "大運", "通変星", "天干五行", "地支五行"], rows)


def _render_customer_long_term_luck(rc: dict[str, Any]) -> str:
    """Present owner-calculated long-term luck without deriving an interpretation."""

    luck = _dict(_dict(rc["luck"])["luck_pillars"])
    rows = []
    for pillar_value in _list(luck["pillars"]):
        pillar = _dict(pillar_value)
        rows.append([
            f'第{_text(pillar["index"])}運',
            f'約{_one_decimal(pillar["start_age"])}歳 ～ 約{_one_decimal(pillar["end_age"])}歳',
            _text(pillar["ganzhi"]),
            _text(pillar["stem_ten_god"]),
            f'{_text(pillar["stem_element"])}・{_text(pillar["branch_element"])}',
        ])
    return (
        '<p class="section-intro">大運は、人生の長期的な流れをおよそ10年単位で確認するものです。'
        "ここでは命式から算出された巡りを、順番どおりに掲載します。</p>"
        + _definition_rows(
            [
                ("大運の進行", _text(luck["direction_japanese"])),
                ("大運開始年齢", f'約{_one_decimal(luck["start_age"])}歳'),
            ],
            css_class="facts highlight long-term-summary",
        )
        + _table(
            ["順番", "年齢帯", "大運", "天干通変星", "五行（天干・地支）"],
            rows,
            css_class="data-table long-term-table",
        )
    )


def _render_long_term_details(ai: dict[str, Any]) -> str:
    details = ai.get("long_term_luck", [])
    if not isinstance(details, list) or not details:
        return ""
    parts = ['<div class="long-term-details"><h3>大運から見る人生の流れ</h3>']
    for index, item in enumerate(details):
        if not isinstance(item, dict):
            continue
        age = f'{_one_decimal(item["start_age"])}歳 ～ {_one_decimal(item["end_age"])}歳'
        parts.append(
            '<article class="long-term-detail-card">'
            f'<h4>{escape(str(item["ganzhi"]))}（{escape(age)}）</h4>'
            f'<p class="long-term-detail-title">{_block(item["title"])}</p>'
            '<div class="long-term-detail-grid">'
            f'<div><h5>この10年のテーマ</h5>{_block(item["theme"])}</div>'
            f'<div><h5>仕事・社会との関わり</h5>{_block(item["career"])}</div>'
            f'<div><h5>金運・お金との向き合い方</h5>{_block(item["wealth"])}</div>'
            f'<div><h5>人間関係</h5>{_block(item["relationships"])}</div>'
            f'<div><h5>注意したいこと</h5>{_block(item["caution"])}</div>'
            '</div><h5>この時期を活かすポイント</h5><ul class="long-term-advice">'
            + "".join(f"<li>{_block(block)}</li>" for block in item["advice"])
            + '</ul></article>'
        )
    parts.append("</div>")
    return "".join(parts)


def _catalog_message(entry_value: Any, *, uncertainty: bool) -> str:
    entry = _dict(entry_value)
    value = entry["value"]
    if not uncertainty:
        if type(value) is not str:
            raise ValueError("warning value is invalid")
        return escape(value)
    detail = _dict(value)
    message = detail.get("message")
    if type(message) is not str:
        raise ValueError("uncertainty message is invalid")
    return escape(message)


def _render_notices(ai: dict[str, Any]) -> str:
    warnings = _list(ai["warnings"])
    uncertainty = _list(ai["uncertainty"])
    parts = ['<h3>注意事項</h3>']
    if warnings:
        parts.append('<ul class="notice-list warnings">')
        parts.extend(f"<li>{_catalog_message(entry, uncertainty=False)}</li>" for entry in warnings)
        parts.append("</ul>")
    else:
        parts.append('<p class="empty-state">個別の注意事項はありません。</p>')
    parts.append('<h3>不確実性について</h3>')
    if uncertainty:
        parts.append('<ul class="notice-list uncertainty">')
        parts.extend(f"<li>{_catalog_message(entry, uncertainty=True)}</li>" for entry in uncertainty)
        parts.append("</ul>")
    else:
        parts.append('<p class="empty-state">個別の不確実性情報はありません。</p>')
    disclaimer = ai["disclaimer"]
    if type(disclaimer) is not str:
        raise ValueError("disclaimer is invalid")
    parts.append('<h3>免責事項</h3>')
    parts.append(f'<p id="disclaimer" class="disclaimer">{escape(disclaimer)}</p>')
    return "".join(parts)


def _render_visible(value: dict[str, Any], title: str) -> str:
    engine_result = _dict(value["engine_result"])
    rc = _dict(value["reading_context"])
    ai = _dict(value["ai_reading"])
    sections: dict[str, dict[str, Any]] = {}
    for section_value in _list(ai["sections"]):
        section = _dict(section_value)
        section_id = section["section_id"]
        if type(section_id) is not str:
            raise ValueError("AI section identity is invalid")
        sections[section_id] = section

    visible: list[str] = [
        _section(
            "表紙",
            f'<div class="cover-content"><p class="cover-kicker">八雲式四柱推命</p>'
            f'<h1>{escape(title)}</h1><p class="cover-subtitle">命式と鑑定結果</p></div>',
            "cover",
            css_class="cover",
        ),
        _section("基本情報", _render_basic_info(rc), "subject"),
        _section("命式", _render_pillars(rc, engine_result), "chart"),
        _section("日主", _render_day_master(rc), "day-master"),
        _section("五行", _render_five_elements(rc), "five-elements"),
        _section("月令・通根", _render_month_command_and_roots(rc), "month-command"),
        _section("身強身弱", _render_strength(rc), "strength"),
        _section("干支関係", _render_relations(rc), "relations"),
        _section("格局", _render_pattern(rc), "pattern"),
        _section("用神", _render_useful_gods(rc), "useful-gods"),
    ]
    for section_id in ("core_personality", "career", "wealth", "relationships", "health"):
        visible.append(_section(_SECTION_TITLES[section_id], _ai_section(sections[section_id]), section_id))
    visible.append(_section(
        "現在大運",
        _render_current_luck(rc) + '<h3>鑑定</h3>' + _ai_section(sections["current_luck"]),
        "current-luck",
    ))
    visible.append(_section("現在歳運", _render_annual_luck(rc), "annual-luck"))
    visible.append(_section("今後の流れ", _ai_section(sections["future_flow"]), "future-flow"))
    visible.append(_section("長期大運", _render_long_term_luck(rc) + _render_long_term_details(ai), "long-term-luck"))
    visible.append(_section("総合アドバイス", _ai_section(sections["advice"]), "advice"))
    if ai["consultation_answer"] is not None:
        visible.append(_section("相談への回答", _block(ai["consultation_answer"]), "consultation-answer"))
    visible.append(_section("注意事項・免責", _render_notices(ai), "notices-disclaimer"))
    return "".join(visible)


def _customer_strength(rc: dict[str, Any]) -> str:
    strength = _dict(rc["strength"])
    return _definition_rows(
        [("身強・身弱", _text(strength["label"]))],
        css_class="facts highlight customer-key-fact",
    )


def _customer_pattern(rc: dict[str, Any]) -> str:
    pattern = _dict(rc["pattern"])
    return _definition_rows(
        [("格局", _text(pattern["primary_pattern"]))],
        css_class="facts highlight customer-key-fact",
    ) + _factor_descriptions(pattern["breaking_factors"], "注意要素") + _factor_descriptions(
        pattern["rescue_factors"], "補助要素"
    )


def _customer_useful_gods(rc: dict[str, Any]) -> str:
    useful = _dict(rc["useful_gods"])
    return _definition_rows(
        [
            ("第一候補", _text(useful["primary_useful_element"])),
            ("その他の候補", _joined_text(useful["secondary_useful_elements"])),
            ("用神候補", _joined_text(useful["final_useful_elements"])),
            ("忌神側", _joined_text(useful["unfavorable_elements"])),
        ],
        css_class="facts highlight",
    )


def _customer_calculation_details(rc: dict[str, Any]) -> str:
    command = _dict(_dict(rc["month_command"])["basic"])
    roots = _dict(_dict(rc["roots"])["basic"])
    positions = _list(roots["root_positions"])
    if any(position not in _POSITION_LABELS for position in positions):
        raise ValueError("root positions are invalid")
    return (
        '<details class="calculation-details"><summary>命式の算出詳細（月令・通根）</summary>'
        + _definition_rows(
            [
                ("月支", _text(command["month_branch"])),
                ("月支の五行", _text(command["month_element"])),
                ("通根", _yes_no(roots["has_root"])),
                ("通根位置", "・".join(escape(_POSITION_LABELS[position]) for position in positions) or "—"),
            ],
            css_class="facts compact",
        )
        + "</details>"
    )


def _customer_consultation(
    rc: dict[str, Any],
    ai: dict[str, Any],
    advice: dict[str, Any],
) -> str:
    raw_consultation = rc["consultation"]
    answer = ai["consultation_answer"]
    if raw_consultation is None:
        if answer is not None:
            raise ValueError("consultation answer is inconsistent")
        return ""
    consultation = _dict(raw_consultation)
    has_consultation = consultation["has_consultation"]
    if type(has_consultation) is not bool:
        raise ValueError("consultation status is invalid")
    if not has_consultation:
        if answer is not None:
            raise ValueError("consultation answer is inconsistent")
        return ""
    consultation_input = _dict(consultation["input"])
    concern = consultation_input.get("concern")
    desired_future = consultation_input.get("desired_future")
    if type(concern) is not str or not concern:
        raise ValueError("consultation input is invalid")
    if desired_future is not None and type(desired_future) is not str:
        raise ValueError("consultation desired future is invalid")
    consultation_text = f'<p class="consultation-text">{escape(concern)}</p>'
    if desired_future:
        consultation_text += (
            '<p class="consultation-text"><strong>望んでいる方向：</strong>'
            f"{escape(desired_future)}</p>"
        )
    if answer is None:
        raise ValueError("consultation answer is missing")
    return _section(
        "今回のご相談と鑑定結論",
        '<div class="consultation-card consultation-question"><h3>ご相談内容</h3>'
        + consultation_text
        + "</div>"
        + '<div class="consultation-card consultation-answer"><h3>相談への回答</h3>'
        + _block(answer)
        + "</div>"
        + '<div class="consultation-card consultation-guidance"><h3>まずお伝えしたい結論</h3>'
        + _block(advice["summary"])
        + "</div>",
        "consultation-conclusion",
        css_class="featured-section",
    )


def _render_customer_visible(value: dict[str, Any], title: str) -> str:
    """Render the immutable Product as a sales-ready customer reading."""

    engine_result = _dict(value["engine_result"])
    rc = _dict(value["reading_context"])
    ai = _dict(value["ai_reading"])
    sections: dict[str, dict[str, Any]] = {}
    for section_value in _list(ai["sections"]):
        section = _dict(section_value)
        section_id = section["section_id"]
        if type(section_id) is not str or section_id in sections:
            raise ValueError("AI section identity is invalid")
        sections[section_id] = section

    advice = sections["advice"]
    consultation = _customer_consultation(rc, ai, advice)
    has_consultation = bool(consultation)
    visible: list[str] = [_customer_cover(title)]
    if consultation:
        visible.append(consultation)
    visible.append(
        _section(
            "総合鑑定",
            '<div class="reading-group reading-lead">'
            + _block(ai["summary"])
            + "</div>",
            "reading-overview",
            css_class="reading-section overview-section",
        )
    )
    visible.extend(
        [
            _section(
                "あなたの命式",
                '<div class="presentation-subsection"><h3>基本情報</h3>'
                + _render_basic_info(rc)
                + "</div>"
                '<div class="presentation-subsection"><h3>四柱</h3>'
                + _render_pillars(rc, engine_result)
                + "</div>"
                '<div class="presentation-subsection"><h3>日主</h3>'
                + _render_day_master(rc)
                + "</div>"
                '<div class="presentation-subsection"><h3>五行</h3>'
                + _render_five_elements(rc)
                + "</div>"
                + _customer_calculation_details(rc),
                "customer-chart",
            ),
            _section(
                "命式の重要ポイント",
                '<div class="key-point"><h3>身強・身弱</h3>'
                + _customer_strength(rc)
                + "</div>"
                '<div class="key-point"><h3>格局</h3>'
                + _customer_pattern(rc)
                + "</div>"
                '<div class="key-point"><h3>用神</h3>'
                + _customer_useful_gods(rc)
                + "</div>"
                '<div class="key-point"><h3>干支関係</h3>'
                + _render_relations(rc)
                + "</div>",
                "key-points",
            ),
        ]
    )
    for section_id in ("core_personality", "career", "wealth", "relationships", "health"):
        visible.append(
            _section(
                _CUSTOMER_SECTION_TITLES[section_id],
                _customer_ai_section(sections[section_id]),
                section_id,
                css_class="reading-section",
            )
        )
    visible.extend(
        [
            _section(
                "現在の運勢",
                '<div class="presentation-subsection"><h3>現在大運</h3>'
                + _render_current_luck(rc)
                + _customer_ai_section(sections["current_luck"])
                + "</div>"
                '<div class="presentation-subsection"><h3>現在歳運</h3>'
                + _render_annual_luck(rc)
                + "</div>",
                "current-fortune",
            ),
            _section(
                "これから5年間",
                _customer_ai_section(sections["future_flow"]),
                "five-year-flow",
                css_class="reading-section",
            ),
            _section(
                "長期大運",
                _render_customer_long_term_luck(rc) + _render_long_term_details(ai),
                "long-term-luck",
                css_class="long-term-section",
            ),
            _section(
                "総合アドバイス",
                _customer_ai_section(advice, include_summary=not has_consultation),
                "advice",
                css_class="reading-section advice-section",
            ),
            _section(
                "注意事項・不確実性・免責",
                _render_notices(ai),
                "notices-disclaimer",
            ),
        ]
    )
    return "".join(visible)


_CSS = """
<style>
@page{size:A4;margin:15mm 14mm 17mm;}
*{box-sizing:border-box;}
html{color:#29231d;background:#fff;font-family:"Yu Mincho","Hiragino Mincho ProN","Noto Serif JP",serif;}
body{margin:0;font-size:10.5pt;line-height:1.78;overflow-wrap:anywhere;word-break:normal;}
section{margin:0 0 1.4rem;padding-top:.2rem;}
h1,h2,h3{break-after:avoid-page;page-break-after:avoid;line-height:1.35;}
h1{font-size:25pt;letter-spacing:.12em;margin:.45rem 0;color:#38291f;}
h2{font-size:16pt;margin:1.65rem 0 .8rem;padding:.3rem .55rem;border-left:5px solid #8a5a3b;border-bottom:1px solid #d9c9b9;color:#4a3021;}
h3{font-size:12pt;margin:1rem 0 .45rem;color:#6a412a;}
p{margin:.35rem 0 .7rem;white-space:pre-wrap;}
.cover{min-height:245mm;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;break-after:page;page-break-after:always;}
.cover h2{font-size:9pt;font-weight:400;letter-spacing:.3em;border:0;padding:0;margin:0 0 2.4rem;color:#8a7a6c;}
.cover-kicker{font-size:11pt;letter-spacing:.32em;color:#8a5a3b;}
.cover-subtitle{margin-top:1.3rem;letter-spacing:.22em;color:#6c6259;}
.facts{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.5rem .75rem;margin:.4rem 0 1rem;}
.facts>div{min-width:0;padding:.55rem .65rem;background:#f8f4ef;border:1px solid #e4d8ca;break-inside:avoid;page-break-inside:avoid;}
.facts dt{font-size:8.7pt;color:#75685d;margin-bottom:.12rem;}
.facts dd{margin:0;font-weight:600;overflow-wrap:anywhere;}
.facts.compact{margin-top:.75rem;}
.facts.highlight>div{background:#fffaf1;border-color:#d9c19f;}
.table-wrap{max-width:100%;margin:.5rem 0 1rem;overflow:visible;}
table{width:100%;border-collapse:collapse;table-layout:fixed;font-size:9.3pt;}
thead{display:table-header-group;}
tr{break-inside:avoid;page-break-inside:avoid;}
th,td{border:1px solid #d8cec4;padding:.38rem .32rem;text-align:center;vertical-align:middle;overflow-wrap:anywhere;}
th{background:#efe6dc;color:#4f3829;font-weight:700;}
tbody tr:nth-child(even){background:#fbf8f4;}
.pillar-table th:first-child,.pillar-table td:first-child{width:16%;font-weight:700;background:#f3ece4;}
.reading-text{font-size:10.8pt;line-height:1.9;margin:.35rem 0 .85rem;orphans:3;widows:3;}
.long-term-detail-card{margin:1rem 0 1.4rem;padding:1rem 1.1rem;background:#fffaf4;border:1px solid #dfcdbb;border-radius:4px;break-inside:avoid-page;page-break-inside:avoid;}
.long-term-detail-card h4{margin:.1rem 0 .7rem;color:#4a3021;font-size:13pt;}
.long-term-detail-title{font-weight:700;color:#6a412a;}
.long-term-detail-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.25rem .8rem;}
.long-term-detail-grid>div{break-inside:avoid;page-break-inside:avoid;}
.long-term-detail-card h5{margin:.55rem 0 .15rem;color:#6a412a;font-size:10.5pt;}
.long-term-advice{margin:.2rem 0 .2rem;padding-left:1.3rem;}
.calculated-facts{padding:.2rem .7rem .35rem;border:1px solid #d9c19f;background:#fffdf9;margin-bottom:1rem;}
.year-heading{padding:.3rem .55rem;background:#f3ece4;border-radius:2px;}
.notice-list{margin:.4rem 0 1rem;padding-left:1.4rem;}
.notice-list li{margin:.32rem 0;break-inside:avoid;page-break-inside:avoid;}
.relation-list{margin:.4rem 0 1rem;padding-left:1.4rem;}
.relation-list li{margin:.4rem 0;break-inside:avoid;page-break-inside:avoid;}
.warnings{border-left:4px solid #b16a35;background:#fff8ee;padding:.55rem .75rem .55rem 1.8rem;}
.uncertainty{border-left:4px solid #6a7893;background:#f5f7fb;padding:.55rem .75rem .55rem 1.8rem;}
.disclaimer{padding:.7rem .8rem;border:1px solid #ccc3bb;background:#f7f5f2;}
.fact-note{padding-left:.65rem;border-left:2px solid #c9b29d;}
.empty-state{color:#6f665e;}
@media print{
  body{-webkit-print-color-adjust:exact;print-color-adjust:exact;}
  a{color:inherit;text-decoration:none;}
  .table-wrap{overflow:visible;}
}
</style>"""

_CUSTOMER_CSS = """
<style>
.customer-cover .cover-kicker{font-size:13pt;letter-spacing:.2em;color:#6f452b;}
.customer-cover .cover-subtitle{max-width:32em;font-size:12pt;line-height:1.8;}
.featured-section{margin:0 0 2.4rem;padding:1.1rem 1.2rem 1.25rem;border:1px solid #d8c2a4;background:#fffaf2;}
.featured-section>h2{margin-top:.15rem;}
.consultation-card{margin:.75rem 0;padding:.8rem 1rem;background:#fff;border:1px solid #e3d5c4;break-inside:avoid-page;page-break-inside:avoid;}
.consultation-answer{border-left:5px solid #986538;}
.consultation-guidance{border-left:5px solid #b69764;background:#fffdf8;}
.consultation-text{font-size:10.5pt;line-height:1.85;}
.presentation-subsection,.key-point{margin:.85rem 0 1.25rem;}
.calculation-details{margin:1rem 0;padding:.65rem .8rem;border:1px solid #ddd1c4;background:#faf7f3;color:#50473f;}
.calculation-details summary{cursor:pointer;font-weight:700;color:#6a513e;}
.reading-section{margin-bottom:2rem;}
.reading-group{margin:.7rem 0 1rem;padding:.75rem .9rem;border-left:3px solid #cbb59c;background:#fcfaf7;}
.reading-group h3{margin-top:0;}
.reading-lead{border-left-color:#8a5a3b;background:#fff9ef;}
.reading-advice{border-left-color:#a78550;background:#fffdf6;}
.yearly-flow{margin-top:1.2rem;}
.year-card{margin:.65rem 0;padding:.65rem .85rem;border:1px solid #ddd1c4;background:#fff;break-inside:avoid-page;page-break-inside:avoid;}
.year-card h4{margin:.05rem 0 .45rem;font-size:11.5pt;color:#6a412a;}
.year-detail{margin:.45rem 0 .7rem;padding:.45rem .6rem;border-left:3px solid #d5bea0;background:#fffdf9;}
.year-detail h5{margin:.05rem 0 .25rem;color:#6a513e;font-size:10.5pt;}
.advice-section{padding:.2rem .8rem .8rem;border:1px solid #d9c19f;background:#fffaf1;}
.section-intro{margin:.3rem 0 1rem;padding:.65rem .8rem;border-left:3px solid #b69764;background:#fcfaf6;color:#54493f;}
.long-term-table th:nth-child(1){width:10%;}.long-term-table th:nth-child(2){width:25%;}.long-term-table th:nth-child(3){width:13%;}
.long-term-section{margin-bottom:2rem;}
#current-fortune > .presentation-subsection:first-of-type{break-inside:auto;page-break-inside:auto;}
@media print{
  #current-fortune{break-before:page!important;page-break-before:always!important;}
  #current-fortune > h2{break-before:auto!important;page-break-before:auto!important;}
}
@media(max-width:680px){
  .featured-section,.consultation-card,.reading-group,.advice-section{padding-left:.7rem;padding-right:.7rem;}
  .customer-cover .cover-subtitle{font-size:10.5pt;}
}
@media print{
  .featured-section,.consultation-card,.presentation-subsection,.key-point,.reading-group,.year-card,.facts>div,tr{break-inside:avoid-page;page-break-inside:avoid;}
  .reading-group{background:#fff;}
  .long-term-table{font-size:9pt;}
  .calculation-details:not([open])>:not(summary){display:block!important;}
  .calculation-details summary{display:none;}
}
</style>"""


def render_reading_product_v2_html(
    product: ReadingProductV2,
    *,
    document_title: str | None = None,
    include_css: bool = True,
) -> str:
    if not isinstance(product, ReadingProductV2):
        raise ReadingPdfV2ValidationError("product must be ReadingProductV2")
    if type(include_css) is not bool:
        raise ReadingPdfV2ValidationError("include_css must be a built-in boolean")
    if document_title is None:
        title = "八雲式四柱推命 鑑定書"
    elif type(document_title) is str and document_title.strip():
        title = document_title
    else:
        raise ReadingPdfV2ValidationError("document_title is invalid")
    try:
        value = ReadingProductV2(product.to_dict()).to_dict()
        metadata = _dict(value["metadata"])
        meta = (
            ("engine-version", metadata["engine_version"]),
            ("reading-context-schema", metadata["reading_context_schema"]),
            ("ai-reading-version-method", f'{metadata["ai_reading_version"]}:{metadata["ai_generation_method"]}'),
            ("quality-gate-version-decision", f'{metadata["quality_gate_version"]}:{metadata["quality_status"]}'),
            ("reading-product-version", metadata["product_version"]),
            ("pdf-template-version", READING_PDF_V2_TEMPLATE_VERSION),
            ("source-bundle-sha256", metadata["source_bundle_sha256"]),
        )
        for _, content in meta:
            if type(content) is not str:
                raise ValueError("provenance metadata is invalid")
        meta_html = "".join(
            f'<meta name="{name}" content="{escape(content, quote=True)}">'
            for name, content in meta
        )
        visible = _render_visible(value, title)
    except ReadingPdfV2ValidationError:
        raise
    except Exception:
        raise ReadingPdfV2ValidationError("product presentation data is invalid") from None
    css = _CSS if include_css else ""
    return (
        '<!DOCTYPE html><html lang="ja"><head><meta charset="UTF-8">'
        f"<title>{escape(title)}</title>{meta_html}{css}</head><body>"
        f"{visible}</body></html>"
    )


def render_customer_reading_product_v2_html(
    product: ReadingProductV2,
    *,
    document_title: str | None = None,
    include_css: bool = True,
) -> str:
    """Render the Product for Customer Web and browser-print delivery."""

    if not isinstance(product, ReadingProductV2):
        raise ReadingPdfV2ValidationError("product must be ReadingProductV2")
    if type(include_css) is not bool:
        raise ReadingPdfV2ValidationError("include_css must be a built-in boolean")
    if document_title is None:
        title = "四柱推命鑑定書"
    elif type(document_title) is str and document_title.strip():
        title = document_title
    else:
        raise ReadingPdfV2ValidationError("document_title is invalid")
    try:
        value = ReadingProductV2(product.to_dict()).to_dict()
        metadata = _dict(value["metadata"])
        meta = (
            ("engine-version", metadata["engine_version"]),
            ("reading-context-schema", metadata["reading_context_schema"]),
            ("ai-reading-version-method", f'{metadata["ai_reading_version"]}:{metadata["ai_generation_method"]}'),
            ("quality-gate-version-decision", f'{metadata["quality_gate_version"]}:{metadata["quality_status"]}'),
            ("reading-product-version", metadata["product_version"]),
            ("pdf-template-version", READING_PDF_V2_TEMPLATE_VERSION),
            ("source-bundle-sha256", metadata["source_bundle_sha256"]),
        )
        for _, content in meta:
            if type(content) is not str:
                raise ValueError("provenance metadata is invalid")
        meta_html = "".join(
            f'<meta name="{name}" content="{escape(content, quote=True)}">'
            for name, content in meta
        )
        visible = _render_customer_visible(value, title)
    except ReadingPdfV2ValidationError:
        raise
    except Exception:
        raise ReadingPdfV2ValidationError("product presentation data is invalid") from None
    css = _CSS + _CUSTOMER_CSS if include_css else ""
    return (
        '<!DOCTYPE html><html lang="ja"><head><meta charset="UTF-8">'
        f"<title>{escape(title)}</title>{meta_html}{css}</head><body>"
        f"{visible}</body></html>"
    )


__all__ = [
    "READING_RENDERER_V2_VERSION",
    "READING_RENDERER_V2_METHOD",
    "READING_RENDERER_V2_STATUS",
    "render_customer_reading_product_v2_html",
    "render_reading_product_v2_html",
]
