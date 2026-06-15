"""MCP #3: календарь (аналог Google Calendar).

GET  /mcp/calendar/tools
POST /mcp/calendar/call
"""
from __future__ import annotations

import time
import uuid
from datetime import date, datetime, timedelta
from typing import Any

from fastapi import APIRouter

from ..mcp_servers.data.calendar_seed import CalendarEvent
from ..mcp_servers.state import state
from ..mcp.base import (
    CallRequest,
    CallResponse,
    Tool,
    ToolsResponse,
    err,
    make_response,
    make_trace_id,
)


router = APIRouter(prefix="/mcp/calendar", tags=["mcp: calendar"])

TOOLS = ToolsResponse(
    name="calendar_mcp",
    description="Календарь пользователя: проверка слотов, создание и удаление событий.",
    tools=[
        Tool(
            name="get_free_slots",
            description=(
                "Свободные окна в календаре на дату (длительность по умолчанию 60 мин). "
                "Возвращает список интервалов между занятыми событиями."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "ISO YYYY-MM-DD"},
                    "duration_min": {"type": "number", "default": 60, "minimum": 15, "maximum": 240},
                    "workday_start": {"type": "string", "default": "07:00"},
                    "workday_end": {"type": "string", "default": "23:00"},
                },
                "required": ["date"],
            },
        ),
        Tool(
            name="create_event",
            description="Создать событие. Возвращает event_id и ok=true/false (если конфликт).",
            input_schema={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "start": {"type": "string", "description": "ISO datetime"},
                    "end": {"type": "string", "description": "ISO datetime"},
                    "location": {"type": "string"},
                    "description": {"type": "string"},
                },
                "required": ["title", "start", "end"],
            },
        ),
        Tool(
            name="delete_event",
            description="Удалить событие по event_id.",
            input_schema={
                "type": "object",
                "properties": {"event_id": {"type": "string"}},
                "required": ["event_id"],
            },
        ),
        Tool(
            name="list_events",
            description="Получить все события на неделю, содержащую date (опц.).",
            input_schema={
                "type": "object",
                "properties": {
                    "date": {"type": "string"},
                    "date_from": {"type": "string"},
                    "date_to": {"type": "string"},
                },
            },
        ),
    ],
)


@router.get("/tools", response_model=ToolsResponse)
async def get_tools() -> ToolsResponse:
    _ensure_seeded()
    return TOOLS


@router.post("/call", response_model=CallResponse)
async def call(req: CallRequest) -> CallResponse:
    _ensure_seeded()
    started = time.time()
    trace_id = make_trace_id(req.trace_id)
    try:
        if req.tool == "get_free_slots":
            return _get_free_slots(req.arguments, trace_id, started)
        if req.tool == "create_event":
            return _create_event(req.arguments, trace_id, started)
        if req.tool == "delete_event":
            return _delete_event(req.arguments, trace_id, started)
        if req.tool == "list_events":
            return _list_events(req.arguments, trace_id, started)
        return make_response(trace_id=trace_id, started=started, error=err("BAD_TOOL", f"Unknown tool: {req.tool}"))
    except Exception as exc:  # noqa: BLE001
        return make_response(
            trace_id=trace_id,
            started=started,
            error=err("INTERNAL", f"{type(exc).__name__}: {exc}"),
        )


# ---------- handlers ----------

