"""無料の日干診断（/nikkan）。生年月日から日干を出し、八雲式の読み物の日干の文章を見せる。

鑑定（有料）の入口として置く無料ページ。日干だけを見る読み物で、命式全体の判定はしない。
文章は yakumo_reading_note.DAY_STEM_NOTES と、このファイルの固定の文章だけを使い、AIは使わない。
悩みの種類は任意で選んでもらい、件数を数えるためにログへ種類だけを書く（生年月日は保存しない）。
「とてもつらい」を選んだ人には、販売の案内を出さず、相談窓口を先に出す。
"""

from __future__ import annotations

from datetime import date, datetime
from html import escape
import logging

from api.yakumo_reading_note import DAY_STEM_NOTES, STEM_ELEMENT
from engine.pillars import calculate_four_pillars

logger = logging.getLogger(__name__)

MIN_DATE = date(1900, 1, 1)
STEM_YIN_YANG = {stem: ("陽" if index % 2 == 0 else "陰") for index, stem in enumerate("甲乙丙丁戊己庚辛壬癸")}

CONCERNS = {
    "work": "仕事",
    "relation": "人間関係",
    "love": "恋愛・結婚",
    "self": "自分のこと",
    "hard": "とてもつらい",
}

# 日干×悩みの一言。「とてもつらい」には一言を出さない。
CONCERN_NOTES = {
    "甲": {
        "work": "大樹は、一度根を張った場所で大きくなります。すぐに結果が見えなくても、続けてきたことが、あなたの幹を太くしています。",
        "relation": "大樹は、まっすぐなぶん、ほかの木とぶつかることもあります。まっすぐさはそのままに、枝を少しゆずる場面を選んでみてください。",
        "love": "大樹は、時間をかけて根を張る木です。関係も、急がずに育てていくほうが、あなたらしい形になりやすいでしょう。",
        "self": "迷ったときは、根に戻ってみてください。長く続けてきたことの中に、あなたらしさのヒントがあります。",
    },
    "乙": {
        "work": "草花は、まわりに合わせて形を変えながら咲きます。合わせる力は強みです。ただ、どこで咲きたいかは、自分で決めてよいのです。",
        "relation": "しなやかに受け流せるのは、草花の強さです。受け流しすぎて疲れたら、日だまりで休む時間を先に取ってください。",
        "love": "草花は、寄りそう相手がいると、伸びやかに咲きます。寄りかかりすぎず、支え合える距離を探してみてください。",
        "self": "風に揺れても、草花は折れません。揺れている今も、根はちゃんと地面をつかんでいます。",
    },
    "丙": {
        "work": "太陽は、いるだけで場を明るくします。照らす役割を抱えすぎたら、ひとつ手放しても、光は消えません。",
        "relation": "まわりを照らすあなたも、照らされてよい人です。人に頼ることを、ひとつ試してみてください。",
        "love": "太陽の明るさは、相手を元気にします。自分の気持ちも、同じ明るさで伝えてみてください。",
        "self": "沈む時間のない太陽はありません。休むことも、明日また昇るための時間です。",
    },
    "丁": {
        "work": "灯火は、近くの人の手もとを照らします。目立たなくても、あなたの働きに助けられている人がいます。",
        "relation": "灯火は、狭い範囲を深く照らします。広く付き合うより、大切な人を少しにしぼってもよいのです。",
        "love": "灯火は、そばにいる人を静かに温めます。言葉にしにくい思いも、小さく伝えることから始めてみてください。",
        "self": "灯火は、燃料があってこそ燃え続けます。あなたの心を育ててくれるものを、そばに置いてください。",
    },
    "戊": {
        "work": "山は、まわりのよりどころになります。抱えすぎたときは、山の上から見渡すように、優先順位を見直してみてください。",
        "relation": "山は動かないぶん、人に頼られます。全部を受け止めなくても、山は山のままです。",
        "love": "どっしりした安心感は、あなたの魅力です。ときには自分から一歩動いてみるのも、山の新しい景色です。",
        "self": "山は、季節ごとに表情を変えます。変わらない部分と、変わってよい部分を、分けて考えてみてください。",
    },
    "己": {
        "work": "田畑の土は、じっくり育てる力を持っています。成果が出るまでの時間も、あなたの仕事の一部です。",
        "relation": "受け入れる力が大きいぶん、疲れもたまりやすい土です。土を休ませるように、何もしない日をつくってください。",
        "love": "土は、種を受け入れて育てます。相手を育てるだけでなく、自分が大切にしてもらうことも忘れないでください。",
        "self": "いま育てているものは、すぐには芽を出さないかもしれません。土の中では、ちゃんと根が伸びています。",
    },
    "庚": {
        "work": "鉱石は、鍛えられるほど形が定まります。今の大変さは、あなたの刃が研がれている時間かもしれません。",
        "relation": "刃のようにまっすぐな言葉は、ときに強く届きます。伝える前に、ひと呼吸おいてみてください。",
        "love": "決めたことをやり抜く力は、関係の中でも頼もしさになります。やわらかい言葉を、ひとつ添えてみてください。",
        "self": "張りつめたときは、身のまわりを整えてみてください。区切りをつけると、気持ちも軽くなります。",
    },
    "辛": {
        "work": "宝石は、細かいところまで見分ける力を持っています。その丁寧さを、まわりは見ています。",
        "relation": "繊細な感性は、人の小さな変化に気づく力です。気づきすぎて疲れたら、自分を丁寧に扱う時間を。",
        "love": "宝石は、大切に扱われるほど光ります。あなたも、大切にされてよい人です。",
        "self": "傷つきやすさは、美しいものを見分ける感性の裏返しです。そのままの自分を、磨くように扱ってください。",
    },
    "壬": {
        "work": "大河は、広い視野で流れを読みます。目の前の細かいことより、大きな流れを見ることが得意です。",
        "relation": "大河は、多くの人を運びます。全員を運ぼうとせず、ときには淵で休んでください。",
        "love": "流れに任せる柔らかさは、あなたの魅力です。大事なところでは、行き先をはっきり伝えてみてください。",
        "self": "流れが速すぎると感じたら、立ち止まってよいのです。水辺を歩くと、心も落ち着きます。",
    },
    "癸": {
        "work": "雨露は、目立たないところで、まわりを育てます。あなたの支えで動いているものが、きっとあります。",
        "relation": "静かにうるおす力は、人を安心させます。自分の気持ちも、少しずつ言葉にしてみてください。",
        "love": "雨露は、そっと寄りそう水です。相手を思う気持ちを、小さな行動で伝えてみてください。",
        "self": "気持ちが乾いたら、雨音を聞くように、静かな時間をつくってください。ゆっくり眠ることも大切です。",
    },
}

