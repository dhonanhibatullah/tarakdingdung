import pytest

from tarakdingdung.application.auth.session.usecase import SessionUsecase
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.usecases.auth.session import LoginRequest, RefreshRequest
from tests.fakes.repositories import (
    FakePermissionRepository, FakeRolePermissionRepository, FakeRoleRepository,
    FakeUserRepository,
)
from tests.fakes.utilities import FakePassword, FakeToken, NullLogger


@pytest.fixture
async def ctx():
    roles = FakeRoleRepository()
    perms = FakePermissionRepository()
    rps = FakeRolePermissionRepository(roles=roles, permissions=perms)
    users = FakeUserRepository(roles=roles, role_permissions=rps, permissions=perms)
    token = FakeToken()
    uc = SessionUsecase(users=users, roles=roles, password=FakePassword(),
                        token=token, logger=NullLogger())
    rid = await roles.create(name="super", description=None, is_default=None, created_by=None)
    p_get = await perms.create(name="user:get", description=None, created_by=None)
    await rps.create(role_id=rid, permission_id=p_get, created_by=None)
    uid = await users.create(role_id=rid, name="Grace", bio=None, username="grace",
                             password_hash="hash::secret12", created_by=None)
    return uc, token, uid, rid


@pytest.mark.asyncio
async def test_login_success_returns_tokens_and_claims(ctx):
    uc, token, uid, _rid = ctx
    result = await uc.login(LoginRequest(username="grace", password="secret12"))
    assert result.user.id == uid
    assert result.role.name == "super"
    assert tuple(p.name for p in result.permissions) == ("user:get",)
    assert result.access_token == f"access::{uid}"
    assert token.last_access.permissions == ("user:get",)


@pytest.mark.asyncio
async def test_login_unknown_user_is_not_found(ctx):
    uc, *_ = ctx
    with pytest.raises(DomainError) as ei:
        await uc.login(LoginRequest(username="ghost", password="secret12"))
    assert ei.value.type is ErrorType.NOT_FOUND


@pytest.mark.asyncio
async def test_login_wrong_password_is_unauthorized(ctx):
    uc, *_ = ctx
    with pytest.raises(DomainError) as ei:
        await uc.login(LoginRequest(username="grace", password="wrong-one"))
    assert ei.value.type is ErrorType.UNAUTHORIZED


@pytest.mark.asyncio
async def test_refresh_roundtrip(ctx):
    uc, _token, uid, _rid = ctx
    result = await uc.refresh(RefreshRequest(refresh_token=f"refresh::{uid}"))
    assert result.user.id == uid and result.access_token == f"access::{uid}"


@pytest.mark.asyncio
async def test_refresh_invalid_token(ctx):
    uc, *_ = ctx
    with pytest.raises(DomainError) as ei:
        await uc.refresh(RefreshRequest(refresh_token="garbage"))
    assert ei.value.type is ErrorType.TOKEN_INVALID
