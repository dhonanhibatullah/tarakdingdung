import pytest

from tarakdingdung.application.admin.role_management.usecase import RoleManagementUsecase
from tarakdingdung.domain.models.error import DomainError
from tarakdingdung.domain.models.permission import Permission
from tarakdingdung.domain.usecases.admin.role_management import AddRoleRequest


@pytest.fixture
def usecase(role_repo, permission_repo, role_permission_repo):
    return RoleManagementUsecase(role_repo, permission_repo, role_permission_repo)


async def test_add_role(usecase, role_repo):
    role = await usecase.add(AddRoleRequest(name="admin"))
    assert role.id
    assert await role_repo.read_by_name("admin") is not None


async def test_add_default_role(usecase, role_repo):
    await usecase.add(AddRoleRequest(name="user", is_default=True))
    default = await role_repo.read_default()
    assert default is not None
    assert default.name == "user"


async def test_assign_permission_and_read(usecase, permission_repo):
    role = await usecase.add(AddRoleRequest(name="trader"))
    perm = await permission_repo.create(Permission(id="", name="engine:run"))
    await usecase.assign_permission(role.id, perm.id)
    perms = await usecase.permissions(role.id)
    assert [p.name for p in perms] == ["engine:run"]


async def test_assign_permission_missing_role(usecase):
    with pytest.raises(DomainError):
        await usecase.assign_permission("missing", "missing")
