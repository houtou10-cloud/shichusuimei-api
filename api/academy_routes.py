"""Server-rendered, provider-free Academy MVP."""

from __future__ import annotations

from html import escape
from urllib.parse import parse_qsl

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

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


router = APIRouter()
_MAX_FORM_BYTES = 12_000
_STYLES = """
<style>
:root{color-scheme:light;--ink:#302820;--muted:#75685c;--paper:#fffdfa;--wash:#f5efe7;--line:#dfd1c2;--gold:#9a6a35;--deep:#5d3b25;--danger:#a33a35}
*{box-sizing:border-box}body{margin:0;background:linear-gradient(145deg,#f6f1eb,#eee5da);color:var(--ink);font-family:"Yu Mincho","Hiragino Mincho ProN","Noto Serif JP",serif;line-height:1.7}.shell{width:min(960px,calc(100% - 24px));margin:24px auto 56px;background:var(--paper);border:1px solid var(--line);box-shadow:0 16px 46px #422c1e18;border-radius:16px;overflow:hidden}.hero{padding:30px clamp(20px,5vw,54px);background:linear-gradient(120deg,#fffaf1,#f4eadc);border-bottom:1px solid var(--line)}.eyebrow{margin:0;color:var(--gold);font-size:.8rem;letter-spacing:.16em}.hero h1{margin:.2rem 0 .5rem;color:#422c1e;font-size:clamp(1.7rem,4vw,2.5rem)}.hero p{margin:.25rem 0;color:var(--muted)}.content{padding:28px clamp(20px,5vw,54px)}h2{color:var(--deep);border-bottom:1px solid var(--line);padding-bottom:.35rem;margin-top:1.6rem}.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px 22px}.full{grid-column:1/-1}label{display:block;font-weight:700;margin-bottom:.35rem}input,select{width:100%;font:inherit;padding:9px;border:1px solid #cdbdad;border-radius:7px;background:#fff}fieldset{border:1px solid var(--line);border-radius:10px;margin:18px 0;padding:15px}legend{font-weight:700;color:var(--deep)}.choice{display:inline-flex;align-items:center;gap:6px;margin:.25rem .8rem .25rem 0;font-weight:400}.choice input{width:auto}.button{display:inline-block;border:0;border-radius:8px;padding:12px 18px;background:linear-gradient(120deg,#6b4328,#9a6a35);color:#fff;font:700 1rem inherit;cursor:pointer;text-decoration:none}.nav{display:flex;gap:8px;flex-wrap:wrap;padding:12px clamp(20px,5vw,54px);background:#fffaf4;border-bottom:1px solid var(--line)}.nav a{color:var(--deep);font-weight:700;text-decoration:none;padding:.25rem .6rem}.cards{display:grid;grid-template-columns:repeat(2,1fr);gap:18px}.card{padding:20px;border:1px solid var(--line);border-radius:10px;background:#fffaf4}.card h3{margin-top:0;color:var(--deep)}.step-list{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;list-style:none;padding:0}.step-list li{padding:12px 8px;text-align:center;background:var(--wash);border-radius:8px;font-weight:700}.error{padding:10px 13px;border-left:4px solid var(--danger);background:#fff1ef;color:#772a27}.pillars{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.pillar{padding:12px;text-align:center;background:var(--wash);border:1px solid var(--line);border-radius:8px}.pillar small{display:block;color:var(--muted)}table{width:100%;border-collapse:collapse;margin:12px 0}th,td{text-align:left;padding:8px;border-bottom:1px solid var(--line)}.ok{color:#286c48;font-weight:700}.ng{color:#a33a35;font-weight:700}.note{padding:12px;background:#f8f3ec;border-radius:8px;color:var(--muted)}@media(max-width:680px){.grid,.pillars,.cards{grid-template-columns:1fr 1fr}.full{grid-column:1/-1}.step-list{grid-template-columns:1fr 1fr}}
</style>
"""

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


def _academy_nav() -> str:
    return '<nav class="nav"><a href="/academy">Academyトップ</a><a href="/academy/courses">講座一覧</a><a href="/academy/practice">実践トレーニング</a></nav>'


