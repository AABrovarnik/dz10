"""MCP #1: карты / агрегатор фитнес-центров.

GET  /mcp/maps/tools
POST /mcp/maps/call   { tool: "search_places" | "get_place_details", arguments: {...} }
"""
from __future__ import annotations

import math
import time
from datetime import date
from typing import Any

from fastapi import APIRouter, Request

from ..mcp_servers.data.fitness_centers import PLACES
from ..mcp.base import (
    CallError,
    CallRequest,
    CallResponse,
    Tool,
    ToolsResponse,
    err,
    make_response,
    make_trace_id,
)


router = APIRouter(prefix="/mcp/maps", tags=["mcp: maps"])

TOOLS = ToolsResponse(
    name="maps_mcp",
    description="Поиск фитнес-клубов и детали по местам (агрегатор).",
    tools=[
        Tool(
            name="search_places",
            description=(
                "Поиск фитнес-клубов по типу активности, дате и времени суток. "
                "Возвращает места с координатами, описанием и URL их MCP."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "activity": {
                        "type": "string",
                        "description": "Канонический тип: pool|tennis|yoga|pilates|gym|martial_arts",
                    },
                    "date": {"type": "string", "description": "ISO-дата (YYYY-MM-DD), опционально"},
                    "time_of_day": {
                        "type": "string",
                        "enum": ["morning", "day", "evening", "any"],
                    },
                    "radius_km": {"type": "number", "minimum": 0, "maximum": 50},
                    "lat": {"type": "number"},
                    "lng": {"type": "number"},
                },
            },
        ),
        Tool(
            name="get_place_details",
            description="Полное описание места по id.",
            input_schema={
                "type": "object",
                "properties": {"place_id": {"type": "string"}},
                "required": ["place_id"],
            },
        ),
    ],
)


# Центр Москвы (Красная площадь)
CENTER = (55.7558, 37.6173)


def _haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    R = 6371.0
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


@router.get("/tools", response_model=ToolsResponse)
async def get_tools() -> ToolsResponse:
    return TOOLS


@router.post("/call", response_model=CallResponse)
async def call(req: CallRequest) -> CallResponse:
    started = time.time()
    trace_id = make_trace_id(req.trace_id)
    tool = req.tool
    args = req.arguments

    try:
        if tool == "search_places":
            return _search_places(args, trace_id, started)
        if tool == "get_place_details":
            return _get_place_details(args, trace_id, started)
        return make_response(
            trace_id=trace_id,
            started=started,
            error=err("BAD_TOOL", f"Unknown tool: {tool}"),
        )
    except Exception as exc:  # noqa: BLE001
        return make_response(
            trace_id=trace_id,
            started=started,
            error=err("INTERNAL", f"{type(exc).__name__}: {exc}"),
        )


def _search_places(args: dict[str, Any], trace_id: str, started: float) -> CallResponse:
    activity = args.get("activity")
    radius = float(args.get("radius_km", 5))
    lat = float(args.get("lat", CENTER[0]))
    lng = float(args.get("lng", CENTER[1]))

    if activity is None:
        return make_response(trace_id=trace_id, started=started, error=err("BAD_ARGS", "activity is required"))

    matches: list[dict] = []
    for p in PLACES:
        if activity not in p["type"]:
            continue
        d = _haversine_km((lat, lng), (p["lat"], p["lng"]))
        if d <= radius:
            matches.append({**p, "distance_km": round(d, 2)})
    matches.sort(key=lambda x: x["distance_km"])
    return make_response(
        trace_id=trace_id,
        started=started,
        result={"count": len(matches), "places": matches, "reference": {"lat": lat, "lng": lng, "radius_km": radius}},
    )


def _get_place_details(args: dict[str, Any], trace_id: str, started: float) -> CallResponse:
    place_id = args.get("place_id")
    if not place_id:
        return make_response(trace_id=trace_id, started=started, error=err("BAD_ARGS", "place_id is required"))
    for p in PLACES:
        if p["id"] == place_id:
            return make_response(trace_id=trace_id, started=started, result=p)
    return make_response(trace_id=trace_id, started=started, error=err("NOT_FOUND", f"place {place_id} not found"))
