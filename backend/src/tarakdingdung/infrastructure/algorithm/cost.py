from decimal import Decimal

from tarakdingdung.domain.contracts.algorithm.cost import CostModel
from tarakdingdung.domain.models.algorithm import CostEstimate, PlannedOrder, Side
from tarakdingdung.domain.models.market import BookLevel, OrderBook


def _levels(order: PlannedOrder, book: OrderBook) -> tuple[BookLevel, ...]:
    # A buy consumes the asks, a sell consumes the bids.
    return book.asks if order.side is Side.BUY else book.bids


def _reference(order: PlannedOrder, levels: tuple[BookLevel, ...]) -> Decimal | None:
    if levels:
        return levels[0].price
    return order.price


class FlatFeeCostModel(CostModel):
    """A fixed fee plus a fixed slippage assumption.

    The smoke-test model. It is fast and wrong in a known direction, which
    makes it useful for checking that a pipeline runs and useless for deciding
    whether a strategy is real.
    """

    def __init__(self, *, fee_rate: Decimal, slippage_rate: Decimal = Decimal(0)) -> None:
        self._fee_rate = fee_rate
        self._slippage_rate = slippage_rate

    def estimate(self, order: PlannedOrder, book: OrderBook) -> CostEstimate:
        levels = _levels(order, book)
        price = _reference(order, levels)
        if price is None:
            return CostEstimate(fee=Decimal(0), slippage=Decimal(0),
                                total=Decimal(0), fillable=False)
        notional = order.quantity * price
        fee = notional * self._fee_rate
        slippage = notional * self._slippage_rate
        available = sum((lv.quantity for lv in levels), Decimal(0))
        return CostEstimate(fee=fee, slippage=slippage, total=fee + slippage,
                            fillable=available >= order.quantity)


class DepthWalkCostModel(CostModel):
    """Walks the book level by level and charges the real average price.

    This is the model a backtest has to pass to be believed. Slippage is the
    gap between the volume-weighted fill and the touch, which is precisely the
    cost that a thin IDR book imposes and that a flat assumption hides.

    An order deeper than the book returns ``fillable=False`` with the cost of
    the part that would fill, so the caller sees both that it is impossible
    and how expensive the reachable portion was.
    """

    def __init__(self, *, fee_rate: Decimal) -> None:
        self._fee_rate = fee_rate

    def estimate(self, order: PlannedOrder, book: OrderBook) -> CostEstimate:
        levels = _levels(order, book)
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
