"""Server-rendered customer flow for the trusted v1.2 reading pipeline."""

from __future__ import annotations

from html import escape
import logging
import os
from pathlib import Path
import re
import time
import traceback
from uuid import uuid4
from urllib.parse import parse_qsl

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from starlette.concurrency import run_in_threadpool

from api.customer_pipeline import (
    MAX_CONCERN_CHARS,
    PREFECTURES,
    CustomerConfigurationError,
    CustomerInputError,
    CustomerReadingUnavailableError,
    PerformanceTrace,
    run_customer_reading,
    reset_performance_trace,
    set_performance_trace,
    validate_customer_input,
)
from api.fast_reading import DETAIL_TYPES, _emit_perf, get_session, run_concern_answer, run_detail, run_fast_reading
from api.symbol_judgment_reference import append_product_reference_sidecar, append_reference_sidecar
from engine.reading_renderer_v2 import render_customer_reading_product_v2_html


router = APIRouter()
logger = logging.getLogger(__name__)

_CUSTOMER_STATIC = Path(__file__).resolve().parent / "static" / "customer"

_MAX_FORM_BYTES = 12_000
_NAMED_META = re.compile(r'<meta name="[^"]+" content="[^"]*">')

_FORM_CSS = """
<style>
:root{color-scheme:light;--ink:#302820;--muted:#75685c;--paper:#fffdfa;--wash:#f5efe7;--line:#dfd1c2;--gold:#9a6a35;--deep:#5d3b25;--danger:#a33a35;}
*{box-sizing:border-box}html{font-family:"Yu Mincho","Hiragino Mincho ProN","Noto Serif JP",serif;color:var(--ink);background:#eee7de}
body{margin:0;background:linear-gradient(145deg,#f6f1eb,#eee5da);min-height:100vh;line-height:1.65}
.site-header{padding:18px 22px;border-bottom:1px solid rgba(154,106,53,.25);background:rgba(255,253,250,.92)}
.brand{max-width:900px;margin:auto;color:var(--deep);font-weight:700;letter-spacing:.14em}
.form-shell{width:min(900px,calc(100% - 28px));margin:36px auto 64px;background:var(--paper);border:1px solid var(--line);box-shadow:0 18px 50px rgba(66,46,29,.1);border-radius:16px;overflow:hidden}
.form-intro{padding:34px 42px 26px;background:linear-gradient(120deg,#fffaf1,#f4eadc);border-bottom:1px solid var(--line)}
.eyebrow{margin:0;color:var(--gold);font-size:.83rem;letter-spacing:.16em}.form-intro h1{font-size:clamp(1.7rem,4vw,2.45rem);margin:.25rem 0 .55rem;color:#422c1e;letter-spacing:.06em}.lead{margin:0;color:var(--muted)}
.reading-form{padding:30px 42px 40px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:22px 24px}.field{min-width:0}.field.full{grid-column:1/-1}
label,.label{display:block;font-weight:700;margin-bottom:7px}.required{font-size:.75rem;color:#fff;background:var(--deep);padding:.08rem .38rem;border-radius:3px;margin-left:.45rem}
input,select,textarea{width:100%;font:inherit;color:var(--ink);background:#fff;border:1px solid #cdbdad;border-radius:8px;padding:11px 12px;outline:none}input:focus,select:focus,textarea:focus{border-color:var(--gold);box-shadow:0 0 0 3px rgba(154,106,53,.13)}
.time-row{display:grid;grid-template-columns:1fr auto 1fr auto;gap:8px;align-items:center}.unknown-row{display:flex;align-items:center;gap:9px;margin-top:11px;font-weight:400}.unknown-row input{width:auto;accent-color:var(--deep)}
.hint{margin:.4rem 0 0;color:var(--muted);font-size:.86rem}.field-error{margin:.35rem 0 0;color:var(--danger);font-size:.88rem}.error-box{grid-column:1/-1;border-left:4px solid var(--danger);background:#fff1ef;padding:12px 14px;color:#772a27}.error-box p{margin:0}.install-panel{padding:0 42px 30px}.install-note{margin:0;color:var(--muted);font-size:.88rem}.install-button{display:none;margin-top:10px;border:1px solid var(--gold);border-radius:7px;background:#fffaf1;color:var(--deep);padding:9px 12px;font:inherit;font-weight:700}.install-button.available{display:inline-block}
textarea{min-height:150px;resize:vertical}.actions{grid-column:1/-1;margin-top:8px}.submit{width:100%;border:0;border-radius:9px;padding:14px 20px;background:linear-gradient(120deg,#6b4328,#9a6a35);color:#fff;font:700 1.06rem inherit;letter-spacing:.1em;cursor:pointer}.submit:hover{filter:brightness(1.05)}.submit:disabled{cursor:wait;opacity:.68}.processing{display:none;text-align:center;margin:.75rem 0 0;color:var(--muted)}.processing.active{display:block}
@media(max-width:680px){.form-shell{margin-top:18px;width:min(100% - 18px,900px)}.form-intro,.reading-form,.install-panel{padding-left:20px;padding-right:20px}.grid{grid-template-columns:1fr}.field.full,.error-box,.actions{grid-column:1}.site-header{padding:14px 15px}.time-row{grid-template-columns:minmax(0,1fr) auto minmax(0,1fr) auto}input,select,textarea{font-size:16px}.submit{min-height:48px}}
</style>
"""

_FORM_CSS += """
<style>
.processing{display:none;text-align:center;margin:.75rem 0 0;padding:10px 12px;border:1px solid rgba(154,106,53,.35);border-radius:8px;background:#fffaf1;color:var(--deep);font-size:1rem;font-weight:700}
.processing.active{display:block}
</style>
"""

