"""Базовый календарь пользователя — предзаполненные события на текущую неделю.

В демо мы не различаем пользователей, поэтому календарь один. В реальном
Google Calendar-аналоге это был бы конкретный user_id.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta


@dataclass(frozen=True)
class CalendarEvent:
    event_id: str
    title: str
    start: datetime
    end: datetime
    location: str
    description: str
    source: str = "seed"  # "seed" | "agent"


def _monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())


def generate_calendar_seed(reference: date) -> list[CalendarEvent]:
    monday = _monday_of(reference)
    out: list[CalendarEvent] = []

    def add(idx: int, day_off: int, t: time, dur_min: int, title: str, loc: str, desc: str) -> None:
        d = monday + timedelta(days=day_off)
        start = datetime.combine(d, t)
        end = start + timedelta(minutes=dur_min)
        out.append(
            CalendarEvent(
                event_id=f"seed_{idx}",
                title=title,
                start=start,
                end=end,
                location=loc,
                description=desc,
            )
        )

    # Рабочие будни: работа 9-18 с обедом 13-14
    for d in range(0, 5):
        add(100 + d, d, time(9, 0), 240, "Работа: фокус-блок", "Офис", "Глубокая работа над задачами")
        add(200 + d, d, time(13, 0), 60, "Обед", "Кафе рядом с офисом", "Обеденный перерыв")
        add(300 + d, d, time(14, 0), 240, "Работа: встречи и код", "Офис", "Созвоны и ревью")

    # Дорога утром/вечером
    for d in range(0, 5):
        add(400 + d, d, time(8, 0), 30, "Дорога на работу", "", "Метро + пешком")
        add(500 + d, d, time(18, 30), 30, "Дорога домой", "", "Метро + пешком")

    # Встречи (выборочно)
    add(601, 0, time(11, 0), 30, "Stand-up", "Zoom", "Ежедневный синк")
    add(602, 2, time(15, 0), 60, "Ревью проекта", "Переговорка 3", "Обсуждение MVP")
    add(603, 4, time(11, 30), 30, "1:1 с руководителем", "Zoom", "Синк 1:1")

    # Утренние/вечерние ритуалы
    for d in range(0, 7):
        add(700 + d, d, time(7, 0), 30, "Утренняя рутина", "Дом", "Зарядка, кофе")
        add(800 + d, d, time(22, 30), 30, "Вечерняя рутина", "Дом", "Чтение, подготовка ко сну")

    return out
