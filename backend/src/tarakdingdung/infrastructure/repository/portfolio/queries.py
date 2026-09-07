from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from tarakdingdung.domain.models.market import TimeRange
from tarakdingdung.domain.models.performance import EquityPoint, Fill
from tarakdingdung.domain.models.portfolio import Portfolio
from tarakdingdung.infrastructure.repository.database.orm import (
    EquityPointORM, FillORM, PortfolioSnapshotORM, StrategyHaltORM,
)
from tarakdingdung.infrastructure.repository.shared.trading import (
    balances_to_json, cash_to_json, positions_to_json, symbol_columns,
)

S = PortfolioSnapshotORM
E = EquityPointORM
F = FillORM
H = StrategyHaltORM


def build_insert_snapshot(portfolio: Portfolio):
    return pg_insert(S).values(
        captured_at=portfolio.timestamp, cash=cash_to_json(portfolio.cash),
        positions=positions_to_json(portfolio.positions), equity=portfolio.equity,
        balances=balances_to_json(portfolio.balances))


def build_read_latest(as_of: int) -> Select:
    return (select(S).where(S.captured_at <= as_of)
            .order_by(S.captured_at.desc()).limit(1))


def build_insert_equity_point(point: EquityPoint):
    return pg_insert(E).values(captured_at=point.timestamp, equity=point.equity)


def build_read_equity_curve(window: TimeRange) -> Select:
    return (select(E)
            .where(E.captured_at >= window.start, E.captured_at < window.end)
            .order_by(E.captured_at.asc()))


def build_read_equity_before(as_of: int, *, since: int) -> Select:
    return (select(E).where(E.captured_at <= as_of, E.captured_at >= since)
            .order_by(E.captured_at.asc()))


def build_read_equity_peak(as_of: int):
    return select(func.max(E.equity)).where(E.captured_at <= as_of)


def build_insert_fills(fills: tuple[Fill, ...]):
    return pg_insert(F).values([
        {**symbol_columns(f.symbol), "side": str(f.side), "quantity": f.quantity,
         "price": f.price, "fee": f.fee, "filled_at": f.timestamp} for f in fills])


def build_read_fills(window: TimeRange) -> Select:
    return (select(F)
            .where(F.filled_at >= window.start, F.filled_at < window.end)
            .order_by(F.filled_at.asc()))


def build_set_halt(*, strategy_id: UUID, halted: bool, reason: str | None):
    statement = pg_insert(H).values(strategy_id=strategy_id, halted=halted,
                                    reason=reason, updated_at=func.now())
    return statement.on_conflict_do_update(
        index_elements=[H.strategy_id],
        set_={"halted": statement.excluded.halted,
              "reason": statement.excluded.reason, "updated_at": func.now()})


def build_read_halt(strategy_id: UUID) -> Select:
    return select(H).where(H.strategy_id == strategy_id)
