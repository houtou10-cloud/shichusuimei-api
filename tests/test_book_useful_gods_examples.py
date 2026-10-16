"""応用編p.211〜263の例題で、本どおりモードの用神の一致率が下がらないことを確かめる。"""

from scripts.evaluate_book_useful_gods import evaluate

def test_book_mode_useful_god_agreement_with_oyo_examples():
    result = evaluate("book_kiso")
    assert result["pillars_match"] == 47
    assert result["top1_in_book_set"] >= 45
    assert result["top1_is_book_first"] >= 39
