from decimal import Decimal

from tarakdingdung.application.trading.backtest.historical import run
from tarakdingdung.domain.models.decision import Weight
from tarakdingdung.domain.models.market import Candle
from tarakdingdung.domain.models.symbol import Symbol
from tarakdingdung.infrastructure.algorithm.backtest.fill_sim import SimpleFillSimulator
from tarakdingdung.infrastructure.algorithm.cost.flat_fee import FlatFee
from tarakdingdung.infrastructure.algorithm.metric.standard import StandardMetric
from tarakdingdung.infrastructure.algorithm.rebalance.no_trade_band import NoTradeBandRebalancer


async def _equal_weight_fn(candles, as_of_ms):
    return [Weight(symbol_id="s1", weight=0.5)]


def _candle(ts, close):
    return Candle(
        symbol_id="s1",
        open_time_ms=ts,
        open=Decimal(str(close)),
        high=Decimal(str(close)),
        low=Decimal(str(close)),
        close=Decimal(str(close)),
        volume=Decimal("1"),
    )


async def test_historical_backtest_produces_equity_curve():
    symbols = [Symbol(id="s1", venue="indodax", base="BTC", quote="IDR", external="BTCIDR")]
    candles = {"s1": [_candle(0, 10), _candle(1000, 20)]}

    result = await run(
        NoTradeBandRebalancer(band=0.01, min_notional=Decimal("1")),
        SimpleFillSimulator(StandardMetric()),
        FlatFee(Decimal("0.001")),
        Decimal("1000"),
        symbols,
        candles,
        timestamps=[0, 1000],
        weight_fn=_equal_weight_fn,
    )

    assert len(result.equity_curve) == 2
    assert len(result.fills) == 2
    assert result.equity_curve[1] > result.equity_curve[0]
