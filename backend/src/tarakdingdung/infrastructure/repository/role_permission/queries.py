from uuid import UUID

from sqlalchemy import Select, delete, func, insert, select

from tarakdingdung.infrastructure.repository.database.orm import (
    PermissionORM, RoleORM, RolePermissionORM,
)
from tarakdingdung.infrastructure.repository.shared.query import (
    normalize_limit, normalize_offset,
)

RP, R, P = RolePermissionORM, RoleORM, PermissionORM


def build_create(*, role_id: UUID, permission_id: UUID, created_by: UUID | None):
    return (insert(RP)
            .values(role_id=role_id, permission_id=permission_id, created_by=created_by)
            .returning(RP.id))


def _base_join() -> Select:
    return (select(RP, R, P)
            .join(R, RP.role_id == R.id)
            .join(P, RP.permission_id == P.id)
            .where(R.deleted_at.is_(None), P.deleted_at.is_(None)))


def build_read_by_id(id: UUID) -> Select:
    return _base_join().where(RP.id == id)


def build_read_by_pair(role_id: UUID, permission_id: UUID) -> Select:
    return _base_join().where(RP.role_id == role_id, RP.permission_id == permission_id).limit(1)


def build_count(role_id: UUID | None, permission_id: UUID | None):
    stmt = (select(func.count()).select_from(RP)
            .join(R, RP.role_id == R.id).join(P, RP.permission_id == P.id)
            .where(R.deleted_at.is_(None), P.deleted_at.is_(None)))
    if role_id is not None:
        stmt = stmt.where(RP.role_id == role_id)
    if permission_id is not None:
        stmt = stmt.where(RP.permission_id == permission_id)
    return stmt


def build_read_by_pagination(*, page, limit, role_id, permission_id) -> Select:
    stmt = _base_join()
    if role_id is not None:
        stmt = stmt.where(RP.role_id == role_id)
    if permission_id is not None:
        stmt = stmt.where(RP.permission_id == permission_id)
    return (stmt.order_by(RP.created_at.desc(), RP.id.asc())
                .limit(normalize_limit(limit)).offset(normalize_offset(page, limit)))


def build_delete_by_id(id: UUID):
    return delete(RP).where(RP.id == id)


def build_delete_by_pair(role_id: UUID | None, permission_id: UUID | None):
    stmt = delete(RP)
    if role_id is not None:
        stmt = stmt.where(RP.role_id == role_id)
    if permission_id is not None:
        stmt = stmt.where(RP.permission_id == permission_id)
    return stmt
