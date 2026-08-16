"""
tests/test_reading_decade_luck.py

四柱推命鑑定書 v1.1
大運（10年運）AI鑑定生成レイヤーの単体テスト。
"""

from __future__ import annotations

import json
from copy import deepcopy

import pytest

import engine.reading_decade_luck as decade
from engine.reading_decade_luck import (
    DEFAULT_DECADE_MAX_OUTPUT_TOKENS,
    DEFAULT_PERIOD_COUNT,
    READING_DECADE_LUCK_METHOD,
    READING_DECADE_LUCK_STATUS,
    READING_DECADE_LUCK_VERSION,
    ReadingDecadeLuckDataError,
    ReadingDecadeLuckResponseError,
    ReadingDecadeLuckResult,
    build_decade_interpretation_context,
    build_decade_luck_facts,
    build_decade_luck_output_schema,
    build_decade_luck_payload,
    build_decade_luck_prompt,
    generate_decade_luck_dict,
    generate_decade_luck_reading,
    get_reading_decade_luck_metadata,
    merge_decade_luck_result,
    parse_decade_luck_json,
    select_decade_luck_periods,
    validate_decade_luck_response,
)


def make_luck_pillar(index, ganzhi, stem, branch, stem_element, branch_element, stem_ten_god, start_age, end_age):
    return {
        "index": index,
        "ganzhi": ganzhi,
        "stem": stem,
        "branch": branch,
        "stem_element": stem_element,
        "branch_element": branch_element,
        "stem_ten_god": stem_ten_god,
        "start_age": start_age,
        "end_age": end_age,
        "stem_useful_relation": {
            "relation": "supportive" if stem_element in ("金", "水", "土") else "unfavorable",
        },
        "branch_useful_relation": {
            "relation": "supportive" if branch_element in ("金", "水", "土") else "unfavorable",
        },
    }


def make_reading_context():
    pillars = [
        make_luck_pillar(1, "辛卯", "辛", "卯", "金", "木", "正財", 7.0, 17.0),
        make_luck_pillar(2, "壬辰", "壬", "辰", "水", "土", "偏官", 17.0, 27.0),
        make_luck_pillar(3, "癸巳", "癸", "巳", "水", "火", "正官", 27.0, 37.0),
        make_luck_pillar(4, "甲午", "甲", "午", "木", "火", "偏印", 37.0, 47.0),
        make_luck_pillar(5, "乙未", "乙", "未", "木", "土", "印綬", 47.0, 57.0),
        make_luck_pillar(6, "丙申", "丙", "申", "火", "金", "比肩", 57.0, 67.0),
        make_luck_pillar(7, "丁酉", "丁", "酉", "火", "金", "劫財", 67.0, 77.0),
        make_luck_pillar(8, "戊戌", "戊", "戌", "土", "土", "食神", 77.0, 87.0),
        make_luck_pillar(9, "己亥", "己", "亥", "土", "水", "傷官", 87.0, 97.0),
        make_luck_pillar(10, "庚子", "庚", "子", "金", "水", "偏財", 97.0, 107.0),
    ]

    return {
        "subject": {
            "name": "田中浩二",
            "birth_date": "1976-02-14",
            "birth_time": "10:20",
            "birth_place": "福岡県",
            "gender": "男性",
        },
        "day_master": {
            "stem": "丙",
            "element": "火",
            "yin_yang": "陽",
            "day_pillar": "丙申",
        },
        "five_elements": {
            "weighted_scores": {"木": 0.9, "火": 2.9, "土": 1.1, "金": 1.7, "水": 1.4},
            "strongest_element": "火",
            "weakest_element": "木",
        },
        "strength": {
            "technical_label": "strong",
            "label": "身強",
            "final_score": 69.2,
            "confidence": "high",
        },
        "pattern": {
            "primary_pattern": "偏印格",
            "technical_pattern": "偏印格",
            "overall_judgment": "established",
            "confidence": "high",
        },
        "useful_gods": {
            "primary_useful_element": "金",
            "secondary_useful_elements": ["水", "土"],
            "final_useful_elements": ["金", "水", "土"],
            "unfavorable_elements": ["火", "木"],
            "confidence": "high",
        },
        "luck": {
            "luck_pillars": {
                "direction": "forward",
                "direction_japanese": "順行",
                "start_age": 7.0,
                "start_age_detail": {"years": 7, "months": 0, "days": 0},
                "pillar_count": 10,
                "pillars": pillars,
                "method": "luck_pillars_v2",
                "status": "calculated",
            },
            "current_luck": {
                "has_current_luck": True,
                "current_pillar": deepcopy(pillars[4]),
            },
        },
    }


