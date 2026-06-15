"""Pub/sub-шина для логов: агент пишет, SSE-эндпоинт читает.

Каждое сообщение — это «шаг» ReAct-цикла. Подписчики — асинхронные очереди
по run_id. Когда run завершается, шина шлёт финальный `done`/`error` event.
"""
from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, AsyncIterator


@dataclass
class LogEvent:
    """Один шаг агента или MCP-вызов, видимый в UI."""

    run_id: str
    step: int
    kind: str  # "plan" | "tool_call" | "observation" | "decision" | "status" | "done" | "error"
    title: str
    mcp: str | None = None
    tool: str | None = None
    args: dict[str, Any] | None = None
    result: Any = None
    ok: bool = True
    error: str | None = None
    latency_ms: int | None = None
    ts: float = field(default_factory=time.time)

    def to_sse(self) -> str:
        payload = asdict(self)
        return f"event: {self.kind}\ndata: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"


class LogBus:
    """Простая in-memory pub/sub: один run_id → набор подписчиков."""

    def __init__(self) -> None:
        self._subs: dict[str, set[asyncio.Queue[LogEvent]]] = {}
        self._history: dict[str, list[LogEvent]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, run_id: str) -> asyncio.Queue[LogEvent]:
        q: asyncio.Queue[LogEvent] = asyncio.Queue()
        async with self._lock:
            self._subs.setdefault(run_id, set()).add(q)
            # replay уже записанных событий
            for ev in self._history.get(run_id, []):
                q.put_nowait(ev)
        return q

    async def unsubscribe(self, run_id: str, q: asyncio.Queue[LogEvent]) -> None:
        async with self._lock:
            if run_id in self._subs:
                self._subs[run_id].discard(q)
                if not self._subs[run_id]:
                    del self._subs[run_id]

    async def publish(self, ev: LogEvent) -> None:
        async with self._lock:
            self._history.setdefault(ev.run_id, []).append(ev)
            subs = list(self._subs.get(ev.run_id, ()))
        for q in subs:
            q.put_nowait(ev)

    async def stream(self, run_id: str) -> AsyncIterator[LogEvent]:
        q = await self.subscribe(run_id)
        try:
            while True:
                ev = await q.get()
                yield ev
                if ev.kind in ("done", "error"):
                    return
        finally:
            await self.unsubscribe(run_id, q)

    def history(self, run_id: str) -> list[LogEvent]:
        return list(self._history.get(run_id, []))

    def new_run_id(self) -> str:
        return uuid.uuid4().hex


bus = LogBus()
