import math
from decimal import Decimal
from uuid import UUID

from tarakdingdung.domain.contracts.repository.portfolio import PortfolioRepository
from tarakdingdung.domain.models.market import TimeRange
from tarakdingdung.domain.models.performance import EquityPoint, Fill
from tarakdingdung.domain.models.portfolio import Portfolio, RiskState
from tarakdingdung.infrastructure.repository.database.session import Database
from tarakdingdung.infrastructure.repository.portfolio import queries as q
from tarakdingdung.infrastructure.repository.shared.trading import (
    equity_point_from_orm, fill_from_orm, portfolio_from_orm,
)

_DAY_MS = 86_400_000
_VOLATILITY_WINDOW = 30


class SqlAlchemyPortfolioRepository(PortfolioRepository):
    def __init__(self, database: Database) -> None:
        self._db = database

    async def write_snapshot(self, portfolio: Portfolio) -> None:
        async with self._db.session() as s:
            await s.execute(q.build_insert_snapshot(portfolio))
            await self._db.persist(s)

    async def read_latest(self, *, as_of: int) -> Portfolio | None:
        async with self._db.session() as s:
            row = (await s.execute(q.build_read_latest(as_of))).scalar_one_or_none()
        return portfolio_from_orm(row) if row is not None else None

    async def read_risk_state(self, *, as_of: int) -> RiskState:
        """Derived from the equity curve, never stored separately.

        Peak equity, daily P&L and trailing volatility are functions of the
        curve the reports are drawn from. Storing them alongside would let the
        risk overlay and the performance report disagree about the same run.
        """
        async with self._db.session() as s:
            peak = await s.scalar(q.build_read_equity_peak(as_of))
            recent = (await s.execute(q.build_read_equity_before(
                as_of, since=as_of - _DAY_MS))).scalars().all()
        equities = [float(row.equity) for row in recent]
        current = Decimal(str(equities[-1])) if equities else Decimal(0)
        opening = Decimal(str(equities[0])) if equities else Decimal(0)
        return RiskState(timestamp=as_of,
                         equity_peak=peak if peak is not None else current,
                         daily_pnl=current - opening,
                         realized_volatility=_volatility(equities),
                         halted=False)

    async def write_equity_point(self, point: EquityPoint) -> None:
        async with self._db.session() as s:
            await s.execute(q.build_insert_equity_point(point))
            await self._db.persist(s)

    async def read_equity_curve(self, *, window: TimeRange) -> tuple[EquityPoint, ...]:
        async with self._db.session() as s:
            rows = (await s.execute(
                q.build_read_equity_curve(window))).scalars().all()
        return tuple(equity_point_from_orm(r) for r in rows)

    async def append_fills(self, fills: tuple[Fill, ...]) -> None:
        if not fills:
            return
        async with self._db.session() as s:
            await s.execute(q.build_insert_fills(fills))
            await self._db.persist(s)

    async def read_fills(self, *, window: TimeRange) -> tuple[Fill, ...]:
        async with self._db.session() as s:
            rows = (await s.execute(q.build_read_fills(window))).scalars().all()
        return tuple(fill_from_orm(r) for r in rows)

    async def set_halt(self, *, strategy_id: UUID, halted: bool,
                       reason: str | None) -> None:
        async with self._db.session() as s:
            await s.execute(q.build_set_halt(
                strategy_id=strategy_id, halted=halted, reason=reason))
            await self._db.persist(s)

    async def read_halt(self, *, strategy_id: UUID) -> tuple[bool, str | None]:
        async with self._db.session() as s:
            row = (await s.execute(
                q.build_read_halt(strategy_id))).scalar_one_or_none()
        return (row.halted, row.reason) if row is not None else (False, None)


def _volatility(equities: list[float]) -> float:
    sample = [b / a - 1.0 for a, b in zip(equities, equities[1:]) if a > 0]
    sample = sample[-_VOLATILITY_WINDOW:]
    if len(sample) < 2:
        return 0.0
    mean = sum(sample) / len(sample)
    return math.sqrt(sum((value - mean) ** 2 for value in sample) / len(sample))