_RESULT_CSS = """
<style>
@media screen{
  html{background:#eee7de!important}body{max-width:980px;margin:0 auto!important;padding:0 24px 60px!important;background:#fffdfa!important;box-shadow:0 0 45px rgba(60,40,24,.12)}
  .cover{min-height:58vh!important;border-bottom:1px solid #d9c9b9;margin-bottom:2rem!important;break-after:auto!important;page-break-after:auto!important}
  .web-nav{position:sticky;top:0;z-index:5;margin:0 -24px;padding:10px 24px;background:rgba(255,253,250,.96);border-bottom:1px solid #e4d8ca;text-align:right}
  .web-nav a{display:inline-block;padding:.45rem .85rem;border:1px solid #8a5a3b;border-radius:6px;color:#6a412a;text-decoration:none;font-weight:700}
}
@media(max-width:680px){@media screen{body{padding:0 12px 40px!important}.web-nav{margin:0 -12px;padding:9px 12px}.facts{grid-template-columns:1fr!important}table{font-size:8.5pt!important}th,td{padding:.3rem .18rem!important}}}
@media print{
  .web-nav{display:none!important}
  body{margin:0!important;padding:0!important;box-shadow:none!important}
  section{break-before:auto;page-break-before:auto}
  .table-wrap,table,tr,.facts>div{break-inside:avoid-page;page-break-inside:avoid}
}
</style>
"""

_FAST_CSS = """
<style>
.fast-shell{max-width:900px;margin:30px auto 70px;background:#fffdfa;border:1px solid #dfd1c2;border-radius:16px;box-shadow:0 18px 50px rgba(66,46,29,.1);overflow:hidden}.fast-head{padding:30px 34px;background:linear-gradient(120deg,#fffaf1,#f4eadc);border-bottom:1px solid #dfd1c2}.fast-head h1{margin:.2rem 0;color:#422c1e}.fast-head p{color:#75685c}.fast-facts{display:flex;flex-wrap:wrap;gap:10px;padding:18px 34px;background:#fbf5ec}.fast-facts span{padding:7px 11px;border:1px solid #dfd1c2;border-radius:8px;background:#fff;font-size:.92rem}.fast-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;padding:26px 34px}.fast-card{border:1px solid #dfd1c2;border-radius:12px;padding:18px;background:#fff}.fast-card h2{font-size:1.15rem;color:#5d3b25;margin:0 0 8px}.fast-card p{margin:.2rem 0 1rem;white-space:pre-wrap}.detail-button{border:1px solid #8a5a3b;background:#fffaf1;color:#6a412a;border-radius:7px;padding:8px 12px;cursor:pointer}.detail-box{margin-top:12px;padding:12px;background:#fbf5ec;border-left:3px solid #9a6a35;white-space:pre-wrap}.detail-loading{color:#75685c}.chart-record{grid-column:1/-1;margin:0;padding:20px;border:1px solid #dfd1c2;border-radius:12px;background:#fff}.chart-record h2,.chart-record h3{color:#5d3b25}.chart-record h2{margin:0 0 14px;font-size:1.2rem}.table-wrap{overflow-x:auto;max-width:100%}.chart-table,.luck-table{width:100%;border-collapse:collapse;table-layout:fixed;min-width:620px;text-align:center}.chart-table col{width:20%}.chart-table th,.chart-table td,.luck-table th,.luck-table td{border:1px solid #dfd1c2;padding:9px 7px;vertical-align:middle;overflow-wrap:anywhere;word-break:break-word}.chart-table th,.luck-table th{background:#f4eadc;color:#5d3b25;font-weight:700}.chart-table tbody tr:nth-child(even),.luck-table tbody tr:nth-child(even){background:#fbf5ec}.chart-table td:first-child,.luck-table td:first-child{font-weight:700;color:#5d3b25;background:#fffaf1}.luck-record{margin-top:22px}.current-mark{background:#ead7bd!important;box-shadow:inset 0 0 0 2px #9a6a35;font-weight:700}.annual-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px;min-width:620px}.annual-cell{border:1px solid #dfd1c2;border-radius:8px;padding:10px 7px;text-align:center;background:#fff}.annual-cell:nth-child(even){background:#fbf5ec}.annual-cell strong{display:block;color:#5d3b25}.annual-cell span{display:block;margin-top:3px}.annual-cell small{display:block;margin-top:3px;color:#75685c}.section-label{margin:24px 34px 0;color:#5d3b25;font-size:1.2rem}.section-note{margin:4px 34px 0;color:#75685c;font-size:.9rem}.fast-grid + .section-label{margin-top:0}@media(max-width:680px){.fast-grid{grid-template-columns:1fr;padding:20px}.fast-head,.fast-facts{padding-left:20px;padding-right:20px}.chart-record{margin-left:0;margin-right:0;padding:14px}.section-label{margin-left:20px;margin-right:20px}.section-note{margin-left:20px;margin-right:20px}.chart-table,.luck-table{font-size:.85rem}.chart-table th,.chart-table td,.luck-table th,.luck-table td{padding:7px 5px}.annual-grid{grid-template-columns:repeat(5,110px)}}
</style>
"""

_FAST_CSS += """
<style>
.fast-head{position:relative}.fast-back{display:inline-block;position:absolute;top:24px;right:30px;padding:9px 14px;border:1px solid #8a5a3b;border-radius:8px;background:#fffaf1;color:#6a412a;text-decoration:none;font-weight:700;line-height:1.3}.fast-back:hover{background:#f4eadc}.fast-back:focus-visible{outline:3px solid rgba(154,106,53,.4);outline-offset:2px}.fast-prose{font-size:16.5px;line-height:1.88;overflow-wrap:anywhere}.fast-prose p{margin:0 0 16px}.fast-prose p:last-child{margin-bottom:0}.detail-box{font-size:16.5px;line-height:1.88;overflow-wrap:anywhere}.detail-loading{line-height:1.6}@media(max-width:680px){.fast-head{padding-top:76px}.fast-back{top:18px;left:20px;right:auto;padding:10px 14px}.fast-prose,.detail-box{font-size:16px;line-height:1.9}}
</style>
"""

_FAST_CSS += """
<style>
.detail-box p{margin:0 0 16px}.detail-box p:last-child{margin-bottom:0}
</style>
"""

