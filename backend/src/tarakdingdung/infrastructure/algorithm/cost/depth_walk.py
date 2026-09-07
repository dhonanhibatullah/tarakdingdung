from decimal import Decimal

from tarakdingdung.domain.contracts.algorithm.cost import CostModel
from tarakdingdung.domain.models.algorithm import CostEstimate, PlannedOrder
from tarakdingdung.domain.models.market import OrderBook
from tarakdingdung.infrastructure.algorithm.cost.book import facing_levels


class DepthWalkCostModel(CostModel):
    """Walks the book level by level and charges the real average price.

    This is the model a backtest has to pass to be believed. Slippage is the
    gap between the volume-weighted fill and the touch, which is precisely the
    cost a thin IDR book imposes and that a flat assumption hides.

    An order deeper than the book returns ``fillable=False`` with the cost of
    the part that would fill, so the caller sees both that it is impossible
    and how expensive the reachable portion was.
    """

    def __init__(self, *, fee_rate: Decimal) -> None:
        self._fee_rate = fee_rate

    def estimate(self, order: PlannedOrder, book: OrderBook) -> CostEstimate:
        levels = facing_levels(order, book)
        if not levels:
            return CostEstimate(fee=Decimal(0), slippage=Decimal(0),
                                total=Decimal(0), fillable=False)

        touch = levels[0].price
        remaining = order.quantity
        spent = Decimal(0)
        filled = Decimal(0)
        for level in levels:
            if remaining <= 0:
                break
            take = min(remaining, level.quantity)
            spent += take * level.price
            filled += take
            remaining -= take

        fee = spent * self._fee_rate
        slippage = abs(spent - filled * touch)
        return CostEstimate(fee=fee, slippage=slippage, total=fee + slippage,
                            fillable=remaining <= 0)
