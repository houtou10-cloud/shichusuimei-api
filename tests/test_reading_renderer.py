"""tests/test_reading_renderer.py - ReadingProduct -> HTML renderer non-LIVE tests."""
from pathlib import Path
import pytest
from engine.reading_product import DEFAULT_SECTION_ORDER, ReadingProduct
from engine.reading_renderer import (
    READING_RENDERER_METHOD, READING_RENDERER_STATUS, READING_RENDERER_VERSION,
    get_reading_renderer_metadata, render_reading_product_fragment,
    render_reading_product_html, write_reading_product_html,
)

EXPECTED_SEQUENCE = ["乙丑", "癸未", "丁巳", "辛亥"]
SECTION_TITLES = {
    "core_personality": "本質・性格", "career": "仕事・適職", "wealth": "金運",
    "relationships": "恋愛・人間関係", "health": "健康傾向", "current_luck": "現在の運勢",
    "future_flow": "今後の流れ", "advice": "開運アドバイス",
}

def _pillar(position, pillar, stem, branch, god, stage, hidden, hidden_god):
    return {"position": position, "pillar": pillar, "stem": stem, "branch": branch,
            "stem_ten_god": god, "twelve_stage": stage, "main_hidden_stem": hidden,
            "main_hidden_stem_ten_god": hidden_god}

def _sections():
    return tuple({"key": k, "title": SECTION_TITLES[k], "summary": f"{SECTION_TITLES[k]}の要約{i}",
                  "detail": f"{SECTION_TITLES[k]}の詳細本文{i}。計算済みデータを基にした鑑定です。",
                  "evidence": [f"{SECTION_TITLES[k]}の根拠A", f"{SECTION_TITLES[k]}の根拠B"],
                  "advice": [f"{SECTION_TITLES[k]}の助言A", f"{SECTION_TITLES[k]}の助言B"]}
                 for i, k in enumerate(DEFAULT_SECTION_ORDER, 1))

def make_product(title="四柱推命 AI鑑定書"):
    return ReadingProduct(
        title=title,
        subject={"birth_date":"1985-07-17","birth_time":"21:50","birth_place":"石川県","gender":"female","timezone":"Asia/Tokyo"},
        chart_summary={
            "pillar_sequence": list(EXPECTED_SEQUENCE),
            "pillars": {
                "year": _pillar("year","乙丑","乙","丑","偏印","墓","己","食神"),
                "month": _pillar("month","癸未","癸","未","偏官","冠帯","己","食神"),
                "day": _pillar("day","丁巳","丁","巳","日主","帝旺","丙","劫財"),
                "hour": _pillar("hour","辛亥","辛","亥","偏財","胎","壬","正官"),
            },
            "day_master":{"stem":"丁","element":"火","yin_yang":"陰","day_pillar":"丁巳"},
            "five_elements":{"weighted_scores":{"木":18.0,"火":23.0,"土":20.0,"金":14.0,"水":25.0},"strongest_element":"水","weakest_element":"金"},
            "strength":{"label":"中和","technical_label":"balanced","final_score":50.0},
            "pattern":{"primary_pattern":"食神格","technical_pattern":"食神格","overall_judgment":"成立"},
            "useful_gods":{"primary_useful_element":"金","secondary_useful_elements":["水","木","土"],"unfavorable_elements":["火"]},
            "current_luck":{"ganzhi":"丁亥","stem_ten_god":"比肩","branch_element":"水","start_age":37,"end_age":47},
            "annual_luck":{"year":2026,"ganzhi":"丙午","stem_ten_god":"劫財","twelve_stage":"建禄"},
        },
        sections=_sections(),
        summary="丁を中心に、食神格の表現力を活かしていく命です。",
        disclaimer="本鑑定は傾向を示すもので、将来を確定的に断定するものではありません。医学・医療上の判断は専門家へご相談ください。",
        generation={"model":"gpt-5","response_id":"resp_SECRET_123","response_status":"completed","usage":{"input_tokens":100,"output_tokens":200,"total_tokens":300},"sections":list(DEFAULT_SECTION_ORDER),"method":"openai_responses_api_v1","status":"completed","api_key":"sk-DO-NOT-EXPOSE","system_prompt":"SECRET SYSTEM PROMPT","user_prompt":"SECRET USER PROMPT"},
        metadata={"created_at":"2026-08-12T09:00:00+00:00","reading_context_schema":"reading_context_v1","reading_context_method":"reading_context_v1","reading_context_status":"ready_for_ai_reading","source_metadata":{"internal_secret":"DO-NOT-EXPOSE"},"product_version":"reading_product_v1","recalculates_astrology":False,"rewrites_ai_reading":False},
    )

