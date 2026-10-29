"""Server-rendered, provider-free Academy MVP."""

from __future__ import annotations

from html import escape
import json
import re
from urllib.parse import parse_qsl, urlparse

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from fastapi.concurrency import run_in_threadpool

from api import academy_access
from api.academy_access import AcademyAccessError, Login
from api.academy_terms import ACADEMY_TERMS as _ACADEMY_TERMS

from api.customer_pipeline import (
    PREFECTURES,
    CustomerInputError,
    CustomerReadingInput,
    build_customer_chart_request,
    validate_customer_input,
)
from engine.academy_v1 import (
    ACADEMY_ELEMENT_OPTIONS,
    ACADEMY_STEM_OPTIONS,
    ACADEMY_STRENGTH_OPTIONS,
    ACADEMY_TEN_GOD_OPTIONS,
    build_academy_projection,
    grade_academy_answers,
    pattern_options,
)
from engine.chart import calculate_chart
from engine.academy_content import all_lessons, lesson_by_number, load_lesson_content, load_lesson_quiz


router = APIRouter()
_MAX_FORM_BYTES = 12_000
_STYLES = """
<style>
:root{color-scheme:light;--ink:#302820;--muted:#75685c;--paper:#fffdfa;--wash:#f5efe7;--line:#dfd1c2;--gold:#9a6a35;--deep:#5d3b25;--danger:#a33a35}
*{box-sizing:border-box}[hidden]{display:none!important}body{margin:0;background:linear-gradient(145deg,#f6f1eb,#eee5da);color:var(--ink);font-family:"Yu Mincho","Hiragino Mincho ProN","Noto Serif JP",serif;line-height:1.7}.shell{width:min(960px,calc(100% - 24px));margin:24px auto 56px;background:var(--paper);border:1px solid var(--line);box-shadow:0 16px 46px #422c1e18;border-radius:16px;overflow:hidden}.hero{padding:30px clamp(20px,5vw,54px);background:linear-gradient(120deg,#fffaf1,#f4eadc);border-bottom:1px solid var(--line)}.eyebrow{margin:0;color:var(--gold);font-size:.8rem;letter-spacing:.16em}.hero h1{margin:.2rem 0 .5rem;color:#422c1e;font-size:clamp(1.7rem,4vw,2.5rem)}.hero p{margin:.25rem 0;color:var(--muted)}.content{padding:28px clamp(20px,5vw,54px)}h2{color:var(--deep);border-bottom:1px solid var(--line);padding-bottom:.35rem;margin-top:1.6rem}.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px 22px}.full{grid-column:1/-1}label{display:block;font-weight:700;margin-bottom:.35rem}input,select{width:100%;font:inherit;padding:9px;border:1px solid #cdbdad;border-radius:7px;background:#fff}fieldset{border:1px solid var(--line);border-radius:10px;margin:18px 0;padding:15px}legend{font-weight:700;color:var(--deep)}.choice{display:inline-flex;align-items:center;gap:6px;margin:.25rem .8rem .25rem 0;font-weight:400}.choice input{width:auto}.button{display:inline-block;border:0;border-radius:8px;padding:12px 18px;background:linear-gradient(120deg,#6b4328,#9a6a35);color:#fff;font:700 1rem inherit;cursor:pointer;text-decoration:none}.nav{display:flex;gap:8px;flex-wrap:wrap;padding:12px clamp(20px,5vw,54px);background:#fffaf4;border-bottom:1px solid var(--line)}.nav a{color:var(--deep);font-weight:700;text-decoration:none;padding:.25rem .6rem}.cards{display:grid;grid-template-columns:repeat(2,1fr);gap:18px}.card{padding:20px;border:1px solid var(--line);border-radius:10px;background:#fffaf4}.card h3{margin-top:0;color:var(--deep)}.step-list{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;list-style:none;padding:0}.step-list li{padding:12px 8px;text-align:center;background:var(--wash);border-radius:8px;font-weight:700}.error{padding:10px 13px;border-left:4px solid var(--danger);background:#fff1ef;color:#772a27}.pillars{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.pillar{padding:12px;text-align:center;background:var(--wash);border:1px solid var(--line);border-radius:8px}.pillar small{display:block;color:var(--muted)}table{width:100%;border-collapse:collapse;margin:12px 0}.lesson-table-wrap{overflow-x:auto;margin:12px 0}.lesson-table{min-width:520px}.lesson-table th,.lesson-table td{padding:8px;border:1px solid var(--line);text-align:left;vertical-align:top}th,td{text-align:left;padding:8px;border-bottom:1px solid var(--line)}.ok{color:#286c48;font-weight:700}.ng{color:#a33a35;font-weight:700}.note{padding:12px;background:#f8f3ec;border-radius:8px;color:var(--muted)}@media(max-width:680px){.grid,.pillars,.cards{grid-template-columns:1fr 1fr}.full{grid-column:1/-1}.step-list{grid-template-columns:1fr 1fr}}
.progress-panel{padding:16px;border:1px solid var(--line);border-radius:10px;background:#fffaf4}.progress-panel progress{width:100%;height:16px;accent-color:var(--gold)}.course-search{margin:20px 0;padding:16px;border:1px solid var(--line);border-radius:10px}.course-search label{margin-top:0}.course-search input{min-height:46px}.course-search-output{margin:.5rem 0 0;color:var(--muted)}.chapter-list{display:grid;gap:12px}.chapter-card{border:1px solid var(--line);border-radius:10px;background:#fffaf4;overflow:hidden}.chapter-card summary{cursor:pointer;padding:16px 18px;font-weight:700;color:var(--deep)}.chapter-card summary span{display:block;color:var(--muted);font-size:.9rem;font-weight:400}.chapter-card ul{margin:0;padding:0 20px 18px 42px}.chapter-card li{padding:.4rem 0}.lesson-status,.video-status,.lesson-minutes{display:inline-block;margin-left:.5rem;color:var(--muted);font-size:.86rem}.lesson-status.done{color:#286c48;font-weight:700}.lesson-nav{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:26px 0}.lesson-nav .button{text-align:center}.media-status{padding:18px;border:1px dashed var(--line);border-radius:10px;background:#201b18;color:#fff}.media-status h2{margin-top:0;color:#fff;border-color:#5d5048}.media-status p{color:#eee3d8}.video-frame{position:relative;width:100%;aspect-ratio:16/9;background:#000;border-radius:10px;overflow:hidden}.video-frame iframe{width:100%;height:100%;border:0}.reading-material{margin:24px 0;border:1px solid var(--line);border-radius:10px}.reading-material>summary{cursor:pointer;padding:16px 18px;color:var(--deep);font-weight:700;background:#fffaf4}.reading-material>article{padding:4px 18px 20px}@media(max-width:680px){.shell{width:100%;margin:0;min-height:100vh;border-radius:0}.hero,.content{padding-left:18px;padding-right:18px}.grid,.pillars,.cards{grid-template-columns:1fr}.nav{flex-wrap:nowrap;overflow-x:auto;padding:10px 12px}.nav a{white-space:nowrap}.button{width:100%;text-align:center;min-height:48px}.lesson-nav{grid-template-columns:1fr}.choice{display:flex;min-height:44px;align-items:center}.lesson-table{min-width:480px}}
</style>
"""

_PROGRESS_KEY = "yakumo_academy_completed_v1"
_LAST_LESSON_KEY = "yakumo_academy_last_lesson_v1"


