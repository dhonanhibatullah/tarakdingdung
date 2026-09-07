from abc import ABC, abstractmethod

from tarakdingdung.domain.models.performance import EquityPoint, Fill, PerformanceReport


class PerformanceEvaluator(ABC):
    """Scores a completed run from its equity curve and fills.

    Reports gross and net side by side with an explicit cost drag, because a
    strategy that looks good before costs and dies after is the most common
    outcome and must not be readable as a success.
    """

    @abstractmethod
    def evaluate(self, curve: tuple[EquityPoint, ...],
                 fills: tuple[Fill, ...]) -> PerformanceReport: ...
