from abc import ABC, abstractmethod

from tarakdingdung.domain.models.algorithm import TargetWeights
from tarakdingdung.domain.models.portfolio import Portfolio, RiskState


class RiskRule(ABC):
    """Caps and kill-switches applied after allocation.

    Weights in, weights out, so rules compose into a chain — a per-coin cap, a
    per-venue cap, a volatility kill-switch and a daily-loss halt are four
    independent rules, and adding a control is adding a file rather than
    editing the pipeline.

    Implementations must be idempotent: applying twice equals applying once,
    or a composed chain would silently compound its reductions. A rule that
    trips returns reduced or empty weights and never raises, because a halt
    belongs in the equity curve as a flat period rather than in a stack trace.
    """

    @abstractmethod
    def apply(self, weights: TargetWeights, portfolio: Portfolio,
              state: RiskState) -> TargetWeights: ...
