from tarakdingdung.domain.contracts.algorithm.risk import RiskResult, RiskRule, RiskState
from tarakdingdung.domain.models.decision import Weight


class PerPositionCap(RiskRule):
    def __init__(self, max_weight: float) -> None:
        self._max_weight = max_weight

    def apply(self, weights: list[Weight], state: RiskState) -> RiskResult:
        capped = [
            Weight(w.symbol_id, min(w.weight, self._max_weight)) for w in weights
        ]
        return RiskResult(weights=capped, halted=False, rule="per_position_cap")