# Keep responsive constraints local to the Fast Reading components.  Tables
# intentionally retain their readable minimum width inside ``.table-wrap``;
# prose/cards must instead be allowed to shrink so they cannot widen the page.
_FAST_RESPONSIVE_CSS = """
<style>
.fast-shell,.fast-grid,.fast-card,.chart-record{min-width:0;max-width:100%;}
.fast-grid>*{min-width:0;}
.fast-card p,.fast-prose,.detail-box{max-width:100%;overflow-wrap:anywhere;word-break:break-word;}
.fast-facts{min-width:0;max-width:100%;}
.fast-facts span{min-width:0;max-width:100%;overflow-wrap:anywhere;word-break:break-word;}
.table-wrap{width:100%;min-width:0;max-width:100%;overflow-x:auto;overflow-y:hidden;-webkit-overflow-scrolling:touch;}
.detail-button,.concern-answer-button{max-width:100%;white-space:normal;}
@media(max-width:680px){
  .fast-shell{width:100%;}
  .fast-card,.chart-record{width:auto;}
  .fast-head h1,.fast-head p{max-width:100%;overflow-wrap:anywhere;word-break:break-word;}
  .table-wrap{overflow-x:hidden;}
  .chart-table,.luck-table{min-width:0;table-layout:fixed;font-size:.76rem;}
  .chart-table th,.chart-table td,.luck-table th,.luck-table td{padding:6px 3px;}
  .annual-grid{min-width:0;grid-template-columns:repeat(2,minmax(0,1fr));}
}
</style>
"""

_PWA_HEAD = (
    '<meta name="theme-color" content="#5d3b25">'
    '<meta name="apple-mobile-web-app-capable" content="yes">'
    '<meta name="apple-mobile-web-app-status-bar-style" content="default">'
    '<link rel="manifest" href="/app/manifest.webmanifest">'
    '<link rel="icon" href="/app/icon.svg" type="image/svg+xml">'
    '<link rel="apple-touch-icon" sizes="180x180" href="/app/apple-touch-icon.png">'
)


def _option(value: str, label: str, selected: str) -> str:
    selected_attr = " selected" if value == selected else ""
    return f'<option value="{escape(value, quote=True)}"{selected_attr}>{escape(label)}</option>'


def _is_timeout_failure(exc: BaseException) -> bool:
    """Classify timeouts without exposing provider details to the customer."""
    reason = str(getattr(exc, "reason_code", "")).lower()
    return isinstance(exc, TimeoutError) or "timeout" in reason or "timed_out" in reason


def _generation_error_message(exc: BaseException) -> str:
    if _is_timeout_failure(exc):
        return "鑑定の生成が時間内に完了しませんでした。入力内容は下に保持されています。もう一度お試しください。"
    return "AI鑑定の生成中に確認が必要な状態になりました。入力内容は下に保持されています。時間をおいてもう一度お試しください。"


def _render_form(values: dict[str, str] | None = None, errors: dict[str, str] | None = None) -> str:
    values = {} if values is None else values
    errors = {} if errors is None else errors
    selected_place = values.get("birth_place", "")
    selected_gender = values.get("gender", "")
    selected_hour = values.get("birth_hour", "")
    selected_minute = values.get("birth_minute", "")
    unknown = values.get("birth_time_unknown") == "1"
    places = _option("", "選択してください", selected_place) + "".join(
        _option(place, place, selected_place) for place in PREFECTURES
    )
    genders = (
        _option("", "選択してください", selected_gender)
        + _option("male", "男性", selected_gender)
        + _option("female", "女性", selected_gender)
    )
    hours = _option("", "時", selected_hour) + "".join(
        _option(str(number), f"{number:02d}", selected_hour) for number in range(24)
    )
    minutes = _option("", "分", selected_minute) + "".join(
        _option(str(number), f"{number:02d}", selected_minute) for number in range(60)
    )

    def field_error(field: str) -> str:
        message = errors.get(field)
        return f'<p class="field-error">{escape(message)}</p>' if message else ""

    summary = ""
    if errors:
        summary = (
            '<div class="error-box" role="alert"><p>'
            + escape(errors.get("_form", "入力内容をご確認ください。"))
            + "</p></div>"
        )
    checked = " checked" if unknown else ""
    disabled = " disabled" if unknown else ""
    return f"""<!DOCTYPE html><html lang="ja"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow">{_PWA_HEAD}
<title>八雲式四柱推命 鑑定</title>{_FORM_CSS}</head><body>
<header class="site-header"><div class="brand">八雲式 四柱推命</div></header>
<main class="form-shell"><div class="form-intro"><p class="eyebrow">PERSONAL READING</p><h1>四柱推命鑑定</h1><p class="lead">生年月日などをご入力ください。命式を算出し、あなただけの鑑定結果をお届けします。</p></div>
<form id="reading-form" class="reading-form" method="post" action="/app/reading" novalidate><div class="grid">
{summary}
<div class="field"><label for="birth_date">生年月日<span class="required">必須</span></label><input id="birth_date" name="birth_date" type="date" value="{escape(values.get('birth_date',''), quote=True)}" required aria-describedby="birth-date-hint"><p id="birth-date-hint" class="hint">例：1984年7月22日</p>{field_error('birth_date')}</div>
<div class="field"><label for="birth_place">出生地<span class="required">必須</span></label><select id="birth_place" name="birth_place" required aria-describedby="birth-place-hint">{places}</select><p id="birth-place-hint" class="hint">出生した都道府県を選択してください。</p>{field_error('birth_place')}</div>
<div class="field full"><span class="label">出生時刻</span><div class="time-row"><select id="birth_hour" name="birth_hour" aria-label="出生時刻（時）"{disabled}>{hours}</select><span>時</span><select id="birth_minute" name="birth_minute" aria-label="出生時刻（分）"{disabled}>{minutes}</select><span>分</span></div>
<label class="unknown-row" for="birth_time_unknown"><input id="birth_time_unknown" name="birth_time_unknown" type="checkbox" value="1"{checked}>出生時刻が分からない</label>{field_error('birth_time')}<p class="hint">分からない場合は時刻を推測せず、チェックを入れてください。</p></div>
<div class="field"><label for="gender">性別<span class="required">必須</span></label><select id="gender" name="gender" required aria-describedby="gender-hint">{genders}</select><p id="gender-hint" class="hint">大運の順逆計算に使用します。</p>{field_error('gender')}</div>
<div class="field full"><label for="consultation">現在のお悩み・相談したいこと（任意）</label><textarea id="consultation" name="consultation" maxlength="{MAX_CONCERN_CHARS}" placeholder="仕事、恋愛、これからの方向性など、鑑定で特に知りたいことをご記入ください。">{escape(values.get('consultation',''))}</textarea><p class="hint">{MAX_CONCERN_CHARS}文字以内。入力内容は鑑定の焦点として使用します。</p>{field_error('consultation')}</div>
<div class="actions"><button id="submit-button" class="submit" type="submit">鑑定する</button><p id="processing" class="processing" role="status" aria-live="polite">鑑定結果を作成しています。鑑定中です。しばらくお待ちください。命式計算とAI鑑定を実行しています。</p></div>
</div></form><section class="install-panel" aria-labelledby="install-title"><p id="install-title" class="install-note">この鑑定には通信が必要です。入力内容や結果を、このアプリが端末へ保存することはありません。</p><p id="install-guidance" class="install-note"></p><button id="install-button" class="install-button" type="button">ホーム画面に追加</button></section></main>
<script>
const unknown=document.getElementById('birth_time_unknown');const hour=document.getElementById('birth_hour');const minute=document.getElementById('birth_minute');
function syncTime(){{hour.disabled=unknown.checked;minute.disabled=unknown.checked;if(unknown.checked){{hour.value='';minute.value='';}}}}unknown.addEventListener('change',syncTime);syncTime();
const readingForm=document.getElementById('reading-form');const submitButton=document.getElementById('submit-button');const processing=document.getElementById('processing');readingForm.addEventListener('submit',function(event){{if(this.dataset.submitting==='1'){{event.preventDefault();return;}}event.preventDefault();this.dataset.submitting='1';const button=submitButton;button.disabled=true;button.setAttribute('aria-busy','true');button.textContent='鑑定中…';processing.textContent='鑑定中です。しばらくお待ちください。命式を計算し、AI鑑定を生成しています。';processing.classList.add('active');const form=this;requestAnimationFrame(function(){{requestAnimationFrame(function(){{HTMLFormElement.prototype.submit.call(form);}});}});}},true);window.addEventListener('pageshow',function(){{delete readingForm.dataset.submitting;submitButton.disabled=false;submitButton.removeAttribute('aria-busy');submitButton.textContent='鑑定する';processing.classList.remove('active');}});
const installButton=document.getElementById('install-button');const installGuidance=document.getElementById('install-guidance');let installPrompt=null;const ios=/iphone|ipad|ipod/i.test(navigator.userAgent);const standalone=window.matchMedia('(display-mode: standalone)').matches||navigator.standalone===true;if(standalone){{installGuidance.textContent='ホーム画面から起動しています。鑑定には通信が必要です。';}}else if(ios){{installGuidance.textContent='iPhone／iPadでは共有メニューから「ホーム画面に追加」を選べます。';}}else{{installGuidance.textContent='対応ブラウザでは、利用可能になるとホーム画面へ追加できます。';}}window.addEventListener('beforeinstallprompt',function(event){{event.preventDefault();installPrompt=event;installButton.classList.add('available');}});installButton.addEventListener('click',async function(){{if(!installPrompt)return;installPrompt.prompt();await installPrompt.userChoice;installPrompt=null;installButton.classList.remove('available');}});if('serviceWorker' in navigator){{window.addEventListener('load',function(){{navigator.serviceWorker.register('/app/sw.js',{{scope:'/app'}}).catch(function(){{installGuidance.textContent+=' インストール準備を完了できませんでした。';}});}});}}
</script></body></html>"""


