from abc import ABC, abstractmethod
from collections.abc import Mapping

from tarakdingdung.domain.models.algorithm import OrderPlan, TradeIntent
from tarakdingdung.domain.models.market import Symbol, SymbolRules


class OrderPlanner(ABC):
    """Turns trade intents into orders a venue will actually accept.

    Applies the exchange's rules — tick size, step size, min notional — and is
    where an intent is rejected for being too small to place.

    Implementations must account for every input intent exactly once across
    the returned plan's ``orders`` and ``rejected``. Nothing is silently
    dropped: an intent that vanishes below min-notional is the most common
    source of unexplained live-versus-backtest divergence, and the reason has
    to survive to be diagnosable.
    """

    @abstractmethod
    def plan(self, intents: tuple[TradeIntent, ...],
             rules: Mapping[Symbol, SymbolRules]) -> OrderPlan: ...