def _render_portal() -> str:
    return f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>八雲式 四柱推命Academy</title>{_STYLES}</head><body><main class="shell">{_academy_nav()}<header class="hero"><p class="eyebrow">YAKUMO ACADEMY</p><h1>八雲式 四柱推命Academy</h1><p>「覚える」から「判断できる」へ。</p><p>四柱推命の理論を学び、実際の命式を自分で読み、八雲式で答え合わせしながら鑑定力を身につける実践型Academyです。</p></header><section class="content"><div class="cards"><article class="card"><h3>講座で学ぶ</h3><p>基礎から実践鑑定まで、順番に四柱推命の判断方法を学びます。</p><a class="button" href="/academy/courses">講座を見る</a></article><article class="card"><h3>命式で練習する</h3><p>実際の命式を使って自分で判断し、八雲式エンジンで答え合わせします。</p><a class="button" href="/academy/practice">実践トレーニング</a></article></div><h2>八雲式Academyの学習サイクル</h2><ol class="step-list"><li>理論を学ぶ</li><li>自分で判断する</li><li>命式で練習する</li><li>八雲式で答え合わせ</li><li>判断根拠を確認する</li></ol></section></main></body></html>'''


def _render_courses() -> str:
    chapters = "".join(
        f'<article class="card"><h3>{escape(chapter)}</h3><h2>{escape(title)}</h2><p>{escape(description)}</p>'
        + ("<ul>" + "".join(f"<li>{escape(lesson)}（準備中）</li>" for lesson in lessons) + "</ul>" if lessons else "<p class=\"note\">講座準備中</p>")
        + "</article>"
        for chapter, title, description, lessons in _COURSES
    )
    return f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>講座一覧 | 八雲式Academy</title>{_STYLES}</head><body><main class="shell">{_academy_nav()}<header class="hero"><p class="eyebrow">YAKUMO ACADEMY</p><h1>講座一覧</h1><p>7章構成で、基礎から実践鑑定までの学びを整理しています。</p></header><section class="content"><div class="cards">{chapters}</div></section></main></body></html>'''


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


def _render_start_form(values: dict[str, list[str]] | None = None, error: str = "") -> str:
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
    return f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>八雲式 四柱推命Academy</title>{_STYLES}</head><body><main class="shell"><header class="hero"><p class="eyebrow">YAKUMO ACADEMY</p><h1>八雲式 四柱推命Academy</h1><p>命式を自分で読み、八雲式で答え合わせしながら四柱推命を身につける実践学習ツール。</p><p>まず自分で考えてから、八雲式の判定を確認しましょう。</p></header><section class="content"><h2>学習を始める</h2>{f'<p class="error">{escape(error)}</p>' if error else ''}<form method="post" action="/academy/start"><div class="grid"><div><label for="birth_date">生年月日</label><input id="birth_date" name="birth_date" type="date" value="{escape(date, quote=True)}" required></div><div><label for="birth_place">出生地</label><select id="birth_place" name="birth_place" required><option value="">選択してください</option>{places}</select></div><div class="full"><label>出生時刻</label><div class="grid"><select name="birth_hour"><option value="">時</option>{hours}</select><select name="birth_minute"><option value="">分</option>{minutes}</select></div><label class="choice"><input type="checkbox" name="birth_time_unknown" value="1"{checked}>出生時刻が分からない</label></div><div><label for="gender">性別</label><select id="gender" name="gender" required><option value="">選択してください</option>{selected_gender}</select></div><div class="full"><button class="button" type="submit">学習を開始する</button></div></div></form></section></main></body></html>'''


def _radio(name: str, values: Sequence[str]) -> str:
    return "".join(f'<label class="choice"><input type="radio" name="{name}" value="{escape(value, quote=True)}" required>{escape(value)}</label>' for value in values)


def _render_questions(values: dict[str, list[str]], projection: dict[str, object]) -> str:
    pillars = "".join(f'<div class="pillar"><small>{escape(position)}</small><strong>{escape(str(pillar))}</strong></div>' for position, pillar in projection["pillars"])
    hidden = "".join(f'<label class="choice"><input type="checkbox" name="q2" value="{escape(stem, quote=True)}">{escape(stem)}</label>' for stem in ACADEMY_STEM_OPTIONS)
    q3 = "".join(f'<p><strong>{escape(str(stem))}</strong> <select name="q3_{index}" required><option value="">選択</option>{_options(ACADEMY_TEN_GOD_OPTIONS)}</select></p>' for index, stem in enumerate(projection["month_hidden_stems"]))
    hidden_fields = _start_fields(values)
    return f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>命式を読む | 八雲式Academy</title>{_STYLES}</head><body><main class="shell"><header class="hero"><p class="eyebrow">YAKUMO ACADEMY</p><h1>まず、自分で読んでみましょう</h1><p>以下の命式を手がかりに、6問へ回答してください。正解はこのHTMLやhidden dataには埋め込んでいません。</p></header><section class="content"><h2>命式</h2><div class="pillars">{pillars}</div><form method="post" action="/academy/check">{hidden_fields}<fieldset><legend>Q1 日主</legend><p>この命式の日主はどれでしょうか？</p>{_radio("q1", ACADEMY_STEM_OPTIONS)}</fieldset><fieldset><legend>Q2 月支蔵干</legend><p>月支に含まれる蔵干を選んでください（複数選択）。</p>{hidden}</fieldset><fieldset><legend>Q3 月支蔵干通変星</legend><p>それぞれの日主との関係を選んでください。</p>{q3}</fieldset><fieldset><legend>Q4 身強身弱</legend><p>この命式の身強・身弱判定は？</p>{_radio("q4", ACADEMY_STRENGTH_OPTIONS)}</fieldset><fieldset><legend>Q5 格局</legend><p>この命式の代表格局は？</p>{_radio("q5", pattern_options(projection))}</fieldset><fieldset><legend>Q6 用神第一候補</legend><p>八雲式で用神第一候補となる五行は？</p>{_radio("q6", ACADEMY_ELEMENT_OPTIONS)}</fieldset><button class="button" type="submit">答え合わせをする</button></form></section></main></body></html>'''


