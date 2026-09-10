import pytest

from tarakdingdung.application.admin.permission_management.usecase import (
    PermissionManagementUsecase,
)
from tarakdingdung.domain.models.error import DomainError
from tarakdingdung.domain.usecases.admin.permission_management import AddPermissionRequest


@pytest.fixture
def usecase(permission_repo):
    return PermissionManagementUsecase(permission_repo)


async def test_add_permission(usecase, permission_repo):
    perm = await usecase.add(AddPermissionRequest(name="trade:get"))
    assert perm.id
    assert perm.name == "trade:get"
    assert await permission_repo.read_by_name("trade:get") is not None


async def test_add_duplicate_permission_conflicts(usecase):
    await usecase.add(AddPermissionRequest(name="trade:get"))
    with pytest.raises(DomainError) as exc:
        await usecase.add(AddPermissionRequest(name="trade:get"))
    assert exc.value.error_type.value == "conflict"


async def test_list_paginates(usecase):
    for i in range(5):
        await usecase.add(AddPermissionRequest(name=f"p:{i}"))
    items, total = await usecase.list(1, 2)
    assert total == 5
    assert len(items) == 2
