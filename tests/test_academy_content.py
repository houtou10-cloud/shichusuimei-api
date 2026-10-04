from __future__ import annotations

import json

from fastapi.testclient import TestClient

from engine.academy_content import CONTENT_ROOT, all_lessons, lesson_by_number, load_legacy_catalog, load_lesson_quiz
from api.academy_routes import _curriculum_quiz_name
from main import app


CLIENT = TestClient(app)


def test_curriculum_is_complete_and_data_driven():
    lessons = all_lessons()
    assert 80 <= len(lessons) <= 90
    assert len({lesson["lesson_id"] for lesson in lessons}) == len(lessons)
    assert [lesson["order"] for lesson in lessons] == list(range(1, len(lessons) + 1))
    for lesson in lessons:
        assert (CONTENT_ROOT / "lessons" / f'{lesson["lesson_id"]}.md').exists()
        quiz = CONTENT_ROOT / "quizzes" / f'{lesson["lesson_id"]}.json'
        assert quiz.exists()
        assert json.loads(quiz.read_text(encoding="utf-8"))["questions"]


def test_legacy_catalog_tracks_all_282_source_numbers():
    catalog = load_legacy_catalog()["lessons"]
    assert {item["legacy_lesson"] for item in catalog} == set(range(1, 283))
    assert all(item["new_lessons"] for item in catalog)
    assert all(item["legacy_title"] and item["source_file"] for item in catalog)
    assert all(item["classification"] in {"core", "merged", "detail"} for item in catalog)
    assert all(item.get("source_verified") is True for item in json.loads((CONTENT_ROOT / "curriculum.json").read_text(encoding="utf-8"))["lessons"])
    library = json.loads((CONTENT_ROOT / "detail_library.json").read_text(encoding="utf-8"))
    assert library["status"] == "draft"
    assert set(library["entry_schema"]) >= {"legacy_lesson", "new_lessons", "source_file"}


def test_curriculum_routes_have_navigation_progress_and_safe_quiz():
    for path in ("/academy/course/1/1", "/academy/course/6/7", "/academy/course/12/7"):
        response = CLIENT.get(path)
        assert response.status_code == 200
        assert response.text.count('<nav class="nav">') == 1
        assert "理解度チェック" in response.text
        assert "answer" not in response.text
    assert CLIENT.get("/academy/course/13/1").status_code == 404


def test_curriculum_quiz_is_server_scored():
    response = CLIENT.post(
        "/academy/course/1/2/check",
        data={"lesson_002_002_q1": "0", "lesson_002_002_q2": "0"},
    )
    assert response.status_code == 200
    assert "3問中2問正解" in response.text


def test_all_lessons_have_source_grounding_and_non_repeated_quizzes():
    lessons = all_lessons()
    assert all(lesson["source_lessons"] and lesson["source_files"] for lesson in lessons)
    assert all(len(lesson["source_lessons"]) in {3, 4} for lesson in lessons)
    signatures = []
    for lesson in lessons:
        body = (CONTENT_ROOT / "lessons" / f'{lesson["lesson_id"]}.md').read_text(encoding="utf-8")
        assert len(body) > 700
        assert "学習資料から読む" in body
        quiz = json.loads((CONTENT_ROOT / "quizzes" / f'{lesson["lesson_id"]}.json').read_text(encoding="utf-8"))
        assert 3 <= len(quiz["questions"]) <= 5
        signatures.append(tuple(q["prompt"] for q in quiz["questions"]))
    assert len(set(signatures)) == len(signatures)


def test_all_84_lessons_are_gettable_and_quizzes_are_server_scored():
    lessons = all_lessons()
    assert len(lessons) == 84
    for lesson in lessons:
        chapter = int(lesson["chapter"])
        number = ((int(lesson["order"]) - 1) % 7) + 1
        response = CLIENT.get(f"/academy/course/{chapter}/{number}")
        assert response.status_code == 200
        assert f' action="/academy/course/{chapter}/{number}/check"' in response.text
        assert '"answer"' not in response.text
        for marker in ("原典参照", "参照元:", "旧第", ".zip", ".txt", "source_file", "source_files", "legacy_catalog", "engine"):
            assert marker not in response.text
        quiz = load_lesson_quiz(lesson["lesson_id"])
        quiz_text = json.dumps(quiz, ensure_ascii=False)
        for marker in ("旧第", "原典", "参照元", ".zip", ".txt", "source_file"):
            assert marker not in quiz_text
        values = {
            _curriculum_quiz_name(lesson["lesson_id"], q["id"]): q["answer"]
            for q in quiz["questions"]
        }
        result = CLIENT.post(f"/academy/course/{chapter}/{number}/check", data=values)
        assert result.status_code == 200
        assert f'{len(quiz["questions"])}問中{len(quiz["questions"])}問正解' in result.text
        assert "この講座を修了しました" in result.text


def test_courses_page_exposes_all_84_lesson_links():
    response = CLIENT.get("/academy/courses")
    assert response.status_code == 200
    assert response.text.count('/academy/course/') == 84
    assert "第12章" in response.text
    assert "第84講" in response.text


def test_curriculum_boundaries_and_fail_result():
    first = CLIENT.get("/academy/course/1/1")
    assert "前の講座" not in first.text
    last = CLIENT.get("/academy/course/12/7")
    assert 'href="/academy/course/13/' not in last.text
    failed = CLIENT.post(
        "/academy/course/1/1/check",
        data={"lesson_q1": "9", "lesson_q2": "9", "lesson_q3": "9"},
    )
    assert failed.status_code == 200
    assert "3問中0問正解" in failed.text
    assert "もう一度復習して挑戦しましょう" in failed.text
