"""FastAPI app: MCP-роуты + API + опционально статика собранного фронта."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .api.agent import router as agent_router
from .api.tools import router as tools_router
from .config import get_settings
from .mcp.calendar_mcp import router as calendar_mcp_router
from .mcp.fitness_mcp import router as fitness_mcp_router
from .mcp.maps_mcp import router as maps_mcp_router
from .mcp_servers.state import state


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(title=s.app_name, version=s.app_version)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # MCP-роуты
    app.include_router(maps_mcp_router)
    app.include_router(fitness_mcp_router)
    app.include_router(calendar_mcp_router)

    # API
    app.include_router(agent_router)
    app.include_router(tools_router)

    @app.get("/healthz")
    async def healthz() -> dict:
        return {"ok": True, "version": s.app_version, "llm_provider": s.llm_provider}

    @app.on_event("startup")
    async def _seed() -> None:
        state.seed()

    # Frontend: serve built SPA from ../frontend/dist (если SERVE_FRONTEND=1)
    dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
    if s.serve_frontend and dist.exists():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/")
        async def root() -> FileResponse:
            return FileResponse(dist / "index.html")

        @app.get("/{full_path:path}")
        async def spa(full_path: str) -> FileResponse:
            # SPA fallback
            return FileResponse(dist / "index.html")
    else:
        @app.get("/")
        async def root_dev() -> JSONResponse:
            return JSONResponse(
                {
                    "name": s.app_name,
                    "version": s.app_version,
                    "hint": "Запустите frontend отдельно: cd frontend && npm run dev",
                    "endpoints": [
                        "/healthz",
                        "/mcp/maps/tools",
                        "/mcp/calendar/tools",
                        "/mcp/fitness/fit_1/tools",
                        "/api/agent (POST)",
                        "/api/logs/stream?run_id=…",
                        "/api/tools",
                    ],
                }
            )

    return app


app = create_app()
