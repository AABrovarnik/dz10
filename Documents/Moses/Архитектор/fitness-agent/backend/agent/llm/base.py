"""Интерфейс LLM-провайдера.

Минимально: метод decide(messages, tools) -> AssistantMessage.
messages — список OpenAI-style сообщений (system/user/assistant/tool).
tools — список OpenAI-style tool-описаний.
AssistantMessage содержит либо текстовый ответ, либо tool_calls.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCallRequest:
    name: str  # формат: "mcp_server.tool" напр. "maps_mcp.search_places"
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class AssistantMessage:
    content: str | None = None
    tool_calls: list[ToolCallRequest] = field(default_factory=list)
    raw: Any = None  # для отладки


class LLMProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def decide(
        self,
        *,
        system: str,
        history: list[dict],
        tools: list[dict],
    ) -> AssistantMessage:
        """Один шаг ReAct-цикла: вернуть либо текст, либо tool_calls."""


def message(role: str, **kwargs) -> dict:
    return {"role": role, **kwargs}
