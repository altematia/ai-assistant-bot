"""Text dialogue and unsupported-input replies."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.types import Message
from aiogram.utils.chat_action import ChatActionSender
from sqlalchemy.exc import SQLAlchemyError

from app.bot.handlers.common import identity_of
from app.config import MAX_USER_MESSAGE_LENGTH
from app.services.conversation import ConversationService
from app.services.llm import LLMServiceError
from app.utils.text import split_text

log = logging.getLogger(__name__)
router = Router(name="chat")


@router.message(F.chat.type == ChatType.PRIVATE, F.text)
async def answer_text(message: Message, conversation: ConversationService) -> None:
    if message.from_user is None:
        return
    question = (message.text or "").strip()
    if not question:
        await message.answer("Отправь непустой вопрос текстом.")
        return
    if question.startswith("/"):
        await message.answer("Не знаю такую команду. Напиши /help, чтобы увидеть список.")
        return
    if len(question) > MAX_USER_MESSAGE_LENGTH:
        await message.answer(
            f"Сообщение слишком длинное. Максимум — {MAX_USER_MESSAGE_LENGTH} символов."
        )
        return

    try:
        async with ChatActionSender.typing(bot=message.bot, chat_id=message.chat.id):
            answer = await conversation.ask(identity_of(message.from_user), question)
    except LLMServiceError as exc:
        await message.answer(exc.user_message)
        return
    except SQLAlchemyError:
        log.exception("Database error while processing user %s", message.from_user.id)
        await message.answer("Не удалось сохранить диалог. Попробуйте позже.")
        return

    for part in split_text(answer):
        await message.answer(part)


@router.message(F.chat.type == ChatType.PRIVATE)
async def unsupported_input(message: Message) -> None:
    await message.answer("Сейчас я работаю с текстом. Отправь вопрос обычным сообщением.")
