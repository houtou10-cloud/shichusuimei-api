from datetime import date

from engine.calendar import days_between
from engine.ganzhi import ganzhi_from_index


# ============================================================
# 日柱計算
# ============================================================
#
# 検証済み基準日：
#
# 1984年7月10日 = 乙巳
#
# この検証済み命式を最優先の基準とします。
#
# 六十干支を0始まりで数えると、
#
# 0  = 甲子
# 1  = 乙丑
# ...
# 41 = 乙巳
# ...
# 52 = 丙辰
# 53 = 丁巳
# ...
# 59 = 癸亥
#
# 1984年7月10日から11日後の
# 1984年7月21日は丙辰となるため、
#
# 1984年7月21日 = index 52
#
# を計算上の基準日として採用します。
#
# 採用ルール：
# ・日柱の切り替えは午前0時
# ・日本標準時（JST）の日付を前提とする
#
# 注意：
# 四柱推命には「23時で日柱を切り替える」
# 流派もありますが、このエンジンでは
# 午前0時切り替えを正式ルールとして採用します。
#
# 回帰基準：
# ・1984年7月10日 = 乙巳
# ・1984年7月21日 = 丙辰
# ・1984年7月22日 = 丁巳
#
# ============================================================


BASE_DATE = date(
    1984,
    7,
    21,
)

# 丙辰は六十干支の0始まりで52番
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
        「乙巳」「丙辰」「丁巳」などの六十干支。

    採用ルール
    ----------
    ・日柱の切り替えは午前0時
    ・日本標準時（JST）の日付を前提とする
    ・1984年7月21日 = 丙辰を計算基準とする

    回帰確認
    ----------
    1984年7月10日
        -> 乙巳

    1984年7月21日
        -> 丙辰

    1984年7月22日
        -> 丁巳
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
