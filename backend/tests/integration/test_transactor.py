import uuid

import pytest
from sqlalchemy import text

from tarakdingdung.infrastructure.utility.transactor.sqlalchemy import SqlAlchemyTransactor


@pytest.mark.asyncio
async def test_run_commits_on_success(db):
    tx = SqlAlchemyTransactor(db)
    pid = uuid.uuid4()

    async def op() -> None:
        async with db.session() as s:
            await s.execute(text(
                "INSERT INTO permissions (id, name) VALUES (:id, :n)"), {"id": pid, "n": "p:x"})

    await tx.run(op)
    async with db.session() as s:
        got = await s.scalar(text("SELECT name FROM permissions WHERE id = :id"), {"id": pid})
    assert got == "p:x"

    # clean up the row this test genuinely commits into the session-scoped
    # container so it doesn't leak into absolute-count assertions elsewhere.
    async with db.session() as s:
        await s.execute(text("DELETE FROM permissions WHERE id = :id"), {"id": pid})
        await s.commit()


@pytest.mark.asyncio
async def test_run_rolls_back_on_exception(db):
    tx = SqlAlchemyTransactor(db)
    pid = uuid.uuid4()

    async def op() -> None:
        async with db.session() as s:
            await s.execute(text(
                "INSERT INTO permissions (id, name) VALUES (:id, :n)"), {"id": pid, "n": "p:y"})
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        await tx.run(op)
    async with db.session() as s:
        got = await s.scalar(text("SELECT count(*) FROM permissions WHERE id = :id"), {"id": pid})
    assert got == 0


@pytest.mark.asyncio
async def test_nested_session_reuses_transaction_session(db):
    tx = SqlAlchemyTransactor(db)
    seen = []

    async def op() -> None:
        async with db.session() as a:
            async with db.session() as b:
                seen.append(a is b)

    await tx.run(op)
    assert seen == [True]
