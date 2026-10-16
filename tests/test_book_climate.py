from engine.book_climate import book_climate_useful_gods, chokou_stems


def test_chokou_table_cells_from_oyo_p210():
    assert chokou_stems("甲", "寅") == ("丙癸", True)   # p.211：初春の若木に丙と癸
    assert chokou_stems("丙", "午") == ("壬庚", True)
    assert chokou_stems("丁", "巳") == ("甲庚", True)
    assert chokou_stems("丁", "申") == ("甲庚丙戊", False)  # 大字なし


def test_climate_elements_follow_table_order_and_merge_same_element():
    engine = {"climate_elements": ["水"], "primary_climate_element": "水", "season": "spring"}
    result = book_climate_useful_gods(engine, "甲", "戌")  # 庚甲丁壬癸
    assert result["climate_elements"] == ["金", "木", "火", "水"]
    assert result["climate_candidates"][3]["stems"] == ["壬", "癸"]
    assert result["season"] == "spring"
    assert result["book_status"] == "ok"


def test_no_major_cell_is_hold():
    result = book_climate_useful_gods({"climate_elements": []}, "丁", "酉")
    assert result["book_status"] == "hold"
    assert result["climate_candidates"][0]["is_major"] is False
