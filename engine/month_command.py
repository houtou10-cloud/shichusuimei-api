from engine.constants import (
    BRANCH_ELEMENTS,
    CONTROLS,
    GENERATES,
    STEM_ELEMENTS,
    STEMS,
)


def get_day_element(
    day_stem: str,
) -> str:
    """
    日干から日主の五行を返します。
    """
    if day_stem not in STEMS:
        raise ValueError(
            f"不正な日干です: {day_stem}"
        )

    return STEM_ELEMENTS[day_stem]["element"]


def get_month_element(
    month_branch: str,
) -> str:
    """
    月支の五行を返します。
    """
    if month_branch not in BRANCH_ELEMENTS:
        raise ValueError(
            f"不正な月支です: {month_branch}"
        )

    return BRANCH_ELEMENTS[month_branch]


def classify_month_relationship(
    day_stem: str,
    month_branch: str,
) -> dict:
    """
    月支の五行と日主の関係を分類します。

    現段階では月支そのものの五行だけを使用します。
    蔵干構成や土用、季節旺衰の細分化は未実装です。
    """
    day_element = get_day_element(
        day_stem
    )

    month_element = get_month_element(
        month_branch
    )

    if month_element == day_element:
        relationship = "same"
        label = "比劫"
        effect = "supporting"

    elif GENERATES[month_element] == day_element:
        relationship = "resource"
        label = "印星"
        effect = "supporting"

    elif GENERATES[day_element] == month_element:
        relationship = "output"
        label = "食傷"
        effect = "draining"

    elif CONTROLS[day_element] == month_element:
        relationship = "wealth"
        label = "財星"
        effect = "draining"

    elif CONTROLS[month_element] == day_element:
        relationship = "officer"
        label = "官殺"
        effect = "controlling"

    else:
        raise ValueError(
            "月令との五行関係を判定できません。"
        )

    return {
        "day_stem": day_stem,
        "day_element": day_element,
        "month_branch": month_branch,
        "month_element": month_element,
        "relationship": relationship,
        "relationship_label": label,
        "effect": effect,
        "supports_day_master": (
            effect == "supporting"
        ),
        "method": "month_branch_element_v1",
        "status": "provisional_month_command",
        "notes": [
            "月支の代表五行と日主の関係を分類しています。",
            "月支蔵干の配分や土用期間は未反映です。",
            "この結果だけでは身強・身弱を確定しません。",
        ],
    }
