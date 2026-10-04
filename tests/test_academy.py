from __future__ import annotations

from fastapi.testclient import TestClient

from engine.academy_v1 import build_academy_projection
from engine.chart import calculate_chart
from api.models import ChartRequest
from main import app


CLIENT = TestClient(app)


def _fixture_values(**overrides):
    values = {
        "birth_date": "1984-07-10",
        "birth_place": "愛知県",
        "birth_hour": "22",
        "birth_minute": "45",
        "gender": "male",
    }
    values.update(overrides)
    return values


def _fixture_projection():
    return build_academy_projection(
        calculate_chart(
            ChartRequest(
                birth_date="1984-07-10",
                birth_time="22:45",
                birth_place="愛知県",
                gender="male",
            )
        )
    )


def test_academy_home_and_start_do_not_call_provider_or_leak_answers():
    response = CLIENT.get("/academy")
    assert response.status_code == 200
    assert "八雲式 四柱推命Academy" in response.text

    response = CLIENT.post("/academy/start", data=_fixture_values())
    assert response.status_code == 200
    for pillar in ("甲子", "辛未", "乙巳", "丁亥"):
        assert pillar in response.text
    assert "correct_answer" not in response.text
    assert "source_fact_codes" not in response.text
    assert "reading_context" not in response.text
    assert "final_strength_judgment" not in response.text
    assert "pattern_judgment" not in response.text


def test_academy_fixture_authority_projection_is_exact():
    projection = _fixture_projection()
    assert projection["day_master"] == "乙"
    assert projection["month_hidden_stems"] == ("己", "丁", "乙")
    assert projection["month_hidden_stem_ten_gods"] == ("偏財", "食神", "比肩")
    assert projection["strength"] == "中和"
    assert projection["pattern"] == "食神格"
    assert projection["useful_element"] == "土"
    assert projection["pattern_evidence"]["selected_hidden_stem"] == "丁"
    assert projection["pattern_evidence"]["selected_ten_god"] == "食神"
    assert projection["pattern_evidence"]["exposure_positions"] == ("hour",)


def test_academy_check_compares_all_six_answers_on_server():
    values = _fixture_values(
        q1="乙",
        q2=["己", "丁", "乙"],
        q3_0="偏財",
        q3_1="食神",
        q3_2="比肩",
        q4="中和",
        q5="食神格",
        q6="土",
    )
    response = CLIENT.post("/academy/check", data=values)
    assert response.status_code == 200
    assert "6問 / 6問一致" in response.text
    assert "月干" not in response.text

    values["q6"] = "木"
    response = CLIENT.post("/academy/check", data=values)
    assert response.status_code == 200
    assert "5問 / 6問一致" in response.text


def test_academy_unknown_birth_time_uses_three_pillar_scope_without_fake_hour():
    values = _fixture_values(birth_hour="", birth_minute="", birth_time_unknown="1")
    response = CLIENT.post("/academy/start", data=values)
    assert response.status_code == 200
    assert "甲子" in response.text
    assert "辛未" in response.text
    assert "乙巳" in response.text
    assert "丁亥" not in response.text


def test_existing_customer_routes_remain_available():
    assert CLIENT.get("/app").status_code == 200
    assert CLIENT.get("/app/reading").status_code == 200
