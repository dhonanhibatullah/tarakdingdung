import asyncio
import json
from pathlib import Path

from tarakdingdung.composition.main import infrastructure
from tarakdingdung.config.settings import Settings
from tarakdingdung.domain.models.permission import Permission
from tarakdingdung.domain.models.role import Role
from tarakdingdung.domain.models.role_permission import RolePermission
from tarakdingdung.domain.models.user import User
from tarakdingdung.domain.models.user_role import UserRole


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


def run() -> None:
    settings = Settings()
    asyncio.run(_seed(settings))
