import uuid
from datetime import datetime, timezone

import pytest

from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.permission import Permission
from tarakdingdung.domain.models.role import Role
from tarakdingdung.domain.models.role_permission import RolePermission
from tarakdingdung.domain.models.token_claims import TokenClaimsAccess, TokenClaimsRefresh
from tarakdingdung.domain.models.user import User, UserListItem

NOW = datetime(2026, 9, 6, tzinfo=timezone.utc)


def test_error_type_values_are_their_names():
    assert ErrorType.NOT_FOUND == "NOT_FOUND"
    assert ErrorType.ROLE_PERMISSION_EXISTS == "ROLE_PERMISSION_EXISTS"


def test_domain_error_str_with_and_without_source():
    e1 = DomainError("nope", ErrorType.NOT_FOUND)
    assert str(e1) == "[NOT_FOUND] nope"
    src = ValueError("boom")
    e2 = DomainError("nope", ErrorType.FAILURE, src)
    assert str(e2) == "[FAILURE] nope: boom"
    assert e2.type is ErrorType.FAILURE
    assert e2.source is src


def test_models_are_frozen():
    p = Permission(id=uuid.uuid4(), name="n", description="", preferences={}, created_at=NOW)
    with pytest.raises(Exception):
        p.name = "other"


def test_role_has_is_default_field_order():
    r = Role(id=uuid.uuid4(), name="admin", description="d", is_default=True,
             preferences={}, created_at=NOW)
    assert r.is_default is True
    assert r.updated_at is None


def test_user_list_item_wraps_user():
    u = User(id=uuid.uuid4(), role_id=uuid.uuid4(), name="Grace", bio="", username="grace",
             password_hash="x", preferences={}, created_at=NOW)
    item = UserListItem(user=u, role_name="super")
    assert item.user is u
    assert item.role_name == "super"


def test_token_claims():
    uid = uuid.uuid4()
    a = TokenClaimsAccess(user_id=uid, name="G", username="g", role="super",
                          permissions=("user:get", "user:add"))
    assert a.permissions == ("user:get", "user:add")
    assert TokenClaimsRefresh(user_id=uid).user_id == uid


def test_role_permission_defaults_created_by_none():
    rp = RolePermission(id=uuid.uuid4(), role_id=uuid.uuid4(),
                        permission_id=uuid.uuid4(), created_at=NOW)
    assert rp.created_by is None