def _progress_script(
    *,
    completed_lesson_id: str = "",
    current_lesson_url: str = "",
    current_lesson_title: str = "",
) -> str:
    completed = json.dumps(completed_lesson_id, ensure_ascii=False).replace("<", "\\u003c")
    current_url = json.dumps(current_lesson_url, ensure_ascii=False).replace("<", "\\u003c")
    current_title = json.dumps(current_lesson_title, ensure_ascii=False).replace("<", "\\u003c")
    return f'''<script>
(() => {{
  const key = "{_PROGRESS_KEY}";
  let completed = [];
  try {{ completed = JSON.parse(localStorage.getItem(key) || "[]"); }} catch (_) {{ completed = []; }}
  if (!Array.isArray(completed)) completed = [];
  const justCompleted = {completed};
  if (justCompleted && !completed.includes(justCompleted)) {{
    completed.push(justCompleted);
    try {{ localStorage.setItem(key, JSON.stringify(completed)); }} catch (_) {{}}
  }}
  document.querySelectorAll("[data-lesson-id]").forEach((row) => {{
    const done = completed.includes(row.dataset.lessonId);
    const status = row.querySelector(".lesson-status");
    if (status) {{ status.textContent = done ? "修了" : "未修了"; status.classList.toggle("done", done); }}
  }});
  document.querySelectorAll("[data-progress-total]").forEach((panel) => {{
    const total = Number(panel.dataset.progressTotal || 0);
    const count = Math.min(total, completed.length);
    const bar = panel.querySelector("progress");
    const label = panel.querySelector("[data-progress-label]");
    if (bar) bar.value = count;
    if (label) label.textContent = `${{count}}講 修了`;
  }});
  const currentUrl = {current_url};
  const currentTitle = {current_title};
  if (currentUrl) {{
    try {{ localStorage.setItem("{_LAST_LESSON_KEY}", JSON.stringify({{url: currentUrl, title: currentTitle}})); }} catch (_) {{}}
  }}
  let last = null;
  try {{ last = JSON.parse(localStorage.getItem("{_LAST_LESSON_KEY}") || "null"); }} catch (_) {{ last = null; }}
  document.querySelectorAll("[data-resume-link]").forEach((link) => {{
    if (last && typeof last.url === "string" && last.url.startsWith("/academy/" + "course/")) {{
      link.href = last.url;
      link.textContent = `続きから学ぶ：${{last.title || "前回の講座"}}`;
      link.hidden = false;
    }}
  }});
}})();
</script>'''


def _course_search_script(total: int) -> str:
    return f'''<script>
(() => {{
  const input = document.querySelector("[data-course-search]");
  const output = document.querySelector("[data-course-search-output]");
  if (!input || !output) return;
  const rows = [...document.querySelectorAll("[data-course-title]")];
  const chapters = [...document.querySelectorAll(".chapter-card")];
  const update = () => {{
    const query = input.value.trim().toLocaleLowerCase("ja");
    let shown = 0;
    rows.forEach((row) => {{
      const match = !query || row.dataset.courseTitle.toLocaleLowerCase("ja").includes(query);
      row.hidden = !match;
      if (match) shown += 1;
    }});
    chapters.forEach((chapter) => {{
      const hasVisible = [...chapter.querySelectorAll("[data-course-title]")].some((row) => !row.hidden);
      chapter.hidden = !hasVisible;
      if (query && hasVisible) chapter.open = true;
    }});
    output.textContent = query ? `${{shown}}講が一致しました` : `すべての講を表示中`;
  }};
  input.addEventListener("input", update);
  update();
}})();
</script>'''

_COURSES = (
    ("第1章", "四柱推命の土台", "四柱推命を学ぶための基本概念を順番に身につけます。", (
        "四柱推命とは何を読むものか", "陰陽五行", "十干", "十二支", "四柱の意味", "日主とは何か",
    )),
    ("第2章", "命式構成情報", "命式を構成する天干・地支・蔵干などを読み解きます。", ()),
    ("第3章", "命式全体判断", "日主を中心に命式全体のバランスを見る視点を学びます。", ()),
    ("第4章", "格局・用神", "月令を起点に格局と用神を確認する考え方を学びます。", ()),
    ("第5章", "干支関係", "命式内の合・冲など、干支同士の関係を確認します。", ()),
    ("第6章", "大運・歳運", "10年単位・1年単位の流れを命式と重ねて読みます。", ()),
    ("第7章", "実践鑑定", "根拠を整理し、読み手に伝わる鑑定へ組み立てます。", ()),
)

_LESSON_1_1 = {
    "title": "第1章 四柱推命の土台",
    "lesson": "第1講 四柱推命とは何を読むものか",
    "questions": (
        {
            "id": "lesson_q1",
            "prompt": "四柱推命の「四柱」とは何を指しますか？",
            "choices": ("年柱・月柱・日柱・時柱", "五行の五つの要素", "大運の10年区分"),
            "answer": "0",
            "explanation": "四柱は、年柱・月柱・日柱・時柱という四つの柱です。",
        },
        {
            "id": "lesson_q2",
            "prompt": "命式とは何ですか？",
            "choices": ("生年月日だけを記録した一覧", "四柱など、命式を構成する情報を整理したもの", "AIが作る鑑定本文"),
            "answer": "1",
            "explanation": "命式は、生まれの情報から四柱などを整理した、読み取りの土台です。",
        },
        {
            "id": "lesson_q3",
            "prompt": "八雲式Academyが重視する学び方はどれですか？",
            "choices": ("答えを暗記する", "理論を学び、自分で判断し、答え合わせで根拠を確認する", "AIにすべて判断してもらう"),
            "answer": "1",
            "explanation": "理論を学び、自分で考え、答え合わせで判断根拠を確認する学び方を重視します。",
        },
    ),
}


def _academy_nav() -> str:
    account = '<a href="/academy/purchase">受講登録・ログイン</a>' if academy_access.login_required() else ""
    return f'<nav class="nav"><a href="/academy">Academyトップ</a><a href="/academy/courses">講座一覧</a><a href="/academy/practice">実践トレーニング</a>{account}</nav>'


def _current_login(request: Request) -> Login | None:
    return academy_access.read_login(request.cookies.get(academy_access.ACCESS_COOKIE, ""))


def _refreshed_login(request: Request) -> tuple[Login | None, bool]:
    """Current login; an expired paid-through time is re-checked at Stripe (renewals)."""
    login = _current_login(request)
    if login is None or login.active():
        return login, False
    try:
        until = academy_access.find_access_until(login.email)
    except AcademyAccessError:
        return login, False
    if until > login.access_until:
        return Login(login.email, until), True
    return login, False


def _lesson_locked(chapter: int, login: Login | None) -> bool:
    if not academy_access.login_required() or academy_access.chapter_is_free(chapter):
        return False
    return login is None or not login.active()


_PLAN_TERMS = (
    '<ul><li>料金：月額プラン 2,980円（税込）／年額プラン 19,800円（税込）</li>'
    '<li>支払い：申込時にクレジットカードで支払い、以後は契約日から月額は1か月ごと、年額は1年ごとに自動で請求します。</li>'
    '<li>契約期間：解約するまで自動で更新します。最低契約期間はありません。</li>'
    '<li>解約：このページの「契約の確認・解約」からいつでも手続きできます。次回の請求日の前日までに解約すると、次回の請求は行いません。解約後も、支払い済みの期間の終わりまで視聴できます。</li>'
    '<li>提供時期：決済完了後すぐに、すべての講を視聴できます。</li>'
    '<li>返金：デジタルコンテンツのため、利用者の都合による返金（日割りを含む）は原則として行いません。購入前に、無料の第1章で内容をご確認ください。</li>'
    '<li>対象：18歳以上の方</li></ul>'
    '<p>詳しくは<a href="/academy/terms">受講規約</a>・<a href="/terms">利用規約</a>・<a href="/privacy">プライバシーポリシー</a>・<a href="/legal">特定商取引法に基づく表記</a>をご確認ください。</p>'
)


