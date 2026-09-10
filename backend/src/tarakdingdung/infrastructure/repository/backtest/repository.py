import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from tarakdingdung.domain.contracts.repository.backtest import BacktestRepository
from tarakdingdung.domain.models.backtest import BacktestResult
from tarakdingdung.infrastructure.repository.database.orm import BacktestResultRow


def _curve_to_json(curve: list[Decimal]) -> list[str]:
    return [str(v) for v in curve]


def _curve_from_json(data: list[str]) -> list[Decimal]:
    return [Decimal(v) for v in data]


def _to_domain(row: BacktestResultRow) -> BacktestResult:
    return BacktestResult(
        id=row.id,
        universe_id=row.universe_id,
        from_ms=row.from_ms,
        to_ms=row.to_ms,
        equity_curve=_curve_from_json(row.equity_curve),
        sharpe=row.sharpe,
        max_drawdown=row.max_drawdown,
        turnover=row.turnover,
    )


class SqlAlchemyBacktestRepository(BacktestRepository):
    def __init__(self, sessions: async_sessionmaker) -> None:
        self._sessions = sessions

    async def create(self, entity: BacktestResult) -> BacktestResult:
        id_ = entity.id or str(uuid.uuid4())
        async with self._sessions() as session:
            session.add(
                BacktestResultRow(
                    id=id_,
                    universe_id=entity.universe_id,
                    from_ms=entity.from_ms,
                    to_ms=entity.to_ms,
                    equity_curve=_curve_to_json(entity.equity_curve),
                    sharpe=entity.sharpe,
                    max_drawdown=entity.max_drawdown,
                    turnover=entity.turnover,
                )
            )
            await session.commit()
        return BacktestResult(
            id=id_, universe_id=entity.universe_id, from_ms=entity.from_ms,
            to_ms=entity.to_ms, equity_curve=entity.equity_curve,
            sharpe=entity.sharpe, max_drawdown=entity.max_drawdown,
            turnover=entity.turnover,
        )

    async def read_by_id(self, id: str) -> BacktestResult | None:
        async with self._sessions() as session:
            row = await session.get(BacktestResultRow, id)
            return _to_domain(row) if row else None

    async def read_by_pagination(
        self, page: int, per_page: int
    ) -> tuple[list[BacktestResult], int]:
        async with self._sessions() as session:
            base = select(BacktestResultRow)
            total = (
                await session.execute(select(func.count()).select_from(base.subquery()))
            ).scalar_one()
            stmt = base.order_by(BacktestResultRow.to_ms.desc()).offset(
                (page - 1) * per_page
            ).limit(per_page)
            rows = (await session.execute(stmt)).scalars().all()
            return [_to_domain(r) for r in rows], total
