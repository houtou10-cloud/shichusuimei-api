"""自分史鑑定の申込ページ（/jibunshi）と、支払い後の案内ページ（/jibunshi/thanks）。

支払いはStripeの支払いリンク、自分史の受け取りはGoogleフォームで行う。
URLは環境変数で設定し、未設定または形式が違う場合は「準備中」と表示する。
"""

from __future__ import annotations

import os
from html import escape

from api.day_stem_check import _CSS

PRICE = 19800
MONITOR_PRICE = 9800
MONITOR_SEATS = 5
DELIVERY_DAYS = 14
MONTHLY_LIMIT = 4
KEEP_DAYS = 30

PAYMENT_ENV = "JIBUNSHI_PAYMENT_URL"
MONITOR_PAYMENT_ENV = "JIBUNSHI_MONITOR_PAYMENT_URL"
FORM_ENV = "JIBUNSHI_FORM_URL"

_PAYMENT_PREFIXES = ("https://buy.stripe.com/",)
_FORM_PREFIXES = ("https://docs.google.com/forms/", "https://forms.gle/")

DESCRIPTION = (
    "送っていただいた自分史を、命式の持ち星と10年ごとの大運に重ねて読み、"
    f"あなた専用の動画とPDFでお届けする鑑定です。{PRICE:,}円（税込）・買い切り。"
)

PRE_SUPPORT = (
    '<section class="box support-first" aria-label="相談窓口">'
    "<h2>お申し込みの前に</h2>"
    "<p>いま、ひとりで抱えきれないほどつらいときは、鑑定より先に、話を聞いてくれる人や場所に連絡してください。"
    "自分史を書くことが、つらい記憶を思い出すきっかけになることもあります。</p>"
    '<p class="tel">よりそいホットライン <a href="tel:0120279338">0120-279-338</a>（24時間・無料）</p>'
    '<p class="tel">いのちの電話 <a href="tel:0570783556">0570-783-556</a></p>'
    '<p><a href="https://www.mhlw.go.jp/mamorouyokokoro/" target="_blank" rel="noopener noreferrer">まもろうよ こころ（厚生労働省）</a>では、電話やSNSで相談できる窓口を探せます。</p>'
    "</section>"
)


def _env_url(name: str, prefixes: tuple[str, ...]) -> str:
    value = os.getenv(name, "").strip()
    if not value.startswith(prefixes) or any(ch in value for ch in "\"'<> "):
        return ""
    return value


def payment_url() -> str:
    return _env_url(PAYMENT_ENV, _PAYMENT_PREFIXES)


def monitor_payment_url() -> str:
    return _env_url(MONITOR_PAYMENT_ENV, _PAYMENT_PREFIXES)


def form_url() -> str:
    return _env_url(FORM_ENV, _FORM_PREFIXES)


def _document(body: str, robots: str, title: str) -> str:
    return (
        '<!DOCTYPE html><html lang="ja"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        f"{robots}<title>{title}｜八雲式 四柱推命</title>{_CSS}</head><body>"
        '<header class="head">八雲式 四柱推命</header>'
        f"<main>{body}"
        '<p class="support">つらいときは、ひとりで抱えずに相談してください。よりそいホットライン 0120-279-338（24時間・無料）／いのちの電話 0570-783-556</p>'
        '</main><footer><a href="/terms">利用規約</a><a href="/privacy">プライバシーポリシー</a><a href="/legal">特商法表示</a></footer>'
        "</body></html>"
    )


def _purchase_box() -> str:
    regular = payment_url()
    monitor = monitor_payment_url()
    if not regular and not monitor:
        return (
            '<section class="box" id="apply"><h2>お申し込み</h2>'
            "<p><strong>現在、受付の準備中です。</strong>受付を始めたら、公式LINEでお知らせします。</p>"
            '<a class="line-btn" href="https://lin.ee/oeoF4hI" target="_blank" rel="noopener noreferrer">公式LINEに登録する（無料）</a>'
            "</section>"
        )
    buttons = ""
    if monitor:
        buttons += (
            f'<a class="cta" href="{escape(monitor, quote=True)}" rel="noopener noreferrer">モニター価格で申し込む（{MONITOR_PRICE:,}円）</a>'
            f'<p class="note">最初の{MONITOR_SEATS}名さま限定です。お届けのあとに、感想をお願いします（掲載するのは、了承をいただいた場合だけです）。定員に達すると、このボタンは表示されなくなります。</p>'
        )
    if regular:
        buttons += f'<a class="cta" href="{escape(regular, quote=True)}" rel="noopener noreferrer">申し込む（{PRICE:,}円）</a>'
    return (
        '<section class="box" id="apply"><h2>お申し込み</h2>'
        f"{buttons}"
        '<p class="note">Stripeの安全な決済画面へ移動します。支払いが終わると、自分史を送るフォームのご案内が表示されます。</p>'
        '<p class="note">お申し込みをもって、<a href="/terms">利用規約</a>と<a href="/privacy">プライバシーポリシー</a>に同意したものとします。'
        f"受付は月{MONTHLY_LIMIT}件までです。上限に達した月は、ボタンを外して受付を止めます。</p>"
        "</section>"
    )


