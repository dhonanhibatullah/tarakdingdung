import uuid
from decimal import Decimal

import pytest

from tarakdingdung.application.trading.engine.usecase import TradingEngineUsecase
from tarakdingdung.application.trading.history.usecase import MarketDataHistoryUsecase
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.execution import ExecutionResult, OrderState
from tarakdingdung.domain.models.performance import Fill
from tarakdingdung.domain.models.strategy import TradingMode
from tarakdingdung.domain.usecases.trading.engine import CycleDecision, RunCycleRequest
from tests.application.trading.conftest import (
    BTC, StubPlanner, order, plan, rules, snapshot,
)
from tests.fakes.trading import (
    TS, FakeClock, FakeExecutor, FakeMarketDataRepository, FakeOrderJournalRepository,
    FakePortfolioRepository, FakeSingleFlight, FakeStrategyRepository, make_portfolio,
    make_strategy,
)
from tests.fakes.utilities import NullLogger


class Ctx:
    def __init__(self, *, cycle_plan=None, strategy=None, executor=None,
                 lock=None, portfolio=True, prices=True):
        self.config = strategy or make_strategy(universe=(BTC,), mode=TradingMode.PAPER)
        self.strategies = FakeStrategyRepository((self.config,))
        self.market_data = FakeMarketDataRepository()
        self.market_data.snapshot = snapshot(prices=prices)
        self.market_data.rules = {BTC: rules(BTC)}
        self.journal = FakeOrderJournalRepository()
        self.executor = executor or FakeExecutor(journal=self.journal)
        self.portfolios = FakePortfolioRepository(
            portfolio=make_portfolio() if portfolio else None)
        self.lock = lock or FakeSingleFlight()
        self.planner = StubPlanner(cycle_plan or plan(orders=(order(),)))
        self.engine = TradingEngineUsecase(
            strategies=self.strategies,
            history=MarketDataHistoryUsecase(market_data=self.market_data,
                                             logger=NullLogger()),
            market_data=self.market_data, portfolios=self.portfolios,
            journal=self.journal,
            executors={TradingMode.PAPER: self.executor},
            planner_factory=lambda config, params: self.planner,
            lock=self.lock, clock=FakeClock(), logger=NullLogger())

    async def run(self, **kw):
        return await self.engine.run_cycle(
            RunCycleRequest(strategy_id=self.config.id, **kw))


# --- the write-ahead guarantee ---------------------------------------------

async def test_planned_orders_are_persisted_before_submission():
    # The whole recovery story depends on this ordering: a process that dies
    # on submit must leave a record to reconcile from.
    ctx = Ctx()
    await ctx.run()
    assert ctx.journal.events == ["write_planned", "submit", "write_execution"]


async def test_the_record_survives_a_failing_submission():
    ctx = Ctx(executor=None)
    ctx.executor = FakeExecutor(fail_submit=True, journal=ctx.journal)
    ctx.engine._executors = {TradingMode.PAPER: ctx.executor}
    await ctx.run()
    assert ctx.journal.planned, "intent must be recorded even when submission fails"


# --- no blind retry ---------------------------------------------------------

async def test_a_transport_failure_leaves_the_order_unconfirmed():
    ctx = Ctx()
    ctx.executor = FakeExecutor(fail_submit=True, journal=ctx.journal)
    ctx.engine._executors = {TradingMode.PAPER: ctx.executor}
    result = await ctx.run()
    assert result.execution is not None and not result.execution.is_complete
    assert ctx.journal.states["tdd0000000000001"] is OrderState.UNCONFIRMED
    # Submitted exactly once. A retry here is how one position becomes two.
    assert len(ctx.executor.submitted) == 1


async def test_the_next_cycle_reconciles_rather_than_resubmitting():
    ctx = Ctx(cycle_plan=plan(orders=()))
    ctx.journal.unreconciled = [order()]
    result = await ctx.run()
    assert result.reconciled == 1
    assert ctx.executor.submitted == []


async def test_reconciliation_runs_before_anything_is_planned():
    # A decision sized against a portfolio missing orders we already placed
    # would double down on a position we already have.
    ctx = Ctx()
    ctx.journal.unreconciled = [order()]
    await ctx.run()
    assert ctx.planner.calls == 1
    assert ctx.journal.events[0] == "reconcile"


async def test_a_failed_reconciliation_does_not_stop_the_cycle():
    class Failing(FakeExecutor):
        async def read_by_client_order_id(self, client_order_id, *, symbol=None):
            raise DomainError("venue down", ErrorType.UPSTREAM)

    ctx = Ctx()
    ctx.executor = Failing(journal=ctx.journal)
    ctx.engine._executors = {TradingMode.PAPER: ctx.executor}
    ctx.journal.unreconciled = [order()]
    result = await ctx.run()
    assert result.decision is CycleDecision.TRADED
    assert result.reconciled == 0


async def test_reconcile_passes_the_symbol_to_the_executor():
    # Binance order lookup needs a symbol; the journal entry carries it.
    ctx = Ctx(cycle_plan=plan(orders=()))
    ctx.journal.unreconciled = [order()]
    await ctx.run()
    assert ctx.executor.looked_up == [("tdd0000000000001", BTC)]


# --- fills and the shared ledger ------------------------------------------

class _FillingExecutor(FakeExecutor):
    """Accepts every order and reports a fill for it."""

    async def submit(self, orders) -> ExecutionResult:
        base = await super().submit(orders)
        fills = tuple(
            Fill(symbol=o.symbol, side=o.side, quantity=o.quantity,
                 price=o.price or Decimal("1"), fee=Decimal("0"), timestamp=0)
            for o in orders)
        return ExecutionResult(accepted=base.accepted, rejected=base.rejected,
                               unconfirmed=base.unconfirmed, fills=fills)


