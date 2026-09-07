import uuid
from decimal import Decimal

import pytest

from tarakdingdung.application.trading.backtest.usecase import BacktestingUsecase
from tarakdingdung.application.trading.validation.usecase import StrategyValidationUsecase
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.market import Coverage, TimeRange
from tarakdingdung.domain.models.performance import OverfittingReport
from tarakdingdung.domain.usecases.trading.backtest import (
    ListBacktestsRequest, RunBacktestRequest,
)
from tarakdingdung.domain.usecases.trading.validation import RunWalkForwardRequest
from tarakdingdung.infrastructure.algorithm.cost.flat_fee import FlatFeeCostModel
from tarakdingdung.infrastructure.algorithm.metric.standard import (
    StandardPerformanceEvaluator,
)
from tarakdingdung.infrastructure.algorithm.validation.combinatorial import (
    CombinatorialOverfittingTest,
)
from tests.application.trading.conftest import BTC, StubPlanner, order, plan, rules, snapshot
from tests.fakes.trading import (
    TS, FakeBacktestRepository, FakeMarketDataRepository, FakeStrategyRepository,
    make_strategy,
)
from tests.fakes.utilities import NullLogger

HOUR = 3_600_000
WINDOW = TimeRange(start=TS, end=TS + HOUR * 10)


async def build(*, cycle_plan=None, coverage=None):
    config = make_strategy(universe=(BTC,))
    market_data = FakeMarketDataRepository()
    market_data.snapshot = snapshot()
    await market_data.write_rules({BTC: rules(BTC)})
    market_data.coverage = coverage
    backtests = FakeBacktestRepository()
    planner = StubPlanner(cycle_plan or plan(orders=()))
    usecase = BacktestingUsecase(
        strategies=FakeStrategyRepository((config,)), market_data=market_data,
        backtests=backtests, planner_factory=lambda c, p: planner,
        cost_model=FlatFeeCostModel(fee_rate=Decimal("0.001")),
        evaluator=StandardPerformanceEvaluator(), logger=NullLogger())
    return usecase, config, backtests, planner


def request(config, **kw):
    base = dict(strategy_id=config.id, window=WINDOW,
                initial_equity=Decimal("10000"), interval="1h")
    return RunBacktestRequest(**{**base, **kw})


# --- backtesting ------------------------------------------------------------

async def test_replays_one_cycle_per_interval():
    usecase, config, _, planner = await build()
    result = await usecase.run(request(config))
    assert result.cycles == 10
    assert planner.calls == 10


async def test_refuses_a_window_with_insufficient_coverage():
    # A gap becomes an invented flat period and the report would describe a
    # strategy that never traded.
    gapped = Coverage(symbol=BTC, interval="1h", window=WINDOW,
                      expected=100, present=50, gaps=(TimeRange(start=TS, end=TS + 1),))
    usecase, config, _, _ = await build(coverage=gapped)
    with pytest.raises(DomainError) as e:
        await usecase.run(request(config))
    assert e.value.type is ErrorType.VALIDATION
    assert "covered" in e.value.message


async def test_a_lenient_threshold_admits_a_gapped_window():
    gapped = Coverage(symbol=BTC, interval="1h", window=WINDOW,
                      expected=100, present=50, gaps=())
    usecase, config, _, _ = await build(coverage=gapped)
    result = await usecase.run(request(config, min_completeness=0.4))
    assert result.cycles == 10


async def test_counts_rejected_orders():
    # A backtest whose orders were mostly rejected is not the strategy anyone
    # thinks they tested.
    from tarakdingdung.domain.models.algorithm import RejectedIntent, RejectionReason, Side, TradeIntent
    intent = TradeIntent(symbol=BTC, side=Side.BUY, quantity=Decimal("1"),
                         reference_price=Decimal("100"))
    rejected = (RejectedIntent(intent=intent, reason=RejectionReason.BELOW_MIN_NOTIONAL),)
    usecase, config, _, _ = await build(cycle_plan=plan(orders=(), rejected=rejected))
    result = await usecase.run(request(config))
    assert result.rejected_orders == 10


async def test_persists_a_run_by_default():
    usecase, config, backtests, _ = await build()
    result = await usecase.run(request(config))
    assert result.run_id is not None
    assert await backtests.read_run_by_id(result.run_id) is not None


async def test_a_trial_run_persists_nothing():
    usecase, config, backtests, _ = await build()
    result = await usecase.run(request(config, persist=False))
    assert result.run_id is None
    assert backtests.runs == {}


async def test_returns_a_series_the_overfitting_test_can_consume():
    usecase, config, _, _ = await build()
    result = await usecase.run(request(config))
    assert len(result.returns) == result.cycles


async def test_trading_moves_equity_and_pays_fees():
    usecase, config, _, _ = await build(cycle_plan=plan(orders=(order(),)))
    result = await usecase.run(request(config))
    assert result.report.trade_count > 0
    assert result.report.cost_drag != 0.0


