from decimal import Decimal

from tarakdingdung.domain.contracts.algorithm.metric import Metric


class StandardMetric(Metric):
    def sharpe(self, returns: list[float]) -> float:
        if len(returns) < 2:
            return 0.0
        mean = sum(returns) / len(returns)
        var = sum((r - mean) ** 2 for r in returns) / len(returns)
        std = var ** 0.5
        if std < 1e-12:
            return 0.0
        return mean / std

    def max_drawdown(self, equity: list[Decimal]) -> float:
        if not equity:
            return 0.0
        peak = equity[0]
        max_dd = 0.0
        for value in equity:
            if value > peak:
                peak = value
            if peak > 0:
                dd = float((peak - value) / peak)
                if dd > max_dd:
                    max_dd = dd
        return max_dd

    def turnover(self, trade_values: list[Decimal]) -> float:
        return float(sum(trade_values))
