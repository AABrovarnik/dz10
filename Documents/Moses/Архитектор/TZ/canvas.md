# Технический канвас — AI-агент + MCP (фитнес-бронирование)

> Версия: 0.1 · Дата: 2026-06-15 · На основе ТЗ v0.1
> Цель: превратить ТЗ в конкретный технический чертёж, пригодный к деплою на Replit за один коммит.

---

## 1. Резюме (одной фразой)

Монолитное веб-приложение с **одним процессом**, в котором **3 MCP-сервера** живут как роуты одного backend, а **AI-агент** с tool calling ходит по ним, логируя каждый шаг, и **SPA-фронтенд** в реальном времени показывает логи / карту / календарь / реестр инструментов.

---

## 2. Архитектурная диаграмма

```
┌────────────────────────────────────────────────────────────────────┐
│                         BROWSER (React SPA)                        │
│  ┌──────────┐  ┌──────────────────────────────────────────────┐    │
│  │  Chat    │  │ Tabs: [Логи] [MCP-методы] [Карта] [Календарь] │    │
│  │  25%     │  │                  75%                          │    │
│  └─────┬────┘  └────────────────────┬─────────────────────────┘    │
│        │ POST /api/agent            │ GET /api/logs/stream (SSE)  │
│        │ GET  /api/agent/state      │ GET /api/tools              │
└────────┼───────────────────────────┼──────────────────────────────┘
         │                           │
         ▼                           ▼
┌────────────────────────────────────────────────────────────────────┐
│                      BACKEND (FastAPI · :8000)                     │
│                                                                    │
│  ┌─────────────┐  ┌──────────────────┐  ┌─────────────────────┐   │
│  │  /api/agent │  │  /api/logs (SSE) │  │   /api/tools (read) │   │
│  │  Orchestr.  │  │  event-stream    │  │   реестр для UI     │   │
│  └──────┬──────┘  └────────┬─────────┘  └──────────┬──────────┘   │
│         │                 │                       │               │
│         ▼                 ▼                       ▼               │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │                 AGENT CORE (ReAct loop)                    │   │
│  │  planner → tool_call → observe → decide → … → final       │   │
│  │  llm_provider: openai | mock                              │   │
│  │  log_bus: pub/sub → SSE                                   │   │
│  └─────┬──────────────┬──────────────┬────────────────────────┘   │
│        │              │              │                            │
│        ▼              ▼              ▼                            │
│  ┌──────────┐  ┌────────────────┐  ┌────────────────┐            │
│  │ MCP:     │  │ MCP: fitness   │  │ MCP: calendar  │            │
│  │ maps     │  │ (10 клубов,    │  │ (1 инстанс)    │            │
│  │ /mcp/    │  │  /mcp/fitness/ │  │  /mcp/calendar │            │
│  │  maps    │  │   {fit_1..10}) │  │                │            │
│  └──────────┘  └────────────────┘  └────────────────┘            │
│                                                                    │
│  STATE: in-memory dicts (seed при старте) · без БД                │
└────────────────────────────────────────────────────────────────────┘
         │                            │
         ▼                            ▼
   Leaflet/OSM                  FullCalendar
   (вкладка «Карта»)            (вкладка «Календарь»)
```

**Почему один процесс, а не «настоящие» отдельные MCP-серверы:**

- Сохраняем **реалистичный контракт** (`GET /tools`, `POST /call`, JSON-схемы) — именно это и проверяет демо.
- Экономим один деплой, один порт, один healthcheck — иначе на Replit это 4 сервиса, что усложнит запуск.
- Если позже нужно «расщепить» — это **один `docker-compose`**, MCP-роуты уже изолированы в модулях.

---

## 3. Стек

