"""MCP #2: фитнес-центры (по одному MCP-роуту на клуб).

GET  /mcp/fitness/{fit_id}/tools
POST /mcp/fitness/{fit_id}/call   { tool: ... }

У всех клубов одинаковый набор методов, отличаются только данные.
"""
from __future__ import annotations

import time
import uuid
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, HTTPException

from ..mcp_servers.data.class_catalog import filter_slots
from ..mcp_servers.data.fitness_centers import PLACES
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


router = APIRouter(prefix="/mcp/fitness", tags=["mcp: fitness"])


def _tools_for(club_id: str) -> ToolsResponse:
    place = next((p for p in PLACES if p["id"] == club_id), None)
    if not place:
        raise HTTPException(404, f"club {club_id} not found")
    return ToolsResponse(
        name=f"fitness_mcp_{club_id}",
        description=f"{place['name']} — расписание и бронирования. Адрес: {place['address']}.",
        tools=[
            Tool(
                name="get_classes",
                description="Список типов занятий клуба (gym, pool, yoga, …).",
                input_schema={"type": "object", "properties": {}},
            ),
            Tool(
                name="get_available_slots",
                description=(
                    "Получить доступные слоты. Можно фильтровать по типу занятия, "
                    "дате/диапазону, времени суток (morning/day/evening)."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "class_type": {"type": "string"},
                        "date": {"type": "string", "description": "ISO YYYY-MM-DD"},
                        "date_from": {"type": "string"},
                        "date_to": {"type": "string"},
                        "time_of_day": {"type": "string", "enum": ["morning", "day", "evening", "any"]},
                    },
                },
            ),
            Tool(
                name="book_class",
                description="Забронировать слот по slot_id.",
                input_schema={
                    "type": "object",
                    "properties": {"slot_id": {"type": "string"}},
                    "required": ["slot_id"],
                },
            ),
            Tool(
                name="cancel_booking",
                description="Отменить бронь по slot_id.",
                input_schema={
                    "type": "object",
                    "properties": {"slot_id": {"type": "string"}},
                    "required": ["slot_id"],
                },
            ),
        ],
    )


@router.get("/{fit_id}/tools", response_model=ToolsResponse)
async def get_tools(fit_id: str) -> ToolsResponse:
    _ensure_seeded()
    return _tools_for(fit_id)


@router.post("/{fit_id}/call", response_model=CallResponse)
async def call(fit_id: str, req: CallRequest) -> CallResponse:
    _ensure_seeded()
    started = time.time()
    trace_id = make_trace_id(req.trace_id)
    place = next((p for p in PLACES if p["id"] == fit_id), None)
    if not place:
        return make_response(trace_id=trace_id, started=started, error=err("NOT_FOUND", f"club {fit_id}"))

    try:
        tool = req.tool
        args = req.arguments
        if tool == "get_classes":
            return _get_classes(fit_id, place, trace_id, started)
        if tool == "get_available_slots":
            return _get_slots(fit_id, args, trace_id, started)
        if tool == "book_class":
            return _book(fit_id, args, trace_id, started)
        if tool == "cancel_booking":
            return _cancel(fit_id, args, trace_id, started)
        return make_response(trace_id=trace_id, started=started, error=err("BAD_TOOL", f"Unknown tool: {tool}"))
    except Exception as exc:  # noqa: BLE001
        return make_response(
            trace_id=trace_id,
            started=started,
            error=err("INTERNAL", f"{type(exc).__name__}: {exc}"),
        )


# ---------- handlers ----------

def _get_classes(fit_id: str, place: dict, trace_id: str, started: float) -> CallResponse:
    return make_response(
        trace_id=trace_id,
        started=started,
        result={"club_id": fit_id, "name": place["name"], "class_types": place["type"]},
    )


def _get_slots(fit_id: str, args: dict, trace_id: str, started: float) -> CallResponse:
    class_type = args.get("class_type")
    d_from = _parse_date(args.get("date_from"))
    d_to = _parse_date(args.get("date_to"))
    if args.get("date"):
        d = _parse_date(args["date"])
        if d:
            d_from = d
            d_to = d
    time_of_day = args.get("time_of_day")
    if time_of_day == "any":
        time_of_day = None

    slots = filter_slots(
        state.slots.values(),
        class_type=class_type,
        date_from=d_from,
        date_to=d_to,
        time_of_day=time_of_day,
    )
    slots = [s for s in slots if s.club_id == fit_id and s.available]
    return make_response(
        trace_id=trace_id,
        started=started,
        result={
            "club_id": fit_id,
            "count": len(slots),
            "slots": [
                {
                    "slot_id": s.slot_id,
                    "class_type": s.class_type,
                    "title": s.title,
                    "start": s.start.isoformat(),
                    "end": s.end.isoformat(),
                }
                for s in slots
            ],
        },
    )


def _book(fit_id: str, args: dict, trace_id: str, started: float) -> CallResponse:
    slot_id = args.get("slot_id")
    if not slot_id:
        return make_response(trace_id=trace_id, started=started, error=err("BAD_ARGS", "slot_id required"))
    s = state.slots.get(slot_id)
    if not s or s.club_id != fit_id:
        return make_response(trace_id=trace_id, started=started, error=err("NOT_FOUND", "slot not found"))
    if not state.book(slot_id):
        return make_response(trace_id=trace_id, started=started, error=err("SLOT_TAKEN", "slot already booked"))
    return make_response(
        trace_id=trace_id,
        started=started,
        result={
            "slot_id": slot_id,
            "club_id": fit_id,
            "class_type": s.class_type,
            "start": s.start.isoformat(),
            "end": s.end.isoformat(),
            "confirmation_code": uuid.uuid4().hex[:8].upper(),
        },
    )


def _cancel(fit_id: str, args: dict, trace_id: str, started: float) -> CallResponse:
    slot_id = args.get("slot_id")
    if not slot_id:
        return make_response(trace_id=trace_id, started=started, error=err("BAD_ARGS", "slot_id required"))
    if not state.cancel(slot_id):
        return make_response(trace_id=trace_id, started=started, error=err("NOT_FOUND", "no such booking"))
    return make_response(trace_id=trace_id, started=started, result={"slot_id": slot_id, "status": "cancelled"})


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def _ensure_seeded() -> None:
    if state._seeded_for is None:
        state.seed()
