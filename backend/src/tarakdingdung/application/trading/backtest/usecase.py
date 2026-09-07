import math
from collections.abc import Callable
from decimal import Decimal
from uuid import UUID

from tarakdingdung.application.shared.intervals import interval_ms
from tarakdingdung.application.trading.backtest.replay import (
    DEFAULT_HALF_SPREAD, DEFAULT_LEVEL_STEP, DEFAULT_LEVELS, replay_snapshot,
)
from tarakdingdung.application.trading.backtest.simulation import equity_of, simulate
from tarakdingdung.domain.contracts.algorithm.cost import CostModel
from tarakdingdung.domain.contracts.algorithm.cycle import CyclePlanner
from tarakdingdung.domain.contracts.algorithm.metric import PerformanceEvaluator
from tarakdingdung.domain.contracts.logger.leveled import LeveledLogger
from tarakdingdung.domain.contracts.repository.backtest import BacktestRepository
from tarakdingdung.domain.contracts.repository.market_data import MarketDataRepository
from tarakdingdung.domain.contracts.repository.strategy import StrategyRepository
from tarakdingdung.domain.models.backtest import BacktestRun
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.market import Venue
from tarakdingdung.domain.models.performance import EquityPoint, Fill
from tarakdingdung.domain.models.portfolio import Portfolio, RiskState
from tarakdingdung.domain.models.strategy import StrategyConfig
from tarakdingdung.domain.usecases.trading.backtest import (
    Backtesting, ListBacktestsRequest, ListBacktestsResult, RunBacktestRequest,
    RunBacktestResult,
)

PlannerFactory = Callable[[StrategyConfig, dict], CyclePlanner]

_VOLATILITY_WINDOW = 30
_DAY_MS = 86_400_000


