import pytest

from tarakdingdung.application.admin.user_management.usecase import UserManagementUsecase
from tarakdingdung.application.auth.session.usecase import SessionUsecase
from tarakdingdung.domain.models.error import DomainError
from tarakdingdung.domain.models.role import Role
from tarakdingdung.domain.usecases.admin.user_management import AddUserRequest
from tarakdingdung.domain.usecases.auth.session import LoginRequest, RefreshRequest


@pytest.fixture
def user_mgmt(user_repo, role_repo, user_role_repo, password):
    return UserManagementUsecase(user_repo, role_repo, user_role_repo, password)


@pytest.fixture
def session(user_repo, role_repo, user_role_repo, password, token):
    return SessionUsecase(user_repo, role_repo, user_role_repo, password, token)


async def _seed_user(user_mgmt, role_repo, username="alice"):
    role = await role_repo.create(Role(id="", name="trader"))
    await user_mgmt.add(
        AddUserRequest(
            username=username, email=f"{username}@b.c", password="secret", role_names=["trader"]
        )
    )


async def test_login_returns_tokens(session, user_mgmt, role_repo, token):
    await _seed_user(user_mgmt, role_repo)
    result = await session.login(LoginRequest(username="alice", password="secret"))
    claims = token.decode(result.access_token)
    assert claims.username == "alice"
    assert claims.roles == ["trader"]


async def test_login_wrong_password(session, user_mgmt, role_repo):
    await _seed_user(user_mgmt, role_repo)
    with pytest.raises(DomainError) as exc:
        await session.login(LoginRequest(username="alice", password="nope"))
    assert exc.value.error_type.value == "unauthorized"


async def test_login_unknown_user(session):
    with pytest.raises(DomainError):
        await session.login(LoginRequest(username="ghost", password="x"))


async def test_refresh_returns_new_tokens(session, user_mgmt, role_repo):
    await _seed_user(user_mgmt, role_repo)
    result = await session.login(LoginRequest(username="alice", password="secret"))
    refreshed = await session.refresh(RefreshRequest(refresh_token=result.refresh_token))
    assert refreshed.access_token
