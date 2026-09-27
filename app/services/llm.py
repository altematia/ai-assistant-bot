"""OpenAI Responses API integration."""

from __future__ import annotations

import logging
from typing import Protocol, Sequence

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    OpenAIError,
    RateLimitError,
)

from app.config import MAX_OUTPUT_TOKENS
from app.database.repository import DialogueMessage

log = logging.getLogger(__name__)

BASE_PROMPT = (
    "Ты полезный AI-ассистент. Отвечай понятно, структурированно и по существу. "
    "Если информации недостаточно — честно сообщи об этом. Не выдумывай факты. "
    "Используй короткие абзацы и списки. Не используй Markdown-таблицы."
)
STYLE_PROMPTS = {
    "short": "Отвечай максимально кратко и по существу.",
    "normal": "Отвечай ясно, достаточно подробно, но без лишней воды.",
    "detailed": "Давай подробные объяснения, примеры и структуруй ответ.",
}


class LLMServiceError(Exception):
    user_message = "AI-сервис временно недоступен. Попробуйте позже."


class LLMTimeout(LLMServiceError):
    user_message = "AI-сервис отвечает слишком долго. Попробуйте ещё раз."


class LLMAuthentication(LLMServiceError):
    user_message = "AI-сервис сейчас не настроен. Сообщите владельцу бота."


class LLMRateLimited(LLMServiceError):
    user_message = "Сейчас слишком много запросов к AI. Повторите попытку позже."


class LLMUnavailable(LLMServiceError):
    pass


class TextGenerator(Protocol):
    async def generate(
        self, history: Sequence[DialogueMessage], question: str, style: str, model: str
    ) -> str: ...


class OpenAITextGenerator:
    def __init__(self, api_key: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key, timeout=30.0, max_retries=0)

    async def generate(
        self, history: Sequence[DialogueMessage], question: str, style: str, model: str
    ) -> str:
        instructions = BASE_PROMPT + "\n" + STYLE_PROMPTS[style]
        dialogue = [
            {"role": item.role, "content": item.content} for item in history
        ]
        dialogue.append({"role": "user", "content": question})
        try:
            response = await self._client.responses.create(
                model=model,
                instructions=instructions,
                input=dialogue,
                max_output_tokens=MAX_OUTPUT_TOKENS,
                store=False,
            )
        except APITimeoutError as exc:
            log.warning("OpenAI request timed out")
            raise LLMTimeout() from exc
        except AuthenticationError as exc:
            log.error("OpenAI authentication failed")
            raise LLMAuthentication() from exc
        except RateLimitError as exc:
            log.warning("OpenAI rate limit reached")
            raise LLMRateLimited() from exc
        except (APIConnectionError, APIStatusError, OpenAIError) as exc:
            log.error(
                "OpenAI request failed: %s (status %s)",
                type(exc).__name__,
                getattr(exc, "status_code", "n/a"),
            )
            raise LLMUnavailable() from exc

        answer = (response.output_text or "").strip()
        if not answer:
            log.error("OpenAI returned no text output")
            raise LLMUnavailable()
        return answer

    async def close(self) -> None:
        await self._client.close()
