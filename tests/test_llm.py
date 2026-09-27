from __future__ import annotations

import unittest
from types import SimpleNamespace

from app.database.repository import DialogueMessage
from app.services.llm import OpenAITextGenerator


class FakeResponses:
    def __init__(self) -> None:
        self.kwargs: dict[str, object] = {}

    async def create(self, **kwargs: object) -> SimpleNamespace:
        self.kwargs = kwargs
        return SimpleNamespace(output_text="  Готовый ответ.  ")


class FakeClient:
    def __init__(self) -> None:
        self.responses = FakeResponses()

    async def close(self) -> None:
        pass


class LLMTests(unittest.IsolatedAsyncioTestCase):
    async def test_request_uses_history_style_and_no_api_storage(self) -> None:
        generator = OpenAITextGenerator("placeholder-key")
        client = FakeClient()
        generator._client = client
        answer = await generator.generate(
            [DialogueMessage("user", "Привет"), DialogueMessage("assistant", "Здравствуйте")],
            "Помоги с письмом", "short", "gpt-5-mini",
        )
        self.assertEqual(answer, "Готовый ответ.")
        self.assertEqual(client.responses.kwargs["model"], "gpt-5-mini")
        self.assertEqual(client.responses.kwargs["store"], False)
        self.assertIn("максимально кратко", client.responses.kwargs["instructions"])
        self.assertEqual(
            [item["role"] for item in client.responses.kwargs["input"]],
            ["user", "assistant", "user"],
        )
        await generator.close()