def make_consultation_context():
    return {
        "primary_focus": "career",
        "current_concern": "現職に残るか環境を変えるか迷っている。",
        "ideal_future": "自分の強みを活かして長期的に安定した働き方をしたい。",
    }


def make_ai_period(index):
    return {
        "index": index,
        "title": f"第{index}大運のテーマ",
        "theme": f"第{index}大運では、長期的な流れを見ながら自分の強みを活かすことがテーマです。",
        "career": "仕事では役割や仕組みを整え、長期的な成果につなげる意識が役立ちます。",
        "wealth": "金運では短期的な勢いより、収支や資源配分を丁寧に管理することが大切です。",
        "relationships": "人間関係では相手との認識を確認しながら、無理のない関係を築くことが役立ちます。",
        "caution": "一つの考えに固執せず、状況に応じて軌道修正する余地を残してください。",
        "advice": [
            "半年ごとに目標と現状を見直す。",
            "重要な判断は記録を残して比較する。",
        ],
    }


def make_ai_response_dict(indexes=(5, 6, 7, 8, 9)):
    return {
        "overview": "現在から先の大運を見ると、基盤を整える時期から、社会的役割や資源配分を見直す時期へ段階的に移っていく流れがあります。",
        "periods": [make_ai_period(index) for index in indexes],
    }


def make_facts():
    return build_decade_luck_facts(make_reading_context())


# ============================================================
# 1. Period selection
# ============================================================


def test_selects_current_plus_future_four_periods():
    selected = select_decade_luck_periods(make_reading_context())
    assert len(selected) == 5
    assert [item["index"] for item in selected] == [5, 6, 7, 8, 9]


def test_selected_ganzhi_order_is_preserved():
    selected = select_decade_luck_periods(make_reading_context())
    assert [item["ganzhi"] for item in selected] == ["乙未", "丙申", "丁酉", "戊戌", "己亥"]


def test_current_index_has_priority_over_ganzhi():
    context = make_reading_context()
    context["luck"]["current_luck"]["current_pillar"]["ganzhi"] = "辛卯"
    selected = select_decade_luck_periods(context)
    assert selected[0]["index"] == 5


def test_falls_back_to_current_ganzhi_when_index_missing():
    context = make_reading_context()
    context["luck"]["current_luck"]["current_pillar"].pop("index")
    selected = select_decade_luck_periods(context)
    assert selected[0]["ganzhi"] == "乙未"


def test_supports_legacy_current_luck_pillar_key():
    context = make_reading_context()
    current = context["luck"]["current_luck"].pop("current_pillar")
    context["luck"]["current_luck"]["current_luck_pillar"] = current
    selected = select_decade_luck_periods(context)
    assert selected[0]["index"] == 5


def test_end_of_luck_list_returns_available_periods_only():
    context = make_reading_context()
    context["luck"]["current_luck"]["current_pillar"] = deepcopy(
        context["luck"]["luck_pillars"]["pillars"][8]
    )
    selected = select_decade_luck_periods(context, count=5)
    assert [item["index"] for item in selected] == [9, 10]


def test_invalid_count_type_is_rejected():
    with pytest.raises(TypeError):
        select_decade_luck_periods(make_reading_context(), count="5")


def test_non_positive_count_is_rejected():
    with pytest.raises(ValueError):
        select_decade_luck_periods(make_reading_context(), count=0)


