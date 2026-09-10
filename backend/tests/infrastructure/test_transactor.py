import pytest

from tarakdingdung.infrastructure.utility.transactor.sqlalchemy import (
    SqlAlchemyTransactor,
)


class FakeSession:
    def __init__(self):
        self.committed = False
        self.rolled_back = False
        self.closed = False

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True

    async def close(self):
        self.closed = True


async def _ok(value):
    return value


async def _fail():
    raise RuntimeError("boom")


async def test_transactor_commits_on_success():
    session = FakeSession()
    transactor = SqlAlchemyTransactor(lambda: session)
    result = await transactor(lambda s: _ok(42))
    assert result == 42
    assert session.committed
    assert not session.rolled_back
    assert session.closed


async def test_transactor_rolls_back_on_error():
    session = FakeSession()
    transactor = SqlAlchemyTransactor(lambda: session)
    with pytest.raises(RuntimeError):
        await transactor(lambda s: _fail())
    assert session.rolled_back
    assert not session.committed
    assert session.closed