SUPPORT_BOX = (
    '<section class="box support-first" aria-label="相談窓口">'
    "<h1>ひとりで抱えないでください</h1>"
    "<p>いま、とてもつらいのですね。教えてくれて、ありがとうございます。占いより先に、話を聞いてくれる人や場所に連絡してください。</p>"
    '<p class="tel">よりそいホットライン <a href="tel:0120279338">0120-279-338</a>（24時間・無料）</p>'
    '<p class="tel">いのちの電話 <a href="tel:0570783556">0570-783-556</a></p>'
    '<p><a href="https://www.mhlw.go.jp/mamorouyokokoro/" target="_blank" rel="noopener noreferrer">まもろうよ こころ（厚生労働省）</a>では、電話やSNSで相談できる窓口を探せます。</p>'
    "</section>"
)


class DayStemInputError(ValueError):
    pass


def parse_birth_date(value: str, today: date | None = None) -> date:
    try:
        birth = date.fromisoformat((value or "").strip())
    except ValueError:
        raise DayStemInputError("生年月日を入力してください。") from None
    if birth < MIN_DATE or birth > (today or date.today()):
        raise DayStemInputError("1900年1月1日から今日までの日付を入力してください。")
    return birth


def parse_concern(value: str) -> str:
    """選択肢にない値は「選ばなかった」として扱う。"""
    return value if value in CONCERNS else ""


