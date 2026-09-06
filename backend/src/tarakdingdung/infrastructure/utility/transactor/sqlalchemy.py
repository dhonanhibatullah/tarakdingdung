from collections.abc import Awaitable, Callable
from typing import TypeVar

from tarakdingdung.domain.contracts.utility.transactor import Transactor
from tarakdingdung.infrastructure.repository.database.session import Database

T = TypeVar("T")


class SqlAlchemyTransactor(Transactor):
    def __init__(self, database: Database) -> None:
        self._database = database

    async def run(self, fn: Callable[[], Awaitable[T]]) -> T:
        async with self._database.sessionmaker() as session:
            token = self._database.current_session.set(session)
            try:
                async with session.begin():
                    return await fn()
            finally:
                self._database.current_session.reset(token)
