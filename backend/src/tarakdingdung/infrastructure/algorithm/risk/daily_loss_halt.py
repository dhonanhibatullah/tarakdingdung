from decimal import Decimal

from tarakdingdung.domain.contracts.algorithm.risk import RiskResult, RiskRule, RiskState
from tarakdingdung.domain.models.decision import Weight


class DailyLossHalt(RiskRule):
    def __init__(self, max_daily_loss: Decimal) -> None:
        self._max_daily_loss = max_daily_loss

    def apply(self, weights: list[Weight], state: RiskState) -> RiskResult:
        if state.daily_pnl <= -self._max_daily_loss:
            return RiskResult(
                weights=[],
                halted=True,
                rule="daily_loss_halt",
                reason="daily loss limit breached",
            )
        return RiskResult(weights=weights, halted=False, rule="daily_loss_halt")
