"""Settings command and inline style selection."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bot.handlers.common import identity_of
from app.bot.keyboards.settings import STYLE_LABELS, style_keyboard
from app.services.conversation import ConversationService, SettingsOverview

router = Router(name="settings")


def settings_text(data: SettingsOverview) -> str:
    return (
        "Настройки\n"
        f"Модель: {data.model}\n"
        f"Стиль ответа: {STYLE_LABELS[data.style]}\n"
        f"Сообщений в истории: {data.message_count}\n"
        f"User ID: {data.telegram_id}\n\n"
        "Выбери стиль ответа:"
    )


@router.message(Command("settings"), F.chat.type == ChatType.PRIVATE)
async def settings_command(message: Message, conversation: ConversationService) -> None:
    if message.from_user is None:
        return
    data = await conversation.settings(identity_of(message.from_user))
    await message.answer(settings_text(data), reply_markup=style_keyboard(data.style))


@router.callback_query(F.data.startswith("style:"))
async def choose_style(callback: CallbackQuery, conversation: ConversationService) -> None:
    style = (callback.data or "").partition(":")[2]
    if style not in STYLE_LABELS or not isinstance(callback.message, Message):
        await callback.answer("Настройка недоступна", show_alert=True)
        return
    if callback.message.chat.type != ChatType.PRIVATE or callback.message.chat.id != callback.from_user.id:
        await callback.answer("Эта настройка доступна только в личном чате", show_alert=True)
        return
    current = await conversation.settings(identity_of(callback.from_user))
    if current.style == style:
        await callback.answer("Этот стиль уже выбран")
        return
    data = await conversation.set_style(identity_of(callback.from_user), style)
    await callback.message.edit_text(settings_text(data), reply_markup=style_keyboard(style))
    await callback.answer("Стиль сохранён")
