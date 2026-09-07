"""Invariants that belong to the contracts, not to any one implementation.

Each function asserts what every implementation of a contract must satisfy, so
adding an implementation costs one line in the parametrised list in
``test_conformance.py`` and cannot regress the guarantees the rest of the
system relies on.
"""

from decimal import Decimal

from tarakdingdung.domain.contracts.algorithm.allocation import Allocator
from tarakdingdung.domain.contracts.algorithm.cost import CostModel
from tarakdingdung.domain.contracts.algorithm.order import OrderPlanner
from tarakdingdung.domain.contracts.algorithm.risk import RiskRule
from tarakdingdung.domain.models.algorithm import (
    OrderType, PlannedOrder, Side, Signals, TargetWeights, TimeInForce, TradeIntent,
)
from tarakdingdung.domain.models.market import BookLevel, OrderBook, Symbol, SymbolRules, Venue
from tarakdingdung.domain.models.portfolio import Portfolio, Position, RiskState

TS = 1_757_000_000_000

BTC_IDX = Symbol(venue=Venue.INDODAX, base="BTC", quote="IDR")
ETH_IDX = Symbol(venue=Venue.INDODAX, base="ETH", quote="IDR")
BTC_TKO = Symbol(venue=Venue.TOKOCRYPTO, base="BTC", quote="USDT")
ETH_TKO = Symbol(venue=Venue.TOKOCRYPTO, base="ETH", quote="USDT")
ALL_SYMBOLS = (BTC_IDX, ETH_IDX, BTC_TKO, ETH_TKO)


def portfolio(*, equity: str = "10000", positions=()) -> Portfolio:
    return Portfolio(
        timestamp=TS,
        cash={Venue.INDODAX: Decimal(equity), Venue.TOKOCRYPTO: Decimal(0)},
        positions={p.symbol: p for p in positions},
        equity=Decimal(equity))


def position(symbol: Symbol, quantity: str, price: str = "100") -> Position:
    return Position(symbol=symbol, quantity=Decimal(quantity),
                    average_price=Decimal(price))


def risk_state(*, equity_peak: str = "10000", daily_pnl: str = "0",
               volatility: float = 0.01, halted: bool = False) -> RiskState:
    return RiskState(timestamp=TS, equity_peak=Decimal(equity_peak),
                     daily_pnl=Decimal(daily_pnl),
                     realized_volatility=volatility, halted=halted)


def rules(symbol: Symbol, *, tick: str = "0.01", step: str = "0.0001",
          min_notional: str = "1") -> SymbolRules:
    return SymbolRules(symbol=symbol, tick_size=Decimal(tick),
                       step_size=Decimal(step), min_notional=Decimal(min_notional),
                       maker_fee=Decimal("0.001"), taker_fee=Decimal("0.002"))


def book(symbol: Symbol, *, levels: int = 5, size: str = "10") -> OrderBook:
    bids = tuple(BookLevel(price=Decimal(100 - i), quantity=Decimal(size))
                 for i in range(levels))
    asks = tuple(BookLevel(price=Decimal(101 + i), quantity=Decimal(size))
                 for i in range(levels))
    return OrderBook(symbol=symbol, timestamp=TS, bids=bids, asks=asks)


def gross(weights: TargetWeights) -> float:
    return sum(abs(w) for w in weights.weights.values())


# --- RiskRule ---------------------------------------------------------------

_RISK_CASES = (
    ({BTC_IDX: 0.5, ETH_IDX: 0.5}, risk_state()),
    ({BTC_IDX: 0.9, ETH_TKO: 0.1}, risk_state()),
    ({BTC_IDX: 0.25, ETH_IDX: 0.25, BTC_TKO: 0.25, ETH_TKO: 0.25}, risk_state()),
    ({BTC_IDX: 0.4, BTC_TKO: 0.4}, risk_state()),
    ({}, risk_state()),
    ({BTC_IDX: 1.0}, risk_state(volatility=0.9)),
    ({BTC_IDX: 1.0}, risk_state(halted=True)),
    ({BTC_IDX: 1.0}, risk_state(daily_pnl="-9000")),
)


def assert_risk_rule_conforms(rule: RiskRule) -> None:
    book_ = portfolio(equity="5000")
    for weights, state in _RISK_CASES:
        original = TargetWeights(timestamp=TS, weights=dict(weights))

        once = rule.apply(original, book_, state)
        twice = rule.apply(once, book_, state)

        # Idempotence: a chain of rules must not compound its reductions.
        assert twice.weights == once.weights, f"{type(rule).__name__} is not idempotent"
        # A rule reduces risk; it never invents more.
        assert gross(once) <= gross(original) + 1e-9
        # The output must itself be a valid target, which TargetWeights
        # enforces on construction.
        TargetWeights(timestamp=once.timestamp, weights=dict(once.weights))
        # No rule may introduce a symbol the strategy did not ask for.
        assert set(once.weights) <= set(original.weights)


