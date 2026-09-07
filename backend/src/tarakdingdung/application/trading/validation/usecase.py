from uuid import UUID

from tarakdingdung.domain.contracts.algorithm.validation import OverfittingTest
from tarakdingdung.domain.contracts.logger.leveled import LeveledLogger
from tarakdingdung.domain.contracts.repository.backtest import BacktestRepository
from tarakdingdung.domain.models.backtest import ValidationRun
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.performance import TrialResult
from tarakdingdung.domain.usecases.trading.backtest import Backtesting, RunBacktestRequest
from tarakdingdung.domain.usecases.trading.validation import (
    RunWalkForwardRequest, RunWalkForwardResult, StrategyValidation,
)


class StrategyValidationUsecase(StrategyValidation):
    """Runs the parameter search and puts the result through the gate.

    Depends on ``Backtesting`` as a contract, not as an implementation: a
    validation *is* repeated backtests, and reimplementing the replay here
    would create the second code path the whole design exists to avoid.

    Trials are not persisted individually. What gets stored is the search — all
    trials plus the verdict — because the overfitting probability is only
    interpretable alongside the number of candidates that produced it.
    """

    _TAG = "trading/validation"

    def __init__(self, *, backtesting: Backtesting, backtests: BacktestRepository,
                 overfitting: OverfittingTest, logger: LeveledLogger) -> None:
        self._backtesting = backtesting
        self._backtests = backtests
        self._overfitting = overfitting
        self._logger = logger

    async def run_walk_forward(self, request: RunWalkForwardRequest) -> RunWalkForwardResult:
        if len(request.parameter_grid) < 2:
            err = DomainError(
                "a parameter search needs at least two candidates to rank",
                ErrorType.BAD_ARGS)
            await self._logger.error(f"{self._TAG}/RunWalkForward", "grid too small",
                                     {"err": err, "strategy_id": request.strategy_id})
            raise err

        trials = tuple([await self._trial(request, index, parameters)
                        for index, parameters in enumerate(request.parameter_grid)])
        report = self._overfitting.evaluate(trials)

        validation_id = await self._backtests.create_validation(
            strategy_id=request.strategy_id, window=request.window, trials=trials,
            overfitting=report, created_by=request.created_by)

        if not report.passed:
            await self._logger.warn(
                f"{self._TAG}/RunWalkForward", "search failed the overfitting gate",
                {"strategy_id": request.strategy_id, "probability": report.probability})

        return RunWalkForwardResult(
            validation_id=validation_id, overfitting=report,
            # No winner is offered when the gate fails: naming one beside a
            # verdict of "this search learned the noise" invites exactly the
            # use the test exists to prevent.
            best_parameters=self._best(trials, request) if report.passed else None,
            trials=len(trials))

    async def read_by_id(self, id: UUID) -> ValidationRun:
        run = await self._backtests.read_validation_by_id(id)
        if run is None:
            err = DomainError("validation run not found", ErrorType.NOT_FOUND)
            await self._logger.error(f"{self._TAG}/ReadById", "failed to read validation",
                                     {"err": err, "validation_id": id})
            raise err
        return run

    async def _trial(self, request: RunWalkForwardRequest, index: int,
                     parameters: dict) -> TrialResult:
        result = await self._backtesting.run(RunBacktestRequest(
            strategy_id=request.strategy_id, window=request.window,
            initial_equity=request.initial_equity, interval=request.interval,
            parameters_override=parameters, created_by=request.created_by,
            # Individual trials are not stored: the search is the artefact.
            persist=False))
        return TrialResult(label=f"trial-{index}",
                           parameters={k: str(v) for k, v in parameters.items()},
                           returns=result.returns)

    def _best(self, trials: tuple[TrialResult, ...],
              request: RunWalkForwardRequest) -> dict | None:
        ranked = max(trials, key=lambda t: sum(t.returns), default=None)
        if ranked is None:
            return None
        return dict(request.parameter_grid[int(ranked.label.split("-")[1])])