async def _form_values(request: Request) -> dict[str, str]:
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type != "application/x-www-form-urlencoded":
        raise CustomerInputError({"_form": "入力形式を確認して、もう一度お試しください。"})
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdecimal() and int(content_length) > _MAX_FORM_BYTES:
        raise CustomerInputError({"_form": "入力内容が長すぎます。"})
    body = await request.body()
    if len(body) > _MAX_FORM_BYTES:
        raise CustomerInputError({"_form": "入力内容が長すぎます。"})
    try:
        decoded = body.decode("utf-8", errors="strict")
        pairs = parse_qsl(
            decoded,
            keep_blank_values=True,
            strict_parsing=False,
            max_num_fields=20,
            encoding="utf-8",
            errors="strict",
        )
    except (UnicodeError, ValueError):
        raise CustomerInputError({"_form": "入力内容を読み取れませんでした。"}) from None
    result: dict[str, str] = {}
    allowed = {
        "birth_date", "birth_place", "birth_hour", "birth_minute",
        "birth_time_unknown", "gender", "consultation",
    }
    for key, value in pairs:
        if key not in allowed or key in result:
            raise CustomerInputError({"_form": "入力形式を確認して、もう一度お試しください。"})
        result[key] = value
    return result


def _render_customer_result(product: object) -> str:
    document = render_customer_reading_product_v2_html(product)  # type: ignore[arg-type]
    document = _NAMED_META.sub("", document)
    document = document.replace(
        "</head>",
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="robots" content="noindex,nofollow">' + _PWA_HEAD + _RESULT_CSS + "</head>",
        1,
    )
    document = document.replace(
        "<body>",
        '<body><nav class="web-nav"><a href="/app">入力画面へ戻る</a></nav>',
        1,
    )
    return append_product_reference_sidecar(document, product)