def test_missing_luck_pillars_is_rejected():
    context = make_reading_context()
    context["luck"].pop("luck_pillars")
    with pytest.raises(ReadingDecadeLuckDataError):
        select_decade_luck_periods(context)


def test_empty_luck_pillar_list_is_rejected():
    context = make_reading_context()
    context["luck"]["luck_pillars"]["pillars"] = []
    with pytest.raises(ReadingDecadeLuckDataError):
        select_decade_luck_periods(context)


def test_current_luck_not_found_is_rejected():
    context = make_reading_context()
    context["luck"]["current_luck"]["current_pillar"] = {"index": 999, "ganzhi": "存在しない"}
    with pytest.raises(ReadingDecadeLuckDataError):
        select_decade_luck_periods(context)


# ============================================================
# 2. Protected facts / interpretation context
# ============================================================


def test_build_facts_contains_five_periods():
    facts = make_facts()
    assert facts["period_count"] == 5
    assert len(facts["periods"]) == 5


def test_build_facts_preserves_engine_values():
    first = make_facts()["periods"][0]
    assert first["index"] == 5
    assert first["ganzhi"] == "乙未"
    assert first["stem_ten_god"] == "印綬"
    assert first["start_age"] == 47.0
    assert first["end_age"] == 57.0
    assert first["stem_element"] == "木"
    assert first["branch_element"] == "土"


def test_build_facts_preserves_direction():
    facts = make_facts()
    assert facts["direction"] == "forward"
    assert facts["direction_japanese"] == "順行"
    assert facts["start_age"] == 7.0


def test_build_facts_does_not_mutate_context():
    context = make_reading_context()
    before = deepcopy(context)
    build_decade_luck_facts(context)
    assert context == before


def test_interpretation_context_contains_only_needed_domains():
    context = build_decade_interpretation_context(make_reading_context())
    assert set(context) == {
        "subject",
        "day_master",
        "five_elements",
        "strength",
        "pattern",
        "useful_gods",
    }


def test_interpretation_context_is_independent_copy():
    source = make_reading_context()
    extracted = build_decade_interpretation_context(source)
    extracted["day_master"]["stem"] = "変更"
    assert source["day_master"]["stem"] == "丙"


# ============================================================
# 3. JSON schema / prompt / payload
# ============================================================


def test_schema_requires_overview_and_periods():
    schema = build_decade_luck_output_schema(period_count=5)
    assert schema["required"] == ["overview", "periods"]


def test_schema_requires_exact_period_count():
    schema = build_decade_luck_output_schema(period_count=5)
    periods = schema["properties"]["periods"]
    assert periods["minItems"] == 5
    assert periods["maxItems"] == 5


def test_schema_does_not_ask_ai_for_protected_facts():
    schema = build_decade_luck_output_schema(period_count=5)
    properties = schema["properties"]["periods"]["items"]["properties"]
    for protected in (
        "ganzhi",
        "stem",
        "branch",
        "start_age",
        "end_age",
        "stem_ten_god",
        "stem_element",
        "branch_element",
    ):
        assert protected not in properties


def test_schema_requires_interpretation_fields():
    schema = build_decade_luck_output_schema(period_count=5)
    required = schema["properties"]["periods"]["items"]["required"]
    assert required == [
        "index",
        "title",
        "theme",
        "career",
        "wealth",
        "relationships",
        "caution",
        "advice",
    ]


def test_invalid_schema_period_count_is_rejected():
    with pytest.raises(ValueError):
        build_decade_luck_output_schema(period_count=0)


def test_prompt_contains_stable_control_terms():
    prompt = build_decade_luck_prompt(make_reading_context())
    instructions = prompt["instructions"]
    assert "periods" in instructions
    assert "index" in instructions
    assert "JSON" in instructions


def test_prompt_contains_calculated_luck_facts():
    input_text = build_decade_luck_prompt(make_reading_context())["input"]
    for value in ("乙未", "丙申", "丁酉", "戊戌", "己亥"):
        assert value in input_text