def _jst_date(timestamp: int) -> str:
    day = datetime.fromtimestamp(timestamp, timezone(timedelta(hours=9)))
    return f"{day.year}年{day.month}月{day.day}日"


def _simple_page(title: str, body: str) -> str:
    return f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex"><title>{escape(title)} | 八雲式Academy</title>{_STYLES}</head><body><main class="shell">{_academy_nav()}<header class="hero"><p class="eyebrow">YAKUMO ACADEMY</p><h1>{escape(title)}</h1></header><section class="content">{body}</section></main></body></html>'''


def _login_button(next_path: str) -> str:
    return f'<p><a class="button" href="/academy/login?next={escape(academy_access.safe_next(next_path), quote=True)}">Googleでログイン</a></p>'


def _render_locked_lesson(chapter: int, lesson_number: int, login: Login | None) -> str | None:
    lesson = lesson_by_number(chapter, lesson_number)
    if lesson is None:
        return None
    path = f"/academy/course/{chapter}/{lesson_number}"
    if login is None:
        action = '<p>購入済みの方は、購入時と同じGoogleアカウントでログインしてください。</p>' + _login_button(path)
    else:
        action = f'<p>{escape(login.email)} でログイン中です。このアカウントには有効な受講登録がありません。</p><p><a class="button" href="/academy/purchase">受講登録へ進む</a></p>'
    body = f'<p>第{lesson["order"]}講「{escape(str(lesson["title"]))}」は、受講登録をした方が見られる講です。第1章は無料で見られます。</p><p>受講登録は月額2,980円、または年額19,800円（税込）で、契約中はすべての講を見られます。</p>{action}<p><a href="/academy/courses">講座一覧へ戻る</a></p>'
    return _simple_page("受講登録が必要です", body)


def _render_video_area(lesson: dict[str, object]) -> str:
    video_url = str(lesson.get("video_url") or "").strip()
    if not video_url:
        return '<section class="media-status"><h2>動画講座</h2><p><strong>動画未登録</strong></p><p>この講座には再生可能な動画URLが登録されていません。動画が登録されるまでは、下の補助教材と理解度チェックを利用できます。</p></section>'
    parsed = urlparse(video_url)
    allowed_hosts = {"www.youtube-nocookie.com", "www.youtube.com", "player.vimeo.com"}
    if parsed.scheme != "https" or parsed.hostname not in allowed_hosts:
        return '<section class="media-status"><h2>動画講座</h2><p><strong>動画を表示できません</strong></p><p>登録された動画URLの形式が未対応です。補助教材を利用してください。</p></section>'
    safe_url = escape(video_url, quote=True)
    title = escape(str(lesson["title"]), quote=True)
    return f'<section aria-labelledby="video-heading"><h2 id="video-heading">動画講座</h2><div class="video-frame"><iframe src="{safe_url}" title="{title}" loading="lazy" referrerpolicy="strict-origin-when-cross-origin" allow="accelerometer; autoplay; encrypted-media; picture-in-picture" allowfullscreen></iframe></div></section>'


def _portal_video_note() -> str:
    registered = sum(1 for lesson in all_lessons() if lesson.get("video_url"))
    if registered == 0:
        return '<p class="note">現在、カリキュラムは整備済みですが動画URLは未登録です。登録済みの教材だけを表示します。</p>'
    if registered < len(all_lessons()):
        return f'<p class="note">動画は{registered}講を公開中です。未公開の講は補助教材で学べます。</p>'
    return ""


def _render_portal() -> str:
    return f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>八雲式 四柱推命Academy</title>{_STYLES}</head><body><main class="shell">{_academy_nav()}<header class="hero"><p class="eyebrow">YAKUMO ACADEMY</p><h1>八雲式 四柱推命 動画講座</h1><p>動画を中心に学び、補助教材と理解度チェックで判断根拠を確認します。</p>{_portal_video_note()}</header><section class="content"><p><a class="button" data-resume-link hidden href="/academy/course/1/1">続きから学ぶ</a></p><div class="cards"><article class="card"><h3>動画講座で学ぶ</h3><p>基礎から実践鑑定まで、章ごとに順番に学びます。</p><a class="button" href="/academy/courses">動画講座一覧を見る</a><p><a href="/academy/course/1/1">第1講から学ぶ</a></p></article><article class="card"><h3>命式で練習する</h3><p>実際の命式を使って自分で判断し、八雲式エンジンで答え合わせします。</p><a class="button" href="/academy/practice">実践トレーニング</a></article></div><h2>動画講座の学習サイクル</h2><ol class="step-list"><li>動画を見る</li><li>補助教材を読む</li><li>自分で判断する</li><li>理解度を確認</li><li>命式で練習</li></ol></section>{_progress_script()}</main></body></html>'''


def _render_courses() -> str:
    chapters = "".join(
        f'<article class="card"><h3>{escape(chapter)}</h3><h2>{escape(title)}</h2><p>{escape(description)}</p>'
        + ("<ul>" + "".join(f"<li>{escape(lesson)}（準備中）</li>" for lesson in lessons) + "</ul>" if lessons else "<p class=\"note\">講座準備中</p>")
        + "</article>"
        for chapter, title, description, lessons in _COURSES
    )
    return f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>講座一覧 | 八雲式Academy</title>{_STYLES}</head><body><main class="shell">{_academy_nav()}<header class="hero"><p class="eyebrow">YAKUMO ACADEMY</p><h1>講座一覧</h1><p>7章構成で、基礎から実践鑑定までの学びを整理しています。</p></header><section class="content"><div class="cards">{chapters}</div></section></main></body></html>'''


