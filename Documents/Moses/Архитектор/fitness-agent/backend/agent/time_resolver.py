"""Парсер времени: понимает «завтра», «в среду», «в среду вечером» и т.п.

Поверх dateparser с дефолтами и нормализацией. Используется и MOCK-провайдером,
и (на будущее) в планировщике OpenAI-агента.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Optional

import dateparser
from dateutil.relativedelta import relativedelta


@dataclass
class ResolvedTime:
    date: date
    time_of_day: Optional[str] = None  # morning|day|evening|None


_RANGES = {
    "morning": (time(5, 0), time(11, 59)),
    "day": (time(12, 0), time(16, 59)),
    "evening": (time(17, 0), time(22, 59)),
}


def resolve_time(text: str, *, ref: datetime | None = None) -> ResolvedTime | None:
    """Парсит произвольный RU/EN-текст с временным указанием."""
    if not text:
        return None
    base = ref or datetime.now()
    parsed = dateparser.parse(
        text,
        languages=["ru", "en"],
        settings={
            "PREFER_DATES_FROM": "future",
            "RELATIVE_BASE": base,
        },
    )
    if not parsed:
        return None
    return ResolvedTime(date=parsed.date())


def time_of_day_from_hour(h: int) -> str:
    if 5 <= h < 12:
        return "morning"
    if 12 <= h < 17:
        return "day"
    if 17 <= h < 23:
        return "evening"
    return "night"
