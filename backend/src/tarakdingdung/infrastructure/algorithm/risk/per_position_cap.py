from tarakdingdung.domain.contracts.algorithm.risk import RiskRule
from tarakdingdung.domain.models.algorithm import TargetWeights
from tarakdingdung.domain.models.portfolio import Portfolio, RiskState


class PerPositionCapRiskRule(RiskRule):
    """Clamps any single position to a maximum absolute weight.

    Clamping is naturally idempotent: a weight already inside the bound is
    left exactly as it was.
    """

    def __init__(self, *, max_weight: float) -> None:
        self._max = max_weight

    def apply(self, weights: TargetWeights, portfolio: Portfolio,
              state: RiskState) -> TargetWeights:
        return TargetWeights(
            timestamp=weights.timestamp,
            weights={symbol: max(-self._max, min(self._max, weight))
                     for symbol, weight in weights.weights.items()})
