import inspect
import uuid

import pytest

from tarakdingdung.domain.usecases.admin.permission_management import (
    CreatePermissionRequest, PermissionManagement,
)
from tarakdingdung.domain.usecases.admin.role_management import (
    AssignRolePermissionRequest, RoleManagement,
)
from tarakdingdung.domain.usecases.admin.user_management import (
    CreateUserRequest, UserManagement,
)
from tarakdingdung.domain.usecases.auth.session import LoginResult, Session
from tarakdingdung.domain.usecases.profile.account import Account
from tarakdingdung.domain.usecases.profile.me import Me
from tarakdingdung.domain.usecases.profile.security import Security


@pytest.mark.parametrize("cls", [PermissionManagement, RoleManagement, UserManagement,
                                 Session, Me, Account, Security])
def test_usecase_is_abc(cls):
    with pytest.raises(TypeError):
        cls()


def test_request_dataclasses_have_expected_defaults():
    r = CreatePermissionRequest(name="node:get")
    assert r.description is None and r.created_by is None
    u = CreateUserRequest(role_id=uuid.uuid4(), name="G", username="g", password="secret12")
    assert u.bio is None


def test_assign_role_permission_request_fields():
    r = AssignRolePermissionRequest(role_id=uuid.uuid4(), permission_id=uuid.uuid4())
    assert r.created_by is None


def test_login_result_shape():
    fields = set(LoginResult.__dataclass_fields__)
    assert fields == {"user", "role", "permissions", "access_token", "refresh_token"}


def test_session_methods_are_async():
    assert inspect.iscoroutinefunction(Session.login)
    assert inspect.iscoroutinefunction(Session.refresh)
