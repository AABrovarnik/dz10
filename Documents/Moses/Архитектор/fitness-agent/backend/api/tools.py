"""GET /api/tools — реестр всех MCP и их инструментов (для вкладки «MCP методы»)."""
from __future__ import annotations

import httpx
from fastapi import APIRouter

from ..config import get_settings
from ..mcp_servers.data.fitness_centers import PLACES
from ..agent.tools import all_mcp_servers


router = APIRouter(prefix="/api", tags=["api"])


@router.get("/tools")
async def list_tools() -> dict:
    """Возвращает реестр MCP-серверов с tools (без проксирования).

    Чтобы UI не зависел от того, какие MCP-роуты доступны напрямую, мы
    собираем описание из локального модуля + динамически опрашиваем
    основные серверы. Если опрос не удаётся — отдаём заглушку.
    """
    settings = get_settings()
    base = settings.base_url
    out: list[dict] = []

    async with httpx.AsyncClient(base_url=base, timeout=5.0) as client:
        # Maps + Calendar + каждый клуб
        servers = {
            "maps_mcp": "Карты",
            "calendar_mcp": "Календарь",
        }
        for i in range(1, 11):
            servers[f"fitness_mcp_fit_{i}"] = f"Фитнес #{i}"

        for srv, label in servers.items():
            path = all_mcp_servers()[srv]
            try:
                r = await client.get(f"{base}{path}/tools")
                if r.status_code == 200:
                    payload = r.json()
                    out.append(
                        {
                            "server": srv,
                            "label": label,
                            "url": path,
                            "description": payload.get("description", ""),
                            "tools": payload.get("tools", []),
                        }
                    )
                else:
                    out.append(_stub(srv, label, path, r.status_code))
            except Exception as exc:  # noqa: BLE001
                out.append(_stub(srv, label, path, str(exc)))

    return {"servers": out, "places": PLACES}


def _stub(server: str, label: str, path: str, err) -> dict:
    return {
        "server": server,
        "label": label,
        "url": path,
        "description": f"(недоступен: {err})",
        "tools": [],
    }
