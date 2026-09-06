import uuid

import pytest

from tarakdingdung.application.admin.permission_management.usecase import (
    PermissionManagementUsecase,
)
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.usecases.admin.permission_management import (
    CreatePermissionRequest, DeletePermissionRequest, ReadPermissionsByPaginationRequest,
    UpdatePermissionRequest,
)
from tests.fakes.repositories import FakePermissionRepository
from tests.fakes.utilities import NullLogger


@pytest.fixture
def uc():
    return PermissionManagementUsecase(permissions=FakePermissionRepository(), logger=NullLogger())


@pytest.mark.asyncio
async def test_create_validates_name_then_persists(uc):
    with pytest.raises(DomainError) as ei:
        await uc.create(CreatePermissionRequest(name="bad name"))
    assert ei.value.type is ErrorType.VALIDATION
    pid = await uc.create(CreatePermissionRequest(name="node:get", description="d"))
    got = await uc.read_by_id(__import__("tarakdingdung.domain.usecases.admin.permission_management",
                                         fromlist=["ReadPermissionByIdRequest"])
                              .ReadPermissionByIdRequest(id=pid))
    assert got.name == "node:get"


@pytest.mark.asyncio
async def test_update_rejects_bad_name_and_updates_good(uc):
    pid = await uc.create(CreatePermissionRequest(name="upd:one"))
    with pytest.raises(DomainError):
        await uc.update_by_id(UpdatePermissionRequest(id=pid, name="bad name"))
    await uc.update_by_id(UpdatePermissionRequest(id=pid, description="new"))


@pytest.mark.asyncio
async def test_pagination_and_delete(uc):
    for n in ["a:get", "a:set", "b:get"]:
        await uc.create(CreatePermissionRequest(name=n))
    items, total = await uc.read_by_pagination(
        ReadPermissionsByPaginationRequest(page=1, limit=10, search="a:"))
    assert total == 2 and {i.name for i in items} == {"a:get", "a:set"}
    await uc.delete_by_id(DeletePermissionRequest(id=items[0].id))
    with pytest.raises(DomainError) as ei:
        await uc.delete_by_id(DeletePermissionRequest(id=uuid.uuid4()))
    assert ei.value.type is ErrorType.NOT_FOUND
