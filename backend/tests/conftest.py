import pytest

from testcontainers.postgres import PostgresContainer

from tarakdingdung.config.settings import Settings
from tarakdingdung.infrastructure.repository.database.migrations import upgrade_to_head


@pytest.fixture
def settings() -> Settings:
    return Settings()


@pytest.fixture(scope="session")
def postgres_url() -> str:
    with PostgresContainer("postgres:16-alpine") as pg:
        raw = pg.get_connection_url()  # postgresql+psycopg2://user:pass@host:port/db
        yield raw.replace("+psycopg2", "+asyncpg")


@pytest.fixture(scope="session")
def migrated_url(postgres_url: str) -> str:
    upgrade_to_head(postgres_url)
    return postgres_url
