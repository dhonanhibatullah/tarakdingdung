import inspect

import pytest

from tarakdingdung.domain.contracts.repository.permission import PermissionRepository
from tarakdingdung.domain.contracts.repository.role import RoleRepository
from tarakdingdung.domain.contracts.repository.role_permission import RolePermissionRepository
from tarakdingdung.domain.contracts.repository.user import UserRepository
from tarakdingdung.domain.contracts.utility.password import Password
from tarakdingdung.domain.contracts.utility.token import Token
from tarakdingdung.domain.contracts.utility.transactor import Transactor

ALL = [PermissionRepository, RoleRepository, RolePermissionRepository, UserRepository,
       Password, Token, Transactor]


@pytest.mark.parametrize("cls", ALL)
def test_cannot_instantiate_abc(cls):
    with pytest.raises(TypeError):
        cls()


def test_repository_verbs_are_the_fixed_set():
    verbs = {n for n in dir(UserRepository) if not n.startswith("_")}
    assert verbs == {
        "create", "read_by_id", "read_by_username", "read_permissions",
        "read_by_pagination", "update_by_id", "delete_by_id",
    }


@pytest.mark.parametrize("cls,method", [
    (PermissionRepository, "create"),
    (RoleRepository, "read_default"),
    (UserRepository, "read_permissions"),
    (Password, "hash"),
    (Token, "validate_access"),
    (Transactor, "run"),
])
def test_methods_are_coroutine_functions(cls, method):
    assert inspect.iscoroutinefunction(getattr(cls, method))
