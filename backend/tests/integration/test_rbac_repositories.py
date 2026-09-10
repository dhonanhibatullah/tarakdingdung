import pytest

from tarakdingdung.domain.models.permission import Permission
from tarakdingdung.domain.models.role import Role
from tarakdingdung.domain.models.role_permission import RolePermission
from tarakdingdung.domain.models.user import User
from tarakdingdung.domain.models.user_role import UserRole
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


@pytest.fixture
def permission_repo(session_factory):
    return SqlAlchemyPermissionRepository(session_factory)


@pytest.fixture
def role_repo(session_factory):
    return SqlAlchemyRoleRepository(session_factory)


@pytest.fixture
def role_permission_repo(session_factory):
    return SqlAlchemyRolePermissionRepository(session_factory)


@pytest.fixture
def user_repo(session_factory):
    return SqlAlchemyUserRepository(session_factory)


@pytest.fixture
def user_role_repo(session_factory):
    return SqlAlchemyUserRoleRepository(session_factory)


async def test_permission_crud_and_soft_delete(permission_repo):
    created = await permission_repo.create(Permission(id="", name="trade:get"))
    assert created.id
    assert await permission_repo.read_by_id(created.id) is not None
    assert await permission_repo.delete_by_id(created.id) is True
    assert await permission_repo.read_by_id(created.id) is None
    # name is reusable after soft delete
    again = await permission_repo.create(Permission(id="", name="trade:get"))
    assert again.id != created.id


async def test_permission_pagination(permission_repo):
    for i in range(5):
        await permission_repo.create(Permission(id="", name=f"p:{i}"))
    items, total = await permission_repo.read_by_pagination(1, 2)
    assert total == 5
    assert len(items) == 2


async def test_role_permissions_join(role_repo, permission_repo, role_permission_repo):
    role = await role_repo.create(Role(id="", name="trader"))
    perm = await permission_repo.create(Permission(id="", name="engine:run"))
    await role_permission_repo.create(
        RolePermission(role_id=role.id, permission_id=perm.id)
    )
    perms = await role_repo.read_permissions(role.id)
    assert [p.name for p in perms] == ["engine:run"]


async def test_user_and_roles(user_repo, role_repo, user_role_repo):
    user = await user_repo.create(
        User(id="", username="alice", email="a@b.c", password_hash="x")
    )
    role = await role_repo.create(Role(id="", name="admin"))
    await user_role_repo.create(UserRole(user_id=user.id, role_id=role.id))
    roles = await user_role_repo.read_roles_by_user(user.id)
    assert [r.name for r in roles] == ["admin"]
