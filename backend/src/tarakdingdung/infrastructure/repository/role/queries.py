from uuid import UUID

from sqlalchemy import Select, func, insert, select, update

from tarakdingdung.infrastructure.repository.database.orm import (
    PermissionORM, RoleORM, RolePermissionORM,
)
from tarakdingdung.infrastructure.repository.shared.query import (
    normalize_limit, normalize_offset, search_pattern,
)

R = RoleORM


def build_create(*, name, description, is_default, created_by):
    values: dict = {"name": name, "created_by": created_by}
    if description is not None:
        values["description"] = description
    if is_default is not None:
        values["is_default"] = is_default
    return insert(R).values(**values).returning(R.id)


def build_unset_defaults(updated_by, *, except_id: UUID | None = None):
    stmt = (update(R).where(R.is_default.is_(True), R.deleted_at.is_(None))
            .values(is_default=False, updated_at=func.now(), updated_by=updated_by))
    if except_id is not None:
        stmt = stmt.where(R.id != except_id)
    return stmt


def build_read_by_id(id: UUID) -> Select:
    return select(R).where(R.id == id, R.deleted_at.is_(None))


def build_read_by_name(name: str) -> Select:
    return select(R).where(R.name == name, R.deleted_at.is_(None)).limit(1)


def build_read_default() -> Select:
    return select(R).where(R.is_default.is_(True), R.deleted_at.is_(None)).limit(1)


def build_read_permissions(role_id: UUID) -> Select:
    return (select(PermissionORM)
            .join(RolePermissionORM, RolePermissionORM.permission_id == PermissionORM.id)
            .where(RolePermissionORM.role_id == role_id, PermissionORM.deleted_at.is_(None))
            .order_by(PermissionORM.created_at.desc(), PermissionORM.id.asc()))


def build_count(search: str | None):
    stmt = select(func.count()).select_from(R).where(R.deleted_at.is_(None))
    pattern = search_pattern(search)
    if pattern is not None:
        stmt = stmt.where(R.name.ilike(pattern))
    return stmt


def build_read_by_pagination(*, page, limit, search) -> Select:
    stmt = select(R).where(R.deleted_at.is_(None))
    pattern = search_pattern(search)
    if pattern is not None:
        stmt = stmt.where(R.name.ilike(pattern))
    return (stmt.order_by(R.created_at.desc(), R.id.asc())
                .limit(normalize_limit(limit)).offset(normalize_offset(page, limit)))


def build_update_by_id(id: UUID, *, name, description, is_default, preferences, updated_by):
    values: dict = {"updated_at": func.now(), "updated_by": updated_by}
    if name is not None:
        values["name"] = name
    if description is not None:
        values["description"] = description
    if is_default is not None:
        values["is_default"] = is_default
    if preferences is not None:
        values["preferences"] = preferences
    return update(R).where(R.id == id, R.deleted_at.is_(None)).values(**values)


def build_soft_delete(id: UUID, *, deleted_by):
    return (update(R).where(R.id == id, R.deleted_at.is_(None))
            .values(deleted_at=func.now(), deleted_by=deleted_by))
