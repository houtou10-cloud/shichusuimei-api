"""公式LINEの無料日干診断（/line/webhook）。"""

import base64
import hashlib
import hmac
import json
from datetime import date

import pytest
from fastapi.testclient import TestClient

from api import line_bot
from api.day_stem_check import CONCERN_NOTES
from main import app

CLIENT = TestClient(app)
SECRET = "test-channel-secret"


@pytest.fixture
def sent(monkeypatch):
    monkeypatch.setenv("LINE_CHANNEL_SECRET", SECRET)
    monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "test-token")
    replies = []
    monkeypatch.setattr(line_bot, "reply", lambda token, messages: replies.append((token, messages)))
    return replies


def _post(events, secret=SECRET):
    body = json.dumps({"events": events}, ensure_ascii=False).encode("utf-8")
    signature = base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()
    return CLIENT.post("/line/webhook", content=body, headers={"x-line-signature": signature, "content-type": "application/json"})


def _texts(replies):
    return "\n".join(m["text"] for _, messages in replies for m in messages)


def test_not_configured_returns_503(monkeypatch):
    monkeypatch.delenv("LINE_CHANNEL_SECRET", raising=False)
    monkeypatch.delenv("LINE_CHANNEL_ACCESS_TOKEN", raising=False)
    assert CLIENT.post("/line/webhook", content=b"{}").status_code == 503


def test_bad_signature_is_rejected(sent):
    assert _post([{"type": "follow", "replyToken": "r"}], secret="wrong").status_code == 400
    assert sent == []


def test_follow_sends_welcome(sent):
    assert _post([{"type": "follow", "replyToken": "r1"}]).status_code == 200
    assert sent[0][0] == "r1"
    assert "友だち追加ありがとうございます" in _texts(sent)


@pytest.mark.parametrize("text", ["1985/10/13", "1985年10月13日", "１９８５－１０－１３", "19851013"])
def test_birth_date_message_returns_day_stem_and_concern_buttons(sent, text):
    _post([{"type": "message", "replyToken": "r", "message": {"type": "text", "text": text}}])
    messages = sent[0][1]
    assert "あなたの日干は「乙」" in messages[0]["text"]
    labels = [item["action"]["label"] for item in messages[2]["quickReply"]["items"]]
    assert "年の柱：比肩" in messages[1]["text"] and "月の柱：傷官" in messages[1]["text"]
    assert labels == ["仕事", "人間関係", "恋愛・結婚", "自分のこと", "とてもつらい"]


def test_same_star_in_year_and_month_is_shown_once(sent):
    _post([{"type": "message", "replyToken": "r", "message": {"type": "text", "text": "1966/8/27"}}])
    holding = sent[0][1][1]["text"]
    assert "年の柱・月の柱：偏印" in holding
    assert holding.count("日干を生じる星です") == 1


@pytest.mark.parametrize("concern, shown, hidden", [
    ("work", "/academy?src=line", "/jibunshi"),
    ("relation", "/academy?src=line", "/jibunshi"),
    ("self", "/jibunshi?src=line", "/academy"),
])
def test_concern_reply_offers_at_most_two_links(sent, concern, shown, hidden):
    _post([{"type": "postback", "replyToken": "r", "postback": {"data": f"concern={concern}&birth_date=1985-10-13"}}])
    text = _texts(sent)
    assert "/career-reading?src=line" in text and shown in text
    assert hidden not in text


def test_preview_titles_name_each_page(monkeypatch):
    from api import customer_routes
    monkeypatch.setenv("CUSTOMER_PUBLIC_BASE_URL", "https://app.example.test")
    monkeypatch.setattr(customer_routes, "checkout_mode", lambda: "live")
    assert 'og:title" content="人生設計書プログラム｜八雲式 四柱推命"' in CLIENT.get("/jibunshi").text
    assert 'og:title" content="八雲式 四柱推命鑑定"' in CLIENT.get("/career-reading").text
    academy = CLIENT.get("/academy").text
    assert 'og:title" content="八雲式 四柱推命Academy"' in academy
    assert 'og:description" content="四柱推命を基礎から実践まで' in academy


