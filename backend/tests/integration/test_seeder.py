import pytest

from tarakdingdung.composition.seeder.launcher import _apply
from tarakdingdung.config.settings import Settings
from tarakdingdung.infrastructure.repository.permission.repository import (
    SqlAlchemyPermissionRepository,
)
from tarakdingdung.infrastructure.repository.role.repository import SqlAlchemyRoleRepository
from tarakdingdung.infrastructure.repository.role_permission.repository import (
    SqlAlchemyRolePermissionRepository,
)
from tarakdingdung.infrastructure.repository.user.repository import SqlAlchemyUserRepository
from tarakdingdung.infrastructure.repository.user_role.repository import (
    SqlAlchemyUserRoleRepository,
)
from tarakdingdung.infrastructure.utility.password.bcrypt import BcryptPassword


def _repos(session_factory):
    return {
        "permissions": SqlAlchemyPermissionRepository(session_factory),
        "roles": SqlAlchemyRoleRepository(session_factory),
        "role_permissions": SqlAlchemyRolePermissionRepository(session_factory),
        "users": SqlAlchemyUserRepository(session_factory),
        "user_roles": SqlAlchemyUserRoleRepository(session_factory),
    }


def _settings():
    return Settings(
        _env_file=None,
        seed_super_password="s",
        seed_admin_password="a",
        seed_user_password="u",
    )


async def test_seeder_is_idempotent(session_factory):
    repos = _repos(session_factory)
    password = BcryptPassword(cost=4)
    settings = _settings()

    await _apply(repos, password, settings)
    perms1, _ = await repos["permissions"].read_by_pagination(1, 100)
    roles1, _ = await repos["roles"].read_by_pagination(1, 100)
    users1, _ = await repos["users"].read_by_pagination(1, 100)

    await _apply(repos, password, settings)
    perms2, _ = await repos["permissions"].read_by_pagination(1, 100)
    roles2, _ = await repos["roles"].read_by_pagination(1, 100)
    users2, _ = await repos["users"].read_by_pagination(1, 100)

    assert len(perms1) == len(perms2)
    assert len(roles1) == len(roles2)
    assert len(users1) == len(users2)
    assert len(perms1) > 0


async def test_seeder_assigns_default_role(session_factory):
    repos = _repos(session_factory)
    password = BcryptPassword(cost=4)
    await _apply(repos, password, _settings())

    default = await repos["roles"].read_default()
    assert default is not None
    assert default.name == "user"

    user = await repos["users"].read_by_username("user")
    roles = await repos["user_roles"].read_roles_by_user(user.id)
    assert [r.name for r in roles] == ["user"]