def _render_courses_with_lesson_link() -> str:
    chapters = []
    for chapter_index, (chapter, title, description, lessons) in enumerate(_COURSES):
        lesson_items = []
        for lesson_index, lesson in enumerate(lessons):
            label = escape(lesson)
            if chapter_index == 0 and lesson_index == 0:
                lesson_items.append(f'<li><a href="/academy/course/1/1">{label}</a></li>')
            else:
                lesson_items.append(f"<li>{label}（準備中）</li>")
        lesson_html = "<ul>" + "".join(lesson_items) + "</ul>" if lesson_items else '<p class="note">講座準備中</p>'
        chapters.append(f'<article class="card"><h3>{escape(chapter)}</h3><h2>{escape(title)}</h2><p>{escape(description)}</p>{lesson_html}</article>')
    return f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>講座一覧 | 八雲式Academy</title>{_STYLES}</head><body><main class="shell">{_academy_nav()}<header class="hero"><p class="eyebrow">YAKUMO ACADEMY</p><h1>講座一覧</h1><p>7章構成で、基礎から実践鑑定までの学びを整理しています。</p></header><section class="content"><div class="cards">{"".join(chapters)}</div></section></main></body></html>'''


def _courses_access_note() -> str:
    if not academy_access.login_required():
        return ""
    return '<p>第1章は無料で見られます。第2章以降は<a href="/academy/purchase">受講登録</a>が必要です。</p>'


def _render_curriculum_courses() -> str:
    curriculum = all_lessons()
    grouped: dict[int, list[dict[str, object]]] = {}
    for lesson in curriculum:
        grouped.setdefault(int(lesson["chapter"]), []).append(lesson)
    cards = []
    for chapter, lessons in grouped.items():
        first = lessons[0]
        items = "".join(
            f'<li data-lesson-id="{escape(str(lesson["lesson_id"]), quote=True)}" data-course-title="{escape(str(lesson["title"]), quote=True)}"><a href="/academy/course/{lesson["chapter"]}/{((lesson["order"] - 1) % 7) + 1}">第{lesson["order"]}講　{escape(lesson["title"])}</a><span class="lesson-minutes">約{lesson["estimated_minutes"]}分</span><span class="video-status">{"動画あり" if lesson.get("video_url") else "動画未登録"}</span><span class="lesson-status">未修了</span></li>'
            for lesson in lessons
        )
        cards.append(f'<details class="chapter-card"{" open" if chapter == 1 else ""}><summary>第{chapter}章　{escape(str(first["chapter_title"]).split(" ", 1)[-1])}<span>{len(lessons)}講</span></summary><ul>{items}</ul></details>')
    progress = f'<section class="progress-panel" data-progress-total="{len(curriculum)}"><strong data-progress-label>0講 修了</strong><progress value="0" max="{len(curriculum)}" aria-label="講座の修了進捗"></progress><p class="note">理解度チェックに合格した講座を、この端末のブラウザに記録します。ログイン同期・端末間同期には未対応です。</p></section>'
    search = f'<section class="course-search" role="search"><label for="course-search">講座名から探す</label><input id="course-search" data-course-search type="search" placeholder="例：五行、用神、大運" autocomplete="off"><p class="course-search-output" data-course-search-output aria-live="polite">すべての講を表示中</p></section>'
    return f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>講座一覧 | 八雲式Academy</title>{_STYLES}</head><body><main class="shell">{_academy_nav()}<header class="hero"><p class="eyebrow">YAKUMO ACADEMY</p><h1>講座一覧</h1><p>基礎から実践まで順に学びます。すべての教材は現在draftとして管理されています。</p>{_courses_access_note()}</header><section class="content">{progress}<p><a class="button" data-resume-link hidden href="#">続きから学ぶ</a></p>{search}<h2>章から選ぶ</h2><div class="chapter-list">{"".join(cards)}</div></section>{_progress_script()}{_course_search_script(len(curriculum))}</main></body></html>'''


def _render_lesson_1_1(error: str = "") -> str:
    sections = (
        ("この講座で学ぶこと", "四柱推命とは何か、命式とは何か、四柱の意味、そして八雲式Academyで目指す学び方を整理します。"),
        ("四柱推命の基本", "四柱推命は、生年月日や出生時刻などから命式を作り、そこに現れる構造を読みながら、性質や傾向、運の流れを考える体系です。結果を一方的に決めつけるのではなく、どの根拠からどの解釈へ進むかを学びます。"),
        ("四柱の意味", "命式には、年柱・月柱・日柱・時柱という四つの柱があります。最初はそれぞれを一つの情報単位として捉え、細かな解釈は次の講座で段階的に確認していきます。"),
        ("命式とは", "年柱・月柱・日柱・時柱など、生まれの情報から整理された構造全体を命式と呼びます。命式は答えそのものではなく、読み解きを始めるための地図のようなものです。"),
        ("八雲式Academyの考え方", "理論を学ぶ、まず自分で判断する、実際の命式で練習する、八雲式で答え合わせをする、そして判断根拠を確認する。この順番を大切にします。"),
    )
    section_html = "".join(f"<section><h2>{escape(title)}</h2><p>{escape(body)}</p></section>" for title, body in sections)
    important = "<ul><li>四柱は年柱・月柱・日柱・時柱の四つです。</li><li>命式は、四柱などを整理した読み解きの土台です。</li><li>四柱推命は、根拠と解釈のつながりを読む体系です。</li><li>答えを暗記するより、判断の理由を確認することを重視します。</li></ul>"
    questions = []
    for question in _LESSON_1_1["questions"]:
        choices = "".join(f'<label class="choice"><input type="radio" name="{question["id"]}" value="{index}" required>{escape(choice)}</label>' for index, choice in enumerate(question["choices"]))
        questions.append(f'<fieldset><legend>{escape(question["prompt"])}</legend>{choices}</fieldset>')
    error_html = f'<p class="error">{escape(error)}</p>' if error else ""
    return f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(_LESSON_1_1["lesson"])} | 八雲式Academy</title>{_STYLES}</head><body><main class="shell">{_academy_nav()}<header class="hero"><p class="eyebrow">YAKUMO ACADEMY</p><h1>{escape(_LESSON_1_1["title"])}</h1><p>{escape(_LESSON_1_1["lesson"])}</p><p>まず教材を読み、自分の言葉で理解できたかを確認しましょう。</p></header><section class="content">{section_html}<section><h2>重要ポイント</h2>{important}</section><section><h2>理解度チェック</h2><p>教材を読んでから、3問に答えてください。</p>{error_html}<form method="post" action="/academy/course/1/1/check">{"".join(questions)}<button class="button" type="submit">答え合わせをする</button></form></section><p><a href="/academy/courses">講座一覧へ戻る</a></p></section></main></body></html>'''


def _render_lesson_result(values: dict[str, list[str]]) -> str:
    rows = []
    score = 0
    for question in _LESSON_1_1["questions"]:
        submitted = values.get(question["id"], [""])[0]
        valid = submitted in {str(index) for index in range(len(question["choices"]))}
        correct = valid and submitted == question["answer"]
        score += int(correct)
        answer = question["choices"][int(question["answer"])]
        status = "○" if correct else "×"
        status_class = "ok" if correct else "ng"
        rows.append(f'<article class="card"><h3 class="{status_class}">{status} {escape(question["prompt"])}</h3><p>正解：{escape(answer)}</p><p>{escape(question["explanation"])}</p></article>')
    return f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>第1講の学習結果 | 八雲式Academy</title>{_STYLES}</head><body><main class="shell">{_academy_nav()}<header class="hero"><p class="eyebrow">YAKUMO ACADEMY</p><h1>第1講の学習結果</h1><p>{len(_LESSON_1_1["questions"])}問中{score}問正解</p></header><section class="content"><div class="cards">{"".join(rows)}</div><p class="note">間違えた問題は、解説を確認してからもう一度読み返してみましょう。</p><p><a class="button" href="/academy/course/1/1">第1講をもう一度読む</a></p><p><a class="button" href="/academy/practice">実際の命式を見てみる</a></p><p><strong>次の講座：陰陽五行（準備中）</strong></p><p><a href="/academy/courses">講座一覧へ戻る</a></p></section></main></body></html>'''


def _field(name: str, value: str = "") -> str:
    return f'<input type="hidden" name="{escape(name, quote=True)}" value="{escape(value, quote=True)}">'


def _parse_form(request: Request, body: bytes) -> dict[str, list[str]]:
    if len(body) > _MAX_FORM_BYTES:
        raise CustomerInputError({"_form": "入力内容が大きすぎます。"})
    try:
        pairs = parse_qsl(body.decode("utf-8"), keep_blank_values=True, max_num_fields=100)
    except (UnicodeDecodeError, ValueError):
        raise CustomerInputError({"_form": "入力を読み取れませんでした。"}) from None
    allowed = {
        "birth_date", "birth_place", "birth_hour", "birth_minute", "birth_time_unknown", "gender",
        "q1", "q2", "q3_0", "q3_1", "q3_2", "q3_3", "q3_4", "q4", "q5", "q6",
        "lesson_q1", "lesson_q2", "lesson_q3",
    }
    result: dict[str, list[str]] = {}
    for key, value in pairs:
        if key not in allowed:
            raise CustomerInputError({"_form": "不正な入力項目があります。"})
        result.setdefault(key, []).append(value)
    return result


