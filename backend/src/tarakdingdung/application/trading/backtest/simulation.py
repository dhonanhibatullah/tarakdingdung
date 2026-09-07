"""Fill simulation for replays.

Deliberately pessimistic where it is uncertain: a fill crosses the spread (it
takes the near touch of the book, never the mid or the strategy's own limit),
pays the cost model's fee and the slippage of walking deeper, and an order the
book cannot absorb does not fill at all rather than filling at an invented
price. Filling at the mid, or ignoring depth, is how a backtest reports an edge
that execution then eats.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal

from tarakdingdung.domain.contracts.algorithm.cost import CostModel
from tarakdingdung.domain.models.algorithm import PlannedOrder, Side
from tarakdingdung.domain.models.market import (
    MarketSnapshot, OrderBook, Symbol, Venue,
)
from tarakdingdung.domain.models.performance import Fill
from tarakdingdung.domain.models.portfolio import Portfolio, Position


@dataclass(frozen=True, slots=True)
class SimulationResult:
    portfolio: Portfolio
    fills: tuple[Fill, ...]
    unfilled: int


def simulate(*, orders: tuple[PlannedOrder, ...], snapshot: MarketSnapshot,
             portfolio: Portfolio, cost_model: CostModel) -> SimulationResult:
    positions = dict(portfolio.positions)
    cash = dict(portfolio.cash)
    fills: list[Fill] = []
    unfilled = 0

    for order in orders:
        book = snapshot.books.get(order.symbol)
        price = _fill_price(order, book, snapshot)
        if book is None or price is None:
            unfilled += 1
            continue
        estimate = cost_model.estimate(order, book)
        if not estimate.fillable:
            unfilled += 1
            continue

        notional = order.quantity * price
        cost = estimate.fee + estimate.slippage
        venue = order.symbol.venue
        if order.side is Side.BUY:
            cash[venue] = cash.get(venue, Decimal(0)) - notional - cost
            _add(positions, order.symbol, order.quantity, price)
        else:
            cash[venue] = cash.get(venue, Decimal(0)) + notional - cost
            _add(positions, order.symbol, -order.quantity, price)

        fills.append(Fill(symbol=order.symbol, side=order.side,
                          quantity=order.quantity, price=price,
                          fee=estimate.fee, timestamp=snapshot.timestamp))

    return SimulationResult(
        portfolio=Portfolio(timestamp=snapshot.timestamp, cash=cash,
                            positions=positions,
                            equity=equity_of(cash, positions, snapshot.last_prices)),
        fills=tuple(fills), unfilled=unfilled)


def equity_of(cash: Mapping[Venue, Decimal], positions: Mapping[Symbol, Position],
              prices: Mapping[Symbol, Decimal]) -> Decimal:
    held = sum((p.quantity * prices[s] for s, p in positions.items() if s in prices),
               Decimal(0))
    return held + sum(cash.values(), Decimal(0))


def _fill_price(order: PlannedOrder, book: OrderBook | None,
                snapshot: MarketSnapshot) -> Decimal | None:
    """Where the order fills: the near touch of the book it crosses.

    A buy lifts the best ask, a sell hits the best bid — so the fill already
    pays the spread, and the cost model's slippage is only what walking deeper
    adds on top. Falls back to the order's own limit, then the last price, when
    there is no book (which a replay should never hit).
    """
    if book is not None:
        levels = book.asks if order.side is Side.BUY else book.bids
        if levels:
            return levels[0].price
    return order.price if order.price is not None else snapshot.last_prices.get(order.symbol)


def _add(positions: dict[Symbol, Position], symbol: Symbol, delta: Decimal,
         price: Decimal) -> None:
    current = positions.get(symbol)
    quantity = (current.quantity if current else Decimal(0)) + delta
    if quantity <= 0:
        positions.pop(symbol, None)
        return
    positions[symbol] = Position(symbol=symbol, quantity=quantity, average_price=price)
