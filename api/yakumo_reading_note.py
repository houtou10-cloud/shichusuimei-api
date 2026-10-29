"""八雲式の読み物（鑑定結果の最後に付ける、命式のイメージを味わう固定の文章）。

ここは四柱推命の判定ではない。日干の自然のたとえと、命式の文字に表れた五行の数から、
暮らしの中で試せることとふり返りの問いを添える。AIは使わず、文章はすべてこのファイルに置く。
霊・因縁・不安をあおる表現、健康やお金の結果を言い切る表現は入れない。
"""

from __future__ import annotations

from html import escape

ELEMENTS = ("木", "火", "土", "金", "水")

STEM_ELEMENT = {
    "甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土",
    "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水",
}
BRANCH_ELEMENT = {
    "寅": "木", "卯": "木", "巳": "火", "午": "火", "辰": "土", "戌": "土",
    "丑": "土", "未": "土", "申": "金", "酉": "金", "亥": "水", "子": "水",
}

# 日干ごとの自然のイメージ、心が整う過ごし方、ふり返りの問い。
DAY_STEM_NOTES = {
    "甲": {
        "image": "大樹",
        "nature": "空へまっすぐ伸びる、大きな木のイメージです。一度根を張った場所で、時間をかけて大きく育っていく力を持っています。",
        "care": "迷ったときは、木のように「根」に戻ってみてください。朝の散歩や、長く続けてきたことに触れる時間が、心をまっすぐに戻してくれます。",
        "question": "あなたが、時間をかけて育てていきたいものは何ですか？",
    },
    "乙": {
        "image": "草花",
        "nature": "風に揺れながらも、しなやかに咲く草花のイメージです。まわりに合わせて形を変えながら、自分の場所で花を咲かせる力を持っています。",
        "care": "疲れたときは、草花のように日だまりで休む時間を。好きな花を一輪飾る、やわらかな音楽を聴くなど、小さな心地よさを大切にしてください。",
        "question": "あなたが、しなやかに受け流したいことは何ですか？",
    },
    "丙": {
        "image": "太陽",
        "nature": "まわりを明るく照らす、太陽のイメージです。その場にいるだけで空気を明るくし、人に元気を分ける力を持っています。",
        "care": "照らし続けて疲れたら、夕日をゆっくり眺めるように、自分を照らす時間を。誰かのためではなく、自分が楽しいことをひとつ選んでください。",
        "question": "あなた自身を照らしてくれるものは何ですか？",
    },
    "丁": {
        "image": "灯火",
        "nature": "暗いところで、近くの人の手もとを照らす灯火のイメージです。静かに、でも確かに、そばにいる人を温める力を持っています。",
        "care": "灯火は、燃料があってこそ燃え続けます。学びや、尊敬する人、心を育ててくれるものを、そばに置いてください。",
        "question": "あなたの灯りを支えているものは何ですか？",
    },
    "戊": {
        "image": "山",
        "nature": "どっしりとそびえる山のイメージです。揺らがない安心感で、まわりの人がよりどころにできる力を持っています。",
        "care": "抱えすぎたと感じたら、山の上から景色を眺めるように、少し離れて全体を見てください。高いところや、見晴らしのよい場所で過ごすのもおすすめです。",
        "question": "あなたが、どっしり構えて見守りたいことは何ですか？",
    },
    "己": {
        "image": "田畑",
        "nature": "作物を育てる、やわらかな田畑の土のイメージです。人やものごとを受け入れ、じっくり育てる力を持っています。",
        "care": "与えるばかりで疲れたら、土を休ませるように、何もしない日をつくってください。料理や手仕事など、手を動かす時間も心を整えてくれます。",
        "question": "あなたが、いま育てているものは何ですか？",
    },
    "庚": {
        "image": "鉱石",
        "nature": "鍛えられて刃や器になる、鉱石のイメージです。困難をくぐるほど形が定まり、決めたことをやり抜く力を持っています。",
        "care": "張りつめたときは、刃を研ぐように、身のまわりを整える時間を。不要なものを手放すと、気持ちにも区切りがつきます。",
        "question": "あなたが、いま区切りをつけたいことは何ですか？",
    },
    "辛": {
        "image": "宝石",
        "nature": "磨かれて光る、宝石のイメージです。繊細な感性と、美しいものを見分ける力を持っています。",
        "care": "疲れたときは、宝石を磨くように、自分を丁寧に扱う時間を。好きな器や小物を使う、身だしなみを整えるなど、小さな美しさを大切にしてください。",
        "question": "あなたが、大切に磨き続けたいものは何ですか？",
    },
    "壬": {
        "image": "大河",
        "nature": "大きく流れる川や海のイメージです。広い視野で流れを読み、人やものごとを運んでいく力を持っています。",
        "care": "流れが速すぎると感じたら、川がゆるやかな淵で休むように、立ち止まる時間を。水辺を歩く、湯船にゆっくりつかるのもおすすめです。",
        "question": "あなたが、いま流れに任せてよいことは何ですか？",
    },
    "癸": {
        "image": "雨露",
        "nature": "大地をうるおす、雨や露のイメージです。目立たないところで、まわりを静かに育てる力を持っています。",
        "care": "気持ちが乾いたと感じたら、雨音を聞くように、静かな時間を。日記を書く、ゆっくり眠るなど、心をうるおすことを選んでください。",
        "question": "あなたが、静かにうるおしたいものは何ですか？",
    },
}

