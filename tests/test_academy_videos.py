"""講座動画（YouTube 限定公開）の登録と表示。"""

import json

from fastapi.testclient import TestClient

import engine.academy_content as academy_content
from main import app
from scripts.register_academy_videos import parse_line

CLIENT = TestClient(app)


def test_parse_line_accepts_common_youtube_urls():
    assert parse_line("1 https://youtu.be/abcdefghijk") == ("001", "https://www.youtube-nocookie.com/embed/abcdefghijk")
    assert parse_line("第12講 https://www.youtube.com/watch?v=abc_efg-ijk&t=3") == ("012", "https://www.youtube-nocookie.com/embed/abc_efg-ijk")
    assert parse_line("084_ケーススタディ https://youtube.com/shorts/abcdefghijk") == ("084", "https://www.youtube-nocookie.com/embed/abcdefghijk")
    assert parse_line("5 -") == ("005", None)
    assert parse_line("85 https://youtu.be/abcdefghijk") is None
    assert parse_line("# コメント") is None
    assert parse_line("7 https://example.com/video") is None


def test_registered_video_is_embedded_and_listed(tmp_path, monkeypatch):
    root = tmp_path / "academy_content"
    root.mkdir()
    (root / "curriculum.json").write_text((academy_content.CONTENT_ROOT / "curriculum.json").read_text(encoding="utf-8"), encoding="utf-8")
    (root / "videos.json").write_text(json.dumps({"001": "https://www.youtube-nocookie.com/embed/abcdefghijk"}), encoding="utf-8")
    monkeypatch.setattr(academy_content, "CONTENT_ROOT", root)

    lessons = academy_content.all_lessons()
    assert lessons[0]["video_url"] == "https://www.youtube-nocookie.com/embed/abcdefghijk"
    assert "video_url" not in lessons[1]

    courses = CLIENT.get("/academy/courses").text
    assert courses.count("動画あり") == 1
    assert "動画未登録" in courses
    assert "動画は1講を公開中" in CLIENT.get("/academy").text


def test_lessons_without_videos_keep_placeholder():
    registered = academy_content.load_video_urls()
    lesson = academy_content.lesson_by_number(1, 1)
    page = CLIENT.get("/academy/course/1/1").text
    if registered.get("001"):
        assert f'<iframe src="{registered["001"]}"' in page
    else:
        assert "動画未登録" in page
        assert lesson.get("video_url") is None
