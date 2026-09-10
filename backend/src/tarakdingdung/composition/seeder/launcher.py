import asyncio
import json
from decimal import Decimal
from pathlib import Path

from tarakdingdung.composition.main import infrastructure
from tarakdingdung.config.settings import Settings
from tarakdingdung.domain.models.permission import Permission
from tarakdingdung.domain.models.portfolio import Balance, PortfolioSnapshot
from tarakdingdung.domain.models.role import Role
from tarakdingdung.domain.models.role_permission import RolePermission
from tarakdingdung.domain.models.symbol import (
    MembershipState,
    Symbol,
    Universe,
    UniverseMembership,
)
from tarakdingdung.domain.models.user import User
from tarakdingdung.domain.models.user_role import UserRole
from tarakdingdung.infrastructure.utility.clock.system import SystemClock


def _seed_dir() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "database" / "seeder").exists():
            return parent / "database" / "seeder"
    raise RuntimeError("database/seeder not found above the package")


def _load(name: str) -> list[dict]:
    return json.loads((_seed_dir() / name).read_text())


async def _seed(settings: Settings) -> None:
    repos = infrastructure.build_repositories(settings)
    password = infrastructure.build_password(settings)
    await _apply(repos, password, settings)


async def _apply(repos: dict, password, settings: Settings) -> None:
    permissions = repos["permissions"]
    roles = repos["roles"]
    role_permissions = repos["role_permissions"]
    users = repos["users"]
    user_roles = repos["user_roles"]

    for spec in _load("permission.json"):
        existing = await permissions.read_by_name(spec["name"])
        if existing is None:
            await permissions.create(
                Permission(
                    id="", name=spec["name"], description=spec.get("description", "")
                )
            )

    for spec in _load("role.json"):
        role = await roles.read_by_name(spec["name"])
        if role is None:
            role = await roles.create(
                Role(
                    id="",
                    name=spec["name"],
                    description=spec.get("description", ""),
                    is_default=spec.get("is_default", False),
                )
            )
        assigned = {rp.permission_id for rp in await role_permissions.read_by_role(role.id)}
        for perm_name in spec.get("permissions", []):
            perm = await permissions.read_by_name(perm_name)
            if perm is None or perm.id in assigned:
                continue
            await role_permissions.create(
                RolePermission(role_id=role.id, permission_id=perm.id)
            )

    for spec in _load("user.json"):
        user = await users.read_by_username(spec["username"])
        if user is None:
            password_value = getattr(settings, spec["password"])
            user = await users.create(
                User(
                    id="",
                    username=spec["username"],
                    email=spec["email"],
                    password_hash=password.hash(password_value),
                )
            )
        assigned_roles = {ur.role_id for ur in await user_roles.read_by_user(user.id)}
        for role_name in spec.get("roles", []):
            role = await roles.read_by_name(role_name)
            if role is None or role.id in assigned_roles:
                continue
            await user_roles.create(UserRole(user_id=user.id, role_id=role.id))

    await _seed_universe(repos, settings)


async def _seed_universe(repos: dict, settings: Settings) -> None:
    universes = repos["universes"]
    symbols = repos["symbols"]
    spec = json.loads((_seed_dir() / "universe.json").read_text())

    universe = await universes.read_by_id(spec["id"])
    if universe is None:
        universe = await universes.create(
            Universe(id=spec["id"], name=spec["name"])
        )

    for item in spec["symbols"]:
        symbol = await symbols.read_by_external(item["venue"], item["external"])
        if symbol is None:
            symbol = await symbols.create(
                Symbol(
                    id="",
                    venue=item["venue"],
                    base=item["base"],
                    quote=item["quote"],
                    external=item["external"],
                )
            )
        memberships = await universes.read_memberships(universe.id)
        if not any(m.symbol_id == symbol.id for m in memberships):
            await universes.add_membership(
                UniverseMembership(
                    universe_id=universe.id,
                    symbol_id=symbol.id,
                    state=MembershipState.APPROVED,
                    rationale="seeded",
                )
            )

    if settings.engine_mode == "paper":
        portfolio = repos["portfolio"]
        latest = await portfolio.read_latest(settings.engine_venue)
        if latest is None:
            equity = Decimal(settings.engine_initial_equity)
            await portfolio.create_snapshot(
                PortfolioSnapshot(
                    id="",
                    venue=settings.engine_venue,
                    as_of_ms=SystemClock().now_ms(),
                    equity=equity,
                ),
                [Balance(snapshot_id="", asset="IDR", free=equity, locked=Decimal("0"))],
            )


def run() -> None:
    settings = Settings()
    asyncio.run(_seed(settings))
