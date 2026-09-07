from collections.abc import Mapping
from decimal import Decimal

from tarakdingdung.domain.contracts.repository.market_data import MarketDataRepository
from tarakdingdung.domain.models.market import (
    Candle, Coverage, MarketSnapshot, OrderBook, Symbol, SymbolRules, TimeRange,
)
from tarakdingdung.infrastructure.repository.database.session import Database
from tarakdingdung.infrastructure.repository.market_data import queries as q
from tarakdingdung.infrastructure.repository.shared.trading import (
    book_from_orm, candle_from_orm, rules_from_orm, symbol_from_row,
)


class SqlAlchemyMarketDataRepository(MarketDataRepository):
    """Market history in Postgres.

    Read methods honour the ``MarketSnapshot`` obligation directly in SQL:
    every query is bounded by ``<= as_of``, so nothing stamped after the
    requested instant can reach a strategy even by accident.
    """

    def __init__(self, database: Database) -> None:
        self._db = database

    async def write_candles(self, *, symbol, interval, candles) -> int:
        if not candles:
            return 0
        async with self._db.session() as s:
            await s.execute(q.build_upsert_candles(
                symbol=symbol, interval=interval, candles=candles))
            await self._db.persist(s)
        return len(candles)

    async def write_book(self, book: OrderBook) -> None:
        async with self._db.session() as s:
            await s.execute(q.build_insert_book(book))
            await self._db.persist(s)

    async def write_price(self, *, symbol, timestamp, price) -> None:
        async with self._db.session() as s:
            await s.execute(q.build_insert_price(
                symbol=symbol, timestamp=timestamp, price=price))
            await self._db.persist(s)

    async def read_candles(self, *, symbol, interval, window, limit=None):
        async with self._db.session() as s:
            rows = (await s.execute(q.build_read_candles(
                symbol=symbol, interval=interval,
                window=window, limit=limit))).scalars().all()
        return tuple(candle_from_orm(r) for r in rows)

    async def read_book(self, *, symbol, as_of) -> OrderBook | None:
        async with self._db.session() as s:
            row = (await s.execute(q.build_read_book(
                symbol=symbol, as_of=as_of))).scalar_one_or_none()
        return book_from_orm(row) if row is not None else None

    async def read_prices(self, *, symbols, as_of, max_age) -> Mapping[Symbol, Decimal]:
        if not symbols:
            return {}
        async with self._db.session() as s:
            rows = (await s.execute(q.build_read_prices(
                symbols=symbols, as_of=as_of, max_age=max_age))).scalars().all()
        return {symbol_from_row(r): r.price for r in rows}

    async def read_snapshot(self, *, symbols, as_of, interval, lookback,
                            max_age) -> MarketSnapshot:
        prices = await self.read_prices(symbols=symbols, as_of=as_of, max_age=max_age)
        candles: dict[Symbol, tuple[Candle, ...]] = {}
        books: dict[Symbol, OrderBook] = {}
        # Only symbols with a fresh price take part: a candle history without a
        # current price cannot be sized against, and including it would let a
        # strategy rank a symbol it cannot trade.
        for symbol in prices:
            candles[symbol] = await self._lookback(symbol, interval, as_of, lookback)
            book = await self.read_book(symbol=symbol, as_of=as_of)
            if book is not None:
                books[symbol] = book
        return MarketSnapshot(timestamp=as_of, candles=candles, books=books,
                              last_prices=prices)

    async def read_coverage(self, *, symbol, interval, window) -> Coverage:
        async with self._db.session() as s:
            stamps = (await s.execute(q.build_read_open_times(
                symbol=symbol, interval=interval, window=window))).scalars().all()
        step = self._step(stamps, window)
        expected = max(1, window.duration // step) if step else 1
        return Coverage(symbol=symbol, interval=interval, window=window,
                        expected=expected, present=len(stamps),
                        gaps=self._gaps(list(stamps), step))

    async def write_rules(self, rules: Mapping[Symbol, SymbolRules]) -> None:
        if not rules:
            return
        async with self._db.session() as s:
            await s.execute(q.build_upsert_rules(rules))
            await self._db.persist(s)

    async def read_rules(self, *, symbols) -> Mapping[Symbol, SymbolRules]:
        if not symbols:
            return {}
        async with self._db.session() as s:
            rows = (await s.execute(q.build_read_rules(symbols))).scalars().all()
        return {symbol_from_row(r): rules_from_orm(r) for r in rows}

    async def _lookback(self, symbol, interval, as_of, lookback):
        async with self._db.session() as s:
            rows = (await s.execute(q.build_read_candles_before(
                symbol=symbol, interval=interval,
                as_of=as_of, lookback=lookback))).scalars().all()
        return tuple(candle_from_orm(r) for r in reversed(rows))

    @staticmethod
    def _step(stamps, window: TimeRange) -> int:
        """Infer the interval from the data rather than parsing its name.

        The stored candles are the authority on their own spacing, and a
        mismatch between a label and what was actually collected should not
        silently change what "complete" means.
        """
        if len(stamps) < 2:
            return window.duration
        return min(b - a for a, b in zip(stamps, stamps[1:]) if b > a)

    @staticmethod
    def _gaps(stamps: list[int], step: int) -> tuple[TimeRange, ...]:
        if step <= 0 or len(stamps) < 2:
            return ()
        found = []
        for earlier, later in zip(stamps, stamps[1:]):
            if later - earlier > step:
                found.append(TimeRange(start=earlier + step, end=later))
        return tuple(found)
