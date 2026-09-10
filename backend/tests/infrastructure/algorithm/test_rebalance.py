from decimal import Decimal

from tarakdingdung.domain.models.decision import Weight
from tarakdingdung.domain.models.order import OrderSide
from tarakdingdung.infrastructure.algorithm.cost.flat_fee import FlatFee
from tarakdingdung.infrastructure.algorithm.rebalance.identifiers import client_order_id
from tarakdingdung.infrastructure.algorithm.rebalance.no_trade_band import (
    NoTradeBandRebalancer,
)


def test_flat_fee():
    fee = FlatFee(Decimal("0.001"))
    assert fee.fee(Decimal("1000")) == Decimal("1.000")


def test_rebalancer_buys_when_underweight():
    rb = NoTradeBandRebalancer(band=0.01, min_notional=Decimal("1"))
    plan = rb.rebalance(
        current={},
        target=[Weight("btc", 0.5)],
        prices={"btc": Decimal("10")},
        equity=Decimal("1000"),
    )
    assert len(plan.orders) == 1
    order = plan.orders[0]
    assert order.symbol_id == "btc"
    assert order.side is OrderSide.BUY
    assert order.notional == Decimal("500")
    assert order.quantity == Decimal("50")


def test_rebalancer_sells_when_overweight():
    rb = NoTradeBandRebalancer(band=0.01, min_notional=Decimal("1"))
    plan = rb.rebalance(
        current={"btc": Decimal("800")},
        target=[Weight("btc", 0.3)],
        prices={"btc": Decimal("10")},
        equity=Decimal("1000"),
    )
    assert plan.orders[0].side is OrderSide.SELL
    assert plan.orders[0].notional == Decimal("500")


def test_no_trade_band_suppresses_small_deltas():
    rb = NoTradeBandRebalancer(band=0.05, min_notional=Decimal("1"))
    plan = rb.rebalance(
        current={"btc": Decimal("490")},
        target=[Weight("btc", 0.5)],
        prices={"btc": Decimal("10")},
        equity=Decimal("1000"),
    )
    assert plan.orders == []


def test_rebalancer_rejects_below_min_notional():
    rb = NoTradeBandRebalancer(band=0.0, min_notional=Decimal("100"))
    plan = rb.rebalance(
        current={},
        target=[Weight("btc", 0.01)],
        prices={"btc": Decimal("10")},
        equity=Decimal("1000"),
    )
    assert plan.orders == []
    assert len(plan.rejected) == 1
    assert plan.rejected[0].reason == "below min notional"


def test_rebalancer_rejects_missing_price():
    rb = NoTradeBandRebalancer(band=0.0, min_notional=Decimal("1"))
    plan = rb.rebalance(
        current={},
        target=[Weight("btc", 0.5)],
        prices={},
        equity=Decimal("1000"),
    )
    assert plan.orders == []
    assert plan.rejected[0].reason == "no price"


def test_client_order_id_is_deterministic():
    a = client_order_id("u1", 1000, "btc", "buy")
    b = client_order_id("u1", 1000, "btc", "buy")
    c = client_order_id("u1", 1000, "btc", "sell")
    assert a == b
    assert a != c
