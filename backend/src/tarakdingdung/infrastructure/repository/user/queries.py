from uuid import UUID

from sqlalchemy import Select, func, insert, or_, select, update

from tarakdingdung.infrastructure.repository.database.orm import (
    PermissionORM, RoleORM, RolePermissionORM, UserORM,
)
from tarakdingdung.infrastructure.repository.shared.query import (
    normalize_limit, normalize_offset, search_pattern,
)

U, R, RP, P = UserORM, RoleORM, RolePermissionORM, PermissionORM


def build_create(*, role_id, name, bio, username, password_hash, created_by):
    values: dict = {"role_id": role_id, "name": name, "username": username,
                    "password_hash": password_hash, "created_by": created_by}
    if bio is not None:
        values["bio"] = bio
    return insert(U).values(**values).returning(U.id)


def build_read_by_id(id: UUID) -> Select:
    return select(U).where(U.id == id, U.deleted_at.is_(None))


def build_read_by_username(username: str) -> Select:
    return select(U).where(U.username == username, U.deleted_at.is_(None)).limit(1)


def build_read_permissions(user_id: UUID) -> Select:
    return (select(P).select_from(U)
            .join(R, R.id == U.role_id)
            .join(RP, RP.role_id == R.id)
            .join(P, P.id == RP.permission_id)
            .where(U.id == user_id, U.deleted_at.is_(None),
                   R.deleted_at.is_(None), P.deleted_at.is_(None))
            .order_by(P.created_at.desc(), P.id.asc()))


def build_count(search: str | None, role_id: UUID | None):
    stmt = select(func.count()).select_from(U).where(U.deleted_at.is_(None))
    pattern = search_pattern(search)
    if pattern is not None:
        stmt = stmt.where(or_(
            U.name.ilike(pattern, escape="\\"),
            U.username.ilike(pattern, escape="\\"),
        ))
    if role_id is not None:
        stmt = stmt.where(U.role_id == role_id)
    return stmt


def build_read_by_pagination(*, page, limit, search, role_id) -> Select:
    stmt = (select(U, R.name.label("role_name"))
            .outerjoin(R, R.id == U.role_id)
            .where(U.deleted_at.is_(None)))
    pattern = search_pattern(search)
    if pattern is not None:
        stmt = stmt.where(or_(
            U.name.ilike(pattern, escape="\\"),
            U.username.ilike(pattern, escape="\\"),
        ))
    if role_id is not None:
        stmt = stmt.where(U.role_id == role_id)
    return (stmt.order_by(U.created_at.desc(), U.id.asc())
                .limit(normalize_limit(limit)).offset(normalize_offset(page, limit)))


def build_update_by_id(id: UUID, *, role_id, name, bio, username,
                       password_hash, preferences, updated_by):
    values: dict = {"updated_at": func.now(), "updated_by": updated_by}
    for key, val in (("role_id", role_id), ("name", name), ("bio", bio),
                     ("username", username), ("password_hash", password_hash),
                     ("preferences", preferences)):
        if val is not None:
            values[key] = val
    return update(U).where(U.id == id, U.deleted_at.is_(None)).values(**values)


def build_soft_delete(id: UUID, *, deleted_by):
    return (update(U).where(U.id == id, U.deleted_at.is_(None))
            .values(deleted_at=func.now(), deleted_by=deleted_by))