| Слой | Технология | Обоснование |
|---|---|---|
| **Backend** | **Python 3.11 + FastAPI** | 1) единый async-стек для SSE, HTTP-вызовов, OpenAI SDK; 2) `pydantic` идеально ложится на `input_schema` MCP; 3) минимум boilerplate. Альтернатива: Node.js + Fastify (тоже ок, выбирается по предпочтению). |
| **LLM** | **OpenAI GPT-5.x (tool calling)** + **MOCK-провайдер** | OpenAI — по умолчанию; MOCK — для офлайн-демо и CI, реализует детерминированный ReAct на rule-based парсере намерений. Переключатель `LLM_PROVIDER=openai\|mock`. |
| **Frontend** | **Vite + React 18 + TypeScript** | Быстрый dev-server, простая сборка для Replit Static / Vite preview. |
| **Карта** | **Leaflet + OpenStreetMap** (без API-ключа) | Mapbox требует токен; для демо OSM хватит. |
| **Календарь** | **FullCalendar (React)** | Готовые week/day view, клик-события. |
| **UI-styling** | **CSS Modules + небольшой токен-слой** (НЕ Tailwind v4) | См. [[tailwind-v4-production-bug]] — в Docker standalone баг с генерацией утилит. CSS Modules безопасны. |
| **Realtime** | **Server-Sent Events** (`/api/logs/stream`) | Проще WebSocket’а, идеально для «ищу / бронирую / готово». |
| **Парсинг времени** | `dateparser` (en+ru) | «завтра утром», «в среду вечером» → конкретный ISO. |
| **Деплой** | **Replit (Web App, Python)** | Один процесс = один Web App. Порт 8000. Frontend собирается и раздаётся FastAPI как `StaticFiles` (режим `SERVE_FRONTEND=1`). В dev — два процесса. |

---

## 4. Структура папок (монолит под Replit)

```
Архитектор/
├── TZ/                          ← документация (ТЗ, канвас, ADR)
│   ├── canvas.md                ← этот файл
│   └── …
├── fitness-agent/               ← приложение (моно-репо)
│   ├── .replit                  ← entrypoint: uvicorn main:app
│   ├── replit.nix               ← python-3.11 + node-20
│   ├── pyproject.toml           ← poetry / uv
│   ├── requirements.txt         ← fallback
│   ├── README.md
│   │
│   ├── backend/
│   │   ├── main.py              ← FastAPI app, mount routers, static
│   │   ├── config.py            ← env: LLM_PROVIDER, OPENAI_API_KEY, …
│   │   │
│   │   ├── mcp/
│   │   │   ├── __init__.py      ← MCPRequest/Response pydantic-модели
│   │   │   ├── base.py          ← общий router-фабрика
│   │   │   ├── maps_mcp.py      ← /mcp/maps   (search_places, get_place_details)
│   │   │   ├── fitness_mcp.py   ← /mcp/fitness/{fit_id}  (×10 инстансов)
│   │   │   └── calendar_mcp.py  ← /mcp/calendar (get_free_slots, create_event, …)
│   │   │
│   │   ├── mcp_servers/
│   │   │   ├── data/
│   │   │   │   ├── fitness_centers.py   ← 10 клубов (id, name, lat, lng, types)
│   │   │   │   ├── class_catalog.py     ← расписание слотов
│   │   │   │   └── calendar_seed.py     ← предзаполненные события
│   │   │   └── state.py                 ← in-memory state + seed()
│   │   │
│   │   ├── agent/
│   │   │   ├── core.py          ← ReAct-цикл
│   │   │   ├── tools.py         ← обёртки над MCP в формат OpenAI tools
│   │   │   ├── llm/
│   │   │   │   ├── base.py      ← интерфейс LLMProvider
│   │   │   │   ├── openai_provider.py
│   │   │   │   └── mock_provider.py     ← детерминированный rule-based
│   │   │   ├── prompts.py       ← SYSTEM_PROMPT
│   │   │   └── time_resolver.py ← dateparser-обёртка
│   │   │
│   │   ├── api/
│   │   │   ├── agent.py         ← POST /api/agent, GET /api/agent/state
│   │   │   ├── logs.py          ← GET /api/logs (history), /api/logs/stream (SSE)
│   │   │   └── tools.py         ← GET /api/tools (реестр для UI)
│   │   │
│   │   └── logbus.py            ← pub/sub: agent→UI через asyncio.Queue
│   │
│   ├── frontend/
│   │   ├── package.json
│   │   ├── vite.config.ts       ← proxy /api → :8000
│   │   ├── index.html
│   │   ├── src/
│   │   │   ├── main.tsx
│   │   │   ├── App.tsx
│   │   │   ├── api.ts           ← fetch-обёртки + EventSource
│   │   │   ├── components/
│   │   │   │   ├── Chat/        ← 25% левая колонка
│   │   │   │   ├── Logs/        ← tab 1
│   │   │   │   ├── McpMethods/  ← tab 2
│   │   │   │   ├── MapTab/      ← tab 3 (Leaflet)
│   │   │   │   ├── CalendarTab/ ← tab 4 (FullCalendar)
│   │   │   │   └── shared/      ← Tabs, JsonView (collapse/expand)
│   │   │   ├── store/           ← zustand или просто useState
│   │   │   └── styles/
│   │   │       ├── tokens.css   ← светлая тема, палитра
│   │   │       └── *.module.css
│   │   └── public/
│   │
│   └── tests/
│       ├── test_mcp_contracts.py
│       ├── test_agent_react.py
│       └── test_frontend_smoke.py
│
└── Posts/                       ← журнал / отчёты (есть уже)
```

