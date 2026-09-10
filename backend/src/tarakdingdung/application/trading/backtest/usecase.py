from decimal import Decimal

from tarakdingdung.domain.contracts.algorithm.backtest import (
    FillSimulator,
    RebalanceEvent,
)
from tarakdingdung.domain.contracts.algorithm.cost import CostModel
from tarakdingdung.domain.contracts.algorithm.rebalance import Rebalancer
from tarakdingdung.domain.contracts.repository.backtest import BacktestRepository
from tarakdingdung.domain.contracts.repository.decision import DecisionRepository
from tarakdingdung.domain.contracts.repository.market_data import MarketDataRepository
from tarakdingdung.domain.models.backtest import BacktestResult
from tarakdingdung.domain.usecases.trading.backtest import Backtest


class BacktestUsecase(Backtest):
    def __init__(
        self,
        decisions: DecisionRepository,
        market_data: MarketDataRepository,
        backtests: BacktestRepository,
        rebalancer: Rebalancer,
        simulator: FillSimulator,
        cost_model: CostModel,
        initial_equity: Decimal,
        lookback_ms: int = 86_400_000,
    ) -> None:
        self._decisions = decisions
        self._market_data = market_data
        self._backtests = backtests
        self._rebalancer = rebalancer
        self._simulator = simulator
        self._cost_model = cost_model
        self._initial_equity = initial_equity
        self._lookback_ms = lookback_ms

    async def replay(
        self, universe_id: str, from_ms: int, to_ms: int
    ) -> BacktestResult:
        recorded = await self._decisions.read_range(universe_id, from_ms, to_ms)
        events: list[RebalanceEvent] = []
        for decision in recorded:
            prices: dict[str, Decimal] = {}
            for weight in decision.weights:
                candles = await self._market_data.read_range(
                    weight.symbol_id,
                    decision.as_of_ms - self._lookback_ms,
                    decision.as_of_ms,
                )
                if candles:
                    prices[weight.symbol_id] = candles[-1].close
            events.append(
                RebalanceEvent(
                    timestamp_ms=decision.as_of_ms,
                    target=decision.weights,
                    prices=prices,
                )
            )

        result = self._simulator.simulate(
            events, self._rebalancer, self._cost_model, self._initial_equity
        )
        return await self._backtests.create(
            BacktestResult(
                id="",
                universe_id=universe_id,
                from_ms=from_ms,
                to_ms=to_ms,
                equity_curve=result.equity_curve,
                sharpe=result.sharpe,
                max_drawdown=result.max_drawdown,
                turnover=result.turnover,
            )
        )
