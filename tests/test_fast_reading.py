import json
from html.parser import HTMLParser
from types import SimpleNamespace

import pytest

from api.customer_pipeline import CustomerReadingInput
from api.fast_reading import FAST_SECTIONS, _FAST_SCHEMA, _build_context, _chart_card, _detail_projection, _emit_perf, _provider_call, _validate_fast_texts, run_concern_answer, run_detail, run_fast_reading
from api.customer_routes import _move_fast_back_link_to_header, _render_fast_prose, _render_fast_result, _split_fast_prose


class _Responses:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        schema = kwargs["text"]["format"]["schema"]
        if "text" in schema["properties"]:
            value = {"text": "必要な項目だけを、命式の根拠に沿って詳しく説明します。"}
        else:
            value = {key: "短い結論を、命式の根拠に沿って説明します。" for key in schema["properties"]}
        return SimpleNamespace(output_text=json.dumps(value, ensure_ascii=False))


class _IncompleteResponses:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(status="incomplete", incomplete_details=SimpleNamespace(reason="max_output_tokens"))


class _TextResponses:
    def __init__(self, text):
        self.text = text

    def create(self, **kwargs):
        return SimpleNamespace(status="completed", output_text=self.text)


def test_fast_provider_incomplete_is_classified_without_accepting_partial_json():
    responses = _IncompleteResponses()
    performance = {}
    with pytest.raises(ValueError, match="incomplete"):
        _provider_call(
            SimpleNamespace(responses=responses),
            model="test-model",
            instructions="test",
            context={},
            schema=_FAST_SCHEMA,
            performance=performance,
        )
    assert performance["provider_status"] == "incomplete"
    assert performance["incomplete_reason"] == "max_output_tokens"
    assert performance["failure_stage"] == "provider_response"
    assert responses.calls[0]["max_output_tokens"] == 4000


@pytest.mark.parametrize(
    ("text", "stage"),
    [("{", "provider_json"), ("{}", "provider_schema")],
)
def test_fast_provider_invalid_payload_is_classified(text, stage):
    performance = {}
    with pytest.raises(ValueError):
        _provider_call(
            SimpleNamespace(responses=_TextResponses(text)),
            model="test-model",
            instructions="test",
            context={},
            schema=_FAST_SCHEMA,
            performance=performance,
        )
    assert performance["failure_stage"] == stage


def test_chart_card_preserves_mapping_like_pillars_and_rejects_invalid_shape(capsys):
    pillar = SimpleNamespace(
        stem="乙", branch="巳", stem_ten_god="比肩", twelve_stage="沐浴",
        hidden_stems=["丙"], hidden_stem_ten_gods=[{"ten_god": "傷官"}],
    )
    card = _chart_card({"chart": {position: pillar for position in ("year", "month", "day", "hour")}})
    assert card["year"]["stem"] == "乙"
    assert card["year"]["hidden_stem_ten_gods"] == ["傷官"]
    unknown_card = _chart_card({"chart": {"year": pillar, "month": pillar, "day": pillar, "hour": None}})
    assert unknown_card["hour"]["unavailable"] == "出生時刻不明"
    assert unknown_card["hour"]["stem"] is None
    with pytest.raises(TypeError, match="chart pillar year"):
        _chart_card({"chart": {"year": None}})
    diagnostic = capsys.readouterr().err
    assert "[FAST_CHART_DIAG]" in diagnostic
    assert "position=year" in diagnostic
    assert "pillar_type=NoneType" in diagnostic
    assert "pillar_none=true" in diagnostic
    assert "hidden_stem" not in diagnostic


def test_known_and_unknown_birth_time_keep_distinct_chart_semantics():
    import api.fast_reading as fast
    from datetime import datetime

    fast._CHART_CACHE.clear()
    known = _value()
    unknown = CustomerReadingInput(
        birth_date=known.birth_date, birth_time=None, birth_place=known.birth_place,
        gender=known.gender, consultation=known.consultation,
    )
    known_perf, unknown_perf = {}, {}
    known_chart, _, _ = _build_context(known, datetime(2026, 10, 8), known_perf)
    unknown_chart, _, _ = _build_context(unknown, datetime(2026, 10, 8), unknown_perf)
    assert known_chart["chart"]["hour"] is not None
    assert unknown_chart["chart"]["hour"] is None
    assert known_perf["birth_time_known"] is True
    assert known_perf["chart_hour_none"] is False
    assert unknown_perf["birth_time_known"] is False
    assert unknown_perf["chart_hour_none"] is True
    assert known_perf["chart_cache_hit"] is False
    assert unknown_perf["chart_cache_hit"] is False


