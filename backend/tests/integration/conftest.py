import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.community.postgres import PostgresContainer

from tarakdingdung.infrastructure.repository.database.migrations import upgrade_to_head
from tarakdingdung.infrastructure.repository.database.orm import Base


@pytest.fixture(scope="session")
def postgres_dsn():
    with PostgresContainer("postgres:16") as pg:
        url = pg.get_connection_url()
        for driver in ("+psycopg2", "+pg8000", "+psycopg"):
            url = url.replace(driver, "+asyncpg")
        upgrade_to_head(url)
        yield url


@pytest.fixture
async def session_factory(postgres_dsn):
    engine = create_async_engine(postgres_dsn)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest.fixture(autouse=True)
async def _clean_tables(session_factory):
    async with session_factory() as session:
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(text(f'TRUNCATE TABLE "{table.name}" CASCADE'))
        await session.commit()
    yield
