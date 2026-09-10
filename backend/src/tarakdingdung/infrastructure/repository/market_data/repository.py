import uuid

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import async_sessionmaker

from tarakdingdung.domain.contracts.repository.market_data import MarketDataRepository
from tarakdingdung.domain.models.market import Candle
from tarakdingdung.infrastructure.repository.database.orm import CandleRow


def _to_domain(row: CandleRow) -> Candle:
    return Candle(
        symbol_id=row.symbol_id,
        open_time_ms=row.open_time_ms,
        open=row.open,
        high=row.high,
        low=row.low,
        close=row.close,
        volume=row.volume,
    )


class SqlAlchemyMarketDataRepository(MarketDataRepository):
    def __init__(self, sessions: async_sessionmaker) -> None:
        self._sessions = sessions

    async def append_candles(self, candles: list[Candle]) -> None:
        if not candles:
            return
        rows = [
            {
                "id": str(uuid.uuid4()),
                "symbol_id": c.symbol_id,
                "open_time_ms": c.open_time_ms,
                "open": c.open,
                "high": c.high,
                "low": c.low,
                "close": c.close,
                "volume": c.volume,
            }
            for c in candles
        ]
        async with self._sessions() as session:
            stmt = pg_insert(CandleRow).values(rows).on_conflict_do_nothing(
                index_elements=["symbol_id", "open_time_ms"]
            )
            await session.execute(stmt)
            await session.commit()

    async def read_range(
        self, symbol_id: str, from_ms: int, to_ms: int
    ) -> list[Candle]:
        async with self._sessions() as session:
            stmt = (
                select(CandleRow)
                .where(
                    CandleRow.symbol_id == symbol_id,
                    CandleRow.open_time_ms >= from_ms,
                    CandleRow.open_time_ms <= to_ms,
                )
                .order_by(CandleRow.open_time_ms)
            )
            rows = (await session.execute(stmt)).scalars().all()
            return [_to_domain(r) for r in rows]

    async def read_latest(self, symbol_id: str) -> Candle | None:
        async with self._sessions() as session:
            stmt = (
                select(CandleRow)
                .where(CandleRow.symbol_id == symbol_id)
                .order_by(CandleRow.open_time_ms.desc())
                .limit(1)
            )
            row = (await session.execute(stmt)).scalar_one_or_none()
            return _to_domain(row) if row else None

    async def read_coverage(self, symbol_id: str) -> tuple[int, int] | None:
        async with self._sessions() as session:
            stmt = select(
                func.min(CandleRow.open_time_ms), func.max(CandleRow.open_time_ms)
            ).where(CandleRow.symbol_id == symbol_id)
            lo, hi = (await session.execute(stmt)).one()
            if lo is None or hi is None:
                return None
            return int(lo), int(hi)