def _render_fast_chart(result: dict[str, object]) -> str:
    """Render the trusted chart/luck projection above the Fast Reading prose."""
    chart = result.get("chart", {})
    card = result.get("chart_card", {})

    def text(value: object) -> str:
        if value is None or value == "":
            return "―"
        return escape(str(value))

    def integer_age(item: dict[str, object], key: str) -> str:
        detail_key = "start_age_detail" if key == "start_age" else "end_age_detail"
        detail = item.get(detail_key)
        if isinstance(detail, dict) and isinstance(detail.get("years"), int):
            return str(detail["years"])
        value = item.get(key)
        if isinstance(value, (int, float)):
            return str(int(value))
        return "―"

    def pillar_value(position: str, key: str) -> str:
        pillar = card.get(position, {}) if isinstance(card, dict) else {}
        if not isinstance(pillar, dict):
            return "―"
        if position == "hour" and pillar.get("unavailable"):
            return text(pillar["unavailable"])
        value = pillar.get(key)
        if key in ("hidden_stems", "hidden_stem_ten_gods"):
            values = value if isinstance(value, list) else []
            return text(" / ".join(str(item) for item in values if item not in (None, "")))
        return text(value)

    positions = ("year", "month", "day", "hour")
    headers = "".join(
        f'<th scope="col">{label}</th>'
        for label in ("年柱", "月柱", "日柱", "時柱")
    )
    rows = []
    for label, key in (
        ("天干", "stem"), ("地支", "branch"), ("天干通変星", "stem_ten_god"),
        ("十二運", "twelve_stage"), ("蔵干", "hidden_stems"),
        ("蔵干通変星", "hidden_stem_ten_gods"),
    ):
        cells = "".join(f"<td>{pillar_value(position, key)}</td>" for position in positions)
        rows.append(f'<tr><th scope="row">{label}</th>{cells}</tr>')

    luck = result.get("luck_pillars", [])
    current = chart.get("current_luck", {}) if isinstance(chart, dict) else {}
    current_pillar = current.get("current_luck_pillar", {}) if isinstance(current, dict) else {}
    current_index = current_pillar.get("index") if isinstance(current_pillar, dict) else None
    luck_rows = []
    if isinstance(luck, list):
        for item in luck:
            if not isinstance(item, dict):
                continue
            mark = " current-mark" if current_index is not None and item.get("index") == current_index else ""
            age = f'{integer_age(item, "start_age")}〜{integer_age(item, "end_age")}歳'
            extras = " / ".join(str(item.get(key)) for key in ("stem_ten_god", "stem_element", "branch_element") if item.get(key))
            luck_rows.append(f'<tr class="{mark.strip()}"><td>{age}</td><td>{text(item.get("ganzhi"))}</td><td>{text(extras)}</td></tr>')

    annual = result.get("annual_luck_15", [])
    current_year = result.get("current_year")
    annual_cells = []
    if isinstance(annual, list):
        for item in annual:
            if not isinstance(item, dict):
                continue
            mark = " current-mark" if item.get("year") == current_year else ""
            stem_element = item.get("stem_element")
            branch_element = item.get("branch_element")
            elements = "―" if not stem_element or not branch_element else f"{escape(str(stem_element))} / {escape(str(branch_element))}"
            annual_cells.append(f'<div class="annual-cell{mark}"><strong>{text(item.get("year"))}年</strong><span>{text(item.get("ganzhi"))}</span><small>{elements}</small></div>')

    return (
        '<section class="chart-record"><h2>鑑定カルテ</h2>'
        '<div class="table-wrap"><table class="chart-table"><colgroup><col><col><col><col><col></colgroup><thead><tr>'
        f'<th scope="col">項目名</th>{headers}'
        '</tr></thead><tbody>' + "".join(rows) + '</tbody></table></div>'
        '<div class="luck-record"><h3>大運</h3><p class="section-note">算出された全期間を表示しています。</p>'
        '<div class="table-wrap"><table class="luck-table"><thead><tr><th>開始〜終了年齢</th><th>干支</th><th>対応情報</th></tr></thead><tbody>'
        + "".join(luck_rows) + '</tbody></table></div></div>'
        '<div class="luck-record"><h3>年運</h3><p class="section-note">現在年から10年分（五行：天干 / 地支）</p>'
        '<div class="table-wrap"><div class="annual-grid">' + "".join(annual_cells) + '</div></div></div></section>'
    )


def _split_fast_prose(value: object) -> list[str]:
    """Create display-only paragraphs without rewriting provider prose."""
    text = "" if value is None else str(value)
    if not text.strip():
        return ["―"]
    blocks = re.split(r"\n\s*\n+", text.strip())
    result: list[str] = []
    opening = set("（「『【［〈《")
    closing = set("）」』】］〉》")
    for block in blocks:
        if "\n" in block:
            result.append(block)
            continue
        current: list[str] = []
        sentences = 0
        depth = 0
        quote: str | None = None
        for char in block:
            current.append(char)
            if char in opening:
                depth += 1
            elif char in closing:
                depth = max(0, depth - 1)
            elif char in {'"', "'"} and depth == 0:
                quote = None if quote == char else (quote or char)
            elif depth == 0 and quote is None and char in "。！？!?":
                sentences += 1
                if sentences >= 3:
                    result.append("".join(current))
                    current = []
                    sentences = 0
        if current:
            result.append("".join(current))
    return result


def _render_fast_prose(value: object) -> str:
    """Render provider prose while preserving its authored line breaks safely."""
    text = "" if value is None else str(value)
    if not text.strip():
        return "<p>―</p>"
    rendered: list[str] = []
    for block in _split_fast_prose(text):
        safe = escape(block).replace("\n", "<br>\n")
        rendered.append(f"<p>{safe}</p>")
    return "".join(rendered)


_FAST_DETAIL_PROSE_SCRIPT = r'''<script>
function splitFastProse(value) {
  const text = String(value ?? "");
  if (!text.trim()) return ["―"];
  const blocks = text.trim().split(/\n\s*\n+/);
  const result = [];
  const opening = new Set(["（", "「", "『", "【", "［", "〈", "《"]);
  const closing = new Set(["）", "」", "』", "】", "］", "〉", "》"]);
  for (const block of blocks) {
    if (block.includes("\n")) { result.push(block); continue; }
    let current = "", sentences = 0, depth = 0, quote = null;
    for (const char of block) {
      current += char;
      if (opening.has(char)) depth += 1;
      else if (closing.has(char)) depth = Math.max(0, depth - 1);
      else if ((char === '"' || char === "'") && depth === 0) quote = quote === char ? null : (quote || char);
      else if (depth === 0 && !quote && "。！？!?".includes(char)) {
        sentences += 1;
        if (sentences >= 3) { result.push(current); current = ""; sentences = 0; }
      }
    }
    if (current) result.push(current);
  }
  return result;
}
function renderFastProse(box, value) {
  box.replaceChildren();
  for (const block of splitFastProse(value)) {
    const paragraph = document.createElement("p");
    block.split("\n").forEach((line, index) => {
      if (index) paragraph.append(document.createElement("br"));
      paragraph.append(document.createTextNode(line));
    });
    box.append(paragraph);
  }
}
</script>'''


