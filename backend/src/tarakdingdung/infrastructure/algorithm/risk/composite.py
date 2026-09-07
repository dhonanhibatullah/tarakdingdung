from tarakdingdung.domain.contracts.algorithm.risk import RiskRule
from tarakdingdung.domain.models.algorithm import TargetWeights
from tarakdingdung.domain.models.portfolio import Portfolio, RiskState


class CompositeRiskRule(RiskRule):
    """Applies rules in order, and is itself a rule.

    Being a ``RiskRule`` is what lets an overlay nest inside another one
    without callers knowing. Every constituent contracts weights toward zero
    and never expands them, so the composition inherits idempotence.
    """

    def __init__(self, rules: tuple[RiskRule, ...]) -> None:
        self._rules = rules

    def apply(self, weights: TargetWeights, portfolio: Portfolio,
              state: RiskState) -> TargetWeights:
        for rule in self._rules:
            weights = rule.apply(weights, portfolio, state)
        return weights
