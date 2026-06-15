"""In-memory state всех MCP-серверов + сидирование при старте.

Никакой БД — всё в dict’ах. State-объекты пересоздаются при импорте,
что нормально для демо (один процесс).
"""
from __future__ import annotations

from datetime import date, datetime
from threading import RLock

from .data.calendar_seed import CalendarEvent, generate_calendar_seed
from .data.class_catalog import Slot, generate_week_slots


class State:
    def __init__(self) -> None:
        self._lock = RLock()
        # Ключ — slot_id; значение — Slot (available=True/False)
        self.slots: dict[str, Slot] = {}
        # Ключ — slot_id; значение — запись о бронировании (для cancel)
        self.bookings: dict[str, dict] = {}
        # Список событий календаря
        self.events: list[CalendarEvent] = []
        self._seeded_for: date | None = None

    def seed(self, reference: date | None = None) -> None:
        ref = reference or date.today()
        with self._lock:
            self.slots = {s.slot_id: s for s in generate_week_slots(ref)}
            self.bookings = {}
            self.events = generate_calendar_seed(ref)
            self._seeded_for = ref

    def book(self, slot_id: str) -> bool:
        """Пометить слот как забронированный. Возвращает True, если успешно."""
        with self._lock:
            s = self.slots.get(slot_id)
            if s is None:
                return False
            if not s.available:
                return False
            object.__setattr__(s, "available", False)  # Slot frozen → меняем через object.__setattr__
            self.slots[slot_id] = s
            self.bookings[slot_id] = {
                "slot_id": slot_id,
                "club_id": s.club_id,
                "class_type": s.class_type,
                "booked_at": datetime.utcnow().isoformat(),
            }
            return True

    def cancel(self, slot_id: str) -> bool:
        with self._lock:
            s = self.slots.get(slot_id)
            if s is None or slot_id not in self.bookings:
                return False
            object.__setattr__(s, "available", True)
            self.slots[slot_id] = s
            del self.bookings[slot_id]
            return True

    def add_event(self, ev: CalendarEvent) -> None:
        with self._lock:
            self.events.append(ev)

    def delete_event(self, event_id: str) -> bool:
        with self._lock:
            for i, e in enumerate(self.events):
                if e.event_id == event_id:
                    del self.events[i]
                    return True
            return False

    def has_conflict(self, start: datetime, end: datetime) -> bool:
        with self._lock:
            for e in self.events:
                if e.start < end and start < e.end:
                    return True
            return False


state = State()
# Lazy seed — будет вызван при первом запросе, чтобы не зависеть от текущей даты в импорте.
