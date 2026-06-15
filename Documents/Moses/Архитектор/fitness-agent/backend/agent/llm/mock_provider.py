"""MOCK-провайдер: детерминированный ReAct без внешнего API.

Идея: парсим пользовательский запрос rule-based’ом (activity/time_of_day/day)
и эмулируем tool_calls точно так же, как сделал бы OpenAI, но стабильно
и без задержек. Это позволяет демо работать офлайн и быть CI-friendly.

Поддерживаемые сценарии: «хочу <activity> <day> <time_of_day>» (в любом
порядке и опционально).
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta

from ..time_resolver import ResolvedTime, resolve_time
from ...mcp_servers.data.fitness_centers import normalize_activity
from .base import AssistantMessage, LLMProvider, ToolCallRequest


# Простая эвристика: «среда» → 2 (Пн=0)
WEEKDAY_NAMES_RU = {
    "понедельник": 0, "пн": 0,
    "вторник": 1, "вт": 1,
    "среда": 2, "ср": 2, "среду": 2, "среды": 2,
    "четверг": 3, "чт": 3,
    "пятница": 4, "пт": 4, "пятницу": 4,
    "суббота": 5, "сб": 5, "субботу": 5,
    "воскресенье": 6, "вс": 6,
}

TIME_OF_DAY_RU = {
    "утро": "morning", "утром": "morning",
    "день": "day", "днём": "day", "днем": "day",
    "вечер": "evening", "вечером": "evening",
}


def _extract_day_of_week(text: str, ref_date: date) -> date | None:
    t = text.lower()
    for name, dow in WEEKDAY_NAMES_RU.items():
        if re.search(rf"\b{name}\b", t):
            days_ahead = (dow - ref_date.weekday()) % 7
            return ref_date + timedelta(days=days_ahead)
    return None


def _extract_time_of_day(text: str) -> str | None:
    t = text.lower()
    for k, v in TIME_OF_DAY_RU.items():
        if k in t:
            return v
    return None


def _extract_activity(text: str) -> str | None:
    return normalize_activity(text)


class MockProvider(LLMProvider):
    name = "mock"

    def __init__(self, ref_date: date | None = None) -> None:
        self._ref_date = ref_date or date.today()

    async def decide(
        self,
        *,
        system: str,
        history: list[dict],
        tools: list[dict],
    ) -> AssistantMessage:
        # Найти последний user-текст
        user_text = ""
        for m in reversed(history):
            if m.get("role") == "user":
                user_text = m.get("content", "") or ""
                break
        if not user_text:
            return AssistantMessage(content="Не удалось разобрать запрос.")

        # Шаг 1: классифицируем намерение
        if "отмен" in user_text.lower() or "удали" in user_text.lower():
            # В демо просто сообщаем, отмена не реализована в агенте
            return AssistantMessage(
                content="Чтобы отменить бронь, используйте карточку события в календаре."
            )

        activity = _extract_activity(user_text)
        if not activity:
            return AssistantMessage(
                content=(
                    "Я умею бронировать: бассейн (pool), теннис (tennis), йогу (yoga), "
                    "пилатес (pilates), зал (gym), единоборства (martial_arts). "
                    "Уточните, пожалуйста, что хотите."
                )
            )

        time_of_day = _extract_time_of_day(user_text) or "any"
        day = _extract_day_of_week(user_text, self._ref_date) or self._ref_date

        # Шаг 2: генерируем план
        plan = (
            f"План: найти места с типом '{activity}' → проверить слоты на "
            f"{day.isoformat()} ({time_of_day}) → проверить календарь → "
            f"забронировать и создать событие."
        )

        # Шаг 3: первый tool_call — search_places
        tc = ToolCallRequest(
            name="maps_mcp.search_places",
            arguments={"activity": activity, "time_of_day": time_of_day, "date": day.isoformat()},
        )
        return AssistantMessage(
            content=plan,
            tool_calls=[tc],
        )