def render_page(robots: str) -> str:
    body = (
        '<section class="box"><p class="eyebrow">LIFE STORY READING</p>'
        "<h1>八雲式 自分史鑑定</h1>"
        "<p><strong>持ち星と10年の季節で、あなたの人生を読み直す。</strong></p>"
        "<p>送っていただいた自分史を、命式の「持ち星」と、10年ごとに巡る「大運」に重ねて読み、"
        "<strong>あなた専用の動画（約8分）</strong>と<strong>PDF（A4で8〜10ページ）</strong>でお届けします。</p>"
        f'<p class="question">{PRICE:,}円（税込）・買い切り</p>'
        f'<p class="note">自分史を受け取ってから{DELIVERY_DAYS}日以内にお届けします。継続課金はありません。</p>'
        '<a class="sub" href="#apply">お申し込みへ</a>'
        "</section>"
        + PRE_SUPPORT
        + '<section class="box"><h2>このような方へ</h2><ul class="stars">'
        "<li>これまでの遠回りに、意味があったのかを考えたい</li>"
        "<li>自分の持ち星（生まれ持った力のヒント）を、自分の経験と重ねて知りたい</li>"
        "<li>あの時期がどんな「季節」だったのかを、静かに読み直したい</li>"
        "<li>占いの言葉に振り回されず、自分で考える材料がほしい</li>"
        "</ul></section>"
        '<section class="box"><h2>お届けするもの</h2><ul class="stars">'
        "<li><strong>あなた専用の動画（約8分）</strong>：命式、持ち星、大運と自分史の重なり、今の大運、ふり返りの問い。読み上げの声つき。</li>"
        "<li><strong>PDF（A4で8〜10ページ）</strong>：動画の内容に、命式の表、大運の表、自分史と大運を並べた年表を加えたもの。</li>"
        "<li>お届けは、Googleドライブの共有リンクです。お申し込みのメールアドレスの方だけが見られる設定にします。</li>"
        "</ul></section>"
        '<section class="box"><h2>お申し込みからお届けまで</h2><ol class="stars">'
        "<li>このページの内容と、利用規約を確認する</li>"
        "<li>Stripeでお支払い</li>"
        "<li>表示されるフォームから、生年月日・出生時刻（分からなくても大丈夫です）・出生地・自分史を送る</li>"
        "<li>運営者が内容を確認してから、鑑定を始めます</li>"
        f"<li>自分史を受け取ってから{DELIVERY_DAYS}日以内に、動画とPDFをお届けします</li>"
        "</ol>"
        "<p class=\"note\">自分史は、年ごとに1行ずつ、できごとと、そのとき感じたことを書いてください（上限2万字）。うまくいかなかったことも、書ける範囲で大丈夫です。取り上げてほしくない時期や話題は、フォームで教えてください。</p>"
        "</section>"
        '<section class="box"><h2>大切にしていること</h2><div class="concern">'
        "<p>命式は規則どおりに計算し、生まれた時刻が分からないなどで判定が決まらないところは「保留」とお伝えします。</p>"
        "<p>自分史のできごとの理由を、命式で決めつけません。「重ねて読むことができる」ところまでをお伝えします。"
        "将来の時期を言い当てたり、転職・独立・結婚・離婚などを勧めたりはしません。</p>"
        "<p>病気、借金、ご家族の死、自殺に関わるできごとは、命式と結びつけて読みません。ほかの方（ご家族、元恋人、同僚など）の名前は、動画とPDFに入れません。</p>"
        "<p>霊視など霊的な力による鑑定ではありません。魂の自然、魂の季節といった言葉は、自分を見つめるための「たとえ」として使います。結果や収入などを保証するものではありません。</p>"
        "</div></section>"
        '<section class="box"><h2>よくある質問</h2>'
        "<p><strong>出生時刻が分からなくても申し込めますか？</strong><br>申し込めます。時刻によって変わるところは「保留」として、変わらないところを中心に読みます。</p>"
        "<p><strong>キャンセルや返金はできますか？</strong><br>鑑定の作業を始める前なら、全額を返金します。作業を始めたあとは、お申し込みの方のご都合による返金はお受けしていません。"
        f"こちらの事情で{DELIVERY_DAYS}日以内にお届けできない場合や、内容を確認したうえで鑑定を見合わせた場合は、全額を返金します。</p>"
        "<p><strong>送った自分史はどうなりますか？</strong><br>"
        f"鑑定のためだけに使い、お届けしてから{KEEP_DAYS}日後に、受け取った自分史と作ったファイルを削除します。"
        "台本の下書きを作るときに、AI（Anthropic社のClaude）で処理します。動画やPDFを、許可なく公開したり、ほかに使ったりすることはありません。</p>"
        "<p><strong>何歳から申し込めますか？</strong><br>18歳以上の方が対象です。</p>"
        "</section>"
        + _purchase_box()
    )
    return _document(body, robots, "自分史鑑定")


def render_thanks(robots: str) -> str:
    url = form_url()
    if url:
        action = (
            f'<a class="cta" href="{escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">自分史を送るフォームを開く</a>'
            "<p class=\"note\">フォームには、お支払いのときと同じメールアドレスを入力してください。お支払いの確認に使います。</p>"
        )
    else:
        action = "<p><strong>フォームの準備中です。</strong>お支払いのメールアドレスに、運営者からフォームのご案内をお送りします。</p>"
    body = (
        '<section class="box"><p class="eyebrow">THANK YOU</p>'
        "<h1>お申し込みありがとうございます</h1>"
        "<p>次に、自分史を送ってください。</p>"
        f"{action}"
        "<ul class=\"stars\">"
        "<li>自分史は、年ごとに1行ずつ。できごとと、そのとき感じたことを書いてください（上限2万字）。</li>"
        "<li>書きながらつらくなったときは、無理に続けないでください。書けたところまでで大丈夫です。</li>"
        f"<li>運営者が内容を確認してから鑑定を始め、受け取ってから{DELIVERY_DAYS}日以内にお届けします。</li>"
        "</ul>"
        '<p class="note">フォームの送信前なら、キャンセルして全額を返金できます。<a href="https://form.os7.biz/f/be4d264a/" target="_blank" rel="noopener noreferrer">お問い合わせフォーム</a>からご連絡ください。</p>'
        "</section>"
    )
    return _document(body, robots, "お申し込みありがとうございます")