**Ключевые соглашения:**

- **MCP-роуты не знают про агента** — это просто `GET /tools`, `POST /call`. Агент — клиент к ним.
- **Агент пишет в `logbus`** на каждом шаге, **SSE-эндпоинт читает** — и UI получает события в реальном времени.
- **Frontend dev-server** на Vite (`:5173`) проксирует `/api/*` на FastAPI (`:8000`). В production оба собираются в один origin.

---

## 5. Контракты (финальные)

### 5.1 MCP — общий протокол

```http
GET /mcp/{server}/tools
→ 200 {
    "name": "fitness_mcp_fit_1",
    "server_version": "0.1.0",
    "protocol_version": "2024-11-05",
    "description": "Iron Pulse Gym — расписание и бронирования",
    "tools": [
      { "name": "get_classes", "description": "…",
        "input_schema": { "type":"object", "properties": { … } } }
    ]
  }
```

```http
POST /mcp/{server}/call
Content-Type: application/json
{ "tool": "get_available_slots", "arguments": { … }, "trace_id": "uuid" }

→ 200 {
    "ok": true,
    "trace_id": "uuid",
    "latency_ms": 12,
    "result": { … }
  }
→ 4xx/5xx {
    "ok": false,
    "trace_id": "uuid",
    "error": { "code": "SLOT_TAKEN", "message": "…" }
  }
```

### 5.2 Список MCP-эндпоинтов

| URL | Методы |
|---|---|
| `GET /mcp/maps/tools`, `POST /mcp/maps/call` | `search_places`, `get_place_details` |
| `GET /mcp/fitness/fit_1/tools` … `fit_10` | `get_classes`, `get_available_slots`, `book_class`, `cancel_booking` |
| `GET /mcp/calendar/tools`, `POST /mcp/calendar/call` | `get_free_slots`, `create_event`, `delete_event`, `list_events` |

### 5.3 Агент → UI

```http
POST /api/agent        { "message": "Хочу теннис в среду вечером" }
→ 202 { "run_id": "uuid" }     # асинхронно

GET  /api/agent/state?run_id=…
→ 200 { "status": "searching|booking|done|error", "final": "…", "steps": [ … ] }

GET  /api/logs/stream?run_id=…   # SSE: event: step / event: done
```

### 5.4 Агент-флоу (ReAct, 5–7 шагов)