def test_annual_card_handles_optional_current_luck_attribute_error(monkeypatch):
    import api.fast_reading as fast

    calls = []

    def fake_annual(**kwargs):
        calls.append(kwargs["current_luck"])
        if len(calls) == 1:
            raise AttributeError("optional current luck field")
        return [{"year": 2026, "ganzhi": "丙午"}]

    monkeypatch.setattr(fast, "calculate_annual_luck_range", fake_annual)
    result = fast._annual_card(
        {"annual_luck": {"year": 2026}, "day_master": {"stem": "乙"}, "useful_gods": {}, "current_luck": object()}
    )
    assert result == [{"year": 2026, "ganzhi": "丙午"}]
    assert calls[0] is not None
    assert calls[1] is None


def _value():
    return CustomerReadingInput(birth_date="1984-07-10", birth_time="22:45", birth_place="愛知県", gender="male", consultation="転職するか迷っています。")


def test_fast_reading_and_detail_are_server_owned_and_cached():
    responses = _Responses()
    client = SimpleNamespace(responses=responses)
    result = run_fast_reading(_value(), client=client, model="test-model")
    assert set(result["sections"]) == {key for key, _ in FAST_SECTIONS}
    first = run_detail(result["session_id"], "career", client=client, model="test-model")
    assert run_detail(result["session_id"], "career", client=client, model="test-model") == first
    assert len(responses.calls) == 2


def test_concern_answer_uses_submitted_consultation_and_is_cached():
    responses = _Responses()
    client = SimpleNamespace(responses=responses)
    result = run_fast_reading(_value(), client=client, model="test-model")
    first = run_concern_answer(result["session_id"], client=client, model="test-model")
    second = run_concern_answer(result["session_id"], client=client, model="test-model")
    assert first == second
    assert first["consultation"] == _value().consultation
    assert first["answer"]
    assert len(responses.calls) == 2


def test_concern_answer_provider_and_validation_failures_are_separate():
    result = run_fast_reading(_value(), client=SimpleNamespace(responses=_Responses()), model="test-model")

    class _Failing:
        def create(self, **kwargs):
            raise RuntimeError("provider failure")

    provider_perf = {}
    with pytest.raises(RuntimeError):
        run_concern_answer(result["session_id"], client=SimpleNamespace(responses=_Failing()), performance=provider_perf)
    assert provider_perf["provider_call_attempted"] is True

    invalid_perf = {}
    with pytest.raises(ValueError):
        run_concern_answer(
            result["session_id"],
            client=SimpleNamespace(responses=_TextResponses(json.dumps({"text": "9999年の断定"}, ensure_ascii=False))),
            performance=invalid_perf,
        )
    assert invalid_perf["validation_failed"] is True


def test_fast_result_renders_optional_concern_card_without_leaking_when_empty():
    base = {"session_id": "a" * 32, "chart": {}, "sections": {key: "本文" for key, _ in FAST_SECTIONS}}
    assert "concern-card" not in _render_fast_result(base)
    document = _render_fast_result({**base, "consultation": "転職 <script>alert(1)</script>"})
    assert "concern-card" in document
    assert "転職 &lt;script&gt;alert(1)&lt;/script&gt;" in document
    assert "fetch('/app/reading/concern'" in document
    assert document.index('class="concern-card"') > document.rindex('class="fast-card"')
    assert document.count("<script") == document.count("</script>")
    assert "個別回答を取得できませんでした" in document
    assert "button.disabled=false" in document


def test_fast_result_does_not_silently_drop_concern_markup_when_marker_missing(monkeypatch):
    import api.customer_routes as routes

    monkeypatch.setattr(routes, "_render_fast_result_raw", lambda _result: "<html></html>")
    with pytest.raises(RuntimeError, match="concern_css"):
        routes._render_fast_result({"session_id": "a" * 32, "consultation": "相談"})


def test_invalid_detail_type_and_session_are_rejected():
    with pytest.raises(ValueError):
        run_detail("0" * 32, "not-a-detail")
    with pytest.raises(KeyError):
        run_detail("0" * 32, "career")


def test_expired_session_is_rejected():
    import api.fast_reading as fast
    responses = _Responses()
    result = run_fast_reading(_value(), client=SimpleNamespace(responses=responses), model="test-model")
    fast._SESSIONS[result["session_id"]]["created"] -= fast._SESSION_TTL
    with pytest.raises(KeyError):
        run_detail(result["session_id"], "career", client=SimpleNamespace(responses=responses), model="test-model")


def test_fast_validation_rejects_missing_empty_numeric_and_luck_boundary():
    context = {"luck": {"five_year_luck": [{"year": 2026}]}}
    valid = {key: "根拠に沿った短い説明" for key, _ in FAST_SECTIONS}
    _validate_fast_texts(valid, context)
    with pytest.raises(ValueError):
        _validate_fast_texts({key: "" for key, _ in FAST_SECTIONS}, context)
    invalid = dict(valid)
    invalid["career"] = "大運だけを説明します。"
    with pytest.raises(ValueError):
        _validate_fast_texts(invalid, context)
    invalid = dict(valid)
    invalid["wealth"] = "成功率80%です。"
    with pytest.raises(ValueError):
        _validate_fast_texts(invalid, context)


