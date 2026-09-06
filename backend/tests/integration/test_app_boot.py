import pytest
from httpx import ASGITransport, AsyncClient

from tarakdingdung.composition.main.launcher import create_app
from tarakdingdung.config.settings import Settings


def _settings(migrated_url: str) -> Settings:
    from urllib.parse import urlparse
    parsed = urlparse(migrated_url.replace("+asyncpg", ""))
    return Settings(
        postgres_host=parsed.hostname, postgres_port=parsed.port,
        postgres_username=parsed.username, postgres_password=parsed.password,
        postgres_database=parsed.path.lstrip("/"),
        logger_format="json", app_version="v-boot",
    )


@pytest.mark.asyncio
async def test_app_serves_version_and_openapi(migrated_url):
    app = create_app(_settings(migrated_url))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        v = await c.get("/api/version")
        assert v.status_code == 200 and v.text == "v-boot"
        spec = await c.get("/api/openapi.json")
        assert spec.status_code == 200
        paths = spec.json()["paths"]
        assert "/api/v1/auth/login" in paths
        assert "/api/v1/admin/users/{id}" in paths
    await app.state.driver.database.dispose()


@pytest.mark.asyncio
async def test_lifespan_disposes_engine_on_shutdown(migrated_url):
    app = create_app(_settings(migrated_url))
    engine = app.state.driver.database.engine
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            assert (await c.get("/api/version")).status_code == 200
        pool_before = engine.pool
    # AsyncEngine.dispose() swaps in a fresh pool -> proof the engine was disposed
    assert engine.pool is not pool_before


@pytest.mark.asyncio
async def test_unknown_route_is_404_not_proxied(migrated_url):
    app = create_app(_settings(migrated_url))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        assert (await c.get("/not/a/route")).status_code == 404
    await app.state.driver.database.dispose()
