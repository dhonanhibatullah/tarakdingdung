from tarakdingdung.domain.contracts.algorithm.risk import RiskRule
from tarakdingdung.domain.models.algorithm import TargetWeights
from tarakdingdung.domain.models.portfolio import Portfolio, RiskState
from tarakdingdung.infrastructure.algorithm.shared.weights import flat


class DailyLossHaltRiskRule(RiskRule):
    """Flattens for the day once the daily loss limit is breached.

    The limit is a fraction of current equity rather than a fixed amount, so
    it scales with the book instead of becoming meaningless as it grows.
    """

    def __init__(self, *, max_daily_loss: float) -> None:
        self._max = max_daily_loss

    def apply(self, weights: TargetWeights, portfolio: Portfolio,
              state: RiskState) -> TargetWeights:
        equity = float(portfolio.equity)
        if equity <= 0:
            return flat(weights)
        return flat(weights) if -float(state.daily_pnl) / equity > self._max else weights
