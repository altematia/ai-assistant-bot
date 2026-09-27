from __future__ import annotations

import unittest

from app.config import MAX_HISTORY_MESSAGES
from app.database.repository import DialogueMessage
from app.database.session import Database
from app.services.conversation import ConversationService, Identity
from app.utils.text import split_text


class FakeGenerator:
    def __init__(self) -> None:
        self.calls: list[tuple[list[DialogueMessage], str, str, str]] = []

    async def generate(
        self, history: list[DialogueMessage], question: str, style: str, model: str
    ) -> str:
        self.calls.append((list(history), question, style, model))
        return f"Ответ на {question}"


class ConversationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.database = Database("sqlite+aiosqlite:///:memory:")
        await self.database.create_tables()
        self.generator = FakeGenerator()
        self.service = ConversationService(self.database, self.generator, "gpt-5-mini")
        self.alice = Identity(101, "alice", "Алиса")
        self.bob = Identity(202, "bob", "Боб")

    async def asyncTearDown(self) -> None:
        await self.database.close()

    async def test_history_is_isolated_limited_and_reset(self) -> None:
        for number in range(12):
            await self.service.ask(self.alice, f"Вопрос {number}")
        await self.service.ask(self.bob, "Другой вопрос")
        await self.service.ask(self.alice, "Последний вопрос")

        history, question, style, model = self.generator.calls[-1]
        self.assertEqual(len(history), MAX_HISTORY_MESSAGES)
        self.assertEqual(history[0].content, "Вопрос 2")
        self.assertEqual(question, "Последний вопрос")
        self.assertEqual((style, model), ("normal", "gpt-5-mini"))

        alice_stats = await self.service.stats(self.alice)
        bob_stats = await self.service.stats(self.bob)
        self.assertEqual((alice_stats.user_messages, alice_stats.assistant_messages), (13, 13))
        self.assertEqual((bob_stats.user_messages, bob_stats.assistant_messages), (1, 1))

        await self.service.set_style(self.alice, "detailed")
        await self.service.reset(self.alice)
        self.assertEqual((await self.service.stats(self.alice)).user_messages, 0)
        self.assertEqual((await self.service.stats(self.bob)).user_messages, 1)
        self.assertEqual((await self.service.settings(self.alice)).style, "detailed")
        await self.service.ask(self.alice, "Новый разговор")
        self.assertEqual(self.generator.calls[-1][0], [])
        self.assertEqual(self.generator.calls[-1][2], "detailed")

    def test_long_reply_is_split_for_telegram(self) -> None:
        chunks = split_text("A" * 8500)
        self.assertEqual([len(part) for part in chunks], [4000, 4000, 500])
