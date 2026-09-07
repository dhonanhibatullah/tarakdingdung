from tarakdingdung.domain.contracts.algorithm.risk import RiskRule
from tarakdingdung.domain.models.algorithm import TargetWeights
from tarakdingdung.domain.models.portfolio import Portfolio, RiskState
from tarakdingdung.infrastructure.algorithm.shared.weights import flat


class HaltFlagRiskRule(RiskRule):
    """Honours an externally set halt: hold nothing while it stands.

    The manual override — an operator, or an upstream supervisor, deciding to
    stop without having to reach into the strategy.
    """

    def apply(self, weights: TargetWeights, portfolio: Portfolio,
              state: RiskState) -> TargetWeights:
        return flat(weights) if state.halted else weights