def _customer_input(values: dict[str, list[str]]) -> CustomerReadingInput:
    flat = {key: items[0] for key, items in values.items() if items}
    flat["consultation"] = ""
    return validate_customer_input(flat)


def _chart_from_values(values: dict[str, list[str]]) -> tuple[dict[str, object], dict[str, object]]:
    customer_input = _customer_input(values)
    chart = calculate_chart(build_customer_chart_request(customer_input))
    return chart, build_academy_projection(chart)


def _start_fields(values: dict[str, list[str]]) -> str:
    return "".join(_field(key, items[0]) for key, items in values.items() if key in {
        "birth_date", "birth_place", "birth_hour", "birth_minute", "birth_time_unknown", "gender"
    } for _ in [0])


def _render_start_form_raw(values: dict[str, list[str]] | None = None, error: str = "") -> str:
    values = values or {}
    date = values.get("birth_date", [""])[0]
    place = values.get("birth_place", [""])[0]
    hour = values.get("birth_hour", [""])[0]
    minute = values.get("birth_minute", [""])[0]
    gender = values.get("gender", [""])[0]
    unknown = values.get("birth_time_unknown", [""])[0] == "1"
    places = "".join(
        f'<option value="{escape(place_name, quote=True)}"{' selected' if place_name == place else ''}>{escape(place_name)}</option>'
        for place_name in PREFECTURES
    )
    hours = "".join(f'<option value="{n:02d}">{n:02d}</option>' for n in range(24))
    minutes = "".join(f'<option value="{n:02d}">{n:02d}</option>' for n in range(60))
    checked = " checked" if unknown else ""
    selected_gender = "".join(
        f'<option value="{value}"{' selected' if value == gender else ''}>{label}</option>'
        for value, label in (("male", "男性"), ("female", "女性"))
    )
    return f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>八雲式 四柱推命Academy</title>{_STYLES}</head><body><main class="shell">{_academy_nav()}<header class="hero"><p class="eyebrow">YAKUMO ACADEMY</p><h1>八雲式 四柱推命Academy</h1><p>命式を自分で読み、八雲式で答え合わせしながら四柱推命を身につける実践学習ツール。</p><p>まず自分で考えてから、八雲式の判定を確認しましょう。</p></header><section class="content"><h2>学習を始める</h2>{f'<p class="error">{escape(error)}</p>' if error else ''}<form method="post" action="/academy/start"><div class="grid"><div><label for="birth_date">生年月日</label><input id="birth_date" name="birth_date" type="date" value="{escape(date, quote=True)}" required></div><div><label for="birth_place">出生地</label><select id="birth_place" name="birth_place" required><option value="">選択してください</option>{places}</select></div><div class="full"><label>出生時刻</label><div class="grid"><select name="birth_hour"><option value="">時</option>{hours}</select><select name="birth_minute"><option value="分">分</option>{minutes}</select></div><label class="choice"><input type="checkbox" name="birth_time_unknown" value="1"{checked}>出生時刻が分からない</label></div><div><label for="gender">性別</label><select id="gender" name="gender" required><option value="">選択してください</option>{selected_gender}</select></div><div class="full"><button class="button" type="submit">学習を開始する</button></div></div></form></section></main></body></html>'''


def _render_start_form(values: dict[str, list[str]] | None = None, error: str = "") -> str:
    html = _render_start_form_raw(values, error)
    return html.replace('name="birth_minute"><option value="分">', 'name="birth_minute"><option value="">')


def _with_academy_nav(html: str) -> str:
    if '<nav class="nav">' in html:
        return html
    return html.replace("<body>", f"<body>{_academy_nav()}", 1)


def _render_lesson_markdown(markdown: str) -> str:
    blocks: list[str] = []
    paragraph: list[str] = []
    list_items: list[str] = []
    table_rows: list[list[str]] = []

    def flush() -> None:
        nonlocal paragraph, list_items, table_rows
        if table_rows:
            header, *rows = table_rows
            head_html = "".join(f"<th>{escape(cell)}</th>" for cell in header)
            body_html = "".join(
                "<tr>" + "".join(f"<td>{escape(cell)}</td>" for cell in row) + "</tr>"
                for row in rows
            )
            blocks.append(f'<div class="lesson-table-wrap"><table class="lesson-table"><thead><tr>{head_html}</tr></thead><tbody>{body_html}</tbody></table></div>')
            table_rows = []
        if list_items:
            blocks.append("<ul>" + "".join(f"<li>{escape(item)}</li>" for item in list_items) + "</ul>")
            list_items = []
        if paragraph:
            blocks.append("<p>" + escape(" ".join(paragraph)) + "</p>")
            paragraph = []

    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line:
            flush()
        elif line.startswith("### "):
            flush(); blocks.append(f"<h3>{escape(line[4:])}</h3>")
        elif line.startswith("## "):
            flush(); blocks.append(f"<h2>{escape(line[3:])}</h2>")
        elif line.startswith("# "):
            flush(); blocks.append(f"<h1>{escape(line[2:])}</h1>")
        elif line.startswith("- "):
            if paragraph: flush()
            list_items.append(line[2:])
        elif re.match(r"^\d+\. ", line):
            if paragraph: flush()
            list_items.append(re.sub(r"^\d+\. ", "", line))
        elif line.startswith("|") and line.endswith("|"):
            if paragraph or list_items: flush()
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if cells and all(re.fullmatch(r":?-+:?", cell) for cell in cells):
                continue
            table_rows.append(cells)
        else:
            if table_rows: flush()
            paragraph.append(line)
    flush()
    return "".join(blocks)


def _curriculum_quiz_name(lesson_id: str, question_id: str) -> str:
    if lesson_id == "001":
        return "lesson_" + question_id.rsplit("_", 1)[-1]
    return f"lesson_{lesson_id}_{question_id}"


def _render_curriculum_lesson(chapter: int, lesson_number: int, error: str = "") -> str | None:
    lesson = lesson_by_number(chapter, lesson_number)
    if lesson is None:
        return None
    quiz = load_lesson_quiz(lesson["lesson_id"]) if lesson.get("quiz") else {"questions": []}
    lessons = all_lessons()
    index = lesson["order"] - 1
    previous = lessons[index - 1] if index else None
    following = lessons[index + 1] if index + 1 < len(lessons) else None
    questions = []
    for question in quiz["questions"]:
        name = _curriculum_quiz_name(lesson["lesson_id"], question["id"])
        choices = "".join(f'<label class="choice"><input type="radio" name="{escape(name, quote=True)}" value="{index}" required>{escape(choice)}</label>' for index, choice in enumerate(question["choices"]))
        questions.append(f'<fieldset><legend>{escape(question["prompt"])}</legend>{choices}</fieldset>')
    error_html = f'<p class="error">{escape(error)}</p>' if error else ""
    links = []
    if previous:
        links.append(f'<a class="button" href="/academy/course/{previous["chapter"]}/{((previous["order"] - 1) % 7) + 1}">前の講座</a>')
    else:
        links.append('<a class="button" href="/academy/courses">講座一覧</a>')
    if following:
        links.append(f'<a class="button" href="/academy/course/{following["chapter"]}/{((following["order"] - 1) % 7) + 1}">次の講座</a>')
    body = _render_lesson_markdown(load_lesson_content(lesson["lesson_id"]))
    position = round(lesson["order"] * 100 / max(1, len(lessons)))
    media = _render_video_area(lesson)
    lesson_url = f"/academy/course/{chapter}/{lesson_number}"
    lesson_title = f'第{lesson["order"]}講　{lesson["title"]}'
    return f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(lesson["title"])} | 八雲式Academy</title>{_STYLES}</head><body><main class="shell">{_academy_nav()}<header class="hero"><p class="eyebrow">YAKUMO VIDEO COURSE</p><h1>{escape(lesson["chapter_title"])}</h1><p>第{lesson["order"]}講　{escape(lesson["title"])}</p><p>カリキュラム位置 第{lesson["order"]}講（{position}%）　目安 {lesson["estimated_minutes"]}分</p></header><section class="content">{media}<details class="reading-material"><summary>補助教材を読む</summary><article>{body}</article></details><section><h2>理解度チェック</h2><p>動画または補助教材で学んでから、理解度を確認してください。3分の2以上の正解で、この端末に修了として記録します。</p>{error_html}<form method="post" action="/academy/course/{chapter}/{lesson_number}/check">{"".join(questions)}<button class="button" type="submit">答え合わせをする</button></form></section><nav class="lesson-nav" aria-label="講座間の移動">{"".join(links)}</nav><p><a href="/academy/courses">講座一覧へ戻る</a>　<a href="/academy/practice">実践トレーニング</a></p></section>{_progress_script(current_lesson_url=lesson_url, current_lesson_title=lesson_title)}</main></body></html>'''


