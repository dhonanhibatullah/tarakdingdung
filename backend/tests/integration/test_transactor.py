import pytest
from sqlalchemy import text

from tarakdingdung.infrastructure.utility.transactor.sqlalchemy import (
    SqlAlchemyTransactor,
)


async def test_transactor_commits(session_factory):
    transactor = SqlAlchemyTransactor(session_factory)

    async def work(session):
        await session.execute(
            text("INSERT INTO permissions (id, name, description) VALUES ('c1', 'commit-test', '')")
        )

    await transactor(work)

    async with session_factory() as session:
        result = await session.execute(
            text("SELECT count(*) FROM permissions WHERE id = 'c1'")
        )
        assert result.scalar() == 1


async def test_transactor_rolls_back(session_factory):
    transactor = SqlAlchemyTransactor(session_factory)

    async def work(session):
        await session.execute(
            text("INSERT INTO permissions (id, name, description) VALUES ('r1', 'rollback-test', '')")
        )
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        await transactor(work)

    async with session_factory() as session:
        result = await session.execute(
            text("SELECT count(*) FROM permissions WHERE id = 'r1'")
        )
        assert result.scalar() == 0
