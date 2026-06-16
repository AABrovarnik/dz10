"""Загрузчик system prompt для LLM.

Текст промпта хранится в `SYSTEM_PROMPT.md` (этот же файл) как Markdown —
источник истины. Этот модуль читает блок кода, расположенныйный после
заголовка «Сырой текст промпта (передаётся в LLM)», и публикует его
как константу SYSTEM_PROMPT.

Зачем так:
- Промпт редактируется в .md без переписывания Python-кода.
- Ревью промпта = ревью одного файла.
- Можно положить в отдельный .md без экранирования кавычек.

Если файл SYSTEM_PROMPT.md не найден (например, при сборке wheel'а без
docs) — используется встроенный fallback ниже.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path


_FALLBACK_PROMPT = """\
Ты — AI-агент фитнес-бронирования. Твоя задача — помогать пользователю найти и
забронировать тренировку, опираясь на три MCP-сервера:

1. maps_mcp — поиск фитнес-клубов по типу активности и локации.
2. fitness_mcp.{club_id} — расписание и бронирование в конкретном клубе.
3. calendar_mcp — проверка занятости и создание событий.

У тебя есть инструменты. Используй их строго в этом порядке (ReAct-цикл):

Шаг 1. Пойми запрос пользователя: тип активности (activity), день (date), время суток (morning|day|evening).
Шаг 2. Вызови maps_mcp.search_places — выбери ближайший подходящий клуб.
Шаг 3. Вызови fitness_mcp.{club_id}.get_available_slots — выбери слот.
Шаг 4. Вызови calendar_mcp.get_free_slots на это время — проверь, что нет конфликта.
Шаг 5. Вызови fitness_mcp.{club_id}.book_class — забронируй.
Шаг 6. Вызови calendar_mcp.create_event — добавь событие в календарь.
Шаг 7. Ответь пользователю кратко, что забронировано.

Правила:
- Не выдумывай ID. Используй только те, что вернули предыдущие вызовы.
- Если слот занят — попробуй следующий (до 3 попыток).
- Если мест нет — честно скажи пользователю.
- Не вызывай инструменты без необходимости.
- Финальный ответ — короткий, по-русски, человеческим языком.
"""


_MARKER = "## Сырой текст промпта (передаётся в LLM)"


@lru_cache(maxsize=1)
def _load_prompt() -> str:
    md_path = Path(__file__).parent / "SYSTEM_PROMPT.md"
    if not md_path.exists():
        return _FALLBACK_PROMPT
    text = md_path.read_text(encoding="utf-8")
    # Берём первый fenced code block после маркера
    if _MARKER in text:
        tail = text.split(_MARKER, 1)[1]
    else:
        tail = text
    # Ищем ```…```
    m = re.search(r"```(?:[a-zA-Z]+)?\n(.*?)```", tail, flags=re.DOTALL)
    if not m:
        return _FALLBACK_PROMPT
    return m.group(1).rstrip() + "\n"


# Публичный API: импортируется как `from .prompts import SYSTEM_PROMPT`
SYSTEM_PROMPT: str = _load_prompt()


def reload() -> str:
    """Сбросить кэш и перечитать SYSTEM_PROMPT.md (для горячей перезагрузки)."""
    _load_prompt.cache_clear()
    global SYSTEM_PROMPT
    SYSTEM_PROMPT = _load_prompt()
    return SYSTEM_PROMPT
