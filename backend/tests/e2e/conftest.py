from urllib.parse import urlparse

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from tarakdingdung.composition.main.driver import build_driver
from tarakdingdung.composition.main.infrastructure import build_infrastructure
from tarakdingdung.composition.main.launcher import create_app
from tarakdingdung.composition.seeder.launcher import seed
from tarakdingdung.config.settings import Settings


def _settings(url: str) -> Settings:
    p = urlparse(url.replace("+asyncpg", ""))
    return Settings(postgres_host=p.hostname, postgres_port=p.port, postgres_username=p.username,
                    postgres_password=p.password, postgres_database=p.path.lstrip("/"),
                    logger_format="plain", password_bcrypt_cost=4,
                    seed_super_password="superpass12")


@pytest_asyncio.fixture
async def e2e_app(migrated_url):
    settings = _settings(migrated_url)
    driver = build_driver(settings)
    infra = build_infrastructure(driver, settings)
    await seed(infra, settings)
    app = create_app(settings)
    try:
        yield app
    finally:
        async with driver.database.session() as s:
            await s.execute(text("DELETE FROM role_permission"))
            await s.execute(text("DELETE FROM users"))
            await s.execute(text("DELETE FROM roles"))
            await s.execute(text("DELETE FROM permissions"))
            await s.commit()
        await driver.database.dispose()
        await app.state.driver.database.dispose()


@pytest_asyncio.fixture
async def e2e_client(e2e_app):
    async with AsyncClient(transport=ASGITransport(app=e2e_app), base_url="http://t") as c:
        yield c


@pytest_asyncio.fixture
async def super_headers(e2e_client):
    resp = await e2e_client.post("/api/v1/auth/login",
                                 json={"username": "super", "password": "superpass12"})
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}
