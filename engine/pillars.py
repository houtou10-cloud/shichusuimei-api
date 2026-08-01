# TODO: pillar calculation

from datetime import datetime

from engine.day import calculate_day_pillar
from engine.ganzhi import split_ganzhi
from engine.hour import calculate_hour_pillar
from engine.month import calculate_month_pillar
from engine.year import (
    calculate_year_pillar,
    is_near_provisional_lichun,
)


def build_pillar_data(pillar: str) -> dict[str, str]:
    """
    「甲子」のような干支を、
    天干・地支を含む辞書形式へ変換します。
    """
    parts = split_ganzhi(pillar)

    return {
        "pillar": pillar,
        "stem": parts["stem"],
        "branch": parts["branch"],
    }


def calculate_four_pillars(
    birth_datetime: datetime,
) -> dict:
    """
    出生日時から四柱を計算します。

    現在の計算ルール：
    ・年柱は暫定立春日を使用
    ・月柱は固定の節入り日を使用
    ・日柱の切り替えは午前0時
    ・時柱は入力時刻をそのまま使用
    ・真太陽時補正は未実装
    """
    if not isinstance(birth_datetime, datetime):
        raise TypeError(
            "birth_datetimeはdatetime型で指定してください。"
        )

    year_pillar = calculate_year_pillar(
        birth_datetime
    )

    year_stem = year_pillar[0]

    month_pillar = calculate_month_pillar(
        birth_datetime,
        year_stem,
    )

    day_pillar = calculate_day_pillar(
        birth_datetime.date()
    )

    day_stem = day_pillar[0]

    hour_pillar = calculate_hour_pillar(
        day_stem,
        birth_datetime.hour,
    )

    warnings: list[str] = []

    if is_near_provisional_lichun(
        birth_datetime
    ):
        warnings.append(
            "立春付近の出生です。"
            "現在は2月4日午前0時を暫定境界としているため、"
            "年柱は正式版で変わる可能性があります。"
        )

    if birth_datetime.day in {
        4,
        5,
        6,
        7,
        8,
    }:
        warnings.append(
            "節入り日前後の出生です。"
            "現在の月柱は固定日による暫定計算のため、"
            "正式な節入り時刻の実装後に変わる可能性があります。"
        )

    return {
        "year": build_pillar_data(
            year_pillar
        ),
        "month": build_pillar_data(
            month_pillar
        ),
        "day": build_pillar_data(
            day_pillar
        ),
        "hour": build_pillar_data(
            hour_pillar
        ),
        "day_master": {
            "stem": day_stem,
        },
        "calculation_rules": {
            "year_boundary": (
                "暫定：2月4日00:00"
            ),
            "month_boundary": (
                "暫定：固定節入り日"
            ),
            "day_boundary": "00:00",
            "hour_boundary": (
                "子刻は23:00～00:59"
            ),
            "time_adjustment": (
                "標準時・真太陽時補正なし"
            ),
        },
        "calculation_status": (
            "provisional_four_pillars"
        ),
        "warnings": warnings,
    }
