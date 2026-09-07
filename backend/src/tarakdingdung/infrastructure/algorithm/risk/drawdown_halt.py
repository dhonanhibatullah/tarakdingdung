from tarakdingdung.domain.contracts.algorithm.risk import RiskRule
from tarakdingdung.domain.models.algorithm import TargetWeights
from tarakdingdung.domain.models.portfolio import Portfolio, RiskState
from tarakdingdung.infrastructure.algorithm.shared.weights import flat


class DrawdownHaltRiskRule(RiskRule):
    """Stops trading once the drawdown budget is spent.

    The budget is fixed in advance, per the research: a drawdown limit chosen
    while losing money is not a limit.
    """

    def __init__(self, *, max_drawdown: float) -> None:
        self._max = max_drawdown

    def apply(self, weights: TargetWeights, portfolio: Portfolio,
              state: RiskState) -> TargetWeights:
        peak = float(state.equity_peak)
        if peak <= 0:
            return weights
        drawdown = (peak - float(portfolio.equity)) / peak
        return flat(weights) if drawdown > self._max else weights
