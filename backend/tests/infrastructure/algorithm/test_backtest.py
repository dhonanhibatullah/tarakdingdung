from decimal import Decimal

from tarakdingdung.domain.contracts.algorithm.backtest import RebalanceEvent
from tarakdingdung.domain.models.decision import Weight
from tarakdingdung.infrastructure.algorithm.backtest.fill_sim import SimpleFillSimulator
from tarakdingdung.infrastructure.algorithm.cost.flat_fee import FlatFee
from tarakdingdung.infrastructure.algorithm.metric.standard import StandardMetric
from tarakdingdung.infrastructure.algorithm.rebalance.no_trade_band import (
    NoTradeBandRebalancer,
)


def _simulator():
    return SimpleFillSimulator(StandardMetric())


def test_buy_then_sell_equity_curve():
    rb = NoTradeBandRebalancer(band=0.01, min_notional=Decimal("1"))
    fee = FlatFee(Decimal("0.001"))
    events = [
        RebalanceEvent(
            timestamp_ms=0,
            target=[Weight("btc", 0.5)],
            prices={"btc": Decimal("10")},
        ),
        RebalanceEvent(
            timestamp_ms=1,
            target=[],
            prices={"btc": Decimal("20")},
        ),
    ]
    result = _simulator().simulate(events, rb, fee, Decimal("1000"))
    assert result.equity_curve == [Decimal("999.5"), Decimal("1498.5")]
    assert len(result.fills) == 2
    assert result.turnover == 1500.0
    assert result.max_drawdown == 0.0


def test_no_events_returns_empty_curve():
    rb = NoTradeBandRebalancer(band=0.01, min_notional=Decimal("1"))
    fee = FlatFee(Decimal("0.001"))
    result = _simulator().simulate([], rb, fee, Decimal("1000"))
    assert result.equity_curve == []
    assert result.fills == []
    assert result.sharpe == 0.0
