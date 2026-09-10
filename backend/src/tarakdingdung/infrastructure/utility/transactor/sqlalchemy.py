from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from tarakdingdung.domain.contracts.utility.transactor import Transactor

T = TypeVar("T")


class SqlAlchemyTransactor(Transactor):
    def __init__(self, session_factory: Callable[[], Any]) -> None:
        self._session_factory = session_factory

    async def __call__(self, fn: Callable[[Any], Awaitable[T]]) -> T:
        session = self._session_factory()
        try:
            result = await fn(session)
            await session.commit()
            return result
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
