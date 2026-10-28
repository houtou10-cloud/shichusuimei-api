"""Data-driven, provider-free Academy curriculum loader."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


CONTENT_ROOT = Path(__file__).resolve().parent.parent / "academy_content"


def load_video_urls() -> dict[str, str]:
    """academy_content/videos.json（講座番号 → 埋め込み用の動画URL）。未登録の講は空文字。"""
    path = CONTENT_ROOT / "videos.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {str(key): str(value or "").strip() for key, value in data.items()}


def load_curriculum() -> dict[str, Any]:
    curriculum = json.loads((CONTENT_ROOT / "curriculum.json").read_text(encoding="utf-8"))
    videos = load_video_urls()
    for lesson in curriculum["lessons"]:
        if videos.get(lesson["lesson_id"]):
            lesson["video_url"] = videos[lesson["lesson_id"]]
    return curriculum


def load_legacy_catalog() -> dict[str, Any]:
    return json.loads((CONTENT_ROOT / "legacy_catalog.json").read_text(encoding="utf-8"))


def lesson_by_number(chapter: int, lesson: int) -> dict[str, Any] | None:
    if chapter < 1 or lesson < 1:
        return None
    chapter_lessons = [item for item in load_curriculum()["lessons"] if item["chapter"] == chapter]
    return chapter_lessons[lesson - 1] if lesson <= len(chapter_lessons) else None


def load_lesson_content(lesson_id: str) -> str:
    return (CONTENT_ROOT / "lessons" / f"{lesson_id}.md").read_text(encoding="utf-8")


def load_lesson_quiz(lesson_id: str) -> dict[str, Any]:
    return json.loads((CONTENT_ROOT / "quizzes" / f"{lesson_id}.json").read_text(encoding="utf-8"))


def all_lessons() -> list[dict[str, Any]]:
    return list(load_curriculum()["lessons"])


__all__ = ["CONTENT_ROOT", "all_lessons", "lesson_by_number", "load_curriculum", "load_legacy_catalog", "load_lesson_content", "load_lesson_quiz", "load_video_urls"]
