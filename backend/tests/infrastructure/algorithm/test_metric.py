from decimal import Decimal

from tarakdingdung.infrastructure.algorithm.metric.standard import StandardMetric


def test_sharpe_zero_for_single_return():
    m = StandardMetric()
    assert m.sharpe([0.1]) == 0.0


def test_sharpe_positive_for_positive_returns():
    m = StandardMetric()
    assert m.sharpe([0.1, 0.2, 0.3]) > 0


def test_sharpe_zero_for_flat_returns():
    m = StandardMetric()
    assert m.sharpe([0.1, 0.1, 0.1]) == 0.0


def test_max_drawdown():
    m = StandardMetric()
    equity = [Decimal("100"), Decimal("120"), Decimal("90"), Decimal("110")]
    dd = m.max_drawdown(equity)
    assert dd == float((Decimal("120") - Decimal("90")) / Decimal("120"))


def test_max_drawdown_empty():
    assert StandardMetric().max_drawdown([]) == 0.0


def test_turnover_sums_values():
    m = StandardMetric()
    assert m.turnover([Decimal("100"), Decimal("50")]) == 150.0
