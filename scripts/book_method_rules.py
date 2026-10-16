"""研究用の入口。本どおりの規則の実体は engine/book_rules.py にある。"""

from engine.book_rules import (  # noqa: F401
    SUMMER_TIME_PERIODS,
    BookResult,
    book_hidden_stem,
    book_hidden_stems_for_chart,
    book_hour_pillar,
    days_since_setsuiri,
    in_summer_time,
)
