from collections.abc import Callable, Mapping

from tarakdingdung.domain.contracts.algorithm.cycle import CyclePlanner
from tarakdingdung.domain.contracts.execution.executor import Executor
from tarakdingdung.domain.contracts.logger.leveled import LeveledLogger
from tarakdingdung.domain.contracts.repository.market_data import MarketDataRepository
from tarakdingdung.domain.contracts.repository.order_journal import OrderJournalRepository
from tarakdingdung.domain.contracts.repository.portfolio import PortfolioRepository
from tarakdingdung.domain.contracts.repository.strategy import StrategyRepository
from tarakdingdung.domain.contracts.utility.clock import Clock
from tarakdingdung.domain.contracts.utility.single_flight import SingleFlight
from tarakdingdung.domain.models.algorithm import CyclePlan
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.execution import ExecutionResult, OrderState
from tarakdingdung.domain.models.strategy import StrategyConfig, TradingMode
from tarakdingdung.domain.usecases.trading.engine import (
    CycleDecision, RunCycleRequest, RunCycleResult, TradingEngine,
)
from tarakdingdung.domain.usecases.trading.history import (
    MarketDataHistory, ReadSnapshotRequest,
)

PlannerFactory = Callable[[StrategyConfig, dict], CyclePlanner]


class TradingEngineUsecase(TradingEngine):
    """One decide-and-act pass.

    The ordering here is the safety design, not an implementation detail:

    - unreconciled orders from a previous cycle are resolved *first*, before
      anything new is planned, so the portfolio a decision is sized against is
      not missing orders we already placed;
    - planned orders are written before submission, so a crash mid-submit
      leaves a record rather than untracked orders at the venue;
    - a submission that fails in transport is left unconfirmed and never
      retried, because the order may already exist;
    - a halt cancels resting orders and still submits the exits the planner
      produced, because de-risking means reducing exposure rather than merely
      declining to add to it.
    """

    _TAG = "trading/engine"
    _SNAPSHOT_LOOKBACK = 300

    def __init__(self, *, strategies: StrategyRepository, history: MarketDataHistory,
                 market_data: MarketDataRepository, portfolios: PortfolioRepository,
                 journal: OrderJournalRepository,
                 executors: Mapping[TradingMode, Executor],
                 planner_factory: PlannerFactory, lock: SingleFlight, clock: Clock,
                 logger: LeveledLogger, interval: str = "1h",
                 max_age_ms: int = 7_200_000) -> None:
        self._strategies = strategies
        self._history = history
        self._market_data = market_data
        self._portfolios = portfolios
        self._journal = journal
        self._executors = executors
        self._planner_factory = planner_factory
        self._lock = lock
        self._clock = clock
        self._logger = logger
        self._interval = interval
        self._max_age_ms = max_age_ms

    async def run_cycle(self, request: RunCycleRequest) -> RunCycleResult:
        config = await self._config(request)
        now = await self._clock.now_ms()

        if not config.is_enabled:
            return RunCycleResult(timestamp=now, strategy_id=config.id,
                                  decision=CycleDecision.DISABLED)

        key = f"cycle:{config.id}"
        if not await self._lock.acquire(key):
            # Skipped rather than queued: by the time a waiting cycle ran, its
            # snapshot would be stale anyway.
            await self._logger.warn(f"{self._TAG}/RunCycle", "cycle already running",
                                    {"strategy_id": config.id})
            return RunCycleResult(timestamp=now, strategy_id=config.id,
                                  decision=CycleDecision.SKIPPED)
        try:
            return await self._cycle(config, request, now)
        finally:
            await self._lock.release(key)

    async def _cycle(self, config: StrategyConfig, request: RunCycleRequest,
                     now: int) -> RunCycleResult:
        executor = self._executor(config)
        reconciled = await self._reconcile(config, executor)

        snapshot = await self._history.read_snapshot(ReadSnapshotRequest(
            symbols=config.universe, as_of=now, interval=self._interval,
            lookback=self._SNAPSHOT_LOOKBACK, max_age_ms=self._max_age_ms))
        portfolio = await self._portfolios.read_latest(as_of=now)
        if not snapshot.last_prices or portfolio is None:
            await self._logger.warn(f"{self._TAG}/RunCycle", "no usable market data",
                                    {"strategy_id": config.id, "as_of": now})
            return RunCycleResult(timestamp=now, strategy_id=config.id,
                                  decision=CycleDecision.NO_DATA, reconciled=reconciled)

        plan = self._planner_factory(config, config.parameters).plan(
            strategy_id=config.id, snapshot=snapshot, portfolio=portfolio,
            state=await self._portfolios.read_risk_state(as_of=now),
            rules=await self._market_data.read_rules(symbols=config.universe))

        if plan.is_halted:
            await self._halt(config, executor, plan)

        if request.dry_run:
            return self._result(config, plan, CycleDecision.DRY_RUN, reconciled)
        if not plan.orders.orders:
            decision = CycleDecision.HALTED if plan.is_halted else CycleDecision.NO_DRIFT
            return self._result(config, plan, decision, reconciled)

        execution = await self._submit(config, executor, plan)
        decision = CycleDecision.HALTED if plan.is_halted else CycleDecision.TRADED
        return self._result(config, plan, decision, reconciled, execution)

    async def _submit(self, config: StrategyConfig, executor: Executor,
                      plan: CyclePlan) -> ExecutionResult:
        # Write-ahead: the record must exist before the orders can. A process
        # that dies on the next line leaves something to reconcile from.
        await self._journal.write_planned(
            strategy_id=config.id, timestamp=plan.timestamp, orders=plan.orders.orders)

        execution = await executor.submit(plan.orders.orders)

        await self._journal.write_execution(
            strategy_id=config.id, timestamp=plan.timestamp, result=execution)
        await self._record_states(execution)
        await self._portfolios.append_fills(execution.fills)

        if not execution.is_complete:
            await self._logger.error(
                f"{self._TAG}/RunCycle", "submission left unconfirmed orders",
                {"strategy_id": config.id, "count": len(execution.unconfirmed)})
        return execution

    async def _record_states(self, execution: ExecutionResult) -> None:
        for ack in execution.accepted:
            await self._journal.set_state(client_order_id=ack.client_order_id,
                                          state=OrderState.ACCEPTED,
                                          venue_order_id=ack.venue_order_id, reason=None)
        for rejection in execution.rejected:
            await self._journal.set_state(client_order_id=rejection.client_order_id,
                                          state=OrderState.REJECTED,
                                          venue_order_id=None, reason=rejection.reason)
        for pending in execution.unconfirmed:
            await self._journal.set_state(client_order_id=pending.client_order_id,
                                          state=OrderState.UNCONFIRMED,
                                          venue_order_id=None, reason=pending.reason)

    async def _reconcile(self, config: StrategyConfig, executor: Executor) -> int:
        """Resolve orders we submitted but never confirmed.

        Queried by client order id, never resubmitted: the order may already be
        working, and a blind retry is how one intended position becomes two.
        """
        pending = await self._journal.read_unreconciled(strategy_id=config.id)
        resolved = 0
        for order in pending:
            if order.client_order_id is None:
                continue
            try:
                found = await executor.read_by_client_order_id(order.client_order_id)
            except DomainError as err:
                await self._logger.warn(f"{self._TAG}/Reconcile", "failed to reconcile order",
                                        {"err": err, "client_order_id": order.client_order_id})
                continue
            await self._record_states(found)
            await self._portfolios.append_fills(found.fills)
            resolved += 1
        return resolved

    async def _halt(self, config: StrategyConfig, executor: Executor,
                    plan: CyclePlan) -> None:
        """Pull resting orders, and make a failure to do so louder, not quieter.

        A halt whose cancellation failed has left live orders working with no
        supervision, so the flag persists and every later cycle re-attempts it.
        """
        try:
            await executor.cancel_all(config.universe)
        except DomainError as err:
            await self._logger.error(f"{self._TAG}/Halt", "failed to cancel resting orders",
                                     {"err": err, "strategy_id": config.id,
                                      "halted_by": plan.halted_by})
            await self._portfolios.set_halt(strategy_id=config.id, halted=True,
                                            reason=f"cancel failed: {err.message}")
            return
        await self._portfolios.set_halt(strategy_id=config.id, halted=False, reason=None)
        await self._logger.warn(f"{self._TAG}/Halt", "risk rule halted the strategy",
                                {"strategy_id": config.id, "halted_by": plan.halted_by})

    async def _config(self, request: RunCycleRequest) -> StrategyConfig:
        config = await self._strategies.read_by_id(request.strategy_id)
        if config is None:
            err = DomainError("strategy not found", ErrorType.NOT_FOUND)
            await self._logger.error(f"{self._TAG}/RunCycle", "failed to read strategy",
                                     {"err": err, "strategy_id": request.strategy_id})
            raise err
        return config

    def _executor(self, config: StrategyConfig) -> Executor:
        executor = self._executors.get(config.mode)
        if executor is None:
            raise DomainError(f"no executor configured for mode {config.mode}",
                              ErrorType.BAD_STATE)
        return executor

    def _result(self, config: StrategyConfig, plan: CyclePlan,
                decision: CycleDecision, reconciled: int,
                execution: ExecutionResult | None = None) -> RunCycleResult:
        return RunCycleResult(timestamp=plan.timestamp, strategy_id=config.id,
                              decision=decision, weights=plan.weights,
                              plan=plan.orders, execution=execution,
                              halted_by=plan.halted_by, reconciled=reconciled)
