from tarakdingdung.domain.contracts.algorithm.risk import RiskResult, RiskRule, RiskState
from tarakdingdung.domain.models.decision import Weight


class VolatilityKillSwitch(RiskRule):
    def __init__(self, max_volatility: float) -> None:
        self._max_volatility = max_volatility

    def apply(self, weights: list[Weight], state: RiskState) -> RiskResult:
        if state.volatility > self._max_volatility:
            return RiskResult(
                weights=[],
                halted=True,
                rule="volatility_kill_switch",
                reason="volatility threshold exceeded",
            )
        return RiskResult(weights=weights, halted=False, rule="volatility_kill_switch")
