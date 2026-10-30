"""公式LINEの無料日干診断（Messaging APIのWebhook、/line/webhook）。

友だちがトークに生年月日を送ると、日干の読み物を返す。続けて悩みの種類をボタンで選ぶと、
日干×悩みの一言を返す。文章は day_stem_check と同じ固定の文章で、AIは使わない。
生年月日は保存しない（ボタンの中に入れて往復させるだけ）。件数は悩みの種類だけをログに書く。
「とてもつらい」を選んだ人や、命に関わる言葉を送った人には、診断より先に相談窓口を返し、販売の案内は出さない。

環境変数：LINE_CHANNEL_SECRET（署名の確認）、LINE_CHANNEL_ACCESS_TOKEN（返信）。
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import re
import unicodedata
from datetime import date
from urllib.parse import parse_qs, urlencode

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from api import day_stem_check
from api.day_stem_check import CONCERN_NOTES, CONCERNS, DayStemInputError, STEM_YIN_YANG, day_stem_for, parse_birth_date
from api.yakumo_reading_note import DAY_STEM_NOTES, STEM_ELEMENT

logger = logging.getLogger(__name__)
router = APIRouter()

REPLY_URL = "https://api.line.me/v2/bot/message/reply"
MAX_BODY_BYTES = 64 * 1024

CRISIS_WORDS = ("死にたい", "消えたい", "自殺", "死のう", "生きていたくない", "生きるのがつらい", "いなくなりたい")

SUPPORT_TEXT = (
    "いま、とてもつらいのですね。教えてくれて、ありがとうございます。\n"
    "占いより先に、話を聞いてくれる人や場所に連絡してください。\n\n"
    "よりそいホットライン\n0120-279-338（24時間・無料）\n\n"
    "いのちの電話\n0570-783-556\n\n"
    "電話やSNSで相談できる窓口は、こちらで探せます。\n"
    "まもろうよ こころ（厚生労働省）\nhttps://www.mhlw.go.jp/mamorouyokokoro/"
)

HELP_TEXT = (
    "無料の日干診断です。\n"
    "生年月日を、次のように送ってください。\n\n"
    "1985/10/13\n\n"
    "あなた自身を表す「日干」と、その自然のイメージをお届けします。\n"
    "送っていただいた生年月日は、診断にだけ使い、保存しません。"
)

WELCOME_TEXT = "友だち追加ありがとうございます。八雲式 四柱推命です。\n\n" + HELP_TEXT

_DATE = re.compile(r"(\d{4})\D{0,2}(\d{1,2})\D{0,2}(\d{1,2})")


def _secret() -> str:
    return os.getenv("LINE_CHANNEL_SECRET", "").strip()


def _token() -> str:
    return os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "").strip()


def valid_signature(body: bytes, signature: str, secret: str) -> bool:
    expected = base64.b64encode(hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()).decode("ascii")
    return bool(signature) and hmac.compare_digest(expected, signature)


def parse_date_text(text: str) -> date | None:
    """「1985/10/13」「1985年10月13日」「19851013」などを日付にする。読めなければ None。"""
    normalized = unicodedata.normalize("NFKC", text or "").strip()
    match = _DATE.search(normalized) or re.fullmatch(r"(\d{4})(\d{2})(\d{2})", normalized)
    if not match:
        return None
    try:
        return parse_birth_date(f"{int(match[1]):04d}-{int(match[2]):02d}-{int(match[3]):02d}")
    except DayStemInputError:
        return None


def _public_link(path: str) -> str:
    base = os.getenv("CUSTOMER_PUBLIC_BASE_URL", "").strip().rstrip("/") or "https://app.yakumoshiki.jp"
    return f"{base}{path}?src=line"


def _text(text: str, quick_reply: dict | None = None) -> dict:
    message: dict = {"type": "text", "text": text[:5000]}
    if quick_reply:
        message["quickReply"] = quick_reply
    return message


def _concern_buttons(birth: date) -> dict:
    items = []
    for key, label in CONCERNS.items():
        data = urlencode({"concern": key, "birth_date": birth.isoformat()})
        items.append({"type": "action", "action": {"type": "postback", "label": label, "data": data, "displayText": label}})
    return {"items": items}


def day_stem_messages(birth: date) -> list[dict]:
    stem = day_stem_for(birth)
    note = DAY_STEM_NOTES[stem]
    body = (
        f"{birth.year}年{birth.month}月{birth.day}日生まれ\n\n"
        f"あなたの日干は「{stem}」\n{note['image']}のイメージです。\n"
        f"日干の{stem}は、{STEM_YIN_YANG[stem]}の{STEM_ELEMENT[stem]}です。\n\n"
        f"{note['nature']}\n\n{note['care']}\n\n"
        f"ふり返りの問い\n「{note['question']}」\n"
        "ノートに一行、書いてみてください。答えに正解はありません。\n\n"
        "※ 日干だけを見た、八雲式の読み物です。四柱推命の判定ではありません。23時以降に生まれた方は、日干が翌日のものになる場合があります。"
    )
    ask = "いまの悩みに近いものを選ぶと、日干に合わせた一言をお届けします（選ばなくても大丈夫です）。"
    return [_text(body), _text(ask, _concern_buttons(birth))]


def concern_messages(concern: str, birth: date) -> list[dict]:
    if concern == "hard":
        return [_text(SUPPORT_TEXT)]
    stem = day_stem_for(birth)
    note = CONCERN_NOTES[stem].get(concern)
    if not note:
        return [_text(HELP_TEXT)]
    return [
        _text(f"{stem}（{DAY_STEM_NOTES[stem]['image']}）のあなたが、「{CONCERNS[concern]}」に悩むとき\n\n{note}"),
        _text(
            "いまの悩みに、命式全体から答えるのが、八雲式 四柱推命鑑定です。\n"
            "命式全体と今の流れ、お悩みへの回答、八雲式の読み物をお届けします。\n"
            f"{_public_link('/career-reading')}\n\n"
            "自分で読めるようになりたい方は、アカデミー（第1章は無料）\n"
            f"{_public_link('/academy')}"
        ),
    ]


def messages_for_event(event: dict) -> list[dict]:
    kind = event.get("type")
    if kind == "follow":
        return [_text(WELCOME_TEXT)]
    if kind == "message" and isinstance(event.get("message"), dict):
        message = event["message"]
        if message.get("type") != "text":
            return [_text(HELP_TEXT)]
        text = str(message.get("text", ""))
        if any(word in unicodedata.normalize("NFKC", text) for word in CRISIS_WORDS):
            day_stem_check.record_concern("hard")
            return [_text(SUPPORT_TEXT)]
        birth = parse_date_text(text)
        if birth is None:
            return [_text(HELP_TEXT)]
        return day_stem_messages(birth)
    if kind == "postback" and isinstance(event.get("postback"), dict):
        data = parse_qs(str(event["postback"].get("data", "")))
        concern = day_stem_check.parse_concern((data.get("concern") or [""])[0])
        try:
            birth = parse_birth_date((data.get("birth_date") or [""])[0])
        except DayStemInputError:
            return [_text(HELP_TEXT)]
        if not concern:
            return [_text(HELP_TEXT)]
        day_stem_check.record_concern(concern)
        return concern_messages(concern, birth)
    return []


def reply(reply_token: str, messages: list[dict]) -> None:
    response = httpx.post(
        REPLY_URL,
        headers={"Authorization": f"Bearer {_token()}", "Content-Type": "application/json"},
        content=json.dumps({"replyToken": reply_token, "messages": messages[:5]}, ensure_ascii=False).encode("utf-8"),
        timeout=10,
    )
    if response.status_code >= 400:
        logger.warning("line reply failed status=%s", response.status_code)


@router.post("/line/webhook", include_in_schema=False)
async def line_webhook(request: Request) -> JSONResponse:
    secret = _secret()
    if not secret or not _token():
        return JSONResponse({"error": "line_not_configured"}, status_code=503)
    body = await request.body()
    if len(body) > MAX_BODY_BYTES or not valid_signature(body, request.headers.get("x-line-signature", ""), secret):
        return JSONResponse({"error": "invalid_signature"}, status_code=400)
    try:
        events = json.loads(body.decode("utf-8")).get("events", [])
    except (UnicodeError, ValueError, AttributeError):
        return JSONResponse({"error": "invalid_body"}, status_code=400)
    for event in events if isinstance(events, list) else []:
        if not isinstance(event, dict):
            continue
        messages = messages_for_event(event)
        token = event.get("replyToken")
        if messages and isinstance(token, str):
            try:
                await run_in_threadpool(reply, token, messages)
            except httpx.HTTPError as exc:
                logger.warning("line reply error: %s", type(exc).__name__)
    return JSONResponse({"received": True})
