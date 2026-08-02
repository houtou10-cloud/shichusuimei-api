from engine.five_elements import (
    get_stem_element,
)


SEASONAL_STATES = {
    "寅": {
        "木": "旺",
        "火": "相",
        "水": "休",
        "金": "囚",
        "土": "死",
    },
    "卯": {
        "木": "旺",
        "火": "相",
        "水": "休",
        "金": "囚",
        "土": "死",
    },
    "辰": {
        "土": "旺",
        "金": "相",
        "火": "休",
        "木": "囚",
        "水": "死",
    },
    "巳": {
        "火": "旺",
        "土": "相",
        "木": "休",
        "水": "囚",
        "金": "死",
    },
    "午": {
        "火": "旺",
        "土": "相",
        "木": "休",
        "水": "囚",
        "金": "死",
    },
    "未": {
        "土": "旺",
        "金": "相",
        "火": "休",
        "木": "囚",
        "水": "死",
    },
    "申": {
        "金": "旺",
        "水": "相",
        "土": "休",
        "火": "囚",
        "木": "死",
    },
    "酉": {
        "金": "旺",
        "水": "相",
        "土": "休",
        "火": "囚",
        "木": "死",
    },
    "戌": {
        "土": "旺",
        "金": "相",
        "火": "休",
        "木": "囚",
        "水": "死",
    },
    "亥": {
        "水": "旺",
        "木": "相",
        "金": "休",
        "土": "囚",
        "火": "死",
    },
    "子": {
        "水": "旺",
        "木": "相",
        "金": "休",
        "土": "囚",
        "火": "死",
    },
    "丑": {
        "土": "旺",
        "金": "相",
        "火": "休",
        "木": "囚",
        "水": "死",
    },
}


STATE_SCORES = {
    "旺": 12.0,
    "相": 8.0,
    "休": 2.0,
    "囚": -6.0,
    "死": -10.0,
}


def evaluate_seasonal_strength(
    day_stem: str,
    month_branch: str,
) -> dict:
    """
    日主の五行が月支の季節で
    どの状態になるかを評価します。
    """
    day_element = get_stem_element(
        day_stem
    )

    if month_branch not in SEASONAL_STATES:
        raise ValueError(
            f"不正な月支です: {month_branch}"
        )

    state = SEASONAL_STATES[
        month_branch
    ][day_element]

    score = STATE_SCORES[state]

    return {
        "day_stem": day_stem,
        "day_element": day_element,
        "month_branch": month_branch,
        "state": state,
        "score": score,
        "method": "seasonal_state_v1",
        "status": "provisional_seasonal_strength",
        "notes": [
            "月支と日主五行から旺相休囚死を判定しています。",
            "土用期間と節入り直後の細分化は未反映です。",
            "流派差を含むため暫定評価です。",
        ],
    }
