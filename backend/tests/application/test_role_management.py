import uuid

import pytest

from tarakdingdung.application.admin.role_management.usecase import RoleManagementUsecase
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.usecases.admin.role_management import (
    AssignRolePermissionRequest, CreateRoleRequest, ReadDefaultRoleRequest,
    ReadRolePermissionByRoleIdAndPermissionIdRequest, ReadRolePermissionsByPaginationRequest,
    ReadRolePermissionsRequest, RevokeRolePermissionRequest, SetDefaultRoleRequest,
    UpdateRoleRequest,
)
from tests.fakes.repositories import (
    FakePermissionRepository, FakeRolePermissionRepository, FakeRoleRepository,
)
from tests.fakes.utilities import NullLogger


@pytest.fixture
def ctx():
    roles = FakeRoleRepository()
    perms = FakePermissionRepository()
    rps = FakeRolePermissionRepository(roles=roles, permissions=perms)
    uc = RoleManagementUsecase(roles=roles, role_permissions=rps, logger=NullLogger())
    return uc, roles, perms, rps


@pytest.mark.asyncio
async def test_create_validates_and_set_default(ctx):
    uc, *_ = ctx
    with pytest.raises(DomainError) as ei:
        await uc.create(CreateRoleRequest(name="x"))
    assert ei.value.type is ErrorType.VALIDATION
    a = await uc.create(CreateRoleRequest(name="role_a"))
    b = await uc.create(CreateRoleRequest(name="role_b"))
    await uc.set_default_role(SetDefaultRoleRequest(id=a))
    await uc.set_default_role(SetDefaultRoleRequest(id=b))
    default = await uc.read_default(ReadDefaultRoleRequest())
    assert default.id == b


@pytest.mark.asyncio
async def test_assign_revoke_and_read_pair(ctx):
    uc, roles, perms, _ = ctx
    rid = await uc.create(CreateRoleRequest(name="rp_role"))
    pid = await perms.create(name="rp:get", description=None, created_by=None)
    link = await uc.assign_permission(AssignRolePermissionRequest(role_id=rid, permission_id=pid))
    assert isinstance(link, uuid.UUID)
    with pytest.raises(DomainError) as ei:
        await uc.assign_permission(AssignRolePermissionRequest(role_id=rid, permission_id=pid))
    assert ei.value.type is ErrorType.ROLE_PERMISSION_EXISTS
    result = await uc.read_role_permission_by_role_id_and_permission_id(
        ReadRolePermissionByRoleIdAndPermissionIdRequest(role_id=rid, permission_id=pid))
    assert result.role.id == rid and result.permission.id == pid
    perms_of_role = await uc.read_permissions(ReadRolePermissionsRequest(role_id=rid))
    assert perms_of_role == []  # FakeRoleRepository.read_permissions is a stub that returns []
    await uc.revoke_permission(RevokeRolePermissionRequest(role_id=rid, permission_id=pid))
    with pytest.raises(DomainError) as ei:
        await uc.read_role_permission_by_role_id_and_permission_id(
            ReadRolePermissionByRoleIdAndPermissionIdRequest(role_id=rid, permission_id=pid))
    assert ei.value.type is ErrorType.NOT_FOUND


@pytest.mark.asyncio
async def test_read_role_permission_by_id_missing_raises(ctx):
    uc, *_ = ctx
    from tarakdingdung.domain.usecases.admin.role_management import ReadRolePermissionByIdRequest
    with pytest.raises(DomainError) as ei:
        await uc.read_role_permission_by_id(ReadRolePermissionByIdRequest(id=uuid.uuid4()))
    assert ei.value.type is ErrorType.NOT_FOUND


@pytest.mark.asyncio
async def test_pagination_of_role_permissions(ctx):
    uc, roles, perms, _ = ctx
    rid = await uc.create(CreateRoleRequest(name="pg_role"))
    pid = await perms.create(name="pg:get", description=None, created_by=None)
    await uc.assign_permission(AssignRolePermissionRequest(role_id=rid, permission_id=pid))
    rows, total = await uc.read_role_permissions_by_pagination(
        ReadRolePermissionsByPaginationRequest(page=1, limit=10, role_id=rid))
    assert total == 1 and rows[0].role.id == rid


@pytest.mark.asyncio
async def test_update_rejects_bad_name(ctx):
    uc, *_ = ctx
    rid = await uc.create(CreateRoleRequest(name="upd_role"))
    with pytest.raises(DomainError):
        await uc.update_by_id(UpdateRoleRequest(id=rid, name="!!"))
