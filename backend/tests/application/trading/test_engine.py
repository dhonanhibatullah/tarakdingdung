import uuid
from decimal import Decimal

from tarakdingdung.application.trading.engine.usecase import TradingEngineUsecase
from tarakdingdung.domain.contracts.algorithm.risk import RiskResult, RiskRule, RiskState
from tarakdingdung.domain.contracts.llm.pipeline import DecisionResult
from tarakdingdung.domain.contracts.trade.executor import ExecutionResult
from tarakdingdung.domain.contracts.trade.reconciler import ReconcileResult
from tarakdingdung.domain.models.decision import Decision, Weight
from tarakdingdung.domain.models.market import Candle
from tarakdingdung.domain.models.order import Fill, Order, OrderStatus
from tarakdingdung.domain.models.portfolio import Balance, PortfolioSnapshot
from tarakdingdung.domain.models.symbol import Symbol
from tarakdingdung.domain.usecases.trading.engine import CycleStatus
from tarakdingdung.infrastructure.algorithm.rebalance.no_trade_band import NoTradeBandRebalancer
from tarakdingdung.infrastructure.algorithm.risk.overlay import StandardRiskOverlay
from tarakdingdung.infrastructure.utility.single_flight.memory import InMemorySingleFlight
from tests.fakes.trading import (
    InMemoryDecisionRepository,
    InMemoryMarketDataRepository,
    InMemoryNewsRepository,
    InMemoryOrderJournalRepository,
    InMemoryPortfolioRepository,
    InMemoryUniverseRepository,
)


def _btc():
    return Symbol(id="s-btc", venue="indodax", base="BTC", quote="IDR", external="BTCIDR")


def _valid_decision():
    return Decision(
        id="",
        universe_id="u1",
        as_of_ms=1000,
        weights=[Weight("s-btc", 0.5)],
        reasoning="r",
        confidence=0.8,
        traces={},
        prompt="p",
        raw_response="j",
        status="valid",
    )


class FakeClock:
    def now_ms(self) -> int:
        return 2000


class FakeDecisionMaker:
    def __init__(self, decision=None, held=False, events=None) -> None:
        self.decision = decision
        self.held = held
        self.events = events

    async def decide(self, context):
        if self.events is not None:
            self.events.append("decision_maker.decide")
        return DecisionResult(decision=self.decision, held=self.held, traces={})


class RecordingExecutor:
    def __init__(self, events, order_journal) -> None:
        self.events = events
        self.order_journal = order_journal

    async def submit(self, orders, symbols):
        self.events.append("executor.submit")
        fills = [
            Fill(
                id=str(uuid.uuid4()),
                order_id=o.id,
                price=o.price,
                quantity=o.quantity,
                fee=Decimal("0"),
                filled_at_ms=2000,
            )
            for o in orders
        ]
        return ExecutionResult(unconfirmed=[], fills=fills)


class RecordingReconciler:
    def __init__(self, events) -> None:
        self.events = events

    async def reconcile(self, orders, symbols):
        self.events.append("reconciler.reconcile")
        return ReconcileResult(
            resolved=[(o.client_order_id, OrderStatus.SUBMITTED) for o in orders],
            still_unconfirmed=[],
        )


class AlwaysHaltRule(RiskRule):
    def apply(self, weights, state):
        return RiskResult(weights=[], halted=True, rule="test_halt", reason="x")


def _market_data():
    md = InMemoryMarketDataRepository()
    md.candles.append(
        Candle(
            symbol_id="s-btc",
            open_time_ms=1000,
            open=Decimal("10"),
            high=Decimal("10"),
            low=Decimal("10"),
            close=Decimal("10"),
            volume=Decimal("1"),
        )
    )
    return md


