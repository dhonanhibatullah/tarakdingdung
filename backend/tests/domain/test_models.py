import pytest

from tarakdingdung.domain.models.error import DomainError
from tarakdingdung.domain.models.permission import Permission
from tarakdingdung.domain.models.role import Role
from tarakdingdung.domain.models.role_permission import RolePermission
from tarakdingdung.domain.models.user import User


def test_permission_is_frozen():
    p = Permission(id="1", name="trade:get")
    with pytest.raises(Exception):
        p.name = "other"


def test_permission_requires_name():
    with pytest.raises(DomainError):
        Permission(id="1", name="")


def test_role_defaults():
    r = Role(id="1", name="admin")
    assert r.description == ""


def test_role_requires_name():
    with pytest.raises(DomainError):
        Role(id="1", name="")


def test_role_permission_is_frozen():
    rp = RolePermission(role_id="r1", permission_id="p1")
    assert rp.role_id == "r1"
    assert rp.permission_id == "p1"


def test_user_requires_username_and_email():
    with pytest.raises(DomainError):
        User(id="1", username="", email="a@b.c", password_hash="x")
    with pytest.raises(DomainError):
        User(id="1", username="alice", email="", password_hash="x")


def test_user_defaults():
    u = User(id="1", username="alice", email="a@b.c", password_hash="x")
    assert u.is_active is True
    assert u.is_deleted is False
