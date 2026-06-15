"""Seed-данные: 10 фитнес-центров в центре Москвы.

Координаты — приблизительные к реальным адресам, чтобы на карте Leaflet
было визуально осмысленно. mcp_url — это URL соответствующего MCP-роута.
"""
from __future__ import annotations

from typing import TypedDict


class FitnessPlace(TypedDict):
    id: str
    name: str
    lat: float
    lng: float
    type: list[str]
    description: str
    address: str
    mcp_url: str


# Москва, центр и ближайшие районы
PLACES: list[FitnessPlace] = [
    {
        "id": "fit_1",
        "name": "Iron Pulse Gym",
        "lat": 55.7558,
        "lng": 37.6173,
        "type": ["gym", "pool", "yoga"],
        "description": "Современный зал с бассейном 25 м и зоной йоги. Рядом с Красной площадью.",
        "address": "ул. Тверская, 1",
        "mcp_url": "/mcp/fitness/fit_1",
    },
    {
        "id": "fit_2",
        "name": "Nordic Tennis Club",
        "lat": 55.7700,
        "lng": 37.6300,
        "type": ["tennis", "gym"],
        "description": "4 крытых корта, тренеры, прокат оборудования.",
        "address": "ул. Маросейка, 7",
        "mcp_url": "/mcp/fitness/fit_2",
    },
    {
        "id": "fit_3",
        "name": "Aqua Marina",
        "lat": 55.7400,
        "lng": 37.6050,
        "type": ["pool", "yoga"],
        "description": "Бассейн 50 м, аквааэробика, йога-студия с панорамными окнами.",
        "address": "Остоженка, 12",
        "mcp_url": "/mcp/fitness/fit_3",
    },
    {
        "id": "fit_4",
        "name": "Dojo24",
        "lat": 55.7600,
        "lng": 37.6500,
        "type": ["martial_arts", "gym"],
        "description": "Залы для бокса, ММА и карате. Тренировки для взрослых и детей.",
        "address": "Покровка, 22",
        "mcp_url": "/mcp/fitness/fit_4",
    },
    {
        "id": "fit_5",
        "name": "Yoga Loft Moscow",
        "lat": 55.7350,
        "lng": 37.5900,
        "type": ["yoga", "pilates"],
        "description": "Тёплое пространство с двумя залами, авторские классы.",
        "address": "Большая Пироговская, 8",
        "mcp_url": "/mcp/fitness/fit_5",
    },
    {
        "id": "fit_6",
        "name": "SportLife Park",
        "lat": 55.7800,
        "lng": 37.6200,
        "type": ["gym", "pool", "tennis"],
        "description": "Большой комплекс: тренажёры, бассейн, корты.",
        "address": "Лесная, 5",
        "mcp_url": "/mcp/fitness/fit_6",
    },
    {
        "id": "fit_7",
        "name": "Strike Zone",
        "lat": 55.7250,
        "lng": 37.6400,
        "type": ["martial_arts"],
        "description": "Специализация — кикбоксинг и тайский бокс.",
        "address": "Дубининская, 27",
        "mcp_url": "/mcp/fitness/fit_7",
    },
    {
        "id": "fit_8",
        "name": "Balance Pilates Studio",
        "lat": 55.7650,
        "lng": 37.6050,
        "type": ["pilates", "yoga"],
        "description": "Реформеры, маты, индивидуальные и групповые занятия.",
        "address": "Малая Никитская, 14",
        "mcp_url": "/mcp/fitness/fit_8",
    },
    {
        "id": "fit_9",
        "name": "Riverside Pool & Gym",
        "lat": 55.7100,
        "lng": 37.6100,
        "type": ["pool", "gym"],
        "description": "Бассейн с панорамой на Москва-реку, кардио-зона.",
        "address": "Крымский Вал, 9",
        "mcp_url": "/mcp/fitness/fit_9",
    },
    {
        "id": "fit_10",
        "name": "Grand Slam Tennis",
        "lat": 55.7450,
        "lng": 37.5800,
        "type": ["tennis", "gym"],
        "description": "6 кортов (hard/grass), детские группы, абонементы.",
        "address": "Зубовский бульвар, 17",
        "mcp_url": "/mcp/fitness/fit_10",
    },
]


# Нормализация названий активностей (используется в планировщике и MCP)
ACTIVITY_ALIASES: dict[str, str] = {
    "бассейн": "pool",
    "бассейна": "pool",
    "pool": "pool",
    "swim": "pool",
    "swimming": "pool",
    "теннис": "tennis",
    "tennis": "tennis",
    "йога": "yoga",
    "yoga": "yoga",
    "пилатес": "pilates",
    "pilates": "pilates",
    "зал": "gym",
    "тренажёрный зал": "gym",
    "тренажерный зал": "gym",
    "gym": "gym",
    "тренировка": "gym",
    "единоборства": "martial_arts",
    "бокс": "martial_arts",
    "мма": "martial_arts",
    "карате": "martial_arts",
    "martial_arts": "martial_arts",
}


def normalize_activity(text: str) -> str | None:
    """Извлекает канонический тип активности из пользовательского запроса."""
    t = text.lower()
    for k, v in ACTIVITY_ALIASES.items():
        if k in t:
            return v
    return None
