from abc import ABC, abstractmethod

from tarakdingdung.domain.models.performance import OverfittingReport, TrialResult


class OverfittingTest(ABC):
    """Judges whether a parameter search found an edge or fitted noise.

    The baseline implementation is the Probability of Backtest Overfitting
    test, which the research identifies as the one broadly transferable
    technique in the literature. It is an interface so that a cheaper
    robustness proxy can stand beside it when trials are expensive.
    """

    @abstractmethod
    def evaluate(self, trials: tuple[TrialResult, ...]) -> OverfittingReport: ...
