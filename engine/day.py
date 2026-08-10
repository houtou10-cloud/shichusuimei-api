from datetime import date

from engine.calendar import days_between
from engine.ganzhi import ganzhi_from_index


# ============================================================
# 日柱計算
# ============================================================
#
# 検証済み基準日：
#
#   1984年7月21日 = 丙辰
#
# 六十干支を0始まりで数えると、
#
#   0  = 甲子
#   1  = 乙丑
#   ...
#   40 = 甲辰
#   41 = 乙巳
#   42 = 丙午
#   ...
#   52 = 丙辰
#   ...
#   59 = 癸亥
#
# したがって、
#
#   1984年7月21日 = index 52
#
# を日柱計算の基準とします。
#
# 採用ルール：
# ・日柱の切り替えは午前0時
# ・日本標準時（JST）の日付を前提とする
#
# 注意：
# 四柱推命には「23時で日柱を切り替える」
# 流派もありますが、このエンジンでは
# 午前0時切り替えを正式ルールとして採用します。
# ============================================================


BASE_DATE = date(1984, 7, 21)

BASE_GANZHI_INDEX = 52


def calculate_day_pillar(
    target_date: date,
) -> str:
    """
    指定された日付の日柱を返します。

    Parameters
    ----------
    target_date : date
        日柱を計算する対象日。

    Returns
    -------
    str
        「乙巳」「丙辰」などの六十干支。

    採用ルール
    ----------
    ・日柱の切り替えは午前0時
    ・日本標準時の日付を前提とする
    ・1984年7月21日 = 丙辰を基準日とする

    Examples
    --------
    1984年7月10日
        -> 乙巳

    1984年7月21日
        -> 丙辰
    """

    if not isinstance(
        target_date,
        date,
    ):
        raise TypeError(
            "target_dateはdate型で指定してください。"
        )

    elapsed_days = days_between(
        BASE_DATE,
        target_date,
    )

    target_index = (
        BASE_GANZHI_INDEX
        + elapsed_days
    )

    return ganzhi_from_index(
        target_index
    )
