# AI-агент + MCP · фитнес-бронирование

Демонстрационное веб-приложение, показывающее работу AI-агента,
взаимодействующего с тремя MCP-серверами (карты, фитнес-клубы, календарь)
для поиска и бронирования тренировки.

## Стек

- **Backend**: Python 3.11 + FastAPI + uvicorn
- **Frontend**: Vite + React 18 + TypeScript
- **MCP-серверы**: 3 типа (maps, 10× fitness, calendar) как роуты одного процесса
- **LLM**: OpenAI GPT-5.x (через tool calling) **или** MOCK-провайдер (rule-based)
- **Карта**: Leaflet + OpenStreetMap (без API-ключа)
- **Календарь**: FullCalendar

## Структура

```
fitness-agent/
├── backend/
│   ├── main.py                 ← FastAPI app
│   ├── config.py               ← переменные окружения
│   ├── logbus.py               ← pub/sub шина для SSE
│   ├── mcp/                    ← 3 MCP-роута (maps, fitness×10, calendar)
│   ├── mcp_servers/            ← in-memory state + seed-данные
│   ├── agent/                  ← ReAct-цикл + LLM-провайдеры
│   └── api/                    ← /api/agent, /api/logs, /api/tools, …
├── frontend/
│   ├── package.json
│   ├── vite.config.ts          ← прокси /api → :8000
│   ├── index.html
│   └── src/
│       ├── App.tsx             ← layout 25/75 + табы
│       ├── api.ts              ← клиент + SSE
│       ├── components/
│       │   ├── Chat/           ← левая колонка
│       │   ├── Logs/           ← таб 1
│       │   ├── McpMethods/     ← таб 2
│       │   ├── MapTab/         ← таб 3 (Leaflet)
│       │   └── CalendarTab/    ← таб 4 (FullCalendar)
│       └── styles.css
└── tests/
    └── test_e2e_smoke.py       ← smoke-тест: «теннис в среду»
```

## Запуск (локально)

### 1. Backend

```bash
cd fitness-agent
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000
```

Проверки:
- `http://localhost:8000/healthz` — `{"ok": true, ...}`
- `http://localhost:8000/mcp/maps/tools` — список tools
- `http://localhost:8000/mcp/fitness/fit_2/tools` — один клуб
- `http://localhost:8000/mcp/calendar/tools` — календарь

### 2. Frontend

```bash
cd fitness-agent/frontend
npm install
npm run dev
```

Открыть `http://localhost:5173`.

### 3. LLM-провайдер

По умолчанию работает **MOCK** (без API-ключа, детерминированный).

Чтобы включить **OpenAI GPT-5.x**:
```bash
# в fitness-agent/.env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-5-mini
```

### 4. Production-сборка (один процесс)

```bash
cd fitness-agent/frontend && npm ci && npm run build
SERVE_FRONTEND=1 uvicorn backend.main:app --port 8000
```

Открыть `http://localhost:8000`.

## Демо-сценарий

1. Открыть UI.
2. Нажать кнопку-подсказку **«Запиши меня на теннис в среду вечером»** (или ввести свой запрос).
3. В табе **«Логи»** появятся ~5–7 шагов:
   - `maps_mcp.search_places` → 1–N клубов
   - `fitness_mcp_fit_X.get_available_slots` → слоты
   - `calendar_mcp.get_free_slots` → проверка конфликта
   - `fitness_mcp_fit_X.book_class` → бронь с кодом
   - `calendar_mcp.create_event` → событие
4. В табе **«Календарь»** появится новое событие (иконка `agent` синяя).
5. В верхней панели — статус `ищу → бронирую → готово`.
6. Повторный запрос на тот же слот → агент скажет «слот занят».

## MCP-контракт (для справки)

```http
GET  /mcp/{server}/tools   →  { name, server_version, protocol_version, description, tools: [...] }
POST /mcp/{server}/call    →  { ok, trace_id, latency_ms, result|error }
```

Серверы: `maps`, `fitness/fit_1` … `fitness/fit_10`, `calendar`.

## Что внутри

- **3 MCP-роута** имитируют «реальный» MCP (HTTP+JSON, схемы, ошибки).
- **Агент** — синхронный оркестратор ReAct-цикла (без полноценного LLM-цикла для простоты демо).
- **Логи** — pub/sub через `logbus`, доставляются во фронтенд через SSE.
- **Состояние** — in-memory dict; сидируется при старте.

## Что НЕ реализовано (для будущей итерации)

- Аутентификация пользователей.
- БД (сейчас перезапуск = сброс).
- WebSocket (SSE покрывает сценарий).
- Полная отмена брони через UI (только через прямой `cancel_booking` MCP-вызов).
- Деплой на Replit (см. `TZ/canvas.md` §6).
