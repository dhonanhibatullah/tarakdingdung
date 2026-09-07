from tarakdingdung.domain.contracts.logger.leveled import LeveledLogger
from tarakdingdung.domain.contracts.repository.strategy import StrategyRepository
from tarakdingdung.domain.models.error import DomainError
from tarakdingdung.domain.usecases.trading.engine import (
    CycleDecision, RunCycleRequest, TradingEngine,
)

TAG = "cron/engine"

# Outcomes that are ordinary operation rather than something to look into.
_ROUTINE = {CycleDecision.TRADED, CycleDecision.NO_DRIFT, CycleDecision.DISABLED}


async def run_cycles(*, engine: TradingEngine, strategies: StrategyRepository,
                     logger: LeveledLogger) -> None:
    """Step every enabled strategy once.

    Each strategy is isolated: one failing must not stop the others, because a
    single misconfigured strategy would otherwise silently halt trading for
    every other one.
    """
    for config in await strategies.read_enabled():
        try:
            result = await engine.run_cycle(RunCycleRequest(strategy_id=config.id))
        except DomainError as err:
            await logger.error(TAG, "cycle failed",
                               {"err": err, "strategy_id": config.id,
                                "strategy": config.name})
            continue

        level = logger.info if result.decision in _ROUTINE else logger.warn
        await level(TAG, f"cycle finished: {result.decision}", {
            "strategy_id": config.id, "strategy": config.name,
            "decision": str(result.decision), "halted_by": result.halted_by,
            "reconciled": result.reconciled,
            "orders": len(result.plan.orders) if result.plan else 0})