@pytest.fixture
def product(): return make_product()
@pytest.fixture
def html_document(product): return render_reading_product_html(product)
@pytest.fixture
def fragment(product): return render_reading_product_fragment(product)

def test_renderer_constants():
    assert READING_RENDERER_VERSION == "reading_renderer_v1"
    assert READING_RENDERER_METHOD == "reading_renderer_v1"
    assert READING_RENDERER_STATUS == "ready"

def test_renderer_metadata():
    m=get_reading_renderer_metadata()
    assert m["version"]==READING_RENDERER_VERSION and m["method"]==READING_RENDERER_METHOD and m["status"]==READING_RENDERER_STATUS
    assert m["input_type"]=="ReadingProduct" and m["recalculates_astrology"] is False and m["rewrites_ai_reading"] is False
    assert m["escapes_html"] is True and m["exposes_generation_metadata"] is False and m["exposes_api_key"] is False and m["print_ready"] is True

@pytest.mark.parametrize("bad", [None,{},[],"product",123])
def test_render_html_rejects_non_product(bad):
    with pytest.raises(TypeError): render_reading_product_html(bad)
@pytest.mark.parametrize("bad", [None,{},[],"product",123])
def test_render_fragment_rejects_non_product(bad):
    with pytest.raises(TypeError): render_reading_product_fragment(bad)

def test_full_document_contract(html_document):
    assert html_document.startswith("<!DOCTYPE html>")
    for token in ['<html lang="ja">','charset="UTF-8"','name="viewport"','noindex,nofollow','<main class="reading-document">','<header class="cover">']:
        assert token in html_document

def test_subject_content(html_document):
    for token in ["四柱推命 AI鑑定書","1985-07-17","21:50","石川県","女性","Asia/Tokyo"]: assert token in html_document

@pytest.mark.parametrize("pillar", EXPECTED_SEQUENCE)
def test_each_pillar(html_document,pillar): assert pillar in html_document
@pytest.mark.parametrize("label", ["年柱","月柱","日柱","時柱"])
def test_pillar_labels(html_document,label): assert label in html_document

def test_chart_summary_content(html_document):
    for token in ["日主","丁","五行","火","身強・身弱","中和","balanced","格局","食神格","用神","金","最も強い五行","水","最も弱い五行","現在の大運","丁亥","歳運","丙午","2026"]:
        assert token in html_document

def test_overall_content(html_document):
    assert "総合鑑定" in html_document and "丁を中心に、食神格の表現力を活かしていく命です。" in html_document

@pytest.mark.parametrize("key", DEFAULT_SECTION_ORDER)
def test_section_full_contract(html_document,key):
    title=SECTION_TITLES[key]
    for token in [title,f"{title}の要約",f"{title}の詳細本文",f"{title}の根拠A",f"{title}の根拠B",f"{title}の助言A",f"{title}の助言B"]: assert token in html_document

def test_section_headings(html_document):
    assert "鑑定の根拠" in html_document and "アドバイス" in html_document

def test_disclaimer(html_document):
    assert "免責・注意事項" in html_document and "医学・医療上の判断は専門家へ" in html_document

@pytest.mark.parametrize("secret", ["resp_SECRET_123","sk-DO-NOT-EXPOSE","SECRET SYSTEM PROMPT","SECRET USER PROMPT","DO-NOT-EXPOSE","openai_responses_api_v1"])
def test_no_internal_data(html_document,secret): assert secret not in html_document

def test_title_escaped():
    h=render_reading_product_html(make_product('<script>alert("x")</script>'))
    assert "<script>" not in h and "&lt;script&gt;" in h

def test_subject_escaped():
    p=make_product(); p.subject["birth_place"]='<img src=x onerror="boom">'; h=render_reading_product_html(p)
    assert '<img src=x onerror="boom">' not in h and "&lt;img" in h

def test_summary_escaped():
    p=make_product(); object.__setattr__(p,"summary","<b>危険</b>"); h=render_reading_product_html(p)
    assert "<b>危険</b>" not in h and "&lt;b&gt;危険&lt;/b&gt;" in h

def test_section_content_escaped():
    p=make_product(); p.sections[0]["detail"]='<script>alert("d")</script>'; p.sections[0]["evidence"][0]="<b>根拠</b>"; p.sections[0]["advice"][0]="<i>助言</i>"
    h=render_reading_product_html(p)
    for raw in ['<script>alert("d")</script>',"<b>根拠</b>","<i>助言</i>"]: assert raw not in h
    for escaped in ["&lt;script&gt;","&lt;b&gt;根拠&lt;/b&gt;","&lt;i&gt;助言&lt;/i&gt;"]: assert escaped in h