def _render_curriculum_result(chapter: int, lesson_number: int, values: dict[str, list[str]]) -> str | None:
    lesson = lesson_by_number(chapter, lesson_number)
    if lesson is None:
        return None
    quiz = load_lesson_quiz(lesson["lesson_id"])
    lessons = all_lessons()
    following = lessons[lesson["order"]] if lesson["order"] < len(lessons) else None
    score = 0
    total = len(quiz["questions"])
    rows = []
    for question in quiz["questions"]:
        name = _curriculum_quiz_name(lesson["lesson_id"], question["id"])
        submitted = values.get(name, [""])[0]
        valid = submitted in {str(i) for i in range(len(question["choices"]))}
        correct = valid and submitted == question["answer"]
        score += int(correct)
        answer = question["choices"][int(question["answer"])]
        submitted_label = question["choices"][int(submitted)] if valid else "未回答"
        rows.append(f'<article class="card"><h3 class="{"ok" if correct else "ng"}">{"○" if correct else "×"} {escape(question["prompt"])}</h3><p>あなたの回答：{escape(submitted_label)}</p><p>正解：{escape(answer)}</p><p>解説：{escape(question["explanation"])}</p></article>')
    passed = score * 3 >= total * 2
    status_html = '<p class="ok"><strong>この講座を修了しました。</strong></p>' if passed else '<p class="note">もう一度復習して挑戦しましょう。</p>'
    if following:
        next_link = f'<p><a class="button" href="/academy/course/{following["chapter"]}/{((following["order"] - 1) % 7) + 1}">次の講座：{escape(following["title"])}</a></p>'
    elif passed:
        next_link = '<section class="card"><h2>公開中の最後の講を修了しました</h2><p>この端末での学習位置として、公開中の最後の講まで到達しました。ユーザー別の永続的な全講修了判定は、ログイン機能追加後に拡張できます。</p></section>'
    else:
        next_link = '<p class="note">この講は合格後に修了扱いになります。</p>'
    completed_id = str(lesson["lesson_id"]) if passed else ""
    return f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>学習結果 | 八雲式Academy</title>{_STYLES}</head><body><main class="shell">{_academy_nav()}<header class="hero"><p class="eyebrow">YAKUMO ACADEMY</p><h1>学習結果</h1><p>{total}問中{score}問正解</p>{status_html}</header><section class="content"><div class="cards">{"".join(rows)}</div><div class="lesson-nav"><a class="button" href="/academy/course/{chapter}/{lesson_number}">講座をもう一度読む</a>{next_link}</div><p><a href="/academy/practice">実践トレーニング</a>　<a href="/academy/courses">講座一覧へ戻る</a></p></section>{_progress_script(completed_lesson_id=completed_id)}</main></body></html>'''


def _parse_curriculum_form(body: bytes, lesson_id: str) -> dict[str, list[str]]:
    if len(body) > _MAX_FORM_BYTES:
        raise CustomerInputError({"_form": "入力内容が大きすぎます。"})
    try:
        pairs = parse_qsl(body.decode("utf-8"), keep_blank_values=True, max_num_fields=30)
    except (UnicodeDecodeError, ValueError):
        raise CustomerInputError({"_form": "入力を読み取れませんでした。"}) from None
    quiz = load_lesson_quiz(lesson_id)
    allowed = {_curriculum_quiz_name(lesson_id, q["id"]) for q in quiz["questions"]}
    result: dict[str, list[str]] = {}
    for key, value in pairs:
        if key not in allowed:
            raise CustomerInputError({"_form": "不正な入力項目があります。"})
        result.setdefault(key, []).append(value)
    return result


def _radio(name: str, values: Sequence[str]) -> str:
    return "".join(f'<label class="choice"><input type="radio" name="{name}" value="{escape(value, quote=True)}" required>{escape(value)}</label>' for value in values)


def _render_questions(values: dict[str, list[str]], projection: dict[str, object]) -> str:
    pillars = "".join(f'<div class="pillar"><small>{escape(position)}</small><strong>{escape(str(pillar))}</strong></div>' for position, pillar in projection["pillars"])
    hidden = "".join(f'<label class="choice"><input type="checkbox" name="q2" value="{escape(stem, quote=True)}">{escape(stem)}</label>' for stem in ACADEMY_STEM_OPTIONS)
    q3 = "".join(f'<p><strong>{escape(str(stem))}</strong> <select name="q3_{index}" required><option value="">選択</option>{_options(ACADEMY_TEN_GOD_OPTIONS)}</select></p>' for index, stem in enumerate(projection["month_hidden_stems"]))
    hidden_fields = _start_fields(values)
    return f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>命式を読む | 八雲式Academy</title>{_STYLES}</head><body><main class="shell"><header class="hero"><p class="eyebrow">YAKUMO ACADEMY</p><h1>まず、自分で読んでみましょう</h1><p>以下の命式を手がかりに、6問へ回答してください。正解はこのHTMLやhidden dataには埋め込んでいません。</p></header><section class="content"><h2>命式</h2><div class="pillars">{pillars}</div><form method="post" action="/academy/check">{hidden_fields}<fieldset><legend>Q1 日主</legend><p>この命式の日主はどれでしょうか？</p>{_radio("q1", ACADEMY_STEM_OPTIONS)}</fieldset><fieldset><legend>Q2 月支蔵干</legend><p>月支に含まれる蔵干を選んでください（複数選択）。</p>{hidden}</fieldset><fieldset><legend>Q3 月支蔵干通変星</legend><p>それぞれの日主との関係を選んでください。</p>{q3}</fieldset><fieldset><legend>Q4 身旺身弱</legend><p>この命式の身旺・身弱判定は？</p>{_radio("q4", ACADEMY_STRENGTH_OPTIONS)}</fieldset><fieldset><legend>Q5 格局</legend><p>この命式の代表格局は？</p>{_radio("q5", pattern_options(projection))}</fieldset><fieldset><legend>Q6 用神第一候補</legend><p>八雲式で用神第一候補となる五行は？</p>{_radio("q6", ACADEMY_ELEMENT_OPTIONS)}</fieldset><button class="button" type="submit">答え合わせをする</button></form></section></main></body></html>'''


def _options(values: Sequence[str]) -> str:
    return "".join(f'<option value="{escape(value, quote=True)}">{escape(value)}</option>' for value in values)


