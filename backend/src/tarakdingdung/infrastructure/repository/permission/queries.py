from uuid import UUID

from sqlalchemy import Select, func, insert, select, update

from tarakdingdung.infrastructure.repository.database.orm import PermissionORM
from tarakdingdung.infrastructure.repository.shared.query import (
    normalize_limit, normalize_offset, search_pattern,
)

P = PermissionORM


def build_create(*, name: str, description: str | None, created_by: UUID | None):
    values: dict = {"name": name, "created_by": created_by}
    if description is not None:
        values["description"] = description
    return insert(P).values(**values).returning(P.id)


def build_read_by_id(id: UUID) -> Select:
    return select(P).where(P.id == id, P.deleted_at.is_(None))


def build_read_by_name(name: str) -> Select:
    return select(P).where(P.name == name, P.deleted_at.is_(None)).limit(1)


def build_count(search: str | None):
    stmt = select(func.count()).select_from(P).where(P.deleted_at.is_(None))
    pattern = search_pattern(search)
    if pattern is not None:
        stmt = stmt.where(P.name.ilike(pattern, escape="\\"))
    return stmt


def build_read_by_pagination(*, page: int, limit: int, search: str | None) -> Select:
    stmt = select(P).where(P.deleted_at.is_(None))
    pattern = search_pattern(search)
    if pattern is not None:
        stmt = stmt.where(P.name.ilike(pattern, escape="\\"))
    return (stmt.order_by(P.created_at.desc(), P.id.asc())
                .limit(normalize_limit(limit))
                .offset(normalize_offset(page, limit)))


def build_update_by_id(id: UUID, *, name, description, preferences, updated_by):
    values: dict = {"updated_at": func.now(), "updated_by": updated_by}
    if name is not None:
        values["name"] = name
    if description is not None:
        values["description"] = description
    if preferences is not None:
        values["preferences"] = preferences
    return update(P).where(P.id == id, P.deleted_at.is_(None)).values(**values)


def build_soft_delete(id: UUID, *, deleted_by: UUID | None):
    return (update(P).where(P.id == id, P.deleted_at.is_(None))
            .values(deleted_at=func.now(), deleted_by=deleted_by))
