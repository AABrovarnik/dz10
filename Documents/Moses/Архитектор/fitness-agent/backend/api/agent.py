"""HTTP API для оркестратора агента и UI."""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..agent.core import run_agent
from ..logbus import bus
from ..mcp_servers.data.calendar_seed import CalendarEvent
from ..mcp_servers.state import state


router = APIRouter(prefix="/api", tags=["api"])


@router.get("/calendar/events")
async def calendar_events() -> dict:
    """Прямой листинг событий календаря для UI (минуя MCP-протокол)."""
    if state._seeded_for is None:
        state.seed()
    items = [
        {
            "event_id": e.event_id,
            "title": e.title,
            "start": e.start.isoformat(),
            "end": e.end.isoformat(),
            "location": e.location,
            "description": e.description,
            "source": e.source,
        }
        for e in state.events
    ]
    items.sort(key=lambda x: x["start"])
    return {"events": items}


class AgentRequest(BaseModel):
    message: str


@router.post("/agent")
async def start_agent(req: AgentRequest) -> dict[str, Any]:
    """Запустить новый run агента. Возвращает run_id, по которому UI
    открывает SSE-стрим на /api/logs/stream."""
    if not req.message.strip():
        raise HTTPException(400, "message is empty")
    run_id = bus.new_run_id()
    # Запускаем агент в фоне — не блокируем HTTP-ответ
    asyncio.create_task(run_agent(req.message, run_id))
    return {"run_id": run_id, "status": "started"}


@router.get("/agent/state")
async def get_state(run_id: str) -> dict[str, Any]:
    """Текущее состояние run’а: список шагов + статус."""
    history = bus.history(run_id)
    status = "running"
    final = None
    if history and history[-1].kind == "done":
        status = "done"
        final = history[-1].title
    elif history and history[-1].kind == "error":
        status = "error"
        final = history[-1].title
    return {
        "run_id": run_id,
        "status": status,
        "final": final,
        "steps": [_step_to_dict(e) for e in history],
    }


@router.get("/logs")
async def get_logs(run_id: str) -> dict[str, Any]:
    """История шагов как JSON (для refresh / debug)."""
    return {"run_id": run_id, "steps": [_step_to_dict(e) for e in bus.history(run_id)]}


@router.get("/logs/stream")
async def stream_logs(run_id: str) -> StreamingResponse:
    """SSE-стрим: каждое сообщение — шаг агента."""
    async def gen():
        # Если история уже есть — сначала отдадим её
        for ev in bus.history(run_id):
            yield ev.to_sse()
            if ev.kind in ("done", "error"):
                return
        # Затем подписываемся на новые события
        async for ev in bus.stream(run_id):
            yield ev.to_sse()
            if ev.kind in ("done", "error"):
                return

    return StreamingResponse(gen(), media_type="text/event-stream")


def _step_to_dict(e) -> dict:
    """Безопасная сериализация LogEvent в JSON (для /state и /logs)."""
    return {
        "run_id": e.run_id,
        "step": e.step,
        "kind": e.kind,
        "title": e.title,
        "mcp": e.mcp,
        "tool": e.tool,
        "args": e.args,
        "result": e.result,
        "ok": e.ok,
        "error": e.error,
        "latency_ms": e.latency_ms,
        "ts": e.ts,
    }
