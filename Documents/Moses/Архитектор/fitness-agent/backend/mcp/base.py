"""Базовые Pydantic-модели MCP-протокола.

Используются всеми MCP-роутами для единого формата ответа.
Контракт совместим с идеей MCP 2024-11-05 (но мы говорим по HTTP, не по stdio).
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field


class Tool(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any]


class ToolsResponse(BaseModel):
    name: str
    server_version: str = "0.1.0"
    protocol_version: str = "2024-11-05"
    description: str
    tools: list[Tool]


class CallRequest(BaseModel):
    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    trace_id: str | None = None


class CallError(BaseModel):
    code: str
    message: str


class CallResponse(BaseModel):
    ok: bool
    trace_id: str
    latency_ms: int
    result: Any = None
    error: CallError | None = None


def make_trace_id(provided: str | None) -> str:
    return provided or uuid.uuid4().hex


def make_response(
    *,
    trace_id: str,
    started: float,
    result: Any = None,
    error: CallError | None = None,
) -> CallResponse:
    return CallResponse(
        ok=error is None,
        trace_id=trace_id,
        latency_ms=int((time.time() - started) * 1000),
        result=result,
        error=error,
    )


def err(code: str, message: str) -> CallError:
    return CallError(code=code, message=message)


# Список кодов ошибок для UI
ErrorCode = Literal[
    "BAD_TOOL",
    "BAD_ARGS",
    "NOT_FOUND",
    "SLOT_TAKEN",
    "NO_AVAILABILITY",
    "CONFLICT",
    "INTERNAL",
]
