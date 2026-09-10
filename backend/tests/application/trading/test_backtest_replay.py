from decimal import Decimal

from tarakdingdung.application.trading.backtest.usecase import BacktestUsecase
from tarakdingdung.domain.models.decision import Decision, Weight
from tarakdingdung.domain.models.market import Candle
from tarakdingdung.infrastructure.algorithm.backtest.fill_sim import SimpleFillSimulator
from tarakdingdung.infrastructure.algorithm.cost.flat_fee import FlatFee
from tarakdingdung.infrastructure.algorithm.metric.standard import StandardMetric
from tarakdingdung.infrastructure.algorithm.rebalance.no_trade_band import NoTradeBandRebalancer
from tests.fakes.trading import (
    InMemoryBacktestRepository,
    InMemoryDecisionRepository,
    InMemoryMarketDataRepository,
)


async def test_replay_produces_result():
    decisions = InMemoryDecisionRepository()
    await decisions.create(
        Decision(
            id="",
            universe_id="u1",
            as_of_ms=1000,
            weights=[Weight("s1", 0.5)],
            reasoning="",
            confidence=0.5,
            traces={},
            prompt="",
            raw_response="",
            status="valid",
        )
    )

    market_data = InMemoryMarketDataRepository()
    market_data.candles.append(
        Candle(
            symbol_id="s1",
            open_time_ms=900,
            open=Decimal("10"),
            high=Decimal("10"),
            low=Decimal("10"),
            close=Decimal("10"),
            volume=Decimal("1"),
        )
    )

    backtests = InMemoryBacktestRepository()
    usecase = BacktestUsecase(
        decisions,
        market_data,
        backtests,
        NoTradeBandRebalancer(band=0.01, min_notional=Decimal("1")),
        SimpleFillSimulator(StandardMetric()),
        FlatFee(Decimal("0.001")),
        Decimal("1000"),
    )

    result = await usecase.replay("u1", 0, 2000)

    assert result.id
    assert len(result.equity_curve) == 1
    assert len(backtests.items) == 1
