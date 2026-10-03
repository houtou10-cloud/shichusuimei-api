"""Customer form and trusted v1.2 browser-flow tests."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import inspect
import json
from types import SimpleNamespace
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
import pytest

import api.customer_routes as customer_routes
import engine.reading_renderer_v2 as renderer_v2
from api.customer_pipeline import (
    MAX_CONCERN_CHARS,
    PREFECTURES,
    CustomerInputError,
    CustomerReadingUnavailableError,
    OpenAISemanticAssessorV2,
    SemanticAssessmentProviderError,
    _semantic_reference_catalog,
    build_customer_chart_request,
    run_customer_reading,
    validate_customer_input,
)
from main import app
import tests.test_ai_reading_v2_e2e as base
from tests.test_reading_pdf_v2 import _product, _product_with_prose


FIXED = datetime(2026, 8, 10, 15, 36, tzinfo=ZoneInfo("Asia/Tokyo"))


class FakeResponses:
    def __init__(self, semantic_results=None, repair_results=None):
        self.semantic_results = deepcopy(
            semantic_results or [{"status": "completed", "findings": []}]
        )
        self.repair_results = deepcopy(repair_results or [])
        self.calls: list[dict] = []
        self.semantic_calls = 0
        self.repair_calls = 0

    def create(self, **kwargs):
        self.calls.append(deepcopy(kwargs))
        schema_name = kwargs["text"]["format"]["name"]
        if schema_name == "ai_reading_v2":
            content = kwargs["input"][0]["content"]
            model_input = json.loads(content.split("model_input=", 1)[1])
            request = {
                "trusted_attachments": {
                    "future_flow_years": model_input["future_flow_years"],
                    "long_term_luck_pillars": model_input["long_term_luck_pillars"],
                    "consultation_present": model_input["reading_context"]["consultation"] is not None,
                }
            }
            payload = base._transport_payload(base._model_payload(request))
        elif schema_name == "semantic_assessment_v2":
            payload = self.semantic_results[
                min(self.semantic_calls, len(self.semantic_results) - 1)
            ]
            self.semantic_calls += 1
        elif schema_name == "ai_reading_repair_patch_v2":
            payload = self.repair_results[self.repair_calls]
            self.repair_calls += 1
        else:  # pragma: no cover - proves a new provider surface is not silently accepted
            raise AssertionError(f"unexpected schema name: {schema_name}")
        return SimpleNamespace(
            id="provider-internal-id",
            status="completed",
            output_text=json.dumps(
                payload,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            ),
            usage={"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
        )


def _client(semantic_results=None, repair_results=None):
    return SimpleNamespace(
        responses=FakeResponses(semantic_results, repair_results)
    )


def _values(**overrides):
    values = {
        "birth_date": "1984-07-22",
        "birth_hour": "13",
        "birth_minute": "40",
        "birth_place": "福岡県",
        "gender": "male",
        "consultation": "今後の仕事について相談したいです。",
    }
    values.update(overrides)
    return values


def _route_pipeline(fake_client):
    def execute(value):
        return run_customer_reading(
            value,
            client=fake_client,
            model="test-model",
            reference_time=FIXED,
        )

    return execute


def _post(client: TestClient, values: dict[str, str]):
    return client.post(
        "/app/reading",
        content=urlencode(values),
        headers={"content-type": "application/x-www-form-urlencoded"},
    )


def test_customer_form_is_japanese_responsive_and_has_all_inputs():
    response = TestClient(app).get("/app")
    assert response.status_code == 200
    for label in (
        "生年月日", "出生時刻", "出生時刻が分からない", "出生地", "性別",
        "現在のお悩み・相談したいこと（任意）", "鑑定する",
    ):
        assert label in response.text
    assert response.text.count('<option value="') >= len(PREFECTURES) + 24 + 60
    assert 'name="source_path"' not in response.text
    assert "@media(max-width:680px)" in response.text
    assert "button.disabled=true" in response.text
    assert "鑑定結果を作成しています" in response.text


def test_known_and_unknown_time_map_to_formal_chart_request():
    known = validate_customer_input(_values())
    known_request = build_customer_chart_request(known)
    assert known_request.birth_time == "13:40"
    assert known_request.birth_place == "福岡県"
    unknown = validate_customer_input(_values(
        birth_hour="", birth_minute="", birth_time_unknown="1", consultation="",
    ))
    unknown_request = build_customer_chart_request(unknown)
    assert unknown_request.birth_time is None
    assert unknown.consultation == ""


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"birth_date": "2024-02-30"}, "birth_date"),
        ({"birth_date": ""}, "birth_date"),
        ({"birth_hour": "24"}, "birth_time"),
        ({"birth_minute": "60"}, "birth_time"),
        ({"birth_time_unknown": "1"}, "birth_time"),
        ({"gender": "other"}, "gender"),
        ({"birth_place": "架空県"}, "birth_place"),
        ({"consultation": "あ" * (MAX_CONCERN_CHARS + 1)}, "consultation"),
    ],
)
def test_customer_input_validation_is_strict_and_customer_readable(overrides, field):
    with pytest.raises(CustomerInputError) as captured:
        validate_customer_input(_values(**overrides))
    assert field in captured.value.errors
    assert captured.value.errors[field].endswith("。")


def test_form_route_returns_japanese_errors_without_internal_details():
    response = _post(TestClient(app), _values(birth_date="invalid"))
    assert response.status_code == 422
    assert "実在する生年月日" in response.text
    assert "Traceback" not in response.text
    assert "ValidationError" not in response.text
    assert "pydantic" not in response.text.lower()


def test_gc03_browser_flow_runs_real_trusted_pipeline_and_renders_consultation(monkeypatch):
    fake = _client()
    monkeypatch.setattr(customer_routes, "run_customer_reading", _route_pipeline(fake))
    response = _post(TestClient(app), _values())
    assert response.status_code == 200
    for visible in (
        "四柱推命", "基本情報", "あなたの命式", "福岡県", "男性", "相談への回答",
        "現在大運", "現在歳運", "これから5年間", "注意事項・不確実性・免責",
    ):
        assert visible in response.text
    assert "実用的な指針です。" in response.text
    assert fake.responses.semantic_calls == 1
    assert [call["text"]["format"]["name"] for call in fake.responses.calls] == [
        "ai_reading_v2", "semantic_assessment_v2",
    ]
    for hidden in (
        "source_path", "source_contract", "source_bundle_sha256", "provider-internal-id",
        "OPENAI_API_KEY", "schema_version", "warning_id", "uncertainty_id",
    ):
        assert hidden not in response.text


def test_verified_1984_chart_distinguishes_stem_and_hidden_stem_ten_gods(monkeypatch):
    fake = _client()
    monkeypatch.setattr(customer_routes, "run_customer_reading", _route_pipeline(fake))
    response = _post(TestClient(app), _values(
        birth_date="1984-07-10",
        birth_hour="22",
        birth_minute="45",
        birth_place="愛知県",
        gender="male",
    ))

    assert response.status_code == 200
    assert "天干通変星" in response.text
    assert "蔵干通変星" in response.text
    assert "<td>辛</td>" in response.text
    assert "<td>偏官</td>" in response.text
    assert "<td>己・丁・乙</td>" in response.text
    assert "<td>偏財・食神・比肩</td>" in response.text


def test_gc10_browser_flow_preserves_unknown_hour_warning_and_uncertainty(monkeypatch):
    fake = _client()
    monkeypatch.setattr(customer_routes, "run_customer_reading", _route_pipeline(fake))
    response = _post(TestClient(app), _values(
        birth_date="1985-07-17",
        birth_hour="",
        birth_minute="",
        birth_time_unknown="1",
        birth_place="石川県",
        gender="female",
        consultation="",
    ))
    assert response.status_code == 200
    assert "出生時刻不明" in response.text
    assert "時柱は計算していません" in response.text
    assert "既知の三柱範囲または推定値" in response.text
    assert "石川県" in response.text and "女性" in response.text
    assert "相談への回答" not in response.text
    assert "12:00" not in response.text


def test_pipeline_runs_frozen_auto_repair_then_publishes():
    finding = {
        "status": "completed",
        "findings": [{
            "code": "claim_type_mismatch",
            "path": "/sections/0/summary",
            "evidence": [{
                "source_contract": "ai_reading_v2",
                "path": "/sections/0/summary",
            }],
        }],
    }
    fake = _client(
        semantic_results=[finding, {"status": "completed", "findings": []}],
        repair_results=[{
            "patches": [{
                "op": "replace",
                "path": "/sections/0/summary/text",
                "value": "修復後の顧客向け文章です。",
            }],
        }],
    )
    product = run_customer_reading(
        validate_customer_input(_values()),
        client=fake,
        model="test-model",
        reference_time=FIXED,
    )
    snapshot = product.to_dict()
    assert snapshot["repair_history"]["state"] == "auto_repair_v2"
    assert snapshot["ai_reading"]["sections"][0]["summary"]["text"] == "修復後の顧客向け文章です。"
    assert fake.responses.repair_calls == 1
    assert len(fake.responses.calls) == 4


def test_pipeline_reports_safe_auto_repair_provider_failure_reason():
    finding = {
        "status": "completed",
        "findings": [{
            "code": "claim_type_mismatch",
            "path": "/sections/0/summary",
            "evidence": [{
                "source_contract": "ai_reading_v2",
                "path": "/sections/0/summary",
            }],
        }],
    }
    secret = "API_KEY_SECRET raw repair provider body"

    class ProviderRateLimit(RuntimeError):
        status_code = 429

    class RepairFailureResponses(FakeResponses):
        def create(self, **kwargs):
            if kwargs["text"]["format"]["name"] == "ai_reading_repair_patch_v2":
                self.calls.append(deepcopy(kwargs))
                self.repair_calls += 1
                raise ProviderRateLimit(secret)
            return super().create(**kwargs)

    responses = RepairFailureResponses([finding], [])
    with pytest.raises(CustomerReadingUnavailableError) as caught:
        run_customer_reading(
            validate_customer_input(_values()),
            client=SimpleNamespace(responses=responses),
            model="test-model",
            reference_time=FIXED,
        )

    error = caught.value
    assert error.stage == "auto_repair"
    assert error.reason_code == "repair_provider_rate_limited"
    assert error.decision == "fail"
    assert error.blocking_codes == ("claim_type_mismatch",)
    assert secret not in str(error)
    assert secret not in repr(vars(error))
    assert error.__context__ is None
    assert error.__cause__ is None
    assert responses.repair_calls == 1


def test_review_state_is_not_published_or_repaired():
    fake = _client(semantic_results=[{"status": "inconclusive", "findings": []}])
    with pytest.raises(CustomerReadingUnavailableError) as captured:
        run_customer_reading(
            validate_customer_input(_values()),
            client=fake,
            model="test-model",
            reference_time=FIXED,
        )
    assert captured.value.stage == "quality_gate"
    assert captured.value.reason_code == "quality_gate_review"
    assert captured.value.decision == "review"
    assert fake.responses.semantic_calls == 1
    assert fake.responses.repair_calls == 0
    assert len(fake.responses.calls) == 2


def test_non_auto_fail_is_not_repaired_or_published():
    finding = {
        "status": "completed",
        "findings": [{
            "code": "prohibited_claim",
            "path": "/sections/0/summary",
            "evidence": [{
                "source_contract": "ai_reading_v2",
                "path": "/sections/0/summary",
            }],
        }],
    }
    fake = _client(semantic_results=[finding])
    with pytest.raises(CustomerReadingUnavailableError) as captured:
        run_customer_reading(
            validate_customer_input(_values()),
            client=fake,
            model="test-model",
            reference_time=FIXED,
        )
    assert captured.value.stage == "quality_gate"
    assert captured.value.reason_code == "quality_gate_non_auto_fail"
    assert captured.value.decision == "fail"
    assert captured.value.blocking_codes == ("prohibited_claim",)
    assert fake.responses.repair_calls == 0
    assert len(fake.responses.calls) == 2


def test_semantic_assessor_uses_one_strict_call_and_exact_three_owner_inputs():
    fake = _client()
    assessor = OpenAISemanticAssessorV2(client=fake, model="test-model")
    ai = {"value": "AI"}
    rc = {"value": "RC"}
    metadata = {"value": "metadata"}
    result = assessor.assess(ai, rc, metadata)
    assert result == {"status": "completed", "findings": []}
    assert len(fake.responses.calls) == 1
    request = fake.responses.calls[0]
    assert request["model"] == "test-model"
    assert request["store"] is False
    assert request["text"]["format"]["strict"] is True
    assert request["text"]["format"]["name"] == "semantic_assessment_v2"
    assert request["max_output_tokens"] == 12000
    instructions = request["instructions"]
    assert "core_personality=0、career=1、wealth=2" in instructions
    assert "/sections/6/yearly/{year_index}/summary" in instructions
    assert "/future_flow_yearlyや/sections/future_flowなどのpathを作ってはいけません" in instructions
    assert "宣言されたclaim_typeとそのblockのtextの意味が一致しない場合だけ" in instructions
    assert "evidence pathも該当source_contractの入力JSONからexact key" in instructions
    assert "metadata-only claim contract catalogue" in instructions
    assert "A long_term_title is a concise customer-facing summary" in instructions
    assert json.loads(request["input"][0]["content"]) == {
        "ai_reading": ai,
        "reading_context": rc,
        "judgment_metadata": metadata,
    }


def test_semantic_assessor_transport_schema_bounds_finding_and_evidence_paths():
    fake = _client()
    assessor = OpenAISemanticAssessorV2(client=fake, model="test-model")
    assessor.assess({"sections": [{"section_id": "future_flow"}]}, {"facts": []}, {"components": []})
    request = fake.responses.calls[0]
    output_schema = request["text"]["format"]["schema"]
    assert output_schema["properties"]["findings"]["items"]["properties"]["path"].get("enum")


def test_semantic_reference_catalog_keeps_evidence_as_source_not_claim_target():
    ai = {
        "sections": [{
            "summary": {"text": "summary", "claim_type": "practical"},
            "evidence": [{"text": "evidence", "claim_type": "astrology"}],
        }]
    }
    catalog = _semantic_reference_catalog(ai, {"facts": []}, {"components": {}})
    finding_paths = {entry["path"] for entry in catalog["finding_refs"]}
    evidence_paths = {entry["path"] for entry in catalog["evidence_refs"]}
    assert "/sections/0/summary" in finding_paths
    assert "/sections/0/evidence/0" not in finding_paths
    assert ("ai_reading_v2", "/sections/0/evidence/0") in {
        (entry["source_contract"], entry["path"])
        for entry in catalog["evidence_refs"]
    }


@pytest.mark.parametrize("kind", ["transport", "malformed", "hostile_property"])
def test_semantic_assessor_sanitizes_all_provider_boundaries(kind):
    secret = "API_KEY_SECRET raw-provider-response"

    if kind == "transport":
        class Responses:
            def create(self, **_kwargs):
                raise RuntimeError(secret)
    elif kind == "malformed":
        class Responses:
            def create(self, **_kwargs):
                return SimpleNamespace(output_text='{"status":' + secret)
    else:
        class Hostile:
            @property
            def output_text(self):
                raise RuntimeError(secret)

        class Responses:
            def create(self, **_kwargs):
                return Hostile()

    assessor = OpenAISemanticAssessorV2(
        client=SimpleNamespace(responses=Responses()),
        model="test-model",
    )
    with pytest.raises(SemanticAssessmentProviderError) as captured:
        assessor.assess({}, {}, {})
    error = captured.value
    assert secret not in str(error)
    assert error.__context__ is None
    assert error.__cause__ is None
    assert vars(error) == {}


def test_semantic_assessor_classifies_incomplete_response_without_partial_output():
    secret = "PARTIAL_SEMANTIC_OUTPUT_SECRET"

    class Responses:
        def create(self, **_kwargs):
            return SimpleNamespace(
                status="incomplete",
                incomplete_details=SimpleNamespace(reason="max_output_tokens"),
                output_text='{"status":"completed","findings":[' + secret,
                output=[],
            )

    assessor = OpenAISemanticAssessorV2(
        client=SimpleNamespace(responses=Responses()),
        model="test-model",
    )
    with pytest.raises(SemanticAssessmentProviderError) as captured:
        assessor.assess({}, {}, {})
    assert assessor.diagnostic_codes == (
        "semantic_provider_response_incomplete_max_output_tokens",
    )
    assert assessor.diagnostic_locations == ()
    assert secret not in str(captured.value)
    assert secret not in repr(vars(assessor))
    assert captured.value.__context__ is None
    assert captured.value.__cause__ is None


def test_semantic_assessor_keeps_only_safe_codes_and_locations_for_qg_diagnostics():
    ai_reading = {
        "sections": [
            {"section_id": section_id, "interpretation": [{}]}
            for section_id in (
                "core_personality", "career", "wealth", "relationships",
                "health", "current_luck", "future_flow", "advice",
            )
        ]
    }
    result = {
        "status": "completed",
        "findings": [{
            "code": "prohibited_claim",
            "path": "/sections/4/interpretation/0",
            "evidence": [{
                "source_contract": "reading_context_v2",
                "path": "/missing",
            }],
        }],
    }
    assessor = OpenAISemanticAssessorV2(
        client=_client(semantic_results=[result]),
        model="test-model",
    )
    assert assessor.assess(ai_reading, {}, {}) == result
    assert assessor.diagnostic_codes == (
        "prohibited_claim",
        "semantic_result_evidence_path_invalid",
    )
    assert assessor.diagnostic_locations == ("health.interpretation[0]",)


def test_invalid_named_section_finding_path_stays_rejected_but_has_safe_location():
    ai_reading = {
        "sections": [
            {"section_id": section_id, "interpretation": [{}]}
            for section_id in (
                "core_personality", "career", "wealth", "relationships",
                "health", "current_luck", "future_flow", "advice",
            )
        ]
    }
    result = {
        "status": "completed",
        "findings": [{
            "code": "claim_type_mismatch",
            "path": "/sections/health/interpretation/0",
            "evidence": [{
                "source_contract": "ai_reading_v2",
                "path": "/sections/4/interpretation/0",
            }],
        }],
    }
    assessor = OpenAISemanticAssessorV2(
        client=_client(semantic_results=[result]),
        model="test-model",
    )

    assert assessor.assess(ai_reading, {}, {}) == result
    assert assessor.diagnostic_codes == (
        "claim_type_mismatch",
        "semantic_result_finding_path_invalid",
    )
    assert assessor.diagnostic_locations == ("health.interpretation[0]",)


def test_pipeline_reproduces_invalid_semantic_finding_path_as_safe_review():
    result = {
        "status": "completed",
        "findings": [{
            "code": "claim_type_mismatch",
            "path": "/sections/health/interpretation/0",
            "evidence": [{
                "source_contract": "ai_reading_v2",
                "path": "/sections/4/summary",
            }],
        }],
    }
    fake = _client(semantic_results=[result])

    with pytest.raises(CustomerReadingUnavailableError) as captured:
        run_customer_reading(
            validate_customer_input(_values()),
            client=fake,
            model="test-model",
            reference_time=FIXED,
        )

    error = captured.value
    assert error.stage == "quality_gate"
    assert error.reason_code == "quality_gate_review"
    assert error.decision == "review"
    assert error.blocking_codes == ("semantic_assessment_failed",)
    assert error.diagnostic_codes == (
        "claim_type_mismatch",
        "semantic_result_finding_path_invalid",
    )
    assert error.diagnostic_locations == ("health.interpretation[0]",)
    assert fake.responses.semantic_calls == 1
    assert fake.responses.repair_calls == 0


def test_post_repair_semantic_infrastructure_failure_has_safe_diagnostic():
    class Responses(FakeResponses):
        def create(self, **kwargs):
            name = kwargs["text"]["format"]["name"]
            if name == "ai_reading_v2":
                response = super().create(**kwargs)
                payload = json.loads(response.output_text)
                block = payload["sections"]["core_personality"]["summary"]
                block["text"] = (
                    "trusted sourceにない数値999999です。"
                )
                block["claim_type"] = "astrology"
                block["source_fact_codes"] = [
                    kwargs["text"]["format"]["schema"]["$defs"]
                    ["fact_code_array"]["items"]["enum"][0]
                ]
                response.output_text = json.dumps(
                    payload,
                    ensure_ascii=False,
                    separators=(",", ":"),
                    allow_nan=False,
                )
                return response
            if name == "semantic_assessment_v2":
                self.calls.append(deepcopy(kwargs))
                self.semantic_calls += 1
                return SimpleNamespace(
                    status="incomplete",
                    incomplete_details=SimpleNamespace(reason="max_output_tokens"),
                    output_text='{"status":"completed","findings":[',
                    output=[],
                )
            return super().create(**kwargs)

    responses = Responses(
        repair_results=[{
            "patches": [{
                "op": "replace",
                "path": "/sections/0/summary/text",
                "value": "数値を追加せず、trusted factに沿って説明します。",
            }],
        }],
    )
    with pytest.raises(CustomerReadingUnavailableError) as captured:
        run_customer_reading(
            validate_customer_input(_values()),
            client=SimpleNamespace(responses=responses),
            model="test-model",
            reference_time=FIXED,
        )
    error = captured.value
    assert error.stage == "post_repair_quality_gate"
    assert error.reason_code == "repair_exhausted"
    assert error.decision == "review"
    assert error.blocking_codes == ("semantic_assessment_failed",)
    assert error.diagnostic_codes == (
        "semantic_provider_response_incomplete_max_output_tokens",
    )
    assert error.diagnostic_locations == ()
    assert responses.semantic_calls == 1
    assert responses.repair_calls == 1


def test_route_sanitizes_provider_failure(monkeypatch, caplog):
    def fail(_value):
        raise CustomerReadingUnavailableError(
            "API_KEY_SECRET raw response",
            stage="generator",
            reason_code="generator_provider_request_failed",
        )

    monkeypatch.setattr(customer_routes, "run_customer_reading", fail)
    with caplog.at_level("WARNING"):
        response = _post(TestClient(app), _values())
    assert response.status_code == 503
    assert "確認が必要な状態" in response.text
    assert "API_KEY_SECRET" not in response.text
    assert "raw response" not in response.text
    assert "Traceback" not in response.text
    assert "stage=generator" in caplog.text
    assert "reason=generator_provider_request_failed" in caplog.text
    assert "API_KEY_SECRET" not in caplog.text
    assert "raw response" not in caplog.text


def test_pipeline_public_error_does_not_retain_provider_secret_chain():
    secret = "API_KEY_SECRET raw response from generator"

    class Responses:
        def create(self, **_kwargs):
            raise RuntimeError(secret)

    with pytest.raises(CustomerReadingUnavailableError) as captured:
        run_customer_reading(
            validate_customer_input(_values()),
            client=SimpleNamespace(responses=Responses()),
            model="test-model",
            reference_time=FIXED,
        )
    error = captured.value
    assert secret not in str(error)
    assert error.stage == "generator"
    assert error.reason_code == "generator_provider_request_failed"
    assert error.decision is None
    assert error.blocking_codes == ()
    assert error.__context__ is None
    assert error.__cause__ is None


def test_pipeline_classifies_provider_schema_rejection_without_secret_leak():
    secret = "API_KEY_SECRET raw invalid schema response"

    class ProviderBadRequest(RuntimeError):
        status_code = 400
        code = "invalid_json_schema"

    class Responses:
        def create(self, **_kwargs):
            raise ProviderBadRequest(secret)

    with pytest.raises(CustomerReadingUnavailableError) as captured:
        run_customer_reading(
            validate_customer_input(_values()),
            client=SimpleNamespace(responses=Responses()),
            model="test-model",
            reference_time=FIXED,
        )
    error = captured.value
    assert error.stage == "generator"
    assert error.reason_code == "generator_provider_schema_rejected"
    assert secret not in str(error)
    assert vars(error) == {
        "stage": "generator",
        "reason_code": "generator_provider_schema_rejected",
        "decision": None,
        "blocking_codes": (),
    }
    assert error.__context__ is None
    assert error.__cause__ is None


def test_pipeline_reports_incomplete_generator_response_without_partial_output():
    secret = "PARTIAL_PROVIDER_OUTPUT_SECRET"

    class Responses:
        def create(self, **_kwargs):
            return SimpleNamespace(
                status="incomplete",
                incomplete_details=SimpleNamespace(reason="max_output_tokens"),
                output_text='{"summary":"' + secret,
                output=[],
            )

    with pytest.raises(CustomerReadingUnavailableError) as captured:
        run_customer_reading(
            validate_customer_input(_values()),
            client=SimpleNamespace(responses=Responses()),
            model="test-model",
            reference_time=FIXED,
        )
    error = captured.value
    assert error.stage == "generator"
    assert error.reason_code == "generator_response_incomplete_max_output_tokens"
    assert secret not in str(error)
    assert error.__context__ is None
    assert error.__cause__ is None


def test_pipeline_reports_sanitized_generator_semantic_code_and_location():
    class Responses:
        def create(self, **kwargs):
            assert kwargs["text"]["format"]["name"] == "ai_reading_v2"
            model_input = json.loads(
                kwargs["input"][0]["content"].split("model_input=", 1)[1]
            )
            request = {
                "trusted_attachments": {
                        "future_flow_years": model_input["future_flow_years"],
                        "long_term_luck_pillars": model_input["long_term_luck_pillars"],
                        "consultation_present": model_input["reading_context"]["consultation"] is not None,
                }
            }
            payload = base._model_payload(request)
            fact_code = kwargs["text"]["format"]["schema"]["$defs"][
                "fact_code_array"
            ]["items"]["enum"][0]
            payload["summary"]["source_fact_codes"] = [fact_code]
            payload = base._transport_payload(payload)
            return SimpleNamespace(
                status="completed",
                output_text=json.dumps(
                    payload,
                    ensure_ascii=False,
                    separators=(",", ":"),
                    allow_nan=False,
                ),
                output=[],
            )

    with pytest.raises(CustomerReadingUnavailableError) as captured:
        run_customer_reading(
            validate_customer_input(_values()),
            client=SimpleNamespace(responses=Responses()),
            model="test-model",
            reference_time=FIXED,
        )
    error = captured.value
    assert error.stage == "generator"
    assert error.reason_code == "generator_semantic_practical_has_grounding_references"
    assert error.diagnostic_codes == ("practical_has_grounding_references",)
    assert error.diagnostic_locations == ("summary",)
    assert error.decision is None
    assert error.blocking_codes == ()
    assert error.__context__ is None
    assert error.__cause__ is None


def test_duplicate_or_non_form_request_is_rejected_before_pipeline():
    client = TestClient(app)
    duplicate = client.post(
        "/app/reading",
        content="birth_date=1984-01-01&birth_date=1985-01-01",
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert duplicate.status_code == 422
    wrong_type = client.post(
        "/app/reading",
        json={"birth_date": "1984-01-01"},
    )
    assert wrong_type.status_code == 422


def test_customer_result_preserves_arbitrary_ai_prose_and_escapes_html():
    prose = (
        "これは顧客画面の表示確認用文章です。複数の文をそのまま表示します。"
        "<script>alert('x')</script> & 表示安全性も確認します。"
    )
    product = _product_with_prose(prose)
    before = product.to_dict()
    document = customer_routes._render_customer_result(product)
    assert prose not in document
    assert "これは顧客画面の表示確認用文章です。複数の文をそのまま表示します。" in document
    assert "&lt;script&gt;alert(&#x27;x&#x27;)&lt;/script&gt; &amp;" in document
    assert "<script>alert('x')</script>" not in document
    assert product.to_dict() == before


def test_customer_result_formats_age_precision_without_mutating_product():
    product = _product("gc03")
    before = product.to_dict()
    exact_age = before["reading_context"]["luck"]["current_luck"]["exact_age"]
    document = customer_routes._render_customer_result(product)
    assert f"約{exact_age:.1f}歳" in document
    assert str(exact_age) not in document
    assert product.to_dict() == before


def test_customer_result_uses_sales_order_and_moves_consultation_near_top(monkeypatch):
    fake = _client()
    monkeypatch.setattr(customer_routes, "run_customer_reading", _route_pipeline(fake))
    response = _post(TestClient(app), _values())

    assert response.status_code == 200
    ordered_ids = (
        "cover",
        "consultation-conclusion",
        "reading-overview",
        "customer-chart",
        "key-points",
        "core_personality",
        "career",
        "wealth",
        "relationships",
        "health",
        "current-fortune",
        "five-year-flow",
        "long-term-luck",
        "advice",
        "notices-disclaimer",
    )
    positions = [response.text.index(f'id="{section_id}"') for section_id in ordered_ids]
    assert positions == sorted(positions)
    assert response.text.index("相談への回答") < response.text.index(">あなたの命式<")
    assert "今後の仕事について相談したいです。" in response.text
    assert "あなたの命式から読み解く、これからの道しるべ" in response.text
    assert ">表紙<" not in response.text
    assert "<h1>四柱推命鑑定書</h1>" in response.text
    assert ">総合鑑定<" in response.text
    assert ">まずお伝えしたい結論<" in response.text


def test_customer_result_without_consultation_omits_consultation_feature():
    document = customer_routes._render_customer_result(_product("gc10"))
    assert 'id="consultation-conclusion"' not in document
    assert "ご相談内容" not in document
    assert "相談への回答" not in document
    assert document.index('id="cover"') < document.index('id="reading-overview"')
    assert document.index('id="reading-overview"') < document.index('id="customer-chart"')


@pytest.mark.parametrize("case", ["gc03", "gc10"])
def test_customer_long_term_luck_is_complete_readable_and_owner_sourced(case):
    product = _product(case)
    before = product.to_dict()
    luck = before["reading_context"]["luck"]["luck_pillars"]
    document = customer_routes._render_customer_result(product)

    assert "人生の長期的な流れをおよそ10年単位で確認" in document
    assert "天干通変星" in document
    assert "五行（天干・地支）" in document
    for pillar in luck["pillars"]:
        assert f'第{pillar["index"]}運' in document
        assert pillar["ganzhi"] in document
        assert pillar["stem_ten_god"] in document
        assert f'約{pillar["start_age"]:.1f}歳' in document
        assert f'約{pillar["end_age"]:.1f}歳' in document
    assert "stem_useful_relation" not in document
    assert "branch_useful_relation" not in document
    assert product.to_dict() == before


def test_customer_result_hides_internal_metadata_and_machine_labels(monkeypatch):
    fake = _client()
    monkeypatch.setattr(customer_routes, "run_customer_reading", _route_pipeline(fake))
    response = _post(TestClient(app), _values())
    assert response.status_code == 200
    forbidden = (
        "claim_type",
        "source_fact_codes",
        "source_components",
        "warning_id",
        "uncertainty_id",
        "source_path",
        "schema_version",
        "source_bundle_sha256",
        "supportive",
        "mixed",
        "月令総合スコア",
        "成立スコア",
    )
    for marker in forbidden:
        assert marker not in response.text


def test_customer_result_print_css_hides_web_navigation_and_preserves_tables():
    document = customer_routes._render_customer_result(_product("gc03"))
    assert '<nav class="web-nav">' in document
    assert "@media print" in document
    assert ".web-nav{display:none!important}" in document
    assert "break-inside:avoid-page" in document
    assert "thead{display:table-header-group;}" in document
    assert "#current-fortune > .presentation-subsection:first-of-type{break-inside:auto;page-break-inside:auto;}" in document
    assert "#current-fortune{break-before:page!important;page-break-before:always!important;}" in document


def test_customer_renderer_is_presentation_only_and_does_not_add_astrology_calls():
    source = inspect.getsource(renderer_v2._render_customer_visible)
    for forbidden_call in (
        "calculate_chart",
        "build_reading_context",
        "generate_ai_reading",
        "evaluate_ai_reading_quality",
        "repair_ai_reading",
    ):
        assert forbidden_call not in source


def _legacy_long_term_detail_cards_fixture_note():
    return
    """
    block = {"text": "long-term prose", "claim_type": "luck_astrology",
        "text": "螟ｧ驕九・謗｡縺ｮ譁ｹ驥昴〒縺吶・,
        "claim_type": "luck_astrology",
        "source_fact_codes": [],
        "source_components": ["luck_pillars"],
        "warnings": [],
        "uncertainty": [],
    }
    """
    detail = {
        "index": 4, "ganzhi": "乙亥", "start_age": 39.257612,
        "end_age": 49.257612, "stem_ten_god": "偏印",
        "stem_element": "木", "branch_element": "水",
        "title": block, "theme": block, "career": block, "wealth": block,
        "relationships": block, "caution": block, "advice": [block, block],
    }
    html = renderer_v2._render_long_term_details({"long_term_luck": [detail]})
    assert "大運から見る人生の流れ" in html
    assert "約39.3歳" in html and "約49.3歳" in html
    assert html.count("螟ｧ驕九・謗｡縺ｮ譁ｹ驥昴〒縺吶・") >= 7