def _options(values: Sequence[str]) -> str:
    return "".join(f'<option value="{escape(value, quote=True)}">{escape(value)}</option>' for value in values)


def _position_label(value: str) -> str:
    return {"year": "年干", "month": "月干", "day": "日干", "hour": "時干"}.get(value, value)


def _render_result(projection: dict[str, object], results: Sequence[bool]) -> str:
    labels = ("日主", "月支蔵干", "蔵干通変星", "身強身弱", "格局", "用神第一候補")
    rows = "".join(f'<tr><th>{label}</th><td class="{"ok" if ok else "ng"}">{"○" if ok else "×"}</td></tr>' for label, ok in zip(labels, results))
    evidence = dict(projection["pattern_evidence"])
    evidence["exposure_positions"] = tuple(_position_label(value) for value in evidence["exposure_positions"])
    note = '<p class="note">出生時刻不明のため、時干への透干を確認できない三柱範囲の学習結果です。格局などは既存エンジンの暫定判定として確認してください。</p>' if projection["unknown_birth_time"] else ''
    explanation = f'''<h2>八雲式判定と判断材料</h2><dl><dt>日主</dt><dd>{escape(str(projection["day_master"]))}（日柱の日干）</dd><dt>月支蔵干</dt><dd>{escape("・".join(projection["month_hidden_stems"]))}（月支 {escape(str(projection["month_branch"]))}）</dd><dt>蔵干通変星</dt><dd>{escape("・".join(projection["month_hidden_stem_ten_gods"]))}</dd><dt>身強身弱</dt><dd>{escape(str(projection["strength"]))}</dd><dt>格局</dt><dd>{escape(str(projection["pattern"]))}（月支 {escape(str(evidence["month_branch"]))}、採用蔵干 {escape(str(evidence["selected_hidden_stem"]))}、通変星 {escape(str(evidence["selected_ten_god"]))}、透干位置 {escape("・".join(evidence["exposure_positions"]) or "確認なし")}）</dd><dt>用神第一候補</dt><dd>{escape(str(projection["useful_element"]))}</dd></dl>{note}'''
    return f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>学習結果 | 八雲式Academy</title>{_STYLES}</head><body><main class="shell"><header class="hero"><p class="eyebrow">YAKUMO ACADEMY</p><h1>学習結果</h1><p>{sum(results)}問 / {len(results)}問一致</p></header><section class="content"><table>{rows}</table>{explanation}<p><a class="button" href="/academy">もう一度挑戦する</a></p></section></main></body></html>'''


@router.get("/academy", response_class=HTMLResponse, include_in_schema=False)
def academy_home() -> HTMLResponse:
    return HTMLResponse(_render_portal())


@router.get("/academy/courses", response_class=HTMLResponse, include_in_schema=False)
def academy_courses() -> HTMLResponse:
    return HTMLResponse(_render_courses())


@router.get("/academy/practice", response_class=HTMLResponse, include_in_schema=False)
def academy_practice() -> HTMLResponse:
    return HTMLResponse(_render_start_form())


@router.post("/academy/start", response_class=HTMLResponse, include_in_schema=False)
async def academy_start(request: Request) -> HTMLResponse:
    try:
        values = _parse_form(request, await request.body())
        chart, projection = _chart_from_values(values)
    except (CustomerInputError, ValueError) as exc:
        message = next(iter(exc.errors.values())) if isinstance(exc, CustomerInputError) else "入力を確認してください。"
        return HTMLResponse(_render_start_form(values if "values" in locals() else {}, message), status_code=422)
    return HTMLResponse(_render_questions(values, projection).replace("<body>", f"<body>{_academy_nav()}", 1))


@router.post("/academy/check", response_class=HTMLResponse, include_in_schema=False)
async def academy_check(request: Request) -> HTMLResponse:
    try:
        values = _parse_form(request, await request.body())
        chart, projection = _chart_from_values(values)
        results = grade_academy_answers(projection, {key: (items if key == "q2" else items[0]) for key, items in values.items()})
    except (CustomerInputError, ValueError):
        return HTMLResponse(_render_start_form({}, "入力を確認して、もう一度学習を開始してください。"), status_code=422)
    return HTMLResponse(_render_result(projection, results).replace("<body>", f"<body>{_academy_nav()}", 1))


__all__ = ["router", "academy_home", "academy_courses", "academy_practice", "academy_start", "academy_check"]
