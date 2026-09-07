from abc import ABC, abstractmethod

from tarakdingdung.domain.models.algorithm import CostEstimate, PlannedOrder
from tarakdingdung.domain.models.market import OrderBook


class CostModel(ABC):
    """Estimates what an order really costs against a given book.

    A contract rather than a function because several are needed: a flat taker
    fee for smoke tests, a depth-walking model for honest backtests, and a
    deliberately pessimistic one for stress runs.

    Cost is non-negative and non-decreasing in order size, and ``fillable`` is
    False whenever the requested size exceeds the book's depth.
    """

    @abstractmethod
    def estimate(self, order: PlannedOrder, book: OrderBook) -> CostEstimate: ...
