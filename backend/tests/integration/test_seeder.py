import pytest
from sqlalchemy import text

from tarakdingdung.composition.main.driver import build_driver
from tarakdingdung.composition.main.infrastructure import build_infrastructure
from tarakdingdung.composition.seeder.launcher import seed
from tarakdingdung.config.settings import Settings


def _settings(url: str) -> Settings:
    from urllib.parse import urlparse
    p = urlparse(url.replace("+asyncpg", ""))
    return Settings(postgres_host=p.hostname, postgres_port=p.port, postgres_username=p.username,
                    postgres_password=p.password, postgres_database=p.path.lstrip("/"),
                    logger_format="json", seed_super_password="superpass12")


@pytest.mark.asyncio
async def test_seed_is_idempotent_and_links_permissions(migrated_url):
    settings = _settings(migrated_url)
    driver = build_driver(settings)
    infra = build_infrastructure(driver, settings)
    try:
        await seed(infra, settings)
        await seed(infra, settings)  # second run must not raise or duplicate
        async with driver.database.session() as s:
            perms = await s.scalar(text("SELECT count(*) FROM permissions WHERE deleted_at IS NULL"))
            roles = await s.scalar(text("SELECT count(*) FROM roles WHERE deleted_at IS NULL"))
            users = await s.scalar(text("SELECT count(*) FROM users WHERE deleted_at IS NULL"))
            super_links = await s.scalar(text(
                "SELECT count(*) FROM role_permission rp "
                "JOIN roles r ON r.id = rp.role_id WHERE r.name = 'super'"))
            default_role = await s.scalar(text(
                "SELECT name FROM roles WHERE is_default = TRUE AND deleted_at IS NULL"))
        assert perms == 20 and roles == 3 and users == 3
        assert super_links == 20
        assert default_role == "user"
    finally:
        async with driver.database.session() as s:
            await s.execute(text("DELETE FROM role_permission"))
            await s.execute(text("DELETE FROM users"))
            await s.execute(text("DELETE FROM roles"))
            await s.execute(text("DELETE FROM permissions"))
            await s.commit()
        await driver.database.dispose()


@pytest.mark.asyncio
async def test_seed_hashes_password_from_settings(migrated_url):
    settings = _settings(migrated_url)
    driver = build_driver(settings)
    infra = build_infrastructure(driver, settings)
    try:
        await seed(infra, settings)
        user = await infra.users.read_by_username("super")
        await infra.password.compare(user.password_hash, "superpass12")  # no raise
    finally:
        async with driver.database.session() as s:
            await s.execute(text("DELETE FROM role_permission"))
            await s.execute(text("DELETE FROM users"))
            await s.execute(text("DELETE FROM roles"))
            await s.execute(text("DELETE FROM permissions"))
            await s.commit()
        await driver.database.dispose()
