"""Customer-Web tests for the optional B research sidecar.

Records here are synthetic validation data, not source-text cases or fixtures.
"""

from copy import deepcopy
import os
from urllib.parse import urlencode

import api.customer_routes as customer_routes
import api.fast_reading as fast_reading
import api.symbol_judgment_reference as reference_sidecar
from api.symbol_judgment_reference import (
    FEATURE_FLAG_ENV, append_product_reference_sidecar, append_reference_sidecar,
    build_reference_sidecar, reference_evaluation_enabled, render_reference_sidecar_html,
)
from fastapi.testclient import TestClient
from main import app
from scripts.preview_symbol_judgment_b_customer_web import generate_preview


def synthetic_production(*, hour="乙巳"):
    pillars = {"year": "甲辰", "month": "癸酉", "day": "丁亥", "hour": hour}
    chart = {position: None if ganzhi is None else {
        "stem": ganzhi[0], "branch": ganzhi[1], "ganzhi": ganzhi,
    } for position, ganzhi in pillars.items()}
    return {
        "chart": chart,
        "useful_gods": {"primary_useful_element": "木", "secondary_useful_elements": ["火", "水"],
                        "support_balance": {"unfavorable_elements": ["土", "金"]}},
        "current_luck": {"has_current_luck": True,
                         "current_luck_pillar": {"stem": "壬", "branch": "子", "ganzhi": "壬子"}},
        "annual_luck": {"stem": "癸", "branch": "亥", "ganzhi": "癸亥"},
    }


def test_server_flag_is_disabled_by_default_and_requires_explicit_true_value():
    assert reference_evaluation_enabled({}) is False
    assert reference_evaluation_enabled({FEATURE_FLAG_ENV: "false"}) is False
    assert reference_evaluation_enabled({FEATURE_FLAG_ENV: "1"}) is True
    assert reference_evaluation_enabled({FEATURE_FLAG_ENV: "TRUE"}) is True


def test_disabled_connection_returns_original_html_and_never_calls_b_boundary():
    calls = []
    def forbidden_runner(*_args, **_kwargs):
        calls.append(True)
        raise AssertionError("disabled feature called B boundary")
    original = "<!doctype html><body><main>既存鑑定本文</main></body>"
    rendered = append_reference_sidecar(original, synthetic_production(), enabled=False,
                                        runner=forbidden_runner)
    assert rendered == original
    assert calls == []
    assert "八雲式・参考評価" not in rendered


def test_enabled_connection_renders_reason_rules_assumptions_and_version():
    source = synthetic_production()
    before = deepcopy(source)
    rendered = append_reference_sidecar(
        "<html><body><main>既存鑑定本文</main></body></html>", source, enabled=True)
    assert source == before
    assert "既存鑑定本文" in rendered
    assert rendered.count("八雲式・参考評価") == 1
    assert all(text in rendered for text in ("理由・根拠", "適用規則", "研究用仮定", "yakumo-b-research-v1", "転職・投資"))
    assert any(symbol in rendered for symbol in ("○", "△", "×"))


def test_unknown_birth_time_is_held_without_guessing_an_hour():
    sidecar = build_reference_sidecar(synthetic_production(hour=None), enabled=True)
    assert sidecar["status"] == "hold"
    assert sidecar["adapter_result"]["reasons"] == ["chart_hour_not_mapping"]
    rendered = render_reference_sidecar_html(sidecar)
    assert "判定保留" in rendered
    assert "input" not in sidecar["adapter_result"]
    assert not any(mark in rendered for mark in (">◎<", ">○<", ">△<", ">×<"))


def test_boundary_exception_is_visible_as_error_and_existing_reading_survives():
    def broken_runner(*_args, **_kwargs):
        raise RuntimeError("synthetic boundary failure")
    rendered = append_reference_sidecar(
        "<html><body><main>既存鑑定本文</main></body></html>", synthetic_production(),
        enabled=True, runner=broken_runner)
    assert "既存鑑定本文" in rendered
    assert "評価エラー" in rendered and "RuntimeError" in rendered
    assert "判定保留" not in rendered
    assert not any(mark in rendered for mark in (">◎<", ">○<", ">△<", ">×<"))


