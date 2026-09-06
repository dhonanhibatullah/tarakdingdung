import pytest_asyncio

from tarakdingdung.infrastructure.repository.database.session import Database


@pytest_asyncio.fixture
async def db(migrated_url: str):
    database = Database(migrated_url, pool_size=5)
    async with database.engine.connect() as conn:
        trans = await conn.begin()
        session = database.sessionmaker(bind=conn)
        token = database.current_session.set(session)
        try:
            yield database
        finally:
            database.current_session.reset(token)
            await session.close()
            await trans.rollback()
    await database.dispose()
