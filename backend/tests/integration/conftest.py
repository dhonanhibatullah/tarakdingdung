import pytest
import pytest_asyncio
from sqlalchemy import text
from testcontainers.postgres import PostgresContainer

from tarakdingdung.infrastructure.repository.database.migrations import upgrade_to_head
from tarakdingdung.infrastructure.repository.database.session import Database


@pytest.fixture(scope="session")
def postgres_url() -> str:
    with PostgresContainer("postgres:16-alpine") as pg:
        raw = pg.get_connection_url()  # postgresql+psycopg2://user:pass@host:port/db
        yield raw.replace("+psycopg2", "+asyncpg")


@pytest.fixture(scope="session")
def migrated_url(postgres_url: str) -> str:
    upgrade_to_head(postgres_url)
    return postgres_url


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
