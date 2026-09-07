from decimal import Decimal

from tarakdingdung.domain.models.algorithm import (
    CyclePlan, OrderPlan, OrderType, PlannedOrder, Side, TargetWeights, TimeInForce,
)
from tarakdingdung.domain.models.market import (
    BookLevel, Candle, MarketSnapshot, OrderBook, Symbol, SymbolRules, Venue,
)
from tests.fakes.trading import TS

BTC = Symbol(venue=Venue.INDODAX, base="BTC", quote="IDR")
ETH = Symbol(venue=Venue.INDODAX, base="ETH", quote="IDR")


def order(symbol: Symbol = BTC, *, side: Side = Side.BUY, quantity: str = "1",
          client_order_id: str = "tdd0000000000001") -> PlannedOrder:
    return PlannedOrder(symbol=symbol, side=side, type=OrderType.LIMIT,
                        quantity=Decimal(quantity), price=Decimal("100"),
                        time_in_force=TimeInForce.GTC,
                        client_order_id=client_order_id)


def plan(*, orders=(), rejected=(), halted_by=None) -> CyclePlan:
    return CyclePlan(timestamp=TS,
                     weights=TargetWeights(timestamp=TS, weights={}),
                     orders=OrderPlan(orders=tuple(orders), rejected=tuple(rejected)),
                     halted_by=halted_by)


def book(symbol: Symbol = BTC, *, size: str = "1000") -> OrderBook:
    return OrderBook(
        symbol=symbol, timestamp=TS,
        bids=(BookLevel(price=Decimal("100"), quantity=Decimal(size)),),
        asks=(BookLevel(price=Decimal("101"), quantity=Decimal(size)),))


def snapshot(symbols=(BTC,), *, prices=True) -> MarketSnapshot:
    return MarketSnapshot(
        timestamp=TS,
        candles={s: (Candle(open_time=TS, open=Decimal("100"), high=Decimal("100"),
                            low=Decimal("100"), close=Decimal("100"),
                            volume=Decimal("1")),) for s in symbols},
        books={s: book(s) for s in symbols},
        last_prices={s: Decimal("100") for s in symbols} if prices else {})


def rules(symbol: Symbol = BTC) -> SymbolRules:
    return SymbolRules(symbol=symbol, tick_size=Decimal("0.01"),
                       step_size=Decimal("0.0001"), min_notional=Decimal("1"),
                       maker_fee=Decimal("0.001"), taker_fee=Decimal("0.002"))


class StubPlanner:
    """Returns a fixed plan, so engine tests exercise the engine rather than
    re-testing the planner."""

    def __init__(self, result: CyclePlan) -> None:
        self.result = result
        self.calls = 0

    def plan(self, **kwargs) -> CyclePlan:
        self.calls += 1
        return self.result
