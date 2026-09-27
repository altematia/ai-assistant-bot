"""Onboarding and informational commands."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from app.bot.handlers.common import identity_of
from app.bot.keyboards.settings import STYLE_LABELS
from app.services.conversation import ConversationService

router = Router(name="commands")


@router.message(CommandStart(), F.chat.type == ChatType.PRIVATE)
async def start(message: Message, conversation: ConversationService) -> None:
    if message.from_user is None:
        return
    await conversation.settings(identity_of(message.from_user))
    await message.answer(
        "Привет! Я AI-ассистент: отвечаю на вопросы и помню наш разговор.\n\n"
        "Напиши вопрос обычным сообщением. /help покажет команды, "
        "а /settings позволит выбрать стиль ответа."
    )


@router.message(Command("help"), F.chat.type == ChatType.PRIVATE)
async def help_command(message: Message) -> None:
    await message.answer(
        "Команды\n"
        "/start — начать разговор\n"
        "/help — список команд\n"
        "/reset — очистить историю диалога\n"
        "/settings — модель, стиль и размер истории\n"
        "/stats — статистика использования\n\n"
        "Для разговора просто отправь текст."
    )


@router.message(Command("reset"), F.chat.type == ChatType.PRIVATE)
async def reset(message: Message, conversation: ConversationService) -> None:
    if message.from_user is None:
        return
    await conversation.reset(identity_of(message.from_user))
    await message.answer("История диалога очищена. Настройка стиля сохранена.")


@router.message(Command("stats"), F.chat.type == ChatType.PRIVATE)
async def stats(message: Message, conversation: ConversationService) -> None:
    if message.from_user is None:
        return
    data = await conversation.stats(identity_of(message.from_user))
    await message.answer(
        "Твоя статистика\n"
        f"Сообщений: {data.user_messages}\n"
        f"Ответов AI: {data.assistant_messages}\n"
        f"Первое использование: {data.first_used:%d.%m.%Y} (UTC)\n"
        f"Стиль: {STYLE_LABELS[data.style]}"
    )