def test_css_and_print(html_document):
    for token in ["<style>","@page","size: A4","@media print","max-width: 720px"]: assert token in html_document

def test_css_can_be_omitted(product):
    h=render_reading_product_html(product,include_css=False); assert "<style>" not in h and "四柱推命 AI鑑定書" in h

def test_custom_document_title(product):
    h=render_reading_product_html(product,document_title="八雲 四柱推命鑑定")
    assert "<title>八雲 四柱推命鑑定</title>" in h and "四柱推命 AI鑑定書" in h

def test_fragment_contract(fragment):
    assert fragment.startswith('<div class="reading-document">')
    for token in ["<!DOCTYPE html>",'<html lang="ja">',"<head>","<body>",'<header class="cover">']: assert token not in fragment
    for token in ["基本情報","1985-07-17","乙丑","癸未","丁巳","辛亥","免責・注意事項"]: assert token in fragment
    assert "sk-DO-NOT-EXPOSE" not in fragment

def test_missing_timezone_not_rendered():
    p=make_product(); p.subject["timezone"]=None; assert "タイムゾーン" not in render_reading_product_html(p)

def test_unknown_gender_preserved():
    p=make_product(); p.subject["gender"]="custom"; assert "custom" in render_reading_product_html(p)

def test_missing_optional_value_uses_dash():
    p=make_product(); p.chart_summary["pillars"]["year"]["stem_ten_god"]=None; assert "―" in render_reading_product_html(p)

def test_write_returns_path_and_creates_utf8(product,tmp_path):
    out=tmp_path/"nested"/"reading.html"; result=write_reading_product_html(product,out)
    assert isinstance(result,Path) and result==out and out.exists()
    text=out.read_text(encoding="utf-8"); assert "四柱推命" in text and "石川県" in text and "丁巳" in text

@pytest.mark.parametrize("suffix", [".html",".htm"])
def test_write_accepts_html_extensions(product,tmp_path,suffix):
    out=tmp_path/f"reading{suffix}"; assert write_reading_product_html(product,out).exists()

@pytest.mark.parametrize("filename", ["reading.txt","reading.pdf","reading","reading.json"])
def test_write_rejects_non_html(product,tmp_path,filename):
    with pytest.raises(ValueError): write_reading_product_html(product,tmp_path/filename)

def test_written_content_matches_renderer(product,tmp_path):
    out=tmp_path/"reading.html"; write_reading_product_html(product,out)
    assert out.read_text(encoding="utf-8")==render_reading_product_html(product)

def test_renderer_does_not_mutate_source(product):
    subject=dict(product.subject); seq=list(product.chart_summary["pillar_sequence"])
    sections=[(x["key"],x["title"],x["summary"],x["detail"],list(x["evidence"]),list(x["advice"])) for x in product.sections]
    render_reading_product_html(product)
    assert product.subject==subject and product.chart_summary["pillar_sequence"]==seq
    assert [(x["key"],x["title"],x["summary"],x["detail"],list(x["evidence"]),list(x["advice"])) for x in product.sections]==sections

def test_reading_renderer_v1_final_gate(product):
    h=render_reading_product_html(product); f=render_reading_product_fragment(product)
    assert h.startswith("<!DOCTYPE html>") and '<html lang="ja">' in h and 'charset="UTF-8"' in h
    for token in ["1985-07-17","21:50","石川県","女性",*EXPECTED_SEQUENCE,"中和","食神格","丁亥","丙午","免責・注意事項"]: assert token in h
    for key in DEFAULT_SECTION_ORDER:
        title=SECTION_TITLES[key]
        for token in [title,f"{title}の要約",f"{title}の詳細本文",f"{title}の根拠A",f"{title}の助言A"]: assert token in h
    for secret in ["resp_SECRET_123","sk-DO-NOT-EXPOSE","SECRET SYSTEM PROMPT","SECRET USER PROMPT","DO-NOT-EXPOSE"]:
        assert secret not in h and secret not in f
    assert "@page" in h and "size: A4" in h and "@media print" in h
    assert f.startswith('<div class="reading-document">') and "<!DOCTYPE html>" not in f
    m=get_reading_renderer_metadata()
    assert m["recalculates_astrology"] is False and m["rewrites_ai_reading"] is False and m["escapes_html"] is True and m["exposes_api_key"] is False