def _build(events, **overrides):
    approved = overrides.get("approved", [_btc()])
    snapshot = overrides.get(
        "snapshot",
        PortfolioSnapshot(id="snap1", venue="indodax", as_of_ms=1000, equity=Decimal("1000")),
    )
    balances = overrides.get(
        "balances",
        [
            Balance(snapshot_id="snap1", asset="IDR", free=Decimal("1000"), locked=Decimal("0")),
            Balance(snapshot_id="snap1", asset="BTC", free=Decimal("0"), locked=Decimal("0")),
        ],
    )
    order_journal = overrides.get("order_journal", InMemoryOrderJournalRepository(events=events))
    engine = TradingEngineUsecase(
        enabled=overrides.get("enabled", True),
        universe_id="u1",
        venue="indodax",
        single_flight=overrides.get("single_flight", InMemorySingleFlight()),
        universes=InMemoryUniverseRepository(approved_symbols=approved),
        order_journal=order_journal,
        reconciler=overrides.get("reconciler", RecordingReconciler(events)),
        portfolio=InMemoryPortfolioRepository(snapshot=snapshot, balances=balances),
        market_data=overrides.get("market_data", _market_data()),
        news=InMemoryNewsRepository(),
        decision_maker=overrides.get(
            "decision_maker", FakeDecisionMaker(decision=_valid_decision(), events=events)
        ),
        decisions=InMemoryDecisionRepository(events=events),
        risk_overlay=overrides.get("risk_overlay", StandardRiskOverlay([])),
        rebalancer=NoTradeBandRebalancer(band=0.01, min_notional=Decimal("1")),
        executor=overrides.get("executor", RecordingExecutor(events, order_journal)),
        clock=FakeClock(),
    )
    return engine, order_journal


async def test_disabled_returns_disabled():
    engine, _ = _build([], enabled=False)
    result = await engine.run_cycle()
    assert result.status is CycleStatus.DISABLED


async def test_single_flight_skip():
    sf = InMemorySingleFlight()
    await sf.acquire("engine:u1")
    engine, _ = _build([], single_flight=sf)
    result = await engine.run_cycle()
    assert result.status is CycleStatus.SKIPPED


async def test_no_snapshot_returns_no_data():
    engine, _ = _build([], snapshot=None)
    result = await engine.run_cycle()
    assert result.status is CycleStatus.NO_DATA


async def test_held_decision_returns_held():
    engine, _ = _build([], decision_maker=FakeDecisionMaker(held=True))
    result = await engine.run_cycle()
    assert result.status is CycleStatus.HELD


async def test_halted_returns_halted():
    engine, _ = _build([], risk_overlay=StandardRiskOverlay([AlwaysHaltRule()]))
    result = await engine.run_cycle()
    assert result.status is CycleStatus.HALTED
    assert result.detail == "test_halt"


async def test_executed_persists_before_submit():
    events = []
    engine, order_journal = _build(events)
    result = await engine.run_cycle()

    assert result.status is CycleStatus.EXECUTED
    assert "executor.submit" in events
    i_dec = events.index("decision.create")
    i_order = events.index("order.create")
    i_submit = events.index("executor.submit")
    assert i_dec < i_order < i_submit
    assert len(order_journal.orders) == 1
    assert len(order_journal.fills) == 1


async def test_reconcile_runs_before_decide():
    events = []
    order_journal = InMemoryOrderJournalRepository(events=events)
    from tarakdingdung.domain.models.order import OrderSide

    unconfirmed = Order(
        id="o-prev",
        client_order_id="prev",
        symbol_id="s-btc",
        side=OrderSide.BUY,
        price=Decimal("10"),
        quantity=Decimal("1"),
        status=OrderStatus.UNCONFIRMED,
        created_at_ms=100,
    )
    order_journal.orders["o-prev"] = unconfirmed

    engine, _ = _build(events, order_journal=order_journal)
    await engine.run_cycle()

    assert events.index("reconciler.reconcile") < events.index("decision_maker.decide")


async def test_dry_run_does_not_submit():
    events = []
    engine, _ = _build(events)
    result = await engine.dry_run()
    assert result.status is CycleStatus.EXECUTED
    assert "executor.submit" not in events
