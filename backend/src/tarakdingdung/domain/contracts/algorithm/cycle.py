from abc import ABC, abstractmethod
from collections.abc import Mapping
from uuid import UUID

from tarakdingdung.domain.models.algorithm import CyclePlan
from tarakdingdung.domain.models.market import MarketSnapshot, Symbol, SymbolRules
from tarakdingdung.domain.models.portfolio import Portfolio, RiskState


class CyclePlanner(ABC):
    """The whole decision, from market data to submittable orders, as one pure
    function.

    This exists so the backtester and the live engine cannot diverge. Both call
    it with the same arguments and act on the same result; they differ only in
    where the snapshot came from and what is done with the orders. Written as
    two loops instead, they would drift, and a backtest that disagrees with
    live is worse than no backtest.

    It stays in the algorithm layer because it does no I/O: it composes
    ``Strategy``, ``RiskRule``, ``Rebalancer`` and ``OrderPlanner``, all of
    which are themselves pure.

    ``strategy_id`` is here because client order ids are derived from it, and
    they must be identical for a given cycle no matter which caller computed
    the plan — that determinism is what makes reconciling an unconfirmed
    submission safe instead of a way to double a position.
    """

    @abstractmethod
    def plan(self, *, strategy_id: UUID, snapshot: MarketSnapshot,
             portfolio: Portfolio, state: RiskState,
             rules: Mapping[Symbol, SymbolRules]) -> CyclePlan: ...
