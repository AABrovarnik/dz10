"""OpenAI GPT-5.x провайдер с tool calling.

Использует openai>=1.0 SDK. Если API-ключ не задан — провайдер бросает
RuntimeError при вызове decide(); main.py должен падать в MOCK, если
ключа нет.
"""
from __future__ import annotations

import json
from typing import Any

from .base import AssistantMessage, LLMProvider, ToolCallRequest


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, api_key: str, model: str = "gpt-5-mini") -> None:
        # Импорт локальный, чтобы не падать без openai в MOCK-режиме
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def decide(
        self,
        *,
        system: str,
        history: list[dict],
        tools: list[dict],
    ) -> AssistantMessage:
        messages: list[dict] = [{"role": "system", "content": system}] + history
        kwargs: dict[str, Any] = {"model": self._model, "messages": messages}
        if tools:
            # Конвертируем наш tools-список (OpenAI-style) — оставляем как есть
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        resp = await self._client.chat.completions.create(**kwargs)
        msg = resp.choices[0].message
        tool_calls: list[ToolCallRequest] = []
        for tc in (msg.tool_calls or []):
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            tool_calls.append(ToolCallRequest(name=tc.function.name, arguments=args))
        return AssistantMessage(content=msg.content, tool_calls=tool_calls, raw=resp.model_dump())
