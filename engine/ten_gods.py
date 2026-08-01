# TODO: ten gods

from engine.constants import (
    CONTROLS,
    GENERATES,
    STEM_ELEMENTS,
    STEMS,
)


def get_element(stem: str) -> str:
    """
    天干の五行を返します。

    例：
        甲 -> 木
        丁 -> 火
        癸 -> 水
    """
    if stem not in STEMS:
        raise ValueError(
            f"不正な天干です: {stem}"
        )

    return STEM_ELEMENTS[stem]["element"]


def get_yin_yang(stem: str) -> str:
    """
    天干の陰陽を返します。

    例：
        甲 -> 陽
        乙 -> 陰
    """
    if stem not in STEMS:
        raise ValueError(
            f"不正な天干です: {stem}"
        )

    return STEM_ELEMENTS[stem]["yin_yang"]


def get_element_relationship(
    day_stem: str,
    target_stem: str,
) -> str:
    """
    日主と対象天干の五行関係を返します。

    same:
        日主と同じ五行

    output:
        日主が生じる五行

    wealth:
        日主が剋す五行

    officer:
        日主を剋す五行

    resource:
        日主を生じる五行
    """
    day_element = get_element(day_stem)
    target_element = get_element(target_stem)

    if day_element == target_element:
        return "same"

    if GENERATES[day_element] == target_element:
        return "output"

    if CONTROLS[day_element] == target_element:
        return "wealth"

    if CONTROLS[target_element] == day_element:
        return "officer"

    if GENERATES[target_element] == day_element:
        return "resource"

    raise ValueError(
        "五行関係を判定できません。"
    )


def calculate_ten_god(
    day_stem: str,
    target_stem: str,
) -> str:
    """
    日主と対象天干から通変星を返します。

    正偏の判定：
    ・比劫と食傷は同性が比肩・食神
    ・財官印は異性が正財・正官・印綬
    """
    relationship = get_element_relationship(
        day_stem,
        target_stem,
    )

    same_polarity = (
        get_yin_yang(day_stem)
        == get_yin_yang(target_stem)
    )

    if relationship == "same":
        return "比肩" if same_polarity else "劫財"

    if relationship == "output":
        return "食神" if same_polarity else "傷官"

    if relationship == "wealth":
        return "偏財" if same_polarity else "正財"

    if relationship == "officer":
        return "偏官" if same_polarity else "正官"

    if relationship == "resource":
        return "偏印" if same_polarity else "印綬"

    raise ValueError(
        "通変星を判定できません。"
    )
