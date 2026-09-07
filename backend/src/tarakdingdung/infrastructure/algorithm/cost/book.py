from decimal import Decimal

from tarakdingdung.domain.models.algorithm import PlannedOrder, Side
from tarakdingdung.domain.models.market import BookLevel, OrderBook


def facing_levels(order: PlannedOrder, book: OrderBook) -> tuple[BookLevel, ...]:
    """The side of the book the order consumes: a buy lifts asks, a sell hits
    bids. Getting this backwards makes every cost estimate a credit."""
    return book.asks if order.side is Side.BUY else book.bids


def touch_price(order: PlannedOrder,
                levels: tuple[BookLevel, ...]) -> Decimal | None:
    """Best available price, falling back to the order's own limit when the
    book is empty."""
    return levels[0].price if levels else order.price
