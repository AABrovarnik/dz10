"""ReAct-цикл агента.

Главная функция: run_agent(user_message, run_id). Она:

1. Понимает намерение (через LLM).
2. Делает tool_calls в MCP-серверы.
3. Получает observations, решает, что делать дальше.
4. Повторяет до 6 шагов или до финального ответа.
5. Логирует каждый шаг через logbus (SSE-стрим).

Поскольку MOCK-провайдер возвращает только первый tool_call, основная
логика (карты → слоты → календарь → бронь → событие) выполняется
оркестратором на основе результатов tool_calls. Это нормальный паттерн:
агент выбирает «следующее действие», а мы, получив результат, решаем
по правилам, какое следующее действие предложить.
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict
from datetime import date, datetime
from typing import Any

import httpx

from ..config import get_settings
from ..logbus import LogEvent, bus
from .llm.base import LLMProvider
from .llm.mock_provider import MockProvider
from .llm.openai_provider import OpenAIProvider
from .prompts import SYSTEM_PROMPT
from .tools import all_mcp_servers, call_tool, fetch_tools


MAX_STEPS = 8


def _make_provider() -> LLMProvider:
    s = get_settings()
    if s.llm_provider == "openai":
        if not s.openai_api_key:
            raise RuntimeError("LLM_PROVIDER=openai, but OPENAI_API_KEY is not set")
        return OpenAIProvider(api_key=s.openai_api_key, model=s.openai_model)
    return MockProvider()


def _ev(run_id: str, step: int, kind: str, **kw) -> LogEvent:
    return LogEvent(run_id=run_id, step=step, kind=kind, **kw)


async def _emit(ev: LogEvent) -> None:
    await bus.publish(ev)


async def run_agent(user_message: str, run_id: str) -> None:
    """Основной цикл. Логирует всё в bus. По завершении шлёт done/error."""
    settings = get_settings()
    base = settings.base_url
    provider = _make_provider()
    step = 0
    history: list[dict] = [{"role": "user", "content": user_message}]
    final_text: str | None = None
    booked: dict | None = None
    event: dict | None = None

    try:
        await _emit(_ev(run_id, step, "status", title="Агент запущен", mcp=None))
        step += 1

        async with httpx.AsyncClient(base_url=base, timeout=10.0) as client:
            # 0. Собираем tools реестр
            tools_spec: list[dict] = []
            for srv in all_mcp_servers().keys():
                try:
                    tools_spec.extend(await fetch_tools(client, srv, base))
                except Exception as exc:  # noqa: BLE001
                    await _emit(
                        _ev(
                            run_id,
                            step,
                            "status",
                            title=f"Не удалось получить tools от {srv}",
                            error=str(exc),
                        )
                    )
                step += 1

            # 1. LLM решает первое действие
            await _emit(
                _ev(
                    run_id,
                    step,
                    "status",
                    title=f"Запрос к {provider.name} LLM",
                )
            )
            step += 1
            msg = await provider.decide(system=SYSTEM_PROMPT, history=history, tools=tools_spec)
            if msg.content and not msg.tool_calls:
                # MOCK может сразу ответить текстом (нет активности / запрос на отмену)
                final_text = msg.content
                await _emit(_ev(run_id, step, "decision", title=msg.content))
                step += 1
                return _finish(run_id, step, final_text, booked, event)

            # 2. Первый tool_call — search_places (по плану)
            for tc in msg.tool_calls:
                server, tool = tc.name.split(".", 1)
                await _emit(
                    _ev(
                        run_id,
                        step,
                        "tool_call",
                        title=f"{server}.{tool}",
                        mcp=server,
                        tool=tool,
                        args=tc.arguments,
                    )
                )
                step += 1
                started = time.time()
                resp = await call_tool(client, server, tool, tc.arguments, trace_id=run_id)
                latency = int((time.time() - started) * 1000)
                await _emit(
                    _ev(
                        run_id,
                        step,
                        "observation",
                        title=f"ответ {server}.{tool}",
                        mcp=server,
                        tool=tool,
                        ok=resp.get("ok", False),
                        result=resp.get("result"),
                        error=(resp.get("error") or {}).get("message") if resp.get("error") else None,
                        latency_ms=latency,
                    )
                )
                step += 1

                if not resp.get("ok") or not resp.get("result"):
                    final_text = "Не удалось получить список клубов. Попробуйте другой запрос."
                    return _finish(run_id, step, final_text, booked, event)

                places = resp["result"].get("places", [])
                if not places:
                    final_text = "Подходящих клубов не нашлось. Попробуйте другую активность."
                    return _finish(run_id, step, final_text, booked, event)

                chosen = places[0]
                await _emit(
                    _ev(
                        run_id,
                        step,
                        "decision",
                        title=f"Выбран клуб: {chosen['name']} (≈{chosen['distance_km']} км)",
                        result={"club_id": chosen["id"]},
                    )
                )
                step += 1

                # 3. get_available_slots
                args = {
                    "date": tc.arguments.get("date"),
                    "time_of_day": tc.arguments.get("time_of_day", "any"),
                }
                # activity из первого запроса нужен фитнес-MCP
                activity = tc.arguments.get("activity")
                if activity:
                    args["class_type"] = activity

                srv_fit = f"fitness_mcp_{chosen['id']}"
                await _emit(
                    _ev(
                        run_id,
                        step,
                        "tool_call",
                        title=f"{srv_fit}.get_available_slots",
                        mcp=srv_fit,
                        tool="get_available_slots",
                        args=args,
                    )
                )
                step += 1
                started = time.time()
                resp = await call_tool(client, srv_fit, "get_available_slots", args, trace_id=run_id)
                latency = int((time.time() - started) * 1000)
                await _emit(
                    _ev(
                        run_id,
                        step,
                        "observation",
                        title=f"ответ {srv_fit}.get_available_slots",
                        mcp=srv_fit,
                        tool="get_available_slots",
                        ok=resp.get("ok", False),
                        result=resp.get("result"),
                        error=(resp.get("error") or {}).get("message") if resp.get("error") else None,
                        latency_ms=latency,
                    )
                )
                step += 1

                slots = (resp.get("result") or {}).get("slots", [])
                if not slots:
                    final_text = f"В клубе {chosen['name']} нет свободных слотов под ваш запрос. Попробуйте другой день."
                    return _finish(run_id, step, final_text, booked, event)

                slot = slots[0]
                await _emit(
                    _ev(
                        run_id,
                        step,
                        "decision",
                        title=f"Выбран слот: {slot['title']} в {slot['start']}",
                        result={"slot_id": slot["slot_id"]},
                    )
                )
                step += 1

                # 4. calendar_mcp.get_free_slots (проверим конфликт)
                slot_start = datetime.fromisoformat(slot["start"])
                slot_end = datetime.fromisoformat(slot["end"])
                dur = int((slot_end - slot_start).total_seconds() // 60)
                cal_args = {"date": slot_start.date().isoformat(), "duration_min": dur}
                await _emit(
                    _ev(
                        run_id,
                        step,
                        "tool_call",
                        title="calendar_mcp.get_free_slots",
                        mcp="calendar_mcp",
                        tool="get_free_slots",
                        args=cal_args,
                    )
                )
                step += 1
                started = time.time()
                resp = await call_tool(client, "calendar_mcp", "get_free_slots", cal_args, trace_id=run_id)
                latency = int((time.time() - started) * 1000)
                await _emit(
                    _ev(
                        run_id,
                        step,
                        "observation",
                        title="ответ calendar_mcp.get_free_slots",
                        mcp="calendar_mcp",
                        tool="get_free_slots",
                        ok=resp.get("ok", False),
                        result=resp.get("result"),
                        latency_ms=latency,
                    )
                )
                step += 1

                # 5. book_class
                book_args = {"slot_id": slot["slot_id"]}
                await _emit(
                    _ev(
                        run_id,
                        step,
                        "tool_call",
                        title=f"{srv_fit}.book_class",
                        mcp=srv_fit,
                        tool="book_class",
                        args=book_args,
                    )
                )
                step += 1
                started = time.time()
                resp = await call_tool(client, srv_fit, "book_class", book_args, trace_id=run_id)
                latency = int((time.time() - started) * 1000)
                await _emit(
                    _ev(
                        run_id,
                        step,
                        "observation",
                        title=f"ответ {srv_fit}.book_class",
                        mcp=srv_fit,
                        tool="book_class",
                        ok=resp.get("ok", False),
                        result=resp.get("result"),
                        error=(resp.get("error") or {}).get("message") if resp.get("error") else None,
                        latency_ms=latency,
                    )
                )
                step += 1

                if not resp.get("ok"):
                    final_text = "Слот уже занят. Попробуйте ещё раз."
                    return _finish(run_id, step, final_text, booked, event)

                booked = resp["result"]

                # 6. calendar_mcp.create_event
                ev_args = {
                    "title": f"Тренировка: {slot['title']}",
                    "start": slot["start"],
                    "end": slot["end"],
                    "location": chosen["name"],
                    "description": f"Бронь #{booked.get('confirmation_code', '?')} в клубе «{chosen['name']}»",
                }
                await _emit(
                    _ev(
                        run_id,
                        step,
                        "tool_call",
                        title="calendar_mcp.create_event",
                        mcp="calendar_mcp",
                        tool="create_event",
                        args=ev_args,
                    )
                )
                step += 1
                started = time.time()
                resp = await call_tool(client, "calendar_mcp", "create_event", ev_args, trace_id=run_id)
                latency = int((time.time() - started) * 1000)
                await _emit(
                    _ev(
                        run_id,
                        step,
                        "observation",
                        title="ответ calendar_mcp.create_event",
                        mcp="calendar_mcp",
                        tool="create_event",
                        ok=resp.get("ok", False),
                        result=resp.get("result"),
                        error=(resp.get("error") or {}).get("message") if resp.get("error") else None,
                        latency_ms=latency,
                    )
                )
                step += 1

                if resp.get("ok"):
                    event = resp["result"]
                    when = slot["start"].replace("T", " ")
                    final_text = (
                        f"Готово! Забронировал «{slot['title']}» в клубе «{chosen['name']}» "
                        f"на {when}. Код подтверждения: {booked.get('confirmation_code')}."
                    )
                else:
                    final_text = "Бронь создана, но в календарь событие не добавилось (конфликт?)."

        return _finish(run_id, step, final_text or "Готово.", booked, event)
    except Exception as exc:  # noqa: BLE001
        await _emit(
            _ev(
                run_id,
                step,
                "error",
                title="Ошибка агента",
                error=f"{type(exc).__name__}: {exc}",
            )
        )
        step += 1
        await _emit(_ev(run_id, step, "done", title="Завершено с ошибкой", ok=False))


def _finish(run_id: str, step: int, final_text: str, booked: dict | None, event: dict | None) -> None:
    """Публикует финальный decision + done event (синхронно, т.к. вызывается
    из уже-async-функции). Подписчики SSE получат оба."""
    decision = LogEvent(
        run_id=run_id,
        step=step,
        kind="decision",
        title=final_text,
        result={"booked": booked, "event": event},
    )
    bus._history[run_id].append(decision)  # type: ignore[attr-defined]
    for q in list(bus._subs.get(run_id, ())):  # type: ignore[attr-defined]
        try:
            q.put_nowait(decision)
        except Exception:
            pass

    done_event = LogEvent(
        run_id=run_id,
        step=step + 1,
        kind="done",
        title="Завершено",
        ok=True,
    )
    bus._history[run_id].append(done_event)  # type: ignore[attr-defined]
    for q in list(bus._subs.get(run_id, ())):  # type: ignore[attr-defined]
        try:
            q.put_nowait(done_event)
        except Exception:
            pass
