"""天然石＋プレミアム鑑定の見本ページ（/stones）。

まだ販売していない見本。検索エンジンに出さず、どのページからもリンクしない。
予約ボタンは押せない。文章は docs/business/powerstone_premium_pages.md（研究用リポジトリ）にもとづく。
"""

from __future__ import annotations

from html import escape

from api.jibunshi import _document

ROBOTS = '<meta name="robots" content="noindex,nofollow">'

# (商品名, 石, 五行, 色見本, 説明)
BRACELETS = (
    ("翠山", "翡翠", "木", "#3f7a52",
     "大地に根を張り、まっすぐに伸びていく木。四柱推命で「木」は、成長と始まりを表す五行です。深い緑をたたえた翡翠を、色の深さと透明感で選びます。"),
    ("紅灯", "ガーネット", "火", "#8c1f2c",
     "あたりを照らし、人を温める火。四柱推命で「火」は、明るさと表現を表す五行です。深い紅色のロードライトガーネットを、光を通したときの輝きで選びます。"),
    ("金穂", "シトリン", "土", "#c99a2e",
     "すべてを受けとめ、実りを育てる土。四柱推命で「土」は、安定と信頼を表す五行です。実った稲穂のような黄金色のシトリンを、色のむらの少なさで選びます。"
     "市場に出回るシトリンの多くは、アメジストを加熱して色を変えたものです。加熱の有無は商品ごとに明記します。"),
    ("白刃", "ルチルクォーツ", "金", "#d8cfa8",
     "鍛えられて輝きを増す金。四柱推命で「金」は、意志と決断を表す五行です。透明度の高い水晶に、金色の針が均一に入ったルチルクォーツを選びます。"),
    ("深海", "ラピスラズリ", "水", "#1f3a78",
     "形を変えながら流れていく水。四柱推命で「水」は、知恵と柔軟さを表す五行です。夜空のような深い青に、金色のパイライトが散らばるラピスラズリを選びます。"),
)

_STYLE = (
    "<style>.sample{background:#fff4d6;border:2px solid #c99a2e;border-radius:14px;padding:14px 18px;margin-bottom:18px;font-weight:700}"
    ".item{display:flex;gap:16px;align-items:flex-start;border-top:1px solid #dfd1c2;padding:18px 0}.item:first-of-type{border-top:0}"
    ".swatch{flex:0 0 56px;height:56px;border-radius:50%;box-shadow:inset 0 -6px 12px rgba(0,0,0,.25)}"
    ".item h3{margin:0 0 4px}.price{color:#5d3b25;font-weight:700}"
    ".disabled{display:inline-block;margin-top:8px;padding:12px 20px;border-radius:999px;background:#d9d2c8;color:#6b6157;font-weight:700}"
    "@media(max-width:480px){.swatch{flex-basis:40px;height:40px}}</style>"
)


def _bracelet(name: str, stone: str, element: str, color: str, text: str) -> str:
    return (
        '<div class="item">'
        f'<div class="swatch" style="background:{escape(color, quote=True)}" aria-hidden="true"></div>'
        f"<div><h3>{escape(name)} {escape(stone)}ブレスレット（{escape(element)}の色）</h3>"
        f"<p>{escape(text)}</p>"
        '<p class="price">販売価格【未定】（税込）・プレミアム鑑定付き</p></div>'
        "</div>"
    )


def render_page() -> str:
    items = "".join(_bracelet(*row) for row in BRACELETS)
    body = (
        _STYLE
        + '<p class="sample" role="note">これは見本です。まだ販売していません。価格・仕様・写真は、仕入れ先が決まってから入れます。</p>'
        '<section class="box"><p class="eyebrow">NATURAL STONE & PREMIUM READING</p>'
        "<h1>天然石とプレミアム鑑定</h1>"
        "<p>四柱推命のプレミアム鑑定と、上位グレードの天然石をひとつにしてお届けする、完全予約制の商品です。</p>"
        "<p>すべての商品に、PDFの鑑定書と音声解説が付きます。価格は、石とプレミアム鑑定を合わせた金額です。</p>"
        "</section>"
        '<section class="box"><h2>五行のブレスレット</h2>'
        "<p>石の色と五行の対応は、四柱推命で使われる色の考え方にもとづきます。お好きな色でお選びいただいて大丈夫です。"
        "プレミアム鑑定書では、あなたの用神（命式を整える五行）と、お選びいただいた石の色の五行との関わりをお伝えします。</p>"
        f"{items}</section>"
        '<section class="box"><h2>プレミアム鑑定の内容</h2><ol class="stars">'
        "<li>あなたの命式：命式表と、日干から読み解く本質</li>"
        "<li>五行のバランス：多い五行と少ない五行</li>"
        "<li>用神とこの石：用神と、お選びいただいた石の色の五行との関わり</li>"
        "<li>強みのヒント：通変星から見る、仕事や人との関わりの傾向（才能を言い切るものではありません）</li>"
        "<li>人生の流れ：10年ごとの大運と、いまどの時期にいるか</li>"
        "<li>これからの流れ：年ごとの運気の流れのヒント（出来事を言い当てるものではありません）</li>"
        "</ol>"
        "<p>鑑定書はPDFでお届けし、内容を音声でもお伝えします（音声合成：VOICEVOX「麒ヶ島宗麟」）。</p>"
        "<p><strong>八雲式 四柱推命鑑定（1,980円）との違い</strong><br>"
        "命式の計算は、1,980円の鑑定と同じ八雲式の規則で行います。プレミアム鑑定は、その内容をPDFの鑑定書と音声解説にまとめ、"
        "お選びいただいた石と用神の関わりを加えたものです。1,980円の鑑定をご購入済みの方は、1,980円を差し引きます。</p>"
        "<p><strong>生まれた時間がわからない方へ</strong><br>"
        "年・月・日の三柱で鑑定します。三柱では、身旺・身弱や用神が決まらず「保留」になる場合があります。"
        "その場合、石と用神の関わりも「保留」としてお伝えします。</p>"
        "</section>"
        '<section class="box"><h2>ご予約からお届けまで</h2><ol class="stars">'
        "<li>ご予約：生年月日など、鑑定に必要なことをご入力いただきます</li>"
        "<li>在庫のご連絡：石をご用意できるかをメールでお知らせします。この時点では代金はかかりません</li>"
        "<li>お支払い：ご用意できる場合に、お支払い方法をご案内します</li>"
        "<li>鑑定と石の準備：鑑定書と音声解説を作成し、必要な石は鑑別に出します</li>"
        "<li>お届け：石を発送し、鑑定書（PDF）と音声解説をメールでお送りします</li>"
        "</ol>"
        '<span class="disabled" aria-disabled="true">在庫確認・ご予約（見本のため押せません）</span>'
        "</section>"
        '<section class="box"><h2>ご注意</h2>'
        "<p>天然石は、ひとつずつ色や模様、内包物が異なります。加熱・含浸などの処理がされている石は、商品ごとに明記します。</p>"
        "<p>プレミアム鑑定は、四柱推命の考え方にもとづくひとつの読み解きです。石の色と五行を結びつける見方は、八雲式の楽しみ方のひとつです。"
        "天然石はお守りとしてお楽しみください。健康や運勢、将来の出来事への効果を保証するものではありません。</p>"
        "</section>"
    )
    return _document(body, ROBOTS, "天然石とプレミアム鑑定（見本）")
