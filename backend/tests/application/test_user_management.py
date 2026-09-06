import uuid

import pytest

from tarakdingdung.application.admin.user_management.usecase import UserManagementUsecase
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.usecases.admin.user_management import (
    CreateUserRequest, DeleteUserRequest, ReadUserByIdRequest, ReadUserPermissionsRequest,
    ReadUsersByPaginationRequest, ResetUserPasswordRequest, UpdateUserRequest,
)
from tests.fakes.repositories import (
    FakePermissionRepository, FakeRolePermissionRepository, FakeRoleRepository,
    FakeUserRepository,
)
from tests.fakes.utilities import FakePassword, NullLogger


@pytest.fixture
def ctx():
    roles = FakeRoleRepository()
    perms = FakePermissionRepository()
    rps = FakeRolePermissionRepository(roles=roles, permissions=perms)
    users = FakeUserRepository(roles=roles, role_permissions=rps, permissions=perms)
    uc = UserManagementUsecase(users=users, password=FakePassword(), logger=NullLogger())
    return uc, roles, perms, rps, users


@pytest.mark.asyncio
async def test_create_validates_and_hashes(ctx):
    uc, roles, *_ = ctx
    rid = await roles.create(name="urole", description=None, is_default=None, created_by=None)
    with pytest.raises(DomainError) as ei:
        await uc.create(CreateUserRequest(role_id=rid, name="Ada", username="ad", password="x"))
    assert ei.value.type is ErrorType.VALIDATION
    uid = await uc.create(CreateUserRequest(
        role_id=rid, name="Ada Lovelace", username="ada", password="secret12"))
    user = await uc.read_by_id(ReadUserByIdRequest(id=uid))
    assert user.password_hash == "hash::secret12"


@pytest.mark.asyncio
async def test_duplicate_username_surfaces(ctx):
    uc, roles, *_ = ctx
    rid = await roles.create(name="urole", description=None, is_default=None, created_by=None)
    await uc.create(CreateUserRequest(role_id=rid, name="A B", username="dupe", password="secret12"))
    with pytest.raises(DomainError) as ei:
        await uc.create(CreateUserRequest(role_id=rid, name="C D", username="dupe",
                                          password="secret12"))
    assert ei.value.type is ErrorType.USERNAME_EXISTS


@pytest.mark.asyncio
async def test_reset_password_rehashes(ctx):
    uc, roles, *_ = ctx
    rid = await roles.create(name="urole", description=None, is_default=None, created_by=None)
    uid = await uc.create(CreateUserRequest(role_id=rid, name="E F", username="eff",
                                            password="secret12"))
    await uc.reset_password(ResetUserPasswordRequest(id=uid, password="newpass99"))
    user = await uc.read_by_id(ReadUserByIdRequest(id=uid))
    assert user.password_hash == "hash::newpass99"
    with pytest.raises(DomainError):
        await uc.reset_password(ResetUserPasswordRequest(id=uid, password="short"))


@pytest.mark.asyncio
async def test_update_validates_optional_fields_and_delete(ctx):
    uc, roles, *_ = ctx
    rid = await roles.create(name="urole", description=None, is_default=None, created_by=None)
    uid = await uc.create(CreateUserRequest(role_id=rid, name="G H", username="ghi",
                                            password="secret12"))
    with pytest.raises(DomainError):
        await uc.update_by_id(UpdateUserRequest(id=uid, username="no good"))
    await uc.update_by_id(UpdateUserRequest(id=uid, name="Grace Hopper"))
    await uc.delete_by_id(DeleteUserRequest(id=uid))
    with pytest.raises(DomainError) as ei:
        await uc.delete_by_id(DeleteUserRequest(id=uuid.uuid4()))
    assert ei.value.type is ErrorType.NOT_FOUND