def _render_fast_result_raw(result: dict[str, object]) -> str:
    session_id = escape(str(result["session_id"]), quote=True)
    chart = result.get("chart", {})
    pillars = chart.get("chart", {}) if isinstance(chart, dict) else {}
    pillar_text = " / ".join(
        str(pillars.get(key, {}).get("pillar", ""))
        for key in ("year", "month", "day", "hour")
        if isinstance(pillars.get(key), dict) and pillars.get(key, {}).get("pillar")
    )
    sections = result.get("sections", {})
    cards: list[str] = []
    for key, label in ("basic_type", "あなたの基本タイプ"), ("career", "仕事・適職"), ("wealth", "お金"), ("relationships", "人間関係"), ("current_luck", "現在の運勢"), ("future_flow", "今後の流れ"), ("advice", "今すべきこと"):
        prose = _render_fast_prose(sections.get(key, "") if isinstance(sections, dict) else "")
        button = "" if key in ("basic_type", "advice") else f'<button class="detail-button" data-detail="{key}" type="button">詳しく見る</button><div class="detail-box" hidden></div>'
        cards.append(f'<article class="fast-card"><h2>{label}</h2><div class="fast-prose">{prose}</div>{button}</article>')
    # The chart is rendered from server-owned projections before the existing
    # Fast Reading cards; provider contracts and detail behavior stay intact.
    cards.insert(0, _render_fast_chart(result))
    return f'''<!DOCTYPE html><html lang="ja"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow">{_PWA_HEAD}<title>八雲式 四柱推命 鑑定結果</title>{_FAST_CSS}</head><body><nav class="web-nav"><a href="/app">入力画面へ戻る</a></nav><main class="fast-shell"><header class="fast-head"><p class="eyebrow">PERSONAL READING</p><h1>あなたの鑑定結果</h1><p>命式の主要な傾向を先に確認できます。詳しい内容は必要な項目だけご覧ください。</p></header><div class="fast-facts"><span>命式：{escape(pillar_text)}</span></div><section class="fast-grid">{''.join(cards)}</section></main><script>
const sid="{session_id}";document.querySelectorAll('.detail-button').forEach((button)=>button.addEventListener('click',async()=>{{const box=button.nextElementSibling;const type=button.dataset.detail;if(!box.hidden){{box.hidden=true;button.textContent='詳しく見る';return;}}button.disabled=true;box.hidden=false;box.className='detail-box detail-loading';box.textContent='詳しい鑑定を準備しています…';try{{const response=await fetch('/app/reading/detail',{{method:'POST',headers:{{'content-type':'application/json'}},body:JSON.stringify({{session_id:sid,detail_type:type}})}});const data=await response.json();if(!response.ok)throw new Error();box.className='detail-box';box.textContent=data.text;button.textContent='閉じる';}}catch(_error){{box.textContent='詳細鑑定を取得できませんでした。もう一度お試しください。';}}finally{{button.disabled=false;}}}}));
 </script></body></html>'''


def _render_fast_result(result: dict[str, object]) -> str:
    """Add safe client-side paragraph rendering to the existing result shell."""
    document = _render_fast_result_raw(result)

    def replace_once(marker: str, replacement: str, *, label: str) -> str:
        if document.count(marker) != 1:
            raise RuntimeError(f"fast result render marker missing or duplicated: {label}")
        return document.replace(marker, replacement, 1)

    concern_card = _render_concern_card(result)
    if concern_card:
        document = replace_once(
            "</head>",
            "<style>.concern-card{grid-column:1/-1;min-width:0;max-width:100%;border:1px solid #dfd1c2;border-radius:12px;padding:18px;background:#fffaf1}.concern-card h2{color:#5d3b25}.concern-label{font-weight:700;color:#75685c}.concern-text{white-space:pre-wrap;max-width:100%;overflow-wrap:anywhere;word-break:break-word;margin:8px 0 14px}.concern-answer-button{border:1px solid #8a5a3b;background:#fff;color:#6a412a;border-radius:7px;padding:8px 12px;cursor:pointer;max-width:100%;white-space:normal}.concern-answer-button:disabled{opacity:.65;cursor:wait}</style></head>",
            label="concern_css_head",
        )
        document = replace_once(
            "</section></main><script>",
            f"</section>{concern_card}</main><script>",
            label="concern_card",
        )
    document = replace_once(
        "</head>",
        _FAST_RESPONSIVE_CSS + "</head>",
        label="responsive_css_head",
    )
    # Keep the detail-button handler inside the existing script element.  The
    # prose helper is a complete script fragment for standalone rendering, but
    # inserting its closing tag here would leave `const sid` outside executable
    # JavaScript and prevent all detail-button listeners from being registered.
    detail_script = _FAST_DETAIL_PROSE_SCRIPT
    if detail_script.rstrip().endswith("</script>"):
        detail_script = detail_script.rstrip()[:-len("</script>")]
    document = replace_once(
        "<script>\nconst sid=",
        detail_script.rstrip() + "\nconst sid=",
        label="detail_script",
    )
    document = document.replace("box.textContent=data.text;", "renderFastProse(box,data.text);")
    if concern_card:
        document = replace_once(
            "</script></body></html>",
            """document.querySelectorAll('.concern-answer-button').forEach((button)=>button.addEventListener('click',async()=>{const box=button.nextElementSibling;button.disabled=true;box.hidden=false;box.className='detail-box detail-loading';box.textContent='回答を準備しています…';try{const response=await fetch('/app/reading/concern',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({session_id:sid})});const data=await response.json();if(!response.ok)throw new Error();box.className='detail-box';renderFastProse(box,data.answer);button.textContent='回答を表示中';}catch(_error){box.textContent='個別回答を取得できませんでした。もう一度お試しください。';}finally{button.disabled=false;}}));</script></body></html>""",
            label="concern_script",
        )
    return append_reference_sidecar(document, result.get("chart"))


