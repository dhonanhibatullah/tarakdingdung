import uuid
from datetime import datetime, timezone

from tarakdingdung.domain.models.permission import Permission
from tarakdingdung.domain.models.role import Role
from tarakdingdung.domain.models.user import User, UserListItem
from tarakdingdung.domain.usecases.admin.role_management import RolePermissionResult
from tarakdingdung.domain.models.role_permission import RolePermission
from tarakdingdung.domain.usecases.auth.session import LoginResult
from tarakdingdung.presentation.http.schemas import response as r

NOW = datetime(2026, 9, 6, tzinfo=timezone.utc)


def _perm(name="node:get"):
    return Permission(id=uuid.uuid4(), name=name, description="d", preferences={}, created_at=NOW)


def _role():
    return Role(id=uuid.uuid4(), name="super", description="", is_default=False,
               preferences={}, created_at=NOW)


def _user(role_id):
    return User(id=uuid.uuid4(), role_id=role_id, name="Grace", bio="b", username="grace",
               password_hash="secret", preferences={}, created_at=NOW)


def test_permission_response_shape_and_preferences_default():
    p = Permission(id=uuid.uuid4(), name="x:y", description="", preferences=None,  # type: ignore[arg-type]
                   created_at=NOW)
    resp = r.permission_response(p)
    assert resp.id == str(p.id) and resp.preferences == {}
    assert resp.model_dump()["created_by"] is None


def test_user_response_never_leaks_password_hash():
    role = _role()
    resp = r.user_response(_user(role.id))
    assert "password_hash" not in resp.model_dump()
    assert resp.role_id == str(role.id)


def test_user_list_item_response_carries_role_name():
    role = _role()
    item = UserListItem(user=_user(role.id), role_name="super")
    assert r.user_list_item_response(item).role_name == "super"


def test_login_response_maps_all_parts():
    role = _role()
    result = LoginResult(user=_user(role.id), role=role, permissions=(_perm("a:b"),),
                         access_token="AT", refresh_token="RT")
    resp = r.login_response(result)
    assert resp.access_token == "AT" and resp.refresh_token == "RT"
    assert [p.name for p in resp.permissions] == ["a:b"]


def test_role_permission_detail_response():
    role = _role()
    perm = _perm()
    rp = RolePermission(id=uuid.uuid4(), role_id=role.id, permission_id=perm.id, created_at=NOW)
    detail = r.role_permission_detail_response(
        RolePermissionResult(role_permission=rp, role=role, permission=perm))
    assert detail.role.id == str(role.id) and detail.permission.id == str(perm.id)


def test_page_data_response_generic():
    page = r.PageResponse(page=1, limit=10, total_items=2)
    pdr = r.PageDataResponse[r.PermissionResponse](
        data=[r.permission_response(_perm())], page=page)
    assert pdr.model_dump()["page"]["total_items"] == 2