async def test_a_missing_strategy_raises():
    usecase, _, _, _ = await build()
    with pytest.raises(DomainError) as e:
        await usecase.run(RunBacktestRequest(
            strategy_id=uuid.uuid4(), window=WINDOW, initial_equity=Decimal("1")))
    assert e.value.type is ErrorType.NOT_FOUND


async def test_an_unknown_interval_raises_rather_than_defaulting():
    usecase, config, _, _ = await build()
    with pytest.raises(DomainError) as e:
        await usecase.run(request(config, interval="1fortnight"))
    assert e.value.type is ErrorType.BAD_ARGS


async def test_lists_runs():
    usecase, config, _, _ = await build()
    await usecase.run(request(config))
    result = await usecase.read_by_pagination(ListBacktestsRequest(page=1, limit=10))
    assert result.total == 1


# --- validation -------------------------------------------------------------

class StubBacktesting:
    def __init__(self, series) -> None:
        self.series = series
        self.calls = []

    async def run(self, request):
        from tarakdingdung.domain.models.performance import PerformanceReport
        self.calls.append(request)
        index = len(self.calls) - 1
        return type("R", (), {
            "run_id": None,
            "report": PerformanceReport(0, 0, 0, 0, 0, 0, 0, 0, 0),
            "cycles": 0, "rejected_orders": 0,
            "returns": self.series[index % len(self.series)]})()

    async def read_by_id(self, id): ...
    async def read_by_pagination(self, request): ...


def validation(series, *, threshold=0.10):
    backtests = FakeBacktestRepository()
    stub = StubBacktesting(series)
    usecase = StrategyValidationUsecase(
        backtesting=stub, backtests=backtests,
        overfitting=CombinatorialOverfittingTest(subsets=4, threshold=threshold),
        logger=NullLogger())
    return usecase, stub, backtests


def wf_request(grid):
    return RunWalkForwardRequest(strategy_id=uuid.uuid4(), window=WINDOW,
                                 parameter_grid=grid, initial_equity=Decimal("10000"))


async def test_runs_one_backtest_per_grid_entry():
    usecase, stub, _ = validation([tuple([0.01] * 40), tuple([0.02] * 40)])
    await usecase.run_walk_forward(wf_request(({"n": 1}, {"n": 2}, {"n": 3})))
    assert len(stub.calls) == 3


async def test_trials_are_run_without_persisting():
    # The search is the artefact, not its individual runs.
    usecase, stub, backtests = validation([tuple([0.01] * 40)])
    await usecase.run_walk_forward(wf_request(({"n": 1}, {"n": 2})))
    assert all(call.persist is False for call in stub.calls)
    assert backtests.runs == {}


async def test_each_trial_gets_its_parameters():
    usecase, stub, _ = validation([tuple([0.01] * 40)])
    await usecase.run_walk_forward(wf_request(({"n": 1}, {"n": 2})))
    assert [c.parameters_override for c in stub.calls] == [{"n": 1}, {"n": 2}]


async def test_a_grid_of_one_is_refused():
    # With nothing to rank against, the gate has no meaning.
    usecase, _, _ = validation([tuple([0.01] * 40)])
    with pytest.raises(DomainError) as e:
        await usecase.run_walk_forward(wf_request(({"n": 1},)))
    assert e.value.type is ErrorType.BAD_ARGS


async def test_persists_the_whole_search():
    usecase, _, backtests = validation([tuple([0.01] * 40)])
    result = await usecase.run_walk_forward(wf_request(({"n": 1}, {"n": 2})))
    stored = await backtests.read_validation_by_id(result.validation_id)
    assert len(stored.trials) == 2


async def test_no_winner_is_offered_when_the_gate_fails():
    # Naming a winner beside "this search learned the noise" invites exactly
    # the use the test exists to prevent.
    usecase, _, _ = validation([tuple([0.01] * 40)], threshold=0.0)
    result = await usecase.run_walk_forward(wf_request(({"n": 1}, {"n": 2})))
    assert result.overfitting.passed is False
    assert result.best_parameters is None


async def test_a_passing_search_names_its_winner():
    # One trial is genuinely better in every split, so the in-sample winner
    # keeps winning out-of-sample and the gate passes.
    usecase, _, _ = validation([tuple([0.02] * 40), tuple([-0.01] * 40)])
    result = await usecase.run_walk_forward(wf_request(({"n": 1}, {"n": 2})))
    assert result.overfitting.passed is True
    assert result.best_parameters == {"n": 1}


async def test_reading_a_missing_validation_raises():
    usecase, _, _ = validation([tuple([0.01] * 40)])
    with pytest.raises(DomainError) as e:
        await usecase.read_by_id(uuid.uuid4())
    assert e.value.type is ErrorType.NOT_FOUND