def test_unreadable_message_returns_help(sent):
    _post([{"type": "message", "replyToken": "r", "message": {"type": "text", "text": "こんにちは"}}])
    assert "生年月日を、次のように送ってください" in _texts(sent)


def test_crisis_words_return_support_without_sales(sent):
    _post([{"type": "message", "replyToken": "r", "message": {"type": "text", "text": "もう死にたい 1985/10/13"}}])
    text = _texts(sent)
    assert "0120-279-338" in text
    assert "career-reading" not in text and "academy" not in text
    assert "日干" not in text


def test_concern_postback_returns_note_and_paid_link(sent):
    _post([{"type": "postback", "replyToken": "r", "postback": {"data": "concern=relation&birth_date=1985-10-13"}}])
    text = _texts(sent)
    assert CONCERN_NOTES["乙"]["relation"] in text
    assert "/career-reading?src=line" in text


def test_hard_postback_returns_support_and_invites_writing(sent):
    _post([{"type": "postback", "replyToken": "r", "postback": {"data": "concern=hard&birth_date=1985-10-13"}}])
    text = _texts(sent)
    assert "0120-279-338" in text
    assert "いまの気持ちを、このトークに書いて吐き出してください" in text
    assert "お返事は自動の一通" in text
    assert "career-reading" not in text and "academy" not in text
    assert "八雲が" not in text


def test_only_concern_type_is_logged(sent, caplog):
    caplog.set_level("INFO", logger="api.day_stem_check")
    _post([{"type": "postback", "replyToken": "r", "postback": {"data": "concern=work&birth_date=1985-10-13"}}])
    messages = [r.getMessage() for r in caplog.records if r.name == "api.day_stem_check"]
    assert messages == ["free_day_stem_check concern=work"]


def test_written_concern_gets_one_automatic_reply(sent, caplog):
    caplog.set_level("INFO", logger="api.line_bot")
    concern = "職場の人間関係がうまくいかなくて、毎日疲れています。"
    _post([{"type": "message", "replyToken": "r", "message": {"type": "text", "text": concern}}])
    text = _texts(sent)
    assert "気持ちを聞かせてくださって、ありがとうございます" in text
    assert "お返事は自動の一通" in text
    assert "career-reading" not in text and "academy" not in text
    assert "0120-279-338" in text and "mamorouyokokoro" in text
    assert "八雲が" not in text
    messages = [r.getMessage() for r in caplog.records if r.name == "api.line_bot"]
    assert messages == ["line_concern_text_received"]
    assert concern not in " ".join(r.getMessage() for r in caplog.records)


@pytest.mark.parametrize("text", ["日干診断", "こんにちは", "よろしく"])
def test_short_text_returns_help(sent, text):
    _post([{"type": "message", "replyToken": "r", "message": {"type": "text", "text": text}}])
    assert "生年月日を、次のように送ってください" in _texts(sent)


def test_concern_postback_invites_written_concern(sent):
    _post([{"type": "postback", "replyToken": "r", "postback": {"data": "concern=work&birth_date=1985-10-13"}}])
    assert "いまの悩みを、このトークに書いて送っていただくこともできます" in _texts(sent)


def test_parse_date_text_rejects_impossible_dates():
    assert line_bot.parse_date_text("1985/02/30") is None
    assert line_bot.parse_date_text("1899/12/31") is None
    assert line_bot.parse_date_text("1985/10/13") == date(1985, 10, 13)


def test_concern_postback_links_to_jibunshi(sent):
    _post([{"type": "postback", "replyToken": "r", "postback": {"data": "concern=self&birth_date=1985-10-13"}}])
    assert "/jibunshi?src=line" in _texts(sent)


