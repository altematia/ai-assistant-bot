"""Per-user dialogue operations and persistence."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from weakref import WeakValueDictionary

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import MAX_HISTORY_MESSAGES, MAX_USER_MESSAGE_LENGTH
from app.database import repository
from app.database.models import User, UserSetting
from app.database.session import Database
from app.services.llm import STYLE_PROMPTS, TextGenerator


@dataclass(frozen=True, slots=True)
class Identity:
    telegram_id: int
    username: str | None
    first_name: str | None


@dataclass(frozen=True, slots=True)
class SettingsOverview:
    model: str
    style: str
    message_count: int
    telegram_id: int


@dataclass(frozen=True, slots=True)
class UserStats:
    user_messages: int
    assistant_messages: int
    first_used: datetime
    style: str


class ConversationService:
    def __init__(self, database: Database, generator: TextGenerator, default_model: str) -> None:
        self._database = database
        self._generator = generator
        self._default_model = default_model
        self._locks: WeakValueDictionary[int, asyncio.Lock] = WeakValueDictionary()

    def _lock_for(self, telegram_id: int) -> asyncio.Lock:
        lock = self._locks.get(telegram_id)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[telegram_id] = lock
        return lock

    async def _ensure(
        self, session: AsyncSession, identity: Identity
    ) -> tuple[User, UserSetting]:
        return await repository.ensure_user(
            session,
            identity.telegram_id,
            identity.username,
            identity.first_name,
            self._default_model,
        )

    async def ask(self, identity: Identity, question: str) -> str:
        question = question.strip()
        if not question or len(question) > MAX_USER_MESSAGE_LENGTH:
            raise ValueError("Invalid message length")

        async with self._lock_for(identity.telegram_id):
            async with self._database.sessions.begin() as session:
                user, setting = await self._ensure(session, identity)
                user_id, style, model = user.id, setting.response_style, setting.model
                history = await repository.recent_messages(
                    session, user_id, MAX_HISTORY_MESSAGES
                )

            answer = await self._generator.generate(history, question, style, model)

            async with self._database.sessions.begin() as session:
                await repository.save_exchange(session, user_id, question, answer)
            return answer

    async def reset(self, identity: Identity) -> None:
        async with self._lock_for(identity.telegram_id):
            async with self._database.sessions.begin() as session:
                user, _ = await self._ensure(session, identity)
                await repository.clear_messages(session, user.id)

    async def settings(self, identity: Identity) -> SettingsOverview:
        async with self._lock_for(identity.telegram_id):
            async with self._database.sessions.begin() as session:
                user, setting = await self._ensure(session, identity)
                counts = await repository.message_counts(session, user.id)
                return SettingsOverview(
                    setting.model, setting.response_style, counts.total, identity.telegram_id
                )

    async def set_style(self, identity: Identity, style: str) -> SettingsOverview:
        if style not in STYLE_PROMPTS:
            raise ValueError("Unknown response style")
        async with self._lock_for(identity.telegram_id):
            async with self._database.sessions.begin() as session:
                user, setting = await self._ensure(session, identity)
                setting.response_style = style
                counts = await repository.message_counts(session, user.id)
                return SettingsOverview(
                    setting.model, setting.response_style, counts.total, identity.telegram_id
                )

    async def stats(self, identity: Identity) -> UserStats:
        async with self._lock_for(identity.telegram_id):
            async with self._database.sessions.begin() as session:
                user, setting = await self._ensure(session, identity)
                counts = await repository.message_counts(session, user.id)
                return UserStats(
                    counts.user, counts.assistant, user.created_at, setting.response_style
                )
