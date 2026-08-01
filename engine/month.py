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
