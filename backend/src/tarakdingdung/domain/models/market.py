from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class Venue(StrEnum):
    INDODAX = "INDODAX"
    TOKOCRYPTO = "TOKOCRYPTO"


@dataclass(frozen=True, slots=True)
class Symbol:
    """A tradable pair on one venue.

    The venue is part of the identity: the same pair on two exchanges carries
    two prices, which is precisely what a cross-exchange strategy trades. Wire
    formats (``BTC_USDT`` on Indodax, ``BTCUSDT`` on Tokocrypto) stay an
    infrastructure translation concern.
    """

    venue: Venue
    base: str
    quote: str


@dataclass(frozen=True, slots=True)
class Candle:
    open_time: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


@dataclass(frozen=True, slots=True)
class BookLevel:
    price: Decimal
    quantity: Decimal


@dataclass(frozen=True, slots=True)
class OrderBook:
    symbol: Symbol
    timestamp: int
    bids: tuple[BookLevel, ...]
    asks: tuple[BookLevel, ...]


@dataclass(frozen=True, slots=True)
class SymbolRules:
    """Venue constraints and economics for one pair.

    Fees sit alongside the rounding rules so the cost model and the order
    planner read venue economics from one place rather than from a config
    constant that drifts away from reality.
    """

    symbol: Symbol
    tick_size: Decimal
    step_size: Decimal
    min_notional: Decimal
    maker_fee: Decimal
    taker_fee: Decimal


@dataclass(frozen=True, slots=True)
class MarketSnapshot:
    """Everything known at ``timestamp`` — and nothing else.

    This is the lookahead-bias boundary. Whoever builds a snapshot — the
    collector, the backtester — owes two guarantees that the algorithm blocks
    rely on and cannot check cheaply:

    - every datum held has a timestamp at or before ``timestamp``, and
      ``candles`` holds closed candles only, ordered oldest to newest, so a
      strategy cannot see the future;
    - stale data is omitted rather than carried, because a four-hour-old price
      looks valid and will size a real order.

    Because ``Strategy.decide`` takes nothing besides a snapshot and a
    portfolio, the backtest and the live engine run the same code path against
    the same information.
    """

    timestamp: int
    candles: Mapping[Symbol, tuple[Candle, ...]]
    books: Mapping[Symbol, OrderBook]
    last_prices: Mapping[Symbol, Decimal]
