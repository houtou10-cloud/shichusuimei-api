from datetime import datetime
from zoneinfo import ZoneInfo

from skyfield import almanac
from skyfield.api import load


JST = ZoneInfo("Asia/Tokyo")

SOLAR_TERMS = [
    "春分",
    "夏至",
    "秋分",
    "冬至",
]


def get_season_events(year: int) -> list[dict]:
    """
    指定年の春分・夏至・秋分・冬至を日本時間で返します。
    """
    ts = load.timescale()
    eph = load("de421.bsp")

    start = ts.utc(year, 1, 1)
    end = ts.utc(year + 1, 1, 1)

    times, events = almanac.find_discrete(
        start,
        end,
        almanac.seasons(eph),
    )

    results = []

    for time, event in zip(times, events):
        utc_datetime = time.utc_datetime()
        jst_datetime = utc_datetime.astimezone(JST)

        results.append({
            "name": SOLAR_TERMS[int(event)],
            "datetime": jst_datetime.isoformat(),
        })

    return results
