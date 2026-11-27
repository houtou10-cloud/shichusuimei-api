"""人生設計書プログラム（1か月目）の申込ページ（/jibunshi）と、支払い後の案内ページ（/jibunshi/thanks）。

支払いはStripeの支払いリンク、自分史の受け取りはGoogleフォームで行う。
URLは環境変数で設定し、未設定または形式が違う場合は「準備中」と表示する。
"""

from __future__ import annotations

import os
from html import escape

from api.day_stem_check import _CSS

PRICE = 25000
CONTINUE_PRICE = 50000
CONTINUE_DAYS = 30
DELIVERY_DAYS = 14
MONTHLY_LIMIT = 4
KEEP_DAYS = 30

PAYMENT_ENV = "JIBUNSHI_PAYMENT_URL"
FORM_ENV = "JIBUNSHI_FORM_URL"

_PAYMENT_PREFIXES = ("https://buy.stripe.com/",)
_FORM_PREFIXES = ("https://docs.google.com/forms/", "https://forms.gle/")

DESCRIPTION = (
    "人生設計書プログラム（3か月）の1か月目。送っていただいた自分史を、命式の持ち星と10年ごとの大運に重ねて読み、"
    f"あなた専用の動画とPDFでお届けする鑑定です。{PRICE:,}円（税込）。続ける方は、残り{CONTINUE_PRICE:,}円で2か月目・3か月目に進めます。"
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


# 見本：八雲本人の1か月目（docs/products/jinsei_sekkei/sample_yakumo/1kagetsume.md）から抜き出したもの。
# 誕生日と命式の表は出さない。結婚・お金・病気・死に関わる年は選ばない。
_SAMPLE_YEARS = (
    ("2006年・22歳", "丙戌（傷官）", "夢を「太陽電池で環境問題を解決する」と言い切る", "外に出す星（傷官）の年。丙は月柱の辛と干合"),
    ("2007年・23歳", "丁亥（食神）", "大学院に落ち、内定をもらう。卒業論文を書き上げる", "書く星（食神）の年。亥は日柱の巳と冲"),
    ("2012年・28歳", "壬辰（印綬）", "初めて四柱推命の鑑定を受ける。「28歳で、やっと人生の目標が定まった」", "壬は時柱の丁（食神）と干合。学びの星と書く星が手をつなぐ"),
    ("2016年・32歳", "丙申（傷官）", "「32歳で完敗した」。「日記をPDFにしてネットで売ろう」", "丙は月柱の辛と干合。申は日柱の巳と支合"),
    ("2026年・42歳", "丙午（傷官）", "八雲式四柱推命が生まれる。日記の本を出す", "丙は月柱の辛と干合。午は月柱の未と支合、年柱の子と冲"),
)

SAMPLE = (
    '<section class="box" id="sample"><h2>見本　八雲の1か月目から（一部）</h2>'
    '<p class="note">運営者の八雲が、自分の日記を自分史として送ったつもりで作った見本の一部です。お客様のものではありません。'
    "お届けするPDFでは、この表が19歳から今年まで、1年ずつ続きます。</p>"
    '<h3>年ごとの読み直し（5年分を抜き出し）</h3><ul class="stars">'
    + "".join(
        f"<li><strong>{year}　{luck}</strong><br>その年のあなた：{event}<br>"
        f'<span class="note">命式から見ると：{reading}</span></li>'
        for year, luck, event, reading in _SAMPLE_YEARS
    )
    + "</ul>"
    "<h3>十年ごとに巡る同じ星</h3>"
    "<p><strong>傷官（丙）の年　2006・2016・2026</strong><br>夢を言い切る／「32歳で完敗した」と言い切る／八雲式四柱推命に名前を付ける</p>"
    '<div class="concern"><p>星が同じことをさせた、とは読みません。十年たっても、あなたが同じところで迷い、同じところで決めてきた、ということです。</p>'
    "<p>ただ、十年前と同じ星の年に、あなたは十年前より少しだけ先へ進んでいます。2006年に言い切ったのは夢でした。"
    "2016年に言い切ったのは自分の負けでした。2026年に言い切ったのは、自分の仕事の名前でした。</p></div>"
    "<h3>転機の読み直し　大学院に落ちた年（2007年・23歳）</h3>"
    '<div class="concern"><p>この年の年運は丁亥です。丁は、あなたの格局を決めている食神。亥は、日柱の巳とぶつかる「冲」の関係にあります。'
    "冲は、足元が揺さぶられ、それまでの場所から動かされる形です。</p>"
    "<p>9年後、32歳のあなたは、こう書きました。「もし、あの時大学院に行っていたら、自分はいろんなことに挑戦することはなかっただろう」</p>"
    "<p>学問の道は閉じましたが、学ぶことはやめませんでした。</p></div>"
    '<p class="note">できごとの理由を、命式で決めつけてはいません。命式と、あなたが書いた言葉を並べて、重ねて読めるところまでをお伝えします。</p>'
    "<p>見本の全体（3か月分と自分史、73ページ）は、公式LINEで「見本」と送ると見られます。</p>"
    '<a class="line-btn" href="https://lin.ee/oeoF4hI" target="_blank" rel="noopener noreferrer">公式LINEで見本の全体を見る（無料）</a>'
    "</section>"
)


def _env_url(name: str, prefixes: tuple[str, ...]) -> str:
    value = os.getenv(name, "").strip()
    if not value.startswith(prefixes) or any(ch in value for ch in "\"'<> "):
        return ""
    return value


def payment_url() -> str:
    return _env_url(PAYMENT_ENV, _PAYMENT_PREFIXES)


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
    if not regular:
        return (
            '<section class="box" id="apply"><h2>お申し込み</h2>'
            "<p><strong>現在、受付の準備中です。</strong>受付を始めたら、公式LINEでお知らせします。</p>"
            '<a class="line-btn" href="https://lin.ee/oeoF4hI" target="_blank" rel="noopener noreferrer">公式LINEに登録する（無料）</a>'
            "</section>"
        )
    return (
        '<section class="box" id="apply"><h2>お申し込み</h2>'
        f'<a class="cta" href="{escape(regular, quote=True)}" rel="noopener noreferrer">申し込む（{PRICE:,}円）</a>'
        '<p class="note">Stripeの安全な決済画面へ移動します。支払いが終わると、自分史を送るフォームのご案内が表示されます。</p>'
        '<p class="note">お申し込みをもって、<a href="/terms">利用規約</a>と<a href="/privacy">プライバシーポリシー</a>に同意したものとします。'
        f"受付は月{MONTHLY_LIMIT}件までです。上限に達した月は、ボタンを外して受付を止めます。</p>"
        "</section>"
    )


def render_page(robots: str) -> str:
    body = (
        '<section class="box"><p class="eyebrow">LIFE PLAN PROGRAM</p>'
        "<h1>八雲式 人生設計書プログラム</h1>"
        "<p><strong>これまでの人生を読み直して、これからの20年を設計する。</strong></p>"
        "<p>「このままでいいのか」と思いながら、働いてきた方へ。3か月で、あなたの命式とこれまでの人生から、1冊の「人生設計書」をつくります。</p>"
        '<ul class="stars">'
        "<li><strong>1か月目</strong>：これまでの人生を、1年ずつ年運と並べて読み直す。転機3つは、持ち星と10年ごとの大運で深く読む（動画 約15〜17分・PDF A4で14〜18ページ）</li>"
        "<li><strong>2か月目『取扱説明書』</strong>：あなたの大黒柱、仕事で力が出る場面と出ない場面、手放してよいもの</li>"
        "<li><strong>3か月目『未来設計書』</strong>：これからの20年の大運と節目の年、最初の1年の計画、五つの指針。年運カレンダー（10年分）と製本版（郵送）つき</li>"
        "</ul>"
        "<p>このページは<strong>1か月目</strong>のお申し込みです。</p>"
        f'<p class="question">{PRICE:,}円（税込）</p>'
        f'<p class="note">自分史を受け取ってから{DELIVERY_DAYS}日以内にお届けします。1か月目だけで終えることもできます。続けるかどうかは、お届けのあとに選べます。自動で請求が続くことはありません。</p>'
        '<a class="sub" href="#apply">お申し込みへ</a>'
        "</section>"
        + PRE_SUPPORT
        + '<section class="box"><h2>このような方へ</h2><ul class="stars">'
        "<li>仕事は続けてきたけれど、「このままでいいのか」が消えない</li>"
        "<li>転職や副業を考えては、決めきれずに何年もたっている</li>"
        "<li>資格や教材にお金を使ってきたが、何が自分に合うのか分からない</li>"
        "<li>40代からの後半戦を、何を軸に生きるか考え始めた</li>"
        "<li>占いの言葉に振り回されず、自分で決めるための材料がほしい</li>"
        "</ul></section>"
        '<section class="box"><h2>お届けするもの</h2><ul class="stars">'
        "<li><strong>あなた専用の動画（約15〜17分）</strong>：命式、持ち星、人生のグラフと10年ごとの大運、十年ごとに巡る同じ星、転機3つの読み直し、今の大運、ふり返りの問い。読み上げの声つき。</li>"
        "<li><strong>PDF（A4で14〜18ページ）</strong>：動画の内容に、命式の表、大運の表、あなたの人生のグラフ、八雲からの手紙を加えたもの。厚みは、書いていただく量によって変わります。</li>"
        "<li><strong>年ごとの読み直し</strong>（PDFの中）：19歳から今年まで（最大30年）、1年ずつ、その年の年運とあなたの言葉を並べた表。年運は10年でひと回りするので、「十年前の同じ星の年」とも読み比べます。</li>"
        "<li><strong>文章での質問</strong>：お届けのあと、1回まで文章で質問できます。</li>"
        "<li>お届けは、Googleドライブの共有リンクです。お申し込みのメールアドレスの方だけが見られる設定にします。</li>"
        "</ul>"
        '<a class="sub" href="#sample">見本を見る（八雲の1か月目から）</a>'
        "</section>"
        + SAMPLE
        + ""
        '<section class="box"><h2>お申し込みからお届けまで</h2><ol class="stars">'
        "<li>このページの内容と、利用規約を確認する</li>"
        "<li>Stripeでお支払い</li>"
        "<li>表示されるフォームから、生年月日・出生時刻（分からなくても大丈夫です）・出生地・自分史を送る</li>"
        "<li>運営者が内容を確認してから、鑑定を始めます</li>"
        f"<li>自分史を受け取ってから{DELIVERY_DAYS}日以内に、動画とPDFをお届けします</li>"
        "</ol>"
        "<p class=\"note\">自分史は、年代ごとの質問と、覚えている年ごとのできごと、仕事のことの質問に答える形で書いていただきます（目安は90〜130分）。年ごとのできごとは、覚えている年だけで大丈夫です。一度に書かなくて大丈夫です。"
        "書きたくない年代や質問は、空欄のままで構いません。書いていてつらくなったら、そこでやめてください。書けたところまでで読みます。取り上げてほしくない時期や話題は、フォームで教えてください。</p>"
        "</section>"
        '<section class="box"><h2>2か月目・3か月目に続ける場合</h2><ul class="stars">'
        f"<li>1か月目のお届けから{CONTINUE_DAYS}日以内に、残り{CONTINUE_PRICE:,}円（税込）をお支払いいただくと、2か月目に進みます。お支払いのご案内は、1か月目をお届けするときにメールでお送りします。</li>"
        "<li><strong>2か月目『取扱説明書』</strong>：あなたの大黒柱、仕事で力が出る場面と出ない場面、続くもの・続かないもの、手放してよいもの、調子が落ちたときの対処。PDFと解説動画でお届けします。</li>"
        "<li><strong>3か月目『未来設計書』</strong>：これからの20年の大運と節目の年、最初の1年の計画、五つの指針。迷っている働き方の道があれば、それぞれで得られるもの・手放すものを並べます（どの道がよいかは、こちらからは言いません）。"
        "年運カレンダー（10年分）と、1〜3か月目をまとめた製本版（郵送）もお届けします。</li>"
        "<li>2か月目は入金を確かめてから約1か月、3か月目はその約1か月後にお届けします。終わってから1年後に、翌年の流年レポートと、一度だけの質問をお届けします。</li>"
        "<li>どの月も、やり取りは文章と、録画した解説だけです。通話はしません。</li>"
        "</ul></section>"
        '<section class="box"><h2>大切にしていること</h2><div class="concern">'
        "<p>命式は規則どおりに計算し、生まれた時刻が分からないなどで判定が決まらないところは「保留」とお伝えします。</p>"
        "<p>自分史のできごとの理由を、命式で決めつけません。「重ねて読むことができる」ところまでをお伝えします。"
        "将来の時期を言い当てたり、転職・独立・結婚・離婚などを勧めたりはしません。</p>"
        "<p>人生設計書は、あなたが自分で決めるための材料を、1冊にまとめるものです。決めるのは、あなたです。</p>"
        "<p>病気、借金、ご家族の死、自殺に関わるできごとは、命式と結びつけて読みません。ほかの方（ご家族、元恋人、同僚など）の名前は、動画とPDFに入れません。</p>"
        "<p>霊視など霊的な力による鑑定ではありません。魂の自然、魂の季節といった言葉は、自分を見つめるための「たとえ」として使います。結果や収入などを保証するものではありません。</p>"
        "</div></section>"
        '<section class="box"><h2>よくある質問</h2>'
        "<p><strong>出生時刻が分からなくても申し込めますか？</strong><br>申し込めます。時刻によって変わるところは「保留」として、変わらないところを中心に読みます。</p>"
        "<p><strong>仕事の悩みに、答えを出してもらえますか？</strong><br>転職する・しないなど、どちらがよいかをこちらから決めることはしません。"
        "あなたの持ち星と10年ごとの流れ、これまでの人生の中で続いてきたものを並べて、あなたが決めるための材料をお渡しします。</p>"
        "<p><strong>文章を書くのが苦手です。</strong><br>短い言葉で大丈夫です。書けない質問は空欄のままで構いません。書いていただいた言葉は、レポートの中で、そのまま引用させていただくことがあります。</p>"
        "<p><strong>キャンセルや返金はできますか？</strong><br>鑑定の作業を始める前なら、全額を返金します。作業を始めたあとは、お申し込みの方のご都合による返金はお受けしていません。"
        f"こちらの事情で{DELIVERY_DAYS}日以内にお届けできない場合や、内容を確認したうえで鑑定を見合わせた場合は、全額を返金します。"
        f"2か月目・3か月目の{CONTINUE_PRICE:,}円は、2か月目の作業を始める前なら全額を返金します。始めたあとは、ご都合による返金はお受けしていません。</p>"
        "<p><strong>送った自分史はどうなりますか？</strong><br>"
        f"鑑定のためだけに使い、お届けしてから{KEEP_DAYS}日後に、受け取った自分史と作ったファイルを削除します。"
        f"2か月目・3か月目に続ける方は、3か月目をお届けしてから{KEEP_DAYS}日後に削除します（1年後のフォローのため、生年月日・出生時刻・出生地だけは、そのフォローをお届けするまで保管します）。"
        "台本の下書きを作るときに、AI（Anthropic社のClaude）で処理します。動画やPDFを、許可なく公開したり、ほかに使ったりすることはありません。</p>"
        "<p><strong>何歳から申し込めますか？</strong><br>18歳以上の方が対象です。</p>"
        "</section>"
        + _purchase_box()
    )
    return _document(body, robots, "人生設計書プログラム")


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
        "<li>自分史は、フォームの案内にそって、年代ごとの質問と、仕事のことの質問に答えてください。書きたくない質問は空欄で大丈夫です。</li>"
        "<li>書きながらつらくなったときは、無理に続けないでください。書けたところまでで大丈夫です。</li>"
        f"<li>運営者が内容を確認してから鑑定を始め、受け取ってから{DELIVERY_DAYS}日以内にお届けします。</li>"
        "</ul>"
        '<p class="note">フォームの送信前なら、キャンセルして全額を返金できます。<a href="https://form.os7.biz/f/be4d264a/" target="_blank" rel="noopener noreferrer">お問い合わせフォーム</a>からご連絡ください。</p>'
        "</section>"
    )
    return _document(body, robots, "お申し込みありがとうございます")
