import pytest

from tarakdingdung.application.admin.user_management.usecase import UserManagementUsecase
from tarakdingdung.domain.models.error import DomainError
from tarakdingdung.domain.models.role import Role
from tarakdingdung.domain.usecases.admin.user_management import AddUserRequest


@pytest.fixture
def usecase(user_repo, role_repo, user_role_repo, password):
    return UserManagementUsecase(user_repo, role_repo, user_role_repo, password)


async def test_add_user_with_role(usecase, role_repo, user_role_repo):
    role = await role_repo.create(Role(id="", name="admin"))
    user = await usecase.add(
        AddUserRequest(
            username="alice", email="a@b.c", password="secret", role_names=["admin"]
        )
    )
    assert user.id
    assert user.password_hash != "secret"
    roles = await user_role_repo.read_roles_by_user(user.id)
    assert [r.name for r in roles] == ["admin"]


async def test_add_duplicate_username_conflicts(usecase):
    await usecase.add(AddUserRequest(username="alice", email="a@b.c", password="x"))
    with pytest.raises(DomainError):
        await usecase.add(AddUserRequest(username="alice", email="c@b.c", password="x"))


async def test_add_with_missing_role(usecase):
    with pytest.raises(DomainError):
        await usecase.add(
            AddUserRequest(
                username="alice", email="a@b.c", password="x", role_names=["ghost"]
            )
        )


async def test_deactivate(usecase, user_repo):
    user = await usecase.add(AddUserRequest(username="alice", email="a@b.c", password="x"))
    updated = await usecase.deactivate(user.id)
    assert updated.is_active is False
    fetched = await user_repo.read_by_id(user.id)
    assert fetched.is_active is False
