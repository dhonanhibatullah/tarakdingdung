from tarakdingdung.domain.models.permission import Permission
from tarakdingdung.domain.models.role import Role
from tarakdingdung.domain.models.role_permission import RolePermission
from tarakdingdung.domain.models.user import User, UserListItem
from tarakdingdung.infrastructure.repository.database.orm import (
    PermissionORM, RoleORM, RolePermissionORM, UserORM,
)


def permission_from_orm(row: PermissionORM) -> Permission:
    return Permission(
        id=row.id, name=row.name, description=row.description,
        preferences=dict(row.preferences or {}), created_at=row.created_at,
        updated_at=row.updated_at, deleted_at=row.deleted_at,
        created_by=row.created_by, updated_by=row.updated_by, deleted_by=row.deleted_by,
    )


def role_from_orm(row: RoleORM) -> Role:
    return Role(
        id=row.id, name=row.name, description=row.description, is_default=row.is_default,
        preferences=dict(row.preferences or {}), created_at=row.created_at,
        updated_at=row.updated_at, deleted_at=row.deleted_at,
        created_by=row.created_by, updated_by=row.updated_by, deleted_by=row.deleted_by,
    )


def role_permission_from_orm(row: RolePermissionORM) -> RolePermission:
    return RolePermission(
        id=row.id, role_id=row.role_id, permission_id=row.permission_id,
        created_at=row.created_at, created_by=row.created_by,
    )


def user_from_orm(row: UserORM) -> User:
    return User(
        id=row.id, role_id=row.role_id, name=row.name, bio=row.bio, username=row.username,
        password_hash=row.password_hash, preferences=dict(row.preferences or {}),
        created_at=row.created_at, updated_at=row.updated_at, deleted_at=row.deleted_at,
        created_by=row.created_by, updated_by=row.updated_by, deleted_by=row.deleted_by,
    )


def user_list_item_from_orm(row: UserORM, role_name: str | None) -> UserListItem:
    return UserListItem(user=user_from_orm(row), role_name=role_name or "")