async def test_paper_fills_stay_out_of_the_shared_ledger():
    # A paper strategy on the engine exercises the whole cycle, but its fills
    # are fictional: the shared fills/portfolio tables track the real account.
    ctx = Ctx()  # PAPER by default
    ctx.executor = _FillingExecutor(journal=ctx.journal)
    ctx.engine._executors = {TradingMode.PAPER: ctx.executor}
    result = await ctx.run()
    assert result.decision is CycleDecision.TRADED
    assert ctx.portfolios.fills == []
    # the per-strategy journal still records what it did
    assert ctx.journal.states["tdd0000000000001"] is OrderState.ACCEPTED


async def test_live_fills_are_recorded_to_the_shared_ledger():
    ctx = Ctx(strategy=make_strategy(universe=(BTC,), mode=TradingMode.LIVE))
    ctx.executor = _FillingExecutor(journal=ctx.journal)
    ctx.engine._executors = {TradingMode.LIVE: ctx.executor}
    result = await ctx.run()
    assert result.decision is CycleDecision.TRADED
    assert len(ctx.portfolios.fills) == 1


# --- halting ----------------------------------------------------------------

async def test_a_halt_cancels_resting_orders():
    ctx = Ctx(cycle_plan=plan(orders=(order(),), halted_by="HaltFlagRiskRule"))
    result = await ctx.run()
    assert ctx.executor.cancelled == [(BTC,)]
    assert result.decision is CycleDecision.HALTED
    assert result.halted_by == "HaltFlagRiskRule"


async def test_a_halt_still_submits_its_exit_orders():
    # De-risking means reducing exposure, not merely declining to add to it.
    ctx = Ctx(cycle_plan=plan(orders=(order(),), halted_by="DrawdownHaltRiskRule"))
    await ctx.run()
    assert len(ctx.executor.submitted) == 1


async def test_a_failed_cancellation_persists_the_halt():
    ctx = Ctx(cycle_plan=plan(orders=(), halted_by="HaltFlagRiskRule"))
    ctx.executor = FakeExecutor(fail_cancel=True, journal=ctx.journal)
    ctx.engine._executors = {TradingMode.PAPER: ctx.executor}
    await ctx.run()
    halted, reason = await ctx.portfolios.read_halt(strategy_id=ctx.config.id)
    assert halted is True
    assert "cancel failed" in (reason or "")


async def test_a_successful_cancellation_clears_a_standing_halt():
    ctx = Ctx(cycle_plan=plan(orders=(), halted_by="HaltFlagRiskRule"))
    await ctx.portfolios.set_halt(strategy_id=ctx.config.id, halted=True,
                                  reason="cancel failed: earlier")
    await ctx.run()
    assert await ctx.portfolios.read_halt(strategy_id=ctx.config.id) == (False, None)


# --- concurrency ------------------------------------------------------------

async def test_an_overlapping_cycle_is_skipped_not_queued():
    ctx = Ctx(lock=FakeSingleFlight(available=False))
    result = await ctx.run()
    assert result.decision is CycleDecision.SKIPPED
    assert ctx.planner.calls == 0


async def test_the_lock_is_released_even_when_the_cycle_raises():
    ctx = Ctx()
    ctx.planner.plan = lambda **kw: (_ for _ in ()).throw(
        DomainError("boom", ErrorType.FAILURE))
    with pytest.raises(DomainError):
        await ctx.run()
    assert ctx.lock.released == [f"cycle:{ctx.config.id}"]


# --- data and state guards --------------------------------------------------

async def test_a_stale_or_empty_snapshot_stops_the_cycle():
    ctx = Ctx(prices=False)
    result = await ctx.run()
    assert result.decision is CycleDecision.NO_DATA
    assert ctx.planner.calls == 0


async def test_no_recorded_portfolio_stops_the_cycle():
    ctx = Ctx(portfolio=False)
    assert (await ctx.run()).decision is CycleDecision.NO_DATA


async def test_a_disabled_strategy_does_nothing():
    ctx = Ctx(strategy=make_strategy(universe=(BTC,), is_enabled=False))
    result = await ctx.run()
    assert result.decision is CycleDecision.DISABLED
    assert ctx.lock.held == set()


async def test_a_missing_strategy_raises():
    ctx = Ctx()
    with pytest.raises(DomainError) as e:
        await ctx.engine.run_cycle(RunCycleRequest(strategy_id=uuid.uuid4()))
    assert e.value.type is ErrorType.NOT_FOUND


async def test_a_mode_without_an_executor_raises():
    ctx = Ctx(strategy=make_strategy(universe=(BTC,), mode=TradingMode.LIVE))
    with pytest.raises(DomainError) as e:
        await ctx.run()
    assert e.value.type is ErrorType.BAD_STATE


# --- dry run ----------------------------------------------------------------

async def test_a_dry_run_plans_without_touching_the_market():
    ctx = Ctx()
    result = await ctx.run(dry_run=True)
    assert result.decision is CycleDecision.DRY_RUN
    assert result.plan is not None and result.plan.orders
    assert ctx.executor.submitted == []
    assert ctx.journal.planned == []


# --- ordinary outcomes ------------------------------------------------------

async def test_no_drift_is_distinct_from_no_data():
    ctx = Ctx(cycle_plan=plan(orders=()))
    result = await ctx.run()
    assert result.decision is CycleDecision.NO_DRIFT
    assert ctx.executor.submitted == []


async def test_a_traded_cycle_records_states_and_fills():
    ctx = Ctx()
    result = await ctx.run()
    assert result.decision is CycleDecision.TRADED
    assert ctx.journal.states["tdd0000000000001"] is OrderState.ACCEPTED
    assert ctx.journal.executions