@pytest.mark.parametrize("event", [
    {"type": "postback", "replyToken": "r", "postback": {"data": "concern=hard&birth_date=1985-10-13"}},
    {"type": "message", "replyToken": "r", "message": {"type": "text", "text": "職場の人間関係がうまくいかなくて、毎日疲れています。"}},
    {"type": "message", "replyToken": "r", "message": {"type": "text", "text": "死にたい"}},
])
def test_jibunshi_is_never_offered_to_people_in_pain(sent, event):
    _post([event])
    assert "jibunshi" not in _texts(sent)


@pytest.mark.parametrize("text", ["読んだ", "よんだ", "読了", "読みました！", "読み終わりました。", " 読んだ "])
def test_read_report_returns_life_bible(sent, text):
    _post([{"type": "message", "replyToken": "r", "message": {"type": "text", "text": text}}])
    reply = _texts(sent)
    assert "https://yakumo-shiki.jp/bible/" in reply
    assert "八雲の人生バイブル" in reply
    assert "生年月日を、次のように送ってください" not in reply


@pytest.mark.parametrize("text", ["本を読んだけど、仕事のことでずっと悩んでいます", "読んだ本の感想です。とても良かったです"])
def test_read_word_inside_a_longer_message_is_not_a_read_report(sent, text):
    _post([{"type": "message", "replyToken": "r", "message": {"type": "text", "text": text}}])
    assert "https://yakumo-shiki.jp/bible/" not in _texts(sent)


def test_crisis_words_win_over_read_report(sent):
    assert line_bot.is_read_report("読んだ")
    assert not line_bot.is_read_report("死にたい")


@pytest.mark.parametrize("text", ["単発鑑定", "単発鑑定！", "単発鑑定を申し込みたい"])
def test_tanpatsu_keyword_returns_questions(sent, text):
    _post([{"type": "message", "replyToken": "r", "message": {"type": "text", "text": text}}])
    messages = sent[0][1]
    assert len(messages) == 3
    assert messages[1]["text"].startswith("【単発鑑定 お申し込み】")
    assert "②生年月日（西暦）：" in messages[1]["text"]
    assert "https://yakumo-shiki.jp/tanpatsu" in messages[2]["text"]


APPLICATION = (
    "【単発鑑定 お申し込み】\n①お名前（ニックネーム可）：たろう\n②生年月日（西暦）：1985/10/13\n"
    "③出生時刻（分からなければ「不明」）：不明\n④出生地（都道府県・市区町村）：愛知県名古屋市\n⑤性別：男性\n"
    "⑥メニュー（仕事と転職／お金と副業／人生の後半戦）：仕事と転職\n⑦いちばん知りたいこと（1つ）：転職するべきか\n"
    "⑧その悩みの背景（いつごろから、何があったか）：3年前から\n⑨これまでの人生で、大きく動いた年を3つ：2008年 入社"
)


def test_tanpatsu_application_is_acknowledged_without_day_stem(sent, caplog):
    caplog.set_level("INFO")
    _post([{"type": "message", "replyToken": "r", "message": {"type": "text", "text": APPLICATION}}])
    reply = _texts(sent)
    assert "たしかに受け取りました" in reply
    assert "あなたの日干は" not in reply
    assert len(sent[0][1]) == 1
    logs = " ".join(r.getMessage() for r in caplog.records)
    assert "1985" not in logs and "転職するべきか" not in logs


def test_tanpatsu_application_without_header_is_recognized(sent):
    text = APPLICATION.replace("【単発鑑定 お申し込み】\n", "単発鑑定の申し込みです\n")
    _post([{"type": "message", "replyToken": "r", "message": {"type": "text", "text": text}}])
    assert "たしかに受け取りました" in _texts(sent)


def test_crisis_words_in_application_return_support_first(sent):
    _post([{"type": "message", "replyToken": "r", "message": {"type": "text", "text": APPLICATION + "\n死にたいと思うことがある"}}])
    reply = _texts(sent)
    assert "たしかに受け取りました" not in reply
    assert "0120-279-338" in reply


def test_birth_date_alone_still_returns_day_stem(sent):
    _post([{"type": "message", "replyToken": "r", "message": {"type": "text", "text": "1985/10/13"}}])
    assert "あなたの日干は" in _texts(sent)
