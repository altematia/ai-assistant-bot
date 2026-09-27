"""Queries used by the conversation service."""

from __future__ import annotations

from dataclasses import dataclass
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Message, User, UserSetting


@dataclass(frozen=True, slots=True)
class DialogueMessage:
    role: str
    content: str


@dataclass(frozen=True, slots=True)
class MessageCounts:
    user: int
    assistant: int

    @property
    def total(self) -> int:
        return self.user + self.assistant


async def ensure_user(
    session: AsyncSession,
    telegram_id: int,
    username: str | None,
    first_name: str | None,
    model: str,
) -> tuple[User, UserSetting]:
    user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
    if user is None:
        user = User(telegram_id=telegram_id, username=username, first_name=first_name)
        session.add(user)
        await session.flush()
    elif user.username != username or user.first_name != first_name:
        user.username = username
        user.first_name = first_name

    setting = await session.get(UserSetting, user.id)
    if setting is None:
        setting = UserSetting(user_id=user.id, response_style="normal", model=model)
        session.add(setting)
    elif setting.model != model:
        setting.model = model
    await session.flush()
    return user, setting


async def recent_messages(
    session: AsyncSession, user_id: int, limit: int
) -> list[DialogueMessage]:
    rows = (await session.scalars(
        select(Message)
        .where(Message.user_id == user_id)
        .order_by(Message.id.desc())
        .limit(limit)
    )).all()
    return [DialogueMessage(row.role, row.content) for row in reversed(rows)]


async def save_exchange(
    session: AsyncSession, user_id: int, question: str, answer: str
) -> None:
    session.add_all([
        Message(user_id=user_id, role="user", content=question),
        Message(user_id=user_id, role="assistant", content=answer),
    ])


async def clear_messages(session: AsyncSession, user_id: int) -> None:
    await session.execute(delete(Message).where(Message.user_id == user_id))


async def message_counts(session: AsyncSession, user_id: int) -> MessageCounts:
    rows = (await session.execute(
        select(Message.role, func.count(Message.id))
        .where(Message.user_id == user_id)
        .group_by(Message.role)
    )).all()
    counts = dict(rows)
    return MessageCounts(user=counts.get("user", 0), assistant=counts.get("assistant", 0))