def test_prompt_contains_consultation_context():
    prompt = build_decade_luck_prompt(
        make_reading_context(),
        consultation_context=make_consultation_context(),
    )
    assert "現職に残るか環境を変えるか迷っている。" in prompt["input"]


def test_prompt_does_not_mutate_inputs():
    context = make_reading_context()
    consultation = make_consultation_context()
    context_before = deepcopy(context)
    consultation_before = deepcopy(consultation)
    build_decade_luck_prompt(context, consultation_context=consultation)
    assert context == context_before
    assert consultation == consultation_before


def test_payload_uses_structured_outputs():
    result = build_decade_luck_payload(make_reading_context(), model="test-model")
    payload = result["payload"]
    assert payload["model"] == "test-model"
    assert payload["text"]["format"]["type"] == "json_schema"
    assert payload["text"]["format"]["strict"] is True


def test_payload_has_five_period_facts():
    result = build_decade_luck_payload(make_reading_context(), model="test-model")
    assert result["period_count"] == 5
    assert [item["index"] for item in result["facts"]["periods"]] == [5, 6, 7, 8, 9]


def test_payload_preserves_max_output_tokens():
    result = build_decade_luck_payload(
        make_reading_context(),
        model="test-model",
        max_output_tokens=4321,
    )
    assert result["payload"]["max_output_tokens"] == 4321


def test_payload_rejects_non_positive_max_output_tokens():
    with pytest.raises(ValueError):
        build_decade_luck_payload(
            make_reading_context(),
            model="test-model",
            max_output_tokens=0,
        )


# ============================================================
# 4. JSON parsing / response validation
# ============================================================


def test_parse_valid_json():
    source = make_ai_response_dict()
    parsed = parse_decade_luck_json(json.dumps(source, ensure_ascii=False))
    assert parsed == source


def test_parse_rejects_non_string():
    with pytest.raises(ReadingDecadeLuckResponseError):
        parse_decade_luck_json({})


def test_parse_rejects_empty_string():
    with pytest.raises(ReadingDecadeLuckResponseError):
        parse_decade_luck_json("   ")


def test_parse_rejects_invalid_json():
    with pytest.raises(ReadingDecadeLuckResponseError):
        parse_decade_luck_json("{not-json}")


def test_parse_rejects_non_object_json():
    with pytest.raises(ReadingDecadeLuckResponseError):
        parse_decade_luck_json("[]")


def test_validate_accepts_valid_response():
    validated = validate_decade_luck_response(make_ai_response_dict(), make_facts())
    assert validated["valid"] is True
    assert len(validated["periods"]) == 5


def test_validate_rejects_wrong_period_count():
    parsed = make_ai_response_dict(indexes=(5, 6, 7, 8))
    with pytest.raises(ReadingDecadeLuckResponseError):
        validate_decade_luck_response(parsed, make_facts())


def test_validate_rejects_wrong_index():
    parsed = make_ai_response_dict()
    parsed["periods"][2]["index"] = 999
    with pytest.raises(ReadingDecadeLuckResponseError):
        validate_decade_luck_response(parsed, make_facts())


def test_validate_rejects_missing_text_field():
    parsed = make_ai_response_dict()
    parsed["periods"][0]["career"] = ""
    with pytest.raises(ReadingDecadeLuckResponseError):
        validate_decade_luck_response(parsed, make_facts())


def test_validate_rejects_advice_not_list():
    parsed = make_ai_response_dict()
    parsed["periods"][0]["advice"] = "文字列"
    with pytest.raises(ReadingDecadeLuckResponseError):
        validate_decade_luck_response(parsed, make_facts())


def test_validate_rejects_too_few_advice_items():
    parsed = make_ai_response_dict()
    parsed["periods"][0]["advice"] = ["1件だけ"]
    with pytest.raises(ReadingDecadeLuckResponseError):
        validate_decade_luck_response(parsed, make_facts())


