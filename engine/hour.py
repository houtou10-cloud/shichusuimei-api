from engine.constants import BRANCHES, STEMS


# 日干ごとの「子の刻」の時干
#
# 甲・己日：甲子
# 乙・庚日：丙子
# 丙・辛日：戊子
# 丁・壬日：庚子
# 戊・癸日：壬子
HOUR_STEM_START_INDEX = {
    "甲": 0,
    "己": 0,
    "乙": 2,
    "庚": 2,
    "丙": 4,
    "辛": 4,
    "丁": 6,
    "壬": 6,
    "戊": 8,
    "癸": 8,
}


def calculate_hour_branch_index(hour: int) -> int:
    """
    出生時刻の「時」から時支の番号を返します。

    0: 子
    1: 丑
    2: 寅
    ...
    11: 亥

    採用する時刻区分：
    子：23:00～00:59
    丑：01:00～02:59
    寅：03:00～04:59
    ...
    亥：21:00～22:59
    """
    if not isinstance(hour, int):
        raise TypeError("hourは整数で指定してください。")

    if not 0 <= hour <= 23:
        raise ValueError("hourは0～23の範囲で指定してください。")

    return ((hour + 1) // 2) % 12


def calculate_hour_branch(hour: int) -> str:
    """
    出生時刻から時支を返します。
    """
    branch_index = calculate_hour_branch_index(hour)

    return BRANCHES[branch_index]


def calculate_hour_pillar(
    day_stem: str,
    hour: int,
) -> str:
    """
    日干と出生時刻から時柱を計算します。

    この段階では出生地による真太陽時補正を行わず、
    入力された日本標準時をそのまま使用します。
    """
    if day_stem not in STEMS:
        raise ValueError(
            f"不正な日干です: {day_stem}"
        )

    branch_index = calculate_hour_branch_index(hour)
    starting_stem_index = HOUR_STEM_START_INDEX[day_stem]

    stem_index = (
        starting_stem_index + branch_index
    ) % 10

    stem = STEMS[stem_index]
    branch = BRANCHES[branch_index]

    return stem + branch
