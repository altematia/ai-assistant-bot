"""Last-resort error handling for Telegram updates."""

from __future__ import annotations

import logging

from aiogram.exceptions import TelegramAPIError
from aiogram.types import ErrorEvent, Message
from sqlalchemy.exc import SQLAlchemyError

log = logging.getLogger(__name__)


async def handle_error(event: ErrorEvent) -> bool:
    error = event.exception
    if isinstance(error, TelegramAPIError):
        log.error("Telegram API error: %s", type(error).__name__, exc_info=error)
        return True
    if isinstance(error, SQLAlchemyError):
        log.error("Database error", exc_info=error)
        response = "База данных временно недоступна. Попробуйте позже."
    else:
        log.error("Unexpected update error", exc_info=error)
        response = "Произошла ошибка. Попробуйте позже."

    message = event.update.message
    if isinstance(message, Message):
        try:
            await message.answer(response)
        except TelegramAPIError:
            log.exception("Could not send error reply through Telegram")
    else:
        callback = event.update.callback_query
        if callback is not None:
            try:
                await callback.answer(response, show_alert=True)
            except TelegramAPIError:
                log.exception("Could not answer failed callback")
    return True