def test_validate_rejects_too_many_advice_items():
    parsed = make_ai_response_dict()
    parsed["periods"][0]["advice"] = ["1", "2", "3", "4"]
    with pytest.raises(ReadingDecadeLuckResponseError):
        validate_decade_luck_response(parsed, make_facts())


# ============================================================
# 5. Merge protected facts
# ============================================================


def test_merge_combines_ai_text_with_engine_facts():
    facts = make_facts()
    validated = validate_decade_luck_response(make_ai_response_dict(), facts)
    merged = merge_decade_luck_result(validated, facts)
    first = merged["periods"][0]
    assert first["ganzhi"] == "乙未"
    assert first["start_age"] == 47.0
    assert first["end_age"] == 57.0
    assert first["title"] == "第5大運のテーマ"


def test_merge_engine_facts_override_ai_protected_fields():
    facts = make_facts()
    ai = make_ai_response_dict()
    ai["periods"][0].update(
        {
            "ganzhi": "偽干支",
            "start_age": 999,
            "end_age": 1000,
            "stem_ten_god": "偽通変星",
            "stem_element": "偽五行",
            "branch_element": "偽五行",
        }
    )
    validated = validate_decade_luck_response(ai, facts)
    validated["periods"][0].update(
        {
            "ganzhi": "偽干支",
            "start_age": 999,
            "end_age": 1000,
            "stem_ten_god": "偽通変星",
        }
    )
    merged = merge_decade_luck_result(validated, facts)
    first = merged["periods"][0]
    assert first["ganzhi"] == "乙未"
    assert first["start_age"] == 47.0
    assert first["end_age"] == 57.0
    assert first["stem_ten_god"] == "印綬"
    assert first["stem_element"] == "木"
    assert first["branch_element"] == "土"


def test_merge_preserves_direction_metadata():
    facts = make_facts()
    validated = validate_decade_luck_response(make_ai_response_dict(), facts)
    merged = merge_decade_luck_result(validated, facts)
    assert merged["direction"] == "forward"
    assert merged["direction_japanese"] == "順行"
    assert merged["start_age"] == 7.0


def test_merge_rejects_different_period_counts():
    facts = make_facts()
    validated = {"overview": "概要", "periods": [make_ai_period(5)]}
    with pytest.raises(ReadingDecadeLuckResponseError):
        merge_decade_luck_result(validated, facts)


# ============================================================
# 6. Result object
# ============================================================


def test_result_to_dict_is_serializable():
    result = ReadingDecadeLuckResult(
        overview="概要",
        periods=({"index": 5, "ganzhi": "乙未"},),
        model="test-model",
        response_id="resp_test",
        response_status="completed",
        usage={"input_tokens": 100, "output_tokens": 200},
    )
    data = result.to_dict()
    loaded = json.loads(json.dumps(data, ensure_ascii=False))
    assert loaded["periods"][0]["ganzhi"] == "乙未"


def test_result_to_dict_returns_independent_period_copy():
    result = ReadingDecadeLuckResult(
        overview="概要",
        periods=({"index": 5, "ganzhi": "乙未"},),
        model="test-model",
        response_id=None,
        response_status="completed",
        usage={},
    )
    data = result.to_dict()
    data["periods"][0]["ganzhi"] = "変更"
    assert result.periods[0]["ganzhi"] == "乙未"


# ============================================================
# 7. Fake generation
# ============================================================


def configure_fake_generation(monkeypatch):
    response_payload = make_ai_response_dict()

    class FakeClient:
        pass

    fake_client = FakeClient()
    captured = {}

    def fake_execute(client, payload):
        assert client is fake_client
        captured["payload"] = deepcopy(payload)
        return {"fake": True}

    def fake_raise_if_unusable(response):
        assert response == {"fake": True}

    def fake_extract_output_text(response):
        assert response == {"fake": True}
        return json.dumps(response_payload, ensure_ascii=False)

    def fake_response_metadata(response):
        assert response == {"fake": True}
        return {
            "response_id": "resp_decade_test",
            "response_status": "completed",
            "usage": {"input_tokens": 123, "output_tokens": 456},
        }

    monkeypatch.setattr(decade, "_execute_responses_create", fake_execute)
    monkeypatch.setattr(decade, "_raise_if_unusable_response", fake_raise_if_unusable)
    monkeypatch.setattr(decade, "_extract_output_text", fake_extract_output_text)
    monkeypatch.setattr(decade, "_response_metadata", fake_response_metadata)

    return fake_client, captured