```
1. plan     → разобрать запрос (activity, time_of_day, day)
2. act      → maps_mcp.search_places(filter=[activity], radius_km=5)
3. act      → fitness_mcp.{id}.get_available_slots(class_type, date)
4. obs+plan → выбрать клуб (ближайший + есть слот)
5. act      → calendar_mcp.get_free_slots(start, end)        # проверить конфликт
6. act      → fitness_mcp.{id}.book_class(slot_id)
7. act      → calendar_mcp.create_event(…)
              done
```

При `SLOT_TAKEN` → шаг 3 с другим клубом/слотом (до 3 попыток, затем user-facing ошибка).

---

## 6. Деплой на Replit

**Один Repl, тип «Web App», Python.**

`replit.nix`:
```nix
{ pkgs }: { deps = [ pkgs.python311 pkgs.nodejs-20_x ]; }
```

`.replit` (run):
```
run = "uvicorn backend.main:app --host 0.0.0.0 --port 8000"
```

Build (frontend):
```
[nix]
build = "cd frontend && npm ci && npm run build && cd .."
```

`SERVE_FRONTEND=1` → FastAPI отдаёт `frontend/dist/` через `StaticFiles` + SPA-fallback на `index.html`.

**Env-переменные** (в Secrets):
- `LLM_PROVIDER=mock` (по умолчанию) или `openai`
- `OPENAI_API_KEY=…` (только для openai)
- `SERVE_FRONTEND=1` (production-режим)
- `DEMO_TIMEZONE=Europe/Moscow`

---

## 7. Открытые вопросы (нужно решить ДО кода)

| # | Вопрос | Варианты |
|---|---|---|
| Q1 | **Стек backend** | Python+FastAPI (рекомендую) / Node+Fastify |
| Q2 | **LLM-режим** | OpenAI GPT-5.x / MOCK (детерминированный) / оба (переключатель) |
| Q3 | **Где развернуть** | Replit (как в ТЗ) / локально / Docker-образ |
| Q4 | **Tailwind** | CSS Modules (рекомендую) / Tailwind v3.4 (без v4) |
| Q5 | **Карта** | Leaflet+OSM (рекомендую) / Mapbox (нужен токен) |
| Q6 | **Базовый календарь** | предзаполнить на **эту неделю** (рекомендую) / на **фиксированную неделю** 2026-06-15..21 |

---

## 8. План работ (после выбора Q1–Q6)

1. **Скелет** (структура папок, пустые роуты, hello-world `/api/agent` → `/api/logs/stream`).
2. **MCP-серверы** (контракт + seed-данные + ручные curl-проверки).
3. **MOCK-агент** (ReAct-цикл, лог-шина, детерминированные ответы).
4. **Frontend-скелет** (4 таба, chat, SSE-подключение).
5. **UI-табы**: Logs → McpMethods → Map (Leaflet) → Calendar (FullCalendar).
6. **OpenAI-провайдер** (если выбран) + system prompt.
7. **E2E-сценарий** «теннис в среду вечером» — запись в README.
8. **Деплой на Replit** (или Docker).

---

## 9. Что я могу сделать сам

Могу прямо сейчас сгенерировать **полный код-каркас** всего MVP в папку `fitness-agent/`:
- ~25 файлов Python + ~15 файлов TypeScript,
- все 3 MCP-сервера с seed-данными (10 клубов, расписание, базовый календарь),
- MOCK-агент с ReAct-циклом и лог-шиной,
- React UI с 4 табами и работающим SSE,
- OpenAI-провайдер (включается флагом),
- README с инструкцией запуска локально и на Replit,
- E2E-тест одного демо-сценария.

**Не потребуется от тебя** ничего, кроме выбора Q1–Q6 из §7. OpenAI-ключ — по желанию, без него всё работает в MOCK-режиме.

---

## 10. Ключевая идея демо (напоминание)

Это **не UI** и **не форма бронирования**. Это наглядный показ:

> «Вот запрос → вот 5 MCP-вызовов с аргументами и ответами → вот решение агента → вот результат в календаре и на карте»

Каждая из этих 4–5 карточек логов = шаг ReAct-цикла. Это и есть «как AI-агент думает», что и требовало ТЗ.