def assert_risk_rule_respects_halt(rule: RiskRule) -> None:
    """Only for rules that claim to halt; asserted separately from the
    universal invariants because a cap legitimately ignores the halt flag."""
    weights = TargetWeights(timestamp=TS, weights={BTC_IDX: 0.5})
    halted = rule.apply(weights, portfolio(), risk_state(halted=True))
    assert halted.weights == {}


# --- Allocator --------------------------------------------------------------

_SIGNAL_CASES = (
    {},
    {BTC_IDX: 1.0},
    {BTC_IDX: 1.0, ETH_IDX: 0.5, BTC_TKO: 0.25},
    {BTC_IDX: 0.0, ETH_IDX: 0.0},
    {s: 1.0 for s in ALL_SYMBOLS},
)


def assert_allocator_conforms(allocator: Allocator) -> None:
    book_ = portfolio()
    for scores in _SIGNAL_CASES:
        signals = Signals(timestamp=TS, scores=dict(scores))
        weights = allocator.allocate(signals, book_)

        # Gross exposure within budget — TargetWeights enforces it, but assert
        # explicitly so a failure names the allocator.
        assert gross(weights) <= 1.0 + 1e-9, f"{type(allocator).__name__} over-allocated"
        # Only symbols it was given an opinion about.
        assert set(weights.weights) <= set(scores)
        # A zero signal is not a position.
        for symbol, weight in weights.weights.items():
            assert scores[symbol] != 0.0 or weight == 0.0
        assert weights.timestamp == TS


def assert_allocator_is_flat_without_signals(allocator: Allocator) -> None:
    weights = allocator.allocate(Signals(timestamp=TS, scores={}), portfolio())
    assert weights.weights == {}


# --- CostModel --------------------------------------------------------------

def _order(quantity: str, side: Side = Side.BUY) -> PlannedOrder:
    return PlannedOrder(symbol=BTC_IDX, side=side, type=OrderType.LIMIT,
                        quantity=Decimal(quantity), price=Decimal("100"),
                        time_in_force=TimeInForce.GTC)


def assert_cost_model_conforms(model: CostModel) -> None:
    depth = book(BTC_IDX, levels=5, size="10")

    for side in (Side.BUY, Side.SELL):
        small = model.estimate(_order("1", side), depth)
        large = model.estimate(_order("40", side), depth)

        assert small.fee >= 0 and small.slippage >= 0
        # Non-decreasing in size: a bigger order never costs less.
        assert large.total >= small.total, f"{type(model).__name__} is not monotonic"
        assert small.fillable is True

    # Beyond the book's depth, the honest answer is "cannot fill".
    beyond = model.estimate(_order("10000"), depth)
    assert beyond.fillable is False

    empty = OrderBook(symbol=BTC_IDX, timestamp=TS, bids=(), asks=())
    assert model.estimate(_order("1"), empty).fillable is False


# --- OrderPlanner -----------------------------------------------------------

_INTENTS = (
    TradeIntent(symbol=BTC_IDX, side=Side.BUY, quantity=Decimal("1.23456789"),
                reference_price=Decimal("100.007")),
    TradeIntent(symbol=ETH_IDX, side=Side.SELL, quantity=Decimal("0.00000001"),
                reference_price=Decimal("50.004")),
    TradeIntent(symbol=BTC_TKO, side=Side.BUY, quantity=Decimal("2"),
                reference_price=Decimal("0.0001")),
    TradeIntent(symbol=ETH_TKO, side=Side.SELL, quantity=Decimal("5"),
                reference_price=Decimal("20")),
)


def assert_order_planner_conforms(planner: OrderPlanner) -> None:
    known = {s: rules(s) for s in (BTC_IDX, ETH_IDX, BTC_TKO)}
    plan = planner.plan(_INTENTS, known)

    # Nothing is silently dropped: this is the invariant OrderPlan exists for.
    accounted = len(plan.orders) + len(plan.rejected)
    assert accounted == len(_INTENTS), (
        f"{type(planner).__name__} lost {len(_INTENTS) - accounted} intent(s)")

    rejected_symbols = [r.intent.symbol for r in plan.rejected]
    # ETH_TKO has no rules, so it must be rejected rather than guessed at.
    assert ETH_TKO in rejected_symbols

    for order in plan.orders:
        assert order.quantity > 0
        assert order.symbol in known

    assert planner.plan((), known).orders == ()
    assert planner.plan((), known).rejected == ()
