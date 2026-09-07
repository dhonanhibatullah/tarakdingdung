from decimal import Decimal

from tarakdingdung.domain.models.algorithm import Side
from tarakdingdung.infrastructure.algorithm.cost.depth_walk import DepthWalkCostModel
from tarakdingdung.infrastructure.algorithm.cost.flat_fee import FlatFeeCostModel
from tests.infrastructure.algorithm.conformance import BTC_IDX, book
from tests.infrastructure.algorithm.fixtures import buy, level, order_book


def test_flat_fee_is_proportional_to_notional():
    estimate = FlatFeeCostModel(fee_rate=Decimal("0.002")).estimate(
        buy("2"), book(BTC_IDX))
    # Best ask is 101.
    assert estimate.fee == Decimal("2") * Decimal("101") * Decimal("0.002")


def test_flat_fee_adds_its_slippage_assumption():
    estimate = FlatFeeCostModel(fee_rate=Decimal("0"),
                                slippage_rate=Decimal("0.01")).estimate(
        buy("1"), book(BTC_IDX))
    assert estimate.slippage == Decimal("101") * Decimal("0.01")
    assert estimate.total == estimate.fee + estimate.slippage


def test_depth_walk_charges_nothing_extra_at_the_touch():
    model = DepthWalkCostModel(fee_rate=Decimal("0"))
    assert model.estimate(buy("1"), book(BTC_IDX, levels=5, size="1")).slippage == 0


def test_depth_walk_charges_for_eating_the_book():
    model = DepthWalkCostModel(fee_rate=Decimal("0"))
    deep = model.estimate(buy("4"), book(BTC_IDX, levels=5, size="1"))
    assert deep.slippage > 0


def test_depth_walk_uses_the_side_the_order_consumes():
    # A buy lifts asks; a sell hits bids. Reading the wrong side would turn a
    # cost into a credit.
    lopsided = order_book(BTC_IDX,
                          bids=[level("90", "10")], asks=[level("110", "10")])
    model = DepthWalkCostModel(fee_rate=Decimal("0.001"))
    assert model.estimate(buy("1"), lopsided).fee == Decimal("110") * Decimal("0.001")


def test_depth_walk_reports_an_unfillable_order_with_partial_cost():
    estimate = DepthWalkCostModel(fee_rate=Decimal("0.001")).estimate(
        buy("1000"), book(BTC_IDX, levels=2, size="1"))
    assert estimate.fillable is False
    assert estimate.total > 0


def test_an_empty_book_is_never_fillable():
    empty = order_book(BTC_IDX)
    for model in (FlatFeeCostModel(fee_rate=Decimal("0.002")),
                  DepthWalkCostModel(fee_rate=Decimal("0.002"))):
        assert model.estimate(buy("1"), empty).fillable is False


def test_sell_side_walks_the_bids():
    from tarakdingdung.domain.models.algorithm import OrderType, PlannedOrder, TimeInForce
    sell = PlannedOrder(symbol=BTC_IDX, side=Side.SELL, type=OrderType.LIMIT,
                        quantity=Decimal("2"), price=Decimal("100"),
                        time_in_force=TimeInForce.GTC)
    lopsided = order_book(BTC_IDX, bids=[level("90", "1"), level("80", "1")],
                          asks=[level("110", "10")])
    estimate = DepthWalkCostModel(fee_rate=Decimal("0")).estimate(sell, lopsided)
    # Filled at 90 and 80 against a 90 touch: 10 of slippage.
    assert estimate.slippage == Decimal("10")
