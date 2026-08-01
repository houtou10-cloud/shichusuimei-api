from datetime import date

from engine.constants import STEMS, BRANCHES


# 検証済み基準日
# 1984年7月21日 = 甲辰
BASE_DATE = date(1984, 7, 21)

# 甲辰は六十干支の40番目
# 0始まりでは40
BASE_INDEX = 40


def ganzhi_from_index(index: int) -> str:
    """
    0〜59の番号から六十干支を返します。
    """
    stem = STEMS[index % 10]
    branch = BRANCHES[index % 12]

    return stem + branch


def calculate_day_pillar(target_date: date) -> str:
    """
    指定日の日柱を計算します。

    採用ルール：
    ・日付変更は0時
    ・日本標準時を前提
    """
    days_difference = (target_date - BASE_DATE).days
    index = (BASE_INDEX + days_difference) % 60

    return ganzhi_from_index(index)
