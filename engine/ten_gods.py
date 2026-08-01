from engine.constants import (
    CONTROLS,
    GENERATES,
    STEM_ELEMENTS,
    STEMS,
)


def get_element(stem: str) -> str:
    """
    天干の五行を返します。
    """
    if stem not in STEMS:
        raise ValueError(
            f"不正な天干です: {stem}"
        )

    return STEM_ELEMENTS[stem]["element"]


def get_yin_yang(stem: str) -> str:
    """
    天干の陰陽を返します。
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
