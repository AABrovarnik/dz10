"""Application configuration loaded from environment variables.

Провайдер LLM переключается переменной LLM_PROVIDER=mock|openai.
Дефолт — mock, чтобы демо работало без API-ключа.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    llm_provider: str = "mock"  # mock | openai
    openai_api_key: str | None = None
    openai_model: str = "gpt-5-mini"  # актуальная модель по умолчанию
    serve_frontend: bool = False
    demo_timezone: str = "Europe/Moscow"
    app_name: str = "fitness-agent-mcp-demo"
    app_version: str = "0.1.0"
    # MCP-серверы бьются по /mcp/<name> через единый процесс, порт один.
    base_url: str = "http://localhost:8000"


@lru_cache
def get_settings() -> Settings:
    return Settings()