def _get_free_slots(args: dict, trace_id: str, started: float) -> CallResponse:
    d = _parse_date(args.get("date"))
    if not d:
        return make_response(trace_id=trace_id, started=started, error=err("BAD_ARGS", "date is required"))
    duration = int(args.get("duration_min", 60))
    wd_start = _parse_time(args.get("workday_start", "07:00"))
    wd_end = _parse_time(args.get("workday_end", "23:00"))
    if wd_start is None or wd_end is None:
        return make_response(trace_id=trace_id, started=started, error=err("BAD_ARGS", "bad workday bounds"))

    day_start = datetime.combine(d, wd_start)
    day_end = datetime.combine(d, wd_end)
    busy = sorted(
        [e for e in state.events if e.start.date() == d or e.end.date() == d],
        key=lambda e: e.start,
    )
    free: list[dict] = []
    cursor = day_start
    for e in busy:
        if e.start > cursor:
            free.append(_slice_free(cursor, e.start, duration))
        cursor = max(cursor, e.end)
    if cursor < day_end:
        free.append(_slice_free(cursor, day_end, duration))
    flat: list[dict] = []
    for chunk in free:
        flat.extend(chunk)
    return make_response(trace_id=trace_id, started=started, result={"date": d.isoformat(), "duration_min": duration, "free_slots": flat})


def _create_event(args: dict, trace_id: str, started: float) -> CallResponse:
    title = args.get("title")
    start_s = args.get("start")
    end_s = args.get("end")
    if not (title and start_s and end_s):
        return make_response(trace_id=trace_id, started=started, error=err("BAD_ARGS", "title, start, end required"))
    try:
        start = datetime.fromisoformat(start_s)
        end = datetime.fromisoformat(end_s)
    except ValueError:
        return make_response(trace_id=trace_id, started=started, error=err("BAD_ARGS", "bad ISO datetime"))
    if end <= start:
        return make_response(trace_id=trace_id, started=started, error=err("BAD_ARGS", "end must be after start"))
    if state.has_conflict(start, end):
        return make_response(trace_id=trace_id, started=started, error=err("CONFLICT", "time slot is busy"))
    ev = CalendarEvent(
        event_id="evt_" + uuid.uuid4().hex[:10],
        title=title,
        start=start,
        end=end,
        location=args.get("location", ""),
        description=args.get("description", ""),
        source="agent",
    )
    state.add_event(ev)
    return make_response(trace_id=trace_id, started=started, result=_event_to_dict(ev))


def _delete_event(args: dict, trace_id: str, started: float) -> CallResponse:
    eid = args.get("event_id")
    if not eid:
        return make_response(trace_id=trace_id, started=started, error=err("BAD_ARGS", "event_id required"))
    if not state.delete_event(eid):
        return make_response(trace_id=trace_id, started=started, error=err("NOT_FOUND", "no such event"))
    return make_response(trace_id=trace_id, started=started, result={"event_id": eid, "status": "deleted"})


def _list_events(args: dict, trace_id: str, started: float) -> CallResponse:
    d_from = _parse_date(args.get("date_from")) or (
        _parse_date(args.get("date")) or date.today()
    )
    d_to = _parse_date(args.get("date_to")) or (d_from + timedelta(days=7))
    items = [
        _event_to_dict(e)
        for e in state.events
        if d_from <= e.start.date() <= d_to
    ]
    items.sort(key=lambda x: x["start"])
    return make_response(trace_id=trace_id, started=started, result={"date_from": d_from.isoformat(), "date_to": d_to.isoformat(), "events": items})


# ---------- helpers ----------

def _slice_free(start: datetime, end: datetime, duration: int) -> list[dict]:
    out: list[dict] = []
    cur = start
    step = timedelta(minutes=duration)
    while cur + step <= end:
        out.append({"start": cur.isoformat(), "end": (cur + step).isoformat()})
        cur += step
    return out


def _event_to_dict(e: CalendarEvent) -> dict:
    return {
        "event_id": e.event_id,
        "title": e.title,
        "start": e.start.isoformat(),
        "end": e.end.isoformat(),
        "location": e.location,
        "description": e.description,
        "source": e.source,
    }


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def _parse_time(s: str | None):
    from datetime import time as _t
    if not s:
        return None
    try:
        h, m = s.split(":")
        return _t(int(h), int(m))
    except Exception:
        return None


def _ensure_seeded() -> None:
    if state._seeded_for is None:
        state.seed()