def test_renderer_escapes_research_payload():
    sidecar = {"status": "hold", "display": {"display_name": "八雲式・参考評価",
        "items": [{"symbol": None, "display_symbol": "判定保留", "target": "<script>x</script>",
                   "reason": "<img src=x onerror=1>", "applied_rules": [], "assumptions": []}],
        "model_version": "test", "uncertainties": [], "notice": "研究用"}}
    rendered = render_reference_sidecar_html(sidecar)
    assert "<script>x</script>" not in rendered and "<img src=x onerror=1>" not in rendered
    assert "&lt;script&gt;x&lt;/script&gt;" in rendered


def test_customer_renderer_holds_unestablished_top_mark_instead_of_publishing_it():
    sidecar = {"status": "success", "display": {"display_name": "八雲式・参考評価",
        "items": [{"symbol": "◎", "display_symbol": "◎", "target": "水",
                   "reason": "synthetic top score", "applied_rules": ["B.GRADE.001"],
                   "assumptions": [{"rule_id": "B.GRADE.001", "basis": "八雲式仮定"}]}],
        "model_version": "test", "uncertainties": [], "notice": "研究用"}}
    rendered = render_reference_sidecar_html(sidecar)
    assert "◎" not in rendered
    assert "判定保留" in rendered
    assert "最高評価候補" in rendered and "判定規則が未確立" in rendered


def test_full_customer_renderer_uses_sidecar_only_when_server_flag_is_enabled(monkeypatch):
    product = {"engine_result": synthetic_production()}
    base = "<html><head></head><body><main>既存鑑定本文</main></body></html>"
    monkeypatch.setattr(customer_routes, "render_customer_reading_product_v2_html", lambda _product: base)
    monkeypatch.delenv(FEATURE_FLAG_ENV, raising=False)
    disabled = customer_routes._render_customer_result(product)
    assert "既存鑑定本文" in disabled and "八雲式・参考評価" not in disabled
    monkeypatch.setenv(FEATURE_FLAG_ENV, "true")
    enabled = customer_routes._render_customer_result(product)
    assert "既存鑑定本文" in enabled and "八雲式・参考評価" in enabled


def test_fast_customer_renderer_remains_unchanged_when_disabled(monkeypatch):
    result = {"chart": synthetic_production()}
    base = "<html><head></head><body><main>既存高速鑑定</main><script>\nconst sid=\"x\";</script></body></html>"
    monkeypatch.setattr(customer_routes, "_render_fast_result_raw", lambda _result: base)
    monkeypatch.delenv(FEATURE_FLAG_ENV, raising=False)
    disabled = customer_routes._render_fast_result(result)
    assert "既存高速鑑定" in disabled and "八雲式・参考評価" not in disabled

    monkeypatch.setenv(FEATURE_FLAG_ENV, "on")
    enabled = customer_routes._render_fast_result(result)
    assert "既存高速鑑定" in enabled and "八雲式・参考評価" in enabled


def test_product_sidecar_accepts_immutable_product_shape():
    class Product:
        def to_dict(self):
            return {"engine_result": synthetic_production()}
    rendered = append_product_reference_sidecar(
        "<html><body><main>本文</main></body></html>", Product(), enabled=True)
    assert "本文" in rendered and "八雲式・参考評価" in rendered


def test_disabled_product_connection_does_not_even_read_product_snapshot():
    class BrokenProduct:
        def to_dict(self):
            raise AssertionError("disabled connection read product")
    original = "<html><body><main>本文</main></body></html>"
    assert append_product_reference_sidecar(original, BrokenProduct(), enabled=False) == original


def test_product_snapshot_exception_is_error_sidecar_without_losing_reading():
    class BrokenProduct:
        def to_dict(self):
            raise RuntimeError("synthetic snapshot failure")
    rendered = append_product_reference_sidecar(
        "<html><body><main>本文</main></body></html>", BrokenProduct(), enabled=True)
    assert "本文" in rendered and "評価エラー" in rendered and "RuntimeError" in rendered


def _post_synthetic_customer(monkeypatch, *, flag, unknown_time=False):
    monkeypatch.setattr(fast_reading, "create_customer_provider_client", lambda: None)
    if flag is None:
        monkeypatch.delenv(FEATURE_FLAG_ENV, raising=False)
    else:
        monkeypatch.setenv(FEATURE_FLAG_ENV, flag)
    values = {
        "birth_date": "1984-07-22", "birth_place": "福岡県", "gender": "male",
        "consultation": "合成入力による公開前接続確認です。",
    }
    if unknown_time:
        values.update(birth_time_unknown="1", birth_hour="", birth_minute="")
    else:
        values.update(birth_hour="13", birth_minute="40")
    return TestClient(app).post(
        "/app/reading", content=urlencode(values),
        headers={"content-type": "application/x-www-form-urlencoded"},
    )


