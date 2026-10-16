from __future__ import annotations

import json

from fastapi.testclient import TestClient

from engine.academy_content import CONTENT_ROOT, all_lessons, lesson_by_number, load_legacy_catalog, load_lesson_quiz
from api.academy_routes import _curriculum_quiz_name, _render_video_area
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


def test_legacy_curriculum_quiz_is_server_scored():
    response = CLIENT.post(
        "/academy/course/1/2/check",
        data={"lesson_002_002_q1": "0", "lesson_002_002_q2": "1", "lesson_002_002_q3": "2"},
    )
    assert response.status_code == 200
    assert "3問中3問正解" in response.text


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


def test_mobile_course_catalog_has_collapsible_chapters_and_device_progress():
    response = CLIENT.get("/academy/courses")
    assert response.status_code == 200
    assert response.text.count('class="chapter-card"') == 12
    assert 'data-progress-total="84"' in response.text
    assert 'key = "yakumo_academy_completed_v1"' in response.text
    assert "ログイン同期・端末間同期には未対応" in response.text
    assert response.text.count('class="lesson-status"') == 84
    assert response.text.count('class="lesson-minutes"') == 84


def test_course_catalog_has_client_side_title_search_without_external_requests():
    response = CLIENT.get("/academy/courses")
    assert response.status_code == 200
    assert 'role="search"' in response.text
    assert "data-course-search" in response.text
    assert 'aria-live="polite"' in response.text
    assert response.text.count("data-course-title=") == 84
    assert "fetch(" not in response.text
    assert "84講が一致しました" not in response.text


def test_lesson_screen_discloses_missing_video_and_has_adjacent_navigation():
    middle = CLIENT.get("/academy/course/6/4")
    assert middle.status_code == 200
    assert "再生可能な動画URLが登録されていません" in middle.text
    assert 'aria-label="講座間の移動"' in middle.text
    assert "前の講座" in middle.text
    assert "次の講座" in middle.text
    assert "3分の2以上の正解" in middle.text
    assert "補助教材を読む" in middle.text
    assert middle.text.index("動画未登録") < middle.text.index("補助教材を読む")
    assert 'const currentUrl = "/academy/course/6/4"' in middle.text
    assert "yakumo_academy_last_lesson_v1" in middle.text


def test_portal_and_catalog_offer_device_local_resume_link():
    for path in ("/academy", "/academy/courses"):
        response = CLIENT.get(path)
        assert response.status_code == 200
        assert "data-resume-link" in response.text
        assert "続きから学ぶ" in response.text
        assert "yakumo_academy_last_lesson_v1" in response.text
        assert "[hidden]{display:none!important}" in response.text


def test_video_area_only_embeds_supported_https_providers():
    allowed = _render_video_area({
        "title": "確認用",
        "video_url": "https://www.youtube-nocookie.com/embed/example",
    })
    assert '<iframe src="https://www.youtube-nocookie.com/embed/example"' in allowed
    assert "allowfullscreen" in allowed

    unsupported = _render_video_area({
        "title": "確認用",
        "video_url": "https://example.com/video",
    })
    assert "動画を表示できません" in unsupported
    assert "<iframe" not in unsupported


def test_only_a_passing_quiz_records_local_completion():
    quiz = load_lesson_quiz("001")
    passed_values = {
        _curriculum_quiz_name("001", question["id"]): question["answer"]
        for question in quiz["questions"]
    }
    passed = CLIENT.post("/academy/course/1/1/check", data=passed_values)
    assert 'const justCompleted = "001"' in passed.text

    failed = CLIENT.post(
        "/academy/course/1/1/check",
        data={"lesson_q1": "9", "lesson_q2": "9", "lesson_q3": "9"},
    )
    assert 'const justCompleted = ""' in failed.text


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
def test_legacy_first_chapter_has_topic_specific_theory_and_rendered_tables():
    lessons = all_lessons()[:7]
    theories = []
    for lesson in lessons:
        body = (CONTENT_ROOT / "lessons" / f'{lesson["lesson_id"]}.md').read_text(encoding="utf-8")
        assert "### 理論解説" in body
        theory = body.split("### 理論解説", 1)[1].split("### 専門用語", 1)[0].strip()
        assert len(theory) >= 500
        theories.append(theory)
    assert len(set(theories)) == 7
    response = CLIENT.get("/academy/course/1/1")
    assert response.status_code == 200
    assert '<table class="lesson-table">' in response.text
    assert "lesson-table-wrap" in response.text


def test_first_chapter_quizzes_are_complete_and_answer_positions_vary():
    quizzes = [load_lesson_quiz(f"{number:03d}") for number in range(1, 8)]
    assert sum(len(quiz["questions"]) for quiz in quizzes) == 21
    for question_index in range(3):
        positions = {quiz["questions"][question_index]["answer"] for quiz in quizzes}
        assert len(positions) >= 2


# ASCII-only structural assertions avoid coupling regression tests to console
# encoding while still verifying the rewritten chapter content.
def test_first_chapter_has_topic_specific_theory_and_rendered_tables():
    lessons = all_lessons()[:7]
    bodies = []
    for lesson in lessons:
        body = (CONTENT_ROOT / "lessons" / f'{lesson["lesson_id"]}.md').read_text(encoding="utf-8")
        assert body.count("### ") >= 8
        assert len(body) >= 1000
        bodies.append(body)
    assert len(set(bodies)) == 7
    response = CLIENT.get("/academy/course/1/1")
    assert response.status_code == 200
    assert '<table class="lesson-table">' in response.text
    assert "lesson-table-wrap" in response.text


def test_curriculum_quiz_is_server_scored():
    response = CLIENT.post(
        "/academy/course/1/2/check",
        data={"lesson_002_002_q1": "0", "lesson_002_002_q2": "1", "lesson_002_002_q3": "2"},
    )
    assert response.status_code == 200
    assert "3問中3問正解" in response.text
