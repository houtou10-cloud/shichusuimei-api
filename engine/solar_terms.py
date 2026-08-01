from datetime import datetime
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")

SOLAR_TERMS = [
    "小寒",
    "大寒",
    "立春",
    "雨水",
    "啓蟄",
    "春分",
    "清明",
    "穀雨",
    "立夏",
    "小満",
    "芒種",
    "夏至",
    "小暑",
    "大暑",
    "立秋",
    "処暑",
    "白露",
    "秋分",
    "寒露",
    "霜降",
    "立冬",
    "小雪",
    "大雪",
    "冬至",
]


def get_solar_terms(year: int):
    """
    将来的にSkyfieldで24節気を計算する。
    今は空データを返す。
    """
    return []
