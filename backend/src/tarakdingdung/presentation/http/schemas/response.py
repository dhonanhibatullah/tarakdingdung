from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel

from tarakdingdung.domain.models.permission import Permission
from tarakdingdung.domain.models.role import Role
from tarakdingdung.domain.models.user import User, UserListItem
from tarakdingdung.domain.usecases.admin.role_management import RolePermissionResult
from tarakdingdung.domain.usecases.auth.session import LoginResult

T = TypeVar("T")


def uuid_str(value: UUID | None) -> str | None:
    if value is None or value == UUID(int=0):
        return None
    return str(value)


def normalize_preferences(value: dict | None) -> dict:
    return value or {}


class AuditResponse(BaseModel):
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
    created_by: str | None = None
    updated_by: str | None = None
    deleted_by: str | None = None


def _audit(obj) -> dict:
    return dict(
        created_at=obj.created_at, updated_at=obj.updated_at, deleted_at=obj.deleted_at,
        created_by=uuid_str(obj.created_by), updated_by=uuid_str(obj.updated_by),
        deleted_by=uuid_str(obj.deleted_by),
    )


class PermissionResponse(AuditResponse):
    id: str
    name: str
    description: str
    preferences: dict


def permission_response(p: Permission) -> PermissionResponse:
    return PermissionResponse(id=str(p.id), name=p.name, description=p.description,
                              preferences=normalize_preferences(p.preferences), **_audit(p))


def permissions_response(items: list[Permission]) -> list[PermissionResponse]:
    return [permission_response(p) for p in items]


class RoleResponse(AuditResponse):
    id: str
    name: str
    description: str
    is_default: bool
    preferences: dict


def role_response(role: Role) -> RoleResponse:
    return RoleResponse(id=str(role.id), name=role.name, description=role.description,
                        is_default=role.is_default,
                        preferences=normalize_preferences(role.preferences), **_audit(role))


def roles_response(items: list[Role]) -> list[RoleResponse]:
    return [role_response(r) for r in items]


class UserResponse(AuditResponse):
    id: str
    role_id: str
    role_name: str | None = None
    name: str
    bio: str
    username: str
    preferences: dict


def user_response(user: User) -> UserResponse:
    return UserResponse(id=str(user.id), role_id=str(user.role_id), name=user.name,
                        bio=user.bio, username=user.username,
                        preferences=normalize_preferences(user.preferences), **_audit(user))


def user_list_item_response(item: UserListItem) -> UserResponse:
    resp = user_response(item.user)
    resp.role_name = item.role_name or None
    return resp


def users_response(items: list[User]) -> list[UserResponse]:
    return [user_response(u) for u in items]


def user_list_items_response(items: list[UserListItem]) -> list[UserResponse]:
    return [user_list_item_response(i) for i in items]


class RolePermissionResponse(BaseModel):
    id: str
    role_id: str
    permission_id: str
    created_at: datetime
    created_by: str | None = None


class RolePermissionDetailResponse(BaseModel):
    role_permission: RolePermissionResponse
    role: RoleResponse
    permission: PermissionResponse


def role_permission_detail_response(result: RolePermissionResult) -> RolePermissionDetailResponse:
    rp = result.role_permission
    return RolePermissionDetailResponse(
        role_permission=RolePermissionResponse(
            id=str(rp.id), role_id=str(rp.role_id), permission_id=str(rp.permission_id),
            created_at=rp.created_at, created_by=uuid_str(rp.created_by)),
        role=role_response(result.role),
        permission=permission_response(result.permission),
    )


def role_permission_details_response(
        items: list[RolePermissionResult]) -> list[RolePermissionDetailResponse]:
    return [role_permission_detail_response(i) for i in items]


class LoginResponse(BaseModel):
    user: UserResponse
    role: RoleResponse
    permissions: list[PermissionResponse]
    access_token: str
    refresh_token: str


def login_response(result: LoginResult) -> LoginResponse:
    return LoginResponse(
        user=user_response(result.user), role=role_response(result.role),
        permissions=[permission_response(p) for p in result.permissions],
        access_token=result.access_token, refresh_token=result.refresh_token,
    )


class IdResponse(BaseModel):
    id: str


class ErrorResponse(BaseModel):
    error: str
    message: str


class PageResponse(BaseModel):
    page: int
    limit: int
    total_items: int


class PageDataResponse(BaseModel, Generic[T]):
    data: list[T]
    page: PageResponse
