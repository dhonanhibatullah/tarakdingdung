from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from tarakdingdung.domain.contracts.repository.backtest import BacktestRepository
from tarakdingdung.domain.models.backtest import BacktestRun, ValidationRun
from tarakdingdung.domain.models.market import TimeRange
from tarakdingdung.infrastructure.repository.backtest import queries as q
from tarakdingdung.infrastructure.repository.database.session import Database
from tarakdingdung.infrastructure.repository.shared.errors import map_db_error
from tarakdingdung.infrastructure.repository.shared.results import require
from tarakdingdung.infrastructure.repository.shared.trading import (
    overfitting_from_json, report_from_json, trials_from_json,
)


def _run(row) -> BacktestRun:
    return BacktestRun(
        id=row.id, strategy_id=row.strategy_id,
        window=TimeRange(start=row.window_start, end=row.window_end),
        initial_equity=row.initial_equity, report=report_from_json(row.report),
        created_at=row.created_at, created_by=row.created_by)


def _validation(row) -> ValidationRun:
    return ValidationRun(
        id=row.id, strategy_id=row.strategy_id,
        window=TimeRange(start=row.window_start, end=row.window_end),
        trials=trials_from_json(row.trials),
        overfitting=overfitting_from_json(row.overfitting),
        created_at=row.created_at, created_by=row.created_by)


class SqlAlchemyBacktestRepository(BacktestRepository):
    def __init__(self, database: Database) -> None:
        self._db = database

    async def create_run(self, *, strategy_id, window, initial_equity, report,
                         created_by) -> UUID:
        try:
            async with self._db.session() as s:
                new_id = await s.scalar(q.build_create_run(
                    strategy_id=strategy_id, window=window,
                    initial_equity=initial_equity, report=report,
                    created_by=created_by))
                await self._db.persist(s)
                return require(new_id, "failed to record backtest run")
        except SQLAlchemyError as exc:
            raise map_db_error("failed to record backtest run", exc) from exc

    async def read_run_by_id(self, id: UUID) -> BacktestRun | None:
        async with self._db.session() as s:
            row = (await s.execute(q.build_read_run_by_id(id))).scalar_one_or_none()
        return _run(row) if row is not None else None

    async def read_runs_by_pagination(self, *, page, limit, strategy_id):
        async with self._db.session() as s:
            total = await s.scalar(q.build_count_runs(strategy_id))
            if not total:
                return [], 0
            rows = (await s.execute(q.build_read_runs_by_pagination(
                page=page, limit=limit, strategy_id=strategy_id))).scalars().all()
        return [_run(r) for r in rows], int(total)

    async def create_validation(self, *, strategy_id, window, trials, overfitting,
                                created_by) -> UUID:
        try:
            async with self._db.session() as s:
                new_id = await s.scalar(q.build_create_validation(
                    strategy_id=strategy_id, window=window, trials=trials,
                    overfitting=overfitting, created_by=created_by))
                await self._db.persist(s)
                return require(new_id, "failed to record validation run")
        except SQLAlchemyError as exc:
            raise map_db_error("failed to record validation run", exc) from exc

    async def read_validation_by_id(self, id: UUID) -> ValidationRun | None:
        async with self._db.session() as s:
            row = (await s.execute(
                q.build_read_validation_by_id(id))).scalar_one_or_none()
        return _validation(row) if row is not None else None

    async def read_validations_by_pagination(self, *, page, limit, strategy_id):
        async with self._db.session() as s:
            total = await s.scalar(q.build_count_validations(strategy_id))
            if not total:
                return [], 0
            rows = (await s.execute(q.build_read_validations_by_pagination(
                page=page, limit=limit, strategy_id=strategy_id))).scalars().all()
        return [_validation(r) for r in rows], int(total)
