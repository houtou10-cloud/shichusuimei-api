from datetime import datetime

# 暫定の節入り日
#
# 後でSkyfieldに置き換える
#
# 月番号 : (開始月, 開始日, 月支)
#
SOLAR_MONTHS = [
    (2, 4, "寅"),
    (3, 6, "卯"),
    (4, 5, "辰"),
    (5, 6, "巳"),
    (6, 6, "午"),
    (7, 7, "未"),
    (8, 8, "申"),
    (9, 8, "酉"),
    (10, 8, "戌"),
    (11, 8, "亥"),
    (12, 7, "子"),
    (1, 6, "丑"),
]


def calculate_month_branch(
    birth_datetime: datetime,
) -> str:
    """
    暫定版

    節入り日だけ固定値で判定する。
    """

    month = birth_datetime.month
    day = birth_datetime.day

    # 1月
    if month == 1:
        if day >= 6:
            return "丑"
        return "子"

    # 2〜12月
    for i in range(len(SOLAR_MONTHS) - 1):

        start_month, start_day, branch = SOLAR_MONTHS[i]
        next_month, next_day, _ = SOLAR_MONTHS[i + 1]

        if month == start_month:

            if day >= start_day:
                return branch

        if start_month < month < next_month:
            return branch

    # 12月
    if month == 12:
        if day >= 7:
            return "子"

    return "丑"


from engine.constants import BRANCHES, STEMS


# 年干ごとの寅月の開始天干
#
# 甲・己年：丙寅
# 乙・庚年：戊寅
# 丙・辛年：庚寅
# 丁・壬年：壬寅
# 戊・癸年：甲寅
TIGER_MONTH_STEM_START = {
    "甲": 2,
    "己": 2,
    "乙": 4,
    "庚": 4,
    "丙": 6,
    "辛": 6,
    "丁": 8,
    "壬": 8,
    "戊": 0,
    "癸": 0,
}


MONTH_BRANCH_ORDER = [
    "寅",
    "卯",
    "辰",
    "巳",
    "午",
    "未",
    "申",
    "酉",
    "戌",
    "亥",
    "子",
    "丑",
]


def calculate_month_stem(
    year_stem: str,
    month_branch: str,
) -> str:
    """
    年干と月支から月干を計算します。
    五虎遁を使用します。
    """
    if year_stem not in STEMS:
        raise ValueError(
            f"不正な年干です: {year_stem}"
        )

    if month_branch not in MONTH_BRANCH_ORDER:
        raise ValueError(
            f"不正な月支です: {month_branch}"
        )

    branch_index = MONTH_BRANCH_ORDER.index(
        month_branch
    )

    starting_stem_index = (
        TIGER_MONTH_STEM_START[year_stem]
    )

    stem_index = (
        starting_stem_index + branch_index
    ) % 10

    return STEMS[stem_index]


def calculate_month_pillar(
    birth_datetime: datetime,
    year_stem: str,
) -> str:
    """
    出生日時と年干から月柱を計算します。

    現在は固定の節入り日を使用する暫定版です。
    """
    month_branch = calculate_month_branch(
        birth_datetime
    )

    month_stem = calculate_month_stem(
        year_stem,
        month_branch,
    )

    return month_stem + month_branch
