import pytest

from tarakdingdung.composition.main.application import build_container
from tarakdingdung.composition.main.driver import build_driver
from tarakdingdung.composition.main.infrastructure import build_infrastructure
from tarakdingdung.config.settings import Settings
from tarakdingdung.presentation.http.dependencies.container import Container


def _settings(migrated_url: str) -> Settings:
    from urllib.parse import urlparse
    parsed = urlparse(migrated_url.replace("+asyncpg", ""))
    return Settings(
        postgres_host=parsed.hostname, postgres_port=parsed.port,
        postgres_username=parsed.username, postgres_password=parsed.password,
        postgres_database=parsed.path.lstrip("/"),
        logger_format="json",
    )


@pytest.mark.asyncio
async def test_container_has_every_usecase(migrated_url):
    settings = _settings(migrated_url)
    driver = build_driver(settings)
    infra = build_infrastructure(driver, settings)
    container = build_container(infra)
    assert isinstance(container, Container)
    for field in ("session", "permission_management", "role_management", "user_management",
                  "profile_me", "profile_account", "profile_security", "token"):
        assert getattr(container, field) is not None
    await driver.database.dispose()


@pytest.mark.asyncio
async def test_wired_permission_management_hits_real_db(migrated_url):
    settings = _settings(migrated_url)
    driver = build_driver(settings)
    infra = build_infrastructure(driver, settings)
    container = build_container(infra)
    from tarakdingdung.domain.usecases.admin.permission_management import (
        CreatePermissionRequest, ReadPermissionByNameRequest,
    )
    name = "wire:check"
    await container.permission_management.create(CreatePermissionRequest(name=name))
    got = await container.permission_management.read_by_name(
        ReadPermissionByNameRequest(name=name))
    assert got is not None and got.name == name
    # cleanup so the session-scoped migrated_url stays reusable
    async with driver.database.session() as s:
        from sqlalchemy import text
        await s.execute(text("DELETE FROM permissions WHERE name = :n"), {"n": name})
        await s.commit()
    await driver.database.dispose()
