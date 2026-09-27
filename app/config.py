"""Application configuration and request limits."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

MAX_HISTORY_MESSAGES = 20
MAX_USER_MESSAGE_LENGTH = 4000
MAX_OUTPUT_TOKENS = 1600


@dataclass(frozen=True, slots=True)
class Settings:
    telegram_bot_token: str
    openai_api_key: str
    openai_model: str
    database_url: str


def load_settings() -> Settings:
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model = os.getenv("OPENAI_MODEL", "gpt-5-mini").strip()
    database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./bot.db").strip()

    if not token or token.startswith("your_"):
        raise ValueError("Укажите TELEGRAM_BOT_TOKEN в .env")
    if not api_key or api_key.startswith("your_"):
        raise ValueError("Укажите OPENAI_API_KEY в .env")
    if not model:
        raise ValueError("OPENAI_MODEL не может быть пустой")
    if not database_url:
        raise ValueError("DATABASE_URL не может быть пустой")
    return Settings(token, api_key, model, database_url)