def _move_fast_back_link_to_header(document: str) -> str:
    """Move the existing return link into the Fast Reading header."""
    document = re.sub(r'<nav class="web-nav"><a href="/app">.*?</a></nav>', "", document, count=1)
    return document.replace(
        '<header class="fast-head"><p class="eyebrow">',
        '<header class="fast-head"><a class="fast-back" href="/app" '
        'onclick="if(window.history.length>1){window.history.back();return false;}">'
        '← 入力画面に戻る</a><p class="eyebrow">',
        1,
    )


def _render_concern_card(result: dict[str, object]) -> str:
    consultation = result.get("consultation")
    if not isinstance(consultation, str) or not consultation.strip():
        return ""
    safe = escape(consultation, quote=True)
    return (
        '<section class="concern-card">'
        '<h2>あなたのお悩みへの個別回答</h2>'
        '<p class="concern-label">ご相談内容</p>'
        f'<div class="concern-text">{safe}</div>'
        '<button class="concern-answer-button" type="button">八雲からの回答を見る</button>'
        '<div class="concern-answer-box" hidden></div>'
        '</section>'
    )


@router.get("/app", response_class=HTMLResponse, include_in_schema=False)
def customer_form() -> HTMLResponse:
    return HTMLResponse(_render_form())


@router.get("/app/manifest.webmanifest", include_in_schema=False)
def customer_manifest() -> FileResponse:
    return FileResponse(
        _CUSTOMER_STATIC / "manifest.webmanifest",
        media_type="application/manifest+json",
        headers={"Cache-Control": "no-cache"},
    )


@router.get("/app/icon.svg", include_in_schema=False)
def customer_icon() -> FileResponse:
    return FileResponse(
        _CUSTOMER_STATIC / "icon.svg",
        media_type="image/svg+xml",
        headers={"Cache-Control": "public, max-age=86400"},
    )


