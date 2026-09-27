"""Async database engine and sessions."""

from __future__ import annotations

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.database.models import Base


class Database:
    def __init__(self, url: str) -> None:
        self.engine: AsyncEngine = create_async_engine(url, pool_pre_ping=True)
        self.sessions: async_sessionmaker[AsyncSession] = async_sessionmaker(
            self.engine, expire_on_commit=False
        )
        if url.startswith("sqlite+"):
            @event.listens_for(self.engine.sync_engine, "connect")
            def enable_foreign_keys(dbapi_connection: object, _: object) -> None:
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

    async def create_tables(self) -> None:
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def close(self) -> None:
        await self.engine.dispose()
