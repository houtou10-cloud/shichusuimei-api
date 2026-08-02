from engine.constants import (
    CONTROLS,
    GENERATES,
    STEM_ELEMENTS,
    STEMS,
)


def get_day_master_element(
    day_stem: str,
) -> str:
    """
    日主の天干から五行を返します。
    """
    if day_stem not in STEMS:
        raise ValueError(
            f"不正な日干です: {day_stem}"
        )

    return STEM_ELEMENTS[day_stem]["element"]


def get_supporting_elements(
    day_stem: str,
) -> list[str]:
    """
    日主を助ける五行を返します。

    ・日主と同じ五行
    ・日主を生じる五行
    """
    day_element = get_day_master_element(
        day_stem
    )

    resource_element = next(
        element
        for element, generated_element
        in GENERATES.items()
        if generated_element == day_element
    )

    return [
        day_element,
        resource_element,
    ]


def get_draining_elements(
    day_stem: str,
) -> list[str]:
    """
    日主を弱める側の五行を返します。

    ・日主が生じる五行
    ・日主が剋す五行
    ・日主を剋す五行
    """
    day_element = get_day_master_element(
        day_stem
    )

    output_element = GENERATES[
        day_element
    ]

    wealth_element = CONTROLS[
        day_element
    ]

    officer_element = next(
        element
        for element, controlled_element
        in CONTROLS.items()
        if controlled_element == day_element
    )

    return [
        output_element,
        wealth_element,
        officer_element,
    ]


def classify_five_elements_for_day_master(
    day_stem: str,
    five_elements: dict,
) -> dict:
    """
    五行集計を、日主を助ける側と
    弱める側へ分類します。
    """
    counts = five_elements["counts"]

    supporting_elements = (
        get_supporting_elements(
            day_stem
        )
    )

    draining_elements = (
        get_draining_elements(
            day_stem
        )
    )

    supporting_score = sum(
        counts[element]
        for element in supporting_elements
    )

    draining_score = sum(
        counts[element]
        for element in draining_elements
    )

    total = supporting_score + draining_score

    supporting_ratio = (
        round(
            supporting_score / total * 100,
            2,
        )
        if total
        else 0.0
    )

    draining_ratio = (
        round(
            draining_score / total * 100,
            2,
        )
        if total
        else 0.0
    )

    return {
        "day_stem": day_stem,
        "day_element": (
            get_day_master_element(
                day_stem
            )
        ),
        "supporting_elements": (
            supporting_elements
        ),
        "draining_elements": (
            draining_elements
        ),
        "supporting_score": (
            supporting_score
        ),
        "draining_score": (
            draining_score
        ),
        "supporting_ratio": (
            supporting_ratio
        ),
        "draining_ratio": (
            draining_ratio
        ),
        "method": (
            "simple_element_relation_v1"
        ),
        "status": (
            "classification_only"
        ),
        "notes": [
            "単純五行集計を日主との関係で分類しています。",
            "月令、通根、季節補正は未反映です。",
            "この結果だけでは身強・身弱を確定しません。",
        ],
    }
    def classify_weighted_elements_for_day_master(
    day_stem: str,
    weighted_five_elements: dict,
) -> dict:
    """
    重み付き五行スコアを、
    日主を助ける側と弱める側へ分類します。
    """
    scores = weighted_five_elements["scores"]

    supporting_elements = get_supporting_elements(
        day_stem
    )

    draining_elements = get_draining_elements(
        day_stem
    )

    supporting_score = round(
        sum(
            scores[element]
            for element in supporting_elements
        ),
        2,
    )

    draining_score = round(
        sum(
            scores[element]
            for element in draining_elements
        ),
        2,
    )

    total = round(
        supporting_score + draining_score,
        2,
    )

    supporting_ratio = (
        round(
            supporting_score / total * 100,
            2,
        )
        if total
        else 0.0
    )

    draining_ratio = (
        round(
            draining_score / total * 100,
            2,
        )
        if total
        else 0.0
    )

    return {
        "day_stem": day_stem,
        "day_element": get_day_master_element(
            day_stem
        ),
        "supporting_elements": supporting_elements,
        "draining_elements": draining_elements,
        "supporting_score": supporting_score,
        "draining_score": draining_score,
        "supporting_ratio": supporting_ratio,
        "draining_ratio": draining_ratio,
        "method": "weighted_element_relation_v1",
        "status": "provisional_weighted_classification",
        "notes": [
            "重み付き五行スコアを日主との関係で分類しています。",
            "蔵干比率は暫定値です。",
            "月令と季節旺衰は別途評価します。",
        ],
    }


