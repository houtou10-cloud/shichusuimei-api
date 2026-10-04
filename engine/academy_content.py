"""Data-driven, provider-free Academy curriculum loader."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


CONTENT_ROOT = Path(__file__).resolve().parent.parent / "academy_content"


def load_curriculum() -> dict[str, Any]:
    return json.loads((CONTENT_ROOT / "curriculum.json").read_text(encoding="utf-8"))


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


__all__ = ["CONTENT_ROOT", "all_lessons", "lesson_by_number", "load_curriculum", "load_legacy_catalog", "load_lesson_content", "load_lesson_quiz"]
