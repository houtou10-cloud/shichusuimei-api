from datetime import date, datetime
from zoneinfo import ZoneInfo

from engine.five_elements import calculate_five_elements
from engine.pillars import calculate_four_pillars


JST = ZoneInfo("Asia/Tokyo")


def normalize_birth_date(
    value: str | date,
) -> str:
    """
    birth_dateをYYYY-MM-DD形式の文字列へ統一します。
    """
    if isinstance(value, date):
        return value.isoformat()

    if isinstance(value, str):
        try:
            datetime.strptime(
                value,
                "%Y-%m-%d",
            )
        except ValueError as error:
            raise ValueError(
                "birth_dateはYYYY-MM-DD形式で指定してください。"
            ) from error

        return value

    raise TypeError(
        "birth_dateは文字列またはdate型で指定してください。"
    )


def normalize_birth_time(
    value: str | None,
) -> str | None:
    """
    birth_timeをHH:MM形式として検証します。
    """
    if value is None:
        return None

    if not isinstance(value, str):
        raise TypeError(
            "birth_timeはHH:MM形式の文字列で指定してください。"
        )

    try:
        datetime.strptime(
            value,
            "%H:%M",
        )
    except ValueError as error:
        raise ValueError(
            "birth_timeはHH:MM形式で指定してください。"
        ) from error

    return value


def calculate_chart(req) -> dict:
    """
    APIの入力情報から四柱を計算し、
    GPT Actionsへ返すデータを作成します。
    """
    birth_date = normalize_birth_date(
        req.birth_date
    )

    birth_time = normalize_birth_time(
        req.birth_time
    )

    warnings: list[str] = []

    if birth_time is None:
        # 出生時間不明の場合は、
        # 日付計算のため仮に正午を使用します。
        time_text = "12:00"

        warnings.append(
            "出生時間が不明なため、時柱は計算していません。"
        )
    else:
        time_text = birth_time

    birth_datetime = datetime.strptime(
        f"{birth_date} {time_text}",
        "%Y-%m-%d %H:%M",
    ).replace(
        tzinfo=JST
    )

    pillars = calculate_four_pillars(
        birth_datetime
    )

    if birth_time is None:
        pillars["hour"] = None

    five_elements = calculate_five_elements(
        {
            "year": pillars["year"],
            "month": pillars["month"],
            "day": pillars["day"],
            "hour": pillars["hour"],
        }
    )

    warnings.extend(
        pillars.get(
            "warnings",
            [],
        )
    )

    return {
        "input": {
            "birth_date": birth_date,
            "birth_time": birth_time,
            "birth_place": req.birth_place,
            "gender": req.gender,
            "timezone": "Asia/Tokyo",
        },
        "chart": {
            "year": pillars["year"],
            "month": pillars["month"],
            "day": pillars["day"],
            "hour": pillars["hour"],
        },
        "day_master": pillars["day_master"],
        "five_elements": five_elements,
        "calculation_rules": (
            pillars["calculation_rules"]
        ),
        "calculation_status": (
            pillars["calculation_status"]
        ),
        "warnings": warnings,
    }
