from decimal import Decimal
from uuid import UUID

from sqlalchemy import Select, func, insert, select

from tarakdingdung.domain.models.market import TimeRange
from tarakdingdung.domain.models.performance import (
    OverfittingReport, PerformanceReport, TrialResult,
)
from tarakdingdung.infrastructure.repository.database.orm import (
    BacktestRunORM, ValidationRunORM,
)
from tarakdingdung.infrastructure.repository.shared.query import (
    normalize_limit, normalize_offset,
)
from tarakdingdung.infrastructure.repository.shared.trading import (
    overfitting_to_json, report_to_json, trials_to_json,
)

B = BacktestRunORM
V = ValidationRunORM


def build_create_run(*, strategy_id: UUID, window: TimeRange,
                     initial_equity: Decimal, report: PerformanceReport,
                     created_by: UUID | None):
    return insert(B).values(
        strategy_id=strategy_id, window_start=window.start, window_end=window.end,
        initial_equity=initial_equity, report=report_to_json(report),
        created_by=created_by).returning(B.id)


def build_read_run_by_id(id: UUID) -> Select:
    return select(B).where(B.id == id)


def build_count_runs(strategy_id: UUID | None):
    stmt = select(func.count()).select_from(B)
    return stmt.where(B.strategy_id == strategy_id) if strategy_id else stmt


def build_read_runs_by_pagination(*, page: int, limit: int,
                                  strategy_id: UUID | None) -> Select:
    stmt = select(B)
    if strategy_id is not None:
        stmt = stmt.where(B.strategy_id == strategy_id)
    return (stmt.order_by(B.created_at.desc(), B.id.asc())
                .limit(normalize_limit(limit))
                .offset(normalize_offset(page, limit)))


def build_create_validation(*, strategy_id: UUID, window: TimeRange,
                            trials: tuple[TrialResult, ...],
                            overfitting: OverfittingReport,
                            created_by: UUID | None):
    return insert(V).values(
        strategy_id=strategy_id, window_start=window.start, window_end=window.end,
        trials=trials_to_json(trials), overfitting=overfitting_to_json(overfitting),
        created_by=created_by).returning(V.id)


def build_read_validation_by_id(id: UUID) -> Select:
    return select(V).where(V.id == id)


def build_count_validations(strategy_id: UUID | None):
    stmt = select(func.count()).select_from(V)
    return stmt.where(V.strategy_id == strategy_id) if strategy_id else stmt


def build_read_validations_by_pagination(*, page: int, limit: int,
                                         strategy_id: UUID | None) -> Select:
    stmt = select(V)
    if strategy_id is not None:
        stmt = stmt.where(V.strategy_id == strategy_id)
    return (stmt.order_by(V.created_at.desc(), V.id.asc())
                .limit(normalize_limit(limit))
                .offset(normalize_offset(page, limit)))
