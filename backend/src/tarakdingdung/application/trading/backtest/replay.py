"""Turning a candle bar into the book a replay needs.

A REST poller cannot store a dense historical order-book series, so a backtest
cannot read one. The bar itself is the only per-interval information there is,
so the replay synthesises a book from it: a ladder of levels stepped out from
the close, holding a slice of the bar's traded volume each. That keeps the cost
model honest — a small order pays the spread, a larger one walks the ladder and
accrues impact, and an order bigger than the bar ever traded is rejected rather
than filled at an invented price.
"""

from decimal import Decimal

from tarakdingdung.domain.models.market import (
    BookLevel, Candle, MarketSnapshot, OrderBook, Symbol,
)

DEFAULT_HALF_SPREAD = Decimal("0.0005")
DEFAULT_LEVELS = 5
DEFAULT_LEVEL_STEP = Decimal("0.0005")


def synthetic_book(candle: Candle, symbol: Symbol, *,
                   half_spread: Decimal = DEFAULT_HALF_SPREAD,
                   levels: int = DEFAULT_LEVELS,
                   level_step: Decimal = DEFAULT_LEVEL_STEP) -> OrderBook:
    """A ``levels``-deep ladder each side of ``candle.close``.

    Level ``i`` (0-based) sits ``half_spread + i * level_step`` away from the
    close and holds ``candle.volume / levels`` of size. A bar that reports no
    volume produces zero-size levels, so every order against it is rejected —
    visibly, in the rejected count, rather than silently filled.
    """
    rungs = max(1, levels)
    close = candle.close
    per_level = candle.volume / rungs if candle.volume > 0 else Decimal(0)

    asks: list[BookLevel] = []
    bids: list[BookLevel] = []
    for i in range(rungs):
        offset = half_spread + level_step * i
        asks.append(BookLevel(price=close * (Decimal(1) + offset), quantity=per_level))
        bids.append(BookLevel(price=close * (Decimal(1) - offset), quantity=per_level))
    return OrderBook(symbol=symbol, timestamp=candle.open_time,
                     bids=tuple(bids), asks=tuple(asks))


def replay_snapshot(base: MarketSnapshot, *,
                    half_spread: Decimal = DEFAULT_HALF_SPREAD,
                    levels: int = DEFAULT_LEVELS,
                    level_step: Decimal = DEFAULT_LEVEL_STEP) -> MarketSnapshot:
    """``base`` with a synthetic book for any symbol that lacks one.

    ``base`` comes from ``MarketDataRepository.read_replay_snapshot`` — candles
    and last prices from the closed-candle series, ``books`` empty. This fills
    that gap so ``simulate`` has a book to price fills against; a symbol that
    already carries a book (a caller that supplied real depth) keeps it.
    """
    books: dict[Symbol, OrderBook] = dict(base.books)
    for symbol, series in base.candles.items():
        if symbol in books or not series:
            continue
        books[symbol] = synthetic_book(
            series[-1], symbol, half_spread=half_spread,
            levels=levels, level_step=level_step)
    return MarketSnapshot(timestamp=base.timestamp, candles=base.candles,
                          books=books, last_prices=base.last_prices)
