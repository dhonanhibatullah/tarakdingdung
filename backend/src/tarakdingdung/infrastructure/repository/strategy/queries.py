from uuid import UUID

from sqlalchemy import Select, func, insert, select, update

from tarakdingdung.domain.models.market import Symbol
from tarakdingdung.domain.models.strategy import TradingMode
from tarakdingdung.infrastructure.repository.database.orm import StrategyORM
from tarakdingdung.infrastructure.repository.shared.query import (
    normalize_limit, normalize_offset, search_pattern,
)
from tarakdingdung.infrastructure.repository.shared.trading import universe_to_json

S = StrategyORM


def build_create(*, name: str, description: str | None, kind: str,
                 mode: TradingMode, universe: tuple[Symbol, ...],
                 parameters: dict | None, is_enabled: bool | None,
                 created_by: UUID | None):
    values: dict = {"name": name, "kind": kind, "mode": str(mode),
                    "universe": universe_to_json(universe), "created_by": created_by}
    if description is not None:
        values["description"] = description
    if parameters is not None:
        values["parameters"] = parameters
    if is_enabled is not None:
        values["is_enabled"] = is_enabled
    return insert(S).values(**values).returning(S.id)


def build_read_by_id(id: UUID) -> Select:
    return select(S).where(S.id == id, S.deleted_at.is_(None))


def build_read_by_name(name: str) -> Select:
    return select(S).where(S.name == name, S.deleted_at.is_(None)).limit(1)


def build_read_enabled() -> Select:
    return (select(S).where(S.is_enabled.is_(True), S.deleted_at.is_(None))
            .order_by(S.name.asc()))


def _filtered(stmt, search: str | None, mode: TradingMode | None):
    pattern = search_pattern(search)
    if pattern is not None:
        stmt = stmt.where(S.name.ilike(pattern, escape="\\"))
    if mode is not None:
        stmt = stmt.where(S.mode == str(mode))
    return stmt


def build_count(search: str | None, mode: TradingMode | None):
    return _filtered(
        select(func.count()).select_from(S).where(S.deleted_at.is_(None)), search, mode)


def build_read_by_pagination(*, page: int, limit: int, search: str | None,
                             mode: TradingMode | None) -> Select:
    stmt = _filtered(select(S).where(S.deleted_at.is_(None)), search, mode)
    return (stmt.order_by(S.created_at.desc(), S.id.asc())
                .limit(normalize_limit(limit))
                .offset(normalize_offset(page, limit)))


def build_update_by_id(id: UUID, *, name, description, kind, mode, universe,
                       parameters, is_enabled, preferences, updated_by):
    values: dict = {"updated_at": func.now(), "updated_by": updated_by}
    for column, value in (("name", name), ("description", description),
                          ("kind", kind), ("parameters", parameters),
                          ("preferences", preferences)):
        if value is not None:
            values[column] = value
    if mode is not None:
        values["mode"] = str(mode)
    if universe is not None:
        values["universe"] = universe_to_json(universe)
    if is_enabled is not None:
        values["is_enabled"] = is_enabled
    return update(S).where(S.id == id, S.deleted_at.is_(None)).values(**values)


def build_soft_delete(id: UUID, *, deleted_by: UUID | None):
    return (update(S).where(S.id == id, S.deleted_at.is_(None))
            .values(deleted_at=func.now(), deleted_by=deleted_by))
