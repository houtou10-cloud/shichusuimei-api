"""YouTube の動画URLを講座に登録する（academy_content/videos.json を更新）。

使い方：
  python scripts/register_academy_videos.py urls.txt
  python scripts/register_academy_videos.py urls.txt --dry-run

urls.txt は 1 行に「講座番号 と YouTube の URL」を書く（順番・区切りは自由）。
  1 https://youtu.be/abcdefghijk
  第2講 https://www.youtube.com/watch?v=abcdefghijk
  003_日主とは何か https://youtube.com/shorts/abcdefghijk
URL の代わりに「-」と書くと、その講の登録を外す。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

VIDEOS = Path(__file__).resolve().parent.parent / "academy_content" / "videos.json"
LESSON_COUNT = 84
_ID = r"([A-Za-z0-9_-]{11})"
_URL_PATTERNS = (
    re.compile(r"youtu\.be/" + _ID),
    re.compile(r"[?&]v=" + _ID),
    re.compile(r"/(?:embed|shorts|live)/" + _ID),
)


def embed_url(video_id: str) -> str:
    return f"https://www.youtube-nocookie.com/embed/{video_id}"


def parse_line(line: str) -> tuple[str, str | None] | None:
    """1 行から（講座番号, 埋め込みURL または None=登録解除）を取り出す。読めない行は None。"""
    text = line.strip()
    if not text or text.startswith("#"):
        return None
    number = re.search(r"\d{1,3}", text)
    if not number or not 1 <= int(number.group()) <= LESSON_COUNT:
        return None
    lesson_id = f"{int(number.group()):03d}"
    rest = text[number.end():]
    if rest.strip() in {"-", "－"}:
        return lesson_id, None
    for pattern in _URL_PATTERNS:
        found = pattern.search(rest)
        if found:
            return lesson_id, embed_url(found.group(1))
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    videos = json.loads(VIDEOS.read_text(encoding="utf-8")) if VIDEOS.exists() else {}
    videos = {f"{i:03d}": videos.get(f"{i:03d}", "") for i in range(1, LESSON_COUNT + 1)}
    skipped = []
    changed = 0
    for raw in args.source.read_text(encoding="utf-8").splitlines():
        parsed = parse_line(raw)
        if parsed is None:
            if raw.strip() and not raw.strip().startswith("#"):
                skipped.append(raw.strip())
            continue
        lesson_id, url = parsed
        videos[lesson_id] = url or ""
        changed += 1

    registered = sum(1 for url in videos.values() if url)
    print(f"更新 {changed} 行 / 登録済み {registered} / {LESSON_COUNT} 講")
    for line in skipped:
        print(f"読めなかった行: {line}", file=sys.stderr)
    missing = [key for key, url in videos.items() if not url]
    if missing:
        print("未登録の講: " + ", ".join(missing))
    if not args.dry_run:
        VIDEOS.write_text(json.dumps(videos, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 1 if skipped else 0


if __name__ == "__main__":
    raise SystemExit(main())
