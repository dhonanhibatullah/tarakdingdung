import asyncio
import json
from pathlib import Path

from tarakdingdung.composition.main.driver import build_driver
from tarakdingdung.composition.main.infrastructure import Infrastructure, build_infrastructure
from tarakdingdung.config.settings import Settings
from tarakdingdung.domain.models.market import Symbol, Venue
from tarakdingdung.domain.models.strategy import TradingMode

_SEED_DIR = Path(__file__).resolve().parents[4] / "database" / "seeder"


def _load(name: str) -> list[dict]:
    return json.loads((_SEED_DIR / name).read_text(encoding="utf-8"))


async def seed(infra: Infrastructure, settings: Settings) -> None:
    permissions = _load("permission.json")
    roles = _load("role.json")
    users = _load("user.json")
    strategies = _load("strategy.json")

    password_overrides = {
        "super": settings.seed_super_password,
        "admin": settings.seed_admin_password,
        "user": settings.seed_user_password,
    }

    async def _do() -> None:
        perm_ids: dict[str, object] = {}
        for entry in permissions:
            existing = await infra.permissions.read_by_name(entry["name"])
            if existing is None:
                perm_ids[entry["name"]] = await infra.permissions.create(
                    name=entry["name"], description=entry.get("description"), created_by=None)
            else:
                perm_ids[entry["name"]] = existing.id

        role_ids: dict[str, object] = {}
        for entry in roles:
            existing = await infra.roles.read_by_name(entry["name"])
            if existing is None:
                role_id = await infra.roles.create(
                    name=entry["name"], description=entry.get("description"),
                    is_default=entry.get("is_default", False), created_by=None)
            else:
                role_id = existing.id
            role_ids[entry["name"]] = role_id
            for perm_name in entry.get("permissions", []):
                pid = perm_ids[perm_name]
                link = await infra.role_permissions.read_by_role_id_and_permission_id(role_id, pid)
                if link is None:
                    await infra.role_permissions.create(
                        role_id=role_id, permission_id=pid, created_by=None)

        for entry in users:
            if await infra.users.read_by_username(entry["username"]) is not None:
                continue
            raw = password_overrides.get(entry["role_name"]) or entry["password"]
            password_hash = await infra.password.hash(raw)
            await infra.users.create(
                role_id=role_ids[entry["role_name"]], name=entry["name"], bio=None,
                username=entry["username"], password_hash=password_hash, created_by=None)

        for entry in strategies:
            if await infra.strategies.read_by_name(entry["name"]) is not None:
                continue
            universe = tuple(
                Symbol(venue=Venue(item["venue"].upper()),
                       base=item["base"].upper(), quote=item["quote"].upper())
                for item in entry.get("universe", []))
            await infra.strategies.create(
                name=entry["name"], description=entry.get("description"),
                kind=entry["kind"], mode=TradingMode(entry["mode"].upper()),
                universe=universe, parameters=entry.get("parameters") or {},
                is_enabled=entry.get("is_enabled", False), created_by=None)

    await infra.transactor.run(_do)


async def _run(settings: Settings) -> None:
    """Seed and release, inside one event loop.

    Both halves must share a loop: asyncpg binds a connection to the loop that
    opened it, so disposing the pool from a second ``asyncio.run`` tears down
    connections that belong to a loop which no longer exists.
    """
    driver = build_driver(settings)
    try:
        await seed(build_infrastructure(driver, settings), settings)
    finally:
        await driver.database.dispose()
        await driver.http.aclose()


def run() -> None:
    asyncio.run(_run(Settings()))