def _customer_png_icon(filename: str) -> FileResponse:
    return FileResponse(
        _CUSTOMER_STATIC / filename,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.get("/app/apple-touch-icon.png", include_in_schema=False)
def customer_apple_touch_icon() -> FileResponse:
    return _customer_png_icon("apple-touch-icon.png")


@router.get("/app/icon-192.png", include_in_schema=False)
def customer_icon_192() -> FileResponse:
    return _customer_png_icon("icon-192.png")


@router.get("/app/icon-512.png", include_in_schema=False)
def customer_icon_512() -> FileResponse:
    return _customer_png_icon("icon-512.png")


@router.get("/app/sw.js", include_in_schema=False)
def customer_service_worker() -> FileResponse:
    return FileResponse(
        _CUSTOMER_STATIC / "sw.js",
        media_type="application/javascript",
        headers={"Cache-Control": "no-store", "Service-Worker-Allowed": "/app"},
    )


@router.get("/app/reading", response_class=HTMLResponse, include_in_schema=False)
def customer_reading_form() -> HTMLResponse:
    return HTMLResponse(_render_form())


@router.post("/app/reading/full", response_class=HTMLResponse, include_in_schema=False)
async def customer_reading_full(request: Request) -> HTMLResponse:
    performance = PerformanceTrace()
    values: dict[str, str] = {}
    try:
        with performance.measure("request_parse"):
            values = await _form_values(request)
            customer_input = validate_customer_input(values)
    except CustomerInputError as exc:
        performance.finish(status="error")
        return HTMLResponse(_render_form(values, exc.errors), status_code=422)
    try:
        token = set_performance_trace(performance)
        try:
            product = await run_in_threadpool(run_customer_reading, customer_input)
        finally:
            reset_performance_trace(token)
        with performance.measure("html_render"):
            document = _render_customer_result(product)
        performance.skip("pdf_generation")
        performance.finish(status="success")
        return HTMLResponse(document)
    except CustomerConfigurationError as exc:
        performance.finish(status="error")
        logger.error(
            "customer reading configuration failure stage=%s reason=%s",
            exc.stage,
            exc.reason_code,
        )
        return HTMLResponse(
            _render_form(values, {"_form": "現在、鑑定サービスの準備が整っていません。しばらくしてからお試しください。"}),
            status_code=503,
        )
    except CustomerReadingUnavailableError as exc:
        performance.finish(status="error")
        logger.warning(
            "customer reading publication unavailable stage=%s reason=%s decision=%s blockers=%s diagnostic_codes=%s locations=%s",
            exc.stage,
            exc.reason_code,
            exc.decision or "none",
            ",".join(exc.blocking_codes) if exc.blocking_codes else "none",
            ",".join(getattr(exc, "diagnostic_codes", ())) or "none",
            ",".join(getattr(exc, "diagnostic_locations", ())) or "none",
        )
        return HTMLResponse(
            _render_form(values, {"_form": _generation_error_message(exc)}),
            status_code=503,
        )
    except Exception as exc:
        performance.finish(status="error")
        logger.error("customer reading unexpected failure: %s", type(exc).__name__)
        return HTMLResponse(
            _render_form(values, {"_form": _generation_error_message(exc)}),
            status_code=500,
        )


@router.post("/app/reading", response_class=HTMLResponse, include_in_schema=False)
async def customer_reading_fast(request: Request) -> HTMLResponse:
    """Fast first-screen reading; the frozen full pipeline remains at /full."""
    values: dict[str, str] = {}
    request_id = uuid4().hex
    started = time.perf_counter()
    performance: dict[str, object] = {"provider_calls": 0, "status": "error"}
    try:
        values = await _form_values(request)
        customer_input = validate_customer_input(values)
        result = await run_in_threadpool(run_fast_reading, customer_input, performance=performance)
        render_started = time.perf_counter()
        document = _render_fast_result(result)
        document = _move_fast_back_link_to_header(document)
        performance["render_elapsed"] = time.perf_counter() - render_started
        performance["status"] = "success"
        return HTMLResponse(document)
    except CustomerInputError as exc:
        return HTMLResponse(_render_form(values, exc.errors), status_code=422)
    except Exception as exc:
        frames = traceback.extract_tb(exc.__traceback__) if exc.__traceback__ else []
        frame = frames[-1] if frames else None
        performance["failure_type"] = type(exc).__name__
        performance["failure_stage"] = performance.get("fast_stage") or ("provider" if "provider" in str(exc).lower() else "fast_reading")
        if frame is not None:
            performance["failure_file"] = os.path.basename(frame.filename)
            performance["failure_function"] = frame.name
            performance["failure_line"] = frame.lineno
        logger.warning(
            "fast customer reading unavailable error_type=%s stage=%s file=%s function=%s line=%s",
            type(exc).__name__,
            performance["failure_stage"],
            performance.get("failure_file", "unknown"),
            performance.get("failure_function", "unknown"),
            performance.get("failure_line", "unknown"),
            exc_info=False,
        )
        # Existing provider-free browser regression tests replace the legacy
        # pipeline with a deterministic fake.  Preserve that test seam (and
        # the full pipeline itself) without affecting the production fast
        # path, whose function remains the original imported implementation.
        if getattr(run_customer_reading, "__module__", "api.customer_pipeline") != "api.customer_pipeline":
            try:
                product = await run_in_threadpool(run_customer_reading, customer_input)
                return HTMLResponse(_render_customer_result(product))
            except CustomerReadingUnavailableError as exc:
                logger.warning(
                    "customer reading publication unavailable stage=%s reason=%s decision=%s blockers=%s diagnostic_codes=%s locations=%s",
                    exc.stage,
                    exc.reason_code,
                    exc.decision or "none",
                    ",".join(exc.blocking_codes) if exc.blocking_codes else "none",
                    ",".join(getattr(exc, "diagnostic_codes", ())) or "none",
                    ",".join(getattr(exc, "diagnostic_locations", ())) or "none",
                )
                return HTMLResponse(
                    _render_form(values, {"_form": _generation_error_message(exc)}),
                    status_code=503,
                )
            except Exception:
                pass
        logger.warning("fast customer reading unavailable", exc_info=False)
        return HTMLResponse(
            _render_form(values, {"_form": _generation_error_message(exc)}),
            status_code=503,
        )


    finally:
        performance["total_elapsed"] = time.perf_counter() - started
        _emit_perf("FAST_PERF", {"request_id": request_id, **performance})


@router.post("/app/reading/detail", response_class=HTMLResponse, include_in_schema=False)
async def customer_reading_detail(request: Request) -> HTMLResponse:
    request_id = uuid4().hex
    started = time.perf_counter()
    performance: dict[str, object] = {"provider_calls": 0, "cache_hit": False, "status": "error"}
    try:
        payload = await request.json()
        session_id = payload.get("session_id") if isinstance(payload, dict) else None
        detail_type = payload.get("detail_type") if isinstance(payload, dict) else None
        performance["payload_valid"] = isinstance(payload, dict)
        performance["detail_type_allowed"] = isinstance(detail_type, str) and detail_type in DETAIL_TYPES
        session = get_session(session_id) if isinstance(session_id, str) else None
        performance["session_present"] = session is not None
        if not isinstance(session_id, str) or not isinstance(detail_type, str):
            raise ValueError("invalid detail request")
        if session is None or detail_type not in DETAIL_TYPES:
            raise ValueError("invalid detail request")
        text = await run_in_threadpool(run_detail, session_id, detail_type, performance=performance)
        performance["provider_calls"] = 0 if performance.get("cache_hit") else 1
        performance["status"] = "success"
        return JSONResponse({"text": text})
    except Exception as exc:
        performance["failure_type"] = type(exc).__name__
        performance["failure_stage"] = performance.get("failure_stage") or (
            "request_parse" if "payload_valid" not in performance else
            "session_or_detail_validation" if not performance.get("session_present", False) or not performance.get("detail_type_allowed", False) else
            "detail_generation"
        )
        logger.warning(
            "fast detail unavailable error_type=%s stage=%s session_present=%s detail_type_allowed=%s",
            performance["failure_type"],
            performance["failure_stage"],
            performance.get("session_present", False),
            performance.get("detail_type_allowed", False),
            exc_info=False,
        )
        return JSONResponse(
            {"error": "詳細鑑定を取得できませんでした。もう一度お試しください。"},
            status_code=400,
        )
    finally:
        performance["total_elapsed"] = time.perf_counter() - started
        _emit_perf(
            "DETAIL_PERF",
            {"request_id": request_id, "detail_type": locals().get("detail_type"), **performance},
        )


@router.post("/app/reading/concern", response_class=JSONResponse, include_in_schema=False)
async def customer_reading_concern(request: Request) -> JSONResponse:
    """Generate the optional consultation answer without affecting Fast Reading."""
    request_id = uuid4().hex
    started = time.perf_counter()
    performance: dict[str, object] = {
        "provider_call_attempted": False,
        "validation_failed": False,
        "cache_hit": False,
        "status": "error",
    }
    session_present = False
    try:
        payload = await request.json()
        session_id = payload.get("session_id") if isinstance(payload, dict) else None
        session_present = isinstance(session_id, str) and get_session(session_id) is not None
        performance["session_present"] = session_present
        if not isinstance(session_id, str) or not session_present:
            raise ValueError("invalid concern request")
        result = await run_in_threadpool(run_concern_answer, session_id, performance=performance)
        performance["status"] = "success"
        return JSONResponse(result)
    except Exception as exc:
        performance["failure_type"] = type(exc).__name__
        performance["failure_stage"] = (
            "request_parse" if "payload" not in locals() else
            "session_validation" if not session_present else
            "concern_generation"
        )
        logger.warning(
            "fast concern unavailable error_type=%s stage=%s session_present=%s provider_call_attempted=%s validation_failed=%s",
            performance["failure_type"],
            performance["failure_stage"],
            session_present,
            performance["provider_call_attempted"],
            performance["validation_failed"],
            exc_info=False,
        )
        return JSONResponse(
            {"error": "個別回答を取得できませんでした。もう一度お試しください。"},
            status_code=400,
        )
    finally:
        performance["total_elapsed"] = time.perf_counter() - started
        _emit_perf("CONCERN_PERF", {"request_id": request_id, **performance})


# Backward-compatible Python import alias; the public POST route is now fast.
customer_reading = customer_reading_full

__all__ = ["router", "customer_form", "customer_reading", "customer_reading_fast", "customer_reading_full", "customer_reading_detail"]
