"""Smoke-тест: поднимаем TestClient, прогоняем полный сценарий «теннис в среду».

Требует: pip install httpx (уже в requirements).
"""
from __future__ import annotations

import sys
import time
from datetime import date

from fastapi.testclient import TestClient


def main(base_url: str = "http://localhost:8000") -> int:
    print(f"[smoke] base_url={base_url}")
    import httpx

    # 1. /healthz
    with httpx.Client(base_url=base_url, timeout=5.0) as c:
        r = c.get("/healthz")
        r.raise_for_status()
        print("[smoke] healthz ok:", r.json())

        # 2. MCP контракт maps
        r = c.get("/mcp/maps/tools")
        r.raise_for_status()
        assert "tools" in r.json()
        print("[smoke] maps tools ok:", [t["name"] for t in r.json()["tools"]])

        # 3. MCP контракт calendar
        r = c.get("/mcp/calendar/tools")
        r.raise_for_status()
        print("[smoke] calendar tools ok:", [t["name"] for t in r.json()["tools"]])

        # 4. Запуск агента
        r = c.post("/api/agent", json={"message": "Хочу теннис в среду вечером"})
        r.raise_for_status()
        run_id = r.json()["run_id"]
        print("[smoke] agent started run_id=", run_id)

        # 5. Ждём done
        deadline = time.time() + 15
        final = None
        steps = 0
        while time.time() < deadline:
            r = c.get(f"/api/agent/state?run_id={run_id}")
            r.raise_for_status()
            data = r.json()
            steps = len(data["steps"])
            if data["status"] in ("done", "error"):
                final = data
                break
            time.sleep(0.3)

        assert final is not None, "agent did not finish in time"
        print(f"[smoke] agent finished: status={final['status']}, steps={steps}")
        print(f"[smoke] final: {final['final']}")
        # Печатаем типы шагов
        for e in final["steps"]:
            print(f"  - step {e['step']:>2}  {e['kind']:<12} {e['title']}")

        # 6. Минимальные проверки
        kinds = [e["kind"] for e in final["steps"]]
        assert "tool_call" in kinds, "expected at least one tool_call"
        assert "observation" in kinds, "expected at least one observation"
        assert final["status"] == "done", f"expected done, got {final['status']}"

        # 7. Состояние календаря: должно быть +1 событие agent-source
        r = c.get("/api/calendar/events")
        r.raise_for_status()
        events = r.json()["events"]
        agent_events = [e for e in events if e["source"] == "agent"]
        print(f"[smoke] calendar has {len(events)} events total, {len(agent_events)} from agent")
        assert len(agent_events) >= 1, "expected at least one event from agent"

    print("[smoke] ALL OK ✅")
    return 0


if __name__ == "__main__":
    base = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    sys.exit(main(base))