def test_synthetic_customer_input_runs_real_chart_to_reference_html_flag_off_and_on(monkeypatch):
    disabled = _post_synthetic_customer(monkeypatch, flag=None)
    assert disabled.status_code == 200
    assert "あなたの鑑定結果" in disabled.text
    assert "八雲式・参考評価" not in disabled.text

    enabled = _post_synthetic_customer(monkeypatch, flag="true")
    assert enabled.status_code == 200
    assert "あなたの鑑定結果" in enabled.text
    assert "八雲式・参考評価" in enabled.text
    assert all(label in enabled.text for label in ("理由・根拠", "適用規則", "研究用仮定"))
    assert "◎" not in enabled.text
    # 本どおりの命式（book_kiso、2026-10-16〜）ではこの入力に最高評価候補が出ないため、
    # 「最高評価候補を◎で公開せず保留表示する」ことは
    # test_customer_renderer_holds_unestablished_top_mark_instead_of_publishing_it で確認する。
    if "最高評価候補" in enabled.text:
        assert "判定規則が未確立" in enabled.text


def test_synthetic_customer_flag_off_never_calls_b_boundary(monkeypatch):
    def forbidden_evaluator(*_args, **_kwargs):
        raise AssertionError("disabled customer path called B boundary")
    monkeypatch.setattr(reference_sidecar, "run_reference_evaluation", forbidden_evaluator)
    response = _post_synthetic_customer(monkeypatch, flag=None)
    assert response.status_code == 200
    assert "あなたの鑑定結果" in response.text
    assert "八雲式・参考評価" not in response.text


def test_synthetic_customer_global_hold_is_not_converted_to_normal_symbol(monkeypatch):
    def held_evaluator(*_args, **_kwargs):
        return {"status": "hold", "enabled": True, "display": {
            "display_name": "八雲式・参考評価", "status": "hold",
            "items": [{"symbol": None, "display_symbol": "判定保留", "target": "全体",
                       "reason": "合成競合のため判定を保留しました。",
                       "applied_rules": ["B.TRANSFORM.001"],
                       "assumptions": [{"rule_id": "B.TRANSFORM.001", "basis": "八雲式仮定"}]}],
            "model_version": "yakumo-b-research-v1", "uncertainties": ["合成競合"],
            "notice": "研究用の参考評価です。",
        }}
    monkeypatch.setattr(reference_sidecar, "run_reference_evaluation", held_evaluator)
    response = _post_synthetic_customer(monkeypatch, flag="true")
    assert response.status_code == 200
    assert "あなたの鑑定結果" in response.text
    assert "八雲式・参考評価" in response.text
    assert "判定保留" in response.text and "合成競合" in response.text
    assert not any(mark in response.text for mark in (">◎<", ">○<", ">△<", ">×<"))


def test_synthetic_unknown_birth_time_keeps_reading_and_holds_reference(monkeypatch):
    response = _post_synthetic_customer(monkeypatch, flag="true", unknown_time=True)
    assert response.status_code == 200
    assert "あなたの鑑定結果" in response.text
    assert "八雲式・参考評価" in response.text
    assert "判定保留" in response.text


def test_synthetic_customer_b_exception_keeps_existing_reading(monkeypatch):
    def broken_evaluator(*_args, **_kwargs):
        raise RuntimeError("synthetic B failure")
    monkeypatch.setattr(reference_sidecar, "run_reference_evaluation", broken_evaluator)
    response = _post_synthetic_customer(monkeypatch, flag="true")
    assert response.status_code == 200
    assert "あなたの鑑定結果" in response.text
    assert "八雲式・参考評価" in response.text
    assert "評価エラー" in response.text
    assert "RuntimeError" in response.text


def test_preview_generator_uses_real_renderer_without_external_ai(tmp_path, monkeypatch):
    monkeypatch.setenv(FEATURE_FLAG_ENV, "original-test-value")
    output = generate_preview(tmp_path / "preview.html")
    document = output.read_text(encoding="utf-8")
    assert "あなたの鑑定結果" in document
    assert "八雲式・参考評価" in document
    assert "合成入力によるステージング画面確認です。" in document
    assert "◎" not in document
    assert os.environ[FEATURE_FLAG_ENV] == "original-test-value"
