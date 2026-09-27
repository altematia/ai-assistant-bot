"""Run the Telegram bot with long polling: python -m app.main."""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher

from app.bot.handlers import chat, settings, start
from app.bot.handlers.errors import handle_error
from app.config import load_settings
from app.database.session import Database
from app.services.conversation import ConversationService
from app.services.llm import OpenAITextGenerator
from app.utils.logging import configure_logging

log = logging.getLogger(__name__)


async def run() -> None:
    settings_config = load_settings()
    database = Database(settings_config.database_url)
    generator = OpenAITextGenerator(settings_config.openai_api_key)
    bot = Bot(settings_config.telegram_bot_token)
    dispatcher = Dispatcher()
    dispatcher.include_routers(start.router, settings.router, chat.router)
    dispatcher.errors.register(handle_error)
    conversation = ConversationService(database, generator, settings_config.openai_model)

    try:
        await database.create_tables()
        await bot.delete_webhook(drop_pending_updates=False)
        log.info("Starting AI Assistant Bot polling")
        await dispatcher.start_polling(bot, conversation=conversation, handle_as_tasks=True)
    finally:
        await bot.session.close()
        await generator.close()
        await database.close()


def main() -> None:
    configure_logging()
    try:
        asyncio.run(run())
    except ValueError as exc:
        log.error("Configuration error: %s", exc)
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