def record_concern(concern: str) -> None:
    """件数の集計用。悩みの種類だけを書き、生年月日などは書かない。"""
    logger.info("free_day_stem_check concern=%s", concern or "none")


def day_stem_for(birth: date) -> str:
    """生年月日の日干。時刻が分からないので正午で計算する。"""
    return calculate_four_pillars(datetime(birth.year, birth.month, birth.day, 12))["day"]["stem"]


# 持ち星（年干・月干の通変星）に関係する事柄。講座の本の定義から、才能・仕事に関わるものだけを選ぶ。
# 劫財は事柄の一覧を確認できていないので、「日干の力になる星」という分類だけを書く。
TEN_GOD_NOTES = {
    "比肩": "日干と同じ五行・同じ陰陽の星です。関係する事柄は、独立、活動、競争、生一本。",
    "劫財": "日干と同じ五行で、日干の力になる星です。",
    "食神": "日干から生じる星です。関係する事柄は、食禄、発想、アイデア。",
    "傷官": "日干から生じる星です。関係する事柄は、技術、学芸。",
    "偏財": "日干が剋す星です。関係する事柄は、商業、仲介、活動。",
    "正財": "日干が剋す星です。関係する事柄は、商工業、慎重、規律的。",
    "偏官": "日干を剋す星です。関係する事柄は、職業、権利、勤人。",
    "正官": "日干を剋す星です。関係する事柄は、目上、職業、誠実、温和。",
    "偏印": "日干を生じる星です。関係する事柄は、芸術、自由業、機敏。",
    "印綬": "日干を生じる星です。関係する事柄は、学芸技術、理知的、名声、信用。",
}


def holding_stars(birth: date) -> tuple[list[tuple[str, str]], bool]:
    """年干・月干の通変星（持ち星）と、生まれた時刻で年や月の柱が変わる日かどうか。"""
    noon = calculate_four_pillars(datetime(birth.year, birth.month, birth.day, 12))
    stars = [(label, str(noon[key]["stem_ten_god"])) for key, label in (("year", "年の柱"), ("month", "月の柱"))]
    edges = [calculate_four_pillars(datetime(birth.year, birth.month, birth.day, h, m)) for h, m in ((0, 0), (23, 59))]
    changes = any(edge[key]["pillar"] != noon[key]["pillar"] for edge in edges for key in ("year", "month"))
    return stars, changes


HOLDING_LEAD = "持ち星は、命式にある通変星のことで、才能のヒントです。ここでは、年と月の天干から見た2つの星をお届けします。才能を言い切るものではありません。"
HOLDING_CHANGE_NOTE = "この日は季節の変わり目（節入り）にあたり、生まれた時刻によって持ち星が変わることがあります。"
HOLDING_MORE = "時の柱や地支の中の星も合わせた、命式全体の持ち星は、八雲式 四柱推命鑑定でお伝えします。"


LINE_FRIEND_URL = "https://lin.ee/oeoF4hI"


def _line_box() -> str:
    return (
        '<section class="box"><h2>公式LINEでも診断できます</h2>'
        '<p>公式LINEに登録して生年月日を送ると、日干と持ち星がトークに届きます。あとから読み返したいときに便利です（無料）。</p>'
        f'<a class="line-btn" href="{LINE_FRIEND_URL}" target="_blank" rel="noopener noreferrer">公式LINEに登録する</a></section>'
    )


def _holding_html(birth: date) -> str:
    stars, changes = holding_stars(birth)
    items = "".join(f"<li><strong>{label}：{star}</strong><br>{escape(TEN_GOD_NOTES.get(star, ''))}</li>" for label, star in stars)
    note = f'<p class="note">{HOLDING_CHANGE_NOTE}</p>' if changes else ""
    return f'<h2>あなたの持ち星</h2><p>{HOLDING_LEAD}</p><ul class="stars">{items}</ul>{note}'


def holding_text(birth: date) -> str:
    stars, changes = holding_stars(birth)
    lines = ["あなたの持ち星", HOLDING_LEAD, ""]
    for label, star in stars:
        lines += [f"{label}：{star}", TEN_GOD_NOTES.get(star, ""), ""]
    if changes:
        lines += [HOLDING_CHANGE_NOTE, ""]
    lines.append(HOLDING_MORE)
    return "\n".join(lines)


