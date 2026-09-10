from decimal import Decimal

from tarakdingdung.infrastructure.algorithm.cost.flat_fee import FlatFee


def test_flat_fee_zero_notional():
    fee = FlatFee(Decimal("0.001"))
    assert fee.fee(Decimal("0")) == Decimal("0")