def _position_label(value: str) -> str:
    return {"year": "年干", "month": "月干", "day": "日干", "hour": "時干"}.get(value, value)


def _render_result(projection: dict[str, object], results: Sequence[bool]) -> str:
    labels = ("日主", "月支蔵干", "蔵干通変星", "身旺身弱", "格局", "用神第一候補")
    rows = "".join(f'<tr><th>{label}</th><td class="{"ok" if ok else "ng"}">{"○" if ok else "×"}</td></tr>' for label, ok in zip(labels, results))
    evidence = dict(projection["pattern_evidence"])
    evidence["exposure_positions"] = tuple(_position_label(value) for value in evidence["exposure_positions"])
    note = '<p class="note">出生時刻不明のため、時干への透干を確認できない三柱範囲の学習結果です。格局などは既存エンジンの暫定判定として確認してください。</p>' if projection["unknown_birth_time"] else ''
    explanation = f'''<h2>八雲式判定と判断材料</h2><dl><dt>日主</dt><dd>{escape(str(projection["day_master"]))}（日柱の日干）</dd><dt>月支蔵干</dt><dd>{escape("・".join(projection["month_hidden_stems"]))}（月支 {escape(str(projection["month_branch"]))}）</dd><dt>蔵干通変星</dt><dd>{escape("・".join(projection["month_hidden_stem_ten_gods"]))}</dd><dt>身旺身弱</dt><dd>{escape(str(projection["strength"]))}</dd><dt>格局</dt><dd>{escape(str(projection["pattern"]))}（月支 {escape(str(evidence["month_branch"]))}、採用蔵干 {escape(str(evidence["selected_hidden_stem"]))}、通変星 {escape(str(evidence["selected_ten_god"]))}、透干位置 {escape("・".join(evidence["exposure_positions"]) or "確認なし")}）</dd><dt>用神第一候補</dt><dd>{escape(str(projection["useful_element"]))}</dd></dl>{note}'''
    return f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>学習結果 | 八雲式Academy</title>{_STYLES}</head><body><main class="shell"><header class="hero"><p class="eyebrow">YAKUMO ACADEMY</p><h1>学習結果</h1><p>{sum(results)}問 / {len(results)}問一致</p></header><section class="content"><table>{rows}</table>{explanation}<p><a class="button" href="/academy">もう一度挑戦する</a></p></section></main></body></html>'''


@router.get("/academy", response_class=HTMLResponse, include_in_schema=False)
def academy_home() -> HTMLResponse:
    return HTMLResponse(_render_portal())


@router.get("/academy/courses", response_class=HTMLResponse, include_in_schema=False)
def academy_courses() -> HTMLResponse:
    return HTMLResponse(_render_curriculum_courses())


@router.get("/academy/course/1/1", response_class=HTMLResponse, include_in_schema=False)
def academy_lesson_1_1() -> HTMLResponse:
    return HTMLResponse(_render_curriculum_lesson(1, 1) or "Not Found", status_code=200)


@router.post("/academy/course/1/1/check", response_class=HTMLResponse, include_in_schema=False)
async def academy_lesson_1_1_check(request: Request) -> HTMLResponse:
    try:
        values = _parse_curriculum_form(await request.body(), "001")
    except CustomerInputError as exc:
        message = next(iter(exc.errors.values()))
        return HTMLResponse(_render_curriculum_lesson(1, 1, message) or "Not Found", status_code=422)
    return HTMLResponse(_render_curriculum_result(1, 1, values) or "Not Found")


@router.get("/academy/course/{chapter}/{lesson}", response_class=HTMLResponse, include_in_schema=False)
def academy_curriculum_lesson(chapter: int, lesson: int, request: Request) -> HTMLResponse:
    login, refreshed = _refreshed_login(request) if academy_access.login_required() else (None, False)
    if _lesson_locked(chapter, login):
        locked = _render_locked_lesson(chapter, lesson, login)
        return HTMLResponse(locked or "講座が見つかりません。", status_code=403 if locked else 404)
    rendered = _render_curriculum_lesson(chapter, lesson)
    response = HTMLResponse(rendered or "講座が見つかりません。", status_code=200 if rendered else 404)
    if refreshed and login is not None:
        _set_login_cookie(response, login)
    return response


@router.post("/academy/course/{chapter}/{lesson}/check", response_class=HTMLResponse, include_in_schema=False)
async def academy_curriculum_lesson_check(chapter: int, lesson: int, request: Request) -> HTMLResponse:
    item = lesson_by_number(chapter, lesson)
    if item is None:
        return HTMLResponse("講座が見つかりません。", status_code=404)
    login, _ = _refreshed_login(request) if academy_access.login_required() else (None, False)
    if _lesson_locked(chapter, login):
        return HTMLResponse(_render_locked_lesson(chapter, lesson, login) or "", status_code=403)
    try:
        values = _parse_curriculum_form(await request.body(), item["lesson_id"])
    except CustomerInputError as exc:
        message = next(iter(exc.errors.values()))
        return HTMLResponse(_render_curriculum_lesson(chapter, lesson, message) or "Not Found", status_code=422)
    return HTMLResponse(_render_curriculum_result(chapter, lesson, values) or "Not Found")


@router.get("/academy/practice", response_class=HTMLResponse, include_in_schema=False)
def academy_practice() -> HTMLResponse:
    return HTMLResponse(_with_academy_nav(_render_start_form()))


@router.post("/academy/start", response_class=HTMLResponse, include_in_schema=False)
async def academy_start(request: Request) -> HTMLResponse:
    try:
        values = _parse_form(request, await request.body())
        chart, projection = _chart_from_values(values)
    except (CustomerInputError, ValueError) as exc:
        message = next(iter(exc.errors.values())) if isinstance(exc, CustomerInputError) else "入力を確認してください。"
        return HTMLResponse(_with_academy_nav(_render_start_form(values if "values" in locals() else {}, message)), status_code=422)
    return HTMLResponse(_with_academy_nav(_render_questions(values, projection)))


@router.post("/academy/check", response_class=HTMLResponse, include_in_schema=False)
async def academy_check(request: Request) -> HTMLResponse:
    try:
        values = _parse_form(request, await request.body())
        chart, projection = _chart_from_values(values)
        results = grade_academy_answers(projection, {key: (items if key == "q2" else items[0]) for key, items in values.items()})
    except (CustomerInputError, ValueError):
        return HTMLResponse(_with_academy_nav(_render_start_form({}, "入力を確認して、もう一度学習を開始してください。")), status_code=422)
    return HTMLResponse(_with_academy_nav(_render_result(projection, results)))


def _set_login_cookie(response: Response, login: Login) -> None:
    response.set_cookie(
        academy_access.ACCESS_COOKIE,
        academy_access.issue_login(login),
        max_age=academy_access.LOGIN_SECONDS,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/academy",
    )


def _not_ready() -> HTMLResponse:
    return HTMLResponse(_simple_page("準備中です", "<p>受講登録とログインは準備中です。しばらくお待ちください。</p>"), status_code=503)


@router.get("/academy/login", include_in_schema=False)
def academy_login(next: str = "/academy/courses") -> Response:
    if not academy_access.login_required():
        return RedirectResponse("/academy/courses", status_code=303)
    try:
        state, state_token = academy_access.issue_state(next)
        url = academy_access.google_auth_url(state)
    except AcademyAccessError:
        return _not_ready()
    response = RedirectResponse(url, status_code=303)
    response.set_cookie(academy_access.STATE_COOKIE, state_token, max_age=academy_access.STATE_SECONDS, httponly=True, secure=True, samesite="lax", path="/academy")
    return response


@router.get("/academy/auth/callback", include_in_schema=False)
def academy_auth_callback(request: Request, code: str = "", state: str = "") -> Response:
    if not academy_access.login_required():
        return RedirectResponse("/academy/courses", status_code=303)
    next_path = academy_access.read_state(request.cookies.get(academy_access.STATE_COOKIE, ""), state)
    if next_path is None or not code:
        return HTMLResponse(_simple_page("ログインできませんでした", "<p>ログインの有効期限が切れたか、途中で中断されました。もう一度お試しください。</p>" + _login_button("/academy/courses")), status_code=400)
    try:
        email = academy_access.google_email(code)
        until = academy_access.find_access_until(email)
    except AcademyAccessError:
        return HTMLResponse(_simple_page("ログインできませんでした", "<p>ログインまたは受講登録の確認ができませんでした。時間をおいてもう一度お試しください。</p>" + _login_button(next_path)), status_code=502)
    login = Login(email, until)
    response = RedirectResponse(next_path if login.active() else "/academy/purchase", status_code=303)
    _set_login_cookie(response, login)
    response.delete_cookie(academy_access.STATE_COOKIE, path="/academy")
    return response


@router.get("/academy/logout", include_in_schema=False)
def academy_logout() -> RedirectResponse:
    response = RedirectResponse("/academy", status_code=303)
    response.delete_cookie(academy_access.ACCESS_COOKIE, path="/academy")
    return response


def _plan_forms() -> str:
    forms = "".join(
        f'<form method="post" action="/academy/checkout"><input type="hidden" name="plan" value="{key}"><button class="button" type="submit">{escape(plan["label"])}で申し込む（{escape(plan["price_text"])}）</button></form>'
        for key, plan in academy_access.PLANS.items()
    )
    return f'<div class="cards">{forms}</div>'


@router.get("/academy/purchase", response_class=HTMLResponse, include_in_schema=False)
def academy_purchase(request: Request) -> HTMLResponse:
    if not academy_access.login_required():
        return HTMLResponse(_simple_page("受講登録", '<p>現在、講座はどなたでも見られます。</p><p><a class="button" href="/academy/courses">講座一覧へ</a></p>'))
    if not academy_access.purchase_ready():
        return _not_ready()
    login, _ = _refreshed_login(request)
    intro = "<p>受講登録をすると、契約中はすべての講の動画・補助教材・理解度チェックを見られます。第1章は登録なしで見られます。</p>"
    if login is None:
        return HTMLResponse(_simple_page("受講登録・ログイン", intro + "<p>まずGoogleアカウントでログインしてください。受講登録済みの方も、申し込み時と同じGoogleアカウントでログインすると続きから見られます。</p>" + _login_button("/academy/courses") + "<h2>料金と契約の内容</h2>" + _PLAN_TERMS))
    account = f'<p>{escape(login.email)} でログイン中です。<a href="/academy/logout">ログアウト</a></p>'
    billing = '<form method="post" action="/academy/billing"><button class="button" type="submit">契約の確認・解約</button></form>'
    if login.active():
        page = _simple_page("受講中です", f'{account}<p>{_jst_date(login.access_until)}まで支払い済みです。契約は解約するまで自動で更新されます。</p><p><a class="button" href="/academy/courses">講座一覧へ</a></p>{billing}<p class="note">解約、カードの変更、領収書の確認は「契約の確認・解約」からできます（Stripeの画面に移ります）。</p>')
    else:
        page = _simple_page("受講登録", f'{intro}{account}<h2>料金と契約の内容</h2>{_PLAN_TERMS}{_plan_forms()}<p class="note">お支払いはStripeの画面で行います。ログイン中のメールアドレスで契約が記録されます。以前に契約していた方は、下のボタンから契約の状況を確認できます。</p>{billing}')
    response = HTMLResponse(page)
    _set_login_cookie(response, login)
    return response


@router.post("/academy/checkout", include_in_schema=False)
async def academy_checkout(request: Request) -> Response:
    if not academy_access.login_required():
        return RedirectResponse("/academy/courses", status_code=303)
    login = _current_login(request)
    if login is None:
        return RedirectResponse("/academy/purchase", status_code=303)
    if login.active():
        return RedirectResponse("/academy/courses", status_code=303)
    body = await request.body()
    plan = dict(parse_qsl(body.decode("utf-8", "replace")[:200])).get("plan", "")
    if plan not in academy_access.PLANS:
        return RedirectResponse("/academy/purchase", status_code=303)
    try:
        url = await run_in_threadpool(academy_access.create_academy_checkout, login.email, plan)
    except AcademyAccessError:
        return HTMLResponse(_simple_page("申し込みを開始できませんでした", '<p>時間をおいてもう一度お試しください。料金は請求されていません。</p><p><a href="/academy/purchase">受講登録へ戻る</a></p>'), status_code=502)
    return RedirectResponse(url, status_code=303)


@router.post("/academy/billing", include_in_schema=False)
def academy_billing(request: Request) -> Response:
    if not academy_access.login_required():
        return RedirectResponse("/academy/courses", status_code=303)
    login = _current_login(request)
    if login is None:
        return RedirectResponse("/academy/purchase", status_code=303)
    try:
        url = academy_access.billing_portal_url(login.email)
    except AcademyAccessError:
        return HTMLResponse(_simple_page("契約の画面を開けませんでした", '<p>このアカウントの契約が見つからないか、一時的に接続できませんでした。時間をおいてもう一度お試しください。解決しない場合は、<a href="https://form.os7.biz/f/be4d264a/" target="_blank" rel="noopener noreferrer">お問い合わせフォーム</a>からご連絡ください。</p><p><a href="/academy/purchase">受講登録へ戻る</a></p>'), status_code=502)
    return RedirectResponse(url, status_code=303)


@router.get("/academy/checkout/success", response_class=HTMLResponse, include_in_schema=False)
def academy_checkout_success(request: Request, session_id: str = "") -> HTMLResponse:
    if not academy_access.login_required():
        return HTMLResponse(_simple_page("受講登録", '<p><a href="/academy/courses">講座一覧へ</a></p>'))
    login = _current_login(request)
    if login is None:
        return HTMLResponse(_simple_page("ログインしてください", "<p>申し込み時と同じGoogleアカウントでログインすると、受講できるようになります。再度のお支払いは不要です。</p>" + _login_button("/academy/courses")), status_code=401)
    try:
        until = academy_access.verify_academy_checkout(session_id, login.email)
    except AcademyAccessError:
        return HTMLResponse(_simple_page("お支払いを確認できませんでした", '<p>時間をおいて<a href="/academy/purchase">受講登録のページ</a>を開き直してください。再度のお支払いは不要です。</p>'), status_code=502)
    login = Login(login.email, max(until, login.access_until))
    response = HTMLResponse(_simple_page("受講登録が完了しました", f'<p>ありがとうございます。すべての講を見られるようになりました。</p><p>契約は解約するまで自動で更新されます。解約は、<a href="/academy/purchase">受講登録のページ</a>の「契約の確認・解約」からいつでもできます。</p><p><a class="button" href="/academy/courses">講座一覧へ</a></p>'))
    _set_login_cookie(response, login)
    return response


@router.get("/academy/terms", response_class=HTMLResponse, include_in_schema=False)
def academy_terms() -> HTMLResponse:
    return HTMLResponse(_simple_page("八雲式Academy 受講規約", _ACADEMY_TERMS))


__all__ = ["router", "academy_home", "academy_courses", "academy_lesson_1_1", "academy_lesson_1_1_check", "academy_practice", "academy_start", "academy_check"]
