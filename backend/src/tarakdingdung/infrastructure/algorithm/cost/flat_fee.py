from decimal import Decimal

from tarakdingdung.domain.contracts.algorithm.cost import CostModel
from tarakdingdung.domain.models.algorithm import CostEstimate, PlannedOrder
from tarakdingdung.domain.models.market import OrderBook
from tarakdingdung.infrastructure.algorithm.cost.book import facing_levels, touch_price


class FlatFeeCostModel(CostModel):
    """A fixed fee plus a fixed slippage assumption.

    The smoke-test model. It is fast and wrong in a known direction, which
    makes it useful for checking that a pipeline runs and useless for deciding
    whether a strategy is real.
    """

    def __init__(self, *, fee_rate: Decimal,
                 slippage_rate: Decimal = Decimal(0)) -> None:
        self._fee_rate = fee_rate
        self._slippage_rate = slippage_rate

    def estimate(self, order: PlannedOrder, book: OrderBook) -> CostEstimate:
        levels = facing_levels(order, book)
        price = touch_price(order, levels)
        if price is None:
            return CostEstimate(fee=Decimal(0), slippage=Decimal(0),
                                total=Decimal(0), fillable=False)
        notional = order.quantity * price
        fee = notional * self._fee_rate
        slippage = notional * self._slippage_rate
        available = sum((lv.quantity for lv in levels), Decimal(0))
        return CostEstimate(fee=fee, slippage=slippage, total=fee + slippage,
                            fillable=available >= order.quantity)
