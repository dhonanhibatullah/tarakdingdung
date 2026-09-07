from tarakdingdung.domain.contracts.algorithm.metric import PerformanceEvaluator
from tarakdingdung.domain.models.performance import EquityPoint, Fill, PerformanceReport
from tarakdingdung.infrastructure.algorithm.shared import statistics

_EMPTY = PerformanceReport(total_return=0.0, sharpe=0.0, sortino=0.0,
                           max_drawdown=0.0, turnover=0.0, gross_return=0.0,
                           net_return=0.0, cost_drag=0.0, trade_count=0)


class StandardPerformanceEvaluator(PerformanceEvaluator):
    """Scores a run from its equity curve and fills.

    ``periods_per_year`` must match the curve's sampling — 365 for daily
    points, 8760 for hourly. Getting it wrong scales Sharpe by the square root
    of the error, which is the easiest way to manufacture a number that looks
    like an edge.

    Gross return adds the fees back to the final equity: it is what the
    strategy would have earned trading for free, and the gap to net is the
    cost drag the research says decides most strategies.
    """

    def __init__(self, *, periods_per_year: float = 365.0) -> None:
        self._periods_per_year = periods_per_year

    def evaluate(self, curve: tuple[EquityPoint, ...],
                 fills: tuple[Fill, ...]) -> PerformanceReport:
        if len(curve) < 2:
            return _EMPTY

        equity = [float(point.equity) for point in curve]
        start, end = equity[0], equity[-1]
        if start <= 0:
            return _EMPTY

        returns = statistics.simple_returns(equity)
        fees = sum(float(f.fee) for f in fills)
        traded = sum(float(f.quantity * f.price) for f in fills)

        net_return = end / start - 1.0
        gross_return = (end + fees) / start - 1.0

        return PerformanceReport(
            total_return=net_return,
            sharpe=statistics.annualised_ratio(
                returns, statistics.stdev(returns), self._periods_per_year),
            sortino=statistics.annualised_ratio(
                returns, statistics.downside_stdev(returns), self._periods_per_year),
            max_drawdown=statistics.max_drawdown(equity),
            turnover=traded / start,
            gross_return=gross_return,
            net_return=net_return,
            cost_drag=gross_return - net_return,
            trade_count=len(fills),
        )