def test_detail_context_is_scoped_by_detail_type():
    context = {"chart": {}, "facts": [], "luck": {"current_luck": {"x": 1}, "five_year_luck": [{"year": 2026}]}}
    metadata = {"components": {"strength": {"x": 1}, "pattern": {"x": 1}, "useful_gods": {"x": 1}}}
    career = _detail_projection(context, metadata, "career")
    annual = _detail_projection(context, metadata, "annual_luck")
    assert "current_luck" not in career
    assert "five_year_luck" not in career
    assert "five_year_luck" in annual
    assert "current_luck" in annual


def test_performance_log_is_numeric_only_and_flushable(capsys):
    _emit_perf("FAST_PERF", {"request_id": "abc", "total_elapsed": 1.25, "provider_calls": 1, "birth_time_known": True, "birth_time_type": "str", "chart_hour_none": False, "chart_time_scope": "four_pillars", "status": "success"})
    output = capsys.readouterr().err
    assert "[FAST_PERF]" in output
    assert "request_id=abc" in output
    assert "total_elapsed=1.25" in output
    assert "birth_time_known=true" in output
    assert "birth_time_type=str" in output
    assert "chart_hour_none=false" in output
    assert "chart_time_scope=four_pillars" in output
    assert "birth_date" not in output
    assert "prompt" not in output


def test_fast_result_contains_trusted_chart_luck_and_15_year_projection():
    from datetime import datetime

    responses = _Responses()
    result = run_fast_reading(
        _value(),
        client=SimpleNamespace(responses=responses),
        model="test-model",
        reference_time=datetime(2026, 10, 8),
    )
    assert set(result["chart_card"]) == {"year", "month", "day", "hour"}
    assert result["chart_card"]["day"]["stem_ten_god"] == "―"
    assert len(result["luck_pillars"]) == len(result["chart"]["luck_pillars"]["pillars"])
    assert len(result["annual_luck_15"]) == 10
    years = [item["year"] for item in result["annual_luck_15"]]
    assert result["chart"]["current_luck"]["current_luck_pillar"]["ganzhi"] == "乙亥"
    assert result["chart"]["current_luck"]["current_luck_pillar"]["index"] == next(
        item["index"] for item in result["luck_pillars"] if item["ganzhi"] == "乙亥"
    )
    assert years == list(range(2026, 2036))
    source_pillars = result["chart"]["chart"]
    for position in ("year", "month", "day", "hour"):
        assert result["chart_card"][position]["hidden_stems"] == source_pillars[position]["hidden_stems"]
        assert len(result["chart_card"][position]["hidden_stems"]) == len(result["chart_card"][position]["hidden_stem_ten_gods"])

    document = _render_fast_result(result)
    assert "鑑定カルテ" in document
    assert "大運" in document and "年運" in document
    assert document.count('<div class="annual-cell') == 10
    assert 'class="current-mark"' in document
    assert "annual-cell current-mark" in document
    assert "2026年" in document and "2035年" in document
    assert "9.257612" not in document and "39.257612" not in document
    assert " / " in document
    assert document.count("current-mark") >= 2
    assert "詳しく見る" in document


def test_fast_back_link_is_in_header_once():
    document = '<body><nav class="web-nav"><a href="/app">old</a></nav><main><header class="fast-head"><p class="eyebrow">PERSONAL READING</p></header></main></body>'
    moved = _move_fast_back_link_to_header(document)
    assert moved.count('href="/app"') == 1
    assert 'class="fast-back"' in moved
    assert '← 入力画面に戻る' in moved
    assert '<nav class="web-nav">' not in moved
    assert '<header class="fast-head"><a class="fast-back"' in moved


def test_fast_prose_preserves_authored_breaks_and_escapes_html():
    rendered = _render_fast_prose("第一文。\n第二文。\n\n第三文。<script>alert(1)</script>")
    assert rendered.count("<p>") == 2
    assert "第一文。<br>\n第二文。" in rendered
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in rendered
    assert "<script>" not in rendered


def test_fast_prose_splits_long_text_without_splitting_parenthetical_sentences():
    blocks = _split_fast_prose("第一文（ここで終わらない。続きです）。第二文。第三文。第四文。")
    assert len(blocks) == 2
    assert "第一文（ここで終わらない。続きです）。第二文。第三文。" in blocks[0]


