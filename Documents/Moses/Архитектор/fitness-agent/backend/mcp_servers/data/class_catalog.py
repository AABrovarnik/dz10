"""Каталог занятий и расписание слотов.

Каждый клуб имеет набор class_type → список шаблонов слотов по дням недели.
В демо-режиме мы генерируем слоты на текущую неделю (Пн–Вс).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Iterable


# (club_id, class_type) → список (day_of_week, time, duration_min, title)
SLOT_TEMPLATES: dict[tuple[str, str], list[tuple[int, time, int, str]]] = {
    # fit_1 — gym, pool, yoga
    ("fit_1", "pool"): [
        (0, time(7, 0), 60, "Утреннее плавание"),
        (0, time(19, 0), 60, "Вечерний бассейн"),
        (2, time(7, 0), 60, "Утреннее плавание"),
        (2, time(19, 0), 60, "Вечерний бассейн"),
        (4, time(7, 0), 60, "Утреннее плавание"),
        (5, time(10, 0), 60, "Субботний бассейн"),
    ],
    ("fit_1", "gym"): [
        (0, time(18, 0), 90, "Силовая тренировка"),
        (1, time(18, 0), 90, "Силовая тренировка"),
        (2, time(18, 0), 90, "Силовая тренировка"),
        (3, time(19, 0), 90, "Вечерняя силовая"),
        (4, time(18, 0), 90, "Силовая тренировка"),
    ],
    ("fit_1", "yoga"): [
        (6, time(10, 0), 75, "Воскресная йога"),
        (3, time(20, 0), 75, "Вечерняя йога"),
    ],
    # fit_2 — tennis, gym
    ("fit_2", "tennis"): [
        (1, time(19, 0), 60, "Тренировка по теннису"),
        (2, time(19, 0), 60, "Тренировка по теннису"),
        (2, time(20, 0), 60, "Вечерний теннис (вт)"),
        (3, time(19, 0), 60, "Тренировка по теннису"),
        (3, time(20, 0), 60, "Вечерний теннис (ср)"),
        (4, time(20, 0), 60, "Вечерний теннис (чт)"),
        (5, time(11, 0), 90, "Субботний теннис"),
        (6, time(11, 0), 90, "Воскресный теннис"),
    ],
    ("fit_2", "gym"): [
        (0, time(8, 0), 60, "Утренняя тренировка"),
        (2, time(20, 0), 60, "Вечерняя тренировка"),
    ],
    # fit_3 — pool, yoga
    ("fit_3", "pool"): [
        (1, time(7, 0), 60, "Утренний бассейн"),
        (1, time(20, 0), 60, "Вечерний бассейн"),
        (3, time(7, 0), 60, "Утренний бассейн"),
        (3, time(20, 0), 60, "Вечерний бассейн"),
        (5, time(9, 0), 75, "Длинный бассейн"),
    ],
    ("fit_3", "yoga"): [
        (0, time(19, 0), 75, "Вечерняя йога"),
        (4, time(19, 0), 75, "Вечерняя йога"),
    ],
    # fit_4 — martial_arts, gym
    ("fit_4", "martial_arts"): [
        (0, time(20, 0), 90, "Бокс для взрослых"),
        (1, time(20, 0), 90, "Бокс для взрослых"),
        (2, time(20, 0), 90, "Карате"),
        (3, time(20, 0), 90, "ММА"),
        (4, time(20, 0), 90, "Бокс для взрослых"),
    ],
    ("fit_4", "gym"): [
        (5, time(11, 0), 60, "Субботний зал"),
    ],
    # fit_5 — yoga, pilates
    ("fit_5", "yoga"): [
        (0, time(8, 0), 75, "Утренняя йога"),
        (1, time(8, 0), 75, "Утренняя йога"),
        (2, time(8, 0), 75, "Утренняя йога"),
        (3, time(8, 0), 75, "Утренняя йога"),
        (4, time(8, 0), 75, "Утренняя йога"),
        (5, time(10, 0), 90, "Субботняя йога"),
        (6, time(10, 0), 90, "Воскресная йога"),
    ],
    ("fit_5", "pilates"): [
        (0, time(19, 0), 60, "Пилатес вечер"),
        (2, time(19, 0), 60, "Пилатес вечер"),
    ],
    # fit_6 — gym, pool, tennis
    ("fit_6", "gym"): [
        (0, time(7, 0), 60, "Утренний зал"),
        (3, time(19, 0), 60, "Вечерний зал"),
    ],
    ("fit_6", "pool"): [
        (5, time(11, 0), 60, "Семейный бассейн"),
    ],
    ("fit_6", "tennis"): [
        (1, time(20, 0), 60, "Вечерний теннис"),
        (3, time(20, 0), 60, "Вечерний теннис"),
    ],
    # fit_7 — martial_arts
    ("fit_7", "martial_arts"): [
        (1, time(19, 0), 90, "Кикбоксинг"),
        (3, time(19, 0), 90, "Тайский бокс"),
        (5, time(12, 0), 90, "Спарринги"),
    ],
    # fit_8 — pilates, yoga
    ("fit_8", "pilates"): [
        (0, time(19, 0), 60, "Пилатес на реформере"),
        (2, time(19, 0), 60, "Пилатес на реформере"),
        (4, time(19, 0), 60, "Пилатес на реформере"),
    ],
    ("fit_8", "yoga"): [
        (1, time(20, 0), 60, "Хатха-йога"),
        (5, time(11, 0), 75, "Субботняя йога"),
    ],
    # fit_9 — pool, gym
    ("fit_9", "pool"): [
        (0, time(8, 0), 60, "Утренний бассейн"),
        (2, time(8, 0), 60, "Утренний бассейн"),
        (4, time(8, 0), 60, "Утренний бассейн"),
        (6, time(10, 0), 75, "Воскресный бассейн"),
    ],
    ("fit_9", "gym"): [
        (1, time(19, 0), 60, "Вечерний зал"),
        (3, time(19, 0), 60, "Вечерний зал"),
    ],
    # fit_10 — tennis, gym
    ("fit_10", "tennis"): [
        (0, time(20, 0), 60, "Вечерний теннис"),
        (2, time(20, 0), 60, "Вечерний теннис"),
        (4, time(20, 0), 60, "Вечерний теннис"),
        (6, time(11, 0), 90, "Воскресный теннис"),
    ],
    ("fit_10", "gym"): [
        (1, time(8, 0), 60, "Утренний зал"),
    ],
}


@dataclass(frozen=True)
class Slot:
    slot_id: str
    club_id: str
    class_type: str
    title: str
    start: datetime
    end: datetime
    available: bool = True


def _monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())


def generate_week_slots(reference: date) -> list[Slot]:
    """Сгенерировать слоты на неделю, начинающуюся с понедельника `reference`."""
    monday = _monday_of(reference)
    out: list[Slot] = []
    for (club_id, class_type), templates in SLOT_TEMPLATES.items():
        for dow, t, dur, title in templates:
            day = monday + timedelta(days=dow)
            start = datetime.combine(day, t)
            end = start + timedelta(minutes=dur)
            slot_id = f"{club_id}_{class_type}_{start.isoformat()}"
            out.append(
                Slot(
                    slot_id=slot_id,
                    club_id=club_id,
                    class_type=class_type,
                    title=title,
                    start=start,
                    end=end,
                )
            )
    return out


def filter_slots(
    slots: Iterable[Slot],
    *,
    class_type: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    time_of_day: str | None = None,
) -> list[Slot]:
    """Фильтр по типу, диапазону дат и времени суток (morning|day|evening)."""
    out = []
    for s in slots:
        if class_type and s.class_type != class_type:
            continue
        if date_from and s.start.date() < date_from:
            continue
        if date_to and s.start.date() > date_to:
            continue
        if time_of_day:
            h = s.start.hour
            if time_of_day == "morning" and not (5 <= h < 12):
                continue
            if time_of_day == "day" and not (12 <= h < 17):
                continue
            if time_of_day == "evening" and not (17 <= h < 23):
                continue
        out.append(s)
    return out
