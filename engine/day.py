from datetime import date

from engine.calendar import days_between
from engine.ganzhi import ganzhi_from_index


# 検証済み基準日
# 1984年7月21日 = 甲辰
BASE_DATE = date(1984, 7, 21)

# 甲辰は六十干支の0始まりで40番
BASE_GANZHI_INDEX = 40


def calculate_day_pillar(target_date: date) -> str:
    """
    指定された日付の日柱を返します。

    採用ルール:
    ・日柱の切り替えは午前0時
    ・日本標準時を前提
    """
    elapsed_days = days_between(
        BASE_DATE,
        target_date,
    )

    target_index = (
        BASE_GANZHI_INDEX + elapsed_days
    )

    return ganzhi_from_index(target_index)
