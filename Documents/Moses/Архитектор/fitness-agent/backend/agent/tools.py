"""Адаптеры MCP → OpenAI tool format + helpers для оркестратора.

Каждый MCP-роут мы регистрируем в OpenAI function-calling формате. Агент
видит один плоский список tools с именами вида "<mcp_server>.<tool>".
"""
from __future__ import annotations

from typing import Any

import httpx

from ..config import get_settings


# Имена MCP-серверов, в которые оркестратор может ходить напрямую.
# Каждый клуб — отдельный MCP, но инструменты в нём одинаковые.
MCP_SERVERS = {
    "maps_mcp": "/mcp/maps",
    "calendar_mcp": "/mcp/calendar",
}


def all_mcp_servers() -> dict[str, str]:
    """Возвращает словарь {server_name: path} для всех известных MCP-серверов.

    maps_mcp + calendar_mcp + 10 клубов.
    """
    out = dict(MCP_SERVERS)
    for i in range(1, 11):
        out[f"fitness_mcp_fit_{i}"] = f"/mcp/fitness/fit_{i}"
    return out


async def fetch_tools(client: httpx.AsyncClient, server: str, base: str) -> list[dict]:
    """Сходить в MCP /tools, вернуть список OpenAI-style tool-описаний."""
    path = all_mcp_servers()[server]
    r = await client.get(f"{base}{path}/tools")
    r.raise_for_status()
    payload = r.json()
    out: list[dict] = []
    for t in payload["tools"]:
        out.append(
            {
                "type": "function",
                "function": {
                    "name": f"{server}.{t['name']}",
                    "description": t["description"],
                    "parameters": t["input_schema"],
                }
            }
        )
    return out


async def call_tool(
    client: httpx.AsyncClient,
    server: str,
    tool: str,
    arguments: dict[str, Any],
    *,
    trace_id: str | None = None,
) -> dict:
    """Сходить в MCP /call, вернуть (ok, payload, latency_ms, error)."""
    path = all_mcp_servers()[server]
    body = {"tool": tool, "arguments": arguments}
    if trace_id:
        body["trace_id"] = trace_id
    r = await client.post(f"{path}/call", json=body)
    return r.json()
