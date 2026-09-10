import pytest

from tarakdingdung.application.admin.user_management.usecase import UserManagementUsecase
from tarakdingdung.application.profile.me.usecase import MeUsecase
from tarakdingdung.application.profile.security.usecase import SecurityUsecase
from tarakdingdung.domain.models.error import DomainError
from tarakdingdung.domain.models.role import Role
from tarakdingdung.domain.usecases.admin.user_management import AddUserRequest
from tarakdingdung.domain.usecases.profile.security import ChangePasswordRequest


@pytest.fixture
def user_mgmt(user_repo, role_repo, user_role_repo, password):
    return UserManagementUsecase(user_repo, role_repo, user_role_repo, password)


async def _seed_user(user_mgmt, role_repo):
    role = await role_repo.create(Role(id="", name="admin"))
    await user_mgmt.add(
        AddUserRequest(
            username="alice", email="a@b.c", password="secret", role_names=["admin"]
        )
    )


async def test_me_returns_profile(user_mgmt, role_repo, user_repo, user_role_repo):
    await _seed_user(user_mgmt, role_repo)
    user = await user_repo.read_by_username("alice")
    me = await MeUsecase(user_repo, user_role_repo, role_repo).get(user.id)
    assert me.username == "alice"
    assert me.roles == ["admin"]


async def test_me_missing_user(user_repo, user_role_repo, role_repo):
    with pytest.raises(DomainError):
        await MeUsecase(user_repo, user_role_repo, role_repo).get("missing")


async def test_change_password(user_mgmt, role_repo, user_repo, password):
    await _seed_user(user_mgmt, role_repo)
    user = await user_repo.read_by_username("alice")
    usecase = SecurityUsecase(user_repo, password)
    await usecase.change_password(
        ChangePasswordRequest(user_id=user.id, old_password="secret", new_password="newpass")
    )
    updated = await user_repo.read_by_id(user.id)
    assert password.verify("newpass", updated.password_hash)


async def test_change_password_wrong_old(user_mgmt, role_repo, user_repo, password):
    await _seed_user(user_mgmt, role_repo)
    user = await user_repo.read_by_username("alice")
    usecase = SecurityUsecase(user_repo, password)
    with pytest.raises(DomainError):
        await usecase.change_password(
            ChangePasswordRequest(user_id=user.id, old_password="wrong", new_password="newpass")
        )
