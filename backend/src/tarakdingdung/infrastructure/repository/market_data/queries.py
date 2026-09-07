from collections.abc import Mapping

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from tarakdingdung.domain.models.market import Candle, OrderBook, Symbol, SymbolRules, TimeRange
from tarakdingdung.infrastructure.repository.database.orm import (
    CandleORM, OrderBookORM, PriceORM, SymbolRulesORM,
)
from tarakdingdung.infrastructure.repository.shared.trading import (
    levels_to_json, symbol_columns,
)

C = CandleORM
B = OrderBookORM
P = PriceORM
R = SymbolRulesORM


def _match(model, symbol: Symbol):
    return and_(model.venue == symbol.venue, model.base == symbol.base,
                model.quote == symbol.quote)


def _any_of(model, symbols: tuple[Symbol, ...]):
    return or_(*[_match(model, s) for s in symbols]) if symbols else False


def build_upsert_candles(*, symbol: Symbol, interval: str,
                         candles: tuple[Candle, ...]):
    """Idempotent on the natural key.

    Collection re-fetches overlapping windows every pass, so an ordinary insert
    would either duplicate history or fail the whole batch on one repeat. The
    later fetch wins: a venue revising a candle is a correction, not a conflict.
    """
    rows = [{**symbol_columns(symbol), "interval": interval,
             "open_time": c.open_time, "open": c.open, "high": c.high,
             "low": c.low, "close": c.close, "volume": c.volume}
            for c in candles]
    statement = pg_insert(C).values(rows)
    return statement.on_conflict_do_update(
        constraint="uq_candles_symbol_interval_open_time",
        set_={"open": statement.excluded.open, "high": statement.excluded.high,
              "low": statement.excluded.low, "close": statement.excluded.close,
              "volume": statement.excluded.volume})


def build_insert_book(book: OrderBook):
    """Upsert the single row for this symbol — only the latest book is read.

    The ``where`` keeps the newest: an out-of-order write (an older book
    arriving after a newer one) is dropped rather than regressing the row.
    """
    statement = pg_insert(B).values(
        **symbol_columns(book.symbol), captured_at=book.timestamp,
        bids=levels_to_json(book.bids), asks=levels_to_json(book.asks))
    return statement.on_conflict_do_update(
        constraint="uq_order_books_symbol",
        set_={"captured_at": statement.excluded.captured_at,
              "bids": statement.excluded.bids, "asks": statement.excluded.asks},
        where=B.captured_at <= statement.excluded.captured_at)


def build_insert_price(*, symbol: Symbol, timestamp: int, price):
    """Upsert the single row for this symbol — only the latest price is read.

    The ``where`` keeps the newest, so an out-of-order write cannot regress the
    stored price.
    """
    statement = pg_insert(P).values(
        **symbol_columns(symbol), captured_at=timestamp, price=price)
    return statement.on_conflict_do_update(
        constraint="uq_prices_symbol",
        set_={"captured_at": statement.excluded.captured_at,
              "price": statement.excluded.price},
        where=P.captured_at <= statement.excluded.captured_at)


def build_read_candles(*, symbol: Symbol, interval: str, window: TimeRange,
                       limit: int | None) -> Select:
    stmt = (select(C)
            .where(_match(C, symbol), C.interval == interval,
                   C.open_time >= window.start, C.open_time < window.end)
            .order_by(C.open_time.asc()))
    return stmt.limit(limit) if limit else stmt


def build_read_candles_before(*, symbol: Symbol, interval: str, as_of: int,
                              lookback: int, inclusive: bool = True) -> Select:
    # Descending then reversed by the caller: the newest N rows are what a
    # lookback window means, and ordering ascending would scan from the start.
    #
    # ``inclusive`` is the lookahead boundary. A live cycle wants the bar in
    # progress (its close so far is the latest price), so ``open_time <= as_of``.
    # A replay steps exactly on bar boundaries, where ``open_time == as_of`` is
    # a bar that has not closed yet, so it passes ``inclusive=False``.
    bound = C.open_time <= as_of if inclusive else C.open_time < as_of
    return (select(C)
            .where(_match(C, symbol), C.interval == interval, bound)
            .order_by(C.open_time.desc())
            .limit(lookback))


def build_read_book(*, symbol: Symbol, as_of: int) -> Select:
    return (select(B).where(_match(B, symbol), B.captured_at <= as_of)
            .order_by(B.captured_at.desc()).limit(1))


def build_read_prices(*, symbols: tuple[Symbol, ...], as_of: int,
                      max_age: int) -> Select:
    """Latest price per symbol within the freshness bound.

    ``DISTINCT ON`` keeps one row per symbol without a correlated subquery per
    symbol; the age filter is applied here rather than in Python so a stale row
    never leaves the database.
    """
    return (select(P)
            .where(_any_of(P, symbols), P.captured_at <= as_of,
                   P.captured_at >= as_of - max_age)
            .order_by(P.venue, P.base, P.quote, P.captured_at.desc())
            .distinct(P.venue, P.base, P.quote))


def build_count_candles(*, symbol: Symbol, interval: str, window: TimeRange):
    return (select(func.count()).select_from(C)
            .where(_match(C, symbol), C.interval == interval,
                   C.open_time >= window.start, C.open_time < window.end))


def build_read_open_times(*, symbol: Symbol, interval: str, window: TimeRange) -> Select:
    return (select(C.open_time)
            .where(_match(C, symbol), C.interval == interval,
                   C.open_time >= window.start, C.open_time < window.end)
            .order_by(C.open_time.asc()))


def build_upsert_rules(rules: Mapping[Symbol, SymbolRules]):
    rows = [{**symbol_columns(symbol), "tick_size": r.tick_size,
             "step_size": r.step_size, "min_notional": r.min_notional,
             "maker_fee": r.maker_fee, "taker_fee": r.taker_fee,
             "updated_at": func.now()}
            for symbol, r in rules.items()]
    statement = pg_insert(R).values(rows)
    return statement.on_conflict_do_update(
        constraint="uq_symbol_rules_symbol",
        set_={"tick_size": statement.excluded.tick_size,
              "step_size": statement.excluded.step_size,
              "min_notional": statement.excluded.min_notional,
              "maker_fee": statement.excluded.maker_fee,
              "taker_fee": statement.excluded.taker_fee,
              "updated_at": func.now()})


def build_read_rules(symbols: tuple[Symbol, ...]) -> Select:
    return select(R).where(_any_of(R, symbols))
