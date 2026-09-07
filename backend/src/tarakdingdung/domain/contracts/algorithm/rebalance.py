from abc import ABC, abstractmethod
from collections.abc import Mapping
from decimal import Decimal

from tarakdingdung.domain.models.algorithm import TargetWeights, TradeIntent
from tarakdingdung.domain.models.market import Symbol
from tarakdingdung.domain.models.portfolio import Portfolio


class Rebalancer(ABC):
    """Turns a desired portfolio into the trades that would reach it.

    Applies our own policy — no-trade bands, turnover caps — deciding what is
    worth trading at all. Venue rules are deliberately not its concern; those
    belong to the order planner, and merging the two produces backtests that
    trade quantities the exchange refuses.

    This is also the one place where float weights meet a Decimal portfolio,
    which is why the conversion is auditable rather than scattered.
    """

    @abstractmethod
    def plan(self, target: TargetWeights, portfolio: Portfolio,
             prices: Mapping[Symbol, Decimal]) -> tuple[TradeIntent, ...]: ...
