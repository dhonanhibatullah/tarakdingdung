from collections.abc import Awaitable, Callable
from decimal import Decimal

from tarakdingdung.domain.contracts.algorithm.backtest import (
    FillSimResult,
    FillSimulator,
    RebalanceEvent,
)
from tarakdingdung.domain.contracts.algorithm.cost import CostModel
from tarakdingdung.domain.contracts.algorithm.rebalance import Rebalancer
from tarakdingdung.domain.models.decision import Weight
from tarakdingdung.domain.models.market import Candle
from tarakdingdung.domain.models.symbol import Symbol

WeightFn = Callable[[dict[str, list[Candle]], int], Awaitable[list[Weight]]]


def price_at(candles: list[Candle], as_of_ms: int) -> Decimal | None:
    best: Candle | None = None
    for candle in candles:
        if candle.open_time_ms <= as_of_ms:
            best = candle
        else:
            break
    return best.close if best is not None else None


async def run(
    rebalancer: Rebalancer,
    simulator: FillSimulator,
    cost_model: CostModel,
    initial_equity: Decimal,
    symbols: list[Symbol],
    candles_by_symbol: dict[str, list[Candle]],
    timestamps: list[int],
    weight_fn: WeightFn,
) -> FillSimResult:
    events: list[RebalanceEvent] = []
    for ts in timestamps:
        prices: dict[str, Decimal] = {}
        for symbol in symbols:
            price = price_at(candles_by_symbol.get(symbol.id, []), ts)
            if price is not None:
                prices[symbol.id] = price
        weights = await weight_fn(candles_by_symbol, ts)
        events.append(RebalanceEvent(timestamp_ms=ts, target=weights, prices=prices))
    return simulator.simulate(events, rebalancer, cost_model, initial_equity)
