from abc import ABC, abstractmethod

from tarakdingdung.domain.models.algorithm import Signals, TargetWeights
from tarakdingdung.domain.models.portfolio import Portfolio


class Allocator(ABC):
    """Turns conviction into position sizes.

    The same signals sized equal-weight or volatility-targeted are genuinely
    different risk profiles with no change to the signal code, which is why
    this is a seam. Implementations emit only symbols present in the input
    signals, and gross exposure never exceeds one.
    """

    @abstractmethod
    def allocate(self, signals: Signals, portfolio: Portfolio) -> TargetWeights: ...