def test_generate_decade_luck_reading_with_fake_api(monkeypatch):
    client, captured = configure_fake_generation(monkeypatch)
    result = generate_decade_luck_reading(
        make_reading_context(),
        consultation_context=make_consultation_context(),
        client=client,
        model="test-model",
    )
    assert isinstance(result, ReadingDecadeLuckResult)
    assert result.model == "test-model"
    assert result.response_id == "resp_decade_test"
    assert result.response_status == "completed"
    assert len(result.periods) == 5
    assert result.periods[0]["ganzhi"] == "乙未"
    assert captured["payload"]["text"]["format"]["strict"] is True


def test_generate_decade_luck_dict_with_fake_api(monkeypatch):
    client, _ = configure_fake_generation(monkeypatch)
    result = generate_decade_luck_dict(
        make_reading_context(),
        client=client,
        model="test-model",
    )
    assert isinstance(result, dict)
    assert result["periods"][0]["ganzhi"] == "乙未"
    assert result["generation"]["response_id"] == "resp_decade_test"


def test_generation_does_not_mutate_reading_context(monkeypatch):
    client, _ = configure_fake_generation(monkeypatch)
    context = make_reading_context()
    before = deepcopy(context)
    generate_decade_luck_reading(context, client=client, model="test-model")
    assert context == before


# ============================================================
# 8. Metadata / final gate
# ============================================================


def test_metadata():
    metadata = get_reading_decade_luck_metadata()
    assert metadata["version"] == READING_DECADE_LUCK_VERSION
    assert metadata["method"] == READING_DECADE_LUCK_METHOD
    assert metadata["status"] == READING_DECADE_LUCK_STATUS
    assert metadata["default_period_count"] == DEFAULT_PERIOD_COUNT
    assert metadata["default_max_output_tokens"] == DEFAULT_DECADE_MAX_OUTPUT_TOKENS
    assert metadata["recalculates_astrology"] is False
    assert metadata["ai_controls_protected_facts"] is False


def test_reading_decade_luck_v1_final_gate(monkeypatch):
    client, captured = configure_fake_generation(monkeypatch)
    context = make_reading_context()
    before = deepcopy(context)

    selected = select_decade_luck_periods(context)
    assert [item["index"] for item in selected] == [5, 6, 7, 8, 9]

    facts = build_decade_luck_facts(context)
    assert [item["ganzhi"] for item in facts["periods"]] == ["乙未", "丙申", "丁酉", "戊戌", "己亥"]

    result = generate_decade_luck_reading(
        context,
        consultation_context=make_consultation_context(),
        client=client,
        model="test-model",
    )

    assert result.status == "completed"
    assert len(result.periods) == 5
    assert [item["index"] for item in result.periods] == [5, 6, 7, 8, 9]
    assert [item["ganzhi"] for item in result.periods] == ["乙未", "丙申", "丁酉", "戊戌", "己亥"]
    assert [
        (item["start_age"], item["end_age"])
        for item in result.periods
    ] == [
        (47.0, 57.0),
        (57.0, 67.0),
        (67.0, 77.0),
        (77.0, 87.0),
        (87.0, 97.0),
    ]
    assert [item["stem_ten_god"] for item in result.periods] == [
        "印綬",
        "比肩",
        "劫財",
        "食神",
        "傷官",
    ]
    assert captured["payload"]["text"]["format"]["type"] == "json_schema"
    assert captured["payload"]["text"]["format"]["strict"] is True
    assert context == before
