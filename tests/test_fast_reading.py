import json
from types import SimpleNamespace

import pytest

from api.customer_pipeline import CustomerReadingInput
from api.fast_reading import FAST_SECTIONS, _detail_projection, _emit_perf, _validate_fast_texts, run_detail, run_fast_reading
from api.customer_routes import _render_fast_result


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
    _emit_perf("FAST_PERF", {"request_id": "abc", "total_elapsed": 1.25, "provider_calls": 1, "status": "success"})
    output = capsys.readouterr().err
    assert "[FAST_PERF]" in output
    assert "request_id=abc" in output
    assert "total_elapsed=1.25" in output
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
    assert len(result["annual_luck_15"]) == 15
    years = [item["year"] for item in result["annual_luck_15"]]
    assert result["chart"]["current_luck"]["current_luck_pillar"]["ganzhi"] == "乙亥"
    assert result["chart"]["current_luck"]["current_luck_pillar"]["index"] == next(
        item["index"] for item in result["luck_pillars"] if item["ganzhi"] == "乙亥"
    )
    assert years == list(range(2026, 2041))
    source_pillars = result["chart"]["chart"]
    for position in ("year", "month", "day", "hour"):
        assert result["chart_card"][position]["hidden_stems"] == source_pillars[position]["hidden_stems"]
        assert len(result["chart_card"][position]["hidden_stems"]) == len(result["chart_card"][position]["hidden_stem_ten_gods"])

    document = _render_fast_result(result)
    assert "鑑定カルテ" in document
    assert "大運" in document and "年運" in document
    assert document.count('<div class="annual-cell') == 15
    assert 'class="current-mark"' in document
    assert "annual-cell current-mark" in document
    assert "2026年" in document and "2040年" in document
    assert document.count("current-mark") >= 2
    assert "詳しく見る" in document