def _safe_src(value: str) -> str:
    """どの動画・投稿から来たかの目印。英数字と _ - だけを残す。"""
    return "".join(ch for ch in (value or "")[:40] if ch.isascii() and (ch.isalnum() or ch in "_-"))


_CSS = """<style>
*{box-sizing:border-box}body{margin:0;background:#f4ede4;color:#302820;font-family:"Yu Mincho","Hiragino Mincho ProN","Noto Serif JP",serif;line-height:1.8}
.head{padding:16px 22px;background:#fffdfa;border-bottom:1px solid #dfd1c2;color:#5d3b25;font-weight:700;letter-spacing:.14em}
main{width:min(720px,calc(100% - 32px));margin:28px auto 48px}.box{padding:28px 26px;background:#fffdfa;border:1px solid #dfd1c2;border-radius:14px;margin-bottom:18px}
h1{color:#4d3322;font-size:clamp(1.5rem,5vw,2.1rem);line-height:1.4;margin:.2rem 0 1rem}h2{color:#4d3322;font-size:1.2rem}.eyebrow{color:#9a6a35;font-weight:700;letter-spacing:.18em;margin:0}
label{display:block;font-weight:700;margin-bottom:.4rem}input[type=date]{width:100%;font:inherit;padding:12px;border:1px solid #cdb9a4;border-radius:8px;background:#fff}
fieldset{border:0;padding:0;margin:1.2rem 0 0}legend{font-weight:700;margin-bottom:.4rem}.choices{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.choices label{font-weight:400;margin:0;padding:10px 12px;border:1px solid #cdb9a4;border-radius:8px;background:#fff;cursor:pointer}
.cta{display:block;width:100%;margin-top:1rem;border:0;border-radius:9px;padding:14px 20px;background:linear-gradient(120deg,#6b4328,#9a6a35);color:#fff;text-align:center;text-decoration:none;font:700 1rem inherit;cursor:pointer}
.sub{display:block;margin-top:.8rem;text-align:center;color:#5d3b25}.error{color:#a33a35;font-weight:700}.note{color:#6f6257;font-size:.9rem}.question{font-size:1.15rem;font-weight:700;color:#5d3b25}
.line-btn{display:block;margin-top:1rem;border-radius:9px;padding:14px 20px;background:#06c755;color:#fff;text-align:center;text-decoration:none;font-weight:700}.stars{padding-left:1.2rem}.stars li{margin-bottom:.6rem}.concern{border-left:5px solid #9a6a35;background:#fffaf1;padding:14px 16px}.support-first{border:2px solid #9a6a35}.tel{font-size:1.15rem;font-weight:700}.tel a{color:#5d3b25}
.support{font-size:.9rem;color:#6f6257;border-top:1px solid #dfd1c2;padding-top:1rem}footer{text-align:center;font-size:.85rem;padding:0 16px 32px}footer a{margin:0 .5rem;color:#5d3b25}
</style>"""


def _document(body: str, robots: str) -> str:
    return (
        '<!DOCTYPE html><html lang="ja"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        f'{robots}<title>無料の日干診断｜八雲式 四柱推命</title>{_CSS}</head><body>'
        '<header class="head">八雲式 四柱推命</header>'
        f'<main>{body}'
        '<p class="support">つらいときは、ひとりで抱えずに相談してください。よりそいホットライン 0120-279-338（24時間・無料）／いのちの電話 0570-783-556</p>'
        '</main><footer><a href="/terms">利用規約</a><a href="/privacy">プライバシーポリシー</a><a href="/legal">特商法表示</a></footer>'
        '</body></html>'
    )


def _concern_fieldset(selected: str) -> str:
    options = "".join(
        f'<label><input type="radio" name="concern" value="{key}"{" checked" if key == selected else ""}> {label}</label>'
        for key, label in CONCERNS.items()
    )
    return f'<fieldset><legend>いまの悩みに近いもの（選ばなくても調べられます）</legend><div class="choices">{options}</div></fieldset>'


