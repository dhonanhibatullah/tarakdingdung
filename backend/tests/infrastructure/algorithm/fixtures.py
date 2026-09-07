"""Shared constructors for algorithm tests.

Kept apart from ``conformance.py``, which holds the contract invariants: this
module only builds inputs.
"""

from decimal import Decimal

from tarakdingdung.domain.models.algorithm import (
    OrderType, PlannedOrder, Side, TimeInForce,
)
from tarakdingdung.domain.models.market import BookLevel, Candle, MarketSnapshot, OrderBook
from tarakdingdung.domain.models.performance import EquityPoint, Fill
from tests.infrastructure.algorithm.conformance import BTC_IDX, TS


def candles(prices: list[float]) -> tuple[Candle, ...]:
    return tuple(Candle(open_time=TS + i, open=Decimal(str(p)), high=Decimal(str(p)),
                        low=Decimal(str(p)), close=Decimal(str(p)),
                        volume=Decimal("1"))
                 for i, p in enumerate(prices))


def snapshot(*, candle_map=None, books=None, prices=None) -> MarketSnapshot:
    return MarketSnapshot(timestamp=TS, candles=candle_map or {},
                          books=books or {}, last_prices=prices or {})


def buy(quantity: str, price: str = "101") -> PlannedOrder:
    return PlannedOrder(symbol=BTC_IDX, side=Side.BUY, type=OrderType.LIMIT,
                        quantity=Decimal(quantity), price=Decimal(price),
                        time_in_force=TimeInForce.GTC)


def curve(values) -> tuple[EquityPoint, ...]:
    return tuple(EquityPoint(timestamp=TS + i, equity=Decimal(str(v)))
                 for i, v in enumerate(values))


def fill(quantity: str, price: str, fee: str) -> Fill:
    return Fill(symbol=BTC_IDX, side=Side.BUY, quantity=Decimal(quantity),
                price=Decimal(price), fee=Decimal(fee), timestamp=TS)


def level(price: str, quantity: str) -> BookLevel:
    return BookLevel(price=Decimal(price), quantity=Decimal(quantity))


def order_book(symbol, *, bids=(), asks=()) -> OrderBook:
    return OrderBook(symbol=symbol, timestamp=TS, bids=tuple(bids), asks=tuple(asks))
