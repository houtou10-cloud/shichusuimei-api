"""Server-rendered customer flow for the trusted v1.2 reading pipeline."""

from __future__ import annotations

from html import escape
import logging
import re
from urllib.parse import parse_qsl

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
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
from engine.reading_renderer_v2 import render_customer_reading_product_v2_html


router = APIRouter()
logger = logging.getLogger(__name__)

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
.hint{margin:.4rem 0 0;color:var(--muted);font-size:.86rem}.field-error{margin:.35rem 0 0;color:var(--danger);font-size:.88rem}.error-box{grid-column:1/-1;border-left:4px solid var(--danger);background:#fff1ef;padding:12px 14px;color:#772a27}.error-box p{margin:0}
textarea{min-height:150px;resize:vertical}.actions{grid-column:1/-1;margin-top:8px}.submit{width:100%;border:0;border-radius:9px;padding:14px 20px;background:linear-gradient(120deg,#6b4328,#9a6a35);color:#fff;font:700 1.06rem inherit;letter-spacing:.1em;cursor:pointer}.submit:hover{filter:brightness(1.05)}.submit:disabled{cursor:wait;opacity:.68}.processing{display:none;text-align:center;margin:.75rem 0 0;color:var(--muted)}.processing.active{display:block}
@media(max-width:680px){.form-shell{margin-top:18px;width:min(100% - 18px,900px)}.form-intro,.reading-form{padding-left:20px;padding-right:20px}.grid{grid-template-columns:1fr}.field.full,.error-box,.actions{grid-column:1}.site-header{padding:14px 15px}}
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


def _option(value: str, label: str, selected: str) -> str:
    selected_attr = " selected" if value == selected else ""
    return f'<option value="{escape(value, quote=True)}"{selected_attr}>{escape(label)}</option>'


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
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow">
<title>八雲式四柱推命 鑑定</title>{_FORM_CSS}</head><body>
<header class="site-header"><div class="brand">八雲式 四柱推命</div></header>
<main class="form-shell"><div class="form-intro"><p class="eyebrow">PERSONAL READING</p><h1>四柱推命鑑定</h1><p class="lead">生年月日などをご入力ください。命式を算出し、あなただけの鑑定結果をお届けします。</p></div>
<form id="reading-form" class="reading-form" method="post" action="/app/reading" novalidate><div class="grid">
{summary}
<div class="field"><label for="birth_date">生年月日<span class="required">必須</span></label><input id="birth_date" name="birth_date" type="date" value="{escape(values.get('birth_date',''), quote=True)}" required>{field_error('birth_date')}</div>
<div class="field"><label for="birth_place">出生地<span class="required">必須</span></label><select id="birth_place" name="birth_place" required>{places}</select>{field_error('birth_place')}</div>
<div class="field full"><span class="label">出生時刻</span><div class="time-row"><select id="birth_hour" name="birth_hour" aria-label="出生時刻（時）"{disabled}>{hours}</select><span>時</span><select id="birth_minute" name="birth_minute" aria-label="出生時刻（分）"{disabled}>{minutes}</select><span>分</span></div>
<label class="unknown-row" for="birth_time_unknown"><input id="birth_time_unknown" name="birth_time_unknown" type="checkbox" value="1"{checked}>出生時刻が分からない</label>{field_error('birth_time')}<p class="hint">分からない場合は時刻を推測せず、チェックを入れてください。</p></div>
<div class="field"><label for="gender">性別<span class="required">必須</span></label><select id="gender" name="gender" required>{genders}</select>{field_error('gender')}</div>
<div class="field full"><label for="consultation">現在のお悩み・相談したいこと（任意）</label><textarea id="consultation" name="consultation" maxlength="{MAX_CONCERN_CHARS}" placeholder="仕事、恋愛、これからの方向性など、鑑定で特に知りたいことをご記入ください。">{escape(values.get('consultation',''))}</textarea><p class="hint">{MAX_CONCERN_CHARS}文字以内。入力内容は鑑定の焦点として使用します。</p>{field_error('consultation')}</div>
<div class="actions"><button id="submit-button" class="submit" type="submit">鑑定する</button><p id="processing" class="processing" role="status" aria-live="polite">鑑定結果を作成しています。画面を閉じずにお待ちください…</p></div>
</div></form></main>
<script>
const unknown=document.getElementById('birth_time_unknown');const hour=document.getElementById('birth_hour');const minute=document.getElementById('birth_minute');
function syncTime(){{hour.disabled=unknown.checked;minute.disabled=unknown.checked;if(unknown.checked){{hour.value='';minute.value='';}}}}unknown.addEventListener('change',syncTime);syncTime();
document.getElementById('reading-form').addEventListener('submit',function(){{const button=document.getElementById('submit-button');button.disabled=true;button.textContent='鑑定中…';document.getElementById('processing').classList.add('active');}});
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
        '<meta name="robots" content="noindex,nofollow">' + _RESULT_CSS + "</head>",
        1,
    )
    document = document.replace(
        "<body>",
        '<body><nav class="web-nav"><a href="/app">入力画面へ戻る</a></nav>',
        1,
    )
    return document


@router.get("/app", response_class=HTMLResponse, include_in_schema=False)
def customer_form() -> HTMLResponse:
    return HTMLResponse(_render_form())


@router.get("/app/reading", response_class=HTMLResponse, include_in_schema=False)
def customer_reading_form() -> HTMLResponse:
    return HTMLResponse(_render_form())


@router.post("/app/reading", response_class=HTMLResponse, include_in_schema=False)
async def customer_reading(request: Request) -> HTMLResponse:
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
            _render_form(values, {"_form": "鑑定結果の生成中に確認が必要な状態になりました。恐れ入りますが、もう一度お試しください。"}),
            status_code=503,
        )
    except Exception as exc:
        performance.finish(status="error")
        logger.error("customer reading unexpected failure: %s", type(exc).__name__)
        return HTMLResponse(
            _render_form(values, {"_form": "鑑定結果を作成できませんでした。時間をおいてもう一度お試しください。"}),
            status_code=500,
        )


__all__ = ["router", "customer_form", "customer_reading"]
