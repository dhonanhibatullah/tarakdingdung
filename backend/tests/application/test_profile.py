import uuid

import pytest

from tarakdingdung.application.profile.account.usecase import AccountUsecase
from tarakdingdung.application.profile.me.usecase import MeUsecase
from tarakdingdung.application.profile.security.usecase import SecurityUsecase
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.usecases.profile.account import UpdateProfileRequest
from tarakdingdung.domain.usecases.profile.me import GetProfilePermissionsRequest, GetProfileRequest
from tarakdingdung.domain.usecases.profile.security import ChangePasswordRequest
from tests.fakes.repositories import (
    FakePermissionRepository, FakeRolePermissionRepository, FakeRoleRepository,
    FakeUserRepository,
)
from tests.fakes.utilities import FakePassword, NullLogger


@pytest.fixture
async def ctx():
    roles = FakeRoleRepository()
    perms = FakePermissionRepository()
    rps = FakeRolePermissionRepository(roles=roles, permissions=perms)
    users = FakeUserRepository(roles=roles, role_permissions=rps, permissions=perms)
    rid = await roles.create(name="user", description=None, is_default=True, created_by=None)
    p = await perms.create(name="profile:get", description=None, created_by=None)
    await rps.create(role_id=rid, permission_id=p, created_by=None)
    uid = await users.create(role_id=rid, name="Grace", bio="", username="grace",
                             password_hash="hash::secret12", created_by=None)
    return users, uid


@pytest.mark.asyncio
async def test_me_get_profile_and_permissions(ctx):
    users, uid = ctx
    me = MeUsecase(users=users, logger=NullLogger())
    assert (await me.get_profile(GetProfileRequest(user_id=uid))).id == uid
    names = [p.name for p in await me.get_permissions(GetProfilePermissionsRequest(user_id=uid))]
    assert names == ["profile:get"]


@pytest.mark.asyncio
async def test_account_update_validates_and_persists(ctx):
    users, uid = ctx
    account = AccountUsecase(users=users, logger=NullLogger())
    with pytest.raises(DomainError):
        await account.update_profile(UpdateProfileRequest(user_id=uid, username="no good"))
    await account.update_profile(UpdateProfileRequest(user_id=uid, name="Grace Hopper", updated_by=uid))
    assert (await users.read_by_id(uid)).name == "Grace Hopper"


@pytest.mark.asyncio
async def test_change_password_flow(ctx):
    users, uid = ctx
    security = SecurityUsecase(users=users, password=FakePassword(), logger=NullLogger())
    with pytest.raises(DomainError) as ei:
        await security.change_password(ChangePasswordRequest(
            user_id=uid, current_password="wrong", new_password="brandnew1"))
    assert ei.value.type is ErrorType.UNAUTHORIZED
    with pytest.raises(DomainError) as ei2:
        await security.change_password(ChangePasswordRequest(
            user_id=uid, current_password="secret12", new_password="short"))
    assert ei2.value.type is ErrorType.VALIDATION
    await security.change_password(ChangePasswordRequest(
        user_id=uid, current_password="secret12", new_password="brandnew1", updated_by=uid))
    assert (await users.read_by_id(uid)).password_hash == "hash::brandnew1"


@pytest.mark.asyncio
async def test_change_password_missing_user(ctx):
    users, _uid = ctx
    security = SecurityUsecase(users=users, password=FakePassword(), logger=NullLogger())
    with pytest.raises(DomainError) as ei:
        await security.change_password(ChangePasswordRequest(
            user_id=uuid.uuid4(), current_password="x", new_password="brandnew1"))
    assert ei.value.type is ErrorType.NOT_FOUND
