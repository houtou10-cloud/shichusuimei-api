from datetime import datetime

from engine.ganzhi import ganzhi_from_index


# 1984年は甲子年
BASE_YEAR = 1984
BASE_YEAR_GANZHI_INDEX = 0


def calculate_effective_year(
    birth_datetime: datetime,
) -> int:
    """
    年柱計算に使用する干支年を返します。

    暫定ルール：
    ・立春は毎年2月4日00:00とする
    ・立春より前は前年の干支年として扱う

    注意：
    実際の立春時刻は年によって異なるため、
    後で天文計算による正確な時刻へ置き換えます。
    """
    if not isinstance(birth_datetime, datetime):
        raise TypeError(
            "birth_datetimeはdatetime型で指定してください。"
        )

    provisional_lichun = datetime(
        birth_datetime.year,
        2,
        4,
        0,
        0,
        tzinfo=birth_datetime.tzinfo,
    )

    if birth_datetime < provisional_lichun:
        return birth_datetime.year - 1

    return birth_datetime.year


def calculate_year_pillar(
    birth_datetime: datetime,
) -> str:
    """
    出生日時から年柱を計算します。

    1984年の甲子を基準に、
    60干支を循環させます。
    """
    effective_year = calculate_effective_year(
        birth_datetime
    )

    elapsed_years = effective_year - BASE_YEAR

    ganzhi_index = (
        BASE_YEAR_GANZHI_INDEX + elapsed_years
    )

    return ganzhi_from_index(ganzhi_index)


def is_near_provisional_lichun(
    birth_datetime: datetime,
    margin_days: int = 2,
) -> bool:
    """
    暫定立春日の前後に該当するか判定します。

    正確な節入り時刻が未実装のため、
    2月2日～2月6日付近では警告に使用します。
    """
    if margin_days < 0:
        raise ValueError(
            "margin_daysは0以上で指定してください。"
        )

    provisional_lichun = datetime(
        birth_datetime.year,
        2,
        4,
        0,
        0,
        tzinfo=birth_datetime.tzinfo,
    )

    difference = abs(
        birth_datetime - provisional_lichun
    )

    return difference.days <= margin_days
