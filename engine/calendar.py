from datetime import date, datetime


def parse_date(date_string: str) -> date:
    """
    YYYY-MM-DD文字列をdateへ変換する
    """
    return datetime.strptime(
        date_string,
        "%Y-%m-%d",
    ).date()


def days_between(
    start_date: date,
    end_date: date,
) -> int:
    """
    2つの日付の差(日数)を返す
    """
    return (
        end_date - start_date
    ).days


def add_days(
    target_date: date,
    days: int,
) -> date:
    """
    日付へ日数を加算する
    """
    from datetime import timedelta

    return (
        target_date
        + timedelta(days=days)
    )