def test_fast_result_uses_safe_detail_prose_renderer():
    document = _render_fast_result({"session_id": "a" * 32, "chart": {}, "sections": {key: "本文" for key, _ in FAST_SECTIONS}})
    assert "function renderFastProse" in document
    assert "renderFastProse(box,data.text);" in document
    assert "box.textContent=data.text;" not in document
    sid_position = document.index('const sid="')
    script_start = document.rfind("<script>", 0, sid_position)
    script_end = document.find("</script>", script_start)
    assert script_start >= 0
    assert script_end > sid_position

    class _ScriptParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.in_script = False
            self.script_text = []
            self.body_text = []

        def handle_starttag(self, tag, attrs):
            if tag == "script":
                self.in_script = True

        def handle_endtag(self, tag):
            if tag == "script":
                self.in_script = False

        def handle_data(self, data):
            (self.script_text if self.in_script else self.body_text).append(data)

    parser = _ScriptParser()
    parser.feed(document)
    assert any('const sid="' in text for text in parser.script_text)
    assert not any('const sid="' in text for text in parser.body_text)
    assert document.count('class="detail-button"') == 5
    assert "fetch('/app/reading/detail'" in document


def test_chart_cache_reuses_only_same_fixture_and_second():
    from datetime import datetime

    import api.fast_reading as fast

    fast._CHART_CACHE.clear()
    fast._CHART_INFLIGHT.clear()
    fast._CHART_INFLIGHT_ERRORS.clear()
    responses = _Responses()
    client = SimpleNamespace(responses=responses)
    fixed = datetime(2026, 10, 8, 12, 0, 0)
    first_perf = {}
    second_perf = {}
    run_fast_reading(_value(), client=client, model="test-model", reference_time=fixed, performance=first_perf)
    run_fast_reading(_value(), client=client, model="test-model", reference_time=fixed, performance=second_perf)
    assert first_perf["chart_cache_hit"] is False
    assert second_perf["chart_cache_hit"] is True
    assert second_perf["chart_elapsed"] >= 0


def test_chart_cache_concurrent_same_key_returns_identical_results():
    from concurrent.futures import ThreadPoolExecutor
    from datetime import datetime

    import api.fast_reading as fast

    fast._CHART_CACHE.clear()
    fast._CHART_INFLIGHT.clear()
    fast._CHART_INFLIGHT_ERRORS.clear()
    responses = _Responses()
    fixed = datetime(2026, 10, 8, 12, 0, 0)

    def call():
        return run_fast_reading(_value(), client=SimpleNamespace(responses=responses), model="test-model", reference_time=fixed)

    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = list(pool.map(lambda _: call(), (1, 2)))
    assert first["chart"] == second["chart"]


def test_chart_inflight_failure_is_propagated_and_next_request_can_retry(monkeypatch):
    from datetime import datetime

    import api.fast_reading as fast

    fast._CHART_CACHE.clear()
    fast._CHART_INFLIGHT.clear()
    fast._CHART_INFLIGHT_ERRORS.clear()
    calls = {"count": 0}

    def fail_once(request, *, target_datetime):
        calls["count"] += 1
        if calls["count"] == 1:
            raise ValueError("synthetic chart failure")
        return {"chart": {}, "day_master": {}, "luck_pillars": {"pillars": []}, "annual_luck": {}}

    monkeypatch.setattr(fast, "calculate_chart", fail_once)
    monkeypatch.setattr(fast, "build_reading_context_v2", lambda chart, consultation_context=None: {})
    monkeypatch.setattr(fast, "build_common_judgment_metadata", lambda chart: {})
    value = _value()
    reference = datetime(2026, 10, 8, 12, 0)
    with pytest.raises(ValueError, match="synthetic chart failure"):
        _build_context(value, reference)
    # The failed inflight marker is released, so a subsequent request retries.
    chart, _, _ = _build_context(value, reference)
    assert chart["chart"] == {}
    assert calls["count"] == 2
    assert not fast._CHART_INFLIGHT


def test_chart_inflight_failure_reaches_waiting_request(monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from datetime import datetime
    import time

    import api.fast_reading as fast

    fast._CHART_CACHE.clear()
    fast._CHART_INFLIGHT.clear()
    fast._CHART_INFLIGHT_ERRORS.clear()

    def fail(request, *, target_datetime):
        time.sleep(0.05)
        raise ValueError("shared chart failure")

    monkeypatch.setattr(fast, "calculate_chart", fail)
    value = _value()
    reference = datetime(2026, 10, 8, 12, 1)

    def call(_):
        try:
            _build_context(value, reference)
        except Exception as exc:
            return type(exc), str(exc)
        return None, ""

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(call, (1, 2)))
    assert outcomes == [(ValueError, "shared chart failure"), (ValueError, "shared chart failure")]
    assert not fast._CHART_INFLIGHT
