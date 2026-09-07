from tarakdingdung.domain.contracts.algorithm.risk import RiskRule
from tarakdingdung.domain.models.algorithm import TargetWeights
from tarakdingdung.domain.models.portfolio import Portfolio, RiskState
from tarakdingdung.infrastructure.algorithm.shared.weights import flat


class VolatilityKillSwitchRiskRule(RiskRule):
    """De-risks entirely when realised volatility exceeds a threshold.

    Returns empty weights rather than raising, because a halt is a decision
    that belongs in the equity curve as a flat period, not in a stack trace.
    """

    def __init__(self, *, max_volatility: float) -> None:
        self._max = max_volatility

    def apply(self, weights: TargetWeights, portfolio: Portfolio,
              state: RiskState) -> TargetWeights:
        return flat(weights) if state.realized_volatility > self._max else weights
