from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from contextvars import ContextVar

from sqlalchemy.ext.asyncio import (
    AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine,
)


class Database:
    def __init__(self, dsn: str, *, pool_size: int, echo: bool = False) -> None:
        self.engine: AsyncEngine = create_async_engine(
            dsn, pool_size=pool_size, pool_pre_ping=True, echo=echo)
        self.sessionmaker: async_sessionmaker[AsyncSession] = async_sessionmaker(
            self.engine, expire_on_commit=False)
        self.current_session: ContextVar[AsyncSession | None] = ContextVar(
            "tarakdingdung_current_session", default=None)

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        existing = self.current_session.get()
        if existing is not None:
            yield existing
            return
        async with self.sessionmaker() as session:
            yield session

    async def dispose(self) -> None:
        await self.engine.dispose()
