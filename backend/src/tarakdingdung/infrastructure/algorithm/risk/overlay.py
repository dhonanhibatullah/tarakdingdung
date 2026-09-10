from tarakdingdung.domain.contracts.algorithm.risk import (
    RiskOverlay,
    RiskResult,
    RiskRule,
    RiskState,
)
from tarakdingdung.domain.models.decision import Weight


class StandardRiskOverlay(RiskOverlay):
    def __init__(self, rules: list[RiskRule]) -> None:
        self._rules = rules

    def apply(self, weights: list[Weight], state: RiskState) -> RiskResult:
        current = weights
        for rule in self._rules:
            result = rule.apply(current, state)
            if result.halted:
                return result
            current = result.weights
        return RiskResult(weights=current, halted=False, rule="")