# 命式の文字に少ない五行を、暮らしの中で意識するためのヒント。
FEW_ELEMENT_CARE = {
    "木": "木は「伸びる」力です。朝の光の中を歩く、植物を育てる、新しいことを小さく始めてみる、といった過ごし方がヒントになります。",
    "火": "火は「照らす」力です。日の光を浴びる、人と笑い合う、好きなことを言葉にしてみる、といった過ごし方がヒントになります。",
    "土": "土は「支える」力です。決まった時間に食事をとる、部屋を整える、足もとを確かめるように一日の予定を見直す、といった過ごし方がヒントになります。",
    "金": "金は「区切る」力です。不要なものを手放す、姿勢を正す、終わらせることをひとつ決める、といった過ごし方がヒントになります。",
    "水": "水は「めぐる」力です。湯船にゆっくりつかる、静かな時間をつくる、よく眠る、といった過ごし方がヒントになります。",
}

# 命式の文字に多い五行を、持ち味として受け止めるための一文。
MANY_ELEMENT_NOTE = {
    "木": "多い木は、伸びていく力の表れです。広げすぎたと感じたら、ひとつに絞ってみてください。",
    "火": "多い火は、情熱と明るさの表れです。燃えすぎたと感じたら、静かな時間で火を休ませてください。",
    "土": "多い土は、安定と粘り強さの表れです。重くなったと感じたら、新しい風を入れてみてください。",
    "金": "多い金は、決断力とけじめの表れです。かたくなったと感じたら、やわらかいものに触れてみてください。",
    "水": "多い水は、知恵と柔軟さの表れです。流れが定まらないと感じたら、ひとつ決めて形にしてみてください。",
}


def _pillar_characters(chart: object) -> list[tuple[str, str]]:
    """命式の天干・地支を、分かっている柱だけ集める（時刻不明なら三柱）。"""
    pillars = chart.get("chart", {}) if isinstance(chart, dict) else {}
    found: list[tuple[str, str]] = []
    for key in ("year", "month", "day", "hour"):
        pillar = pillars.get(key) if isinstance(pillars, dict) else None
        if not isinstance(pillar, dict):
            continue
        stem, branch = pillar.get("stem"), pillar.get("branch")
        if stem in STEM_ELEMENT and branch in BRANCH_ELEMENT:
            found += [("stem", str(stem)), ("branch", str(branch))]
    return found


def element_counts(chart: object) -> dict[str, int]:
    counts = dict.fromkeys(ELEMENTS, 0)
    for kind, char in _pillar_characters(chart):
        counts[(STEM_ELEMENT if kind == "stem" else BRANCH_ELEMENT)[char]] += 1
    return counts


def render_yakumo_note(chart: object) -> str:
    """鑑定結果に付ける「八雲式の読み物」のカード。日干が分からなければ出さない。"""
    pillars = chart.get("chart", {}) if isinstance(chart, dict) else {}
    day = pillars.get("day") if isinstance(pillars, dict) else None
    stem = day.get("stem") if isinstance(day, dict) else None
    note = DAY_STEM_NOTES.get(str(stem))
    characters = _pillar_characters(chart)
    if note is None or not characters:
        return ""
    counts = element_counts(chart)
    fewest = min(counts.values())
    most = max(counts.values())
    few = [e for e in ELEMENTS if counts[e] == fewest]
    many = [e for e in ELEMENTS if counts[e] == most]
    count_text = "、".join(f"{e}{counts[e]}" for e in ELEMENTS)
    few_care = "".join(f"<p>{escape(FEW_ELEMENT_CARE[e])}</p>" for e in few)
    many_note = "".join(f"<p>{escape(MANY_ELEMENT_NOTE[e])}</p>" for e in many) if most > fewest else ""
    return (
        '<article class="yakumo-note"><h2>八雲式の読み物</h2>'
        '<p class="note-lead">ここからは四柱推命の判定ではなく、命式のイメージを自然にたとえて味わう読み物です。</p>'
        f'<h3>日干は{escape(str(stem))}：{escape(note["image"])}</h3>'
        f'<p>{escape(note["nature"])}</p><p>{escape(note["care"])}</p>'
        '<h3>五行のセルフケア</h3>'
        f'<p>命式の{len(characters)}文字を五行で数えると、{escape(count_text)}です。'
        f'少ない五行は{escape("・".join(few))}、多い五行は{escape("・".join(many))}です。</p>'
        f'{few_care}{many_note}'
        '<h3>ふり返りの問い</h3>'
        f'<p class="note-question">{escape(note["question"])}</p>'
        '<p class="note-hint">ノートに一行、書いてみてください。答えに正解はありません。</p>'
        '</article>'
    )
