from abc import ABC, abstractmethod

from tarakdingdung.domain.models.algorithm import TargetWeights
from tarakdingdung.domain.models.market import MarketSnapshot
from tarakdingdung.domain.models.portfolio import Portfolio


class Strategy(ABC):
    """The only interface the backtester, paper trader and live engine see.

    Whether the weights come from a chained pipeline of the blocks in this
    package or from a trained policy is invisible to callers, so replacing one
    with the other moves nothing else.

    Taking nothing but a snapshot and a portfolio is what makes lookahead bias
    structurally impossible: there is no clock, no repository and no exchange
    client to reach past the snapshot's cut-off with.
    """

    @abstractmethod
    def decide(self, snapshot: MarketSnapshot, portfolio: Portfolio) -> TargetWeights: ...
