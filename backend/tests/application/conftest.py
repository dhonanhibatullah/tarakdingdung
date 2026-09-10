import pytest

from tests.fakes.repositories import (
    InMemoryPermissionRepository,
    InMemoryRolePermissionRepository,
    InMemoryRoleRepository,
    InMemoryStore,
    InMemoryUserRepository,
    InMemoryUserRoleRepository,
)
from tarakdingdung.infrastructure.utility.password.bcrypt import BcryptPassword
from tarakdingdung.infrastructure.utility.token.jwt import JwtToken


@pytest.fixture
def store():
    return InMemoryStore()


@pytest.fixture
def permission_repo(store):
    return InMemoryPermissionRepository(store)


@pytest.fixture
def role_repo(store):
    return InMemoryRoleRepository(store)


@pytest.fixture
def role_permission_repo(store):
    return InMemoryRolePermissionRepository(store)


@pytest.fixture
def user_repo(store):
    return InMemoryUserRepository(store)


@pytest.fixture
def user_role_repo(store):
    return InMemoryUserRoleRepository(store)


@pytest.fixture
def password():
    return BcryptPassword(cost=4)


@pytest.fixture
def token():
    return JwtToken("a" * 32, "b" * 32, 900, 86400)