def render_form(robots: str, src: str = "", value: str = "", error: str = "", concern: str = "") -> str:
    error_html = f'<p class="error" role="alert">{escape(error)}</p>' if error else ""
    return _document(
        '<section class="box"><p class="eyebrow">FREE CHECK</p><h1>あなたの日干を、無料で調べる</h1>'
        '<p>日干は、生まれた日の天干で、四柱推命で「あなた自身」を表す文字です。生年月日を入れると、日干と、その自然のイメージが分かります。</p>'
        f'{error_html}<form method="post" action="/nikkan">'
        f'<input type="hidden" name="src" value="{escape(_safe_src(src), quote=True)}">'
        f'<label for="birth_date">生年月日</label><input id="birth_date" name="birth_date" type="date" required min="{MIN_DATE.isoformat()}" value="{escape(value, quote=True)}">'
        f'{_concern_fieldset(concern)}'
        '<button class="cta" type="submit">日干を調べる</button></form>'
        '<p class="note">入力した生年月日は、日干の計算にだけ使い、保存しません。選んだ悩みの種類は、どの悩みが多いかを数えるためだけに記録します。</p></section>',
        robots,
    )


def render_result(birth: date, robots: str, src: str = "", concern: str = "") -> str:
    stem = day_stem_for(birth)
    note = DAY_STEM_NOTES[stem]
    query = f"?src={_safe_src(src)}" if _safe_src(src) else ""
    if concern == "hard":
        # とてもつらい人には販売の案内を出さず、相談窓口を先に出す
        return _document(
            SUPPORT_BOX
            + '<section class="box"><p class="eyebrow">YOUR DAY STEM</p>'
            f'<h2>あなたの日干は「{stem}」：{note["image"]}のイメージ</h2>'
            f'<p>{escape(note["care"])}</p>'
            f'<a class="sub" href="/nikkan{query}">ほかの生年月日で調べる</a></section>',
            robots,
        )
    concern_note = CONCERN_NOTES[stem].get(concern, "")
    concern_html = f'<h2>「{CONCERNS[concern]}」に悩むとき</h2><p class="concern">{escape(concern_note)}</p>' if concern_note else ""
    lead = "いまの悩みに、命式全体から答えるのが、八雲式 四柱推命鑑定です。" if concern_note else ""
    return _document(
        '<section class="box"><p class="eyebrow">YOUR DAY STEM</p>'
        f'<p>{birth.year}年{birth.month}月{birth.day}日生まれ</p>'
        f'<h1>あなたの日干は「{stem}」<br>{note["image"]}のイメージ</h1>'
        f'<p>日干の{stem}は、{STEM_YIN_YANG[stem]}の{STEM_ELEMENT[stem]}です。</p>'
        f'<p>{escape(note["nature"])}</p><p>{escape(note["care"])}</p>'
        f'{_holding_html(birth)}'
        f'{concern_html}'
        '<h2>ふり返りの問い</h2>'
        f'<p class="question">{escape(note["question"])}</p>'
        '<p class="note">ノートに一行、書いてみてください。答えに正解はありません。</p>'
        '<p class="note">これは日干だけを見た、八雲式の読み物です。四柱推命の判定ではありません。23時以降に生まれた方は、日干が翌日のものになる場合があります。</p></section>'
        f'{_line_box()}'
        '<section class="box"><h2>命式全体で、もっと深く</h2>'
        f'<p>{HOLDING_MORE}</p>'
        '<p>四柱推命では、日干のほかに、年・月・時の柱と、10年ごとに巡る大運を合わせて読みます。'
        f'{lead}八雲式 四柱推命鑑定では、あなたの命式全体と今の流れ、お悩みへの回答、八雲式の読み物をお届けします。</p>'
        f'<a class="cta" href="/career-reading{query}">八雲式 四柱推命鑑定を見る</a>'
        f'<a class="sub" href="/academy{query}">自分で読めるようになりたい方は：アカデミー（第1章は無料）</a>'
        f'<a class="sub" href="/nikkan{query}">ほかの生年月日で調べる</a></section>',
        robots,
    )