class BacktestingUsecase(Backtesting):
    """Replays stored history through the same planner the live engine uses.

    Refuses rather than approximates. Coverage below the requested threshold
    raises, because a gap becomes an invented flat period and the report would
    describe a strategy that never traded.
    """

    _TAG = "trading/backtest"
    _SNAPSHOT_LOOKBACK = 300

    def __init__(self, *, strategies: StrategyRepository,
                 market_data: MarketDataRepository, backtests: BacktestRepository,
                 planner_factory: PlannerFactory, cost_model: CostModel,
                 evaluator: PerformanceEvaluator, logger: LeveledLogger,
                 replay_half_spread: Decimal = DEFAULT_HALF_SPREAD,
                 replay_book_levels: int = DEFAULT_LEVELS,
                 replay_level_step: Decimal = DEFAULT_LEVEL_STEP) -> None:
        self._strategies = strategies
        self._market_data = market_data
        self._backtests = backtests
        self._planner_factory = planner_factory
        self._cost_model = cost_model
        self._evaluator = evaluator
        self._logger = logger
        # Shape of the book each bar is expanded into (see backtest/replay.py).
        self._half_spread = replay_half_spread
        self._book_levels = replay_book_levels
        self._level_step = replay_level_step

    async def run(self, request: RunBacktestRequest) -> RunBacktestResult:
        config = await self._config(request.strategy_id)
        await self._require_coverage(config, request)

        planner = self._planner_factory(
            config, request.parameters_override or config.parameters)
        rules = await self._market_data.read_rules(symbols=config.universe)

        portfolio = self._seed(config, request.initial_equity)
        curve = [EquityPoint(timestamp=request.window.start, equity=portfolio.equity)]
        fills: list[Fill] = []
        cycles = rejected = 0

        for stamp in self._timeline(request):
            base = await self._market_data.read_replay_snapshot(
                symbols=config.universe, as_of=stamp, interval=request.interval,
                lookback=self._SNAPSHOT_LOOKBACK, max_age=interval_ms(request.interval) * 2)
            if not base.last_prices:
                continue

            snapshot = replay_snapshot(base, half_spread=self._half_spread,
                                       levels=self._book_levels,
                                       level_step=self._level_step)
            cycles += 1
            plan = planner.plan(strategy_id=config.id, snapshot=snapshot,
                                portfolio=portfolio, state=self._risk_state(curve, stamp),
                                rules=rules)
            rejected += len(plan.orders.rejected)

            outcome = simulate(orders=plan.orders.orders, snapshot=snapshot,
                               portfolio=portfolio, cost_model=self._cost_model)
            portfolio = outcome.portfolio
            fills.extend(outcome.fills)
            curve.append(EquityPoint(timestamp=stamp, equity=portfolio.equity))

        if cycles == 0:
            err = DomainError(
                "backtest produced no evaluable cycles: candle coverage passed "
                "the gate but no usable snapshot could be built over the window",
                ErrorType.VALIDATION)
            await self._logger.error(f"{self._TAG}/Run", "no evaluable cycles",
                                     {"err": err, "strategy_id": config.id,
                                      "window": (request.window.start, request.window.end)})
            raise err

        report = self._evaluator.evaluate(tuple(curve), tuple(fills))
        run_id = await self._persist(config, request, report) if request.persist else None
        return RunBacktestResult(run_id=run_id, report=report, cycles=cycles,
                                 rejected_orders=rejected,
                                 returns=self._returns(curve))

    async def read_by_id(self, id: UUID) -> BacktestRun:
        run = await self._backtests.read_run_by_id(id)
        if run is None:
            err = DomainError("backtest run not found", ErrorType.NOT_FOUND)
            await self._logger.error(f"{self._TAG}/ReadById", "failed to read run",
                                     {"err": err, "run_id": id})
            raise err
        return run

    async def read_by_pagination(self, request: ListBacktestsRequest) -> ListBacktestsResult:
        runs, total = await self._backtests.read_runs_by_pagination(
            page=request.page, limit=request.limit, strategy_id=request.strategy_id)
        return ListBacktestsResult(runs=tuple(runs), total=total)

    async def _config(self, strategy_id: UUID) -> StrategyConfig:
        config = await self._strategies.read_by_id(strategy_id)
        if config is None:
            err = DomainError("strategy not found", ErrorType.NOT_FOUND)
            await self._logger.error(f"{self._TAG}/Run", "failed to read strategy",
                                     {"err": err, "strategy_id": strategy_id})
            raise err
        return config

    async def _require_coverage(self, config: StrategyConfig,
                                request: RunBacktestRequest) -> None:
        for symbol in config.universe:
            coverage = await self._market_data.read_coverage(
                symbol=symbol, interval=request.interval, window=request.window)
            if coverage.completeness < request.min_completeness:
                err = DomainError(
                    f"insufficient history for {symbol.base}/{symbol.quote} on "
                    f"{symbol.venue}: {coverage.completeness:.1%} covered, "
                    f"{request.min_completeness:.1%} required",
                    ErrorType.VALIDATION)
                await self._logger.error(f"{self._TAG}/Run", "insufficient coverage",
                                         {"err": err, "symbol": str(symbol),
                                          "gaps": len(coverage.gaps)})
                raise err

    def _timeline(self, request: RunBacktestRequest) -> range:
        return range(request.window.start, request.window.end,
                     interval_ms(request.interval))

    def _seed(self, config: StrategyConfig, equity: Decimal) -> Portfolio:
        venues = {symbol.venue for symbol in config.universe} or {Venue.INDODAX}
        share = equity / len(venues)
        return Portfolio(timestamp=0, cash={v: share for v in venues},
                         positions={}, equity=equity)

    def _risk_state(self, curve: list[EquityPoint], stamp: int) -> RiskState:
        """Derived from the curve so far — never from anything after ``stamp``.

        Computed here rather than read from a repository because a replay's
        risk state is a function of the replay itself, not of live history.
        """
        equities = [float(point.equity) for point in curve]
        current = equities[-1]
        recent = [p for p in curve if p.timestamp >= stamp - _DAY_MS]
        opening = float(recent[0].equity) if recent else current
        return RiskState(
            timestamp=stamp,
            equity_peak=Decimal(str(max(equities))),
            daily_pnl=Decimal(str(current - opening)),
            realized_volatility=_volatility(equities),
            halted=False)

    def _returns(self, curve: list[EquityPoint]) -> tuple[float, ...]:
        return tuple(_returns_of([float(p.equity) for p in curve]))

    async def _persist(self, config: StrategyConfig, request: RunBacktestRequest,
                       report) -> UUID:
        return await self._backtests.create_run(
            strategy_id=config.id, window=request.window,
            initial_equity=request.initial_equity, report=report,
            created_by=request.created_by)


def _returns_of(equities: list[float]) -> list[float]:
    return [b / a - 1.0 for a, b in zip(equities, equities[1:]) if a > 0]


def _volatility(equities: list[float]) -> float:
    sample = _returns_of(equities)[-_VOLATILITY_WINDOW:]
    if len(sample) < 2:
        return 0.0
    mean = sum(sample) / len(sample)
    return math.sqrt(sum((value - mean) ** 2 for value in sample) / len(sample))
